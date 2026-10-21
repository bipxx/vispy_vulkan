#pragma once

#include "shader/artifact.hpp"

#include <array>
#include <memory>

namespace vispy::shader {

inline constexpr uint32_t kLineEvaluatorAbi = 1;
inline constexpr uint32_t kLineEvaluatorWorkgroup = 64;

struct LineEvaluatorLimits {
    uint64_t max_storage_buffer_binding_size = UINT64_MAX;
    uint64_t max_buffer_size = UINT64_MAX;
    uint32_t max_storage_buffers = 2;
    uint32_t max_bindings = UINT32_MAX;
    uint32_t max_workgroup_size_x = 64;
    uint32_t max_workgroup_invocations = 64;
    uint32_t max_workgroups_x = 65535;
};

struct LineInputField {
    NormAttribute attribute;
    ShaderValueType value_type;
    uint32_t word_offset = 0;  // Relative to row, after exact uint32 IDs.
};

struct LineOutputField {
    NormVarying varying;
    std::string storage_type;
    uint32_t offset = 0, size = 0, array_stride = 0, matrix_stride = 0;
};

struct LineEvaluatorArtifact {
    // Shared immutable provenance; the render artifact has no back-reference.
    std::shared_ptr<const PortableShaderArtifact> original;
    // Compute owns its ingestion policy; render compatibility is provenance
    // on original and must not become an evaluator permission.
    SpirvDerivativeMode derivative_mode = SpirvDerivativeMode::Strict;
    std::string identity, cache_key, compute, log, error;
    std::vector<int> line_map;
    std::vector<uint32_t> spv;
    std::vector<LineInputField> inputs;
    std::vector<LineOutputField> outputs;
    std::vector<NormUniform> uniforms;
    std::vector<NormSampler> samplers;
    uint32_t input_binding = 0, output_binding = 0;
    uint32_t input_row_words = 2, output_row_bytes = 16;
    uint32_t uniform_bytes = 0, uniform_stage_mask = 0;
    uint64_t relocated_global_initializers = 0;
    bool ok = false;
    int mapped_line = 0;
    ShaderBuildTimings timings;
    // This artifact only, excluding the separately deduplicated original.
    size_t storage_bytes() const;
};

std::shared_ptr<const LineEvaluatorArtifact> build_line_evaluator(
    std::shared_ptr<const PortableShaderArtifact> original,
    const LineEvaluatorLimits& limits = {});

struct LineEvaluatorDispatch {
    std::array<uint32_t, 4> input_header{};
    uint64_t input_bytes = 0, output_bytes = 0;
    uint32_t workgroups_x = 0;
};

// Count is selected endpoint rows including original instances. Zero is a
// no-op. Resolving constants/divisors and immutable source rows is runtime's
// responsibility. Validate before allocating or encoding any endpoint work.
bool line_evaluator_dispatch(const LineEvaluatorArtifact& artifact, uint64_t count,
                             const LineEvaluatorLimits& limits,
                             LineEvaluatorDispatch& dispatch, std::string& error);

}  // namespace vispy::shader
