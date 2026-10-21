#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include "shader/normalize.hpp"

// The only translation unit that may include glslang TIntermediate types is
// glslang_spv.cpp. Callers see SPIR-V words and a diagnostic string.

struct SpvStage {
    std::vector<uint32_t> words;
    std::string log;
    bool ok = false;
};

struct SpvResourceUsage {
    uint32_t binding = 0;
    uint32_t stage_mask = 0;  // vertex = 1, fragment = 2, compute = 4
};

struct SpvCompile {
    SpvStage vertex;
    SpvStage fragment;
    bool ok = false;
    std::string log;
    uint64_t parse_ns = 0;
    uint64_t link_ns = 0;
    uint64_t spirv_ns = 0;
    uint64_t resource_reflect_ns = 0;
    uint64_t parse_calls = 0;
    uint64_t link_calls = 0;
    uint64_t spirv_stages = 0;
    // Populated when cleanup is requested: original active input locations.
    // Their positions in this sorted vector are the final compact locations.
    std::vector<uint32_t> vertex_input_locations;
    std::vector<SpvResourceUsage> resource_usage;
};

// Compiles Vulkan-flavored GLSL with TShader::parse, TProgram::link, and
// GlslangToSpv. TShader::preprocess is intentionally not called.
SpvCompile compile_vulkan_glsl(const std::string& vertex, const std::string& fragment,
                              bool vertex_input_cleanup = false);

// Conservative ordinary stencil fallback admission over validated FINAL modules.
// It does not inherit the line evaluator's separate shader policy.
std::string ordinary_stencil_replay_error(const std::vector<uint32_t>& vertex,
                                          const std::vector<uint32_t>& fragment);

struct SpvComputeCompile {
    SpvStage compute;
    bool ok = false;
    std::string log;
    std::vector<SpvResourceUsage> resource_usage;
    uint64_t parse_ns = 0, link_ns = 0, spirv_ns = 0, resource_reflect_ns = 0;
    uint64_t parse_calls = 0, link_calls = 0, spirv_stages = 0;
    uint64_t relocated_global_initializers = 0;
};

enum class ComputeInitializerPolicy : uint32_t { Default, EndpointInputsFirst };

// EndpointInputsFirst requires the generated entry's direct reserved marker
// after guarded input decoding. Original initializer aggregates move intact
// to that marker; ordinary compute and render compilation stay unchanged.
SpvComputeCompile compile_vulkan_compute(const std::string& source,
    ComputeInitializerPolicy initializer_policy = ComputeInitializerPolicy::Default);

struct SpvStorageMember {
    std::string name;
    ShaderValueType value_type;
    uint32_t offset = 0, size = 0, array_size = 0, array_stride = 0, matrix_stride = 0;
};

struct SpvStorageLayout {
    std::vector<SpvStorageMember> members;
    uint32_t row_stride = 0;
};

// Reflect a std430 block containing one runtime array of typed row structs.
bool reflect_storage_rows(const std::vector<uint32_t>& words, const std::string& block_name,
                          SpvStorageLayout& layout, std::string& error);

// Reads the emitted SPIR-V block member offsets, array strides, matrix
// strides, dimensions, and orientation. Checks metadata against the actual
// compiler output, then updates it. Call for each stage before GPU creation.
bool reflect_uniform_layout(const std::vector<uint32_t>& words,
                            std::vector<NormUniform>& uniforms,
                            uint32_t& uniform_bytes, std::string& error);

// Check live separate texture bindings against actual emitted OpTypeImage
// scalar/dimension metadata. stage_mask is exactly one render/compute stage.
bool reflect_sampler_types(const std::vector<uint32_t>& words,
                           const std::vector<NormSampler>& samplers,
                           uint32_t stage_mask, std::string& error);

struct SpvSampledStage {
    std::vector<uint32_t> words;
    std::vector<SpvResourceUsage> resource_usage;
    bool ok = false;
    std::string error;
};

// Cleanup semantic sampling specializations, preserving the existing IO
// declarations/locations. Resource masks describe actual ID references in
// reachable emitted functions after DCE, not pre-lowering GLSL reflection.
SpvSampledStage finalize_sampled_stage(const std::vector<uint32_t>& words,
                                     uint32_t stage_mask);

// Exact emitted IO declarations, referenced type/array-length definitions,
// variable/member decorations, and ordered entry-point IO references. Used by
// finalization and exposed for CPU counterfactual interface contracts.
bool same_sampled_stage_io(const std::vector<uint32_t>& before,
                          const std::vector<uint32_t>& after, std::string& error);


namespace vispy::shader {
struct LineConsumerCompile {
    SpvCompile stages;
    uint64_t relocated_fragment_initializers = 0;
};
// Local compiler proposal: same pinned parse/link/emission/opaque-helper policy
// as glslang_spv.cpp, plus explicit linked-fragment initializer placement.
// No live compiler TU or default render/compute behavior is changed.
LineConsumerCompile compile_line_consumer_glsl(const std::string& vertex,
                                               const std::string& fragment);
}
