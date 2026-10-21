#include "runtime_line_pool.hpp"

#include <array>
#include <iostream>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace {
using namespace vispy::lines;
unsigned checks = 0;
void check(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
template<class Error, class Call> void rejects(Call&& call, const char* message) {
    bool caught = false;
    try { call(); } catch (const Error&) { caught = true; }
    check(caught, message);
}

struct Payload {
    std::shared_ptr<uint64_t> native_owner;
    int compute_value = 0, render_value = 0;
};
using Pool = LineResourcePool<Payload>;
struct Builder {
    uint64_t calls = 0, fail_call = 0;
    bool excess_control = false;
    std::vector<std::weak_ptr<uint64_t>> created;
    BuiltPoolPayload<Payload> operator()(const SlotPlan& plan) {
        ++calls;
        if (calls == fail_call) throw std::runtime_error("injected native builder failure");
        auto owner = std::make_shared<uint64_t>(calls);
        created.push_back(owner);
        return {Payload{std::move(owner)}, plan.extra_control_bytes + (excess_control ? 1 : 0)};
    }
};
PoolLimits limits(size_t count, uint64_t bytes, uint64_t control = 65536) {
    return {count, bytes, control, bytes, control};
}
LeaseRequest request(std::string_view affinity, LeaseCapacities capacities,
        uint64_t extra = 0, uint64_t generation = 1) {
    return {generation, affinity, capacities, extra};
}
auto reserve(Pool& pool, const LeaseRequest& value, Builder& builder) {
    return pool.reserve_batch(std::span<const LeaseRequest>(&value, 1), builder);
}
void finish(Pool::ReserveResult& result) {
    result.reservation.mark_submitted();
    result.reservation.retire();
}
void bounds(const Pool& pool) {
    const auto stats = pool.stats(); const auto cap = pool.limits();
    check(stats.slots <= cap.max_slots, "resident slot bound");
    check(stats.busy_slots <= stats.slots, "busy subset");
    check(stats.owned_capacity_bytes <= cap.owned_capacity_bytes, "resident owned-capacity bound");
    check(stats.control_bytes <= cap.control_bytes, "resident control-capacity bound");
    check(stats.staging_peak_slots <= cap.max_slots, "staged payload count bound");
    check(stats.staging_peak_owned_capacity_bytes <= cap.staging_owned_capacity_bytes, "staged owned-capacity bound");
    check(stats.staging_peak_control_bytes <= cap.staging_control_bytes, "staged control-capacity bound");
}

void distinct_pending_values_and_real_retirement() {
    Pool pool(limits(2, 64), 1); Builder builder;
    const std::array values{request("same", {16, 8, 8}, 128), request("same", {16, 8, 8}, 128)};
    auto batch = pool.reserve_batch(values, builder);
    check(bool(batch) && batch.reservation.size() == 2, "whole batch admitted");
    check(batch.reservation.at(0).id() != batch.reservation.at(1).id(), "pending draws have distinct slots");
    batch.reservation.at(0).payload().compute_value = 11;
    batch.reservation.at(0).payload().render_value = 21;
    batch.reservation.at(1).payload().compute_value = 12;
    batch.reservation.at(1).payload().render_value = 22;
    batch.reservation.mark_submitted();
    check(std::as_const(batch.reservation.at(0)).payload().compute_value == 11 &&
        std::as_const(batch.reservation.at(1)).payload().compute_value == 12, "compute values stay distinct");
    check(std::as_const(batch.reservation.at(0)).payload().render_value == 21 &&
        std::as_const(batch.reservation.at(1)).payload().render_value == 22, "paired render values stay distinct");
    rejects<std::logic_error>([&] { batch.reservation.at(0).payload(); }, "submitted payload cannot mutate");
    rejects<std::logic_error>([&] { batch.reservation.rollback(); }, "submission cannot roll back before processing");
    rejects<std::logic_error>([&] { batch.reservation.mark_submitted(); }, "no duplicate submission");
    auto busy = reserve(pool, values[0], builder);
    check(!busy && busy.status == ReservationStatus::Unavailable && busy.reservation.size() == 0,
        "actual busy resources defer without partial reservation");
    check(builder.calls == 2 && pool.stats().deferrals == 1 && pool.stats().busy_slots == 2,
        "deferral performs no builders and preserves submitted owners");
    const auto previous = batch.reservation.at(0);
    batch.reservation.retire();
    batch.reservation.retire();
    check(pool.stats().busy_slots == 0, "actual processing releases whole batch exactly once");
    rejects<std::logic_error>([&] { std::as_const(previous).payload(); }, "retired handle is stale");
    auto reused = pool.reserve_batch(values, builder);
    check(bool(reused) && builder.calls == 2 && pool.stats().hits == 2, "whole retired batch reuses native owners");
    rejects<std::logic_error>([&] { std::as_const(previous).payload(); }, "old token cannot access a new lease");
    rejects<std::logic_error>([&] { reused.reservation.retire(); }, "unsubmitted work is not a processed Ticket");
    reused.reservation.rollback();
    bounds(pool);
}

void affinity_reuse_and_capacity_cover() {
    Pool pool(limits(3, 96), 1); Builder builder;
    auto a = reserve(pool, request("A", {16, 4, 4}, 8), builder);
    const auto aid = a.reservation.at(0).id(); const auto apayload = a.reservation.at(0).payload().native_owner;
    finish(a);
    auto b = reserve(pool, request("B", {16, 4, 4}, 8), builder);
    const auto bid = b.reservation.at(0).id(); finish(b);
    check(aid != bid && pool.stats().slots == 2, "available budget preserves separate A and B affinities");
    auto again = reserve(pool, request("A", {8, 2, 2}, 4), builder);
    check(again.reservation.at(0).id() == aid && again.reservation.at(0).payload().native_owner == apayload,
        "A-B-A retains exact owner and covers all smaller capacities");
    check(builder.calls == 2 && pool.stats().hits == 1, "A-B-A needs no builder");
    finish(again);
    auto changed = reserve(pool, request("A", {8, 2, 2}, 16), builder);
    check(changed.reservation.at(0).id() != aid && builder.calls == 3,
        "dynamic key/weak-ref/UBO-shadow capacity participates in cover");
    check(changed.reservation.at(0).extra_control_bytes() == 16, "charged dynamic upper bound retained");
    finish(changed);
    bounds(pool);
}

void matching_is_not_request_order_dependent() {
    Pool pool(limits(2, 32), 1); Builder builder;
    const std::array initial{request("A", {8, 8, 0}), request("A", {8, 0, 8})};
    auto cached = pool.reserve_batch(initial, builder);
    const auto special = cached.reservation.at(0).id(); finish(cached);
    const std::array needs{request("A", {8, 0, 0}), request("A", {8, 8, 0})};
    auto assigned = pool.reserve_batch(needs, builder);
    check(bool(assigned) && builder.calls == 2, "augmenting assignment reuses specialized idle slots");
    check(assigned.reservation.at(1).id() == special, "specialized request gets its only suitable slot");
    check(assigned.reservation.at(0).id() != special, "generic request moves to the other suitable slot");
    assigned.reservation.rollback(); bounds(pool);

    Pool pressure(limits(1, 16), 1); Builder other;
    auto old = reserve(pressure, request("old", {8, 4, 4}, 8), other);
    const auto identity = old.reservation.at(0).id(); finish(old);
    auto rekeyed = reserve(pressure, request("new", {4, 2, 2}, 4), other);
    check(rekeyed.reservation.at(0).id() == identity && other.calls == 1,
        "full idle pool rekeys suitable capacity without allocation");
    std::string stored;
    pressure.for_each_slot([&](const auto& slot) { stored.assign(slot.affinity); });
    check(stored == "new", "affinity updates only after successful reservation");
    rekeyed.reservation.rollback(); bounds(pressure);
}

void replacement_has_bounded_staging_and_strong_builder_failure() {
    Pool pool(limits(2, 64), 1); Builder initial;
    const std::array old{request("old-a", {16, 4, 4}), request("old-b", {16, 4, 4})};
    auto cached = pool.reserve_batch(old, initial);
    const auto first_weak = initial.created[0], second_weak = initial.created[1];
    finish(cached); cached.reservation = {};
    const auto before = pool.stats();
    const std::array replacement{request("new-a", {16, 8, 8}), request("new-b", {16, 8, 8})};
    Builder failed; failed.fail_call = 2;
    rejects<std::runtime_error>([&] { pool.reserve_batch(replacement, failed); }, "second builder failure propagates");
    check(pool.stats().slots == before.slots && pool.stats().busy_slots == 0 &&
        pool.stats().owned_capacity_bytes == before.owned_capacity_bytes &&
        pool.stats().hits == before.hits && pool.stats().evictions == before.evictions,
        "builder failure neither publishes partial slots nor evicts idle victims");
    check(!first_weak.expired() && !second_weak.expired() && failed.created[0].expired(),
        "old idle owners survive, staged failed payload is released");
    Builder complete; uint64_t staged = 0;
    auto result = pool.reserve_batch(replacement, [&](const SlotPlan& plan) {
        check(!first_weak.expired() && !second_weak.expired(), "old idle owners remain during every builder");
        check(pool.stats().owned_capacity_bytes == before.owned_capacity_bytes && pool.stats().busy_slots == 0,
            "builders observe no partial publication");
        staged += line_pool_detail::capacity_bytes(plan.capacities);
        check(staged <= pool.limits().staging_owned_capacity_bytes, "staged payload capacities are independently bounded");
        check(pool.stats().owned_capacity_bytes + staged <=
            pool.limits().owned_capacity_bytes + pool.limits().staging_owned_capacity_bytes,
            "resident plus transient capacity has declared combined bound");
        return complete(plan);
    });
    check(bool(result) && first_weak.expired() && second_weak.expired(), "full-idle replacement publishes atomically");
    check(pool.stats().evictions == 2 && pool.stats().owned_capacity_bytes == 64,
        "replacement charges new owners and counts both old evictions");
    check(pool.stats().staging_peak_owned_capacity_bytes == 64 && pool.stats().staging_peak_slots == 2,
        "staging peaks disclose full replacement allowance");
    result.reservation.rollback(); bounds(pool);
}

void permanent_limits_and_whole_batch_busy_deferral() {
    Pool pool(limits(2, 32), 1); Builder builder;
    const std::array impossible{request("A", {17, 0, 0}), request("B", {16, 0, 0})};
    rejects<std::length_error>([&] { pool.reserve_batch(impossible, builder); }, "permanent combined byte excess is explicit");
    const std::array too_many{request("A", {1, 0, 0}), request("B", {1, 0, 0}), request("C", {1, 0, 0})};
    rejects<std::length_error>([&] { pool.reserve_batch(too_many, builder); }, "permanent batch slot excess is explicit");
    check(builder.calls == 0 && pool.stats().slots == 0, "impossible batches reject before builders");
    auto busy = reserve(pool, request("busy", {16, 0, 0}), builder);
    busy.reservation.mark_submitted();
    const std::array whole{request("A", {8, 0, 0}), request("B", {8, 0, 0})};
    auto deferred = pool.reserve_batch(whole, builder);
    check(!deferred && builder.calls == 1 && pool.stats().slots == 1 && pool.stats().busy_slots == 1,
        "slot pressure defers whole batch rather than publishing its first draw");
    busy.reservation.retire();
    auto available = pool.reserve_batch(whole, builder);
    check(bool(available) && available.reservation.size() == 2, "same legal batch admits after actual processing");
    available.reservation.rollback(); bounds(pool);
    auto cap = limits(1, 32); cap.staging_owned_capacity_bytes = 16;
    Pool staged(cap, 1);
    rejects<std::length_error>([&] { reserve(staged, request("large", {17, 0, 0}), builder); },
        "permanent staging capacity excess is separately explicit");
}

void control_count_churn_and_binary_affinity() {
    Pool probe(limits(4, 16), 1); Builder builder;
    auto seed = reserve(probe, request("A", {1, 0, 0}, 4096), builder); finish(seed);
    const auto stats = probe.stats();
    const auto control = std::max(stats.control_bytes, stats.staging_peak_control_bytes) + 128;
    Pool tight(limits(4, 16, control), 1); Builder small;
    auto a = reserve(tight, request("A", {1, 0, 0}, 4096), small); finish(a); a.reservation = {};
    auto b = reserve(tight, request("B", {1, 1, 0}, 4096), small); finish(b);
    check(tight.stats().slots == 1 && tight.stats().evictions == 1 && small.calls == 2,
        "dynamic control pressure evicts despite available GPU bytes/count");
    bounds(tight);

    Pool churn(limits(2, 8), 1); Builder many;
    for (unsigned index = 0; index != 25; ++index) {
        const std::string key = std::to_string(index);
        auto next = reserve(churn, request(key, {4, 0, 0}), many); finish(next);
        bounds(churn);
    }
    // Same capacities are repurposed under pressure; count/capacity cannot grow.
    check(churn.stats().slots == 2 && many.calls == 2 && churn.stats().hits == 23,
        "long affinity churn stays bounded and reuses sufficient idle capacity");
    Pool binary(limits(2, 8), 1); Builder keys;
    const std::string first("A\0B", 3), second("A\0C", 3);
    auto one = reserve(binary, request(first, {4, 0, 0}), keys); const auto identity = one.reservation.at(0).id(); finish(one);
    auto two = reserve(binary, request(second, {4, 0, 0}), keys); finish(two);
    auto again = reserve(binary, request(first, {4, 0, 0}), keys);
    check(again.reservation.at(0).id() == identity && keys.calls == 2, "binary affinities compare their complete length");
    again.reservation.rollback(); bounds(binary);
}

void failure_control_overflow_and_stale_generation() {
    Pool pool(limits(1, 16), 1); Builder builder;
    auto old = reserve(pool, request("A", {8, 0, 0}, 8), builder);
    const auto id = old.reservation.at(0).id(); finish(old);
    Builder invalid; invalid.excess_control = true;
    rejects<std::length_error>([&] { reserve(pool, request("B", {16, 0, 0}, 16), invalid); },
        "builder cannot exceed reserved dynamic key/shadow capacity");
    check(pool.stats().slots == 1 && pool.stats().evictions == 0 && pool.stats().busy_slots == 0,
        "post-build capacity failure preserves old ledger");
    auto again = reserve(pool, request("A", {8, 0, 0}, 8), builder);
    check(again.reservation.at(0).id() == id && builder.calls == 1, "failed replacement preserves exact affinity owner");
    again.reservation.rollback();
    rejects<std::overflow_error>([&] { reserve(pool, request("overflow", {UINT64_MAX, 1, 0}), builder); },
        "output plus UBO arithmetic cannot wrap");
    rejects<std::overflow_error>([&] { reserve(pool, request("overflow", {1, 0, 0}, UINT64_MAX), builder); },
        "dynamic control arithmetic cannot wrap");
    rejects<std::length_error>([&] { reserve(pool, request(std::string(65536, 'x'), {1, 0, 0}), builder); },
        "excessive affinity control rejects before copying into pool");
    rejects<std::invalid_argument>([&] { reserve(pool, request("stale", {1, 0, 0}, 0, 2), builder); },
        "stale device request cannot enter generation");
    rejects<std::invalid_argument>([&] { pool.invalidate_generation(0); }, "zero generation is invalid");
    auto bad = limits(1, 16); bad.staging_owned_capacity_bytes = 17;
    rejects<std::invalid_argument>([&] { Pool invalid_limits(bad, 1); }, "staging capacities cannot exceed resident ceiling");
    bad = limits(1, 16); ++bad.staging_control_bytes;
    rejects<std::invalid_argument>([&] { Pool invalid_limits(bad, 1); }, "staging control cannot exceed resident ceiling");
    bounds(pool);
}

void old_generation_busy_and_external_owners() {
    Pool pool(limits(2, 32), 1); Builder builder;
    auto old = reserve(pool, request("A", {16, 0, 0}), builder);
    auto old_handle = old.reservation.at(0); const auto weak = builder.created.back();
    old.reservation.mark_submitted(); pool.invalidate_generation(2);
    check(pool.stats().slots == 1 && pool.stats().busy_slots == 1 && pool.stats().owned_capacity_bytes == 16,
        "old generation submitted resource stays fully charged");
    auto fresh = reserve(pool, request("A", {16, 0, 0}, 0, 2), builder);
    check(fresh.reservation.at(0).id() != old_handle.id() && fresh.reservation.at(0).generation() == 2,
        "new generation never recycles an old busy handle");
    check(std::as_const(old_handle).payload().native_owner && !weak.expired(),
        "old submitted external owner survives generation replacement");
    finish(fresh); old.reservation.retire();
    check(pool.stats().slots == 1 && pool.stats().busy_slots == 0 && pool.stats().owned_capacity_bytes == 16,
        "old generation leaves cache only after actual processing");
    check(!weak.expired(), "retired external native owner remains separately live");
    rejects<std::logic_error>([&] { std::as_const(old_handle).payload(); }, "retired old-generation lease cannot encode");
    check(old_handle.inspect_payload().native_owner != nullptr, "separate accounting can inspect retired owner");
    old.reservation = {}; old_handle = {};
    check(weak.expired(), "last external retired owner releases old native payload");
    rejects<std::invalid_argument>([&] { pool.invalidate_generation(1); }, "generation cannot move backward");
    bounds(pool);

    auto held = fresh.reservation.at(0); const auto second_weak = builder.created.back();
    fresh.reservation = {}; pool.invalidate_generation(3);
    check(pool.stats().slots == 0 && !second_weak.expired(), "idle generation invalidation preserves external owners only");
    held = {};
    check(second_weak.expired(), "external owner controls its own eventual destruction");
    auto empty = pool.reserve_batch(std::span<const LeaseRequest>{}, builder);
    check(bool(empty) && empty.reservation.size() == 0 && builder.calls == 2, "empty batch requires no builder");
    finish(empty); bounds(pool);
}

void unsubmitted_rollback_and_owner_lifetime() {
    Pool pool(limits(1, 8), 1); Builder builder;
    uint64_t identity = 0;
    {
        auto rollback = reserve(pool, request("A", {8, 0, 0}), builder);
        identity = rollback.reservation.at(0).id();
        check(pool.stats().busy_slots == 1, "unsubmitted slot is exclusive");
    }
    check(pool.stats().busy_slots == 0, "unsubmitted reservation destruction rolls back without completion");
    auto reused = reserve(pool, request("A", {8, 0, 0}), builder);
    check(reused.reservation.at(0).id() == identity && builder.calls == 1, "rollback preserves cached payload");
    auto moved = std::move(reused.reservation);
    check(moved.size() == 1 && pool.stats().busy_slots == 1, "move transfers reservation without releasing slot");
    moved.mark_submitted();
    const auto weak = builder.created.back();
    {
        auto temporary = std::move(pool);
        check(!weak.expired() && temporary.stats().busy_slots == 1, "moving ledger preserves busy owner");
    }
    check(!weak.expired(), "Ticket-like reservation retains state after pool destruction");
    moved.retire(); moved = {};
    check(weak.expired(), "real processing and last owner destruction release payload");

    Pool no_false_retirement(limits(1, 8), 1); Builder another;
    {
        auto submitted = reserve(no_false_retirement, request("A", {8, 0, 0}), another);
        submitted.reservation.mark_submitted();
    }
    check(no_false_retirement.stats().busy_slots == 1, "dropping submitted owner never manufactures Ticket completion");
    check(!reserve(no_false_retirement, request("A", {8, 0, 0}), another),
        "missing explicit retirement remains bounded nonblocking deferral");
    bounds(no_false_retirement);
}

void invalid_native_payloads_discard_only_at_release() {
    Pool pool(limits(2, 32), 1); Builder builder;
    auto good = reserve(pool, request("good", {16, 0, 0}), builder);
    const auto good_id = good.reservation.at(0).id(); finish(good);
    auto bad = reserve(pool, request("bad", {16, 0, 0}), builder);
    const auto first_bad_id = bad.reservation.at(0).id();
    auto previous_bad = bad.reservation.at(0);
    const auto first_bad_weak = builder.created.back();
    bad.reservation.rollback(false);
    check(pool.stats().slots == 1 && pool.stats().busy_slots == 0,
        "unsubmitted failure drops only its cache owner");
    check(!first_bad_weak.expired(), "invalid external handle retains payload until its owner releases");
    rejects<std::logic_error>([&] { std::as_const(previous_bad).payload(); }, "discarded failed lease cannot encode");
    auto rebuilt = reserve(pool, request("bad", {16, 0, 0}), builder);
    check(rebuilt.reservation.at(0).id() != first_bad_id && builder.calls == 3,
        "failed native payload is rebuilt rather than a cache hit");
    const auto second_bad_id = rebuilt.reservation.at(0).id();
    rebuilt.reservation.mark_submitted();
    rejects<std::logic_error>([&] { rebuilt.reservation.rollback(false); },
        "submitted invalid payload cannot be discarded before processing");
    check(pool.stats().slots == 2 && pool.stats().busy_slots == 1 && pool.stats().owned_capacity_bytes == 32,
        "failed submitted slot remains charged/nonreusable until actual retirement");
    const std::array busy_needs{request("good", {16, 0, 0}), request("bad", {16, 0, 0})};
    auto blocked = pool.reserve_batch(busy_needs, builder);
    check(!blocked && builder.calls == 3 && pool.stats().busy_slots == 1,
        "busy invalid payload defers whole batch without reserving/rekeying good survivor");
    rebuilt.reservation.retire(false);
    check(pool.stats().slots == 1 && pool.stats().busy_slots == 0 && pool.stats().owned_capacity_bytes == 16,
        "actual failure retirement drops only submitted batch cache owner");
    const auto calls = builder.calls;
    auto survivor = reserve(pool, request("good", {16, 0, 0}), builder);
    check(survivor.reservation.at(0).id() == good_id && builder.calls == calls,
        "unrelated valid owner survives failure and remains reusable");
    // An already-finished reservation cannot discard a subsequent lease of
    // the same valid slot, even when the later operation asks not to retain.
    good.reservation.retire(false);
    check(pool.stats().busy_slots == 1 && survivor.reservation.at(0).payload().native_owner,
        "old finished reservation cannot retire/discard new token");
    survivor.reservation.rollback();
    bad.reservation = {}; previous_bad = {};
    check(first_bad_weak.expired(), "invalid old external payload eventually releases");
    auto final_bad = reserve(pool, request("bad", {16, 0, 0}), builder);
    check(final_bad.reservation.at(0).id() != second_bad_id && builder.calls == calls + 1,
        "submitted native failure is not reused on next matching draw");
    final_bad.reservation.rollback(); bounds(pool);
}

void exact_staging_ceiling_replaces_idle_without_false_busy() {
    const auto large = request("large", {16, 0, 0}, 4096);
    Pool probe(limits(1, 16), 1); Builder probe_builder;
    auto measured = reserve(probe, large, probe_builder); finish(measured);
    const auto exact = probe.stats().staging_peak_control_bytes;
    check(exact >= probe.stats().control_bytes, "test derives genuine exact empty-pool staging ceiling");
    Pool pool(limits(1, 16, exact), 1); Builder builder;
    auto small = reserve(pool, request("small", {8, 0, 0}), builder);
    const auto weak = builder.created.back(); finish(small); small.reservation = {};
    const auto old_stats = pool.stats();
    Builder failure; failure.fail_call = 1;
    rejects<std::runtime_error>([&] { reserve(pool, large, failure); }, "exact-bound replacement reaches staged builder");
    check(pool.stats().slots == 1 && pool.stats().busy_slots == 0 && pool.stats().deferrals == 0 &&
        pool.stats().owned_capacity_bytes == old_stats.owned_capacity_bytes && !weak.expired(),
        "exact-bound failed builder preserves idle old owner without false deferral");
    auto replaced = pool.reserve_batch(std::span<const LeaseRequest>(&large, 1), [&](const SlotPlan& plan) {
        check(!weak.expired() && pool.stats().slots == 1 && pool.stats().busy_slots == 0,
            "pruned empty planner retains original State owner through construction");
        return builder(plan);
    });
    check(bool(replaced) && replaced.reservation.size() == 1 && pool.stats().deferrals == 0,
        "idle replacement admits at exact fresh staging ceiling");
    check(weak.expired() && pool.stats().evictions == 1 && pool.stats().staging_peak_control_bytes == exact,
        "atomic publication releases old owner and charges exact staging capacity");
    replaced.reservation.rollback(); bounds(pool);
}
} // namespace

int main() {
    try {
        distinct_pending_values_and_real_retirement();
        affinity_reuse_and_capacity_cover();
        matching_is_not_request_order_dependent();
        replacement_has_bounded_staging_and_strong_builder_failure();
        permanent_limits_and_whole_batch_busy_deferral();
        control_count_churn_and_binary_affinity();
        failure_control_overflow_and_stale_generation();
        old_generation_busy_and_external_owners();
        unsubmitted_rollback_and_owner_lifetime();
        invalid_native_payloads_discard_only_at_release();
        exact_staging_ceiling_replaces_idle_without_false_busy();
        std::cout << "line resource pool: " << checks << " checks passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "line resource pool contract failed after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
