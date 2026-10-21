#include "runtime_point_batch_owner.hpp"

#include <array>
#include <iostream>
#include <string>

namespace {
using vispy::points::PackedLayout;
using vispy::points::PackedSource;
using vispy::points::Selection;
namespace batch = vispy::points::batches;
namespace owners = batch::owners;

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}
template<class Function> void rejects(Function&& function, const std::string& message) {
    try { function(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
template<class T> std::vector<uint8_t> index_bytes(const std::vector<uint32_t>& ids) {
    std::vector<uint8_t> result(ids.size() * sizeof(T));
    for (size_t n = 0; n < ids.size(); ++n) {
        const T value = static_cast<T>(ids[n]);
        std::memcpy(result.data() + n * sizeof(T), &value, sizeof(T));
    }
    return result;
}
void append_word(std::vector<uint8_t>& output, uint32_t word) {
    const auto offset = output.size();
    output.resize(offset + 4);
    std::memcpy(output.data() + offset, &word, 4);
}

// Payloads intentionally include signed zero, infinities and NaN bit patterns.
// The independent oracle compares bytes; it never converts them to floats.
uint32_t word(size_t field, uint64_t element, size_t component) {
    constexpr uint32_t bits[] = {0x80000000, 0x7fc01234, 0xff800000, 0x3f800001};
    return bits[component % 4] ^ static_cast<uint32_t>(element * 0x101 + field * 0x20000);
}
struct Fixture {
    std::array<std::vector<uint8_t>, 4> storage;
    std::array<PackedSource, 4> sources;
    PackedLayout layout;
    explicit Fixture(uint64_t vertices, uint64_t instances) {
        const uint64_t widths[] = {4, 8, 12, 16};
        const uint64_t strides[] = {11, 13, 17, 0};
        const uint64_t offsets[] = {3, 5, 1, 7};
        const uint64_t divisors[] = {0, 2, 3, 0};
        for (size_t field = 0; field < 4; ++field) {
            const uint64_t elements = strides[field] == 0 ? 1 :
                divisors[field] ? (instances - 1) / divisors[field] + 1 : vertices;
            storage[field].resize(static_cast<size_t>(offsets[field] +
                (elements - 1) * strides[field] + widths[field]), 0xda);
            for (uint64_t element = 0; element < elements; ++element)
                for (size_t component = 0; component < widths[field] / 4; ++component) {
                    const uint32_t value = word(field, element, component);
                    std::memcpy(storage[field].data() + offsets[field] + element * strides[field] + component * 4,
                                &value, 4);
                }
            sources[field] = {storage[field], field + 1, 9, offsets[field], strides[field],
                              widths[field], divisors[field], "field"};
        }
        const uint32_t widths32[] = {4, 8, 12, 16};
        layout = vispy::points::packed_layout(widths32, 4, 1, 40);
    }
};

void verify(const Selection& selection, const std::vector<uint32_t>& original_ids,
            const Fixture& fixture, uint64_t buffer_cap, uint64_t storage_cap) {
    const auto plan = batch::plan(selection, fixture.sources, fixture.layout,
                                  {buffer_cap, storage_cap, sizeof(batch::Plan), 4096});
    require(plan.total_rows() == original_ids.size() * selection.instances, "flattened row count");
    require(plan.control_bytes() == sizeof(batch::Plan), "fixed logical plan charge");
    require(batch::physical_first_instance == 0, "point draw local instance starts at zero");
    std::vector<uint8_t> actual_identity, actual_packed, expected_identity, expected_packed;
    uint64_t cursor = 0;
    bool crossed_instance = false;
    for (uint64_t number = 0; number < plan.encoded_draws(); ++number) {
        const auto range = plan.range(number);
        require(range.first == cursor && range.count && range.count <= INT32_MAX, "contiguous bounded range");
        crossed_instance |= range.first / selection.count != (range.first + range.count - 1) / selection.count;
        auto identity = batch::identity_data(plan, number);
        auto packed = batch::packed_data(plan, fixture.sources, fixture.layout, number);
        require(identity.size() == range.count * 8 && identity.size() <= buffer_cap &&
                identity.size() <= storage_cap, "identity buffer/storage cap");
        require(packed.size() == range.count * 40 && packed.size() <= buffer_cap, "packed user buffer cap");
        actual_identity.insert(actual_identity.end(), identity.begin(), identity.end());
        actual_packed.insert(actual_packed.end(), packed.begin(), packed.end());
        cursor += range.count;
    }
    require(cursor == plan.total_rows(), "ranges cover original flattened domain exactly");
    require(crossed_instance, "fixture exercises a range crossing an instance seam");
    // Independent instance-major oracle uses fixture IDs directly, not the
    // production Selection::vertex or planner range calculations.
    for (uint32_t instance = 0; instance < selection.instances; ++instance)
        for (uint32_t vertex : original_ids) {
            append_word(expected_identity, vertex);
            append_word(expected_identity, instance);
            for (size_t field = 0; field < 4; ++field) {
                const uint64_t element = field == 0 ? vertex : field == 1 ? instance / 2 :
                                         field == 2 ? instance / 3 : 0;
                for (size_t component = 0; component <= field; ++component)
                    append_word(expected_packed, word(field, element, component));
            }
        }
    require(actual_identity == expected_identity, "original vertex and global instance ABI bytes");
    require(actual_packed == expected_packed, "raw attribute bits and global divisor 2/3 fetches");
    rejects([&] { plan.range(plan.encoded_draws()); }, "out-of-plan range accepted");
    rejects([&] { batch::identity_data(plan, UINT64_MAX); }, "overflowing batch number accepted");
}

void ordered_ranges_and_bits() {
    constexpr uint64_t instances = 13;
    Fixture fixture(17, instances);
    const std::vector<uint32_t> arrays = {11, 12, 13, 14, 15};
    verify({11, 5, instances}, arrays, fixture, 120, 40); // Three rows, user-buffer bound.
    verify({11, 5, instances}, arrays, fixture, 240, 16); // Two rows, identity-storage bound.
    const std::vector<uint32_t> indexed = {6, 1, 4, 1, 7};
    for (uint32_t width : {1u, 2u, 4u}) {
        auto bytes = width == 1 ? index_bytes<uint8_t>(indexed) :
                     width == 2 ? index_bytes<uint16_t>(indexed) : index_bytes<uint32_t>(indexed);
        verify({UINT64_MAX, indexed.size(), instances, bytes, width}, indexed, fixture, 120, 40);
    }
}

void identity_only_and_large_domains() {
    const PackedLayout empty;
    for (uint32_t width : {1u, 2u, 4u}) {
        const std::vector<uint32_t> ids = width == 1 ? std::vector<uint32_t>{255, 0, 255} :
            width == 2 ? std::vector<uint32_t>{65535, 0, 65535} :
                         std::vector<uint32_t>{UINT32_MAX, 0x80000001, UINT32_MAX};
        auto bytes = width == 1 ? index_bytes<uint8_t>(ids) :
                     width == 2 ? index_bytes<uint16_t>(ids) : index_bytes<uint32_t>(ids);
        const auto plan = batch::plan({0, ids.size(), 3, bytes, width}, {}, empty,
                                     {16, 16, sizeof(batch::Plan), 5});
        std::vector<uint8_t> actual, expected;
        for (uint64_t number = 0; number < plan.encoded_draws(); ++number) {
            auto payload = batch::identity_data(plan, number);
            actual.insert(actual.end(), payload.begin(), payload.end());
            require(batch::packed_data(plan, {}, empty, number).empty(), "identity-only has no user allocation");
        }
        for (uint32_t instance = 0; instance < 3; ++instance)
            for (auto vertex : ids) { append_word(expected, vertex); append_word(expected, instance); }
        require(actual == expected, "all-ones ordinary IDs and high uint32 identities survive seams");
    }

    // This domain exceeds the old single-draw flattened INT32 admission. It
    // must create a fixed-size plan without enumerating billions of batches.
    const auto huge = batch::plan({0, INT32_MAX, INT32_MAX}, {}, empty,
        {8, 8, sizeof(batch::Plan), UINT64_MAX});
    const uint64_t total = uint64_t(INT32_MAX) * INT32_MAX;
    require(huge.total_rows() == total && huge.encoded_draws() == total && huge.rows_per_batch() == 1,
            "large flattened domain stays implicit");
    const auto last = huge.range(total - 1);
    require(last.first == total - 1 && last.count == 1, "last huge implicit range");
    std::vector<uint8_t> last_expected;
    append_word(last_expected, INT32_MAX - 1); append_word(last_expected, INT32_MAX - 1);
    require(batch::identity_data(huge, total - 1) == last_expected, "last huge range original identities");
    const auto native = batch::plan({0, INT32_MAX, 2}, {}, empty,
        {UINT64_MAX, UINT64_MAX, sizeof(batch::Plan), 2});
    require(native.rows_per_batch() == INT32_MAX && native.encoded_draws() == 2,
            "physical draws retain native INT32 count limit");
    const auto high = batch::plan({UINT32_MAX, 1, 2}, {}, empty, {8, 8, sizeof(batch::Plan), 2});
    std::vector<uint8_t> high_expected;
    append_word(high_expected, UINT32_MAX); append_word(high_expected, 1);
    require(batch::identity_data(high, 1) == high_expected, "array high uint32 nonzero first");
}

void sparse_constant_and_divisor_sources() {
    const std::vector<uint32_t> ids = {UINT32_MAX, 0x80000001, UINT32_MAX};
    auto indices = index_bytes<uint32_t>(ids);
    const auto constant = index_bytes<uint32_t>({0x7fc12345});
    const auto instanced = index_bytes<uint32_t>({0x80000000, 0xff800000});
    std::array<PackedSource, 2> sources = {{
        {constant, 1, 1, 0, 0, 4, 0, "constant"},
        {instanced, 2, 1, 0, 4, 4, 2, "divisor"}
    }};
    const uint32_t widths[] = {4, 4};
    const auto layout = vispy::points::packed_layout(widths, 2, 1, 8);
    const batch::Limits limits{16, 16, sizeof(batch::Plan), 5};
    const Selection selected{0, 3, 3, indices, 4};
    const auto plan = batch::plan(selected, sources, layout, limits);
    std::vector<uint8_t> actual, expected;
    for (uint64_t number = 0; number < plan.encoded_draws(); ++number) {
        auto payload = batch::packed_data(plan, sources, layout, number);
        actual.insert(actual.end(), payload.begin(), payload.end());
    }
    for (uint32_t instance = 0; instance < 3; ++instance)
        for (size_t point = 0; point < ids.size(); ++point) {
            append_word(expected, 0x7fc12345);
            append_word(expected, instance < 2 ? 0x80000000 : 0xff800000);
        }
    require(actual == expected, "sparse high IDs keep stride-zero constants and original divisor IDs");
    sources[0].stride = 4;
    rejects([&] { batch::plan(selected, sources, layout, limits); }, "sparse out-of-range source admitted");
    rejects([&] { batch::packed_data(plan, sources, layout, 0); }, "sparse out-of-range source copied");
}

void admission_and_revalidation() {
    Fixture fixture(17, 13);
    const Selection selection{11, 5, 13};
    auto make = [&](batch::Limits limits) { return batch::plan(selection, fixture.sources, fixture.layout, limits); };
    const batch::Limits exact{120, 40, sizeof(batch::Plan), 22};
    require(make(exact).encoded_draws() == 22, "exact encoded-draw budget accepted");
    rejects([&] { make({120, 40, sizeof(batch::Plan), 21}); }, "draw budget ignored");
    rejects([&] { make({120, 40, sizeof(batch::Plan) - 1, 22}); }, "control budget ignored");
    rejects([&] { make({39, 40, sizeof(batch::Plan), 100}); }, "one user row beyond buffer cap accepted");
    rejects([&] { make({120, 7, sizeof(batch::Plan), 100}); }, "one identity row beyond storage cap accepted");
    rejects([&] { make({7, 120, sizeof(batch::Plan), 100}); }, "one identity row beyond buffer cap accepted");
    const auto plan = make(exact);
    auto sources = fixture.sources;
    sources[0].bytes = sources[0].bytes.first(5);
    rejects([&] { batch::plan(selection, sources, fixture.layout, exact); }, "truncated vertex source admitted");
    rejects([&] { batch::packed_data(plan, sources, fixture.layout, 0); }, "truncated pack source copied");
    sources = fixture.sources; sources[1].bytes = sources[1].bytes.first(12);
    rejects([&] { batch::plan(selection, sources, fixture.layout, exact); }, "global divisor source tail omitted");
    sources = fixture.sources; sources[0].offset = UINT64_MAX; sources[0].stride = UINT64_MAX;
    rejects([&] { batch::plan(selection, sources, fixture.layout, exact); }, "overflowing source address accepted");
    sources = fixture.sources; sources[0].element_bytes = 3;
    rejects([&] { batch::plan(selection, sources, fixture.layout, exact); }, "unsupported raw field width accepted");
    auto layout = fixture.layout; layout.offsets[1] += 1;
    rejects([&] { batch::plan(selection, fixture.sources, layout, exact); }, "noncontiguous layout accepted");
    layout = fixture.layout; layout.stride += 4;
    rejects([&] { batch::packed_data(plan, fixture.sources, layout, 0); }, "mismatched packing layout accepted");
    rejects([&] { batch::checked_product(UINT64_MAX, 2); }, "checked row-byte multiplication wrapped");
    rejects([&] { batch::plan({0, uint64_t(INT32_MAX) + 1, 1}, {}, PackedLayout{}, exact); }, "oversized original count accepted");
    rejects([&] { batch::plan({0, 1, uint64_t(INT32_MAX) + 1}, {}, PackedLayout{}, exact); }, "oversized original instances accepted");
    rejects([&] { batch::plan({UINT32_MAX, 2, 1}, {}, PackedLayout{}, exact); }, "array identity wrapped");
    const uint8_t one[] = {1};
    rejects([&] { batch::plan({0, 2, 1, one, 1}, {}, PackedLayout{}, exact); }, "truncated selected indices accepted");
    rejects([&] { batch::plan({0, 0, 1, {}, 3}, {}, PackedLayout{}, {}); }, "unsupported zero-draw index width accepted");

    // Either empty domain avoids source/layout reads and all resource grants.
    auto bad_layout = fixture.layout; bad_layout.stride = UINT32_MAX;
    sources = fixture.sources; sources[0].offset = UINT64_MAX;
    for (const Selection zero : {Selection{0, 0, 13}, Selection{11, 5, 0}}) {
        const auto empty = batch::plan(zero, sources, bad_layout, {});
        require(!empty.total_rows() && !empty.encoded_draws() && !empty.control_bytes(), "zero-draw no allocation");
        rejects([&] { empty.range(0); }, "zero-draw exposed a physical draw");
    }
}

struct OwnerNode;
using OwnerRecord = std::shared_ptr<OwnerNode>;
struct OwnerNode {
    std::vector<uint8_t> bytes;
    owners::LeafKind kind = owners::LeafKind::Users;
    std::unordered_map<std::string, OwnerRecord> children;
    std::shared_ptr<const owners::OwnerData<OwnerRecord>> data;
};
struct BuildState {
    uint64_t roots = 0, leaves = 0, attaches = 0;
    uint64_t fail_leaf = 0, fail_attach = 0;
    std::vector<std::weak_ptr<OwnerNode>> nodes;
};
struct OwnerBuilder {
    std::shared_ptr<BuildState> state;
    OwnerRecord node() const {
        auto result = std::make_shared<OwnerNode>();
        state->nodes.push_back(result);
        return result;
    }
    OwnerRecord make_root() const { ++state->roots; return node(); }
    OwnerRecord make_leaf(std::vector<uint8_t>&& bytes, owners::LeafKind kind) const {
        if (++state->leaves == state->fail_leaf) throw std::runtime_error("injected late leaf failure");
        auto result = node(); result->bytes = std::move(bytes); result->kind = kind;
        return result;
    }
    void attach(OwnerRecord& root, std::string key, const OwnerRecord& child) const {
        if (++state->attaches == state->fail_attach) throw std::runtime_error("injected late attach failure");
        require(root->children.emplace(std::move(key), child).second, "unique owner edge key");
    }
};
owners::Limits owner_limits() {
    return {1024 * 1024, 1024 * 1024, 2 * 1024 * 1024, 4096,
            sizeof(OwnerNode) + 2 * sizeof(void*),
            sizeof(decltype(OwnerNode::children)::value_type) + 4 * sizeof(void*)};
}

void owner_oracle_and_lifetime() {
    for (uint32_t width : {0u, 1u, 2u, 4u}) {
        owners::PreparedOwner<OwnerRecord> prepared;
        std::vector<uint8_t> expected_identity, expected_users;
        auto state = std::make_shared<BuildState>();
        {
            Fixture fixture(17, 13);
            const std::vector<uint32_t> ids = width ? std::vector<uint32_t>{6, 1, 4, 1, 7} :
                                                    std::vector<uint32_t>{11, 12, 13, 14, 15};
            auto indices = width == 1 ? index_bytes<uint8_t>(ids) :
                           width == 2 ? index_bytes<uint16_t>(ids) : index_bytes<uint32_t>(ids);
            Selection selected{11, ids.size(), 13};
            if (width) { selected.indices = indices; selected.index_bytes = width; }
            const auto plan = batch::plan(selected, fixture.sources, fixture.layout,
                                          {120, 40, sizeof(batch::Plan), 22});
            prepared = owners::prepare_owner<OwnerRecord>(plan, fixture.sources, fixture.layout,
                                                          owner_limits(), OwnerBuilder{state}, true);
            // Build an independent oracle while producers are alive, then
            // destroy every Plan, Selection, source, index and layout below.
            for (uint32_t instance = 0; instance < 13; ++instance)
                for (uint32_t vertex : ids) {
                    append_word(expected_identity, vertex); append_word(expected_identity, instance);
                    for (size_t field = 0; field < 4; ++field) {
                        const uint64_t element = field == 0 ? vertex : field == 1 ? instance / 2 :
                                                 field == 2 ? instance / 3 : 0;
                        for (size_t component = 0; component <= field; ++component)
                            append_word(expected_users, word(field, element, component));
                    }
                }
        }
        require(prepared.root && prepared.data && prepared.data->draws.size() == 22 &&
                prepared.data->total_rows == 65, "complete bounded owning draw table");
        std::vector<uint8_t> actual_identity, actual_users;
        uint64_t rows = 0, payload = 0, capacities = 0, keys = 0;
        for (size_t number = 0; number < prepared.data->draws.size(); ++number) {
            const auto& draw = prepared.data->draws[number];
            require(draw.instances == (number == 21 ? 2u : 3u), "owner physical draw row count");
            require(draw.users.size() == 1 && draw.users.front() && draw.identity && draw.users.front()->kind == owners::LeafKind::Users &&
                    draw.identity->kind == owners::LeafKind::Identity, "separate owning user/identity leaves");
            require(prepared.root->children.at(owners::edge_key(number, owners::LeafKind::Users)) == draw.users.front() &&
                    prepared.root->children.at(owners::edge_key(number, owners::LeafKind::Identity)) == draw.identity,
                    "root graph owns the exact descriptor leaves");
            require(draw.users.front()->bytes.size() == uint64_t(draw.instances) * 40 &&
                    draw.identity->bytes.size() == uint64_t(draw.instances) * 8,
                    "leaf payload matches physical instance count");
            actual_users.insert(actual_users.end(), draw.users.front()->bytes.begin(), draw.users.front()->bytes.end());
            actual_identity.insert(actual_identity.end(), draw.identity->bytes.begin(), draw.identity->bytes.end());
            rows += draw.instances;
            payload += draw.users.front()->bytes.size() + draw.identity->bytes.size();
            capacities += draw.users.front()->bytes.capacity() + draw.identity->bytes.capacity();
        }
        for (const auto& [key, child] : prepared.root->children) {
            (void)child; keys += key.capacity() + 1;
        }
        const auto& counts = prepared.data->counts;
        require(rows == 65 && actual_identity == expected_identity && actual_users == expected_users,
                "actual owner leaves match independent instance-major oracle after producers die");
        require(prepared.data->packed_bytes == payload && prepared.data->payload_bytes() == payload &&
                counts.payload_bytes == payload && counts.payload_capacity_bytes == capacities,
                "actual payload and byte-vector capacities charged");
        const uint64_t metadata = sizeof(owners::OwnerData<OwnerRecord>) + 2 * sizeof(void*) +
            prepared.data->draws.capacity() * sizeof(owners::Draw<OwnerRecord>) +
            prepared.data->draws.size() * sizeof(OwnerRecord);
        require(prepared.data->metadata_storage_bytes() == metadata && counts.metadata_bytes == metadata,
                "metadata has exact descriptor capacity and no duplicate node/edge cost");
        const auto limits = owner_limits();
        require(counts.records == 45 && counts.edges == 44 && counts.edge_key_bytes == keys &&
                counts.control_bytes == metadata + counts.records * limits.node_bytes +
                    counts.edges * limits.edge_bytes + keys &&
                counts.retained_bytes == counts.control_bytes + capacities, "complete retained representation charge");

        // Model runtime root->data as well as root->leaf ownership. Data has
        // no reverse edge: it can retain leaves after root destruction.
        prepared.root->data = prepared.data;
        std::weak_ptr<OwnerNode> weak_root = prepared.root;
        std::weak_ptr<OwnerNode> weak_leaf = prepared.data->draws.front().identity;
        prepared.root.reset();
        require(weak_root.expired() && !weak_leaf.expired(), "root has no ownership cycle");
        prepared.data.reset();
        require(weak_leaf.expired(), "last data owner releases leaves");
        for (const auto& weak : state->nodes) require(weak.expired(), "all private owner nodes released");
    }
}

void owner_optional_leaves_and_budgets() {
    Fixture fixture(17, 13);
    const auto plan = batch::plan({11, 5, 13}, fixture.sources, fixture.layout,
                                  {120, 40, sizeof(batch::Plan), 22});
    const auto generous = owner_limits();
    auto state = std::make_shared<BuildState>();
    auto complete = owners::prepare_owner<OwnerRecord>(plan, fixture.sources, fixture.layout,
                                                      generous, OwnerBuilder{state}, true);
    const auto expected = complete.data->counts;
    auto prepare = [&](owners::Limits limits, std::shared_ptr<BuildState> trace) {
        return owners::prepare_owner<OwnerRecord>(plan, fixture.sources, fixture.layout,
                                                  limits, OwnerBuilder{std::move(trace)}, true);
    };
    auto exact = generous;
    exact.max_payload_bytes = expected.payload_capacity_bytes;
    exact.max_control_bytes = expected.control_bytes;
    exact.max_retained_bytes = expected.retained_bytes;
    exact.max_records = expected.records;
    require(prepare(exact, std::make_shared<BuildState>()).data->counts.retained_bytes == expected.retained_bytes,
            "exact aggregate owner budgets admitted");
    for (uint32_t failure = 0; failure < 6; ++failure) {
        auto limits = exact;
        if (failure == 0) --limits.max_payload_bytes;
        if (failure == 1) --limits.max_control_bytes;
        if (failure == 2) --limits.max_retained_bytes;
        if (failure == 3) --limits.max_records;
        if (failure == 4) limits.node_bytes = UINT64_MAX;
        if (failure == 5) limits.edge_bytes = UINT64_MAX;
        auto trace = std::make_shared<BuildState>();
        rejects([&] { prepare(limits, trace); }, "aggregate owner budget/overflow accepted");
        require(trace->roots == 0 && trace->leaves == 0 && trace->attaches == 0,
                "budget refusal occurs before any Builder allocation");
    }
    const auto no_identity = owners::prepare_owner<OwnerRecord>(plan, fixture.sources, fixture.layout,
        generous, OwnerBuilder{std::make_shared<BuildState>()}, false);
    require(no_identity.data->counts.records == 23 && no_identity.data->packed_bytes == 65 * 40,
            "dead identity has no leaf or payload charge");
    for (const auto& draw : no_identity.data->draws)
        require(draw.users.size() == 1 && draw.users.front() && !draw.identity && draw.instances, "optional identity omitted");

    const auto empty_users = batch::plan({UINT32_MAX, 1, 3}, {}, PackedLayout{}, {16, 16, sizeof(batch::Plan), 2});
    for (bool identity_live : {false, true}) {
        auto owned = owners::prepare_owner<OwnerRecord>(empty_users, {}, PackedLayout{}, generous,
            OwnerBuilder{std::make_shared<BuildState>()}, identity_live);
        require(owned.data->draws.size() == 2 && owned.data->packed_bytes == (identity_live ? 24u : 0u) &&
                owned.data->counts.records == (identity_live ? 3u : 1u), "optional user and identity leaves charged");
        for (const auto& draw : owned.data->draws)
            require(draw.users.empty() && bool(draw.identity) == identity_live, "identity-only or no-input draw ownership");
    }
    const auto huge = batch::plan({0, INT32_MAX, INT32_MAX}, {}, PackedLayout{}, {8, 8, sizeof(batch::Plan), UINT64_MAX});
    auto trace = std::make_shared<BuildState>();
    rejects([&] { owners::prepare_owner<OwnerRecord>(huge, {}, PackedLayout{}, generous, OwnerBuilder{trace}, true); },
            "huge implicit draw table admitted into bounded owner");
    require(trace->roots == 0, "huge table refused without enumerating or allocating leaves");
    const auto zero = batch::plan({0, 0, 1}, {}, PackedLayout{}, {});
    auto zero_state = std::make_shared<BuildState>();
    const auto zero_owner = owners::prepare_owner<OwnerRecord>(zero, fixture.sources, PackedLayout{}, {}, OwnerBuilder{zero_state}, true);
    require(!zero_owner.root && !zero_owner.data && !zero_state->roots, "zero owner has no allocation or source reads");
}

void owner_high_ids_and_key_widths() {
    for (uint32_t width : {1u, 2u, 4u}) {
        owners::PreparedOwner<OwnerRecord> owned;
        std::vector<uint8_t> expected;
        {
            const std::vector<uint32_t> ids = width == 1 ? std::vector<uint32_t>{255, 0, 255} :
                width == 2 ? std::vector<uint32_t>{65535, 0, 65535} :
                             std::vector<uint32_t>{UINT32_MAX, 0x80000001, UINT32_MAX};
            auto bytes = width == 1 ? index_bytes<uint8_t>(ids) :
                         width == 2 ? index_bytes<uint16_t>(ids) : index_bytes<uint32_t>(ids);
            const auto plan = batch::plan({0, 3, 3, bytes, width}, {}, PackedLayout{}, {16, 16, sizeof(batch::Plan), 5});
            owned = owners::prepare_owner<OwnerRecord>(plan, {}, PackedLayout{}, owner_limits(),
                OwnerBuilder{std::make_shared<BuildState>()}, true);
            for (uint32_t instance = 0; instance < 3; ++instance)
                for (auto vertex : ids) { append_word(expected, vertex); append_word(expected, instance); }
        }
        std::vector<uint8_t> actual;
        for (const auto& draw : owned.data->draws)
            actual.insert(actual.end(), draw.identity->bytes.begin(), draw.identity->bytes.end());
        require(actual == expected, "owning all-ones/high indexed identities survive producer release");
    }
    const auto plan = batch::plan({0, 10001, 1}, {}, PackedLayout{}, {8, 8, sizeof(batch::Plan), 10001});
    const owners::Limits limits{1024 * 1024, 16 * 1024 * 1024, 32 * 1024 * 1024, 20000, 32, 32};
    const auto measured = owners::measure_owner<OwnerRecord>(plan, limits, true);
    uint64_t actual_keys = 0;
    for (uint64_t number = 0; number < 10001; ++number) {
        const auto key = owners::edge_key(number, owners::LeafKind::Identity);
        require(key == "p:" + std::to_string(number) + ":identity", "decimal-width key contents");
        actual_keys += key.capacity() + 1;
    }
    require(measured.edge_key_bytes == actual_keys && measured.edges == 10001 && measured.records == 10002,
            "closed-form key preflight matches actual capacities across decimal and inline-buffer boundaries");
}

void owner_failure_keeps_cache_predecessor() {
    Fixture fixture(17, 13);
    const auto plan = batch::plan({11, 5, 13}, fixture.sources, fixture.layout,
                                  {120, 40, sizeof(batch::Plan), 22});
    const auto limits = owner_limits();
    auto before = owners::prepare_owner<OwnerRecord>(plan, fixture.sources, fixture.layout,
        limits, OwnerBuilder{std::make_shared<BuildState>()}, true);
    std::unordered_map<std::string, OwnerRecord> cache{{"current", before.root}};
    for (bool attach_failure : {false, true}) {
        auto state = std::make_shared<BuildState>();
        if (attach_failure) state->fail_attach = 7;
        else state->fail_leaf = 7;
        rejects([&] {
            auto next = owners::prepare_owner<OwnerRecord>(plan, fixture.sources, fixture.layout,
                                                           limits, OwnerBuilder{state}, true);
            cache.at("current") = std::move(next.root);
        }, "late Builder failure did not propagate");
        require(cache.size() == 1 && cache.at("current") == before.root &&
                before.root->children.size() == 44 && before.data->draws.size() == 22,
                "late private preparation failure preserves cache predecessor");
        require(state->leaves >= 7 && state->attaches >= 6, "failure occurs after several complete leaves");
        for (const auto& weak : state->nodes) require(weak.expired(), "failed private graph releases every node");
    }
    auto sources = fixture.sources;
    sources[2].bytes = sources[2].bytes.first(1);
    auto state = std::make_shared<BuildState>();
    rejects([&] { owners::prepare_owner<OwnerRecord>(plan, sources, fixture.layout,
                                                    limits, OwnerBuilder{state}, true); },
            "stale source admitted after borrowed plan preparation");
    require(!state->roots && !state->leaves && cache.at("current") == before.root,
            "all-source revalidation precedes Builder allocation and cache mutation");
}
}  // namespace

int main() {
    try {
        ordered_ranges_and_bits();
        identity_only_and_large_domains();
        sparse_constant_and_divisor_sources();
        admission_and_revalidation();
        owner_oracle_and_lifetime();
        owner_optional_leaves_and_budgets();
        owner_high_ids_and_key_widths();
        owner_failure_keeps_cache_predecessor();
        std::cout << "point_batch_contract: PASS (CPU owning preparation)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "point_batch_contract: " << error.what() << '\n';
        return 1;
    }
}
