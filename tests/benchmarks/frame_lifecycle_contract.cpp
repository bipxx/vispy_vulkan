#include "runtime_frame_lifecycle.hpp"
#include "runtime_query_timing.hpp"
#include "runtime_render_semantics.hpp"
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string_view>

using vispy::frames::Lifecycle;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
template<class F> void rejected(F f, const char* message) {
    bool threw = false; try { f(); } catch (const std::runtime_error&) { threw = true; }
    require(threw, message);
}
int main() {
    try {
        using vispy::render::SnapshotOrigin;
        struct RenderSnapshot {
            SnapshotOrigin origin = SnapshotOrigin::UserDraw;
            bool load_clear = false, depth_clear = false, stencil_clear = false;
            bool framebuffer = false;
        };
        RenderSnapshot attachment_clear{SnapshotOrigin::Clear, true, false, false, false};
        auto shader_clear = attachment_clear;
        // Shader lowering removes attachment clear flags to load untouched
        // channels, yet cannot change the operation recorded by glClear.
        shader_clear.load_clear = shader_clear.depth_clear = shader_clear.stencil_clear = false;
        const auto queued_clear = shader_clear;
        require(std::string_view(vispy::render::pass_kind(queued_clear.origin, queued_clear.framebuffer)) == "clear",
                "shader-backed masked clear remains clear after lowering and immutable queue copy");
        auto framebuffer_clear = queued_clear; framebuffer_clear.framebuffer = true;
        require(std::string_view(vispy::render::pass_kind(framebuffer_clear.origin, true)) == "clear",
                "clear origin takes precedence over framebuffer target classification");
        RenderSnapshot user_draw;
        require(std::string_view(vispy::render::pass_kind(user_draw.origin, false)) == "scene" &&
                std::string_view(vispy::render::pass_kind(user_draw.origin, true)) == "framebuffer",
                "user DRAW retains scene/framebuffer target classification");
        uint64_t scene_draws = 0, physical_draws = 0;
        vispy::render::count_encoded_draw(queued_clear.origin, scene_draws, physical_draws);
        require(scene_draws == 0 && physical_draws == 1,
                "masked clear counts its physical native Draw without inventing a user DRAW");
        vispy::render::count_encoded_draw(user_draw.origin, scene_draws, physical_draws);
        require(scene_draws == 1 && physical_draws == 2,
                "real user DRAW still increments both semantic and physical counters");
        vispy::render::count_encoded_draw(framebuffer_clear.origin, scene_draws, physical_draws);
        require(scene_draws == 1 && physical_draws == 3,
                "framebuffer shader clear also preserves the exact physical counter");
        vispy::frames::AdmissionCapacity single; single.slots = 1; single.owners = 1;
        Lifecycle reservation;
        require(reservation.reserved_unpainted() && single.ready(true) && !single.ready(),
                "one-slot reserved request may paint but cannot admit another measured owner");
        single.gpu_timing = true; single.queries = 1;
        require(single.ready(true, true) && !single.ready(),
                "timed one-slot reservation also admits its own paint rather than deadlocking");
        single.tickets = 1; require(!single.ready(true, true), "reservation cannot discount actual GPU tickets");
        single.tickets = 0; single.queued_batches = 1;
        require(!single.ready(true, true), "reservation cannot discount queued submission batches");
        single.queued_batches = 0; single.completions = single.terminal_limit;
        require(!single.ready(true, true), "full terminal receipt queue still blocks reserved paint");
        single.completions = 0; single.gpu_records = single.terminal_limit;
        require(!single.ready(true, true), "full terminal GPU queue still blocks reserved paint");
        single.gpu_records = 0; single.query_segments = single.query_segment_limit;
        require(!single.ready(true, true), "reserved query cannot discount actual pending maps");
        single.query_segments = 0; single.canvas_gpu_records = single.canvas_gpu_record_limit;
        require(!single.ready(true, true), "full canvas result queue remains bounded");
        single.canvas_gpu_records = 0; reservation.bind_paint(1);
        require(!reservation.reserved_unpainted(), "active paint never receives the unpainted reservation exception");
        Lifecycle closed_reservation; closed_reservation.close(1);
        require(!closed_reservation.reserved_unpainted(), "closed reservation cannot be reused");
        Lifecycle queued_reservation; queued_reservation.enqueue(1);
        require(!queued_reservation.reserved_unpainted(), "admitted queued work is not a fresh paint reservation");
        vispy::frames::AdmissionCapacity available; available.slots = 3; available.tickets = 2; available.owners = 2;
        require(available.ready(), "prior painted tickets may remain in flight when one new owner slot is available");
        available.slots = UINT64_MAX; available.owners = UINT64_MAX; available.terminal_limit = UINT64_MAX;
        available.completions = 1;
        require(!available.ready(true), "admission subtraction does not overflow near uint64 limits");
        Lifecycle checked; checked.generation = 4;
        checked.validate_submission(1, 4);
        require(checked.submissions == 0 && checked.outstanding == 0 && checked.last_ticket == 0,
                "pre-submit validation does not publish a GPU submission");
        rejected([&] { checked.validate_submission(1, 5); }, "generation mismatch rejected before Queue.Submit");
        require(checked.submissions == 0 && checked.outstanding == 0,
                "failed validation leaves ownership/counts unchanged");
        Lifecycle frame; frame.begin_ns = 10; frame.generation = 4; frame.bind_paint(9);
        frame.enqueue(3); frame.begin_batch(); frame.submitted(3, 20, 4); frame.presented(); frame.finish_batch();
        frame.retired(25);
        require(!frame.ready(), "first present/retirement cannot close a paint (timestamps disabled too)");
        frame.enqueue(3); frame.close(30);
        require(!frame.admission_finished(), "closed paint retains queued alpha/final work");
        frame.begin_batch(); frame.submitted(5, 40, 4); frame.presented();
        require(!frame.admission_finished(), "encoding work remains owned"); frame.finish_batch();
        require(frame.admission_finished() && !frame.ready(), "receipt waits for the final owned Ticket");
        frame.retired(50);
        require(frame.ready() && frame.submissions == 2 && frame.presents == 2 && frame.completed_at() == 50,
                "whole paint joins both actual submissions/presents");
        require(frame.last_present_submission_index == 1, "last actual surface presentation index is exact and zero based");
        rejected([&] { frame.presented(); }, "a Ticket cannot count the same surface present twice");
        Lifecycle copies; copies.generation = 1; copies.submitted(1, 2, 1); copies.presented();
        copies.submitted(3, 4, 1); copies.close(6); copies.retired(7); copies.retired(8);
        require(copies.ready() && copies.submissions == 2 && copies.presents == 1 && copies.last_present_submission_index == 0,
                "later copy-only submission remains included without pretending it presented");
        Lifecycle unavailable; unavailable.generation = 3; unavailable.bind_paint(10); unavailable.expect_surface(true);
        unavailable.enqueue(3); unavailable.begin_batch(); unavailable.submitted(1, 10, 3);
        unavailable.presented(); unavailable.finish_batch(); unavailable.retired(15);
        unavailable.enqueue(3); unavailable.enqueue(3); unavailable.close(20);
        unavailable.begin_batch();
        require(unavailable.surface_unavailable(false, "final surface expired"),
                "expired or detached attachment is not mistaken for intentional offscreen paint");
        unavailable.submitted(3, 25, 3); unavailable.finish_batch();
        require(!unavailable.ready(), "unavailable final presentation retains queued and submitted work");
        unavailable.retired(30); require(!unavailable.ready(), "queued work still belongs to failed paint");
        unavailable.begin_batch(); unavailable.finish_batch();
        require(unavailable.ready() && unavailable.status() == "failed" && unavailable.error == "final surface expired" &&
                unavailable.submissions == 2 && unavailable.presents == 1 && unavailable.last_present_submission_index == 0,
                "earlier successful present remains diagnostic but cannot admit failed final acquisition");
        Lifecycle retry; retry.bind_paint(11); retry.expect_surface(true);
        require(retry.failure.empty(), "later repaint independently retries without inherited transient failure");
        Lifecycle offscreen; offscreen.bind_paint(12);
        require(!offscreen.surface_unavailable(false, "no attached surface") && offscreen.failure.empty(),
                "intentional offscreen Qt paint remains admitted");
        Lifecycle direct;
        require(!direct.surface_unavailable(true, "legacy surface unavailable") && direct.failure.empty(),
                "legacy native-present behavior remains unchanged");
        rejected([&] { frame.enqueue(3); }, "closed recording cannot accept later work");
        rejected([&] { frame.submitted(7, 60, 4); }, "closed unqueued work is rejected");
        rejected([&] { frame.retired(70); }, "duplicate retirement is rejected");
        Lifecycle early; early.generation = 2; early.submitted(1, 10, 2); early.retired(15); early.close(25);
        require(early.ready() && early.completed_at() == 25, "paint closure after GPU callback remains in completion boundary");
        Lifecycle ordered; ordered.generation = 2; ordered.submitted(2, 10, 2); ordered.submitted(6, 12, 2);
        ordered.close(15); ordered.retired(30); require(!ordered.ready(), "out-of-order callbacks cannot omit another Ticket");
        ordered.retired(20); require(ordered.ready() && ordered.completed_at() == 30, "latest owned observation retained");
        Lifecycle bounded; bounded.enqueue(1);
        rejected([&] { bounded.enqueue(1); }, "queued work bounded without waits");
        bounded.fail("failed", "first exception"); bounded.fail("cancelled", "abort cleanup");
        bounded.close(8); bounded.discard_queued(1);
        require(bounded.ready() && bounded.status() == "failed" && bounded.error == "first exception", "abort preserves original failure");
        Lifecycle lost; lost.generation = 1; lost.enqueue(1); lost.begin_batch();
        rejected([&] { lost.submitted(1, 3, 2); }, "device generation cannot silently change");
        lost.finish_batch(); lost.fail("device_lost", "actual loss"); lost.close(4);
        require(lost.ready() && lost.status() == "device_lost", "unsubmitted loss is terminal rather than success");
        Lifecycle pending; pending.fail("cancelled", "paint never began"); pending.close(4);
        require(pending.ready() && pending.status() == "cancelled", "unpainted request cancellation is explicit");
        Lifecycle empty; empty.close(5); require(empty.status() == "no_submission", "empty paint is not fabricated GPU completion");
        Lifecycle huge; huge.generation = 1; huge.submissions = UINT64_MAX;
        rejected([&] { huge.submitted(1, 3, 1); }, "submission overflow checked before mutation");
        struct Counters { uint64_t submits, passes, layer_submits; } probe{1, 2, 7};
        vispy::frames::FrozenSubmission<Counters> frozen;
        frozen.capture(3, probe); const auto first_receipt = *frozen.value;
        probe = {2, 4, 9}; frozen.capture(5, probe); probe = {8, 20, 40};
        require(first_receipt.submits == 1 && frozen.value->submits == 2 && frozen.value->passes == 4 &&
                frozen.value->layer_submits == 9, "owned snapshots exclude future callback/submission counters");
        rejected([&] { frozen.capture(5, probe); }, "duplicate snapshot cannot replay newer counters");
        rejected([&] { frozen.capture(3, probe); }, "older ticket cannot replace final snapshot");
        vispy::timing::Frame queries; queries.frame_id = 17; queries.paint_token = 9;
        queries.frame_scope = "qt_paint"; queries.finalized = true;
        queries.submission_count = 3; queries.last_present_submission_index = 1;
        queries.fail(vispy::timing::Status::UnsupportedFeature, "not granted");
        vispy::timing::FrameResult result;
        require(queries.collect(result) && result.frame_id == 17 && result.paint_token == 9 &&
                result.frame_scope == "qt_paint" && result.status == "unsupported_feature" &&
                result.submission_count == 3 && result.last_present_submission_index == 1,
                "even typed unsupported GPU records join the identical paint owner");
        vispy::timing::Frame missing_queries; missing_queries.frame_id = 18; missing_queries.paint_token = 10;
        missing_queries.frame_scope = "qt_paint"; missing_queries.submission_count = 2;
        missing_queries.last_present_submission_index = 0; missing_queries.finalized = true;
        missing_queries.fail(vispy::timing::Status::SubmissionError, unavailable.error);
        require(missing_queries.collect(result) && result.status == "submission_error" &&
                result.paint_token == unavailable.paint_token && result.last_present_submission_index == 0 &&
                result.error == "final surface expired",
                "failed final presentation also rejects GPU admission while preserving the earlier present index");
        auto owner = std::make_shared<Lifecycle>(); std::weak_ptr<Lifecycle> weak = owner;
        std::function<void()> callback = [owner] { owner->close(10); }; owner.reset();
        require(!weak.expired(), "pending callback independently retains frame owner"); callback(); callback = {};
        require(weak.expired(), "callback retirement releases final owner without cycle");
        std::cout << "full paint closure, timestamp-independent joins, FIFO admission, errors/loss and owner lifetime passed\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
