#include "runtime_batch_owner.hpp"
#include <iostream>
#include <map>
#include <tuple>

namespace batch = vispy::inputs::batches;
namespace own = vispy::inputs::batches::owners;
using namespace vispy::inputs;

static uint64_t checks = 0;
static void check(bool value, const char* why) {
    ++checks;
    if (!value) throw std::runtime_error(why);
}
template<class Call> static void refuses(Call&& call, const char* why) {
    bool threw = false;
    try { call(); } catch (const std::exception&) { threw = true; }
    check(threw, why);
}
static uint32_t word(std::span<const uint8_t> bytes, uint64_t offset) {
    uint32_t value = 0;
    if (offset > bytes.size() || bytes.size() - static_cast<size_t>(offset) < 4)
        throw std::runtime_error("oracle read exceeds bytes");
    std::memcpy(&value, bytes.data() + offset, 4);
    return value;
}
static void put(std::vector<uint8_t>& bytes, size_t offset, uint32_t value) {
    std::memcpy(bytes.data() + offset, &value, 4);
}

struct Node;
using Record = std::shared_ptr<Node>;
struct Node {
    inline static uint64_t live = 0;
    std::vector<uint8_t> bytes;
    own::LeafKind kind{};
    std::map<std::string, Record> children;
    std::shared_ptr<const own::OwnerData<Record>> batch_data;
    Node() { ++live; }
    ~Node() { --live; }
};
struct Builder {
    uint64_t operations = 0, fail_at = 0, leaves = 0, roots = 0;
    std::weak_ptr<Node> last_root;
    void operation() {
        ++operations;
        if (operations == fail_at) throw std::runtime_error("injected unpublished graph failure");
    }
    Record make_root() {
        operation(); ++roots;
        auto result = std::make_shared<Node>(); last_root = result; return result;
    }
    Record make_leaf(std::vector<uint8_t>&& bytes, own::LeafKind kind) {
        operation(); ++leaves;
        auto result = std::make_shared<Node>(); result->bytes = std::move(bytes); result->kind = kind; return result;
    }
    void attach(Record& root, std::string key, const Record& child) {
        operation();
        if (!root->children.emplace(std::move(key), child).second)
            throw std::runtime_error("duplicate generated edge key");
    }
};
static own::Limits generous() {
    return {1ULL << 32, 1ULL << 32, 1ULL << 33, 1ULL << 24, 1ULL << 25, 96, 80};
}

struct Fixture {
    std::vector<std::vector<uint8_t>> storage;
    std::vector<Source> sources;
    std::vector<uint8_t> indices;
    Selection selection;
    Layout layout;
};
static Fixture fixture(bool indexed, uint64_t count = 10, uint64_t instances = 7) {
    Fixture f;
    f.storage.resize(4);
    const std::array<uint64_t, 4> widths{16, 12, 16, 8};
    const std::array<uint64_t, 4> strides{24, 20, 24, 16};
    const std::array<uint64_t, 4> offsets{8, 4, 8, 4};
    for (size_t field = 0; field < 4; ++field) {
        f.storage[field].resize(static_cast<size_t>(offsets[field] + strides[field] * 20), 0xab);
        for (size_t row = 0; row < 20; ++row)
            for (size_t w = 0; w < widths[field] / 4; ++w) {
                const uint32_t bits = row == 1 && w == 0 ? 0x80000000u :
                    row == 2 && w == 0 ? 0x7fc01234u :
                    0x01000001u + static_cast<uint32_t>(field * 10000 + row * 100 + w);
                put(f.storage[field], static_cast<size_t>(offsets[field] + row * strides[field] + w * 4), bits);
            }
        f.sources.push_back({f.storage[field], 100 + field, 7, offsets[field], strides[field], widths[field],
            field == 2 ? 2ull : field == 3 ? 3ull : 0ull, "field" + std::to_string(field)});
    }
    f.selection = {1, count, instances};
    if (indexed) {
        const uint32_t values[]{5, 1, 5, 2, 8, 2, 7, 4, 9, 3};
        check(count <= 10, "fixture count");
        f.indices.resize(static_cast<size_t>(count * 4));
        std::memcpy(f.indices.data(), values, f.indices.size());
        f.selection.first = 0;
        f.selection.index_bytes = 4;
        f.selection.indices = f.indices;
    }
    f.layout = compact_layout(f.sources, 30, 8, 16);
    check(f.layout.streams.size() == 4, "four physical streams");
    return f;
}
static batch::Plan make_plan(const Fixture& f, uint64_t buffer = 48, uint64_t storage = 24) {
    return batch::plan_triangle_list(f.selection, f.sources, f.layout, {buffer, storage, 1ULL << 28, 1ULL << 25});
}
static own::PreparedOwner<Record> prepare(batch::Plan plan, const Fixture& f, Builder& builder,
                                           own::Limits limits = generous(), uint64_t uniform = 16) {
    auto owner = own::prepare_owner<Record>(std::move(plan), f.sources, limits, uniform, builder);
    if (owner.root) owner.root->batch_data = owner.data; // Runtime's root-only metadata hook.
    return owner;
}

using Invocation = std::pair<uint32_t, uint32_t>;
using Primitive = std::tuple<uint32_t, uint32_t, uint32_t, uint32_t>;
static void verify_graph(const Fixture& f, const own::PreparedOwner<Record>& owner) {
    const auto& data = *owner.data;
    const auto& plan = data.plan;
    check(data.geometry.size() == plan.geometry.size(), "one geometry view per chunk");
    check(data.blocks.size() == plan.instance_block_count, "one block view per block");
    check(owner.root->children.size() == data.counts.edges, "exact graph edge count");
    uint64_t bytes = 0, allocated = 0, key_bytes = 0, identities = 0, origins = 0;
    for (const auto& [key, node] : owner.root->children) {
        bytes += node->bytes.size(); allocated += std::max(size_t(4), (node->bytes.size() + 3) / 4 * 4);
        key_bytes += key.size() + 1;
        identities += node->kind == own::LeafKind::GeometryIdentity;
        origins += node->kind == own::LeafKind::InstanceOrigin;
        check(!node->batch_data && node->children.empty(), "leaf owns no aggregate/root metadata");
    }
    check(bytes == data.counts.packed_bytes, "exact leaf payload accounting");
    check(allocated == data.counts.buffer_allocation_bytes, "exact rounded buffer accounting");
    check(key_bytes == data.counts.edge_key_bytes, "exact deterministic key charge");
    check(identities == plan.geometry.size(), "ID table retained once per geometry, never geometry x blocks");
    check(origins == plan.instance_block_count, "origin retained once per block");
    check(data.counts.records == data.counts.edges + 1, "one nonpayload root");
    check(data.metadata_storage_bytes() == data.counts.metadata_bytes, "retained metadata capacity accounting");
    for (size_t g = 0; g < data.geometry.size(); ++g) {
        const auto& records = data.geometry[g];
        const auto& geometry = plan.geometry[g];
        check(records.vertices.size() == plan.layout.streams.size(), "geometry physical-slot vector");
        check(records.identity->bytes.size() == (plan.indexed ? geometry.original_vertices.size() * 4 : 4), "geometry identity has no block header");
        check(bool(records.index) == plan.indexed, "index owner shape");
        for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot) {
            const auto& stream = plan.layout.streams[slot];
            check(bool(records.vertices[slot]) == !stream.instance, "empty other-step geometry slots");
            if (stream.instance) continue;
            for (uint64_t row = 0; row < batch::vertex_rows(plan, geometry); ++row) {
                const uint64_t original = plan.indexed ? geometry.original_vertices[static_cast<size_t>(row)] : geometry.vertex_base + row;
                for (size_t field : stream.fields)
                    for (uint64_t w = 0; w < f.sources[field].element_bytes; w += 4)
                        check(word(records.vertices[slot]->bytes, row * stream.stride + plan.layout.offsets[field] + w) ==
                            word(f.sources[field].bytes, f.sources[field].offset + original * f.sources[field].stride + w),
                            "every vertex stream raw word/source offset+stride");
            }
        }
    }
    for (size_t b = 0; b < data.blocks.size(); ++b) {
        const auto block = plan.instance_block(b);
        const auto& records = data.blocks[b];
        check(records.instances.size() == plan.layout.streams.size(), "block physical-slot vector");
        check(records.origin->bytes.size() == 16, "std140 origin is exactly16 bytes");
        check(word(records.origin->bytes, 0) == block.first, "block origin exact uint32");
        for (uint64_t w = 4; w < 16; w += 4) check(word(records.origin->bytes, w) == 0, "reserved origin words zero");
        for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot) {
            const auto& stream = plan.layout.streams[slot];
            check(bool(records.instances[slot]) == stream.instance, "empty other-step block slots");
            if (!stream.instance) continue;
            for (uint64_t row = 0; row < block.count; ++row)
                for (size_t field : stream.fields)
                    for (uint64_t w = 0; w < f.sources[field].element_bytes; w += 4) {
                        const auto original = (block.first + row) / f.sources[field].divisor;
                        check(word(records.instances[slot]->bytes, row * stream.stride + plan.layout.offsets[field] + w) ==
                            word(f.sources[field].bytes, f.sources[field].offset + original * f.sources[field].stride + w),
                            "instance raw words use original divisor domain");
                    }
        }
    }
    std::vector<Invocation> expected, actual;
    std::vector<Primitive> expected_primitives, actual_primitives;
    auto original_vertex = [&](uint64_t element) {
        return f.selection.index_bytes ? word(f.selection.indices, element * 4) : static_cast<uint32_t>(f.selection.first + element);
    };
    for (uint64_t i = 0; i < f.selection.instances; ++i) {
        for (uint64_t e = 0; e < f.selection.count; ++e) expected.emplace_back(original_vertex(e), static_cast<uint32_t>(i));
        for (uint64_t e = 0; e + 2 < f.selection.count; e += 3)
            expected_primitives.emplace_back(original_vertex(e), original_vertex(e + 1), original_vertex(e + 2), static_cast<uint32_t>(i));
    }
    uint64_t calls = 0;
    plan.for_each_draw([&](const batch::DrawRef& draw) {
        ++calls;
        const auto& geometry = data.geometry[draw.geometry];
        const auto& block = data.blocks[static_cast<size_t>(draw.instance_block)];
        const auto& shape = plan.geometry[draw.geometry];
        for (uint64_t native_local = 0; native_local < draw.instance_count; ++native_local) {
            const auto native_instance_index = draw.row_offset + native_local;
            const auto restored_instance = word(block.origin->bytes, 0) + static_cast<uint32_t>(native_instance_index);
            check(restored_instance == draw.instance_base + native_local, "firstInstance row_offset + blockbase exactly once");
            std::vector<uint32_t> vertices;
            for (uint64_t e = 0; e < shape.element_count; ++e) {
                const auto local_vertex = plan.indexed ? word(geometry.index->bytes, e * 4) : static_cast<uint32_t>(e);
                const auto restored_vertex = plan.indexed ? word(geometry.identity->bytes, uint64_t(local_vertex) * 4) :
                    word(geometry.identity->bytes, 0) + local_vertex;
                vertices.push_back(restored_vertex);
                actual.emplace_back(restored_vertex, restored_instance);
                for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot) {
                    const auto& stream = plan.layout.streams[slot];
                    for (size_t field : stream.fields) {
                        const auto row = stream.instance ? native_instance_index : local_vertex;
                        const auto source_row = stream.instance ? restored_instance / f.sources[field].divisor : restored_vertex;
                        const auto& leaf = stream.instance ? block.instances[slot] : geometry.vertices[slot];
                        check(word(leaf->bytes, row * stream.stride + plan.layout.offsets[field]) ==
                            word(f.sources[field].bytes, f.sources[field].offset + uint64_t(source_row) * f.sources[field].stride),
                            "native firstInstance fetch and restored IDs use same original row");
                    }
                }
            }
            for (size_t e = 0; e + 2 < vertices.size(); e += 3)
                actual_primitives.emplace_back(vertices[e], vertices[e + 1], vertices[e + 2], restored_instance);
        }
    });
    check(calls == plan.encoded_draws, "physical call count");
    check(expected == actual, "exact original selected invocation order including terminal tails");
    check(expected_primitives == actual_primitives, "exact triangles and LAST-provoking element without tail crossjoin");
    auto order_model = [](const std::vector<Primitive>& primitives) {
        uint64_t state = 0x91827364;
        for (const auto& [a, b, c, i] : primitives) state = (state * 1664525 + c * 101 + a * 7 + b * 3 + i) ^ (state >> 7);
        return state;
    };
    check(order_model(expected_primitives) == order_model(actual_primitives), "order-sensitive overlap/state model");
}

static void boundary_and_transaction() {
    const auto f = fixture(true);
    const auto plan = make_plan(f);
    Builder baseline_builder;
    const auto baseline = prepare(plan, f, baseline_builder);
    verify_graph(f, baseline);
    const auto& counts = baseline.data->counts;
    auto exact = generous();
    exact.max_packed_bytes = counts.packed_bytes;
    exact.max_control_bytes = counts.charged_control_bytes;
    exact.max_retained_bytes = counts.retained_bytes;
    exact.max_records = counts.records;
    exact.max_encoded_draws = counts.encoded_draws;
    Builder exact_builder;
    const auto exact_owner = prepare(plan, f, exact_builder, exact);
    check(exact_owner.root != nullptr, "all exact joint budgets accepted");
    for (int budget = 0; budget < 5; ++budget) {
        auto limited = exact;
        if (budget == 0) --limited.max_packed_bytes;
        if (budget == 1) --limited.max_control_bytes;
        if (budget == 2) --limited.max_retained_bytes;
        if (budget == 3) --limited.max_records;
        if (budget == 4) --limited.max_encoded_draws;
        Builder builder;
        refuses([&] { prepare(plan, f, builder, limited); }, "one below joint budget refuses");
        check(builder.operations == 0, "all budget refusals precede payload packing/record construction");
    }
    Builder uniform_builder;
    refuses([&] { prepare(plan, f, uniform_builder, generous(), 15); }, "uniform16 exact versus15 refusal");
    check(uniform_builder.operations == 0, "uniform refusal before graph build");

    using Entry = own::CacheEntry<Record>;
    std::shared_ptr<const Entry> current;
    own::prepare_and_publish_current(current, "old:ABI2", [&] { return baseline; });
    const auto old = current;
    const auto live_before = Node::live;
    for (uint64_t fail = 1; fail <= baseline_builder.operations; ++fail) {
        Builder builder; builder.fail_at = fail;
        refuses([&] {
            own::prepare_and_publish_current(current, "new:ABI2", [&] { return prepare(plan, f, builder); });
        }, "every root/leaf/attach failure throws");
        check(current == old && current->key == "old:ABI2" && current->prepared.root == baseline.root,
            "key plus complete current owner unchanged on staged graph failure");
        check(builder.last_root.expired(), "partial local root released after failure");
        check(Node::live == live_before, "no partial graph or ownership cycle leaked");
    }
    Builder successful;
    own::prepare_and_publish_current(current, "new:ABI2", [&] { return prepare(plan, f, successful); });
    check(current != old && current->key == "new:ABI2" && current->prepared.root != baseline.root,
        "single current publication replaces key and complete graph together");
    check(old->prepared.root == baseline.root, "older queued/current snapshots keep their graph");
}

static void lifecycle() {
    const auto f = fixture(false);
    std::weak_ptr<Node> weak;
    std::vector<Record> queued, ticket;
    {
        Builder builder;
        auto owner = prepare(make_plan(f), f, builder);
        weak = owner.root;
        queued.push_back(owner.root);
    }
    check(!weak.expired(), "queued owner outlives current temporary");
    ticket.push_back(queued.front()); queued.clear();
    check(!weak.expired(), "ticket owner survives queue removal");
    ticket.clear();
    check(weak.expired(), "root->metadata->leaf graph has no selfcycle and retires");
}

static void zero_huge_and_small_grants() {
    auto f = fixture(false, 0, 7);
    Builder zero;
    const auto empty = prepare(make_plan(f), f, zero, {} , 0);
    check(!empty.root && !empty.data && zero.operations == 0, "zero draw creates no graph/admission");
    f = fixture(false, 3, 0);
    Builder zero_instances;
    check(!prepare(make_plan(f), f, zero_instances, {}, 0).root && zero_instances.operations == 0,
        "zero instances create no owner");

    std::vector<uint8_t> constant(4, 0);
    std::vector<Source> sources{{constant, 1, 1, 0, 0, 4, 0, "constant"}};
    auto layout = compact_layout(sources, 30, 8, 16);
    Selection one{0, 1, 1};
    auto tiny = batch::plan_triangle_list(one, sources, layout, {12, 8, 1ULL << 20, 100});
    Builder tiny_builder;
    refuses([&] { own::prepare_owner<Record>(tiny, sources, generous(), 16, tiny_builder); },
        "planner ABI1 legal but splitABI2 origin cannot fit12-byte buffer");
    check(tiny_builder.operations == 0, "split ABI2 actual16-byte capacity admitted before packing");
    auto exact = batch::plan_triangle_list(one, sources, layout, {16, 8, 1ULL << 20, 100});
    Builder small_builder;
    check(own::prepare_owner<Record>(exact, sources, generous(), 16, small_builder).root != nullptr,
        "actual16-byte uniform/buffer boundary accepted");

    sources.push_back({constant, 2, 1, 0, 0, 4, 1, "constant_instance"});
    layout = compact_layout(sources, 30, 8, 16);
    Selection huge{0, 3, INT32_MAX};
    auto plan = batch::plan_triangle_list(huge, sources, layout, {16, 8, 1ULL << 20, uint64_t(INT32_MAX)});
    check(plan.geometry.size() == 1 && plan.instance_block_count > 500000000, "huge schedule stays implicit");
    auto limited = generous(); limited.max_control_bytes = 1ULL << 20;
    Builder huge_builder;
    refuses([&] { own::prepare_owner<Record>(plan, sources, limited, 16, huge_builder); }, "huge block-view ownership refused before growth");
    check(huge_builder.operations == 0, "huge admission does not build/pack any leaf");
    auto overflow = generous(); overflow.record_control_bytes = UINT64_MAX;
    refuses([&] { own::measure_owner<Record>(exact, overflow, 16); }, "joint control arithmetic checked");
}

static void high_ids_and_key_digits() {
    std::vector<uint8_t> constant(8); put(constant, 4, 0x80000000u);
    std::vector<uint8_t> indices(12);
    put(indices, 0, UINT32_MAX); put(indices, 4, 16777217u); put(indices, 8, UINT32_MAX);
    std::vector<Source> sources{{constant, 1, 1, 4, 0, 4, 0, "constant"}};
    auto layout = compact_layout(sources, 30, 8, 16);
    Selection selection{0, 3, 120, indices, 4};
    auto plan = batch::plan_triangle_list(selection, sources, layout, {16, 16, 1ULL << 20, 1000});
    Builder builder;
    auto owner = own::prepare_owner<Record>(plan, sources, generous(), 16, builder);
    check(word(owner.data->geometry[0].identity->bytes, 0) == UINT32_MAX &&
          word(owner.data->geometry[0].identity->bytes, 4) == 16777217u, "full32-bit IDs never float encoded");
    for (uint64_t n : {0ull, 9ull, 10ull, 99ull, 100ull, 1000ull})
        for (auto kind : {own::LeafKind::GeometryIdentity, own::LeafKind::Indices, own::LeafKind::VertexStream,
                          own::LeafKind::InstanceOrigin, own::LeafKind::InstanceStream})
            check(own::key_bytes('g', n, kind, 31) == own::edge_key('g', n, kind, 31).size() + 1, "key character charge across decimal boundaries");
    // Force more than 100 blocks without huge metadata; this validates the
    // closed-form decimal-key summation against actual graph keys.
    sources.push_back({constant, 2, 1, 4, 0, 4, 1, "constant_instance"});
    layout = compact_layout(sources, 30, 8, 16);
    selection.instances = 401;
    plan = batch::plan_triangle_list(selection, sources, layout, {16, 16, 1ULL << 20, 1000});
    Builder many_builder;
    owner = own::prepare_owner<Record>(plan, sources, generous(), 16, many_builder);
    uint64_t keys = 0;
    for (const auto& [key, node] : owner.root->children) { (void)node; keys += key.size() + 1; }
    check(owner.data->blocks.size() == 101 && keys == owner.data->counts.edge_key_bytes, "blockkey sum exact through100");
}

int main() {
    try {
        for (bool indexed : {false, true})
            for (uint64_t count = 1; count <= 10; ++count)
                for (uint64_t instances : {1ull, 2ull, 3ull, 4ull, 7ull}) {
                    const auto f = fixture(indexed, count, instances);
                    Builder builder;
                    const auto owner = prepare(make_plan(f), f, builder);
                    verify_graph(f, owner);
                }
        boundary_and_transaction();
        lifecycle();
        zero_huge_and_small_grants();
        high_ids_and_key_digits();
        check(Node::live == 0, "all portable records retired");
        std::cout << checks << " batch-owner CPU checks passed\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAILED after " << checks << " checks: " << e.what() << '\n';
        return 1;
    }
}
