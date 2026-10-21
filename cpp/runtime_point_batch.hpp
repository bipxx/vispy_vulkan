#pragma once

// Bounded point payload preparation. Runtime cache ownership/publication and
// physical encoding consume the separately prepared owning draw descriptors.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4267) // Existing partition_layout size_t -> uint32_t warning.
#endif
#include "runtime_point_partition.hpp"
#ifdef _MSC_VER
#pragma warning(pop)
#endif

namespace vispy::points::batches {

// Each physical draw keeps the existing point identity ABI: a headerless
// uint32x2 {original vertex, original instance} per flattened row. The physical
// draw starts at instance zero; user attribute divisors use the original ID.
inline constexpr uint64_t identity_row_bytes = 8;
inline constexpr uint32_t physical_first_instance = 0;

struct Limits {
    uint64_t buffer_bytes = 0;
    uint64_t storage_bytes = 0;
    uint64_t max_control_bytes = 0;
    uint64_t max_encoded_draws = 0;
};

struct Range { uint64_t first = 0, count = 0; };

inline uint64_t checked_product(uint64_t a, uint64_t b) {
    if (a && b > UINT64_MAX / a)
        throw std::length_error("DRAW point batches: row-byte multiplication overflow");
    return a * b;
}

inline void validate_packed_layout(std::span<const PackedSource> sources, const PackedLayout& layout) {
    if (layout.offsets.size() != sources.size())
        throw std::runtime_error("DRAW point batches: packed layout differs from source fields");
    uint64_t stride = 0;
    for (size_t field = 0; field < sources.size(); ++field) {
        const uint64_t bytes = sources[field].element_bytes;
        if ((bytes != 4 && bytes != 8 && bytes != 12 && bytes != 16) ||
            layout.offsets[field] != stride)
            throw std::runtime_error("DRAW point batches: packed layout differs from source fields");
        stride += bytes;
        if (stride > UINT32_MAX)
            throw std::runtime_error("DRAW point batches: packed stride exceeds uint32");
    }
    if (stride != layout.stride)
        throw std::runtime_error("DRAW point batches: packed stride differs from source fields");
}

struct PartitionShape {
    uint32_t stride = 0, maximum_stride = 0, streams = 0;
    std::array<uint64_t, 2> map{};
    bool operator==(const PartitionShape&) const = default;
};

// A bounded structural fingerprint detects replacement of a caller's physical
// map between planning and packing. Runtime cache keys use the exact map text.
inline PartitionShape partition_shape(std::span<const PackedSource> sources, const inputs::Layout& layout) {
    validate_partitioned_layout(sources, layout);
    PartitionShape result;
    result.streams = static_cast<uint32_t>(layout.streams.size());
    result.map = {14695981039346656037ull, 1099511628211ull};
    auto append = [&](uint64_t value) {
        for (unsigned byte = 0; byte < 8; ++byte) {
            const auto part = static_cast<uint8_t>(value >> (byte * 8));
            result.map[0] = (result.map[0] ^ part) * 1099511628211ull;
            result.map[1] = (result.map[1] + part + 0x9e3779b97f4a7c15ull) * 0xbf58476d1ce4e5b9ull;
            result.map[1] ^= result.map[1] >> 29;
        }
    };
    append(sources.size()); append(layout.streams.size());
    for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
        const auto& stream = layout.streams[slot];
        result.stride += stream.stride;
        result.maximum_stride = std::max(result.maximum_stride, stream.stride);
        append(slot); append(stream.stride); append(stream.fields.size());
        for (size_t field : stream.fields) {
            append(field); append(layout.offsets[field]); append(sources[field].element_bytes);
        }
    }
    return result;
}

class Plan {
public:
    Plan(const Plan&) = default;
    Plan(Plan&&) = default;
    Plan& operator=(const Plan&) = default;
    Plan& operator=(Plan&&) = default;

    const Selection& selection() const { return selection_; }
    const Limits& limits() const { return limits_; }
    uint64_t total_rows() const { return total_rows_; }
    uint64_t rows_per_batch() const { return rows_per_batch_; }
    uint64_t encoded_draws() const { return encoded_draws_; }
    uint64_t control_bytes() const { return total_rows_ ? sizeof(Plan) : 0; }
    uint32_t packed_stride() const { return packed_stride_; }
    uint32_t stream_count() const { return shape_.streams; }
    uint32_t max_stream_stride() const { return shape_.maximum_stride; }
    bool partitioned() const { return partitioned_; }
    void validate_layout(std::span<const PackedSource> sources, const inputs::Layout& layout) const {
        if (!partitioned_ || partition_shape(sources, layout) != shape_)
            throw std::runtime_error("DRAW point batches: physical partition differs from plan");
    }

    Range range(uint64_t number) const {
        if (number >= encoded_draws_)
            throw std::out_of_range("DRAW point batches: batch range outside plan");
        const uint64_t first = checked_product(number, rows_per_batch_);
        return {first, std::min(rows_per_batch_, total_rows_ - first)};
    }

private:
    Plan() = default;
    Selection selection_;
    Limits limits_;
    uint64_t total_rows_ = 0, rows_per_batch_ = 0, encoded_draws_ = 0;
    uint32_t packed_stride_ = 0;
    PartitionShape shape_;
    bool partitioned_ = false;

    friend Plan plan(const Selection&, std::span<const PackedSource>, const PackedLayout&, Limits);
    friend Plan plan(const Selection&, std::span<const PackedSource>, const inputs::Layout&, Limits);
};

// The plan owns no per-batch vector and borrows the selection's index revision.
// The caller must keep that revision immutable/alive until preparation ends.
// Control bytes charge the fixed logical Plan object, not allocator/RSS usage.
// Output caps apply to each separate identity/user buffer; retaining every
// batch simultaneously would require a separate aggregate residency budget.
inline Plan plan(const Selection& selection, std::span<const PackedSource> sources,
                 const PackedLayout& layout, Limits limits) {
    inputs::validate_selection(selection);
    Plan result;
    result.selection_ = selection;
    result.limits_ = limits;
    // Preserve zero-draw behavior: no layout, source read or allocation grant
    // is needed when either selected domain is empty.
    if (!selection.count || !selection.instances) return result;

    validate_packed_layout(sources, layout);
    result.packed_stride_ = layout.stride;
    result.shape_.stride = layout.stride;
    result.shape_.maximum_stride = layout.stride;
    result.shape_.streams = sources.empty() ? 0 : 1;
    result.total_rows_ = checked_product(selection.count, selection.instances);
    if (sizeof(Plan) > limits.max_control_bytes)
        throw std::length_error("DRAW point batches: explicit plan control-byte budget exceeded");

    uint64_t capacity = std::min({limits.buffer_bytes / identity_row_bytes,
        limits.storage_bytes / identity_row_bytes, uint64_t(SIZE_MAX / identity_row_bytes),
        uint64_t(INT32_MAX)});
    if (!sources.empty())
        capacity = std::min({capacity, limits.buffer_bytes / layout.stride,
                            uint64_t(SIZE_MAX / layout.stride)});
    if (!capacity)
        throw std::runtime_error("DRAW point batches: one flattened row exceeds granted buffer/storage limit");
    result.rows_per_batch_ = capacity;
    result.encoded_draws_ = result.total_rows_ / capacity + (result.total_rows_ % capacity != 0);
    if (result.encoded_draws_ > limits.max_encoded_draws)
        throw std::length_error("DRAW point batches: explicit encoded-draw budget exceeded");

    // Prove all source reads before any derived payload is allocated. Sparse
    // original IDs and divisor fetches retain their original global domains.
    if (!sources.empty())
        inputs::validate_sources(selection, sources, inputs::maximum_vertex(selection));
    return result;
}

inline Plan plan(const Selection& selection, std::span<const PackedSource> sources,
                 const inputs::Layout& layout, Limits limits) {
    inputs::validate_selection(selection);
    Plan result;
    result.selection_ = selection;
    result.limits_ = limits;
    result.partitioned_ = true;
    if (!selection.count || !selection.instances) return result;
    result.shape_ = partition_shape(sources, layout);
    result.packed_stride_ = result.shape_.stride;
    result.total_rows_ = checked_product(selection.count, selection.instances);
    if (sizeof(Plan) > limits.max_control_bytes)
        throw std::length_error("DRAW point batches: explicit plan control-byte budget exceeded");
    uint64_t capacity = std::min({limits.buffer_bytes / identity_row_bytes,
        limits.storage_bytes / identity_row_bytes, uint64_t(SIZE_MAX / identity_row_bytes), uint64_t(INT32_MAX)});
    if (result.max_stream_stride())
        capacity = std::min({capacity, limits.buffer_bytes / result.max_stream_stride(),
                            uint64_t(SIZE_MAX / result.max_stream_stride())});
    if (!capacity)
        throw std::runtime_error("DRAW point batches: one flattened row exceeds granted buffer/storage limit");
    result.rows_per_batch_ = capacity;
    result.encoded_draws_ = result.total_rows_ / capacity + (result.total_rows_ % capacity != 0);
    if (result.encoded_draws_ > limits.max_encoded_draws)
        throw std::length_error("DRAW point batches: explicit encoded-draw budget exceeded");
    if (!sources.empty())
        inputs::validate_sources(selection, sources, inputs::maximum_vertex(selection));
    return result;
}

inline std::vector<uint8_t> identity_data(const Plan& plan, uint64_t number) {
    const Range range = plan.range(number);
    const auto& selection = plan.selection();
    const uint64_t bytes = checked_product(range.count, identity_row_bytes);
    std::vector<uint8_t> result(static_cast<size_t>(bytes));
    for (uint64_t local = 0; local < range.count; ++local) {
        const uint64_t row = range.first + local;
        const uint32_t identity[] = {selection.vertex(row % selection.count),
                                    static_cast<uint32_t>(row / selection.count)};
        std::memcpy(result.data() + local * identity_row_bytes, identity, identity_row_bytes);
    }
    return result;
}

inline std::vector<uint8_t> packed_data(const Plan& plan, std::span<const PackedSource> sources,
                                      const PackedLayout& layout, uint64_t number) {
    const Range range = plan.range(number);
    validate_packed_layout(sources, layout);
    if (plan.partitioned() || layout.stride != plan.packed_stride())
        throw std::runtime_error("DRAW point batches: packed stride differs from plan");
    if (sources.empty()) return {};
    const auto& selection = plan.selection();

    // Recheck this range's reads before allocation, so a shortened/replaced
    // caller source fails before copying. No whole-selection scratch is used.
    uint32_t maximum_vertex = 0;
    for (uint64_t local = 0; local < range.count; ++local)
        maximum_vertex = std::max(maximum_vertex,
                                 selection.vertex((range.first + local) % selection.count));
    const uint64_t last_instance = (range.first + range.count - 1) / selection.count;
    for (const auto& source : sources)
        inputs::source_address(source, source.divisor ? last_instance / source.divisor : maximum_vertex);

    const uint64_t bytes = checked_product(range.count, layout.stride);
    std::vector<uint8_t> result(static_cast<size_t>(bytes));
    for (uint64_t local = 0; local < range.count; ++local) {
        const uint64_t row = range.first + local;
        const uint64_t instance = row / selection.count;
        const uint32_t vertex = selection.vertex(row % selection.count);
        for (size_t field = 0; field < sources.size(); ++field) {
            const auto& source = sources[field];
            const uint64_t element = source.divisor ? instance / source.divisor : vertex;
            const size_t start = inputs::source_address(source, element);
            std::memcpy(result.data() + local * layout.stride + layout.offsets[field],
                        source.bytes.data() + start, static_cast<size_t>(source.element_bytes));
        }
    }
    return result;
}

inline std::vector<uint8_t> packed_data(const Plan& plan, std::span<const PackedSource> sources,
        const inputs::Layout& layout, uint64_t number, uint32_t slot) {
    const Range range = plan.range(number);
    plan.validate_layout(sources, layout);
    if (slot >= layout.streams.size())
        throw std::out_of_range("DRAW point batches: stream slot outside partition");
    const auto& stream = layout.streams[slot];
    const auto& selection = plan.selection();
    uint32_t maximum_vertex = 0;
    for (uint64_t local = 0; local < range.count; ++local)
        maximum_vertex = std::max(maximum_vertex, selection.vertex((range.first + local) % selection.count));
    const uint64_t last_instance = (range.first + range.count - 1) / selection.count;
    for (size_t field : stream.fields) {
        const auto& source = sources[field];
        inputs::source_address(source, source.divisor ? last_instance / source.divisor : maximum_vertex);
    }
    const uint64_t bytes = checked_product(range.count, stream.stride);
    std::vector<uint8_t> result(static_cast<size_t>(bytes));
    for (uint64_t local = 0; local < range.count; ++local) {
        const uint64_t row = range.first + local, instance = row / selection.count;
        const uint32_t vertex = selection.vertex(row % selection.count);
        for (size_t field : stream.fields) {
            const auto& source = sources[field];
            const size_t start = inputs::source_address(source, source.divisor ? instance / source.divisor : vertex);
            std::memcpy(result.data() + local * stream.stride + layout.offsets[field],
                        source.bytes.data() + start, static_cast<size_t>(source.element_bytes));
        }
    }
    return result;
}

}  // namespace vispy::points::batches
