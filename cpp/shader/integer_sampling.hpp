#pragma once

#include "shader/normalize.hpp"
#include <cstdint>
#include <string>
#include <vector>

namespace vispy::shader {

enum class IntegerWrap : uint32_t { ClampToEdge, Repeat, MirroredRepeat };

// A proposed immutable specialization input, NOT inferred from shader text or
// an arbitrary default sampler. Runtime integration must snapshot the actual
// sampler state and include this identity in its portable/pipeline cache key.
struct IntegerSamplePolicy {
    uint32_t texture_binding = 0, sampler_binding = 0;
    ShaderScalarType scalar = ShaderScalarType::Uint;
    IntegerWrap s = IntegerWrap::ClampToEdge, t = IntegerWrap::ClampToEdge;
    bool nearest = true;
    bool base_level_only = true;
};

struct IntegerSampleLowering {
    std::vector<uint32_t> words;
    std::vector<uint32_t> texture_bindings;
    uint32_t samples_lowered = 0;
    bool ok = false;
    std::string error;
};

struct IntegerSampleBinding {
    uint32_t texture_binding = 0, sampler_binding = 0;
    ShaderScalarType scalar = ShaderScalarType::Uint;
    uint32_t stage_mask = 0;
    friend bool operator==(const IntegerSampleBinding&, const IntegerSampleBinding&) = default;
};
struct IntegerSampleBindings {
    std::vector<IntegerSampleBinding> bindings;
    bool ok = false;
    std::string error;
};

// Semantic inspection uses the same validated admission as the lowerer; no
// source matching or guessed bindings. Call after live-code cleanup when the
// caller needs executable resource liveness. stage_mask is 0, 1, 2 or 4.
IntegerSampleBindings integer_sample_bindings(const std::vector<uint32_t>& words,
                                             uint32_t stage_mask = 0);

// Semantic SPIR-V specialization only. Admits 32-bit signed/unsigned non-array,
// non-depth 2D normalized-coordinate samples, direct resource loads, and LOD0
// (or implicit LOD with an explicitly base-level-only policy). Finite float32
// coordinates are required; non-finite sampling has no portable value promise.
// Input is const and output is published only after full Vulkan validation.
// Existing texelFetch and all floating sampling instructions are unchanged.
IntegerSampleLowering lower_integer_nearest_2d(const std::vector<uint32_t>& words,
                                             const std::vector<IntegerSamplePolicy>& policies);

// Versioned, order-independent exact specialization identity, including all
// wrap/scalar/binding/admission fields. Empty means invalid policy metadata.
std::string integer_sample_policy_identity(const std::vector<IntegerSamplePolicy>& policies);

}  // namespace vispy::shader
