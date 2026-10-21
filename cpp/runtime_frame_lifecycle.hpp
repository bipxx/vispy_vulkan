#pragma once

#include <algorithm>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>

namespace vispy::frames {

template<class Snapshot> struct FrozenSubmission {
    uint64_t ticket = 0;
    std::optional<Snapshot> value;
    void capture(uint64_t id, const Snapshot& counters) {
        if (!id || id <= ticket) throw std::runtime_error("submission counters were captured more than once or out of order");
        value = counters; ticket = id;
    }
};

// Reserve a new measured owner, or admit the paint of an owner already
// reserved by benchmark_begin_frame. Actual GPU/queue/result usage never
// receives a reservation discount. Subtraction avoids overflowing counts.
struct AdmissionCapacity {
    uint64_t slots = 1, tickets = 0, queued_batches = 0;
    uint64_t owners = 0, queries = 0, query_segments = 0, query_segment_limit = 64;
    uint64_t completions = 0, gpu_records = 0, canvas_gpu_records = 0;
    uint64_t terminal_limit = 4096, canvas_gpu_record_limit = 2;
    bool gpu_timing = false;

    bool ready(bool reserved_owner = false, bool reserved_query = false) const {
        if (!slots || !terminal_limit || tickets >= slots || queued_batches ||
            (reserved_owner && !owners) || (reserved_query && (!reserved_owner || !queries))) return false;
        const uint64_t other_owners = owners - (reserved_owner ? 1 : 0);
        if (other_owners >= slots || completions >= terminal_limit ||
            other_owners >= terminal_limit - completions) return false;
        if (!gpu_timing) return !reserved_query;
        const uint64_t other_queries = queries - (reserved_query ? 1 : 0);
        return other_queries < slots && query_segments < query_segment_limit &&
            canvas_gpu_records < canvas_gpu_record_limit && gpu_records < terminal_limit &&
            other_queries < terminal_limit - gpu_records;
    }
};

// CPU recording/queue ownership only. No clock reads, callbacks or GPU waits.
// The renderer calls these methods under its engine mutex. A Ticket retires
// once; callback threads merely publish the Ticket's completion observation.
struct Lifecycle {
    uint64_t begin_ns = 0, close_ns = 0, last_submit_ns = 0, completion_ns = 0;
    uint64_t generation = 0, paint_token = 0;
    uint64_t queued_batches = 0, encoding_batches = 0, outstanding = 0;
    uint64_t submissions = 0, presents = 0, last_ticket = 0;
    uint64_t last_present_submission_index = UINT64_MAX;
    bool closed = false, emitted = false, surface_expected = false;
    std::string failure, error;

    void bind_paint(uint64_t token) {
        if (!token || paint_token || closed) throw std::runtime_error("paint owner is already bound or closed");
        paint_token = token;
    }
    void expect_surface(bool attached) { surface_expected = surface_expected || attached; }
    bool surface_unavailable(bool attached, const std::string& message) {
        expect_surface(attached);
        if (!paint_token || !surface_expected) return false;
        fail("failed", message);
        return true;
    }
    void enqueue(uint64_t limit) {
        if (closed) throw std::runtime_error("cannot record work after frame closure");
        if (queued_batches >= limit) throw std::runtime_error("frame queued submission capacity full");
        ++queued_batches;
    }
    void begin_batch() {
        if (!queued_batches || encoding_batches) throw std::runtime_error("invalid queued frame batch transition");
        --queued_batches; ++encoding_batches;
    }
    void finish_batch() {
        if (!encoding_batches) throw std::runtime_error("frame batch was not encoding");
        --encoding_batches;
    }
    void submitted(uint64_t ticket, uint64_t timestamp, uint64_t device_generation) {
        if (device_generation != generation) throw std::runtime_error("frame submissions span device generations");
        if (closed && !encoding_batches) throw std::runtime_error("submission was not admitted before frame closure");
        if (!ticket || ticket <= last_ticket || submissions == UINT64_MAX || outstanding == UINT64_MAX)
            throw std::runtime_error("frame submission identity/count overflow");
        last_ticket = ticket; last_submit_ns = timestamp; ++submissions; ++outstanding;
    }
    void presented() {
        if (!submissions || presents == UINT64_MAX || last_present_submission_index == submissions - 1)
            throw std::runtime_error("frame presentation has no unique submitted Ticket");
        last_present_submission_index = submissions - 1;
        ++presents;
    }
    void retired(uint64_t timestamp) {
        if (!outstanding) throw std::runtime_error("frame Ticket retired more than once");
        --outstanding; completion_ns = std::max(completion_ns, timestamp);
    }
    void fail(const std::string& status, const std::string& message) {
        if (failure.empty()) { failure = status; error = message; }
    }
    void close(uint64_t timestamp) {
        if (!closed) { closed = true; close_ns = timestamp; }
    }
    void discard_queued(uint64_t count) {
        if (count > queued_batches) throw std::runtime_error("invalid frame queued work retirement");
        queued_batches -= count;
    }
    bool admission_finished() const { return closed && !queued_batches && !encoding_batches; }
    bool reserved_unpainted() const {
        return !paint_token && !closed && !submissions && !queued_batches && !encoding_batches && !outstanding;
    }
    bool ready() const { return admission_finished() && !outstanding; }
    uint64_t completed_at() const { return std::max(close_ns, completion_ns); }
    std::string status() const { return failure.empty() ? (submissions ? "success" : "no_submission") : failure; }
};

}  // namespace vispy::frames
