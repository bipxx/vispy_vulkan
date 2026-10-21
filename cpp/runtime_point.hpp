#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <limits>
#include <list>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace vispy::points {

inline constexpr const char* identity_attribute = "vispy_point_identity";

// Route selection changes only the snapshot and the derived point slot.
// Programs retain their LINK artifact for later ordinary primitives and for
// loss recovery; relinking must clear the derived slot.
template<class Artifact, class Build>
std::shared_ptr<Artifact> select_draw_artifact(bool point_draw,
        const std::shared_ptr<Artifact>& original, std::shared_ptr<Artifact>& point_variant, Build&& build) {
    if (!original) throw std::runtime_error("DRAW: program has not been linked");
    if (!point_draw) {
        if (original->portable->point_sprites)
            throw std::runtime_error("DRAW: gl_PointCoord requires point primitives");
        return original;
    }
    if (original->portable->point_sprites) return original;
    if (!point_variant) point_variant = std::forward<Build>(build)(original);
    return point_variant;
}

struct Selection {
    uint64_t first = 0, count = 0, instances = 1;
    std::span<const uint8_t> indices;
    uint32_t index_bytes = 0;  // zero for DrawArrays; otherwise 1, 2 or 4.

    uint64_t rows(uint64_t max_buffer_bytes, uint64_t element_bytes) const {
        if (index_bytes != 0 && index_bytes != 1 && index_bytes != 2 && index_bytes != 4)
            throw std::runtime_error("DRAW points: unsupported index width");
        if (index_bytes && count > indices.size() / index_bytes)
            throw std::runtime_error("DRAW points: index selection exceeds its revision");
        if (!index_bytes && count && (first > UINT32_MAX || count - 1 > UINT32_MAX - first))
            throw std::runtime_error("DRAW points: original vertex identity exceeds uint32");
        if (instances > static_cast<uint64_t>(INT32_MAX) ||
            (instances && count > static_cast<uint64_t>(INT32_MAX) / instances))
            throw std::runtime_error("DRAW points: flattened instance count exceeds native draw limit");
        const uint64_t total = count * instances;
        if (!element_bytes || total > max_buffer_bytes / element_bytes ||
            total > std::numeric_limits<size_t>::max() / element_bytes)
            throw std::runtime_error("DRAW points: derived buffer exceeds granted allocation limit");
        return total;
    }

    uint32_t vertex(uint64_t point) const {
        if (point >= count) throw std::runtime_error("DRAW points: identity point exceeds selection");
        if (!index_bytes) {
            if (first > UINT32_MAX || point > UINT32_MAX - first)
                throw std::runtime_error("DRAW points: original vertex identity exceeds uint32");
            return static_cast<uint32_t>(first + point);
        }
        if ((index_bytes != 1 && index_bytes != 2 && index_bytes != 4) ||
            point >= indices.size() / index_bytes)
            throw std::runtime_error("DRAW points: identity index exceeds its revision");
        uint32_t result = 0;
        // Host storage is native-endian, matching the public GLIR byte blob.
        if (index_bytes == 1) result = indices[static_cast<size_t>(point)];
        else if (index_bytes == 2) {
            uint16_t value;
            std::memcpy(&value, indices.data() + point * 2, 2); result = value;
        } else std::memcpy(&result, indices.data() + point * 4, 4);
        return result;
    }
};

// Allocation identities are monotonic, never pointer addresses. Include the
// source/index revision and selection even when the map's owner is reused.
inline std::string conversion_key(const char* operation, const Selection& selection,
                                 uint64_t source_id, uint64_t source_revision,
                                 uint64_t index_id, uint64_t index_revision,
                                 uint64_t offset = 0, uint64_t stride = 0,
                                 uint64_t element_bytes = 8, uint64_t divisor = 0) {
    std::string key = std::string("points:") + operation;
    for (uint64_t value : {source_id, source_revision, index_id, index_revision,
                          selection.first, selection.count, selection.instances,
                          static_cast<uint64_t>(selection.index_bytes), offset, stride, element_bytes, divisor})
        key += ':' + std::to_string(value);
    return key;
}

// Build before mutating the cache. Pending draws can own evicted children,
// and children never own their source, so cache eviction cannot invalidate
// snapshots or form a parent/child ownership cycle.
template<class Map, class Build>
auto cached_conversion(Map& cache, const std::string& key, Build&& build, size_t limit = 128) {
    using Record = typename Map::mapped_type;
    if (auto found = cache.find(key); found != cache.end()) return std::pair<Record, bool>{found->second, false};
    if (!limit) throw std::runtime_error("DRAW points: derived cache limit must be positive");
    Record result = std::forward<Build>(build)();
    while (cache.size() >= limit) cache.erase(cache.begin());
    cache.emplace(key, result);
    return std::pair<Record, bool>{std::move(result), true};
}

inline std::vector<uint8_t> identity_data(const Selection& selection, uint64_t max_buffer_bytes) {
    const auto total = selection.rows(max_buffer_bytes, 8);
    if (!total) return {};
    std::vector<uint8_t> result(static_cast<size_t>(total) * 8);
    for (uint64_t instance = 0; instance < selection.instances; ++instance) {
        for (uint64_t point = 0; point < selection.count; ++point) {
            const uint32_t identity[] = {selection.vertex(point), static_cast<uint32_t>(instance)};
            std::memcpy(result.data() + (instance * selection.count + point) * 8, identity, 8);
        }
    }
    return result;
}

inline std::vector<uint8_t> gather_data(const Selection& selection, std::span<const uint8_t> source,
                                      uint64_t offset, uint64_t stride, uint64_t element_bytes,
                                      uint64_t divisor, uint64_t max_buffer_bytes) {
    const auto total = selection.rows(max_buffer_bytes, element_bytes);
    if (!total) return {};
    // Prove every read before allocating/copying any derived payload. In
    // particular, a huge sparse uint32 index cannot request a wrapped offset.
    auto address = [&](uint64_t element) -> size_t {
        if (offset > source.size() ||
            (stride && element > (source.size() - offset) / stride))
            throw std::runtime_error("DRAW points: attribute element exceeds source revision");
        const uint64_t start = offset + element * stride;
        if (element_bytes > source.size() - start)
            throw std::runtime_error("DRAW points: attribute payload exceeds source revision");
        return static_cast<size_t>(start);
    };
    if (total) {
        if (divisor) address((selection.instances - 1) / divisor);
        else for (uint64_t point = 0; point < selection.count; ++point) address(selection.vertex(point));
    }
    std::vector<uint8_t> result(static_cast<size_t>(total * element_bytes));
    for (uint64_t instance = 0; instance < selection.instances; ++instance) {
        for (uint64_t point = 0; point < selection.count; ++point) {
            const uint64_t element = divisor ? instance / divisor : selection.vertex(point);
            const size_t start = address(element);
            std::memcpy(result.data() + (instance * selection.count + point) * element_bytes,
                        source.data() + start, static_cast<size_t>(element_bytes));
        }
    }
    return result;
}

struct PackedLayout {
    std::vector<uint32_t> offsets;
    uint32_t stride = 0;
};

inline PackedLayout packed_layout(std::span<const uint32_t> element_bytes, uint32_t max_attributes,
                                  uint32_t max_vertex_buffers, uint32_t max_stride) {
    if (element_bytes.size() > max_attributes)
        throw std::runtime_error("DRAW points: active user inputs=" + std::to_string(element_bytes.size()) +
                                 " exceed granted attribute limit=" + std::to_string(max_attributes));
    if (!element_bytes.empty() && !max_vertex_buffers)
        throw std::runtime_error("DRAW points: packed user inputs require one granted vertex buffer");
    uint64_t stride = 0;
    for (uint32_t bytes : element_bytes) {
        if (bytes != 4 && bytes != 8 && bytes != 12 && bytes != 16)
            throw std::runtime_error("DRAW points: unsupported packed attribute width");
        stride += bytes;
        if (stride > max_stride || stride > UINT32_MAX)
            throw std::runtime_error("DRAW points: packed user input stride exceeds granted limit");
    }
    PackedLayout result;
    result.stride = static_cast<uint32_t>(stride);
    result.offsets.reserve(element_bytes.size());
    uint32_t offset = 0;
    for (uint32_t bytes : element_bytes) { result.offsets.push_back(offset); offset += bytes; }
    return result;
}

struct PackedSource {
    std::span<const uint8_t> bytes;
    uint64_t identity = 0, revision = 0;
    uint64_t offset = 0, stride = 0, element_bytes = 0, divisor = 0;
    std::string_view name;
};

inline std::string packed_source_key(std::span<const PackedSource> sources,
                                     uint64_t index_identity, uint64_t index_revision, uint32_t index_bytes) {
    std::string key = "point-sources:" + std::to_string(index_identity) + ':' +
        std::to_string(index_revision) + ':' + std::to_string(index_bytes);
    for (const auto& source : sources) {
        key += ';' + std::to_string(source.name.size()) + ':';
        key.append(source.name);
        for (uint64_t value : {source.identity, source.revision, source.offset, source.stride,
                              source.element_bytes, source.divisor}) key += ':' + std::to_string(value);
    }
    return key;
}

template<class Map>
void refresh_sources(std::string& previous, const std::string& current, Map& cache) {
    if (previous == current) return;
    // Snapshot owners remain valid. Drop the cache's stale CPU/GPU owners
    // immediately instead of retaining 128 complete update revisions.
    cache.clear();
    previous = current;
}

inline std::vector<uint8_t> packed_data(const Selection& selection, std::span<const PackedSource> sources,
                                      const PackedLayout& layout, uint64_t max_buffer_bytes) {
    uint64_t stride = 0;
    if (layout.offsets.size() != sources.size())
        throw std::runtime_error("DRAW points: packed layout differs from source fields");
    for (size_t n = 0; n < sources.size(); ++n) {
        const auto bytes = sources[n].element_bytes;
        if ((bytes != 4 && bytes != 8 && bytes != 12 && bytes != 16) || layout.offsets[n] != stride)
            throw std::runtime_error("DRAW points: packed layout differs from source fields");
        stride += bytes;
    }
    if (stride != layout.stride) throw std::runtime_error("DRAW points: packed layout stride differs from source fields");
    const uint64_t rows = selection.rows(sources.empty() ? UINT64_MAX : max_buffer_bytes,
                                         sources.empty() ? 1 : layout.stride);
    if (!rows || sources.empty()) return {};
    auto address = [&](const PackedSource& source, uint64_t element) -> size_t {
        if (source.offset > source.bytes.size() ||
            (source.stride && element > (source.bytes.size() - source.offset) / source.stride))
            throw std::runtime_error("ATTRIBUTE " + std::string(source.name) + ": point element exceeds source revision");
        const uint64_t start = source.offset + element * source.stride;
        if (source.element_bytes > source.bytes.size() - start)
            throw std::runtime_error("ATTRIBUTE " + std::string(source.name) + ": point payload exceeds source revision");
        return static_cast<size_t>(start);
    };
    // Reads are monotonic in the selected element for each unsigned stride.
    // Find the greatest sparse index once and prove every source before any
    // output allocation. Constants use stride zero and ignore this index.
    uint32_t maximum_vertex = 0;
    for (uint64_t point = 0; point < selection.count; ++point)
        maximum_vertex = std::max(maximum_vertex, selection.vertex(point));
    for (const auto& source : sources)
        address(source, source.divisor ? (selection.instances - 1) / source.divisor : maximum_vertex);
    std::vector<uint8_t> result(static_cast<size_t>(rows * layout.stride));
    for (uint64_t instance = 0; instance < selection.instances; ++instance) {
        for (uint64_t point = 0; point < selection.count; ++point) {
            const uint32_t vertex = selection.vertex(point);
            const uint64_t row = instance * selection.count + point;
            for (size_t field = 0; field < sources.size(); ++field) {
                const auto& source = sources[field];
                const uint64_t element = source.divisor ? instance / source.divisor : vertex;
                const size_t start = address(source, element);
                std::memcpy(result.data() + row * layout.stride + layout.offsets[field],
                            source.bytes.data() + start, static_cast<size_t>(source.element_bytes));
            }
        }
    }
    return result;
}

}  // namespace vispy::points

namespace vispy::inputs {

using Selection = vispy::points::Selection;
using Source = vispy::points::PackedSource;
inline constexpr size_t cache_entry_limit = 128;
inline constexpr uint64_t cache_byte_limit = 64ull * 1024 * 1024;
// Conservative node/link bookkeeping, separate from the value/key capacity.
// Allocator headers and bucket-array padding are not physical/RSS accounting.
inline constexpr uint64_t cache_entry_bookkeeping = 4 * sizeof(void*);

template<class Artifact, class Build>
std::shared_ptr<Artifact> select_compact_artifact(bool indexed,
        const std::shared_ptr<Artifact>& original, std::shared_ptr<Artifact>& affine,
        std::shared_ptr<Artifact>& indexed_variant, Build&& build) {
    if (!original) throw std::runtime_error("DRAW inputs: program has not been linked");
    if (original->portable->point_sprites)
        throw std::runtime_error("DRAW inputs: point sprite artifact cannot select an ordinary identity policy");
    auto& selected=indexed?indexed_variant:affine;
    if (!selected) selected=std::forward<Build>(build)(original,indexed);
    return selected;
}

inline void validate_selection(const Selection& selection) {
    if (selection.count > INT32_MAX || selection.instances > INT32_MAX)
        throw std::runtime_error("DRAW inputs: vertex/instance count exceeds native draw limit");
    if (selection.index_bytes != 0 && selection.index_bytes != 1 &&
        selection.index_bytes != 2 && selection.index_bytes != 4)
        throw std::runtime_error("DRAW inputs: unsupported index width");
    if (selection.index_bytes && selection.count > selection.indices.size() / selection.index_bytes)
        throw std::runtime_error("DRAW inputs: index selection exceeds its revision");
    if (!selection.index_bytes && selection.count &&
        (selection.first > UINT32_MAX || selection.count - 1 > UINT32_MAX - selection.first))
        throw std::runtime_error("DRAW inputs: original vertex identity exceeds uint32");
}

// Admission for whole BufferRev uploads, after selection/source validation.
// Native index binding supports uint16/uint32 only; an unconverted uint8
// selection must enter compact remapping even when its backing bytes fit.
inline bool direct_uploads_fit(const Selection& selection, std::span<const Source> sources,
                               uint64_t max_buffer_bytes) {
    if (selection.index_bytes && (selection.index_bytes != 2 && selection.index_bytes != 4)) return false;
    if (selection.index_bytes && selection.indices.size() > max_buffer_bytes) return false;
    return std::all_of(sources.begin(), sources.end(), [&](const auto& source) {
        return source.bytes.size() <= max_buffer_bytes;
    });
}

inline bool u8_widening_fits(uint64_t count, uint64_t max_buffer_bytes) {
    return count <= max_buffer_bytes / 2;
}

inline uint32_t maximum_vertex(const Selection& selection) {
    validate_selection(selection);
    uint32_t maximum = 0;
    if (!selection.count || !selection.instances) return maximum;
    if (!selection.index_bytes) return static_cast<uint32_t>(selection.first + selection.count - 1);
    for (uint64_t n = 0; n < selection.count; ++n) maximum = std::max(maximum, selection.vertex(n));
    return maximum;
}

inline size_t source_address(const Source& source, uint64_t element) {
    if (source.offset > source.bytes.size() ||
        (source.stride && element > (source.bytes.size() - source.offset) / source.stride))
        throw std::runtime_error("ATTRIBUTE " + std::string(source.name) + ": input element exceeds source revision");
    const uint64_t start = source.offset + element * source.stride;
    if (source.element_bytes > source.bytes.size() - start)
        throw std::runtime_error("ATTRIBUTE " + std::string(source.name) + ": input payload exceeds source revision");
    return static_cast<size_t>(start);
}

inline void validate_sources(const Selection& selection, std::span<const Source> sources, uint32_t maximum) {
    validate_selection(selection);
    if (!selection.count || !selection.instances) return;
    for (const auto& source : sources) {
        if (source.element_bytes != 4 && source.element_bytes != 8 &&
            source.element_bytes != 12 && source.element_bytes != 16)
            throw std::runtime_error("ATTRIBUTE " + std::string(source.name) + ": unsupported input width");
        source_address(source, source.divisor ? (selection.instances - 1) / source.divisor : maximum);
    }
}

struct Stream {
    uint64_t bind_offset = 0;
    uint32_t stride = 0;
    bool instance = false;
    std::vector<size_t> fields;
};

struct Layout {
    std::vector<Stream> streams;
    std::vector<uint32_t> slots, offsets;
    bool direct = false;
};

inline Layout direct_layout(std::span<const Source> sources, uint32_t max_attributes,
                            uint32_t max_buffers, uint32_t max_stride) {
    if (sources.size() > max_attributes)
        throw std::runtime_error("DRAW inputs: active user inputs=" + std::to_string(sources.size()) +
                                 " exceed granted attribute limit=" + std::to_string(max_attributes));
    Layout layout;
    layout.slots.resize(sources.size()); layout.offsets.resize(sources.size());
    std::vector<size_t> ordered;
    ordered.reserve(sources.size());
    for (size_t n = 0; n < sources.size(); ++n) {
        const auto& source = sources[n];
        if (source.offset > UINT64_MAX - source.element_bytes)
            throw std::runtime_error("ATTRIBUTE " + std::string(source.name) + ": input offset plus width overflows uint64");
        if ((source.element_bytes != 4 && source.element_bytes != 8 &&
             source.element_bytes != 12 && source.element_bytes != 16) ||
            source.divisor > 1 || source.offset % 4 || source.stride % 4 ||
            source.stride > max_stride) return {};
        ordered.push_back(n);
    }
    // Group each revision's increasing offsets so declaration order cannot
    // consume an extra slot by joining an overlapping middle interval first.
    // Fields retain their original shader locations through slots/offsets.
    std::stable_sort(ordered.begin(), ordered.end(), [&](size_t a, size_t b) {
        return sources[a].offset < sources[b].offset;
    });
    for (size_t n : ordered) {
        const auto& source = sources[n];
        bool grouped = false;
        for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
            auto& stream = layout.streams[slot];
            const auto& first = sources[stream.fields.front()];
            if (source.identity != first.identity || source.revision != first.revision ||
                source.stride != first.stride || (source.divisor != 0) != stream.instance) continue;
            const uint64_t base = std::min(source.offset, stream.bind_offset);
            uint64_t tail = source.offset - base + source.element_bytes;
            for (size_t field : stream.fields)
                tail = std::max(tail, sources[field].offset - base + sources[field].element_bytes);
            if (tail > (source.stride ? source.stride : max_stride)) continue;
            stream.bind_offset = base;
            stream.fields.push_back(n);
            layout.slots[n] = static_cast<uint32_t>(slot);
            for (size_t field : stream.fields)
                layout.offsets[field] = static_cast<uint32_t>(sources[field].offset - base);
            grouped = true; break;
        }
        if (grouped) continue;
        if (source.element_bytes > (source.stride ? source.stride : max_stride)) return {};
        layout.slots[n] = static_cast<uint32_t>(layout.streams.size());
        layout.streams.push_back({source.offset, static_cast<uint32_t>(source.stride), source.divisor != 0, {n}});
    }
    if (layout.streams.size() > max_buffers) return {};
    std::stable_sort(layout.streams.begin(), layout.streams.end(), [](const auto& a, const auto& b) {
        return *std::min_element(a.fields.begin(),a.fields.end()) < *std::min_element(b.fields.begin(),b.fields.end());
    });
    for (size_t slot=0; slot<layout.streams.size(); ++slot)
        for (size_t field:layout.streams[slot].fields) layout.slots[field]=static_cast<uint32_t>(slot);
    layout.direct = true;
    return layout;
}

// Field locations need not be contiguous within a physical buffer. Search for
// an exact packing: first-fit/contiguous splitting can exceed the buffer grant
// even when another legal partition exists. Widths have only four possible
// values and active attributes are bounded by the device's public grant.
inline Layout partition_layout(std::span<const uint32_t> widths,
                               std::span<const uint8_t> instance_steps,
                               uint32_t max_attributes, uint32_t max_buffers,
                               uint32_t max_stride) {
    if (widths.size() > max_attributes)
        throw std::runtime_error("DRAW inputs: active user inputs=" + std::to_string(widths.size()) +
                                 " exceed granted attribute limit=" + std::to_string(max_attributes));
    if (!instance_steps.empty() && instance_steps.size() != widths.size())
        throw std::runtime_error("DRAW inputs: field step count differs from active inputs");
    uint64_t total = 0;
    for (size_t n = 0; n < widths.size(); ++n) {
        const auto bytes = widths[n];
        if (bytes != 4 && bytes != 8 && bytes != 12 && bytes != 16)
            throw std::runtime_error("DRAW inputs: unsupported packed attribute width");
        if (bytes > max_stride)
            throw std::runtime_error("DRAW inputs: one compact field exceeds granted vertex stride");
        if (!instance_steps.empty() && instance_steps[n] > 1)
            throw std::runtime_error("DRAW inputs: invalid field step category");
        total += bytes;
    }
    Layout result;
    result.slots.resize(widths.size()); result.offsets.resize(widths.size());
    const uint32_t capacity = std::min<uint64_t>(max_stride / 4, total / 4);
    for (bool instance : {false, true}) {
        std::vector<size_t> fields;
        uint64_t words = 0;
        for (size_t n = 0; n < widths.size(); ++n) {
            if ((!instance_steps.empty() && instance_steps[n] != 0) != instance) continue;
            fields.push_back(n); words += widths[n] / 4;
        }
        if (fields.empty()) continue;
        std::stable_sort(fields.begin(), fields.end(), [&](size_t a, size_t b) { return widths[a] > widths[b]; });
        const size_t available = max_buffers - result.streams.size();
        const size_t minimum = static_cast<size_t>((words + capacity - 1) / capacity);
        std::vector<size_t> assigned(fields.size());
        size_t bins = minimum;
        bool packed = false;
        for (; bins <= available && bins <= fields.size(); ++bins) {
            std::vector<uint32_t> remaining(bins, capacity);
            std::unordered_set<std::string> failed;
            auto search = [&](auto&& self, size_t at) -> bool {
                if (at == fields.size()) return true;
                auto canonical = remaining;
                std::sort(canonical.begin(), canonical.end());
                std::string key = std::to_string(at);
                for (auto free : canonical) key += ':' + std::to_string(free);
                if (failed.contains(key)) return false;
                const uint32_t width = widths[fields[at]] / 4;
                std::vector<uint32_t> tried;
                for (size_t slot = 0; slot < bins; ++slot) {
                    const uint32_t free = remaining[slot];
                    if (free < width || std::find(tried.begin(), tried.end(), free) != tried.end()) continue;
                    tried.push_back(free);
                    remaining[slot] -= width; assigned[at] = slot;
                    if (self(self, at + 1)) return true;
                    remaining[slot] += width;
                }
                failed.insert(std::move(key));
                return false;
            };
            if (search(search, 0)) { packed = true; break; }
        }
        if (!packed)
            throw std::runtime_error("DRAW inputs: compact fields have no representation within granted vertex stride/buffer limits");
        std::vector<Stream> streams(bins);
        for (auto& stream : streams) stream.instance = instance;
        for (size_t n = 0; n < fields.size(); ++n) streams[assigned[n]].fields.push_back(fields[n]);
        for (auto& stream : streams) std::sort(stream.fields.begin(), stream.fields.end());
        std::sort(streams.begin(), streams.end(), [](const auto& a, const auto& b) { return a.fields.front() < b.fields.front(); });
        for (auto& stream : streams) {
            const uint32_t slot = static_cast<uint32_t>(result.streams.size());
            for (size_t field : stream.fields) {
                result.slots[field] = slot; result.offsets[field] = stream.stride;
                stream.stride += widths[field];
            }
            result.streams.push_back(std::move(stream));
        }
    }
    return result;
}

inline Layout compact_layout(std::span<const Source> sources, uint32_t max_attributes,
                             uint32_t max_buffers, uint32_t max_stride) {
    if (sources.size() > max_attributes)
        throw std::runtime_error("DRAW inputs: active user inputs=" + std::to_string(sources.size()) +
                                 " exceed granted attribute limit=" + std::to_string(max_attributes));
    std::vector<uint32_t> widths;
    std::vector<uint8_t> steps;
    widths.reserve(sources.size()); steps.reserve(sources.size());
    for (const auto& source : sources) {
        if (source.element_bytes != 4 && source.element_bytes != 8 &&
            source.element_bytes != 12 && source.element_bytes != 16)
            throw std::runtime_error("DRAW inputs: unsupported packed attribute width");
        widths.push_back(static_cast<uint32_t>(source.element_bytes));
        steps.push_back(source.divisor != 0);
    }
    return partition_layout(widths, steps, max_attributes, max_buffers, max_stride);
}

struct IndexedSelection {
    std::vector<uint32_t> identities;
    std::vector<uint32_t> indices;
};

inline uint64_t compact_vertex_capacity(const Selection& selection, const Layout& layout,
                                        uint64_t max_buffer_bytes, uint64_t max_storage_bytes,
                                        bool identity_storage) {
    validate_selection(selection);
    if (identity_storage && (max_buffer_bytes < 4 || max_storage_bytes < 4))
        throw std::runtime_error("DRAW inputs: exact vertex identities require four granted storage bytes");
    uint64_t capacity = selection.index_bytes ? max_buffer_bytes / 4 : UINT64_MAX;
    if (selection.index_bytes && identity_storage) capacity = std::min(capacity, max_storage_bytes / 4);
    for (const auto& stream : layout.streams) {
        if (!stream.stride) throw std::runtime_error("DRAW inputs: compact stream has zero stride");
        if (stream.instance) {
            if (selection.instances > max_buffer_bytes / stream.stride)
                throw std::runtime_error("DRAW inputs: combined instance stream exceeds granted allocation limit; field partitioning or ordered batching is required");
        } else capacity = std::min(capacity, max_buffer_bytes / stream.stride);
    }
    if (!selection.index_bytes && selection.count > capacity)
        throw std::runtime_error("DRAW inputs: combined vertex stream exceeds granted allocation limit; field partitioning or ordered batching is required");
    return capacity;
}

inline IndexedSelection compact_indices(const Selection& selection, uint64_t max_buffer_bytes,
                                         uint64_t max_unique_vertices) {
    validate_selection(selection);
    if (!selection.index_bytes) throw std::runtime_error("DRAW inputs: indexed remapping requires indices");
    if (!selection.count || !selection.instances) return {};
    if (selection.count > max_buffer_bytes / 4 || selection.count > SIZE_MAX / 4)
        throw std::runtime_error("DRAW inputs: remapped index stream exceeds granted allocation limit");
    if (!max_unique_vertices) throw std::runtime_error("DRAW inputs: combined vertex/identity stream has no granted row capacity");
    IndexedSelection result;
    result.indices.reserve(static_cast<size_t>(selection.count));
    std::unordered_map<uint32_t, uint32_t> unique;
    for (uint64_t n = 0; n < selection.count; ++n) {
        const uint32_t original = selection.vertex(n);
        auto found = unique.find(original);
        if (found == unique.end()) {
            if (result.identities.size() >= max_unique_vertices || result.identities.size() >= INT32_MAX)
                throw std::runtime_error("DRAW inputs: combined compact vertex/identity stream exceeds granted allocation limit; field partitioning or ordered batching is required");
            const uint32_t compact = static_cast<uint32_t>(result.identities.size());
            found = unique.emplace(original, compact).first;
            result.identities.push_back(original);
        }
        result.indices.push_back(found->second);
    }
    return result;
}

// Only selected indices are converted. A resident source may be larger than
// the selected prefix, and unused trailing bytes do not consume a child grant.
inline std::vector<uint8_t> widen_u8(const Selection& selection, uint64_t max_buffer_bytes) {
    validate_selection(selection);
    if (selection.index_bytes != 1) throw std::runtime_error("DRAW inputs: byte widening requires uint8 indices");
    if (!selection.count || !selection.instances) return {};
    if (selection.count > max_buffer_bytes / 2 || selection.count > SIZE_MAX / 2)
        throw std::runtime_error("DRAW inputs: widened index stream exceeds granted allocation limit");
    std::vector<uint8_t> result(static_cast<size_t>(selection.count * 2));
    for (uint64_t n = 0; n < selection.count; ++n) {
        const uint16_t value = static_cast<uint16_t>(selection.vertex(n));
        std::memcpy(result.data() + n * 2, &value, 2);
    }
    return result;
}

inline std::vector<uint8_t> topology_indices(const Selection& selection, bool fan, uint64_t max_buffer_bytes) {
    validate_selection(selection);
    if (!selection.count || !selection.instances) return {};
    const uint64_t count = selection.count;
    const uint64_t output_count = fan ? (count >= 3 ? (count - 2) * 3 : 0) : (count >= 2 ? count + 1 : 0);
    if (output_count > INT32_MAX || output_count > max_buffer_bytes / 4 || output_count > SIZE_MAX / 4)
        throw std::runtime_error("DRAW inputs: expanded primitive exceeds granted allocation/count limit");
    std::vector<uint8_t> result(static_cast<size_t>(output_count * 4));
    size_t position = 0;
    auto emit = [&](uint32_t value) { std::memcpy(result.data() + position++ * 4, &value, 4); };
    if (fan) {
        for (uint64_t n = 1; n + 1 < count; ++n) {
            emit(selection.vertex(0)); emit(selection.vertex(n)); emit(selection.vertex(n + 1));
        }
    } else if (count >= 2) {
        for (uint64_t n = 0; n < count; ++n) emit(selection.vertex(n));
        emit(selection.vertex(0));
    }
    return result;
}

inline std::vector<uint8_t> pack_stream(const Selection& selection, std::span<const Source> sources,
                                      const Stream& stream, std::span<const uint32_t> vertices,
                                      uint64_t max_buffer_bytes) {
    validate_selection(selection);
    const uint64_t rows = stream.instance ? selection.instances : selection.index_bytes ? vertices.size() : selection.count;
    if (!selection.count || !selection.instances || stream.fields.empty()) return {};
    if (!stream.stride || rows > max_buffer_bytes / stream.stride || rows > SIZE_MAX / stream.stride)
        throw std::runtime_error("DRAW inputs: combined compact stream exceeds granted allocation limit; field partitioning or ordered batching is required");
    uint64_t stride = 0;
    for (size_t field : stream.fields) {
        if (field >= sources.size() || (sources[field].divisor != 0) != stream.instance)
            throw std::runtime_error("DRAW inputs: compact stream field differs from source");
        stride += sources[field].element_bytes;
    }
    if (stride != stream.stride) throw std::runtime_error("DRAW inputs: compact stream stride differs from source");
    uint32_t maximum = 0;
    if (!stream.instance) {
        if (selection.index_bytes) {
            for (uint32_t vertex : vertices) maximum = std::max(maximum, vertex);
        } else maximum = maximum_vertex(selection);
    }
    for (size_t field : stream.fields)
        source_address(sources[field], stream.instance ? (selection.instances - 1) / sources[field].divisor : maximum);
    std::vector<uint8_t> result(static_cast<size_t>(rows * stream.stride));
    for (uint64_t row = 0; row < rows; ++row) {
        size_t offset = 0;
        for (size_t field : stream.fields) {
            const auto& source = sources[field];
            const uint64_t element = stream.instance ? row / source.divisor :
                selection.index_bytes ? vertices[static_cast<size_t>(row)] : selection.first + row;
            std::memcpy(result.data() + row * stream.stride + offset,
                        source.bytes.data() + source_address(source, element), static_cast<size_t>(source.element_bytes));
            offset += static_cast<size_t>(source.element_bytes);
        }
    }
    return result;
}

inline std::string selection_key(const Selection& selection, uint64_t index_identity, uint64_t index_revision) {
    return std::to_string(index_identity) + ':' + std::to_string(index_revision) + ':' +
        std::to_string(selection.index_bytes) + ':' + std::to_string(selection.first) + ':' + std::to_string(selection.count);
}

inline std::string source_key(std::span<const Source> sources) {
    // The Program's LINK reset owns interface changes. Ordered field values
    // identify geometry exactly without copying arbitrarily long shader names
    // into every cache key and source stamp.
    std::string key="input-sources";
    for (const auto& source:sources) {
        key+=';';
        for (uint64_t value:{source.identity,source.revision,source.offset,source.stride,source.element_bytes,source.divisor})
            key+=':'+std::to_string(value);
    }
    return key;
}

// One exact dependency stamp for the whole vertex or instance category. A
// partitioned category is one cache/current owner with stream children; the
// partition shape must not alias another legal physical representation.
// Preserve the original single-stream stamp byte for byte.
inline std::string partition_source_key(const Layout& layout, std::span<const Source> sources,
                                        bool instance) {
    if (layout.slots.size() != sources.size() || layout.offsets.size() != sources.size())
        throw std::runtime_error("DRAW inputs: partition map differs from source count");
    std::vector<Source> fields;
    for (const auto& source : sources)
        if ((source.divisor != 0) == instance) fields.push_back(source);
    std::string key = source_key(fields);
    std::vector<size_t> streams;
    std::vector<bool> seen(sources.size());
    for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
        const auto& stream = layout.streams[slot];
        if (stream.instance != instance) continue;
        streams.push_back(slot);
        for (size_t field : stream.fields) {
            if (field >= sources.size() || (sources[field].divisor != 0) != instance || seen[field] ||
                layout.slots[field] != slot || layout.offsets[field] > stream.stride ||
                sources[field].element_bytes > stream.stride - layout.offsets[field])
                throw std::runtime_error("DRAW inputs: invalid compact partition dependency map");
            seen[field] = true;
        }
    }
    for (size_t field = 0; field < sources.size(); ++field)
        if ((sources[field].divisor != 0) == instance && !seen[field])
            throw std::runtime_error("DRAW inputs: partition dependency map omits source");
    if (streams.size() <= 1) return key;
    key += ":partitions=" + std::to_string(streams.size());
    for (size_t slot : streams) {
        const auto& stream = layout.streams[slot];
        key += ":stride=" + std::to_string(stream.stride);
        for (size_t field : stream.fields)
            key += ":field=" + std::to_string(field) + ',' + std::to_string(layout.offsets[field]);
    }
    return key;
}

template<class Map> void discard_category(Map& cache, const std::string& prefix) {
    for (auto it = cache.begin(); it != cache.end();) {
        if (it->first.starts_with(prefix)) it = cache.erase(it); else ++it;
    }
}

// One current owner for each ordinary/endpoint conversion category. These owners are
// independent of the bounded historical cache: a legal oversized conversion
// remains resident after snapshots/Tickets retire, without retaining sources.
enum class CurrentCategory : size_t { IndexWiden, Topology, Bounds, Selection, Vertex, Instance, LineEndpoint, Batch, CompactFit, Count };

template<class Record> class CurrentConversions {
public:
    struct Entry { std::string key; Record record; };
    static constexpr size_t category_count = static_cast<size_t>(CurrentCategory::Count);
    class Prepared {
        friend class CurrentConversions;
        size_t slot_;
        Entry entry_;
        Prepared(size_t slot, const std::string& key, Record record)
            : slot_(slot), entry_{key, std::move(record)} {}
    };

    Record find(CurrentCategory category, const std::string& key) const {
        const auto& entry = entries_.at(static_cast<size_t>(category));
        return entry.record && entry.key == key ? entry.record : Record{};
    }
    Prepared prepare(CurrentCategory category, const std::string& key, Record record) const {
        const auto slot = static_cast<size_t>(category);
        (void)entries_.at(slot);  // Validate before any other cache is published.
        return Prepared(slot, key, std::move(record));
    }
    void publish(Prepared&& next) noexcept {
        // The key is already allocated and the category validated. Record is
        // a shared_ptr, so both owner swaps are allocation-free.
        auto& entry = entries_[next.slot_];
        entry.key.swap(next.entry_.key);
        entry.record.swap(next.entry_.record);
    }
    void replace(CurrentCategory category, const std::string& key, Record record) {
        publish(prepare(category, key, std::move(record)));
    }
    void clear(CurrentCategory category) {
        entries_.at(static_cast<size_t>(category)) = Entry{};
    }
    void clear() { for (auto& entry : entries_) entry = Entry{}; }
    size_t size() const {
        return std::count_if(entries_.begin(), entries_.end(), [](const auto& entry) { return bool(entry.record); });
    }
    template<class Visit> void for_each(Visit&& visit) const {
        for (size_t n = 0; n < entries_.size(); ++n) {
            const auto& entry = entries_[n];
            if (entry.record) visit(static_cast<CurrentCategory>(n), entry.key, entry.record);
        }
    }
private:
    std::array<Entry, category_count> entries_{};
};

inline constexpr size_t oversized_entry_limit = 8;
inline constexpr uint64_t oversized_byte_limit = 256ull * 1024 * 1024;

inline uint64_t bounded_cost_add(uint64_t left, uint64_t right) {
    return right > UINT64_MAX - left ? UINT64_MAX : left + right;
}

// A separate shared per-Program working set for records too large for ordinary
// history. Current owners and pending work may overlap this graph; this budget
// charges its own occupied entries/keys and each retained record/child once.
// Hits move to the front; capacity evicts least-recently-used entries. Explicit
// invalidation/deletion does not count as a capacity eviction.
template<class Record> class OversizedConversions {
public:
    struct Entry { CurrentCategory category; std::string key; Record record; };
    explicit OversizedConversions(size_t entries = oversized_entry_limit,
            uint64_t bytes = oversized_byte_limit)
        : entry_limit_(std::min(entries, oversized_entry_limit)),
          byte_limit_(std::min(bytes, oversized_byte_limit)) {}

    // std::list move construction can allocate its sentinel on MSVC. A cache
    // transaction commits with list::swap instead, which transfers all owners
    // without moving nodes or allocating new list control storage.
    void swap(OversizedConversions& other) noexcept {
        entries_.swap(other.entries_);
        using std::swap;
        swap(entry_limit_, other.entry_limit_);
        swap(byte_limit_, other.byte_limit_);
        swap(evictions_, other.evictions_);
    }
    friend void swap(OversizedConversions& left, OversizedConversions& right) noexcept {
        left.swap(right);
    }

    Record find(CurrentCategory category, const std::string& key) {
        for (auto it = entries_.begin(); it != entries_.end(); ++it) {
            if (it->category == category && it->key == key) {
                entries_.splice(entries_.begin(), entries_, it);
                return entries_.front().record;
            }
        }
        return {};
    }
    Record peek(CurrentCategory category, const std::string& key) const {
        for (const auto& entry : entries_)
            if (entry.category == category && entry.key == key) return entry.record;
        return {};
    }
    size_t size() const { return entries_.size(); }
    size_t entry_limit() const { return entry_limit_; }
    uint64_t byte_limit() const { return byte_limit_; }
    uint64_t evictions() const { return evictions_; }
    static uint64_t entry_bytes(const std::string& key) {
        return bounded_cost_add(sizeof(Entry) + 2 * sizeof(void*), key.capacity());
    }
    template<class Bytes> uint64_t storage_bytes(Bytes&& bytes,
            std::unordered_set<const void*>& visited) const {
        uint64_t total = 0;
        for (const auto& entry : entries_) {
            total = bounded_cost_add(total, entry_bytes(entry.key));
            total = bounded_cost_add(total, bytes(entry.record, visited));
        }
        return total;
    }
    template<class Bytes> uint64_t storage_bytes(Bytes&& bytes) const {
        std::unordered_set<const void*> visited;
        return storage_bytes(std::forward<Bytes>(bytes), visited);
    }
    template<class Bytes> bool admit(CurrentCategory category, const std::string& key,
            Record record, Bytes&& bytes) {
        if (!record || !entry_limit_ || !byte_limit_) return false;
        // Allocate the new entry/key and evaluate all footprints before
        // removing existing owners. A throwing builder/footprint/key allocation
        // leaves resident history intact; publication uses noexcept list moves.
        std::list<Entry> next;
        next.push_front({category, key, std::move(record)});
        auto footprint = [&](size_t keep) {
            std::unordered_set<const void*> visited;
            uint64_t total = bounded_cost_add(entry_bytes(next.front().key),
                                             bytes(next.front().record, visited));
            size_t retained = 0;
            for (const auto& entry : entries_) {
                if (entry.category == category && entry.key == key) continue;
                if (retained++ == keep) break;
                total = bounded_cost_add(total, entry_bytes(entry.key));
                total = bounded_cost_add(total, bytes(entry.record, visited));
            }
            return total;
        };
        if (footprint(0) > byte_limit_) return false;
        size_t keep = std::min(entries_.size(), entry_limit_ - 1);
        while (footprint(keep) > byte_limit_) --keep;
        for (auto it = entries_.begin(); it != entries_.end();) {
            if (it->category == category && it->key == key) it = entries_.erase(it);
            else ++it;
        }
        while (entries_.size() > keep) {
            entries_.pop_back();
            ++evictions_;
        }
        entries_.splice(entries_.begin(), next);
        return true;
    }
    void clear(CurrentCategory category) {
        entries_.remove_if([&](const auto& entry) { return entry.category == category; });
    }
    void clear() { entries_.clear(); }
    template<class Visit> void for_each(Visit&& visit) const {
        for (const auto& entry : entries_) visit(entry.category, entry.key, entry.record);
    }
private:
    std::list<Entry> entries_;
    size_t entry_limit_;
    uint64_t byte_limit_, evictions_ = 0;
};

// One budget covers all cache categories. The caller's byte function charges
// owned payload/record children; keys and map record bookkeeping are charged
// here. Oversized results stay owned by the caller but are never admitted.
template<class Map, class Build, class Bytes>
auto cached_conversion(Map& cache, const std::string& key, Build&& build, Bytes&& bytes,
                       size_t entry_limit = cache_entry_limit, uint64_t byte_limit = cache_byte_limit) {
    using Record = typename Map::mapped_type;
    if (auto found = cache.find(key); found != cache.end()) return std::pair<Record, bool>{found->second, false};
    Record record = std::forward<Build>(build)();
    auto cost = [&](const auto& identity, const Record& item) {
        const uint64_t payload = bytes(item);
        const uint64_t overhead = static_cast<uint64_t>(sizeof(typename Map::value_type)) +
            cache_entry_bookkeeping + identity.capacity();
        return payload > UINT64_MAX - overhead ? UINT64_MAX : payload + overhead;
    };
    const uint64_t required = cost(key, record);
    if (!entry_limit || required > byte_limit) return std::pair<Record, bool>{std::move(record), true};
    uint64_t used = 0;
    for (const auto& [identity, item] : cache) {
        const auto amount = cost(identity, item);
        if (amount > byte_limit || used > byte_limit - amount) {
            cache.clear(); used = 0; break;
        }
        used += amount;
    }
    while (!cache.empty() && (cache.size() >= entry_limit || used > byte_limit - required)) {
        const auto it = cache.begin(); used -= cost(it->first, it->second); cache.erase(it);
    }
    cache.emplace(key, record);
    return std::pair<Record, bool>{std::move(record), true};
}

template<class Map, class Build, class Bytes>
auto current_cached_conversion(CurrentConversions<typename Map::mapped_type>& current,
                               CurrentCategory category, Map& history, const std::string& key,
                               Build&& build, Bytes&& bytes, size_t entry_limit = cache_entry_limit,
                               uint64_t byte_limit = cache_byte_limit) {
    using Record = typename Map::mapped_type;
    if (auto record = current.find(category, key)) return std::pair<Record, bool>{std::move(record), false};
    auto result = cached_conversion(history, key, std::forward<Build>(build), std::forward<Bytes>(bytes),
                                    entry_limit, byte_limit);
    // A throwing builder leaves the old current owner and historical cache
    // untouched. Adopting a historical hit also stabilizes child identities.
    current.replace(category, key, result.first);
    return result;
}

struct PrepareCurrentConversion {
    template<class Current, class Record>
    auto operator()(const Current& current, CurrentCategory category,
                    const std::string& key, Record record) const {
        return current.prepare(category, key, std::move(record));
    }
};

template<class Map, class Build, class Bytes, class GraphBytes, class Prepare = PrepareCurrentConversion>
auto working_cached_conversion(CurrentConversions<typename Map::mapped_type>& current,
        OversizedConversions<typename Map::mapped_type>& oversized, CurrentCategory category,
        Map& history, const std::string& key, Build&& build, Bytes&& bytes, GraphBytes&& graph_bytes,
        size_t entry_limit = cache_entry_limit, uint64_t byte_limit = cache_byte_limit,
        Prepare prepare_current = {}) {
    using Record = typename Map::mapped_type;
    if (auto record = current.find(category, key)) {
        oversized.find(category, key);
        return std::pair<Record, bool>{std::move(record), false};
    }
    if (auto record = oversized.peek(category, key)) {
        auto prepared = prepare_current(current, category, key, record);
        oversized.find(category, key);
        current.publish(std::move(prepared));
        return std::pair<Record, bool>{std::move(record), false};
    }
    auto result = cached_conversion(history, key, std::forward<Build>(build), bytes, entry_limit, byte_limit);
    // Allocate the current key before oversized admission can evict anything.
    // Admission performs all throwing footprint work before its own commit;
    // the following current publication is then allocation-free.
    auto prepared = prepare_current(current, category, key, result.first);
    const auto overhead = bounded_cost_add(sizeof(typename Map::value_type) + cache_entry_bookkeeping, key.capacity());
    if (bounded_cost_add(bytes(result.first), overhead) > byte_limit)
        oversized.admit(category, key, result.first, std::forward<GraphBytes>(graph_bytes));
    current.publish(std::move(prepared));
    return result;
}

}  // namespace vispy::inputs
