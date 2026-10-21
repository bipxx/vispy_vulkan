#include "runtime_point_batch_owner.hpp"

#include <iostream>

namespace {
namespace points = vispy::points;
namespace batches = points::batches;
namespace owners = batches::owners;
namespace inputs = vispy::inputs;

void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
template<class F> void rejects(F&& f, const char* message) {
    try { f(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
void word(std::vector<uint8_t>& out, uint32_t value) {
    const auto at = out.size(); out.resize(at + 4); std::memcpy(out.data() + at, &value, 4);
}
uint32_t bits(size_t field, uint64_t element, size_t component) {
    constexpr uint32_t special[] = {0x80000000u, 0x7fc12345u, 0xff800000u, 0x3f800001u};
    return special[component] ^ static_cast<uint32_t>(field * 0x10000 + element * 0x101);
}
struct Fixture {
    std::array<std::vector<uint8_t>, 4> storage;
    std::array<points::PackedSource, 4> sources;
    std::array<uint32_t, 4> widths;
    bool sparse;
    Fixture(std::array<uint32_t, 4> sizes, bool sparse_ids = false) : widths(sizes), sparse(sparse_ids) {
        for (size_t field = 0; field < 4; ++field) {
            const uint64_t divisor = field == 1 ? 2 : field == 2 ? 3 : 0;
            const uint64_t stride = field == 3 || (sparse && field == 0) ? 0 : widths[field] + 5;
            const uint64_t elements = !stride ? 1 : divisor ? 12 / divisor + 1 : 20;
            const uint64_t offset = field + 1;
            auto& bytes = storage[field];
            bytes.resize(static_cast<size_t>(offset + (elements - 1) * stride + widths[field]), 0xda);
            for (uint64_t element = 0; element < elements; ++element)
                for (size_t component = 0; component < widths[field] / 4; ++component) {
                    const auto value = bits(field, element, component);
                    std::memcpy(bytes.data() + offset + element * stride + component * 4, &value, 4);
                }
            sources[field] = {bytes, field + 1, 7, offset, stride, widths[field], divisor, "raw"};
        }
    }
};
std::vector<uint8_t> indices(const std::vector<uint32_t>& ids, uint32_t width) {
    if (!width) return {};
    std::vector<uint8_t> result(ids.size() * width);
    for (size_t n = 0; n < ids.size(); ++n) {
        if (width == 1) result[n] = static_cast<uint8_t>(ids[n]);
        else if (width == 2) {
            const auto value = static_cast<uint16_t>(ids[n]); std::memcpy(result.data() + n * 2, &value, 2);
        } else std::memcpy(result.data() + n * 4, &ids[n], 4);
    }
    return result;
}
struct Expected {
    std::vector<uint8_t> identity;
    std::vector<std::vector<uint8_t>> streams;
};
Expected oracle(const Fixture& fixture, const std::vector<uint32_t>& ids,
                const std::vector<std::vector<size_t>>& fields) {
    Expected expected; expected.streams.resize(fields.size());
    for (uint32_t instance = 0; instance < 13; ++instance)
        for (auto vertex : ids) {
            word(expected.identity, vertex); word(expected.identity, instance);
            for (size_t slot = 0; slot < fields.size(); ++slot)
                for (size_t field : fields[slot]) {
                    const uint64_t element = field == 1 ? instance / 2 : field == 2 ? instance / 3 :
                        field == 3 || fixture.sparse ? 0 : vertex;
                    for (size_t component = 0; component < fixture.widths[field] / 4; ++component)
                        word(expected.streams[slot], bits(field, element, component));
                }
        }
    return expected;
}
void verify(const Fixture& fixture, const std::vector<uint32_t>& ids, uint32_t index_width,
            uint32_t stride_cap, const std::vector<std::vector<size_t>>& expected_fields,
            uint64_t buffer_cap, uint64_t storage_cap, bool expect_seam) {
    auto bytes = indices(ids, index_width);
    points::Selection selected{11, ids.size(), 13};
    if (index_width) { selected.indices = bytes; selected.index_bytes = index_width; selected.first = UINT64_MAX; }
    const auto layout = points::partitioned_layout(fixture.widths, 4, 2, stride_cap);
    check(layout.streams.size() == expected_fields.size(), "exact physical stream count");
    for (size_t slot = 0; slot < expected_fields.size(); ++slot) {
        check(layout.streams[slot].fields == expected_fields[slot], "independent exact partition map");
        check(layout.streams[slot].instance && !layout.streams[slot].bind_offset, "all point streams instance step");
    }
    const auto plan = batches::plan(selected, fixture.sources, layout,
        {buffer_cap, storage_cap, sizeof(batches::Plan), 4096});
    check(plan.stream_count() == expected_fields.size() && plan.packed_stride() == 40 &&
          plan.max_stream_stride() == stride_cap, "plan stores total versus individual stream stride");
    if (stride_cap == 20 && buffer_cap == 60 && storage_cap == 24)
        check(plan.rows_per_batch() == 3, "capacity uses largest stream, not aggregate stride");
    Expected actual; actual.streams.resize(expected_fields.size());
    bool seam = false;
    uint64_t cursor = 0;
    for (uint64_t number = 0; number < plan.encoded_draws(); ++number) {
        const auto range = plan.range(number);
        check(range.first == cursor, "ordered row ranges");
        seam |= range.first / ids.size() != (range.first + range.count - 1) / ids.size();
        auto identity = batches::identity_data(plan, number);
        check(identity.size() <= buffer_cap && identity.size() <= storage_cap, "identity grants");
        actual.identity.insert(actual.identity.end(), identity.begin(), identity.end());
        for (uint32_t slot = 0; slot < plan.stream_count(); ++slot) {
            auto data = batches::packed_data(plan, fixture.sources, layout, number, slot);
            check(data.size() == range.count * layout.streams[slot].stride && data.size() <= buffer_cap,
                  "each physical stream obeys its own allocation grant");
            actual.streams[slot].insert(actual.streams[slot].end(), data.begin(), data.end());
        }
        cursor += range.count;
    }
    const auto expected = oracle(fixture, ids, expected_fields);
    check(actual.identity == expected.identity && actual.streams == expected.streams,
          "independent original IDs, global divisor 2/3 and raw-bit oracle");
    check(cursor == 65 && (!expect_seam || seam), "full flattened domain and instance seam");
    rejects([&] { batches::packed_data(plan, fixture.sources, layout, 0, plan.stream_count()); }, "bad slot accepted");
}

void layouts_and_seams() {
    const Fixture non_greedy({12, 12, 8, 8});
    const Fixture mixed({4, 8, 12, 16});
    const std::vector<uint32_t> arrays{11, 12, 13, 14, 15}, selected{6, 1, 4, 1, 7};
    for (uint32_t width : {0u, 1u, 2u, 4u}) {
        const auto& ids = width ? selected : arrays;
        verify(non_greedy, ids, width, 20, {{0, 2}, {1, 3}}, 60, 24, true);
        verify(mixed, ids, width, 20, {{0, 3}, {1, 2}}, 60, 24, true);
        verify(mixed, ids, width, 40, {{0, 1, 2, 3}}, 4096, 4096, false);
    }
    const uint32_t widths[] = {4, 8, 12, 16};
    const auto old = points::packed_layout(widths, 4, 1, 40);
    const auto same = points::partitioned_layout(widths, 4, 1, 40);
    check(same.streams.size() == 1 && same.offsets == old.offsets && same.streams[0].stride == old.stride,
          "one-stream ABI offsets and stride unchanged");
    const points::Selection one_stream_selection{11, 5, 13};
    const auto one_stream_plan = batches::plan(one_stream_selection, mixed.sources, same,
                                              {4096, 4096, sizeof(batches::Plan), 1});
    check(batches::packed_data(one_stream_plan, mixed.sources, same, 0, 0) ==
          points::packed_data(one_stream_selection, mixed.sources, old, 4096),
          "one-stream payload is byte-exact with existing whole-row packing");
    bool attribute_refused = false;
    try {
        points::partitioned_layout(widths, 3, 8, 40);
    } catch (const std::runtime_error& error) {
        attribute_refused = true;
        check(std::string(error.what()) ==
              "DRAW point partition: active user inputs exceed granted attribute limit",
              "public attribute-limit diagnostic changed");
    }
    check(attribute_refused, "attribute grant ignored");
    rejects([&] { points::partitioned_layout(widths, 4, 1, 20); }, "stream count grant ignored");
    rejects([&] { points::partitioned_layout(widths, 4, 4, 12); }, "individual width grant ignored");
    for (uint32_t width : {1u, 2u, 4u}) {
        const auto high = width == 1 ? 255u : width == 2 ? 65535u : UINT32_MAX;
        const std::vector<uint32_t> ids{high, 0, high, width == 4 ? 0x80000001u : 1u, high};
        verify(Fixture({12, 12, 8, 8}, true), ids, width, 20, {{0, 2}, {1, 3}}, 60, 24, true);
    }
}

struct Node;
using Record = std::shared_ptr<Node>;
struct Node {
    std::vector<uint8_t> bytes;
    std::unordered_map<std::string, Record> children;
    std::shared_ptr<const owners::OwnerData<Record>> data;
};
struct Trace {
    size_t roots = 0, leaves = 0, attaches = 0, fail_leaf = 0, fail_attach = 0;
    std::vector<std::weak_ptr<Node>> nodes;
};
struct Builder {
    std::shared_ptr<Trace> trace;
    Record node() const { auto node = std::make_shared<Node>(); trace->nodes.push_back(node); return node; }
    Record make_root() const { ++trace->roots; return node(); }
    Record make_leaf(std::vector<uint8_t>&& bytes, owners::LeafKind) const {
        if (++trace->leaves == trace->fail_leaf) throw std::runtime_error("late leaf failure");
        auto result = node(); result->bytes = std::move(bytes); return result;
    }
    void attach(Record& root, std::string key, const Record& child) const {
        if (++trace->attaches == trace->fail_attach) throw std::runtime_error("late attach failure");
        check(root->children.emplace(std::move(key), child).second, "unique stream-specific edge key");
    }
};
owners::Limits grants() { return {1024 * 1024, 1024 * 1024, 2 * 1024 * 1024, 4096, 128, 64}; }

void owning_streams() {
    owners::PreparedOwner<Record> owned;
    Expected expected;
    auto trace = std::make_shared<Trace>();
    {
        Fixture fixture({12, 12, 8, 8});
        const std::vector<uint32_t> ids{6, 1, 4, 1, 7};
        auto bytes = indices(ids, 2);
        const points::Selection selected{0, 5, 13, bytes, 2};
        const auto layout = points::partitioned_layout(fixture.widths, 4, 2, 20);
        const auto plan = batches::plan(selected, fixture.sources, layout, {60, 24, sizeof(batches::Plan), 22});
        owned = owners::prepare_owner<Record>(plan, fixture.sources, layout, grants(), Builder{trace}, true);
        expected = oracle(fixture, ids, {{0, 2}, {1, 3}});
    }
    Expected actual; actual.streams.resize(2);
    uint64_t payload = 0, capacities = 0, keys = 0;
    uint64_t metadata = sizeof(owners::OwnerData<Record>) + 2 * sizeof(void*) +
        owned.data->draws.capacity() * sizeof(owners::Draw<Record>);
    for (size_t number = 0; number < owned.data->draws.size(); ++number) {
        const auto& draw = owned.data->draws[number];
        check(draw.users.size() == 2 && draw.identity, "all physical streams independently owned");
        metadata += draw.users.capacity() * sizeof(Record);
        for (uint32_t slot = 0; slot < 2; ++slot) {
            check(owned.root->children.at(owners::edge_key(number, owners::LeafKind::Users, slot)) == draw.users[slot],
                  "root and descriptor share exact stream owner");
            const auto& bytes = draw.users[slot]->bytes;
            actual.streams[slot].insert(actual.streams[slot].end(), bytes.begin(), bytes.end());
            payload += bytes.size(); capacities += bytes.capacity();
        }
        const auto& bytes = draw.identity->bytes;
        actual.identity.insert(actual.identity.end(), bytes.begin(), bytes.end());
        payload += bytes.size(); capacities += bytes.capacity();
    }
    for (const auto& [key, value] : owned.root->children) { (void)value; keys += key.capacity() + 1; }
    check(actual.identity == expected.identity && actual.streams == expected.streams,
          "owning stream oracle remains valid after all producer lifetimes end");
    const auto& counts = owned.data->counts;
    check(counts.records == 67 && counts.edges == 66 && counts.edge_key_bytes == keys &&
          counts.payload_bytes == payload && counts.payload_capacity_bytes == capacities &&
          counts.metadata_bytes == metadata && owned.data->metadata_storage_bytes() == metadata,
          "actual per-stream records, key capacities and per-draw user vector capacities charged");
    owned.root->data = owned.data;
    const std::weak_ptr<Node> weak_root = owned.root, weak_leaf = owned.data->draws.front().users.front();
    owned.root.reset();
    check(weak_root.expired() && !weak_leaf.expired(), "no root-data ownership cycle");
    owned.data.reset();
    check(weak_leaf.expired(), "last descriptor owner releases every stream");
    for (const auto& weak : trace->nodes) check(weak.expired(), "complete private graph released");
}

void refusal_and_budgets() {
    Fixture fixture({12, 12, 8, 8});
    const points::Selection selected{11, 5, 13};
    const auto layout = points::partitioned_layout(fixture.widths, 4, 2, 20);
    const batches::Limits limits{60, 24, sizeof(batches::Plan), 22};
    const auto plan = batches::plan(selected, fixture.sources, layout, limits);
    const auto signature = points::partition_key(layout, fixture.sources);
    auto changed_sources = fixture.sources; changed_sources[0].divisor = 7;
    check(points::partition_key(layout, changed_sources) == signature, "physical key independent of original divisor");
    auto changed = layout;
    std::swap(changed.streams[0], changed.streams[1]);
    for (size_t slot = 0; slot < changed.streams.size(); ++slot)
        for (size_t field : changed.streams[slot].fields) changed.slots[field] = static_cast<uint32_t>(slot);
    check(points::partition_key(changed, fixture.sources) != signature, "exact cache domain distinguishes physical slot map");
    rejects([&] { batches::packed_data(plan, fixture.sources, changed, 0, 0); }, "same-stride altered partition accepted");
    auto trace = std::make_shared<Trace>();
    rejects([&] { owners::prepare_owner<Record>(plan, fixture.sources, changed, grants(), Builder{trace}, true); },
            "altered owner partition accepted");
    check(!trace->roots, "altered layout refused before Builder");
    for (unsigned failure = 0; failure < 8; ++failure) {
        auto invalid = layout;
        auto sources = fixture.sources;
        if (failure == 0) invalid.streams[0].fields.push_back(0);
        if (failure == 1) invalid.streams[0].fields.pop_back();
        if (failure == 2) invalid.streams[0].instance = false;
        if (failure == 3) invalid.offsets[2] += 4;
        if (failure == 4) invalid.slots[2] = 1;
        if (failure == 5) invalid.streams[0].bind_offset = 4;
        if (failure == 6) invalid.direct = true;
        if (failure == 7) sources[0].element_bytes = 3;
        rejects([&] { points::partition_key(invalid, sources); }, "malformed physical map admitted");
        rejects([&] { batches::plan(selected, sources, invalid, limits); }, "malformed planner map admitted");
    }
    const auto complete = owners::prepare_owner<Record>(plan, fixture.sources, layout, grants(),
                                                       Builder{std::make_shared<Trace>()}, true);
    const auto measured = owners::measure_owner<Record>(plan, grants(), true);
    check(measured.retained_bytes == complete.data->counts.retained_bytes, "preflight includes all nested user-vector capacities");
    auto exact = grants(); const auto& counts = complete.data->counts;
    exact.max_payload_bytes = counts.payload_capacity_bytes; exact.max_control_bytes = counts.control_bytes;
    exact.max_retained_bytes = counts.retained_bytes; exact.max_records = counts.records;
    check(owners::prepare_owner<Record>(plan, fixture.sources, layout, exact,
          Builder{std::make_shared<Trace>()}, true).data->counts.retained_bytes == exact.max_retained_bytes,
          "exact aggregate grants admitted");
    for (unsigned failure = 0; failure < 6; ++failure) {
        auto reduced = exact;
        if (failure == 0) --reduced.max_payload_bytes;
        if (failure == 1) --reduced.max_control_bytes;
        if (failure == 2) --reduced.max_retained_bytes;
        if (failure == 3) --reduced.max_records;
        if (failure == 4) reduced.node_bytes = UINT64_MAX;
        if (failure == 5) reduced.edge_bytes = UINT64_MAX;
        auto state = std::make_shared<Trace>();
        rejects([&] { owners::prepare_owner<Record>(plan, fixture.sources, layout, reduced, Builder{state}, true); },
                "aggregate multi-stream budget ignored");
        check(!state->roots && !state->leaves, "aggregate refusal before Builder or payload retention");
    }
    std::unordered_map<std::string, Record> cache{{"before", complete.root}};
    for (bool attach : {false, true}) {
        auto state = std::make_shared<Trace>();
        if (attach) state->fail_attach = 8; else state->fail_leaf = 8;
        rejects([&] {
            auto next = owners::prepare_owner<Record>(plan, fixture.sources, layout, grants(), Builder{state}, true);
            cache.at("before") = next.root;
        }, "late multi-stream builder failure ignored");
        check(cache.at("before") == complete.root && state->leaves >= 8, "late failure preserves published predecessor");
        for (const auto& weak : state->nodes) check(weak.expired(), "late private graph rolled back");
    }
    changed_sources = fixture.sources; changed_sources[1].bytes = changed_sources[1].bytes.first(2);
    trace = std::make_shared<Trace>();
    rejects([&] { owners::prepare_owner<Record>(plan, changed_sources, layout, grants(), Builder{trace}, true); },
            "truncated global divisor source admitted");
    check(!trace->roots, "all-source revalidation before Builder");
    rejects([&] { batches::plan(selected, fixture.sources, layout, {19, 24, sizeof(batches::Plan), 100}); },
            "one physical user row overflow admitted");
    rejects([&] { batches::plan(selected, fixture.sources, layout, {60, 7, sizeof(batches::Plan), 100}); },
            "identity grant ignored");
    rejects([&] { batches::plan(selected, fixture.sources, layout, {60, 24, sizeof(batches::Plan) - 1, 100}); },
            "fixed plan control grant ignored");
    rejects([&] { batches::plan(selected, fixture.sources, layout, {60, 24, sizeof(batches::Plan), 21}); },
            "encoded draw grant ignored");
    const auto no_identity = owners::prepare_owner<Record>(plan, fixture.sources, layout, grants(),
        Builder{std::make_shared<Trace>()}, false);
    check(no_identity.data->counts.records == 45 && no_identity.data->packed_bytes == 65 * 40,
          "dead identity omitted while both user streams retained");
    inputs::Layout empty;
    const auto huge = batches::plan({0, INT32_MAX, INT32_MAX}, {}, empty,
        {8, 8, sizeof(batches::Plan), UINT64_MAX});
    trace = std::make_shared<Trace>();
    rejects([&] { owners::prepare_owner<Record>(huge, {}, empty, grants(), Builder{trace}, true); },
            "huge implicit owner allocation admitted");
    check(!trace->roots, "huge scalar plan refused without enumerating draws");
    auto invalid = layout; invalid.streams[0].instance = false;
    changed_sources = fixture.sources; changed_sources[0].offset = UINT64_MAX;
    for (auto zero : {points::Selection{0, 0, 13}, points::Selection{11, 5, 0}}) {
        const auto zero_plan = batches::plan(zero, changed_sources, invalid, {});
        trace = std::make_shared<Trace>();
        const auto owner = owners::prepare_owner<Record>(zero_plan, changed_sources, invalid, {}, Builder{trace}, true);
        check(!owner.root && !owner.data && !trace->roots, "zero domains avoid all layout/source/grant reads");
    }
}
} // namespace

int main() {
    try {
        layouts_and_seams(); owning_streams(); refusal_and_budgets();
        std::cout << "point_partition_contract: PASS (CPU physical streams and owning preparation)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "point_partition_contract: " << error.what() << '\n'; return 1;
    }
}
