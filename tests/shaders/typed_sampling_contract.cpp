// CPU compiler/reflection proposal. No Dawn device or graphics execution.
#include "shader/artifact.hpp"
#include <SPIRV/spirv.hpp11>

#include <algorithm>
#include <iostream>
#include <map>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace {
size_t checks = 0;
void require(bool value, const std::string& message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
const std::string vertex = "in vec2 a_position;void main(){gl_Position=vec4(a_position,0,1);}";

std::string byte_fragment(bool signed_words, bool helper = false) {
    const std::string sampler = signed_words ? "isampler2D" : "usampler2D";
    const std::string vector = signed_words ? "ivec4" : "uvec4";
    std::string source = "uniform " + sampler + " u_words;\n";
    if (helper) source += vector + " read_words(" + sampler + " words,ivec2 p){return texelFetch(words,p,0);}\n";
    source += "void main(){ivec2 p=ivec2(int(gl_FragCoord.x)/4,int(gl_FragCoord.y)/6);";
    const std::string fetch = helper ? "read_words(u_words,p).r" : "texelFetch(u_words,p,0).r";
    source += signed_words ? "int value=" + fetch + ";uint word=uint(value);" : "uint word=" + fetch + ";";
    source += "uvec4 bytes=uvec4(word&255u,(word>>8u)&255u,(word>>16u)&255u,(word>>24u)&255u);"
              "gl_FragColor=vec4(bytes)*(1.0/255.0);}";
    return source;
}

struct Definition { spv::Op op; uint32_t type; std::vector<uint32_t> args; };
void integer_fetch_and_byte_conversion(const std::vector<uint32_t>& words, ShaderScalarType expected) {
    std::unordered_map<uint32_t, ShaderScalarType> scalars;
    std::unordered_map<uint32_t, uint32_t> vectors, constants;
    std::unordered_map<uint32_t, Definition> values;
    std::unordered_map<uint32_t, std::vector<uint32_t>> stores;
    std::vector<uint32_t> fetch_results, float_inputs;
    size_t masks = 0, signed_float_conversions = 0;
    for (size_t at = 5; at < words.size();) {
        const size_t count = words[at] >> 16;
        require(count && count <= words.size() - at, "valid actual SPIR-V instruction extent");
        const auto op = static_cast<spv::Op>(words[at] & 0xffffu);
        const auto* a = words.data() + at + 1;
        if (op == spv::Op::OpTypeInt && count == 4 && a[1] == 32) scalars[a[0]] = a[2] ? ShaderScalarType::Sint : ShaderScalarType::Uint;
        if (op == spv::Op::OpTypeFloat && count == 3 && a[1] == 32) scalars[a[0]] = ShaderScalarType::Float;
        if (op == spv::Op::OpTypeVector && count == 4) vectors[a[0]] = a[1];
        if (op == spv::Op::OpConstant && count == 4) constants[a[1]] = a[2];
        if (op == spv::Op::OpStore && count == 3) stores[a[0]].push_back(a[1]);
        if (op == spv::Op::OpLoad || op == spv::Op::OpCopyObject || op == spv::Op::OpCompositeConstruct ||
            op == spv::Op::OpBitwiseAnd || op == spv::Op::OpImageFetch) {
            require(count >= 4, "typed actual compiler value has result type/id");
            values.emplace(a[1], Definition{op, a[0], {a + 2, a + count - 1}});
        }
        if (op == spv::Op::OpImageFetch) fetch_results.push_back(a[1]);
        if (op == spv::Op::OpConvertUToF) { require(count == 4, "uint-to-float instruction shape"); float_inputs.push_back(a[2]); }
        signed_float_conversions += op == spv::Op::OpConvertSToF;
        masks += op == spv::Op::OpBitwiseAnd;
        at += count;
    }
    require(fetch_results.size() == 1, "actual compiled integer shader has one texture fetch");
    const auto fetch_type = values.at(fetch_results.front()).type;
    require(vectors.contains(fetch_type) && scalars.at(vectors.at(fetch_type)) == expected,
            "OpImageFetch returns the original uint32 or sint32 vector, never float");
    require(float_inputs.size() == 1 && signed_float_conversions == 0 && masks >= 4,
            "only masked byte-vector conversion reaches the float color output");
    auto is_byte = [&](auto&& self, uint32_t id, std::unordered_set<uint32_t>& path) -> bool {
        if (constants.contains(id)) return constants.at(id) <= 255;
        if (!path.insert(id).second || !values.contains(id)) return false;
        const auto& value = values.at(id);
        bool valid = false;
        if (value.op == spv::Op::OpBitwiseAnd && value.args.size() == 2)
            valid = (constants.contains(value.args[0]) && constants.at(value.args[0]) == 255) ||
                    (constants.contains(value.args[1]) && constants.at(value.args[1]) == 255);
        else if (value.op == spv::Op::OpCompositeConstruct)
            valid = std::all_of(value.args.begin(), value.args.end(), [&](uint32_t child) { return self(self, child, path); });
        else if (value.op == spv::Op::OpCopyObject && value.args.size() == 1) valid = self(self, value.args[0], path);
        else if (value.op == spv::Op::OpLoad && value.args.size() == 1 && stores.contains(value.args[0]))
            valid = std::all_of(stores.at(value.args[0]).begin(), stores.at(value.args[0]).end(),
                [&](uint32_t child) { return self(self, child, path); });
        path.erase(id);
        return valid;
    };
    std::unordered_set<uint32_t> path;
    require(is_byte(is_byte, float_inputs.front(), path), "every integer-to-float input is proven byte-masked first");
}

void typed_fetches() {
    for (bool signed_words : {false, true}) for (bool helper : {false, true}) for (bool base : {false, true}) {
        const auto scalar = signed_words ? ShaderScalarType::Sint : ShaderScalarType::Uint;
        const auto fragment = byte_fragment(signed_words, helper);
        auto normalized = normalize_program(vertex, fragment, NormalizeOptions{base});
        require(normalized.error.empty(), normalized.error);
        require(normalized.samplers.size() == 1 && normalized.samplers[0].sample_scalar == scalar &&
                normalized.samplers[0].dim == "2d", "typed sampler declarations retain scalar and dimension metadata");
        require(normalized.fragment.find(signed_words ? "itexture2D" : "utexture2D") != std::string::npos,
                "normalization emits actual typed separate image resources");
        require(normalized.fragment.find("textureLod") == std::string::npos,
                "integer texelFetch is not rewritten by the implicit base-level sampling policy");
        auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment, true);
        require(compiled.ok, compiled.log + "\n" + normalized.fragment);
        integer_fetch_and_byte_conversion(compiled.fragment.words, scalar);
        auto artifact = vispy::shader::build_portable_shader(vertex, fragment, NormalizeOptions{base}, "typed-sampling-candidate");
        require(artifact->ok, artifact->error);
        require(artifact->samplers.size() == 1 && artifact->samplers[0].sample_scalar == scalar &&
                artifact->samplers[0].texture_stage_mask == 2, "portable linked live reflection retains the actual integer resource type");
        std::string error;
        require(reflect_sampler_types(artifact->spv_frag, artifact->samplers, 2, error), error);
        auto broken = artifact->samplers;
        broken[0].sample_scalar = ShaderScalarType::Float;
        require(!reflect_sampler_types(artifact->spv_frag, broken, 2, error) && error.find("sampled scalar differs") != std::string::npos,
                "compiler reflection refuses a float binding description for an actual integer sampled image");
        broken = artifact->samplers; broken[0].dim = "3d";
        require(!reflect_sampler_types(artifact->spv_frag, broken, 2, error), "compiler reflection refuses a wrong texture dimension");
        broken = artifact->samplers; broken[0].texture_binding += 100;
        require(!reflect_sampler_types(artifact->spv_frag, broken, 2, error), "compiler reflection refuses a missing live texture binding");
        auto malformed = artifact->spv_frag; malformed[5] &= 0xffffu;
        require(!reflect_sampler_types(malformed, artifact->samplers, 2, error), "malformed instruction lengths fail reflection before descriptor creation");
    }
}

void stage_and_type_controls() {
    auto lossy = byte_fragment(false);
    const auto conversion = lossy.find("gl_FragColor=vec4(bytes)");
    require(conversion != std::string::npos, "integer-byte fixture has the declared output conversion");
    lossy.replace(conversion, std::string("gl_FragColor=vec4(bytes)").size(), "gl_FragColor=vec4(word)");
    const auto lossy_artifact = vispy::shader::build_portable_shader(vertex, lossy, {}, "typed-lossy-counterfactual");
    require(lossy_artifact->ok, lossy_artifact->error);
    bool rejected_lossy_word = false;
    try { integer_fetch_and_byte_conversion(lossy_artifact->spv_frag, ShaderScalarType::Uint); }
    catch (const std::runtime_error&) { rejected_lossy_word = true; }
    require(rejected_lossy_word, "actual compiler float conversion of the original32-bit sample fails the independent byte-preservation contract");
    const auto shared = vispy::shader::build_portable_shader(
        "uniform usampler2D words;void main(){uint b=texelFetch(words,ivec2(0),0).r&255u;gl_Position=vec4(float(b)/255.0,0,0,1);}",
        "uniform usampler2D words;void main(){uint b=texelFetch(words,ivec2(0),0).r&255u;gl_FragColor=vec4(float(b)/255.0);}", {}, "typed-stage-controls");
    require(shared->ok, shared->error);
    require(shared->samplers.size() == 1 && shared->samplers[0].sample_scalar == ShaderScalarType::Uint &&
            shared->samplers[0].texture_stage_mask == 3, "same typed uniform has independently live vertex and fragment images");
    for (const auto& wrong : {std::string("isampler2D"), std::string("sampler2D")}) {
        auto rejected = normalize_program("uniform usampler2D words;void main(){gl_Position=vec4(0,0,0,1);}",
            "uniform " + wrong + " words;void main(){gl_FragColor=vec4(1);}");
        require(rejected.error.find("stage sampler types differ") != std::string::npos,
                "uniform scalar mismatches across stages are contextual normalization failures");
    }
    auto arrays = normalize_program(vertex, "uniform usampler2D words[2];void main(){gl_FragColor=vec4(1);}");
    require(arrays.error.find("sampler arrays") != std::string::npos, "unsupported typed sampler arrays retain explicit refusal");
    auto output = normalize_program(vertex,
        "uniform isampler2D words;void bad(out isampler2D image){}void main(){bad(words);gl_FragColor=vec4(1);}");
    require(output.error.find("named scalar input") != std::string::npos, "typed opaque output parameters are rejected before compilation");
    const auto mixed = vispy::shader::build_portable_shader(vertex,
        "uniform sampler2D f;uniform usampler2D u;uniform isampler2D s;uniform usampler2D unused;"
        "uvec4 typed(usampler2D image){return texelFetch(image,ivec2(0),0);}"
        "ivec4 typed(isampler2D image){return texelFetch(image,ivec2(0),0);}"
        "void main(){uint b=(typed(u).r&255u)+(uint(typed(s).r)&255u);gl_FragColor=texture2D(f,vec2(.5))+vec4(float(b)/510.0);}",
        NormalizeOptions{true}, "typed-mixed-controls");
    require(mixed->ok, mixed->error);
    require(mixed->samplers.size() == 3 && mixed->samplers[0].sample_scalar == ShaderScalarType::Float &&
            mixed->samplers[1].sample_scalar == ShaderScalarType::Uint && mixed->samplers[2].sample_scalar == ShaderScalarType::Sint,
            "mixed float/unsigned/signed helper overloads retain independent binding scalar types and drop inactive resources");
    const auto floats = vispy::shader::build_portable_shader(vertex,
        "uniform sampler2D f;void main(){gl_FragColor=texture2D(f,vec2(.5));}", {}, "typed-float-control");
    require(floats->ok && floats->samplers.size() == 1 && floats->samplers[0].sample_scalar == ShaderScalarType::Float,
            "ordinary floating sampler behavior and default metadata remain intact");
}
}

int main() {
    try {
        typed_fetches(); stage_and_type_controls();
        std::cout << "typed sampling CPU compiler/reflection checks passed: " << checks
                  << "; no Dawn/Tint WGSL reader, device, runtime or pixel qualification\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
