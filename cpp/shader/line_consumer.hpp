#pragma once

// PROPOSED SOURCE ONLY. No generated consumer, native integration or raster
// coverage is implemented by this header. These types describe the next packet.
#include "shader/line_evaluator.hpp"

#include <algorithm>
#include <limits>
#include <span>
#include <stdexcept>
#include <string_view>

namespace vispy::shader {

inline constexpr uint32_t kLineConsumerAbi = 1;

enum class LineCoveragePolicy { AliasedMajorAxis, SmoothReference };
struct LineConsumerPolicy {
    LineCoveragePolicy coverage = LineCoveragePolicy::AliasedMajorAxis;
    uint32_t sample_count = 1;
    // Exact algorithm/compiler identity; the smooth reference model is OPEN.
    std::string coverage_identity;
};

// Every grant must come from the selected device, rather than these defaults.
struct LineConsumerLimits {
    uint64_t max_storage_binding_bytes = 0, max_buffer_bytes = 0;
    uint64_t max_uniform_binding_bytes = 0;
    uint32_t max_storage_buffers_per_stage = 0, max_bindings_per_group = 0;
    // ABI1 prospective planner limits; generated ABI2 uses the actual
    // Dawn maxInterStageShaderVariables grant below instead.
    uint32_t max_inter_stage_locations = 0, max_inter_stage_components = 0;
    uint32_t max_inter_stage_shader_variables = 0;
};

struct LineOutputLayoutSummary {
    uint32_t row_bytes = 0, inter_stage_locations = 0, inter_stage_components = 0;
};

namespace line_consumer_detail {
inline uint64_t add(uint64_t a, uint64_t b, const char* message) {
    if (b > UINT64_MAX - a) throw std::overflow_error(message);
    return a + b;
}
inline uint64_t multiply(uint64_t a, uint64_t b, const char* message) {
    if (a && b > UINT64_MAX / a) throw std::overflow_error(message);
    return a * b;
}
inline uint64_t align(uint64_t value, uint64_t alignment) {
    return add(value, alignment - 1, "line consumer: layout alignment overflow") & ~(alignment - 1);
}
inline std::string value_name(const ShaderValueType& type) {
    if (!type.rows || type.rows > 4 || !type.columns || type.columns > 4)
        throw std::invalid_argument("line consumer: invalid varying dimensions");
    const char* scalar;
    const char* vector;
    switch (type.scalar) {
        case ShaderScalarType::Float: scalar = "float"; vector = "vec"; break;
        case ShaderScalarType::Sint: scalar = "int"; vector = "ivec"; break;
        case ShaderScalarType::Uint: scalar = "uint"; vector = "uvec"; break;
        case ShaderScalarType::Bool: scalar = "bool"; vector = "bvec"; break;
        default: throw std::invalid_argument("line consumer: invalid varying scalar type");
    }
    if (type.columns == 1) return type.rows == 1 ? scalar : vector + std::to_string(type.rows);
    if (type.scalar != ShaderScalarType::Float)
        throw std::invalid_argument("line consumer: nonfloat matrix varying");
    return "mat" + std::to_string(type.columns) + "x" + std::to_string(type.rows);
}
inline bool type_matches(std::string_view name, const ShaderValueType& type) {
    const auto canonical = value_name(type);
    return name == canonical || (type.columns > 1 && type.columns == type.rows &&
        name == "mat" + std::to_string(type.columns));
}
} // namespace line_consumer_detail

// Pure validation of the evaluator's existing reflected std430 ABI.
// Canonical type-name construction may allocate; no allocation-free promise.
// Borrowed fields must remain valid for this call; no view is retained.
// Bool semantic values use uint/uvec physical storage, never float carriers.
inline LineOutputLayoutSummary validate_line_output_layout(
        uint32_t row_bytes, std::span<const LineOutputField> fields) {
    using namespace line_consumer_detail;
    if (row_bytes < 16 || row_bytes % 16)
        throw std::invalid_argument("line consumer: row stride must include aligned GL clip_position");
    uint64_t cursor = 16, locations = 0, components = 0;
    for (size_t i = 0; i < fields.size(); ++i) {
        const auto& field = fields[i];
        const auto& varying = field.varying;
        if (varying.name.empty() || !varying.vertex_declared || varying.array_size < 0)
            throw std::invalid_argument("line consumer: invalid original varying metadata");
        for (size_t previous = 0; previous < i; ++previous)
            if (fields[previous].varying.name == varying.name)
                throw std::invalid_argument("line consumer: duplicate original varying name");
        if (!type_matches(varying.type, varying.value_type))
            throw std::invalid_argument("line consumer: semantic varying type differs");
        auto physical = varying.value_type;
        if (physical.scalar == ShaderScalarType::Bool) physical.scalar = ShaderScalarType::Uint;
        if (!type_matches(field.storage_type, physical))
            throw std::invalid_argument("line consumer: physical varying type differs");
        if (varying.interpolation != "smooth" && varying.interpolation != "noperspective" &&
                varying.interpolation != "flat")
            throw std::invalid_argument("line consumer: missing original interpolation policy");
        if (varying.fragment_declared && varying.value_type.scalar != ShaderScalarType::Float &&
                varying.interpolation != "flat")
            throw std::invalid_argument("line consumer: integer/bool fragment transport must be flat");
        const uint64_t alignment = varying.value_type.rows == 1 ? 4 : varying.value_type.rows == 2 ? 8 : 16;
        uint64_t element = varying.value_type.rows * 4;
        const uint64_t matrix_stride = varying.value_type.columns > 1 ? align(element, alignment) : 0;
        if (matrix_stride) element = multiply(matrix_stride, varying.value_type.columns, "line consumer: matrix size overflow");
        const uint64_t array_stride = varying.array_size ? align(element, alignment) : 0;
        const uint64_t elements = varying.array_size ? static_cast<uint32_t>(varying.array_size) : 1;
        const uint64_t size = multiply(array_stride ? array_stride : element, elements,
                                       "line consumer: array size overflow");
        cursor = align(cursor, alignment);
        if (cursor > UINT32_MAX || size > UINT32_MAX - cursor || field.offset != cursor ||
                field.size != size || field.matrix_stride != matrix_stride || field.array_stride != array_stride)
            throw std::invalid_argument("line consumer: reflected varying extent/stride differs");
        cursor += size;
        if (varying.fragment_declared) {
            const auto extent = multiply(varying.value_type.columns, elements, "line consumer: location extent overflow");
            const auto end = add(varying.location, extent, "line consumer: location address overflow");
            if (end > UINT32_MAX) throw std::overflow_error("line consumer: location address exceeds uint32");
            for (size_t previous = 0; previous < i; ++previous) {
                const auto& old = fields[previous].varying;
                if (!old.fragment_declared) continue;
                const auto old_end = uint64_t(old.location) + uint64_t(old.value_type.columns) *
                    (old.array_size ? static_cast<uint32_t>(old.array_size) : 1);
                if (varying.location < old_end && old.location < end)
                    throw std::invalid_argument("line consumer: overlapping fragment varying locations");
            }
            locations = std::max(locations, end);
            components = add(components, multiply(extent, varying.value_type.rows,
                              "line consumer: component extent overflow"), "line consumer: component total overflow");
        }
    }
    if (align(cursor, 16) != row_bytes || components > UINT32_MAX)
        throw std::invalid_argument("line consumer: exact output row/interface extent differs");
    return {row_bytes, static_cast<uint32_t>(locations), static_cast<uint32_t>(components)};
}

struct LineConsumerArtifact {
    // Both must identify the same original snapshot. No render back-reference.
    std::shared_ptr<const LineEvaluatorArtifact> evaluator;
    std::shared_ptr<const PortableShaderArtifact> original;
    LineConsumerPolicy policy;
    std::string identity, cache_key, vertex, fragment, log, error;
    std::vector<int> vertex_line_map, fragment_line_map;
    std::vector<uint32_t> vertex_spv, fragment_spv;
    std::vector<NormUniform> uniforms;
    std::vector<NormSampler> samplers;
    std::vector<SpvResourceUsage> resource_usage;
    uint32_t output_binding = 0, uniform_bytes = 0, parameters_offset = 0;
    uint32_t internal_inter_stage_locations = 0, internal_inter_stage_components = 0;
    bool ok = false;
};

// PROPOSED DECLARATION ONLY: generation, fragment bridge, coverage and compiled
// reflection are a separate implementation packet. No caller may infer success
// from pure layout/range admission. Cache the complete derived graph within the
// existing joint shader budget, excluding its separately deduplicated original.
std::shared_ptr<const LineConsumerArtifact> build_line_consumer(
    std::shared_ptr<const LineEvaluatorArtifact>, const LineConsumerPolicy&,
    const LineConsumerLimits&);

} // namespace vispy::shader

// Canonical integration of the unchanged pure occurrence/range planner.


// PROPOSED SOURCE ONLY: pure plans contain no GPU objects, leases or dispatches.

#include "runtime_line.hpp"

#include <cstddef>

namespace vispy::lines {

struct LineDrawSlice { uint64_t first_segment = 0, segment_count = 0; };
struct LineConsumerViewport { double x = 0, y = 0, width = 0, height = 0; };

// Bind topology to its row table at construction; a separately supplied Mode
// must not reinterpret List rows as Strip/Loop rows in the generated shader.
class LineConsumerSelection {
    Mode primitive_;
    EndpointRows rows_;
public:
    LineConsumerSelection(Mode primitive, Selection selection, uint64_t maximum_rows = UINT32_MAX)
        : primitive_(primitive), rows_(primitive, selection, maximum_rows) {}
    Mode primitive() const noexcept { return primitive_; }
    const EndpointRows& rows() const noexcept { return rows_; }
    uint64_t size() const { return rows_.size(); }
    uint64_t segment_count() const { return rows_.segment_count(); }
    Endpoint at(uint64_t row) const { return rows_.at(row); }
};

// Proposed std140 parameter block. Actual generated compiler reflection must
// verify these offsets before runtime packing; this is not a compiled ABI proof.
struct alignas(16) LineConsumerParameters {
    std::array<uint32_t, 4> header{}; // ABI, logical rows, row bytes, primitive.
    std::array<uint32_t, 4> ranges{}; // Rows/instance, segments/instance, first, count.
    std::array<float, 4> viewport{}; // Physical pixel x, y, width, height.
    std::array<float, 4> raster{};   // Positive pixel width; reserved zeros.
};
static_assert(sizeof(LineConsumerParameters) == 64 && alignof(LineConsumerParameters) == 16);
static_assert(offsetof(LineConsumerParameters, ranges) == 16);
static_assert(offsetof(LineConsumerParameters, viewport) == 32);
static_assert(offsetof(LineConsumerParameters, raster) == 48);

// These requirements come from the FUTURE compiled consumer's exact resource
// reflection. Original UBO values and the parameter block share the paired UBO;
// packing is by reflected names/offsets, never a positional old/new layout copy.
struct LineConsumerResources {
    uint64_t uniform_bytes = 0;
    uint32_t parameters_offset = 0, output_binding = 0, highest_binding = 0;
    uint32_t binding_count = 0, vertex_storage_bindings = 0;
    uint32_t internal_inter_stage_locations = 0, internal_inter_stage_components = 0;
};
struct LineConsumerDrawPlan {
    uint32_t vertex_count = 0, instance_count = 0;
    uint64_t endpoint_buffer_bytes = 0, render_uniform_bytes = 0;
    LineConsumerParameters parameters{};
    State snapshot{}; // Includes original smoothing; no coverage formula here.
    bool empty() const noexcept { return instance_count == 0; }
};

inline void validate_line_draw_slice(const LineConsumerSelection& selection, LineDrawSlice slice) {
    const auto& rows = selection.rows();
    if (slice.first_segment > rows.segment_count() ||
            slice.segment_count > rows.segment_count() - slice.first_segment)
        throw std::out_of_range("line consumer: segment slice exceeds original DRAW");
}
inline SegmentRows line_consumer_segment_rows(const LineConsumerSelection& selection,
        LineDrawSlice slice, uint64_t local_segment) {
    validate_line_draw_slice(selection, slice);
    if (local_segment >= slice.segment_count)
        throw std::out_of_range("line consumer: local segment exceeds slice");
    return selection.rows().segment_rows(slice.first_segment + local_segment);
}

// Validation is non-mutating and keeps occurrence/instance-major identities.
// EndpointRows borrows immutable selection bytes; its capture owner must outlive
// this call and every segment_rows lookup. A plan retains scalar metadata only.
inline LineConsumerDrawPlan plan_line_consumer_draw(
        uint32_t row_bytes, std::span<const shader::LineOutputField> fields,
        Mode primitive, const LineConsumerSelection& selection, LineDrawSlice slice, State state,
        LineConsumerViewport viewport, const LineConsumerResources& resources,
        const shader::LineConsumerLimits& limits) {
    using namespace shader::line_consumer_detail;
    const auto& rows = selection.rows();
    const auto layout = shader::validate_line_output_layout(row_bytes, fields);
    validate_line_draw_slice(selection, slice);
    state = lines::state(state.width, state.smooth);
    if (primitive != Mode::List && primitive != Mode::Strip && primitive != Mode::Loop)
        throw std::invalid_argument("line consumer: invalid primitive policy");
    if (primitive != selection.primitive())
        throw std::invalid_argument("line consumer: primitive differs from captured occurrence table");
    for (const auto value : {viewport.x, viewport.y, viewport.width, viewport.height})
        if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
            throw std::invalid_argument("line consumer: viewport cannot be represented");
    if (viewport.width < 0 || viewport.height < 0)
        throw std::invalid_argument("line consumer: negative viewport extent");
    const float viewport_width = static_cast<float>(viewport.width);
    const float viewport_height = static_cast<float>(viewport.height);
    if ((viewport.width > 0 && (!std::isfinite(viewport_width) || viewport_width <= 0)) ||
            (viewport.height > 0 && (!std::isfinite(viewport_height) || viewport_height <= 0)))
        throw std::invalid_argument("line consumer: positive viewport extent underflows shader precision");
    const float width = static_cast<float>(state.width);
    if (!std::isfinite(width) || width <= 0)
        throw std::invalid_argument("line consumer: pixel width cannot be represented");
    LineConsumerDrawPlan result;
    result.snapshot = state;
    if (!slice.segment_count || !viewport.width || !viewport.height) return result;
    if (rows.size() > UINT32_MAX || rows.per_instance() > UINT32_MAX ||
            slice.first_segment > UINT32_MAX || slice.segment_count > UINT32_MAX)
        throw std::overflow_error("line consumer: row/draw address exceeds uint32");
    // All modes have a constant-sized occurrence table; no segment/index scan.
    const uint64_t per_instance = primitive == Mode::List ? rows.per_instance() / 2 :
        primitive == Mode::Strip ? rows.per_instance() - 1 : rows.per_instance();
    if (!per_instance || per_instance > UINT32_MAX)
        throw std::overflow_error("line consumer: segment divisor exceeds uint32");
    const auto bytes = multiply(rows.size(), layout.row_bytes, "line consumer: endpoint byte size overflow");
    if (!limits.max_storage_buffers_per_stage || resources.vertex_storage_bindings != 1 ||
            resources.vertex_storage_bindings > limits.max_storage_buffers_per_stage ||
            bytes > std::min(limits.max_storage_binding_bytes, limits.max_buffer_bytes))
        throw std::length_error("line consumer: endpoint output exceeds granted storage/allocation");
    if (resources.parameters_offset % 16 || resources.parameters_offset > resources.uniform_bytes ||
            sizeof(LineConsumerParameters) > resources.uniform_bytes - resources.parameters_offset ||
            resources.uniform_bytes > std::min(limits.max_uniform_binding_bytes, limits.max_buffer_bytes))
        throw std::length_error("line consumer: reflected render UBO/parameters exceed grant");
    if (!resources.binding_count || resources.binding_count > limits.max_bindings_per_group ||
            resources.highest_binding >= limits.max_bindings_per_group ||
            resources.output_binding > resources.highest_binding)
        throw std::length_error("line consumer: reflected binding range exceeds grant");
    const auto locations = add(layout.inter_stage_locations, resources.internal_inter_stage_locations,
                               "line consumer: inter-stage location overflow");
    const auto components = add(layout.inter_stage_components, resources.internal_inter_stage_components,
                                "line consumer: inter-stage component overflow");
    if (locations > limits.max_inter_stage_locations || components > limits.max_inter_stage_components)
        throw std::length_error("line consumer: typed fragment interface exceeds grant");
    // Six corners per segment; instanced addressing avoids a proportional CPU
    // vertex array. Check the logical expansion count even though Draw uses6.
    multiply(slice.segment_count, 6, "line consumer: corner count overflow");
    result.vertex_count = 6;
    result.instance_count = static_cast<uint32_t>(slice.segment_count);
    result.endpoint_buffer_bytes = bytes;
    result.render_uniform_bytes = resources.uniform_bytes;
    result.parameters.header = {shader::kLineConsumerAbi, static_cast<uint32_t>(rows.size()), row_bytes,
        primitive == Mode::List ? 0u : primitive == Mode::Strip ? 1u : 2u};
    result.parameters.ranges = {static_cast<uint32_t>(rows.per_instance()), static_cast<uint32_t>(per_instance),
        static_cast<uint32_t>(slice.first_segment), static_cast<uint32_t>(slice.segment_count)};
    result.parameters.viewport = {static_cast<float>(viewport.x), static_cast<float>(viewport.y),
        viewport_width, viewport_height};
    result.parameters.raster[0] = width;
    // Smoothing, sample count and the exact coverage identity belong to the
    // compiled policy/pipeline key, not a guessed alpha formula in this planner.
    return result;
}

} // namespace vispy::lines

// Generated aliased consumer API and paired ABI2 parameters.


// Isolated implementation proposal. Compilation, runtime and pixels are
// separate admission gates; these files do not change the installed renderer.



namespace vispy::shader {

inline constexpr uint32_t kGeneratedLineConsumerAbi = 2;
inline constexpr const char* kAliasedLineCoverageIdentity =
    "gl46-14.5.1-14.5.2.2-symbolic-diamond-exit-affine-planes-clipped-terminal-major-axis-v2";

// Complete CPU lookup identity, available before shader generation. Limits,
// DRAW width/viewport, device generation and attachment formats do not change
// generated shader policy. Unsupported policies still refuse in the builder.
inline std::string generated_line_consumer_policy_identity(
        const LineEvaluatorArtifact& evaluator, const LineConsumerPolicy& policy) {
    if (!evaluator.original) throw std::invalid_argument("line consumer policy requires an original");
    if (!policy.sample_count || policy.coverage_identity.empty() ||
        (policy.coverage != LineCoveragePolicy::AliasedMajorAxis && policy.coverage != LineCoveragePolicy::SmoothReference))
        throw std::invalid_argument("line consumer policy identity is incomplete");
    const auto& original = *evaluator.original;
    std::string key = "vispy-generated-line-consumer-policy-v5;abi=2;typed-storage-both-stages;"
        "fragment=private-inputs-AST-initializers-once;helper=logical-or-current-native-query-v1;"
        "finite=ieee754-signmask-unsigned-v1;product=topology-bounded-v1;coordinate=gl-window-present-y-v1;"
        "mapping=whole-or-local-chunk-original-primitive-v1;coverage=" + std::to_string(static_cast<uint32_t>(policy.coverage)) +
        ";samples=" + std::to_string(policy.sample_count) + ";base=" +
        std::to_string(original.options.base_level_sampling) + ";render-derivatives=" +
        spirv_derivative_mode_name(original.derivative_mode) + ";evaluator-derivatives=" +
        spirv_derivative_mode_name(evaluator.derivative_mode) + ';';
    for (const auto* field : {&original.identity, &evaluator.identity, &original.compiler_identity, &policy.coverage_identity})
        key += std::to_string(field->size()) + ':' + *field;
    return key;
}

struct GeneratedLineConsumerArtifact : LineConsumerArtifact {
    std::string policy_identity;  // Immutable full key retained/charged by this owner.
    ShaderBuildTimings timings;
    uint64_t relocated_fragment_initializers = 0;
    SpvStorageLayout vertex_rows, fragment_rows;
    uint32_t uniform_stage_mask = 0;
    uint32_t vertex_storage_bindings = 0, fragment_storage_bindings = 0;
    // Required pipeline state: GL lines are front facing, and generated
    // triangles must not introduce polygon culling or polygon depth bias.
    bool requires_cull_none = true, requires_zero_polygon_bias = true;
    size_t storage_bytes() const;
};

// Same original/evaluator allocation, complete exact policy/compiler identity.
// No vertex user code is copied into the consumer. Original fragment code is
// reconstructed from the canonical normalized snapshot, with private inputs.
std::shared_ptr<const GeneratedLineConsumerArtifact> build_generated_line_consumer(
    std::shared_ptr<const LineEvaluatorArtifact>, const LineConsumerPolicy&,
    const LineConsumerLimits&);

// ABI 2: values are GL window coordinates. Dawn's viewport must use
// framebuffer_height - viewport.y - viewport.height for its top-left origin.
// The shader performs GL->Dawn y/depth conversion once; paired UBO packing
// must use these reflected names/offsets together with the immutable originals.
struct alignas(16) GeneratedLineConsumerParameters {
    // Modes 0/1/2 retain whole list/strip/loop addressing. Modes >=3 encode
    // chunk flags: bit0 previous seam, bit1 closing seam, bit2 list.
    std::array<uint32_t, 4> header{}; // ABI, logical rows, row bytes, mode.
    // Whole: rows/instance, segments/instance, first, count.
    // Chunk: newly evaluated rows, original first segment, zero, count.
    std::array<uint32_t, 4> ranges{};
    std::array<float, 4> viewport{}; // GL x/y/width/height in framebuffer pixels.
    std::array<float, 4> raster{}; // aliased width, framebuffer height, depth near/far.
};
static_assert(sizeof(GeneratedLineConsumerParameters) == 64);
static_assert(offsetof(GeneratedLineConsumerParameters, ranges) == 16);
static_assert(offsetof(GeneratedLineConsumerParameters, viewport) == 32);
static_assert(offsetof(GeneratedLineConsumerParameters, raster) == 48);

struct GeneratedLineConsumerDraw {
    GeneratedLineConsumerParameters parameters{};
    uint64_t endpoint_bytes = 0, render_uniform_bytes = 0;
    uint32_t vertex_count = 0, instance_count = 0;
};

// This planner uses the actual generated interface (one flat uvec4), not
// the prospective original-varying interface from the earlier CPU29 proposal.
GeneratedLineConsumerDraw plan_generated_line_consumer_draw(
    const GeneratedLineConsumerArtifact&, const lines::LineConsumerSelection&,
    lines::LineDrawSlice, lines::State, lines::LineConsumerViewport,
    double framebuffer_height, double depth_near, double depth_far,
    const LineConsumerLimits&);

// Output rows contain newly evaluated endpoints followed by the optional
// previous endpoint and original loop-first endpoint. Segment and LAST IDs
// address that local table; gl_PrimitiveID retains the original flattened ID.
// A final loop chunk may have no newly evaluated rows and two copied seams.
GeneratedLineConsumerDraw plan_generated_line_consumer_chunk_draw(
    const GeneratedLineConsumerArtifact&, uint32_t new_rows, uint32_t output_rows,
    uint32_t segment_count, bool previous, bool closing, bool list,
    uint32_t original_first_segment, lines::State, lines::LineConsumerViewport,
    double framebuffer_height, double depth_near, double depth_far,
    const LineConsumerLimits&);

} // namespace vispy::shader
