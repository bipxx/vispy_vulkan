#include "runtime.hpp"
#include "command_decode.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <cstdint>
#include <chrono>
#include <cstring>
#include <memory>
#include <stdexcept>

namespace nb = nanobind;

namespace {
using vispy_binding::decode;

nb::object state_query_value(const Value& value) {
    if (value.kind == Value::Kind::Int) return nb::int_(value.i);
    if (value.kind == Value::Kind::Float) return nb::float_(value.f);
    if (value.kind == Value::Kind::List) {
        nb::list items;
        for (const auto& item : value.list) items.append(state_query_value(item));
        return nb::tuple(items);
    }
    throw std::runtime_error("state query: unsupported native return type");
}

nb::dict info_dict(const DeviceInfo& info) {
    nb::dict out;
    out["backend"] = info.backend;
    out["adapter_type"] = info.adapter_type;
    out["vendor"] = info.vendor;
    out["device"] = info.device;
    out["driver"] = info.driver;
    out["vendor_id"] = info.vendor_id;
    out["device_id"] = info.device_id;
    out["max_texture_dimension_1d"] = info.max_texture_1d;
    out["max_texture_dimension_2d"] = info.max_texture_2d;
    out["max_texture_dimension_3d"] = info.max_texture_3d;
    out["max_vertex_attributes"] = info.max_vertex_attributes;
    out["max_vertex_buffers"] = info.max_vertex_buffers;
    out["max_vertex_buffer_array_stride"] = info.max_vertex_buffer_stride;
    out["max_storage_buffers_per_shader_stage"] = info.max_storage_buffers;
    out["max_uniform_buffers_per_shader_stage"] = info.max_uniform_buffers;
    out["max_inter_stage_shader_variables"] = info.max_inter_stage_shader_variables;
    out["max_storage_buffer_binding_size"] = info.max_storage_buffer_size;
    out["max_bindings_per_bind_group"] = info.max_bindings_per_bind_group;
    out["max_compute_invocations_per_workgroup"] = info.max_compute_invocations_per_workgroup;
    out["max_compute_workgroup_size_x"] = info.max_compute_workgroup_size_x;
    out["max_compute_workgroups_per_dimension"] = info.max_compute_workgroups_per_dimension;
    out["max_point_vertex_attributes"] = info.max_point_vertex_attributes;
    out["core_features_and_limits"] = info.core_features_and_limits;
    out["point_input_limit_scope"] = "all active user point inputs share one vertex buffer; exact vertex/instance identities use read-only vertex storage without reserving a user attribute; actual granted attribute/stride/storage/allocation limits apply";
    out["max_samplers_per_shader_stage"] = info.max_samplers;
    out["max_sampled_textures_per_shader_stage"] = info.max_sampled_textures;
    out["max_buffer_size"] = info.max_buffer_size;
    out["max_uniform_buffer_binding_size"] = info.max_uniform_buffer_size;
    out["software"] = info.software;
    out["float32_filterable"] = info.float32_filterable;
    out["unorm16_texture_formats"] = info.unorm16_texture_formats;
    out["bresenham_lines"] = info.bresenham_lines;
    out["last_vertex_provoking"] = info.last_vertex_provoking;
    out["timestamp_query"] = info.timestamp_query;
    out["timestamp_quantization_ns"] = info.timestamp_quantization_ns;
    out["depth_stencil_storage"] = info.depth_stencil_storage;
    out["ok"] = info.ok;
    out["error"] = info.error;
    out["loss_count"] = info.loss_count;
    out["revision"] = runtime_revision();
    return out;
}

nb::dict probe_dict(const Probe& probe) {
    nb::dict out;
    out["application_presents"] = probe.application_presents;
    out["dawn_queue_submits"] = probe.dawn_queue_submits;
    out["vk_queue_submits"] = probe.vk_queue_submits;
    out["texture_uploads"] = probe.texture_uploads;
    out["buffer_uploads"] = probe.buffer_uploads;
    out["pipeline_misses"] = probe.pipeline_misses;
    out["pipeline_hits"] = probe.pipeline_hits;
    out["presentation_passes"] = probe.presentation_passes;
    out["finish_calls"] = probe.finish_calls;
    out["copy_bytes"] = probe.copy_bytes;
    out["completion_waits"] = probe.completion_waits;
    out["pending_tickets"] = probe.pending_tickets;
    out["retired_tickets"] = probe.retired_tickets;
    out["live_buffer_bytes"] = probe.live_buffer_bytes;
    out["live_cpu_buffer_bytes"] = probe.live_cpu_buffer_bytes;
    out["live_texture_bytes"] = probe.live_texture_bytes;
    out["deferred_frames"] = probe.deferred_frames;
    out["queued_frames"] = probe.queued_frames;
    out["buffer_allocations"] = probe.buffer_allocations;
    out["texture_allocations"] = probe.texture_allocations;
    out["uniform_upload_bytes"] = probe.uniform_upload_bytes;
    out["texture_upload_bytes"] = probe.texture_upload_bytes;
    out["geometry_upload_bytes"] = probe.geometry_upload_bytes;
    out["point_conversion_builds"] = probe.point_conversion_builds;
    out["point_conversion_bytes"] = probe.point_conversion_bytes;
    out["canvas_texture_bytes"] = probe.canvas_texture_bytes;
    out["transient_buffer_bytes"] = probe.transient_buffer_bytes;
    out["draw_calls"] = probe.draw_calls;
    out["artifact_cache_entries"] = probe.artifact_cache_entries;
    out["pipeline_cache_entries"] = probe.pipeline_cache_entries;
    out["portable_shader_hits"] = probe.portable_shader_hits;
    out["portable_shader_misses"] = probe.portable_shader_misses;
    out["portable_shader_bytes"] = probe.portable_shader_bytes;
    out["shader_cache_bytes"] = probe.shader_cache_bytes;
    out["shader_cache_limit"] = probe.shader_cache_limit;
    out["live_portable_shader_bytes"] = probe.live_portable_shader_bytes;
    out["uncached_live_portable_shader_bytes"] = probe.uncached_live_portable_shader_bytes;
    out["live_line_evaluator_bytes"] = probe.live_line_evaluator_bytes;
    out["uncached_live_line_evaluator_bytes"] = probe.uncached_live_line_evaluator_bytes;
    out["live_line_consumer_bytes"] = probe.live_line_consumer_bytes;
    out["uncached_live_line_consumer_bytes"] = probe.uncached_live_line_consumer_bytes;
    out["live_device_shader_bytes"] = probe.live_device_shader_bytes;
    out["uncached_live_device_shader_bytes"] = probe.uncached_live_device_shader_bytes;
    out["line_evaluator_hits"] = probe.line_evaluator_hits;
    out["line_evaluator_misses"] = probe.line_evaluator_misses;
    out["line_consumer_hits"] = probe.line_consumer_hits;
    out["line_consumer_misses"] = probe.line_consumer_misses;
    out["line_resource_pool_slots"] = probe.line_resource_pool_slots;
    out["line_resource_pool_busy_slots"] = probe.line_resource_pool_busy_slots;
    out["line_resource_pool_bytes"] = probe.line_resource_pool_bytes;
    out["line_resource_pool_hits"] = probe.line_resource_pool_hits;
    out["line_resource_pool_evictions"] = probe.line_resource_pool_evictions;
    out["line_resource_pool_deferrals"] = probe.line_resource_pool_deferrals;
    out["device_generation"] = probe.device_generation;
    out["bresenham_line_pipelines"] = probe.bresenham_line_pipelines;
    out["last_vertex_pipelines"] = probe.last_vertex_pipelines;
    out["binding_decode_ns"] = probe.binding_decode_ns;
    out["binding_decode_bytes"] = probe.binding_decode_bytes;
    out["owned_upload_captures"] = probe.owned_upload_captures;
    out["owned_upload_capture_bytes"] = probe.owned_upload_capture_bytes;
    out["owned_upload_fallback_dtypes"] = probe.owned_upload_fallback_dtypes;
    out["owned_upload_fallback_exports"] = probe.owned_upload_fallback_exports;
    out["owned_texture_transfers"] = probe.owned_texture_transfers;
    out["owned_texture_transfer_bytes"] = probe.owned_texture_transfer_bytes;
    out["native_batches"] = probe.native_batches;
    out["native_commands"] = probe.native_commands;
    out["native_interpret_ns"] = probe.native_interpret_ns;
    out["native_submit_ns"] = probe.native_submit_ns;
    out["texture_conversion_ns"] = probe.texture_conversion_ns;
    out["texture_upload_cpu_ns"] = probe.texture_upload_cpu_ns;
    out["buffer_upload_cpu_ns"] = probe.buffer_upload_cpu_ns;
    out["shader_cache_lookup_ns"] = probe.shader_cache_lookup_ns;
    out["shader_normalize_ns"] = probe.shader_normalize_ns;
    out["shader_parse_ns"] = probe.shader_parse_ns;
    out["shader_link_ns"] = probe.shader_link_ns;
    out["shader_spirv_ns"] = probe.shader_spirv_ns;
    out["shader_reflect_ns"] = probe.shader_reflect_ns;
    out["shader_cpu_build_ns"] = probe.shader_cpu_build_ns;
    out["device_cache_lookup_ns"] = probe.device_cache_lookup_ns;
    out["pipeline_cache_lookup_ns"] = probe.pipeline_cache_lookup_ns;
    out["shader_module_creation_ns"] = probe.shader_module_creation_ns;
    out["pipeline_creation_ns"] = probe.pipeline_creation_ns;
    out["shader_normalizations"] = probe.shader_normalizations;
    out["shader_parse_calls"] = probe.shader_parse_calls;
    out["shader_link_calls"] = probe.shader_link_calls;
    out["shader_spirv_stages"] = probe.shader_spirv_stages;
    out["shader_module_creations"] = probe.shader_module_creations;
    out["render_pipeline_creations"] = probe.render_pipeline_creations;
    out["compute_pipeline_creations"] = probe.compute_pipeline_creations;
    out["render_passes"] = probe.render_passes;
    out["compute_passes"] = probe.compute_passes;
    out["command_encoders"] = probe.command_encoders;
    out["bind_group_creations"] = probe.bind_group_creations;
    out["native_draw_calls"] = probe.native_draw_calls;
    out["line_endpoint_dispatches"] = probe.line_endpoint_dispatches;
    out["line_endpoint_rows"] = probe.line_endpoint_rows;
    out["line_endpoint_conversion_builds"] = probe.line_endpoint_conversion_builds;
    out["line_endpoint_conversion_bytes"] = probe.line_endpoint_conversion_bytes;
    out["line_endpoint_upload_bytes"] = probe.line_endpoint_upload_bytes;
    out["vertex_input_conversion_builds"] = probe.vertex_input_conversion_builds;
    out["vertex_input_conversion_bytes"] = probe.vertex_input_conversion_bytes;
    out["vertex_input_current_entries"] = probe.vertex_input_current_entries;
    out["vertex_input_current_bytes"] = probe.vertex_input_current_bytes;
    out["vertex_input_cache_entries"] = probe.vertex_input_cache_entries;
    out["vertex_input_cache_bytes"] = probe.vertex_input_cache_bytes;
    out["vertex_input_oversized_entries"] = probe.vertex_input_oversized_entries;
    out["vertex_input_oversized_bytes"] = probe.vertex_input_oversized_bytes;
    out["vertex_input_oversized_entry_limit"] = probe.vertex_input_oversized_entry_limit;
    out["vertex_input_oversized_byte_limit"] = probe.vertex_input_oversized_byte_limit;
    out["vertex_input_oversized_evictions"] = probe.vertex_input_oversized_evictions;
    out["timestamp_query_sets"] = probe.timestamp_query_sets;
    out["timestamp_resolves"] = probe.timestamp_resolves;
    out["timestamp_readbacks"] = probe.timestamp_readbacks;
    out["pending_timestamp_frames"] = probe.pending_timestamp_frames;
    out["peak_pending_timestamp_frames"] = probe.peak_pending_timestamp_frames;
    out["pending_draws"] = probe.pending_draws;
    out["peak_pending_tickets"] = probe.peak_pending_tickets;
    out["peak_queued_frames"] = probe.peak_queued_frames;
    out["peak_pending_draws"] = probe.peak_pending_draws;
    out["peak_shader_cache_bytes"] = probe.peak_shader_cache_bytes;
    out["descriptor_samples"] = probe.descriptor_samples;
    out["sampled_peak_live_buffer_bytes"] = probe.sampled_peak_live_buffer_bytes;
    out["sampled_peak_live_cpu_buffer_bytes"] = probe.sampled_peak_live_cpu_buffer_bytes;
    out["sampled_peak_live_texture_bytes"] = probe.sampled_peak_live_texture_bytes;
    out["frame_slots"] = probe.frame_slots;
    out["vk_memory_available"] = probe.vk_memory_available;
    out["vk_memory_complete"] = probe.vk_memory_complete;
    out["vk_memory_active_devices"] = probe.vk_memory_active_devices;
    out["vk_memory_tracking_devices"] = probe.vk_memory_tracking_devices;
    out["vk_memory_allocate_calls"] = probe.vk_memory_allocate_calls;
    out["vk_memory_allocate_failures"] = probe.vk_memory_allocate_failures;
    out["vk_memory_allocation_count"] = probe.vk_memory_allocation_count;
    out["vk_memory_allocated_bytes"] = probe.vk_memory_allocated_bytes;
    out["vk_memory_free_calls"] = probe.vk_memory_free_calls;
    out["vk_memory_free_count"] = probe.vk_memory_free_count;
    out["vk_memory_freed_bytes"] = probe.vk_memory_freed_bytes;
    out["vk_memory_null_free_calls"] = probe.vk_memory_null_free_calls;
    out["vk_memory_unknown_free_calls"] = probe.vk_memory_unknown_free_calls;
    out["vk_memory_live_allocations"] = probe.vk_memory_live_allocations;
    out["vk_memory_live_bytes"] = probe.vk_memory_live_bytes;
    out["vk_memory_peak_live_allocations"] = probe.vk_memory_peak_live_allocations;
    out["vk_memory_peak_live_bytes"] = probe.vk_memory_peak_live_bytes;
    out["vk_memory_retired_allocations"] = probe.vk_memory_retired_allocations;
    out["vk_memory_retired_bytes"] = probe.vk_memory_retired_bytes;
    out["vk_memory_tracking_errors"] = probe.vk_memory_tracking_errors;
    out["allocation_accounting"] = "renderer-owned resource descriptor bytes; excludes driver padding and opaque depth backing";
    return out;
}

nb::dict ownership_dict(const vispy::lines::LineOwnershipSnapshot& value) {
    using Snapshot = vispy::lines::LineOwnershipSnapshot;
    nb::dict out, limits, pool, counters;
    out["schema"] = "line_ownership_v1";
    out["canvas_id"] = value.canvas_id;
    out["generation"] = value.generation;
    out["poll_performed"] = false;
    out["device_initialized"] = false;
    out["records_drained"] = false;
    out["truncated"] = false;
    out["ticket_scope"] = "engine";
    out["pool_scope"] = "engine";
    out["query_scope"] = "engine";
    out["capture_scope"] = "canvas";
    out["frame_scope"] = "canvas";
    out["queue_scope"] = "canvas";
    out["capture_charge_scope"] = "engine";
    out["capture_charge_bytes"] = value.capture_charge_bytes;
    out["diagnostic_control_capacity_bytes"] = value.allocated_control_bytes();
    out["diagnostic_control_usage_bytes"] = value.control_capacity_bytes();
    out["diagnostic_control_limit"] = Snapshot::max_control_bytes;
    out["diagnostic_accounting"] = "bounded C++ value storage; usage overlaps reserved arena; excludes Python, allocator headers, stack and driver memory";
    limits["frame_slots"] = value.frame_slots;
    limits["pool_slots"] = value.pool_limits.max_slots;
    limits["captures"] = Snapshot::max_captures;
    limits["terminal_records"] = value.terminal_record_limit;
    limits["observed_frames"] = Snapshot::max_frames;
    limits["pool_owned_bytes"] = value.pool_limits.owned_capacity_bytes;
    limits["pool_control_bytes"] = value.pool_limits.control_bytes;
    out["limits"] = limits;
    pool["slots"] = value.pool.slots;
    pool["busy_slots"] = value.pool.busy_slots;
    pool["owned_capacity_bytes"] = value.pool.owned_capacity_bytes;
    pool["control_bytes"] = value.pool.control_bytes;
    out["pool"] = pool;
#define EXPORT_OWNERSHIP_COUNTER(name) counters[#name] = value.counters.name
    EXPORT_OWNERSHIP_COUNTER(dawn_queue_submits);
    EXPORT_OWNERSHIP_COUNTER(draw_calls);
    EXPORT_OWNERSHIP_COUNTER(line_endpoint_dispatches);
    EXPORT_OWNERSHIP_COUNTER(line_endpoint_rows);
    EXPORT_OWNERSHIP_COUNTER(compute_passes);
    EXPORT_OWNERSHIP_COUNTER(retired_tickets);
    EXPORT_OWNERSHIP_COUNTER(successful_ticket_retirements);
    EXPORT_OWNERSHIP_COUNTER(failed_ticket_retirements);
    EXPORT_OWNERSHIP_COUNTER(completion_waits);
    EXPORT_OWNERSHIP_COUNTER(finish_calls);
    EXPORT_OWNERSHIP_COUNTER(timestamp_query_sets);
    EXPORT_OWNERSHIP_COUNTER(timestamp_resolves);
    EXPORT_OWNERSHIP_COUNTER(timestamp_readbacks);
    EXPORT_OWNERSHIP_COUNTER(query_map_callbacks_completed);
    EXPORT_OWNERSHIP_COUNTER(buffer_allocations);
    EXPORT_OWNERSHIP_COUNTER(bind_group_creations);
    EXPORT_OWNERSHIP_COUNTER(line_resource_pool_hits);
    EXPORT_OWNERSHIP_COUNTER(line_resource_pool_evictions);
    EXPORT_OWNERSHIP_COUNTER(line_resource_pool_deferrals);
    EXPORT_OWNERSHIP_COUNTER(deferred_frames);
    EXPORT_OWNERSHIP_COUNTER(uniform_upload_bytes);
    EXPORT_OWNERSHIP_COUNTER(line_endpoint_conversion_builds);
    EXPORT_OWNERSHIP_COUNTER(line_endpoint_conversion_bytes);
    EXPORT_OWNERSHIP_COUNTER(line_endpoint_upload_bytes);
#undef EXPORT_OWNERSHIP_COUNTER
    out["counters"] = counters;
    auto slots = [](const auto& rows) {
        nb::list result;
        for (const auto& row : rows) {
            nb::dict item;
            item["slot_id"] = row.slot_id; item["generation"] = row.generation;
            switch (row.state) {
                case vispy::lines::PoolSlotState::Idle: item["state"] = "idle"; break;
                case vispy::lines::PoolSlotState::Reserved: item["state"] = "reserved"; break;
                case vispy::lines::PoolSlotState::Submitted: item["state"] = "submitted"; break;
                default: throw std::logic_error("line ownership: invalid slot state");
            }
            item["output_capacity"] = row.capacities.output;
            item["compute_ubo_capacity"] = row.capacities.compute_ubo;
            item["render_ubo_capacity"] = row.capacities.render_ubo;
            item["extra_control_bytes"] = row.extra_control_bytes;
            result.append(item);
        }
        return result;
    };
    out["slots"] = slots(value.slots);
    out["external_slots"] = slots(value.external_slots);
    auto ids = [](const auto& values) {
        nb::list result;
        for (auto id : values) result.append(id);
        return result;
    };
    auto string = [](const auto& text) { return nb::str(text.data(), text.size()); };
    nb::list tickets, queued, captures, segments, frames;
    for (const auto& row : value.tickets) {
        nb::dict item;
        item["canvas_id"] = row.canvas_id;
        item["ticket_id"] = row.ticket_id; item["generation"] = row.generation;
        item["frame_id"] = row.frame_id; item["paint_token"] = row.paint_token;
        item["callback_complete"] = row.callback_complete; item["callback_ok"] = row.callback_ok;
        item["retirement_processed"] = row.retirement_processed;
        item["has_encoding_validation"] = row.has_encoding_validation;
        item["encoding_validation_complete"] = row.encoding_validation_complete;
        item["encoding_validation_ok"] = row.encoding_validation_ok;
        item["error"] = string(row.error); item["validation_error"] = string(row.validation_error);
        item["slot_ids"] = ids(row.slot_ids);
        tickets.append(item);
    }
    for (const auto& row : value.queued) {
        nb::dict item;
        item["queue_id"] = row.queue_id; item["generation"] = row.generation;
        item["frame_id"] = row.frame_id; item["paint_token"] = row.paint_token;
        item["draw_count"] = row.draw_count; item["capture_ids"] = ids(row.capture_ids);
        queued.append(item);
    }
    for (const auto& row : value.captures) {
        nb::dict item;
        item["canvas_id"] = row.canvas_id;
        item["capture_id"] = row.capture_id; item["ticket_id"] = row.ticket_id;
        item["frame_id"] = row.frame_id; item["paint_token"] = row.paint_token;
        item["generation"] = row.generation; item["ticket_finished"] = row.ticket_finished;
        item["charged_bytes"] = row.charged_bytes; item["readback_capacity"] = row.readback_capacity;
        item["status"] = string(row.status); item["error"] = string(row.error);
        captures.append(item);
    }
    for (const auto& row : value.query_segments) {
        nb::dict item;
        item["canvas_id"] = row.canvas_id;
        item["ticket_id"] = row.ticket_id; item["generation"] = row.generation;
        item["frame_id"] = row.frame_id; item["paint_token"] = row.paint_token;
        item["submission_index"] = row.submission_index;
        item["resolve_capacity"] = row.resolve_capacity; item["readback_capacity"] = row.readback_capacity;
        item["map_requested"] = row.map_requested; item["map_callback_complete"] = row.map_callback_complete;
        segments.append(item);
    }
    for (const auto& row : value.frames) {
        nb::dict item;
        item["frame_id"] = row.frame_id; item["paint_token"] = row.paint_token;
        item["generation"] = row.generation; item["gpu_timing"] = row.gpu_timing;
        item["closed"] = row.closed; item["receipt_emitted"] = row.receipt_emitted;
        item["gpu_result_emitted"] = row.gpu_result_emitted;
        item["submissions"] = row.submissions; item["outstanding"] = row.outstanding;
        item["queued_batches"] = row.queued_batches;
        item["failure"] = string(row.failure); item["error"] = string(row.error);
        frames.append(item);
    }
    out["tickets"] = tickets; out["queued"] = queued; out["captures"] = captures;
    out["query_segments"] = segments; out["frames"] = frames;
    return out;
}

}  // namespace

static nb::dict memory_window_dict(const VulkanMemoryWindow& window) {
    nb::dict out, counters;
    const char* status = "unknown";
    switch (window.status) {
    case VulkanMemoryWindowStatus::Unavailable: status = "unavailable"; break;
    case VulkanMemoryWindowStatus::Active: status = "active"; break;
    case VulkanMemoryWindowStatus::Complete: status = "complete"; break;
    case VulkanMemoryWindowStatus::Incomplete: status = "incomplete"; break;
    case VulkanMemoryWindowStatus::Overlap: status = "overlap"; break;
    case VulkanMemoryWindowStatus::InvalidToken: status = "invalid_token"; break;
    case VulkanMemoryWindowStatus::TokenExhausted: status = "token_exhausted"; break;
    case VulkanMemoryWindowStatus::Cancelled: status = "cancelled"; break;
    case VulkanMemoryWindowStatus::Busy: status = "busy"; break;
    }
    out["schema"] = window.schema; out["token"] = window.token; out["status"] = status;
    out["supported"] = window.supported != 0; out["available"] = window.available != 0;
    out["complete"] = window.complete != 0; out["invalidations"] = window.invalidations;
    out["seed_live_allocations"] = window.seed_live_allocations; out["seed_live_bytes"] = window.seed_live_bytes;
#define VISPY_WINDOW_FIELD(field) counters[#field] = window.counters.field
    VISPY_WINDOW_FIELD(allocate_calls); VISPY_WINDOW_FIELD(allocate_failures);
    VISPY_WINDOW_FIELD(allocation_count); VISPY_WINDOW_FIELD(allocated_bytes);
    VISPY_WINDOW_FIELD(free_calls); VISPY_WINDOW_FIELD(free_count); VISPY_WINDOW_FIELD(freed_bytes);
    VISPY_WINDOW_FIELD(null_free_calls); VISPY_WINDOW_FIELD(unknown_free_calls);
    VISPY_WINDOW_FIELD(retired_allocations); VISPY_WINDOW_FIELD(retired_bytes); VISPY_WINDOW_FIELD(tracking_errors);
    VISPY_WINDOW_FIELD(live_allocations); VISPY_WINDOW_FIELD(live_bytes);
    VISPY_WINDOW_FIELD(peak_live_allocations); VISPY_WINDOW_FIELD(peak_live_bytes);
#undef VISPY_WINDOW_FIELD
    out["counters"] = counters;
    out["scope"] = "process-wide intercepted Vulkan device-memory allocationSize totals; event-level measured window including seeded tracked handles; not physical residency, imported payload size, or opaque driver allocations";
    return out;
}

NB_MODULE(_dawn, m) {
    m.attr("submission_contract_version") = 1;
    m.attr("state_query_contract_version") = 1;
    m.def("_capture_upload", &vispy_binding::capture_upload);
    m.def("revision", &runtime_revision);
    m.def("device_info", []() { return info_dict(ensure_device()); });
    m.def("probe", []() { return probe_dict(probe_counters()); });
    m.def("diagnostic_peek_line_ownership", [](int canvas_id) {
        return ownership_dict(diagnostic_peek_line_ownership(canvas_id));
    }, nb::arg("canvas_id"));
    m.def("layer_vk_submit_count", &layer_submit_count);
    m.def("register_canvas", &register_canvas, nb::arg("width"), nb::arg("height"),
          nb::arg("samples"), nb::arg("vsync") = false);
    m.def("configure_canvas", &configure_canvas);
    m.def("framebuffer_config", [](int canvas_id) {
        const auto config = framebuffer_config(canvas_id);
        nb::dict out;
        out["red_size"] = config.red_size;
        out["green_size"] = config.green_size;
        out["blue_size"] = config.blue_size;
        out["alpha_size"] = config.alpha_size;
        if (config.depth_size) out["depth_size"] = *config.depth_size;
        else out["depth_size"] = nb::none();
        out["depth_size_minimum"] = config.depth_size_minimum;
        out["depth_size_exact"] = config.depth_size_exact;
        out["stencil_size"] = config.stencil_size;
        out["backing_depth_size_minimum"] = config.backing_depth_size_minimum;
        out["backing_stencil_size"] = config.backing_stencil_size;
        out["sample_count"] = config.sample_count;
        out["samples"] = config.samples;
        out["double_buffer"] = config.double_buffer;
        out["stereo"] = config.stereo;
        out["srgb"] = config.srgb;
        out["has_depth_attachment"] = config.has_depth_attachment;
        out["has_stencil_attachment"] = config.has_stencil_attachment;
        out["framebuffer_id"] = config.framebuffer_id;
        out["width"] = config.width;
        out["height"] = config.height;
        out["color_format"] = config.color_format;
        out["depth_stencil_format"] = config.depth_stencil_format;
        out["configuration_source"] = config.configuration_source;
        return out;
    }, nb::arg("canvas_id"));
    m.def("destroy_canvas", &destroy_canvas);
    m.def("set_surface", &set_surface);
    m.def("set_surface_win32", &set_surface);
    m.def("set_surface_x11", &set_surface_x11, nb::arg("canvas_id"), nb::arg("display"),
          nb::arg("window"), nb::arg("owned_display") = false);
    m.def("set_surface_metal_view", &set_surface_metal_view);
    m.def("clear_surface", &clear_surface);
    m.def("update_surface_scale", &update_surface_scale);
    m.def("execute", [](int canvas_id, nb::list commands, nb::list arrays) {
        const auto started = std::chrono::steady_clock::now();
        uint64_t decoded_bytes = 0;
        auto decoded = decode(commands, arrays, decoded_bytes);
        const uint64_t decode_ns = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now() - started).count());
        execute_commands(canvas_id, decoded, decode_ns, decoded_bytes);
    });
    m.def("_execute_owned", [](int canvas_id, nb::list commands, nb::list arrays, nb::dict stats) {
        const auto started = std::chrono::steady_clock::now();
        uint64_t decoded_bytes = 0;
        auto decoded = decode(commands, arrays, decoded_bytes, true);
        UploadCaptureStats capture;
        capture.captures = nb::cast<uint64_t>(stats["captures"]);
        capture.bytes = nb::cast<uint64_t>(stats["bytes"]);
        capture.fallback_dtypes = nb::cast<uint64_t>(stats["fallback_dtypes"]);
        capture.fallback_exports = nb::cast<uint64_t>(stats["fallback_exports"]);
        const uint64_t decode_ns = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now() - started).count());
        execute_owned_commands(canvas_id, std::move(decoded), decode_ns, decoded_bytes, capture);
    });
    m.def("finish", &finish_canvas);
    m.def("present", &present_canvas);
    m.def("process_events", &process_events);
    m.def("viewport", &canvas_viewport);
    m.def("state_parameter", [](int canvas_id, int pname) {
        return state_query_value(canvas_state_parameter(canvas_id, pname));
    }, nb::arg("canvas_id"), nb::arg("pname"));
    m.def("frame_ready", &frame_ready);
    m.def("benchmark_frame_request_ready", &benchmark_frame_request_ready);
    m.def("configure_frame_slots", &configure_frame_slots);
    m.def("diagnostic_submission_controls", &diagnostic_submission_controls,
          nb::arg("hold_completions") = false, nb::arg("fail_once") = "");
    m.def("configure_shader_cache", &configure_shader_cache, nb::arg("entries"), nb::arg("bytes"));
    m.def("benchmark_begin_frame", &benchmark_begin_frame);
    m.def("benchmark_memory_window_begin", []() {
        const auto window = benchmark_memory_window_begin();
        try { return memory_window_dict(window); }
        catch (...) {
            // A Python allocation failure must not orphan an active native
            // token before the caller has received its ownership receipt.
            if (window.status == VulkanMemoryWindowStatus::Active && window.token) {
                try { benchmark_memory_window_end(window.token, true); } catch (...) {}
            }
            throw;
        }
    });
    m.def("benchmark_memory_window_end", [](nb::handle token, bool cancel) {
        if (!nb::isinstance<nb::int_>(token) || nb::isinstance<nb::bool_>(token))
            throw nb::type_error("allocation window token must be an exact unsigned integer");
        return memory_window_dict(benchmark_memory_window_end(nb::cast<uint64_t>(token), cancel));
    }, nb::arg("token"), nb::arg("cancel") = false);
    m.def("begin_canvas_paint", &begin_canvas_paint, nb::arg("canvas_id"));
    m.def("end_canvas_paint", &end_canvas_paint, nb::arg("canvas_id"), nb::arg("token"));
    m.def("abort_canvas_paint", &abort_canvas_paint, nb::arg("canvas_id"), nb::arg("token"), nb::arg("reason"));
    m.def("benchmark_cancel_frame", &benchmark_cancel_frame, nb::arg("canvas_id"), nb::arg("frame_id"), nb::arg("reason"));
    m.def("benchmark_submit_intermediate", &benchmark_submit_intermediate);
    m.def("benchmark_configure_gpu_timing", [](int canvas_id, bool enabled) {
        benchmark_configure_gpu_timing(canvas_id, enabled);
        auto device = ensure_device();
        const auto probe = probe_counters();
        nb::dict info;
        info["enabled"] = enabled;
        info["supported"] = device.ok && device.timestamp_query;
        info["quantization_ns"] = device.timestamp_quantization_ns;
        info["max_queries_per_frame"] = vispy::timing::max_queries_per_frame;
        info["max_submissions_per_frame"] = vispy::timing::max_submissions_per_frame;
        info["pending_limit"] = probe.frame_slots;
        info["device_generation"] = probe.device_generation;
        info["scope"] = "all recorded compute/render/presentation pass pairs across frame submissions; span encloses pass intervals; excludes uploads before first pass, query resolve/readback, diagnostic quality readback, presentation engine and scanout; pass intervals may overlap";
        return info;
    }, nb::arg("canvas_id"), nb::arg("enabled") = true);
    m.def("benchmark_gpu_timings", [](int canvas_id) {
        nb::list records;
        for (const auto& sample : benchmark_gpu_timings(canvas_id)) {
            nb::dict item;
            item["frame_id"] = sample.frame_id;
            item["paint_token"] = sample.paint_token;
            item["last_present_submission_index"] = sample.last_present_submission_index;
            item["frame_scope"] = sample.frame_scope;
            item["device_generation"] = sample.device_generation;
            item["quantization_ns"] = sample.quantization_ns;
            item["submission_count"] = sample.submission_count;
            item["status"] = sample.status;
            item["error"] = sample.error;
            item["render_span_ns"] = sample.render_span_ns;
            item["pass_sum_ns"] = sample.pass_sum_ns;
            nb::list passes;
            for (const auto& pass : sample.passes) {
                nb::dict row;
                row["submission_index"] = pass.submission_index;
                row["kind"] = pass.kind;
                row["begin_ns"] = pass.begin_ns;
                row["end_ns"] = pass.end_ns;
                row["elapsed_ns"] = pass.elapsed_ns;
                passes.append(row);
            }
            item["passes"] = passes;
            records.append(item);
        }
        return records;
    });
    m.def("benchmark_telemetry_info", []() {
        const auto device = ensure_device();
        nb::dict info;
        info["counter_capture"] = "submission";
        info["capture_scope"] = "copied after the last actual owned Ticket submission and its surface-presentation attempt, if any; cumulative engine observations at that boundary, excluding later callbacks and submissions; unsubmitted terminal frames have no counter snapshot";
        info["frame_ownership_scope"] = "whole_qt_paint_v1";
        info["terminal_record_limit"] = 4096;
        info["terminal_canvas_tombstones"] = 128;
        info["terminal_record_scope"] = "separate bounded receipt and GPU-record queues survive canvas teardown; recent empty canvas IDs retain at most 128 tombstones";
        info["timing_clock"] = "steady_clock monotonic host wall nanoseconds";
        info["timings_enabled"] = "always";
        info["timing_scope"] = "inclusive host intervals overlap and cannot be summed; excludes engine mutex acquisition; not CPU thread, GPU, or scanout time";
        info["binding_decode_scope"] = "nanobind command conversion, legacy bytes copies and owned snapshot transfers; bytes count logical payload size, not physical copies or Python GLIR packing/capture; owned capture counts/bytes and fallback reasons are separate; scopes overlap";
        info["shader_stage_scope"] = "actual compiler calls only; retained historical timings are never added on cache hits or portable recovery; SPIR-V includes emission, validation and compatibility passes; reflection includes live resource stage masks and physical uniform layout";
        info["cache_lookup_scope"] = "identity/lookup/admission host time excluding portable compilation; pipeline lookup excludes pipeline creation";
        info["creation_scope"] = "native API invocation counts, including attempts rejected by validation; module/pipeline host calls and existing pipeline validation checks";
        info["draw_scope"] = "draw_calls counts encoded user GLIR DRAW snapshots; native_draw_calls additionally includes shader-backed masked/scissored clears, presentation and depth capture draws; clear pass labels retain glClear origin independently of attachment load operations";
        info["compute_scope"] = "compute_passes counts actual encoded compute passes; line_endpoint_dispatches counts actual encoded endpoint DispatchWorkgroups calls; line_endpoint_rows counts valid logical endpoint rows, excluding padded invocations";
        info["line_resource_pool_scope"] = "sampled resident native pool slots, busy slots and charged resident bytes for owned endpoint output buffers, compute and paired-render uniform buffers, key/slot/control capacities, and the bounded shared diagnostic canary template; the template's actual allocation is included in sampled bytes and its maximum 64 KiB capacity is reserved within the owned-buffer ceiling; temporary transactional staging is bounded separately and excluded from resident pool bytes; borrowed and staged native handles are deduplicated with existing logical resource gauges, which overlap this pool view and cannot be added to it; diagnostic staging readback and retained raw/logical capture bytes are separate ownership; cumulative hits count actual idle-slot owned-capacity reuse, evictions count policy idle victims actually removed, and deferrals count reservations unavailable due to busy ownership, independently of frame-ring deferral; excludes CPU evaluator/consumer allocations and physical driver memory; no hardware qualification claim";
        info["buffer_upload_scope"] = "buffer_upload_cpu_ns includes transient uniform allocation/write/padding and resident geometry allocation/write; buffer_uploads and geometry_upload_bytes count revision geometry only; uniform_upload_bytes separately reports transient uniform payloads; warmed uniform changes can add upload host time without geometry reupload";
        info["point_conversion_scope"] = "new owned CPU point identity/packed user payloads only; resident reuse and device-loss CPU reuse add no conversions; actual native uploads remain buffer_uploads/geometry_upload_bytes";
        info["vertex_input_conversion_scope"] = "new owned ordinary input/index/topology/selection-bound and batch CPU payloads only; cached capacity decisions do not count as payload conversions; grouped direct views do not copy user payloads; resident/loss CPU reuse adds no conversions; GPU uploads remain buffer_uploads/geometry_upload_bytes";
        info["vertex_input_cache_scope"] = "per-Program historical cache has at most 128 ordinary records and 64 MiB CPU vector/key capacities plus declared record/control/node bookkeeping; eviction uses unordered-map iteration, not recency; allocator headers and bucket padding are excluded; source parents are not retained; oversized records skip historical admission";
        info["vertex_input_current_scope"] = "per-Program nine current exact-key owners (six ordinary: index widening, topology, bounds, selection with owned child indices, vertex, instance; plus line endpoint, ordered batch, compact-fit decision) are outside the historical budget, including legal oversized records; all nine share the same historical and oversized working budgets; current_entries/current_bytes and cache_entries/cache_bytes are overlapping sampled owner views across Programs, not additive; current bytes include occupied-slot/key/record/control/child-map bookkeeping with retained record subtrees deduplicated; empty inline slots and allocator headers are excluded; pending/in-flight owners are outside both views; live_cpu_buffer_bytes deduplicates all actual retained vector capacities and live_buffer_bytes all actual retained GPU buffers; current categories replace on successful lookup/build and do not promise arbitrary alternating oversized reuse";
        info["vertex_input_oversized_scope"] = "additional per-Program oversized working history shared by all nine categories (six ordinary plus line endpoint, ordered batch and compact-fit decision): at most 8 entries and 256 MiB occupied entry/key/record/control/child bookkeeping and CPU vector capacities; shared record/child subgraphs counted once; least-recently-used capacity eviction, with current hits refreshing recency; actual DATA/SIZE/DELETE/ATTRIBUTE/LINK or source-stamp invalidation drops dependent categories and permits rebuilding; unchanged source stamps and DRAW selection alternation within admitted budget preserve exact owned children and uploaded resources; over-budget records skip admission but may remain current; evictions counts capacity removals cumulatively, not invalidations; entry/byte gauges aggregate live Programs and overlap current/history/pending owners, so views are not additive; excludes empty container, allocator headers/bucket padding, texture shadows and physical driver memory";
        info["cpu_buffer_scope"] = "deduplicated BufferRev CPU vector capacities reachable through live objects, derived caches, pending/queued snapshots and in-flight tickets; excludes keys/container/allocator overhead, texture shadows and driver allocations; sampled peak uses these same ownership checkpoints";
        info["descriptor_peak_scope"] = "sampled at explicit probe and marked submission; retained renderer-owned descriptor bytes, excluding driver padding, opaque depth backing, and capture temporaries outside the retained graph";
        info["work_peak_scope"] = "renderer pending tickets, queued submission batches, retained draw/clear snapshots and bounded shader cache bytes; not full driver/allocator peaks";
        info["completion_scope"] = "Qt paint closure and all owned queued/render/presentation work callback observations, or legacy direct-native present closure; terminal cancellation/loss does not claim GPU completion; excludes scanout; no deliberate wait or present added by telemetry";
        info["surface_acquisition_scope"] = "unavailable requested attached Qt surface fails that paint owner and GPU record; earlier successful presents remain diagnostic; submitted work retires normally and later repaints may retry; intentional offscreen/no-surface native behavior is unchanged";
        info["gpu_timestamps_available"] = device.ok && device.timestamp_query;
        info["gpu_timing_collection"] = "per-canvas opt-in, off by default";
        info["gpu_timestamp_quantization_ns"] = device.timestamp_quantization_ns;
        info["gpu_timestamp_clock"] = "device timestamps converted to nanoseconds by Dawn; unrelated to host steady_clock or scanout clock";
        info["gpu_timing_scope"] = "recorded compute/render/presentation pass timestamps across submissions; span encloses all intervals, summed intervals may overlap; excludes uploads before first pass, query resolve/readback, diagnostic quality readback, presentation engine and scanout";
        info["gpu_timing_overhead"] = "query resolve/quantization/copy adds GPU work to actual completion and throughput; callback copies mapped values asynchronously; no overhead is subtracted";
        info["vk_memory_scope"] = "successful intercepted vkAllocateMemory handle allocationSize including slabs/padding; vkFreeMemory handle release may precede payload reclamation; excludes physical residency and opaque driver allocations; retired handles are not frees";
        info["scanout_timestamps_available"] = false;
        info["driver_allocation_peak_available"] = false;
        info["gauges"] = std::vector<std::string>{"pending_tickets", "queued_frames", "pending_draws", "pending_timestamp_frames", "live_buffer_bytes", "live_cpu_buffer_bytes", "live_texture_bytes", "canvas_texture_bytes", "transient_buffer_bytes", "artifact_cache_entries", "pipeline_cache_entries", "portable_shader_bytes", "shader_cache_bytes", "shader_cache_limit", "live_portable_shader_bytes", "uncached_live_portable_shader_bytes", "live_line_evaluator_bytes", "uncached_live_line_evaluator_bytes", "live_line_consumer_bytes", "uncached_live_line_consumer_bytes", "live_device_shader_bytes", "uncached_live_device_shader_bytes", "line_resource_pool_slots", "line_resource_pool_busy_slots", "line_resource_pool_bytes", "vertex_input_current_entries", "vertex_input_current_bytes", "vertex_input_cache_entries", "vertex_input_cache_bytes", "vertex_input_oversized_entries", "vertex_input_oversized_bytes", "vertex_input_oversized_entry_limit", "vertex_input_oversized_byte_limit", "device_generation", "frame_slots", "vk_memory_active_devices", "vk_memory_tracking_devices", "vk_memory_live_allocations", "vk_memory_live_bytes"};
        info["high_water_marks"] = std::vector<std::string>{"peak_pending_tickets", "peak_queued_frames", "peak_pending_draws", "peak_pending_timestamp_frames", "peak_shader_cache_bytes", "sampled_peak_live_buffer_bytes", "sampled_peak_live_cpu_buffer_bytes", "sampled_peak_live_texture_bytes", "vk_memory_peak_live_allocations", "vk_memory_peak_live_bytes"};
        return info;
    });
    m.def("benchmark_completions", [](int canvas_id) {
        nb::list result;
        for (const auto& record : benchmark_completions(canvas_id)) {
            nb::dict item;
            item["frame_id"] = record.frame_id;
            item["frame_scope"] = record.frame_scope;
            item["paint_token"] = record.paint_token;
            item["submission_count"] = record.submission_count;
            item["present_count"] = record.present_count;
            item["last_present_submission_index"] = record.last_present_submission_index;
            item["ownership_closed"] = record.ownership_closed;
            item["ownership_retired"] = record.ownership_retired;
            item["counters_captured"] = record.counters_captured;
            item["error"] = record.error;
            item["completion_latency_ns"] = record.completion_latency_ns;
            item["completion_timestamp_ns"] = record.completion_timestamp_ns;
            item["submit_latency_ns"] = record.submit_latency_ns;
            item["status"] = record.status;
            item["presented"] = record.presented;
            item["counter_capture"] = record.counters_captured ? "submission" :
                record.submission_count ? "unavailable_snapshot" : "unavailable_unsubmitted";
            item["counters"] = probe_dict(record.counters);
            result.append(item);
        }
        return result;
    });
    m.def("benchmark_surface_info", [](int canvas_id) {
        auto info = benchmark_surface_info(canvas_id);
        nb::dict result;
        result["present_mode"] = info.present_mode;
        result["vsync_requested"] = info.vsync_requested;
        result["pacing_disabled"] = info.pacing_disabled;
        result["attached"] = info.attached;
        return result;
    });
    m.def("diagnostic_configure_line_endpoints", &diagnostic_configure_line_endpoints,
          nb::arg("canvas_id"), nb::arg("enabled"), nb::arg("capture") = true,
          "Internal endpoint evaluator opt-in with optional diagnostic quality capture; changes no public GLIR or width/smoothing capability.");
    m.def("diagnostic_line_endpoints", [](int canvas_id) {
        nb::list result;
        for (auto& record : diagnostic_line_endpoints(canvas_id)) {
            bool completed = record.status == "completed" && record.error.empty();
            if (completed && ((record.rows && !record.row_bytes) ||
                uint64_t(record.rows) * record.row_bytes != record.data.size())) {
                record.status = "error";
                record.error = "Malformed completed endpoint capture dimensions";
                completed = false;
            }
            nb::dict item;
            item["capture_id"] = record.capture_id;
            item["ticket_id"] = record.ticket_id;
            item["device_generation"] = record.device_generation;
            item["rows"] = record.rows;
            item["row_bytes"] = record.row_bytes;
            item["status"] = record.status;
            item["error"] = record.error;
            item["evaluator_key"] = record.evaluator_key;
            nb::list fields;
            for (const auto& field : record.fields) {
                nb::dict value;
                value["name"] = field.name;
                value["type"] = field.type;
                value["interpolation"] = field.interpolation;
                value["offset"] = field.offset;
                value["size"] = field.size;
                value["array_stride"] = field.array_stride;
                value["matrix_stride"] = field.matrix_stride;
                value["array_size"] = field.array_size;
                fields.append(value);
            }
            item["fields"] = fields;
            if (!record.chunks.empty()) {
                nb::list chunks;
                for (const auto& chunk : record.chunks) {
                    nb::dict value;
                    value["first_row"] = chunk.first_row;
                    value["rows"] = chunk.rows;
                    value["output_rows"] = chunk.output_rows;
                    value["raw_offset"] = chunk.raw_offset;
                    value["raw_bytes"] = chunk.raw_bytes;
                    chunks.append(value);
                }
                item["chunks"] = chunks;
                item["capture_phase"] = "evaluated_before_carry";
            }
            auto owner = std::make_unique<std::vector<uint8_t>>(
                completed ? std::move(record.data) : std::vector<uint8_t>{});
            // Even an empty array has an allocated, capsule-owned data pointer.
            if (owner->empty()) owner->reserve(1);
            nb::capsule deleter(owner.get(), [](void* ptr) noexcept {
                delete static_cast<std::vector<uint8_t>*>(ptr);
            });
            auto* bytes = owner.release();
            if (completed) {
                item["data"] = nb::cast(nb::ndarray<nb::numpy, uint8_t>(
                    bytes->data(), {static_cast<size_t>(record.rows), static_cast<size_t>(record.row_bytes)}, deleter));
            } else {
                item["data"] = nb::cast(nb::ndarray<nb::numpy, uint8_t>(bytes->data(), {size_t(0)}, deleter));
            }
            auto raw_owner = std::make_unique<std::vector<uint8_t>>(std::move(record.raw_data));
            if (raw_owner->empty()) raw_owner->reserve(1);
            nb::capsule raw_deleter(raw_owner.get(), [](void* ptr) noexcept {
                delete static_cast<std::vector<uint8_t>*>(ptr);
            });
            auto* raw_bytes = raw_owner.release();
            item["raw_data"] = nb::cast(nb::ndarray<nb::numpy, uint8_t>(
                raw_bytes->data(), {raw_bytes->size()}, raw_deleter));
            result.append(item);
        }
        return result;
    }, nb::arg("canvas_id"),
       "Internal quality readback; may wait for actual Ticket retirement and mapping. Completed records own logical uint8 rows by row_bytes; other statuses own empty data vectors. Every record owns flat raw_data containing any successfully mapped padded buffer/canary, including validation failures. Excluded from resident timing intervals.");
    m.def("read_presented", [](int canvas_id, int x, int y, int width, int height) {
        Readback read = read_presented(canvas_id, x, y, width, height);
        if (!read.error.empty() && read.rgba.empty()) {
            throw std::runtime_error(read.error);
        }
        auto* owner = new std::vector<uint8_t>(std::move(read.rgba));
        nb::capsule deleter(owner, [](void* ptr) noexcept { delete static_cast<std::vector<uint8_t>*>(ptr); });
        return nb::ndarray<nb::numpy, uint8_t>(
            owner->data(), {static_cast<size_t>(read.height), static_cast<size_t>(read.width), 4},
            deleter);
    });
    m.def("read_pixels", [](int canvas_id, int x, int y, int width, int height, bool alpha, bool floating,
                            const std::string& mode) -> nb::object {
        Readback read = read_canvas(canvas_id, x, y, width, height, alpha, floating, mode);
        if (!read.error.empty()) {
            throw std::runtime_error(read.error);
        }
        size_t channels = static_cast<size_t>(read.channels);
        if (floating) {
            auto* owner = new std::vector<float>(std::move(read.floating_rgba));
            nb::capsule deleter(owner, [](void* ptr) noexcept { delete static_cast<std::vector<float>*>(ptr); });
            return nb::cast(nb::ndarray<nb::numpy, float>(
                owner->data(), {static_cast<size_t>(read.height), static_cast<size_t>(read.width), channels},
                deleter));
        }
        auto* owner = new std::vector<uint8_t>(std::move(read.rgba));
        nb::capsule deleter(owner, [](void* ptr) noexcept { delete static_cast<std::vector<uint8_t>*>(ptr); });
        return nb::cast(nb::ndarray<nb::numpy, uint8_t>(
            owner->data(), {static_cast<size_t>(read.height), static_cast<size_t>(read.width), channels},
            deleter));
    }, nb::arg("canvas_id"), nb::arg("x"), nb::arg("y"), nb::arg("width"), nb::arg("height"),
       nb::arg("alpha"), nb::arg("floating") = false, nb::arg("mode") = "color");
    m.def("compile_variant", [](const std::string& vertex, const std::string& fragment, bool base_level_sampling,
                               bool has_depth, bool point_sprites, bool allow_non_uniform_derivatives) {
        CompileInfo info = compile_variant(vertex, fragment, base_level_sampling, has_depth, point_sprites,
            allow_non_uniform_derivatives);
        nb::dict out;
        out["ok"] = info.ok;
        out["pipeline"] = info.pipeline;
        out["cache_hit"] = info.cache_hit;
        out["allow_non_uniform_derivatives"] = info.allow_non_uniform_derivatives;
        out["spirv_derivative_mode"] = info.spirv_derivative_mode;
        out["cache_key"] = info.cache_key;
        out["error"] = info.error;
        out["compiler_entry"] = info.compiler_entry;
        out["vertex_log"] = info.vertex_log;
        out["fragment_log"] = info.fragment_log;
        out["mapped_line"] = info.mapped_line;
        out["normalized_vertex"] = info.normalized_vertex;
        out["normalized_fragment"] = info.normalized_fragment;
        out["spirv_vertex_words"] = static_cast<int>(info.spirv_vertex.size());
        out["spirv_fragment_words"] = static_cast<int>(info.spirv_fragment.size());
        out["spirv_magic"] = info.spirv_vertex.empty() ? 0 : info.spirv_vertex[0];
        return out;
    }, nb::arg("vertex"), nb::arg("fragment"), nb::arg("base_level_sampling") = true,
       nb::arg("has_depth") = false, nb::arg("point_sprites") = false,
       nb::arg("allow_non_uniform_derivatives") = false);
    m.def("debug_trace", []() { return debug_trace(); });
    m.def("lose_device", &lose_device);
    m.def("shutdown", &shutdown_runtime);
    // Release devices and dispatch their callbacks while Python and Dawn's
    // process globals are still alive, before native static destruction.
    nb::module_::import_("atexit").attr("register")(m.attr("shutdown"));
}
