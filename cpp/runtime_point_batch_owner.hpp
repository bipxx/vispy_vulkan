#pragma once

#include "runtime_point_batch.hpp"

namespace vispy::points::batches::owners {

enum class LeafKind { Users, Identity };

struct Limits {
    uint64_t max_payload_bytes = 0;
    uint64_t max_control_bytes = 0;
    uint64_t max_retained_bytes = 0;
    uint64_t max_records = 0;
    // Caller-defined representation charges for each root/leaf and root edge.
    // These include shared ownership and container bookkeeping. Retained key
    // character capacity is charged separately, including a terminator.
    uint64_t node_bytes = 0;
    uint64_t edge_bytes = 0;
};

inline uint64_t add(uint64_t a, uint64_t b) {
    if (b > UINT64_MAX - a)
        throw std::length_error("DRAW point owner: representation addition overflow");
    return a + b;
}

struct Counts {
    uint64_t payload_bytes = 0, payload_capacity_bytes = 0;
    uint64_t records = 0, edges = 0, edge_key_bytes = 0;
    uint64_t metadata_bytes = 0, control_bytes = 0, retained_bytes = 0;
};

template<class Record> struct Draw {
    std::vector<Record> users;
    Record identity{};
    uint32_t instances = 0;
};

// Only owning records survive preparation. In particular, no Selection/Plan,
// borrowed index/source span, root, or parent backreference is retained here.
template<class Record> struct OwnerData {
    std::vector<Draw<Record>> draws;
    uint64_t total_rows = 0;
    uint64_t packed_bytes = 0;
    Counts counts;

    uint64_t metadata_storage_bytes() const {
        auto bytes = add(add(sizeof(OwnerData), 2 * sizeof(void*)),
                         checked_product(draws.capacity(), sizeof(Draw<Record>)));
        for (const auto& draw : draws)
            bytes = add(bytes, checked_product(draw.users.capacity(), sizeof(Record)));
        return bytes;
    }
    uint64_t payload_bytes() const { return packed_bytes; }
};

template<class Record> struct PreparedOwner {
    Record root{};
    std::shared_ptr<const OwnerData<Record>> data;
};

inline uint64_t digits(uint64_t number) {
    uint64_t width = 1;
    while (number >= 10) { number /= 10; ++width; }
    return width;
}

inline uint64_t key_length(uint64_t width, LeafKind kind) {
    return add(width, kind == LeafKind::Users ? 8 : 11); // p:N:users / p:N:identity
}

inline std::string edge_key(uint64_t number, LeafKind kind) {
    const auto decimal = std::to_string(number);
    const std::string_view suffix = kind == LeafKind::Users ? ":users" : ":identity";
    // Exact-size construction makes the character-capacity policy identical to
    // preflight, including implementations that retain an inline string buffer.
    std::string result(static_cast<size_t>(key_length(decimal.size(), kind)), '\0');
    result[0] = 'p'; result[1] = ':';
    std::memcpy(result.data() + 2, decimal.data(), decimal.size());
    std::memcpy(result.data() + 2 + decimal.size(), suffix.data(), suffix.size());
    return result;
}

inline uint64_t key_storage(uint64_t width, LeafKind kind) {
    return add(std::string(static_cast<size_t>(key_length(width, kind)), '\0').capacity(), 1);
}

inline std::string edge_key(uint64_t number, LeafKind kind, uint32_t slot) {
    if (kind == LeafKind::Identity) return edge_key(number, kind);
    const auto decimal = std::to_string(number), stream = std::to_string(slot);
    std::string result(static_cast<size_t>(add(add(decimal.size(), stream.size()), 9)), '\0');
    result[0] = 'p'; result[1] = ':';
    std::memcpy(result.data() + 2, decimal.data(), decimal.size());
    std::memcpy(result.data() + 2 + decimal.size(), ":users:", 7);
    std::memcpy(result.data() + 9 + decimal.size(), stream.data(), stream.size());
    return result;
}

inline uint64_t partition_key_storage(uint64_t number_width, uint64_t slot_width) {
    return add(std::string(static_cast<size_t>(add(add(number_width, slot_width), 9)), '\0').capacity(), 1);
}

inline uint64_t users_key_storage(const Plan& plan, uint64_t number_width) {
    if (!plan.stream_count()) return 0;
    if (!plan.partitioned()) return key_storage(number_width, LeafKind::Users);
    uint64_t result = 0, remaining = plan.stream_count(), first = 0, upper = 10, width = 1;
    while (remaining) {
        const auto in_range = std::min(remaining, upper - first);
        result = add(result, checked_product(in_range, partition_key_storage(number_width, width)));
        remaining -= in_range; first = upper;
        if (remaining) { upper = checked_product(upper, 10); ++width; }
    }
    return result;
}

inline void finish_counts(Counts& counts, const Limits& limits) {
    counts.control_bytes = add(counts.metadata_bytes,
        add(checked_product(counts.records, limits.node_bytes),
            add(checked_product(counts.edges, limits.edge_bytes), counts.edge_key_bytes)));
    counts.retained_bytes = add(counts.control_bytes, counts.payload_capacity_bytes);
    if (counts.records > limits.max_records || counts.payload_bytes > limits.max_payload_bytes ||
        counts.payload_capacity_bytes > limits.max_payload_bytes ||
        counts.control_bytes > limits.max_control_bytes || counts.retained_bytes > limits.max_retained_bytes ||
        counts.metadata_bytes > SIZE_MAX)
        throw std::length_error("DRAW point owner: explicit retained representation budget exceeded");
}

// Allocation-free in batch count: decimal-width probes use at most twenty
// tiny strings, never an encoded-draw table or a loop over all flattened rows.
// All payload/record/draw-vector lower bounds are admitted before allocation.
template<class Record>
Counts measure_owner(const Plan& plan, const Limits& limits, bool identity_live) {
    Counts counts;
    if (!plan.total_rows()) return counts;
    const auto draw_count = plan.encoded_draws();
    const uint64_t users = plan.stream_count();
    const uint64_t identities = identity_live;
    counts.records = add(1, checked_product(draw_count, add(users, identities)));
    counts.edges = counts.records - 1;
    const auto row_bytes = add(plan.packed_stride(), checked_product(identities, identity_row_bytes));
    counts.payload_bytes = checked_product(plan.total_rows(), row_bytes);
    counts.payload_capacity_bytes = counts.payload_bytes;
    counts.metadata_bytes = add(add(sizeof(OwnerData<Record>), 2 * sizeof(void*)),
        add(checked_product(draw_count, sizeof(Draw<Record>)),
            checked_product(checked_product(draw_count, users), sizeof(Record))));
    finish_counts(counts, limits);

    // Charge actual key string capacities by decimal width, not by draw.
    uint64_t remaining = draw_count, first = 0, upper = 10, width = 1;
    while (remaining) {
        const uint64_t in_range = std::min(remaining, upper - first);
        uint64_t per_draw = 0;
        if (users) per_draw = add(per_draw, users_key_storage(plan, width));
        if (identities) per_draw = add(per_draw, key_storage(width, LeafKind::Identity));
        counts.edge_key_bytes = add(counts.edge_key_bytes, checked_product(in_range, per_draw));
        remaining -= in_range;
        first = upper;
        if (remaining) { upper = checked_product(upper, 10); ++width; }
    }
    finish_counts(counts, limits);
    return counts;
}

// Builder: make_root(), make_leaf(vector<uint8_t>&&, LeafKind), and
// attach(Record&, string, const Record&). Builder operations may throw, must
// retain moved buffers/keys without increasing their storage, and build only
// private unpublished records. Caller cache publication happens after return.
// node_bytes/edge_bytes must cover any generic Builder/container bookkeeping;
// these are portable representation budgets, not allocator peaks or GPU/RSS.
template<class Record, class Builder, class Validate, class Pack>
PreparedOwner<Record> prepare_owner_impl(const Plan& plan, std::span<const PackedSource> sources,
        Limits limits, Builder&& builder, bool identity_live, Validate&& validate, Pack&& pack) {
    auto counts = measure_owner<Record>(plan, limits, identity_live);
    if (!plan.total_rows()) return {};
    validate();
    if (!sources.empty())
        inputs::validate_sources(plan.selection(), sources, inputs::maximum_vertex(plan.selection()));

    auto data = std::make_shared<OwnerData<Record>>();
    data->draws.resize(static_cast<size_t>(plan.encoded_draws()));
    for (auto& draw : data->draws) draw.users.resize(plan.stream_count());
    data->total_rows = plan.total_rows();
    data->packed_bytes = counts.payload_bytes;
    // Observe actual descriptor-vector capacity before any payload or builder
    // allocation. Over-allocation is refused without publishing a root.
    counts.metadata_bytes = data->metadata_storage_bytes();
    finish_counts(counts, limits);
    auto root = builder.make_root();
    auto leaf = [&](std::vector<uint8_t>&& bytes, LeafKind kind, uint64_t number, uint32_t slot) {
        if (bytes.empty() || bytes.capacity() > plan.limits().buffer_bytes ||
            (kind == LeafKind::Identity && bytes.capacity() > plan.limits().storage_bytes))
            throw std::length_error("DRAW point owner: leaf capacity exceeds granted buffer/storage limit");
        // Preflight charged every logical byte. Account any implementation's
        // extra byte-vector capacity before the Builder can retain this leaf.
        counts.payload_capacity_bytes = add(counts.payload_capacity_bytes, bytes.capacity() - bytes.size());
        finish_counts(counts, limits);
        auto key = plan.partitioned() ? edge_key(number, kind, slot) : edge_key(number, kind);
        const auto key_bytes = plan.partitioned() && kind == LeafKind::Users ?
            partition_key_storage(digits(number), digits(slot)) : key_storage(digits(number), kind);
        if (add(key.capacity(), 1) != key_bytes)
            throw std::length_error("DRAW point owner: key capacity differs from preflight");
        auto record = builder.make_leaf(std::move(bytes), kind);
        builder.attach(root, std::move(key), record);
        return record;
    };
    for (uint64_t number = 0; number < plan.encoded_draws(); ++number) {
        auto& draw = data->draws[static_cast<size_t>(number)];
        const auto range = plan.range(number);
        draw.instances = static_cast<uint32_t>(range.count);
        for (uint32_t slot = 0; slot < plan.stream_count(); ++slot)
            draw.users[slot] = leaf(pack(number, slot), LeafKind::Users, number, slot);
        if (identity_live)
            draw.identity = leaf(batches::identity_data(plan, number), LeafKind::Identity, number, 0);
    }
    data->counts = counts;
    return {std::move(root), std::move(data)};
}

template<class Record, class Builder>
PreparedOwner<Record> prepare_owner(const Plan& plan, std::span<const PackedSource> sources,
        const PackedLayout& layout, Limits limits, Builder&& builder, bool identity_live) {
    return prepare_owner_impl<Record>(plan, sources, limits, std::forward<Builder>(builder), identity_live,
        [&] {
            validate_packed_layout(sources, layout);
            if (plan.partitioned() || layout.stride != plan.packed_stride())
                throw std::runtime_error("DRAW point owner: packed layout differs from plan");
        }, [&](uint64_t number, uint32_t) { return batches::packed_data(plan, sources, layout, number); });
}

template<class Record, class Builder>
PreparedOwner<Record> prepare_owner(const Plan& plan, std::span<const PackedSource> sources,
        const inputs::Layout& layout, Limits limits, Builder&& builder, bool identity_live) {
    return prepare_owner_impl<Record>(plan, sources, limits, std::forward<Builder>(builder), identity_live,
        [&] { plan.validate_layout(sources, layout); },
        [&](uint64_t number, uint32_t slot) { return batches::packed_data(plan, sources, layout, number, slot); });
}

}  // namespace vispy::points::batches::owners
