#pragma once

#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4267)
#endif
#include "runtime_point.hpp"
#ifdef _MSC_VER
#pragma warning(pop)
#endif

namespace vispy::points {

// Point rows have already flattened the original vertex/instance domains.
// Every physical user stream consequently advances once per local instance,
// regardless of the original source's divisor.
inline inputs::Layout partitioned_layout(std::span<const uint32_t> widths,
        uint32_t max_attributes, uint32_t max_vertex_buffers, uint32_t max_stride) {
    if (widths.size() > max_attributes)
        throw std::runtime_error("DRAW point partition: active user inputs exceed granted attribute limit");
    const std::vector<uint8_t> steps(widths.size(), 1);
    return inputs::partition_layout(widths, steps, max_attributes, max_vertex_buffers, max_stride);
}

inline void validate_partitioned_layout(std::span<const PackedSource> sources,
                                       const inputs::Layout& layout) {
    if (layout.direct || layout.slots.size() != sources.size() ||
        layout.offsets.size() != sources.size() || layout.streams.size() > UINT32_MAX)
        throw std::runtime_error("DRAW point partition: layout differs from packed fields");
    size_t fields = 0;
    uint64_t total = 0;
    for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
        const auto& stream = layout.streams[slot];
        if (!stream.instance || stream.bind_offset || stream.fields.empty() || !stream.stride)
            throw std::runtime_error("DRAW point partition: invalid flattened stream");
        uint64_t offset = 0;
        for (size_t field : stream.fields) {
            if (field >= sources.size() || layout.slots[field] != slot || layout.offsets[field] != offset)
                throw std::runtime_error("DRAW point partition: invalid field map");
            const uint64_t width = sources[field].element_bytes;
            if (width != 4 && width != 8 && width != 12 && width != 16)
                throw std::runtime_error("DRAW point partition: unsupported raw field width");
            // Duplicate fields in this stream cannot share the increasing
            // packed offset; cross-stream duplicates cannot share a slot.
            offset += width;
            if (offset > UINT32_MAX)
                throw std::runtime_error("DRAW point partition: stream stride exceeds uint32");
            ++fields;
        }
        if (offset != stream.stride)
            throw std::runtime_error("DRAW point partition: stream stride differs from fields");
        total += stream.stride;
        if (total > UINT32_MAX)
            throw std::runtime_error("DRAW point partition: aggregate stride exceeds uint32");
    }
    if (fields != sources.size())
        throw std::runtime_error("DRAW point partition: incomplete field map");
}

// This exact physical description is suitable for runtime cache domains.
// Source revision/address/divisor identity belongs to packed_source_key.
inline std::string partition_key(const inputs::Layout& layout, std::span<const PackedSource> sources) {
    validate_partitioned_layout(sources, layout);
    std::string result = "point-partition:" + std::to_string(sources.size());
    for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
        const auto& stream = layout.streams[slot];
        result += ";s:" + std::to_string(slot) + ':' + std::to_string(stream.stride);
        for (size_t field : stream.fields)
            result += ";f:" + std::to_string(field) + ':' + std::to_string(layout.offsets[field]) +
                      ':' + std::to_string(sources[field].element_bytes);
    }
    return result;
}

} // namespace vispy::points
