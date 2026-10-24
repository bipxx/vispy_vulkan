// CPU-only semantic SPIR-V compilation, validation and coordinate dataflow.
#include "shader/artifact.hpp"
#include "shader/integer_sampling.hpp"
#include <SPIRV/spirv.hpp11>
#include <SPIRV/GLSL.std.450.h>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <unordered_map>

using namespace vispy::shader;
namespace {
size_t checks = 0;
void require(bool ok, const std::string& why) { ++checks; if (!ok) throw std::runtime_error(why); }
struct Ins { spv::Op op; std::vector<uint32_t> a; };
std::vector<Ins> decode(const std::vector<uint32_t>& words) {
    std::vector<Ins> out;
    for (size_t at = 5; at < words.size();) {
        auto n = words[at] >> 16;
        require(n && n <= words.size() - at, "actual instruction bounds");
        out.push_back({spv::Op(words[at] & 0xffff), {words.begin() + at + 1, words.begin() + at + n}}); at += n;
    }
    return out;
}
bool sample(spv::Op op) { return op == spv::Op::OpImageSampleImplicitLod || op == spv::Op::OpImageSampleExplicitLod; }
const std::string vertex = "in vec2 a_position;out vec2 v_uv;void main(){v_uv=a_position;gl_Position=vec4(a_position,0,1);}";
std::string fragment(bool sint, bool helper, bool mixed = false) {
    const std::string sampler = sint ? "isampler2D" : "usampler2D", vec = sint ? "ivec4" : "uvec4";
    std::string src = "in vec2 v_uv;uniform " + sampler + " u_words;";
    if (mixed) src += "uniform sampler2D u_float;";
    if (helper) src += vec + " fetch_words(" + sampler + " source,vec2 p){return texture(source,p);}";
    src += "void main(){" + vec + " w=" + (helper ? "fetch_words(u_words,v_uv)" : "texture(u_words,v_uv)") + ";";
    src += "uint word=uint(w.r);uvec4 b=uvec4(word&255u,(word>>8u)&255u,(word>>16u)&255u,(word>>24u)&255u);gl_FragColor=vec4(b)/255.0";
    if (mixed) src += "+texture(u_float,v_uv)*0.01";
    return src + ";}";
}
struct Compiled { NormalizedShader normalized; SpvCompile compiled; };
Compiled compile(bool sint, bool helper, bool base, bool mixed = false) {
    Compiled out;
    out.normalized = normalize_program(vertex, fragment(sint, helper, mixed), NormalizeOptions{base});
    require(out.normalized.error.empty(), out.normalized.error);
    out.compiled = compile_vulkan_glsl(out.normalized.vertex, out.normalized.fragment, true);
    require(out.compiled.ok, out.compiled.log); return out;
}
IntegerSamplePolicy policy(const NormalizedShader& n, bool sint, IntegerWrap s, IntegerWrap t) {
    const auto& sampler = n.samplers[0];
    return {sampler.texture_binding, sampler.sampler_binding, sint ? ShaderScalarType::Sint : ShaderScalarType::Uint, s, t};
}
// Independently evaluate the emitted coordinate SSA, using original coordinate
// result IDs as inputs. Arithmetic dispatch is by actual SPIR-V opcode, not a
// second call to the lowerer's coordinate implementation.
struct Interpreter {
    std::unordered_map<uint32_t, Ins> defs;
    std::unordered_map<uint32_t, std::vector<double>> inputs;
    std::array<int, 2> dimensions;
    explicit Interpreter(const std::vector<uint32_t>& words, std::array<int, 2> dims) : dimensions(dims) {
        for (const auto& i : decode(words)) {
            if (i.op == spv::Op::OpConstant || i.op == spv::Op::OpConstantComposite || i.op == spv::Op::OpCompositeExtract ||
                i.op == spv::Op::OpCompositeConstruct || i.op == spv::Op::OpImageQuerySizeLod || i.op == spv::Op::OpConvertSToF ||
                i.op == spv::Op::OpConvertFToS || i.op == spv::Op::OpFMul || i.op == spv::Op::OpFSub || i.op == spv::Op::OpFMod ||
                i.op == spv::Op::OpFOrdEqual || i.op == spv::Op::OpSelect || i.op == spv::Op::OpISub || i.op == spv::Op::OpExtInst) defs[i.a[1]] = i;
            if (i.op == spv::Op::OpTypeInt || i.op == spv::Op::OpTypeFloat) defs[i.a[0]] = i;
        }
    }
    std::vector<double> eval(uint32_t id) {
        if (inputs.contains(id)) return inputs.at(id);
        require(defs.contains(id), "coordinate graph has no unknown dependency");
        const auto& i = defs.at(id); const auto& a = i.a;
        if (i.op == spv::Op::OpConstant) {
            const bool fp = defs.at(a[0]).op == spv::Op::OpTypeFloat;
            return {fp ? double(std::bit_cast<float>(a[2])) : double(int32_t(a[2]))};
        }
        if (i.op == spv::Op::OpConstantComposite || i.op == spv::Op::OpCompositeConstruct) {
            std::vector<double> out;
            for (size_t p = 2; p < a.size(); ++p) { auto child = eval(a[p]); out.insert(out.end(), child.begin(), child.end()); }
            return out;
        }
        if (i.op == spv::Op::OpCompositeExtract) return {eval(a[2]).at(a[3])};
        if (i.op == spv::Op::OpImageQuerySizeLod) return {double(dimensions[0]), double(dimensions[1])};
        if (i.op == spv::Op::OpConvertSToF || i.op == spv::Op::OpConvertFToS) {
            auto x = eval(a[2]);
            for (auto& v : x) v = i.op == spv::Op::OpConvertSToF ? double(float(v)) : double(int32_t(v));
            return x;
        }
        if (i.op == spv::Op::OpSelect) return eval(a[eval(a[2]).at(0) != 0 ? 3 : 4]);
        if (i.op == spv::Op::OpFMul || i.op == spv::Op::OpFSub || i.op == spv::Op::OpISub || i.op == spv::Op::OpFMod || i.op == spv::Op::OpFOrdEqual) {
            auto x = eval(a[2]), y = eval(a[3]); require(x.size() == y.size(), "vector arity");
            for (size_t p = 0; p < x.size(); ++p) {
                x[p] = i.op == spv::Op::OpFMul ? double(float(x[p]) * float(y[p])) :
                       i.op == spv::Op::OpFSub ? double(float(x[p]) - float(y[p])) :
                       i.op == spv::Op::OpFMod ? double(float(x[p] - y[p] * std::floor(x[p] / y[p]))) :
                       i.op == spv::Op::OpFOrdEqual ? double(x[p] == y[p]) : x[p] - y[p];
            }
            return x;
        }
        if (i.op == spv::Op::OpExtInst) {
            auto x = eval(a[4]);
            if (a[3] == GLSLstd450Floor) for (auto& v : x) v = std::floor(v);
            else if (a[3] == GLSLstd450Fract) for (auto& v : x) v = float(v - std::floor(v));
            else if (a[3] == GLSLstd450FAbs) for (auto& v : x) v = std::abs(v);
            else if (a[3] == GLSLstd450FClamp || a[3] == GLSLstd450SClamp) {
                auto lo = eval(a[5]), hi = eval(a[6]);
                for (size_t p = 0; p < x.size(); ++p) x[p] = std::clamp(x[p], lo[p], hi[p]);
            } else throw std::runtime_error("unexpected coordinate extended instruction");
            return x;
        }
        throw std::runtime_error("unexpected coordinate opcode");
    }
};
// Independent scalar reference: Euclidean unit/length-two intervals, then
// nearest selection by floor. Mirrored internal texel boundaries stay on the
// wrapped coordinate before quantization, including the exact normalized edge.
int oracle(double u, int size, IntegerWrap mode) {
    double wrapped = u;
    if (mode == IntegerWrap::Repeat) { wrapped = std::fmod(u, 1.0); if (wrapped < 0) wrapped += 1.0; }
    if (mode == IntegerWrap::MirroredRepeat) { wrapped = std::fmod(std::abs(u), 2.0); if (wrapped > 1) wrapped = 2 - wrapped; }
    return int(std::clamp<int64_t>(int64_t(std::floor(wrapped * size)), 0, size - 1));
}
void coordinates_and_types() {
    const std::array<IntegerWrap, 3> modes{IntegerWrap::ClampToEdge, IntegerWrap::Repeat, IntegerWrap::MirroredRepeat};
    // Avoid exactly mirrored texel boundaries except normalized integer edges,
    // where the explicit last-texel clamp is the defined edge treatment.
    const std::array<float, 14> coordinates{-8.125f, -2.0f, -1.875f, -1.0f, -.3125f, -.03125f,
                                           0.0f, .03125f, .3125f, .96875f, 1.0f, 1.125f, 2.0f, 8.125f};
    for (bool sint : {false, true}) for (bool helper : {false, true}) for (bool base : {false, true}) {
        const auto c = compile(sint, helper, base);
        const auto original = decode(c.compiled.fragment.words);
        std::vector<Ins> old_samples;
        for (const auto& i : original) if (sample(i.op)) old_samples.push_back(i);
        require(old_samples.size() == 1, "one real integer sample even through opaque helper");
        const auto original_words = c.compiled.fragment.words;
        for (const auto s : modes) for (const auto t : modes) {
            const auto p = policy(c.normalized, sint, s, t);
            const auto lowered = lower_integer_nearest_2d(original_words, {p});
            require(lowered.ok, lowered.error);
            require(original_words == c.compiled.fragment.words, "input compiler module is immutable");
            require(lowered.samples_lowered == 1 && lowered.texture_bindings == std::vector<uint32_t>{p.texture_binding}, "exact sample count and original binding");
            std::vector<Ins> fetches; size_t queries = 0, samples = 0;
            for (const auto& i : decode(lowered.words)) {
                if (i.op == spv::Op::OpImageFetch) fetches.push_back(i);
                queries += i.op == spv::Op::OpImageQuerySizeLod; samples += sample(i.op);
            }
            require(fetches.size() == 1 && queries == 1 && samples == 0, "integer sample is query+fetch without unsupported sample op");
            require(fetches[0].a[0] == old_samples[0].a[0] && fetches[0].a[1] == old_samples[0].a[1], "fetch preserves integer result type/id and all original byte consumers");
            std::string error;
            require(reflect_sampler_types(lowered.words, c.normalized.samplers, 2, error), error);
            for (const auto dims : {std::array<int, 2>{8, 4}, std::array<int, 2>{1, 1}, std::array<int, 2>{7, 5}}) {
                Interpreter eval(lowered.words, dims);
                for (float x : coordinates) for (float y : coordinates) {
                    eval.inputs[old_samples[0].a[3]] = {x, y};
                    const auto got = eval.eval(fetches[0].a[3]);
                    require(got.size() == 2 && int(got[0]) == oracle(x, dims[0], s) && int(got[1]) == oracle(y, dims[1], t),
                            "actual emitted coordinate SSA selects the independent signed texel lattice");
                }
            }
        }
    }
}
void compatibility_and_rejections() {
    auto c = compile(false, false, true, true);
    auto p = policy(c.normalized, false, IntegerWrap::Repeat, IntegerWrap::ClampToEdge);
    auto lowered = lower_integer_nearest_2d(c.compiled.fragment.words, {p});
    require(lowered.ok, lowered.error);
    std::vector<Ins> original_float, lowered_float;
    std::map<uint32_t, spv::Op> types;
    for (const auto& i : decode(c.compiled.fragment.words)) if (i.op == spv::Op::OpTypeFloat || i.op == spv::Op::OpTypeInt || i.op == spv::Op::OpTypeVector) types[i.a[0]] = i.op;
    for (const auto& i : decode(c.compiled.fragment.words)) if (sample(i.op) && i.a[0] != 0) {
        bool integer = false;
        for (const auto& d : decode(c.compiled.fragment.words)) if (d.op == spv::Op::OpTypeVector && d.a[0] == i.a[0]) integer = types.at(d.a[1]) == spv::Op::OpTypeInt;
        if (!integer) original_float.push_back(i);
    }
    for (const auto& i : decode(lowered.words)) if (sample(i.op)) lowered_float.push_back(i);
    require(original_float.size() == 1 && lowered_float.size() == 1 && original_float[0].op == lowered_float[0].op && original_float[0].a == lowered_float[0].a, "mixed float sampling instruction and operands are byte-exact");
    auto fetch = normalize_program(vertex, "uniform usampler2D words;void main(){gl_FragColor=vec4(texelFetch(words,ivec2(0),0)&255u)/255.0;}");
    require(fetch.error.empty(), fetch.error);
    auto compiled_fetch = compile_vulkan_glsl(fetch.vertex, fetch.fragment);
    require(compiled_fetch.ok, compiled_fetch.log);
    auto untouched = lower_integer_nearest_2d(compiled_fetch.fragment.words, {});
    require(untouched.ok && untouched.words == compiled_fetch.fragment.words && untouched.samples_lowered == 0, "existing integer texelFetch entire module remains byte-exact");
    auto float_norm = normalize_program(vertex, "in vec2 v_uv;uniform sampler2D f;void main(){gl_FragColor=texture(f,v_uv);}", NormalizeOptions{true});
    auto floats = compile_vulkan_glsl(float_norm.vertex, float_norm.fragment);
    require(floats.ok, floats.log);
    untouched = lower_integer_nearest_2d(floats.fragment.words, {});
    require(untouched.ok && untouched.words == floats.fragment.words, "float-only entire module remains byte-exact");
    auto reject = [&](const std::vector<IntegerSamplePolicy>& policies, const std::string& detail) {
        auto r = lower_integer_nearest_2d(c.compiled.fragment.words, policies);
        require(!r.ok && r.words.empty() && !r.error.empty(), detail + " refuses before publishing words");
    };
    reject({}, "missing actual sampler state");
    auto bad = p; bad.nearest = false; reject({bad}, "linear filtering");
    bad = p; bad.base_level_only = false; reject({bad}, "mip state");
    bad = p; bad.s = IntegerWrap(99); reject({bad}, "unknown wrap");
    bad = p; bad.scalar = ShaderScalarType::Sint; reject({bad}, "scalar mismatch");
    bad = p; ++bad.sampler_binding; reject({bad}, "sampler pair mismatch");
    reject({p, p}, "duplicate policy");
    auto malformed = c.compiled.fragment.words; malformed[0] = 0;
    auto r = lower_integer_nearest_2d(malformed, {p}); require(!r.ok && r.words.empty(), "malformed SPIR-V rejected");
    auto lod = normalize_program(vertex, "in vec2 v_uv;uniform usampler2D words;void main(){gl_FragColor=vec4(textureLod(words,v_uv,1.0)&255u)/255.0;}");
    auto compiled_lod = compile_vulkan_glsl(lod.vertex, lod.fragment);
    require(compiled_lod.ok, compiled_lod.log);
    r = lower_integer_nearest_2d(compiled_lod.fragment.words, {policy(lod, false, p.s, p.t)});
    require(r.ok && r.samples_lowered == 1, "actual one-level nearest policy admits nonzero explicit LOD");
    auto without_one_level = policy(lod, false, p.s, p.t); without_one_level.base_level_only = false;
    auto refused_level = lower_integer_nearest_2d(compiled_lod.fragment.words, {without_one_level});
    require(!refused_level.ok && refused_level.words.empty(), "nonzero LOD cannot bypass the actual one-level policy");
    auto evaluated = normalize_program(vertex,
        "in vec2 v_uv;uniform usampler2D words;float counter=0.;"
        "float next_level(){counter+=1.;return 2.;}vec2 next_dx(){counter+=2.;return vec2(.25,0);}"
        "vec2 next_dy(){counter+=3.;return vec2(0,.25);}void main(){"
        "uvec4 a=textureLod(words,v_uv,next_level());uvec4 b=textureGrad(words,v_uv,next_dx(),next_dy());"
        "gl_FragColor=vec4(float((a.r+b.r)&255u)/255.,counter*.125,0,1);}");
    require(evaluated.error.empty(), evaluated.error);
    auto evaluated_compiled=compile_vulkan_glsl(evaluated.vertex,evaluated.fragment);
    require(evaluated_compiled.ok,evaluated_compiled.log);
    auto lowered_evaluation=lower_integer_nearest_2d(evaluated_compiled.fragment.words,
        {policy(evaluated,false,p.s,p.t)});
    require(lowered_evaluation.ok && lowered_evaluation.samples_lowered==2,lowered_evaluation.error);
    const auto before_code=decode(evaluated_compiled.fragment.words),after_code=decode(lowered_evaluation.words);
    size_t calls=0;
    for(const auto& instruction:before_code) {
        if(instruction.op!=spv::Op::OpFunctionCall && instruction.op!=spv::Op::OpStore)continue;
        calls+=instruction.op==spv::Op::OpFunctionCall;
        require(std::any_of(after_code.begin(),after_code.end(),[&](const auto& actual){
            return actual.op==instruction.op && actual.a==instruction.a;
        }),"integer one-level lowering preserves actual operand calls and private stores");
    }
    require(calls>=3,"finite LOD/gradient side-effect fixture has real compiled helper calls");
    auto identity = integer_sample_policy_identity({p}); require(!identity.empty(), "explicit policy identity");
    bad = p; bad.t = IntegerWrap::MirroredRepeat;
    require(identity != integer_sample_policy_identity({bad}), "wrap specialization changes cache identity");
    bad = p; bad.scalar = ShaderScalarType::Sint;
    require(identity != integer_sample_policy_identity({bad}), "scalar specialization changes cache identity");
    bad = p; bad.texture_binding += 4; bad.sampler_binding += 4;
    require(integer_sample_policy_identity({p, bad}) == integer_sample_policy_identity({bad, p}), "policy ordering does not change identity");
    require(integer_sample_policy_identity({p, p}).empty(), "invalid policy cannot create a cache key");
}
}
int main() {
    try { coordinates_and_types(); compatibility_and_rejections(); std::cout << "integer sampling semantic CPU checks passed: " << checks << '\n'; return 0; }
    catch (const std::exception& error) { std::cerr << "integer sampling contract: " << error.what() << '\n'; return 1; }
}
