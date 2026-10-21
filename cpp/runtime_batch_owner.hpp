#pragma once

// Portable bridge only. No native handles, runtime cache or GPU publication.
#include "runtime_batch_plan.hpp"

namespace vispy::inputs::batches::owners {

// Split ABI 2 deliberately does not reinterpret identity_data()/ABI 1.
// Geometry storage: affine uint base OR headerless uint original IDs[].
// Instance uniform: std140 uvec4, x = original instance-block first.
inline constexpr uint32_t identity_abi = 2;
inline constexpr uint64_t instance_origin_bytes = 16;
struct InstanceOrigin { uint32_t first, reserved[3]; };
static_assert(sizeof(InstanceOrigin) == instance_origin_bytes);

enum class LeafKind { GeometryIdentity, Indices, VertexStream, InstanceOrigin, InstanceStream };

struct Limits {
    uint64_t max_packed_bytes = 0;
    uint64_t max_control_bytes = 0;
    uint64_t max_retained_bytes = 0;
    uint64_t max_records = 0;
    uint64_t max_encoded_draws = 0;
    // Caller-defined charges for generic Record and root graph edge ownership.
    // They include the caller's node/shared-owner and edge bookkeeping. Key
    // characters are charged separately. These are representation charges,
    // never a promise about allocator peaks, buckets, driver heaps or RSS.
    uint64_t record_control_bytes = 0;
    uint64_t edge_control_bytes = 0;
};

struct Counts {
    uint64_t packed_bytes = 0, buffer_allocation_bytes = 0;
    uint64_t records = 0, edges = 0, edge_key_bytes = 0;
    uint64_t metadata_bytes = 0, charged_control_bytes = 0, retained_bytes = 0;
    uint64_t encoded_draws = 0;
};

template<class Record> struct GeometryRecords {
    Record identity{}, index{};
    // Physical layout slots; instance-only slots are empty.
    std::vector<Record> vertices;
};
template<class Record> struct InstanceRecords {
    Record origin{};
    // Physical layout slots; vertex-only slots are empty.
    std::vector<Record> instances;
};

inline uint64_t plan_dynamic_bytes(const Plan& plan, bool capacities) {
    auto bytes = multiply(capacities ? plan.layout.streams.capacity() : plan.layout.streams.size(), sizeof(Stream));
    bytes = add(bytes, multiply(capacities ? plan.layout.slots.capacity() : plan.layout.slots.size(), sizeof(uint32_t)));
    bytes = add(bytes, multiply(capacities ? plan.layout.offsets.capacity() : plan.layout.offsets.size(), sizeof(uint32_t)));
    for (const auto& stream : plan.layout.streams)
        bytes = add(bytes, multiply(capacities ? stream.fields.capacity() : stream.fields.size(), sizeof(size_t)));
    bytes = add(bytes, multiply(capacities ? plan.geometry.capacity() : plan.geometry.size(), sizeof(GeometryBatch)));
    for (const auto& g : plan.geometry) {
        bytes = add(bytes, multiply(capacities ? g.original_vertices.capacity() : g.original_vertices.size(), sizeof(uint32_t)));
        bytes = add(bytes, multiply(capacities ? g.remapped_indices.capacity() : g.remapped_indices.size(), sizeof(uint32_t)));
    }
    return bytes;
}

template<class Record> struct OwnerData {
    Plan plan;
    std::vector<GeometryRecords<Record>> geometry;
    std::vector<InstanceRecords<Record>> blocks;
    Counts counts;

    // Actual retained vector capacities + object bytes, with a portable charge
    // for this shared owner's control block. Leaves/Record pointees and root
    // edges are counted separately by the caller's existing graph traversal.
    uint64_t metadata_storage_bytes() const {
        auto bytes = add(sizeof(OwnerData), 2 * sizeof(void*));
        bytes = add(bytes, plan_dynamic_bytes(plan, true));
        bytes = add(bytes, multiply(geometry.capacity(), sizeof(GeometryRecords<Record>)));
        bytes = add(bytes, multiply(blocks.capacity(), sizeof(InstanceRecords<Record>)));
        for (const auto& g : geometry) bytes = add(bytes, multiply(g.vertices.capacity(), sizeof(Record)));
        for (const auto& b : blocks) bytes = add(bytes, multiply(b.instances.capacity(), sizeof(Record)));
        return bytes;
    }
};

// No root appears in OwnerData: root->batch_data can own data without a cycle.
template<class Record> struct PreparedOwner {
    Record root{};
    std::shared_ptr<const OwnerData<Record>> data;
};

inline uint64_t digits(uint64_t number) {
    uint64_t result = 1;
    while (number >= 10) { number /= 10; ++result; }
    return result;
}
inline uint64_t key_bytes(char domain, uint64_t number, LeafKind kind, uint64_t slot = 0) {
    (void)domain;
    // "g:N:id", "g:N:index", "g:N:stream:S", "b:N:origin".
    uint64_t length = add(3, digits(number));
    switch (kind) {
    case LeafKind::GeometryIdentity: length = add(length, 2); break;
    case LeafKind::Indices: length = add(length, 5); break;
    case LeafKind::InstanceOrigin: length = add(length, 6); break;
    default: length = add(length, add(7, digits(slot))); break;
    }
    return add(length, 1); // Include a terminating character in the charge.
}
inline std::string edge_key(char domain, uint64_t number, LeafKind kind, uint64_t slot = 0) {
    std::string result(1, domain);
    result += ':' + std::to_string(number) + ':';
    switch (kind) {
    case LeafKind::GeometryIdentity: return result + "id";
    case LeafKind::Indices: return result + "index";
    case LeafKind::InstanceOrigin: return result + "origin";
    default: return result + "stream:" + std::to_string(slot);
    }
}
inline void finish_counts(Counts& counts, const Limits& limits) {
    counts.charged_control_bytes = add(counts.metadata_bytes,
        add(multiply(counts.records, limits.record_control_bytes),
            add(multiply(counts.edges, limits.edge_control_bytes), counts.edge_key_bytes)));
    counts.retained_bytes = add(counts.charged_control_bytes, counts.packed_bytes);
    if (counts.records > limits.max_records || counts.encoded_draws > limits.max_encoded_draws ||
        counts.packed_bytes > limits.max_packed_bytes || counts.charged_control_bytes > limits.max_control_bytes ||
        counts.retained_bytes > limits.max_retained_bytes || counts.metadata_bytes > SIZE_MAX)
        throw std::length_error("DRAW batch owner: explicit retained representation budget exceeded");
}
inline uint64_t stream_count(const Plan& plan, bool instance) {
    uint64_t count = 0;
    for (const auto& stream : plan.layout.streams) if (stream.instance == instance) ++count;
    return count;
}
inline void charge_leaf(Counts& counts, const Plan& plan, uint64_t bytes,
                        bool storage, bool uniform, uint64_t uniform_bytes,
                        char domain, uint64_t number, LeafKind kind, uint64_t slot = 0) {
    const auto allocated = std::max(uint64_t(4), add(bytes, 3) / 4 * 4);
    if (!bytes || bytes > SIZE_MAX || allocated > plan.limits.buffer_bytes ||
        (storage && bytes > plan.limits.storage_bytes) || (uniform && bytes > uniform_bytes))
        throw std::length_error("DRAW batch owner: leaf exceeds granted byte capacity");
    counts.packed_bytes = add(counts.packed_bytes, bytes);
    counts.buffer_allocation_bytes = add(counts.buffer_allocation_bytes, allocated);
    counts.records = add(counts.records, 1);
    counts.edges = add(counts.edges, 1);
    counts.edge_key_bytes = add(counts.edge_key_bytes, key_bytes(domain, number, kind, slot));
}

// Allocation-free preflight, except that the caller already owns the Plan.
// It accounts for BOTH Plan's uint32 arrays and the generated byte leaves.
// It deliberately does not materialize geometry*block/draw schedules or tables.
template<class Record>
Counts measure_owner(const Plan& plan, Limits limits, uint64_t max_uniform_bytes) {
    Counts counts;
    if (!plan.selected_count || !plan.instances) return counts;
    if (plan.geometry.empty() || !plan.instance_rows_per_block ||
        plan.instance_block_count != ceil_div(plan.instances, plan.instance_rows_per_block) ||
        plan.encoded_draws != draw_count(plan.geometry.size(), plan.instances, plan.instance_block_count))
        throw std::runtime_error("DRAW batch owner: malformed plan schedule");
    counts.encoded_draws = plan.encoded_draws;
    counts.records = 1; // The non-payload root.
    counts.metadata_bytes = add(sizeof(OwnerData<Record>), 2 * sizeof(void*));
    counts.metadata_bytes = add(counts.metadata_bytes, plan_dynamic_bytes(plan, true));
    counts.metadata_bytes = add(counts.metadata_bytes, multiply(plan.geometry.size(), sizeof(GeometryRecords<Record>)));
    counts.metadata_bytes = add(counts.metadata_bytes, multiply(plan.instance_block_count, sizeof(InstanceRecords<Record>)));
    counts.metadata_bytes = add(counts.metadata_bytes, multiply(plan.geometry.size(), multiply(plan.layout.streams.size(), sizeof(Record))));
    counts.metadata_bytes = add(counts.metadata_bytes, multiply(plan.instance_block_count, multiply(plan.layout.streams.size(), sizeof(Record))));
    // Refuse huge block/control/call products before enumerating block leaves.
    finish_counts(counts, limits);
    for (size_t g = 0; g < plan.geometry.size(); ++g) {
        const auto& geometry = plan.geometry[g];
        if (!geometry.element_count || (plan.indexed && (geometry.original_vertices.empty() ||
            geometry.remapped_indices.size() != geometry.element_count)))
            throw std::runtime_error("DRAW batch owner: malformed geometry");
        charge_leaf(counts, plan, plan.indexed ? multiply(geometry.original_vertices.size(), 4) : 4,
            true, false, max_uniform_bytes, 'g', g, LeafKind::GeometryIdentity);
        if (plan.indexed) charge_leaf(counts, plan, multiply(geometry.remapped_indices.size(), 4),
            false, false, max_uniform_bytes, 'g', g, LeafKind::Indices);
        for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot) {
            const auto& stream = plan.layout.streams[slot];
            if (!stream.stride) throw std::runtime_error("DRAW batch owner: zero stream stride");
            if (!stream.instance) charge_leaf(counts, plan, multiply(vertex_rows(plan, geometry), stream.stride),
                false, false, max_uniform_bytes, 'g', g, LeafKind::VertexStream, slot);
        }
        finish_counts(counts, limits);
    }
    // The sums are affine in block count. Compute them without a B-element
    // loop, so even an enormous number of tiny blocks is refused promptly.
    const auto blocks = plan.instance_block_count;
    const auto instance_streams = stream_count(plan, true);
    const auto leaves_per_block = add(1, instance_streams);
    const auto block_leaves = multiply(blocks, leaves_per_block);
    counts.records = add(counts.records, block_leaves);
    counts.edges = add(counts.edges, block_leaves);
    counts.packed_bytes = add(counts.packed_bytes, multiply(blocks, instance_origin_bytes));
    counts.buffer_allocation_bytes = add(counts.buffer_allocation_bytes, multiply(blocks, instance_origin_bytes));
    if (instance_origin_bytes > plan.limits.buffer_bytes || instance_origin_bytes > max_uniform_bytes)
        throw std::length_error("DRAW batch owner: instance uniform exceeds granted byte capacity");
    for (const auto& stream : plan.layout.streams) if (stream.instance) {
        const auto largest = multiply(std::min(plan.instances, plan.instance_rows_per_block), stream.stride);
        if (!stream.stride || largest > plan.limits.buffer_bytes || largest > SIZE_MAX)
            throw std::length_error("DRAW batch owner: instance stream exceeds granted byte capacity");
        const auto total = multiply(plan.instances, stream.stride);
        counts.packed_bytes = add(counts.packed_bytes, total);
        // Compact stream strides are four-byte aligned; no per-block padding.
        if (stream.stride % 4) throw std::runtime_error("DRAW batch owner: unaligned compact stride");
        counts.buffer_allocation_bytes = add(counts.buffer_allocation_bytes, total);
    }
    // Sum decimal key lengths by digit ranges, not by block enumeration.
    uint64_t remaining = blocks, first = 0, upper = 10, width = 1;
    while (remaining) {
        const auto in_range = std::min(remaining, upper - first);
        uint64_t per_block = add(10, width); // b:N:origin + NUL
        for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot)
            if (plan.layout.streams[slot].instance) per_block = add(per_block, add(add(11, width), digits(slot)));
        counts.edge_key_bytes = add(counts.edge_key_bytes, multiply(in_range, per_block));
        remaining -= in_range;
        first = upper;
        if (remaining) { upper = multiply(upper, 10); ++width; }
    }
    finish_counts(counts, limits);
    return counts;
}

// Builder contract: make_root(), make_leaf(vector<uint8_t>&&, LeafKind), and
// attach(Record& root, string key, const Record& child). All three may throw.
// They MUST build only local unpublished records, never mutate a live cache.
// The caller must keep immutable source revisions alive during this call.
template<class Record, class Build>
PreparedOwner<Record> prepare_owner(Plan plan, std::span<const Source> sources,
                                   Limits limits, uint64_t max_uniform_bytes, Build&& build) {
    auto counts = measure_owner<Record>(plan, limits, max_uniform_bytes);
    if (!plan.selected_count || !plan.instances) return {};
    require_sources(plan, sources);
    auto data = std::make_shared<OwnerData<Record>>();
    data->plan = std::move(plan);
    data->geometry.resize(data->plan.geometry.size());
    data->blocks.resize(static_cast<size_t>(data->plan.instance_block_count));
    for (auto& g : data->geometry) g.vertices.resize(data->plan.layout.streams.size());
    for (auto& b : data->blocks) b.instances.resize(data->plan.layout.streams.size());
    // Check actual metadata vector capacities before packing or record builds.
    counts.metadata_bytes = data->metadata_storage_bytes();
    finish_counts(counts, limits);
    data->counts = counts;
    auto root = build.make_root();
    auto leaf = [&](std::vector<uint8_t> bytes, LeafKind kind, char domain, uint64_t number, uint64_t slot = 0) {
        auto record = build.make_leaf(std::move(bytes), kind);
        build.attach(root, edge_key(domain, number, kind, slot), record);
        return record;
    };
    for (size_t g = 0; g < data->geometry.size(); ++g) {
        const auto& batch = data->plan.geometry[g];
        auto& records = data->geometry[g];
        std::vector<uint8_t> identity(data->plan.indexed ? static_cast<size_t>(multiply(batch.original_vertices.size(), 4)) : 4);
        if (data->plan.indexed) std::memcpy(identity.data(), batch.original_vertices.data(), identity.size());
        else std::memcpy(identity.data(), &batch.vertex_base, 4);
        records.identity = leaf(std::move(identity), LeafKind::GeometryIdentity, 'g', g);
        if (data->plan.indexed) {
            std::vector<uint8_t> indices(static_cast<size_t>(multiply(batch.remapped_indices.size(), 4)));
            std::memcpy(indices.data(), batch.remapped_indices.data(), indices.size());
            records.index = leaf(std::move(indices), LeafKind::Indices, 'g', g);
        }
        for (size_t slot = 0; slot < data->plan.layout.streams.size(); ++slot)
            if (!data->plan.layout.streams[slot].instance)
                records.vertices[slot] = leaf(pack_vertex_stream(data->plan, g, slot, sources),
                    LeafKind::VertexStream, 'g', g, slot);
    }
    for (size_t b = 0; b < data->blocks.size(); ++b) {
        auto& records = data->blocks[b];
        const auto block = data->plan.instance_block(b);
        if (block.first > UINT32_MAX) throw std::length_error("DRAW batch owner: instance origin exceeds uint32");
        const InstanceOrigin origin{static_cast<uint32_t>(block.first), {0, 0, 0}};
        std::vector<uint8_t> bytes(instance_origin_bytes);
        std::memcpy(bytes.data(), &origin, sizeof(origin));
        records.origin = leaf(std::move(bytes), LeafKind::InstanceOrigin, 'b', b);
        for (size_t slot = 0; slot < data->plan.layout.streams.size(); ++slot)
            if (data->plan.layout.streams[slot].instance)
                records.instances[slot] = leaf(pack_instance_stream(data->plan, b, slot, sources),
                    LeafKind::InstanceStream, 'b', b, slot);
    }
    return {std::move(root), std::move(data)};
}

// A single immutable key+complete-owner entry. Staging may throw, publication
// is only a noexcept shared_ptr swap. This models one current cache entry,
// NOT a transaction over runtime history/LRU/category/pending-frame state.
template<class Record> struct CacheEntry { std::string key; PreparedOwner<Record> prepared; };
template<class Record, class Prepare>
void prepare_and_publish_current(std::shared_ptr<const CacheEntry<Record>>& current,
                                 std::string key, Prepare&& prepare) {
    auto next = std::make_shared<const CacheEntry<Record>>(CacheEntry<Record>{std::move(key), prepare()});
    current.swap(next);
}

} // namespace vispy::inputs::batches::owners
