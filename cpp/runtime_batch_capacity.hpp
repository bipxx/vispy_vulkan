#pragma once

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4267) // Existing partition_layout dependency conversion.
#endif
#include "runtime_point.hpp"
#ifdef _MSC_VER
#pragma warning(pop)
#endif

namespace vispy::inputs {

enum class WholeCompactReason { Fits, InstanceRows, IndexBytes, VertexRows, IdentityBytes, UniqueVertices };
struct WholeCompactFit {
    bool fits = false;
    WholeCompactReason reason = WholeCompactReason::Fits;
    uint64_t vertex_capacity = 0;
    uint64_t unique_vertices_observed = 0;
    uint64_t indices_scanned = 0;
    uint64_t peak_scratch_keys = 0;
    uint64_t scratch_key_bound = 0;
};

// Probe the existing whole compact representation, NOT batch identity ABI1/2.
// Affine identity is one uint32 base; indexed identity is headerless uint32[].
// Source payload bounds must already be validated by the caller. Selection's
// index-read/array-ID bounds are validated here, including no-op selections.
// No remapped index vector or source attribute payload is materialized.
inline WholeCompactFit probe_whole_compact_fit(const Selection& selected, const Layout& layout,
                                               uint64_t buffer_bytes, uint64_t storage_bytes,
                                               bool live_vertex_identity) {
    validate_selection(selected);
    WholeCompactFit result;
    if (!selected.count || !selected.instances) { result.fits = true; return result; }
    if (layout.direct) throw std::runtime_error("DRAW inputs: whole compact probe expects compact layout");
    for (const auto& stream : layout.streams)
        if (!stream.stride) throw std::runtime_error("DRAW inputs: whole compact probe has zero stream stride");

    // Reject domain/byte limits before reading any selected index.
    for (const auto& stream : layout.streams) if (stream.instance &&
        (selected.instances > buffer_bytes / stream.stride || selected.instances > SIZE_MAX / stream.stride)) {
        result.reason = WholeCompactReason::InstanceRows; return result;
    }
    if (selected.index_bytes && (selected.count > buffer_bytes / 4 || selected.count > SIZE_MAX / 4)) {
        result.reason = WholeCompactReason::IndexBytes; return result;
    }
    uint64_t capacity = selected.index_bytes ? std::min({buffer_bytes / 4, uint64_t(SIZE_MAX / 4), uint64_t(INT32_MAX)}) : UINT64_MAX;
    for (const auto& stream : layout.streams) if (!stream.instance)
        capacity = std::min({capacity, buffer_bytes / stream.stride, uint64_t(SIZE_MAX / stream.stride)});
    result.vertex_capacity = capacity;
    if (!selected.index_bytes && selected.count > capacity) {
        result.reason = WholeCompactReason::VertexRows; return result;
    }
    if (live_vertex_identity && (buffer_bytes < 4 || storage_bytes < 4)) {
        result.reason = WholeCompactReason::IdentityBytes; return result;
    }
    if (!selected.index_bytes) { result.fits = true; return result; }
    if (live_vertex_identity) capacity = std::min(capacity, storage_bytes / 4);
    result.vertex_capacity = capacity;
    result.scratch_key_bound = std::min(capacity, selected.count);
    if (!capacity) { result.reason = WholeCompactReason::VertexRows; return result; }

    // Grow with actual distinct IDs, never reserve(count) or reserve(capacity).
    // At most scratch_key_bound keys are stored. Encountering distinct key
    // capacity+1 decides failure without inserting that final key. This bounds
    // logical key count; unordered_set bucket/node overhead and allocator peaks
    // are deliberately not claimed as exact byte bounds.
    std::unordered_set<uint32_t> unique;
    for (uint64_t n = 0; n < selected.count; ++n) {
        const uint32_t original = selected.vertex(n);
        ++result.indices_scanned;
        if (unique.contains(original)) continue;
        ++result.unique_vertices_observed;
        if (unique.size() >= capacity) {
            result.reason = WholeCompactReason::UniqueVertices; return result;
        }
        unique.insert(original);
        result.peak_scratch_keys = unique.size();
    }
    result.fits = true;
    return result;
}

} // namespace vispy::inputs
