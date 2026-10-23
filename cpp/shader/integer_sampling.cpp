#include "shader/integer_sampling.hpp"
#include <SPIRV/spirv.hpp11>
#include <SPIRV/GLSL.std.450.h>
#include <spirv-tools/libspirv.h>
#include <algorithm>
#include <cstring>
#include <limits>
#include <map>
#include <set>
#include <unordered_map>

namespace vispy::shader {
namespace {
using Words = std::vector<uint32_t>;
struct Inst { spv::Op op; Words a; };
void emit(Words& out, spv::Op op, std::initializer_list<uint32_t> operands) {
    out.push_back((uint32_t(operands.size() + 1) << 16) | uint32_t(op));
    out.insert(out.end(), operands.begin(), operands.end());
}
bool validate(const Words& words, std::string& error) {
    auto context = spvContextCreate(SPV_ENV_VULKAN_1_2);
    spv_const_binary_t binary{words.data(), words.size()};
    spv_diagnostic diagnostic = nullptr;
    const auto status = spvValidate(context, &binary, &diagnostic);
    if (status != SPV_SUCCESS) error = diagnostic && diagnostic->error ? diagnostic->error : "SPIR-V validation failed";
    spvDiagnosticDestroy(diagnostic); spvContextDestroy(context);
    return status == SPV_SUCCESS;
}
bool valid_wrap(IntegerWrap wrap) { return uint32_t(wrap) <= uint32_t(IntegerWrap::MirroredRepeat); }
bool policies_valid(const std::vector<IntegerSamplePolicy>& policies) {
    std::set<uint32_t> textures, samplers;
    for (const auto& p : policies) {
        if (!p.nearest || !p.base_level_only || !valid_wrap(p.s) || !valid_wrap(p.t) ||
            (p.scalar != ShaderScalarType::Sint && p.scalar != ShaderScalarType::Uint) ||
            p.texture_binding == p.sampler_binding || !textures.insert(p.texture_binding).second ||
            !samplers.insert(p.sampler_binding).second) return false;
    }
    return true;
}
}

std::string integer_sample_policy_identity(const std::vector<IntegerSamplePolicy>& policies) {
    if (!policies_valid(policies)) return {};
    auto ordered = policies;
    std::sort(ordered.begin(), ordered.end(), [](const auto& a, const auto& b) { return a.texture_binding < b.texture_binding; });
    std::string identity = "integer-nearest-2d=spirv-query-fetch-wrap-parity-v3;set=0;finite-f32;single-level-lod-grad;";
    for (const auto& p : ordered) {
        identity += std::to_string(p.texture_binding) + ',' + std::to_string(p.sampler_binding) + ',' +
                    std::to_string(uint32_t(p.scalar)) + ',' + std::to_string(uint32_t(p.s)) + ',' +
                    std::to_string(uint32_t(p.t)) + ",nearest=1,base-only=1;";
    }
    return identity;
}

static IntegerSampleLowering lower_impl(const Words& input, const std::vector<IntegerSamplePolicy>& policies,
                                       IntegerSampleBindings* inspection) {
    IntegerSampleLowering out;
    auto fail = [&](const std::string& why) { out.error = "integer nearest 2D lowering: " + why; return out; };
    if (!policies_valid(policies)) return fail("invalid or duplicate immutable policy");
    std::string validation;
    if (!validate(input, validation)) return fail("invalid input: " + validation);
    std::vector<Inst> instructions;
    std::unordered_map<uint32_t, Inst> defs;
    std::unordered_map<uint32_t, uint32_t> bindings, sets;
    uint32_t glsl = 0, int_type = 0, float_type = 0, bool_type = 0, ivec2 = 0, fvec2 = 0;
    bool query_capability = false;
    for (size_t at = 5; at < input.size();) {
        const uint32_t count = input[at] >> 16;
        if (!count || count > input.size() - at) return fail("truncated instruction");
        Inst inst{spv::Op(input[at] & 0xffff), Words(input.begin() + at + 1, input.begin() + at + count)};
        const auto& a = inst.a;
        if (inst.op == spv::Op::OpCapability && a[0] == uint32_t(spv::Capability::ImageQuery)) query_capability = true;
        if (inst.op == spv::Op::OpExtInstImport && a.size() >= 2 &&
            std::string(reinterpret_cast<const char*>(a.data() + 1)) == "GLSL.std.450") glsl = a[0];
        if (inst.op == spv::Op::OpDecorate && a.size() == 3) {
            if (a[1] == uint32_t(spv::Decoration::Binding)) bindings[a[0]] = a[2];
            if (a[1] == uint32_t(spv::Decoration::DescriptorSet)) sets[a[0]] = a[2];
        }
        if (inst.op >= spv::Op::OpTypeVoid && inst.op <= spv::Op::OpTypePointer && !a.empty()) defs[a[0]] = inst;
        if (inst.op == spv::Op::OpTypeBool) bool_type = a[0];
        if (inst.op == spv::Op::OpTypeInt && a.size() == 3 && a[1] == 32 && a[2] == 1) int_type = a[0];
        if (inst.op == spv::Op::OpTypeFloat && a.size() == 2 && a[1] == 32) float_type = a[0];
        if ((inst.op == spv::Op::OpLoad || inst.op == spv::Op::OpCopyObject || inst.op == spv::Op::OpSampledImage ||
             inst.op == spv::Op::OpConstant || inst.op == spv::Op::OpVariable) && a.size() >= 2) defs[a[1]] = inst;
        instructions.push_back(std::move(inst)); at += count;
    }
    for (const auto& inst : instructions) if (inst.op == spv::Op::OpTypeVector && inst.a[2] == 2) {
        if (inst.a[1] == int_type) ivec2 = inst.a[0];
        if (inst.a[1] == float_type) fvec2 = inst.a[0];
    }
    auto definition = [&](uint32_t id) -> const Inst* { auto it = defs.find(id); return it == defs.end() ? nullptr : &it->second; };
    auto resource_binding = [&](uint32_t id, uint32_t& binding) {
        const Inst* def = definition(id);
        std::set<uint32_t> seen;
        while (def && def->op == spv::Op::OpCopyObject && def->a.size() == 3 && seen.insert(id).second) {
            id = def->a[2]; def = definition(id);
        }
        if (!def || def->op != spv::Op::OpLoad || def->a.size() != 3) return false;
        const auto variable = def->a[2];
        const auto* v = definition(variable);
        if (!v || v->op != spv::Op::OpVariable || !bindings.contains(variable) || !sets.contains(variable) || sets[variable] != 0) return false;
        binding = bindings[variable]; return true;
    };
    uint32_t next = input[3];
    auto fresh = [&]() -> uint32_t { if (next >= 0x3fffffu) return 0; return next++; };
    Words declarations, import;
    auto setup = [&]() {
        if (!bool_type) { bool_type = fresh(); emit(declarations, spv::Op::OpTypeBool, {bool_type}); }
        if (!int_type) { int_type = fresh(); emit(declarations, spv::Op::OpTypeInt, {int_type, 32, 1}); }
        if (!float_type) { float_type = fresh(); emit(declarations, spv::Op::OpTypeFloat, {float_type, 32}); }
        if (!ivec2) { ivec2 = fresh(); emit(declarations, spv::Op::OpTypeVector, {ivec2, int_type, 2}); }
        if (!fvec2) { fvec2 = fresh(); emit(declarations, spv::Op::OpTypeVector, {fvec2, float_type, 2}); }
        if (!glsl) {
            glsl = fresh(); const char name[] = "GLSL.std.450";
            import.resize(2 + (sizeof(name) + 3) / 4);
            import[0] = (uint32_t(import.size()) << 16) | uint32_t(spv::Op::OpExtInstImport); import[1] = glsl;
            std::memcpy(import.data() + 2, name, sizeof(name));
        }
    };
    uint32_t zero_i = 0, one_i2 = 0, zero_i2 = 0, zero_f = 0, one_f = 0, half_f = 0, two_f = 0;
    auto constants = [&]() {
        if (zero_i) return;
        setup(); zero_i = fresh(); emit(declarations, spv::Op::OpConstant, {int_type, zero_i, 0});
        const uint32_t one_i = fresh(); emit(declarations, spv::Op::OpConstant, {int_type, one_i, 1});
        zero_i2 = fresh(); emit(declarations, spv::Op::OpConstantComposite, {ivec2, zero_i2, zero_i, zero_i});
        one_i2 = fresh(); emit(declarations, spv::Op::OpConstantComposite, {ivec2, one_i2, one_i, one_i});
        auto scalar = [&](uint32_t bits) { auto id = fresh(); emit(declarations, spv::Op::OpConstant, {float_type, id, bits}); return id; };
        zero_f = scalar(0); one_f = scalar(0x3f800000); half_f = scalar(0x3f000000); two_f = scalar(0x40000000);
    };
    std::map<size_t, Words> replacements;
    for (size_t n = 0; n < instructions.size(); ++n) {
        const auto& inst = instructions[n];
        const auto& a = inst.a;
        const bool sample = inst.op >= spv::Op::OpImageSampleImplicitLod && inst.op <= spv::Op::OpImageSampleProjDrefExplicitLod;
        if (!sample || a.size() < 4) continue;
        const auto* result_type = definition(a[0]);
        if (!result_type || result_type->op != spv::Op::OpTypeVector || result_type->a.size() != 3) continue;
        const auto* scalar = definition(result_type->a[1]);
        if (!scalar || scalar->op != spv::Op::OpTypeInt) continue;  // Float/depth sampling untouched.
        if (scalar->a.size() != 3 || scalar->a[1] != 32 || result_type->a[2] != 4) return fail("only 32-bit integer vec4 sample results admitted");
        if (inst.op != spv::Op::OpImageSampleImplicitLod && inst.op != spv::Op::OpImageSampleExplicitLod) return fail("projective/depth samples are outside this policy");
        const auto* combined = definition(a[2]);
        if (!combined || combined->op != spv::Op::OpSampledImage || combined->a.size() != 4) return fail("sampled image must be a direct semantic image/sampler pair");
        const auto* image = definition(combined->a[2]);
        const auto* image_type = image && image->a.size() >= 2 ? definition(image->a[0]) : nullptr;
        if (!image_type || image_type->op != spv::Op::OpTypeImage || image_type->a.size() < 8 ||
            image_type->a[2] != uint32_t(spv::Dim::Dim2D) || image_type->a[3] != 0 || image_type->a[4] != 0 ||
            image_type->a[5] != 0 || image_type->a[6] != 1 || image_type->a[1] != result_type->a[1]) return fail("sampled image is not a matching non-depth, non-array, non-MS 2D integer texture");
        uint32_t texture_binding = 0, sampler_binding = 0;
        if (!resource_binding(combined->a[2], texture_binding) || !resource_binding(combined->a[3], sampler_binding)) return fail("integer pair must resolve to direct set-0 resource bindings");
        const auto policy = std::find_if(policies.begin(), policies.end(), [&](const auto& p) { return p.texture_binding == texture_binding; });
        if (!inspection && policy == policies.end()) return fail("integer sampling has no immutable sampler policy");
        if (!inspection && (policy->sampler_binding != sampler_binding || policy->scalar != (scalar->a[2] ? ShaderScalarType::Sint : ShaderScalarType::Uint))) return fail("policy scalar/sampler binding differs from emitted image pair");
        if (inst.op == spv::Op::OpImageSampleImplicitLod) {
            if (a.size() != 4) return fail("implicit sample image operands are unsupported");
        } else {
            const bool lod = a.size() == 6 && a[4] == uint32_t(spv::ImageOperandsMask::Lod);
            const bool gradients = a.size() == 7 && a[4] == uint32_t(spv::ImageOperandsMask::Grad);
            if (!lod && !gradients) return fail("only explicit LOD or gradients are admitted by the one-level nearest policy");
            // The actual captured policy is mandatory for specialization and
            // proves nearest filtering of a single available mip. That makes
            // every finite requested LOD/gradient select mip zero. Preserve all
            // original operand instructions: calls and private writes still
            // execute, even though their returned level/gradient is not fetched.
        }
        if (inspection) {
            IntegerSampleBinding binding{texture_binding, sampler_binding,
                scalar->a[2] ? ShaderScalarType::Sint : ShaderScalarType::Uint, 0};
            if (std::find(inspection->bindings.begin(), inspection->bindings.end(), binding) == inspection->bindings.end())
                inspection->bindings.push_back(binding);
            continue;
        }
        constants();
        Words code;
        auto binary = [&](spv::Op op, uint32_t type, uint32_t x, uint32_t y) { auto id = fresh(); emit(code, op, {type, id, x, y}); return id; };
        auto unary_ext = [&](uint32_t op, uint32_t x) { auto id = fresh(); emit(code, spv::Op::OpExtInst, {float_type, id, glsl, op, x}); return id; };
        auto wrap_axis = [&](uint32_t coordinate, IntegerWrap mode) {
            if (mode == IntegerWrap::Repeat) return unary_ext(GLSLstd450Fract, coordinate);
            if (mode == IntegerWrap::MirroredRepeat) {
                // Mirroring is even in the original coordinate. Preserve its
                // exact magnitude on the first unit interval; do not cancel
                // it through 1-abs(2*fract(u/2)-1) at internal texel boundaries.
                auto magnitude = unary_ext(GLSLstd450FAbs, coordinate);
                auto whole = unary_ext(GLSLstd450Floor, magnitude);
                auto parity = binary(spv::Op::OpFMod, float_type, whole, two_f);
                const auto odd = fresh();
                emit(code, spv::Op::OpFOrdEqual, {bool_type, odd, parity, one_f});
                auto frac = unary_ext(GLSLstd450Fract, magnitude);
                auto reflected = binary(spv::Op::OpFSub, float_type, one_f, frac);
                const auto selected = fresh();
                emit(code, spv::Op::OpSelect, {float_type, selected, odd, reflected, frac});
                return selected;
            }
            auto id = fresh(); emit(code, spv::Op::OpExtInst, {float_type, id, glsl, GLSLstd450FClamp, coordinate, zero_f, one_f}); return id;
        };
        uint32_t axes[2];
        for (uint32_t axis = 0; axis < 2; ++axis) {
            const auto component = fresh(); emit(code, spv::Op::OpCompositeExtract, {float_type, component, a[3], axis});
            axes[axis] = wrap_axis(component, axis ? policy->t : policy->s);
        }
        const auto wrapped = fresh(); emit(code, spv::Op::OpCompositeConstruct, {fvec2, wrapped, axes[0], axes[1]});
        const auto size = fresh(); emit(code, spv::Op::OpImageQuerySizeLod, {ivec2, size, combined->a[2], zero_i});
        const auto float_size = fresh(); emit(code, spv::Op::OpConvertSToF, {fvec2, float_size, size});
        const auto scaled = binary(spv::Op::OpFMul, fvec2, wrapped, float_size);
        const auto floored = fresh(); emit(code, spv::Op::OpExtInst, {fvec2, floored, glsl, GLSLstd450Floor, scaled});
        const auto integer = fresh(); emit(code, spv::Op::OpConvertFToS, {ivec2, integer, floored});
        const auto last = binary(spv::Op::OpISub, ivec2, size, one_i2);
        const auto clamped = fresh(); emit(code, spv::Op::OpExtInst, {ivec2, clamped, glsl, GLSLstd450SClamp, integer, zero_i2, last});
        emit(code, spv::Op::OpImageFetch, {a[0], a[1], combined->a[2], clamped, uint32_t(spv::ImageOperandsMask::Lod), zero_i});
        replacements[n] = std::move(code); ++out.samples_lowered; out.texture_bindings.push_back(texture_binding);
    }
    if (replacements.empty()) { out.words = input; out.ok = true; return out; }
    Words candidate(input.begin(), input.begin() + 5); candidate[3] = next;
    if (!query_capability) emit(candidate, spv::Op::OpCapability, {uint32_t(spv::Capability::ImageQuery)});
    bool declared = false;
    for (size_t n = 0; n < instructions.size(); ++n) {
        const auto& inst = instructions[n];
        if (inst.op == spv::Op::OpMemoryModel) candidate.insert(candidate.end(), import.begin(), import.end());
        if (inst.op == spv::Op::OpFunction && !declared) { candidate.insert(candidate.end(), declarations.begin(), declarations.end()); declared = true; }
        if (const auto it = replacements.find(n); it != replacements.end()) candidate.insert(candidate.end(), it->second.begin(), it->second.end());
        else { candidate.push_back((uint32_t(inst.a.size() + 1) << 16) | uint32_t(inst.op)); candidate.insert(candidate.end(), inst.a.begin(), inst.a.end()); }
    }
    if (!validate(candidate, validation)) return fail("invalid lowered module: " + validation);
    std::sort(out.texture_bindings.begin(), out.texture_bindings.end());
    out.texture_bindings.erase(std::unique(out.texture_bindings.begin(), out.texture_bindings.end()), out.texture_bindings.end());
    out.words = std::move(candidate); out.ok = true; return out;
}

IntegerSampleLowering lower_integer_nearest_2d(const Words& input, const std::vector<IntegerSamplePolicy>& policies) {
    return lower_impl(input, policies, nullptr);
}

IntegerSampleBindings integer_sample_bindings(const Words& input, uint32_t stage_mask) {
    IntegerSampleBindings out;
    if (stage_mask != 0 && stage_mask != 1 && stage_mask != 2 && stage_mask != 4) {
        out.error = "integer sampling inspection: invalid stage mask"; return out;
    }
    auto checked = lower_impl(input, {}, &out);
    if (!checked.ok) { out.bindings.clear(); out.error = checked.error; return out; }
    for (auto& binding : out.bindings) binding.stage_mask = stage_mask;
    std::sort(out.bindings.begin(), out.bindings.end(), [](const auto& a, const auto& b) {
        return a.texture_binding < b.texture_binding;
    });
    out.ok = true; return out;
}
}  // namespace vispy::shader
