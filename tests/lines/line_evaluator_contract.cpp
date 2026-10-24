#include "shader/line_evaluator.hpp"
#include "runtime_line_cache.hpp"
#include "runtime_line_resources.hpp"
#include "runtime_point.hpp"
#include <SPIRV/spirv.hpp11>

#include <cstring>
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace {
using namespace vispy::shader;
uint32_t checks = 0;
void require(bool value, const std::string& reason) {
    ++checks;
    if (!value) throw std::runtime_error(reason);
}

const std::string fragment = "varying vec4 color; void main(){gl_FragColor=color;}";

std::shared_ptr<const PortableShaderArtifact> original(const std::string& vertex, const std::string& frag = fragment,
                                                      NormalizeOptions options = {}) {
    auto value = build_portable_shader(vertex, frag, options, "line-contract-pinned-compiler");
    require(value->ok, "original render shader: " + value->error);
    return value;
}

std::shared_ptr<const LineEvaluatorArtifact> evaluator(const std::string& vertex, const std::string& frag = fragment) {
    auto result = build_line_evaluator(original(vertex, frag));
    require(result->ok, result->error);
    require(result->timings.parse_calls == 1 && result->timings.link_calls == 1 && result->timings.spirv_stages == 1,
            "evaluator must genuinely parse/link/emit compute once");
    return result;
}

std::string name(const uint32_t* data, size_t count) {
    const char* start = reinterpret_cast<const char*>(data);
    const void* end = std::memchr(start, 0, count * 4);
    return std::string(start, end ? static_cast<const char*>(end) - start : count * 4);
}

struct Instruction {
    spv::Op op;
    size_t offset;
    uint32_t function, block;
    std::vector<uint32_t> args;
};

struct SpvTrace {
    uint32_t entry = 0, first_block = 0;
    std::vector<Instruction> code;
    std::unordered_map<uint32_t, std::string> names;
    std::unordered_map<uint32_t, std::vector<uint32_t>> successors;

    explicit SpvTrace(const std::vector<uint32_t>& words) {
        uint32_t function = 0, block = 0;
        for (size_t p = 5; p < words.size();) {
            const uint32_t count = words[p] >> 16;
            require(count && count <= words.size() - p, "well-formed compiler instruction stream");
            const auto op = static_cast<spv::Op>(words[p] & 0xffffu);
            const auto* a = words.data() + p + 1;
            if (op == spv::Op::OpName) names[a[0]] = name(a+1, count-2);
            if (op == spv::Op::OpEntryPoint) { require(a[0] == uint32_t(spv::ExecutionModel::GLCompute), "genuine compute entry"); entry = a[1]; }
            if (op == spv::Op::OpFunction) { function = a[1]; block = 0; }
            if (op == spv::Op::OpLabel) { block = a[0]; if (function == entry && !first_block) first_block = block; }
            if (function == entry && op == spv::Op::OpBranch) successors[block] = {a[0]};
            if (function == entry && op == spv::Op::OpBranchConditional) successors[block] = {a[1],a[2]};
            code.push_back({op,p,function,block,{a,a+count-1}});
            if (op == spv::Op::OpFunctionEnd) { function = 0; block = 0; }
            p += count;
        }
    }

    uint32_t id(const std::string& text, bool prefix = false) const {
        for (const auto& [id,value] : names) if (prefix ? value.starts_with(text) : value == text) return id;
        throw std::runtime_error("missing compiler name " + text);
    }
    const Instruction& store(const std::string& text) const {
        const auto variable = id(text);
        const Instruction* found = nullptr;
        for (const auto& value : code) if (value.function == entry && value.op == spv::Op::OpStore && value.args[0] == variable) {
            require(!found, "original initializer or decoded input is assigned once in entry: " + text);
            found = &value;
        }
        require(found, "original initializer/input store survives: " + text);
        return *found;
    }
    const Instruction& call(const std::string& prefix) const {
        const auto target = id(prefix,true);
        const Instruction* found = nullptr;
        for (const auto& value : code) if (value.function == entry && value.op == spv::Op::OpFunctionCall && value.args[2] == target) {
            require(!found, "one original call in entry: " + prefix); found = &value;
        }
        require(found, "original call survives: " + prefix); return *found;
    }
    bool reaches(uint32_t start, uint32_t target, uint32_t excluded = 0) const {
        std::vector<uint32_t> pending{start}; std::unordered_set<uint32_t> seen;
        while (!pending.empty()) {
            const auto next = pending.back(); pending.pop_back();
            if (next == excluded || !seen.insert(next).second) continue;
            if (next == target) return true;
            if (const auto position = successors.find(next); position != successors.end())
                pending.insert(pending.end(),position->second.begin(),position->second.end());
        }
        return false;
    }
    bool dominates(uint32_t before, uint32_t after) const {
        return reaches(first_block,after) && !reaches(first_block,after,before);
    }
};

void original_global_initializers_follow_inputs() {
    auto value = evaluator(
        "attribute vec2 p;varying vec4 color;float initial_state=2.0;\n"
        "float seed(float v){initial_state+=1.0;return v+float(gl_VertexID%13)+float(gl_InstanceID%7);}\n"
        "float direct=p.x+float(gl_VertexID);\n"
        "float from_helper=seed(direct);\n"
        "float conditional=p.y>0.0?from_helper:-direct;\n"
        "void main(){gl_Position=vec4(p,0,1);color=vec4(direct,from_helper,conditional,initial_state);"
        "if(gl_InstanceID%2==1)return;initial_state+=7.0;}\n");
    require(value->relocated_global_initializers > 0, "actual original AST initializer aggregates relocated");
    require(value->identity.find("initializers=original-AST-after-guarded-inputs") != std::string::npos,
            "initializer-order policy participates in portable evaluator identity");
    const SpvTrace trace(value->spv);
    const auto& input = trace.store("p");
    const auto& vertex = trace.store("vispy_line_vertex_id");
    const auto& instance = trace.store("vispy_line_instance_id");
    const auto& state = trace.store("initial_state");
    const auto& direct = trace.store("direct");
    const auto& helper = trace.call("seed(");
    const auto& from_helper = trace.store("from_helper");
    const auto& conditional = trace.store("conditional");
    const auto& main = trace.call("vispy_user_main(");
    require(std::max({input.offset,vertex.offset,instance.offset}) < state.offset && state.offset < direct.offset &&
            direct.offset < helper.offset && helper.offset < from_helper.offset && from_helper.offset < conditional.offset && conditional.offset < main.offset,
            "decoded attributes/IDs precede original constant/direct/helper/conditional initialization, in declaration order, then one user main");
    for (const auto* initializer : {&state,&direct,&helper,&from_helper,&conditional,&main})
        require(trace.dominates(input.block,initializer->block) && trace.dominates(vertex.block,initializer->block) &&
                trace.dominates(instance.block,initializer->block), "all initializer/main paths are dominated by exact decoded inputs");
    std::unordered_map<uint32_t,uint32_t> loaded;
    for (const auto& instruction : trace.code) if (instruction.op == spv::Op::OpLoad) loaded[instruction.args[1]] = instruction.args[2];
    uint32_t predicate = 0;
    for (const auto& instruction : trace.code) if (instruction.function == trace.entry && instruction.op == spv::Op::OpUGreaterThanEqual &&
        loaded[instruction.args[2]] == trace.id("vispy_line_row") && loaded[instruction.args[3]] == trace.id("vispy_line_count")) predicate = instruction.args[1];
    require(predicate, "padded-invocation row/count predicate survives compiler lowering");
    const Instruction* guard = nullptr;
    for (const auto& instruction : trace.code) if (instruction.function == trace.entry && instruction.op == spv::Op::OpBranchConditional && instruction.args[0] == predicate) guard = &instruction;
    require(guard, "padded row has an actual early-return control edge");
    bool returns = false;
    for (const auto& instruction : trace.code) if (instruction.function == trace.entry && instruction.op == spv::Op::OpReturn && trace.reaches(guard->args[1],instruction.block)) returns = true;
    require(returns && trace.reaches(guard->args[2],input.block), "invalid padded rows return; valid rows can decode original inputs");
    for (const auto* work : {&input,&state,&direct,&helper,&from_helper,&conditional,&main})
        require(!trace.reaches(guard->args[1],work->block), "padded invocation cannot execute input decode, original initializer or main");
    for (const auto& instruction : trace.code)
        if (instruction.op == spv::Op::OpFunctionCall)
            require(!trace.names.at(instruction.args[2]).starts_with("vispy_line_initialize_globals("), "marker replaced, not replayed alongside initializers");
    // Compile the exact same generated source with the ordinary compute policy:
    // this reproduces the pinned hoisting behavior and makes the order assertion
    // a regression against the old route, rather than a mirror of generation.
    const auto legacy = compile_vulkan_compute(value->compute);
    require(legacy.ok && legacy.relocated_global_initializers == 0, "default compute compiler policy stays unchanged");
    const SpvTrace unrelocated(legacy.compute.words);
    require(unrelocated.store("direct").offset < unrelocated.store("p").offset, "ordinary policy independently demonstrates the input-dependent hoisting gap");
    require(value->line_map.size() == std::count(value->compute.begin(),value->compute.end(),'\n') &&
            std::find(value->line_map.begin(),value->line_map.end(),5) != value->line_map.end(), "original initializer source mapping survives");
}

void isolated_private_main_and_early_returns() {
    auto value = evaluator(
        "attribute vec2 p; varying vec4 color; float private_state=2.0;\n"
        "void hook(){private_state+=3.0;gl_Position=vec4(p,private_state,1.0);}\n"
        "void main(){hook();color=vec4(private_state);if(gl_VertexID%2==1)return;"
        "private_state+=7.0;gl_Position.z=private_state;}\n");
    require(value->compute.find("gl_Position") == std::string::npos && value->compute.find("gl_VertexIndex") == std::string::npos,
            "compute must use raw GL clip and exact original semantic identities");
    require(value->compute.find("= -") == std::string::npos && value->compute.find("* 0.5") == std::string::npos,
            "endpoint evaluation must not apply GL-to-WebGPU coordinates");
    uint32_t entry = 0, user = 0, private_variable = 0;
    std::unordered_map<uint32_t, std::string> names;
    for (size_t p = 5; p < value->spv.size();) {
        const auto count = value->spv[p] >> 16, op = value->spv[p] & 0xffffu;
        const auto* a = value->spv.data() + p + 1;
        if (op == 5) names[a[0]] = name(a + 1, count - 2);
        if (op == 15) { require(a[0] == 5, "SPIR-V execution model must be GLCompute"); entry = a[1]; }
        p += count;
    }
    for (const auto& [id, text] : names) {
        if (text.starts_with("vispy_user_main(")) user = id;
        if (text == "private_state") private_variable = id;
    }
    require(entry && user && private_variable, "entry/private global/user function reflection must survive");
    uint32_t current = 0, user_calls = 0, private_stores = 0; bool private_storage = false, returns = false;
    for (size_t p = 5; p < value->spv.size();) {
        const auto count = value->spv[p] >> 16, op = value->spv[p] & 0xffffu;
        const auto* a = value->spv.data() + p + 1;
        if (op == 54) current = a[1];
        if (op == 56) current = 0;
        if (op == 57 && a[2] == user) { require(current == entry, "only generated compute entry invokes original main"); ++user_calls; }
        if (op == 59 && a[1] == private_variable) private_storage = a[2] == 6;
        if (op == 62 && a[0] == private_variable && current == entry) ++private_stores;
        if (op == 253 && current == user) returns = true;
        p += count;
    }
    require(user_calls == 1 && private_storage && private_stores == 1 && returns,
            "one user-main call, per-invocation private initialization and early-return control flow required");
    require(value->outputs[0].varying.name == "color" && value->outputs[0].offset == 16 && value->output_row_bytes == 32,
            "final clip/value typed output row");
    require(value->line_map.size() == std::count(value->compute.begin(), value->compute.end(), '\n'), "full evaluator source mapping");
    require(std::find(value->line_map.begin(), value->line_map.end(), 3) != value->line_map.end(), "original early-return line must remain mapped");
}

void typed_arrays_matrix_interpolation_and_ids() {
    const std::string vertex =
        "attribute vec2 p;attribute uvec2 data;varying vec3 colors[2];noperspective out mat2x3 basis[2];"
        "flat out uvec2 ids;out vec2 linear;void main(){gl_Position=vec4(p,0.0,1.0);"
        "colors[0]=vec3(1);colors[1]=vec3(2);basis[0]=mat2x3(1);basis[1]=mat2x3(2);"
        "ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID))+data;linear=p;}";
    const std::string frag =
        "varying vec3 colors[2];noperspective in mat2x3 basis[2];flat in uvec2 ids;in vec2 linear;"
        "void main(){gl_FragColor=vec4(colors[0]+colors[1]+vec3(basis[1][1].x)+vec3(ids.x)+vec3(linear,0),1);}";
    auto render = original(vertex, frag); auto value = build_line_evaluator(render);
    require(value->ok, value->error);
    require(render->varyings.size() == 4 && render->varyings[0].location == 0 && render->varyings[1].location == 2 &&
            render->varyings[2].location == 6 && render->varyings[3].location == 7, "array/matrix location spans retain paired interfaces");
    require(value->input_row_words == 6 && value->inputs[0].word_offset == 2 && value->inputs[1].word_offset == 4,
            "exact IDs precede active raw-component attribute row");
    require(value->inputs[1].value_type.scalar == ShaderScalarType::Uint && value->compute.find("uintBitsToFloat(vispy_line_words[vispy_line_base + 4u]") == std::string::npos,
            "uint inputs must retain raw integer identity");
    require(value->compute.find("int(vispy_line_vertex_id)") != std::string::npos && value->compute.find("int(vispy_line_instance_id)") != std::string::npos,
            "GL integer builtins originate from exact uint32 storage, never float");
    require(value->outputs[0].offset == 16 && value->outputs[0].array_stride == 16 && value->outputs[0].size == 32,
            "vec3 array std430 packing");
    require(value->outputs[1].offset == 48 && value->outputs[1].array_stride == 32 && value->outputs[1].matrix_stride == 16 && value->outputs[1].size == 64,
            "rectangular matrix array std430 packing");
    require(value->outputs[1].varying.interpolation == "noperspective" && value->outputs[2].varying.interpolation == "flat" &&
            value->outputs[3].varying.interpolation == "smooth", "interpolation metadata survives evaluator compilation");
    require(value->outputs[2].offset == 112 && value->outputs[2].storage_type == "uvec2" && value->outputs[3].offset == 120 && value->output_row_bytes == 128,
            "typed uint/float output offsets and reflected row stride");
    require(value->identity != render->identity && value->original == render && value->identity.find("isolated-main-once-v3") != std::string::npos,
            "evaluator policy/source identity and immutable provenance are separate");
    require(value->storage_bytes() >= sizeof(LineEvaluatorArtifact) + value->spv.size()*4, "evaluator CPU owned storage is accounted");
}

void qualified_interpolation_survives_endpoint_compilation() {
    for (const std::string qualifier : {"centroid", "sample"}) {
        const auto value = evaluator(
            "attribute vec2 p;" + qualifier + " out vec4 color;"
            "void main(){gl_Position=vec4(p,0,1);color=vec4(p,0,1);}",
            qualifier + " in vec4 color;void main(){gl_FragColor=color;}");
        require(value->outputs.size() == 1 && value->outputs[0].varying.name == "color",
                "qualified original varying survives real render and endpoint compilation");
        const auto& varying = value->outputs[0].varying;
        require(varying.centroid == (qualifier == "centroid") && varying.sample == (qualifier == "sample") &&
                varying.interpolation == "smooth",
                "endpoint output retains the distinct interpolation location for the render consumer");
        SpvStorageLayout layout; std::string error;
        require(reflect_storage_rows(value->spv, "VispyLineOutputs", layout, error), error);
        require(layout.members.size() == 2 && layout.row_stride == 32 &&
                layout.members[1].offset == 16 && layout.members[1].size == 16 &&
                layout.members[1].value_type.scalar == ShaderScalarType::Float &&
                layout.members[1].value_type.rows == 4,
                "compiled qualified endpoint emits the full floating-point varying in its storage row");
        SpvTrace trace(value->spv);
        require(trace.entry != 0, "qualified endpoint has an actual compute entry point");
    }
}

void bool_uniforms_samplers_and_inactive_inputs() {
    NormalizeOptions options; options.base_level_sampling = true;
    auto render = original(
        "attribute vec2 p;attribute float inactive_count;uniform bool gate;uniform bvec3 channels;uniform sampler2D image;varying vec4 color;"
        "vec4 fetch(sampler2D s,vec2 uv){if(gate)return texture2D(s,uv);return vec4(channels,1); }"
        "void main(){color=fetch(image,p);gl_Position=vec4(p,0,1);}", fragment, options);
    auto value = build_line_evaluator(render);
    require(value->ok, value->error);
    require(value->inputs.size() == 1 && value->inputs[0].attribute.name == "p" && value->input_row_words == 4,
            "inactive count input must not require sparse source fetch");
    require(value->uniforms.size() == 2 && value->uniforms[0].type == "bool" && value->uniforms[0].storage_type == "int" &&
            value->uniforms[1].type == "bvec3" && value->uniforms[1].storage_type == "ivec3", "bool semantic/storage reflection preserved");
    require(value->uniform_stage_mask == 4 && value->samplers.size() == 1 && value->samplers[0].texture_stage_mask == 4 &&
            value->samplers[0].sampler_stage_mask == 4, "compute resource visibility is queried rather than render-mask reuse");
    require(value->input_binding > value->samplers[0].sampler_binding && value->output_binding == value->input_binding + 1,
            "generated storage bindings cannot collide with UBO/textures/samplers");
    require(value->compute.find("textureLod") != std::string::npos, "admitted base-level sampler semantics survive opaque helper lowering");
}

void dispatch_grants_and_failure_atomicity() {
    auto value = evaluator("attribute vec2 p;varying vec4 color;void main(){gl_Position=vec4(p,0,1);color=vec4(1);}");
    LineEvaluatorLimits limits; LineEvaluatorDispatch dispatch; std::string error;
    require(line_evaluator_dispatch(*value, 65, limits, dispatch, error) && dispatch.workgroups_x == 2 &&
            dispatch.input_header == std::array<uint32_t,4>{65,1,4,0} && dispatch.input_bytes == 16+65*16 && dispatch.output_bytes == 65*32,
            "bounded count/header/workgroup arithmetic");
    const auto retained = dispatch;
    auto small = limits; small.max_storage_buffer_binding_size = dispatch.output_bytes-1;
    require(!line_evaluator_dispatch(*value,65,small,dispatch,error) && error.find("partitioning required") != std::string::npos && dispatch.input_header == retained.input_header,
            "storage overflow fails before publishing/allocating dispatch");
    small = limits;small.max_workgroups_x=1;
    require(!line_evaluator_dispatch(*value,65,small,dispatch,error), "actual workgroup grants constrain payload batching");
    require(!line_evaluator_dispatch(*value,uint64_t(UINT32_MAX)+1,limits,dispatch,error), "uint32 identity/count overflow rejected");
    require(!line_evaluator_dispatch(*value,UINT32_MAX,limits,dispatch,error), "raw storage word indexing overflow rejected");
    require(line_evaluator_dispatch(*value,0,limits,dispatch,error) && dispatch.input_bytes==0 && dispatch.output_bytes==0 && dispatch.workgroups_x==0,
            "empty original selection dispatches nothing");
    small=limits;small.max_storage_buffers=1;
    require(!build_line_evaluator(value->original,small)->ok, "missing granted read/write compute storage capability rejected");
    small=limits;small.max_workgroup_invocations=32;
    require(!build_line_evaluator(value->original,small)->ok, "unsafe workgroup capability cannot be assumed");
    small=limits;small.max_buffer_size=16;
    require(!build_line_evaluator(value->original,small)->ok, "even one row must satisfy actual allocation grants");
    small=limits;small.max_bindings=value->output_binding;
    require(!build_line_evaluator(value->original,small)->ok, "reserved binding must fit actual binding range");
}

void captured_resource_remapping() {
    using namespace vispy::lines;
    const auto render = original(
        "attribute vec2 p;uniform mat3 u_matrix[2];uniform vec2 u_array[2];"
        "uniform bvec2 u_flags;uniform ivec2 u_signed;uniform vec4 u_raw;varying vec4 color;"
        "void main(){gl_Position=vec4(p+u_array[0]+u_array[1]+u_matrix[0][0].xy+u_matrix[1][1].xy,0,1);"
        "color=u_raw+vec4(u_signed,u_flags.x?1:0,u_flags.y?1:0);}",
        "uniform float u_fragment;varying vec4 color;void main(){gl_FragColor=color*u_fragment;}");
    const auto compute = build_line_evaluator(render);
    require(compute->ok, "genuine compute resource reflection: " + compute->error);
    std::vector<uint8_t> captured(render->uniform_bytes, 0);
    auto field = [&](const std::string& text) -> const NormUniform& {
        for (const auto& uniform : render->uniforms) if (uniform.name == text) return uniform;
        throw std::runtime_error("missing original uniform " + text);
    };
    auto pack = [&](const std::string& text, const void* values, size_t bytes) {
        std::string error;
        require(pack_uniform_value(field(text), values, bytes, captured.data(), captured.size(), &error), error);
    };
    const float matrices[] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18};
    const uint32_t raw[] = {0x80000000u, 0x7fc12345u, 0x3f800000u, 0xc0400000u};
    const uint32_t arrays[] = {0x80000000u, 0x3e800000u, 0x7fc23456u, 0xbf800000u};
    const int32_t flags[] = {1, 0};
    const int32_t signed_values[] = {INT32_MIN, INT32_MAX};
    const float fragment_only = .5f;
    pack("u_matrix", matrices, sizeof(matrices));
    pack("u_raw", raw, sizeof(raw));
    pack("u_array", arrays, sizeof(arrays));
    pack("u_flags", flags, sizeof(flags));
    pack("u_signed", signed_values, sizeof(signed_values));
    pack("u_fragment", &fragment_only, sizeof(fragment_only));
    const auto genuine = repack_endpoint_uniforms(render->uniforms, captured, compute->uniforms,
                                                 compute->uniform_bytes, 65536);
    require(genuine.size() == compute->uniform_bytes, "actual reflected compute UBO mapped from captured original");
    // A second legal physical layout reorders fields, pads arrays differently
    // and stores matrices by row. Expected landmarks are independent of the
    // remapper, while source metadata/payload came from the real compiler.
    auto requested = render->uniforms;
    std::erase_if(requested, [](const auto& value) { return value.name == "u_fragment"; });
    std::reverse(requested.begin(), requested.end());
    uint32_t bytes = 16;
    for (auto& uniform : requested) {
        uniform.offset = bytes;
        if (uniform.name == "u_matrix") {
            uniform.row_major = true;
            uniform.array_stride = 64;
            uniform.size = 128;
        } else if (uniform.name == "u_array") {
            uniform.array_stride = 32;
            uniform.size = 64;
        }
        bytes += (uniform.size + 15u) & ~15u;
    }
    const int32_t noncanonical_true = -3;
    std::memcpy(captured.data() + field("u_flags").offset, &noncanonical_true, 4);
    const auto mapped = repack_endpoint_uniforms(render->uniforms, captured, requested, bytes, 65536);
    auto target = [&](const std::string& text) -> const NormUniform& {
        for (const auto& uniform : requested) if (uniform.name == text) return uniform;
        throw std::runtime_error("missing target uniform " + text);
    };
    auto word = [&](uint32_t offset) {
        uint32_t value;
        std::memcpy(&value, mapped.data() + offset, 4);
        return value;
    };
    require(std::all_of(mapped.begin(), mapped.begin()+16, [](uint8_t value) { return value == 0; }),
            "unused compute UBO prefix is zero");
    for (uint32_t component = 0; component < 4; ++component)
        require(word(target("u_raw").offset + component*4) == raw[component], "raw float bits survive changed UBO offsets");
    require(word(target("u_signed").offset) == 0x80000000u && word(target("u_signed").offset+4) == 0x7fffffffu,
            "signed integer extremes survive physical remapping without float carriers");
    require(word(target("u_flags").offset) == 1 && word(target("u_flags").offset+4) == 0,
            "bool physical storage normalized without changing false");
    const auto& matrix = target("u_matrix");
    for (uint32_t array = 0; array < 2; ++array) {
        for (uint32_t column = 0; column < 3; ++column) {
            for (uint32_t row = 0; row < 3; ++row) {
                uint32_t expected;
                std::memcpy(&expected, matrices + array*9 + column*3 + row, 4);
                require(word(matrix.offset + array*64 + row*16 + column*4) == expected,
                        "column-major logical components map into row-major array matrices");
            }
        }
    }
    const auto& array = target("u_array");
    require(word(array.offset) == arrays[0] && word(array.offset+4) == arrays[1] &&
            word(array.offset+32) == arrays[2] && word(array.offset+36) == arrays[3],
            "array elements use compute reflected stride and preserve signed-zero/NaN bits");
    auto rejects = [&](auto&& action, const std::string& reason) {
        bool rejected = false;
        try { action(); }
        catch (const std::exception& error) { rejected = std::string(error.what()).find(reason) != std::string::npos; }
        require(rejected, "resource mapping must reject " + reason);
    };
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, captured, requested, UINT32_MAX, 32); }, "granted binding size");
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, std::span<const uint8_t>(captured).first(4), requested, bytes, 65536); }, "exceeds buffer");
    auto broken = requested;
    broken[0].type = "mat2";
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, captured, broken, bytes, 65536); }, "incompatible type/array");
    broken = requested;
    broken[0].component_count = UINT32_MAX;
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, captured, broken, bytes, 65536); }, "inconsistent reflected type");
    broken = requested;
    for (auto& value : broken) if (value.name == "u_matrix") value.matrix_stride = UINT32_MAX - 3;
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, captured, broken, bytes, 65536); }, "array stride aliases logical elements");
    for (const auto& where : {std::string("source"), std::string("target")}) {
        for (const auto& defect : {std::string("matrix"), std::string("array"), std::string("unaligned"), std::string("overlap")}) {
            auto source_fields = render->uniforms;
            auto target_fields = requested;
            auto& changed = where == "source" ? source_fields : target_fields;
            for (auto& value : changed) {
                if (defect == "matrix" && value.name == "u_matrix") value.matrix_stride = 4;
                if (defect == "array" && value.name == "u_array") value.array_stride = 4;
                if (defect == "unaligned" && value.name == "u_raw") ++value.offset;
                if (defect == "overlap" && value.name == "u_raw") {
                    const auto found = std::find_if(changed.begin(), changed.end(), [](const auto& other) { return other.name == "u_signed"; });
                    value.offset = found->offset;
                }
            }
            const auto reason = defect == "matrix" ? "matrix stride aliases" : defect == "array" ? "array stride aliases" :
                                defect == "unaligned" ? "unaligned reflected" : "overlapping reflected members";
            rejects([&]{ repack_endpoint_uniforms(source_fields, captured, target_fields, bytes, 65536); }, reason);
        }
    }
    broken = requested;
    broken.push_back(broken[0]);
    broken.back().offset = bytes;
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, captured, broken, bytes+128, 65536); }, "duplicate requested name");
    broken = requested;
    broken[0].name = "missing";
    rejects([&]{ repack_endpoint_uniforms(render->uniforms, captured, broken, bytes, 65536); }, "missing or incompatible");
    auto duplicate = render->uniforms;
    duplicate.push_back(duplicate[0]);
    rejects([&]{ repack_endpoint_uniforms(duplicate, captured, requested, bytes, 65536); }, "duplicate reflected name");

    const std::vector<NormAttribute> attributes = {{"unused", "vec4", 0}, {"b", "uint", 1}, {"a", "vec2", 2}};
    std::vector<LineInputField> inputs(2);
    inputs[0].attribute = attributes[2]; inputs[1].attribute = attributes[1];
    require(endpoint_attribute_order(attributes, inputs) == std::vector<size_t>{2,1},
            "compute active attributes map by name/type independent of original slot order");
    inputs[0].attribute.type = "ivec2";
    rejects([&]{ endpoint_attribute_order(attributes, inputs); }, "incompatible type");
    const std::vector<NormSampler> samplers = {{"unused_fragment", "2d", 1, 2, 2, 2}, {"volume", "3d", 3, 4, 1, 1},
                                              {"image", "2d", 5, 6, 1, 1}};
    auto compute_samplers = std::vector<NormSampler>{samplers[2], samplers[1]};
    for (auto& value : compute_samplers) { value.texture_stage_mask = value.sampler_stage_mask = 4; value.texture_binding += 10; }
    require(endpoint_sampler_order(samplers, compute_samplers) == std::vector<size_t>{2,1},
            "vertex-only compute textures map independently of fragment filtering and changed bindings");
    compute_samplers[0].dim = "3d";
    rejects([&]{ endpoint_sampler_order(samplers, compute_samplers); }, "incompatible dimension");
    auto typed_original = samplers;
    typed_original[2].sample_scalar = ShaderScalarType::Uint;
    typed_original[1].sample_scalar = ShaderScalarType::Sint;
    auto typed_requested = std::vector<NormSampler>{typed_original[2], typed_original[1]};
    for (auto& value : typed_requested) {
        value.texture_stage_mask = value.sampler_stage_mask = 4;
        value.texture_binding += 10;
    }
    require(endpoint_sampler_order(typed_original, typed_requested) == std::vector<size_t>{2,1},
            "typed endpoint textures retain scalar identity across stage and binding changes");
    typed_requested[0].sample_scalar = ShaderScalarType::Float;
    rejects([&]{ endpoint_sampler_order(typed_original, typed_requested); }, "incompatible sampled scalar");
    typed_requested[0].sample_scalar = ShaderScalarType::Sint;
    rejects([&]{ endpoint_sampler_order(typed_original, typed_requested); }, "incompatible sampled scalar");
    typed_requested[0].sample_scalar = ShaderScalarType::Uint;
    typed_requested[1].sample_scalar = ShaderScalarType::Uint;
    rejects([&]{ endpoint_sampler_order(typed_original, typed_requested); }, "incompatible sampled scalar");
}

void contextual_unsupported_and_mapped_errors() {
    const std::string compute_prefix = "#version 450\nlayout(local_size_x=64)in;";
    for (const auto& body : {"void main(){}", "void vispy_line_initialize_globals(){}void main(){vispy_line_initialize_globals();vispy_line_initialize_globals();}",
                            "void vispy_line_initialize_globals(){}void main(){if(gl_GlobalInvocationID.x==0u)vispy_line_initialize_globals();}"}) {
        const auto unexpected = compile_vulkan_compute(compute_prefix+body,ComputeInitializerPolicy::EndpointInputsFirst);
        require(!unexpected.ok && unexpected.log.find("unexpected pinned glslang tree") != std::string::npos && unexpected.spirv_stages == 0,
                "missing/duplicate/nested marker fails contextually before SPIR-V publication");
    }
    require(!compile_vulkan_compute(compute_prefix+"void main(){}",static_cast<ComputeInitializerPolicy>(99)).ok, "unknown compute policy cannot silently use default semantics");
    require(!build_line_evaluator({})->ok, "unvalidated/missing original shader cannot be evaluated");
    auto render = original("attribute vec2 p;varying vec4 color;void main(){gl_Position=vec4(p,0,1);color=vec4(1);}");
    auto changed = std::make_shared<PortableShaderArtifact>(*render);
    changed->source_vertex = "attribute vec2 p;varying vec4 color;\nvoid main(){\n gl_Position=vec4(p,0,1);color=does_not_exist;\n}\n";
    auto invalid = build_line_evaluator(changed);
    require(!invalid->ok && invalid->mapped_line == 3 && invalid->error.find("does_not_exist") != std::string::npos,
            "compute parse failure retains exact original source line and stage evidence");
    for (const auto& builtin : {"gl_ClipDistance", "gl_DrawID", "gl_VertexIndex"}) {
        changed = std::make_shared<PortableShaderArtifact>(*render);
        changed->source_vertex = std::string("varying vec4 color;void main(){gl_Position=vec4(1);color=vec4(") + builtin + ");}";
        invalid = build_line_evaluator(changed);
        require(!invalid->ok && invalid->error.find("unsupported builtin " + std::string(builtin)) != std::string::npos,
                "unsupported original builtin must fail contextually before compute encoding");
    }
    changed=std::make_shared<PortableShaderArtifact>(*render);
    changed->source_vertex="varying vec4 color;float vispy_line_row;void main(){gl_Position=vec4(1);color=vec4(1);}";
    require(build_line_evaluator(changed)->error.find("reserved name vispy_line_row")!=std::string::npos, "reserved private evaluator names rejected");
    changed=std::make_shared<PortableShaderArtifact>(*render);
    changed->source_vertex="#define vispy_line_count 0u\nvarying vec4 color;void main(){gl_Position=vec4(1);color=vec4(1);}";
    require(build_line_evaluator(changed)->error.find("reserved name vispy_line_count")!=std::string::npos, "macro cannot overwrite generated ABI names");
    changed=std::make_shared<PortableShaderArtifact>(*render);
    changed->source_fragment="uniform float vispy_line_row;varying vec4 color;void main(){gl_FragColor=color*vispy_line_row;}";
    require(build_line_evaluator(changed)->error.find("reserved name vispy_line_row")!=std::string::npos, "fragment resource cannot collide with compute ABI globals");
    changed=std::make_shared<PortableShaderArtifact>(*render);
    changed->source_vertex="layout(binding=9) buffer Values { float shared_value; };varying vec4 color;void main(){shared_value+=1;gl_Position=vec4(1);color=vec4(shared_value);}";
    require(build_line_evaluator(changed)->error.find("shared storage/side effects")!=std::string::npos, "shared shader storage is not an isolated private invocation");
    changed=std::make_shared<PortableShaderArtifact>(*render);changed->point_sprites=true;
    require(build_line_evaluator(changed)->error.find("point-quad")!=std::string::npos, "original endpoint cannot be a previously expanded point vertex");
    NormalizeOptions options;options.line_evaluator=true;
    require(!build_portable_shader(render->source_vertex,render->source_fragment,options,"pins")->ok,
            "compute evaluator body cannot accidentally become a render artifact");
    SpvStorageLayout reflected;std::string error;
    require(!reflect_storage_rows({0x07230203u,0,0,0,0,0},"VispyLineOutputs",reflected,error), "truncated storage reflection rejected");
}

void endpoint_input_identity_and_shared_cache() {
    using vispy::lines::EndpointInputStamp;
    using vispy::lines::Mode;
    using namespace vispy::inputs;
    using vispy::lines::endpoint_constant_word;
    for (const auto* type : {"uint", "uvec2", "uvec3", "uvec4"}) {
        require(endpoint_constant_word(type, true, 16777217, 0) == 16777217 &&
                endpoint_constant_word(type, true, UINT32_MAX, 0) == UINT32_MAX,
                "internal unsigned constant words preserve high IDs without float rounding");
    }
    for (const auto* type : {"int", "ivec2", "ivec3", "ivec4"}) {
        require(endpoint_constant_word(type, true, INT32_MIN, 0) == 0x80000000u &&
                endpoint_constant_word(type, true, -1, 0) == UINT32_MAX &&
                endpoint_constant_word(type, true, INT32_MAX, 0) == 0x7fffffffu,
                "internal signed constant words preserve exact int32 bit patterns");
    }
    for (const auto* type : {"float", "vec2", "vec3", "vec4"}) {
        require(endpoint_constant_word(type, false, 0, -0.0) == 0x80000000u &&
                endpoint_constant_word(type, false, 0, 0.0) == 0 &&
                endpoint_constant_word(type, false, 0, 1.5) == 0x3fc00000u &&
                endpoint_constant_word(type, true, 16777217, 0) == std::bit_cast<uint32_t>(float(16777217)),
                "float constants select numeric carrier and preserve floating signed zero");
    }
    auto rejected_constant = [&](const char* type, bool integer_value, int64_t integer, double floating) {
        bool rejected = false;
        try { endpoint_constant_word(type, integer_value, integer, floating); }
        catch (const std::exception& error) { rejected = std::string(error.what()).starts_with("lines:"); }
        require(rejected, "invalid internal endpoint constant rejects before lossy integer conversion");
    };
    rejected_constant("int", false, 0, 1.0);
    rejected_constant("uint", false, 0, 16777217.0);
    rejected_constant("ivec2", true, int64_t(INT32_MIN) - 1, 0);
    rejected_constant("ivec4", true, int64_t(INT32_MAX) + 1, 0);
    rejected_constant("uvec2", true, -1, 0);
    rejected_constant("uvec4", true, int64_t(UINT32_MAX) + 1, 0);
    rejected_constant("uint", true, INT64_MAX, 0);
    rejected_constant("int", true, INT64_MIN, 0);
    rejected_constant("bool", true, 1, 0);
    rejected_constant("vec5", false, 0, 1.0);
    const std::vector<EndpointInputStamp> inputs{
        {"position", "vec2", 100, 7, 4, 24, 0, 2},
        {"instance_color", "uvec4", 101, 8, 8, 32, 2, 4}};
    const auto key = [&](const std::vector<EndpointInputStamp>& stamps,
            std::string_view identity = "original;source:abi1", Mode mode = Mode::List,
            uint64_t first = 3, uint64_t count = 4, uint64_t instances = 2,
            uint64_t index = 200, uint64_t revision = 9, uint32_t width = 4) {
        return vispy::lines::endpoint_input_key(identity, mode, first, count, instances,
                                               index, revision, width, stamps);
    };
    const auto a_key = key(inputs);
    require(a_key.starts_with("line-endpoint:v1:"), "endpoint input key has separate policy/category prefix");
    require(a_key == key(inputs), "identical immutable endpoint input stamps have stable exact keys");
    std::unordered_set<std::string> identities{a_key};
    auto distinct = [&](std::string changed) {
        require(changed != a_key && identities.insert(std::move(changed)).second,
                "each endpoint geometry dependency has its own collision-free identity");
    };
    distinct(key(inputs, "original;source:abi2"));
    distinct(key(inputs, "original;source:abi1", Mode::Strip));
    distinct(key(inputs, "original;source:abi1", Mode::Loop));
    distinct(key(inputs, "original;source:abi1", Mode::List, 4));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 5));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 4, 3));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 4, 2, 201));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 4, 2, 200, 10));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 4, 2, 200, 9, 2));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 4, 2, 200, 9, 1));
    distinct(key(inputs, "original;source:abi1", Mode::List, 3, 4, 2, 200, 9, 0));
    for (size_t field = 0; field < inputs.size(); ++field) {
        for (unsigned dependency = 0; dependency < 8; ++dependency) {
            auto changed = inputs;
            auto& stamp = changed[field];
            switch (dependency) {
                case 0: stamp.name += ":changed"; break;
                case 1: stamp.type += ":changed"; break;
                case 2: ++stamp.identity; break;
                case 3: ++stamp.revision; break;
                case 4: ++stamp.offset; break;
                case 5: ++stamp.stride; break;
                case 6: ++stamp.divisor; break;
                case 7: ++stamp.components; break;
            }
            distinct(key(changed));
        }
    }
    auto reordered = inputs; std::reverse(reordered.begin(), reordered.end());
    distinct(key(reordered));
    auto fewer = inputs; fewer.pop_back(); distinct(key(fewer));
    auto extra = inputs; extra.push_back(inputs[0]); distinct(key(extra));
    auto constant = inputs; constant[0].stride = 0;
    auto newer_constant = constant; ++newer_constant[0].revision;
    auto replaced_constant = constant; ++replaced_constant[0].identity;
    require(key(constant) != key(newer_constant) && key(constant) != key(replaced_constant),
            "raw constant value revisions and allocations invalidate geometry even with zero stride");
    auto ambiguous_a = inputs, ambiguous_b = inputs;
    ambiguous_a[0].name = "a:b"; ambiguous_a[0].type = "c";
    ambiguous_b[0].name = "a"; ambiguous_b[0].type = "b:c";
    require(key(ambiguous_a) != key(ambiguous_b), "name/type delimiter redistribution cannot alias framed strings");
    const std::string embedded("original\0source:abi1", 20);
    require(key(inputs, embedded) != key(inputs, std::string_view(embedded.data(), 8)),
            "full evaluator identity retains embedded zeros instead of C-string truncation");
    ambiguous_a[0].name = std::string("x\0:y", 4);
    ambiguous_b[0].name = "x";
    require(key(ambiguous_a) != key(ambiguous_b), "raw field names remain length-framed");
    auto boundary = inputs;
    boundary[0].identity = boundary[0].revision = boundary[0].offset = boundary[0].stride = boundary[0].divisor = UINT64_MAX;
    boundary[0].components = UINT32_MAX;
    const auto full_width = key(boundary, "abi", Mode::List, UINT64_MAX, UINT64_MAX, UINT64_MAX,
                                UINT64_MAX, UINT64_MAX, 4);
    require(full_width.find("18446744073709551615:") != std::string::npos &&
            full_width.find("4294967295:") != std::string::npos && full_width != a_key,
            "key encoding preserves complete uint64/uint32 stamps without arithmetic truncation");
    for (auto invalid : {0, 1}) {
        bool rejected = false;
        try { key(inputs, "abi", invalid ? Mode::List : static_cast<Mode>(99), 0, 1, 1, 0, 0, invalid ? 3 : 0); }
        catch (const std::invalid_argument& error) { rejected = std::string(error.what()).starts_with("lines:"); }
        require(rejected, "invalid primitive/index-width key metadata rejects contextually");
    }

    struct InputRecord {
        std::vector<uint8_t> cpu;
        std::shared_ptr<InputRecord> child;
        bool gpu = true;
    };
    using Ptr = std::shared_ptr<InputRecord>;
    std::function<uint64_t(const Ptr&,std::unordered_set<const void*>&)> graph;
    graph = [&](const Ptr& record, std::unordered_set<const void*>& visited) -> uint64_t {
        if (!record || !visited.insert(record.get()).second) return 0;
        return bounded_cost_add(sizeof(InputRecord) + 2 * sizeof(void*) + record->cpu.capacity(),
                                graph(record->child, visited));
    };
    const auto bytes = [&](const Ptr& record) {
        std::unordered_set<const void*> visited;
        return graph(record, visited);
    };
    const auto make = [](size_t size) {
        auto record = std::make_shared<InputRecord>(); record->cpu.resize(size); return record;
    };
    CurrentConversions<Ptr> current;
    OversizedConversions<Ptr> working(2, 10000);
    std::unordered_map<std::string,Ptr> history;
    size_t builds = 0;
    auto convert = [&](CurrentCategory category, const std::string& identity, size_t size = 1400) {
        return working_cached_conversion(current, working, category, history, identity,
            [&] { ++builds; return make(size); }, bytes, graph, 2, 1024);
    };
    static_assert(static_cast<size_t>(CurrentCategory::LineEndpoint) == 6);
    static_assert(static_cast<size_t>(CurrentCategory::Batch) == 7);
    static_assert(static_cast<size_t>(CurrentCategory::CompactFit) == 8);
    require(CurrentConversions<Ptr>::category_count == 9 && current.size() == 0,
            "endpoint and batch owners retain their ordinals and share fixed existing cache budgets");
    auto [a, cold_a] = convert(CurrentCategory::LineEndpoint, a_key);
    const auto b_key = key(inputs, "original;source:abi1", Mode::List, 7);
    auto [b, cold_b] = convert(CurrentCategory::LineEndpoint, b_key);
    std::weak_ptr<InputRecord> weak_a = a, weak_b = b;
    a.reset(); b.reset();  // Simulate all Tickets retiring.
    auto [again, rebuilt] = convert(CurrentCategory::LineEndpoint, a_key);
    require(cold_a && cold_b && !rebuilt && builds == 2 && again == weak_a.lock() && !weak_b.expired(),
            "within-budget endpoint A-B-A retains exact CPU/GPU owner after Ticket retirement");
    const auto evictions = working.evictions();
    auto ordinary = convert(CurrentCategory::Vertex, "vertex:shared-budget").first;
    require(working.size() == 2 && working.evictions() == evictions + 1 &&
            working.peek(CurrentCategory::LineEndpoint, a_key) == again &&
            !working.peek(CurrentCategory::LineEndpoint, b_key) &&
            current.find(CurrentCategory::Vertex, "vertex:shared-budget") == ordinary,
            "endpoint and ordinary oversized entries compete for one LRU budget");
    convert(CurrentCategory::Instance, "instance:shared-budget");
    require(!working.peek(CurrentCategory::LineEndpoint, a_key) &&
            current.find(CurrentCategory::LineEndpoint, a_key) == again &&
            !convert(CurrentCategory::LineEndpoint, a_key).second,
            "current endpoint owner survives shared-history eviction and stays an exact hit");
    const auto stable_builds = builds;
    bool failed = false;
    try {
        working_cached_conversion(current, working, CurrentCategory::LineEndpoint, history, "line-endpoint:failed",
            []() -> Ptr { throw std::runtime_error("endpoint pack failure"); }, bytes, graph, 2, 1024);
    } catch (const std::runtime_error&) { failed = true; }
    require(failed && builds == stable_builds && current.find(CurrentCategory::LineEndpoint, a_key) == again,
            "failed endpoint builder preserves previously current owner");

    std::unordered_set<const void*> loss_owners;
    auto lose = [&](const Ptr& record, auto&& self) -> void {
        if (!record || !loss_owners.insert(record.get()).second) return;
        record->gpu = false; self(record->child, self);
    };
    current.for_each([&](auto, const auto&, const Ptr& record) { lose(record,lose); });
    working.for_each([&](auto, const auto&, const Ptr& record) { lose(record,lose); });
    require(!again->gpu && !convert(CurrentCategory::LineEndpoint, a_key).second && builds == stable_builds,
            "loss visits deduplicated cached endpoint owners while immutable CPU input remains reusable");
    current.clear(CurrentCategory::LineEndpoint); working.clear(CurrentCategory::LineEndpoint);
    discard_category(history, "line-endpoint:");
    require(current.find(CurrentCategory::Vertex, "vertex:shared-budget") == ordinary,
            "endpoint invalidation leaves unrelated ordinary current owners intact");
    again.reset();
    require(weak_a.expired(), "deleted endpoint input releases after last current/Ticket owner without retaining sources");

    CurrentConversions<Ptr> small_current;
    OversizedConversions<Ptr> small_working;
    std::unordered_map<std::string,Ptr> small_history;
    for (size_t n = 0; n < 3; ++n) {
        const auto identity = n == 1 ? a_key : "ordinary:" + std::to_string(n);
        const auto category = n == 1 ? CurrentCategory::LineEndpoint : CurrentCategory::Vertex;
        working_cached_conversion(small_current, small_working, category, small_history, identity,
            [&] { return make(16); }, bytes, graph, 2, 4096);
    }
    require(small_history.size() == 2 && small_working.size() == 0 &&
            small_current.find(CurrentCategory::LineEndpoint, a_key),
            "small endpoint and ordinary conversions share the historical entry budget, with current survival");
    CurrentConversions<Ptr> huge_current;
    OversizedConversions<Ptr> huge_working(8, 1024);
    std::unordered_map<std::string,Ptr> huge_history;
    auto huge = working_cached_conversion(huge_current, huge_working, CurrentCategory::LineEndpoint,
        huge_history, a_key, [&] { return make(2048); }, bytes, graph, 2, 512).first;
    std::weak_ptr<InputRecord> huge_owner = huge;
    huge.reset();
    bool called = false;
    auto [huge_again, huge_cold] = working_cached_conversion(huge_current, huge_working,
        CurrentCategory::LineEndpoint, huge_history, a_key,
        [&] { called = true; return make(2048); }, bytes, graph, 2, 512);
    require(!called && !huge_cold && huge_again == huge_owner.lock() &&
            huge_history.empty() && huge_working.size() == 0 && huge_current.size() == 1,
            "above both history budgets endpoint input survives only in its bounded current slot after Tickets retire");
    huge_current.clear(); huge_again.reset();
    require(huge_owner.expired(), "clearing the current endpoint slot releases non-admitted oversized input");
    auto child = make(500), parent_a = make(16), parent_b = make(16);
    parent_a->child = child; parent_b->child = child;
    OversizedConversions<Ptr> measured(2, 10000);
    require(measured.admit(CurrentCategory::LineEndpoint, a_key, parent_a, graph) &&
            measured.admit(CurrentCategory::Vertex, b_key, parent_b, graph),
            "endpoint and ordinary children enter one graph-accounted working cache");
    const uint64_t shared_bytes = measured.storage_bytes(graph);
    std::unordered_set<const void*> shared;
    const uint64_t graph_bytes = graph(parent_a, shared) + graph(parent_b, shared);
    uint64_t key_bytes = 0;
    measured.for_each([&](auto, const auto& stored_key, const auto&) {
        key_bytes += OversizedConversions<Ptr>::entry_bytes(stored_key);
    });
    require(shared.size() == 3 && shared_bytes == graph_bytes + key_bytes,
            "shared child is not charged separately for each category");
    OversizedConversions<Ptr> boundary_cache(2, shared_bytes);
    require(boundary_cache.admit(CurrentCategory::LineEndpoint, a_key, parent_a, graph) &&
            boundary_cache.admit(CurrentCategory::Vertex, b_key, parent_b, graph) &&
            boundary_cache.storage_bytes(graph) == shared_bytes,
            "cross-category endpoint graph children are charged once at the exact shared byte boundary");
    const auto before = boundary_cache.size();
    require(!boundary_cache.admit(CurrentCategory::LineEndpoint, "line-endpoint:overflow", make(1),
            [](const Ptr&,std::unordered_set<const void*>&) { return UINT64_MAX; }) &&
            boundary_cache.size() == before,
            "overflowing endpoint graph footprint rejects without evicting resident owners");
}

// Storage-access regression begins.
struct BufferAccess {
    uint32_t variable = 0, block = 0;
    bool located = false, non_readable = false, non_writable = false;
    size_t stores = 0, value_loads = 0;
    std::unordered_set<uint32_t> types, pointers;

    bool output_ok() const { return located && !non_readable && !non_writable && stores && !value_loads; }
    bool input_ok() const { return located && !non_readable && non_writable; }
};

// Inspect the actual bound variable and its entire block/row type graph, rather
// than banning decorations on unrelated images or relying on source spelling.
BufferAccess buffer_access(const std::vector<uint32_t>& words, uint32_t binding) {
    const SpvTrace trace(words);
    BufferAccess result;
    std::unordered_map<uint32_t, uint32_t> bindings, sets, variable_types;
    std::unordered_map<uint32_t, std::vector<uint32_t>> children, decorations;
    for (const auto& instruction : trace.code) {
        const auto& a = instruction.args;
        if (instruction.op == spv::Op::OpDecorate && a.size() >= 2) {
            decorations[a[0]].push_back(a[1]);
            if (a[1] == uint32_t(spv::Decoration::Binding)) bindings[a[0]] = a.at(2);
            if (a[1] == uint32_t(spv::Decoration::DescriptorSet)) sets[a[0]] = a.at(2);
        }
        if (instruction.op == spv::Op::OpMemberDecorate && a.size() >= 3)
            decorations[a[0]].push_back(a[2]);
        if (instruction.op == spv::Op::OpVariable && a.size() >= 3 &&
                (a[2] == uint32_t(spv::StorageClass::StorageBuffer) || a[2] == uint32_t(spv::StorageClass::Uniform)))
            variable_types[a[1]] = a[0];
        if (instruction.op == spv::Op::OpTypePointer) children[a[0]] = {a.at(2)};
        if (instruction.op == spv::Op::OpTypeStruct) children[a[0]] = std::vector<uint32_t>(a.begin()+1,a.end());
        if (instruction.op == spv::Op::OpTypeArray || instruction.op == spv::Op::OpTypeRuntimeArray ||
                instruction.op == spv::Op::OpTypeMatrix || instruction.op == spv::Op::OpTypeVector)
            children[a[0]] = {a.at(1)};
    }
    // Decoration groups are legal SPIR-V too. Resolve them before deciding
    // whether an access restriction belongs to this particular binding.
    for (const auto& instruction : trace.code) {
        const auto& a = instruction.args;
        if (instruction.op == spv::Op::OpGroupDecorate || instruction.op == spv::Op::OpGroupMemberDecorate) {
            const auto group = decorations[a[0]];
            const size_t step = instruction.op == spv::Op::OpGroupMemberDecorate ? 2 : 1;
            for (size_t n = 1; n < a.size(); n += step)
                decorations[a[n]].insert(decorations[a[n]].end(),group.begin(),group.end());
        }
    }
    for (const auto& [variable,type] : variable_types) {
        const auto found_binding = bindings.find(variable), found_set = sets.find(variable);
        if (found_binding == bindings.end() || found_set == sets.end() || found_binding->second != binding || found_set->second != 0) continue;
        if (result.located) { result.located = false; return result; }
        result.located = true; result.variable = variable; result.pointers.insert(variable);
        if (!children.contains(type) || children.at(type).size() != 1) { result.located = false; return result; }
        result.block = children.at(type).front();
        std::vector<uint32_t> pending{type};
        while (!pending.empty()) {
            const auto next = pending.back(); pending.pop_back();
            if (!result.types.insert(next).second) continue;
            if (children.contains(next)) pending.insert(pending.end(),children.at(next).begin(),children.at(next).end());
        }
    }
    if (!result.located) return result;
    auto inspect = [&](uint32_t id) {
        for (const auto decoration : decorations[id]) {
            result.non_readable |= decoration == uint32_t(spv::Decoration::NonReadable);
            result.non_writable |= decoration == uint32_t(spv::Decoration::NonWritable);
        }
    };
    inspect(result.variable);
    for (const auto type : result.types) inspect(type);
    bool changed = true;
    while (changed) {
        changed = false;
        for (const auto& instruction : trace.code) {
            const auto& a = instruction.args;
            if ((instruction.op == spv::Op::OpAccessChain || instruction.op == spv::Op::OpInBoundsAccessChain ||
                    instruction.op == spv::Op::OpPtrAccessChain || instruction.op == spv::Op::OpInBoundsPtrAccessChain ||
                    instruction.op == spv::Op::OpCopyObject) && result.pointers.contains(a.at(2)))
                changed |= result.pointers.insert(a.at(1)).second;
        }
    }
    for (const auto& instruction : trace.code) {
        const auto& a = instruction.args;
        if (instruction.op == spv::Op::OpStore && result.pointers.contains(a.at(0))) ++result.stores;
        if ((instruction.op == spv::Op::OpLoad || instruction.op == spv::Op::OpAtomicLoad) &&
                result.pointers.contains(a.at(2))) ++result.value_loads;
        if ((instruction.op == spv::Op::OpCopyMemory || instruction.op == spv::Op::OpCopyMemorySized) &&
                result.pointers.contains(a.at(1))) ++result.value_loads;
    }
    return result;
}

std::vector<uint32_t> add_access_decoration(const std::vector<uint32_t>& words, uint32_t target,
                                         spv::Decoration decoration, bool member = false) {
    const SpvTrace trace(words);
    size_t position = words.size();
    for (const auto& instruction : trace.code) if (instruction.op == spv::Op::OpTypeVoid) {
        position = instruction.offset; break;
    }
    require(position != words.size(), "compiled type section locates legal decoration insertion");
    auto mutated = words;
    const std::vector<uint32_t> addition = member ?
        std::vector<uint32_t>{(4u<<16)|uint32_t(spv::Op::OpMemberDecorate),target,0,uint32_t(decoration)} :
        std::vector<uint32_t>{(3u<<16)|uint32_t(spv::Op::OpDecorate),target,uint32_t(decoration)};
    mutated.insert(mutated.begin()+position,addition.begin(),addition.end());
    return mutated;
}

void storage_access_matches_dawn_binding() {
    auto value = evaluator("attribute vec2 p;varying vec4 color;void main(){gl_Position=vec4(p,0,1);color=vec4(1);}");
    const auto output = buffer_access(value->spv,value->output_binding);
    require(output.output_ok() && output.stores >= value->outputs.size()+1,
            "actual output binding is read-write storage with clip/varying stores and no value loads");
    require(buffer_access(value->spv,value->input_binding).input_ok(),
            "actual input binding remains NonWritable/read-only storage");
    require(value->identity.find("output-access=read-write-storage") != std::string::npos,
            "Dawn-compatible output access is explicit in evaluator policy identity");
    auto old_identity = value->identity;
    old_identity.replace(old_identity.find("isolated-main-once-v3"),std::string("isolated-main-once-v3").size(),"isolated-main-once-v2");
    old_identity.erase(old_identity.find("output-access=read-write-storage;"),std::string("output-access=read-write-storage;").size());
    require(shader_identity_digest(old_identity) != value->cache_key,
            "pre-repair evaluator policy cannot alias the new portable artifact");
    for (const auto access : {spv::Decoration::NonReadable,spv::Decoration::NonWritable}) {
        require(!buffer_access(add_access_decoration(value->spv,output.variable,access),value->output_binding).output_ok(),
                "output variable access restriction is rejected");
        require(!buffer_access(add_access_decoration(value->spv,output.block,access),value->output_binding).output_ok(),
                "output block access restriction is rejected");
        require(!buffer_access(add_access_decoration(value->spv,output.block,access,true),value->output_binding).output_ok(),
                "output block member access restriction is rejected");
    }
    const SpvTrace compiled(value->spv);
    uint32_t row_type = 0;
    for (const auto& instruction : compiled.code) if (instruction.op == spv::Op::OpTypeStruct &&
            instruction.args[0] != output.block && output.types.contains(instruction.args[0])) row_type = instruction.args[0];
    require(row_type, "compiled output row struct belongs to the selected binding graph");
    require(!buffer_access(add_access_decoration(value->spv,row_type,spv::Decoration::NonReadable,true),value->output_binding).output_ok(),
            "nested typed output row member access restriction is rejected");
    auto no_stores = value->spv;
    for (auto instruction = compiled.code.rbegin(); instruction != compiled.code.rend(); ++instruction)
        if (instruction->op == spv::Op::OpStore && output.pointers.contains(instruction->args[0])) {
            const auto length = no_stores[instruction->offset] >> 16;
            no_stores.erase(no_stores.begin()+instruction->offset,no_stores.begin()+instruction->offset+length);
        }
    require(!buffer_access(no_stores,value->output_binding).output_ok(),
            "actual output store removal cannot pass a permission-only check");
    const auto input = buffer_access(value->spv,value->input_binding);
    const auto unrelated = add_access_decoration(value->spv,input.variable,spv::Decoration::NonReadable);
    require(buffer_access(unrelated,value->output_binding).output_ok() &&
            !buffer_access(unrelated,value->input_binding).input_ok(),
            "access checks are binding-specific rather than a module-wide decoration ban");
    auto writable_input_source = value->compute;
    const std::string readonly_input = "readonly buffer VispyLineInputs";
    const auto input_declaration = writable_input_source.find(readonly_input);
    require(input_declaration != std::string::npos, "locate actual input declaration for a compiler counterfactual");
    writable_input_source.erase(input_declaration,std::string("readonly ").size());
    const auto writable_input = compile_vulkan_compute(writable_input_source,ComputeInitializerPolicy::EndpointInputsFirst);
    require(writable_input.ok && !buffer_access(writable_input.compute.words,value->input_binding).input_ok() &&
            buffer_access(writable_input.compute.words,value->output_binding).output_ok(),
            "compiled loss of input NonWritable is rejected without confusing the output binding");
    auto legacy_source = value->compute;
    const auto declaration = legacy_source.find(") buffer VispyLineOutputs");
    require(declaration != std::string::npos, "locate the generated output declaration for a compiler counterfactual");
    legacy_source.insert(declaration+2,"writeonly ");
    const auto legacy = compile_vulkan_compute(legacy_source,ComputeInitializerPolicy::EndpointInputsFirst);
    require(legacy.ok, "legacy writeonly output remains valid Vulkan SPIR-V, independently of Dawn acceptance");
    const auto legacy_output = buffer_access(legacy.compute.words,value->output_binding);
    require(legacy_output.non_readable && legacy_output.stores == output.stores && !legacy_output.value_loads && !legacy_output.output_ok(),
            "compiled old qualifier reproduces NonReadable output while preserving store-only shader behavior");
    SpvStorageLayout repaired_layout, legacy_layout; std::string error;
    require(reflect_storage_rows(value->spv,"VispyLineOutputs",repaired_layout,error) &&
            reflect_storage_rows(legacy.compute.words,"VispyLineOutputs",legacy_layout,error) &&
            repaired_layout.row_stride == legacy_layout.row_stride && repaired_layout.members.size() == legacy_layout.members.size(),
            "output access repair leaves the compiled row ABI unchanged");
    for (size_t n = 0; n < repaired_layout.members.size(); ++n)
        require(repaired_layout.members[n].name == legacy_layout.members[n].name &&
                repaired_layout.members[n].offset == legacy_layout.members[n].offset &&
                repaired_layout.members[n].size == legacy_layout.members[n].size,
                "access change preserves every output member name/offset/size");
    auto load_source = value->compute;
    const std::string assignment = "vispy_line_outputs[vispy_line_row].clip_position = vispy_line_clip_position;";
    const auto store = load_source.find(assignment);
    require(store != std::string::npos, "locate an actual output store for a load counterfactual");
    load_source.replace(store,assignment.size(),
        "vispy_line_outputs[vispy_line_row].clip_position = vispy_line_clip_position + vispy_line_outputs[vispy_line_row].clip_position;");
    const auto loading = compile_vulkan_compute(load_source,ComputeInitializerPolicy::EndpointInputsFirst);
    require(loading.ok && buffer_access(loading.compute.words,value->output_binding).value_loads &&
            !buffer_access(loading.compute.words,value->output_binding).output_ok(),
            "compiled read-write permission does not hide an accidental output-value load");
    const auto typed = evaluator(
        "attribute vec2 p;varying vec4 color;out mat2 basis[2];flat out uvec2 ids;"
        "void main(){gl_Position=vec4(p,0,1);color=vec4(1);basis[0]=mat2(1);basis[1]=mat2(2);ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID));}",
        "varying vec4 color;in mat2 basis[2];flat in uvec2 ids;void main(){gl_FragColor=color+vec4(basis[0][0]+basis[1][1],vec2(ids));}");
    require(buffer_access(typed->spv,typed->output_binding).output_ok() &&
            buffer_access(typed->spv,typed->input_binding).input_ok(),
            "typed matrix/array/integer output graph obeys the same actual storage access policy");
}
// Storage-access regression ends.

void evaluator_derivative_policy_is_independent() {
    const std::string source = "attribute vec2 p;varying vec4 color;"
        "void main(){gl_Position=vec4(p,0,1);color=vec4(1);}";
    auto strict_parent = build_portable_shader(source, fragment, NormalizeOptions{}, "line-contract-pinned-compiler");
    auto compatible_parent = build_portable_shader(source, fragment, NormalizeOptions{}, "line-contract-pinned-compiler",
        SpirvDerivativeMode::AllowNonUniform);
    require(strict_parent->ok && compatible_parent->ok, strict_parent->error + compatible_parent->error);
    auto strict = build_line_evaluator(strict_parent);
    auto compatible = build_line_evaluator(compatible_parent);
    require(strict->ok && compatible->ok, strict->error + compatible->error);
    require(LineEvaluatorArtifact{}.derivative_mode == SpirvDerivativeMode::Strict &&
            strict->derivative_mode == SpirvDerivativeMode::Strict &&
            compatible->derivative_mode == SpirvDerivativeMode::Strict &&
            compatible->original->derivative_mode == SpirvDerivativeMode::AllowNonUniform,
            "endpoint compute retains independent strict policy despite compatible render provenance");
    require(strict->identity.find(";endpoint-spirv-derivatives=strict-v1;") != std::string::npos &&
            compatible->identity.find(";endpoint-spirv-derivatives=strict-v1;") != std::string::npos &&
            compatible->identity.find(";endpoint-spirv-derivatives=allow-nonuniform-v1;") == std::string::npos,
            "compute identity declares strict ingestion independently from parent render tag");
    require(strict->original == strict_parent && compatible->original == compatible_parent &&
            strict->identity != compatible->identity && strict->cache_key != compatible->cache_key &&
            strict->compute == compatible->compute && strict->spv == compatible->spv,
            "evaluator retains separate parent provenance while emitting the same strict compute shader");
}
} // namespace

int main() {
    try {
        isolated_private_main_and_early_returns();
        original_global_initializers_follow_inputs();
        typed_arrays_matrix_interpolation_and_ids();
        qualified_interpolation_survives_endpoint_compilation();
        bool_uniforms_samplers_and_inactive_inputs();
        dispatch_grants_and_failure_atomicity();
        captured_resource_remapping();
        contextual_unsupported_and_mapped_errors();
        endpoint_input_identity_and_shared_cache();
        storage_access_matches_dawn_binding();
        evaluator_derivative_policy_is_independent();
        std::cout << checks << " line evaluator CPU checks passed\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
