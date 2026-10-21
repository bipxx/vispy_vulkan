#include "runtime_query_timing.hpp"
#include <functional>
#include <iostream>
#include <stdexcept>

using namespace vispy::timing;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }

int main() {
    try {
        Frame frame;
        frame.frame_id = 7; frame.device_generation = 3; frame.quantization_ns = 65536;
        uint32_t count = 0;
        require(frame.reserve(3, 2, count) && count == 4, "bounded pair layout");
        auto first = std::make_shared<Segment>(), last = std::make_shared<Segment>();
        first->kinds = {"scene", "present_capture"}; first->submission_index = frame.submission_count++;
        last->kinds = {"surface_conversion"}; last->submission_index = frame.submission_count++;
        frame.segments = {first, last}; frame.finalized = true;
        last->status = Status::Success; last->values = {3 * 65536, 4 * 65536};
        FrameResult result;
        require(!frame.collect(result), "out-of-order callbacks retain pending first submission");
        first->status = Status::Success; first->values = {65536, 65536, 65536, 2 * 65536};
        require(frame.collect(result) && result.status == "success" && result.submission_count == 2 &&
                result.passes.size() == 3 && result.passes[0].elapsed_ns == 0 &&
                result.render_span_ns == 3 * 65536 && result.pass_sum_ns == 2 * 65536,
                "quantized zero is valid; every submission/pass remains included");
        first->values = {1, 8, 3, 12}; last->values = {9, 14};
        require(frame.collect(result) && result.render_span_ns == 13 && result.pass_sum_ns == 21,
                "overlapping intervals are not rejected or mistaken for additive frame time");
        last->values = {9, 8};
        require(frame.collect(result) && result.status == "invalid_timestamp" && result.passes.empty(),
                "reversed samples fail explicitly");
        last->status = Status::MapError; last->error = "actual map failure";
        require(frame.collect(result) && result.status == "map_error" && result.error == last->error,
                "map errors do not synthesize GPU durations");
        last->status = Status::Pending;
        frame.fail(Status::DeviceLost, "lost");
        require(frame.collect(result) && result.status == "device_lost", "loss cancels pending observations without a wait");
        Frame bounded; bounded.device_generation = 3;
        require(bounded.reserve(3, 2048, count) && count == 4096 && !bounded.reserve(3, 1, count) &&
                bounded.failure == Status::PassLimit, "total per-frame query allocation is bounded across submits");
        Frame huge; huge.device_generation = 3;
        require(!huge.reserve(3, UINT64_MAX, count), "overflowing pass count cannot wrap admission");
        Frame many; many.device_generation = 3; many.submission_count = 64;
        require(!many.reserve(3, 1, count) && many.failure == Status::SubmissionLimit, "submission bound");
        Frame generation; generation.device_generation = 3;
        require(!generation.reserve(4, 1, count) && generation.failure == Status::DeviceLost, "generation identity");
        Frame unavailable; unavailable.fail(Status::UnsupportedFeature, "not granted"); unavailable.finalized = true;
        require(unavailable.collect(result) && result.status == "unsupported_feature" && result.passes.empty(),
                "unsupported capability has typed empty timing");
        Frame empty; empty.finalized = true;
        require(empty.collect(result) && result.status == "no_render_passes", "empty frame is not a fabricated zero duration");
        auto owned = std::make_shared<Segment>(); std::weak_ptr<Segment> weak = owned;
        std::function<void()> callback = [owned] { std::lock_guard<std::mutex> lock(owned->mutex); owned->status = Status::Success; };
        owned.reset(); require(!weak.expired(), "callback independently owns canceled native state");
        callback(); callback = {}; require(weak.expired(), "callback retirement releases its final owner");
        std::cout << "timestamp bounds, quantization, overlapping multi-submit aggregation, cancellation and callback ownership passed\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
