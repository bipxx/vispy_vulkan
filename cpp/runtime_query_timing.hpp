#pragma once

#include <algorithm>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace vispy::timing {

inline constexpr uint32_t max_queries_per_frame = 4096;
inline constexpr uint32_t max_submissions_per_frame = 64;

enum class Status { Pending, Success, UnsupportedFeature, PassLimit, SubmissionLimit,
                    MapError, SubmissionError, DeviceLost, Cancelled, InvalidTimestamp, NoPasses };

inline const char* status_name(Status status) {
    switch (status) {
        case Status::Pending: return "pending";
        case Status::Success: return "success";
        case Status::UnsupportedFeature: return "unsupported_feature";
        case Status::PassLimit: return "unsupported_pass_count";
        case Status::SubmissionLimit: return "unsupported_submission_count";
        case Status::MapError: return "map_error";
        case Status::SubmissionError: return "submission_error";
        case Status::DeviceLost: return "device_lost";
        case Status::Cancelled: return "cancelled";
        case Status::InvalidTimestamp: return "invalid_timestamp";
        case Status::NoPasses: return "no_render_passes";
    }
    return "invalid_status";
}

struct PassResult {
    uint32_t submission_index = 0;
    std::string kind;
    uint64_t begin_ns = 0, end_ns = 0, elapsed_ns = 0;
};

struct FrameResult {
    uint64_t frame_id = 0, device_generation = 0, quantization_ns = 0;
    uint64_t paint_token = 0;
    uint64_t last_present_submission_index = UINT64_MAX;
    std::string frame_scope = "native_present";
    uint32_t submission_count = 0;
    std::string status, error;
    uint64_t render_span_ns = 0, pass_sum_ns = 0;
    std::vector<PassResult> passes;
};

// A native map callback owns its segment independently of canvas, device
// generation, Ticket retirement and caller result lifetimes. Publish mapped
// values and errors under this mutex; the collector never waits for Pending.
struct Segment {
    mutable std::mutex mutex;
    Status status = Status::Pending;
    std::string error;
    uint32_t submission_index = 0, reserved_queries = 0;
    std::vector<std::string> kinds;
    std::vector<uint64_t> values;
    virtual ~Segment() = default;
};

struct Frame {
    uint64_t frame_id = 0, device_generation = 0, quantization_ns = 0;
    uint64_t paint_token = 0;
    uint64_t last_present_submission_index = UINT64_MAX;
    std::string frame_scope = "native_present";
    uint32_t submission_count = 0, reserved_queries = 0;
    bool finalized = false;
    Status failure = Status::Pending;
    std::string error;
    std::vector<std::shared_ptr<Segment>> segments;

    void fail(Status status, const std::string& message) {
        if (failure == Status::Pending) { failure = status; error = message; }
    }

    bool reserve(uint64_t generation, uint64_t pass_capacity, uint32_t& queries) {
        queries = 0;
        if (failure != Status::Pending) return false;
        if (generation != device_generation) {
            fail(Status::DeviceLost, "frame submissions span different device generations");
            return false;
        }
        if (submission_count >= max_submissions_per_frame) {
            fail(Status::SubmissionLimit, "GPU timing frame exceeds submission limit");
            return false;
        }
        if (pass_capacity > max_queries_per_frame / 2 ||
            pass_capacity * 2 > max_queries_per_frame - reserved_queries) {
            fail(Status::PassLimit, "GPU timing frame exceeds reserved timestamp query limit");
            return false;
        }
        queries = static_cast<uint32_t>(pass_capacity * 2);
        reserved_queries += queries;
        return true;
    }

    bool collect(FrameResult& result) const {
        if (!finalized) return false;
        result = {};
        result.frame_id = frame_id;
        result.paint_token = paint_token;
        result.last_present_submission_index = last_present_submission_index;
        result.frame_scope = frame_scope;
        result.device_generation = device_generation;
        result.quantization_ns = quantization_ns;
        result.submission_count = submission_count;
        if (failure != Status::Pending) {
            result.status = status_name(failure); result.error = error;
            return true;
        }
        uint64_t earliest = std::numeric_limits<uint64_t>::max(), latest = 0;
        for (const auto& segment : segments) {
            std::lock_guard<std::mutex> lock(segment->mutex);
            if (segment->status == Status::Pending) return false;
            if (segment->status != Status::Success) {
                result.status = status_name(segment->status); result.error = segment->error;
                result.passes.clear(); result.render_span_ns = result.pass_sum_ns = 0;
                return true;
            }
            if (segment->values.size() != segment->kinds.size() * 2) {
                result.status = status_name(Status::InvalidTimestamp);
                result.error = "mapped timestamp count differs from recorded pass count";
                result.passes.clear(); result.pass_sum_ns = 0;
                return true;
            }
            for (size_t i = 0; i < segment->kinds.size(); ++i) {
                const uint64_t begin = segment->values[i * 2], end = segment->values[i * 2 + 1];
                if (end < begin || end - begin > std::numeric_limits<uint64_t>::max() - result.pass_sum_ns) {
                    result.status = status_name(Status::InvalidTimestamp);
                    result.error = "reversed timestamp pair or overflowing elapsed sum";
                    result.passes.clear(); result.pass_sum_ns = 0;
                    return true;
                }
                result.passes.push_back({segment->submission_index, segment->kinds[i], begin, end, end - begin});
                result.pass_sum_ns += end - begin;
                earliest = std::min(earliest, begin); latest = std::max(latest, end);
            }
        }
        result.status = result.passes.empty() ? status_name(Status::NoPasses) : status_name(Status::Success);
        if (!result.passes.empty()) result.render_span_ns = latest - earliest;
        return true;
    }
};

}  // namespace vispy::timing
