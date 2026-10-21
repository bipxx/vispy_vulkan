#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace vispy::lines {

struct PoolLimits {
    size_t max_slots = 128;
    uint64_t owned_capacity_bytes = 64ull * 1024 * 1024;
    uint64_t control_bytes = 1024 * 1024;
    uint64_t staging_owned_capacity_bytes = 64ull * 1024 * 1024;
    uint64_t staging_control_bytes = 1024 * 1024;
};

struct LeaseCapacities {
    uint64_t output = 0, compute_ubo = 0, render_ubo = 0;
    bool covers(const LeaseCapacities& value) const noexcept {
        return output >= value.output && compute_ubo >= value.compute_ubo && render_ubo >= value.render_ubo;
    }
    friend bool operator==(const LeaseCapacities&, const LeaseCapacities&) = default;
};

struct LeaseRequest {
    uint64_t generation = 0;
    std::string_view affinity;
    LeaseCapacities capacities;
    // An upper bound for retained dynamic Payload control storage, including
    // both UBO byte shadows and bind-key/weak-reference vector capacities.
    // The runtime must not grow that storage beyond this reserved capacity.
    uint64_t extra_control_bytes = 0;
};

struct SlotPlan {
    uint64_t slot_id = 0, generation = 0;
    std::string_view affinity;
    LeaseCapacities capacities;
    uint64_t extra_control_bytes = 0;
};

template<class Payload> struct BuiltPoolPayload {
    Payload payload;
    // Actual dynamic control capacity constructed by the builder. It must fit
    // SlotPlan::extra_control_bytes, which remains the charged upper bound.
    // Native buffer sizes must likewise fit SlotPlan::capacities; the caller
    // applies alignment/padding before requesting these logical capacities.
    uint64_t extra_control_bytes = 0;
};

enum class ReservationStatus { Ready, Unavailable };
enum class PoolSlotState { Idle, Reserved, Submitted };

namespace line_pool_detail {
inline uint64_t add(uint64_t left, uint64_t right) {
    if (right > UINT64_MAX - left)
        throw std::overflow_error("lines: resource pool byte accounting overflow");
    return left + right;
}
inline uint64_t multiply(uint64_t left, uint64_t right) {
    if (left && right > UINT64_MAX / left)
        throw std::overflow_error("lines: resource pool control accounting overflow");
    return left * right;
}
inline uint64_t capacity_bytes(const LeaseCapacities& value) {
    return add(add(value.output, value.compute_ubo), value.render_ubo);
}
} // namespace line_pool_detail

// A single-threaded ledger: the runtime calls it under its Engine mutex, never
// from native callbacks. It knows no Dawn handles or borrowed source owners.
// Native bind-key validation/weak-reference pruning belongs to Payload's user.
// Resident budgets include all idle/reserved/submitted slots, including busy
// old generations. Retired external handles are outside the ledger's cache
// budget and must join the runtime's deduplicated live-resource accounting.
// Transactional construction retains old idle victims until publication, but
// new capacities/control have independently declared staging ceilings.
// Control totals charge exact key bytes, sizeof records/control bookkeeping,
// STL capacities and the declared dynamic Payload upper bounds. Allocator
// headers, native driver memory, borrowed resources and thread stack memory
// are outside this logical ownership budget. Builders must not reenter/mutate
// the pool while its transaction is being planned or constructed.
template<class Payload> class LineResourcePool {
    struct Slot;
    struct State;
    using SlotPtr = std::shared_ptr<Slot>;

public:
    struct Stats {
        uint64_t slots = 0, busy_slots = 0, owned_capacity_bytes = 0, control_bytes = 0;
        uint64_t hits = 0, evictions = 0, deferrals = 0;
        // Declared upper bounds encountered during admitted transactions,
        // not measurements of allocator/driver memory or physical peaks.
        uint64_t staging_peak_slots = 0, staging_peak_owned_capacity_bytes = 0, staging_peak_control_bytes = 0;
    };

    class LeaseHandle {
        friend class LineResourcePool;
        SlotPtr slot_;
        uint64_t token_ = 0;
        LeaseHandle(SlotPtr slot, uint64_t token) : slot_(std::move(slot)), token_(token) {}
        void active() const {
            if (!slot_ || slot_->token != token_ || slot_->state == PoolSlotState::Idle)
                throw std::logic_error("lines: stale resource pool lease");
        }
    public:
        LeaseHandle() = default;
        uint64_t id() const noexcept { return slot_ ? slot_->id : 0; }
        uint64_t generation() const noexcept { return slot_ ? slot_->generation : 0; }
        LeaseCapacities capacities() const noexcept { return slot_ ? slot_->capacities : LeaseCapacities{}; }
        uint64_t extra_control_bytes() const noexcept { return slot_ ? slot_->extra_control_bytes : 0; }
        // Observe the actual scalar state even for an external retired owner;
        // this grants no payload access and never activates a stale token.
        PoolSlotState state() const {
            if (!slot_) throw std::logic_error("lines: empty resource pool lease");
            return slot_->state;
        }
        Payload& payload() {
            active();
            if (slot_->state != PoolSlotState::Reserved)
                throw std::logic_error("lines: submitted resource pool payload is immutable until retirement");
            return slot_->payload;
        }
        const Payload& payload() const { active(); return slot_->payload; }
        // Read-only accounting may inspect even a retired external owner. It
        // confers no permission to encode or mutate that slot's native state.
        const Payload& inspect_payload() const {
            if (!slot_) throw std::logic_error("lines: empty resource pool lease");
            return slot_->payload;
        }
    };

    class BatchReservation {
        friend class LineResourcePool;
        std::shared_ptr<State> owner_;
        std::vector<LeaseHandle> handles_;
        bool submitted_ = false, finished_ = false;
        BatchReservation(std::shared_ptr<State> owner, std::vector<LeaseHandle> handles)
            : owner_(std::move(owner)), handles_(std::move(handles)) {}
        void release(bool processed, bool retain_payload) {
            if (finished_) return;
            if (submitted_ != processed)
                throw std::logic_error(processed ? "lines: unsubmitted pool lease cannot retire" :
                    "lines: submitted pool lease requires actual Ticket processing");
            for (const auto& handle : handles_) {
                handle.active();
                if (handle.slot_->state != (processed ? PoolSlotState::Submitted : PoolSlotState::Reserved))
                    throw std::logic_error("lines: pool reservation state mismatch");
            }
            for (const auto& handle : handles_) handle.slot_->state = PoolSlotState::Idle;
            if (owner_) {
                std::erase_if(owner_->slots, [&](const auto& slot) {
                    return slot->state == PoolSlotState::Idle && (slot->generation != owner_->generation ||
                        (!retain_payload && std::any_of(handles_.begin(), handles_.end(),
                            [&](const auto& handle) { return handle.slot_ == slot; })));
                });
            }
            finished_ = true;
        }
        void rollback_noexcept() noexcept {
            if (!submitted_ && !finished_) {
                try { release(false, true); } catch (...) { std::terminate(); }
            }
            // Submitted destruction is deliberately not retirement: the pool
            // keeps those slots busy. The runtime must retain this owner until
            // actual completion/failure processing and explicitly retire it.
        }
    public:
        BatchReservation() = default;
        BatchReservation(const BatchReservation&) = delete;
        BatchReservation& operator=(const BatchReservation&) = delete;
        BatchReservation(BatchReservation&& other) noexcept
            : owner_(std::move(other.owner_)), handles_(std::move(other.handles_)),
              submitted_(other.submitted_), finished_(other.finished_) { other.finished_ = true; }
        BatchReservation& operator=(BatchReservation&& other) noexcept {
            if (this != &other) {
                rollback_noexcept();
                owner_ = std::move(other.owner_); handles_ = std::move(other.handles_);
                submitted_ = other.submitted_; finished_ = other.finished_; other.finished_ = true;
            }
            return *this;
        }
        ~BatchReservation() { rollback_noexcept(); }
        size_t size() const noexcept { return handles_.size(); }
        const LeaseHandle& at(size_t index) const { return handles_.at(index); }
        LeaseHandle& at(size_t index) { return handles_.at(index); }
        bool submitted() const noexcept { return submitted_; }
        bool finished() const noexcept { return finished_; }
        void mark_submitted() {
            if (submitted_ || finished_)
                throw std::logic_error("lines: pool reservation submitted twice or after release");
            for (const auto& handle : handles_) {
                handle.active();
                if (handle.slot_->state != PoolSlotState::Reserved)
                    throw std::logic_error("lines: pool reservation is not reserved");
            }
            for (const auto& handle : handles_) handle.slot_->state = PoolSlotState::Submitted;
            submitted_ = true;
        }
        // A creation/encoding error may poison buffers or bind groups. Drop
        // only this batch's cache owners at the appropriate release boundary;
        // old external handles still retain their native payload for accounting.
        // Submitted failure never permits rollback or early cache removal.
        void rollback(bool retain_payload = true) { release(false, retain_payload); }
        void retire(bool retain_payload = true) { release(true, retain_payload); }
    };

    struct ReserveResult {
        ReservationStatus status = ReservationStatus::Unavailable;
        BatchReservation reservation;
        explicit operator bool() const noexcept { return status == ReservationStatus::Ready; }
    };

    // Value-only diagnostic metadata. No affinity bytes, Payload references or
    // shared native owners escape through this snapshot. External-only retired
    // leases are intentionally outside the pool's retained slot inventory.
    struct SlotSnapshot {
        uint64_t slot_id = 0, generation = 0;
        PoolSlotState state = PoolSlotState::Idle;
        LeaseCapacities capacities;
        uint64_t extra_control_bytes = 0;
        friend bool operator==(const SlotSnapshot&, const SlotSnapshot&) = default;
    };

    struct SlotView {
        uint64_t id, generation;
        std::string_view affinity;
        LeaseCapacities capacities;
        uint64_t extra_control_bytes;
        PoolSlotState state;
        const Payload& payload;
    };

private:
    // Exact byte ownership avoids implementation-defined std::string spare
    // capacities when planning a replacement alongside its old idle owner.
    struct Key {
        std::unique_ptr<char[]> data;
        size_t length = 0;
        Key() = default;
        explicit Key(std::string_view value) : length(value.size()) {
            const auto bytes = line_pool_detail::add(length, 1);
            if (bytes > SIZE_MAX) throw std::overflow_error("lines: resource pool key length overflow");
            data = std::make_unique<char[]>(static_cast<size_t>(bytes));
            if (length) std::memcpy(data.get(), value.data(), length);
            data[length] = 0;
        }
        std::string_view view() const noexcept { return {data.get(), length}; }
        uint64_t bytes() const { return line_pool_detail::add(length, 1); }
        void swap(Key& other) noexcept { data.swap(other.data); std::swap(length, other.length); }
    };
    struct Slot {
        uint64_t id, generation, token = 0;
        Key affinity;
        LeaseCapacities capacities;
        uint64_t extra_control_bytes;
        PoolSlotState state = PoolSlotState::Idle;
        Payload payload;
        Slot(uint64_t identity, uint64_t gen, Key key, LeaseCapacities cap,
             uint64_t extra, Payload value)
            : id(identity), generation(gen), affinity(std::move(key)), capacities(cap),
              extra_control_bytes(extra), payload(std::move(value)) {}
    };
    struct State {
        PoolLimits limits;
        uint64_t generation, next_slot = 1, next_token = 1;
        std::vector<SlotPtr> slots;
        Stats counters;
        State(PoolLimits value, uint64_t gen) : limits(value), generation(gen) {}
    };
    std::shared_ptr<State> state_;
    struct Pending {
        SlotPtr slot;
        Key affinity;
        LeaseCapacities capacities;
        uint64_t extra = 0;
    };
    struct Plan {
        std::vector<Pending> entries;
        std::vector<SlotPtr> kept;
        uint64_t owned = 0, control = 0, new_count = 0;
        uint64_t staging_owned = 0, staging_control = 0;
        uint64_t planning_peak_control = 0;
    };

    static uint64_t base_control() { return sizeof(State) + 2 * sizeof(void*); }
    static uint64_t slot_control(uint64_t key_bytes, uint64_t extra) {
        // Conservative shared-control/lease bookkeeping is charged even idle.
        return line_pool_detail::add(sizeof(Slot) + 2 * sizeof(void*) + sizeof(LeaseHandle) + 4 * sizeof(void*),
            line_pool_detail::add(key_bytes, extra));
    }
    static uint64_t slot_control(const Slot& slot) {
        return slot_control(slot.affinity.bytes(), slot.extra_control_bytes);
    }
    bool suitable(const Slot& slot, const LeaseRequest& request) const noexcept {
        return slot.state == PoolSlotState::Idle && slot.generation == request.generation &&
               slot.capacities.covers(request.capacities) && slot.extra_control_bytes >= request.extra_control_bytes;
    }

    void totals(Plan& plan) const {
        using namespace line_pool_detail;
        plan.owned = 0;
        plan.control = add(base_control(), multiply(plan.kept.size() + plan.new_count, sizeof(SlotPtr)));
        for (const auto& slot : plan.kept) {
            const auto replacement = std::find_if(plan.entries.begin(), plan.entries.end(), [&](const auto& entry) {
                return entry.slot == slot;
            });
            plan.owned = add(plan.owned, capacity_bytes(slot->capacities));
            plan.control = add(plan.control, replacement == plan.entries.end() ? slot_control(*slot) :
                slot_control(replacement->affinity.bytes(), slot->extra_control_bytes));
        }
        plan.staging_owned = 0;
        plan.staging_control = add(sizeof(Plan) + 2 * sizeof(std::vector<SlotPtr>),
            add(multiply(plan.entries.capacity(), sizeof(Pending)),
            add(multiply(plan.kept.capacity(), sizeof(SlotPtr)),
            add(multiply(plan.entries.size(), sizeof(LeaseHandle)),
                multiply(plan.kept.size() + plan.new_count, sizeof(SlotPtr))))));
        for (const auto& entry : plan.entries) {
            plan.staging_control = add(plan.staging_control, entry.affinity.bytes());
            if (entry.slot) continue;
            const uint64_t owned = capacity_bytes(entry.capacities);
            const uint64_t control = slot_control(entry.affinity.bytes(), entry.extra);
            plan.owned = add(plan.owned, owned);
            plan.control = add(plan.control, control);
            plan.staging_owned = add(plan.staging_owned, owned);
            plan.staging_control = add(plan.staging_control, control);
        }
        plan.staging_control = std::max(plan.staging_control, plan.planning_peak_control);
    }

    bool fits(const Plan& plan) const noexcept {
        const auto& limit = state_->limits;
        return plan.kept.size() + plan.new_count <= limit.max_slots &&
            plan.owned <= limit.owned_capacity_bytes && plan.control <= limit.control_bytes &&
            plan.new_count <= limit.max_slots && plan.staging_owned <= limit.staging_owned_capacity_bytes &&
            plan.staging_control <= limit.staging_control_bytes;
    }

    bool prune(Plan& plan) const {
        totals(plan);
        while (!fits(plan)) {
            const auto victim = std::find_if(plan.kept.begin(), plan.kept.end(), [&](const auto& slot) {
                return slot->state == PoolSlotState::Idle && std::none_of(plan.entries.begin(), plan.entries.end(),
                    [&](const auto& entry) { return entry.slot == slot; });
            });
            if (victim == plan.kept.end()) return false;
            plan.kept.erase(victim);
            // Selected idle victims are still owned by State until successful
            // publication. Empty planner membership must not retain obsolete
            // capacity and turn exact fresh feasibility into false busy deferral.
            if (plan.kept.empty()) std::vector<SlotPtr>{}.swap(plan.kept);
            totals(plan);
        }
        return true;
    }

    // Maximum bipartite matching avoids authoring-order false unavailability
    // when one idle slot covers several requests and another is specialized.
    Plan make_plan(std::span<const LeaseRequest> requests, unsigned policy, bool empty = false) const {
        using namespace line_pool_detail;
        Plan plan;
        const auto slots = empty ? 0 : state_->slots.size();
        // Planner heap/control capacity is checked before copying any keys.
        uint64_t workspace = add(sizeof(Plan) + 2 * sizeof(std::vector<size_t>),
            add(multiply(requests.size(), sizeof(Pending)),
                multiply(slots, sizeof(SlotPtr) + sizeof(size_t) + sizeof(uint8_t))));
        for (const auto& request : requests) workspace = add(workspace, add(request.affinity.size(), 1));
        if (workspace > state_->limits.staging_control_bytes)
            throw std::length_error("lines: endpoint batch exceeds resource pool planning-control limit");
        plan.entries.reserve(requests.size());
        if (!empty) plan.kept = state_->slots;
        for (const auto& request : requests)
            plan.entries.push_back({{}, Key(request.affinity), request.capacities, request.extra_control_bytes});
        plan.planning_peak_control = add(sizeof(Plan) + 2 * sizeof(std::vector<size_t>),
            add(multiply(plan.entries.capacity(), sizeof(Pending)),
                multiply(plan.kept.capacity(), sizeof(SlotPtr))));
        for (const auto& entry : plan.entries)
            plan.planning_peak_control = add(plan.planning_peak_control, entry.affinity.bytes());
        if (policy != 2) {
            std::vector<size_t> assigned(slots, requests.size());
            std::vector<uint8_t> visited(slots);
            plan.planning_peak_control = add(plan.planning_peak_control,
                add(multiply(assigned.capacity(), sizeof(size_t)), multiply(visited.capacity(), sizeof(uint8_t))));
            if (plan.planning_peak_control > state_->limits.staging_control_bytes)
                throw std::length_error("lines: resource pool planner capacity exceeds staging limit");
            // The recursive augmenting search uses no per-call heap storage;
            // visited slot indices bound its depth by the declared slot count.
            auto match = [&](auto&& self, size_t request) -> bool {
                for (unsigned pass = 0; pass != (policy == 1 ? 2u : 1u); ++pass) {
                    for (size_t index = 0; index < slots; ++index) {
                        const auto& slot = *state_->slots[index];
                        const bool exact = slot.affinity.view() == requests[request].affinity;
                        if (visited[index] || !suitable(slot, requests[request]) || exact != (pass == 0)) continue;
                        visited[index] = true;
                        if (assigned[index] == requests.size() || self(self, assigned[index])) {
                            assigned[index] = request; return true;
                        }
                    }
                }
                return false;
            };
            for (size_t request = 0; request < requests.size(); ++request) {
                std::fill(visited.begin(), visited.end(), uint8_t{0});
                match(match, request);
            }
            for (size_t index = 0; index < assigned.size(); ++index)
                if (assigned[index] != requests.size()) plan.entries[assigned[index]].slot = state_->slots[index];
        }
        for (const auto& entry : plan.entries) if (!entry.slot) ++plan.new_count;
        return plan;
    }

public:
    explicit LineResourcePool(PoolLimits limits = {}, uint64_t generation = 0)
        : state_(std::make_shared<State>(limits, generation)) {
        if (!limits.max_slots || !limits.owned_capacity_bytes || limits.control_bytes < base_control() ||
                !limits.staging_owned_capacity_bytes || !limits.staging_control_bytes ||
                limits.staging_owned_capacity_bytes > limits.owned_capacity_bytes ||
                limits.staging_control_bytes > limits.control_bytes)
            throw std::invalid_argument("lines: invalid resource pool resident/staging limits");
    }
    LineResourcePool(const LineResourcePool&) = delete;
    LineResourcePool& operator=(const LineResourcePool&) = delete;
    LineResourcePool(LineResourcePool&&) noexcept = default;
    LineResourcePool& operator=(LineResourcePool&&) noexcept = default;
    PoolLimits limits() const noexcept { return state_->limits; }
    uint64_t generation() const noexcept { return state_->generation; }
    Stats stats() const {
        using namespace line_pool_detail;
        Stats result = state_->counters;
        result.slots = state_->slots.size(); result.busy_slots = 0; result.owned_capacity_bytes = 0;
        result.control_bytes = add(base_control(), multiply(state_->slots.capacity(), sizeof(SlotPtr)));
        for (const auto& slot : state_->slots) {
            result.busy_slots += slot->state != PoolSlotState::Idle;
            result.owned_capacity_bytes = add(result.owned_capacity_bytes, capacity_bytes(slot->capacities));
            result.control_bytes = add(result.control_bytes, slot_control(*slot));
        }
        return result;
    }
    // Diagnostic callers use the same Engine mutex as every pool operation.
    // The caller owns and accounts for its output storage; these observations
    // do not allocate, reserve, poll callbacks, update counters or retire work.
    size_t slot_snapshot_count() const noexcept { return state_->slots.size(); }
    size_t snapshot_slots(std::span<SlotSnapshot> destination) const {
        const auto count = state_->slots.size();
        if (destination.size() < count)
            throw std::length_error("lines: resource pool snapshot destination is too small");
        // Membership order is stable between mutations. Iteration is bounded
        // by the declared max_slots, and excess caller rows remain untouched.
        for (size_t index = 0; index < count; ++index) {
            const auto& slot = *state_->slots[index];
            destination[index] = {slot.id, slot.generation, slot.state,
                                  slot.capacities, slot.extra_control_bytes};
        }
        return count;
    }

    template<class Call> void for_each_slot(Call&& call) const {
        for (const auto& slot : state_->slots)
            call(SlotView{slot->id, slot->generation, slot->affinity.view(), slot->capacities,
                          slot->extra_control_bytes, slot->state, slot->payload});
    }
    void invalidate_generation(uint64_t next) {
        if (!next || next < state_->generation)
            throw std::invalid_argument("lines: resource pool generation must be positive and monotonic");
        if (next == state_->generation) return;
        state_->generation = next;
        std::erase_if(state_->slots, [](const auto& slot) { return slot->state == PoolSlotState::Idle; });
    }

    template<class Builder> ReserveResult reserve_batch(std::span<const LeaseRequest> requests, Builder&& builder) {
        using namespace line_pool_detail;
        if (requests.empty()) return {ReservationStatus::Ready, BatchReservation(state_, {})};
        if (requests.size() > state_->limits.max_slots)
            throw std::length_error("lines: endpoint batch exceeds resource pool slot limit");
        // Reject absurd counts/keys/control before copying strings or invoking
        // a native builder. Checked sums also distinguish overflow from busy.
        uint64_t minimum_control = add(base_control(), multiply(requests.size(),
            sizeof(SlotPtr) + sizeof(Slot) + 2 * sizeof(void*) + sizeof(LeaseHandle) + 4 * sizeof(void*)));
        uint64_t minimum_owned = 0;
        for (const auto& request : requests) {
            if (!request.generation || request.generation != state_->generation)
                throw std::invalid_argument("lines: resource pool request has stale device generation");
            minimum_owned = add(minimum_owned, capacity_bytes(request.capacities));
            minimum_control = add(minimum_control, add(add(request.affinity.size(), 1), request.extra_control_bytes));
        }
        if (minimum_owned > state_->limits.owned_capacity_bytes || minimum_control > state_->limits.control_bytes)
            throw std::length_error("lines: endpoint batch permanently exceeds resource pool byte/control limits");
        // An empty pool must be able to admit the batch. This is the permanent
        // check; existing busy owners can only produce Unavailable afterward.
        {
            Plan fresh = make_plan(requests, 2, true);
            totals(fresh);
            if (!fits(fresh))
                throw std::length_error("lines: endpoint batch permanently exceeds resource pool staging/control limits");
        }

        // Preserve A/B affinity owners while space permits. Under pressure,
        // repurpose idle suitable capacities, then replace oversized idle
        // victims with exact fresh capacities rather than falsely reject.
        auto unavailable = [&]() -> ReserveResult {
            if (std::none_of(state_->slots.begin(), state_->slots.end(),
                    [](const auto& slot) { return slot->state != PoolSlotState::Idle; }))
                throw std::length_error("lines: resource pool planning capacity cannot admit idle replacement");
            state_->counters.deferrals = add(state_->counters.deferrals, 1);
            return {};
        };
        Plan plan = make_plan(requests, 0);
        totals(plan);
        if (!fits(plan)) {
            plan = {};
            plan = make_plan(requests, 1);
            if (!prune(plan)) {
                plan = {};
                plan = make_plan(requests, 2);
                if (!prune(plan)) return unavailable();
            }
        }
        if (plan.new_count > UINT64_MAX - state_->next_slot || state_->next_token == UINT64_MAX)
            throw std::overflow_error("lines: resource pool identity exhausted");

        // Every allocation and builder runs before any existing state changes.
        // The staging bounds include new payload/control plus transaction
        // metadata; old idle victims remain alive until this succeeds.
        std::vector<SlotPtr> next;
        next.reserve(plan.kept.size() + plan.new_count);
        next.insert(next.end(), plan.kept.begin(), plan.kept.end());
        std::vector<LeaseHandle> handles;
        handles.reserve(plan.entries.size());
        // Charge actual STL capacities before invoking any native builder.
        const uint64_t extra_membership = multiply(next.capacity() - (plan.kept.size() + plan.new_count), sizeof(SlotPtr));
        plan.control = add(plan.control, extra_membership);
        plan.staging_control = add(plan.staging_control, add(extra_membership,
            multiply(handles.capacity() - plan.entries.size(), sizeof(LeaseHandle))));
        if (!fits(plan)) return unavailable();
        const uint64_t hits = plan.entries.size() - plan.new_count;
        const uint64_t committed_hits = add(state_->counters.hits, hits);
        const uint64_t committed_evictions = add(state_->counters.evictions, state_->slots.size() - plan.kept.size());
        state_->counters.staging_peak_slots = std::max(state_->counters.staging_peak_slots, plan.new_count);
        state_->counters.staging_peak_owned_capacity_bytes =
            std::max(state_->counters.staging_peak_owned_capacity_bytes, plan.staging_owned);
        state_->counters.staging_peak_control_bytes =
            std::max(state_->counters.staging_peak_control_bytes, plan.staging_control);
        uint64_t next_id = state_->next_slot;
        const uint64_t token = state_->next_token;
        for (auto& entry : plan.entries) {
            if (!entry.slot) {
                const SlotPlan descriptor{next_id, state_->generation, entry.affinity.view(), entry.capacities, entry.extra};
                auto built = builder(descriptor);
                if (built.extra_control_bytes > descriptor.extra_control_bytes)
                    throw std::length_error("lines: resource pool builder exceeded declared dynamic control capacity");
                entry.slot = std::make_shared<Slot>(next_id++, state_->generation, std::move(entry.affinity),
                    entry.capacities, entry.extra, std::move(built.payload));
                next.push_back(entry.slot);
            }
            handles.push_back(LeaseHandle(entry.slot, token));
        }
        // From here publication is only noexcept key/vector swaps and
        // scalar changes. No failed builder can evict/rekey/reserve old slots.
        for (auto& entry : plan.entries) {
            if (entry.slot->id < state_->next_slot) entry.slot->affinity.swap(entry.affinity);
            entry.slot->token = token;
            entry.slot->state = PoolSlotState::Reserved;
        }
        state_->counters.hits = committed_hits;
        state_->counters.evictions = committed_evictions;
        state_->next_slot = next_id; ++state_->next_token;
        state_->slots.swap(next);
        return {ReservationStatus::Ready, BatchReservation(state_, std::move(handles))};
    }
};

} // namespace vispy::lines
