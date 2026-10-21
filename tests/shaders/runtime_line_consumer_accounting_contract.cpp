#include "runtime_line_consumer_accounting.hpp"

#include <algorithm>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using vispy::lines::LineDeviceDescriptorAccounting;

namespace {
size_t checks = 0;
void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
template <class Operation>
void refuses(Operation&& operation, const char* message) {
    bool refused = false;
    try { operation(); } catch (const std::invalid_argument&) { refused = true; }
    require(refused, message);
}

// Actual production accounting helper with synthetic identity/descriptor
// facts. No native module, shader compiler, hardware allocation or Ticket is
// created. Snapshot/Ticket routes below are strong CPU owner vectors only.
struct Record { size_t payload; };
struct Artifact { size_t exclusive; std::vector<std::shared_ptr<Record>> records; };
using Accounting = LineDeviceDescriptorAccounting;
constexpr size_t control = 2 * sizeof(void*);
constexpr size_t maximum = std::numeric_limits<size_t>::max();
void gather(Accounting& account, const std::shared_ptr<Artifact>& artifact, bool cached) {
    size_t total = artifact->exclusive;
    for (const auto& record : artifact->records) total += record->payload + control;
    account.observe_artifact(artifact.get(), cached, total);
    for (const auto& record : artifact->records) {
        account.observe_record(record.get(), record->payload, control);
        account.contains(artifact.get(), record.get());
    }
}
void empty_unique_and_cached_upgrade() {
    Accounting account;
    auto empty = account.finish();
    require(empty.live_bytes == 0 && empty.artifact_count == 0 && empty.record_count == 0 && !empty.saturated,
            "empty observation has exact zero footprint");
    int a, b, r;
    account.observe_artifact(&a, false, 120 + control);
    account.observe_record(&r, 20, control);
    account.contains(&a, &r);
    account.observe_artifact(&b, false, 300);
    auto before = account.finish();
    require(before.uncached_container_bytes == 400 && before.uncached_record_bytes == 20 + control &&
            before.uncached_bytes == 420 + control && before.cached_bytes == 0,
            "unique external containers and records partition their actual descriptor costs");
    account.observe_artifact(&a, true, 120 + control);
    account.observe_artifact(&a, false, 120 + control);
    account.observe_record(&r, 20, control);
    account.contains(&a, &r);
    auto after = account.finish();
    require(after.cached_container_bytes == 100 && after.cached_record_bytes == 20 + control &&
            after.cached_bytes == 120 + control && after.uncached_bytes == 300 &&
            after.live_bytes == before.live_bytes, "cached upgrade never duplicates or downgrades an observed owner");
    require(after.artifact_count == 2 && after.cached_artifact_count == 1 &&
            after.uncached_artifact_count == 1 && after.record_count == 1 && after.cached_record_count == 1,
            "duplicate observations and containment edges preserve exact unique counts");
}
void mixed_snapshot_ticket_order() {
    auto record = std::make_shared<Record>(Record{80});
    auto snapshot_artifact = std::make_shared<Artifact>(Artifact{100, {}});
    auto ticket_artifact = std::make_shared<Artifact>(Artifact{200, {record}});
    std::vector<std::shared_ptr<Record>> snapshots{record};
    std::vector<std::shared_ptr<Artifact>> tickets{ticket_artifact};
    std::vector<int> order{0, 1, 2};
    do {
        Accounting account;
        for (int route : order) {
            if (route == 0) gather(account, snapshot_artifact, false);
            if (route == 1) account.observe_record(snapshots[0].get(), snapshots[0]->payload, control);
            if (route == 2) gather(account, tickets[0], false);
        }
        auto result = account.finish();
        require(result.uncached_container_bytes == 300 && result.uncached_record_bytes == 80 + control &&
                result.live_bytes == 380 + control && result.cached_bytes == 0,
                "snapshot-first versus Ticket-Artifact-first charges the shared allocation exactly once");
        require(result.artifact_count == 2 && result.record_count == 1 && result.uncached_record_count == 1,
                "mixed route observation is independent of every traversal order");
    } while (std::next_permutation(order.begin(), order.end()));
}
void shared_cached_and_external_containers() {
    auto record = std::make_shared<Record>(Record{80});
    auto a = std::make_shared<Artifact>(Artifact{100, {record}});
    auto b = std::make_shared<Artifact>(Artifact{200, {record}});
    for (bool reverse : {false, true}) {
        Accounting account;
        gather(account, reverse ? b : a, false);
        gather(account, reverse ? a : b, false);
        auto external = account.finish();
        require(external.uncached_container_bytes == 300 && external.live_bytes == 380 + control &&
                external.record_count == 1, "two unresident Artifact containers share one record payload/control cost");
        gather(account, b, true);
        auto mixed = account.finish();
        require(mixed.cached_bytes == 280 + control && mixed.uncached_bytes == 100 &&
                mixed.live_bytes == external.live_bytes && mixed.cached_record_count == 1,
                "a record shared with a cached container belongs once to the cached class");
        gather(account, a, true);
        auto cached = account.finish();
        require(cached.cached_container_bytes == 300 && cached.cached_record_bytes == 80 + control &&
                cached.cached_bytes == 380 + control && cached.uncached_bytes == 0,
                "distinct resident map/FIFO residuals remain while shared record storage deduplicates");
    }
}
void detached_owner_lifetime_and_new_observation() {
    auto selected = std::make_shared<Record>(Record{80});
    auto unrelated = std::make_shared<Record>(Record{40});
    auto artifact = std::make_shared<Artifact>(Artifact{150, {selected, unrelated}});
    std::vector<std::shared_ptr<Record>> queued{selected, unrelated, selected};
    auto submitted = queued;
    Accounting before;
    gather(before, artifact, true);
    auto resident = before.finish();
    require(resident.cached_bytes == 270 + 2 * control && resident.record_count == 2,
            "resident synthetic A/B/A owners share their container's two allocations");
    artifact->records.erase(artifact->records.begin());
    Accounting after;
    gather(after, artifact, true);
    for (const auto& owner : submitted) after.observe_record(owner.get(), owner->payload, control);
    auto detached = after.finish();
    require(detached.cached_bytes == 190 + control && detached.uncached_record_bytes == 80 + control &&
            detached.live_bytes == resident.live_bytes && detached.uncached_record_count == 1,
            "detached record stays charged once through queued/submitted owner routes");
    std::weak_ptr<Record> weak = selected;
    selected.reset(); queued.clear();
    require(!weak.expired(), "metadata gathering cannot replace submitted ownership");
    submitted.clear();
    require(weak.expired(), "borrowed accounting facts never retain a retired external record");
    after.clear();
    gather(after, artifact, true);
    require(after.finish().live_bytes == 190 + control && after.finish().record_count == 1,
            "fresh observation releases retired facts and retains unaffected record charges");
}
void identity_cost_and_edge_refusals() {
    Accounting account;
    int a, b, r, s;
    refuses([&] { account.observe_artifact(nullptr, false, 1); }, "null Artifact identity refuses");
    refuses([&] { account.observe_record(nullptr, 1); }, "null record identity refuses");
    account.observe_artifact(&a, true, 120 + control);
    account.observe_record(&r, 20, control);
    refuses([&] { account.observe_artifact(&a, false, 121 + control); }, "same Artifact identity cannot change cost");
    refuses([&] { account.observe_record(&r, 21, control - 1); },
            "same total with different payload/control identity still refuses");
    refuses([&] { account.contains(&b, &r); }, "missing Artifact endpoint refuses");
    refuses([&] { account.contains(&a, &s); }, "missing record endpoint refuses");
    account.contains(&a, &r); account.contains(&a, &r);
    require(account.finish().cached_container_bytes == 100, "duplicate containment cannot subtract twice");
    Accounting omitted;
    omitted.observe_artifact(&a, false, 39 + 2 * control);
    omitted.observe_record(&r, 20, control); omitted.observe_record(&s, 20, control);
    omitted.contains(&a, &r); omitted.contains(&a, &s);
    refuses([&] { (void)omitted.finish(); }, "finite total below distinct contained contributions refuses underflow");
}
void saturated_ownership_classes() {
    int a, b, r, s;
    for (bool cached : {false, true}) {
        Accounting total;
        total.observe_artifact(&a, cached, maximum);
        total.observe_record(&r, 20, control); total.contains(&a, &r);
        auto result = total.finish();
        require(result.live_bytes == maximum && result.saturated &&
                (cached ? result.cached_container_bytes : result.uncached_container_bytes) == maximum,
                "saturated total cannot become finite after subtraction");
        Accounting payload;
        payload.observe_record(&r, maximum, control);
        if (cached) { payload.observe_artifact(&a, true, maximum); payload.contains(&a, &r); }
        auto record = payload.finish();
        require(record.live_bytes == maximum && record.saturated &&
                (cached ? record.cached_record_bytes : record.uncached_record_bytes) == maximum,
                "saturated record preserves its final ownership class");
    }
    Accounting missing;
    missing.observe_artifact(&a, false, 100);
    missing.observe_record(&r, maximum, control); missing.contains(&a, &r);
    refuses([&] { (void)missing.finish(); }, "finite total cannot cover a saturated record");
    Accounting control_overflow;
    control_overflow.observe_record(&r, maximum - 4, 8);
    require(control_overflow.finish().uncached_bytes == maximum,
            "shared-owner metadata addition saturates rather than wraps");
    Accounting class_sum;
    class_sum.observe_artifact(&a, true, maximum - 1);
    class_sum.observe_artifact(&b, true, 2);
    require(class_sum.finish().cached_bytes == maximum && class_sum.finish().uncached_bytes == 0,
            "multiple finite cached containers saturate their class sum");
    Accounting live_sum;
    live_sum.observe_artifact(&a, true, maximum - 1); live_sum.observe_record(&s, 2, 0);
    auto result = live_sum.finish();
    require(result.cached_bytes == maximum - 1 && result.uncached_bytes == 2 &&
            result.live_bytes == maximum && result.saturated,
            "live total saturates while finite ownership classes remain separately visible");
}
}  // namespace

int main() {
    try {
        empty_unique_and_cached_upgrade();
        mixed_snapshot_ticket_order();
        shared_cached_and_external_containers();
        detached_owner_lifetime_and_new_observation();
        identity_cost_and_edge_refusals();
        saturated_ownership_classes();
        std::cout << "runtime line consumer accounting contract: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "runtime line consumer accounting contract failed after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
