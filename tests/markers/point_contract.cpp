#include "shader/normalize.hpp"
#include "shader/glslang_spv.hpp"
#include "shader/artifact.hpp"
#include "runtime_point.hpp"

#ifdef VISPY_TEST_TINT_READER
#include "src/tint/lang/core/ir/module.h"
#include "src/tint/lang/spirv/reader/reader.h"
#endif

#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <limits>
#include <unordered_map>

namespace {
void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}
std::string read(const std::filesystem::path& file) {
    std::ifstream input(file);
    require(input.good(), "missing marker source " + file.string());
    return std::string(std::istreambuf_iterator<char>(input), {});
}
void check(NormalizedShader& normalized) {
    require(normalized.error.empty(), normalized.error);
    auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment, normalized.point_sprites);
    require(compiled.ok, compiled.log + "\n" + normalized.vertex + "\n" + normalized.fragment);
#ifdef VISPY_TEST_TINT_READER
    for (const auto* stage : {&compiled.vertex, &compiled.fragment}) {
        auto ir = tint::spirv::reader::ReadIR(stage->words);
        require(ir == tint::Success, ir == tint::Success ? "" : ir.Failure().reason);
    }
#endif
    std::string error;
    require(reflect_uniform_layout(compiled.vertex.words, normalized.uniforms, normalized.uniform_bytes, error), error);
    require(reflect_uniform_layout(compiled.fragment.words, normalized.uniforms, normalized.uniform_bytes, error), error);
}
void point_lowering() {
    NormalizeOptions options;
    options.point_sprites = true;
    auto normalized = normalize_program(
        "attribute vec2 a_position; attribute float a_size; varying float v_id; "
        "void main(){ gl_Position=vec4(a_position,0,2); gl_PointSize=a_size; v_id=float(gl_VertexID); }",
        "varying float v_id; void main(){ gl_FragColor=gl_FrontFacing ? vec4(gl_PointCoord,v_id,1) : vec4(0); }", options);
    check(normalized);
    require(normalized.point_sprites && normalized.uniforms.back().name == "vispy_point_viewport", "point policy and viewport reflection");
    require(normalized.vertex.find("gl_PointSize") == std::string::npos && normalized.fragment.find("gl_PointCoord") == std::string::npos, "unsupported builtins lowered");
    require(normalized.fragment.find("gl_FrontFacing") == std::string::npos, "GL points are always front-facing");
    require(normalized.vertex.find("int(vispy_point_identity[gl_InstanceIndex].x)") != std::string::npos,
            "original vertex ID uses exact uint32 storage input");
    require(normalized.attributes.size() == 2 && normalized.point_identity_binding == 1 &&
            normalized.vertex.find("readonly buffer VispyPointIdentity") != std::string::npos,
            "identity storage adds no public vertex attribute");
    require(normalized.vertex.find("gl_Position.xy +=") < normalized.vertex.find("gl_Position.y = -"), "quad expansion precedes coordinate conversion");
    require(normalized.vertex.find("gl_Position.w / vispy_point_viewport") != std::string::npos, "window size remains fixed under perspective");
    const float viewport[] = {100, 50};
    std::vector<uint8_t> bytes(normalized.uniform_bytes, 0);
    std::string error;
    require(pack_uniform_value(normalized.uniforms.back(), viewport, sizeof(viewport), bytes.data(), bytes.size(), &error), error);
    auto rejected = normalize_program("void main(){ gl_Position=vec4(0,0,0,1); }",
                                      "void main(){ gl_FragColor=vec4(gl_PointCoord,0,1); }");
    require(rejected.error.find("point-sprite") != std::string::npos, "unadmitted point coordinates fail explicitly");
    rejected = normalize_program("attribute vec2 vispy_point_identity; void main(){gl_Position=vec4(0);}",
                                 "void main(){gl_FragColor=vec4(1);}", options);
    require(rejected.error.find("reserved") != std::string::npos, "reserved identity collision rejected");
}
template<class Function> void rejects(Function&& function, const std::string& message) {
    try { function(); } catch (const std::runtime_error&) { return; }
    throw std::runtime_error(message);
}
template<class T> std::vector<uint8_t> bytes(std::initializer_list<T> values) {
    std::vector<uint8_t> result(values.size() * sizeof(T));
    std::memcpy(result.data(), values.begin(), result.size());
    return result;
}
void identity_and_gather() {
    using namespace vispy::points;
    const uint64_t limit = 1024;
    Selection selection{3, 2, 3};
    require(identity_data(selection, limit) == bytes<uint32_t>({3,0,4,0,3,1,4,1,3,2,4,2}),
            "nonzero first and original instance identities are instance-major");
    for (uint32_t width : {1u, 2u, 4u}) {
        auto index = width == 1 ? bytes<uint8_t>({6,1,4,1}) :
                     width == 2 ? bytes<uint16_t>({6,1,4,1}) : bytes<uint32_t>({6,1,4,1});
        selection = {0,4,1,index,width};
        require(identity_data(selection,limit) == bytes<uint32_t>({6,0,1,0,4,0,1,0}),
                "8/16/32-bit indices preserve duplicate draw ordering");
    }
    auto high = bytes<uint32_t>({16777217,UINT32_MAX});
    selection = {0,2,1,high,4};
    require(identity_data(selection,limit) == bytes<uint32_t>({16777217,0,UINT32_MAX,0}),
            "sparse uint32 identity never passes through float");
    const auto constant = bytes<uint32_t>({0x7fc01234});
    require(gather_data(selection,constant,0,0,4,0,limit) == bytes<uint32_t>({0x7fc01234,0x7fc01234}),
            "constant stride zero ignores sparse vertex indices and preserves bits");
    const auto source = bytes<uint32_t>({91,10,11,73,91,20,21,73,91,30,31,73});
    auto reversed = bytes<uint16_t>({2,0});
    selection = {0,2,4,reversed,2};
    require(gather_data(selection,source,4,16,8,0,limit) ==
            bytes<uint32_t>({30,31,10,11,30,31,10,11,30,31,10,11,30,31,10,11}),
            "interleaved per-vertex views repeat for each original instance");
    require(gather_data(selection,source,4,16,8,2,limit) ==
            bytes<uint32_t>({10,11,10,11,10,11,10,11,20,21,20,21,20,21,20,21}),
            "divisor two selects original instance divided by two");
    rejects([&] { gather_data(selection,source,UINT64_MAX,16,8,0,limit); }, "offset overflow rejected");
    rejects([&] { gather_data(selection,source,4,UINT64_MAX,8,0,limit); }, "stride overflow rejected");
    rejects([&] { identity_data(selection,63); }, "allocation grant checked before payload allocation");
    Selection excessive{0,UINT64_MAX,UINT64_MAX};
    rejects([&] { identity_data(excessive,UINT64_MAX); }, "flattened count overflow rejected");
    Selection incomplete{0,3,1,reversed,2};
    rejects([&] { identity_data(incomplete,limit); }, "truncated indices rejected");
    Selection end{UINT32_MAX,2,1};
    rejects([&] { identity_data(end,limit); }, "arrays uint32 identity overflow rejected");
    Selection empty{0,0,INT32_MAX};
    require(identity_data(empty,limit).empty(), "empty selection does not iterate enormous instance count");
    selection.instances = 0;
    require(identity_data(selection,limit).empty(), "zero original instances remain no draw");
}
void conversion_cache() {
    using namespace vispy::points;
    using Map = std::unordered_map<std::string,std::shared_ptr<std::vector<uint8_t>>>;
    Map cache;
    Selection selection{3,2,2};
    const auto key = conversion_key("identity",selection,41,1,0,0);
    int builds = 0;
    auto build = [&] { ++builds; return std::make_shared<std::vector<uint8_t>>(identity_data(selection,1024)); };
    auto [first, made] = cached_conversion(cache,key,build,2);
    auto [again, rebuilt] = cached_conversion(cache,key,build,2);
    require(made && !rebuilt && first == again && builds == 1, "resident conversion retains exact payload owner");
    require(key != conversion_key("identity",selection,42,1,0,0), "allocation identity prevents address reuse alias");
    require(key != conversion_key("identity",selection,41,2,0,0), "source revision separates pending updates");
    for (int revision : {2,3}) cached_conversion(cache,conversion_key("identity",selection,41,revision,0,0),build,2);
    require(cache.size() == 2 && *first == identity_data(selection,1024), "bounded eviction preserves pending snapshot data");
    const auto count = cache.size();
    rejects([&] { cached_conversion(cache,"invalid",[]() -> Map::mapped_type {
        throw std::runtime_error("invalid source"); }); }, "invalid conversion throws");
    require(cache.size() == count && !cache.contains("invalid"), "failed conversion does not mutate cache");
    auto changed = selection; changed.first++;
    require(key != conversion_key("identity",changed,41,1,0,0), "selection first participates in cache");
    changed = selection; changed.instances++;
    require(key != conversion_key("identity",changed,41,1,0,0), "original instances participate in cache");
    changed = selection; changed.count++;
    require(key != conversion_key("identity",changed,41,1,0,0), "point count participates in cache");
    require(conversion_key("gather",selection,41,1,5,1,4,16,8,2) !=
            conversion_key("gather",selection,41,1,5,2,4,16,8,2), "index revision participates in cache");
    require(conversion_key("gather",selection,41,1,5,1,4,16,8,2) !=
            conversion_key("gather",selection,41,1,5,1,4,16,8,1), "divisor participates in cache");
    require(conversion_key("gather",selection,41,1,5,1,4,16,8,2) !=
            conversion_key("gather",selection,41,1,5,1,8,16,8,2), "view offset participates in cache");
}
void inactive_point_inputs() {
    NormalizeOptions options; options.point_sprites = true;
    auto artifact = vispy::shader::build_portable_shader(
        "attribute float a_count; attribute vec2 a_position; varying float v_id; "
        "void main(){gl_Position=vec4(a_position,0,1);gl_PointSize=3;"
        "v_id=float(gl_VertexID%4+gl_InstanceID%2);}",
        "varying float v_id; void main(){gl_FragColor=vec4(v_id);}", options, "point-contract");
    require(artifact->ok, artifact->error);
    require(artifact->attributes.size() == 1 && artifact->attributes[0].name == "a_position" &&
            artifact->attributes[0].location == 0 && artifact->point_identity_binding == 1,
            "unused count input omitted and remaining public input compacted; identity consumes no attribute");
    require(artifact->vertex.find("int(vispy_point_identity[gl_InstanceIndex].y)") != std::string::npos,
            "original instance ID uses exact uint32 storage input");
}
void capacity_shader_interface() {
    NormalizeOptions options;options.point_sprites=true;options.base_level_sampling=true;
    std::string vertex="attribute float unused_before;";
    for (int n=0;n<32;++n) vertex+="attribute vec4 a_"+std::to_string(n)+";";
    vertex+="varying vec4 unused_varying; varying vec4 color; void main(){vec4 p=vec4(0);";
    for (int n=0;n<32;++n) vertex+="p+=a_"+std::to_string(n)+";";
    vertex+="gl_Position=p;gl_PointSize=3;color=vec4(float(gl_VertexID%4),float(gl_InstanceID%2),0,1);}";
    const std::string fragment="uniform sampler2D u_image;varying vec4 unused_varying;varying vec4 color;"
        "void main(){gl_FragColor=color+texture2D(u_image,vec2(.5));}";
    const auto artifact=vispy::shader::build_portable_shader(vertex,fragment,options,"capacity-contract");
    require(artifact->ok,artifact->error);
    require(artifact->attributes.size()==32&&artifact->point_identity_binding==3,
            "32 actually used user fields retain full budget; identity storage follows user sampler bindings");
    for (uint32_t n=0;n<artifact->attributes.size();++n)
        require(artifact->attributes[n].location==n&&artifact->attributes[n].name!="unused_before",
                "active user locations compact without hidden identity input");
#ifdef VISPY_TEST_TINT_READER
    for(const auto* words:{&artifact->spv_vert,&artifact->spv_frag}) {
        auto ir=tint::spirv::reader::ReadIR(*words);
        require(ir==tint::Success,ir==tint::Success?"":ir.Failure().reason);
    }
#endif
    // Compact only vertex inputs. color remains location one because the
    // paired declared varying before it retains its own original location.
    auto location_words=[](const std::vector<uint32_t>& words,uint32_t storage) {
        std::unordered_map<uint32_t,uint32_t> variables,locations;
        for(size_t n=5;n<words.size();) {
            const auto count=words[n]>>16,op=words[n]&0xffff;
            if(op==59&&count>=4) variables[words[n+2]]=words[n+3];
            if(op==71&&count>=4&&words[n+2]==30) locations[words[n+1]]=words[n+3];
            n+=count;
        }
        std::vector<uint32_t> result;
        for(const auto&[id,location]:locations)
            if(variables.contains(id)&&variables[id]==storage) result.push_back(location);
        return result;
    };
    const auto outputs=location_words(artifact->spv_vert,3),inputs=location_words(artifact->spv_frag,1);
    require(std::find(outputs.begin(),outputs.end(),1)!=outputs.end()&&
            std::find(inputs.begin(),inputs.end(),1)!=inputs.end(),"paired color varying location stays unchanged during input compaction");
    options.point_sprites=false;
    auto ordinary=vispy::shader::build_portable_shader("attribute float unused;attribute vec2 live;"
        "void main(){gl_Position=vec4(live,0,1);}","void main(){gl_FragColor=vec4(1);}",options,"capacity-contract");
    require(ordinary->ok&&ordinary->attributes.size()==1&&ordinary->attributes[0].location==0,
            ordinary->error+"ordinary LINK inputs are live and compact for canonical packed pipeline");
    options.point_sprites=true;
    auto no_ids=vispy::shader::build_portable_shader("attribute vec2 live;void main(){gl_Position=vec4(live,0,1);gl_PointSize=3;}",
        "void main(){gl_FragColor=vec4(1);}",options,"capacity-contract");
    require(no_ids->ok&&!no_ids->point_identity_binding,no_ids->error+"unused identity storage consumes no descriptor");
}
void snapshot_artifact_selection() {
    using namespace vispy::shader;
    using Handle=std::shared_ptr<int>;
    struct Device:DeviceShaderArtifact<Handle,Handle,Handle> {
        std::shared_ptr<const PortableShaderArtifact> portable;
    };
    const std::string vertex="attribute vec2 p;void main(){gl_Position=vec4(p,0,1);gl_PointSize=3;}";
    const std::string fragment="void main(){gl_FragColor=vec4(1);}";
    auto original=std::make_shared<Device>();
    original->portable=build_portable_shader(vertex,fragment,NormalizeOptions{},"route-contract");
    require(original->portable->ok,original->portable->error);
    original->device_generation=1;original->pipeline=std::make_shared<int>(1);original->pipeline_ok=true;
    const auto original_identity=original->portable->identity;
    std::shared_ptr<Device> point_variant;
    int builds=0;
    auto build=[&](const std::shared_ptr<Device>& base) {
        ++builds;require(base==original,"point variant builds from immutable LINK artifact");
        auto result=std::make_shared<Device>();
        NormalizeOptions options;options.point_sprites=true;
        result->portable=build_portable_shader(base->portable->source_vertex,base->portable->source_fragment,options,"route-contract");
        require(result->portable->ok,result->portable->error);
        result->device_generation=1;result->pipeline=std::make_shared<int>(2);result->pipeline_ok=true;
        return result;
    };
    auto pending_point=vispy::points::select_draw_artifact(true,original,point_variant,build);
    require(pending_point==point_variant&&pending_point!=original&&pending_point->portable->point_sprites,
            "point snapshot owns its derived route");
    for(const std::string mode:{"triangles","lines","triangle_strip"}) {
        const auto ordinary=vispy::points::select_draw_artifact(false,original,point_variant,build);
        require(ordinary==original&&!ordinary->portable->point_sprites,
                "points then "+mode+" retains ordinary LINK semantics");
    }
    require(vispy::points::select_draw_artifact(true,original,point_variant,build)==pending_point&&builds==1,
            "alternating routes reuse resident point variant");
    require(original->portable->identity==original_identity&&original->portable->source_vertex==vertex,
            "draw selection never replaces original identity/source");
    std::shared_ptr<Device> affine_variant,indexed_variant;
    int ordinary_builds=0;
    auto build_ordinary=[&](const std::shared_ptr<Device>& base,bool indexed) {
        ++ordinary_builds;require(base==original,"compact variants build from LINK source");
        auto result=std::make_shared<Device>();NormalizeOptions options;
        options.vertex_identity=indexed?VertexIdentityPolicy::Indexed:VertexIdentityPolicy::Affine;
        result->portable=build_portable_shader(base->portable->source_vertex,base->portable->source_fragment,options,"route-contract");
        require(result->portable->ok,result->portable->error);return result;
    };
    const auto pending_affine=vispy::inputs::select_compact_artifact(false,original,affine_variant,indexed_variant,build_ordinary);
    auto pending_indexed=vispy::inputs::select_compact_artifact(true,original,affine_variant,indexed_variant,build_ordinary);
    require(pending_affine==affine_variant&&pending_indexed==indexed_variant&&ordinary_builds==2&&
            vispy::inputs::select_compact_artifact(false,original,affine_variant,indexed_variant,build_ordinary)==pending_affine&&
            original->portable->identity==original_identity,"compact array/indexed/point routes retain immutable LINK and independent resident variants");
    std::weak_ptr<Device> old_indexed=pending_indexed;indexed_variant.reset();
    require(!old_indexed.expired()&&pending_indexed->portable->source_vertex==vertex,"LINK reset leaves pending compact snapshot usable");
    pending_indexed.reset();require(old_indexed.expired(),"retired compact device variant has no parent cycle");
    rejects([&]{vispy::inputs::select_compact_artifact(true,original,affine_variant,indexed_variant,
        [](const auto&,bool)->std::shared_ptr<Device>{throw std::runtime_error("bad compact build");});},"compact build failures propagate");
    require(!indexed_variant&&affine_variant==pending_affine&&original->portable->identity==original_identity,
            "failed indexed build cannot replace affine or original artifacts");
    const auto saved_portable=point_variant->portable;
    point_variant->invalidate();
    require(!point_variant->valid_for(1)&&point_variant->portable==saved_portable,
            "derived device invalidation retains portable shader for rematerialization");
    require(vispy::points::select_draw_artifact(true,original,point_variant,build)==pending_point&&builds==1,
            "loss route selection preserves owned CPU artifact without recompilation");
    std::weak_ptr<Device> retired=pending_point;
    point_variant.reset();
    require(!retired.expired()&&pending_point->portable==saved_portable,
            "relink can clear variant owner while old snapshot stays immutable");
    pending_point.reset();require(retired.expired(),"retired variant has no hidden parent ownership cycle");
    rejects([&] {vispy::points::select_draw_artifact(true,original,point_variant,
        [](const auto&)->std::shared_ptr<Device>{throw std::runtime_error("compile failure");});},"variant compilation failure reported");
    require(!point_variant&&original->portable->identity==original_identity,"failed point build mutates neither route owner");
    auto required_point=std::make_shared<Device>();
    NormalizeOptions required_options;required_options.point_sprites=true;
    required_point->portable=build_portable_shader(vertex,
        "void main(){gl_FragColor=vec4(gl_PointCoord,0,1);}",required_options,"route-contract");
    require(required_point->portable->ok,required_point->portable->error);
    rejects([&] {vispy::points::select_draw_artifact(false,required_point,point_variant,build);},
            "actual original point-coordinate shader still rejects ordinary primitives");
}
void packed_inputs() {
    using namespace vispy::points;
    const auto interleaved = bytes<uint32_t>({99,10,11,77,99,20,21,77,99,30,31,77});
    const auto instances = bytes<uint32_t>({100,200});
    const auto constant = bytes<uint32_t>({0x7fc01234});
    const auto indices = bytes<uint16_t>({2,0,2});
    Selection selected{0,3,4,indices,2};
    std::vector<PackedSource> sources = {
        {interleaved,41,1,4,16,8,0,"positions"},
        {instances,42,1,0,4,4,2,"divisor_two"},
        {constant,43,1,0,0,4,0,"constant"}};
    const auto layout = packed_layout(std::vector<uint32_t>{8,4,4},3,1,16);
    require(layout.offsets == std::vector<uint32_t>({0,8,12}) && layout.stride == 16,
            "three public fields consume one vertex buffer and no hidden attribute");
    const auto packed = packed_data(selected,sources,layout,1024);
    const auto expected = bytes<uint32_t>({
        30,31,100,0x7fc01234,10,11,100,0x7fc01234,30,31,100,0x7fc01234,
        30,31,100,0x7fc01234,10,11,100,0x7fc01234,30,31,100,0x7fc01234,
        30,31,200,0x7fc01234,10,11,200,0x7fc01234,30,31,200,0x7fc01234,
        30,31,200,0x7fc01234,10,11,200,0x7fc01234,30,31,200,0x7fc01234});
    require(packed == expected,"packed instance-major rows preserve duplicate indices, divisor two and exact constant NaN bits");
    std::vector<uint32_t> widths(32,16);
    require(packed_layout(widths,32,1,512).offsets.back() == 496,
            "full active public capacity remains legal with only one granted vertex buffer");
    rejects([&] { packed_layout(widths,31,1,512); },"above public attribute limit rejected");
    rejects([&] { packed_layout(widths,32,0,512); },"zero granted vertex buffers rejected");
    rejects([&] { packed_layout(widths,32,1,511); },"packed stride grant checked");
    rejects([&] { packed_data(selected,sources,layout,191); },"packed total allocation grant checked");
    auto malformed=layout; malformed.offsets[1]++;
    rejects([&] { packed_data(selected,sources,malformed,1024); },"field layout mismatch rejected");
    auto invalid=sources; invalid[0].stride=UINT64_MAX;
    rejects([&] { packed_data(selected,invalid,layout,1024); },"sparse input read overflow rejected");
    Selection sparse{UINT32_MAX,1,1};
    std::vector<PackedSource> constants{{constant,43,1,0,0,4,0,"constant"}};
    const auto constant_layout=packed_layout(std::vector<uint32_t>{4},1,1,4);
    require(packed_data(sparse,constants,constant_layout,4)==constant,
            "largest exact original identity does not cause a constant input fetch");
    Selection first{1,2,1};
    std::vector<PackedSource> vertex_source{sources[0]};
    require(packed_data(first,vertex_source,packed_layout(std::vector<uint32_t>{8},1,1,8),16)==
            bytes<uint32_t>({20,21,30,31}),"nonzero first selects original source rows");
    using Map=std::unordered_map<std::string,std::shared_ptr<std::vector<uint8_t>>>;
    Map cache; std::string stamp;
    const auto key=packed_source_key(sources,91,1,2);
    refresh_sources(stamp,key,cache);
    int builds=0;
    auto build=[&] { ++builds;return std::make_shared<std::vector<uint8_t>>(packed); };
    auto [pending,built]=cached_conversion(cache,"selection",build);
    std::weak_ptr<std::vector<uint8_t>> old=pending;
    refresh_sources(stamp,key,cache);
    require(!cached_conversion(cache,"selection",build).second&&builds==1,
            "resident packed source reuse builds once");
    auto changed=sources;changed[0].revision++;
    refresh_sources(stamp,packed_source_key(changed,91,1,2),cache);
    require(cache.empty()&&!old.expired()&&*pending==packed,
            "attribute update drops stale cache ownership while pending snapshot retains exact old payload");
    pending.reset();require(old.expired(),"no hidden source-parent cycle retains stale packed payload");
    require(key!=packed_source_key(sources,91,2,2),"index revision invalidates geometry source stamp");
    changed=sources;changed[1].divisor=1;
    require(key!=packed_source_key(changed,91,1,2),"divisor participates in packed source stamp");
    // Attribute updates do not change the separately keyed identity storage.
    Map identities;
    const auto identity_key=conversion_key("identity-storage",selected,91,1,91,1);
    auto identity_build=[&] {return std::make_shared<std::vector<uint8_t>>(identity_data(selected,1024));};
    auto [identity,built_identity]=cached_conversion(identities,identity_key,identity_build);
    refresh_sources(stamp,key,cache);
    require(!cached_conversion(identities,identity_key,identity_build).second&&
            identities.at(identity_key)==identity,"attribute source refresh retains independent resident identity allocation");
}
void live_resource_descriptors() {
    NormalizeOptions options; options.base_level_sampling = true;
    const std::string vertex = "void main(){gl_Position=vec4(0,0,0,1);}";
    std::string declarations;
    for (int n = 0; n < 16; ++n) declarations += "uniform sampler2D u_texture_" + std::to_string(n) + ";";
    declarations += "uniform sampler2D dummy1;";
    std::string body = "void main(){vec4 color=vec4(0);";
    for (int n = 0; n < 16; ++n) body += "color+=texture2D(u_texture_" + std::to_string(n) + ",vec2(.5));";
    auto make = [&](bool active) {
        return vispy::shader::build_portable_shader(vertex,
            declarations + "vec4 unused_helper(){return texture2D(dummy1,vec2(.5));}" + body +
            (active ? "color+=texture2D(dummy1,vec2(.5));" : "") + "gl_FragColor=color;}", options, "resource-contract");
    };
    const auto dead = make(false);
    require(dead->ok, dead->error);
    require(dead->samplers.size() == 16, "uncalled helper/declaration does not consume sampler slots");
    require(dead->source_fragment.find("dummy1") != std::string::npos &&
            dead->fragment.find("vispy_tex_dummy1") != std::string::npos,
            "original and normalized source provenance retain inactive declaration");
    for (const auto& sampler : dead->samplers)
        require(sampler.texture_stage_mask == 2 && sampler.sampler_stage_mask == 2,
                "fragment-only live descriptors do not count against vertex stage");
    require(vispy::shader::resource_limit_error(dead->samplers,16,48).empty(), "16 live resources fit granted sampler budget");
    const auto active = make(true);
    require(active->ok && active->samplers.size() == 17, active->error + "all 17 actual samplers remain reflected");
    require(vispy::shader::resource_limit_error(active->samplers,16,48).find("fragment active samplers=17") != std::string::npos,
            "17 actual samplers produce contextual capability error");
    require(vispy::shader::resource_limit_error(dead->samplers,48,15).find("sampled textures=16") != std::string::npos,
            "actual sampled-texture budget is checked independently");
    auto mixed = vispy::shader::build_portable_shader(
        "uniform sampler2D shared; uniform sampler2D vertex_only;"
        "void main(){gl_Position=texture2D(shared,vec2(.5))+texture2D(vertex_only,vec2(.5));}",
        "uniform sampler2D shared; uniform sampler2D fragment_only;"
        "void main(){gl_FragColor=texture2D(shared,vec2(.5))+texture2D(fragment_only,vec2(.5));}", options, "resource-contract");
    require(mixed->ok && mixed->samplers.size() == 3, mixed->error);
    for (const auto& sampler : mixed->samplers) {
        const auto expected = sampler.name == "shared" ? 3u : sampler.name == "vertex_only" ? 1u : 2u;
        require(sampler.texture_stage_mask == expected && sampler.sampler_stage_mask == expected,
                "shared versus single-stage descriptors preserve precise stage visibility: " + sampler.name +
                " texture=" + std::to_string(sampler.texture_stage_mask) + " sampler=" +
                std::to_string(sampler.sampler_stage_mask) + " expected=" + std::to_string(expected));
    }
    auto uniforms = vispy::shader::build_portable_shader("uniform float u_dead;" + vertex,
        "uniform float u_live;void main(){gl_FragColor=vec4(u_live);}", options, "resource-contract");
    require(uniforms->ok && uniforms->uniforms.size() == 2 && uniforms->uniform_stage_mask == 2,
            uniforms->error + "unused uniform packing metadata retained with fragment-only UBO visibility");
    uniforms = vispy::shader::build_portable_shader("uniform float u_dead;" + vertex,
        "void main(){gl_FragColor=vec4(1);}", options, "resource-contract");
    require(uniforms->ok && uniforms->uniforms.size() == 1 && !uniforms->uniform_stage_mask,
            uniforms->error + "fully inactive UBO packing metadata retained without a GPU descriptor");
}
void instanced_marker_hooks() {
    auto normalized = normalize_program(
        "attribute vec2 a_position; void main(){ gl_Position=vec4(a_position,0,1); gl_PointSize=4.0; }",
        "bool isnan(float value){ return !(value<0.0 || value>0.0 || value==0.0); }\n"
        "bool isinf(float value){ return value!=0.0 && value*2.0==value; }\n"
        "void main(){ gl_FragColor=vec4(isnan(0.0)||isinf(0.0) ? 0.0 : 1.0); }");
    check(normalized);
    require(!normalized.point_sprites, "instanced marker route unchanged");
    require(normalized.vertex.find("vispy_corners") == std::string::npos, "no second quad expansion for upstream instanced hooks");
    require(normalized.fragment.find("vispy_user_isnan") != std::string::npos, "composer predicate body retained under distinct name");
}

void ordinary_input_routes() {
    using namespace vispy::inputs;
    const auto interleaved = bytes<uint32_t>({91,10,11,1,2,3,73,91,20,21,4,5,6,73,91,30,31,7,8,9,73});
    const auto constant = bytes<uint32_t>({0x7fc01234});
    std::vector<Source> sources{{interleaved,1,3,4,28,8,0,"position"},
                                {interleaved,1,3,12,28,12,0,"color"},
                                {constant,2,0,0,0,4,0,"constant"}};
    const auto grouped = direct_layout(sources,32,8,2048);
    require(grouped.direct && grouped.streams.size() == 2 && grouped.streams[0].bind_offset == 4 &&
            grouped.slots == std::vector<uint32_t>({0,0,1}) && grouped.offsets == std::vector<uint32_t>({0,8,0}) &&
            grouped.streams[1].stride == 0, "interleaved fields group without copies; constant keeps stride zero");
    sources[1].identity = 9;
    require(!direct_layout(sources,32,2,2048).direct, "different immutable allocations cannot share a physical stream");
    sources[1].identity = 1; sources[1].revision = 4;
    require(!direct_layout(sources,32,2,2048).direct, "different source revisions cannot share a physical stream");
    sources[1].revision = 3; sources[0].divisor = 2;
    require(!direct_layout(sources,32,8,2048).direct, "divisor above one selects compact original-instance rows");
    auto bad = sources; bad[0].offset = UINT64_MAX - 3;
    rejects([&]{direct_layout(bad,32,8,2048);}, "offset-plus-width overflow rejected independently of reads");
    rejects([&]{direct_layout(sources,2,8,2048);}, "active above-capacity inputs fail before packing");
    const auto shifted = bytes<uint32_t>({1,2,3,4,5,6,7,8});
    const std::vector<Source> out_of_order{{shifted,1,0,4,8,4,0,"b"}, {shifted,1,0,8,8,4,0,"c"},
        {shifted,1,0,0,8,4,0,"a"}, {shifted,1,0,12,8,4,0,"d"}};
    const auto ordered = direct_layout(out_of_order,4,2,8);
    require(ordered.direct && ordered.streams.size()==2 && ordered.slots==std::vector<uint32_t>({0,1,0,1}) &&
            ordered.offsets==std::vector<uint32_t>({4,0,0,4}) && ordered.streams[0].bind_offset==0 && ordered.streams[1].bind_offset==8,
            "legal shifted interleaved views group independently of attribute declaration order");

    std::vector<Source> capacity;
    for (uint64_t n = 0; n < 32; ++n) capacity.push_back({constant,n+10,0,0,0,4,0,"lane"});
    require(!direct_layout(capacity,32,8,2048).direct, "full public capacity may exceed physical stream count");
    const auto packed = compact_layout(capacity,32,8,2048);
    require(packed.streams.size() == 1 && packed.streams[0].stride == 128 && packed.offsets.back() == 124,
            "all 32 active inputs fit one packed physical stream");
    const auto sparse = bytes<uint32_t>({16777217,UINT32_MAX,16777217,7});
    Selection selected{0,4,5,sparse,4};
    const auto remapped = compact_indices(selected,1024,8);
    require(remapped.identities == std::vector<uint32_t>({16777217,UINT32_MAX,7}) &&
            remapped.indices == std::vector<uint32_t>({0,1,0,2}), "sparse uint32 IDs use stable unique rows and ordered duplicate indices");
    const auto packed_bytes = pack_stream(selected,capacity,packed.streams[0],remapped.identities,1024);
    require(packed_bytes.size() == 3*128, "ordinary vertex rows are unique and not flattened over instances");
    for (size_t n = 0; n < packed_bytes.size(); n += 4)
        require(std::memcmp(packed_bytes.data()+n,constant.data(),4) == 0, "all active constant fields retain exact bits");

    sources = {{interleaved,1,3,4,28,8,0,"vertex"}, {interleaved,1,3,12,28,12,2,"instance"}};
    auto layout = compact_layout(sources,32,8,2048);
    const auto indices = bytes<uint16_t>({2,0}); selected = {0,2,5,indices,2};
    const auto unique = compact_indices(selected,1024,8);
    require(pack_stream(selected,sources,layout.streams[0],unique.identities,1024) ==
            bytes<uint32_t>({30,31,10,11}), "selected vertex rows preserve interleaved data");
    require(pack_stream(selected,sources,layout.streams[1],unique.identities,1024) ==
            bytes<uint32_t>({1,2,3,1,2,3,4,5,6,4,5,6,7,8,9}), "divisor two packs original five instances, not ten vertex invocations");
    Selection affine{16777217,100,5};
    layout = compact_layout(std::span<const Source>(capacity.data(),1),32,8,2048);
    require(compact_vertex_capacity(affine,layout,400,4,true) == 100, "affine four-byte identity does not constrain draw count to one");
    require(compact_vertex_capacity({4,2,INT32_MAX},layout,8,4,true)==2,
            "ordinary native instance count is not flattened with selected vertices");
    require(pack_stream({1,2,1},std::span<const Source>(sources.data(),1),
        compact_layout(std::span<const Source>(sources.data(),1),32,8,2048).streams[0],{},1024)==bytes<uint32_t>({20,21,30,31}),
            "DrawArrays compact rows start at the original nonzero first");
    rejects([&]{compact_vertex_capacity(affine,layout,399,4,true);}, "combined vertex allocation limit remains explicit");
    rejects([&]{compact_vertex_capacity(affine,layout,400,3,true);}, "identity storage capability checked");
    selected = {0,4,1,sparse,4};
    require(compact_vertex_capacity(selected,layout,1024,4,true) == 1, "indexed storage limits unique identity rows");
    rejects([&]{compact_indices(selected,1024,1);}, "sparse unique table limit checked before oversized dense allocation");
    const auto partitioned = compact_layout(capacity,32,8,64);
    require(partitioned.streams.size() == 2 && partitioned.streams[0].stride == 64 &&
            partitioned.streams[1].stride == 64,
            "combined stride above grant uses legal field partitions");
    bad = sources; bad[0].offset = 10000;
    rejects([&]{validate_sources(selected,bad,UINT32_MAX);}, "attribute source range checked before derived allocation");

    const auto u8 = bytes<uint8_t>({255,1,7,99}); selected = {0,3,1,u8,1};
    require(widen_u8(selected,6) == bytes<uint16_t>({255,1,7}), "u8 widening converts selected prefix and preserves 255 as data");
    auto empty=selected;empty.instances=0;
    require(widen_u8(empty,0).empty() && topology_indices(empty,false,0).empty(),"zero-instance draws create no index conversion payload");
    rejects([&]{widen_u8(selected,5);}, "widened allocation checked before copy");
    require(topology_indices(selected,false,16) == bytes<uint32_t>({255,1,7,255}), "indexed line loop preserves closure and original IDs");
    require(topology_indices({5,4,2},true,24) == bytes<uint32_t>({5,6,7,5,7,8}), "fan expansion retains order and last provoking vertex");
    require(topology_indices({5,4,2},false,20) == bytes<uint32_t>({5,6,7,8,5}), "nonzero-first array loop retains original IDs");
    rejects([&]{topology_indices({5,4,2},true,23);}, "topology allocation grant checked");
    require(selection_key({4,2,1},8,9) == selection_key({4,2,7},8,9), "vertex selection cache is independent of instance count");
    const auto original_key=source_key(sources);
    auto revised=sources;revised[0].revision++;
    require(source_key(revised)!=original_key,"source DATA revision changes exact packed geometry identity");
    revised=sources;revised[1].divisor++;
    require(source_key(revised)!=original_key,"divisor edits invalidate the original instance stream identity");
    revised=sources;revised[0].identity++;
    require(source_key(revised)!=original_key,"constant/reallocation identity changes packed data dependency");
    const std::string huge_name(1024*1024,'x');revised=sources;revised[0].name=huge_name;
    require(source_key(revised)==original_key && original_key.size()<1024,
            "LINK-scoped geometry keys do not duplicate arbitrarily long shader identifiers");
}

void ordinary_field_partitioning() {
    using namespace vispy::inputs;
    const std::vector<uint32_t> widths{16,12,12,8,8,8};
    const auto exact = partition_layout(widths, {}, 6, 2, 32);
    require(exact.streams.size() == 2 && exact.streams[0].stride == 32 && exact.streams[1].stride == 32,
            "exact partition fits two bins where descending first-fit needs three");
    const auto unaligned = partition_layout(widths, {}, 6, 2, 33);
    require(unaligned.slots == exact.slots && unaligned.offsets == exact.offsets,
            "nonmultiple-of-four stride grants do not invent unaligned field offsets");
    require(partition_layout({}, {}, 0, 0, 0).streams.empty(), "empty inputs need no buffer or stride grant");
    rejects([&] { partition_layout(widths, {}, 5, 2, 32); }, "public attribute grant is enforced before partitioning");
    rejects([&] { partition_layout(widths, {}, 6, 1, 32); }, "one buffer cannot represent two complete field rows");
    rejects([&] { partition_layout(widths, {}, 6, 2, 31); }, "a truly insufficient stride and buffer grant rejects");
    rejects([&] { partition_layout(std::vector<uint32_t>{16}, {}, 1, 8, 15); }, "one attribute cannot be split between buffers");
    rejects([&] { partition_layout(std::vector<uint32_t>{20}, {}, 1, 8, 32); }, "unsupported attribute widths remain explicit");
    rejects([&] { partition_layout(widths, std::vector<uint8_t>{0}, 6, 2, 32); }, "step map must cover every field");
    rejects([&] { partition_layout(std::vector<uint32_t>{4}, std::vector<uint8_t>{2}, 1, 1, 32); }, "invalid step categories reject");

    // An independent subset dynamic program enumerates every legal bin, rather
    // than using the production sorted-width assignment search. Exhaust all
    // multisets of up to six fields and reduced aligned/nonaligned grants.
    size_t examined = 0;
    for (size_t a = 0; a <= 6; ++a) for (size_t b = 0; b + a <= 6; ++b)
    for (size_t c = 0; c + b + a <= 6; ++c) for (size_t d = 0; d + c + b + a <= 6; ++d) {
        std::vector<uint32_t> lanes;
        for (auto [count, width] : {std::pair{a,4u}, std::pair{b,8u}, std::pair{c,12u}, std::pair{d,16u}})
            lanes.insert(lanes.end(), count, width);
        const size_t full = (size_t(1) << lanes.size()) - 1;
        for (uint32_t words = 1; words <= 8; ++words) {
            std::vector<size_t> minimum(full + 1, lanes.size() + 1);
            minimum[0] = 0;
            for (size_t mask = 1; mask <= full; ++mask) {
                const size_t anchor = mask & (~mask + 1);
                for (size_t subset = mask; subset; subset = (subset - 1) & mask) {
                    if (!(subset & anchor)) continue;
                    uint32_t sum = 0;
                    for (size_t field = 0; field < lanes.size(); ++field)
                        if (subset & (size_t(1) << field)) sum += lanes[field];
                    if (sum <= 4 * words) minimum[mask] = std::min(minimum[mask], size_t(1) + minimum[mask ^ subset]);
                }
            }
            if (minimum[full] > lanes.size()) {
                rejects([&] { partition_layout(lanes, {}, 6, 6, 4 * words + 3); },
                        "no representation exists when an entire field exceeds the reduced grant");
            } else {
                const auto plan = partition_layout(lanes, {}, 6, static_cast<uint32_t>(minimum[full]), 4 * words + 3);
                require(plan.streams.size() == minimum[full], "production field packing matches independent exact minimum");
                std::vector<bool> seen(lanes.size());
                for (size_t slot = 0; slot < plan.streams.size(); ++slot) {
                    const auto& stream = plan.streams[slot];
                    uint32_t offset = 0;
                    for (size_t field : stream.fields) {
                        require(!seen[field] && plan.slots[field] == slot && plan.offsets[field] == offset,
                                "every original shader location occurs exactly once at its packed byte offset");
                        seen[field] = true; offset += lanes[field];
                    }
                    require(offset == stream.stride && stream.stride <= 4 * words,
                            "each whole field fits its physical stream with checked aligned stride");
                }
                require(std::all_of(seen.begin(), seen.end(), [](bool value) { return value; }),
                        "partition assignment does not drop fields");
                if (minimum[full]) rejects([&] {
                    partition_layout(lanes, {}, 6, static_cast<uint32_t>(minimum[full] - 1), 4 * words + 3);
                }, "one fewer than the independently minimal buffer count rejects");
            }
            ++examined;
        }
    }
    require(examined == 1680, "complete reduced-grant multiset matrix executes");

    const std::vector<uint32_t> mixed_widths{16,12,12,8,8,8,12,8,4};
    const std::vector<uint8_t> steps{0,0,0,0,0,0,1,1,1};
    const auto mixed = partition_layout(mixed_widths, steps, 9, 3, 32);
    require(mixed.streams.size() == 3 && !mixed.streams[0].instance && !mixed.streams[1].instance &&
            mixed.streams[2].instance && mixed.streams[2].stride == 24,
            "vertex and instance partitions share one buffer budget without sharing step modes");
    rejects([&] { partition_layout(mixed_widths, steps, 9, 2, 32); }, "joint physical buffer grant includes both step categories");
    std::vector<std::vector<uint8_t>> data;
    for (size_t field = 0; field < mixed_widths.size(); ++field) {
        std::vector<uint32_t> words;
        for (uint32_t row = 0; row < 5; ++row)
            for (uint32_t component = 0; component < mixed_widths[field] / 4; ++component)
                words.push_back(field == 0 && row == 1 && component == 0 ? 0x80000000u :
                    (row == 0 ? 0x7fc01234u : row == 1 ? 0x80000000u : 0xffffffffu) ^
                    (static_cast<uint32_t>(field) << 8) ^ component ^ (row << 16));
        std::vector<uint8_t> field_data(words.size() * 4);
        std::memcpy(field_data.data(), words.data(), field_data.size());
        data.push_back(std::move(field_data));
    }
    uint32_t negative_zero = 0;
    std::memcpy(&negative_zero, data.front().data() + mixed_widths.front(), sizeof(negative_zero));
    require(negative_zero == 0x80000000u, "partition byte fixture includes a literal negative-zero float bit pattern");
    std::vector<Source> sources;
    for (size_t field = 0; field < data.size(); ++field)
        sources.push_back({data[field], field + 1, 7, 0, mixed_widths[field], mixed_widths[field],
                           field < 6 ? 0u : field == 6 ? 2u : field == 7 ? 3u : 1u, "partition-field"});
    const auto source_layout = compact_layout(sources, 9, 3, 32);
    require(source_layout.slots == mixed.slots && source_layout.offsets == mixed.offsets,
            "width-only pipeline layout and actual source layout use identical physical assignments");
    const auto indices = bytes<uint32_t>({2,0,2});
    const Selection indexed{0,3,5,indices,4};
    const auto remapped = compact_indices(indexed, 1024, 256);
    require(remapped.identities == std::vector<uint32_t>({2,0}) &&
            remapped.indices == std::vector<uint32_t>({0,1,0}), "field partitioning does not reorder original indices");
    auto inspect = [&](const Selection& selection, std::span<const uint32_t> identities) {
        for (const auto& stream : source_layout.streams) {
            const auto packed = pack_stream(selection, sources, stream, identities, 1024);
            const size_t rows = stream.instance ? selection.instances : selection.index_bytes ? identities.size() : selection.count;
            require(packed.size() == rows * stream.stride, "each field partition owns only its selected rows");
            for (size_t row = 0; row < rows; ++row) for (size_t field : stream.fields) {
                const auto& source = sources[field];
                const uint64_t original = stream.instance ? row / source.divisor :
                    selection.index_bytes ? identities[row] : selection.first + row;
                require(std::memcmp(packed.data() + row * stream.stride + source_layout.offsets[field],
                    source.bytes.data() + original * source.stride, source.element_bytes) == 0,
                    "partition bytes preserve exact NaN/signed-zero/uint bits and original vertex/instance divisors");
            }
        }
    };
    inspect(indexed, remapped.identities);
    inspect(Selection{1,2,5}, {});
    const auto vertex_stamp = partition_source_key(source_layout, sources, false);
    const auto instance_stamp = partition_source_key(source_layout, sources, true);
    auto revised = sources; ++revised[0].revision;
    require(partition_source_key(source_layout, revised, false) != vertex_stamp &&
            partition_source_key(source_layout, revised, true) == instance_stamp,
            "whole-category stamps invalidate every vertex partition and preserve independent instance ownership");
    revised = sources; ++revised[7].divisor;
    require(partition_source_key(source_layout, revised, true) != instance_stamp,
            "instance divisor mutations change the complete partition dependency stamp");
    const auto one = compact_layout(sources, 9, 3, 128);
    require(partition_source_key(one, sources, false) == source_key(std::span<const Source>(sources.data(), 6)),
            "single-stream dependency stamps retain exact legacy cache keys");
    require(partition_source_key(one, sources, false) != vertex_stamp,
            "different partition representations cannot alias the same current owner");
    auto incomplete = source_layout; incomplete.streams.front().fields.pop_back();
    rejects([&] { partition_source_key(incomplete, sources, false); }, "incomplete partition maps cannot form cache stamps");
}

void ordinary_cache_ownership() {
    using namespace vispy::inputs;
    struct Record { std::vector<uint8_t> cpu; std::shared_ptr<Record> child; };
    std::unordered_map<std::string,std::shared_ptr<Record>> cache;
    auto cost = [](const auto& record) { return uint64_t(sizeof(Record)+record->cpu.capacity()+
        (record->child ? sizeof(Record)+record->child->cpu.capacity() : 0)); };
    int builds = 0;
    auto make = [&](size_t size) { ++builds; auto r=std::make_shared<Record>(); r->cpu.resize(size,7); return r; };
    auto [vertex,built] = cached_conversion(cache,"vertex:rev1",[&]{return make(8);},cost,3,1024);
    std::weak_ptr<Record> previous=vertex;
    auto [hit,cold] = cached_conversion(cache,"vertex:rev1",[&]{return make(8);},cost,3,1024);
    require(built && !cold && hit==vertex && builds==1,"resident lookup creates no CPU payload");
    auto instance=cached_conversion(cache,"instance:rev1",[&]{return make(8);},cost,3,1024).first;
    discard_category(cache,"vertex:");
    require(cache.size()==1 && cache.at("instance:rev1")==instance && !previous.expired(),
            "vertex invalidation preserves independent instance cache and pending old vertex owner");
    vertex.reset(); hit.reset(); require(previous.expired(),"evicted revision releases after snapshot ownership ends");
    auto [oversized,admitted] = cached_conversion(cache,"selection:large",[&]{return make(2048);},cost,3,1024);
    require(admitted && oversized->cpu.size()==2048 && cache.size()==1,
            "oversized legal result is usable but never admitted");
    auto selection=cached_conversion(cache,"selection:small",[&]{auto r=make(8);r->child=make(8);return r;},cost,3,1024).first;
    std::weak_ptr<Record> child=selection->child;
    const auto budget=sizeof(decltype(cache)::value_type)+cache_entry_bookkeeping+std::string("index:new").capacity()+cost(instance);
    auto fresh=cached_conversion(cache,"index:new",[&]{return make(8);},cost,3,budget).first;
    require(cache.size()==1 && cache.contains("index:new") && !child.expired(),
            "one budget evicts selection plus owned index child while pending owners stay usable");
    selection.reset(); require(child.expired(),"selection child has no parent cycle");
    const auto old_size=cache.size();
    rejects([&]{cached_conversion(cache,"vertex:bad",[]()->std::shared_ptr<Record>{throw std::runtime_error("failed build");},cost,3,1024);},
            "failed builder propagates contextual error");
    require(cache.size()==old_size && cache.at("index:new")==fresh,"failed build leaves cache owners intact");
    auto [overflow,was_built]=cached_conversion(cache,"selection:overflow",[&]{return make(1);},
        [](const auto&){return UINT64_MAX;},3,1024);
    require(was_built && overflow && cache.size()==old_size && cache.at("index:new")==fresh,
            "near-uint64 cost saturates and skips admission without evicting resident owners");
}

void ordinary_current_ownership() {
    using namespace vispy::inputs;
    struct Record {
        std::vector<uint8_t> cpu;
        std::shared_ptr<Record> child;
        uint64_t identity = 0;
        bool gpu = false;
    };
    using Ptr = std::shared_ptr<Record>;
    using Map = std::unordered_map<std::string, Ptr>;
    Map history;
    CurrentConversions<Ptr> current;
    uint64_t builds = 0;
    auto make = [&](size_t size) {
        auto record = std::make_shared<Record>();
        record->identity = ++builds;
        record->cpu.resize(size, 17);
        return record;
    };
    auto cost = [](const auto& record) {
        return uint64_t(sizeof(Record) + record->cpu.capacity() +
            (record->child ? sizeof(Record) + record->child->cpu.capacity() : 0));
    };
    auto convert = [&](CurrentCategory category, const std::string& key, size_t bytes = 2048) {
        return current_cached_conversion(current, category, history, key,
            [&] { return make(bytes); }, cost, 3, 1024);
    };
    auto [selected, cold] = current_cached_conversion(current, CurrentCategory::Selection,
        history, "selection:index-rev1", [&] { auto r = make(2048); r->child = make(2048); return r; }, cost, 3, 1024);
    require(cold && history.empty() && current.size() == 1,
            "oversized selection stays current without historical admission");
    const uint64_t child_identity = selected->child->identity;
    std::weak_ptr<Record> selected_weak = selected, child_weak = selected->child;
    struct FakeTicket { Ptr selection, indices; };
    auto ticket = std::make_unique<FakeTicket>(FakeTicket{selected, selected->child});
    selected.reset(); ticket.reset();
    require(!selected_weak.expired() && !child_weak.expired(),
            "current owner preserves oversized parent and converted indices after Ticket retirement");
    const auto builds_before = builds;
    auto [resident, rebuilt] = current_cached_conversion(current, CurrentCategory::Selection,
        history, "selection:index-rev1", [&]() -> Ptr { throw std::runtime_error("warm conversion must not build"); }, cost, 3, 1024);
    require(!rebuilt && resident == selected_weak.lock() && resident->child->identity == child_identity && builds == builds_before,
            "warm oversized conversion returns exact parent/child allocation identities without a rebuild");
    auto vertex = convert(CurrentCategory::Vertex, "vertex:child-id:" + std::to_string(child_identity)).first;
    vertex->gpu = true;
    resident->gpu = resident->child->gpu = true;
    // Model the renderer's device-loss visit: only GPU state is invalidated;
    // all current CPU records and the exact converted-index identity survive.
    current.for_each([&](auto, const auto&, const auto& record) {
        record->gpu = false; if (record->child) record->child->gpu = false;
    });
    const auto loss_builds = builds;
    auto [loss_hit, loss_cold] = convert(CurrentCategory::Vertex, "vertex:child-id:" + std::to_string(child_identity));
    require(!loss_cold && loss_hit == vertex && builds == loss_builds && !vertex->gpu && !resident->child->gpu,
            "loss preserves CPU conversion and exact child-dependent keys while clearing GPU state");
    vertex->gpu = true;  // One fake re-upload is enough for subsequent warm reuse.
    require(convert(CurrentCategory::Vertex, "vertex:child-id:" + std::to_string(child_identity)).first->gpu,
            "re-uploaded resident owner is reused instead of recreated");
    auto small = cached_conversion(history, "bounds:small", [&] { return make(4); }, cost, 3, 1024).first;
    const auto history_builds = builds;
    auto [adopted, adoption_cold] = convert(CurrentCategory::Bounds, "bounds:small");
    require(!adoption_cold && adopted == small && builds == history_builds,
            "a historical hit is adopted as current without conversion");
    history.clear(); small.reset(); adopted.reset();
    require(bool(current.find(CurrentCategory::Bounds, "bounds:small")),
            "current owner survives independent historical eviction");
    auto instance = convert(CurrentCategory::Instance, "instance:source-rev1").first;
    current.clear(CurrentCategory::Vertex);
    require(current.find(CurrentCategory::Instance, "instance:source-rev1") == instance &&
            current.find(CurrentCategory::Selection, "selection:index-rev1") == resident,
            "vertex-source invalidation preserves independent instance and index-selection owners");
    vertex.reset(); loss_hit.reset();
    for (auto category : {CurrentCategory::IndexWiden, CurrentCategory::Topology, CurrentCategory::Bounds,
                          CurrentCategory::Selection, CurrentCategory::Vertex}) current.clear(category);
    require(current.size() == 1 && current.find(CurrentCategory::Instance, "instance:source-rev1") == instance,
            "index-source invalidation drops every index-dependent current owner while retaining instance stream");
    resident.reset(); require(selected_weak.expired() && child_weak.expired(),
            "retired selection child releases after index invalidation with no source/parent cycle");
    auto source = make(16); std::weak_ptr<Record> source_weak = source;
    auto copied = current_cached_conversion(current, CurrentCategory::Vertex, history, "vertex:copied-source",
        [&] { auto r = make(2048); std::copy(source->cpu.begin(), source->cpu.end(), r->cpu.begin()); return r; }, cost, 3, 1024).first;
    source.reset(); require(source_weak.expired(), "current conversion owns child bytes without retaining source parents");
    std::weak_ptr<Record> old_vertex = copied;
    auto pending = std::make_unique<FakeTicket>(FakeTicket{copied, {}});
    copied.reset();
    auto newer = convert(CurrentCategory::Vertex, "vertex:new-revision").first;
    require(!old_vertex.expired(), "replacement leaves pending old revision alive");
    pending.reset(); require(old_vertex.expired(), "old oversized revision releases when its last Ticket retires");
    auto prior = newer;
    const auto prior_history = history.size();
    rejects([&] { current_cached_conversion(current, CurrentCategory::Vertex, history, "vertex:failed",
        []() -> Ptr { throw std::runtime_error("conversion failed"); }, cost, 3, 1024); }, "failed current build propagates");
    require(current.find(CurrentCategory::Vertex, "vertex:new-revision") == prior && history.size() == prior_history,
            "build-before-replace preserves current and historical owners on failure");
    for (size_t round = 0; round < 40; ++round) {
        for (size_t n = 0; n < CurrentConversions<Ptr>::category_count; ++n)
            convert(static_cast<CurrentCategory>(n), "current:" + std::to_string(n) + ':' + std::to_string(round));
        require(current.size() == CurrentConversions<Ptr>::category_count && history.empty(),
                "oversized category churn is bounded to the fixed current category count");
    }
    prior.reset(); newer.reset(); instance.reset();
    auto final_selection = current_cached_conversion(current, CurrentCategory::Selection,
        history, "selection:pending-delete", [&] { auto r = make(2048); r->child = make(2048); return r; }, cost, 3, 1024).first;
    std::weak_ptr<Record> pending_parent = final_selection, pending_child = final_selection->child;
    ticket = std::make_unique<FakeTicket>(FakeTicket{final_selection, final_selection->child});
    final_selection.reset();
    std::vector<std::weak_ptr<Record>> final_owners;
    current.for_each([&](auto, const auto&, const auto& record) { final_owners.push_back(record); });
    current.clear(); history.clear();
    require(current.size() == 0 && !pending_parent.expired() && !pending_child.expired(),
            "Program DELETE immediately releases current owners while pending work retains selected parent and child");
    ticket.reset();
    require(current.size() == 0 && std::all_of(final_owners.begin(), final_owners.end(), [](const auto& weak) { return weak.expired(); }),
            "LINK/Program deletion/shutdown release all current owners after pending work ends");
    require(pending_child.expired(), "final Ticket retirement releases deleted Program's last child without a cycle");
}

void ordinary_partition_ownership() {
    using namespace vispy::inputs;
    struct Record {
        std::vector<uint8_t> cpu;
        std::vector<std::shared_ptr<Record>> children;
        bool gpu = false;
    };
    using Ptr = std::shared_ptr<Record>;
    using Map = std::unordered_map<std::string, Ptr>;
    auto graph = [](const Ptr& root, std::unordered_set<const void*>& visited) {
        auto visit = [&](auto&& self, const Ptr& item) -> uint64_t {
            if (!item || !visited.insert(item.get()).second) return 0;
            uint64_t bytes = bounded_cost_add(sizeof(Record), item->cpu.capacity());
            bytes = bounded_cost_add(bytes, item->children.capacity() * sizeof(Ptr));
            for (const auto& child : item->children) bytes = bounded_cost_add(bytes, self(self, child));
            return bytes;
        };
        return visit(visit, root);
    };
    auto cost = [&](const Ptr& root) { std::unordered_set<const void*> seen; return graph(root, seen); };
    CurrentConversions<Ptr> current;
    OversizedConversions<Ptr> working(0, 0);
    Map history;
    size_t conversions = 0;
    auto build = [&](size_t streams, size_t fail_at = SIZE_MAX) {
        auto root = std::make_shared<Record>();
        for (size_t n = 0; n < streams; ++n) {
            if (n == fail_at) throw std::runtime_error("partition child conversion failed");
            auto child = std::make_shared<Record>();
            child->cpu.assign(64, static_cast<uint8_t>(++conversions));
            root->children.push_back(std::move(child));
        }
        return root;
    };
    auto convert = [&](CurrentCategory category, const std::string& key, size_t streams) {
        return working_cached_conversion(current, working, category, history, key,
            [&] { return build(streams); }, cost, graph, 0, 0);
    };
    auto [vertex, cold] = convert(CurrentCategory::Vertex, "vertex:partition-A", 2);
    auto instance = convert(CurrentCategory::Instance, "instance:partition-A", 1).first;
    require(cold && current.size() == 2 && history.empty() && working.size() == 0 && conversions == 3,
            "all physical partitions share one current owner per category independently of history admission");
    auto children = vertex->children;
    auto [resident, rebuilt] = working_cached_conversion(current, working, CurrentCategory::Vertex, history,
        "vertex:partition-A", []() -> Ptr { throw std::runtime_error("warm composite must not convert"); },
        cost, graph, 0, 0);
    require(!rebuilt && resident == vertex && resident->children == children && conversions == 3,
            "warm lookup retains every exact partition child without repeated slot replacement or conversion");
    std::vector<std::weak_ptr<Record>> partial_children;
    rejects([&] {
        working_cached_conversion(current, working, CurrentCategory::Vertex, history, "vertex:failed-child",
            [&]() -> Ptr {
                auto root = std::make_shared<Record>();
                auto child = std::make_shared<Record>();
                root->children.push_back(child); partial_children.push_back(child);
                throw std::runtime_error("second partition failed");
            }, cost, graph, 0, 0);
    }, "a later child failure aborts the composite before publication");
    require(current.find(CurrentCategory::Vertex, "vertex:partition-A") == vertex &&
            current.find(CurrentCategory::Instance, "instance:partition-A") == instance &&
            history.empty() && working.size() == 0 && partial_children.front().expired(),
            "failed composite releases temporary children and preserves every old current category");
    auto fail_publication = [](const auto& owners, auto category, const auto& key, auto record)
        -> decltype(owners.prepare(category, key, record)) { throw std::bad_alloc(); };
    bool failed = false;
    try {
        working_cached_conversion(current, working, CurrentCategory::Vertex, history, "vertex:failed-key",
            [&] { return build(2); }, cost, graph, 0, 0, fail_publication);
    } catch (const std::bad_alloc&) { failed = true; }
    require(failed && current.find(CurrentCategory::Vertex, "vertex:partition-A") == vertex && history.empty(),
            "composite key publication failure leaves the old root and all partitions resident");
    vertex->gpu = instance->gpu = true;
    for (auto& child : vertex->children) child->gpu = true;
    for (auto& child : instance->children) child->gpu = true;
    std::unordered_set<const void*> invalidated;
    auto invalidate = [&](auto&& self, const Ptr& root) -> void {
        if (!root || !invalidated.insert(root.get()).second) return;
        root->gpu = false;
        for (const auto& child : root->children) self(self, child);
    };
    current.for_each([&](auto, const auto&, const auto& root) { invalidate(invalidate, root); });
    require(invalidated.size() == 5 && !vertex->children[0]->gpu && !vertex->children[1]->gpu &&
            !instance->children[0]->gpu,
            "loss traverses both composite roots and every physical stream exactly once");
    const auto before_recovery = conversions;
    require(!convert(CurrentCategory::Vertex, "vertex:partition-A", 2).second && conversions == before_recovery,
            "recovery retains all CPU partition identities without reconversion");
    std::weak_ptr<Record> old_root = vertex;
    std::vector<Ptr> pending = vertex->children;
    vertex.reset(); resident.reset();
    const auto replacement = convert(CurrentCategory::Vertex, "vertex:partition-B", 2).first;
    require(old_root.expired() && !pending[0]->cpu.empty() && !pending[1]->cpu.empty(),
            "snapshot children outlive a replaced composite root without retaining source records or a parent cycle");
    current.clear(CurrentCategory::Vertex);
    require(current.size() == 1 && current.find(CurrentCategory::Instance, "instance:partition-A") == instance,
            "vertex mutation or deletion preserves the independent instance composite owner");
    std::weak_ptr<Record> pending_child = pending.front();
    pending.clear();
    require(!pending_child.expired() && children.front() == pending_child.lock(),
            "selected child lifetime follows actual shared ownership after logical current release");
    children.clear();
    require(pending_child.expired(), "old partition releases after its last actual snapshot owner retires");
}

void ordinary_oversized_working_set() {
    using namespace vispy::inputs;
    struct Record {
        std::vector<uint8_t> cpu;
        std::vector<std::shared_ptr<Record>> children;
        uint64_t identity = 0;
        bool gpu = false;
    };
    using Ptr = std::shared_ptr<Record>;
    auto graph = [](const Ptr& root, std::unordered_set<const void*>& visited) {
        std::function<uint64_t(const Ptr&)> visit = [&](const Ptr& item) {
            if (!item || !visited.insert(item.get()).second) return uint64_t(0);
            uint64_t bytes = bounded_cost_add(sizeof(Record) + 2 * sizeof(void*), item->cpu.capacity());
            bytes = bounded_cost_add(bytes, item->children.capacity() * sizeof(Ptr));
            for (const auto& child : item->children) bytes = bounded_cost_add(bytes, visit(child));
            return bytes;
        };
        return visit(root);
    };
    auto cost = [&](const Ptr& root) { std::unordered_set<const void*> visited; return graph(root, visited); };
    uint64_t builds = 0;
    auto make = [&](size_t bytes) {
        auto item = std::make_shared<Record>(); item->cpu.resize(bytes); item->identity = ++builds; return item;
    };
    CurrentConversions<Ptr> current;
    OversizedConversions<Ptr> working(8, 20000);
    std::unordered_map<std::string, Ptr> history;
    auto convert = [&](CurrentCategory category, const std::string& key) {
        return working_cached_conversion(current, working, category, history, key,
            [&] { auto item = make(1600); item->children.push_back(make(1800)); return item; }, cost, graph, 3, 1024);
    };
    auto a = convert(CurrentCategory::Selection, "selection:rev1:first0").first;
    auto b = convert(CurrentCategory::Selection, "selection:rev1:first6").first;
    const auto a_id = a->identity, a_child_id = a->children.front()->identity;
    a->gpu = a->children.front()->gpu = true;
    std::weak_ptr<Record> a_weak = a, child_weak = a->children.front();
    struct Ticket { Ptr parent, child; };
    auto ticket = std::make_unique<Ticket>(Ticket{a, a->children.front()});
    a.reset(); ticket.reset();
    require(!a_weak.expired() && !child_weak.expired() && history.empty() && working.size() == 2,
            "two oversized selections remain owned after current replacement and Ticket retirement");
    const auto prior_builds = builds;
    auto [again, cold] = working_cached_conversion(current, working, CurrentCategory::Selection, history,
        "selection:rev1:first0", []() -> Ptr { throw std::runtime_error("A/B/A must hit retained selection"); }, cost, graph, 3, 1024);
    require(!cold && builds == prior_builds && again->identity == a_id && again->children.front()->identity == a_child_id &&
            again->gpu && again->children.front()->gpu,
            "within-budget A/B/A reuses exact CPU child identities and uploaded resources without reconversion");
    auto vertex = convert(CurrentCategory::Vertex, "same:exact-key").first;
    auto instance = convert(CurrentCategory::Instance, "same:exact-key").first;
    require(vertex != instance && working.find(CurrentCategory::Vertex, "same:exact-key") == vertex &&
            working.find(CurrentCategory::Instance, "same:exact-key") == instance && !working.find(CurrentCategory::Vertex, "same:other-key"),
            "oversized history distinguishes category and complete identity key");
    const auto old_size = working.size(), old_bytes = working.storage_bytes(graph), old_evictions = working.evictions();
    rejects([&] { working_cached_conversion(current, working, CurrentCategory::Selection, history, "selection:failed",
        []() -> Ptr { throw std::runtime_error("failed oversized builder"); }, cost, graph, 3, 1024); }, "builder failure propagates");
    require(current.find(CurrentCategory::Selection, "selection:rev1:first0") == again &&
            working.size() == old_size && working.storage_bytes(graph) == old_bytes && working.evictions() == old_evictions,
            "failed builder preserves current and both histories before publication");
    rejects([&] { working.admit(CurrentCategory::Bounds, "footprint:failed", make(1600),
        [](const Ptr&, auto&) -> uint64_t { throw std::runtime_error("failed footprint"); }); }, "footprint failure propagates");
    require(working.size() == old_size && working.storage_bytes(graph) == old_bytes && working.evictions() == old_evictions,
            "failed admission footprint does not evict existing owners");
    {
        CurrentConversions<Ptr> staged_current;
        OversizedConversions<Ptr> staged_working(1, 5000);
        std::unordered_map<std::string, Ptr> staged_history;
        auto old = working_cached_conversion(staged_current, staged_working, CurrentCategory::Vertex,
            staged_history, "vertex:old", [&] { return make(1600); }, cost, graph, 3, 1024).first;
        std::weak_ptr<Record> retained = old;
        old.reset();
        const auto bytes_before = staged_working.storage_bytes(graph);
        auto fail_key_allocation = [](const auto& current, auto category, const auto& key, auto record)
                -> decltype(current.prepare(category, key, record)) { throw std::bad_alloc(); };
        bool allocation_failed = false;
        try {
            working_cached_conversion(staged_current, staged_working, CurrentCategory::Vertex,
                staged_history, "vertex:would-evict", [&] { return make(1700); }, cost, graph,
                3, 1024, fail_key_allocation);
        } catch (const std::bad_alloc&) { allocation_failed = true; }
        require(allocation_failed && staged_history.empty() && staged_working.size() == 1 &&
                staged_working.storage_bytes(graph) == bytes_before && staged_working.evictions() == 0 &&
                staged_current.find(CurrentCategory::Vertex, "vertex:old") == retained.lock() &&
                staged_working.peek(CurrentCategory::Vertex, "vertex:old") == retained.lock(),
                "current-key allocation failure is staged before capacity eviction or owner publication");
        auto replacement = working_cached_conversion(staged_current, staged_working, CurrentCategory::Vertex,
            staged_history, "vertex:new", [&] { return make(1700); }, cost, graph, 3, 1024).first;
        require(staged_working.evictions() == 1 && retained.expired() &&
                staged_current.find(CurrentCategory::Vertex, "vertex:new") == replacement,
                "successful staged publication evicts once and adopts the same new owner");
    }
    auto small = working_cached_conversion(current, working, CurrentCategory::Bounds, history, "bounds:small",
        [&] { return make(4); }, cost, graph, 3, 1024).first;
    require(history.size() == 1 && working.size() == old_size && history.at("bounds:small") == small,
            "ordinary-sized payload stays in unchanged historical cache");
    const auto explicit_evictions = working.evictions();
    current.clear(CurrentCategory::Vertex); working.clear(CurrentCategory::Vertex); discard_category(history, "vertex:");
    require(working.find(CurrentCategory::Instance, "same:exact-key") == instance &&
            current.find(CurrentCategory::Instance, "same:exact-key") == instance &&
            working.find(CurrentCategory::Selection, "selection:rev1:first0") == again && working.evictions() == explicit_evictions,
            "vertex revision invalidation preserves independent instance/selection owners and is not a capacity eviction");
    // Actual loss walks all owner views through one identity set. Overlap and
    // shared children must not reset/recreate records more than once.
    std::unordered_set<const void*> invalidated;
    size_t resets = 0;
    std::function<void(const Ptr&)> invalidate = [&](const Ptr& item) {
        if (!item || !invalidated.insert(item.get()).second) return;
        item->gpu = false; ++resets; for (const auto& child : item->children) invalidate(child);
    };
    current.for_each([&](auto, const auto&, const auto& item) { invalidate(item); });
    working.for_each([&](auto, const auto&, const auto& item) { invalidate(item); });
    for (const auto& [key, item] : history) invalidate(item);
    require(resets == invalidated.size() && !again->gpu && !again->children.front()->gpu,
            "loss reset deduplicates overlapping working/current/history and owned children");
    const auto loss_builds = builds;
    require(!convert(CurrentCategory::Selection, "selection:rev1:first6").second &&
            !convert(CurrentCategory::Selection, "selection:rev1:first0").second && builds == loss_builds,
            "loss keeps both alternate CPU records and exact child-dependent keys");
    again->gpu = again->children.front()->gpu = true;
    require(convert(CurrentCategory::Selection, "selection:rev1:first0").first->gpu,
            "one re-upload serves following warm draws");
    ticket = std::make_unique<Ticket>(Ticket{again, again->children.front()});
    const auto invalidation_evictions = working.evictions();
    for (auto category : {CurrentCategory::IndexWiden, CurrentCategory::Topology, CurrentCategory::Bounds,
                          CurrentCategory::Selection, CurrentCategory::Vertex}) {
        current.clear(category); working.clear(category);
    }
    require(working.find(CurrentCategory::Instance, "same:exact-key") == instance &&
            current.find(CurrentCategory::Instance, "same:exact-key") == instance &&
            working.evictions() == invalidation_evictions && !a_weak.expired(),
            "index revision invalidation drops dependent categories while retaining instance and pending old children");
    again.reset(); b.reset(); vertex.reset(); instance.reset(); small.reset();
    current.clear(); history.clear(); working.clear();
    require(current.size() == 0 && history.empty() && working.size() == 0 && !a_weak.expired() && !child_weak.expired(),
            "Program DELETE drops all three cache owner views while a pending Ticket retains old immutable children");
    ticket.reset();
    require(a_weak.expired() && child_weak.expired(), "deleted oversized parent and child release after final Ticket without a cycle");

    // Shared child capacity is charged once, but each occupied list entry,
    // copied key and each parent's child-edge storage are charged separately.
    auto shared = make(1800), parent_a = make(64), parent_b = make(64);
    parent_a->children.push_back(shared); parent_b->children.push_back(shared);
    OversizedConversions<Ptr> shared_cache;
    require(shared_cache.admit(CurrentCategory::Vertex, "shared:A", parent_a, graph) &&
            shared_cache.admit(CurrentCategory::Instance, "shared:B", parent_b, graph), "shared parents admitted");
    std::unordered_set<const void*> visited;
    const auto dedup = graph(parent_a, visited) + graph(parent_b, visited);
    const auto expected_cost = dedup + OversizedConversions<Ptr>::entry_bytes("shared:A") + OversizedConversions<Ptr>::entry_bytes("shared:B");
    require(shared_cache.storage_bytes(graph) == expected_cost && dedup < cost(parent_a) + cost(parent_b),
            "shared subgraphs charged once plus exact occupied-entry/key bookkeeping");
    OversizedConversions<Ptr> boundary(8, expected_cost);
    require(boundary.admit(CurrentCategory::Vertex, "shared:A", parent_a, graph) &&
            boundary.admit(CurrentCategory::Instance, "shared:B", parent_b, graph) && boundary.size() == 2,
            "exact inclusive oversized byte boundary admits both shared records");
    OversizedConversions<Ptr> below(8, expected_cost - 1);
    below.admit(CurrentCategory::Vertex, "shared:A", parent_a, graph);
    below.admit(CurrentCategory::Instance, "shared:B", parent_b, graph);
    require(below.size() == 1 && below.evictions() == 1 && below.storage_bytes(graph) <= below.byte_limit(),
            "one-byte over shared budget evicts an old owner and remains bounded");
    OversizedConversions<Ptr> too_small(8, cost(parent_a));
    require(!too_small.admit(CurrentCategory::Vertex, "shared:A", parent_a, graph) && too_small.size() == 0,
            "key and entry overhead can make payload-only allowance insufficient");
    require(!shared_cache.admit(CurrentCategory::Vertex, "overflow", parent_a,
        [](const Ptr&, auto&) { return UINT64_MAX; }) && shared_cache.size() == 2 && shared_cache.evictions() == 0,
            "near-uint64 cost saturates and skips admission without disturbing working set");
    std::string huge_key(8192, 'x');
    OversizedConversions<Ptr> key_budget(8, 4096);
    require(!key_budget.admit(CurrentCategory::Vertex, huge_key, make(1), graph),
            "retained full key capacity counts toward oversized byte budget");

    OversizedConversions<Ptr> entries(99, UINT64_MAX);
    require(entries.entry_limit() == 8 && entries.byte_limit() == 256ull*1024*1024,
            "public oversized policy cannot exceed eight records or256MiB");
    std::vector<std::weak_ptr<Record>> old;
    for (size_t n = 0; n < 10; ++n) {
        auto item = make(1); old.push_back(item);
        require(entries.admit(static_cast<CurrentCategory>(n % 6), "entry:" + std::to_string(n), item, graph), "entry admitted");
        require(entries.size() <= 8 && entries.storage_bytes(graph) <= entries.byte_limit(), "entry and shared byte bounds hold during churn");
    }
    require(entries.size() == 8 && entries.evictions() == 2 && old[0].expired() && old[1].expired(),
            "ninth/tenth entries release least-recently-used old owners");
    require(bool(entries.find(CurrentCategory::Bounds, "entry:2")), "working hit exists");
    entries.admit(CurrentCategory::Vertex, "entry:10", make(1), graph);
    require(!old[2].expired() && old[3].expired() && entries.evictions() == 3,
            "actual working-set hit refreshes recency before capacity eviction");
    entries.clear();
    require(std::all_of(old.begin(), old.end(), [](const auto& weak) { return weak.expired(); }),
            "LINK/deletion/shutdown clear every oversized owner");
}

void ordinary_identity_shaders() {
    const std::string vertex="attribute vec2 a_position;varying float v_id;void main(){gl_Position=vec4(a_position,0,1);v_id=float(gl_VertexID+gl_InstanceID);}";
    const std::string fragment="varying float v_id;void main(){gl_FragColor=vec4(v_id);}";
    std::string previous;
    for (auto policy : {VertexIdentityPolicy::Native,VertexIdentityPolicy::Affine,VertexIdentityPolicy::Indexed}) {
        NormalizeOptions options;options.vertex_identity=policy;
        auto normalized=normalize_program(vertex,fragment,options);check(normalized);
        const auto artifact=vispy::shader::build_portable_shader(vertex,fragment,options,"ordinary-id-contract");
        require(artifact->ok,artifact->error);
        require(artifact->identity!=previous,"each native/affine/indexed policy has its own exact portable identity");
        previous=artifact->identity;
        require(artifact->attributes.size()==1 && artifact->attributes[0].name=="a_position",
                "ordinary identity storage adds no public input");
        require((artifact->vertex_identity_binding!=0)==(policy!=VertexIdentityPolicy::Native),
                "only live lowered identities request storage");
#ifdef VISPY_TEST_TINT_READER
        for (const auto* words : {&artifact->spv_vert,&artifact->spv_frag}) {
            auto ir=tint::spirv::reader::ReadIR(*words);
            require(ir==tint::Success,ir==tint::Success?"":ir.Failure().reason);
        }
#endif
    }
    std::string declarations,contribution;
    for (int n=0;n<32;++n) {
        declarations+="attribute float a_"+std::to_string(n)+";";
        if (n>=2) contribution+=(n==2?"":"+")+std::string("a_")+std::to_string(n);
    }
    for (auto policy:{VertexIdentityPolicy::Affine,VertexIdentityPolicy::Indexed}) {
        NormalizeOptions options;options.vertex_identity=policy;
        const auto full=vispy::shader::build_portable_shader(declarations+
            "varying float v_id;void main(){gl_Position=vec4(a_0,a_1,float(gl_VertexID)*.01,1);v_id="+
            contribution+"+float(gl_InstanceID);}",fragment,options,"ordinary-capacity-contract");
        require(full->ok && full->attributes.size()==32 && full->vertex_identity_binding,
                full->error+"all declared public inputs remain active with storage identity");
        for (size_t n=0;n<32;++n) require(full->attributes[n].location==n,"full-capacity VS locations remain compact");
#ifdef VISPY_TEST_TINT_READER
        for (const auto* words:{&full->spv_vert,&full->spv_frag}) {
            auto ir=tint::spirv::reader::ReadIR(*words);
            require(ir==tint::Success,ir==tint::Success?"":ir.Failure().reason);
        }
#endif
    }
    NormalizeOptions options;options.vertex_identity=VertexIdentityPolicy::Affine;
    const auto unused=vispy::shader::build_portable_shader("attribute vec2 a_position;void main(){gl_Position=vec4(a_position,0,1);}",
        "void main(){gl_FragColor=vec4(1);}",options,"ordinary-id-contract");
    require(unused->ok && !unused->vertex_identity_binding,"unused private storage cannot consume a binding grant");
    auto rejected=normalize_program("uniform float vispy_vertex_identity;void main(){gl_Position=vec4(vispy_vertex_identity);}",fragment,options);
    require(rejected.error.find("reserved")!=std::string::npos,"ordinary reserved identity collision is contextual");
    options.point_sprites=true;
    rejected=normalize_program(vertex,fragment,options);
    require(!rejected.error.empty(),"point and ordinary identity policies cannot be combined");
}
}  // namespace

int main(int argc, char** argv) {
    try {
        point_lowering(); instanced_marker_hooks(); identity_and_gather(); conversion_cache(); inactive_point_inputs(); packed_inputs(); capacity_shader_interface(); snapshot_artifact_selection(); live_resource_descriptors();
        ordinary_input_routes(); ordinary_field_partitioning(); ordinary_cache_ownership(); ordinary_current_ownership(); ordinary_partition_ownership(); ordinary_oversized_working_set(); ordinary_identity_shaders();
        if (argc > 1) for (const auto& file : std::filesystem::directory_iterator(argv[1])) {
            if (file.path().extension() != ".vert") continue;
            auto fragment = file.path(); fragment.replace_extension(".frag");
            const std::string frag = read(fragment);
            const std::string vert = read(file.path());
            NormalizeOptions options;
            options.base_level_sampling = true;
            options.point_sprites = (argc > 2 && std::string(argv[2]) == "--points") ||
                                   frag.find("gl_PointCoord") != std::string::npos;
            if (argc > 2 && std::string(argv[2]) == "--affine") options.vertex_identity=VertexIdentityPolicy::Affine;
            if (argc > 2 && std::string(argv[2]) == "--indexed") options.vertex_identity=VertexIdentityPolicy::Indexed;
            auto normalized = normalize_program(vert, frag, options);
            check(normalized);
            if (argc > 2) {
                auto portable = vispy::shader::build_portable_shader(vert,frag,options,"captured-source-contract");
                require(portable->ok,portable->error);
#ifdef VISPY_TEST_TINT_READER
                for(const auto* words:{&portable->spv_vert,&portable->spv_frag}) {
                    auto ir=tint::spirv::reader::ReadIR(*words);
                    require(ir==tint::Success,ir==tint::Success?"":ir.Failure().reason);
                }
#endif
                if (std::string(argv[2]) == "--resources") {
                    require(vispy::shader::resource_limit_error(portable->samplers,16,48).empty(),
                            "captured actual volume must fit 16 active sampler slots");
                    require(portable->samplers.size() == 16, "captured actual volume has exactly sixteen live samplers");
                    for (const auto& sampler : portable->samplers)
                        require(sampler.name != "dummy1" && sampler.texture_stage_mask == 2 && sampler.sampler_stage_mask == 2,
                                "actual volume declaration-only dummy1 omitted; live volume resources fragment-only");
                }
                if (file.path().stem() == "large_uint32_constant_geometry")
                    for (const auto& attribute : portable->attributes)
                        require(attribute.name != "a_count", "actual large-ID count input has no native vertex fetch");
                std::cout << "active inputs=" << portable->attributes.size() << " samplers=" << portable->samplers.size()
                          << " UBO-stage-mask=" << portable->uniform_stage_mask << '\n';
            }
            std::cout << "validated marker " << file.path().stem().string() << '\n';
        }
        std::cout << "point and ordinary input grouping/identity/instancing/cache contracts, active resources and retained shader hooks passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
