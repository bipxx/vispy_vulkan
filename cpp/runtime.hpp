#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include "runtime_query_timing.hpp"
#include "platform/vk_layer_telemetry.hpp"
#include "runtime_line_ownership.hpp"
#include "runtime_line_capture.hpp"

struct UploadCaptureStats {
    uint64_t captures = 0, bytes = 0, fallback_dtypes = 0, fallback_exports = 0;
};

struct ByteBlob {
    std::vector<uint8_t> bytes;
    std::vector<int> shape;
    std::string dtype;
};

struct Value {
    enum class Kind { None, Int, Float, Bool, Str, Blob, List };
    Kind kind = Kind::None;
    int64_t i = 0;
    double f = 0;
    bool b = false;
    std::string s;
    ByteBlob blob;
    std::vector<Value> list;
};

struct Command {
    std::string op;
    std::vector<Value> args;
};

struct DeviceInfo {
    std::string backend;
    std::string adapter_type;
    std::string vendor;
    std::string device;
    std::string driver;
    std::string error;
    uint32_t vendor_id = 0;
    uint32_t device_id = 0;
    uint32_t max_texture_1d = 0;
    uint32_t max_texture_2d = 0;
    uint32_t max_texture_3d = 0;
    uint32_t max_vertex_attributes = 0;
    uint32_t max_vertex_buffers = 0;
    uint32_t max_vertex_buffer_stride = 0;
    uint32_t max_storage_buffers = 0;
    uint32_t max_uniform_buffers = 0;
    uint32_t max_inter_stage_shader_variables = 0;
    uint64_t max_storage_buffer_size = 0;
    uint32_t max_bindings_per_bind_group = 0;
    uint32_t max_compute_invocations_per_workgroup = 0;
    uint32_t max_compute_workgroup_size_x = 0;
    uint32_t max_compute_workgroups_per_dimension = 0;
    // Point identities use storage; the full user attribute budget is retained.
    uint32_t max_point_vertex_attributes = 0;
    uint32_t max_samplers = 0;
    uint32_t max_sampled_textures = 0;
    uint64_t max_buffer_size = 0;
    uint64_t max_uniform_buffer_size = 0;
    uint32_t loss_count = 0;
    bool software = false;
    bool float32_filterable = false;
    bool unorm16_texture_formats = false;
    bool bresenham_lines = false;
    bool last_vertex_provoking = false;
    bool core_features_and_limits = false;
    bool timestamp_query = false;
    uint64_t timestamp_quantization_ns = 0;
    std::string depth_stencil_storage;
    bool ok = false;
};

struct Probe {
    uint64_t application_presents = 0;
    uint64_t dawn_queue_submits = 0;
    uint64_t vk_queue_submits = 0;
    uint64_t texture_uploads = 0;
    uint64_t buffer_uploads = 0;
    uint64_t pipeline_misses = 0;
    uint64_t pipeline_hits = 0;
    uint64_t presentation_passes = 0;
    uint64_t finish_calls = 0;
    uint64_t copy_bytes = 0;
    uint64_t completion_waits = 0;
    uint64_t pending_tickets = 0;
    uint64_t retired_tickets = 0;
    uint64_t live_buffer_bytes = 0;
    uint64_t live_cpu_buffer_bytes = 0;
    uint64_t live_texture_bytes = 0;
    uint64_t deferred_frames = 0;
    uint64_t queued_frames = 0;
    uint64_t buffer_allocations = 0;
    uint64_t texture_allocations = 0;
    uint64_t uniform_upload_bytes = 0;
    uint64_t texture_upload_bytes = 0;
    uint64_t geometry_upload_bytes = 0;
    uint64_t point_conversion_builds = 0;
    uint64_t point_conversion_bytes = 0;
    uint64_t canvas_texture_bytes = 0;
    uint64_t transient_buffer_bytes = 0;
    uint64_t draw_calls = 0;
    uint64_t artifact_cache_entries = 0;
    uint64_t pipeline_cache_entries = 0;
    uint64_t portable_shader_hits = 0;
    uint64_t portable_shader_misses = 0;
    uint64_t portable_shader_bytes = 0;
    uint64_t shader_cache_bytes = 0;
    uint64_t shader_cache_limit = 0;
    uint64_t live_portable_shader_bytes = 0;
    uint64_t uncached_live_portable_shader_bytes = 0;
    uint64_t live_line_evaluator_bytes = 0;
    uint64_t uncached_live_line_evaluator_bytes = 0;
    uint64_t live_line_consumer_bytes = 0;
    uint64_t uncached_live_line_consumer_bytes = 0;
    // Owned device-record/map/key/error/variant storage, with retained policy
    // records deduplicated across live snapshots and Tickets. Opaque driver
    // module/pipeline allocation bytes are outside this descriptor scope.
    uint64_t live_device_shader_bytes = 0;
    uint64_t uncached_live_device_shader_bytes = 0;
    uint64_t line_evaluator_hits = 0;
    uint64_t line_evaluator_misses = 0;
    uint64_t line_consumer_hits = 0;
    uint64_t line_consumer_misses = 0;
    // Sampled native pool ownership gauges; hits/evictions/deferrals below
    // are cumulative observations, separate from CPU evaluator ownership.
    uint64_t line_resource_pool_slots = 0, line_resource_pool_busy_slots = 0;
    uint64_t line_resource_pool_bytes = 0;
    uint64_t line_resource_pool_hits = 0, line_resource_pool_evictions = 0;
    uint64_t line_resource_pool_deferrals = 0;
    uint64_t device_generation = 0;
    uint64_t bresenham_line_pipelines = 0;
    uint64_t last_vertex_pipelines = 0;
    // Monotonic host wall intervals, always enabled. Inclusive intervals
    // overlap; these are not CPU thread time, GPU time, or scanout time.
    uint64_t binding_decode_ns = 0, binding_decode_bytes = 0;
    uint64_t owned_upload_captures = 0, owned_upload_capture_bytes = 0;
    uint64_t owned_upload_fallback_dtypes = 0, owned_upload_fallback_exports = 0;
    uint64_t owned_texture_transfers = 0, owned_texture_transfer_bytes = 0;
    uint64_t native_batches = 0, native_commands = 0;
    uint64_t native_interpret_ns = 0, native_submit_ns = 0;
    uint64_t texture_conversion_ns = 0, texture_upload_cpu_ns = 0, buffer_upload_cpu_ns = 0;
    uint64_t shader_cache_lookup_ns = 0, shader_normalize_ns = 0, shader_parse_ns = 0;
    uint64_t shader_link_ns = 0, shader_spirv_ns = 0, shader_reflect_ns = 0, shader_cpu_build_ns = 0;
    uint64_t device_cache_lookup_ns = 0, pipeline_cache_lookup_ns = 0;
    uint64_t shader_module_creation_ns = 0, pipeline_creation_ns = 0;
    uint64_t shader_normalizations = 0, shader_parse_calls = 0, shader_link_calls = 0, shader_spirv_stages = 0;
    uint64_t shader_module_creations = 0, render_pipeline_creations = 0;
    uint64_t compute_pipeline_creations = 0;
    uint64_t render_passes = 0, compute_passes = 0, command_encoders = 0, bind_group_creations = 0;
    uint64_t native_draw_calls = 0;
    uint64_t line_endpoint_dispatches = 0, line_endpoint_rows = 0;
    uint64_t line_endpoint_conversion_builds = 0, line_endpoint_conversion_bytes = 0;
    uint64_t line_endpoint_upload_bytes = 0;
    uint64_t vertex_input_conversion_builds = 0, vertex_input_conversion_bytes = 0;
    // Overlapping CPU ownership views, sampled across Programs. Current
    // records may exceed the historical per-Program cache budget.
    uint64_t vertex_input_current_entries = 0, vertex_input_current_bytes = 0;
    uint64_t vertex_input_cache_entries = 0, vertex_input_cache_bytes = 0;
    // Additional overlapping working-set owner view; limits are per Program,
    // entries/bytes aggregate across live Programs and evictions are cumulative.
    uint64_t vertex_input_oversized_entries = 0, vertex_input_oversized_bytes = 0;
    uint64_t vertex_input_oversized_entry_limit = 8;
    uint64_t vertex_input_oversized_byte_limit = 256ull * 1024 * 1024;
    uint64_t vertex_input_oversized_evictions = 0;
    uint64_t timestamp_query_sets = 0, timestamp_resolves = 0, timestamp_readbacks = 0;
    uint64_t pending_timestamp_frames = 0, peak_pending_timestamp_frames = 0;
    bool vk_memory_available = false, vk_memory_complete = false;
    uint64_t vk_memory_active_devices = 0;
    uint64_t vk_memory_tracking_devices = 0;
    uint64_t vk_memory_allocate_calls = 0;
    uint64_t vk_memory_allocate_failures = 0;
    uint64_t vk_memory_allocation_count = 0;
    uint64_t vk_memory_allocated_bytes = 0;
    uint64_t vk_memory_free_calls = 0;
    uint64_t vk_memory_free_count = 0;
    uint64_t vk_memory_freed_bytes = 0;
    uint64_t vk_memory_null_free_calls = 0;
    uint64_t vk_memory_unknown_free_calls = 0;
    uint64_t vk_memory_live_allocations = 0;
    uint64_t vk_memory_live_bytes = 0;
    uint64_t vk_memory_peak_live_allocations = 0;
    uint64_t vk_memory_peak_live_bytes = 0;
    uint64_t vk_memory_retired_allocations = 0;
    uint64_t vk_memory_retired_bytes = 0;
    uint64_t vk_memory_tracking_errors = 0;
    uint64_t pending_draws = 0;
    uint64_t peak_pending_tickets = 0, peak_queued_frames = 0, peak_pending_draws = 0, peak_shader_cache_bytes = 0;
    uint64_t descriptor_samples = 0;
    uint64_t sampled_peak_live_buffer_bytes = 0, sampled_peak_live_texture_bytes = 0;
    uint64_t sampled_peak_live_cpu_buffer_bytes = 0;
    uint64_t frame_slots = 3;
};

struct CompileInfo {
    bool ok = false;
    bool pipeline = false;
    bool cache_hit = false;
    bool allow_non_uniform_derivatives = false;
    std::string spirv_derivative_mode = "strict-v1";
    std::string cache_key;
    std::string error;
    std::string compiler_entry;
    std::string vertex_log;
    std::string fragment_log;
    int mapped_line = 0;
    std::string normalized_vertex;
    std::string normalized_fragment;
    std::vector<uint32_t> spirv_vertex;
    std::vector<uint32_t> spirv_fragment;
};

struct BenchmarkCompletion {
    uint64_t frame_id = 0;
    uint64_t paint_token = 0, submission_count = 0, present_count = 0;
    uint64_t last_present_submission_index = UINT64_MAX;
    std::string frame_scope = "native_present", error;
    bool ownership_closed = false, ownership_retired = false, counters_captured = false;
    uint64_t completion_latency_ns = 0;
    uint64_t completion_timestamp_ns = 0;
    uint64_t submit_latency_ns = 0;
    std::string status;
    bool presented = false;
    Probe counters;
};

struct SurfaceInfo {
    std::string present_mode;
    bool vsync_requested = false;
    bool pacing_disabled = false;
    bool attached = false;
};

struct Readback {
    std::vector<uint8_t> rgba;
    std::vector<float> floating_rgba;
    int width = 0;
    int height = 0;
    int channels = 4;
    std::string error;
};

struct LineEndpointField {
    std::string name, type, interpolation;
    uint32_t offset = 0, size = 0, array_stride = 0, matrix_stride = 0;
    int array_size = 0;
};

// Internal quality capture, independent of normal draw completion/timing.
// A completed record has successfully retired its Ticket and mapped its output.
struct LineEndpointReadback {
    uint64_t capture_id = 0, ticket_id = 0, device_generation = 0;
    uint32_t rows = 0, row_bytes = 0;
    std::string status, error, evaluator_key;
    std::vector<uint8_t> data, raw_data;
    std::vector<LineEndpointField> fields;
    // Present only for partitioned evaluation. Raw bytes retain the actual
    // mapped allocations before shared endpoint carry copies are encoded.
    std::vector<vispy::lines::captures::Part> chunks;
};

DeviceInfo ensure_device();
Probe probe_counters();
uint64_t layer_submit_count();
int register_canvas(int width, int height, int samples, bool vsync);
void configure_canvas(int canvas_id, int width, int height, int samples);
void destroy_canvas(int canvas_id);
void set_surface(int canvas_id, std::uintptr_t hwnd, std::uintptr_t hinstance);
void set_surface_x11(int canvas_id, std::uintptr_t display, uint64_t window, bool owned_display);
void set_surface_metal_view(int canvas_id, std::uintptr_t view);
void clear_surface(int canvas_id);
void update_surface_scale(int canvas_id, double scale);
void execute_commands(int canvas_id, const std::vector<Command>& commands,
                      uint64_t binding_decode_ns = 0, uint64_t binding_decode_bytes = 0);
// Consumes the command vector; the const entry point above remains replayable.
void execute_owned_commands(int canvas_id, std::vector<Command>&& commands,
                            uint64_t binding_decode_ns = 0, uint64_t binding_decode_bytes = 0,
                            const UploadCaptureStats& capture_stats = {});
void finish_canvas(int canvas_id);
void present_canvas(int canvas_id);
bool process_events();
std::vector<int> canvas_viewport(int canvas_id);
bool frame_ready(int canvas_id);
bool benchmark_frame_request_ready(int canvas_id);
void configure_frame_slots(int slots);
void configure_shader_cache(int entries, uint64_t bytes);
void benchmark_begin_frame(int canvas_id, uint64_t frame_id);
VulkanMemoryWindow benchmark_memory_window_begin();
VulkanMemoryWindow benchmark_memory_window_end(uint64_t token, bool cancel = false);
uint64_t begin_canvas_paint(int canvas_id);
void end_canvas_paint(int canvas_id, uint64_t token);
void abort_canvas_paint(int canvas_id, uint64_t token, const std::string& reason);
void benchmark_cancel_frame(int canvas_id, uint64_t frame_id, const std::string& reason);
void benchmark_configure_gpu_timing(int canvas_id, bool enabled);
void benchmark_submit_intermediate(int canvas_id);
std::vector<vispy::timing::FrameResult> benchmark_gpu_timings(int canvas_id);
std::vector<BenchmarkCompletion> benchmark_completions(int canvas_id);
SurfaceInfo benchmark_surface_info(int canvas_id);
Readback read_canvas(int canvas_id, int x, int y, int width, int height, bool alpha, bool floating = false,
                     const std::string& mode = "color");
Readback read_presented(int canvas_id, int x, int y, int width, int height);
void diagnostic_configure_line_endpoints(int canvas_id, bool enabled, bool capture = true);
vispy::lines::LineOwnershipSnapshot diagnostic_peek_line_ownership(int canvas_id);
std::vector<LineEndpointReadback> diagnostic_line_endpoints(int canvas_id);
CompileInfo compile_variant(const std::string& vertex, const std::string& fragment, bool base_level_sampling,
                            bool has_depth, bool point_sprites, bool allow_non_uniform_derivatives = false);
std::vector<std::string> debug_trace();
void lose_device();
void shutdown_runtime();
std::string runtime_revision();
