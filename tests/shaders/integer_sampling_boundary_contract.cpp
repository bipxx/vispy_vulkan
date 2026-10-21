#define main original_contract_main
#include "integer_sampling_contract.cpp"
#undef main
#include <iomanip>
#include <limits>

namespace {
// Additional opcode interpreter for BOTH old and proposed modules. This file
// is frozen before observing either result and does not invoke a sampler/GPU.
struct BoundaryInterpreter {
    std::unordered_map<uint32_t, Ins> defs;
    std::unordered_map<uint32_t, std::vector<double>> inputs;
    std::array<int, 2> dims;
    BoundaryInterpreter(const std::vector<uint32_t>& words, std::array<int, 2> d) : dims(d) {
        for (const auto& i : decode(words)) {
            if (i.op == spv::Op::OpConstant || i.op == spv::Op::OpConstantComposite || i.op == spv::Op::OpCompositeExtract ||
                i.op == spv::Op::OpCompositeConstruct || i.op == spv::Op::OpImageQuerySizeLod || i.op == spv::Op::OpConvertSToF ||
                i.op == spv::Op::OpConvertFToS || i.op == spv::Op::OpFMul || i.op == spv::Op::OpFSub || i.op == spv::Op::OpFMod ||
                i.op == spv::Op::OpFOrdEqual || i.op == spv::Op::OpSelect || i.op == spv::Op::OpISub || i.op == spv::Op::OpExtInst) defs[i.a[1]] = i;
            if (i.op == spv::Op::OpTypeInt || i.op == spv::Op::OpTypeFloat || i.op == spv::Op::OpTypeBool) defs[i.a[0]] = i;
        }
    }
    std::vector<double> eval(uint32_t id) {
        if (inputs.contains(id)) return inputs.at(id);
        require(defs.contains(id), "boundary coordinate graph dependency");
        const auto& i = defs.at(id); const auto& a = i.a;
        if (i.op == spv::Op::OpConstant) return {defs.at(a[0]).op == spv::Op::OpTypeFloat ? double(std::bit_cast<float>(a[2])) : double(int32_t(a[2]))};
        if (i.op == spv::Op::OpConstantComposite || i.op == spv::Op::OpCompositeConstruct) {
            std::vector<double> result;
            for (size_t n = 2; n < a.size(); ++n) { auto v = eval(a[n]); result.insert(result.end(), v.begin(), v.end()); }
            return result;
        }
        if (i.op == spv::Op::OpCompositeExtract) return {eval(a[2]).at(a[3])};
        if (i.op == spv::Op::OpImageQuerySizeLod) return {double(dims[0]), double(dims[1])};
        if (i.op == spv::Op::OpConvertSToF || i.op == spv::Op::OpConvertFToS) {
            auto x = eval(a[2]); for (auto& v : x) v = i.op == spv::Op::OpConvertSToF ? double(float(v)) : double(int32_t(v)); return x;
        }
        if (i.op == spv::Op::OpSelect) return eval(a[eval(a[2]).at(0) != 0 ? 3 : 4]);
        if (i.op == spv::Op::OpFMul || i.op == spv::Op::OpFSub || i.op == spv::Op::OpISub || i.op == spv::Op::OpFMod || i.op == spv::Op::OpFOrdEqual) {
            auto x = eval(a[2]), y = eval(a[3]); require(x.size() == y.size(), "boundary binary arity");
            for (size_t n = 0; n < x.size(); ++n) {
                if (i.op == spv::Op::OpFMul) x[n] = float(float(x[n]) * float(y[n]));
                else if (i.op == spv::Op::OpFSub) x[n] = float(float(x[n]) - float(y[n]));
                else if (i.op == spv::Op::OpISub) x[n] -= y[n];
                else if (i.op == spv::Op::OpFOrdEqual) x[n] = x[n] == y[n];
                else x[n] = float(x[n] - y[n] * std::floor(x[n] / y[n]));
            }
            return x;
        }
        if (i.op == spv::Op::OpExtInst) {
            auto x = eval(a[4]);
            if (a[3] == GLSLstd450Floor) for (auto& v : x) v = std::floor(v);
            else if (a[3] == GLSLstd450Fract) for (auto& v : x) v = float(v - std::floor(v));
            else if (a[3] == GLSLstd450FAbs) for (auto& v : x) v = std::abs(v);
            else if (a[3] == GLSLstd450FClamp || a[3] == GLSLstd450SClamp) {
                auto lo = eval(a[5]), hi = eval(a[6]); for (size_t n = 0; n < x.size(); ++n) x[n] = std::clamp(x[n], lo[n], hi[n]);
            } else throw std::runtime_error("unexpected boundary extended instruction");
            return x;
        }
        throw std::runtime_error("unexpected boundary opcode");
    }
};
int float_reference(float u, int size, IntegerWrap mode) {
    float wrapped = u;
    if (mode == IntegerWrap::ClampToEdge) wrapped = std::clamp(u, 0.0f, 1.0f);
    if (mode == IntegerWrap::Repeat) { wrapped = std::fmod(u, 1.0f); if (wrapped < 0) wrapped = float(wrapped + 1.0f); }
    if (mode == IntegerWrap::MirroredRepeat) { wrapped = std::fmod(std::abs(u), 2.0f); if (wrapped > 1) wrapped = float(2.0f - wrapped); }
    const float scaled = float(wrapped * float(size));
    return std::clamp(int(std::floor(scaled)), 0, size - 1);
}
std::vector<float> probes(int size) {
    std::set<uint32_t> bits;
    for (int whole = -4; whole <= 4; ++whole) for (int n = 0; n <= size; ++n) {
        const float center = float(float(whole) + float(n) / float(size));
        for (float u : {std::nextafter(center, -std::numeric_limits<float>::infinity()), center,
                        std::nextafter(center, std::numeric_limits<float>::infinity())}) bits.insert(std::bit_cast<uint32_t>(u));
    }
    std::vector<float> out; for (auto b : bits) out.push_back(std::bit_cast<float>(b)); return out;
}
int boundary_tests() {
    size_t pairs = 0, mismatches = 0, math_differences = 0, interval_mismatches = 0;
    uint32_t first_bits = 0; int first_size = 0, first_actual = 0, first_expected = 0;
    const std::array<IntegerWrap, 3> modes{IntegerWrap::ClampToEdge, IntegerWrap::Repeat, IntegerWrap::MirroredRepeat};
    int root_got = -1, root_float = -1, root_math = -1;
    for (bool sint : {false, true}) for (bool base : {false, true}) {
        const auto compiled = compile(sint, false, base);
        std::vector<Ins> samples;
        for (const auto& i : decode(compiled.compiled.fragment.words)) if (sample(i.op)) samples.push_back(i);
        require(samples.size() == 1, "one real sample for boundary control");
        for (auto s : modes) for (auto t : modes) {
            auto lowered = lower_integer_nearest_2d(compiled.compiled.fragment.words, {policy(compiled.normalized, sint, s, t)});
            require(lowered.ok, lowered.error);
            uint32_t fetch_coordinate = 0;
            for (const auto& i : decode(lowered.words)) if (i.op == spv::Op::OpImageFetch) fetch_coordinate = i.a[3];
            require(fetch_coordinate != 0, "real lowered fetch coordinate");
            for (auto dims : {std::array<int, 2>{7, 5}, std::array<int, 2>{5, 7}}) {
                BoundaryInterpreter interpreter(lowered.words, dims);
                if (dims[0] == 7 && s == IntegerWrap::MirroredRepeat) {
                    const float u = 1.0f / 7.0f;
                    interpreter.inputs[samples[0].a[3]] = {u, .375f};
                    root_got = int(interpreter.eval(fetch_coordinate)[0]); root_float = float_reference(u, 7, s); root_math = oracle(u, 7, s);
                }
                for (size_t axis = 0; axis < 2; ++axis) for (float u : probes(dims[axis])) {
                    std::array<float, 2> uv{.375f, .375f}; uv[axis] = u;
                    interpreter.inputs[samples[0].a[3]] = {uv[0], uv[1]};
                    const auto got = interpreter.eval(fetch_coordinate); ++pairs;
                    for (size_t k = 0; k < 2; ++k) {
                        const auto mode = k ? t : s;
                        const int expected = float_reference(uv[k], dims[k], mode);
                        math_differences += expected != oracle(uv[k], dims[k], mode);
                        if (int(got[k]) != expected) {
                            if (!mismatches) { first_bits = std::bit_cast<uint32_t>(uv[k]); first_size = dims[k]; first_actual = int(got[k]); first_expected = expected; }
                            ++mismatches;
                            if (mode == IntegerWrap::MirroredRepeat && std::abs(uv[k]) < 1.0f) ++interval_mismatches;
                        }
                    }
                }
            }
        }
    }
    std::cout << "{\"scope\":\"actual_emitted_SPIRV_float32_boundary_CPU_only\",\"coordinate_pairs\":" << pairs
              << ",\"semantic_mismatches\":" << mismatches << ",\"mirrored_unit_interval_mismatches\":" << interval_mismatches
              << ",\"float32_vs_exact_math_differences\":" << math_differences
              << ",\"root_counterexample\":{\"u_bits\":" << std::bit_cast<uint32_t>(1.0f / 7.0f) << ",\"size\":7,\"actual\":" << root_got
              << ",\"float32_reference\":" << root_float << ",\"mathematical_reference\":" << root_math << "}"
              << ",\"first_mismatch\":{\"u_bits\":" << first_bits << ",\"size\":" << first_size << ",\"actual\":" << first_actual
              << ",\"expected\":" << first_expected << "},\"GPU_used\":false}\n";
    return mismatches ? 1 : 0;
}
}
int main() {
    try { return boundary_tests(); }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }
}
