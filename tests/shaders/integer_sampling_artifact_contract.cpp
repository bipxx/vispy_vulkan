#include "shader/artifact.hpp"
#include <SPIRV/spirv.hpp11>
#include <iostream>
#include <stdexcept>
#include <set>
using namespace vispy::shader;
namespace {
size_t checks = 0;
void require(bool value, const std::string& why) { ++checks; if (!value) throw std::runtime_error(why); }
const std::string vs = "in vec2 p;out vec2 uv;uniform usampler2D words;void main(){uv=p;uint w=texture(words,p).r;gl_Position=vec4(p+vec2(float(w&1u)*0.000001),0,1);}";
const std::string fs = "in vec2 uv;uniform usampler2D words;void main(){uint w=texture(words,uv).r;gl_FragColor=vec4(float(w&255u)/255.0,0,0,1);}";
std::vector<IntegerSamplePolicy> policies(const PortableShaderArtifact& base, IntegerWrap wrap = IntegerWrap::Repeat) {
    std::vector<IntegerSamplePolicy> out;
    for (const auto& use : base.integer_sample_uses)
        out.push_back({use.texture_binding,use.sampler_binding,use.scalar,wrap,IntegerWrap::MirroredRepeat,true,true});
    return out;
}
size_t count(const std::vector<uint32_t>& words, spv::Op opcode) {
    size_t n = 0;
    for (size_t at = 5; at < words.size();) {
        const auto width = words[at] >> 16;
        require(width && width <= words.size()-at, "instruction bounds");
        n += spv::Op(words[at]&0xffff) == opcode; at += width;
    }
    return n;
}
bool live(const SpvSampledStage& stage, uint32_t binding) {
    return std::any_of(stage.resource_usage.begin(),stage.resource_usage.end(),[&](auto r){return r.binding==binding;});
}
void stages_and_cache() {
    PortableShaderCache cache;
    NormalizeOptions options; options.base_level_sampling = true;
    auto base = cache.get_or_build(vs,fs,options,"pinned-test");
    require(base->ok, base->error);
    require(base->integer_sample_uses.size()==1 && base->integer_sample_uses[0].stage_mask==3,"live semantic pair joins both stages");
    const auto old_words = base->spv_frag;
    bool hit = true; uint64_t ns=0;
    auto specialized = cache.specialize_integer_sampling(base,policies(*base),&hit,&ns);
    require(specialized && specialized->ok && !hit, specialized ? specialized->error : "null specialization");
    require(specialized->identity!=base->identity && specialized->integer_sample_uses==base->integer_sample_uses,"self-contained variant retains original requirements");
    require(base->spv_frag==old_words && specialized->attributes.size()==base->attributes.size(),"base immutable and input count preserved");
    require(specialized->timings.integer_sampling_builds==1 && specialized->timings.integer_samples_lowered==2,"actual two-stage lowerer work");
    require(specialized->timings.normalizations==0 && specialized->timings.parse_calls==0 && specialized->timings.link_calls==0 && specialized->timings.spirv_stages==0,"specialization does not repeat GLSL compilation");
    require(specialized->samplers.size()==base->samplers.size() && specialized->samplers[0].name==base->samplers[0].name && specialized->samplers[0].texture_stage_mask==3 && specialized->samplers[0].sampler_stage_mask==0,"stable sampler slots use actual fetch liveness");
    for (const auto* words : {&specialized->spv_vert,&specialized->spv_frag}) {
        require(count(*words,spv::Op::OpImageSampleExplicitLod)==0 && count(*words,spv::Op::OpImageSampleImplicitLod)==0 && count(*words,spv::Op::OpSampledImage)==0,"normalized sample and dead combined sampler removed");
        require(count(*words,spv::Op::OpImageFetch)==1 && count(*words,spv::Op::OpImageQuerySizeLod)==1,"validated query+fetch output");
    }
    auto repeated=cache.specialize_integer_sampling(base,policies(*base),&hit,&ns);
    require(hit && repeated==specialized,"warm lookup returns exact immutable portable allocation");
    require(cache.specialize_integer_sampling(specialized,policies(*base),&hit)==specialized && hit,"same-policy idempotence");
    auto other=cache.specialize_integer_sampling(base,policies(*base,IntegerWrap::ClampToEdge),&hit);
    require(other->ok && !hit && other->identity!=specialized->identity,"wrap snapshot namespaces existing cache");
    auto missing=cache.specialize_integer_sampling(base,{});
    require(missing && !missing->ok,"missing actual policy rejected");
    auto wrong=policies(*base); wrong[0].scalar=ShaderScalarType::Sint;
    require(!cache.specialize_integer_sampling(base,wrong)->ok,"signedness mismatch rejected");
    wrong=policies(*base); wrong[0].nearest=false;
    require(!cache.specialize_integer_sampling(base,wrong)->ok,"linear policy rejected");
    wrong=policies(*base); wrong[0].base_level_only=false;
    require(!cache.specialize_integer_sampling(base,wrong)->ok,"non-base policy rejected");
    require(!integer_sampling_generated_stage_error(*specialized,1,"endpoint compute").empty() && !integer_sampling_generated_stage_error(*specialized,2,"line consumer").empty(),"regenerated sources cannot mistake lowered words for support");
    const auto retained=std::weak_ptr<const PortableShaderArtifact>(base);
    cache.clear(); base.reset();
    require(retained.expired() && specialized->ok && !specialized->spv_vert.empty(),"specialized record has no hidden base owner and survives cache clear/loss");
    PortableShaderCache tiny(1,1024*1024);
    auto tb=tiny.get_or_build(vs,fs,options,"tiny"); auto ts=tiny.specialize_integer_sampling(tb,policies(*tb));
    require(ts->ok && tiny.size()==1 && tiny.find_portable(ts->identity)==ts && !tiny.find_portable(tb->identity),"policy variants use same bounded entry budget");
    require(ts->storage_bytes()>sizeof(PortableShaderArtifact) && tiny.storage_bytes()>=ts->storage_bytes(),"owned policy/source/SPIRV capacities charged");
}
void structural_and_float() {
    for (auto identity : {VertexIdentityPolicy::Native,VertexIdentityPolicy::Affine,VertexIdentityPolicy::Indexed,VertexIdentityPolicy::BatchAffine,VertexIdentityPolicy::BatchIndexed}) {
        PortableShaderCache cache;
        NormalizeOptions o; o.base_level_sampling=true; o.vertex_identity=identity;
        const auto source="in vec2 p;uniform usampler2D words;void main(){uint w=texture(words,p).r;gl_Position=vec4(p+vec2(float((uint(gl_VertexID)+uint(gl_InstanceID)+w)&1u)*0.000001),0,1);}";
        auto b=cache.get_or_build(source,"void main(){gl_FragColor=vec4(1);}",o,"structural");
        require(b->ok,b->error); auto s=cache.specialize_integer_sampling(b,policies(*b)); require(s->ok,s->error);
        require(s->options.vertex_identity==identity && s->vertex_identity_binding==b->vertex_identity_binding && s->batch_instance_binding==b->batch_instance_binding && s->attributes.size()==b->attributes.size(),"structural identity metadata survives sampling composition");
        require(integer_sampling_generated_stage_error(*s,2,"consumer").empty(),"unaffected generated fragment remains admitted");
    }
    PortableShaderCache cache;
    NormalizeOptions point; point.base_level_sampling=true; point.point_sprites=true;
    auto pb=cache.get_or_build("in vec2 p;void main(){gl_Position=vec4(p,0,1);gl_PointSize=2;}","uniform isampler2D words;void main(){gl_FragColor=vec4(float(texture(words,gl_PointCoord).r&255)/255.0);}",point,"points");
    require(pb->ok,pb->error); auto ps=cache.specialize_integer_sampling(pb,policies(*pb)); require(ps->ok,ps->error);
    require(ps->point_sprites && ps->point_identity_binding==pb->point_identity_binding,"point structural ABI preserved");
    for (const auto& fragment : {std::string("uniform sampler2D words;void main(){gl_FragColor=texture(words,vec2(.3));}"),std::string("uniform usampler2D words;void main(){gl_FragColor=vec4(texelFetch(words,ivec2(0),0));}")}) {
        auto b=cache.get_or_build("in vec2 p;void main(){gl_Position=vec4(p,0,1);}",fragment,{},"compat");
        require(b->ok,b->error); require(b->integer_sample_uses.empty(),"float/fetch-only has no sampling requirements");
        auto s=cache.specialize_integer_sampling(b,{},nullptr); require(s==b,"float/fetch byte-identical same owner path");
    }
    auto mixed=cache.get_or_build("in vec2 p;out vec2 uv;void main(){uv=p;gl_Position=vec4(p,0,1);}","in vec2 uv;uniform usampler2D ints;uniform sampler2D floats;void main(){gl_FragColor=texture(floats,uv)+vec4(texture(ints,uv)&255u)/255.0;}",{},"mixed");
    require(mixed->ok,mixed->error); auto ms=cache.specialize_integer_sampling(mixed,policies(*mixed));require(ms->ok,ms->error);
    size_t floats=0,ints=0;
    for(const auto& sampler:ms->samplers) if(sampler.sample_scalar==ShaderScalarType::Float){++floats;require(sampler.sampler_stage_mask==2,"float sampler retained live");}else{++ints;require(sampler.sampler_stage_mask==0,"integer sampler dead");}
    require(floats==1 && ints==1 && count(ms->spv_frag,spv::Op::OpImageSampleImplicitLod)==1,"mixed float instruction survives integer specialization");
}
void compute_and_failures() {
    auto source=[](const std::string& lod){return "#version 450\nlayout(local_size_x=1) in;layout(set=0,binding=1) uniform utexture2D tex;layout(set=0,binding=2) uniform sampler samp;layout(std430,set=0,binding=3) buffer Out{uvec4 value;} output_data;void main(){output_data.value=textureLod(usampler2D(tex,samp),vec2(.25),"+lod+");}";};
    auto c=compile_vulkan_compute(source("0.0"));require(c.ok,c.log);
    auto q=integer_sample_bindings(c.compute.words,4);require(q.ok&&q.bindings.size()==1&&q.bindings[0].stage_mask==4,"compute explicit LOD0 semantic inspection is truthful");
    auto l=lower_integer_nearest_2d(c.compute.words,{{1,2,ShaderScalarType::Uint,IntegerWrap::Repeat,IntegerWrap::ClampToEdge,true,true}});require(l.ok,l.error);
    auto f=finalize_sampled_stage(l.words,4);require(f.ok,f.error);require(live(f,1)&&!live(f,2)&&live(f,3),"compute query/fetch liveness excludes dead sampler");
    auto nonzero=compile_vulkan_compute(source("1.0"));require(nonzero.ok,nonzero.log);
    auto nonzero_uses=integer_sample_bindings(nonzero.compute.words,4);
    require(nonzero_uses.ok&&nonzero_uses.bindings.size()==1,"compute nonzero LOD inspection retains the resource pair for actual-policy materialization");
    auto nonzero_lowered=lower_integer_nearest_2d(nonzero.compute.words,{{1,2,ShaderScalarType::Uint,IntegerWrap::Repeat,IntegerWrap::ClampToEdge,true,true}});
    require(nonzero_lowered.ok&&nonzero_lowered.samples_lowered==1,"captured one-level nearest policy specializes actual compute nonzero LOD");
    require(!integer_sample_bindings({1,2,3},1).ok,"invalid module rejected");
    require(!integer_sample_bindings(c.compute.words,3).ok,"combined query stage refused");
}
void exact_io_interface() {
    const std::string vertex="#version 450\nlayout(location=0) in vec2 p;layout(location=2,component=1) flat out uint token;layout(location=3) out vec2 witness[2];layout(set=0,binding=1) uniform utexture2D tex;layout(set=0,binding=2) uniform sampler smp;void main(){token=texture(usampler2D(tex,smp),p).r;witness[0]=p;witness[1]=-p;gl_Position=vec4(p,0,1);}";
    const std::string fragment="#version 450\nlayout(location=2,component=1) flat in uint token;layout(location=3) in vec2 witness[2];layout(location=0) out vec4 color;void main(){color=vec4(float(token&255u)/255.0,witness[0].x,witness[1].y,1);}";
    auto c=compile_vulkan_glsl(vertex,fragment,false);require(c.ok,c.log);
    auto l=lower_integer_nearest_2d(c.vertex.words,{{1,2,ShaderScalarType::Uint,IntegerWrap::Repeat,IntegerWrap::MirroredRepeat,true,true}});require(l.ok,l.error);
    auto f=finalize_sampled_stage(l.words,1);require(f.ok,f.error);
    std::string error;
    require(same_sampled_stage_io(c.vertex.words,f.words,error),"actual flat/component/array/BuiltIn IO survives finalization: "+error);
    for(auto decoration:{spv::Decoration::Location,spv::Decoration::Component,spv::Decoration::BuiltIn}) {
        auto changed=f.words;bool found=false;
        for(size_t at=5;at<changed.size();) {
            const auto n=changed[at]>>16;const auto op=spv::Op(changed[at]&0xffffu);
            const size_t offset=op==spv::Op::OpDecorate?2:op==spv::Op::OpMemberDecorate?3:0;
            if(offset && n>offset+1 && changed[at+offset]==uint32_t(decoration)) {++changed[at+offset+1];found=true;break;}
            at+=n;
        }
        require(found,"compiled interface contains required decoration");
        require(!same_sampled_stage_io(f.words,changed,error),"guard rejects changed Location/Component/BuiltIn metadata");
    }
    auto changed=f.words;bool removed=false;
    for(size_t at=5;at<changed.size();) {
        const auto n=changed[at]>>16;
        if(spv::Op(changed[at]&0xffffu)==spv::Op::OpDecorate && n==3 && changed[at+2]==uint32_t(spv::Decoration::Flat)) {
            changed.erase(changed.begin()+at,changed.begin()+at+n);removed=true;break;
        }
        at+=n;
    }
    require(removed && !same_sampled_stage_io(f.words,changed,error),"guard rejects missing integer Flat decoration");
    changed=f.words;removed=false;
    for(size_t at=5;at<changed.size();) {
        const auto n=changed[at]>>16;
        if(spv::Op(changed[at]&0xffffu)==spv::Op::OpEntryPoint) {
            changed.erase(changed.begin()+at+n-1);changed[at]=((n-1)<<16)|uint32_t(spv::Op::OpEntryPoint);removed=true;break;
        }
        at+=n;
    }
    require(removed && !same_sampled_stage_io(f.words,changed,error),"guard rejects changed ordered entry-point IO list");
    changed=f.words;bool length=false;
    uint32_t array_length=0;
    for(size_t at=5;at<changed.size();) {const auto n=changed[at]>>16;if(spv::Op(changed[at]&0xffffu)==spv::Op::OpTypeArray){array_length=changed[at+3];break;}at+=n;}
    for(size_t at=5;at<changed.size();) {const auto n=changed[at]>>16;if(spv::Op(changed[at]&0xffffu)==spv::Op::OpConstant && changed[at+2]==array_length){++changed[at+3];length=true;break;}at+=n;}
    require(length && !same_sampled_stage_io(f.words,changed,error),"guard rejects changed referenced array-length definition");
}
}
int main(){try{stages_and_cache();structural_and_float();compute_and_failures();exact_io_interface();std::cout<<"integer sampling artifact contracts: "<<checks<<" checks; no device\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
