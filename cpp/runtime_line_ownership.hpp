#pragma once

#include "runtime_line_pool.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <memory_resource>
#include <string>
#include <utility>
#include <vector>

namespace vispy::lines {

// Called under the Engine mutex. Commit actual native/frame retirement once;
// terminal receipt allocation/publication belongs after this boundary so a
// publication failure can retry without releasing or retiring an owner twice.
template<class Process>
bool process_ticket_retirement_once(bool& processed, uint64_t& successes, uint64_t& failures,
                                    bool successful, Process&& process) {
    if (processed) return false;
    std::forward<Process>(process)();
    processed = true;
    ++(successful ? successes : failures);
    return true;
}

// Owned scalar metadata only: this diagnostic result cannot prolong a native
// owner, admit a batch or supply a completion. The Engine fills it under its
// mutex without polling Dawn. Map callbacks retain their independent state.
struct OwnershipSlot {
    uint64_t slot_id = 0, generation = 0;
    PoolSlotState state = PoolSlotState::Idle;
    LeaseCapacities capacities;
    uint64_t extra_control_bytes = 0;
};

struct OwnershipTicket {
    using allocator_type = std::pmr::polymorphic_allocator<std::byte>;
    int canvas_id = 0;
    uint64_t ticket_id = 0, generation = 0, frame_id = 0, paint_token = 0;
    bool callback_complete = false, callback_ok = false, retirement_processed = false;
    bool has_encoding_validation = false, encoding_validation_complete = false, encoding_validation_ok = false;
    std::pmr::vector<uint64_t> slot_ids;
    std::pmr::string error, validation_error;
    explicit OwnershipTicket(std::pmr::memory_resource* memory)
        : slot_ids(memory), error(memory), validation_error(memory) {}
    OwnershipTicket(std::allocator_arg_t, allocator_type allocator)
        : OwnershipTicket(allocator.resource()) {}
    OwnershipTicket(std::allocator_arg_t, allocator_type allocator, const OwnershipTicket& other)
        : canvas_id(other.canvas_id), ticket_id(other.ticket_id), generation(other.generation),
          frame_id(other.frame_id), paint_token(other.paint_token),
          callback_complete(other.callback_complete), callback_ok(other.callback_ok),
          retirement_processed(other.retirement_processed), has_encoding_validation(other.has_encoding_validation),
          encoding_validation_complete(other.encoding_validation_complete), encoding_validation_ok(other.encoding_validation_ok),
          slot_ids(other.slot_ids, allocator.resource()), error(other.error, allocator.resource()),
          validation_error(other.validation_error, allocator.resource()) {}
    OwnershipTicket(std::allocator_arg_t, allocator_type allocator, OwnershipTicket&& other)
        : canvas_id(other.canvas_id), ticket_id(other.ticket_id), generation(other.generation),
          frame_id(other.frame_id), paint_token(other.paint_token),
          callback_complete(other.callback_complete), callback_ok(other.callback_ok),
          retirement_processed(other.retirement_processed), has_encoding_validation(other.has_encoding_validation),
          encoding_validation_complete(other.encoding_validation_complete), encoding_validation_ok(other.encoding_validation_ok),
          slot_ids(std::move(other.slot_ids), allocator.resource()), error(std::move(other.error), allocator.resource()),
          validation_error(std::move(other.validation_error), allocator.resource()) {}
    OwnershipTicket(const OwnershipTicket&) = delete;
    OwnershipTicket(OwnershipTicket&&) noexcept = default;
    OwnershipTicket& operator=(const OwnershipTicket&) = default;
    OwnershipTicket& operator=(OwnershipTicket&&) = default;
};

struct OwnershipQueuedBatch {
    using allocator_type = std::pmr::polymorphic_allocator<std::byte>;
    uint64_t queue_id = 0, generation = 0, frame_id = 0, paint_token = 0, draw_count = 0;
    std::pmr::vector<uint64_t> capture_ids;
    explicit OwnershipQueuedBatch(std::pmr::memory_resource* memory) : capture_ids(memory) {}
    OwnershipQueuedBatch(std::allocator_arg_t, allocator_type allocator) : OwnershipQueuedBatch(allocator.resource()) {}
    OwnershipQueuedBatch(std::allocator_arg_t, allocator_type allocator, const OwnershipQueuedBatch& other)
        : queue_id(other.queue_id), generation(other.generation), frame_id(other.frame_id),
          paint_token(other.paint_token), draw_count(other.draw_count), capture_ids(other.capture_ids, allocator.resource()) {}
    OwnershipQueuedBatch(std::allocator_arg_t, allocator_type allocator, OwnershipQueuedBatch&& other)
        : queue_id(other.queue_id), generation(other.generation), frame_id(other.frame_id),
          paint_token(other.paint_token), draw_count(other.draw_count), capture_ids(std::move(other.capture_ids), allocator.resource()) {}
    OwnershipQueuedBatch(const OwnershipQueuedBatch&) = delete;
    OwnershipQueuedBatch(OwnershipQueuedBatch&&) noexcept = default;
    OwnershipQueuedBatch& operator=(const OwnershipQueuedBatch&) = default;
    OwnershipQueuedBatch& operator=(OwnershipQueuedBatch&&) = default;
};

struct OwnershipCapture {
    using allocator_type = std::pmr::polymorphic_allocator<std::byte>;
    int canvas_id = 0;
    uint64_t capture_id = 0, ticket_id = 0, frame_id = 0, paint_token = 0;
    uint64_t generation = 0, charged_bytes = 0, readback_capacity = 0;
    bool ticket_finished = false;
    std::pmr::string status, error;
    explicit OwnershipCapture(std::pmr::memory_resource* memory) : status(memory), error(memory) {}
    OwnershipCapture(std::allocator_arg_t, allocator_type allocator) : OwnershipCapture(allocator.resource()) {}
    OwnershipCapture(std::allocator_arg_t, allocator_type allocator, const OwnershipCapture& other)
        : canvas_id(other.canvas_id), capture_id(other.capture_id), ticket_id(other.ticket_id),
          frame_id(other.frame_id), paint_token(other.paint_token), generation(other.generation),
          charged_bytes(other.charged_bytes), readback_capacity(other.readback_capacity), ticket_finished(other.ticket_finished),
          status(other.status, allocator.resource()), error(other.error, allocator.resource()) {}
    OwnershipCapture(std::allocator_arg_t, allocator_type allocator, OwnershipCapture&& other)
        : canvas_id(other.canvas_id), capture_id(other.capture_id), ticket_id(other.ticket_id),
          frame_id(other.frame_id), paint_token(other.paint_token), generation(other.generation),
          charged_bytes(other.charged_bytes), readback_capacity(other.readback_capacity), ticket_finished(other.ticket_finished),
          status(std::move(other.status), allocator.resource()), error(std::move(other.error), allocator.resource()) {}
    OwnershipCapture(const OwnershipCapture&) = delete;
    OwnershipCapture(OwnershipCapture&&) noexcept = default;
    OwnershipCapture& operator=(const OwnershipCapture&) = default;
    OwnershipCapture& operator=(OwnershipCapture&&) = default;
};

struct OwnershipQuerySegment {
    int canvas_id = 0;
    uint64_t ticket_id = 0, generation = 0, frame_id = 0, paint_token = 0;
    uint32_t submission_index = 0;
    uint64_t resolve_capacity = 0, readback_capacity = 0;
    bool map_requested = false, map_callback_complete = false;
};

struct OwnershipFrame {
    using allocator_type = std::pmr::polymorphic_allocator<std::byte>;
    uint64_t frame_id = 0, paint_token = 0, generation = 0;
    uint64_t submissions = 0, outstanding = 0, queued_batches = 0;
    bool gpu_timing = false, closed = false;
    bool receipt_emitted = false, gpu_result_emitted = false;
    std::pmr::string failure, error;
    explicit OwnershipFrame(std::pmr::memory_resource* memory) : failure(memory), error(memory) {}
    OwnershipFrame(std::allocator_arg_t, allocator_type allocator) : OwnershipFrame(allocator.resource()) {}
    OwnershipFrame(std::allocator_arg_t, allocator_type allocator, const OwnershipFrame& other)
        : frame_id(other.frame_id), paint_token(other.paint_token), generation(other.generation),
          submissions(other.submissions), outstanding(other.outstanding), queued_batches(other.queued_batches),
          gpu_timing(other.gpu_timing), closed(other.closed), receipt_emitted(other.receipt_emitted), gpu_result_emitted(other.gpu_result_emitted),
          failure(other.failure, allocator.resource()), error(other.error, allocator.resource()) {}
    OwnershipFrame(std::allocator_arg_t, allocator_type allocator, OwnershipFrame&& other)
        : frame_id(other.frame_id), paint_token(other.paint_token), generation(other.generation),
          submissions(other.submissions), outstanding(other.outstanding), queued_batches(other.queued_batches),
          gpu_timing(other.gpu_timing), closed(other.closed), receipt_emitted(other.receipt_emitted), gpu_result_emitted(other.gpu_result_emitted),
          failure(std::move(other.failure), allocator.resource()), error(std::move(other.error), allocator.resource()) {}
    OwnershipFrame(const OwnershipFrame&) = delete;
    OwnershipFrame(OwnershipFrame&&) noexcept = default;
    OwnershipFrame& operator=(const OwnershipFrame&) = default;
    OwnershipFrame& operator=(OwnershipFrame&&) = default;
};

struct OwnershipPoolStats {
    uint64_t slots = 0, busy_slots = 0, owned_capacity_bytes = 0, control_bytes = 0;
};

struct OwnershipCounters {
    uint64_t dawn_queue_submits = 0, draw_calls = 0;
    uint64_t line_endpoint_dispatches = 0, line_endpoint_rows = 0, compute_passes = 0;
    uint64_t retired_tickets = 0, successful_ticket_retirements = 0, failed_ticket_retirements = 0;
    uint64_t completion_waits = 0, finish_calls = 0;
    uint64_t timestamp_query_sets = 0, timestamp_resolves = 0, timestamp_readbacks = 0;
    uint64_t query_map_callbacks_completed = 0;
    uint64_t buffer_allocations = 0, bind_group_creations = 0;
    uint64_t line_resource_pool_hits = 0, line_resource_pool_evictions = 0, line_resource_pool_deferrals = 0;
    uint64_t deferred_frames = 0, uniform_upload_bytes = 0;
    uint64_t line_endpoint_conversion_builds = 0, line_endpoint_conversion_bytes = 0, line_endpoint_upload_bytes = 0;
};

struct LineOwnershipSnapshot {
    static constexpr size_t max_frame_slots = 8;
    static constexpr size_t max_pool_slots = 128;
    static constexpr size_t max_captures = 128;
    static constexpr size_t max_query_segments = max_frame_slots * 64;
    // A selected canvas can retain frames through global frame/query/Ticket
    // lists, its queue and its current mark: each bounded by eight, plus one.
    static constexpr size_t max_frames = 4 * max_frame_slots + 1;
    static constexpr size_t max_external_slots = max_frame_slots * max_pool_slots;
    static constexpr size_t max_error_bytes = 4096;
    static constexpr uint64_t max_control_bytes = 1024 * 1024;

private:
    // All variable-sized result storage shares a fixed arena. The null upstream
    // rejects exhaustion before any allocation can exceed this hard ceiling.
    // The allowance covers the fixed result/resource metadata on every target.
    static constexpr size_t metadata_allowance = 4096;
    struct Storage {
        std::array<std::byte, max_control_bytes - metadata_allowance> bytes;
        std::pmr::monotonic_buffer_resource arena{bytes.data(), bytes.size(), std::pmr::null_memory_resource()};
    };
    std::unique_ptr<Storage> storage_;

public:

    int canvas_id = 0;
    uint64_t generation = 0, frame_slots = 0, capture_charge_bytes = 0, terminal_record_limit = 0;
    PoolLimits pool_limits;
    OwnershipPoolStats pool;
    OwnershipCounters counters;
    std::pmr::vector<OwnershipSlot> slots, external_slots;
    std::pmr::vector<OwnershipTicket> tickets;
    std::pmr::vector<OwnershipQueuedBatch> queued;
    std::pmr::vector<OwnershipCapture> captures;
    std::pmr::vector<OwnershipQuerySegment> query_segments;
    std::pmr::vector<OwnershipFrame> frames;

    LineOwnershipSnapshot()
        : storage_(std::make_unique<Storage>()), slots(memory_resource()), external_slots(memory_resource()),
          tickets(memory_resource()), queued(memory_resource()), captures(memory_resource()),
          query_segments(memory_resource()), frames(memory_resource()) {
        static_assert(sizeof(LineOwnershipSnapshot) + sizeof(Storage) <= max_control_bytes);
    }
    LineOwnershipSnapshot(const LineOwnershipSnapshot&) = delete;
    LineOwnershipSnapshot& operator=(const LineOwnershipSnapshot&) = delete;
    LineOwnershipSnapshot(LineOwnershipSnapshot&&) noexcept = default;
    LineOwnershipSnapshot& operator=(LineOwnershipSnapshot&&) = delete;
    std::pmr::memory_resource* memory_resource() const noexcept { return &storage_->arena; }
    uint64_t allocated_control_bytes() const noexcept { return sizeof(*this) + sizeof(Storage); }

    // Conservative STL value-storage capacity, including nested containers.
    // String small-buffer capacity can overlap its already-counted row. This
    // usage view overlaps the fixed arena allocation; do not add the two.
    // Allocator headers, Python objects, stack and driver memory are excluded.
    uint64_t control_capacity_bytes() const {
        using namespace line_pool_detail;
        uint64_t bytes = sizeof(*this);
        auto capacity = [&](size_t count, size_t width) {
            bytes = add(bytes, multiply(count, width));
        };
        capacity(slots.capacity(), sizeof(OwnershipSlot));
        capacity(external_slots.capacity(), sizeof(OwnershipSlot));
        capacity(tickets.capacity(), sizeof(OwnershipTicket));
        capacity(queued.capacity(), sizeof(OwnershipQueuedBatch));
        capacity(captures.capacity(), sizeof(OwnershipCapture));
        capacity(query_segments.capacity(), sizeof(OwnershipQuerySegment));
        capacity(frames.capacity(), sizeof(OwnershipFrame));
        for (const auto& row : tickets) {
            capacity(row.slot_ids.capacity(), sizeof(uint64_t));
            capacity(row.error.capacity() + 1, sizeof(char));
            capacity(row.validation_error.capacity() + 1, sizeof(char));
        }
        for (const auto& row : queued) capacity(row.capture_ids.capacity(), sizeof(uint64_t));
        for (const auto& row : captures) {
            capacity(row.status.capacity() + 1, sizeof(char));
            capacity(row.error.capacity() + 1, sizeof(char));
        }
        for (const auto& row : frames) {
            capacity(row.failure.capacity() + 1, sizeof(char));
            capacity(row.error.capacity() + 1, sizeof(char));
        }
        return bytes;
    }
};

} // namespace vispy::lines
