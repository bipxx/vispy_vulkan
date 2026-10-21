#pragma once

#include "runtime_batch_plan.hpp"

namespace vispy::inputs::batches {

// Portable CPU proposal only. The current GLIR state interpreter does not
// enable primitive restart. An all-ones index is an ordinary ID by default.
enum class Topology { Points, Lines, LineStrip, LineLoop, Triangles, TriangleStrip, TriangleFan };
enum class RestartMode { Disabled, Index, FixedIndex };
struct RestartPolicy { RestartMode mode = RestartMode::Disabled; uint32_t index = 0; };

struct PrimitiveOrigin {
    uint64_t run = 0, ordinal = 0;
    std::array<uint64_t, 3> input_positions{};
    uint32_t last = 0, previous = 0, next = 0;
    bool odd_strip = false, closes_loop = false, has_previous = false, has_next = false;
};
struct RunOrigin {
    uint64_t input_offset = 0, input_count = 0, primitive_count = 0;
    std::array<uint32_t, 2> incomplete_ids{};
    uint32_t incomplete_count = 0;
};
struct TopologyPlan {
    Plan payload;
    Topology original_topology = Topology::Triangles;
    Topology list_topology = Topology::Triangles;
    RestartPolicy restart;
    uint64_t original_count = 0, restart_markers = 0, complete_primitives = 0;
    uint64_t emitted_indices = 0, incomplete_elements = 0;
    bool source_indexed = false;
    std::vector<RunOrigin> runs;
    // One list per physical geometry child, in original primitive order.
    // These are adjacency/carry facts, not a wide-line join implementation.
    std::vector<std::vector<PrimitiveOrigin>> origins;
};

inline uint32_t primitive_width(Topology topology) {
    switch (topology) {
    case Topology::Points: return 1;
    case Topology::Lines: case Topology::LineStrip: case Topology::LineLoop: return 2;
    case Topology::Triangles: case Topology::TriangleStrip: case Topology::TriangleFan: return 3;
    }
    throw std::runtime_error("DRAW topology batches: unsupported topology");
}
inline uint64_t primitive_count(Topology topology, uint64_t count) {
    switch (topology) {
    case Topology::Points: return count;
    case Topology::Lines: return count / 2;
    case Topology::Triangles: return count / 3;
    case Topology::LineStrip: return count > 1 ? count - 1 : 0;
    case Topology::LineLoop: return count > 1 ? count : 0;
    case Topology::TriangleStrip: case Topology::TriangleFan: return count > 2 ? count - 2 : 0;
    }
    throw std::runtime_error("DRAW topology batches: unsupported topology");
}
inline uint32_t incomplete_count(Topology topology, uint64_t count) {
    switch (topology) {
    case Topology::Points: return 0;
    case Topology::Lines: return static_cast<uint32_t>(count % 2);
    case Topology::Triangles: return static_cast<uint32_t>(count % 3);
    default: return primitive_count(topology, count) ? 0 : static_cast<uint32_t>(count);
    }
}
inline uint32_t restart_index(const Selection& selected, RestartPolicy restart) {
    switch (restart.mode) {
    case RestartMode::Disabled: return 0;
    case RestartMode::Index: return restart.index;
    case RestartMode::FixedIndex:
        return selected.index_bytes == 1 ? UINT8_MAX : selected.index_bytes == 2 ? UINT16_MAX : UINT32_MAX;
    }
    throw std::runtime_error("DRAW topology batches: unsupported restart policy");
}
template<class Visit> void topology_runs(const Selection& selected, RestartPolicy restart, Visit&& visit) {
    const auto sentinel = restart_index(selected, restart);
    if (!selected.index_bytes || restart.mode == RestartMode::Disabled) {
        visit(uint64_t(0), selected.count, uint64_t(0)); return;
    }
    uint64_t first = 0, run = 0;
    for (uint64_t n = 0; n < selected.count; ++n) if (selected.vertex(n) == sentinel) {
        visit(first, n - first, run++); first = n + 1;
    }
    visit(first, selected.count - first, run);
}

inline PrimitiveOrigin primitive_origin(Topology topology, const Selection& selected,
                                        const RunOrigin& run, uint64_t run_number, uint64_t number) {
    PrimitiveOrigin result; result.run = run_number; result.ordinal = number;
    auto position = [&](uint64_t n) { return run.input_offset + n; };
    switch (topology) {
    case Topology::Points: result.input_positions = {position(number), 0, 0}; break;
    case Topology::Lines: result.input_positions = {position(number * 2), position(number * 2 + 1), 0}; break;
    case Topology::Triangles: result.input_positions = {position(number * 3), position(number * 3 + 1), position(number * 3 + 2)}; break;
    case Topology::TriangleStrip:
        result.input_positions = {position(number), position(number + 1), position(number + 2)};
        result.odd_strip = number % 2 != 0;
        if (result.odd_strip) std::swap(result.input_positions[0], result.input_positions[1]);
        break;
    case Topology::TriangleFan:
        result.input_positions = {position(0), position(number + 1), position(number + 2)}; break;
    case Topology::LineStrip:
    case Topology::LineLoop: {
        const bool loop = topology == Topology::LineLoop;
        result.input_positions = {position(number), position((number + 1) % run.input_count), 0};
        result.closes_loop = loop && number + 1 == run.input_count;
        result.has_previous = loop || number != 0;
        result.has_next = loop || number + 2 < run.input_count;
        if (result.has_previous) result.previous = selected.vertex(position((number + run.input_count - 1) % run.input_count));
        if (result.has_next) result.next = selected.vertex(position((number + 2) % run.input_count));
        break;
    }
    }
    result.last = selected.vertex(result.input_positions[primitive_width(topology) - 1]);
    return result;
}

inline TopologyPlan plan_topology(Topology topology, const Selection& selected, std::span<const Source> sources,
                                  const Layout& layout, Limits limits, RestartPolicy restart = {}) {
    validate_selection(selected);
    const auto width = primitive_width(topology);
    (void)restart_index(selected, restart);
    TopologyPlan result;
    result.original_topology = topology;
    result.list_topology = width == 1 ? Topology::Points : width == 2 ? Topology::Lines : Topology::Triangles;
    result.restart = restart; result.source_indexed = selected.index_bytes != 0;
    result.original_count = selected.count;
    result.payload.instances = selected.instances; result.payload.limits = limits;
    if (!selected.count || !selected.instances) return result;

    // A constant-space first pass proves all original reads, including tails,
    // and computes exact emitted/control lower bounds before output growth.
    uint64_t runs = 0, maximum = 0; bool any_source_vertex = false;
    topology_runs(selected, restart, [&](uint64_t first, uint64_t count, uint64_t) {
        runs = add(runs, 1);
        const auto complete = primitive_count(topology, count);
        const auto tail = incomplete_count(topology, count);
        result.complete_primitives = add(result.complete_primitives, complete);
        result.incomplete_elements = add(result.incomplete_elements, tail);
        result.emitted_indices = add(result.emitted_indices, add(multiply(complete, width), tail));
        if (count) {
            any_source_vertex = true;
            if (!selected.index_bytes) maximum = std::max(maximum, uint64_t(selected.vertex(first + count - 1)));
            else for (uint64_t n = 0; n < count; ++n) maximum = std::max(maximum, uint64_t(selected.vertex(first + n)));
        }
    });
    result.restart_markers = runs - 1;
    validate_layout(layout, sources);
    if (any_source_vertex) validate_sources(selected, sources, static_cast<uint32_t>(maximum));
    const auto topology_bytes = add(sizeof(TopologyPlan) - sizeof(Plan),
        add(multiply(runs, sizeof(RunOrigin)), multiply(result.complete_primitives, sizeof(PrimitiveOrigin))));
    if (topology_bytes > limits.max_control_bytes || topology_bytes > SIZE_MAX)
        throw std::length_error("DRAW topology batches: explicit topology control-byte budget exceeded");

    // Preserve the admitted triangle-list route exactly. No expanded global
    // output selection is ever constructed for strips, fans or loops below.
    if (topology == Topology::Triangles && (!selected.index_bytes || restart.mode == RestartMode::Disabled)) {
        auto inner = limits; inner.max_control_bytes -= topology_bytes;
        result.payload = plan_triangle_list(selected, sources, layout, inner);
        result.payload.limits = limits;
        charge(result.payload, topology_bytes);
        charge(result.payload, multiply(result.payload.geometry.size(), sizeof(std::vector<PrimitiveOrigin>)));
        RunOrigin run; run.input_count = selected.count; run.primitive_count = selected.count / 3;
        run.incomplete_count = static_cast<uint32_t>(selected.count % 3);
        for (uint32_t n = 0; n < run.incomplete_count; ++n) run.incomplete_ids[n] = selected.vertex(selected.count - run.incomplete_count + n);
        result.runs.push_back(run); result.origins.resize(result.payload.geometry.size());
        for (size_t g = 0; g < result.payload.geometry.size(); ++g) {
            const auto& geometry = result.payload.geometry[g];
            for (uint64_t n = 0; n + 2 < geometry.element_count; n += 3)
                result.origins[g].push_back(primitive_origin(topology, selected, run, 0, (geometry.element_offset + n) / 3));
        }
        return result;
    }

    // Arrays of independent points/lines need only the affine ABI header.
    // Do not introduce an unnecessary per-vertex table/storage refusal.
    if (!selected.index_bytes && (topology == Topology::Points || topology == Topology::Lines)) {
        auto& plan = result.payload;
        plan.selected_count = selected.count; plan.incomplete_tail = result.incomplete_elements;
        if (limits.buffer_bytes < 8 || limits.storage_bytes < 8)
            throw std::runtime_error("DRAW topology batches: identity ABI needs eight granted bytes");
        uint64_t capacity = INT32_MAX;
        plan.instance_rows_per_block = selected.instances;
        for (const auto& stream : layout.streams) {
            const auto rows = std::min(limits.buffer_bytes / stream.stride, uint64_t(SIZE_MAX / stream.stride));
            if (!rows) throw std::runtime_error("DRAW topology batches: one physical field row exceeds buffer grant");
            if (stream.instance) plan.instance_rows_per_block = std::min(plan.instance_rows_per_block, rows);
            else capacity = std::min(capacity, rows);
        }
        plan.instance_block_count = ceil_div(selected.instances, plan.instance_rows_per_block);
        const auto complete = selected.count - result.incomplete_elements;
        const auto full = capacity / width * width;
        if (complete && !full) throw std::runtime_error("DRAW topology batches: one primitive exceeds vertex grant");
        const auto chunks = complete ? ceil_div(complete, full) : 0;
        const auto last_complete = chunks ? complete - (chunks - 1) * full : 0;
        const bool separate_tail = result.incomplete_elements && (!chunks || last_complete + result.incomplete_elements > capacity);
        if (separate_tail && result.incomplete_elements > capacity)
            throw std::runtime_error("DRAW topology batches: incomplete run exceeds vertex grant");
        const auto count = chunks + separate_tail;
        admit_geometry(plan, count);
        charge(plan, add(sizeof(Plan), topology_bytes));
        charge(plan, multiply(layout.streams.size(), sizeof(Stream)));
        charge(plan, multiply(add(layout.slots.size(), layout.offsets.size()), sizeof(uint32_t)));
        for (const auto& stream : layout.streams) charge(plan, multiply(stream.fields.size(), sizeof(size_t)));
        charge(plan, multiply(count, sizeof(GeometryBatch) + sizeof(std::vector<PrimitiveOrigin>)));
        plan.layout = layout;
        RunOrigin run; run.input_count = selected.count; run.primitive_count = result.complete_primitives;
        run.incomplete_count = static_cast<uint32_t>(result.incomplete_elements);
        for (uint32_t n = 0; n < run.incomplete_count; ++n) run.incomplete_ids[n] = selected.vertex(complete + n);
        result.runs.push_back(run);
        uint64_t cursor = 0;
        for (uint64_t g = 0; g < count; ++g) {
            GeometryBatch batch; batch.element_offset = cursor;
            batch.element_count = g < chunks ? std::min(full, complete - cursor) : result.incomplete_elements;
            if (g + 1 == chunks && !separate_tail) batch.element_count += result.incomplete_elements;
            batch.vertex_base = static_cast<uint32_t>(selected.first + cursor);
            std::vector<PrimitiveOrigin> origins;
            for (uint64_t n = 0; n + width <= batch.element_count; n += width)
                origins.push_back(primitive_origin(topology, selected, run, 0, (cursor + n) / width));
            cursor += batch.element_count;
            plan.geometry.push_back(std::move(batch)); result.origins.push_back(std::move(origins));
        }
        plan.encoded_draws = draw_count(plan.geometry.size(), plan.instances, plan.instance_block_count);
        return result;
    }

    auto& plan = result.payload;
    plan.indexed = true; plan.selected_count = result.emitted_indices; plan.incomplete_tail = result.incomplete_elements;
    plan.instance_rows_per_block = selected.instances;
    uint64_t vertex_capacity = INT32_MAX;
    for (const auto& stream : layout.streams) {
        const auto capacity = std::min(limits.buffer_bytes / stream.stride, uint64_t(SIZE_MAX / stream.stride));
        if (!capacity) throw std::runtime_error("DRAW topology batches: one physical field row exceeds buffer grant");
        if (stream.instance) plan.instance_rows_per_block = std::min(plan.instance_rows_per_block, capacity);
        else vertex_capacity = std::min(vertex_capacity, capacity);
    }
    plan.instance_block_count = ceil_div(selected.instances, plan.instance_rows_per_block);
    charge(plan, add(sizeof(Plan), topology_bytes));
    charge(plan, multiply(layout.streams.size(), sizeof(Stream)));
    charge(plan, multiply(add(layout.slots.size(), layout.offsets.size()), sizeof(uint32_t)));
    for (const auto& stream : layout.streams) charge(plan, multiply(stream.fields.size(), sizeof(size_t)));
    charge(plan, multiply(result.emitted_indices, sizeof(uint32_t)));
    // Restart-only runs own no vertex/identity/index payload and need no ABI.
    if (!result.emitted_indices) {
        topology_runs(selected, restart, [&](uint64_t first, uint64_t count, uint64_t) {
            RunOrigin run; run.input_offset = first; run.input_count = count; result.runs.push_back(run);
        });
        return result;
    }
    if (limits.buffer_bytes < 8 || limits.storage_bytes < 8)
        throw std::runtime_error("DRAW topology batches: identity ABI needs eight granted bytes");
    vertex_capacity = std::min(vertex_capacity, (std::min(limits.buffer_bytes, limits.storage_bytes) - 8) / 4);
    const auto index_capacity = std::min({limits.buffer_bytes / 4, uint64_t(SIZE_MAX / 4), uint64_t(INT32_MAX)});
    if (!vertex_capacity || !index_capacity) throw std::runtime_error("DRAW topology batches: no selected row fits identity/index grant");
    admit_geometry(plan, ceil_div(result.emitted_indices, index_capacity));
    plan.layout = layout;
    GeometryBatch current; std::vector<PrimitiveOrigin> current_origins;
    std::unordered_map<uint32_t, uint32_t> lookup;
    uint64_t emitted = 0; bool current_charged = false;
    auto flush = [&] {
        if (!current.element_count) return;
        plan.geometry.push_back(std::move(current)); result.origins.push_back(std::move(current_origins));
        current = {}; current_origins = {}; lookup.clear(); current_charged = false;
    };
    auto append = [&](const std::array<uint32_t, 3>& atom, uint32_t count, const PrimitiveOrigin* origin) {
        std::array<uint32_t, 3> missing{}; uint64_t missing_count = 0;
        auto count_missing = [&] {
            missing_count = 0;
            for (uint32_t n = 0; n < count; ++n) if (!lookup.contains(atom[n]) &&
                std::find(missing.begin(), missing.begin() + static_cast<ptrdiff_t>(missing_count), atom[n]) ==
                missing.begin() + static_cast<ptrdiff_t>(missing_count)) missing[static_cast<size_t>(missing_count++)] = atom[n];
        };
        count_missing();
        auto fits = [&] { return current.element_count + count <= index_capacity &&
            current.original_vertices.size() + missing_count <= vertex_capacity; };
        if (!fits() && current.element_count) { flush(); count_missing(); }
        if (!fits()) throw std::runtime_error("DRAW topology batches: one primitive or incomplete run exceeds granted capacity");
        if (!current_charged) {
            admit_geometry(plan, plan.geometry.size() + 1);
            charge(plan, sizeof(GeometryBatch) + sizeof(std::vector<PrimitiveOrigin>));
            current_charged = true; current.element_offset = emitted;
        }
        charge(plan, multiply(missing_count, sizeof(uint32_t)));
        for (uint64_t n = 0; n < missing_count; ++n) {
            const auto value = missing[static_cast<size_t>(n)];
            lookup.emplace(value, static_cast<uint32_t>(current.original_vertices.size())); current.original_vertices.push_back(value);
        }
        for (uint32_t n = 0; n < count; ++n) current.remapped_indices.push_back(lookup.at(atom[n]));
        current.element_count += count; emitted += count;
        if (origin) current_origins.push_back(*origin);
    };
    topology_runs(selected, restart, [&](uint64_t first, uint64_t count, uint64_t run_number) {
        RunOrigin run; run.input_offset = first; run.input_count = count;
        run.primitive_count = primitive_count(topology, count); run.incomplete_count = incomplete_count(topology, count);
        for (uint32_t n = 0; n < run.incomplete_count; ++n) run.incomplete_ids[n] = selected.vertex(first + count - run.incomplete_count + n);
        result.runs.push_back(run);
        for (uint64_t n = 0; n < run.primitive_count; ++n) {
            const auto origin = primitive_origin(topology, selected, run, run_number, n);
            std::array<uint32_t, 3> atom{};
            for (uint32_t k = 0; k < width; ++k) atom[k] = selected.vertex(origin.input_positions[k]);
            append(atom, width, &origin);
        }
        if (run.incomplete_count) {
            std::array<uint32_t, 3> atom{};
            for (uint32_t k = 0; k < run.incomplete_count; ++k) atom[k] = run.incomplete_ids[k];
            append(atom, run.incomplete_count, nullptr);
            // Never join an incomplete atom to a subsequent restart run.
            flush();
        }
    });
    flush();
    plan.encoded_draws = draw_count(plan.geometry.size(), plan.instances, plan.instance_block_count);
    return result;
}

} // namespace vispy::inputs::batches
