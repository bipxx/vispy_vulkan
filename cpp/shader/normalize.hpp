#pragma once

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>

struct NormUniform {
    std::string name;
    std::string type;
    // Semantic GLSL type and physical std140 storage are separate for bools.
    std::string storage_type;
    int array_size = 0;
    uint32_t offset = 0;
    uint32_t size = 0;
    uint32_t component_count = 1;
    uint32_t matrix_columns = 1;
    uint32_t matrix_rows = 1;
    uint32_t matrix_stride = 0;
    uint32_t array_stride = 0;
    bool row_major = false;
    // Ordered GLSL shape; array_size is the flattened leaf count and
    // array_stride is the innermost std140 leaf stride.
    std::vector<uint32_t> array_dimensions;
};

enum class VertexIdentityPolicy : uint32_t { Native, Affine, Indexed, BatchAffine, BatchIndexed };

// Batch geometry retains the existing uint32 affine/indexed storage layout.
// Independent instance blocks carry their original base in .x of a std140
// uvec4; native firstInstance contributes the row offset within that block.
inline constexpr uint32_t kBatchInstanceUniformBytes = 16;
inline constexpr const char* kBatchInstanceAbi = "split-std140-uvec4-x-v1";
inline bool batch_identity_policy(VertexIdentityPolicy policy) {
    return policy == VertexIdentityPolicy::BatchAffine || policy == VertexIdentityPolicy::BatchIndexed;
}
enum class ShaderScalarType : uint32_t { Float, Sint, Uint, Bool };

struct ShaderValueType {
    ShaderScalarType scalar = ShaderScalarType::Float;
    uint32_t columns = 1, rows = 1;
    uint32_t components() const { return columns * rows; }
};

bool shader_value_type(const std::string& type, ShaderValueType& value);

struct NormalizeOptions {
    // Explicit admission for runtime textures with one mip level. Implicit
    // reads may use LOD0; explicit LOD/gradient expressions retain evaluation
    // and the actual sampler's min/mag selection. Bias remains a separate
    // unsupported operation under this admission, never silently discarded.
    bool base_level_sampling = false;
    bool point_sprites = false;
    VertexIdentityPolicy vertex_identity = VertexIdentityPolicy::Native;
    // Internal endpoint evaluator body: typed private globals, original GL
    // clip coordinates and identities; compute entry is generated separately.
    bool line_evaluator = false;
    // Reverse normalized clip Z without changing original clip-plane inclusion.
    bool reverse_depth = false;
};

struct NormSampler {
    std::string name;
    std::string dim;
    uint32_t texture_binding = 0;
    uint32_t sampler_binding = 0;
    // 1 = vertex, 2 = fragment, 4 = compute. Compiler live reflection replaces the
    // normalized declaration defaults, separately for texture and sampler.
    uint32_t texture_stage_mask = 3;
    uint32_t sampler_stage_mask = 3;
    // Sampled texel scalar, independent of filtering and resource liveness.
    // Integer sampled words never use float textures or float carriers.
    ShaderScalarType sample_scalar = ShaderScalarType::Float;
};

struct NormAttribute {
    std::string name;
    std::string type;
    uint32_t location = 0;
};

struct NormVarying {
    std::string name, type, interpolation;
    ShaderValueType value_type;
    uint32_t location = 0;
    int array_size = 0;
    int source_line = 0;
    bool centroid = false, sample = false;
    bool vertex_declared = false, fragment_declared = false;
};

struct NormalizedShader {
    std::string vertex;
    std::string fragment;
    std::vector<int> vertex_line_map;
    std::vector<int> fragment_line_map;
    std::vector<NormUniform> uniforms;
    std::vector<NormSampler> samplers;
    std::vector<NormAttribute> attributes;
    std::vector<NormVarying> varyings;
    uint32_t uniform_bytes = 0;
    uint32_t point_identity_binding = 0;
    uint32_t vertex_identity_binding = 0;
    uint32_t batch_instance_binding = 0;
    uint32_t batch_instance_stage_mask = 0;
    bool has_fragment_depth = false;
    bool has_flat_varyings = false;
    bool point_sprites = false;
    std::string error;
};

// Structured compatibility transform from legacy VisPy GLSL to Vulkan GLSL 450.
// This is not a preprocessor and not a regex substitution chain.
NormalizedShader normalize_program(const std::string& vertex, const std::string& fragment);
NormalizedShader normalize_program(const std::string& vertex, const std::string& fragment,
                                   const NormalizeOptions& options);

// GLIR supplies packed 32-bit components, with matrices in OpenGL column
// order. Destination is the entire UBO, not a pointer to this member. The
// helper applies reflected array/matrix strides and normalizes bool storage.
bool pack_uniform_value(const NormUniform& uniform, const void* source, size_t source_bytes,
                        void* destination, size_t destination_bytes,
                        std::string* error = nullptr);

// Resolve a fully or partially indexed name to its contiguous std140 subview.
// Reject malformed, out-of-range or excess indices without modifying the result.
bool uniform_indexed_view(const NormUniform& uniform, const std::string& name,
                          NormUniform& result, std::string* error = nullptr);
