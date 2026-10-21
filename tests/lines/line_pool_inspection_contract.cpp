#include "runtime_line_pool.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <new>
#include <tuple>
#include <type_traits>

// A pure ledger contract. Payload owners below are ordinary C++ sentinels;
// this does not simulate Dawn submission, callbacks, GPU work or retirement.
namespace allocation_probe {
bool forbidden = false;
unsigned attempts = 0;
}
void* operator new(std::size_t bytes) {
    if (allocation_probe::forbidden) {
        ++allocation_probe::attempts;
        throw std::bad_alloc();
    }
    if (auto* result = std::malloc(bytes ? bytes : 1)) return result;
    throw std::bad_alloc();
}
void* operator new[](std::size_t bytes) { return ::operator new(bytes); }
void operator delete(void* value) noexcept { std::free(value); }
void operator delete[](void* value) noexcept { std::free(value); }
void operator delete(void* value, std::size_t) noexcept { std::free(value); }
void operator delete[](void* value, std::size_t) noexcept { std::free(value); }

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
struct AllocationBan {
    AllocationBan() { allocation_probe::forbidden = true; }
    ~AllocationBan() { allocation_probe::forbidden = false; }
};
struct Payload {
    static inline unsigned copies = 0;
    std::shared_ptr<uint64_t> owner;
    explicit Payload(std::shared_ptr<uint64_t> value) : owner(std::move(value)) {}
    Payload(const Payload& other) : owner(other.owner) { ++copies; }
    Payload(Payload&&) noexcept = default;
    Payload& operator=(const Payload& other) { owner = other.owner; ++copies; return *this; }
    Payload& operator=(Payload&&) noexcept = default;
};
using Pool = LineResourcePool<Payload>;
using Snapshot = Pool::SlotSnapshot;
static_assert(std::is_trivially_copyable_v<Snapshot> && std::is_standard_layout_v<Snapshot>);
struct Builder {
    uint64_t calls = 0;
    std::vector<std::weak_ptr<uint64_t>> created;
    BuiltPoolPayload<Payload> operator()(const SlotPlan& plan) {
        auto value = std::make_shared<uint64_t>(++calls);
        created.push_back(value);
        return {Payload(std::move(value)), plan.extra_control_bytes};
    }
};
PoolLimits limits(size_t count, uint64_t bytes) { return {count, bytes, 65536, bytes, 65536}; }
LeaseRequest request(std::string_view key, LeaseCapacities capacities, uint64_t extra = 0, uint64_t generation = 1) {
    return {generation, key, capacities, extra};
}
auto reserve(Pool& pool, const LeaseRequest& value, Builder& builder) {
    return pool.reserve_batch(std::span<const LeaseRequest>(&value, 1), builder);
}
auto stats_key(const Pool::Stats& value) {
    return std::tuple{value.slots, value.busy_slots, value.owned_capacity_bytes, value.control_bytes,
        value.hits, value.evictions, value.deferrals, value.staging_peak_slots,
        value.staging_peak_owned_capacity_bytes, value.staging_peak_control_bytes};
}
struct Observation {
    std::array<Snapshot, 4> rows;
    size_t count = 0;
};
Observation inspect(const Pool& pool, const Builder& builder) {
    const auto before = stats_key(pool.stats());
    const auto calls = builder.calls;
    const auto copies = Payload::copies;
    Observation result;
    for (size_t index = 0; index < result.rows.size(); ++index)
        result.rows[index] = {900 + index, 700 + index, PoolSlotState::Submitted, {101, 102, 103}, 104};
    const auto sentinels = result.rows;
    size_t required = 0;
    {
        AllocationBan ban;
        required = pool.slot_snapshot_count();
        result.count = pool.snapshot_slots(result.rows);
    }
    check(result.count == required && result.count == pool.stats().slots, "inspection reports complete actual membership");
    check(result.count <= pool.limits().max_slots && result.count <= result.rows.size(), "inspection remains caller/pool bounded");
    check(stats_key(pool.stats()) == before, "all accounting and cumulative counters remain unchanged");
    check(builder.calls == calls && Payload::copies == copies, "inspection neither invokes builders nor copies Payload");
    check(allocation_probe::attempts == 0, "successful bounded inspection never allocates");
    for (size_t index = result.count; index < result.rows.size(); ++index)
        check(result.rows[index] == sentinels[index], "excess destination rows remain untouched");
    for (size_t index = 1; index < result.count; ++index)
        check(result.rows[index - 1].slot_id < result.rows[index].slot_id, "deterministic retained slot order");
    return result;
}
const Snapshot& row(const Observation& value, uint64_t id) {
    for (size_t index = 0; index < value.count; ++index)
        if (value.rows[index].slot_id == id) return value.rows[index];
    throw std::runtime_error("missing actual lease identity in snapshot");
}
bool contains(const Observation& value, uint64_t id) {
    for (size_t index = 0; index < value.count; ++index)
        if (value.rows[index].slot_id == id) return true;
    return false;
}
void same_stats(const Pool& observed, const Pool& control) {
    check(stats_key(observed.stats()) == stats_key(control.stats()), "inspection does not alter matched lifecycle/accounting");
}

void empty_reserved_submitted_and_bounded_output() {
    // Prove the allocation sentinel actually refuses allocations before using
    // it as a negative condition on the inspection implementation.
    {
        AllocationBan ban;
        rejects<std::bad_alloc>([] { auto* value = ::operator new(1); ::operator delete(value); }, "allocation fault sentinel is active");
    }
    check(allocation_probe::attempts == 1, "allocation sentinel records the real attempted allocation");
    allocation_probe::attempts = 0;
    Pool pool(limits(3, 512), 1); Builder builder;
    auto empty = inspect(pool, builder);
    check(empty.count == 0, "empty pool exposes no invented slots");
    {
        AllocationBan ban;
        check(pool.snapshot_slots(std::span<Snapshot>{}) == 0, "empty destination accepts empty pool");
    }
    const std::string affinity(4096, 'x');
    const std::array requests{request(affinity, {16, 4, 8}, 80), request("B", {8, 4, 4}, 16)};
    auto batch = pool.reserve_batch(requests, builder);
    check(bool(batch) && batch.reservation.size() == 2, "reserved pair admitted");
    const auto first = batch.reservation.at(0).id(), second = batch.reservation.at(1).id();
    const auto initial = inspect(pool, builder);
    for (size_t index = 0; index < batch.reservation.size(); ++index) {
        const auto& lease = batch.reservation.at(index);
        const auto& actual = row(initial, lease.id());
        check(actual.slot_id == lease.id() && actual.generation == lease.generation(), "snapshot uses actual reservation identity");
        check(actual.state == PoolSlotState::Reserved && actual.capacities == lease.capacities() &&
            actual.extra_control_bytes == lease.extra_control_bytes(), "reserved metadata exactly matches the lease");
    }
    const auto owner_count = std::as_const(batch.reservation.at(0)).payload().owner.use_count();
    for (unsigned repeat = 0; repeat != 64; ++repeat) {
        const auto next = inspect(pool, builder);
        check(next.count == initial.count && next.rows == initial.rows, "repeated snapshots preserve deterministic values");
    }
    check(std::as_const(batch.reservation.at(0)).payload().owner.use_count() == owner_count,
        "plain snapshots retain no shared payload owner");
    std::array<Snapshot, 1> small{Snapshot{123, 456, PoolSlotState::Submitted, {7, 8, 9}, 10}};
    const auto saved = small;
    const auto before = stats_key(pool.stats());
    rejects<std::length_error>([&] { pool.snapshot_slots(small); }, "insufficient caller storage rejects before writing");
    check(small == saved && stats_key(pool.stats()) == before, "insufficient span has no partial output/state change");
    batch.reservation.mark_submitted();
    const auto submitted = inspect(pool, builder);
    check(row(submitted, first).state == PoolSlotState::Submitted && row(submitted, second).state == PoolSlotState::Submitted,
        "inspection observes submitted owners without retirement");
    rejects<std::logic_error>([&] { batch.reservation.rollback(false); }, "inspection cannot make submitted rollback legal");
    for (unsigned repeat = 0; repeat != 32; ++repeat)
        check(inspect(pool, builder).rows == submitted.rows && pool.stats().busy_slots == 2,
            "peeking never supplies a completion or makes a slot idle");
    batch.reservation.retire();
    const auto retired = inspect(pool, builder);
    check(row(retired, first).state == PoolSlotState::Idle && row(retired, second).state == PoolSlotState::Idle,
        "explicit retirement alone changes submitted rows to idle");
    check(row(submitted, first).state == PoolSlotState::Submitted && row(initial, first).state == PoolSlotState::Reserved,
        "previous owned value snapshots do not become aliases to later state");
}

void matched_lifecycle_and_unaffected_idle_control() {
    Pool observed(limits(3, 64), 7), control(limits(3, 64), 7);
    Builder observed_builder, control_builder;
    const auto idle_request = request("unaffected", {8, 4, 4}, 8, 7);
    auto idle = reserve(observed, idle_request, observed_builder);
    auto idle_control = reserve(control, idle_request, control_builder);
    const auto idle_id = idle.reservation.at(0).id();
    idle.reservation.mark_submitted(); idle.reservation.retire();
    idle_control.reservation.mark_submitted(); idle_control.reservation.retire();
    same_stats(observed, control);
    const std::array requests{request("A", {16, 4, 4}, 12, 7), request("B", {16, 4, 4}, 12, 7)};
    auto working = observed.reserve_batch(requests, observed_builder);
    auto working_control = control.reserve_batch(requests, control_builder);
    const auto first = working.reservation.at(0).id(), second = working.reservation.at(1).id();
    check(first == working_control.reservation.at(0).id() && second == working_control.reservation.at(1).id(),
        "inspection has not consumed or changed actual future lease IDs");
    const auto first_owner = observed_builder.created[1];
    working.reservation.mark_submitted(); working_control.reservation.mark_submitted();
    same_stats(observed, control);
    const auto submitted = inspect(observed, observed_builder);
    check(row(submitted, idle_id).state == PoolSlotState::Idle && row(submitted, first).state == PoolSlotState::Submitted &&
        row(submitted, second).state == PoolSlotState::Submitted, "unaffected idle control stays distinct from submitted pair");
    check(observed.stats().owned_capacity_bytes == 64 && observed.stats().busy_slots == 2,
        "all idle and submitted capacities remain fully charged");
    for (unsigned repeat = 0; repeat != 32; ++repeat) {
        check(inspect(observed, observed_builder).rows == submitted.rows, "read-only observation preserves charged submitted identity");
        same_stats(observed, control);
    }
    auto deferred = reserve(observed, requests[0], observed_builder);
    auto deferred_control = reserve(control, requests[0], control_builder);
    check(!deferred && !deferred_control, "actual busy ownership still defers matching admission");
    same_stats(observed, control);
    check(inspect(observed, observed_builder).rows == submitted.rows, "deferral leaves unaffected and busy rows unchanged");
    working.reservation.retire(); working_control.reservation.retire();
    same_stats(observed, control);
    const auto idle_rows = inspect(observed, observed_builder);
    check(row(idle_rows, idle_id).state == PoolSlotState::Idle && row(idle_rows, first).state == PoolSlotState::Idle &&
        row(idle_rows, second).state == PoolSlotState::Idle, "actual release preserves cached idle capacities");
    auto reused = reserve(observed, requests[0], observed_builder);
    auto reused_control = reserve(control, requests[0], control_builder);
    check(reused.reservation.at(0).id() == first && reused_control.reservation.at(0).id() == first,
        "the same idle lease is reused after explicit retirement");
    same_stats(observed, control);
    reused.reservation.rollback(false); reused_control.reservation.rollback(false);
    working.reservation = {}; working_control.reservation = {};
    reused.reservation = {}; reused_control.reservation = {};
    same_stats(observed, control);
    const auto released = inspect(observed, observed_builder);
    check(!contains(released, first) && contains(released, idle_id) && contains(released, second),
        "discard removes only the released lease and leaves unrelated idle capacities intact");
    check(first_owner.expired() && row(submitted, first).slot_id == first,
        "retained scalar snapshots never retain a discarded payload owner");
    check(observed_builder.calls == control_builder.calls, "inspection does not affect future builder/reuse decisions");
}

void old_generation_busy_and_external_only_retired_owner() {
    Pool pool(limits(2, 32), 1); Builder builder;
    auto idle = reserve(pool, request("idle", {16, 0, 0}), builder);
    const auto idle_id = idle.reservation.at(0).id();
    idle.reservation.mark_submitted(); idle.reservation.retire(); idle.reservation = {};
    auto old = reserve(pool, request("old", {16, 0, 0}, 8), builder);
    const auto old_id = old.reservation.at(0).id();
    const auto old_owner = builder.created.back();
    old.reservation.mark_submitted();
    const auto before = inspect(pool, builder);
    pool.invalidate_generation(2);
    const auto invalidated = inspect(pool, builder);
    check(invalidated.count == 1 && row(invalidated, old_id).generation == 1 &&
        row(invalidated, old_id).state == PoolSlotState::Submitted && !contains(invalidated, idle_id),
        "old-generation submitted ownership remains observed and charged after invalidation");
    check(pool.stats().owned_capacity_bytes == 16 && pool.stats().busy_slots == 1,
        "generation change never makes busy capacity free");
    auto fresh = reserve(pool, request("fresh", {16, 0, 0}, 8, 2), builder);
    const auto fresh_id = fresh.reservation.at(0).id();
    const auto mixed = inspect(pool, builder);
    check(fresh_id != old_id && row(mixed, fresh_id).generation == 2 && row(mixed, fresh_id).state == PoolSlotState::Reserved,
        "new generation receives its actual distinct lease metadata");
    old.reservation.retire();
    const auto processed = inspect(pool, builder);
    check(!contains(processed, old_id) && processed.count == 1 && contains(processed, fresh_id),
        "external-only retired old handles are excluded from ledger-owned snapshots");
    check(!old_owner.expired(), "retirement handle still owns its external sentinel independently");
    old.reservation = {};
    check(old_owner.expired() && row(before, old_id).state == PoolSlotState::Submitted,
        "old scalar snapshots do not prolong the external retired owner's lifetime");
    fresh.reservation.rollback(false); fresh.reservation = {};
    check(inspect(pool, builder).count == 0 && pool.stats().owned_capacity_bytes == 0,
        "last release produces an empty actual ledger without retained snapshot ownership");
}
} // namespace

int main() {
    try {
        empty_reserved_submitted_and_bounded_output();
        matched_lifecycle_and_unaffected_idle_control();
        old_generation_busy_and_external_only_retired_owner();
        std::cout << "line pool inspection: " << checks << " checks passed\n";
        return 0;
    } catch (const std::exception& error) {
        allocation_probe::forbidden = false;
        std::cerr << "line pool inspection contract failed after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
