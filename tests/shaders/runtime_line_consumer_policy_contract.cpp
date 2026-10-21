#include "runtime_line_consumer.hpp"
#include "shader/artifact.hpp"

#include <iostream>
#include <array>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <vector>

using namespace vispy::lines;
using namespace vispy::shader;

namespace {
size_t checks = 0;
void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
// Ownership cases use synthetic CPU graphs/handles. The route cases also
// compile two portable CPU artifacts; no Dawn, submission, callback, hardware
// allocation or device-loss event occurs in this contract.
struct Evaluator {
    std::shared_ptr<const PortableShaderArtifact> original;
    bool ok = true;
    size_t storage_bytes() const { return 512; }
};
struct Consumer {
    std::shared_ptr<const PortableShaderArtifact> original;
    std::shared_ptr<const Evaluator> evaluator;
    std::string policy_identity;
    bool ok = true;
    size_t storage_bytes() const { return sizeof(*this) + policy_identity.capacity() + 1; }
};
using Portable = std::shared_ptr<const PortableShaderArtifact>;
using Eval = std::shared_ptr<const Evaluator>;
using Cons = std::shared_ptr<const Consumer>;
struct Handle { int token; };
using Native = std::shared_ptr<Handle>;
using Record = LineConsumerDeviceRecord<Consumer, Native, Native, Native>;
using RecordPtr = std::shared_ptr<Record>;
using Set = LineConsumerDeviceSet<Record>;

struct Device {
    Portable portable;
    Eval evaluator;
    Cons consumer;  // Legacy selected consumer must not hide other subrecords.
    Set policies;
    bool corrupt_view_key = false;
    size_t storage_bytes() const {
        // sizeof(Device) already owns the inline Set bookkeeping.
        return sizeof(*this) + policies.storage_bytes() - sizeof(Set);
    }
    template <class Visitor>
    void for_each_consumer(Visitor&& visitor) const {
        policies.for_each_consumer([&](std::string_view key, const Cons& value) {
            visitor(corrupt_view_key ? std::string_view("foreign full policy key") : key, value);
        });
    }
};
using Cache = ShaderArtifactCache<Device, Evaluator, Consumer>;

std::shared_ptr<PortableShaderArtifact> portable(std::string key) {
    auto value = std::make_shared<PortableShaderArtifact>();
    value->identity = std::move(key);
    value->ok = true;
    return value;
}
std::shared_ptr<Evaluator> evaluator(Portable value) {
    auto result = std::make_shared<Evaluator>();
    result->original = std::move(value);
    return result;
}
std::shared_ptr<Consumer> consumer(Portable original, Eval eval, std::string key) {
    auto result = std::make_shared<Consumer>();
    result->original = std::move(original);
    result->evaluator = std::move(eval);
    result->policy_identity = std::move(key);
    return result;
}
RecordPtr record(Cons value, uint64_t generation, int token = 1) {
    auto result = std::make_shared<Record>(std::move(value), generation);
    result->vert_module = std::make_shared<Handle>(Handle{token});
    result->frag_module = std::make_shared<Handle>(Handle{token + 1});
    result->bind_layout = std::make_shared<Handle>(Handle{token + 2});
    return result;
}
std::shared_ptr<Device> device(Portable p, Eval e) {
    auto value = std::make_shared<Device>();
    value->portable = std::move(p); value->evaluator = std::move(e);
    return value;
}
void immutable_joined_records() {
    static_assert(!std::is_assignable_v<decltype(Record::consumer)&, Cons>);
    static_assert(!std::is_assignable_v<decltype(Record::device_generation)&, uint64_t>);
    auto p = portable("fixed original"); auto e = evaluator(p);
    auto c = consumer(p, e, "full policy A");
    auto r = std::make_shared<Record>(c, 7);
    Set set;
    require(!r->ready_for(7, p, e) && !set.publish(r), "unready handles cannot publish");
    r->vert_module = std::make_shared<Handle>(Handle{1});
    r->frag_module = std::make_shared<Handle>(Handle{2});
    r->bind_layout = std::make_shared<Handle>(Handle{3});
    require(r->ready_for(7, p, e) && set.publish(r), "actual joined ready record publishes");
    require(!r->ready_for(0, p, e) && !r->ready_for(8, p, e), "zero/foreign generation refuses");
    require(!r->ready_for(7, portable("fixed original"), e), "equal source different original allocation refuses");
    require(!r->ready_for(7, p, evaluator(p)), "equal graph different evaluator allocation refuses");
    require(set.find(c->policy_identity, 7) == r && !set.find(c->policy_identity, 8), "full key and generation lookup");
    require(!set.find("different key", 7), "key mismatch never selects an arbitrary record");
    require(set.publish(r) && !set.publish(record(c, 7)), "same key canonical allocation preserved");
    auto wrong_e = evaluator(portable("foreign"));
    require(!set.publish(record(consumer(p, wrong_e, "bad graph"), 7)), "evaluator/original mismatch refuses");
    require(!set.publish(record(consumer(p, e, ""), 7)), "empty full policy refuses");
    require(!set.publish(record(c, 0)), "zero record generation refuses");
    auto failed = consumer(p, e, "failed consumer"); failed->ok = false;
    require(!set.publish(record(failed, 7)), "failed generated artifact never publishes");
    r->error = "real retained module error";
    require(!set.find(c->policy_identity, 7), "failed native metadata does not become ready");
    r->error.clear();
    require(set.find(c->policy_identity, 7) == r, "clearing diagnostic error retains fixed identity");
    auto foreign = portable("foreign original");
    require(!set.publish(record(consumer(foreign, evaluator(foreign), "other graph"), 7)),
            "one device set cannot silently mix original/evaluator allocations");
}
void policy_fifo_snapshot_lifetimes() {
    auto p = portable("original"); auto e = evaluator(p);
    auto a = consumer(p, e, "full A"); auto b = consumer(p, e, "full B"); auto c = consumer(p, e, "full C");
    auto ra = record(a, 9, 11), rb = record(b, 9, 21), rc = record(c, 9, 31);
    Set set(2);
    require(set.publish(ra) && set.publish(rb), "simultaneous A/B resident");
    std::vector<RecordPtr> queued{set.find(a->policy_identity, 9), set.find(b->policy_identity, 9),
                                 set.find(a->policy_identity, 9)};
    std::vector<RecordPtr> submitted = queued;
    queued.clear();
    require(submitted[0] == ra && submitted[1] == rb && submitted[2] == ra,
            "queued-to-submitted A/B/A snapshot references preserve selection");
    require(set.publish(ra) && set.publish(rc), "warm A does not reorder admission FIFO");
    require(!set.find(a->policy_identity, 9) && set.find(b->policy_identity, 9) == rb &&
            set.find(c->policy_identity, 9) == rc, "bounded FIFO evicts only oldest set owner");
    require(submitted[0]->consumer == a && submitted[0]->ready_for(9, p, e),
            "evicted synthetic submitted owner remains exact and ready");
    auto replacement = record(a, 9, 41);
    require(set.publish(replacement) && submitted[0] != set.find(a->policy_identity, 9),
            "new native allocation after eviction does not overwrite old snapshot");
    require(submitted[1]->consumer == b && submitted[1]->vert_module->token == 21,
            "second external owner unaffected by later policies");
    size_t consumers = 0, records = 0;
    set.for_each_consumer([&](std::string_view key, const Cons& owner) {
        ++consumers; require(key == owner->policy_identity, "traversal key owns its exact full identity");
    });
    set.for_each_record([&](const RecordPtr& owner) { ++records; require(bool(owner), "record traversal retains owner"); });
    require(consumers == 2 && records == 2 && set.size() == 2, "complete bounded traversal");
    auto captured = submitted[0];
    std::weak_ptr<Record> old = captured;
    ra.reset(); submitted.clear(); set.clear();
    require(!old.expired() && captured->consumer == a && set.size() == 0,
            "clearing cache collection does not release captured owner");
    captured.reset();
    require(old.expired(), "record destruction follows actual last external CPU owner");
}
void generation_loss_and_recovery() {
    auto p = portable("same retained original"); auto e = evaluator(p);
    auto a = consumer(p, e, "A"), b = consumer(p, e, "B");
    auto old_a = record(a, 3), old_b = record(b, 3);
    old_a->variants.emplace("retained exact render variant", std::make_shared<Handle>(Handle{81}));
    Set set;
    require(set.publish(old_a) && set.publish(old_b), "old generation pair publishes");
    require(!set.publish(record(consumer(p, e, "C"), 4)), "mixed generations refuse until detach");
    require(!set.detach(a->policy_identity, 4) && set.detach(a->policy_identity, 3), "detach needs exact generation");
    require(!set.find(a->policy_identity, 3) && old_a->consumer == a, "detached owner survives outside set");
    set.clear();
    auto new_a = record(a, 4, 51), new_b = record(b, 4, 61);
    require(set.publish(new_a) && set.publish(new_b), "recovery publishes fresh records on exact retained CPU graph");
    require(!set.find(a->policy_identity, 3) && set.find(a->policy_identity, 4) == new_a,
            "lookup never retags a prior generation");
    require(old_a->device_generation == 3 && !old_a->ready_for(4, p, e) &&
            old_b->device_generation == 3 && new_b->consumer == old_b->consumer &&
            old_a->vert_module->token == 1 && old_a->variants.at("retained exact render variant")->token == 81,
            "old records retain identity while recovery preserves exact CPU consumers");
    Set disabled(0);
    require(!disabled.publish(new_a) && disabled.size() == 0, "zero capacity has no fallback collection");
    Set one(1);
    require(one.publish(new_a) && one.publish(new_b) && !one.find(a->policy_identity, 4), "one slot has exact FIFO bound");
    Set defaults;
    RecordPtr captured;
    for (size_t i = 0; i < 129; ++i) {
        auto entry = record(consumer(p, e, "full default policy " + std::to_string(i)), 4);
        if (i == 0) captured = entry;
        require(defaults.publish(entry), "default collection accepts a joined policy within its bounded FIFO");
    }
    require(defaults.size() == 128 && !defaults.find("full default policy 0", 4) &&
            defaults.find("full default policy 128", 4) && captured->ready_for(4, p, e),
            "default 128 capacity evicts first set owner while external owner survives");
}
void complete_cache_consistency_guard() {
    auto p = portable("cache original"); auto e = evaluator(p);
    auto a = consumer(p, e, "A"), b = consumer(p, e, "B");
    Cache cache;
    require(cache.store_auxiliary(p, e) && cache.store_consumer(p, a) && cache.store_consumer(p, b),
            "canonical CPU graph admits both variants");
    auto good = device(p, e);
    require(good->policies.publish(record(a, 5)) && good->policies.publish(record(b, 5)), "real set has two ready records");
    require(cache.store_device(p, {5, true}, good, good->storage_bytes()),
            "complete multi-policy device graph admitted");
    auto clone_b = consumer(p, e, "B");
    auto wrong = device(p, e); wrong->consumer = a;
    require(wrong->policies.publish(record(a, 5)) && wrong->policies.publish(record(clone_b, 5)),
            "independent same-key clone is ready in isolated set");
    require(!cache.store_device(p, {5, false}, wrong, wrong->storage_bytes()),
            "valid selected singleton cannot hide unadmitted second policy allocation");
    wrong->consumer.reset();
    require(!cache.store_device(p, {5, false}, wrong, sizeof(Device)),
            "missing singleton must not bypass all-consumer consistency");
    good->corrupt_view_key = true;
    require(!cache.refresh_device(p->identity, {5, true}, sizeof(Device)) && !cache.find_portable(p->identity),
            "mutable wrong policy view evicts whole cache entry");
    good->corrupt_view_key = false;
    require(good->policies.find(a->policy_identity, 5)->consumer == a,
            "cache eviction preserves external native-record CPU owners");
    Cache refreshed;
    require(refreshed.store_auxiliary(p, e) && refreshed.store_consumer(p, a) && refreshed.store_consumer(p, b) &&
            refreshed.store_device(p, {5, true}, good, good->storage_bytes()),
            "canonical graph can be re-admitted after eviction");
    refreshed.clear_devices();
    require(refreshed.find_consumer(p->identity, "A") == a && refreshed.find_consumer(p->identity, "B") == b &&
            !refreshed.find_device(p->identity, {5, true}), "clear_devices retains both CPU policies");
}
void owned_storage_accounting_and_variants() {
    auto p = portable("original"); auto e = evaluator(p);
    auto a = consumer(p, e, std::string(4096, 'A')), b = consumer(p, e, "B");
    auto ra = record(a, 1), rb = record(b, 1);
    const size_t before = ra->storage_bytes();
    ra->error.reserve(2048);
    ra->variants.emplace(std::string(4096, 'v'), std::make_shared<Handle>(Handle{99}));
    require(ra->storage_bytes() >= before + 2048 + 4096, "owned error and full variant keys are charged");
    Set set;
    const size_t empty = set.storage_bytes();
    require(set.publish(ra), "capacity growth without an error value remains ready");
    const size_t one = set.storage_bytes();
    require(one >= empty + ra->storage_bytes(), "map/node/record bookkeeping joins one device charge");
    require(set.publish(rb) && set.storage_bytes() >= one + rb->storage_bytes(), "second record contributes storage");
    require(set.find(std::string(4096, 'A'), 1) == ra, "large borrowed full policy key retains owner lifetime");
    const size_t key_charge = a->storage_bytes();
    require(key_charge >= sizeof(Consumer) + 4097, "full policy allocation is charged by CPU consumer owner");
    auto captured = ra;
    require(set.detach(a->policy_identity, 1) && set.storage_bytes() < one + rb->storage_bytes(),
            "detached external records leave resident charge");
    require(captured->storage_bytes() > before && captured->variants.size() == 1,
            "external observer can separately deduplicate detached record storage");
    Set moved = std::move(set);
    require(set.size() == 0 && moved.size() == 1 && moved.find("B", 1) == rb, "moving collection preserves borrowed-key owners");
    Set assigned;
    assigned = std::move(moved);
    require(moved.size() == 0 && assigned.find("B", 1) == rb, "move assignment preserves graph and FIFO");
    require(detail::consumer_device_add_bytes(SIZE_MAX, 1) == SIZE_MAX &&
            detail::consumer_device_mul_bytes(SIZE_MAX, 2) == SIZE_MAX,
            "checked bookkeeping overflow refuses a finite footprint");
    Cache bounded(1, 32 * 1024);
    require(bounded.store_auxiliary(p, e) && bounded.store_consumer(p, a) && bounded.store_consumer(p, b),
            "bounded cache canonically owns exact original/evaluator/both consumers");
    auto outside = device(p, e);
    require(outside->policies.publish(ra) && outside->policies.publish(rb), "external policy pair remains joined");
    require(!bounded.store_device(p, {1, true}, outside, SIZE_MAX), "overflow cannot admit an uncharged native record");
    require(!bounded.store_device(p, {1, true}, outside, 32 * 1024),
            "finite device footprint exceeding joint CPU-plus-device budget refuses");
    require(outside->policies.find(a->policy_identity, 1) == ra && captured == ra,
            "budget refusal does not invalidate external selection");
}

void ordinary_line_route_admission() {
    struct Case {
        State raster;
        OrdinaryLineInterfaceUsage usage;
        uint32_t grant;
        LineRenderRoute expected;
    };
    const std::array<Case, 14> cases{{
        {state(1, false), {30, 30, 0}, 30, LineRenderRoute::Native},
        {state(1, false), {31, 30, 0}, 30, LineRenderRoute::Generated},
        {state(1, false), {30, 31, 0}, 30, LineRenderRoute::Generated},
        {state(3, false), {30, 30, 0}, 30, LineRenderRoute::Generated},
        {state(1, true), {30, 30, 0}, 30, LineRenderRoute::Generated},
        {state(3, true), {30, 30, 0}, 30, LineRenderRoute::Generated},
        {state(1, false), {30, 29, 1}, 30, LineRenderRoute::Native},
        {state(1, false), {30, 30, 1}, 30, LineRenderRoute::Generated},
        {state(1, false), {30, 24, 6}, 30, LineRenderRoute::Native},
        {state(1, false), {30, 25, 6}, 30, LineRenderRoute::Generated},
        {state(1, false), {0, 0, 0}, 0, LineRenderRoute::Generated},
        {state(1, false), {0, 0, 0}, 30, LineRenderRoute::Native},
        {state(1, false), {UINT64_MAX, 0, 0}, UINT32_MAX, LineRenderRoute::Generated},
        {state(1, false), {0, UINT64_MAX, UINT32_MAX}, UINT32_MAX, LineRenderRoute::Generated},
    }};
    for (const auto& row : cases)
        require(select_line_render_route(row.raster, row.usage, row.grant) == row.expected,
                "actual shared route preserves thin admission, both stage grants and overflow-safe builtin charge");
    for (double width : {0., -1., std::numeric_limits<double>::infinity(),
                         std::numeric_limits<double>::quiet_NaN()}) {
        bool rejected = false;
        try { (void)select_line_render_route({width, false}, {0, 0, 0}, 30); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "actual shared route refuses invalid line state before selecting a renderer");
    }
    // This helper has no selection or allocation arguments. Actual empty DRAW,
    // preconversion endpoint capture, u8/loop conversion and Vulkan Bresenham
    // admission remain renderer/GPU regressions, not claims of this CPU table.
}

void retained_fragment_builtin_admission() {
    const std::string vertex = "void main(){gl_Position=vec4(0.,0.,0.,1.);}";
    auto coordinate = build_portable_shader(vertex,
        "void main(){gl_FragColor=vec4(gl_FragCoord.x);}", NormalizeOptions{}, "route-contract-compiler-pins");
    auto facing = build_portable_shader(vertex,
        "void main(){gl_FragColor=gl_FrontFacing?vec4(1.):vec4(0.);}", NormalizeOptions{}, "route-contract-compiler-pins");
    require(coordinate->ok && facing->ok, "actual ordinary portable fragments compile for builtin admission");
    const auto original_coordinate = coordinate->spv_frag;
    const auto original_facing = facing->spv_frag;
    require(fragment_inter_stage_builtin_variables(coordinate->spv_frag) == 0,
            "actual compiled FragCoord input does not consume a Dawn inter-stage variable");
    require(fragment_inter_stage_builtin_variables(facing->spv_frag) == 1,
            "actual compiled FrontFacing input consumes one Dawn inter-stage variable");
    require(select_line_render_route(state(1, false), {30, 30,
                fragment_inter_stage_builtin_variables(coordinate->spv_frag)}, 30) == LineRenderRoute::Native,
            "actual compiled uncharged FragCoord preserves the full30 thin route");
    require(select_line_render_route(state(1, false), {30, 30,
                fragment_inter_stage_builtin_variables(facing->spv_frag)}, 30) == LineRenderRoute::Generated,
            "actual compiled charged FrontFacing cannot exceed the full30 grant");
    require(coordinate->spv_frag == original_coordinate && facing->spv_frag == original_facing,
            "builtin admission reads retained artifact words without modifying them");

    // Declaration-only word records exercise all six charged identities and
    // Input versus Output/member provenance. They are not runnable shaders.
    const auto append = [](std::vector<uint32_t>& words, uint32_t op,
                           std::initializer_list<uint32_t> operands) {
        words.push_back((static_cast<uint32_t>(operands.size() + 1) << 16) | op);
        words.insert(words.end(), operands.begin(), operands.end());
    };
    std::vector<uint32_t> words{0x07230203u, 0x00010000u, 0, 128, 0};
    append(words, 32, {10, 1, 11});
    uint32_t id = 20;
    for (uint32_t builtin : {7u, 17u, 18u, 20u, 36u, 41u, 15u}) {
        append(words, 59, {10, id, 1});
        append(words, 71, {id++, 11, builtin});
    }
    append(words, 71, {20, 11, 7});  // Duplicate PrimitiveId is still one flag.
    append(words, 32, {40, 3, 41});
    append(words, 59, {40, 42, 3});
    append(words, 71, {42, 11, 20});  // Output SampleMask is not charged.
    append(words, 72, {41, 0, 11, 17});  // Output struct member is not charged.
    require(fragment_inter_stage_builtin_variables(words) == 6,
            "six distinct Input builtin flags counted once; FragCoord and Output decorations excluded");
    std::vector<uint32_t> block{0x07230203u, 0x00010000u, 0, 128, 0};
    append(block, 32, {10, 1, 11}); append(block, 59, {10, 20, 1});
    append(block, 72, {11, 0, 11, 20});
    require(fragment_inter_stage_builtin_variables(block) == 1,
            "reachable Input block member BuiltIn contributes to the grant");
    for (const auto& invalid : {std::vector<uint32_t>{},
            std::vector<uint32_t>{0, 0, 0, 0, 0},
            std::vector<uint32_t>{0x07230203u, 0, 0, 0, 0, 0},
            std::vector<uint32_t>{0x07230203u, 0, 0, 0, 0, (4u << 16) | 71u, 20}}) {
        bool rejected = false;
        try { (void)fragment_inter_stage_builtin_variables(invalid); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "actual builtin reader refuses missing magic and malformed/truncated word records");
    }
}
}  // namespace

int main() {
    try {
        immutable_joined_records();
        policy_fifo_snapshot_lifetimes();
        generation_loss_and_recovery();
        complete_cache_consistency_guard();
        owned_storage_accounting_and_variants();
        ordinary_line_route_admission();
        retained_fragment_builtin_admission();
        std::cout << "runtime line consumer policy contract: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "runtime line consumer policy contract failed after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
