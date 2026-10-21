#include "runtime_line_ownership.hpp"
#include "runtime_frame_lifecycle.hpp"

#include <array>
#include <iostream>
#include <limits>
#include <memory>
#include <memory_resource>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <type_traits>
#include <utility>

namespace {
using namespace vispy::lines;
using Snapshot = LineOwnershipSnapshot;
unsigned checks = 0;

void check(bool condition, const char* message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}

template<class Error, class Function>
void rejects(Function&& function, const char* message) {
    bool caught = false;
    try { function(); } catch (const Error&) { caught = true; }
    check(caught, message);
}

// Detects accidental PMR default-resource use. It remains a functioning
// upstream so an incorrect allocator reaches an explicit assertion rather
// than obscuring the actual arena-exhaustion assertion with another failure.
struct DefaultGuard final : std::pmr::memory_resource {
    size_t allocations = 0, deallocations = 0;
    std::pmr::memory_resource* previous = nullptr;
    DefaultGuard() : previous(std::pmr::set_default_resource(this)) {}
    ~DefaultGuard() override { std::pmr::set_default_resource(previous); }
    void* do_allocate(size_t bytes, size_t alignment) override {
        ++allocations;
        return std::pmr::new_delete_resource()->allocate(bytes, alignment);
    }
    void do_deallocate(void* pointer, size_t bytes, size_t alignment) override {
        ++deallocations;
        std::pmr::new_delete_resource()->deallocate(pointer, bytes, alignment);
    }
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
        return this == &other;
    }
};

static_assert(!std::is_copy_constructible_v<Snapshot>);
static_assert(!std::is_copy_assignable_v<Snapshot>);
static_assert(std::is_nothrow_move_constructible_v<Snapshot>);
static_assert(!std::is_move_assignable_v<Snapshot>);
static_assert(!std::is_default_constructible_v<OwnershipTicket>);
static_assert(!std::is_default_constructible_v<OwnershipQueuedBatch>);
static_assert(!std::is_default_constructible_v<OwnershipCapture>);
static_assert(!std::is_default_constructible_v<OwnershipFrame>);
static_assert(!std::is_copy_constructible_v<OwnershipTicket>);
static_assert(!std::is_copy_constructible_v<OwnershipQueuedBatch>);
static_assert(!std::is_copy_constructible_v<OwnershipCapture>);
static_assert(!std::is_copy_constructible_v<OwnershipFrame>);
static_assert(std::uses_allocator_v<OwnershipTicket, std::pmr::polymorphic_allocator<OwnershipTicket>>);
static_assert(std::uses_allocator_v<OwnershipQueuedBatch, std::pmr::polymorphic_allocator<OwnershipQueuedBatch>>);
static_assert(std::uses_allocator_v<OwnershipCapture, std::pmr::polymorphic_allocator<OwnershipCapture>>);
static_assert(std::uses_allocator_v<OwnershipFrame, std::pmr::polymorphic_allocator<OwnershipFrame>>);
static_assert(std::is_trivially_copyable_v<OwnershipSlot>);
static_assert(std::is_trivially_copyable_v<OwnershipQuerySegment>);
static_assert(std::is_trivially_copyable_v<OwnershipPoolStats>);
static_assert(std::is_trivially_copyable_v<OwnershipCounters>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipTicket>().slot_ids), std::pmr::vector<uint64_t>>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipQueuedBatch>().capture_ids), std::pmr::vector<uint64_t>>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipTicket>().error), std::pmr::string>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipTicket>().validation_error), std::pmr::string>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipCapture>().status), std::pmr::string>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipCapture>().error), std::pmr::string>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipFrame>().failure), std::pmr::string>);
static_assert(std::is_same_v<decltype(std::declval<OwnershipFrame>().error), std::pmr::string>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().slots), std::pmr::vector<OwnershipSlot>>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().external_slots), std::pmr::vector<OwnershipSlot>>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().tickets), std::pmr::vector<OwnershipTicket>>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().queued), std::pmr::vector<OwnershipQueuedBatch>>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().captures), std::pmr::vector<OwnershipCapture>>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().query_segments), std::pmr::vector<OwnershipQuerySegment>>);
static_assert(std::is_same_v<decltype(std::declval<Snapshot>().frames), std::pmr::vector<OwnershipFrame>>);

void allocator_routes(const Snapshot& snapshot) {
    auto* memory = snapshot.memory_resource();
    check(snapshot.slots.get_allocator().resource() == memory, "slots use snapshot arena");
    check(snapshot.external_slots.get_allocator().resource() == memory, "external slots use snapshot arena");
    check(snapshot.tickets.get_allocator().resource() == memory, "Tickets use snapshot arena");
    check(snapshot.queued.get_allocator().resource() == memory, "queued batches use snapshot arena");
    check(snapshot.captures.get_allocator().resource() == memory, "captures use snapshot arena");
    check(snapshot.query_segments.get_allocator().resource() == memory, "query segments use snapshot arena");
    check(snapshot.frames.get_allocator().resource() == memory, "frames use snapshot arena");
    for (const auto& row : snapshot.tickets) {
        check(row.slot_ids.get_allocator().resource() == memory, "nested Ticket IDs use snapshot arena");
        check(row.error.get_allocator().resource() == memory, "Ticket errors use snapshot arena");
        check(row.validation_error.get_allocator().resource() == memory, "validation errors use snapshot arena");
    }
    for (const auto& row : snapshot.queued)
        check(row.capture_ids.get_allocator().resource() == memory, "nested queued capture IDs use snapshot arena");
    for (const auto& row : snapshot.captures) {
        check(row.status.get_allocator().resource() == memory, "capture statuses use snapshot arena");
        check(row.error.get_allocator().resource() == memory, "capture errors use snapshot arena");
    }
    for (const auto& row : snapshot.frames) {
        check(row.failure.get_allocator().resource() == memory, "frame failures use snapshot arena");
        check(row.error.get_allocator().resource() == memory, "frame errors use snapshot arena");
    }
}

void small_rows(Snapshot& snapshot, uint64_t identity) {
    snapshot.canvas_id = 41;
    snapshot.generation = 7;
    snapshot.slots.push_back({identity, 7, PoolSlotState::Submitted, {4096, 256, 256}, 128});
    snapshot.external_slots.push_back({identity + 1, 6, PoolSlotState::Submitted, {1024, 128, 128}, 64});
    auto& ticket = snapshot.tickets.emplace_back();
    ticket.canvas_id = 41; ticket.ticket_id = identity; ticket.generation = 7;
    ticket.frame_id = identity + 2; ticket.paint_token = identity + 3;
    ticket.slot_ids = {identity, identity + 1};
    ticket.error.assign(80, 't'); ticket.validation_error.assign(96, 'v');
    auto& queued = snapshot.queued.emplace_back();
    queued.queue_id = identity + 4; queued.generation = 7;
    queued.capture_ids = {identity + 5, identity + 6};
    auto& capture = snapshot.captures.emplace_back();
    capture.canvas_id = 41; capture.capture_id = identity + 5; capture.ticket_id = identity;
    capture.frame_id = identity + 2; capture.paint_token = identity + 3;
    capture.generation = 7; capture.charged_bytes = 512; capture.readback_capacity = 128;
    capture.status.assign(64, 's'); capture.error.assign(128, 'e');
    OwnershipQuerySegment segment;
    segment.canvas_id = 41; segment.ticket_id = identity; segment.generation = 7;
    segment.frame_id = identity + 2; segment.paint_token = identity + 3;
    segment.map_requested = true; segment.resolve_capacity = segment.readback_capacity = 48;
    snapshot.query_segments.push_back(segment);
    auto& frame = snapshot.frames.emplace_back();
    frame.frame_id = identity + 2; frame.paint_token = identity + 3; frame.generation = 7;
    frame.failure.assign(64, 'f'); frame.error.assign(160, 'x');
}

void hard_arena_and_failure_preservation() {
    DefaultGuard guard;
    {
        Snapshot snapshot;
        auto* arena = dynamic_cast<std::pmr::monotonic_buffer_resource*>(snapshot.memory_resource());
        check(arena != nullptr, "actual resource is the declared monotonic arena");
        check(arena->upstream_resource() == std::pmr::null_memory_resource(), "null upstream forbids fallback");
        check(snapshot.allocated_control_bytes() <= Snapshot::max_control_bytes,
            "arena and fixed metadata fit hard logical allocation ceiling");
        small_rows(snapshot, 101);
        allocator_routes(snapshot);
        const auto* ids = snapshot.tickets.front().slot_ids.data();
        const auto* error = snapshot.captures.front().error.data();
        const auto capacity = snapshot.control_capacity_bytes();
        rejects<std::bad_alloc>([&] { (void)snapshot.memory_resource()->allocate(Snapshot::max_control_bytes, alignof(std::max_align_t)); },
            "oversized raw arena allocation rejects without fallback");
        check(snapshot.control_capacity_bytes() == capacity && snapshot.tickets.front().slot_ids.data() == ids &&
            snapshot.captures.front().error.data() == error, "failed allocation preserves published value storage");
        rejects<std::bad_alloc>([&] { snapshot.tickets.front().error.reserve(Snapshot::max_control_bytes); },
            "nested string exhaustion rejects without fallback");
        check(snapshot.tickets.front().error.size() == 80 && snapshot.tickets.front().error.front() == 't',
            "failed string growth preserves prior error");
        rejects<std::bad_alloc>([&] { snapshot.queued.front().capture_ids.reserve(Snapshot::max_control_bytes); },
            "nested ID exhaustion rejects without fallback");
        check(snapshot.queued.front().capture_ids.size() == 2 && snapshot.queued.front().capture_ids[1] == 107,
            "failed nested ID growth preserves prior identities");
        rejects<std::bad_alloc>([&] { snapshot.frames.reserve(Snapshot::max_control_bytes); },
            "outer row exhaustion rejects without fallback");
        check(snapshot.frames.size() == 1 && snapshot.frames.front().frame_id == 103,
            "failed outer growth preserves prior frame");
        size_t chunks = 0;
        for (;;) {
            try {
                (void)snapshot.memory_resource()->allocate(4096, alignof(std::max_align_t));
                ++chunks;
                check(chunks <= Snapshot::max_control_bytes / 4096, "cumulative arena use cannot escape hard ceiling");
            } catch (const std::bad_alloc&) { break; }
        }
        check(chunks != 0 && chunks < Snapshot::max_control_bytes / 4096, "real arena exhaustion reached");
        rejects<std::bad_alloc>([&] { (void)snapshot.memory_resource()->allocate(4096, alignof(std::max_align_t)); },
            "exhausted arena remains non-fallback");
        allocator_routes(snapshot);
        check(snapshot.tickets.front().ticket_id == 101 && snapshot.captures.front().error.size() == 128,
            "exhaustion never fabricates or discards prior metadata");
        check(guard.allocations == 0 && guard.deallocations == 0, "no default PMR fallback during exhaustion");
    }
    check(guard.allocations == 0 && guard.deallocations == 0, "snapshot destruction needs no default PMR owner");
}

void maximum_rows_and_exact_scalar_bits() {
    DefaultGuard guard;
    {
        Snapshot snapshot;
        snapshot.slots.resize(Snapshot::max_pool_slots);
        snapshot.external_slots.resize(Snapshot::max_external_slots);
        snapshot.tickets.reserve(Snapshot::max_frame_slots);
        snapshot.queued.reserve(Snapshot::max_frame_slots);
        snapshot.captures.reserve(Snapshot::max_captures);
        snapshot.query_segments.resize(Snapshot::max_query_segments);
        snapshot.frames.reserve(Snapshot::max_frames);
        for (size_t i = 0; i < Snapshot::max_frame_slots; ++i) {
            auto& ticket = snapshot.tickets.emplace_back();
            ticket.ticket_id = UINT64_MAX - i; ticket.canvas_id = std::numeric_limits<int>::max();
            ticket.slot_ids.resize(Snapshot::max_pool_slots);
            for (size_t j = 0; j < ticket.slot_ids.size(); ++j) ticket.slot_ids[j] = UINT64_MAX - j;
            ticket.error.assign(64, 't'); ticket.validation_error.assign(64, 'v');
            auto& queue = snapshot.queued.emplace_back();
            queue.queue_id = UINT64_MAX - i;
            queue.capture_ids.resize(Snapshot::max_captures);
            for (size_t j = 0; j < queue.capture_ids.size(); ++j) queue.capture_ids[j] = UINT64_MAX - j;
        }
        for (size_t i = 0; i < Snapshot::max_captures; ++i) {
            auto& capture = snapshot.captures.emplace_back();
            capture.capture_id = UINT64_MAX - i;
            capture.status.assign(32, 's'); capture.error.assign(64, 'e');
        }
        for (size_t i = 0; i < Snapshot::max_frames; ++i) {
            auto& frame = snapshot.frames.emplace_back();
            frame.paint_token = UINT64_MAX - i; frame.failure.assign(32, 'f'); frame.error.assign(64, 'x');
        }
        snapshot.tickets.front().error.assign(Snapshot::max_error_bytes, 'T');
        snapshot.tickets.front().validation_error.assign(Snapshot::max_error_bytes, 'V');
        snapshot.captures.front().error.assign(Snapshot::max_error_bytes, 'E');
        snapshot.frames.front().error.assign(Snapshot::max_error_bytes, 'X');
        snapshot.captures.front().error[17] = '\0';
        snapshot.query_segments.back().ticket_id = UINT64_MAX;
        snapshot.query_segments.back().submission_index = UINT32_MAX;
        check(snapshot.slots.size() == Snapshot::max_pool_slots && snapshot.external_slots.size() == Snapshot::max_external_slots,
            "all retained and external slot metadata fit individually declared count bounds");
        check(snapshot.tickets.size() == Snapshot::max_frame_slots && snapshot.queued.size() == Snapshot::max_frame_slots,
            "maximum Ticket and queue rows coexist");
        check(snapshot.captures.size() == Snapshot::max_captures && snapshot.frames.size() == Snapshot::max_frames &&
            snapshot.query_segments.size() == Snapshot::max_query_segments, "maximum capture/frame/query rows coexist");
        allocator_routes(snapshot);
        for (const auto& ticket : snapshot.tickets) {
            check(ticket.ticket_id > (uint64_t{1} << 53), "Ticket IDs never narrow to floating point");
            for (size_t j = 0; j < ticket.slot_ids.size(); ++j)
                check(ticket.slot_ids[j] == UINT64_MAX - j, "nested slot IDs retain all uint64 bits");
        }
        for (const auto& queue : snapshot.queued)
            for (size_t j = 0; j < queue.capture_ids.size(); ++j)
                check(queue.capture_ids[j] == UINT64_MAX - j, "nested capture IDs retain all uint64 bits");
        check(snapshot.query_segments.back().ticket_id == UINT64_MAX && snapshot.query_segments.back().submission_index == UINT32_MAX,
            "query identity and submission index preserve exact integer maxima");
        check(snapshot.captures.front().error.size() == Snapshot::max_error_bytes && snapshot.captures.front().error[17] == '\0',
            "bounded string transport preserves length and embedded zero");
        check(snapshot.control_capacity_bytes() <= snapshot.allocated_control_bytes(),
            "ordinary maximum-count usage fits allocated arena accounting");
        check(guard.allocations == 0, "all maximum-count nested rows avoid default PMR allocation");

        // The row maxima are not a promise that every row can simultaneously
        // carry two 4096-byte strings. The global arena is the ultimate bound.
        bool exhausted = false;
        try {
            for (auto& capture : snapshot.captures) {
                capture.status.assign(Snapshot::max_error_bytes, 's');
                capture.error.assign(Snapshot::max_error_bytes, 'e');
            }
        } catch (const std::bad_alloc&) { exhausted = true; }
        check(exhausted, "simultaneously maximal strings reject at shared arena ceiling");
        check(snapshot.captures.size() == Snapshot::max_captures && snapshot.tickets.front().ticket_id == UINT64_MAX,
            "shared ceiling failure leaves real row identities intact");
        check(guard.allocations == 0 && snapshot.allocated_control_bytes() <= Snapshot::max_control_bytes,
            "maximal strings cannot escape shared control ceiling");
    }
    check(guard.allocations == 0 && guard.deallocations == 0, "maximum rows destroy through owned arena only");
}

void allocator_aware_row_ingress() {
    DefaultGuard guard;
    {
        std::array<std::byte, 128 * 1024> foreign_bytes;
        std::pmr::monotonic_buffer_resource foreign(foreign_bytes.data(), foreign_bytes.size(), std::pmr::null_memory_resource());
        Snapshot snapshot;
        OwnershipTicket ticket(&foreign);
        ticket.ticket_id = UINT64_MAX;
        ticket.slot_ids = {UINT64_MAX, UINT64_MAX - 1, UINT64_MAX - 2};
        ticket.error.assign(512, 't'); ticket.validation_error.assign(768, 'v');
        OwnershipQueuedBatch queue(&foreign);
        queue.queue_id = UINT64_MAX - 3; queue.capture_ids = {UINT64_MAX - 4, UINT64_MAX - 5};
        OwnershipCapture capture(&foreign);
        capture.capture_id = UINT64_MAX - 4; capture.status.assign(512, 's'); capture.error.assign(1024, 'e');
        OwnershipFrame frame(&foreign);
        frame.paint_token = UINT64_MAX - 6; frame.failure.assign(512, 'f'); frame.error.assign(1024, 'x');

        // push_back(lvalue) must use allocator-extended construction even if
        // plain Row copies are prohibited. A default-allocator copy is wrong.
        snapshot.tickets.push_back(ticket);
        snapshot.queued.push_back(queue);
        snapshot.captures.push_back(capture);
        snapshot.frames.push_back(frame);
        allocator_routes(snapshot);
        check(ticket.slot_ids.get_allocator().resource() == &foreign && ticket.error.get_allocator().resource() == &foreign,
            "copy ingress does not reparent the independent source");
        check(snapshot.tickets.front().slot_ids[2] == UINT64_MAX - 2 && snapshot.tickets.front().error.size() == 512 &&
            snapshot.tickets.front().validation_error.size() == 768, "allocator-aware Ticket copy preserves long strings and IDs");
        check(snapshot.queued.front().capture_ids[1] == UINT64_MAX - 5 && snapshot.captures.front().error.size() == 1024 &&
            snapshot.frames.front().paint_token == UINT64_MAX - 6, "allocator-aware row copies preserve exact values");

        // The foreign allocator must not follow the values into the result.
        snapshot.tickets.push_back(std::move(ticket));
        snapshot.queued.push_back(std::move(queue));
        snapshot.captures.push_back(std::move(capture));
        snapshot.frames.push_back(std::move(frame));
        allocator_routes(snapshot);
        for (const auto& row : snapshot.tickets)
            check(row.slot_ids[0] == UINT64_MAX && row.error.size() == 512 && row.validation_error.back() == 'v',
                "foreign move ingress retains exact Ticket values in result arena");
        for (const auto& row : snapshot.queued)
            check(row.capture_ids[0] == UINT64_MAX - 4, "foreign move ingress retains queued IDs");
        for (const auto& row : snapshot.captures)
            check(row.status.size() == 512 && row.error.size() == 1024 && row.error.back() == 'e',
                "foreign move ingress retains non-SSO capture strings");
        for (const auto& row : snapshot.frames)
            check(row.failure.size() == 512 && row.error.size() == 1024 && row.error.back() == 'x',
                "foreign move ingress retains non-SSO frame strings");
        check(guard.allocations == 0, "lvalue and foreign move ingress never use PMR default resource");
    }
    check(guard.allocations == 0 && guard.deallocations == 0, "foreign and result arenas destroy independently");

    {
        auto foreign_bytes = std::make_unique<std::byte[]>(3 * Snapshot::max_control_bytes);
        std::pmr::monotonic_buffer_resource foreign(foreign_bytes.get(), 3 * Snapshot::max_control_bytes,
            std::pmr::null_memory_resource());
        OwnershipTicket oversized(&foreign);
        oversized.ticket_id = UINT64_MAX;
        oversized.slot_ids = {UINT64_MAX, UINT64_MAX - 1};
        oversized.error.assign(Snapshot::max_control_bytes, 'z');
        Snapshot copied;
        small_rows(copied, 301);
        rejects<std::bad_alloc>([&] { copied.tickets.push_back(oversized); },
            "oversized foreign copy cannot bypass destination hard arena");
        check(copied.tickets.size() == 1 && copied.tickets.front().ticket_id == 301 &&
            copied.tickets.front().error.size() == 80, "rejected foreign copy preserves previously published destination row");
        check(oversized.error.size() == Snapshot::max_control_bytes && oversized.slot_ids[0] == UINT64_MAX,
            "rejected lvalue copy preserves source values");
        allocator_routes(copied);
        Snapshot moved;
        small_rows(moved, 401);
        rejects<std::bad_alloc>([&] { moved.tickets.push_back(std::move(oversized)); },
            "oversized foreign move cannot import foreign storage past destination ceiling");
        check(moved.tickets.size() == 1 && moved.tickets.front().ticket_id == 401 &&
            moved.tickets.front().slot_ids[1] == 402, "rejected foreign move preserves existing destination identities");
        allocator_routes(moved);
        check(guard.allocations == 0 && copied.allocated_control_bytes() <= Snapshot::max_control_bytes &&
            moved.allocated_control_bytes() <= Snapshot::max_control_bytes, "foreign oversize failures have no fallback allocation");
    }
    check(guard.allocations == 0 && guard.deallocations == 0, "foreign oversize failures destroy without external PMR fallback");
}

Snapshot force_return_move(std::pmr::memory_resource*& resource, const uint64_t*& ids) {
    Snapshot source;
    small_rows(source, 501);
    resource = source.memory_resource();
    ids = source.tickets.front().slot_ids.data();
    return Snapshot(std::move(source)); // Force the actual move rather than rely on NRVO.
}

void move_return_and_destruction_orders() {
    DefaultGuard guard;
    std::pmr::memory_resource* resource = nullptr;
    const uint64_t* ids = nullptr;
    {
        auto returned = force_return_move(resource, ids);
        check(returned.memory_resource() == resource, "returned result retains original arena identity");
        check(returned.tickets.front().slot_ids.data() == ids && ids[0] == 501 && ids[1] == 502,
            "nested ID storage survives destruction of return source");
        allocator_routes(returned);
        Snapshot moved(std::move(returned));
        check(moved.memory_resource() == resource && moved.captures.front().error.size() == 128,
            "second move preserves arena and nested string lifetime");
        allocator_routes(moved);
    }
    // Destination destruction before the moved-from source is a different
    // order from a return. Empty moved-from vectors must not deallocate
    // through the destination's already-destroyed arena.
    {
        std::optional<Snapshot> source;
        source.emplace();
        small_rows(*source, 701);
        auto destination = std::make_unique<Snapshot>(std::move(*source));
        check(destination->tickets.front().slot_ids.front() == 701, "heap destination owns exact metadata");
        destination.reset();
        source.reset();
        check(guard.allocations == 0 && guard.deallocations == 0,
            "destination-before-source destruction has no default or external arena use");
    }
    // No Snapshot operation is permitted on a moved-from result except its
    // destruction. In particular memory_resource() is not called on it.
    check(guard.allocations == 0 && guard.deallocations == 0, "moves never reparent nested containers to default PMR");
}

void value_only_metadata_cannot_retain_native_owner() {
    DefaultGuard guard;
    Snapshot snapshot;
    std::weak_ptr<uint64_t> weak;
    {
        auto otherwise_native_owner = std::make_shared<uint64_t>(991);
        weak = otherwise_native_owner;
        small_rows(snapshot, *otherwise_native_owner);
    }
    check(weak.expired(), "scalar observer metadata does not retain the represented owner");
    check(snapshot.tickets.front().ticket_id == 991 && snapshot.slots.front().slot_id == 991,
        "owner release cannot invalidate independently copied scalar observations");
    // Compile-time exact field/container types above supplement this lifetime
    // test. This target includes no Dawn/resource payload or engine callback.
    allocator_routes(snapshot);
    check(guard.allocations == 0, "value-only observation has no hidden PMR default owner");
}

struct LedgerPayload {
    std::shared_ptr<uint64_t> owner;
};
using Ledger = LineResourcePool<LedgerPayload>;
struct LedgerBuilder {
    uint64_t calls = 0;
    std::vector<std::weak_ptr<uint64_t>> created;
    BuiltPoolPayload<LedgerPayload> operator()(const SlotPlan& plan) {
        auto owner = std::make_shared<uint64_t>(++calls);
        created.push_back(owner);
        return {LedgerPayload{std::move(owner)}, plan.extra_control_bytes};
    }
};

void equal_stats(const Ledger::Stats& left, const Ledger::Stats& right) {
    check(left.slots == right.slots && left.busy_slots == right.busy_slots, "state inspection preserves membership and busy counts");
    check(left.owned_capacity_bytes == right.owned_capacity_bytes && left.control_bytes == right.control_bytes,
        "state inspection preserves charged capacities");
    check(left.hits == right.hits && left.evictions == right.evictions && left.deferrals == right.deferrals,
        "state inspection preserves cumulative policy counters");
    check(left.staging_peak_slots == right.staging_peak_slots &&
        left.staging_peak_owned_capacity_bytes == right.staging_peak_owned_capacity_bytes &&
        left.staging_peak_control_bytes == right.staging_peak_control_bytes, "state inspection preserves staging observations");
}

void inspect_ledger(Ledger& ledger, const Ledger::LeaseHandle& handle, PoolSlotState expected,
        std::string_view affinity, bool ledger_owned) {
    const auto before = ledger.stats();
    const auto id = handle.id(), generation = handle.generation();
    const auto references = handle.inspect_payload().owner.use_count();
    std::array<Ledger::SlotSnapshot, 4> rows{};
    for (unsigned attempt = 0; attempt < 4; ++attempt) {
        check(handle.state() == expected, "external lease state is the actual scalar state");
        const auto count = ledger.snapshot_slots(rows);
        size_t matching = 0;
        for (size_t index = 0; index < count; ++index) {
            if (rows[index].slot_id == id) {
                ++matching;
                check(rows[index].generation == generation && rows[index].state == expected,
                    "ledger snapshot joins actual handle identity/generation/state");
            }
        }
        check(matching == size_t(ledger_owned), "external-only retired handle is not fabricated as ledger membership");
        ledger.for_each_slot([&](const auto& view) {
            if (view.id == id) {
                check(view.affinity == affinity && view.state == expected, "inspection preserves exact borrowed affinity and state");
                check(view.payload.owner.use_count() == references, "inspection does not copy a represented owner");
            }
        });
        check(handle.id() == id && handle.generation() == generation &&
            handle.inspect_payload().owner.use_count() == references, "repeated observations preserve identities and owner refcounts");
        equal_stats(before, ledger.stats());
    }
}

void actual_pool_state_and_external_retired_owners() {
    Ledger::LeaseHandle empty;
    rejects<std::logic_error>([&] { (void)empty.state(); }, "empty lease has no fabricated idle state");
    Ledger ledger(PoolLimits{4, 4096, 65536, 4096, 65536}, 3);
    LedgerBuilder builder;
    LeaseRequest request{3, "immutable-affinity", {256, 64, 64}, 128};
    auto first = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(first) && builder.calls == 1, "real ledger reservation creates one owner");
    auto external = first.reservation.at(0);
    const auto old_id = external.id();
    const auto first_owner = builder.created.front();
    inspect_ledger(ledger, external, PoolSlotState::Reserved, request.affinity, true);
    first.reservation.mark_submitted();
    inspect_ledger(ledger, external, PoolSlotState::Submitted, request.affinity, true);
    rejects<std::logic_error>([&] { first.reservation.rollback(); }, "submitted state cannot be observed as rolled back");
    check(external.state() == PoolSlotState::Submitted, "rejected rollback does not retire submitted owner");
    first.reservation.retire();
    inspect_ledger(ledger, external, PoolSlotState::Idle, request.affinity, true);
    auto reused = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(reused) && reused.reservation.at(0).id() == old_id && builder.calls == 1,
        "actual retirement permits same-affinity reuse without replacement");
    inspect_ledger(ledger, reused.reservation.at(0), PoolSlotState::Reserved, request.affinity, true);
    rejects<std::logic_error>([&] { (void)std::as_const(external).payload(); },
        "scalar state observation does not activate an old lease token");
    reused.reservation.rollback();
    inspect_ledger(ledger, external, PoolSlotState::Idle, request.affinity, true);
    ledger.invalidate_generation(4);
    check(ledger.stats().slots == 0 && !first_owner.expired(), "generation removal leaves actual external retired owner alive");
    inspect_ledger(ledger, external, PoolSlotState::Idle, request.affinity, false);
    first.reservation = {};
    reused.reservation = {};
    external = {};
    check(first_owner.expired(), "state observations never retain removed owner beyond its actual leases");

    request.generation = 4;
    auto busy = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(busy), "new generation admits independent owner");
    auto old_busy = busy.reservation.at(0);
    const auto busy_owner = builder.created.back();
    busy.reservation.mark_submitted();
    ledger.invalidate_generation(5);
    inspect_ledger(ledger, old_busy, PoolSlotState::Submitted, request.affinity, true);
    check(ledger.stats().busy_slots == 1 && old_busy.generation() == 4,
        "busy old generation remains charged and submitted until actual processing");
    request.generation = 5;
    auto current = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(current) && current.reservation.at(0).id() != old_busy.id() &&
        current.reservation.at(0).generation() == 5, "same affinity cannot reuse an old-generation busy owner");
    inspect_ledger(ledger, current.reservation.at(0), PoolSlotState::Reserved, request.affinity, true);
    busy.reservation.retire();
    inspect_ledger(ledger, old_busy, PoolSlotState::Idle, request.affinity, false);
    check(!busy_owner.expired() && ledger.stats().slots == 1, "real processing removes old membership while external lease retains payload");
    current.reservation.rollback();
    inspect_ledger(ledger, current.reservation.at(0), PoolSlotState::Idle, request.affinity, true);
    busy.reservation = {};
    old_busy = {};
    check(busy_owner.expired(), "old-generation owner releases after actual processing and last external handle");
}

void retirement_commits_before_fallible_terminal_publication() {
    Ledger ledger(PoolLimits{4, 4096, 65536, 4096, 65536}, 9);
    LedgerBuilder builder;
    LeaseRequest request{9, "cancelled-but-valid", {256, 64, 64}, 128};
    auto batch = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(batch), "retirement control uses real pool reservation");
    const auto id = batch.reservation.at(0).id();
    batch.reservation.mark_submitted();
    vispy::frames::Lifecycle work;
    work.generation = 9;
    work.bind_paint(901); work.enqueue(1); work.begin_batch();
    work.submitted(801, 100, 9); work.finish_batch();
    work.fail("failed", "logical user cancellation"); work.close(120);
    bool processed = false;
    uint64_t successes = 13, failures = 17, retire_calls = 0, publication_calls = 0;
    auto retire_actual = [&] {
        batch.reservation.retire(true);
        work.retired(150);
        ++retire_calls;
    };
    rejects<std::runtime_error>([&] {
        check(process_ticket_retirement_once(processed, successes, failures, true, retire_actual),
            "first actual processing passes once boundary");
        ++publication_calls;
        throw std::runtime_error("independent terminal publication allocation fault");
    }, "fallible terminal publication may fail after real processing");
    check(processed && batch.reservation.finished() && work.outstanding == 0 && work.ready(),
        "actual pool/frame retirement remains committed despite publication failure");
    check(retire_calls == 1 && successes == 14 && failures == 17 && publication_calls == 1,
        "native-success processing counted exactly once independent of logical failure");
    check(work.status() == "failed" && batch.reservation.at(0).state() == PoolSlotState::Idle,
        "logical cancellation stays failed while successfully processed native payload becomes reusable");
    check(!process_ticket_retirement_once(processed, successes, failures, true, [&] {
        throw std::runtime_error("duplicate actual retirement must never execute");
    }), "publication retry skips previously committed processing");
    ++publication_calls;
    check(retire_calls == 1 && work.outstanding == 0 && successes == 14 && failures == 17 && publication_calls == 2,
        "terminal publication retry cannot duplicate outstanding decrement or diagnostic counter");
    auto reused = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(reused) && reused.reservation.at(0).id() == id && builder.calls == 1,
        "logically cancelled valid payload reuses only after actual native processing");
    reused.reservation.rollback();

    auto retryable = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    retryable.reservation.mark_submitted();
    vispy::frames::Lifecycle pending;
    pending.generation = 9; pending.submitted(802, 200, 9); pending.close(210);
    bool retry_processed = false;
    rejects<std::runtime_error>([&] {
        process_ticket_retirement_once(retry_processed, successes, failures, true, [&] {
            throw std::runtime_error("pre-processing refusal before any pool/frame side effect");
        });
    }, "pre-processing failure remains retryable");
    check(!retry_processed && successes == 14 && failures == 17 && pending.outstanding == 1 &&
        !retryable.reservation.finished() && retryable.reservation.at(0).state() == PoolSlotState::Submitted,
        "pre-processing failure leaves actual ownership, flag and counts unchanged");
    check(process_ticket_retirement_once(retry_processed, successes, failures, true, [&] {
        retryable.reservation.retire(true); pending.retired(230);
    }), "retry after pre-processing refusal performs real retirement once");
    check(retry_processed && successes == 15 && pending.outstanding == 0 && retryable.reservation.finished(),
        "retried real processing commits exactly once");

    request.affinity = "unaffected-valid";
    auto unaffected = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    const auto unaffected_id = unaffected.reservation.at(0).id();
    request.affinity = "invalid-native-payload";
    auto failed = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    // Keep the first real reservation busy until the second has a distinct
    // owner; otherwise legal suitable-idle reuse could alias these controls.
    check(bool(unaffected) && bool(failed) && failed.reservation.at(0).id() != unaffected_id,
        "native-failure control uses an actually separate unaffected owner");
    unaffected.reservation.rollback();
    auto failed_external = failed.reservation.at(0);
    const auto failed_id = failed_external.id();
    failed.reservation.mark_submitted();
    vispy::frames::Lifecycle failed_work;
    failed_work.generation = 9; failed_work.submitted(803, 300, 9);
    failed_work.fail("failed", "native encoding/queue failure"); failed_work.close(310);
    bool failed_processed = false;
    check(process_ticket_retirement_once(failed_processed, successes, failures, false, [&] {
        failed.reservation.retire(false); failed_work.retired(330);
    }), "native failure processes and discards its actual reservation once");
    check(failures == 18 && successes == 15 && failed_work.outstanding == 0 && failed.reservation.finished() &&
        failed_external.state() == PoolSlotState::Idle, "native-failure counter and external retired state are actual processing outcomes");
    bool found_bad = false, found_unaffected = false;
    ledger.for_each_slot([&](const auto& view) {
        found_bad = found_bad || view.id == failed_id;
        found_unaffected = found_unaffected || (view.id == unaffected_id && view.affinity == "unaffected-valid" &&
            view.state == PoolSlotState::Idle);
    });
    check(!found_bad && found_unaffected, "native failure removes only the processed invalid payload from reusable membership");
    auto replacement = ledger.reserve_batch(std::span<const LeaseRequest>(&request, 1), builder);
    check(bool(replacement) && replacement.reservation.at(0).id() != failed_id,
        "invalid native payload cannot be reused after processing");
    replacement.reservation.rollback();
    check(!process_ticket_retirement_once(failed_processed, successes, failures, false, [] {}),
        "native failure publication retry never repeats processing");
    check(failures == 18 && successes == 15, "publication retries preserve both native outcome counters");
}
} // namespace

int main() {
    try {
        hard_arena_and_failure_preservation();
        maximum_rows_and_exact_scalar_bits();
        allocator_aware_row_ingress();
        move_return_and_destruction_orders();
        value_only_metadata_cannot_retain_native_owner();
        actual_pool_state_and_external_retired_owners();
        retirement_commits_before_fallible_terminal_publication();
        std::cout << "line_ownership_contract: " << checks << " checks passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "line_ownership_contract failed after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
