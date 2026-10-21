#include "shader/artifact.hpp"
#include <SPIRV/spirv.hpp11>

#include <iostream>
#include <stdexcept>
#include <unordered_map>

namespace {
size_t checks = 0;
void require(bool value, const std::string& message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
struct Definition { spv::Op op; uint32_t type; std::vector<uint32_t> args; };
struct Module {
    std::unordered_map<uint32_t,Definition> definitions;
    std::unordered_map<uint32_t,std::string> names;
    std::unordered_map<uint32_t,uint32_t> bindings, builtins, stores, offsets, strides;
    explicit Module(const std::vector<uint32_t>& words) {
        require(words.size() >= 5 && words[0] == 0x07230203u, "real valid SPIR-V header required");
        for (size_t p = 5; p < words.size();) {
            const size_t count = words[p] >> 16;
            require(count && count <= words.size()-p, "whole validated SPIR-V instruction required");
            const auto op = static_cast<spv::Op>(words[p]&0xffffu);
            const auto* a = words.data()+p+1;
            if (op == spv::Op::OpName) names[a[0]] = reinterpret_cast<const char*>(a+1);
            else if (op == spv::Op::OpDecorate && count == 4) {
                if (a[1] == uint32_t(spv::Decoration::Binding)) bindings[a[0]] = a[2];
                if (a[1] == uint32_t(spv::Decoration::BuiltIn)) builtins[a[0]] = a[2];
                if (a[1] == uint32_t(spv::Decoration::ArrayStride)) strides[a[0]] = a[2];
            } else if (op == spv::Op::OpMemberDecorate && count == 5 && a[1] == 0 && a[2] == uint32_t(spv::Decoration::Offset)) offsets[a[0]] = a[3];
            if (op >= spv::Op::OpTypeVoid && op <= spv::Op::OpTypePointer)
                definitions[a[0]] = {op,0,std::vector<uint32_t>(a+1,a+count-1)};
            else if (op == spv::Op::OpConstant || op == spv::Op::OpVariable || op == spv::Op::OpLoad ||
                     op == spv::Op::OpAccessChain || op == spv::Op::OpIAdd || op == spv::Op::OpBitcast ||
                     op == spv::Op::OpUConvert || op == spv::Op::OpSConvert || op == spv::Op::OpCompositeConstruct || op == spv::Op::OpConstantComposite ||
                     op == spv::Op::OpCompositeExtract)
                definitions[a[1]] = {op,a[0],std::vector<uint32_t>(a+2,a+count-1)};
            if (op == spv::Op::OpStore) stores[a[0]] = a[1];
            p += count;
        }
    }
    uint32_t named(const std::string& name) const {
        for (const auto& [id,text] : names) if (text == name) return id;
        throw std::runtime_error("missing real emitted name "+name);
    }
    void uniform_layout(uint32_t binding) const {
        uint32_t variable = 0;
        for (const auto& [id,value] : bindings) if (value == binding) variable = id;
        require(variable != 0, "live instance origin UBO variable reflected");
        const auto& pointer = definitions.at(definitions.at(variable).type);
        require(pointer.op == spv::Op::OpTypePointer && pointer.args[0] == uint32_t(spv::StorageClass::Uniform), "instance origin is a uniform resource, never an attribute");
        const auto block_id = pointer.args[1];
        const auto& block = definitions.at(block_id);
        require(block.op == spv::Op::OpTypeStruct && block.args.size() == 1 && offsets.at(block_id) == 0, "instance block has exactly one member at offset0");
        const auto& vector = definitions.at(block.args[0]);
        require(vector.op == spv::Op::OpTypeVector && vector.args[1] == 4, "instance block has exact16-byte uvec4 ABI");
        const auto& scalar = definitions.at(vector.args[0]);
        require(scalar.op == spv::Op::OpTypeInt && scalar.args == std::vector<uint32_t>{32,0}, "instance block is actual unsigned32 in SPIR-V");
    }
    void geometry_layout(uint32_t binding) const {
        uint32_t variable = 0;
        for (const auto& [id,value] : bindings) if (value == binding) variable = id;
        require(variable != 0, "live geometry identity storage reflected");
        const auto& pointer = definitions.at(definitions.at(variable).type);
        require(pointer.op == spv::Op::OpTypePointer && pointer.args[0] == uint32_t(spv::StorageClass::StorageBuffer), "geometry identity retains storage ABI");
        const auto& block = definitions.at(pointer.args[1]);
        const auto& array = definitions.at(block.args.at(0));
        require(array.op == spv::Op::OpTypeRuntimeArray && strides.at(block.args[0]) == 4, "geometry table remains tightly packed uint32");
        const auto& scalar = definitions.at(array.args.at(0));
        require(scalar.op == spv::Op::OpTypeInt && scalar.args == std::vector<uint32_t>{32,0}, "geometry storage has no float carriers");
    }
    std::vector<uint32_t> evaluate(uint32_t id, uint32_t geometry_binding, uint32_t instance_binding,
            const std::vector<uint32_t>& geometry, uint32_t vertex_index, uint32_t instance_index, uint32_t block_base) const {
        const auto& d = definitions.at(id);
        auto sub = [&](uint32_t value) { return evaluate(value,geometry_binding,instance_binding,geometry,vertex_index,instance_index,block_base); };
        if (d.op == spv::Op::OpConstant) return {d.args.at(0)};
        if (d.op == spv::Op::OpCompositeConstruct || d.op == spv::Op::OpConstantComposite) {
            std::vector<uint32_t> result;
            for (auto value : d.args) { auto part = sub(value); result.insert(result.end(),part.begin(),part.end()); }
            return result;
        }
        if (d.op == spv::Op::OpCompositeExtract) return {sub(d.args.at(0)).at(d.args.at(1))};
        if (d.op == spv::Op::OpBitcast || d.op == spv::Op::OpUConvert || d.op == spv::Op::OpSConvert) return sub(d.args.at(0));
        if (d.op == spv::Op::OpIAdd) {
            const auto& scalar = definitions.at(d.type);
            require(scalar.op == spv::Op::OpTypeInt && scalar.args == std::vector<uint32_t>{32,0}, "original-ID sum is uint32, not float or signed-overflow arithmetic");
            return {sub(d.args.at(0)).at(0)+sub(d.args.at(1)).at(0)};
        }
        if (d.op == spv::Op::OpLoad) {
            const auto pointer_id = d.args.at(0);
            if (builtins.contains(pointer_id)) {
                if (builtins.at(pointer_id) == uint32_t(spv::BuiltIn::VertexIndex)) return {vertex_index};
                if (builtins.at(pointer_id) == uint32_t(spv::BuiltIn::InstanceIndex)) return {instance_index};
            }
            const auto& pointer = definitions.at(pointer_id);
            require(pointer.op == spv::Op::OpAccessChain && pointer.args.size() >= 3, "only actual reflected resource loads admitted in ID dataflow");
            const auto binding = bindings.at(pointer.args.at(0));
            require(sub(pointer.args.at(1)).at(0) == 0, "single-member resource block selected");
            if (binding == geometry_binding) return {geometry.at(sub(pointer.args.at(2)).at(0))};
            require(binding == instance_binding && sub(pointer.args.at(2)).at(0) == 0, "instance origin uses only .x of exact captured block");
            return {block_base};
        }
        throw std::runtime_error("unadmitted operation in integer output dataflow; no float conversion is allowed");
    }
};

std::string vertex(bool vertices = true, bool instances = true, unsigned attributes = 1) {
    std::string source;
    for (unsigned n = 0; n < attributes; ++n) source += "in vec4 a"+std::to_string(n)+";";
    source += "flat out uvec2 ids;void main(){ids=uvec2(";
    source += vertices ? "uint(gl_VertexID)," : "7u,";
    source += instances ? "uint(gl_InstanceID));" : "9u);";
    source += "gl_Position=a0";
    for (unsigned n = 1; n < attributes; ++n) source += "+a"+std::to_string(n);
    return source+";}";
}
const std::string fragment = "flat in uvec2 ids;void main(){gl_FragColor=vec4(float(ids.x&255u)/255.0,float(ids.y&255u)/255.0,0,1);}";

void reflected_identity() {
    for (auto policy : {VertexIdentityPolicy::BatchAffine,VertexIdentityPolicy::BatchIndexed}) {
        for (bool vertices : {false,true}) for (bool instances : {false,true}) {
            NormalizeOptions options; options.vertex_identity = policy;
            auto artifact = vispy::shader::build_portable_shader(vertex(vertices,instances),fragment,options,"batch-contract-pins");
            require(artifact->ok,artifact->error);
            require(bool(artifact->vertex_identity_binding) == vertices, "geometry binding follows actual independent liveness");
            require(bool(artifact->batch_instance_binding) == instances && artifact->batch_instance_stage_mask == (instances ? 1u : 0u), "instance UBO follows actual vertex-stage liveness");
            require(artifact->attributes.size() == 1 && artifact->attributes[0].location == 0, "hidden ID resources consume no vertex attributes");
            Module module(artifact->spv_vert);
            if (vertices) module.geometry_layout(artifact->vertex_identity_binding);
            if (instances) module.uniform_layout(artifact->batch_instance_binding);
            const auto geometry = policy == VertexIdentityPolicy::BatchAffine ? std::vector<uint32_t>{16777219u} : std::vector<uint32_t>{17u,900000001u,0xffffffffu};
            for (uint32_t native_instance : {0u,5u,101u}) {
                const auto result = module.evaluate(module.stores.at(module.named("ids")),artifact->vertex_identity_binding,artifact->batch_instance_binding,geometry,1,native_instance,16777235u);
                const uint32_t expected_vertex = !vertices ? 7u : policy == VertexIdentityPolicy::BatchAffine ? geometry[0]+1u : geometry[1];
                require(result == std::vector<uint32_t>{expected_vertex,instances ? 16777235u+native_instance : 9u}, "actual compiled ID expression restores >2**24 IDs and native firstInstance row offset exactly once");
            }
        }
        NormalizeOptions options; options.vertex_identity = policy;
        auto full = vispy::shader::build_portable_shader(vertex(true,true,30),fragment,options,"batch-contract-pins");
        require(full->ok && full->attributes.size() == 30, "batch identity leaves all30 active user attribute locations available");
        const std::string sampled = "uniform sampler2D image;flat in uvec2 ids;void main(){gl_FragColor=texture2D(image,vec2(.5))+vec4(float(ids.x&255u),float(ids.y&255u),0,1);}";
        auto resources = vispy::shader::build_portable_shader(vertex(),sampled,options,"batch-contract-pins");
        require(resources->ok && resources->samplers.size() == 1 && resources->samplers[0].texture_binding == 1 && resources->samplers[0].sampler_binding == 2 && resources->vertex_identity_binding == 3 && resources->batch_instance_binding == 4, "new binding follows existing sampler pairs and geometry slot without collision");
    }
}

void identity_and_refusals() {
    using namespace vispy::shader;
    require(uint32_t(VertexIdentityPolicy::Native)==0 && uint32_t(VertexIdentityPolicy::Affine)==1 && uint32_t(VertexIdentityPolicy::Indexed)==2 && uint32_t(VertexIdentityPolicy::BatchAffine)==3 && uint32_t(VertexIdentityPolicy::BatchIndexed)==4, "legacy policy ordinals remain unchanged and batch values append");
    require(kBatchInstanceUniformBytes == 16, "shared runtime block byte constant matches compiler reflection");
    PortableShaderCache cache;
    std::vector<std::string> keys;
    for (auto policy : {VertexIdentityPolicy::Native,VertexIdentityPolicy::Affine,VertexIdentityPolicy::Indexed,VertexIdentityPolicy::BatchAffine,VertexIdentityPolicy::BatchIndexed}) {
        NormalizeOptions options; options.vertex_identity = policy;
        auto key = portable_shader_identity(vertex(),fragment,options,"pins");
        require((key.find(kBatchInstanceAbi)!=std::string::npos) == batch_identity_policy(policy), "only new policies carry explicit split instance ABI identity");
        require(std::find(keys.begin(),keys.end(),key)==keys.end(), "all five policy/cache identities remain distinct"); keys.push_back(key);
        bool hit = true;
        auto first = cache.get_or_build(vertex(),fragment,options,"pins",&hit);
        require(first->ok && !hit,first->error);
        const auto words = first->spv_vert;
        auto warm = cache.get_or_build(vertex(),fragment,options,"pins",&hit);
        require(hit && first==warm && warm->spv_vert==words, "warm cache retains exact source policy and compiled IDs");
        require(key != portable_shader_identity(vertex(),fragment,options,"different-pins"), "compiler pin participates in batch cache identity");
    }
    for (auto policy : {VertexIdentityPolicy::BatchAffine,VertexIdentityPolicy::BatchIndexed}) {
        NormalizeOptions options; options.vertex_identity = policy;
        for (const auto& name : {"vispy_vertex_identity","VispyVertexIdentity","vispy_batch_instance_origin","VispyBatchInstance"}) {
            for (bool in_fragment : {false,true}) for (bool directive : {false,true}) {
                std::string collision = directive ? std::string("#define ")+name+" hostile\n" : std::string("float ")+name+";\n";
                auto result = normalize_program(in_fragment ? vertex() : collision+vertex(),in_fragment ? collision+fragment : fragment,options);
                require(result.error.find("reserved name")!=std::string::npos, "both stages reject declarations/macros replacing generated batch ABI names");
            }
        }
        options.point_sprites = true;
        require(!normalize_program(vertex(),fragment,options).error.empty(), "batch policy explicitly refuses point-sprite composition");
        options.point_sprites = false; options.line_evaluator = true;
        require(!normalize_program(vertex(),fragment,options).error.empty(), "batch policy explicitly refuses endpoint compute composition");
    }
    NormalizeOptions invalid; invalid.vertex_identity = static_cast<VertexIdentityPolicy>(99);
    require(!normalize_program(vertex(),fragment,invalid).error.empty(), "unknown policies still fail before compiler work");
}
}

void ordinary_stencil_replay_contract() {
    const std::string v = "#version 450\nvoid main(){gl_Position=vec4(0,0,0,1);}";
    const std::string f = "#version 450\nlayout(location=0)out vec4 c;void main(){c=vec4(1);}";
    auto good = compile_vulkan_glsl(v, f); require(good.ok, good.log);
    require(ordinary_stencil_replay_error(good.vertex.words, good.fragment.words).empty(), "ordinary final-SPIRV read-only proof");
    auto malformed = good.vertex.words; malformed[0] = 0;
    require(ordinary_stencil_replay_error(malformed, good.fragment.words).find("vertex final") != std::string::npos, "malformed final module refuses");
    for (const auto& expression : {"effects.x=1u;", "atomicAdd(effects.x,1u);"}) {
        const std::string effects = "#version 450\nlayout(set=0,binding=0)buffer E{uint x;}effects;\n#define EFFECT " + std::string(expression) + "\nvoid main(){EFFECT gl_Position=vec4(0,0,0,1);}";
        auto bad = compile_vulkan_glsl(effects, f); require(bad.ok, bad.log);
        require(!ordinary_stencil_replay_error(bad.vertex.words, bad.fragment.words).empty(), "compiled macro external/atomic writes refuse");
    }
    // Exercise ordinary GLSL.std.450 writable local-pointer operations without
    // inheriting any generated-line proof. Uniform input prevents constant folding.
    auto local = compile_vulkan_glsl("#version 450\nlayout(set=0,binding=0)uniform U{float value;}u;void main(){float whole;float part=modf(u.value,whole);gl_Position=vec4(part,whole,0,1);}", f);
    require(local.ok, local.log);
    require(ordinary_stencil_replay_error(local.vertex.words, local.fragment.words).empty(), "ordinary extended local pointer remains replay-safe");
    auto extended_external = compile_vulkan_glsl("#version 450\nlayout(set=0,binding=0)buffer E{float value;}effects;void main(){float part=modf(1.5,effects.value);gl_Position=vec4(part,0,0,1);}", f);
    require(extended_external.ok, extended_external.log);
    require(!ordinary_stencil_replay_error(extended_external.vertex.words, extended_external.fragment.words).empty(), "compiled extended external write refuses, including compiler temporary stores");
    auto primitive = compile_vulkan_glsl(v, "#version 450\nlayout(location=0)out vec4 c;void main(){c=vec4(float(gl_PrimitiveID));}");
    require(primitive.ok, primitive.log);
    require(ordinary_stencil_replay_error(primitive.vertex.words, primitive.fragment.words).find("PrimitiveId") != std::string::npos, "original primitive ID not silently reset");
}

int main() {
    try {
        reflected_identity(); identity_and_refusals(); ordinary_stencil_replay_contract();
        std::cout << "batch identity glslang/SPIR-V contracts passed: " << checks << "; CPU only, no device or batch draw qualification\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
