#pragma once

// Portable, staged experiment. This is not connected to runtime.cpp or a GPU.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4267) // Existing pinned partition_layout size_t -> uint32_t warning.
#endif
#include "runtime_point.hpp"
#ifdef _MSC_VER
#pragma warning(pop)
#endif
#include <functional>

namespace vispy::inputs::batches {

// A distinct, proposed ABI. Existing Affine/Indexed identity records do not use
// this header and must not be interpreted as these records by the runtime.
inline constexpr uint32_t identity_abi = 1;
inline constexpr uint64_t identity_header_bytes = 8;
struct IdentityHeader { uint32_t vertex_base, instance_base; };
static_assert(sizeof(IdentityHeader) == identity_header_bytes);

struct Limits {
    uint64_t buffer_bytes = 0;
    uint64_t storage_bytes = 0;
    uint64_t max_control_bytes = 0;
    uint64_t max_encoded_draws = 0;
};

inline uint64_t add(uint64_t a, uint64_t b) {
    if (b > UINT64_MAX - a) throw std::length_error("DRAW batches: checked addition overflow");
    return a + b;
}
inline uint64_t multiply(uint64_t a, uint64_t b) {
    if (a && b > UINT64_MAX / a) throw std::length_error("DRAW batches: checked multiplication overflow");
    return a * b;
}
inline uint64_t ceil_div(uint64_t a, uint64_t b) {
    if (!b) throw std::length_error("DRAW batches: zero divisor");
    return a / b + (a % b != 0);
}

struct GeometryBatch {
    uint64_t element_offset = 0, element_count = 0;
    uint32_t vertex_base = 0;
    std::vector<uint32_t> original_vertices, remapped_indices;
};

struct InstanceBlock { uint64_t first = 0, count = 0; };
struct DrawRef {
    size_t geometry = 0;
    uint64_t instance_base = 0, instance_count = 0;
    uint64_t instance_block = 0, row_offset = 0;
};

struct Plan {
    bool indexed = false;
    uint64_t selected_count = 0, instances = 0, incomplete_tail = 0;
    uint64_t instance_rows_per_block = 0, instance_block_count = 0;
    uint64_t encoded_draws = 0, control_bytes = 0;
    Limits limits;
    Layout layout;
    std::vector<GeometryBatch> geometry;

    InstanceBlock instance_block(uint64_t number) const {
        if (number >= instance_block_count) throw std::out_of_range("DRAW batches: instance block");
        const auto first = multiply(number, instance_rows_per_block);
        return {first, std::min(instance_rows_per_block, instances - first)};
    }
    template<class Visit> void for_each_draw(Visit&& visit) const {
        if (geometry.empty()) return;
        if (geometry.size() == 1) {
            for (uint64_t b = 0; b < instance_block_count; ++b) {
                const auto block = instance_block(b);
                visit(DrawRef{0, block.first, block.count, b, 0});
            }
        } else {
            // Preserve the original order: all primitives of instance i must
            // precede any primitive of instance i+1, including blend/stencil.
            for (uint64_t i = 0; i < instances; ++i)
                for (size_t g = 0; g < geometry.size(); ++g)
                    visit(DrawRef{g, i, 1, i / instance_rows_per_block, i % instance_rows_per_block});
        }
    }
};

// Each physical call references an existing full immutable geometry/ID table.
// A single geometry chunk must NOT coalesce instances for a two-face fallback.
struct StencilDrawRef { DrawRef draw; uint32_t first = 0, count = 0, face = 0; };
inline uint64_t stencil_face_draw_count(const Plan& plan) {
    uint64_t per_instance = 0;
    for (const auto& g : plan.geometry) {
        if (g.element_count > UINT32_MAX) throw std::length_error("DRAW stencil faces: geometry range exceeds uint32");
        per_instance = add(per_instance, add(multiply(g.element_count / 3, 2), uint64_t(g.element_count % 3 != 0)));
    }
    const auto calls = multiply(per_instance, plan.instances);
    if (calls > plan.limits.max_encoded_draws) throw std::length_error("DRAW stencil faces: expanded encoded-draw budget exceeded");
    return calls;
}
template<class Visit> void for_each_stencil_draw(const Plan& plan, Visit&& visit) {
    (void)stencil_face_draw_count(plan); // full checked admission before any callback
    if (plan.geometry.empty() || !plan.instances) return;
    if (!plan.instance_rows_per_block) throw std::runtime_error("DRAW stencil faces: missing instance block");
    for (uint64_t i = 0; i < plan.instances; ++i) for (size_t g = 0; g < plan.geometry.size(); ++g) {
        const auto count = plan.geometry[g].element_count;
        const DrawRef base{g, i, 1, i / plan.instance_rows_per_block, i % plan.instance_rows_per_block};
        uint64_t first = 0;
        for (; first + 3 <= count; first += 3) for (uint32_t face = 0; face < 2; ++face)
            visit(StencilDrawRef{base, static_cast<uint32_t>(first), 3, face});
        // Incomplete original inputs still get a real no-rasterization call.
        if (first != count) visit(StencilDrawRef{base, static_cast<uint32_t>(first), static_cast<uint32_t>(count - first), 0});
    }
}

// The control grant is a logical, portable representation charge: sizeof the
// owner/nodes and exact logical vector elements, including ID/index payloads.
// It is not an allocator-capacity, peak scratch, physical-memory or RSS claim.
inline void charge(Plan& plan, uint64_t bytes) {
    const auto next = add(plan.control_bytes, bytes);
    if (next > plan.limits.max_control_bytes || next > SIZE_MAX)
        throw std::length_error("DRAW batches: explicit plan control-byte budget exceeded");
    plan.control_bytes = next;
}

inline void validate_layout(const Layout& layout, std::span<const Source> sources) {
    if (layout.direct || layout.slots.size() != sources.size() || layout.offsets.size() != sources.size())
        throw std::runtime_error("DRAW batches: expected complete compact layout");
    // No scratch allocation is required for this bounded active-field check.
    for (size_t field = 0; field < sources.size(); ++field) {
        size_t appearances = 0;
        for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
            const auto& stream = layout.streams[slot];
            uint64_t offset = 0;
            if (stream.bind_offset || !stream.stride || stream.fields.empty())
                throw std::runtime_error("DRAW batches: invalid compact stream");
            for (size_t index : stream.fields) {
                if (index >= sources.size()) throw std::runtime_error("DRAW batches: invalid field index");
                const auto& source = sources[index];
                if (source.element_bytes != 4 && source.element_bytes != 8 &&
                    source.element_bytes != 12 && source.element_bytes != 16)
                    throw std::runtime_error("DRAW batches: unsupported field width");
                if ((source.divisor != 0) != stream.instance || layout.slots[index] != slot ||
                    layout.offsets[index] != offset)
                    throw std::runtime_error("DRAW batches: compact field map differs from source");
                offset = add(offset, source.element_bytes);
                appearances += index == field;
            }
            if (offset != stream.stride) throw std::runtime_error("DRAW batches: compact stride differs from fields");
        }
        if (appearances != 1) throw std::runtime_error("DRAW batches: missing or repeated compact field");
    }
    if (sources.empty() && !layout.streams.empty())
        throw std::runtime_error("DRAW batches: streams without fields");
}

inline uint64_t draw_count(uint64_t geometry_count, uint64_t instances, uint64_t blocks) {
    return geometry_count == 1 ? blocks : multiply(geometry_count, instances);
}
inline void admit_geometry(const Plan& plan, uint64_t geometry_count) {
    if (draw_count(geometry_count, plan.instances, plan.instance_block_count) > plan.limits.max_encoded_draws)
        throw std::length_error("DRAW batches: explicit encoded-draw budget exceeded");
}

inline Plan plan_triangle_list(const Selection& selection, std::span<const Source> sources,
                              const Layout& layout, Limits limits) {
    validate_selection(selection);
    Plan plan;
    plan.indexed = selection.index_bytes != 0;
    plan.selected_count = selection.count;
    plan.instances = selection.instances;
    plan.incomplete_tail = selection.count % 3;
    plan.limits = limits;
    // Match existing zero-draw preparation: no source reads, converted payload,
    // layout admission or storage grant is needed for either zero domain.
    if (!selection.count || !selection.instances) return plan;
    validate_layout(layout, sources);
    if (limits.buffer_bytes < identity_header_bytes || limits.storage_bytes < identity_header_bytes)
        throw std::runtime_error("DRAW batches: proposed identity ABI needs eight granted bytes");

    uint64_t vertex_capacity = INT32_MAX;
    plan.instance_rows_per_block = selection.instances;
    for (const auto& stream : layout.streams) {
        const auto capacity = std::min(limits.buffer_bytes / stream.stride, uint64_t(SIZE_MAX / stream.stride));
        if (!capacity) throw std::runtime_error("DRAW batches: one compact field row exceeds buffer grant");
        if (stream.instance) plan.instance_rows_per_block = std::min(plan.instance_rows_per_block, capacity);
        else vertex_capacity = std::min(vertex_capacity, capacity);
    }
    plan.instance_block_count = ceil_div(plan.instances, plan.instance_rows_per_block);
    const uint64_t index_capacity = std::min({limits.buffer_bytes / 4, uint64_t(SIZE_MAX / 4), uint64_t(INT32_MAX)});
    if (plan.indexed) vertex_capacity = std::min(vertex_capacity,
        (std::min(limits.buffer_bytes, limits.storage_bytes) - identity_header_bytes) / 4);

    // Before any plan payload allocation, reject obvious control/draw products
    // and prove every source read, including an incomplete terminal primitive.
    uint64_t initial_charge = sizeof(Plan);
    initial_charge = add(initial_charge, multiply(layout.streams.size(), sizeof(Stream)));
    initial_charge = add(initial_charge, multiply(add(layout.slots.size(), layout.offsets.size()), sizeof(uint32_t)));
    for (const auto& stream : layout.streams)
        initial_charge = add(initial_charge, multiply(stream.fields.size(), sizeof(size_t)));
    if (plan.indexed) initial_charge = add(initial_charge, multiply(selection.count, sizeof(uint32_t)));
    charge(plan, initial_charge);
    const auto element_capacity = plan.indexed ? index_capacity : vertex_capacity;
    if (!element_capacity || !vertex_capacity)
        throw std::runtime_error("DRAW batches: no rows for one selected primitive");
    const auto lower_geometry = ceil_div(selection.count, element_capacity);
    admit_geometry(plan, lower_geometry);
    if (add(plan.control_bytes, multiply(lower_geometry, sizeof(GeometryBatch))) > limits.max_control_bytes)
        throw std::length_error("DRAW batches: explicit plan control-byte budget exceeded");
    validate_sources(selection, sources, maximum_vertex(selection));
    plan.layout = layout;

    if (!plan.indexed) {
        const uint64_t complete = selection.count - plan.incomplete_tail;
        const uint64_t full_capacity = vertex_capacity / 3 * 3;
        if (complete && !full_capacity)
            throw std::runtime_error("DRAW batches: one complete triangle exceeds vertex buffer grant");
        uint64_t chunks = complete ? ceil_div(complete, full_capacity) : 0;
        const uint64_t last_complete = chunks ? complete - (chunks - 1) * full_capacity : 0;
        const bool separate_tail = plan.incomplete_tail && (!chunks || last_complete + plan.incomplete_tail > vertex_capacity);
        if (separate_tail && plan.incomplete_tail > vertex_capacity)
            throw std::runtime_error("DRAW batches: incomplete terminal selection exceeds vertex buffer grant");
        const auto total = chunks + separate_tail;
        admit_geometry(plan, total);
        charge(plan, multiply(total, sizeof(GeometryBatch)));
        plan.geometry.reserve(static_cast<size_t>(total));
        uint64_t cursor = 0;
        for (uint64_t g = 0; g < chunks; ++g) {
            const uint64_t count = std::min(full_capacity, complete - cursor);
            GeometryBatch batch;
            batch.element_offset = cursor; batch.element_count = count;
            batch.vertex_base = static_cast<uint32_t>(selection.first + cursor);
            if (g + 1 == chunks && !separate_tail) batch.element_count += plan.incomplete_tail;
            plan.geometry.push_back(std::move(batch)); cursor += count;
        }
        if (separate_tail) {
            GeometryBatch batch;
            batch.element_offset = cursor; batch.element_count = plan.incomplete_tail;
            batch.vertex_base = static_cast<uint32_t>(selection.first + cursor);
            plan.geometry.push_back(std::move(batch));
        }
    } else {
        GeometryBatch current;
        std::unordered_map<uint32_t, uint32_t> lookup;
        auto start = [&] {
            admit_geometry(plan, plan.geometry.size() + 1);
            charge(plan, sizeof(GeometryBatch));
            current.element_offset = current.element_count = 0;
        };
        start();
        for (uint64_t cursor = 0; cursor < selection.count;) {
            const auto atom_count = std::min(uint64_t(3), selection.count - cursor);
            std::array<uint32_t, 3> atom{}, missing{};
            uint64_t missing_count = 0;
            auto count_missing = [&] {
                missing_count = 0;
                for (uint64_t n = 0; n < atom_count; ++n) {
                    if (lookup.contains(atom[n])) continue;
                    if (std::find(missing.begin(), missing.begin() + static_cast<ptrdiff_t>(missing_count), atom[n]) ==
                        missing.begin() + static_cast<ptrdiff_t>(missing_count)) missing[missing_count++] = atom[n];
                }
            };
            for (uint64_t n = 0; n < atom_count; ++n) atom[n] = selection.vertex(cursor + n);
            count_missing();
            auto fits = [&] { return current.element_count + atom_count <= index_capacity &&
                current.original_vertices.size() + missing_count <= vertex_capacity; };
            if (!fits() && current.element_count) {
                plan.geometry.push_back(std::move(current)); current = {}; lookup.clear();
                start(); count_missing();
            }
            if (!fits()) throw std::runtime_error("DRAW batches: one selected primitive exceeds index/vertex/identity grant");
            charge(plan, multiply(missing_count, sizeof(uint32_t)));
            if (!current.element_count) current.element_offset = cursor;
            for (uint64_t n = 0; n < missing_count; ++n) {
                const auto compact = static_cast<uint32_t>(current.original_vertices.size());
                lookup.emplace(missing[n], compact); current.original_vertices.push_back(missing[n]);
            }
            for (uint64_t n = 0; n < atom_count; ++n) current.remapped_indices.push_back(lookup.at(atom[n]));
            current.element_count += atom_count; cursor += atom_count;
        }
        plan.geometry.push_back(std::move(current));
    }
    plan.encoded_draws = draw_count(plan.geometry.size(), plan.instances, plan.instance_block_count);
    return plan;
}

inline uint64_t vertex_rows(const Plan& plan, const GeometryBatch& batch) {
    return plan.indexed ? batch.original_vertices.size() : batch.element_count;
}

// Sources are supplied from the immutable captured revision in a future
// integration. The plan itself owns all selected IDs and borrows no index span.
inline void require_sources(const Plan& plan, std::span<const Source> sources) {
    validate_layout(plan.layout, sources);
}
inline std::vector<uint8_t> pack_vertex_stream(const Plan& plan, size_t geometry, size_t slot,
                                              std::span<const Source> sources) {
    require_sources(plan, sources);
    const auto& batch = plan.geometry.at(geometry);
    const auto& stream = plan.layout.streams.at(slot);
    if (stream.instance) throw std::runtime_error("DRAW batches: expected vertex stream");
    const auto rows = vertex_rows(plan, batch);
    const auto bytes = multiply(rows, stream.stride);
    if (bytes > plan.limits.buffer_bytes || bytes > SIZE_MAX) throw std::length_error("DRAW batches: vertex byte grant");
    for (uint64_t row = 0; row < rows; ++row) {
        const uint64_t original = plan.indexed ? batch.original_vertices[static_cast<size_t>(row)] : batch.vertex_base + row;
        for (size_t field : stream.fields) (void)source_address(sources[field], original);
    }
    std::vector<uint8_t> result(static_cast<size_t>(bytes));
    for (uint64_t row = 0; row < rows; ++row) {
        const uint64_t original = plan.indexed ? batch.original_vertices[static_cast<size_t>(row)] : batch.vertex_base + row;
        for (size_t field : stream.fields) std::memcpy(result.data() + row * stream.stride + plan.layout.offsets[field],
            sources[field].bytes.data() + source_address(sources[field], original), static_cast<size_t>(sources[field].element_bytes));
    }
    return result;
}
inline std::vector<uint8_t> pack_instance_stream(const Plan& plan, uint64_t block_number, size_t slot,
                                                std::span<const Source> sources) {
    require_sources(plan, sources);
    const auto block = plan.instance_block(block_number);
    const auto& stream = plan.layout.streams.at(slot);
    if (!stream.instance) throw std::runtime_error("DRAW batches: expected instance stream");
    const auto bytes = multiply(block.count, stream.stride);
    if (bytes > plan.limits.buffer_bytes || bytes > SIZE_MAX) throw std::length_error("DRAW batches: instance byte grant");
    for (size_t field : stream.fields)
        (void)source_address(sources[field], (block.first + block.count - 1) / sources[field].divisor);
    std::vector<uint8_t> result(static_cast<size_t>(bytes));
    for (uint64_t row = 0; row < block.count; ++row)
        for (size_t field : stream.fields) {
            const auto& source = sources[field];
            const auto element = (block.first + row) / source.divisor;
            std::memcpy(result.data() + row * stream.stride + plan.layout.offsets[field],
                source.bytes.data() + source_address(source, element), static_cast<size_t>(source.element_bytes));
        }
    return result;
}
inline std::vector<uint8_t> identity_data(const Plan& plan, const DrawRef& draw) {
    const auto& batch = plan.geometry.at(draw.geometry);
    const auto block = plan.instance_block(draw.instance_block);
    if (!draw.instance_count || draw.instance_base >= plan.instances ||
        draw.instance_count > plan.instances - draw.instance_base ||
        draw.row_offset >= block.count || draw.instance_count > block.count - draw.row_offset ||
        block.first + draw.row_offset != draw.instance_base)
        throw std::out_of_range("DRAW batches: identity instance range differs from block");
    const auto bytes = add(identity_header_bytes, plan.indexed ? multiply(batch.original_vertices.size(), 4) : 0);
    if (bytes > plan.limits.buffer_bytes || bytes > plan.limits.storage_bytes || bytes > SIZE_MAX ||
        draw.instance_base > UINT32_MAX) throw std::length_error("DRAW batches: identity byte grant");
    const IdentityHeader header{batch.vertex_base, static_cast<uint32_t>(draw.instance_base)};
    std::vector<uint8_t> result(static_cast<size_t>(bytes));
    std::memcpy(result.data(), &header, sizeof(header));
    if (plan.indexed) std::memcpy(result.data() + identity_header_bytes, batch.original_vertices.data(),
        batch.original_vertices.size() * sizeof(uint32_t));
    return result;
}

// A conversion/publication seam for CPU tests. A late builder failure leaves
// the complete previous logical draw owner intact; publication is one noexcept
// shared_ptr swap. This does not yet transact the runtime's existing caches.
template<class Prepared, class Build>
void prepare_and_publish(std::shared_ptr<const Prepared>& current, Build&& build) {
    auto next = std::make_shared<const Prepared>(std::forward<Build>(build)());
    current.swap(next);
}

} // namespace vispy::inputs::batches
