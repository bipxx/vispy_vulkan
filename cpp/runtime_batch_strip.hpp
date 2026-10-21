#pragma once

#include "runtime_batch_topology.hpp"
#include "runtime_batch_cache.hpp"
#include "shader/normalize.hpp"
#include <string_view>

namespace vispy::inputs::batches {

// Ordinary independent triangles, ordered strips and fans use this runtime
// bridge. It adds no primitive-restart state or generated-line/point route.
inline bool ordinary_triangle_batches(std::string_view mode) {
    return mode == "triangles" || mode == "triangle_strip" || mode == "triangle_fan";
}

inline Topology ordinary_triangle_topology(std::string_view mode) {
    if (mode == "triangles") return Topology::Triangles;
    if (mode == "triangle_strip") return Topology::TriangleStrip;
    if (mode == "triangle_fan") return Topology::TriangleFan;
    throw std::runtime_error("DRAW batches: ordinary triangle topology required");
}

// Match topology_indices' whole-fan allocation/count admission without first
// multiplying the number of triangles. Oversized fans retain their original
// selection until the bounded topology planner visits each primitive.
inline bool fan_expansion_fits(uint64_t count, uint64_t buffer_bytes) {
    const auto max_indices = std::min({uint64_t(INT32_MAX), buffer_bytes / 4,
                                      uint64_t(SIZE_MAX / 4)});
    return count < 3 || count - 2 <= max_indices / 3;
}

inline bool defer_triangle_u8_widening(std::string_view mode, uint64_t count, uint64_t buffer_bytes) {
    return ordinary_triangle_batches(mode) && !u8_widening_fits(count, buffer_bytes);
}

inline std::string ordinary_triangle_domain(std::string_view mode, const std::string& selected_key,
                                            uint64_t instances) {
    (void)ordinary_triangle_topology(mode);
    return std::string(mode) + ':' + draw_domain_key(selected_key, instances);
}

inline Plan plan_ordinary_triangle_batches(Topology topology, const Selection& selected,
                                           std::span<const Source> sources, const Layout& layout,
                                           Limits limits) {
    if (topology == Topology::Triangles)
        return plan_triangle_list(selected, sources, layout, limits);
    if (topology != Topology::TriangleStrip && topology != Topology::TriangleFan)
        throw std::runtime_error("DRAW batches: ordinary triangle topology required");
    // Keep only owning Plan vectors. In particular, runs/origins are destroyed
    // on return BEFORE the caller packs an ABI2 OwnerData. No expanded global
    // index byte vector or Selection/index span is retained in Plan.
    auto lowered = plan_topology(topology, selected, sources, layout,
                                limits, RestartPolicy{RestartMode::Disabled, 0});
    return std::move(lowered.payload);
}

struct OrdinaryBatchPolicy {
    ::VertexIdentityPolicy identity;
    std::string_view mode;
    std::string_view index_type;
};

inline OrdinaryBatchPolicy expected_ordinary_batch_policy(Topology original, const Selection& selected) {
    if (original != Topology::Triangles && original != Topology::TriangleStrip && original != Topology::TriangleFan)
        throw std::runtime_error("DRAW batches: ordinary triangle topology required");
    // This semantic invariant permits shader/interface/string preparation before
    // cache access. The private lowered Plan must prove it before publication.
    const bool indexed = original != Topology::Triangles || selected.index_bytes != 0;
    return {indexed ? ::VertexIdentityPolicy::BatchIndexed :
                      ::VertexIdentityPolicy::BatchAffine,
            "triangles", indexed ? "unsigned_int" : ""};
}

inline OrdinaryBatchPolicy ordinary_batch_policy(Topology original, const Plan& payload) {
    if ((original != Topology::Triangles && original != Topology::TriangleStrip && original != Topology::TriangleFan) ||
        (original != Topology::Triangles && !payload.indexed))
        throw std::runtime_error("DRAW batches: lowered triangle payload policy mismatch");
    // DrawArrays strips/fans also produce an owning indexed triangle-list payload.
    // Original selected.index_bytes must never select their shader/index ABI.
    return {payload.indexed ? ::VertexIdentityPolicy::BatchIndexed :
                              ::VertexIdentityPolicy::BatchAffine,
            "triangles", payload.indexed ? "unsigned_int" : ""};
}

inline void validate_ordinary_batch_policy(Topology original, const Plan& payload,
                                          const OrdinaryBatchPolicy& expected) {
    const auto actual = ordinary_batch_policy(original, payload);
    if (actual.identity != expected.identity || actual.mode != expected.mode || actual.index_type != expected.index_type)
        throw std::runtime_error("DRAW batches: lowered payload differs from prepared shader policy");
}

// Thin native lines use the same bounded ABI2 owner as ordinary triangles.
// Keep the triangle-only helpers above intact for their existing callers.
inline bool ordinary_line_batches(std::string_view mode) {
    return mode == "lines" || mode == "line_strip" || mode == "line_loop";
}

inline bool ordinary_input_batches(std::string_view mode) {
    return ordinary_triangle_batches(mode) || ordinary_line_batches(mode);
}

inline Topology ordinary_input_topology(std::string_view mode) {
    if (mode == "lines") return Topology::Lines;
    if (mode == "line_strip") return Topology::LineStrip;
    if (mode == "line_loop") return Topology::LineLoop;
    return ordinary_triangle_topology(mode);
}

inline bool loop_expansion_fits(uint64_t count, uint64_t buffer_bytes) {
    const auto max_indices = std::min({uint64_t(INT32_MAX), buffer_bytes / 4,
                                      uint64_t(SIZE_MAX / 4)});
    return count < 2 || count < max_indices;
}

inline bool defer_ordinary_u8_widening(std::string_view mode, uint64_t count, uint64_t buffer_bytes) {
    return ordinary_input_batches(mode) && !u8_widening_fits(count, buffer_bytes);
}

inline std::string ordinary_input_domain(std::string_view mode, const std::string& selected_key,
                                         uint64_t instances) {
    (void)ordinary_input_topology(mode);
    return std::string(mode) + ':' + draw_domain_key(selected_key, instances);
}

inline bool ordinary_line_topology(Topology topology) {
    return topology == Topology::Lines || topology == Topology::LineStrip || topology == Topology::LineLoop;
}

inline Plan plan_ordinary_input_batches(Topology topology, const Selection& selected,
                                       std::span<const Source> sources, const Layout& layout, Limits limits) {
    if (!ordinary_line_topology(topology))
        return plan_ordinary_triangle_batches(topology, selected, sources, layout, limits);
    auto lowered = plan_topology(topology, selected, sources, layout,
                                limits, RestartPolicy{RestartMode::Disabled, 0});
    return std::move(lowered.payload);
}

inline OrdinaryBatchPolicy expected_ordinary_input_policy(Topology topology, const Selection& selected) {
    if (!ordinary_line_topology(topology)) return expected_ordinary_batch_policy(topology, selected);
    const bool indexed = topology != Topology::Lines || selected.index_bytes != 0;
    return {indexed ? ::VertexIdentityPolicy::BatchIndexed : ::VertexIdentityPolicy::BatchAffine,
            "lines", indexed ? "unsigned_int" : ""};
}

inline OrdinaryBatchPolicy ordinary_input_policy(Topology topology, const Plan& payload) {
    if (!ordinary_line_topology(topology)) return ordinary_batch_policy(topology, payload);
    if (topology != Topology::Lines && !payload.indexed)
        throw std::runtime_error("DRAW batches: lowered line payload must own its index selection");
    return {payload.indexed ? ::VertexIdentityPolicy::BatchIndexed : ::VertexIdentityPolicy::BatchAffine,
            "lines", payload.indexed ? "unsigned_int" : ""};
}

inline void validate_ordinary_input_policy(Topology topology, const Plan& payload,
                                           const OrdinaryBatchPolicy& expected) {
    const auto actual = ordinary_input_policy(topology, payload);
    if (actual.identity != expected.identity || actual.mode != expected.mode || actual.index_type != expected.index_type)
        throw std::runtime_error("DRAW batches: lowered payload differs from prepared shader policy");
}

// plan_topology still admits against its conservative ABI1 eight-byte header
// and transient diagnostic/control charges. We do not relax storage capacity
// to ABI2's smaller headerless identity payload. OwnerData separately accounts
// for actual retained Plan capacities/leaves and its real16-byte origin UBO.

} // namespace vispy::inputs::batches
