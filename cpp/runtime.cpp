#include "runtime.hpp"

#include "shader/glslang_spv.hpp"
#include "shader/artifact.hpp"
#include "shader/normalize.hpp"
#include "runtime_texture.hpp"
#include "runtime_owned_texture.hpp"
#include "runtime_readback.hpp"
#include "runtime_state.hpp"
#include "runtime_point.hpp"
#include "runtime_point_batch_owner.hpp"
#include "runtime_batch_owner.hpp"
#include "runtime_batch_cache.hpp"
#include "runtime_batch_capacity.hpp"
#include "runtime_batch_strip.hpp"
#include "runtime_line.hpp"
#include "runtime_line_batch.hpp"
#include "runtime_line_resources.hpp"
#include "runtime_line_cache.hpp"
#include "runtime_line_pool.hpp"
#include "runtime_line_consumer.hpp"
#include "runtime_line_variants.hpp"
#include "runtime_line_consumer_accounting.hpp"
#include "runtime_frame_lifecycle.hpp"
#include "runtime_render_semantics.hpp"
#include "platform/native_surface.hpp"
#include "platform/native_library.hpp"
#include "platform/vk_layer_telemetry.hpp"

#include <dawn/native/DawnNative.h>
#include <webgpu/webgpu_cpp.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdlib>
#include <cmath>
#include <chrono>
#include <cstring>
#include <deque>
#include <functional>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <memory_resource>
#include <mutex>
#include <optional>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace {

using vispy::shader::SpirvDerivativeMode;

constexpr char kCompilerEntry[] = "TShader::parse+TProgram::link+GlslangToSpv";
constexpr char kPins[] =
    "dawn=499e5c6ff9b37d5de70c6493fb74c251e0d35c1c;"
    "glslang=23baa3f7b58f0dfdccec6755c53e85c31e52efba;"
    "spirv-tools=ce818d1f2db53916d89fa1fe0012237779480a9b;"
    "norm=5";

uint64_t fnv1a(const std::string& text) {
    uint64_t hash = 14695981039346656037ull;
    for (unsigned char c : text) {
        hash ^= c;
        hash *= 1099511628211ull;
    }
    return hash;
}

std::string hex64(uint64_t value) {
    std::ostringstream out;
    out << std::hex << value;
    return out.str();
}

std::string lower_token(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return value;
}

std::string view_to_string(wgpu::StringView view) {
    if (view.data == nullptr) return {};
    size_t length = view.length;
    if (length == WGPU_STRLEN) length = std::strlen(view.data);
    return std::string(view.data, length);
}

const char* error_type_name(wgpu::ErrorType type) {
    switch (type) {
        case wgpu::ErrorType::NoError: return "NoError";
        case wgpu::ErrorType::Validation: return "Validation";
        case wgpu::ErrorType::OutOfMemory: return "OutOfMemory";
        case wgpu::ErrorType::Internal: return "Internal";
        default: return "Unknown";
    }
}

struct BackendShaderLog {
    std::mutex mutex;
    std::ofstream stream;
    std::atomic<bool> failed{false};

    explicit BackendShaderLog(const std::filesystem::path& path) {
        if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
        stream.open(path, std::ios::binary | std::ios::app);
        if (!stream) throw std::runtime_error("Dawn backend shader log cannot be opened");
    }

    void write(wgpu::LoggingType type, wgpu::StringView message) noexcept {
        try {
            const char* name = type == wgpu::LoggingType::Info ? "Info" :
                type == wgpu::LoggingType::Warning ? "Warning" :
                type == wgpu::LoggingType::Error ? "Error" : "Verbose";
            std::lock_guard<std::mutex> lock(mutex);
            stream << "[Dawn " << name << "]\n" << view_to_string(message) << '\n';
            stream.flush();
            if (!stream) failed.store(true);
        } catch (...) {
            failed.store(true);
        }
    }
};

// All callback storage exists before begin(). Pop uses a noncapturing callback
// and transfers its preallocated owner, so timeout never leaves stack userdata.
class PipelineCreationScopes {
    struct Result {
        std::atomic<bool> done{false};
        wgpu::PopErrorScopeStatus status = wgpu::PopErrorScopeStatus::Error;
        wgpu::ErrorType type = wgpu::ErrorType::Unknown;
        std::string message;
        bool message_failed = false;
    };
    wgpu::Instance instance;
    wgpu::Device device;
    wgpu::Future lost;
    std::string role;
    std::shared_ptr<BackendShaderLog> backend_log;
    uint64_t generation;
    bool marker_open = false;
    std::array<std::shared_ptr<Result>, 3> results;
    std::array<std::unique_ptr<std::shared_ptr<Result>>, 3> owners;
    std::array<wgpu::Future, 3> futures{};
    std::array<wgpu::WaitStatus, 3> waits{};
    size_t open = 0;
    bool drained = false;

    void marker(const char* phase) noexcept {
        if (!backend_log) return;
        try {
            const auto text = std::string(phase) + " pipeline creation generation=" +
                std::to_string(generation) + " role=" + role;
            backend_log->write(wgpu::LoggingType::Info, wgpu::StringView{text.data(), text.size()});
        } catch (...) {
            backend_log->failed.store(true);
        }
    }

    void drain() {
        // Healthy Dawn pops synchronously. Register ALL pops before any wait,
        // and never pop again just because a callback wait failed.
        while (open) {
            const size_t index = open - 1;
            futures[index] = device.PopErrorScope(wgpu::CallbackMode::WaitAnyOnly,
                [](wgpu::PopErrorScopeStatus status, wgpu::ErrorType type,
                   wgpu::StringView message, std::shared_ptr<Result>* owner) noexcept {
                    std::unique_ptr<std::shared_ptr<Result>> lifetime(owner);
                    auto& result = **lifetime;
                    result.status = status;
                    result.type = type;
                    try { result.message = view_to_string(message); }
                    catch (...) { result.message_failed = true; }
                    result.done.store(true);
                }, owners[index].get());
            owners[index].release();
            --open;
        }
        for (size_t index = results.size(); index-- > 0;)
            if (futures[index].id)
                waits[index] = instance.WaitAny(futures[index], 30'000'000'000ull);
        drained = true;
        if (marker_open) { marker("END"); marker_open = false; }
    }

public:
    PipelineCreationScopes(const wgpu::Instance& instance, const wgpu::Device& device, std::string role,
                           std::shared_ptr<BackendShaderLog> backend_log, uint64_t generation)
        : instance(instance), device(device), lost(device.GetLostFuture()), role(std::move(role)),
          backend_log(std::move(backend_log)), generation(generation) {
        for (size_t index = 0; index < results.size(); ++index) {
            results[index] = std::make_shared<Result>();
            owners[index] = std::make_unique<std::shared_ptr<Result>>(results[index]);
        }
    }
    PipelineCreationScopes(const PipelineCreationScopes&) = delete;
    PipelineCreationScopes& operator=(const PipelineCreationScopes&) = delete;
    ~PipelineCreationScopes() noexcept {
        if (!drained) {
            try { drain(); } catch (...) {}
        }
    }
    void begin() {
        marker("BEGIN");
        marker_open = true;
        for (auto filter : {wgpu::ErrorFilter::Internal, wgpu::ErrorFilter::OutOfMemory,
                            wgpu::ErrorFilter::Validation}) {
            device.PushErrorScope(filter);
            ++open;
        }
    }
    std::string finish() {
        drain();
        std::string errors;
        auto append = [&](const std::string& detail) {
            if (!errors.empty()) errors += "; ";
            errors += role + ": " + detail;
        };
        for (size_t index = results.size(); index-- > 0;) {
            const auto& result = *results[index];
            if (waits[index] != wgpu::WaitStatus::Success || !result.done.load()) {
                append("error-scope callback wait failed (WaitStatus=" +
                    std::to_string(static_cast<uint32_t>(waits[index])) + ")");
            } else if (result.status != wgpu::PopErrorScopeStatus::Success ||
                       result.type != wgpu::ErrorType::NoError || result.message_failed) {
                append(std::string(error_type_name(result.type)) + " (PopErrorScopeStatus=" +
                    std::to_string(static_cast<uint32_t>(result.status)) + "): " +
                    (result.message_failed ? "diagnostic message could not be retained" : result.message));
            }
        }
        // A lost Dawn device can return synthetic clean pops. Its lost future
        // must therefore refuse admission even when every scope says NoError.
        wgpu::FutureWaitInfo loss{};
        loss.future = lost;
        const auto loss_status = instance.WaitAny(1, &loss, 0);
        if (loss.completed) append("device lost during creation");
        else if (loss_status != wgpu::WaitStatus::Success && loss_status != wgpu::WaitStatus::TimedOut)
            append("device-loss observation failed");
        return errors;
    }
};

void dump_shader_pair(const std::string& prefix, const std::string& vertex,
                      const std::string& fragment, const std::vector<uint32_t>& vertex_spv,
                      const std::vector<uint32_t>& fragment_spv) {
    const char* directory = std::getenv("VISPY_DAWN_SHADER_DUMP");
    if (!directory || !*directory) return;
    const auto root = std::filesystem::u8path(directory);
    std::filesystem::create_directories(root);
    auto write = [&](const char* suffix, const void* data, size_t size) {
        std::ofstream stream(root / (prefix + suffix), std::ios::binary);
        stream.write(static_cast<const char*>(data), static_cast<std::streamsize>(size));
        if (!stream) throw std::runtime_error(prefix + ": shader diagnostic dump failed");
    };
    write(".vert.glsl", vertex.data(), vertex.size());
    write(".frag.glsl", fragment.data(), fragment.size());
    write(".vert.spv", vertex_spv.data(), vertex_spv.size() * sizeof(uint32_t));
    write(".frag.spv", fragment_spv.data(), fragment_spv.size() * sizeof(uint32_t));
}

uint64_t monotonic_ns() {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}

struct HostTimer {
    uint64_t& counter;
    uint64_t begin = monotonic_ns();
    bool active = true;
    explicit HostTimer(uint64_t& value) : counter(value) {}
    void finish() {
        if (active) { counter += monotonic_ns() - begin; active = false; }
    }
    ~HostTimer() { finish(); }
};

using LineConsumerDevice = vispy::lines::LineConsumerDeviceRecord<
    vispy::shader::GeneratedLineConsumerArtifact, wgpu::ShaderModule,
    wgpu::RenderPipeline, wgpu::BindGroupLayout>;

struct Artifact : vispy::shader::DeviceShaderArtifact<
    wgpu::ShaderModule, wgpu::RenderPipeline, wgpu::BindGroupLayout> {
    using Base = vispy::shader::DeviceShaderArtifact<
        wgpu::ShaderModule, wgpu::RenderPipeline, wgpu::BindGroupLayout>;
    std::shared_ptr<const vispy::shader::PortableShaderArtifact> portable;
    std::shared_ptr<const vispy::shader::LineEvaluatorArtifact> evaluator;
    vispy::lines::LineConsumerDeviceSet<LineConsumerDevice> consumer_devices;
    bool default_has_depth = true;
    // Portable LINK and shared resource admission do not require an ordinary
    // vertex/fragment pipeline. Each DRAW route admits its own device interface.
    bool linked = false;
    bool ordinary_attempted = false;
    wgpu::ShaderModule line_module;
    wgpu::BindGroupLayout line_bind_layout;
    wgpu::PipelineLayout line_pipeline_layout;
    wgpu::ComputePipeline line_pipeline;
    uint64_t line_generation = 0;
    bool line_pipeline_ok = false;
    std::string line_error;
    // The bound applies jointly to ordinary and every consumer policy.
    vispy::lines::LineRenderVariantCache<LineConsumerDevice, wgpu::RenderPipeline> render_variants;

    bool linked_for(uint64_t generation) const {
        return generation != 0 && device_generation == generation && linked && portable && portable->ok;
    }
    bool consumer_ready_for(const std::shared_ptr<LineConsumerDevice>& record, uint64_t generation) const {
        return linked_for(generation) && record && record->ready_for(generation, portable, evaluator) &&
            line_pipeline_ok && line_generation == generation && line_module && line_bind_layout && line_pipeline;
    }

    template<class Visit> void for_each_consumer(Visit&& visit) const {
        consumer_devices.for_each_consumer(std::forward<Visit>(visit));
    }

    size_t render_variant_count() const {
        size_t count = variants.size();
        consumer_devices.for_each_record([&](const auto& record) { count += record->variants.size(); });
        return count;
    }

    void cache_render_variant(const std::string& key, const wgpu::RenderPipeline& value,
                              const std::shared_ptr<LineConsumerDevice>& record) {
        render_variants.publish(key, value, record, variants);
    }

    size_t storage_bytes(size_t extra_record_bytes = 0) const {
        size_t bytes = vispy::inputs::bounded_cost_add(Base::storage_bytes(extra_record_bytes),
                                                     line_error.capacity() + 1);
        const auto policy_bytes = consumer_devices.storage_bytes();
        if (policy_bytes == SIZE_MAX) return SIZE_MAX;
        // sizeof(Artifact) already includes the inline set object.
        bytes = vispy::inputs::bounded_cost_add(bytes, policy_bytes - sizeof(consumer_devices));
        const auto variant_bytes = render_variants.storage_bytes();
        if (variant_bytes == SIZE_MAX) return SIZE_MAX;
        bytes = vispy::inputs::bounded_cost_add(bytes, variant_bytes - sizeof(render_variants));
        return bytes;
    }
    void invalidate() {
        Base::invalidate();
        linked = false;
        ordinary_attempted = false;
        line_module = nullptr;
        line_bind_layout = nullptr;
        line_pipeline_layout = nullptr;
        line_pipeline = nullptr;
        line_generation = 0;
        line_pipeline_ok = false;
        line_error.clear();
        // Published policy/generation pairs retained by snapshots are never
        // retagged or overwritten. New-generation records are built afresh.
        consumer_devices.clear();
        render_variants.clear();
    }
};

using NativeShaderCache = vispy::shader::ShaderArtifactCache<Artifact,
    vispy::shader::LineEvaluatorArtifact, vispy::shader::GeneratedLineConsumerArtifact>;

struct BufferRev {
    // Cache keys never use recyclable pointer addresses.
    inline static std::atomic<uint64_t> next_identity{1};
    const uint64_t identity = next_identity.fetch_add(1, std::memory_order_relaxed);
    std::vector<uint8_t> cpu;
    wgpu::Buffer gpu;
    uint64_t generation = 1;
    uint64_t revision = 0;
    uint64_t gpu_revision = 0;
    int owner = 0;
    // Only a composite batch root owns metadata; metadata never owns its root.
    std::shared_ptr<const vispy::inputs::batches::owners::OwnerData<std::shared_ptr<BufferRev>>> batch_data;
    std::shared_ptr<const vispy::points::batches::owners::OwnerData<std::shared_ptr<BufferRev>>> point_batch_data;
    std::unordered_map<std::string, std::shared_ptr<BufferRev>> derived;
};

uint32_t attribute_components(const std::string& type) {
    if (type == "float" || type == "int" || type == "uint") return 1;
    if ((type.starts_with("vec") || type.starts_with("ivec") || type.starts_with("uvec")) &&
        type.back() >= '2' && type.back() <= '4') return type.back() - '0';
    throw std::runtime_error("ATTRIBUTE unsupported native vertex type " + type);
}

wgpu::VertexFormat attribute_format(const std::string& type) {
    const uint32_t components = attribute_components(type);
    if (type == "uint" || type.starts_with("uvec")) {
        const wgpu::VertexFormat formats[] = {wgpu::VertexFormat::Uint32, wgpu::VertexFormat::Uint32x2,
            wgpu::VertexFormat::Uint32x3, wgpu::VertexFormat::Uint32x4};
        return formats[components - 1];
    }
    if (type == "int" || type.starts_with("ivec")) {
        const wgpu::VertexFormat formats[] = {wgpu::VertexFormat::Sint32, wgpu::VertexFormat::Sint32x2,
            wgpu::VertexFormat::Sint32x3, wgpu::VertexFormat::Sint32x4};
        return formats[components - 1];
    }
    const wgpu::VertexFormat formats[] = {wgpu::VertexFormat::Float32, wgpu::VertexFormat::Float32x2,
        wgpu::VertexFormat::Float32x3, wgpu::VertexFormat::Float32x4};
    return formats[components - 1];
}

wgpu::ShaderStage resource_stages(uint32_t mask) {
    auto stages = wgpu::ShaderStage::None;
    if (mask & 1) stages |= wgpu::ShaderStage::Vertex;
    if (mask & 2) stages |= wgpu::ShaderStage::Fragment;
    if (mask & 4) stages |= wgpu::ShaderStage::Compute;
    return stages;
}

struct TextureRev : TextureData {
    bool renderbuffer = false;
    // Storage capability is independent of the source DATA scalar type.
    wgpu::TextureSampleType storage_sample_type = wgpu::TextureSampleType::Float;
    wgpu::Texture texture;
    wgpu::TextureView view;
    wgpu::Sampler sampler;
    std::shared_ptr<int> allocation_token;
    std::shared_ptr<const TextureData> allocation_descriptor;
    std::shared_ptr<TextureRev> base;
    struct Region {
        ByteBlob data;
        std::vector<int> offset;
    };
    std::vector<Region> updates;
    uint64_t revision = 0;
    uint64_t gpu_revision = 0;
    int owner = 0;
    size_t gpu_bytes = 0;
};

wgpu::TextureSampleType declared_sample_type(const NormSampler& sampler) {
    switch (sampler.sample_scalar) {
    case ShaderScalarType::Float: return wgpu::TextureSampleType::Float;
    case ShaderScalarType::Sint: return wgpu::TextureSampleType::Sint;
    case ShaderScalarType::Uint: return wgpu::TextureSampleType::Uint;
    default: throw std::runtime_error("TEXTURE " + sampler.name + ": unsupported sampled scalar type");
    }
}

wgpu::SamplerBindingType declared_sampler_type(const NormSampler& sampler) {
    return sampler.sample_scalar == ShaderScalarType::Float ?
        wgpu::SamplerBindingType::Filtering : wgpu::SamplerBindingType::NonFiltering;
}

void refresh_storage_sample_type(TextureRev& rev) {
    const auto& storage = rev.allocation_descriptor ? *rev.allocation_descriptor :
        static_cast<const TextureData&>(rev);
    if (storage.format == "depth" || storage.format == "stencil" || storage.format == "depth_stencil" || storage.format == "depth_component") {
        rev.storage_sample_type = wgpu::TextureSampleType::Depth;
        return;
    }
    const auto description = texture_detail::describe(storage);
    rev.storage_sample_type = description.integer ? (description.signed_integer ?
        wgpu::TextureSampleType::Sint : wgpu::TextureSampleType::Uint) :
        description.storage == texture_detail::Storage::Float32 ||
        description.storage == texture_detail::Storage::Unorm16 ?
        wgpu::TextureSampleType::UnfilterableFloat : wgpu::TextureSampleType::Float;
}

void validate_sampler_storage(const NormSampler& sampler, TextureRev& rev) {
    if ((sampler.dim == "1d" && rev.dimensions != 1) ||
        (sampler.dim == "2d" && rev.dimensions != 2) ||
        (sampler.dim == "3d" && rev.dimensions != 3))
        throw std::runtime_error("TEXTURE " + sampler.name + ": shader texture dimension differs from retained allocation");
    refresh_storage_sample_type(rev);
    const auto declared = declared_sample_type(sampler);
    const bool compatible = declared == rev.storage_sample_type ||
        (declared == wgpu::TextureSampleType::Float &&
         rev.storage_sample_type == wgpu::TextureSampleType::UnfilterableFloat);
    if (!compatible)
        throw std::runtime_error("TEXTURE " + sampler.name + ": shader sampled scalar differs from retained texture storage");
}

struct AttrBinding {
    bool constant = false;
    int buffer_id = 0;
    int stride = 0;
    int offset = 0;
    int divisor = 0;
    std::string type;
    std::vector<uint32_t> constant_words;
    std::shared_ptr<BufferRev> constant_buffer;
};

struct VertexStream {
    uint64_t offset = 0;
    uint32_t stride = 0;
    bool instance = false;
};

struct GpuObject {
    std::string class_name;
    uint64_t generation = 1;
    bool alive = true;
    std::string shader;
    int vert_id = 0;
    int frag_id = 0;
    int geom_id = 0;
    std::shared_ptr<Artifact> artifact;
    std::shared_ptr<Artifact> point_artifact;
    std::shared_ptr<Artifact> affine_artifact;
    std::shared_ptr<Artifact> indexed_artifact;
    std::shared_ptr<Artifact> batch_affine_artifact, batch_indexed_artifact;
    std::unordered_map<std::string, std::vector<float>> f_uniforms;
    std::unordered_map<std::string, std::vector<int32_t>> i_uniforms;
    std::unordered_map<std::string, AttrBinding> attributes;
    std::unordered_map<std::string, int> textures;
    std::shared_ptr<BufferRev> buffer;
    std::shared_ptr<BufferRev> primitive_indices;
    std::shared_ptr<BufferRev> point_geometry_cache;
    std::string point_geometry_sources;
    int point_geometry_index_owner = 0;
    std::shared_ptr<BufferRev> input_geometry_cache;
    vispy::inputs::CurrentConversions<std::shared_ptr<BufferRev>> input_current;
    vispy::inputs::OversizedConversions<std::shared_ptr<BufferRev>> input_oversized;
    std::string input_vertex_sources, input_instance_sources, input_index_source;
    int input_index_owner = 0;
    std::shared_ptr<TextureRev> texture;
    int fb_color = 0;
    int fb_depth = 0;
    int fb_stencil = 0;
    int width = 1;
    int height = 1;
};

struct LineWork;
struct LineCapture;
struct AsyncResult;

struct DrawSnap {
    // A preparation slot is owned but not an admitted semantic DRAW yet.
    bool staged_admission = false;
    vispy::render::SnapshotOrigin origin = vispy::render::SnapshotOrigin::UserDraw;
    RenderState state;
    std::shared_ptr<Artifact> artifact;
    std::vector<uint8_t> uniforms;
    std::vector<std::shared_ptr<BufferRev>> vertices;
    std::vector<uint32_t> vertex_slots;
    std::vector<VertexStream> vertex_streams;
    std::vector<AttrBinding> bindings;
    std::shared_ptr<BufferRev> point_identity;
    std::shared_ptr<BufferRev> vertex_identity;
    std::shared_ptr<BufferRev> batch_inputs;
    std::shared_ptr<BufferRev> point_batch_inputs;
    bool packed_point_inputs = false;
    std::shared_ptr<BufferRev> index;
    std::string index_type;
    int index_count = 0;
    int first = 0;
    int count = 0;
    int instances = 1;
    std::string mode;
    LogicalDrawTopology logical_topology = LogicalDrawTopology::NonPolygon;
    struct LineInputs {
        vispy::lines::CapturedSelection<BufferRev> selection;
        std::shared_ptr<Artifact> original_artifact;
        std::shared_ptr<const vispy::shader::PortableShaderArtifact> portable;
        std::shared_ptr<const vispy::shader::LineEvaluatorArtifact> evaluator;
        std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact> consumer;
        std::shared_ptr<LineConsumerDevice> consumer_device;
        std::vector<std::shared_ptr<BufferRev>> vertices;
        std::vector<AttrBinding> bindings;
        std::vector<uint8_t> uniforms;
        std::vector<std::shared_ptr<TextureRev>> textures;
    };
    std::shared_ptr<const LineInputs> line_inputs;
    std::shared_ptr<LineWork> line_work;
    // A semantic line DRAW may own several bounded physical leaves. Leaves
    // never point back to this owner, and are flattened only for submission.
    std::shared_ptr<const std::vector<DrawSnap>> line_chunks;
    bool semantic_draw = true;
    bool stencil_face_split = false;
    std::vector<std::shared_ptr<TextureRev>> textures;
    // Value policies and texture owners are captured together. Later GLIR
    // sampler mutations cannot change either side of an admitted DRAW.
    std::vector<vispy::shader::IntegerSamplePolicy> integer_sampling_policies;
    int canvas_id = 0;
    int fbo = 0;
    std::shared_ptr<TextureRev> attachment;
    wgpu::TextureView target_view;
    wgpu::TextureView resolve_view;
    wgpu::TextureView depth_view;
    wgpu::Texture target_texture;
    wgpu::Texture resolve_texture;
    wgpu::Texture depth_texture;
    std::shared_ptr<TextureRev> depth_attachment;
    bool clear_depth = false;
    bool clear_stencil = false;
    int target_width = 0;
    int target_height = 0;
    int viewport[4] = {0, 0, -1, -1};
    int scissor[4] = {0, 0, -1, -1};
    bool scissor_enabled = false;
    bool clear = false;
    float clear_color[4] = {0, 0, 0, 0};
    std::vector<std::shared_ptr<void>> keep;
};

struct LineCapturePart {
    wgpu::Buffer readback;
    std::shared_ptr<AsyncResult> map_result;
    wgpu::Future map_future{};
    bool map_requested = false, collected = false;
};

struct LineCapture {
    int canvas_id = 0;
    uint64_t frame_id = 0, paint_token = 0;
    LineEndpointReadback result;
    std::shared_ptr<const vispy::shader::LineEvaluatorArtifact> evaluator;
    wgpu::Buffer readback;
    std::shared_ptr<AsyncResult> map_result;
    wgpu::Future map_future{};
    uint64_t allocation_bytes = 0, charged_bytes = 0;
    vispy::lines::captures::Plan chunk_plan;
    std::vector<LineCapturePart> parts;
    // Failure metadata may be terminal before its submitted GPU owner is.
    // Keep the diagnostic charge until the real Ticket is processed.
    bool ticket_finished = false;
    static constexpr size_t error_limit = 4096;
    void set_error(std::string_view message) {
        result.error.assign(message.data(), std::min(message.size(), error_limit));
    }
    void reset_readbacks() {
        readback = nullptr;
        for (auto& part : parts) part.readback = nullptr;
    }
    void destroy_readbacks() {
        if (readback) readback.Destroy();
        for (auto& part : parts) if (part.readback) part.readback.Destroy();
        reset_readbacks();
        map_result.reset(); map_future = {};
        for (auto& part : parts) { part.map_result.reset(); part.map_future = {}; }
    }
};

struct LineWork {
    std::shared_ptr<Artifact> original;
    std::shared_ptr<const vispy::shader::LineEvaluatorArtifact> evaluator;
    std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact> consumer;
    std::shared_ptr<LineConsumerDevice> consumer_device;
    vispy::shader::GeneratedLineConsumerDraw consumer_draw;
    vispy::shader::LineEvaluatorDispatch dispatch;
    std::shared_ptr<BufferRev> packed_inputs;
    std::vector<uint8_t> uniforms;
    std::vector<std::shared_ptr<TextureRev>> textures;
    std::shared_ptr<LineCapture> capture;
    std::optional<vispy::lines::batches::Chunk> chunk;
    size_t capture_part = 0;
};

struct LineBindingKey {
    uint32_t binding = 0, kind = 0;
    uintptr_t handle = 0;
    uint64_t offset = 0, size = 0;
    friend bool operator==(const LineBindingKey&, const LineBindingKey&) = default;
};

struct LineBorrowedBuffer {
    std::weak_ptr<BufferRev> owner;
    wgpu::Buffer handle;
};

struct LineBorrowedTexture {
    std::weak_ptr<TextureRev> owner;
    wgpu::Texture texture;
    wgpu::TextureView view;
    wgpu::Sampler sampler;
    uint64_t bytes = 0;
};

struct LineCachedBindings {
    wgpu::BindGroup group;
    WGPUBindGroupLayout layout = nullptr;
    uint64_t generation = 0;
    bool compute = false;
    std::weak_ptr<Artifact> artifact;
    std::weak_ptr<LineConsumerDevice> consumer_device;
    std::pmr::vector<LineBindingKey> keys;
    std::pmr::vector<LineBorrowedBuffer> buffers;
    std::pmr::vector<LineBorrowedTexture> textures;

    explicit LineCachedBindings(std::pmr::memory_resource* memory)
        : keys(memory), buffers(memory), textures(memory) {}
    void clear() {
        group = nullptr; layout = nullptr; generation = 0;
        artifact.reset(); consumer_device.reset(); keys.clear(); buffers.clear(); textures.clear();
    }
    bool sources_live(uint64_t current_generation) const {
        auto source = artifact.lock();
        if (!source || generation != current_generation) return false;
        if (compute) {
            if (source->line_generation != generation || source->line_bind_layout.Get() != layout)
                return false;
        } else {
            const bool ordinary_layout = source->valid_for(generation) && source->bind_layout.Get() == layout;
            const auto selected = consumer_device.lock();
            const bool consumer_layout = source->consumer_ready_for(selected, generation) &&
                selected->bind_layout.Get() == layout;
            if (!ordinary_layout && !consumer_layout) return false;
        }
        for (const auto& borrowed : buffers) {
            auto owner = borrowed.owner.lock();
            if (!owner || !owner->gpu || owner->gpu.Get() != borrowed.handle.Get()) return false;
        }
        for (const auto& borrowed : textures) {
            auto owner = borrowed.owner.lock();
            if (!owner || owner->texture.Get() != borrowed.texture.Get() ||
                    owner->view.Get() != borrowed.view.Get() || owner->sampler.Get() != borrowed.sampler.Get())
                return false;
        }
        return true;
    }
};

struct LineControlShape {
    size_t compute_uniforms = 0, render_uniforms = 0;
    size_t compute_entries = 0, render_entries = 0;
    size_t render_buffers = 0, compute_textures = 0, render_textures = 0;
    friend bool operator==(const LineControlShape&, const LineControlShape&) = default;
};

// All retained variable-sized control data uses one explicitly charged arena.
// Repartitioning an idle slot destroys the old arena before constructing its
// replacement; no vector can silently grow beyond the admitted byte bound.
struct NativeLineControl {
    std::unique_ptr<std::byte[]> storage;
    size_t storage_bytes;
    std::pmr::monotonic_buffer_resource arena;
    std::pmr::vector<uint8_t> compute_shadow, render_shadow;
    LineCachedBindings compute, render;
    LineControlShape shape;
    explicit NativeLineControl(uint64_t charged)
        : storage(std::make_unique<std::byte[]>(static_cast<size_t>(charged - sizeof(NativeLineControl)))),
          storage_bytes(static_cast<size_t>(charged - sizeof(NativeLineControl))),
          arena(storage.get(), storage_bytes, std::pmr::null_memory_resource()),
          compute_shadow(&arena), render_shadow(&arena), compute(&arena), render(&arena) {}
    void configure(const LineControlShape& value) {
        compute_shadow.reserve(value.compute_uniforms);
        render_shadow.reserve(value.render_uniforms);
        compute.keys.reserve(value.compute_entries);
        render.keys.reserve(value.render_entries);
        compute.buffers.reserve(1);
        render.buffers.reserve(value.render_buffers);
        compute.textures.reserve(value.compute_textures);
        render.textures.reserve(value.render_textures);
        shape = value;
    }
};

struct NativeLineSlot {
    wgpu::Buffer output, compute_uniforms, render_uniforms;
    std::unique_ptr<NativeLineControl> control;
};

using NativeLinePool = vispy::lines::LineResourcePool<NativeLineSlot>;

struct FrameMark {
    struct Queries;
    uint64_t frame_id = 0;
    uint64_t begin_ns = 0;
    std::shared_ptr<Queries> queries;
};

struct NativeQuerySegment : vispy::timing::Segment {
    wgpu::QuerySet query_set;
    wgpu::Buffer resolve_buffer, readback_buffer;
    int canvas_id = 0;
    uint64_t ticket_id = 0, generation = 0, frame_id = 0, paint_token = 0;
    uint64_t buffer_capacity = 0;
    // Callback state is published under Segment::mutex; it remains separate
    // from the query status and from actual Ticket processing.
    bool map_requested = false, map_callback_complete = false;
};

struct FrameMark::Queries : vispy::timing::Frame {
    vispy::frames::Lifecycle work;
    int canvas_id = 0;
    uint64_t begin_ns = 0;
    bool final_requested = false;
    bool measured = false, gpu_timing = false, gpu_result_emitted = false;
    bool presentation_requested = false;
    vispy::frames::FrozenSubmission<Probe> final_counters;
};

struct QueuedFrame {
    std::vector<DrawSnap> draws;
    std::optional<FrameMark> mark;
    bool present = false;
    uint64_t id = 0, generation = 0;
};

struct Canvas {
    int id = 0;
    RenderState state;
    int width = 1;
    int height = 1;
    int samples = 1;
    bool vsync = false;
    wgpu::PresentMode present_mode = wgpu::PresentMode::Undefined;
    float clear_color[4] = {0, 0, 0, 1};
    bool clear_pending = false;
    int fbo = 0;
    std::vector<int> framebuffer_stack;
    int viewport[4] = {0, 0, -1, -1};
    int scissor[4] = {0, 0, -1, -1};
    bool scissor_enabled = false;
    int built_w = 0;
    int built_h = 0;
    int built_samples = 0;
    wgpu::Texture color;
    wgpu::TextureView color_view;
    wgpu::Texture multisampled_color;
    wgpu::TextureView multisampled_view;
    wgpu::Texture depth;
    wgpu::TextureView depth_view;
    wgpu::Texture presented;
    wgpu::TextureView presented_view;
    wgpu::BindGroup present_group;
    WGPUTextureView present_group_view = nullptr;
    WGPUBindGroupLayout present_group_layout = nullptr;
    WGPUSampler present_group_sampler = nullptr;
    uint64_t present_group_generation = 0;
    wgpu::Surface surface;
    std::shared_ptr<vispy::platform::NativeSurfaceOwner> surface_owner;
    double surface_scale = 1.0;
    uint64_t surface_generation = 1;
    bool surface_configured = false;
    int surface_w = 0;
    int surface_h = 0;
    bool present_swapchain = false;
    // True after the current color target has been presented to the HWND.
    // A later finish with no new draw must not submit again.
    bool swapchain_current = false;
    bool alive = true;
    bool deferred_present = false;
    std::vector<DrawSnap> pending;
    std::deque<QueuedFrame> queued_frames;
    std::optional<FrameMark> frame_mark;
    uint64_t active_paint_token = 0, last_closed_paint_token = 0;
    bool last_paint_aborted = false;
    std::optional<uint64_t> last_frame_id;
    bool gpu_timing_enabled = false;
    bool diagnostic_line_endpoints = false;
    bool capture_line_endpoints = true;
};

struct Ticket {
    struct OrderedUpload {
        TextureRev* revision;
        uint64_t uploaded_revision;
        uint64_t count;
        uint64_t bytes;
        uint64_t copied_bytes;
    };
    uint64_t id = 0, generation = 0;
    std::atomic<bool> complete{false};
    bool ok = false;
    std::string error;
    int canvas_id = 0;
    uint64_t submit_ns = 0;
    uint64_t completion_ns = 0;
    bool presented = false;
    std::vector<std::shared_ptr<BufferRev>> buffers;
    std::vector<std::shared_ptr<Artifact>> artifacts;
    std::vector<std::shared_ptr<TextureRev>> textures;
    std::vector<std::shared_ptr<const DrawSnap::LineInputs>> line_inputs;
    std::vector<std::shared_ptr<LineWork>> line_work;
    std::vector<std::shared_ptr<LineCapture>> line_captures;
    std::vector<wgpu::BindGroup> bind_groups;
    std::vector<wgpu::Buffer> transient_buffers;
    std::optional<NativeLinePool::BatchReservation> line_resources;
    bool submission_owner_retained = false;
    bool diagnostic_retirement_counted = false;
    std::vector<wgpu::Texture> owned_textures;
    std::vector<std::shared_ptr<vispy::platform::NativeSurfaceOwner>> surface_owners;
    std::vector<wgpu::Surface> surfaces;
    std::vector<OrderedUpload> ordered_uploads;
    Probe submitted_counters;
    std::shared_ptr<FrameMark::Queries> queries;
    std::shared_ptr<NativeQuerySegment> query_segment;
    std::shared_ptr<AsyncResult> encoding_validation;
    wgpu::Future encoding_validation_future{};
    ~Ticket() {
        if (!id && line_resources && !line_resources->submitted())
            line_resources->rollback(false);
        if (!id) for (const auto& capture : line_captures) {
            if (!capture) continue;
            capture->ticket_finished = true;
            if (capture->result.status == "encoded" || capture->result.status == "pending" ||
                    capture->result.status == "empty") {
                capture->result.status = "encoding_error";
                capture->set_error("endpoint command sequence ended before submission");
                capture->reset_readbacks();
            }
        }
        if (!id && queries) {
            queries->fail(vispy::timing::Status::SubmissionError, "GPU timing encoding ended before submission");
        }
    }
};

struct AsyncResult {
    std::atomic<bool> done{false};
    bool ok = false;
    std::string error;
};

struct DeviceCallbacks {
    std::mutex mu;
    std::deque<std::string> errors;
    std::atomic<bool> lost{false};
    std::string loss_message;
};

struct Engine {
    std::mutex mu;
    bool device_ready = false;
    bool device_lost = false;
    std::string last_error;
    // Declared before native device handles: repeatable log callback userdata
    // outlives all generations, including callbacks during their release.
    std::vector<std::shared_ptr<BackendShaderLog>> backend_shader_logs;
    std::shared_ptr<BackendShaderLog> current_backend_shader_log;
    dawn::native::Instance* native = nullptr;
    wgpu::Instance instance;
    wgpu::Adapter adapter;
    wgpu::Device device;
    wgpu::Queue queue;
    DeviceInfo info;
    Probe probe;
    std::unordered_map<int, GpuObject> objects;
    std::unordered_set<int> drop_next;
    std::unordered_set<int> deleted_now;
    std::unordered_map<int, Canvas> canvases;
    std::vector<std::string> trace;
    NativeShaderCache shader_artifacts;
    uint64_t device_generation = 0;
    uint64_t next_ticket = 1;
    uint64_t next_queued_frame = 1;
    uint64_t next_paint_token = 1;
    uint64_t next_line_capture = 1;
    std::deque<std::shared_ptr<LineCapture>> line_captures;
    uint64_t line_capture_bytes = 0;
    std::unique_ptr<NativeLinePool> line_pool;
    wgpu::Buffer line_canary;
    static constexpr uint64_t line_canary_capacity = 64ull * 1024;
    static constexpr size_t line_capture_limit = 128;
    static constexpr uint64_t line_capture_byte_limit = 64ull * 1024 * 1024;
    std::deque<std::shared_ptr<Ticket>> tickets;
    size_t frame_slots = 3;
    std::deque<std::shared_ptr<FrameMark::Queries>> query_frames;
    std::deque<std::shared_ptr<FrameMark::Queries>> frame_works;
    std::unordered_map<int, std::deque<BenchmarkCompletion>> completion_records;
    std::unordered_map<int, std::deque<vispy::timing::FrameResult>> gpu_records;
    size_t completion_record_count = 0, gpu_record_count = 0;
    static constexpr size_t terminal_record_limit = 4096;
    std::deque<int> terminal_canvases;
    std::vector<std::shared_ptr<NativeQuerySegment>> query_segments;
    uint64_t successful_ticket_retirements = 0, failed_ticket_retirements = 0;
    // Map callbacks capture this lifetime-safe counter, never an Engine pointer
    // or its mutex. Device/canvas teardown cannot invalidate the counter.
    std::shared_ptr<std::atomic<uint64_t>> query_map_callbacks_completed =
        std::make_shared<std::atomic<uint64_t>>(0);
    std::shared_ptr<DeviceCallbacks> callbacks = std::make_shared<DeviceCallbacks>();
    vispy::platform::NativeLibrary layer;
    uint64_t (*layer_count)() = nullptr;
    uint64_t (*layer_bresenham_devices)() = nullptr;
    uint64_t (*layer_bresenham_pipelines)() = nullptr;
    uint64_t (*layer_last_vertex_devices)() = nullptr;
    uint64_t (*layer_last_vertex_pipelines)() = nullptr;
    VulkanMemorySnapshotFn layer_memory_snapshot = nullptr;
    VulkanMemoryWindowBeginFn layer_memory_window_begin = nullptr;
    VulkanMemoryWindowEndFn layer_memory_window_end = nullptr;
    uint64_t memory_window_token = 0, memory_window_generation = 0, memory_window_invalidations = 0;
    VulkanMemoryWindow last_memory_window;

    ~Engine() {
        // A failed explicit shutdown may leave Canvas owners in the table.
        // Destroy is synchronous in the pinned Dawn implementation and flushes
        // every WSI deletion before automatic member destruction closes Xlib.
        if (device) device.Destroy();
        delete native;
        native = nullptr;
    }

    bool memory_window_idle() {
        update_work_peaks();
        if (probe.pending_tickets || probe.queued_frames || probe.pending_draws || probe.pending_timestamp_frames) return false;
        for (const auto& entry : canvases)
            if (entry.second.frame_mark || entry.second.active_paint_token) return false;
        return true;
    }

    VulkanMemoryWindow close_memory_window(bool cancel) {
        VulkanMemoryWindow record;
        if (!memory_window_token || !layer_memory_window_end ||
            !layer_memory_window_end(memory_window_token, &record, sizeof(record)))
            throw std::runtime_error("allocation window: active layer owner unavailable");
        if (device_lost || device_generation != memory_window_generation)
            memory_window_invalidations |= WindowDeviceLost;
        record.invalidations |= memory_window_invalidations;
        if (cancel) record.invalidations |= WindowCancelled;
        if (record.invalidations) {
            record.complete = 0;
            record.status = cancel ? VulkanMemoryWindowStatus::Cancelled : VulkanMemoryWindowStatus::Incomplete;
        }
        memory_window_token = 0;
        last_memory_window = record;
        return record;
    }
    std::array<std::shared_ptr<TextureRev>, 3> dummy_textures;
    wgpu::RenderPipeline present_pipeline;
    wgpu::BindGroupLayout present_layout;
    wgpu::Sampler present_sampler;
    bool present_ready = false;
    wgpu::RenderPipeline depth_upload_pipeline;
    wgpu::BindGroupLayout depth_upload_layout;
    // Default MSAA Canvas read_pixels selects actual sample zero for both
    // aspects (OpenGL4.6 section18.2.3 permits implementation-selected values).
    std::array<wgpu::RenderPipeline, 2> sample_zero_capture_pipelines;
    std::array<wgpu::BindGroupLayout, 2> sample_zero_capture_layouts;
    wgpu::RenderPipeline depth_capture_pipeline;
    wgpu::BindGroupLayout depth_capture_layout;

    void store_artifact(const std::shared_ptr<Artifact>& artifact) {
        using Base = vispy::shader::DeviceShaderArtifact<
            wgpu::ShaderModule, wgpu::RenderPipeline, wgpu::BindGroupLayout>;
        if (artifact->evaluator) shader_artifacts.store_auxiliary(artifact->portable, artifact->evaluator);
        artifact->for_each_consumer([&](std::string_view policy, const auto& consumer) {
            if (consumer->original != artifact->portable || consumer->evaluator != artifact->evaluator)
                throw std::runtime_error("lines: device consumer has a different captured original/evaluator pair");
            shader_artifacts.store_consumer(artifact->portable, policy, consumer);
        });
        shader_artifacts.store_device(artifact->portable,
            {artifact->device_generation, artifact->default_has_depth}, artifact,
            artifact->storage_bytes(sizeof(Artifact) - sizeof(Base)));
        update_work_peaks();
    }

    void refresh_artifact(const Artifact& artifact) {
        const auto key = vispy::shader::DeviceArtifactKey{artifact.device_generation, artifact.default_has_depth};
        auto cached = shader_artifacts.find_device(artifact.portable->identity, key);
        // An evicted live program can share an identity/key with a newly
        // cached record. Its variant growth must not overwrite that other
        // record's byte charge.
        if (cached.get() != &artifact) return;
        using Base = vispy::shader::DeviceShaderArtifact<
            wgpu::ShaderModule, wgpu::RenderPipeline, wgpu::BindGroupLayout>;
        shader_artifacts.refresh_device(artifact.portable->identity, key,
            artifact.storage_bytes(sizeof(Artifact) - sizeof(Base)));
        update_work_peaks();
    }

    void update_work_peaks() {
        probe.pending_timestamp_frames = query_frames.size();
        probe.peak_pending_timestamp_frames = std::max(probe.peak_pending_timestamp_frames, probe.pending_timestamp_frames);
        probe.pending_tickets = tickets.size();
        probe.queued_frames = probe.pending_draws = 0;
        for (const auto& [id, canvas] : canvases) {
            probe.queued_frames += canvas.queued_frames.size();
            probe.pending_draws += std::count_if(canvas.pending.begin(), canvas.pending.end(),
                [](const auto& draw) { return !draw.staged_admission; });
            for (const auto& frame : canvas.queued_frames) probe.pending_draws += frame.draws.size();
        }
        probe.peak_pending_tickets = std::max(probe.peak_pending_tickets, probe.pending_tickets);
        probe.peak_queued_frames = std::max(probe.peak_queued_frames, probe.queued_frames);
        probe.peak_pending_draws = std::max(probe.peak_pending_draws, probe.pending_draws);
        probe.peak_shader_cache_bytes = std::max<uint64_t>(probe.peak_shader_cache_bytes, shader_artifacts.storage_bytes());
    }

    void freeze_submission_counters(Ticket& ticket, HostTimer& submit_timer) {
        update_work_peaks();
        // Descriptor scans are explicit probe/marked-submission observations,
        // not a claim about unsampled allocations or driver memory peaks.
        if (ticket.queries && ticket.queries->measured) update_descriptor_accounting();
        if (layer_count) probe.vk_queue_submits = layer_count();
        if (layer_bresenham_pipelines) probe.bresenham_line_pipelines = layer_bresenham_pipelines();
        if (layer_last_vertex_pipelines) probe.last_vertex_pipelines = layer_last_vertex_pipelines();
        update_memory_snapshot();
        submit_timer.finish();
        ticket.submitted_counters = probe;
        if (ticket.queries && ticket.queries->measured && ticket.queries->work.last_ticket == ticket.id)
            ticket.queries->final_counters.capture(ticket.id, ticket.submitted_counters);
    }

    void update_memory_snapshot() {
        probe.vk_memory_available = probe.vk_memory_complete = false;
        VulkanMemoryTelemetry snapshot;
        if (!layer_memory_snapshot || !layer_memory_snapshot(&snapshot, sizeof(snapshot)) || snapshot.schema != 1) return;
        probe.vk_memory_active_devices = snapshot.active_devices;
        probe.vk_memory_tracking_devices = snapshot.tracking_devices;
        probe.vk_memory_allocate_calls = snapshot.allocate_calls;
        probe.vk_memory_allocate_failures = snapshot.allocate_failures;
        probe.vk_memory_allocation_count = snapshot.allocation_count;
        probe.vk_memory_allocated_bytes = snapshot.allocated_bytes;
        probe.vk_memory_free_calls = snapshot.free_calls;
        probe.vk_memory_free_count = snapshot.free_count;
        probe.vk_memory_freed_bytes = snapshot.freed_bytes;
        probe.vk_memory_null_free_calls = snapshot.null_free_calls;
        probe.vk_memory_unknown_free_calls = snapshot.unknown_free_calls;
        probe.vk_memory_live_allocations = snapshot.live_allocations;
        probe.vk_memory_live_bytes = snapshot.live_bytes;
        probe.vk_memory_peak_live_allocations = snapshot.peak_live_allocations;
        probe.vk_memory_peak_live_bytes = snapshot.peak_live_bytes;
        probe.vk_memory_retired_allocations = snapshot.retired_allocations;
        probe.vk_memory_retired_bytes = snapshot.retired_bytes;
        probe.vk_memory_tracking_errors = snapshot.tracking_errors;
        probe.vk_memory_available = snapshot.active_devices > 0 && snapshot.tracking_devices == snapshot.active_devices;
        probe.vk_memory_complete = probe.vk_memory_available && !snapshot.tracking_errors && !snapshot.retired_allocations;
    }

    void log(const std::string& line) {
        static const bool stderr_trace = std::getenv("VISPY_DAWN_TRACE") != nullptr;
        if (stderr_trace) std::cerr << "vispy-dawn: " << line << std::endl;
        if (trace.size() >= 4096) trace.erase(trace.begin(), trace.begin() + 1024);
        trace.push_back(line);
    }

    void collect_frame_completion(const std::shared_ptr<FrameMark::Queries>& frame) {
        if (!frame) return;
        if (frame->work.admission_finished()) frame->finalized = true;
        if (!frame->work.ready() || frame->work.emitted) return;
        if (frame->measured) {
            if (completion_record_count >= terminal_record_limit)
                throw std::runtime_error("benchmark completion queue full; consume frame records");
            BenchmarkCompletion record;
            record.frame_id = frame->frame_id;
            record.paint_token = frame->work.paint_token;
            record.frame_scope = record.paint_token ? "qt_paint" : "native_present";
            record.submission_count = frame->work.submissions;
            record.present_count = frame->work.presents;
            record.last_present_submission_index = frame->work.last_present_submission_index;
            record.ownership_closed = frame->work.closed;
            record.ownership_retired = frame->work.ready();
            record.completion_timestamp_ns = frame->work.completed_at();
            record.completion_latency_ns = record.completion_timestamp_ns - frame->work.begin_ns;
            record.submit_latency_ns = frame->work.last_submit_ns ? frame->work.last_submit_ns - frame->work.begin_ns : 0;
            record.status = frame->work.status();
            record.error = frame->work.error;
            record.presented = frame->work.presents != 0;
            record.counters_captured = frame->final_counters.value.has_value() &&
                frame->final_counters.ticket == frame->work.last_ticket;
            if (record.counters_captured) record.counters = *frame->final_counters.value;
            completion_records[frame->canvas_id].push_back(std::move(record));
            ++completion_record_count;
        }
        frame->work.emitted = true;
    }

    void record_completion(Ticket& ticket, const std::string& status) {
        auto frame = ticket.queries;
        // User cancellation changes the capture/frame result, not successful
        // native payload validity. A native validation/queue failure or loss
        // discards its slots only here, after actual completion processing.
        auto process = [&] {
            if (ticket.line_resources && ticket.line_resources->submitted() && !ticket.line_resources->finished())
                ticket.line_resources->retire(status == "success");
            if (ticket.id && frame)
                frame->work.retired(ticket.completion_ns ? ticket.completion_ns : monotonic_ns());
        };
        if (ticket.id)
            vispy::lines::process_ticket_retirement_once(ticket.diagnostic_retirement_counted,
                successful_ticket_retirements, failed_ticket_retirements, status == "success", process);
        else process();
        // Metadata/receipt publication may allocate or refuse a full terminal
        // queue. A retry performs these idempotent updates without processing
        // the already-retired native owner or frame again.
        if (status != "success") {
            const auto canvas = canvases.find(ticket.canvas_id);
            if (canvas != canvases.end()) canvas->second.present_group = nullptr;
        }
        for (const auto& capture : ticket.line_captures) {
            if (!capture) continue;
            capture->ticket_finished = true;
            if (capture->result.status != "submitted" && capture->result.status != "encoded" &&
                    !(capture->result.status == "empty" && status != "success")) {
                // A prior cancellation remains unsuccessful, even if the
                // queue later completes its already-submitted commands.
                if (capture->result.status != "retired" && capture->result.status != "empty")
                    capture->reset_readbacks();
                continue;
            }
            capture->result.status = status == "success" ? "retired" : status;
            capture->set_error(status == "success" ? std::string{} :
                (ticket.error.empty() ? "endpoint submission did not complete successfully: " + status : ticket.error));
            if (status != "success") capture->reset_readbacks();
        }
        if (frame) {
            if (status != "success") {
                const auto state = status == "device_lost" ? vispy::timing::Status::DeviceLost : vispy::timing::Status::SubmissionError;
                frame->fail(state, "GPU queue completion failed: " + status);
                frame->work.fail(status == "device_lost" ? "device_lost" : "failed", ticket.error.empty() ? "GPU queue completion failed: " + status : ticket.error);
            }
            collect_frame_completion(frame);
        }
    }

    void finalize_query_frame(const std::shared_ptr<FrameMark::Queries>& frame) {
        if (!frame) return;
        frame->work.close(monotonic_ns());
        frame->final_requested = true;
        auto found = canvases.find(frame->canvas_id);
        if (found != canvases.end() && found->second.frame_mark &&
            found->second.frame_mark->queries == frame && !found->second.active_paint_token)
            found->second.frame_mark.reset();
        collect_frame_completion(frame);
    }

    static void fail_line_capture(const std::shared_ptr<LineCapture>& capture,
                                  const std::string& status, const std::string& reason,
                                  bool include_retired = false) {
        if (!capture) return;
        auto& result = capture->result;
        if (result.status != "pending" && result.status != "encoded" && result.status != "submitted" &&
                result.status != "empty" && !(include_retired && result.status == "retired")) return;
        result.status = status;
        capture->set_error(reason);
        result.data.clear();
        if (!result.ticket_id || capture->ticket_finished) capture->reset_readbacks();
    }

    static void fail_line_snapshots(const std::vector<DrawSnap>& draws,
                                    const std::string& status, const std::string& reason) {
        for_each_draw_leaf(draws, [&](const DrawSnap& snap) {
            if (snap.line_work) fail_line_capture(snap.line_work->capture, status, reason);
        });
    }

    template<class Call>
    static void for_each_draw_leaf(const std::vector<DrawSnap>& draws, Call&& call) {
        for (const auto& snap : draws) {
            if (snap.line_chunks) {
                for (const auto& leaf : *snap.line_chunks) call(leaf);
            } else call(snap);
        }
    }

    static void flatten_line_snapshots(std::vector<DrawSnap>& draws) {
        if (std::none_of(draws.begin(), draws.end(), [](const auto& snap) { return bool(snap.line_chunks); })) return;
        size_t count = 0;
        for_each_draw_leaf(draws, [&](const auto&) { ++count; });
        std::vector<DrawSnap> next;
        next.reserve(count);
        for (const auto& snap : draws) {
            if (snap.line_chunks) {
                for (const auto& leaf : *snap.line_chunks) {
                    next.push_back(leaf);
                    next.back().line_inputs = snap.line_inputs;
                }
            } else next.push_back(snap);
        }
        draws.swap(next);
    }

    void cancel_frame(const std::shared_ptr<FrameMark::Queries>& frame,
                      const std::string& status, const std::string& reason) {
        if (!frame || frame->work.emitted) return;
        frame->work.fail(status, reason);
        frame->fail(status == "device_lost" ? vispy::timing::Status::DeviceLost :
                    status == "cancelled" ? vispy::timing::Status::Cancelled : vispy::timing::Status::SubmissionError, reason);
        auto found = canvases.find(frame->canvas_id);
        if (found != canvases.end()) {
            auto& canvas = found->second;
            std::erase_if(canvas.queued_frames, [&](const auto& batch) {
                if (!batch.mark || batch.mark->queries != frame) return false;
                fail_line_snapshots(batch.draws, status, reason);
                frame->work.discard_queued(1); return true;
            });
            if (canvas.frame_mark && canvas.frame_mark->queries == frame) {
                fail_line_snapshots(canvas.pending, status, reason);
                canvas.pending.clear();
                canvas.frame_mark.reset();
                if (canvas.active_paint_token) canvas.last_closed_paint_token = canvas.active_paint_token;
                canvas.last_paint_aborted = true;
                canvas.active_paint_token = 0;
            }
            canvas.deferred_present = !canvas.queued_frames.empty();
        }
        for (const auto& ticket : tickets) if (ticket->queries == frame)
            for (const auto& capture : ticket->line_captures) fail_line_capture(capture, status, reason);
        finalize_query_frame(frame);
    }

    void cancel_canvas_frames(Canvas& canvas, const std::string& status, const std::string& reason) {
        for (const auto& capture : line_captures) if (capture->canvas_id == canvas.id)
            fail_line_capture(capture, status, reason);
        std::vector<std::shared_ptr<FrameMark::Queries>> owners;
        if (canvas.frame_mark) owners.push_back(canvas.frame_mark->queries);
        for (const auto& batch : canvas.queued_frames) if (batch.mark) owners.push_back(batch.mark->queries);
        for (const auto& frame : frame_works) if (frame->canvas_id == canvas.id) owners.push_back(frame);
        for (const auto& ticket : tickets) if (ticket->canvas_id == canvas.id) owners.push_back(ticket->queries);
        std::unordered_set<FrameMark::Queries*> seen;
        for (const auto& owner : owners) if (owner && seen.insert(owner.get()).second) cancel_frame(owner, status, reason);
    }

    std::shared_ptr<FrameMark::Queries> start_frame(Canvas& canvas, uint64_t frame_id, bool measured) {
        if (measured && (frame_works.size() >= frame_slots ||
            completion_record_count + frame_works.size() >= terminal_record_limit))
            throw std::runtime_error("benchmark frame ownership capacity full; consume records and process events");
        auto frame = std::make_shared<FrameMark::Queries>();
        frame->canvas_id = canvas.id; frame->frame_id = frame_id;
        frame->begin_ns = frame->work.begin_ns = monotonic_ns();
        frame->device_generation = frame->work.generation = device_generation;
        frame->measured = measured;
        frame->gpu_timing = measured && canvas.gpu_timing_enabled;
        frame->quantization_ns = info.timestamp_quantization_ns;
        if (frame->gpu_timing) {
            const auto records = gpu_records.find(canvas.id);
            const auto count = records == gpu_records.end() ? 0 : records->second.size();
            if (query_frames.size() >= frame_slots || count >= frame_slots * 2 ||
                gpu_record_count + query_frames.size() >= terminal_record_limit ||
                query_segments.size() >= frame_slots * vispy::timing::max_submissions_per_frame)
                throw std::runtime_error("benchmark GPU timing capacity full; consume timing records and process events");
            if (!info.timestamp_query) frame->fail(vispy::timing::Status::UnsupportedFeature, "TimestampQuery was not granted");
        }
        if (measured) frame_works.push_back(frame);
        try { if (frame->gpu_timing) query_frames.push_back(frame); }
        catch (...) {
            if (measured) frame_works.pop_back();
            throw;
        }
        canvas.frame_mark = FrameMark{frame_id, frame->begin_ns, frame};
        update_work_peaks();
        return frame;
    }

    vispy::frames::AdmissionCapacity frame_capacity(const Canvas& canvas) const {
        vispy::frames::AdmissionCapacity capacity;
        capacity.slots = frame_slots; capacity.tickets = tickets.size();
        capacity.queued_batches = canvas.queued_frames.size(); capacity.owners = frame_works.size();
        capacity.queries = query_frames.size(); capacity.query_segments = query_segments.size();
        capacity.query_segment_limit = frame_slots * vispy::timing::max_submissions_per_frame;
        capacity.completions = completion_record_count; capacity.gpu_records = gpu_record_count;
        const auto records = gpu_records.find(canvas.id);
        capacity.canvas_gpu_records = records == gpu_records.end() ? 0 : records->second.size();
        capacity.terminal_limit = terminal_record_limit; capacity.canvas_gpu_record_limit = frame_slots * 2;
        capacity.gpu_timing = canvas.gpu_timing_enabled;
        return capacity;
    }

    void poll_query_results() {
        for (const auto& frame : frame_works) collect_frame_completion(frame);
        std::erase_if(query_segments, [](const auto& segment) {
            std::lock_guard<std::mutex> lock(segment->mutex);
            return segment->status != vispy::timing::Status::Pending;
        });
        // A late map callback must not let a subsequent frame overtake it in
        // that canvas's result stream. Other canvases can still make progress.
        std::unordered_set<int> blocked_canvases;
        for (auto it = query_frames.begin(); it != query_frames.end();) {
            if (blocked_canvases.contains((*it)->canvas_id)) { ++it; continue; }
            vispy::timing::FrameResult result;
            const auto records = gpu_records.find((*it)->canvas_id);
            const auto count = records == gpu_records.end() ? 0 : records->second.size();
            if (gpu_record_count < terminal_record_limit && count < frame_slots * 2 && (*it)->collect(result)) {
                gpu_records[(*it)->canvas_id].push_back(std::move(result));
                ++gpu_record_count;
                (*it)->gpu_result_emitted = true;
                it = query_frames.erase(it);
            } else { blocked_canvases.insert((*it)->canvas_id); ++it; }
        }
        std::erase_if(frame_works, [](const auto& frame) {
            return frame->work.emitted && (!frame->gpu_timing || frame->gpu_result_emitted);
        });
        update_work_peaks();
    }

    void attach_frame(Ticket& ticket, const std::shared_ptr<FrameMark::Queries>& owner, uint64_t pass_capacity) {
        ticket.queries = owner;
        if (!owner || !owner->gpu_timing) return;
        auto& frame = *ticket.queries;
        uint32_t queries = 0;
        if (!frame.reserve(device_generation, pass_capacity, queries) || !queries) return;
        auto segment = std::make_shared<NativeQuerySegment>();
        segment->reserved_queries = queries;
        segment->submission_index = frame.submission_count;
        wgpu::QuerySetDescriptor descriptor;
        descriptor.type = wgpu::QueryType::Timestamp;
        descriptor.count = queries;
        segment->query_set = device.CreateQuerySet(&descriptor);
        ++probe.timestamp_query_sets;
        wgpu::BufferDescriptor buffer;
        buffer.size = uint64_t(queries) * sizeof(uint64_t);
        segment->buffer_capacity = buffer.size;
        buffer.usage = wgpu::BufferUsage::QueryResolve | wgpu::BufferUsage::CopySrc | wgpu::BufferUsage::CopyDst;
        segment->resolve_buffer = device.CreateBuffer(&buffer);
        ++probe.buffer_allocations;
        buffer.usage = wgpu::BufferUsage::MapRead | wgpu::BufferUsage::CopyDst;
        segment->readback_buffer = device.CreateBuffer(&buffer);
        ++probe.buffer_allocations;
        frame.segments.push_back(segment);
        ticket.query_segment = segment;
    }

    void attach_query_frame(Canvas& canvas, Ticket& ticket, uint64_t pass_capacity) {
        attach_frame(ticket, canvas.frame_mark ? canvas.frame_mark->queries : nullptr, pass_capacity);
    }

    wgpu::RenderPassEncoder begin_timed_pass(const wgpu::CommandEncoder& encoder,
                                            wgpu::RenderPassDescriptor descriptor,
                                            Ticket* ticket, const char* kind) {
        wgpu::PassTimestampWrites writes;
        if (ticket && ticket->query_segment) {
            auto& segment = *ticket->query_segment;
            const uint32_t index = static_cast<uint32_t>(segment.kinds.size() * 2);
            if (index + 2 <= segment.reserved_queries) {
                segment.kinds.emplace_back(kind);
                writes.querySet = segment.query_set;
                writes.beginningOfPassWriteIndex = index;
                writes.endOfPassWriteIndex = index + 1;
                descriptor.timestampWrites = &writes;
            } else ticket->queries->fail(vispy::timing::Status::PassLimit, "actual pass count exceeds reserved query layout");
        }
        ++probe.render_passes;
        return encoder.BeginRenderPass(&descriptor);
    }

    wgpu::ComputePassEncoder begin_timed_compute_pass(const wgpu::CommandEncoder& encoder, Ticket& ticket) {
        wgpu::ComputePassDescriptor descriptor;
        wgpu::PassTimestampWrites writes;
        if (ticket.query_segment) {
            auto& segment = *ticket.query_segment;
            const uint32_t index = static_cast<uint32_t>(segment.kinds.size() * 2);
            if (index + 2 <= segment.reserved_queries) {
                segment.kinds.emplace_back("line_endpoints");
                writes.querySet = segment.query_set;
                writes.beginningOfPassWriteIndex = index;
                writes.endOfPassWriteIndex = index + 1;
                descriptor.timestampWrites = &writes;
            } else ticket.queries->fail(vispy::timing::Status::PassLimit,
                                       "actual compute pass count exceeds reserved query layout");
        }
        ++probe.compute_passes;
        return encoder.BeginComputePass(&descriptor);
    }

    void resolve_ticket_queries(const wgpu::CommandEncoder& encoder, Ticket& ticket) {
        if (!ticket.query_segment || ticket.query_segment->kinds.empty()) return;
        auto& segment = *ticket.query_segment;
        const uint32_t count = static_cast<uint32_t>(segment.kinds.size() * 2);
        encoder.ResolveQuerySet(segment.query_set, 0, count, segment.resolve_buffer, 0);
        encoder.CopyBufferToBuffer(segment.resolve_buffer, 0, segment.readback_buffer, 0,
                                   uint64_t(count) * sizeof(uint64_t));
        ++probe.timestamp_resolves;
    }

    void map_ticket_queries(Ticket& ticket) {
        if (!ticket.queries) return;
        ++ticket.queries->submission_count;
        auto segment = ticket.query_segment;
        if (!segment) return;
        segment->canvas_id = ticket.canvas_id;
        segment->ticket_id = ticket.id;
        segment->generation = ticket.generation;
        segment->frame_id = ticket.queries->frame_id;
        segment->paint_token = ticket.queries->work.paint_token;
        if (segment->kinds.empty()) { segment->status = vispy::timing::Status::Success; return; }
        query_segments.push_back(segment);
        const uint64_t bytes = segment->kinds.size() * 2 * sizeof(uint64_t);
        ++probe.timestamp_readbacks;
        segment->readback_buffer.MapAsync(wgpu::MapMode::Read, 0, bytes, wgpu::CallbackMode::AllowProcessEvents,
            [segment, bytes, completed = query_map_callbacks_completed](wgpu::MapAsyncStatus status, wgpu::StringView message) {
                std::lock_guard<std::mutex> lock(segment->mutex);
                struct PublishCompletion {
                    NativeQuerySegment& segment;
                    const std::shared_ptr<std::atomic<uint64_t>>& completed;
                    ~PublishCompletion() {
                        segment.map_callback_complete = true;
                        completed->fetch_add(1, std::memory_order_relaxed);
                    }
                } completion{*segment, completed};
                if (status != wgpu::MapAsyncStatus::Success) {
                    segment->status = vispy::timing::Status::MapError;
                    segment->error = view_to_string(message);
                    return;
                }
                try {
                    const void* data = segment->readback_buffer.GetConstMappedRange(0, bytes);
                    if (!data) throw std::runtime_error("successful timestamp map returned no data");
                    segment->values.resize(bytes / sizeof(uint64_t));
                    std::memcpy(segment->values.data(), data, static_cast<size_t>(bytes));
                    segment->status = vispy::timing::Status::Success;
                } catch (const std::exception& error) {
                    segment->error = error.what(); segment->status = vispy::timing::Status::MapError;
                } catch (...) {
                    segment->error = "timestamp callback copy failed"; segment->status = vispy::timing::Status::MapError;
                }
                segment->readback_buffer.Unmap();
            });
        // Publish only after the actual call returns. The Engine mutex blocks
        // peeks during registration, and no segment lock crosses a Dawn call.
        std::lock_guard<std::mutex> lock(segment->mutex);
        segment->map_requested = true;
    }

    void poll() {
        if (instance) instance.ProcessEvents();
        if (callbacks->lost.exchange(false)) invalidate_device();
        while (!tickets.empty() && tickets.front()->complete.load()) {
            const auto& ticket = tickets.front();
            if (ticket->encoding_validation && !ticket->encoding_validation->done.load()) break;
            if (ticket->encoding_validation && !ticket->encoding_validation->ok) {
                ticket->ok = false;
                ticket->error = "endpoint command validation: " + ticket->encoding_validation->error;
            }
            log("TICKET complete id=" + std::to_string(ticket->id));
            record_completion(*ticket, ticket->ok ? "success" : "failed");
            const auto error = ticket->ok ? std::string{} : ticket->error;
            for (const auto& buf : ticket->buffers) {
                if (buf.use_count() == 1)
                    log("FREE buffer owner=" + std::to_string(buf->owner) +
                        " generation=" + std::to_string(buf->generation));
            }
            tickets.pop_front();
            ++probe.retired_tickets;
            if (!error.empty() && !device_lost)
                throw std::runtime_error("Dawn submission: " + error);
        }
        poll_query_results();
        probe.pending_tickets = tickets.size();
        update_work_peaks();
        std::lock_guard<std::mutex> guard(callbacks->mu);
        if (!callbacks->errors.empty()) {
            last_error = callbacks->errors.front();
            callbacks->errors.clear();
            throw std::runtime_error("Dawn: " + last_error);
        }
    }

    void track_submission(std::shared_ptr<Ticket> ticket) {
        if (!ticket) ticket = std::make_shared<Ticket>();
        ticket->id = next_ticket++;
        ticket->generation = device_generation;
        for (const auto& capture : ticket->line_captures) {
            capture->result.ticket_id = ticket->id;
            if (capture->result.status == "encoded") capture->result.status = "submitted";
        }
        if (ticket->queries)
            ticket->queries->work.submitted(ticket->id, ticket->submit_ns, device_generation);
        if (!ticket->submission_owner_retained) tickets.push_back(ticket);
        queue.OnSubmittedWorkDone(wgpu::CallbackMode::AllowProcessEvents,
            [ticket](wgpu::QueueWorkDoneStatus status, wgpu::StringView message) {
                ticket->ok = status == wgpu::QueueWorkDoneStatus::Success;
                ticket->error = view_to_string(message);
                ticket->completion_ns = monotonic_ns();
                ticket->complete.store(true);
            });
        // Preserve the actual completion callback even if CPU query-map
        // admission fails after this Ticket was submitted.
        try { map_ticket_queries(*ticket); }
        catch (const std::exception& error) {
            if (ticket->queries) ticket->queries->fail(vispy::timing::Status::MapError, error.what());
            if (ticket->query_segment) {
                std::lock_guard<std::mutex> lock(ticket->query_segment->mutex);
                ticket->query_segment->status = vispy::timing::Status::MapError;
                ticket->query_segment->error = error.what();
            }
            throw;
        }
        update_work_peaks();
    }

    bool wait_result(wgpu::Future future, const std::shared_ptr<AsyncResult>& result) {
        auto status = instance.WaitAny(future, 30'000'000'000ull);
        if (status != wgpu::WaitStatus::Success || !result->done.load()) {
            last_error = "Dawn callback wait failed or timed out";
            return false;
        }
        if (!result->ok) last_error = result->error;
        return result->ok;
    }

    std::string pop_validation() {
        auto result = std::make_shared<AsyncResult>();
        auto future = device.PopErrorScope(wgpu::CallbackMode::WaitAnyOnly,
            [result](wgpu::PopErrorScopeStatus status, wgpu::ErrorType type, wgpu::StringView message) {
                result->ok = status == wgpu::PopErrorScopeStatus::Success && type == wgpu::ErrorType::NoError;
                result->error = view_to_string(message);
                result->done.store(true);
            });
        return wait_result(future, result) ? std::string{} :
            (last_error.empty() ? "Dawn validation failed" : last_error);
    }

    std::string finish_pipeline_creation(PipelineCreationScopes& scopes, uint64_t generation) {
        auto error = scopes.finish();
        if (generation != device_generation || device_lost || callbacks->lost.load()) {
            if (!error.empty()) error += "; ";
            error += "device generation was lost or replaced during pipeline creation";
        }
        if (current_backend_shader_log && current_backend_shader_log->failed.load()) {
            if (!error.empty()) error += "; ";
            error += "Dawn backend shader diagnostic log write failed";
        }
        return error;
    }

    void invalidate_device() {
        if (memory_window_token) memory_window_invalidations |= WindowDeviceLost;
        device_lost = true;
        device_ready = false;
        info.ok = false;
        info.error = "device lost";
        info.loss_count += 1;
        for (const auto& frame : query_frames) {
            frame->fail(vispy::timing::Status::DeviceLost, "device lost before GPU timing collection");
            frame->finalized = true;
        }
        for (auto& [id, canvas] : canvases)
            cancel_canvas_frames(canvas, "device_lost", "device lost before complete paint retirement");
        for (const auto& ticket : tickets) record_completion(*ticket, "device_lost");
        for (const auto& capture : line_captures) {
            capture->destroy_readbacks();
            fail_line_capture(capture, "device_lost", "device lost before endpoint collection", true);
            // Destroy also cancels an outstanding MapAsync. Its callback owns
            // only the old buffer/result, never the Engine or a new instance.

        }
        for (auto& entry : canvases) {
            auto& canvas = entry.second;
            canvas.frame_mark.reset();
            canvas.color = nullptr;
            canvas.color_view = nullptr;
            canvas.multisampled_color = nullptr;
            canvas.multisampled_view = nullptr;
            canvas.depth = nullptr;
            canvas.depth_view = nullptr;
            canvas.presented = nullptr;
            canvas.presented_view = nullptr;
            canvas.present_group = nullptr;
            canvas.built_w = 0;
            canvas.built_h = 0;
            canvas.pending.clear();
            canvas.queued_frames.clear();
            canvas.surface_configured = false;
            canvas.surface_w = 0;
            canvas.surface_h = 0;
            canvas.swapchain_current = false;
            ++canvas.surface_generation;
            if (canvas.surface) {
                canvas.surface.Unconfigure();
                canvas.surface = nullptr;
            }
        }
        for (const auto& frame : query_frames) finalize_query_frame(frame);
        std::unordered_set<TextureRev*> invalidated_textures;
        std::function<void(const std::shared_ptr<TextureRev>&)> invalidate_texture;
        invalidate_texture = [&](const std::shared_ptr<TextureRev>& rev) {
            if (!rev || !invalidated_textures.insert(rev.get()).second) return;
            rev->texture = nullptr;
            rev->view = nullptr;
            rev->sampler = nullptr;
            rev->allocation_token.reset();
            invalidate_texture(rev->base);
        };
        std::unordered_set<BufferRev*> invalidated_buffers;
        std::function<void(const std::shared_ptr<BufferRev>&)> invalidate_buffer;
        invalidate_buffer = [&](const std::shared_ptr<BufferRev>& rev) {
            if (!rev || !invalidated_buffers.insert(rev.get()).second) return;
            rev->gpu = nullptr;
            for (const auto& [key, child] : rev->derived) invalidate_buffer(child);
        };
        for (auto& entry : objects) {
            invalidate_texture(entry.second.texture);
            invalidate_buffer(entry.second.buffer);
            invalidate_buffer(entry.second.primitive_indices);
            invalidate_buffer(entry.second.point_geometry_cache);
            invalidate_buffer(entry.second.input_geometry_cache);
            entry.second.input_current.for_each([&](auto, const auto&, const auto& record) {
                invalidate_buffer(record);
            });
            entry.second.input_oversized.for_each([&](auto, const auto&, const auto& record) {
                invalidate_buffer(record);
            });
            for (auto& [name, binding] : entry.second.attributes)
                invalidate_buffer(binding.constant_buffer);
            if (entry.second.artifact) {
                entry.second.artifact->invalidate();
            }
            if (entry.second.point_artifact) entry.second.point_artifact->invalidate();
            if (entry.second.affine_artifact) entry.second.affine_artifact->invalidate();
            if (entry.second.indexed_artifact) entry.second.indexed_artifact->invalidate();
            if (entry.second.batch_affine_artifact) entry.second.batch_affine_artifact->invalidate();
            if (entry.second.batch_indexed_artifact) entry.second.batch_indexed_artifact->invalidate();
        }
        shader_artifacts.clear_devices();
        line_pool.reset();
        line_canary = nullptr;
        present_pipeline = nullptr;
        present_layout = nullptr;
        present_sampler = nullptr;
        present_ready = false;
        depth_upload_pipeline = nullptr;
        depth_upload_layout = nullptr;
        for (auto& pipeline : sample_zero_capture_pipelines) pipeline = nullptr;
        for (auto& layout : sample_zero_capture_layouts) layout = nullptr;
        depth_capture_pipeline = nullptr;
        depth_capture_layout = nullptr;
        for (auto& texture : dummy_textures) texture.reset();
        if (device) device.Destroy();
        if (instance) instance.ProcessEvents();
        tickets.clear();
        poll_query_results();
        {
            std::lock_guard<std::mutex> guard(callbacks->mu);
            callbacks->errors.clear();
        }
        queue = nullptr;
        device = nullptr;
        update_work_peaks();
        log("device loss reported");
    }

    void shutdown() {
        // Cancel before explicit shutdown waits and destruction; those are not
        // measured allocation events. Never strand the layer's active token.
        if (memory_window_token) close_memory_window(true);
        for (auto& [id, canvas] : canvases)
            cancel_canvas_frames(canvas, "cancelled", "runtime shutdown before complete paint retirement");
        if (queue && instance) wait_queue();
        // Explicit shutdown may wait; normal submission never takes this
        // validation barrier. Process every submitted owner before releasing
        // diagnostic capacity or dropping its generation's native handles.
        for (const auto& ticket : tickets) if (ticket->encoding_validation &&
                !ticket->encoding_validation->done.load()) {
            ++probe.completion_waits;
            wait_result(ticket->encoding_validation_future, ticket->encoding_validation);
        }
        poll();
        if (!tickets.empty())
            throw std::runtime_error("runtime shutdown: submitted endpoint owners have not retired");
        for (const auto& capture : line_captures) {
            // Includes retired/uncollected captures from already-destroyed
            // canvases, which cancel_canvas_frames cannot visit.
            capture->destroy_readbacks();
            fail_line_capture(capture, "cancelled", "runtime shutdown before endpoint collection", true);

        }
        if (instance) instance.ProcessEvents();
        release_surfaces();
        for (const auto& [id, canvas] : canvases) {
            terminal_canvases.push_back(id);
            if (terminal_canvases.size() > 128) terminal_canvases.pop_front();
        }
        // Keep native owners alive until the device has destroyed its WSI.
        for (const auto& frame : query_frames) frame->fail(vispy::timing::Status::Cancelled, "runtime shutdown");
        query_frames.clear();
        frame_works.clear();
        query_segments.clear();
        objects.clear();
        shader_artifacts.clear();
        tickets.clear();
        line_pool.reset();
        line_canary = nullptr;
        for (auto& texture : dummy_textures) texture.reset();
        present_pipeline = nullptr;
        present_layout = nullptr;
        present_sampler = nullptr;
        queue = nullptr;
        depth_upload_pipeline = nullptr;
        depth_upload_layout = nullptr;
        for (auto& pipeline : sample_zero_capture_pipelines) pipeline = nullptr;
        for (auto& layout : sample_zero_capture_layouts) layout = nullptr;
        depth_capture_pipeline = nullptr;
        depth_capture_layout = nullptr;
        if (device) device.Destroy();
        device = nullptr;
        canvases.clear();
        adapter = nullptr;
        instance = nullptr;
        delete native;
        native = nullptr;
        device_ready = false;
        update_work_peaks();
    }

    void load_layer() {
        if (layer || vispy::platform::default_backend() != wgpu::BackendType::Vulkan) return;
        const auto directory = vispy::platform::module_directory(reinterpret_cast<const void*>(&ensure_device));
        auto candidate = vispy::platform::NativeLibrary(directory / vispy::platform::submit_layer_library_name());
        auto submit_count = reinterpret_cast<uint64_t (*)()>(candidate.symbol("vispy_layer_vk_submit_count"));
        auto enable_lines = reinterpret_cast<void (*)(uint32_t)>(candidate.symbol("vispy_layer_vk_enable_bresenham"));
        auto line_devices = reinterpret_cast<uint64_t (*)()>(candidate.symbol("vispy_layer_vk_bresenham_device_creations"));
        auto line_pipelines = reinterpret_cast<uint64_t (*)()>(candidate.symbol("vispy_layer_vk_bresenham_pipeline_count"));
        auto enable_last = reinterpret_cast<void (*)(uint32_t)>(candidate.symbol("vispy_layer_vk_enable_last_vertex"));
        auto last_devices = reinterpret_cast<uint64_t (*)()>(candidate.symbol("vispy_layer_vk_last_vertex_device_creations"));
        auto last_pipelines = reinterpret_cast<uint64_t (*)()>(candidate.symbol("vispy_layer_vk_last_vertex_pipeline_count"));
        auto memory_snapshot = reinterpret_cast<VulkanMemorySnapshotFn>(candidate.symbol("vispy_layer_vk_memory_snapshot"));
        const auto memory_window_functions = optional_vulkan_memory_window_functions(candidate);
        if (!submit_count || !enable_lines || !line_devices || !line_pipelines ||
            !enable_last || !last_devices || !last_pipelines || !memory_snapshot)
            throw std::runtime_error("Vulkan raster compatibility or memory telemetry entry points are unavailable");
        enable_lines(1);
        enable_last(1);
        vispy::platform::enable_submit_layer_environment(directory);
        layer = std::move(candidate);
        layer_count = submit_count;
        layer_bresenham_devices = line_devices;
        layer_bresenham_pipelines = line_pipelines;
        layer_last_vertex_devices = last_devices;
        layer_last_vertex_pipelines = last_pipelines;
        layer_memory_snapshot = memory_snapshot;
        // Optional, additive ABI. An older layer remains usable but cannot
        // claim event-level measured-window allocation telemetry.
        layer_memory_window_begin = memory_window_functions.begin;
        layer_memory_window_end = memory_window_functions.end;
    }

    void release_surfaces() {
        for (auto& entry : canvases) {
            auto& canvas = entry.second;
            if (canvas.surface) {
                canvas.surface.Unconfigure();
                canvas.surface = nullptr;
            }
            canvas.surface_configured = false;
            canvas.swapchain_current = false;
        }
    }

    void check_surface_retirement_device() {
        if (!device || !queue || device_lost || callbacks->lost.load() ||
            dawn::native::IsDeviceLost(device.Get()))
            throw std::runtime_error("native surface retirement: device is lost or unavailable");
        std::lock_guard<std::mutex> guard(callbacks->mu);
        if (!callbacks->errors.empty())
            throw std::runtime_error("native surface retirement: " + callbacks->errors.front());
    }

    void retire_surface(Canvas& canvas) {
        const bool drain_native_owner = canvas.surface_owner &&
            vispy::platform::native_surface_requires_retirement_drain(canvas.surface_owner->descriptor().kind);
        if (drain_native_owner) {
            // Ticket and callback captures pair every retained Surface with its
            // native owner. Retire them before dropping the final Surface; the
            // unique-owner precondition below also catches a hidden capture.
            if (!tickets.empty() && queue) wait_queue();
            if (!tickets.empty())
                throw std::runtime_error("native surface retirement: submitted owners have not retired");
            if (!device) {
                // All paths dropping the old Device explicitly Destroy it
                // first, while Canvas owners remain alive.
                if (canvas.surface || canvas.surface_owner.use_count() != 1)
                    throw std::runtime_error("native surface retirement: surface survives its device");
                canvas.surface_owner.reset();
            } else {
                const uint64_t deadline = monotonic_ns() + 30'000'000'000ull;
                ++probe.completion_waits;
                vispy::platform::retire_owned_surface(canvas.surface_owner,
                    [&] {
                        if (canvas.surface) canvas.surface.Unconfigure();
                        canvas.surface = nullptr;
                    },
                    [&] {
                        // Empty Submit still acquires a Normal recording
                        // context and submits serial N+1 in pinned Dawn.
                        queue.Submit(0, nullptr);
                        ++probe.dawn_queue_submits;
                    },
                    [&] { return dawn::native::DeviceTick(device.Get()); },
                    [&] { check_surface_retirement_device(); },
                    [&] {
                        if (monotonic_ns() >= deadline)
                            throw std::runtime_error("native surface retirement: deletion drain timed out");
                        std::this_thread::sleep_for(std::chrono::milliseconds(1));
                    });
            }
            canvas.surface_configured = false;
            canvas.swapchain_current = false;
            ++canvas.surface_generation;
            return;
        }
        for (auto& ticket : tickets) {
            if (ticket->canvas_id != canvas.id) continue;
            if (canvas.surface_owner) ticket->surface_owners.push_back(canvas.surface_owner);
            if (canvas.surface) ticket->surfaces.push_back(canvas.surface);
        }
        if (canvas.surface) canvas.surface.Unconfigure();
        canvas.surface = nullptr;
        canvas.surface_owner.reset();
        canvas.surface_configured = false;
        canvas.swapchain_current = false;
        ++canvas.surface_generation;
    }

    void ensure_native_surface(Canvas& canvas) {
        if (!canvas.surface_owner || !instance || canvas.surface) return;
        if (!canvas.surface_owner->is_alive()) {
            retire_surface(canvas);
            canvas.surface_configured = false;
            log("expired native canvas window " + std::to_string(canvas.id));
            return;
        }
        canvas.surface_owner->update(canvas.width, canvas.height, canvas.surface_scale);
        canvas.surface = canvas.surface_owner->create_surface(instance);
        wgpu::SurfaceCapabilities capabilities;
        if (canvas.surface.GetCapabilities(adapter, &capabilities) != wgpu::Status::Success) {
            canvas.surface = nullptr;
            throw std::runtime_error("native surface creation failed for selected backend");
        }
        canvas.surface_configured = false;
        canvas.swapchain_current = false;
        ++canvas.surface_generation;
        log("native surface generation=" + std::to_string(canvas.surface_generation));
    }

    bool init_device() {
        if (instance) instance.ProcessEvents();
        if (callbacks->lost.exchange(false)) invalidate_device();
        if (device_ready && !device_lost) return info.ok;
        load_layer();
        const auto search_storage = vispy::platform::default_runtime_search_paths();
        std::vector<std::string_view> search_paths;
        for (const auto& path : search_storage) search_paths.push_back(path);
        dawn::native::DawnInstanceDescriptor native_desc;
        native_desc.additionalRuntimeSearchPaths = std::span<std::string_view>(search_paths);
        wgpu::InstanceFeatureName features[] = {wgpu::InstanceFeatureName::ShaderSourceSPIRV,
                                               wgpu::InstanceFeatureName::TimedWaitAny};
        wgpu::InstanceDescriptor desc;
        desc.nextInChain = &native_desc;
        desc.requiredFeatureCount = 2;
        desc.requiredFeatures = features;
        release_surfaces();
        // Retained Canvas owners outlive all old-generation WSI destruction.
        if (device) device.Destroy();
        queue = nullptr;
        device = nullptr;
        adapter = nullptr;
        instance = nullptr;
        delete native;
        native = new dawn::native::Instance(&desc);
        instance = wgpu::Instance(native->Get());
        wgpu::RequestAdapterOptions options;
        options.powerPreference = wgpu::PowerPreference::HighPerformance;
        auto adapters = native->EnumerateAdapters(&options);
        if (adapters.empty()) {
            info.ok = false;
            info.error = std::string("No adapter for backend ") + vispy::platform::default_backend_name();
            last_error = info.error;
            return false;
        }
        dawn::native::Adapter chosen;
        bool found = false;
        for (auto& candidate : adapters) {
            wgpu::Adapter probe_adapter(candidate.Get());
            wgpu::AdapterInfo adapter_info;
            probe_adapter.GetInfo(&adapter_info);
            if (adapter_info.backendType == vispy::platform::default_backend() &&
                adapter_info.adapterType != wgpu::AdapterType::CPU) {
                chosen = candidate;
                found = true;
                break;
            }
        }
        if (!found) {
            for (auto& candidate : adapters) {
                wgpu::Adapter probe_adapter(candidate.Get());
                wgpu::AdapterInfo adapter_info;
                probe_adapter.GetInfo(&adapter_info);
                if (adapter_info.backendType == vispy::platform::default_backend()) {
                    chosen = candidate;
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            info.ok = false;
            info.error = std::string("No adapter for backend ") + vispy::platform::default_backend_name();
            last_error = info.error;
            return false;
        }
        adapter = wgpu::Adapter(chosen.Get());
        wgpu::AdapterInfo adapter_info;
        adapter.GetInfo(&adapter_info);
        info.backend = vispy::platform::default_backend_name();
        info.vendor = view_to_string(adapter_info.vendor);
        info.device = view_to_string(adapter_info.device);
        info.driver = view_to_string(adapter_info.description);
        info.vendor_id = adapter_info.vendorID;
        info.device_id = adapter_info.deviceID;
        info.software = adapter_info.adapterType == wgpu::AdapterType::CPU;
        if (adapter_info.adapterType == wgpu::AdapterType::DiscreteGPU) info.adapter_type = "discrete";
        else if (adapter_info.adapterType == wgpu::AdapterType::IntegratedGPU) info.adapter_type = "integrated";
        else if (adapter_info.adapterType == wgpu::AdapterType::CPU) info.adapter_type = "cpu";
        else info.adapter_type = "unknown";
        wgpu::Limits limits;
        adapter.GetLimits(&limits);
        wgpu::DeviceDescriptor device_desc;
        // Preserve OpenGL's24-bit normalized depth when Vulkan provides D24S8.
        // Dawn otherwise prefers D32FloatS8 for its abstract Depth24Plus format.
        const char* disabled_toggles[] = {"vulkan_use_d32s8"};
        const char* diagnostic_toggles[] = {"dump_shaders"};
        std::shared_ptr<BackendShaderLog> backend_log;
        if (const char* path = std::getenv("VISPY_DAWN_BACKEND_SHADER_DUMP"); path && *path) {
            backend_log = std::make_shared<BackendShaderLog>(std::filesystem::u8path(path));
            backend_shader_logs.push_back(backend_log);
        }
        current_backend_shader_log = backend_log;
        wgpu::DawnTogglesDescriptor depth_policy;
        if (vispy::platform::default_backend() == wgpu::BackendType::Vulkan) {
            depth_policy.disabledToggleCount = 1;
            depth_policy.disabledToggles = disabled_toggles;
        }
        if (backend_log) {
            depth_policy.enabledToggleCount = 1;
            depth_policy.enabledToggles = diagnostic_toggles;
        }
        if (depth_policy.disabledToggleCount || depth_policy.enabledToggleCount)
            device_desc.nextInChain = &depth_policy;
        device_desc.requiredLimits = &limits;
        std::vector<wgpu::FeatureName> device_features;
        for (auto feature : {wgpu::FeatureName::Float32Filterable,
                             wgpu::FeatureName::Unorm16TextureFormats, wgpu::FeatureName::TimestampQuery}) {
            if (adapter.HasFeature(feature)) device_features.push_back(feature);
        }
        device_desc.requiredFeatureCount = device_features.size();
        device_desc.requiredFeatures = device_features.data();
        device_desc.SetUncapturedErrorCallback(
            [](const wgpu::Device&, wgpu::ErrorType type, wgpu::StringView message, DeviceCallbacks* state) {
                std::lock_guard<std::mutex> guard(state->mu);
                if (state->errors.size() < 32)
                    state->errors.push_back(std::string(error_type_name(type)) + ": " + view_to_string(message));
            }, callbacks.get());
        device_desc.SetDeviceLostCallback(wgpu::CallbackMode::AllowProcessEvents,
            [state = callbacks](const wgpu::Device&, wgpu::DeviceLostReason reason, wgpu::StringView message) {
                if (reason == wgpu::DeviceLostReason::Destroyed ||
                    reason == wgpu::DeviceLostReason::CallbackCancelled) return;
                std::lock_guard<std::mutex> guard(state->mu);
                state->loss_message = view_to_string(message);
                state->lost.store(true);
            });
        const uint64_t previous_line_devices = layer_bresenham_devices ? layer_bresenham_devices() : 0;
        const uint64_t previous_last_devices = layer_last_vertex_devices ? layer_last_vertex_devices() : 0;
        device = wgpu::Device::Acquire(chosen.CreateDevice(&device_desc));
        if (device && backend_log)
            device.SetLoggingCallback(
                [](wgpu::LoggingType type, wgpu::StringView message, BackendShaderLog* state) noexcept {
                    state->write(type, message);
                }, backend_log.get());
        if (!device || device.GetLimits(&limits) != wgpu::Status::Success) {
            info.ok = false;
            info.error = "Dawn device creation failed";
            last_error = info.error;
            return false;
        }
        info.max_texture_1d = limits.maxTextureDimension1D;
        info.max_texture_2d = limits.maxTextureDimension2D;
        info.max_texture_3d = limits.maxTextureDimension3D;
        info.max_vertex_attributes = limits.maxVertexAttributes;
        info.max_vertex_buffers = limits.maxVertexBuffers;
        info.max_vertex_buffer_stride = limits.maxVertexBufferArrayStride;
        info.max_storage_buffers = limits.maxStorageBuffersPerShaderStage;
        info.max_uniform_buffers = limits.maxUniformBuffersPerShaderStage;
        info.max_inter_stage_shader_variables = limits.maxInterStageShaderVariables;
        info.max_storage_buffer_size = limits.maxStorageBufferBindingSize;
        info.max_bindings_per_bind_group = limits.maxBindingsPerBindGroup;
        info.max_compute_invocations_per_workgroup = limits.maxComputeInvocationsPerWorkgroup;
        info.max_compute_workgroup_size_x = limits.maxComputeWorkgroupSizeX;
        info.max_compute_workgroups_per_dimension = limits.maxComputeWorkgroupsPerDimension;
        info.max_point_vertex_attributes = info.max_vertex_attributes;
        info.core_features_and_limits = device.HasFeature(wgpu::FeatureName::CoreFeaturesAndLimits);
        info.max_samplers = limits.maxSamplersPerShaderStage;
        info.max_sampled_textures = limits.maxSampledTexturesPerShaderStage;
        info.max_buffer_size = limits.maxBufferSize;
        info.max_uniform_buffer_size = limits.maxUniformBufferBindingSize;
        info.float32_filterable = device.HasFeature(wgpu::FeatureName::Float32Filterable);
        info.unorm16_texture_formats = device.HasFeature(wgpu::FeatureName::Unorm16TextureFormats);
        info.timestamp_query = device.HasFeature(wgpu::FeatureName::TimestampQuery);
        const auto query_toggles = dawn::native::GetTogglesUsed(device.Get());
        info.timestamp_quantization_ns = std::any_of(query_toggles.begin(), query_toggles.end(),
            [](const char* toggle) { return std::string_view(toggle) == "timestamp_quantization"; }) ? 65536 : 0;
        info.bresenham_lines = layer_bresenham_devices && layer_bresenham_devices() > previous_line_devices;
        info.last_vertex_provoking = layer_last_vertex_devices && layer_last_vertex_devices() > previous_last_devices;
        info.depth_stencil_storage = "implementation_defined";
        if (vispy::platform::default_backend() == wgpu::BackendType::Vulkan) {
            const auto toggles = dawn::native::GetTogglesUsed(device.Get());
            const bool float_storage = std::any_of(toggles.begin(), toggles.end(), [](const char* toggle) {
                return std::strcmp(toggle, "vulkan_use_d32s8") == 0;
            });
            info.depth_stencil_storage = float_storage ? "depth32_float_stencil8" : "depth24_unorm_stencil8";
        }
        ++device_generation;
        probe.device_generation = device_generation;
        queue = device.GetQueue();
        info.ok = true;
        device_ready = true;
        device_lost = false;
        info.error.clear();
        callbacks->lost.store(false);
        for (auto& entry : canvases) ensure_native_surface(entry.second);
        log("device backend=" + info.backend + " adapter=" + info.adapter_type + " name=" + info.device);
        return true;
    }

    Canvas& canvas(int id) {
        auto found = canvases.find(id);
        if (found == canvases.end()) throw std::runtime_error("missing canvas " + std::to_string(id));
        return found->second;
    }

    void capture_target(Canvas& canvas, DrawSnap& snap) {
        ensure_target(canvas);
        snap.state = canvas.state;
        snap.state.sample_count = std::max(1, canvas.samples);
        snap.fbo = canvas.fbo;
        snap.target_view = canvas.color_view;
        snap.depth_view = canvas.depth_view;
        snap.target_texture = canvas.color;
        snap.depth_texture = canvas.depth;
        if (canvas.samples > 1) {
            snap.target_view = canvas.multisampled_view;
            snap.resolve_view = canvas.color_view;
            snap.target_texture = canvas.multisampled_color;
            snap.resolve_texture = canvas.color;
        }
        snap.target_width = canvas.width;
        snap.target_height = canvas.height;
        if (canvas.fbo != 0) {
            auto fb = objects.find(canvas.fbo);
            if (fb == objects.end()) throw std::runtime_error("FRAMEBUFFER missing object");
            auto color = objects.find(fb->second.fb_color);
            if (color == objects.end() || !color->second.texture)
                throw std::runtime_error("FRAMEBUFFER missing color attachment");
            snap.attachment = color->second.texture;
            freeze_texture_allocation(*snap.attachment);
            snap.target_width = snap.attachment->width;
            snap.target_height = snap.attachment->height;
            snap.target_view = nullptr;
            snap.resolve_view = nullptr;
            snap.depth_view = nullptr;
            snap.target_texture = nullptr;
            snap.resolve_texture = nullptr;
            snap.depth_texture = nullptr;
            snap.state.sample_count = 1;
            int depth_id = fb->second.fb_depth ? fb->second.fb_depth : fb->second.fb_stencil;
            if (depth_id) {
                auto found = objects.find(depth_id);
                if (found == objects.end() || !found->second.texture)
                    throw std::runtime_error("FRAMEBUFFER missing depth/stencil allocation");
                snap.depth_attachment = found->second.texture;
                if (snap.depth_attachment->format == "depth_component" && fb->second.fb_stencil)
                    throw std::runtime_error("FRAMEBUFFER separate stencil with depth_component is unsupported");
            }
        }
        std::memcpy(snap.viewport, canvas.viewport, sizeof(snap.viewport));
        std::memcpy(snap.scissor, canvas.scissor, sizeof(snap.scissor));
        snap.scissor_enabled = canvas.scissor_enabled;
    }

    void ensure_target(Canvas& target) {
        if (target.width <= 0 || target.height <= 0) return;
        if (static_cast<uint32_t>(target.width) > info.max_texture_2d ||
            static_cast<uint32_t>(target.height) > info.max_texture_2d)
            throw std::runtime_error("canvas dimensions exceed granted device limit");
        if (target.color && target.built_w == target.width && target.built_h == target.height &&
            target.built_samples == target.samples) {
            return;
        }
        target.present_group = nullptr;
        wgpu::TextureDescriptor td;
        td.size = {static_cast<uint32_t>(target.width), static_cast<uint32_t>(target.height), 1};
        td.format = wgpu::TextureFormat::RGBA8Unorm;
        td.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::CopySrc |
                   wgpu::TextureUsage::TextureBinding;
        target.color = device.CreateTexture(&td);
        ++probe.texture_allocations;
        target.color_view = target.color.CreateView();
        target.multisampled_color = nullptr;
        target.multisampled_view = nullptr;
        if (target.samples > 1) {
            td.sampleCount = target.samples;
            td.usage = wgpu::TextureUsage::RenderAttachment;
            target.multisampled_color = device.CreateTexture(&td);
            ++probe.texture_allocations;
            target.multisampled_view = target.multisampled_color.CreateView();
        }
        td.sampleCount = std::max(1, target.samples);
        td.format = wgpu::TextureFormat::Depth24PlusStencil8;
        td.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::TextureBinding;
        if (td.sampleCount == 1) td.usage |= wgpu::TextureUsage::CopySrc;
        target.depth = device.CreateTexture(&td);
        ++probe.texture_allocations;
        target.depth_view = target.depth.CreateView();
        // The swapchain on this Windows pin is BGRA8. The presented target uses
        // that format so the presentation pass is a real channel conversion.
        td.format = wgpu::TextureFormat::BGRA8Unorm;
        td.sampleCount = 1;
        td.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::CopySrc;
        target.presented = device.CreateTexture(&td);
        ++probe.texture_allocations;
        target.presented_view = target.presented.CreateView();
        target.built_w = target.width;
        target.built_h = target.height;
        target.built_samples = target.samples;
        ++target.surface_generation;
        log("surface generation=" + std::to_string(target.surface_generation) + " " +
            std::to_string(target.width) + "x" + std::to_string(target.height));
    }

    wgpu::ShaderModule make_spirv_module(const std::vector<uint32_t>& words,
                                        SpirvDerivativeMode derivative_mode, const char* label = nullptr) {
        HostTimer timer(probe.shader_module_creation_ns);
        ++probe.shader_module_creations;
        wgpu::DawnShaderModuleSPIRVOptionsDescriptor derivative_options;
        derivative_options.allowNonUniformDerivatives = derivative_mode == SpirvDerivativeMode::AllowNonUniform;
        wgpu::ShaderSourceSPIRV spirv;
        spirv.nextInChain = &derivative_options;
        spirv.code = words.data();
        spirv.codeSize = static_cast<uint32_t>(words.size());
        wgpu::ShaderModuleDescriptor descriptor;
        descriptor.nextInChain = &spirv;
        descriptor.label = label;
        // Both chained descriptors and the retained words remain alive through
        // the synchronous call. Every SPIR-V caller supplies a captured policy.
        return device.CreateShaderModule(&descriptor);
    }

    std::shared_ptr<Artifact> make_artifact(const std::string& vert, const std::string& frag,
                                          std::string& error, bool base_level = false, bool has_depth = true,
                                          bool point_sprites = false,
                                          VertexIdentityPolicy vertex_identity = VertexIdentityPolicy::Native,
                                          SpirvDerivativeMode derivative_mode = SpirvDerivativeMode::Strict,
                                          bool require_ordinary_graphics = true) {
        NormalizeOptions options;
        options.base_level_sampling = base_level;
        options.point_sprites = point_sprites;
        options.vertex_identity = vertex_identity;
        bool portable_hit = false;
        uint64_t lookup_ns = 0;
        auto portable = shader_artifacts.get_or_build(vert, frag, options, kPins, &portable_hit, &lookup_ns,
            derivative_mode);
        probe.shader_cache_lookup_ns += lookup_ns;
        if (portable_hit) ++probe.portable_shader_hits;
        else {
            ++probe.portable_shader_misses;
            const auto& timings = portable->timings;
            probe.shader_normalize_ns += timings.normalize_ns;
            probe.shader_parse_ns += timings.parse_ns;
            probe.shader_link_ns += timings.link_ns;
            probe.shader_spirv_ns += timings.spirv_ns;
            probe.shader_reflect_ns += timings.reflect_ns;
            probe.shader_cpu_build_ns += timings.total_ns;
            probe.shader_normalizations += timings.normalizations;
            probe.shader_parse_calls += timings.parse_calls;
            probe.shader_link_calls += timings.link_calls;
            probe.shader_spirv_stages += timings.spirv_stages;
        }
        update_work_peaks();
        probe.artifact_cache_entries = shader_artifacts.portable_size();
        probe.portable_shader_bytes = shader_artifacts.portable_storage_bytes();
        return materialize_artifact(std::move(portable), has_depth, error, {}, {}, require_ordinary_graphics);
    }

    std::shared_ptr<Artifact> materialize_artifact(
        std::shared_ptr<const vispy::shader::PortableShaderArtifact> portable,
        bool has_depth, std::string& error,
        std::shared_ptr<const vispy::shader::LineEvaluatorArtifact> evaluator = {},
        std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact> consumer = {},
        bool require_ordinary_graphics = true) {
        error.clear();
        // An evicted program can retain another immutable allocation for the
        // same source. Canonicalize cache ownership before attaching a device
        // record, so an entry never hides two portable allocations.
        std::shared_ptr<Artifact> found;
        {
            HostTimer timer(probe.device_cache_lookup_ns);
            // A saved evaluator owns its exact original allocation. Recovery
            // can keep that pair uncached when another allocation is resident;
            // silently reparenting it would falsify ownership and accounting.
            if (consumer && !evaluator) evaluator = consumer->evaluator;
            if (evaluator && evaluator->original != portable)
                throw std::runtime_error("lines: saved evaluator has a different original artifact");
            if (consumer && (consumer->original != portable || consumer->evaluator != evaluator))
                throw std::runtime_error("lines: saved consumer has a different original/evaluator pair");
            if (!evaluator)
                if (auto resident = shader_artifacts.find_portable(portable->identity)) portable = std::move(resident);
            found = shader_artifacts.find_device(portable->identity, {device_generation, has_depth});
        }
        if (found && found->portable == portable && found->linked_for(device_generation) &&
            (!evaluator || found->evaluator == evaluator)) {
            if (consumer) shader_artifacts.store_consumer(portable, consumer->policy_identity, consumer);
            if (require_ordinary_graphics) prepare_ordinary_artifact(found, error);
            return found;
        }
        auto artifact = std::make_shared<Artifact>();
        artifact->portable = std::move(portable);
        artifact->evaluator = std::move(evaluator);
        if (!artifact->evaluator) {
            auto cached = shader_artifacts.find_auxiliary(artifact->portable->identity);
            if (cached && cached->original == artifact->portable) artifact->evaluator = std::move(cached);
        }
        if (consumer) shader_artifacts.store_consumer(artifact->portable, consumer->policy_identity, consumer);
        artifact->device_generation = device_generation;
        artifact->default_has_depth = has_depth;
        if (!artifact->portable->ok) {
            artifact->error = error = artifact->portable->error;
            if (artifact->portable->mapped_line) {
                error += "\nmapped_line=" + std::to_string(artifact->portable->mapped_line);
                log("shader error mapped_line=" + std::to_string(artifact->portable->mapped_line));
            }
            store_artifact(artifact);
            return artifact;
        }
        // A structural integer sampler is removed by semantic lowering. Its
        // pre-lowering sampler count must not reject an otherwise legal
        // texture-only binding layout; the specialized record is checked here
        // before any native preparation. Unaffected programs keep LINK checks.
        const bool requires_draw_policy = !artifact->portable->integer_sample_uses.empty() &&
                                          artifact->portable->integer_sampling_identity.empty();
        if (!requires_draw_policy) {
            if (auto limits = vispy::shader::resource_limit_error(artifact->portable->samplers,
                    info.max_samplers, info.max_sampled_textures); !limits.empty()) {
                artifact->error = error = "Shader active resource layout: " + limits;
                store_artifact(artifact);
                return artifact;
            }
        }
        if (const char* directory = std::getenv("VISPY_DAWN_SHADER_DUMP")) {
            const auto root = std::filesystem::u8path(directory);
            std::filesystem::create_directories(root);
            auto write = [&](const char* suffix, const void* data, size_t size) {
                std::ofstream stream(root / (artifact->portable->cache_key + suffix), std::ios::binary);
                stream.write(static_cast<const char*>(data), static_cast<std::streamsize>(size));
                if (!stream) throw std::runtime_error("shader diagnostic dump failed");
            };
            write(".source.vert", artifact->portable->source_vertex.data(), artifact->portable->source_vertex.size());
            write(".source.frag", artifact->portable->source_fragment.data(), artifact->portable->source_fragment.size());
            write(".normalized.vert", artifact->portable->vertex.data(), artifact->portable->vertex.size());
            write(".normalized.frag", artifact->portable->fragment.data(), artifact->portable->fragment.size());
            write(".vert.spv", artifact->portable->spv_vert.data(), artifact->portable->spv_vert.size() * sizeof(uint32_t));
            write(".frag.spv", artifact->portable->spv_frag.data(), artifact->portable->spv_frag.size() * sizeof(uint32_t));
        }
        artifact->linked = true;
        store_artifact(artifact);
        if (require_ordinary_graphics) prepare_ordinary_artifact(artifact, error);
        return artifact;
    }

    static void require_integer_sampling_route(const vispy::shader::PortableShaderArtifact& portable,
                                              uint32_t stage_mask, const char* route) {
        const auto error = vispy::shader::integer_sampling_generated_stage_error(portable, stage_mask, route);
        if (!error.empty()) throw std::runtime_error(error);
    }

    void capture_integer_sampling(DrawSnap& snap) {
        const auto& portable = *snap.artifact->portable;
        std::vector<vispy::shader::IntegerSamplePolicy> captured;
        captured.reserve(portable.integer_sample_uses.size());
        for (const auto& use : portable.integer_sample_uses) {
            if (!use.stage_mask || (use.stage_mask & ~3u))
                throw std::runtime_error("integer normalized sampling: invalid ordinary-stage metadata");
            const auto found = std::find_if(portable.samplers.begin(), portable.samplers.end(), [&](const auto& sampler) {
                return sampler.texture_binding == use.texture_binding && sampler.sampler_binding == use.sampler_binding &&
                       sampler.sample_scalar == use.scalar;
            });
            if (found == portable.samplers.end())
                throw std::runtime_error("integer normalized sampling: semantic resource has no matching reflected sampler");
            const auto position = static_cast<size_t>(found - portable.samplers.begin());
            if (position >= snap.textures.size() || !snap.textures[position])
                throw std::runtime_error("integer normalized sampling: semantic resource has no retained texture revision");
            const auto& revision = *snap.textures[position];
            // upload_texture explicitly allocates one mip level. Filters and
            // S/T wrap come from this exact retained revision, not the Program.
            const auto policy = snapshot_integer_sample_policy(*found, revision,
                revision.allocation_descriptor.get(), true);
            const auto previous = std::find_if(captured.begin(), captured.end(), [&](const auto& item) {
                return item.texture_binding == policy.texture_binding;
            });
            if (previous != captured.end()) {
                if (previous->sampler_binding != policy.sampler_binding || previous->scalar != policy.scalar ||
                    previous->s != policy.s || previous->t != policy.t || previous->nearest != policy.nearest ||
                    previous->base_level_only != policy.base_level_only)
                    throw std::runtime_error("integer normalized sampling: conflicting retained resource policies");
                continue;
            }
            captured.push_back(policy);
        }
        snap.integer_sampling_policies = std::move(captured);
    }

    void prepare_draw_sampling(DrawSnap& snap, bool ordinary_graphics = true) {
        if (snap.line_work && snap.line_work->consumer) return;
        if (!snap.integer_sampling_policies.empty() && snap.artifact->portable->integer_sampling_identity.empty()) {
            const auto original = snap.artifact;
            bool hit = false;
            uint64_t lookup_ns = 0;
            auto portable = shader_artifacts.specialize_integer_sampling(original->portable,
                snap.integer_sampling_policies, &hit, &lookup_ns);
            probe.shader_cache_lookup_ns += lookup_ns;
            if (!portable || !portable->ok)
                throw std::runtime_error("integer normalized sampling: " +
                    (portable ? portable->error : std::string("specialization produced no portable artifact")));
            if (portable != original->portable) {
                if (hit) ++probe.portable_shader_hits;
                else {
                    ++probe.portable_shader_misses;
                    // A policy miss transforms retained SPIR-V. It is not a
                    // GLSL normalization, parse, link or emission operation.
                    probe.shader_cpu_build_ns += portable->timings.total_ns;
                    probe.shader_reflect_ns += portable->timings.reflect_ns;
                }
                std::string error;
                auto specialized = materialize_artifact(std::move(portable), original->default_has_depth,
                    error, {}, {}, false);
                if (!error.empty()) throw std::runtime_error("integer normalized sampling: " + error);
                // The compiler preserves the user sampler order and binding
                // numbers while updating per-stage liveness after lowering.
                const auto& before = original->portable->samplers;
                const auto& after = specialized->portable->samplers;
                if (before.size() != after.size())
                    throw std::runtime_error("integer normalized sampling: specialization changed retained sampler ordering");
                for (size_t n = 0; n < before.size(); ++n)
                    if (before[n].name != after[n].name || before[n].dim != after[n].dim ||
                        before[n].sample_scalar != after[n].sample_scalar ||
                        before[n].texture_binding != after[n].texture_binding ||
                        before[n].sampler_binding != after[n].sampler_binding)
                        throw std::runtime_error("integer normalized sampling: specialization changed the captured user sampler interface");
                snap.artifact = std::move(specialized);
            }
            probe.artifact_cache_entries = shader_artifacts.portable_size();
            probe.portable_shader_bytes = shader_artifacts.portable_storage_bytes();
            update_work_peaks();
        }
        if (!ordinary_graphics) return;
        std::string error;
        prepare_ordinary_artifact(snap.artifact, error);
        if (!error.empty()) throw std::runtime_error("DRAW ordinary graphics: " + error);
    }

    void prepare_ordinary_artifact(const std::shared_ptr<Artifact>& artifact, std::string& error) {
        error.clear();
        if (!artifact || !artifact->linked_for(device_generation)) {
            error = artifact && !artifact->error.empty() ? artifact->error :
                "ordinary graphics preparation requires a current linked artifact";
            return;
        }
        if (!artifact->portable->integer_sample_uses.empty() && artifact->portable->integer_sampling_identity.empty()) {
            error = "integer normalized sampling requires the actual retained DRAW sampler policy before native preparation";
            return;
        }
        if (artifact->valid_for(device_generation)) {
            probe.pipeline_hits++;
            log("pipeline cache hit " + artifact->portable->cache_key + " spirv_derivatives=" +
                vispy::shader::spirv_derivative_mode_name(artifact->portable->derivative_mode));
            return;
        }
        if (artifact->ordinary_attempted) {
            error = artifact->error.empty() ? "ordinary graphics preparation did not complete" : artifact->error;
            return;
        }
        artifact->ordinary_attempted = true;
        vispy::inputs::Layout canonical_inputs;
        try {
            if (artifact->portable->point_sprites && !info.core_features_and_limits)
                throw std::runtime_error("DRAW points: preserving the public input budget requires granted CoreFeaturesAndLimits");
            if (artifact->portable->vertex_identity_binding && !info.core_features_and_limits)
                throw std::runtime_error("DRAW inputs: original identity storage requires granted CoreFeaturesAndLimits to preserve the public input budget");
            std::vector<uint32_t> widths;
            for (const auto& attr : artifact->portable->attributes)
                widths.push_back(attribute_components(attr.type) * 4);
            if (artifact->portable->point_sprites) {
                canonical_inputs = vispy::points::partitioned_layout(widths, info.max_vertex_attributes,
                    info.max_vertex_buffers, info.max_vertex_buffer_stride);
            } else {
                canonical_inputs = vispy::inputs::partition_layout(widths, {}, info.max_vertex_attributes,
                    info.max_vertex_buffers, info.max_vertex_buffer_stride);
            }
            if (artifact->portable->point_identity_binding &&
                (!info.max_storage_buffers || info.max_storage_buffer_size < 8 || info.max_buffer_size < 8))
                throw std::runtime_error("DRAW points: exact identities require granted vertex storage capacity of at least 8 bytes");
            if (artifact->portable->vertex_identity_binding &&
                (!info.max_storage_buffers || info.max_storage_buffer_size < 4 || info.max_buffer_size < 4))
                throw std::runtime_error("DRAW inputs: exact vertex identities require granted vertex storage capacity of at least 4 bytes");
        } catch (const std::exception& exception) {
            artifact->error = error = "Shader active input layout: " + std::string(exception.what());
            refresh_artifact(*artifact);
            return;
        }
        if (artifact->portable->batch_instance_binding) {
            const auto& portable = *artifact->portable;
            const uint32_t vertex_uniforms = 1 + uint32_t(!portable.uniforms.empty() && (portable.uniform_stage_mask & 1));
            if (portable.batch_instance_stage_mask != 1 ||
                portable.batch_instance_binding >= info.max_bindings_per_bind_group ||
                vertex_uniforms > info.max_uniform_buffers ||
                std::min(info.max_uniform_buffer_size, info.max_buffer_size) < kBatchInstanceUniformBytes) {
                artifact->error = error = "DRAW batches: granted uniform/binding capacity cannot represent original instance IDs";
                refresh_artifact(*artifact);
                return;
            }
        }
        const auto creation_generation = device_generation;
        PipelineCreationScopes creation(instance, device, "ordinary graphics " + artifact->portable->cache_key,
            current_backend_shader_log, creation_generation);
        creation.begin();
        artifact->vert_module = make_spirv_module(artifact->portable->spv_vert,
            artifact->portable->derivative_mode, "ordinary vertex/main");
        artifact->frag_module = make_spirv_module(artifact->portable->spv_frag,
            artifact->portable->derivative_mode, "ordinary fragment/main");
        std::vector<wgpu::BindGroupLayoutEntry> entries;
        if (!artifact->portable->uniforms.empty() && artifact->portable->uniform_stage_mask) {
            wgpu::BindGroupLayoutEntry entry;
            entry.binding = 0;
            entry.visibility = resource_stages(artifact->portable->uniform_stage_mask);
            entry.buffer.type = wgpu::BufferBindingType::Uniform;
            entries.push_back(entry);
        }
        if (artifact->portable->point_identity_binding) {
            wgpu::BindGroupLayoutEntry entry;
            entry.binding = artifact->portable->point_identity_binding;
            entry.visibility = wgpu::ShaderStage::Vertex;
            entry.buffer.type = wgpu::BufferBindingType::ReadOnlyStorage;
            entry.buffer.minBindingSize = 8;
            entries.push_back(entry);
        }
        if (artifact->portable->vertex_identity_binding) {
            wgpu::BindGroupLayoutEntry entry;
            entry.binding = artifact->portable->vertex_identity_binding;
            entry.visibility = wgpu::ShaderStage::Vertex;
            entry.buffer.type = wgpu::BufferBindingType::ReadOnlyStorage;
            entry.buffer.minBindingSize = 4;
            entries.push_back(entry);
        }
        if (artifact->portable->batch_instance_binding) {
            wgpu::BindGroupLayoutEntry entry;
            entry.binding = artifact->portable->batch_instance_binding;
            entry.visibility = resource_stages(artifact->portable->batch_instance_stage_mask);
            entry.buffer.type = wgpu::BufferBindingType::Uniform;
            entry.buffer.minBindingSize = kBatchInstanceUniformBytes;
            entries.push_back(entry);
        }
        for (const auto& sampler : artifact->portable->samplers) {
            wgpu::BindGroupLayoutEntry tex;
            tex.binding = sampler.texture_binding;
            tex.visibility = resource_stages(sampler.texture_stage_mask);
            tex.texture.sampleType = declared_sample_type(sampler);
            tex.texture.viewDimension = sampler.dim == "1d" ? wgpu::TextureViewDimension::e1D :
                sampler.dim == "3d" ? wgpu::TextureViewDimension::e3D
                                                             : wgpu::TextureViewDimension::e2D;
            if (sampler.texture_stage_mask) entries.push_back(tex);
            wgpu::BindGroupLayoutEntry samp;
            samp.binding = sampler.sampler_binding;
            samp.visibility = resource_stages(sampler.sampler_stage_mask);
            samp.sampler.type = declared_sampler_type(sampler);
            if (sampler.sampler_stage_mask) entries.push_back(samp);
        }
        wgpu::BindGroupLayoutDescriptor bgl;
        bgl.entryCount = entries.size();
        bgl.entries = entries.data();
        artifact->bind_layout = device.CreateBindGroupLayout(&bgl);
        wgpu::PipelineLayoutDescriptor pld;
        pld.bindGroupLayoutCount = 1;
        pld.bindGroupLayouts = &artifact->bind_layout;
        auto layout = device.CreatePipelineLayout(&pld);
        std::vector<wgpu::VertexBufferLayout> vbls(canonical_inputs.streams.size());
        std::vector<std::vector<wgpu::VertexAttribute>> attrs(vbls.size());
        for (size_t n = 0; n < artifact->portable->attributes.size(); ++n) {
            const auto& attr = artifact->portable->attributes[n];
            wgpu::VertexAttribute va;
            va.shaderLocation = attr.location;
            va.offset = canonical_inputs.offsets[n];
            va.format = attribute_format(attr.type);
            attrs.at(canonical_inputs.slots[n]).push_back(va);
        }
        for (size_t n = 0; n < vbls.size(); ++n) {
            auto& layout_item = vbls[n];
            layout_item.arrayStride = canonical_inputs.streams[n].stride;
            layout_item.stepMode = canonical_inputs.streams[n].instance ? wgpu::VertexStepMode::Instance : wgpu::VertexStepMode::Vertex;
            layout_item.attributeCount = attrs[n].size();
            layout_item.attributes = attrs[n].data();
        }
        wgpu::VertexState vs;
        vs.module = artifact->vert_module;
        vs.entryPoint = "main";
        vs.bufferCount = vbls.size();
        vs.buffers = vbls.data();
        wgpu::ColorTargetState color;
        color.format = wgpu::TextureFormat::RGBA8Unorm;
        wgpu::FragmentState fs;
        fs.module = artifact->frag_module;
        fs.entryPoint = "main";
        fs.targetCount = 1;
        fs.targets = &color;
        wgpu::RenderPipelineDescriptor rpd;
        rpd.label = "ordinary graphics";
        rpd.layout = layout;
        rpd.vertex = vs;
        rpd.fragment = &fs;
        rpd.primitive.topology = wgpu::PrimitiveTopology::TriangleList;
        wgpu::DepthStencilState depth;
        depth.format = wgpu::TextureFormat::Depth24PlusStencil8;
        depth.depthCompare = wgpu::CompareFunction::Always;
        depth.depthWriteEnabled = wgpu::OptionalBool::False;
        if (artifact->default_has_depth) rpd.depthStencil = &depth;
        std::string validation;
        {
            HostTimer timer(probe.pipeline_creation_ns);
            ++probe.render_pipeline_creations;
            artifact->pipeline = device.CreateRenderPipeline(&rpd);
            validation = finish_pipeline_creation(creation, creation_generation);
        }
        artifact->pipeline_ok = artifact->pipeline.Get() != nullptr && validation.empty();
        if (!artifact->pipeline_ok) {
            error = "RenderPipeline creation failed: " + validation;
            artifact->error = error;
        } else {
            artifact->error.clear();
            probe.pipeline_misses++;
            log("pipeline created " + artifact->portable->cache_key + " spirv_derivatives=" +
                vispy::shader::spirv_derivative_mode_name(artifact->portable->derivative_mode));
        }
        refresh_artifact(*artifact);
    }

    vispy::shader::LineEvaluatorLimits endpoint_limits() const {
        return {info.max_storage_buffer_size, input_buffer_limit(), info.max_storage_buffers,
                info.max_bindings_per_bind_group, info.max_compute_workgroup_size_x,
                info.max_compute_invocations_per_workgroup, info.max_compute_workgroups_per_dimension};
    }

    vispy::shader::LineConsumerLimits consumer_limits() const {
        vispy::shader::LineConsumerLimits limits;
        limits.max_storage_binding_bytes = info.max_storage_buffer_size;
        limits.max_buffer_bytes = input_buffer_limit();
        limits.max_uniform_binding_bytes = info.max_uniform_buffer_size;
        limits.max_storage_buffers_per_stage = info.max_storage_buffers;
        limits.max_bindings_per_group = info.max_bindings_per_bind_group;
        limits.max_inter_stage_shader_variables = info.max_inter_stage_shader_variables;
        return limits;
    }

    std::shared_ptr<const vispy::shader::LineEvaluatorArtifact> prepare_line_evaluator(
        const std::shared_ptr<Artifact>& original) {
        if (!original || !original->portable || !original->portable->ok)
            throw std::runtime_error("lines: endpoint evaluator requires a validated captured original shader");
        if (original->portable->integer_sampling_identity.empty())
            require_integer_sampling_route(*original->portable, 1, "generated line endpoint compute");
        auto evaluator = original->evaluator;
        if (!evaluator) {
            auto cached = shader_artifacts.find_auxiliary(original->portable->identity);
            if (cached && cached->original == original->portable) evaluator = std::move(cached);
        }
        if (evaluator) ++probe.line_evaluator_hits;
        else {
            ++probe.line_evaluator_misses;
            evaluator = vispy::shader::build_line_evaluator(original->portable, endpoint_limits());
            const auto& timings = evaluator->timings;
            probe.shader_normalize_ns += timings.normalize_ns;
            probe.shader_parse_ns += timings.parse_ns;
            probe.shader_link_ns += timings.link_ns;
            probe.shader_spirv_ns += timings.spirv_ns;
            probe.shader_reflect_ns += timings.reflect_ns;
            probe.shader_cpu_build_ns += timings.total_ns;
            probe.shader_normalizations += timings.normalizations;
            probe.shader_parse_calls += timings.parse_calls;
            probe.shader_link_calls += timings.link_calls;
            probe.shader_spirv_stages += timings.spirv_stages;
            if (!evaluator->ok) {
                auto error = evaluator->error;
                if (evaluator->mapped_line) error += "\nmapped_line=" + std::to_string(evaluator->mapped_line);
                throw std::runtime_error(error);
            }
        }
        // Revalidate retained CPU artifacts against the newly granted device,
        // including after loss. Cache identity is independent of device grants.
        if (evaluator->original != original->portable)
            throw std::runtime_error("lines: evaluator has a different captured original artifact");
        const auto limits = endpoint_limits();
        if (limits.max_storage_buffers < 2 || evaluator->output_binding >= limits.max_bindings)
            throw std::runtime_error("lines: evaluator bindings exceed granted compute limits");
        if (evaluator->uniform_bytes > std::min(info.max_uniform_buffer_size, info.max_buffer_size))
            throw std::runtime_error("lines: evaluator uniform buffer exceeds granted binding size");
        if (const auto error = vispy::shader::resource_limit_error(evaluator->samplers,
                info.max_samplers, info.max_sampled_textures); !error.empty())
            throw std::runtime_error("lines: evaluator " + error);
        vispy::shader::LineEvaluatorDispatch minimum;
        std::string error;
        if (!vispy::shader::line_evaluator_dispatch(*evaluator, 1, limits, minimum, error))
            throw std::runtime_error(error);
        original->evaluator = evaluator;
        shader_artifacts.store_auxiliary(original->portable, evaluator);
        refresh_artifact(*original);
        return evaluator;
    }

    std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact> prepare_line_consumer(
            const std::shared_ptr<Artifact>& original, const vispy::shader::LineConsumerPolicy& policy) {
        if (!original || !original->portable)
            throw std::runtime_error("lines: generated consumer requires a captured original shader");
        require_integer_sampling_route(*original->portable, 2, "generated line fragment consumer");
        auto evaluator = prepare_line_evaluator(original);
        const auto policy_identity = vispy::shader::generated_line_consumer_policy_identity(*evaluator, policy);
        std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact> consumer;
        if (auto retained = original->consumer_devices.find(policy_identity, device_generation))
            consumer = retained->consumer;
        if (!consumer) {
            auto cached = shader_artifacts.find_consumer(original->portable->identity, policy_identity);
            if (cached && cached->original == original->portable && cached->evaluator == evaluator)
                consumer = std::move(cached);
        }
        if (consumer) {
            if (consumer->original != original->portable || consumer->evaluator != evaluator ||
                    consumer->policy_identity != policy_identity || consumer->policy.coverage != policy.coverage ||
                    consumer->policy.sample_count != policy.sample_count ||
                    consumer->policy.coverage_identity != policy.coverage_identity ||
                    consumer->policy.depth_output != policy.depth_output)
                throw std::runtime_error("lines: retained consumer has a different captured pair or coverage policy");
            ++probe.line_consumer_hits;
        } else {
            ++probe.line_consumer_misses;
            consumer = vispy::shader::build_generated_line_consumer(evaluator, policy, consumer_limits());
            const auto& timings = consumer->timings;
            probe.shader_normalize_ns += timings.normalize_ns;
            probe.shader_parse_ns += timings.parse_ns;
            probe.shader_link_ns += timings.link_ns;
            probe.shader_spirv_ns += timings.spirv_ns;
            probe.shader_reflect_ns += timings.reflect_ns;
            probe.shader_cpu_build_ns += timings.total_ns;
            probe.shader_normalizations += timings.normalizations;
            probe.shader_parse_calls += timings.parse_calls;
            probe.shader_link_calls += timings.link_calls;
            probe.shader_spirv_stages += timings.spirv_stages;
        }
        if (!consumer->ok) throw std::runtime_error("lines: generated consumer: " + consumer->error);
        if (consumer->original != original->portable || consumer->evaluator != evaluator ||
                consumer->policy_identity != policy_identity)
            throw std::runtime_error("lines: generated consumer has a different original/evaluator pair");
        const auto limits = consumer_limits();
        if (limits.max_inter_stage_shader_variables < 1 || limits.max_storage_buffers_per_stage < 1 ||
                consumer->vertex_storage_bindings != 1 || consumer->fragment_storage_bindings != 1 ||
                consumer->output_binding >= limits.max_bindings_per_group || consumer->uniform_stage_mask != 3 ||
                consumer->uniform_bytes > std::min(limits.max_uniform_binding_bytes, limits.max_buffer_bytes))
            throw std::runtime_error("lines: retained consumer interface exceeds the newly granted device limits");
        if (const auto error = vispy::shader::resource_limit_error(consumer->samplers,
                info.max_samplers, info.max_sampled_textures); !error.empty())
            throw std::runtime_error("lines: consumer " + error);
        // Admission may refuse an oversized graph. The captured draw retains
        // its exact triple, and external-owner accounting includes it.
        shader_artifacts.store_consumer(original->portable, policy_identity, consumer);
        refresh_artifact(*original);
        return consumer;
    }

    void prepare_line_pipeline(const std::shared_ptr<Artifact>& original) {
        if (original->line_pipeline_ok && original->line_generation == device_generation) {
            ++probe.pipeline_hits;
            return;
        }
        const auto& evaluator = *original->evaluator;
        const auto creation_generation = device_generation;
        PipelineCreationScopes creation(instance, device, "line evaluator compute " + evaluator.cache_key,
            current_backend_shader_log, creation_generation);
        creation.begin();
        original->line_module = make_spirv_module(evaluator.spv, evaluator.derivative_mode,
            "line evaluator compute/main");
        std::vector<wgpu::BindGroupLayoutEntry> entries;
        auto buffer_entry = [&](uint32_t binding, wgpu::BufferBindingType type, uint64_t minimum) {
            wgpu::BindGroupLayoutEntry entry;
            entry.binding = binding;
            entry.visibility = wgpu::ShaderStage::Compute;
            entry.buffer.type = type;
            entry.buffer.minBindingSize = minimum;
            entries.push_back(entry);
        };
        buffer_entry(evaluator.input_binding, wgpu::BufferBindingType::ReadOnlyStorage, 16);
        buffer_entry(evaluator.output_binding, wgpu::BufferBindingType::Storage, evaluator.output_row_bytes);
        if (evaluator.uniform_stage_mask)
            buffer_entry(0, wgpu::BufferBindingType::Uniform, evaluator.uniform_bytes);
        for (const auto& sampler : evaluator.samplers) {
            if (sampler.texture_stage_mask) {
                wgpu::BindGroupLayoutEntry entry;
                entry.binding = sampler.texture_binding;
                entry.visibility = wgpu::ShaderStage::Compute;
                entry.texture.sampleType = declared_sample_type(sampler);
                entry.texture.viewDimension = sampler.dim == "1d" ? wgpu::TextureViewDimension::e1D :
                sampler.dim == "3d" ? wgpu::TextureViewDimension::e3D :
                                                                    wgpu::TextureViewDimension::e2D;
                entries.push_back(entry);
            }
            if (sampler.sampler_stage_mask) {
                wgpu::BindGroupLayoutEntry entry;
                entry.binding = sampler.sampler_binding;
                entry.visibility = wgpu::ShaderStage::Compute;
                entry.sampler.type = declared_sampler_type(sampler);
                entries.push_back(entry);
            }
        }
        wgpu::BindGroupLayoutDescriptor bindings;
        bindings.entryCount = entries.size();
        bindings.entries = entries.data();
        original->line_bind_layout = device.CreateBindGroupLayout(&bindings);
        wgpu::PipelineLayoutDescriptor layout;
        layout.bindGroupLayoutCount = 1;
        layout.bindGroupLayouts = &original->line_bind_layout;
        original->line_pipeline_layout = device.CreatePipelineLayout(&layout);
        wgpu::ComputePipelineDescriptor pipeline;
        pipeline.label = "line evaluator compute";
        pipeline.layout = original->line_pipeline_layout;
        pipeline.compute.module = original->line_module;
        pipeline.compute.entryPoint = "main";
        {
            HostTimer timer(probe.pipeline_creation_ns);
            ++probe.compute_pipeline_creations;
            original->line_pipeline = device.CreateComputePipeline(&pipeline);
        }
        original->line_error = finish_pipeline_creation(creation, creation_generation);
        original->line_pipeline_ok = original->line_module && original->line_bind_layout &&
            original->line_pipeline_layout && original->line_pipeline && original->line_error.empty();
        original->line_generation = device_generation;
        refresh_artifact(*original);
        if (!original->line_pipeline_ok)
            throw std::runtime_error("lines: endpoint compute pipeline creation failed: " + original->line_error);
        ++probe.pipeline_misses;
    }

    std::shared_ptr<LineConsumerDevice> prepare_line_consumer_modules(const std::shared_ptr<Artifact>& original,
            const std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact>& consumer) {
        if (!consumer || !consumer->ok || consumer->original != original->portable ||
                consumer->evaluator != original->evaluator)
            throw std::runtime_error("lines: render modules require the exact captured consumer pair");
        if (auto retained = original->consumer_devices.find(consumer->policy_identity, device_generation)) {
            if (retained->consumer != consumer || !retained->ready_for(device_generation, original->portable, original->evaluator))
                throw std::runtime_error("lines: policy device record has a different captured consumer");
            return retained;
        }
        std::vector<wgpu::BindGroupLayoutEntry> entries;
        wgpu::BindGroupLayoutEntry uniforms;
        uniforms.binding = 0;
        uniforms.visibility = resource_stages(consumer->uniform_stage_mask);
        uniforms.buffer.type = wgpu::BufferBindingType::Uniform;
        uniforms.buffer.minBindingSize = consumer->uniform_bytes;
        entries.push_back(uniforms);
        wgpu::BindGroupLayoutEntry rows;
        rows.binding = consumer->output_binding;
        rows.visibility = wgpu::ShaderStage::Vertex | wgpu::ShaderStage::Fragment;
        rows.buffer.type = wgpu::BufferBindingType::ReadOnlyStorage;
        rows.buffer.minBindingSize = consumer->evaluator->output_row_bytes;
        entries.push_back(rows);
        for (const auto& sampler : consumer->samplers) {
            if (sampler.texture_stage_mask) {
                wgpu::BindGroupLayoutEntry entry;
                entry.binding = sampler.texture_binding;
                entry.visibility = resource_stages(sampler.texture_stage_mask);
                entry.texture.sampleType = declared_sample_type(sampler);
                entry.texture.viewDimension = sampler.dim == "1d" ? wgpu::TextureViewDimension::e1D :
                sampler.dim == "3d" ? wgpu::TextureViewDimension::e3D :
                                                                    wgpu::TextureViewDimension::e2D;
                entries.push_back(entry);
            }
            if (sampler.sampler_stage_mask) {
                wgpu::BindGroupLayoutEntry entry;
                entry.binding = sampler.sampler_binding;
                entry.visibility = resource_stages(sampler.sampler_stage_mask);
                entry.sampler.type = declared_sampler_type(sampler);
                entries.push_back(entry);
            }
        }
        wgpu::BindGroupLayoutDescriptor descriptor;
        descriptor.entryCount = entries.size();
        descriptor.entries = entries.data();
        auto record = std::make_shared<LineConsumerDevice>(consumer, device_generation);
        const auto prefix = "line-consumer-" + consumer->cache_key;
        dump_shader_pair(prefix, consumer->vertex, consumer->fragment, consumer->vertex_spv, consumer->fragment_spv);
        const auto creation_generation = device_generation;
        PipelineCreationScopes creation(instance, device, prefix + " modules/layout",
            current_backend_shader_log, creation_generation);
        creation.begin();
        const auto vertex_label = prefix + " vertex/main";
        const auto fragment_label = prefix + " fragment/main";
        descriptor.label = prefix.c_str();
        auto vertex = make_spirv_module(consumer->vertex_spv, consumer->original->derivative_mode,
            vertex_label.c_str());
        auto fragment = make_spirv_module(consumer->fragment_spv, consumer->original->derivative_mode,
            fragment_label.c_str());
        auto layout = device.CreateBindGroupLayout(&descriptor);
        record->error = finish_pipeline_creation(creation, creation_generation);
        if (!vertex || !fragment || !layout || !record->error.empty()) {
            throw std::runtime_error("lines: consumer module/layout creation failed: " + record->error);
        }
        record->vert_module = std::move(vertex);
        record->frag_module = std::move(fragment);
        record->bind_layout = std::move(layout);
        if (!record->ready_for(device_generation, original->portable, original->evaluator) ||
                !original->consumer_devices.publish(record))
            throw std::runtime_error("lines: policy device record publication has a different captured graph");
        refresh_artifact(*original);
        return record;
    }

    using PreparedLineResources = LineWork;

    template<class Rows>
    PreparedLineResources prepare_line_resources(const DrawSnap::LineInputs& captured,
            const std::shared_ptr<Artifact>& original, GpuObject& program, int program_id,
            const Rows& rows, bool cache = true, const std::shared_ptr<BufferRev>& packed = {}) {
        PreparedLineResources result;
        if (!original || original->portable != captured.portable)
            throw std::runtime_error("lines: endpoint resources have a different original snapshot");
        result.evaluator = prepare_line_evaluator(original);
        result.original = original;
        std::string error;
        if (!vispy::shader::line_evaluator_dispatch(*result.evaluator, rows.size(), endpoint_limits(),
                                                   result.dispatch, error))
            throw std::runtime_error(error);
        const auto order = vispy::lines::endpoint_attribute_order(captured.portable->attributes,
                                                                 result.evaluator->inputs);
        std::vector<vispy::lines::EndpointSource> sources;
        std::vector<vispy::lines::EndpointInputStamp> stamps;
        std::vector<uint32_t> widths;
        for (size_t position = 0; position < order.size(); ++position) {
            const auto index = order[position];
            if (index >= captured.vertices.size() || index >= captured.bindings.size() || !captured.vertices[index])
                throw std::runtime_error("lines: endpoint attribute has no captured source revision");
            const auto& binding = captured.bindings[index];
            const auto& field = result.evaluator->inputs[position];
            if (binding.offset < 0 || binding.stride < 0 || binding.divisor < 0 || binding.type != field.attribute.type)
                throw std::runtime_error("lines: endpoint attribute has incompatible captured binding");
            widths.push_back(field.value_type.components());
            sources.push_back({captured.vertices[index]->cpu, static_cast<uint64_t>(binding.offset),
                               static_cast<uint64_t>(binding.stride), static_cast<uint64_t>(binding.divisor),
                               field.value_type.components(), field.attribute.name});
            stamps.push_back({field.attribute.name, field.attribute.type, captured.vertices[index]->identity,
                captured.vertices[index]->revision, static_cast<uint64_t>(binding.offset),
                static_cast<uint64_t>(binding.stride), static_cast<uint64_t>(binding.divisor),
                field.value_type.components()});
        }
        const auto layout = vispy::lines::endpoint_input_layout(widths);
        if (layout.stride_words != result.evaluator->input_row_words)
            throw std::runtime_error("lines: reflected evaluator input row differs from captured layout");
        for (size_t field = 0; field < layout.word_offsets.size(); ++field)
            if (layout.word_offsets[field] != result.evaluator->inputs[field].word_offset)
                throw std::runtime_error("lines: reflected evaluator input field differs from captured layout");
        if (rows.size()) {
            if (packed) result.packed_inputs = packed;
            else if (!cache) {
                result.packed_inputs = std::make_shared<BufferRev>();
                result.packed_inputs->owner = program_id;
                result.packed_inputs->cpu = vispy::lines::pack_endpoint_inputs(rows, sources, layout,
                    std::min(input_buffer_limit(), info.max_storage_buffer_size));
            } else {
                const auto& selected = captured.selection;
                const auto key = vispy::lines::endpoint_input_key(result.evaluator->identity, selected.primitive,
                    selected.first, selected.count, selected.instances, selected.index ? selected.index->identity : 0,
                    selected.index ? selected.index->revision : 0, selected.index_bytes, stamps);
                if (!program.input_geometry_cache) program.input_geometry_cache = std::make_shared<BufferRev>();
                const auto evictions = program.input_oversized.evictions();
                auto [record, built] = vispy::inputs::working_cached_conversion(program.input_current,
                    program.input_oversized, vispy::inputs::CurrentCategory::LineEndpoint,
                    program.input_geometry_cache->derived, key, [&] {
                        auto item = std::make_shared<BufferRev>();
                        item->owner = program_id;
                        item->cpu = vispy::lines::pack_endpoint_inputs(rows, sources, layout,
                            std::min(info.max_buffer_size, info.max_storage_buffer_size));
                        return item;
                    }, [](const auto& item) { return input_record_bytes(item); },
                    [](const auto& item, auto& visited) { return input_graph_bytes(item, visited); });
                probe.vertex_input_oversized_evictions += program.input_oversized.evictions() - evictions;
                if (built) {
                    ++probe.line_endpoint_conversion_builds;
                    probe.line_endpoint_conversion_bytes += record->cpu.size();
                }
                result.packed_inputs = std::move(record);
            }
            if (result.packed_inputs->cpu.size() != result.dispatch.input_bytes)
                throw std::runtime_error("lines: packed input bytes differ from checked dispatch");
        }
        result.uniforms = vispy::lines::repack_endpoint_uniforms(captured.portable->uniforms,
            captured.uniforms, result.evaluator->uniforms, result.evaluator->uniform_bytes,
            std::min(info.max_uniform_buffer_size, info.max_buffer_size));
        for (const auto index : vispy::lines::endpoint_sampler_order(captured.portable->samplers,
                                                                   result.evaluator->samplers)) {
            if (index >= captured.textures.size() || !captured.textures[index])
                throw std::runtime_error("lines: endpoint sampler has no captured texture revision");
            result.textures.push_back(captured.textures[index]);
        }
        if (rows.size()) prepare_line_pipeline(original);
        return result;
    }

    PreparedLineResources prepare_line_resources(const DrawSnap::LineInputs& captured,
            const std::shared_ptr<Artifact>& original, GpuObject& program, int program_id) {
        return prepare_line_resources(captured, original, program, program_id, captured.selection.endpoints());
    }

    void prepare_line_chunks(DrawSnap& snap, DrawSnap::LineInputs& captured,
            GpuObject& program, int program_id) {
        namespace batches = vispy::lines::batches;
        using Record = std::shared_ptr<BufferRev>;
        constexpr uint64_t input_budget = 64ull * 1024 * 1024;
        constexpr uint64_t control_budget = 8ull * 1024 * 1024;
        const auto evaluator = prepare_line_evaluator(captured.original_artifact);
        const auto grant = std::min(input_buffer_limit(), info.max_storage_buffer_size);
        const auto canvas = canvases.find(snap.canvas_id);
        const bool capture_enabled = canvas != canvases.end() && canvas->second.diagnostic_line_endpoints &&
                                     canvas->second.capture_line_endpoints;
        const auto row_bytes = uint64_t(evaluator->input_row_words) * 4;
        auto max_new = grant < 16 ? 0 : std::min({(grant - 16) / row_bytes,
            (uint64_t(UINT32_MAX) - 4) / evaluator->input_row_words,
            uint64_t(info.max_compute_workgroups_per_dimension) * vispy::shader::kLineEvaluatorWorkgroup});
        if (capture_enabled) {
            const auto padded_capacity = grant < 16 ? 0 :
                ((grant - 16) / evaluator->output_row_bytes / vispy::shader::kLineEvaluatorWorkgroup) *
                    vispy::shader::kLineEvaluatorWorkgroup;
            max_new = std::min(max_new, padded_capacity);
        }
        const auto plan = batches::plan(captured.selection.primitive, captured.selection.selection(),
            {max_new, grant / evaluator->output_row_bytes, uint64_t(INT32_MAX), 128, control_budget});
        // Bound the complete retained input/descriptor representation before
        // allocating per-chunk bytes. Output and UBOs have separate pool admission.
        const auto fresh_rows = batches::multiply(plan.endpoint_rows_per_instance(), captured.selection.instances);
        const auto input_bytes = batches::add(batches::multiply(fresh_rows, row_bytes),
            batches::multiply(plan.chunk_count(), 16));
        if (input_bytes > input_budget || batches::multiply(plan.chunk_count(),
                sizeof(DrawSnap) + sizeof(LineWork) + sizeof(Record) * 4 + 128) > control_budget)
            throw std::length_error("lines: chunk input/control representation exceeds explicit budget");
        vispy::shader::LineConsumerPolicy policy;
        policy.coverage = captured.selection.state.smooth ? vispy::shader::LineCoveragePolicy::SmoothAnalytic :
                                                          vispy::shader::LineCoveragePolicy::AliasedMajorAxis;
        policy.sample_count = static_cast<uint32_t>(snap.state.sample_count);
        policy.depth_output = bool(snap.depth_view) || bool(snap.depth_attachment);
        policy.coverage_identity = vispy::shader::line_coverage_identity(
            captured.selection.state.smooth, policy.sample_count);
        const auto consumer = prepare_line_consumer(captured.original_artifact, policy);
        const auto consumer_device = prepare_line_consumer_modules(captured.original_artifact, consumer);
        std::shared_ptr<LineCapture> aggregate_capture;
        std::optional<std::deque<std::shared_ptr<LineCapture>>> next_captures;
        if (capture_enabled) {
            aggregate_capture = prepare_chunk_capture(snap.canvas_id, evaluator, plan, grant);
            next_captures.emplace(line_captures);
            next_captures->push_back(aggregate_capture);
        }
        const auto& selected = captured.selection;
        std::string key = "line-endpoint:chunks:" + vispy::lines::endpoint_input_key(evaluator->identity,
            selected.primitive, selected.first, selected.count, selected.instances,
            selected.index ? selected.index->identity : 0, selected.index ? selected.index->revision : 0,
            selected.index_bytes, {});
        key += ":grant:" + std::to_string(grant) + ":fresh:" + std::to_string(max_new);
        for (size_t n = 0; n < captured.vertices.size(); ++n) {
            const auto& source = captured.vertices[n];
            const auto& binding = captured.bindings.at(n);
            key += ':' + std::to_string(source->identity) + ':' + std::to_string(source->revision) + ':' +
                std::to_string(binding.offset) + ':' + std::to_string(binding.stride) + ':' + std::to_string(binding.divisor);
        }
        auto leaves = std::make_shared<std::vector<DrawSnap>>();
        leaves->reserve(static_cast<size_t>(plan.chunk_count()));
        if (!program.input_geometry_cache) program.input_geometry_cache = std::make_shared<BufferRev>();
        auto build_leaves = [&](const Record& root, bool cold) {
            uint64_t actual_input_bytes = 0;
            for (uint64_t number = 0; number < plan.chunk_count(); ++number) {
                const auto chunk = plan.chunk(number);
                const auto edge = std::to_string(number);
                const auto packed = !cold && chunk.new_rows ? root->derived.at(edge) : Record{};
                auto work = std::make_shared<LineWork>(prepare_line_resources(captured,
                    captured.original_artifact, program, program_id, batches::rows(plan, chunk), false, packed));
                work->chunk = chunk;
                work->capture = aggregate_capture;
                work->capture_part = static_cast<size_t>(number);
                if (work->packed_inputs) {
                    actual_input_bytes = batches::add(actual_input_bytes, work->packed_inputs->cpu.capacity());
                    if (actual_input_bytes > input_budget)
                        throw std::length_error("lines: actual chunk input capacity exceeds budget");
                    if (cold) root->derived.emplace(edge, work->packed_inputs);
                }
                work->dispatch.output_bytes = chunk.output_rows * evaluator->output_row_bytes;
                work->consumer = consumer;
                work->consumer_device = consumer_device;
                work->consumer_draw = vispy::shader::plan_generated_line_consumer_chunk_draw(*consumer,
                    static_cast<uint32_t>(chunk.new_rows), static_cast<uint32_t>(chunk.output_rows),
                    static_cast<uint32_t>(chunk.segment_count), chunk.previous, chunk.closing,
                    chunk.primitive == vispy::lines::Mode::List, static_cast<uint32_t>(chunk.first_segment),
                    selected.state, {double(snap.viewport[0]), double(snap.viewport[1]),
                        double(snap.viewport[2] < 0 ? snap.target_width : snap.viewport[2]),
                        double(snap.viewport[3] < 0 ? snap.target_height : snap.viewport[3])},
                    snap.target_height, snap.state.depth_range[0], snap.state.depth_range[1], consumer_limits());
                DrawSnap leaf = snap;
                leaf.line_chunks.reset();
                leaf.line_work = std::move(work);
                leaf.line_inputs.reset();
                leaf.semantic_draw = number == 0;
                leaf.clear = number == 0 && snap.clear;
                leaf.clear_depth = number == 0 && snap.clear_depth;
                leaf.clear_stencil = number == 0 && snap.clear_stencil;
                leaf.uniforms = vispy::lines::pack_generated_line_consumer_uniforms(*consumer,
                    captured.uniforms, leaf.line_work->consumer_draw,
                    std::min(info.max_uniform_buffer_size, input_buffer_limit()));
                leaf.textures.clear();
                for (const auto index : vispy::lines::endpoint_sampler_order(captured.portable->samplers, consumer->samplers))
                    leaf.textures.push_back(captured.textures.at(index));
                leaf.vertices.clear(); leaf.bindings.clear(); leaf.vertex_slots.clear(); leaf.vertex_streams.clear();
                leaf.point_identity.reset(); leaf.vertex_identity.reset();
                leaf.index.reset(); leaf.index_type.clear(); leaf.index_count = 0;
                leaf.first = 0; leaf.count = 6; leaf.instances = static_cast<int>(chunk.segment_count);
                leaf.mode = "triangles"; leaf.state.cull_enabled = false;
                leaf.state.polygon_offset_fill = false; leaf.state.stencil_back = leaf.state.stencil_front;
                leaves->push_back(std::move(leaf));
            }
            uint64_t output_capacity = 0, native_control = 0;
            uint64_t host_control = batches::add(sizeof(*leaves),
                batches::multiply(leaves->capacity(), sizeof(DrawSnap)));
            for (const auto& leaf : *leaves) {
                const auto& work = *leaf.line_work;
                const auto shape = line_control_shape(leaf);
                output_capacity = batches::add(output_capacity,
                    batches::add(line_capacity(line_output_bytes(work), info.max_storage_buffer_size),
                        batches::add(line_capacity(shape.compute_uniforms, info.max_uniform_buffer_size),
                                     line_capacity(shape.render_uniforms, info.max_uniform_buffer_size))));
                native_control = batches::add(native_control, line_control_bytes(shape));
                host_control = batches::add(host_control, sizeof(LineWork) + 2 * sizeof(void*) +
                    work.uniforms.capacity() + leaf.uniforms.capacity() + key.capacity() +
                    (work.textures.capacity() + leaf.textures.capacity()) * sizeof(std::shared_ptr<TextureRev>) +
                    leaf.vertices.capacity() * sizeof(Record) + leaf.bindings.capacity() * sizeof(AttrBinding) +
                    leaf.vertex_slots.capacity() * sizeof(uint32_t) + leaf.vertex_streams.capacity() * sizeof(VertexStream) +
                    leaf.integer_sampling_policies.capacity() * sizeof(vispy::shader::IntegerSamplePolicy) +
                    leaf.mode.capacity() + leaf.index_type.capacity());
            }
            const vispy::lines::PoolLimits pool_limits;
            if (output_capacity > pool_limits.owned_capacity_bytes - line_canary_capacity ||
                native_control > pool_limits.control_bytes || host_control > control_budget)
                throw std::length_error("lines: aggregate chunk output/control exceeds resident pool budget");
            validate_line_chunk_pool(*leaves);
        };
        Record root = program.input_current.find(vispy::inputs::CurrentCategory::LineEndpoint, key);
        if (root) build_leaves(root, false);
        else {
            const auto previous_evictions = program.input_oversized.evictions();
            auto [record, built] = vispy::inputs::batches::transactional_conversion(program.input_current,
                program.input_oversized, program.input_geometry_cache->derived,
                vispy::inputs::CurrentCategory::LineEndpoint, key, [&] {
                    auto candidate = std::make_shared<BufferRev>(); candidate->owner = program_id;
                    build_leaves(candidate, true);
                    return candidate;
                }, [](const auto& item) { return input_record_bytes(item); },
                   [](const auto& item, auto& visited) { return input_graph_bytes(item, visited); },
                   [&](const auto& current, auto category, const auto& cache_key, auto record) {
                       if (leaves->empty()) build_leaves(record, false);
                       return current.prepare(category, cache_key, std::move(record));
                   });
            probe.vertex_input_oversized_evictions += program.input_oversized.evictions() - previous_evictions;
            if (built) {
                ++probe.line_endpoint_conversion_builds;
                probe.line_endpoint_conversion_bytes += input_record_bytes(record, true);
            }
        }
        captured.evaluator = evaluator; captured.consumer = consumer; captured.consumer_device = consumer_device;
        if (aggregate_capture) {
            line_captures.swap(*next_captures);
            line_capture_bytes += aggregate_capture->charged_bytes;
            ++next_line_capture;
        }
        snap.line_chunks = std::move(leaves);
        snap.vertices.clear(); snap.bindings.clear(); snap.vertex_slots.clear(); snap.vertex_streams.clear();
        snap.index.reset(); snap.point_identity.reset(); snap.vertex_identity.reset();
    }

    void prepare_line_render(DrawSnap& snap, DrawSnap::LineInputs& captured,
                             GpuObject& program, int program_id) {
        const auto& selected = captured.selection;
        const auto evaluator = prepare_line_evaluator(captured.original_artifact);
        const auto segments = selected.segments();
        const auto per_instance_rows = selected.primitive == vispy::lines::Mode::List ?
            selected.count - selected.count % 2 : selected.count;
        const auto total_rows = vispy::lines::batches::multiply(per_instance_rows, selected.instances);
        vispy::shader::LineEvaluatorDispatch whole_dispatch;
        std::string whole_error;
        const bool whole_fits = segments.size() <= INT32_MAX && vispy::shader::line_evaluator_dispatch(*evaluator,
                total_rows, endpoint_limits(), whole_dispatch, whole_error);
        const auto canvas = canvases.find(snap.canvas_id);
        const bool capture_enabled = canvas != canvases.end() && canvas->second.diagnostic_line_endpoints &&
                                     canvas->second.capture_line_endpoints;
        const auto capture_grant = std::min(input_buffer_limit(), info.max_storage_buffer_size);
        const bool whole_capture_fits = !capture_enabled || (whole_fits &&
            vispy::lines::captures::part_raw_bytes(static_cast<uint32_t>(total_rows),
                static_cast<uint32_t>(total_rows), evaluator->output_row_bytes) <= capture_grant);
        if (!whole_fits || !whole_capture_fits) {
            prepare_line_chunks(snap, captured, program, program_id);
            return;
        }
        vispy::lines::LineConsumerSelection selection(selected.primitive, selected.selection());
        vispy::shader::LineConsumerPolicy policy;
        policy.coverage = selected.state.smooth ? vispy::shader::LineCoveragePolicy::SmoothAnalytic :
                                                vispy::shader::LineCoveragePolicy::AliasedMajorAxis;
        policy.sample_count = static_cast<uint32_t>(snap.state.sample_count);
        policy.depth_output = bool(snap.depth_view) || bool(snap.depth_attachment);
        policy.coverage_identity = vispy::shader::line_coverage_identity(
            selected.state.smooth, policy.sample_count);
        auto consumer = prepare_line_consumer(captured.original_artifact, policy);
        const auto draw = vispy::shader::plan_generated_line_consumer_draw(*consumer, selection,
            {0, selection.segment_count()}, selected.state,
            {double(snap.viewport[0]), double(snap.viewport[1]),
             double(snap.viewport[2] < 0 ? snap.target_width : snap.viewport[2]),
             double(snap.viewport[3] < 0 ? snap.target_height : snap.viewport[3])},
            snap.target_height, snap.state.depth_range[0], snap.state.depth_range[1], consumer_limits());
        auto work = std::make_shared<LineWork>(prepare_line_resources(captured,
            captured.original_artifact, program, program_id));
        if (draw.endpoint_bytes != work->dispatch.output_bytes)
            throw std::runtime_error("lines: consumer row extent differs from checked evaluator output");
        work->consumer = consumer;
        work->consumer_draw = draw;
        auto uniforms = vispy::lines::pack_generated_line_consumer_uniforms(*consumer, captured.uniforms,
            draw, std::min(info.max_uniform_buffer_size, info.max_buffer_size));
        std::vector<std::shared_ptr<TextureRev>> textures;
        for (const auto index : vispy::lines::endpoint_sampler_order(captured.portable->samplers, consumer->samplers)) {
            if (index >= captured.textures.size() || !captured.textures[index])
                throw std::runtime_error("lines: consumer sampler has no captured texture revision");
            textures.push_back(captured.textures[index]);
        }
        work->consumer_device = prepare_line_consumer_modules(captured.original_artifact, consumer);
        captured.evaluator = work->evaluator;
        captured.consumer = consumer;
        captured.consumer_device = work->consumer_device;
        snap.line_work = std::move(work);
        snap.uniforms = std::move(uniforms);
        snap.textures = std::move(textures);
        // The evaluator is the sole reader of original vertex/index inputs.
        // Procedural triangles consume its leased rows without invoking user VS.
        snap.vertices.clear(); snap.bindings.clear(); snap.vertex_slots.clear(); snap.vertex_streams.clear();
        snap.point_identity.reset(); snap.vertex_identity.reset();
        snap.index.reset(); snap.index_type.clear(); snap.index_count = 0;
        snap.first = 0;
        snap.count = static_cast<int>(draw.vertex_count);
        snap.instances = static_cast<int>(draw.instance_count);
        snap.mode = "triangles";
        snap.state.cull_enabled = false;
        snap.state.polygon_offset_fill = false;
        // GL lines use the front-face stencil policy irrespective of the
        // generated triangles' winding.
        snap.state.stencil_back = snap.state.stencil_front;
    }

    std::shared_ptr<LineCapture> reserve_line_capture(int canvas_id, const LineWork& work) {
        auto capture = std::make_shared<LineCapture>();
        capture->canvas_id = canvas_id;
        const auto canvas = canvases.find(canvas_id);
        if (canvas != canvases.end() && canvas->second.frame_mark) {
            capture->frame_id = canvas->second.frame_mark->frame_id;
            if (canvas->second.frame_mark->queries)
                capture->paint_token = canvas->second.frame_mark->queries->work.paint_token;
        }
        capture->evaluator = work.evaluator;
        auto& result = capture->result;
        result.capture_id = next_line_capture++;
        result.device_generation = device_generation;
        result.rows = work.dispatch.input_header[0];
        result.row_bytes = work.evaluator->output_row_bytes;
        result.evaluator_key = work.evaluator->cache_key;
        result.status = result.rows ? "pending" : "empty";
        result.error.reserve(LineCapture::error_limit);
        result.fields.reserve(work.evaluator->outputs.size() + 1);
        result.fields.push_back({"gl_Position", "vec4", "", 0, 16, 0, 0, 0});
        for (const auto& output : work.evaluator->outputs)
            result.fields.push_back({output.varying.name, output.varying.type, output.varying.interpolation,
                output.offset, output.size, output.array_stride, output.matrix_stride, output.varying.array_size});
        // Expose all padded output rows to the instrumented binding, so a
        // missing shader guard cannot hide behind robust out-of-bounds access.
        const uint64_t padded_rows = uint64_t(work.dispatch.workgroups_x) * vispy::shader::kLineEvaluatorWorkgroup;
        if (result.rows) {
            const auto limit = std::min({info.max_storage_buffer_size, info.max_buffer_size,
                                         line_capture_byte_limit / 3});
            if (limit < 16 || padded_rows > (limit - 16) / result.row_bytes)
                throw std::runtime_error("lines: diagnostic padded output exceeds granted storage/allocation limits");
            capture->allocation_bytes = padded_rows * result.row_bytes + 16;
        }
        capture->charged_bytes = capture->allocation_bytes * 3 + sizeof(LineCapture) + sizeof(AsyncResult) +
            result.evaluator_key.capacity() + result.status.capacity() + 2 * result.error.capacity() +
            result.fields.capacity() * sizeof(LineEndpointField);
        for (const auto& field : result.fields)
            capture->charged_bytes += field.name.capacity() + field.type.capacity() + field.interpolation.capacity();
        if (line_captures.size() >= line_capture_limit ||
            capture->charged_bytes > line_capture_byte_limit - line_capture_bytes)
            throw std::runtime_error("lines: endpoint diagnostic retention limit exceeded; collect existing captures");
        // Reserve owned CPU readback storage after bounded admission and
        // before publication. Collection does not grow beyond these payloads.
        result.raw_data.reserve(static_cast<size_t>(capture->allocation_bytes));
        result.data.reserve(static_cast<size_t>(uint64_t(result.rows) * result.row_bytes));
        line_captures.push_back(capture);
        line_capture_bytes += capture->charged_bytes;
        return capture;
    }

    std::shared_ptr<LineCapture> prepare_chunk_capture(int canvas_id,
            const std::shared_ptr<const vispy::shader::LineEvaluatorArtifact>& evaluator,
            const vispy::lines::batches::Plan& source, uint64_t binding_limit) {
        namespace caps = vispy::lines::captures;
        namespace batches = vispy::lines::batches;
        if (line_captures.size() >= line_capture_limit)
            throw std::length_error("lines: collect retained endpoint captures before recording another");
        auto capture = std::make_shared<LineCapture>();
        capture->canvas_id = canvas_id;
        const auto canvas = canvases.find(canvas_id);
        if (canvas != canvases.end() && canvas->second.frame_mark) {
            capture->frame_id = canvas->second.frame_mark->frame_id;
            if (canvas->second.frame_mark->queries)
                capture->paint_token = canvas->second.frame_mark->queries->work.paint_token;
        }
        capture->evaluator = evaluator;
        capture->chunk_plan = caps::plan(source, evaluator->output_row_bytes, binding_limit,
            128, line_capture_byte_limit, line_capture_byte_limit);
        capture->allocation_bytes = capture->chunk_plan.raw_bytes;
        auto& result = capture->result;
        result.capture_id = next_line_capture;
        result.device_generation = device_generation;
        result.rows = capture->chunk_plan.rows;
        result.row_bytes = evaluator->output_row_bytes;
        result.evaluator_key = evaluator->cache_key;
        result.status = "pending";
        result.error.reserve(LineCapture::error_limit);
        result.chunks = capture->chunk_plan.parts;
        result.fields.reserve(evaluator->outputs.size() + 1);
        result.fields.push_back({"gl_Position", "vec4", "", 0, 16, 0, 0, 0});
        for (const auto& output : evaluator->outputs)
            result.fields.push_back({output.varying.name, output.varying.type, output.varying.interpolation,
                output.offset, output.size, output.array_stride, output.matrix_stride, output.varying.array_size});
        capture->parts.resize(result.chunks.size());
        auto charge = batches::add(sizeof(LineCapture), capture->chunk_plan.metadata_storage_bytes());
        charge = batches::add(charge, batches::multiply(capture->parts.capacity(), sizeof(LineCapturePart)));
        charge = batches::add(charge, batches::multiply(result.chunks.capacity(), sizeof(caps::Part)));
        charge = batches::add(charge, result.evaluator_key.capacity() + result.status.capacity() + result.error.capacity());
        charge = batches::add(charge, batches::multiply(result.fields.capacity(), sizeof(LineEndpointField)));
        for (const auto& field : result.fields)
            charge = batches::add(charge, field.name.capacity() + field.type.capacity() + field.interpolation.capacity());
        for (const auto& part : result.chunks) if (part.rows)
            charge = batches::add(charge, sizeof(AsyncResult) + 2 * sizeof(void*) + LineCapture::error_limit);
        // Each physical allocation charges its leased output, map-read buffer
        // and retained raw bytes. The separate logical result is also charged.
        charge = batches::add(charge, batches::add(batches::multiply(capture->allocation_bytes, 3),
                                                  capture->chunk_plan.logical_bytes));
        if (charge > line_capture_byte_limit - line_capture_bytes)
            throw std::length_error("lines: aggregate endpoint capture exceeds retained byte budget");
        result.raw_data.reserve(static_cast<size_t>(capture->allocation_bytes));
        result.data.reserve(static_cast<size_t>(capture->chunk_plan.logical_bytes));
        charge = batches::add(charge, result.raw_data.capacity() - capture->allocation_bytes);
        charge = batches::add(charge, result.data.capacity() - capture->chunk_plan.logical_bytes);
        for (size_t index = 0; index < capture->parts.size(); ++index) if (result.chunks[index].rows) {
            auto wait = std::make_shared<AsyncResult>();
            wait->error.reserve(LineCapture::error_limit);
            charge = batches::add(charge, wait->error.capacity() - LineCapture::error_limit);
            capture->parts[index].map_result = std::move(wait);
        }
        if (charge > line_capture_byte_limit - line_capture_bytes)
            throw std::length_error("lines: actual endpoint capture capacities exceed retained byte budget");
        capture->charged_bytes = charge;
        return capture;
    }

    static uint64_t line_output_bytes(const LineWork& work) {
        if (!work.capture) return work.dispatch.output_bytes;
        if (work.capture->parts.empty()) return work.capture->allocation_bytes;
        return std::max(work.dispatch.output_bytes,
            work.capture->chunk_plan.parts.at(work.capture_part).raw_bytes);
    }

    bool collect_chunk_capture(LineCapture& capture) {
        auto& result = capture.result;
        for (size_t index = 0; index < capture.parts.size(); ++index) {
            auto& part = capture.parts[index];
            if (part.collected) continue;
            const auto& shape = capture.chunk_plan.parts.at(index);
            if (!shape.rows) {
                vispy::lines::captures::append_part(capture.chunk_plan, index, {}, result.raw_data, result.data);
                part.collected = true;
                continue;
            }
            if (!part.readback || !part.map_result) {
                result.status = "map_error";
                capture.set_error("endpoint chunk has no retained readback/map state");
                result.data.clear();
                return true;
            }
            const auto wait = part.map_result;
            if (!part.map_requested) {
                part.map_future = part.readback.MapAsync(wgpu::MapMode::Read, 0, shape.raw_bytes,
                    wgpu::CallbackMode::AllowProcessEvents,
                    [wait, owner = part.readback](wgpu::MapAsyncStatus status, wgpu::StringView message) {
                        wait->ok = status == wgpu::MapAsyncStatus::Success;
                        const auto error = view_to_string(message);
                        wait->error.assign(error.data(), std::min(error.size(), LineCapture::error_limit));
                        wait->done.store(true);
                    });
                part.map_requested = true;
            }
            if (!wait->done.load()) {
                ++probe.completion_waits;
                wait_result(part.map_future, wait);
            }
            if (!wait->done.load()) return false;
            if (!wait->ok) {
                result.status = "map_error";
                capture.set_error(wait->error);
                result.data.clear();
                return true;
            }
            const auto* bytes = static_cast<const uint8_t*>(part.readback.GetConstMappedRange(0, shape.raw_bytes));
            if (!bytes) {
                result.status = "map_error";
                capture.set_error("successful endpoint chunk map returned no owned range");
                result.data.clear();
                part.readback.Unmap();
                return true;
            }
            try {
                vispy::lines::captures::append_part(capture.chunk_plan, index,
                    {bytes, static_cast<size_t>(shape.raw_bytes)}, result.raw_data, result.data);
            } catch (const std::exception& error) {
                // append_part preserves actual failed raw bytes before guard
                // rejection. Never return a successful partial logical result.
                result.status = "padding_error";
                capture.set_error(error.what());
                result.data.clear();
                part.readback.Unmap();
                return true;
            }
            part.readback.Unmap();
            part.collected = true;
        }
        if (result.raw_data.size() != capture.chunk_plan.raw_bytes ||
            result.data.size() != capture.chunk_plan.logical_bytes) {
            result.status = "map_error";
            capture.set_error("endpoint chunks did not complete the admitted logical/raw extents");
            result.data.clear();
        } else result.status = "completed";
        return true;
    }

    static bool has_line_resources(const DrawSnap& snap) {
        return snap.line_work && line_output_bytes(*snap.line_work) != 0;
    }

    static bool draw_render_ready(const DrawSnap& snap, uint64_t generation) {
        if (!snap.artifact || !snap.artifact->linked_for(generation)) return false;
        if (snap.line_work && snap.line_work->consumer) {
            const auto& work = *snap.line_work;
            return work.original == snap.artifact && work.evaluator == snap.artifact->evaluator &&
                work.consumer_device && work.consumer == work.consumer_device->consumer &&
                snap.artifact->consumer_ready_for(work.consumer_device, generation);
        }
        return snap.artifact->valid_for(generation);
    }

    static LineControlShape line_control_shape(const DrawSnap& snap) {
        const auto& work = *snap.line_work;
        LineControlShape shape;
        shape.compute_uniforms = work.evaluator->uniform_stage_mask ? work.uniforms.size() : 0;
        shape.compute_entries = 2 + (shape.compute_uniforms ? 1 : 0);
        shape.compute_textures = work.textures.size();
        for (const auto& sampler : work.evaluator->samplers)
            shape.compute_entries += bool(sampler.texture_stage_mask) + bool(sampler.sampler_stage_mask);
        if (snap.artifact && snap.count > 0 && snap.instances > 0) {
            if (!draw_render_ready(snap, snap.artifact->device_generation))
                throw std::runtime_error("lines: render resource admission requires the selected DRAW route");
            const auto& portable = *snap.artifact->portable;
            const bool consumer_render = bool(work.consumer);
            const auto& samplers = consumer_render ? work.consumer->samplers : portable.samplers;
            shape.render_uniforms = consumer_render ? snap.uniforms.size() :
                !portable.uniforms.empty() && portable.uniform_stage_mask ? snap.uniforms.size() : 0;
            shape.render_buffers = consumer_render ? 0 : bool(snap.point_identity) + bool(snap.vertex_identity);
            // The leased row buffer has a mandatory read-only render binding;
            // it is owned by the lease, rather than a borrowed BufferRev.
            shape.render_entries = bool(shape.render_uniforms) + shape.render_buffers + bool(consumer_render);
            shape.render_textures = snap.textures.size();
            for (size_t i = 0; i < std::min(snap.textures.size(), samplers.size()); ++i)
                shape.render_entries += bool(samplers[i].texture_stage_mask) + bool(samplers[i].sampler_stage_mask);
        }
        return shape;
    }

    static uint64_t line_control_bytes(const LineControlShape& shape) {
        using namespace vispy::lines::line_pool_detail;
        auto bytes = add(shape.compute_uniforms, shape.render_uniforms);
        bytes = add(bytes, multiply(add(shape.compute_entries, shape.render_entries), sizeof(LineBindingKey)));
        bytes = add(bytes, multiply(add(1, shape.render_buffers), sizeof(LineBorrowedBuffer)));
        bytes = add(bytes, multiply(add(shape.compute_textures, shape.render_textures), sizeof(LineBorrowedTexture)));
        // Padding and reserve growth stay inside this fixed arena. Its null
        // upstream allocator rejects any attempt to exceed the admitted bound.
        return add(sizeof(NativeLineControl), add(512, multiply(bytes, 2)));
    }

    std::string line_resource_affinity(const DrawSnap& snap) const {
        const auto& work = *snap.line_work;
        std::string affinity = work.evaluator->cache_key + ":" + std::to_string(work.packed_inputs ? work.packed_inputs->identity : 0) +
            ":" + std::to_string(line_output_bytes(work)) + ":" +
            std::to_string(reinterpret_cast<uintptr_t>(work.original->line_bind_layout.Get())) + ":" +
            std::to_string(reinterpret_cast<uintptr_t>(snap.artifact ?
                (work.consumer ? work.consumer_device->bind_layout.Get() : snap.artifact->bind_layout.Get()) : nullptr));
        for (const auto& texture : work.textures)
            affinity += ":ct:" + std::to_string(reinterpret_cast<uintptr_t>(texture.get())) + ":" + std::to_string(texture->revision);
        for (const auto& texture : snap.textures)
            affinity += ":rt:" + std::to_string(reinterpret_cast<uintptr_t>(texture.get())) + ":" + std::to_string(texture->revision);
        affinity += ":p:" + std::to_string(snap.point_identity ? snap.point_identity->identity : 0) +
            ":v:" + std::to_string(snap.vertex_identity ? snap.vertex_identity->identity : 0);
        return affinity;
    }

    void validate_line_chunk_pool(const std::vector<DrawSnap>& leaves) const {
        // Run the real empty-pool admission algorithm before publishing packed
        // inputs. This includes slot/membership/affinity/control overhead, not
        // just output and UBO bytes. The temporary payloads contain no GPU handles.
        vispy::lines::PoolLimits limits;
        limits.owned_capacity_bytes -= line_canary_capacity;
        limits.staging_owned_capacity_bytes = limits.owned_capacity_bytes;
        NativeLinePool trial(limits, device_generation);
        std::vector<std::string> affinities;
        std::vector<vispy::lines::LeaseRequest> requests;
        affinities.reserve(leaves.size()); requests.reserve(leaves.size());
        for (const auto& leaf : leaves) {
            const auto shape = line_control_shape(leaf);
            affinities.push_back(line_resource_affinity(leaf));
            requests.push_back({device_generation, affinities.back(),
                {line_capacity(line_output_bytes(*leaf.line_work), info.max_storage_buffer_size),
                 line_capacity(shape.compute_uniforms, info.max_uniform_buffer_size),
                 line_capacity(shape.render_uniforms, info.max_uniform_buffer_size)}, line_control_bytes(shape)});
        }
        auto reserved = trial.reserve_batch(requests, [](const vispy::lines::SlotPlan& plan) {
            return vispy::lines::BuiltPoolPayload<NativeLineSlot>{NativeLineSlot{}, plan.extra_control_bytes};
        });
        if (!reserved) throw std::length_error("lines: chunk batch cannot fit an empty resource pool");
    }

    uint64_t line_capacity(uint64_t bytes, uint64_t binding_limit) const {
        if (!bytes) return 0;
        if (bytes > UINT64_MAX - 3)
            throw std::overflow_error("lines: resource capacity alignment overflow");
        const uint64_t aligned = std::max<uint64_t>(4, (bytes + 3) & ~uint64_t(3));
        if (aligned > std::min(info.max_buffer_size, binding_limit))
            throw std::length_error("lines: reusable resource exceeds granted binding/allocation limit");
        return aligned;
    }

    void prune_line_bindings() {
        if (!line_pool) return;
        line_pool->for_each_slot([&](const auto& slot) {
            if (slot.state != vispy::lines::PoolSlotState::Idle || !slot.payload.control) return;
            for (auto* cache : {&slot.payload.control->compute, &slot.payload.control->render})
                if (cache->group && !cache->sources_live(device_generation)) cache->clear();
        });
    }

    void ensure_line_canary() {
        if (line_canary) return;
        wgpu::BufferDescriptor descriptor;
        descriptor.size = std::min<uint64_t>(line_canary_capacity, info.max_buffer_size) & ~uint64_t(3);
        if (descriptor.size < 4) throw std::length_error("lines: device cannot allocate the canary template");
        descriptor.usage = wgpu::BufferUsage::CopySrc;
        descriptor.mappedAtCreation = true;
        device.PushErrorScope(wgpu::ErrorFilter::Validation);
        wgpu::Buffer candidate;
        try {
            candidate = device.CreateBuffer(&descriptor);
            ++probe.buffer_allocations;
            if (!candidate) throw std::runtime_error("lines: canary template creation failed");
            auto* initial = candidate.GetMappedRange(0, descriptor.size);
            if (!initial) throw std::runtime_error("lines: canary template has no mapped range");
            std::memset(initial, 0xcd, static_cast<size_t>(descriptor.size));
            candidate.Unmap();
        } catch (...) {
            pop_validation();
            throw;
        }
        const auto error = pop_validation();
        if (!error.empty()) throw std::runtime_error("lines: canary template validation: " + error);
        line_canary = std::move(candidate);
    }

    NativeLinePool::ReserveResult reserve_line_resources(const std::vector<DrawSnap>& draws) {
        if (!line_pool) {
            vispy::lines::PoolLimits limits;
            // Reserve the immutable template's maximum capacity even before
            // it is needed. No late capture can exceed the resident ceiling.
            limits.owned_capacity_bytes -= line_canary_capacity;
            limits.staging_owned_capacity_bytes = limits.owned_capacity_bytes;
            line_pool = std::make_unique<NativeLinePool>(limits, device_generation);
        }
        line_pool->invalidate_generation(device_generation);
        prune_line_bindings();
        size_t count = 0;
        for_each_draw_leaf(draws, [&](const auto& snap) {
            if (has_line_resources(snap)) ++count;
        });
        if (static_cast<size_t>(count) > line_pool->limits().max_slots)
            throw std::length_error("lines: endpoint batch exceeds reusable resource slot limit");
        std::vector<std::string> affinities;
        std::vector<vispy::lines::LeaseRequest> requests;
        affinities.reserve(static_cast<size_t>(count));
        requests.reserve(static_cast<size_t>(count));
        bool capture = false;
        for_each_draw_leaf(draws, [&](const auto& snap) {
            if (!has_line_resources(snap)) return;
            const auto& work = *snap.line_work;
            const auto shape = line_control_shape(snap);
            const vispy::lines::LeaseCapacities capacities{
                line_capacity(line_output_bytes(work), info.max_storage_buffer_size),
                line_capacity(shape.compute_uniforms, info.max_uniform_buffer_size),
                line_capacity(shape.render_uniforms, info.max_uniform_buffer_size)};
            // Affinity is a reuse preference, never a correctness key. Native
            // group identity below compares every binding and weak revision.
            auto affinity = line_resource_affinity(snap);
            affinities.push_back(std::move(affinity));
            requests.push_back({device_generation, affinities.back(), capacities, line_control_bytes(shape)});
            capture = capture || bool(work.capture);
        });
        const auto before = line_pool->stats();
        auto reserved = line_pool->reserve_batch(requests, [&](const vispy::lines::SlotPlan& plan) {
            if (plan.extra_control_bytes <= sizeof(NativeLineControl) || plan.extra_control_bytes > SIZE_MAX)
                throw std::length_error("lines: native control arena exceeds host capacity");
            NativeLineSlot payload;
            payload.control = std::make_unique<NativeLineControl>(plan.extra_control_bytes);
            device.PushErrorScope(wgpu::ErrorFilter::Validation);
            try {
                auto create = [&](uint64_t capacity, wgpu::BufferUsage usage) {
                    if (!capacity) return wgpu::Buffer{};
                    wgpu::BufferDescriptor descriptor;
                    descriptor.size = capacity;
                    descriptor.usage = usage | wgpu::BufferUsage::CopyDst;
                    auto buffer = device.CreateBuffer(&descriptor);
                    ++probe.buffer_allocations;
                    if (!buffer) throw std::runtime_error("lines: reusable native buffer creation failed");
                    return buffer;
                };
                payload.output = create(plan.capacities.output, wgpu::BufferUsage::Storage | wgpu::BufferUsage::CopySrc);
                payload.compute_uniforms = create(plan.capacities.compute_ubo, wgpu::BufferUsage::Uniform);
                payload.render_uniforms = create(plan.capacities.render_ubo, wgpu::BufferUsage::Uniform);
            } catch (...) {
                pop_validation();
                throw;
            }
            const auto error = pop_validation();
            if (!error.empty()) throw std::runtime_error("lines: reusable native buffer validation: " + error);
            return vispy::lines::BuiltPoolPayload<NativeLineSlot>{std::move(payload), plan.extra_control_bytes};
        });
        const auto after = line_pool->stats();
        probe.line_resource_pool_hits += after.hits - before.hits;
        probe.line_resource_pool_evictions += after.evictions - before.evictions;
        probe.line_resource_pool_deferrals += after.deferrals - before.deferrals;
        if (reserved && capture) ensure_line_canary();
        return reserved;
    }

    NativeLineSlot& configure_line_slot(NativeLinePool::LeaseHandle& handle, const DrawSnap& snap) {
        auto& slot = handle.payload();
        const auto shape = line_control_shape(snap);
        if (line_control_bytes(shape) > handle.extra_control_bytes())
            throw std::length_error("lines: control shape exceeds reserved native arena");
        if (!slot.control || slot.control->shape != shape) {
            // The slot is reserved exclusively; its previous native groups
            // have no submitted consumers. Repartition within the same bound.
            slot.control.reset();
            slot.control = std::make_unique<NativeLineControl>(handle.extra_control_bytes());
            slot.control->configure(shape);
        }
        return slot;
    }

    void write_line_uniforms(const wgpu::Buffer& buffer, std::pmr::vector<uint8_t>& shadow,
                             std::span<const uint8_t> bytes) {
        if (bytes.empty()) return;
        if (!buffer || bytes.size() > buffer.GetSize() || bytes.size() % 4 || bytes.size() > shadow.capacity())
            throw std::runtime_error("lines: uniform bytes exceed reserved aligned buffer/control capacity");
        if (shadow.size() == bytes.size() && std::equal(shadow.begin(), shadow.end(), bytes.begin())) return;
        HostTimer timer(probe.buffer_upload_cpu_ns);
        queue.WriteBuffer(buffer, 0, bytes.data(), bytes.size());
        shadow.assign(bytes.begin(), bytes.end());
        probe.uniform_upload_bytes += bytes.size();
        probe.copy_bytes += bytes.size();
    }

    wgpu::BindGroup cached_line_group(LineCachedBindings& cache, const std::shared_ptr<Artifact>& artifact,
            bool compute, const wgpu::BindGroupLayout& layout, std::span<const wgpu::BindGroupEntry> entries,
            std::span<const std::shared_ptr<BufferRev>> buffers,
            std::span<const std::shared_ptr<TextureRev>> textures,
            const std::shared_ptr<LineConsumerDevice>& consumer_device = {}) {
        if (entries.size() > cache.keys.capacity() || buffers.size() > cache.buffers.capacity() ||
                textures.size() > cache.textures.capacity())
            throw std::length_error("lines: bind metadata exceeds reserved native arena shape");
        std::vector<LineBindingKey> keys;
        keys.reserve(entries.size());
        for (const auto& entry : entries) {
            if (entry.buffer) keys.push_back({entry.binding, 0, reinterpret_cast<uintptr_t>(entry.buffer.Get()), entry.offset, entry.size});
            else if (entry.textureView) keys.push_back({entry.binding, 1, reinterpret_cast<uintptr_t>(entry.textureView.Get()), 0, 0});
            else if (entry.sampler) keys.push_back({entry.binding, 2, reinterpret_cast<uintptr_t>(entry.sampler.Get()), 0, 0});
            else throw std::runtime_error("lines: bind entry has no supported native resource");
        }
        if (cache.group && cache.sources_live(device_generation) && cache.layout == layout.Get() &&
                cache.compute == compute && cache.consumer_device.lock() == consumer_device && cache.keys.size() == keys.size() &&
                std::equal(cache.keys.begin(), cache.keys.end(), keys.begin())) return cache.group;
        cache.clear();
        wgpu::BindGroupDescriptor descriptor;
        descriptor.layout = layout;
        descriptor.entryCount = entries.size();
        descriptor.entries = entries.data();
        auto group = device.CreateBindGroup(&descriptor);
        ++probe.bind_group_creations;
        if (!group) throw std::runtime_error("lines: reusable bind group creation failed");
        cache.group = group; cache.layout = layout.Get(); cache.generation = device_generation;
        cache.compute = compute; cache.artifact = artifact;
        cache.consumer_device = consumer_device;
        cache.keys.assign(keys.begin(), keys.end());
        for (const auto& owner : buffers) cache.buffers.push_back({owner, owner->gpu});
        for (const auto& owner : textures)
            cache.textures.push_back({owner, owner->texture, owner->view, owner->sampler, owner->gpu_bytes});
        return group;
    }

    void encode_line_work(const std::shared_ptr<LineWork>& work,
                          const wgpu::CommandEncoder& encoder, Ticket& ticket, NativeLineSlot* slot) {
        if (!work || !work->dispatch.workgroups_x) return;
        if (!slot || !slot->control) throw std::runtime_error("lines: endpoint dispatch has no exclusive resource lease");
        const auto& capture = work->capture;
        const bool chunk_capture = capture && !capture->parts.empty();
        auto* captured_part = chunk_capture ? &capture->parts.at(work->capture_part) : nullptr;
        const uint64_t readback_bytes = !capture ? 0 : chunk_capture ?
            capture->chunk_plan.parts.at(work->capture_part).raw_bytes : capture->allocation_bytes;
        const uint64_t output_bytes = line_output_bytes(*work);
        if (work->original->line_generation != device_generation || !work->original->line_pipeline_ok)
            throw std::runtime_error("lines: endpoint compute state has a stale device generation");
        const bool upload = !work->packed_inputs->gpu ||
                            work->packed_inputs->gpu_revision != work->packed_inputs->revision;
        upload_revision(*work->packed_inputs, wgpu::BufferUsage::Storage);
        if (upload) probe.line_endpoint_upload_bytes += work->packed_inputs->cpu.size();
        ticket.buffers.push_back(work->packed_inputs);
        for (const auto& texture : work->textures) {
            // This is inside the ordered DRAW loop: prior FBO writes remain
            // ahead of these captured copies and this endpoint evaluation.
            upload_texture(*texture, encoder, &ticket);
            ticket.textures.push_back(texture);
        }
        auto output = slot->output;
        if (!output || output_bytes > output.GetSize()) throw std::runtime_error("lines: endpoint output exceeds its lease");
        if (capture) {
            if (!line_canary) throw std::runtime_error("lines: endpoint capture has no initialized canary template");
            for (uint64_t offset = 0; offset < output_bytes; ) {
                const auto bytes = std::min(line_canary.GetSize(), output_bytes - offset);
                encoder.CopyBufferToBuffer(line_canary, 0, output, offset, bytes);
                offset += bytes;
            }
            wgpu::BufferDescriptor descriptor;
            descriptor.size = readback_bytes;
            descriptor.usage = wgpu::BufferUsage::MapRead | wgpu::BufferUsage::CopyDst;
            auto& readback = captured_part ? captured_part->readback : capture->readback;
            readback = device.CreateBuffer(&descriptor);
            ++probe.buffer_allocations;
            if (!readback) throw std::runtime_error("lines: endpoint readback buffer creation failed");
            ticket.transient_buffers.push_back(readback);
        }
        std::vector<wgpu::BindGroupEntry> entries;
        auto buffer_entry = [&](uint32_t binding, const wgpu::Buffer& buffer, uint64_t bytes) {
            wgpu::BindGroupEntry entry;
            entry.binding = binding;
            entry.buffer = buffer;
            entry.size = bytes;
            entries.push_back(entry);
        };
        buffer_entry(work->evaluator->input_binding, work->packed_inputs->gpu, work->dispatch.input_bytes);
        buffer_entry(work->evaluator->output_binding, output, output_bytes);
        if (work->evaluator->uniform_stage_mask) {
            auto uniforms = slot->compute_uniforms;
            write_line_uniforms(uniforms, slot->control->compute_shadow, work->uniforms);
            buffer_entry(0, uniforms, work->evaluator->uniform_bytes);
        }
        for (size_t position = 0; position < work->textures.size(); ++position) {
            const auto& sampler = work->evaluator->samplers[position];
            if (sampler.texture_stage_mask) {
                wgpu::BindGroupEntry entry;
                entry.binding = sampler.texture_binding;
                entry.textureView = work->textures[position]->view;
                entries.push_back(entry);
            }
            if (sampler.sampler_stage_mask) {
                wgpu::BindGroupEntry entry;
                entry.binding = sampler.sampler_binding;
                entry.sampler = work->textures[position]->sampler;
                entries.push_back(entry);
            }
        }
        const std::array borrowed_buffers{work->packed_inputs};
        auto group = cached_line_group(slot->control->compute, work->original, true,
            work->original->line_bind_layout, entries, borrowed_buffers, work->textures);
        ticket.bind_groups.push_back(group);
        auto pass = begin_timed_compute_pass(encoder, ticket);
        pass.SetPipeline(work->original->line_pipeline);
        pass.SetBindGroup(0, group);
        pass.DispatchWorkgroups(work->dispatch.workgroups_x, 1, 1);
        ++probe.line_endpoint_dispatches;
        probe.line_endpoint_rows += work->dispatch.input_header[0];
        pass.End();
        if (capture) {
            encoder.CopyBufferToBuffer(output, 0, captured_part ? captured_part->readback : capture->readback, 0, readback_bytes);
            capture->result.status = "encoded";
        }
    }

    wgpu::Buffer upload_buffer(const void* data, size_t size, wgpu::BufferUsage usage) {
        HostTimer timer(probe.buffer_upload_cpu_ns);
        wgpu::BufferDescriptor bd;
        bd.size = std::max<size_t>(4, (size + 3u) & ~3u);
        if (bd.size > info.max_buffer_size) throw std::runtime_error("buffer exceeds granted device limit");
        bd.usage = usage | wgpu::BufferUsage::CopyDst;
        auto buffer = device.CreateBuffer(&bd);
        ++probe.buffer_allocations;
        if (data != nullptr && size > 0) {
            if (size % 4) {
                std::vector<uint8_t> padded(bd.size, 0);
                std::memcpy(padded.data(), data, size);
                queue.WriteBuffer(buffer, 0, padded.data(), padded.size());
            } else queue.WriteBuffer(buffer, 0, data, size);
            probe.copy_bytes += size;
        }
        return buffer;
    }

    void upload_revision(BufferRev& rev, wgpu::BufferUsage usage) {
        if (!rev.gpu) rev.gpu = upload_buffer(rev.cpu.data(), rev.cpu.size(), usage);
        else if (rev.gpu_revision != rev.revision) {
            HostTimer timer(probe.buffer_upload_cpu_ns);
            if (rev.cpu.size() % 4) {
                std::vector<uint8_t> padded(rev.gpu.GetSize(), 0);
                std::memcpy(padded.data(), rev.cpu.data(), rev.cpu.size());
                queue.WriteBuffer(rev.gpu, 0, padded.data(), padded.size());
            } else queue.WriteBuffer(rev.gpu, 0, rev.cpu.data(), rev.cpu.size());
            probe.copy_bytes += rev.cpu.size();
        } else return;
        rev.gpu_revision = rev.revision;
        ++probe.buffer_uploads;
        probe.geometry_upload_bytes += rev.cpu.size();
    }

    static uint64_t input_record_bytes(const std::shared_ptr<BufferRev>& record, bool payload_only = false) {
        uint64_t bytes = payload_only ? record->cpu.size() : sizeof(BufferRev) + 2 * sizeof(void*) + record->cpu.capacity();
        if (!payload_only && record->batch_data) bytes += record->batch_data->metadata_storage_bytes();
        if (!payload_only && record->point_batch_data) bytes += record->point_batch_data->metadata_storage_bytes();
        for (const auto& [key, child] : record->derived) {
            if (!payload_only) bytes += sizeof(decltype(record->derived)::value_type) +
                vispy::inputs::cache_entry_bookkeeping + key.capacity();
            bytes += input_record_bytes(child, payload_only);
        }
        return bytes;
    }

    static uint64_t input_graph_bytes(const std::shared_ptr<BufferRev>& record,
                                     std::unordered_set<const void*>& visited) {
        using vispy::inputs::bounded_cost_add;
        if (!record || !visited.insert(record.get()).second) return 0;
        uint64_t bytes = bounded_cost_add(sizeof(BufferRev) + 2 * sizeof(void*), record->cpu.capacity());
        if (record->batch_data) bytes = bounded_cost_add(bytes, record->batch_data->metadata_storage_bytes());
        if (record->point_batch_data) bytes = bounded_cost_add(bytes, record->point_batch_data->metadata_storage_bytes());
        for (const auto& [key, child] : record->derived) {
            bytes = bounded_cost_add(bytes, sizeof(decltype(record->derived)::value_type) +
                vispy::inputs::cache_entry_bookkeeping + key.capacity());
            bytes = bounded_cost_add(bytes, input_graph_bytes(child, visited));
        }
        return bytes;
    }

    static void discard_input_category(GpuObject& program, vispy::inputs::CurrentCategory category,
                                       const std::string& prefix) {
        program.input_current.clear(category);
        program.input_oversized.clear(category);
        if (program.input_geometry_cache)
            vispy::inputs::discard_category(program.input_geometry_cache->derived, prefix);
    }

    template<class Build> std::shared_ptr<BufferRev> cache_input(GpuObject& program,
            vispy::inputs::CurrentCategory category, const std::string& key, Build&& build) {
        if (!program.input_geometry_cache) program.input_geometry_cache = std::make_shared<BufferRev>();
        const auto previous_evictions = program.input_oversized.evictions();
        auto [record, built] = vispy::inputs::working_cached_conversion(program.input_current,
            program.input_oversized, category,
            program.input_geometry_cache->derived, key,
            std::forward<Build>(build), [](const auto& item) { return input_record_bytes(item); },
            [](const auto& item, auto& visited) { return input_graph_bytes(item, visited); });
        probe.vertex_input_oversized_evictions += program.input_oversized.evictions() - previous_evictions;
        if (built) {
            ++probe.vertex_input_conversion_builds;
            probe.vertex_input_conversion_bytes += input_record_bytes(record, true);
        }
        return record;
    }

    // Input allocation planning uses the actual granted device limit. An
    // isolated boundary-test derivative can lower only this return value;
    // DeviceInfo and all native device/binding grants stay unchanged.
    uint64_t input_buffer_limit() const noexcept { return info.max_buffer_size; }

    void prepare_index_inputs(GpuObject& program, DrawSnap& snap, int program_id, int original_index_owner) {
        using namespace vispy::inputs;
        program.input_index_owner = original_index_owner;
        // A no-op draw creates no converted payload or cache admission.
        if (!snap.count || !snap.instances) return;
        // Keep an oversized fan's original selection, including u8 indices.
        // Expanding it here would fail before ordered batching can partition it.
        if (snap.mode == "triangle_fan" &&
            !vispy::inputs::batches::fan_expansion_fits(uint64_t(snap.count), input_buffer_limit())) return;
        if (snap.mode == "line_loop" &&
            !vispy::inputs::batches::loop_expansion_fits(uint64_t(snap.count), input_buffer_limit())) return;
        auto selection = [&] {
            Selection selected{static_cast<uint64_t>(snap.first), static_cast<uint64_t>(snap.count),
                               static_cast<uint64_t>(snap.instances)};
            if (snap.index) {
                selected.indices = snap.index->cpu;
                selected.index_bytes = snap.index_type == "unsigned_int" ? 4 : snap.index_type == "unsigned_byte" ? 1 : 2;
            }
            validate_selection(selected);
            return selected;
        };
        if (snap.index && snap.index_type == "unsigned_byte" &&
            vispy::inputs::batches::defer_ordinary_u8_widening(snap.mode,
                uint64_t(snap.count), input_buffer_limit())) return;
        if (snap.index && snap.index_type == "unsigned_byte" && !snap.artifact->portable->point_sprites) {
            const auto selected = selection();
            const auto key = "index:u8:" + selection_key(selected, snap.index->identity, snap.index->revision);
            auto converted = cache_input(program, CurrentCategory::IndexWiden, key, [&] {
                auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                result->cpu = widen_u8(selected, input_buffer_limit()); return result;
            });
            snap.index = std::move(converted); snap.index_type = "unsigned_short";
        }
        if (snap.mode == "triangle_fan" || snap.mode == "line_loop") {
            const bool fan = snap.mode == "triangle_fan";
            const auto selected = selection();
            const auto key = "index:" + snap.mode + ':' +
                selection_key(selected, snap.index ? snap.index->identity : 0, snap.index ? snap.index->revision : 0);
            auto converted = cache_input(program, CurrentCategory::Topology, key, [&] {
                auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                result->cpu = topology_indices(selected, fan, input_buffer_limit()); return result;
            });
            snap.index = std::move(converted); snap.index_type = "unsigned_int";
            snap.index_count = snap.count = static_cast<int>(snap.index->cpu.size() / 4);
            snap.first = 0; snap.mode = fan ? "triangles" : "line_strip";
        }
    }

    // ABI2 keeps geometry tables once per geometry chunk and origin uniforms
    // once per instance block. The implicit plan never stores a G x I schedule.
    void prepare_batched_inputs(GpuObject& program, DrawSnap& snap, int program_id,
            const vispy::inputs::Selection& selected,
            std::span<const vispy::inputs::Source> sources,
            const vispy::inputs::Layout& layout, const std::string& selected_key) {
        namespace batches = vispy::inputs::batches;
        namespace owners = vispy::inputs::batches::owners;
        using Record = std::shared_ptr<BufferRev>;
        constexpr uint64_t max_calls = 100000;
        constexpr uint64_t control_budget = 64ull * 1024 * 1024;
        constexpr uint64_t payload_budget = 4ull * 1024 * 1024 * 1024;
        const auto original_topology = batches::ordinary_input_topology(snap.mode);
        const batches::Limits plan_limits{input_buffer_limit(), info.max_storage_buffer_size,
                                          control_budget, max_calls};
        const auto policy = batches::expected_ordinary_input_policy(original_topology, selected);
        auto& variant = policy.identity == VertexIdentityPolicy::BatchIndexed ?
            program.batch_indexed_artifact : program.batch_affine_artifact;
        if (!variant || variant->portable->options.vertex_identity != policy.identity) {
            std::string error;
            auto next = make_artifact(program.artifact->portable->source_vertex,
                program.artifact->portable->source_fragment, error,
                program.artifact->portable->options.base_level_sampling,
                program.artifact->default_has_depth, false, policy.identity,
                program.artifact->portable->derivative_mode, false);
            if (!error.empty()) throw std::runtime_error("DRAW batches: " + error);
            variant = std::move(next);
        }
        if (!variant->linked_for(device_generation)) {
            std::string error;
            auto next = materialize_artifact(variant->portable, variant->default_has_depth,
                error, variant->evaluator, {}, false);
            if (!error.empty()) throw std::runtime_error("DRAW batches: " + error);
            variant = std::move(next);
        }
        if (variant->portable->attributes.size() != snap.artifact->portable->attributes.size() ||
            variant->portable->uniform_bytes != snap.artifact->portable->uniform_bytes ||
            variant->portable->samplers.size() != snap.artifact->portable->samplers.size())
            throw std::runtime_error("DRAW batches: identity policy changed the original user interface");
        for (size_t n = 0; n < variant->portable->attributes.size(); ++n) {
            const auto& original = snap.artifact->portable->attributes[n];
            const auto& field = variant->portable->attributes[n];
            if (field.name != original.name || field.type != original.type || field.location != original.location)
                throw std::runtime_error("DRAW batches: identity policy changed active attribute " + original.name);
        }
        const auto source_key = vispy::inputs::partition_source_key(layout, sources, false) + ':' +
                                vispy::inputs::partition_source_key(layout, sources, true);
        const auto key = "batch:abi2:" + batches::ordinary_input_domain(snap.mode, selected_key, selected.instances) + ':' + source_key +
            ":buffer:" + std::to_string(plan_limits.buffer_bytes) +
            ":storage:" + std::to_string(plan_limits.storage_bytes) +
            ":uniform:" + std::to_string(std::min(info.max_uniform_buffer_size, input_buffer_limit()));
        // Allocate the snapshot's small layout view before installing its root.
        std::vector<VertexStream> streams;
        streams.reserve(layout.streams.size());
        for (const auto& stream : layout.streams) streams.push_back({0, stream.stride, stream.instance});
        auto slots = layout.slots;
        // Complete all shader/interface/string preparation before cache access.
        // A cold builder proves the actual lowered Plan's policy before commit.
        std::string next_index_type(policy.index_type);
        std::string next_mode(policy.mode);
        Record root = program.input_current.find(vispy::inputs::CurrentCategory::Batch, key);
        if (root) {
            if (!root->batch_data)
                throw std::runtime_error("DRAW batches: prepared cache root has no immutable plan");
            batches::validate_ordinary_input_policy(original_topology, root->batch_data->plan, policy);
            if (snap.stencil_face_split) (void)batches::stencil_face_draw_count(root->batch_data->plan);
            program.input_oversized.find(vispy::inputs::CurrentCategory::Batch, key);
        }
        else {
            // Every throwing conversion, copied cache mutation and ownership
            // charge occurs in private state. Only no-throw swaps publish it.
            const auto previous_evictions = program.input_oversized.evictions();
            auto [record, built] = batches::transactional_conversion(program.input_current,
                program.input_oversized, program.input_geometry_cache->derived,
                vispy::inputs::CurrentCategory::Batch, key, [&] {
                    const owners::Limits owner_limits{payload_budget, control_budget,
                        payload_budget + control_budget, 1000000, max_calls,
                        sizeof(BufferRev) + 2 * sizeof(void*),
                        sizeof(decltype(BufferRev::derived)::value_type) + vispy::inputs::cache_entry_bookkeeping};
                    struct Builder {
                        int owner;
                        Record make_root() const {
                            auto item = std::make_shared<BufferRev>(); item->owner = owner; return item;
                        }
                        Record make_leaf(std::vector<uint8_t>&& data, owners::LeafKind) const {
                            auto item = make_root(); item->cpu = std::move(data); return item;
                        }
                        void attach(Record& parent, std::string edge, const Record& child) const {
                            if (!parent->derived.emplace(std::move(edge), child).second)
                                throw std::runtime_error("DRAW batches: repeated prepared root edge");
                        }
                    };
                    // The adapter destroys topology diagnostics before packing
                    // the owning indexed strip payload into split ABI2 leaves.
                    auto payload = batches::plan_ordinary_input_batches(original_topology,
                        selected, sources, layout, plan_limits);
                    batches::validate_ordinary_input_policy(original_topology, payload, policy);
                    if (snap.stencil_face_split) (void)batches::stencil_face_draw_count(payload);
                    auto prepared = owners::prepare_owner<Record>(std::move(payload), sources,
                        owner_limits, std::min(info.max_uniform_buffer_size, input_buffer_limit()), Builder{program_id});
                    prepared.root->batch_data = std::move(prepared.data);
                    return std::move(prepared.root);
                }, [](const auto& item) { return input_record_bytes(item); },
                   [](const auto& item, auto& visited) { return input_graph_bytes(item, visited); });
            probe.vertex_input_oversized_evictions += program.input_oversized.evictions() - previous_evictions;
            if (built) {
                ++probe.vertex_input_conversion_builds;
                probe.vertex_input_conversion_bytes += input_record_bytes(record, true);
            }
            root = std::move(record);
        }
        if (!root || !root->batch_data)
            throw std::runtime_error("DRAW batches: prepared cache root has no immutable plan");
        batches::validate_ordinary_input_policy(original_topology, root->batch_data->plan, policy);
        if (snap.stencil_face_split) (void)batches::stencil_face_draw_count(root->batch_data->plan);
        snap.artifact = variant;
        snap.vertices.clear(); snap.vertex_streams = std::move(streams); snap.vertex_slots = std::move(slots);
        for (size_t n = 0; n < snap.bindings.size(); ++n) snap.bindings[n].offset = layout.offsets[n];
        snap.index.reset(); snap.vertex_identity.reset(); snap.index_count = 0; snap.first = 0;
        snap.index_type.swap(next_index_type);
        snap.batch_inputs = std::move(root);
        snap.mode.swap(next_mode);
    }

    void prepare_batched_point_inputs(GpuObject& program, DrawSnap& snap, int program_id,
            int original_index_owner, const vispy::points::Selection& selected,
            std::span<const vispy::points::PackedSource> sources,
            const vispy::inputs::Layout& layout) {
        namespace batches = vispy::points::batches;
        namespace owners = vispy::points::batches::owners;
        using Record = std::shared_ptr<BufferRev>;
        constexpr uint64_t max_calls = 100000;
        constexpr uint64_t control_budget = 64ull * 1024 * 1024;
        constexpr uint64_t payload_budget = 4ull * 1024 * 1024 * 1024;
        const batches::Limits plan_limits{input_buffer_limit(), info.max_storage_buffer_size,
                                          control_budget, max_calls};
        const bool identity_live = snap.artifact->portable->point_identity_binding != 0;
        const uint64_t total_rows = batches::checked_product(selected.count, selected.instances);
        const auto key = "batch:points:partitioned-abi1:" + vispy::points::conversion_key("ranges", selected,
            0, 0, snap.index ? snap.index->identity : 0, snap.index ? snap.index->revision : 0) +
            vispy::points::packed_source_key(sources, snap.index ? snap.index->identity : 0,
                snap.index ? snap.index->revision : 0, selected.index_bytes) +
            vispy::points::partition_key(layout, sources) +
            ":buffer:" + std::to_string(plan_limits.buffer_bytes) +
            ":storage:" + std::to_string(plan_limits.storage_bytes) +
            ":identity:" + std::to_string(identity_live);
        // Prepare the snapshot's layout before committing any cache mutation.
        std::vector<VertexStream> streams;
        streams.reserve(layout.streams.size());
        for (const auto& stream : layout.streams) streams.push_back({0, stream.stride, true});
        auto slots = layout.slots;
        program.input_index_owner = original_index_owner;
        if (!program.input_geometry_cache) program.input_geometry_cache = std::make_shared<BufferRev>();
        Record root = program.input_current.find(vispy::inputs::CurrentCategory::Batch, key);
        if (root) program.input_oversized.find(vispy::inputs::CurrentCategory::Batch, key);
        else {
            const auto previous_evictions = program.input_oversized.evictions();
            auto [record, built] = vispy::inputs::batches::transactional_conversion(program.input_current,
                program.input_oversized, program.input_geometry_cache->derived,
                vispy::inputs::CurrentCategory::Batch, key, [&] {
                    const auto plan = batches::plan(selected, sources, layout, plan_limits);
                    const owners::Limits owner_limits{payload_budget, control_budget,
                        payload_budget + control_budget, owners::add(1, batches::checked_product(max_calls,
                            owners::add(layout.streams.size(), uint64_t(identity_live)))),
                        sizeof(BufferRev) + 2 * sizeof(void*),
                        sizeof(decltype(BufferRev::derived)::value_type) + vispy::inputs::cache_entry_bookkeeping};
                    struct Builder {
                        int owner;
                        Record make_root() const {
                            auto item = std::make_shared<BufferRev>(); item->owner = owner; return item;
                        }
                        Record make_leaf(std::vector<uint8_t>&& bytes, owners::LeafKind) const {
                            auto item = make_root(); item->cpu = std::move(bytes); return item;
                        }
                        void attach(Record& parent, std::string edge, const Record& child) const {
                            if (!parent->derived.emplace(std::move(edge), child).second)
                                throw std::runtime_error("DRAW point batches: repeated prepared root edge");
                        }
                    };
                    auto prepared = owners::prepare_owner<Record>(plan, sources, layout,
                        owner_limits, Builder{program_id}, identity_live);
                    if (!prepared.root || !prepared.data || prepared.data->draws.empty() ||
                        prepared.data->total_rows != total_rows)
                        throw std::runtime_error("DRAW point batches: incomplete prepared owner");
                    prepared.root->point_batch_data = std::move(prepared.data);
                    return std::move(prepared.root);
                }, [](const auto& item) { return input_record_bytes(item); },
                   [](const auto& item, auto& visited) { return input_graph_bytes(item, visited); });
            probe.vertex_input_oversized_evictions += program.input_oversized.evictions() - previous_evictions;
            if (built) {
                ++probe.point_conversion_builds;
                probe.point_conversion_bytes += input_record_bytes(record, true);
            }
            root = std::move(record);
        }
        if (!root || !root->point_batch_data || root->point_batch_data->draws.empty() ||
            root->point_batch_data->total_rows != total_rows)
            throw std::runtime_error("DRAW point batches: cached owner differs from selected rows");
        snap.vertices.clear(); snap.point_identity.reset();
        snap.vertex_streams = std::move(streams); snap.vertex_slots = std::move(slots);
        snap.point_batch_inputs = std::move(root);
    }

    void prepare_vertex_inputs(GpuObject& program, DrawSnap& snap, int program_id, int original_index_owner) {
        using namespace vispy::inputs;
        Selection selected{static_cast<uint64_t>(snap.first), static_cast<uint64_t>(snap.count),
                           static_cast<uint64_t>(snap.instances)};
        if (snap.index) {
            selected.indices = snap.index->cpu;
            selected.index_bytes = snap.index_type == "unsigned_int" ? 4 : snap.index_type == "unsigned_byte" ? 1 : 2;
        }
        validate_selection(selected);
        if (!selected.count || !selected.instances) {
            snap.vertices.clear(); snap.vertex_slots.clear(); snap.vertex_streams.clear(); return;
        }
        if (snap.stencil_face_split) {
            const auto error = ordinary_stencil_replay_error(snap.artifact->portable->spv_vert, snap.artifact->portable->spv_frag);
            if (!error.empty()) throw std::runtime_error(error);
        }
        std::vector<Source> sources;
        for (size_t n = 0; n < snap.bindings.size(); ++n) {
            const auto& field = snap.artifact->portable->attributes.at(n);
            const auto& binding = snap.bindings[n];
            const auto& buffer = snap.vertices[n];
            sources.push_back({buffer->cpu, buffer->identity, buffer->revision,
                static_cast<uint64_t>(binding.offset), static_cast<uint64_t>(binding.stride),
                attribute_components(field.type) * 4ull, static_cast<uint64_t>(binding.divisor), field.name});
        }
        const auto key = selection_key(selected, snap.index ? snap.index->identity : 0,
                                       snap.index ? snap.index->revision : 0);
        const auto index_stamp = std::to_string(snap.index ? snap.index->identity : 0) + ':' +
            std::to_string(snap.index ? snap.index->revision : 0) + ':' + std::to_string(selected.index_bytes);
        program.input_index_owner = original_index_owner;
        if (!program.input_geometry_cache) program.input_geometry_cache = std::make_shared<BufferRev>();
        if (program.input_index_source != index_stamp) {
            discard_input_category(program, CurrentCategory::Selection, "selection:");
            discard_input_category(program, CurrentCategory::Bounds, "bounds:");
            discard_input_category(program, CurrentCategory::Vertex, "vertex:");
            discard_input_category(program, CurrentCategory::CompactFit, "compact-fit:");
            program.input_index_source = index_stamp;
        }
        uint32_t maximum;
        if (selected.index_bytes) {
            const auto bound = cache_input(program, CurrentCategory::Bounds, "bounds:" + key, [&] {
                auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                const uint32_t value = maximum_vertex(selected);
                result->cpu.resize(4); std::memcpy(result->cpu.data(), &value, 4); return result;
            });
            std::memcpy(&maximum, bound->cpu.data(), 4);
        } else maximum = maximum_vertex(selected);
        validate_sources(selected, sources, maximum);
        auto layout = direct_layout(sources, info.max_vertex_attributes, info.max_vertex_buffers, info.max_vertex_buffer_stride);
        const bool strip_sentinel = snap.index && (snap.mode == "line_strip" || snap.mode == "triangle_strip") &&
            maximum == (selected.index_bytes == 2 ? UINT16_MAX : UINT32_MAX);
        const bool source_buffers_fit = direct_uploads_fit(selected, sources, input_buffer_limit());
        if (snap.stencil_face_split) {
            layout = compact_layout(sources, info.max_vertex_attributes, info.max_vertex_buffers, info.max_vertex_buffer_stride);
            prepare_batched_inputs(program, snap, program_id, selected, sources, layout, key);
            return;
        }
        if (layout.direct && snap.mode != "triangle_fan" && snap.mode != "line_loop" && !strip_sentinel && source_buffers_fit) {
            const auto original = snap.vertices;
            snap.vertices.clear();
            for (const auto& stream : layout.streams) {
                snap.vertices.push_back(original.at(stream.fields.front()));
                snap.vertex_streams.push_back({stream.bind_offset, stream.stride, stream.instance});
            }
            snap.vertex_slots = std::move(layout.slots);
            for (size_t n = 0; n < snap.bindings.size(); ++n) snap.bindings[n].offset = layout.offsets[n];
            return;
        }
        layout = compact_layout(sources, info.max_vertex_attributes, info.max_vertex_buffers, info.max_vertex_buffer_stride);
        if (snap.mode == "triangle_fan" || snap.mode == "line_loop") {
            // Only fans/loops that could not expand globally survive index preparation.
            // The whole-compact probe measures the original selection, which
            // undercounts expanded indices; go straight to bounded batches.
            prepare_batched_inputs(program, snap, program_id, selected, sources, layout, key);
            return;
        }
        auto& variant = selected.index_bytes ? program.indexed_artifact : program.affine_artifact;
        variant = select_compact_artifact(selected.index_bytes != 0, program.artifact,
            program.affine_artifact, program.indexed_artifact, [&](const auto& original, bool indexed) {
            std::string error;
            auto result = make_artifact(original->portable->source_vertex, original->portable->source_fragment,
                error, original->portable->options.base_level_sampling, original->default_has_depth, false,
                indexed ? VertexIdentityPolicy::Indexed : VertexIdentityPolicy::Affine,
                original->portable->derivative_mode, false);
            if (!error.empty()) throw std::runtime_error("DRAW inputs: " + error);
            return result;
        });
        if (!variant->linked_for(device_generation)) {
            std::string error;
            variant = materialize_artifact(variant->portable, variant->default_has_depth, error,
                variant->evaluator, {}, false);
            if (!error.empty()) throw std::runtime_error("DRAW inputs: " + error);
        }
        if (variant->portable->attributes.size() != snap.artifact->portable->attributes.size() ||
            variant->portable->uniform_bytes != snap.artifact->portable->uniform_bytes ||
            variant->portable->samplers.size() != snap.artifact->portable->samplers.size())
            throw std::runtime_error("DRAW inputs: identity policy changed the original user interface");
        for (size_t n = 0; n < variant->portable->attributes.size(); ++n) {
            const auto& original = snap.artifact->portable->attributes[n];
            const auto& field = variant->portable->attributes[n];
            if (field.name != original.name || field.type != original.type || field.location != original.location)
                throw std::runtime_error("DRAW inputs: identity policy changed active attribute " + original.name);
        }
        if (vispy::inputs::batches::ordinary_input_batches(snap.mode)) {
            // Repeated indices may need only a handful of unique rows even
            // when their count is large. Preserve every existing legal whole
            // compact representation before admitting an ordered batch plan.
            const bool identity_live = variant->portable->vertex_identity_binding != 0;
            const auto fit_key = "compact-fit:" + vispy::inputs::batches::ordinary_input_domain(snap.mode, key, selected.instances) + ':' +
                partition_source_key(layout, sources, false) + ':' +
                partition_source_key(layout, sources, true) +
                ":buffer:" + std::to_string(input_buffer_limit()) +
                ":storage:" + std::to_string(info.max_storage_buffer_size) +
                ":identity:" + std::to_string(identity_live);
            const auto previous_evictions = program.input_oversized.evictions();
            auto [decision, decision_built] = vispy::inputs::working_cached_conversion(program.input_current,
                program.input_oversized, CurrentCategory::CompactFit, program.input_geometry_cache->derived,
                fit_key, [&] {
                    const auto fit = probe_whole_compact_fit(selected, layout, input_buffer_limit(),
                        info.max_storage_buffer_size, identity_live);
                    auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                    result->cpu.push_back(fit.fits ? 1 : 0); return result;
                }, [](const auto& item) { return input_record_bytes(item); },
                   [](const auto& item, auto& visited) { return input_graph_bytes(item, visited); });
            (void)decision_built; // A capacity decision does not convert attribute/index payloads.
            probe.vertex_input_oversized_evictions += program.input_oversized.evictions() - previous_evictions;
            if (!decision || decision->cpu.size() != 1)
                throw std::runtime_error("DRAW inputs: invalid cached whole-compact capacity decision");
            if (!decision->cpu[0]) {
                prepare_batched_inputs(program, snap, program_id, selected, sources, layout, key);
                return;
            }
        }
        snap.artifact = variant;
        // Affine IDs bind one four-byte base, irrespective of draw count.
        // Only an indexed ID table imposes a per-vertex storage grant.
        const uint64_t max_unique = compact_vertex_capacity(selected, layout, input_buffer_limit(),
            info.max_storage_buffer_size, variant->portable->vertex_identity_binding != 0);
        std::shared_ptr<BufferRev> selection;
        if (selected.index_bytes) {
            selection = cache_input(program, CurrentCategory::Selection, "selection:" + key, [&] {
                auto remapped = compact_indices(selected, input_buffer_limit(), max_unique);
                auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                result->cpu.resize(remapped.identities.size() * 4);
                std::memcpy(result->cpu.data(), remapped.identities.data(), result->cpu.size());
                auto indices = std::make_shared<BufferRev>(); indices->owner = program_id;
                indices->cpu.resize(remapped.indices.size() * 4);
                std::memcpy(indices->cpu.data(), remapped.indices.data(), indices->cpu.size());
                result->derived.emplace("indices", std::move(indices)); return result;
            });
            if (selection->cpu.size() / 4 > max_unique)
                throw std::runtime_error("DRAW inputs: retained selection exceeds current compact stream capacity");
        } else {
            selection = cache_input(program, CurrentCategory::Selection, "selection:" + key, [&] {
                auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                const uint32_t first = static_cast<uint32_t>(selected.first);
                result->cpu.resize(4); std::memcpy(result->cpu.data(), &first, 4); return result;
            });
        }
        std::vector<std::shared_ptr<BufferRev>> packed_streams(layout.streams.size());
        for (bool instance : {false, true}) {
            std::vector<size_t> stream_slots;
            for (size_t slot = 0; slot < layout.streams.size(); ++slot)
                if (layout.streams[slot].instance == instance) stream_slots.push_back(slot);
            if (stream_slots.empty()) continue;
            const auto stamp = partition_source_key(layout, sources, instance);
            const std::string category = instance ? "instance:" : "vertex:";
            const auto current_category = instance ? CurrentCategory::Instance : CurrentCategory::Vertex;
            auto& previous = instance ? program.input_instance_sources : program.input_vertex_sources;
            // Build every physical stream before publishing the category root.
            // A throwing conversion retains the previous complete current owner.
            auto next_stamp = stamp;
            const auto data_key = category + stamp + (instance ? ":rows:" + std::to_string(selected.instances) : ":select:" + key);
            auto root = cache_input(program, current_category, data_key, [&] {
                // Decode the byte-owned identity table only on a vertex
                // conversion miss. Warm draws and independent instance
                // records do not copy or rescan the retained table.
                std::vector<uint32_t> original_vertices;
                if (!instance && selected.index_bytes) {
                    original_vertices.resize(selection->cpu.size() / 4);
                    std::memcpy(original_vertices.data(), selection->cpu.data(), selection->cpu.size());
                }
                auto result = std::make_shared<BufferRev>(); result->owner = program_id;
                if (stream_slots.size() == 1) {
                    result->cpu = pack_stream(selected, sources, layout.streams[stream_slots.front()],
                        original_vertices, input_buffer_limit());
                } else {
                    for (size_t n = 0; n < stream_slots.size(); ++n) {
                        auto child = std::make_shared<BufferRev>(); child->owner = program_id;
                        child->cpu = pack_stream(selected, sources, layout.streams[stream_slots[n]],
                            original_vertices, input_buffer_limit());
                        result->derived.emplace("stream:" + std::to_string(n), std::move(child));
                    }
                }
                return result;
            });
            previous.swap(next_stamp);
            for (size_t n = 0; n < stream_slots.size(); ++n)
                packed_streams[stream_slots[n]] = stream_slots.size() == 1 ? root : root->derived.at("stream:" + std::to_string(n));
        }
        snap.vertices = std::move(packed_streams); snap.vertex_streams.clear(); snap.vertex_slots = layout.slots;
        for (const auto& stream : layout.streams) {
            snap.vertex_streams.push_back({0, stream.stride, stream.instance});
        }
        for (size_t n = 0; n < snap.bindings.size(); ++n) snap.bindings[n].offset = layout.offsets[n];
        if (variant->portable->vertex_identity_binding) snap.vertex_identity = selection;
        if (selected.index_bytes) {
            snap.index = selection->derived.at("indices"); snap.index_type = "unsigned_int";
            snap.index_count = snap.count;
        }
        snap.first = 0;
    }

    wgpu::RenderPipeline draw_pipeline(DrawSnap& snap, const RenderState* selected_state = nullptr) {
        auto render_state = selected_state ? *selected_state : snap.state;
        // GL ignores stencil testing when the logical FBO has no stencil bits.
        if (snap.depth_attachment && snap.depth_attachment->format == "depth_component")
            render_state.stencil_test = false;
        if (!draw_render_ready(snap, device_generation))
            throw std::runtime_error("DRAW render state is stale or unprepared for the selected route");
        HostTimer lookup_timer(probe.pipeline_cache_lookup_ns);
        const bool consumer_render = snap.line_work && snap.line_work->consumer;
        if (!consumer_render && (snap.mode == "lines" || snap.mode == "line_strip") &&
            vispy::platform::default_backend() == wgpu::BackendType::Vulkan && !info.bresenham_lines)
            throw std::runtime_error("DRAW lines: selected Vulkan device has no queried Bresenham line support");
        auto& art = *snap.artifact;
        const auto selected_consumer = consumer_render ? snap.line_work->consumer_device :
                                                        std::shared_ptr<LineConsumerDevice>{};
        if (!consumer_render && art.portable->has_flat_varyings && !art.portable->point_sprites && snap.mode != "points" &&
            vispy::platform::default_backend() == wgpu::BackendType::Vulkan && !info.last_vertex_provoking)
            throw std::runtime_error("DRAW flat varyings: selected Vulkan device has no queried last-vertex provoking support");
        std::ostringstream key;
        if (consumer_render) {
            if (!art.consumer_ready_for(selected_consumer, device_generation) ||
                    selected_consumer->consumer != snap.line_work->consumer)
                throw std::runtime_error("lines: render artifact has stale or different consumer modules");
            if (selected_consumer->consumer->policy.depth_output !=
                    (bool(snap.depth_view) || bool(snap.depth_attachment)))
                throw std::runtime_error("lines: consumer depth output differs from captured target");
            // A display digest can collide. Native pipeline lookup retains
            // the complete generated shader/policy identity instead.
            const auto& identity = selected_consumer->consumer->identity;
            key << "line-consumer:" << identity.size() << ':' << identity << ':';
        }
        key << snap.mode << ':' << snap.index_type << ':' <<
            static_cast<uint32_t>(snap.attachment ? snap.attachment->texture.GetFormat() : wgpu::TextureFormat::RGBA8Unorm);
        auto pipeline_state = render_state;
        if (consumer_render) {
            // Width lives in ABI2; coverage/sample/compiler policy is already
            // part of the consumer identity. Changing a uniform must reuse
            // the same native pipeline.
            pipeline_state.line_width = 1;
            pipeline_state.line_smooth = false;
        }
        const auto depth_format = snap.depth_attachment ? snap.depth_attachment->texture.GetFormat() :
            snap.depth_texture ? snap.depth_texture.GetFormat() : wgpu::TextureFormat::Undefined;
        key << ':' << state_key(pipeline_state) << ":depth=" << uint32_t(depth_format);
        for (const auto& stream : snap.vertex_streams)
            key << ":stream=" << stream.stride << ',' << stream.instance;
        for (size_t n = 0; n < snap.bindings.size(); ++n)
            key << ":field=" << snap.vertex_slots.at(n) << ',' << snap.bindings[n].offset;
        const auto cache_key = key.str();
        auto& variants = selected_consumer ? selected_consumer->variants : art.variants;
        if (auto found = variants.find(cache_key); found != variants.end()) {
            ++probe.pipeline_hits;
            return found->second;
        }
        lookup_timer.finish();
        std::vector<std::vector<wgpu::VertexAttribute>> attributes(snap.vertex_streams.size());
        std::vector<wgpu::VertexBufferLayout> buffers(snap.vertex_streams.size());
        for (size_t n = 0; !consumer_render && n < art.portable->attributes.size(); ++n) {
            const auto& attr = art.portable->attributes[n];
            const auto& binding = snap.bindings.at(n);
            wgpu::VertexAttribute a;
            a.shaderLocation = attr.location;
            a.offset = binding.offset;
            a.format = attribute_format(attr.type);
            attributes.at(snap.vertex_slots.at(n)).push_back(a);
        }
        for (size_t n = 0; n < buffers.size(); ++n) {
            auto& buffer = buffers[n];
            buffer.arrayStride = snap.vertex_streams[n].stride;
            buffer.stepMode = snap.vertex_streams[n].instance ? wgpu::VertexStepMode::Instance : wgpu::VertexStepMode::Vertex;
            buffer.attributeCount = attributes[n].size();
            buffer.attributes = attributes[n].data();
        }
        const auto role = std::string(consumer_render ? "generated line raster " : "ordinary DRAW ") +
            (consumer_render ? selected_consumer->consumer->cache_key : art.portable->cache_key);
        const auto creation_generation = device_generation;
        PipelineCreationScopes creation(instance, device, role, current_backend_shader_log, creation_generation);
        creation.begin();
        wgpu::PipelineLayoutDescriptor layout_desc;
        layout_desc.label = role.c_str();
        layout_desc.bindGroupLayoutCount = 1;
        layout_desc.bindGroupLayouts = consumer_render ? &selected_consumer->bind_layout : &art.bind_layout;
        auto layout = device.CreatePipelineLayout(&layout_desc);
        wgpu::ColorTargetState color;
        color.format = snap.attachment ? snap.attachment->texture.GetFormat() : wgpu::TextureFormat::RGBA8Unorm;
        wgpu::FragmentState fragment;
        fragment.module = consumer_render ? selected_consumer->frag_module : art.frag_module;
        fragment.entryPoint = "main";
        fragment.targetCount = 1;
        fragment.targets = &color;
        wgpu::RenderPipelineDescriptor desc;
        desc.label = role.c_str();
        desc.layout = layout;
        desc.vertex.module = consumer_render ? selected_consumer->vert_module : art.vert_module;
        desc.vertex.entryPoint = "main";
        desc.vertex.bufferCount = buffers.size();
        desc.vertex.buffers = buffers.data();
        desc.fragment = &fragment;
        if (snap.mode == "triangles") desc.primitive.topology = wgpu::PrimitiveTopology::TriangleList;
        else if (snap.mode == "triangle_strip") desc.primitive.topology = wgpu::PrimitiveTopology::TriangleStrip;
        else if (snap.mode == "lines") desc.primitive.topology = wgpu::PrimitiveTopology::LineList;
        else if (snap.mode == "line_strip") desc.primitive.topology = wgpu::PrimitiveTopology::LineStrip;
        else if (snap.mode == "points") desc.primitive.topology = wgpu::PrimitiveTopology::PointList;
        else throw std::runtime_error("DRAW unsupported primitive topology " + snap.mode);
        if (snap.index && (snap.mode == "line_strip" || snap.mode == "triangle_strip"))
            desc.primitive.stripIndexFormat = snap.index_type == "unsigned_int" ?
                wgpu::IndexFormat::Uint32 : wgpu::IndexFormat::Uint16;
        wgpu::DepthStencilState depth;
        if (snap.depth_view) depth.format = depth_format;
        wgpu::BlendState blend;
        fill_pipeline_state(render_state, desc, color, depth, blend);
        // The final vertex wrapper reflects clip Y. Compensate winding once
        // so GL's front-face choice survives that coordinate conversion.
        desc.primitive.frontFace = desc.primitive.frontFace == wgpu::FrontFace::CCW ?
            wgpu::FrontFace::CW : wgpu::FrontFace::CCW;
        wgpu::RenderPipeline pipeline;
        std::string error;
        {
            HostTimer timer(probe.pipeline_creation_ns);
            ++probe.render_pipeline_creations;
            pipeline = device.CreateRenderPipeline(&desc);
            error = finish_pipeline_creation(creation, creation_generation);
        }
        if (!pipeline || !error.empty())
            throw std::runtime_error(role + ": " + (error.empty() ? "null pipeline" : error));
        art.cache_render_variant(cache_key, pipeline, selected_consumer);
        refresh_artifact(art);
        ++probe.pipeline_misses;
        return pipeline;
    }

    void lower_masked_clear(DrawSnap& snap) {
        snap.origin = vispy::render::SnapshotOrigin::Clear;
        const bool has_depth = bool(snap.depth_view) || bool(snap.depth_attachment);
        const bool clear_color = snap.clear;
        const bool clear_depth = snap.clear_depth && has_depth;
        const bool clear_stencil = snap.clear_stencil && has_depth;
        std::string error;
        const std::string vertex =
            "void main(){ vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));"
            " gl_Position=vec4(p*2.0-1.0,0.0,1.0); }";
        std::string fragment = "uniform vec4 vispy_clear_color;";
        if (clear_depth) fragment += "uniform float vispy_clear_depth;";
        fragment += "void main(){ gl_FragColor=vispy_clear_color;";
        if (clear_depth) fragment += "gl_FragDepth=vispy_clear_depth;";
        fragment += "}";
        snap.artifact = make_artifact(vertex, fragment, error, false, has_depth, false,
            VertexIdentityPolicy::Native, SpirvDerivativeMode::AllowNonUniform);
        if (!error.empty()) throw std::runtime_error("glClear pipeline: " + error);
        snap.uniforms.assign(snap.artifact->portable->uniform_bytes, 0);
        for (const auto& uniform : snap.artifact->portable->uniforms) {
            const float depth = static_cast<float>(snap.state.clear_depth);
            const void* value = uniform.name == "vispy_clear_color" ?
                static_cast<const void*>(snap.clear_color) : static_cast<const void*>(&depth);
            const size_t bytes = uniform.name == "vispy_clear_color" ? 16 : 4;
            if (!pack_uniform_value(uniform, value, bytes, snap.uniforms.data(), snap.uniforms.size(), &error))
                throw std::runtime_error("glClear uniform: " + error);
        }
        snap.state.blend_enabled = false;
        snap.state.cull_enabled = false;
        snap.state.polygon_offset_fill = false;
        if (!clear_color) snap.state.color_mask.fill(false);
        snap.state.depth_test = clear_depth;
        snap.state.depth_mask = clear_depth;
        snap.state.depth_func = "always";
        snap.state.depth_range = {0, 1};
        snap.state.stencil_test = clear_stencil;
        if (clear_stencil) {
            auto& stencil = snap.state.stencil_front;
            stencil.compare = "always";
            stencil.reference = snap.state.clear_stencil;
            stencil.read_mask = 0xffffffffu;
            stencil.fail = stencil.depth_fail = "keep";
            stencil.pass = "replace";
            snap.state.stencil_back = stencil;
        }
        snap.viewport[0] = snap.viewport[1] = 0;
        snap.viewport[2] = snap.target_width;
        snap.viewport[3] = snap.target_height;
        snap.mode = "triangles";
        snap.count = 3;
        snap.clear = snap.clear_depth = snap.clear_stencil = false;
    }

    void freeze_texture_allocation(TextureRev& rev) {
        if (rev.allocation_descriptor) return;
        auto descriptor = std::make_shared<TextureData>();
        descriptor->width = rev.width;
        descriptor->height = rev.height;
        descriptor->depth = rev.depth;
        descriptor->channels = rev.channels;
        descriptor->dtype = rev.dtype;
        descriptor->format = rev.format;
        descriptor->internal_format = rev.internal_format;
        descriptor->dimensions = rev.dimensions;
        rev.allocation_descriptor = std::move(descriptor);
    }

    void refresh_sampler(TextureRev& rev) {
        const auto descriptor = sampler_texture_descriptor(rev, rev.allocation_descriptor.get());
        rev.sampler = create_sampler(device, descriptor);
    }

    uint64_t pending_depth_upload_passes(const std::shared_ptr<TextureRev>& rev,
                                        std::unordered_set<TextureRev*>& visited) const {
        if (!rev || rev->format != "depth_component" || !visited.insert(rev.get()).second ||
            (rev->texture && rev->gpu_revision == rev->revision)) return 0;
        const bool partial = !rev->updates.empty() && (rev->texture || rev->base);
        return pending_depth_upload_passes(rev->base, visited) + (partial ? rev->updates.size() : 1);
    }

    void encode_depth_upload(const wgpu::Texture& target, const PreparedTexture& payload,
                             const texture_detail::TextureRegionLayout& region,
                             const wgpu::CommandEncoder& encoder, Ticket& ticket) {
        if (!depth_upload_pipeline) {
            constexpr char shader[] = R"(
@group(0) @binding(0) var source: texture_2d<f32>;
struct Vertex { @builtin(position) position: vec4f, @location(0) uv: vec2f }
@vertex fn upload_vertex(@builtin(vertex_index) index: u32) -> Vertex {
    let p = vec2f(f32((index << 1u) & 2u), f32(index & 2u));
    return Vertex(vec4f(p * 2.0 - 1.0, 0.0, 1.0), vec2f(p.x, 1.0 - p.y));
}
@fragment fn upload_fragment(input: Vertex) -> @builtin(frag_depth) f32 {
    return textureLoad(source, vec2i(input.uv * vec2f(textureDimensions(source))), 0).r;
}
)";
            const auto generation = device_generation;
            PipelineCreationScopes scopes(instance, device, "depth upload graphics", current_backend_shader_log, generation);
            scopes.begin();
            wgpu::ShaderSourceWGSL wgsl;
            wgsl.code = shader;
            wgpu::ShaderModuleDescriptor module_descriptor;
            module_descriptor.nextInChain = &wgsl;
            auto module = device.CreateShaderModule(&module_descriptor);
            ++probe.shader_module_creations;
            wgpu::BindGroupLayoutEntry binding;
            binding.binding = 0;
            binding.visibility = wgpu::ShaderStage::Fragment;
            binding.texture.sampleType = wgpu::TextureSampleType::UnfilterableFloat;
            binding.texture.viewDimension = wgpu::TextureViewDimension::e2D;
            wgpu::BindGroupLayoutDescriptor binding_descriptor;
            binding_descriptor.entryCount = 1;
            binding_descriptor.entries = &binding;
            auto binding_layout = device.CreateBindGroupLayout(&binding_descriptor);
            wgpu::PipelineLayoutDescriptor layout_descriptor;
            layout_descriptor.bindGroupLayoutCount = 1;
            layout_descriptor.bindGroupLayouts = &binding_layout;
            auto layout = device.CreatePipelineLayout(&layout_descriptor);
            wgpu::FragmentState fragment;
            fragment.module = module;
            fragment.entryPoint = "upload_fragment";
            wgpu::DepthStencilState depth;
            depth.format = wgpu::TextureFormat::Depth32Float;
            depth.depthWriteEnabled = wgpu::OptionalBool::True;
            depth.depthCompare = wgpu::CompareFunction::Always;
            wgpu::RenderPipelineDescriptor pipeline_descriptor;
            pipeline_descriptor.label = "depth upload graphics";
            pipeline_descriptor.layout = layout;
            pipeline_descriptor.vertex.module = module;
            pipeline_descriptor.vertex.entryPoint = "upload_vertex";
            pipeline_descriptor.fragment = &fragment;
            pipeline_descriptor.depthStencil = &depth;
            auto pipeline = device.CreateRenderPipeline(&pipeline_descriptor);
            ++probe.render_pipeline_creations;
            const auto error = finish_pipeline_creation(scopes, generation);
            if (!module || !binding_layout || !layout || !pipeline || !error.empty())
                throw std::runtime_error("depth upload pipeline: " + (error.empty() ? "null resource" : error));
            depth_upload_layout = binding_layout;
            depth_upload_pipeline = pipeline;
        }
        wgpu::TextureDescriptor descriptor;
        descriptor.size = {uint32_t(region.width), uint32_t(region.height), 1};
        descriptor.format = wgpu::TextureFormat::R32Float;
        descriptor.usage = wgpu::TextureUsage::CopyDst | wgpu::TextureUsage::TextureBinding;
        auto staging = device.CreateTexture(&descriptor);
        ++probe.texture_allocations;
        ticket.owned_textures.push_back(staging);
        wgpu::TexelCopyTextureInfo destination;
        destination.texture = staging;
        wgpu::TexelCopyBufferLayout rows;
        rows.bytesPerRow = uint32_t(region.width) * sizeof(float);
        rows.rowsPerImage = uint32_t(region.height);
        queue.WriteTexture(&destination, payload.bytes.data(), payload.bytes.size(), &rows, &descriptor.size);
        wgpu::BindGroupEntry entry;
        entry.binding = 0;
        entry.textureView = staging.CreateView();
        wgpu::BindGroupDescriptor group_descriptor;
        group_descriptor.layout = depth_upload_layout;
        group_descriptor.entryCount = 1;
        group_descriptor.entries = &entry;
        auto group = device.CreateBindGroup(&group_descriptor);
        ++probe.bind_group_creations;
        wgpu::RenderPassDepthStencilAttachment depth;
        depth.view = target.CreateView();
        depth.depthLoadOp = wgpu::LoadOp::Load;
        depth.depthStoreOp = wgpu::StoreOp::Store;
        wgpu::RenderPassDescriptor pass_descriptor;
        pass_descriptor.depthStencilAttachment = &depth;
        auto pass = begin_timed_pass(encoder, pass_descriptor, &ticket, "depth_upload");
        pass.SetPipeline(depth_upload_pipeline);
        pass.SetBindGroup(0, group);
        pass.SetViewport(float(region.x), float(region.y), float(region.width), float(region.height), 0, 1);
        pass.SetScissorRect(uint32_t(region.x), uint32_t(region.y), uint32_t(region.width), uint32_t(region.height));
        pass.Draw(3);
        ++probe.native_draw_calls;
        pass.End();
    }

    void upload_depth_texture(TextureRev& rev, const wgpu::CommandEncoder& encoder, Ticket* ticket) {
        if (!encoder || !ticket) throw std::runtime_error("depth_component DATA requires an ordered encoder");
        freeze_texture_allocation(rev);
        const bool partial = !rev.updates.empty() && (rev.texture || rev.base);
        if (rev.base) {
            upload_texture(*rev.base, encoder, ticket);
            ticket->textures.push_back(rev.base);
        }
        if (!rev.texture) {
            wgpu::TextureDescriptor descriptor;
            descriptor.size = {uint32_t(rev.width), uint32_t(rev.height), 1};
            descriptor.format = wgpu::TextureFormat::Depth32Float;
            descriptor.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::TextureBinding |
                wgpu::TextureUsage::CopySrc | wgpu::TextureUsage::CopyDst;
            rev.texture = device.CreateTexture(&descriptor);
            rev.view = rev.texture.CreateView();
            rev.allocation_token = std::make_shared<int>(0);
            ++probe.texture_allocations;
        }
        rev.gpu_bytes = size_t(rev.width) * rev.height * sizeof(float);
        uint64_t copied_bytes = 0, uploaded_bytes = 0;
        if (partial && rev.base && rev.base->texture.Get() != rev.texture.Get()) {
            wgpu::TexelCopyTextureInfo source, destination;
            source.texture = rev.base->texture;
            destination.texture = rev.texture;
            wgpu::Extent3D extent{uint32_t(rev.width), uint32_t(rev.height), 1};
            encoder.CopyTextureToTexture(&source, &destination, &extent);
            copied_bytes = rev.gpu_bytes;
        }
        if (partial) {
            for (const auto& update : rev.updates) {
                const auto payload = prepare_region(*rev.allocation_descriptor, update.data);
                const auto region = texture_detail::texture_region_layout(rev.dimensions, update.data.shape, update.offset);
                encode_depth_upload(rev.texture, payload, region, encoder, *ticket);
                uploaded_bytes += payload.bytes.size();
            }
        } else {
            const auto payload = prepare_texture(rev, rev.allocation_descriptor.get());
            texture_detail::TextureRegionLayout region;
            region.width = rev.width;
            region.height = rev.height;
            encode_depth_upload(rev.texture, payload, region, encoder, *ticket);
            uploaded_bytes = payload.bytes.size();
        }
        ticket->ordered_uploads.push_back({&rev, rev.revision, partial ? rev.updates.size() : 1,
            uploaded_bytes, copied_bytes});
    }

    void upload_texture(TextureRev& rev, const wgpu::CommandEncoder& encoder = {}, Ticket* ticket = nullptr) {
        if (ticket && std::any_of(ticket->ordered_uploads.begin(), ticket->ordered_uploads.end(),
                [&](const Ticket::OrderedUpload& upload) { return upload.revision == &rev &&
                    upload.uploaded_revision == rev.revision; })) return;
        if (rev.texture && rev.gpu_revision == rev.revision) {
            if (!rev.sampler && rev.format != "depth" && rev.format != "stencil" && rev.format != "depth_stencil" && rev.format != "depth_component")
                refresh_sampler(rev);
            return;
        }
        const uint32_t limit = rev.dimensions == 1 ? info.max_texture_1d :
            rev.dimensions == 3 ? info.max_texture_3d : info.max_texture_2d;
        if (static_cast<uint32_t>(rev.width) > limit || static_cast<uint32_t>(rev.height) > limit ||
            static_cast<uint32_t>(rev.depth) > limit)
            throw std::runtime_error("texture dimensions exceed granted device limit");
        if (rev.format == "depth_component") {
            upload_depth_texture(rev, encoder, ticket);
            return;
        }
        if (rev.format == "depth" || rev.format == "stencil" || rev.format == "depth_stencil") {
            if (!rev.updates.empty() || rev.base)
                throw std::runtime_error("partial depth/stencil texture updates are unsupported");
            wgpu::TextureDescriptor depth;
            depth.size = {static_cast<uint32_t>(rev.width), static_cast<uint32_t>(rev.height), 1};
            depth.format = wgpu::TextureFormat::Depth24PlusStencil8;
            depth.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::TextureBinding |
                          wgpu::TextureUsage::CopySrc;
            rev.texture = device.CreateTexture(&depth);
            rev.allocation_token = std::make_shared<int>(0);
            ++probe.texture_allocations;
            rev.view = rev.texture.CreateView();
            rev.gpu_bytes = static_cast<size_t>(rev.width) * rev.height * 4;
            rev.gpu_revision = rev.revision;
            return;
        }
        // Color renderbuffers have no CPU DATA payload. Dawn initializes new
        // texture storage before a read/load; uploading a full zero image here
        // adds a transfer to every SceneCanvas.render() readback target.
        if (rev.renderbuffer && rev.dimensions == 2 && rev.format == "rgba" &&
            (rev.internal_format.empty() || rev.internal_format == "rgba8") &&
            rev.pixels.empty() && rev.updates.empty() && !rev.base) {
            freeze_texture_allocation(rev);
            wgpu::TextureDescriptor color;
            color.size = {static_cast<uint32_t>(rev.width), static_cast<uint32_t>(rev.height), 1};
            color.format = wgpu::TextureFormat::RGBA8Unorm;
            color.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::TextureBinding |
                          wgpu::TextureUsage::CopySrc | wgpu::TextureUsage::CopyDst;
            rev.texture = device.CreateTexture(&color);
            rev.allocation_token = std::make_shared<int>(0);
            ++probe.texture_allocations;
            rev.view = rev.texture.CreateView();
            rev.gpu_bytes = static_cast<size_t>(rev.width) * rev.height * 4;
            rev.gpu_revision = rev.revision;
            return;
        }
        if (rev.base) {
            if (ticket) ticket->textures.push_back(rev.base);
            upload_texture(*rev.base, encoder, ticket);
            if (!rev.allocation_descriptor) rev.allocation_descriptor = rev.base->allocation_descriptor;
        }
        freeze_texture_allocation(rev);
        // Before the first native upload, the assembled CPU shadow includes
        // both the initial image and any subsequent patches.
        const bool partial = !rev.updates.empty() && (rev.texture || rev.base);
        PreparedTexture partial_prepared;
        vispy::textures::FullUpload full_upload;
        {
            HostTimer timer(probe.texture_conversion_ns);
            if (partial) partial_prepared = prepare_region(*rev.allocation_descriptor, rev.updates.front().data);
            else full_upload = vispy::textures::prepare_full_upload(rev, rev.allocation_descriptor.get());
        }
        const PreparedTexture& prepared = partial ? partial_prepared : full_upload.prepared();
        wgpu::TextureDescriptor td;
        td.dimension = prepared.dimension;
        // The normalized-integer sampling specialization snapshots this
        // allocation contract; adding mip storage requires a new policy.
        td.mipLevelCount = 1;
        td.size = {static_cast<uint32_t>(rev.width), static_cast<uint32_t>(rev.height),
                   static_cast<uint32_t>(rev.depth)};
        td.format = prepared.format;
        td.usage = wgpu::TextureUsage::TextureBinding | wgpu::TextureUsage::CopyDst |
                   wgpu::TextureUsage::CopySrc;
        if (rev.dimensions == 2) td.usage |= wgpu::TextureUsage::RenderAttachment;
        if (!rev.texture || rev.texture.GetFormat() != prepared.format) {
            rev.texture = device.CreateTexture(&td);
            rev.allocation_token = std::make_shared<int>(0);
            ++probe.texture_allocations;
            rev.view = rev.texture.CreateView();
        }
        // Validate sampling against stable storage rather than DATA's dtype.
        if (!rev.sampler) refresh_sampler(rev);
        rev.gpu_bytes = partial ? prepared.bytes.size() : full_upload.size();
        if (partial) {
            if (!encoder || !ticket) throw std::runtime_error("partial texture upload requires an ordered encoder");
            rev.gpu_bytes = static_cast<size_t>(rev.width) * rev.height * rev.depth * prepared.texel_size;
            uint64_t copied_bytes = 0;
            uint64_t upload_bytes = 0;
            if (rev.base && rev.base->texture.Get() != rev.texture.Get()) {
                wgpu::TexelCopyTextureInfo source, destination;
                source.texture = rev.base->texture;
                destination.texture = rev.texture;
                wgpu::Extent3D size{static_cast<uint32_t>(rev.width), static_cast<uint32_t>(rev.height),
                                   static_cast<uint32_t>(rev.depth)};
                {
                    HostTimer timer(probe.texture_upload_cpu_ns);
                    encoder.CopyTextureToTexture(&source, &destination, &size);
                }
                ticket->textures.push_back(rev.base);
                copied_bytes += rev.gpu_bytes;
            }
            for (const auto& update : rev.updates) {
                HostTimer conversion_timer(probe.texture_conversion_ns);
                auto region = prepare_region(*rev.allocation_descriptor, update.data);
                const auto layout = texture_detail::texture_region_layout(rev.dimensions, update.data.shape, update.offset);
                const uint32_t height = static_cast<uint32_t>(layout.height);
                const uint32_t width = static_cast<uint32_t>(layout.width);
                const uint32_t depth = static_cast<uint32_t>(layout.depth);
                const uint32_t row_bytes = static_cast<uint32_t>(width * region.texel_size);
                const uint32_t bpr = (row_bytes + 255u) & ~255u;
                std::vector<uint8_t> rows(static_cast<size_t>(bpr) * height * depth, 0);
                for (uint32_t z = 0; z < depth; ++z) for (uint32_t y = 0; y < height; ++y) {
                    const size_t row = static_cast<size_t>(z) * height + y;
                    std::memcpy(rows.data() + row * bpr, region.bytes.data() + row * row_bytes, row_bytes);
                }
                conversion_timer.finish();
                auto staging = upload_buffer(rows.data(), rows.size(), wgpu::BufferUsage::CopySrc);
                ticket->transient_buffers.push_back(staging);
                wgpu::TexelCopyBufferInfo source;
                source.buffer = staging;
                source.layout.bytesPerRow = bpr;
                source.layout.rowsPerImage = height;
                wgpu::TexelCopyTextureInfo destination;
                destination.texture = rev.texture;
                destination.origin = {static_cast<uint32_t>(layout.x), static_cast<uint32_t>(layout.y),
                                      static_cast<uint32_t>(layout.z)};
                wgpu::Extent3D size{width, height, depth};
                {
                    HostTimer timer(probe.texture_upload_cpu_ns);
                    encoder.CopyBufferToTexture(&source, &destination, &size);
                }
                upload_bytes += rows.size();
            }
            ticket->ordered_uploads.push_back({&rev, rev.revision, rev.updates.size(), upload_bytes, copied_bytes});
            return;
        }
        // The engine mutex holds the source revision stable. Dawn captures the
        // bytes synchronously in WriteTexture; no pointer is retained by us.
        HostTimer conversion_timer(probe.texture_conversion_ns);
        vispy::textures::with_upload_rows(full_upload,
            [&](const PreparedTexture&, const uint8_t* bytes, size_t submitted_bytes, uint32_t pitch, int height) {
                conversion_timer.finish();
                wgpu::TexelCopyTextureInfo dest;
                dest.texture = rev.texture;
                dest.aspect = wgpu::TextureAspect::All;
                wgpu::TexelCopyBufferLayout layout;
                layout.bytesPerRow = pitch;
                layout.rowsPerImage = static_cast<uint32_t>(height);
                wgpu::Extent3D extent{static_cast<uint32_t>(rev.width), static_cast<uint32_t>(rev.height),
                                     static_cast<uint32_t>(rev.depth)};
                {
                    HostTimer timer(probe.texture_upload_cpu_ns);
                    queue.WriteTexture(&dest, bytes, submitted_bytes, &layout, &extent);
                }
                probe.texture_uploads++;
                probe.copy_bytes += submitted_bytes;
                probe.texture_upload_bytes += submitted_bytes;
            });
        rev.updates.clear();
        rev.base.reset();
        rev.gpu_revision = rev.revision;
    }

    void commit_texture_uploads(Ticket& ticket) {
        for (const auto& upload : ticket.ordered_uploads) {
            upload.revision->updates.clear();
            upload.revision->base.reset();
            upload.revision->gpu_revision = upload.uploaded_revision;
            probe.texture_uploads += upload.count;
            probe.texture_upload_bytes += upload.bytes;
            probe.copy_bytes += upload.copied_bytes;
        }
        ticket.ordered_uploads.clear();
    }

    std::shared_ptr<TextureRev> placeholder_texture(const NormSampler& sampler) {
        const int dimensions = sampler.dim == "1d" ? 1 : sampler.dim == "3d" ? 3 : 2;
        auto& texture = dummy_textures[dimensions - 1];
        if (texture && texture->texture) return texture;
        texture = std::make_shared<TextureRev>();
        texture->dimensions = dimensions;
        texture->width = texture->height = texture->depth = 1;
        texture->channels = 4;
        texture->dtype = "u8";
        texture->pixels = {255, 255, 255, 255};
        upload_texture(*texture);
        return texture;
    }

    wgpu::Texture encode_sample_zero_capture(const wgpu::Texture& source,
                                             const wgpu::CommandEncoder& encoder, Ticket& ticket,
                                             bool stencil) {
        if (source.GetSampleCount() != 4)
            throw std::runtime_error("sample-zero depth/stencil capture requires four samples");
        const size_t slot = stencil ? 1 : 0;
        const auto output_format = stencil ? wgpu::TextureFormat::R8Uint : wgpu::TextureFormat::R32Float;
        auto& retained_pipeline = sample_zero_capture_pipelines[slot];
        auto& retained_layout = sample_zero_capture_layouts[slot];
        if (!retained_pipeline) {
            // Capture an existing sample, never average depths/stencil indices.
            // Samplezero is this backend's explicit default-framebuffer policy;
            // it need not match another driver's chosen centermost sample.
            const std::string shader = std::string("@group(0) @binding(0) var source: ") +
                (stencil ? "texture_multisampled_2d<u32>;" : "texture_depth_multisampled_2d;") + R"(
@vertex fn capture_vertex(@builtin(vertex_index) index: u32) -> @builtin(position) vec4f {
    let position = vec2f(f32((index << 1u) & 2u), f32(index & 2u));
    return vec4f(position * 2.0 - 1.0, 0.0, 1.0);
}
@fragment fn capture_fragment(@builtin(position) position: vec4f) -> @location(0) )" +
                (stencil ? "u32 { return textureLoad(source, vec2i(position.xy), 0).r; }" :
                           "f32 { return textureLoad(source, vec2i(position.xy), 0); }");
            const std::string role = stencil ? "stencil sample-zero capture" : "depth sample-zero capture";
            const auto generation = device_generation;
            PipelineCreationScopes scopes(instance, device, role, current_backend_shader_log, generation);
            scopes.begin();
            wgpu::ShaderSourceWGSL wgsl;
            wgsl.code = shader.c_str();
            wgpu::ShaderModuleDescriptor module_descriptor;
            module_descriptor.nextInChain = &wgsl;
            module_descriptor.label = role.c_str();
            auto module = device.CreateShaderModule(&module_descriptor);
            ++probe.shader_module_creations;
            wgpu::BindGroupLayoutEntry binding;
            binding.binding = 0;
            binding.visibility = wgpu::ShaderStage::Fragment;
            binding.texture.sampleType = stencil ? wgpu::TextureSampleType::Uint : wgpu::TextureSampleType::Depth;
            binding.texture.viewDimension = wgpu::TextureViewDimension::e2D;
            binding.texture.multisampled = true;
            wgpu::BindGroupLayoutDescriptor bind_descriptor;
            bind_descriptor.entryCount = 1;
            bind_descriptor.entries = &binding;
            auto binding_layout = device.CreateBindGroupLayout(&bind_descriptor);
            wgpu::PipelineLayoutDescriptor layout_descriptor;
            layout_descriptor.bindGroupLayoutCount = 1;
            layout_descriptor.bindGroupLayouts = &binding_layout;
            auto layout = device.CreatePipelineLayout(&layout_descriptor);
            wgpu::ColorTargetState color;
            color.format = output_format;
            wgpu::FragmentState fragment;
            fragment.module = module;
            fragment.entryPoint = "capture_fragment";
            fragment.targetCount = 1;
            fragment.targets = &color;
            wgpu::RenderPipelineDescriptor pipeline_descriptor;
            pipeline_descriptor.label = role.c_str();
            pipeline_descriptor.layout = layout;
            pipeline_descriptor.vertex.module = module;
            pipeline_descriptor.vertex.entryPoint = "capture_vertex";
            pipeline_descriptor.fragment = &fragment;
            auto pipeline = device.CreateRenderPipeline(&pipeline_descriptor);
            ++probe.render_pipeline_creations;
            const auto error = finish_pipeline_creation(scopes, generation);
            if (!module || !binding_layout || !layout || !pipeline || !error.empty())
                throw std::runtime_error(role + ": " + (error.empty() ? "null resource" : error));
            retained_layout = binding_layout;
            retained_pipeline = pipeline;
        }
        wgpu::TextureDescriptor descriptor;
        descriptor.size = {source.GetWidth(), source.GetHeight(), 1};
        descriptor.format = output_format;
        descriptor.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::CopySrc;
        auto output = device.CreateTexture(&descriptor);
        ++probe.texture_allocations;
        ticket.owned_textures.push_back(output);
        ticket.owned_textures.push_back(source);
        wgpu::TextureViewDescriptor view_descriptor;
        view_descriptor.aspect = stencil ? wgpu::TextureAspect::StencilOnly : wgpu::TextureAspect::DepthOnly;
        wgpu::BindGroupEntry entry;
        entry.binding = 0;
        entry.textureView = source.CreateView(&view_descriptor);
        wgpu::BindGroupDescriptor bind_descriptor;
        bind_descriptor.layout = retained_layout;
        bind_descriptor.entryCount = 1;
        bind_descriptor.entries = &entry;
        auto group = device.CreateBindGroup(&bind_descriptor);
        ++probe.bind_group_creations;
        wgpu::RenderPassColorAttachment color;
        color.view = output.CreateView();
        color.loadOp = wgpu::LoadOp::Clear;
        color.storeOp = wgpu::StoreOp::Store;
        wgpu::RenderPassDescriptor pass_descriptor;
        pass_descriptor.colorAttachmentCount = 1;
        pass_descriptor.colorAttachments = &color;
        auto pass = begin_timed_pass(encoder, pass_descriptor, &ticket,
            stencil ? "stencil_sample_zero_capture" : "depth_sample_zero_capture");
        pass.SetPipeline(retained_pipeline);
        pass.SetBindGroup(0, group);
        pass.Draw(3);
        ++probe.native_draw_calls;
        pass.End();
        return output;
    }

    wgpu::Texture encode_depth_capture(const wgpu::Texture& source,
                                      const wgpu::CommandEncoder& encoder, Ticket& ticket) {
        if (source.GetSampleCount() != 1)
            throw std::runtime_error("read_pixels depth: multisample attachments require a depth resolve");
        if (!depth_capture_pipeline) {
            // Depth24Plus has no portable depth-to-buffer representation.
            // TextureLoad exposes its actual normalized depth through R32Float.
            constexpr char shader[] = R"(
@group(0) @binding(0) var source_depth: texture_depth_2d;
@vertex fn capture_vertex(@builtin(vertex_index) index: u32) -> @builtin(position) vec4f {
    let position = vec2f(f32((index << 1u) & 2u), f32(index & 2u));
    return vec4f(position * 2.0 - 1.0, 0.0, 1.0);
}
@fragment fn capture_fragment(@builtin(position) position: vec4f) -> @location(0) f32 {
    return textureLoad(source_depth, vec2i(position.xy), 0);
}
)";
            const auto creation_generation = device_generation;
            PipelineCreationScopes creation(instance, device, "depth capture graphics",
                current_backend_shader_log, creation_generation);
            creation.begin();
            wgpu::ShaderSourceWGSL wgsl;
            wgsl.code = shader;
            wgpu::ShaderModuleDescriptor module_descriptor;
            module_descriptor.nextInChain = &wgsl;
            module_descriptor.label = "depth capture vertex/fragment";
            wgpu::ShaderModule module;
            {
                HostTimer timer(probe.shader_module_creation_ns);
                ++probe.shader_module_creations;
                module = device.CreateShaderModule(&module_descriptor);
            }
            wgpu::BindGroupLayoutEntry entry;
            entry.binding = 0;
            entry.visibility = wgpu::ShaderStage::Fragment;
            entry.texture.sampleType = wgpu::TextureSampleType::Depth;
            entry.texture.viewDimension = wgpu::TextureViewDimension::e2D;
            wgpu::BindGroupLayoutDescriptor bind_descriptor;
            bind_descriptor.entryCount = 1;
            bind_descriptor.entries = &entry;
            auto binding_layout = device.CreateBindGroupLayout(&bind_descriptor);
            wgpu::PipelineLayoutDescriptor layout_descriptor;
            layout_descriptor.bindGroupLayoutCount = 1;
            layout_descriptor.bindGroupLayouts = &binding_layout;
            auto layout = device.CreatePipelineLayout(&layout_descriptor);
            wgpu::ColorTargetState color;
            color.format = wgpu::TextureFormat::R32Float;
            wgpu::FragmentState fragment;
            fragment.module = module;
            fragment.entryPoint = "capture_fragment";
            fragment.targetCount = 1;
            fragment.targets = &color;
            wgpu::RenderPipelineDescriptor pipeline_descriptor;
            pipeline_descriptor.label = "depth capture graphics";
            pipeline_descriptor.layout = layout;
            pipeline_descriptor.vertex.module = module;
            pipeline_descriptor.vertex.entryPoint = "capture_vertex";
            pipeline_descriptor.fragment = &fragment;
            pipeline_descriptor.primitive.topology = wgpu::PrimitiveTopology::TriangleList;
            wgpu::RenderPipeline pipeline;
            std::string error;
            {
                HostTimer timer(probe.pipeline_creation_ns);
                ++probe.render_pipeline_creations;
                pipeline = device.CreateRenderPipeline(&pipeline_descriptor);
                error = finish_pipeline_creation(creation, creation_generation);
            }
            if (!module || !binding_layout || !layout || !pipeline || !error.empty())
                throw std::runtime_error("read_pixels depth pipeline: " +
                    (error.empty() ? "null depth capture resource" : error));
            depth_capture_layout = binding_layout;
            depth_capture_pipeline = pipeline;
        }
        wgpu::TextureDescriptor descriptor;
        descriptor.size = {source.GetWidth(), source.GetHeight(), 1};
        descriptor.format = wgpu::TextureFormat::R32Float;
        descriptor.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::CopySrc;
        auto output = device.CreateTexture(&descriptor);
        ++probe.texture_allocations;
        ticket.owned_textures.push_back(output);
        ticket.owned_textures.push_back(source);
        wgpu::TextureViewDescriptor view_descriptor;
        view_descriptor.aspect = wgpu::TextureAspect::DepthOnly;
        auto source_view = source.CreateView(&view_descriptor);
        wgpu::BindGroupEntry entry;
        entry.binding = 0;
        entry.textureView = source_view;
        wgpu::BindGroupDescriptor bind_descriptor;
        bind_descriptor.layout = depth_capture_layout;
        bind_descriptor.entryCount = 1;
        bind_descriptor.entries = &entry;
        auto group = device.CreateBindGroup(&bind_descriptor);
        ++probe.bind_group_creations;
        wgpu::RenderPassColorAttachment color;
        color.view = output.CreateView();
        color.loadOp = wgpu::LoadOp::Clear;
        color.storeOp = wgpu::StoreOp::Store;
        wgpu::RenderPassDescriptor pass_descriptor;
        pass_descriptor.colorAttachmentCount = 1;
        pass_descriptor.colorAttachments = &color;
        auto pass = begin_timed_pass(encoder, pass_descriptor, &ticket, "depth_capture");
        pass.SetPipeline(depth_capture_pipeline);
        pass.SetBindGroup(0, group);
        pass.Draw(3);
        ++probe.native_draw_calls;
        pass.End();
        return output;
    }

    void ensure_present_pipeline() {
        if (present_ready && present_pipeline) return;
        // v_uv.y is 0 at clip-space bottom and 1 at the top. Texture v grows
        // downward, so sampling v_uv places the color target's bottom row
        // (OpenGL's low-Y row, the visual top) at the top of the swapchain.
        const char* vert = R"(#version 450
layout(location = 0) out vec2 v_uv;
void main() {
    vec2 pos = vec2(float((gl_VertexIndex << 1) & 2), float(gl_VertexIndex & 2));
    v_uv = pos * 0.5;
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
}
)";
        const char* frag = R"(#version 450
layout(set = 0, binding = 0) uniform texture2D u_src;
layout(set = 0, binding = 1) uniform sampler u_samp;
layout(location = 0) out vec4 o_color;
void main() {
    vec2 size = vec2(textureSize(sampler2D(u_src, u_samp), 0));
    vec2 uv = gl_FragCoord.xy / size;
    uv.y = 1.0 - uv.y;
    o_color = texture(sampler2D(u_src, u_samp), uv);
}
)";
        const auto compiler_start = monotonic_ns();
        auto spv = compile_vulkan_glsl(vert, frag);
        probe.shader_cpu_build_ns += monotonic_ns() - compiler_start;
        probe.shader_parse_ns += spv.parse_ns;
        probe.shader_link_ns += spv.link_ns;
        probe.shader_spirv_ns += spv.spirv_ns;
        probe.shader_parse_calls += spv.parse_calls;
        probe.shader_link_calls += spv.link_calls;
        probe.shader_spirv_stages += spv.spirv_stages;
        if (!spv.ok) throw std::runtime_error("presentation GLSL compilation: " + spv.log);
        const auto prefix = "presentation-" + hex64(fnv1a(std::string(vert) + frag));
        dump_shader_pair(prefix, vert, frag, spv.vertex.words, spv.fragment.words);
        const auto creation_generation = device_generation;
        PipelineCreationScopes creation(instance, device, prefix + " graphics",
            current_backend_shader_log, creation_generation);
        creation.begin();
        auto vert_module = make_spirv_module(spv.vertex.words, SpirvDerivativeMode::AllowNonUniform,
            "presentation vertex/main");
        auto frag_module = make_spirv_module(spv.fragment.words, SpirvDerivativeMode::AllowNonUniform,
            "presentation fragment/main");
        wgpu::BindGroupLayoutEntry entries[2];
        entries[0].binding = 0;
        entries[0].visibility = wgpu::ShaderStage::Fragment;
        entries[0].texture.sampleType = wgpu::TextureSampleType::Float;
        entries[0].texture.viewDimension = wgpu::TextureViewDimension::e2D;
        entries[1].binding = 1;
        entries[1].visibility = wgpu::ShaderStage::Fragment;
        entries[1].sampler.type = wgpu::SamplerBindingType::Filtering;
        wgpu::BindGroupLayoutDescriptor bgl;
        bgl.entryCount = 2;
        bgl.entries = entries;
        bgl.label = "presentation bindings";
        auto candidate_layout = device.CreateBindGroupLayout(&bgl);
        wgpu::PipelineLayoutDescriptor pld;
        pld.label = "presentation layout";
        pld.bindGroupLayoutCount = 1;
        pld.bindGroupLayouts = &candidate_layout;
        auto layout = device.CreatePipelineLayout(&pld);
        wgpu::SamplerDescriptor sd;
        sd.minFilter = wgpu::FilterMode::Nearest;
        sd.magFilter = wgpu::FilterMode::Nearest;
        auto candidate_sampler = device.CreateSampler(&sd);
        wgpu::VertexState vs;
        vs.module = vert_module;
        vs.entryPoint = "main";
        vs.bufferCount = 0;
        wgpu::ColorTargetState color;
        color.format = wgpu::TextureFormat::BGRA8Unorm;
        wgpu::FragmentState fs;
        fs.module = frag_module;
        fs.entryPoint = "main";
        fs.targetCount = 1;
        fs.targets = &color;
        wgpu::RenderPipelineDescriptor rpd;
        rpd.label = "presentation blit graphics";
        rpd.layout = layout;
        rpd.vertex = vs;
        rpd.fragment = &fs;
        rpd.primitive.topology = wgpu::PrimitiveTopology::TriangleList;
        wgpu::RenderPipeline candidate_pipeline;
        std::string error;
        {
            HostTimer timer(probe.pipeline_creation_ns);
            ++probe.render_pipeline_creations;
            candidate_pipeline = device.CreateRenderPipeline(&rpd);
            error = finish_pipeline_creation(creation, creation_generation);
        }
        if (!vert_module || !frag_module || !candidate_layout || !layout || !candidate_sampler ||
                !candidate_pipeline || !error.empty())
            throw std::runtime_error(prefix + ": " + (error.empty() ? "null presentation resource" : error));
        present_layout = std::move(candidate_layout);
        present_sampler = std::move(candidate_sampler);
        present_pipeline = std::move(candidate_pipeline);
        present_ready = true;
    }

    void blit_present(wgpu::CommandEncoder encoder, Canvas& target, wgpu::TextureView dest,
                      Ticket* ticket = nullptr, const char* kind = "presentation") {
        ensure_present_pipeline();
        if (!present_ready || !target.color_view || !dest)
            throw std::runtime_error("presentation conversion: pipeline/source/destination is unavailable");
        wgpu::RenderPassColorAttachment color;
        color.view = dest;
        color.loadOp = wgpu::LoadOp::Clear;
        color.storeOp = wgpu::StoreOp::Store;
        color.clearValue = {0, 0, 0, 1};
        wgpu::RenderPassDescriptor rp;
        rp.colorAttachmentCount = 1;
        rp.colorAttachments = &color;
        auto pass = begin_timed_pass(encoder, rp, ticket, kind);
        pass.SetPipeline(present_pipeline);
        wgpu::BindGroupEntry entries[2];
        entries[0].binding = 0;
        entries[0].textureView = target.color_view;
        entries[1].binding = 1;
        entries[1].sampler = present_sampler;
        wgpu::BindGroupDescriptor bgd;
        bgd.layout = present_layout;
        bgd.entryCount = 2;
        bgd.entries = entries;
        if (!target.present_group || target.present_group_generation != device_generation ||
                target.present_group_view != target.color_view.Get() ||
                target.present_group_layout != present_layout.Get() ||
                target.present_group_sampler != present_sampler.Get()) {
            target.present_group = nullptr;
            device.PushErrorScope(wgpu::ErrorFilter::Validation);
            auto group = device.CreateBindGroup(&bgd);
            ++probe.bind_group_creations;
            const auto error = pop_validation();
            if (!group || !error.empty())
                throw std::runtime_error("presentation conversion: bind group validation failed: " + error);
            target.present_group = std::move(group);
            target.present_group_generation = device_generation;
            target.present_group_view = target.color_view.Get();
            target.present_group_layout = present_layout.Get();
            target.present_group_sampler = present_sampler.Get();
        }
        auto group = target.present_group;
        if (ticket) {
            ticket->bind_groups.push_back(group);
            ticket->owned_textures.push_back(target.color);
        }
        pass.SetBindGroup(0, group);
        pass.Draw(3, 1, 0, 0);
        ++probe.native_draw_calls;
        pass.End();
        probe.presentation_passes++;
        log("presentation flip format=bgra8unorm");
    }

    void configure_surface(Canvas& target) {
        if (!target.surface || target.width <= 0 || target.height <= 0) return;
        if (target.surface_configured && target.surface_w == target.width && target.surface_h == target.height) return;
        if (target.surface_owner) target.surface_owner->update(target.width, target.height, target.surface_scale);
        wgpu::SurfaceConfiguration config;
        config.device = device;
        config.format = wgpu::TextureFormat::BGRA8Unorm;
        config.usage = wgpu::TextureUsage::RenderAttachment;
        config.width = static_cast<uint32_t>(target.width);
        config.height = static_cast<uint32_t>(target.height);
        config.alphaMode = wgpu::CompositeAlphaMode::Auto;
        wgpu::SurfaceCapabilities capabilities;
        if (target.surface.GetCapabilities(adapter, &capabilities) != wgpu::Status::Success)
            throw std::runtime_error("surface: cannot query presentation capabilities");
        auto supported = [&](wgpu::PresentMode mode) {
            return std::find(capabilities.presentModes,
                capabilities.presentModes + capabilities.presentModeCount, mode) !=
                capabilities.presentModes + capabilities.presentModeCount;
        };
        config.presentMode = wgpu::PresentMode::Fifo;
        if (!target.vsync) {
            if (supported(wgpu::PresentMode::Immediate)) config.presentMode = wgpu::PresentMode::Immediate;
            else if (supported(wgpu::PresentMode::Mailbox)) config.presentMode = wgpu::PresentMode::Mailbox;
        }
        if (!supported(config.presentMode))
            throw std::runtime_error("surface: no supported presentation mode for canvas");
        target.present_mode = config.presentMode;
        target.surface.Configure(&config);
        target.surface_configured = true;
        target.surface_w = target.width;
        target.surface_h = target.height;
        log("hwnd surface configured " + std::to_string(target.width) + "x" + std::to_string(target.height));
        log("surface present mode=" + std::string(config.presentMode == wgpu::PresentMode::Immediate ?
            "immediate" : config.presentMode == wgpu::PresentMode::Mailbox ? "mailbox" : "fifo"));
    }

    void wait_queue() {
        auto result = std::make_shared<AsyncResult>();
        auto future = queue.OnSubmittedWorkDone(wgpu::CallbackMode::WaitAnyOnly,
            [result](wgpu::QueueWorkDoneStatus status, wgpu::StringView message) {
                result->ok = status == wgpu::QueueWorkDoneStatus::Success;
                result->error = view_to_string(message);
                result->done.store(true);
            });
        ++probe.completion_waits;
        if (!wait_result(future, result)) throw std::runtime_error(last_error);
        poll();
    }

    // The color target was already submitted. Configure and present the HWND
    // surface if it was attached or resized after that submit.
    void unavailable_paint_surface(const std::shared_ptr<FrameMark::Queries>& owner,
                                   const Canvas& target, const std::string& reason) {
        if (owner && owner->work.surface_unavailable(bool(target.surface) || bool(target.surface_owner), reason))
            owner->fail(vispy::timing::Status::SubmissionError, reason);
    }

    void present_current_swapchain(Canvas& target, const std::shared_ptr<FrameMark::Queries>& owner) {
        HostTimer submit_timer(probe.native_submit_ns);
        if (!target.surface || !target.color_view || target.width <= 0 || target.height <= 0) {
            unavailable_paint_surface(owner, target, "requested paint surface/source is unavailable");
            return;
        }
        configure_surface(target);
        wgpu::SurfaceTexture current;
        target.surface.GetCurrentTexture(&current);
        if ((current.status != wgpu::SurfaceGetCurrentTextureStatus::SuccessOptimal &&
             current.status != wgpu::SurfaceGetCurrentTextureStatus::SuccessSuboptimal) ||
            !current.texture) {
            log("swapchain unavailable");
            unavailable_paint_surface(owner, target, "requested paint surface texture acquisition is unavailable");
            return;
        }
        auto encoder = device.CreateCommandEncoder();
        ++probe.command_encoders;
        auto ticket = std::make_shared<Ticket>();
        ticket->canvas_id = target.id;
        attach_frame(*ticket, owner, 1);
        blit_present(encoder, target, current.texture.CreateView(), ticket.get(), "surface_conversion");
        log("swapchain present");
        resolve_ticket_queries(encoder, *ticket);
        auto commands = encoder.Finish();
        queue.Submit(1, &commands);
        probe.dawn_queue_submits++;
        probe.application_presents++;
        ticket->owned_textures.push_back(target.color);
        ticket->surface_owners.push_back(target.surface_owner);
        ticket->submit_ns = monotonic_ns();
        track_submission(ticket);
        if (target.surface.Present() != wgpu::Status::Success) {
            target.surface_configured = false;
            freeze_submission_counters(*ticket, submit_timer);
            throw std::runtime_error("surface: presentation failed");
        }
        ticket->presented = true;
        if (ticket->queries) {
            ticket->queries->work.presented();
            ticket->queries->last_present_submission_index = ticket->queries->work.last_present_submission_index;
        }
        target.swapchain_current = true;
        freeze_submission_counters(*ticket, submit_timer);
        if (ticket->queries && ticket->queries->final_requested && target.queued_frames.empty())
            finalize_query_frame(ticket->queries);
    }

    void submit_canvas(Canvas& target, bool present, bool queued_only = false) {
        HostTimer submit_timer(probe.native_submit_ns);
        if (target.width <= 0 || target.height <= 0 || !target.alive) {
            cancel_canvas_frames(target, "cancelled", "zero drawable before frame submission");
            log("skip submit zero drawable");
            return;
        }
        if (!init_device()) throw std::runtime_error("frame submission: device unavailable");
        poll();
        if (!device_ready) throw std::runtime_error("frame submission: device lost before encoding");
        if (!queued_only && (!target.pending.empty() || target.clear_pending || present)) {
            if (target.queued_frames.size() >= frame_slots)
                throw std::runtime_error("frame queue full; process events before recording another submission");
            if (next_queued_frame == std::numeric_limits<uint64_t>::max())
                throw std::overflow_error("frame queue identity exhausted");
            auto mark = target.frame_mark;
            if (mark && mark->queries) mark->queries->work.enqueue(frame_slots);
            try { target.queued_frames.push_back({std::move(target.pending), mark, present,
                                                 next_queued_frame, device_generation}); }
            catch (...) {
                if (mark && mark->queries) mark->queries->work.discard_queued(1);
                throw;
            }
            ++next_queued_frame;
            target.pending.clear();
        }
        target.deferred_present = !target.queued_frames.empty();
        if (tickets.size() >= frame_slots) {
            if (target.deferred_present) ++probe.deferred_frames;
            update_work_peaks();
            return;
        }
        if (target.queued_frames.empty()) return;
        std::optional<NativeLinePool::BatchReservation> line_resources;
        const auto& candidate = target.queued_frames.front().draws;
        if (std::any_of(candidate.begin(), candidate.end(), [](const auto& snap) {
                return bool(snap.line_chunks) || has_line_resources(snap);
            })) {
            try {
                auto reserved = reserve_line_resources(candidate);
                if (!reserved) {
                    // Keep the queued owner and all immutable draws intact.
                    // The regular event loop retries after real retirement.
                    ++probe.deferred_frames;
                    update_work_peaks();
                    return;
                }
                line_resources.emplace(std::move(reserved.reservation));
            } catch (const std::exception& error) {
                const auto failed = target.queued_frames.front().mark;
                fail_line_snapshots(candidate, "encoding_error", error.what());
                if (failed && failed->queries) cancel_frame(failed->queries, "failed", error.what());
                else {
                    target.queued_frames.pop_front();
                    target.deferred_present = !target.queued_frames.empty();
                }
                throw;
            }
        }
        auto batch = std::move(target.queued_frames.front());
        target.queued_frames.pop_front();
        target.deferred_present = !target.queued_frames.empty();
        present = batch.present;
        auto owner = batch.mark ? batch.mark->queries : nullptr;
        if (present && owner) owner->work.expect_surface(bool(target.surface) || bool(target.surface_owner));
        if (owner) owner->work.begin_batch();
        struct BatchGuard {
            std::shared_ptr<FrameMark::Queries> owner;
            const std::vector<DrawSnap>& draws;
            ~BatchGuard() {
                // This owner exists before surface/target creation or a
                // Ticket. Successful submission clears draws first.
                Engine::fail_line_snapshots(draws, "encoding_error", "endpoint batch ended before submission");
                if (owner) owner->work.finish_batch();
            }
        } guard{owner, batch.draws};
        flatten_line_snapshots(batch.draws);
        auto& draws = batch.draws;
        update_work_peaks();
        ensure_native_surface(target);
        ensure_target(target);
        if (draws.empty() && !target.clear_pending) {
            submit_timer.finish();
            if (present && !target.surface)
                unavailable_paint_surface(owner, target, "requested paint surface is detached or expired");
            if (present && target.surface && !target.swapchain_current) present_current_swapchain(target, owner);
            return;
        }
        if (draws.empty() && target.clear_pending) {
            DrawSnap clear_only;
            clear_only.origin = vispy::render::SnapshotOrigin::Clear;
            clear_only.clear = true;
            std::memcpy(clear_only.clear_color, target.clear_color, sizeof(clear_only.clear_color));
            clear_only.canvas_id = 0;
            draws.push_back(clear_only);
            update_work_peaks();
        }
        target.swapchain_current = false;
        wgpu::CommandEncoder encoder = device.CreateCommandEncoder();
        ++probe.command_encoders;
        auto ticket = std::make_shared<Ticket>();
        ticket->canvas_id = target.id;
        ticket->line_resources = std::move(line_resources);
        uint64_t endpoint_passes = 0;
        for (const auto& snap : draws) if (snap.line_work) {
            ticket->line_work.push_back(snap.line_work);
            if (snap.line_work->capture && std::find(ticket->line_captures.begin(),
                    ticket->line_captures.end(), snap.line_work->capture) == ticket->line_captures.end())
                ticket->line_captures.push_back(snap.line_work->capture);
            if (snap.line_work->dispatch.workgroups_x) ++endpoint_passes;
        }
        uint64_t depth_upload_passes = 0;
        std::unordered_set<TextureRev*> depth_upload_revisions;
        for (const auto& snap : draws)
            depth_upload_passes += pending_depth_upload_passes(snap.depth_attachment, depth_upload_revisions);
        // Collect asynchronous encoding validation for endpoint and depth-upload
        // work without waiting between preceding FBO writes and later passes.
        struct EncodingScope {
            wgpu::Device device;
            std::shared_ptr<Ticket> ticket;
            bool active = false;
            EncodingScope(wgpu::Device selected, std::shared_ptr<Ticket> owner, bool enabled)
                : device(selected), ticket(std::move(owner)), active(enabled) {
                if (active) {
                    ticket->encoding_validation = std::make_shared<AsyncResult>();
                    device.PushErrorScope(wgpu::ErrorFilter::Validation);
                }
            }
            void close() {
                if (!active) return;
                active = false;
                auto state = ticket->encoding_validation;
                ticket->encoding_validation_future = device.PopErrorScope(wgpu::CallbackMode::AllowProcessEvents,
                    [state](wgpu::PopErrorScopeStatus status, wgpu::ErrorType type, wgpu::StringView message) {
                        state->ok = status == wgpu::PopErrorScopeStatus::Success && type == wgpu::ErrorType::NoError;
                        state->error = view_to_string(message);
                        state->done.store(true);
                    });
            }
            ~EncodingScope() { close(); }
        } encoding_scope(device, ticket, endpoint_passes != 0 || depth_upload_passes != 0);
        attach_frame(*ticket, owner, draws.size() + endpoint_passes + depth_upload_passes + (present ? 2 : 0));
        size_t line_resource_index = 0;
        for (auto& snap : draws) {
            NativeLineSlot* line_slot = nullptr;
            if (has_line_resources(snap))
                line_slot = &configure_line_slot(ticket->line_resources->at(line_resource_index++), snap);
            if (snap.artifact) ticket->artifacts.push_back(snap.artifact);
            if (snap.line_inputs) ticket->line_inputs.push_back(snap.line_inputs);
            if (snap.target_texture) ticket->owned_textures.push_back(snap.target_texture);
            if (snap.resolve_texture) ticket->owned_textures.push_back(snap.resolve_texture);
            if (snap.depth_texture) ticket->owned_textures.push_back(snap.depth_texture);
            wgpu::TextureView view = snap.target_view;
            if (snap.attachment) {
                upload_texture(*snap.attachment, encoder, ticket.get());
                view = snap.attachment->view;
                ticket->textures.push_back(snap.attachment);
            }
            if (snap.depth_attachment) {
                upload_texture(*snap.depth_attachment, encoder, ticket.get());
                snap.depth_view = snap.depth_attachment->view;
                ticket->textures.push_back(snap.depth_attachment);
            }
            // Copies must precede this pass, but follow earlier recorded
            // draws that may have rendered into the sampled allocation.
            for (const auto& texture : snap.textures)
                upload_texture(*texture, encoder, ticket.get());
            encode_line_work(snap.line_work, encoder, *ticket, line_slot);
            if (snap.line_work && snap.line_work->chunk) {
                const auto& chunk = *snap.line_work->chunk;
                if (!line_slot || chunk.number >= line_resource_index)
                    throw std::runtime_error("lines: chunk has no ordered output lease");
                const size_t first_slot = line_resource_index - 1 - static_cast<size_t>(chunk.number);
                const uint64_t row_bytes = snap.line_work->evaluator->output_row_bytes;
                auto carry = [&](uint64_t source_chunk, uint32_t source_row, uint64_t target_row) {
                    if (source_chunk >= chunk.number)
                        throw std::runtime_error("lines: endpoint carry must read an earlier chunk");
                    const auto& source = ticket->line_resources->at(first_slot + static_cast<size_t>(source_chunk)).inspect_payload();
                    if (!source.output || (uint64_t(source_row) + 1) * row_bytes > source.output.GetSize() ||
                        (target_row + 1) * row_bytes > line_slot->output.GetSize())
                        throw std::runtime_error("lines: endpoint carry exceeds a reserved output");
                    encoder.CopyBufferToBuffer(source.output, uint64_t(source_row) * row_bytes,
                        line_slot->output, target_row * row_bytes, row_bytes);
                };
                if (chunk.previous) carry(chunk.previous_chunk, chunk.previous_source_row, chunk.new_rows);
                if (chunk.closing) carry(chunk.head_chunk, chunk.head_source_row, chunk.new_rows + uint64_t(chunk.previous));
            }
            wgpu::RenderPassColorAttachment color;
            color.view = view;
            color.resolveTarget = snap.resolve_view;
            color.loadOp = snap.clear ? wgpu::LoadOp::Clear : wgpu::LoadOp::Load;
            if (snap.fbo != 0) {
                log(std::string("pass fbo=") + std::to_string(snap.fbo) + " clear=" + (snap.clear ? "1" : "0"));
            }
            color.storeOp = wgpu::StoreOp::Store;
            color.clearValue = {snap.clear_color[0], snap.clear_color[1], snap.clear_color[2], snap.clear_color[3]};
            wgpu::RenderPassDescriptor rp;
            rp.colorAttachmentCount = 1;
            rp.colorAttachments = &color;
            wgpu::RenderPassDepthStencilAttachment depth;
            if (snap.depth_view) {
                depth.view = snap.depth_view;
                depth.depthLoadOp = snap.clear_depth ? wgpu::LoadOp::Clear : wgpu::LoadOp::Load;
                depth.depthStoreOp = wgpu::StoreOp::Store;
                depth.depthClearValue = static_cast<float>(snap.state.clear_depth);
                const bool has_stencil = !snap.depth_attachment || snap.depth_attachment->format != "depth_component";
                if (has_stencil) {
                    depth.stencilLoadOp = snap.clear_stencil ? wgpu::LoadOp::Clear : wgpu::LoadOp::Load;
                    depth.stencilStoreOp = wgpu::StoreOp::Store;
                    depth.stencilClearValue = snap.state.clear_stencil;
                }
                rp.depthStencilAttachment = &depth;
            }
            auto pass = begin_timed_pass(encoder, rp, ticket.get(),
                vispy::render::pass_kind(snap.origin, snap.fbo != 0));
            if (snap.artifact && snap.count > 0 && snap.instances > 0) {
                if (!draw_render_ready(snap, device_generation))
                    throw std::runtime_error("DRAW render state is stale or unprepared for the selected route");
                const bool consumer_render = snap.line_work && snap.line_work->consumer;
                const auto& render_samplers = consumer_render ? snap.line_work->consumer->samplers :
                                                                snap.artifact->portable->samplers;
                const auto& render_layout = consumer_render ? snap.line_work->consumer_device->bind_layout :
                                                               snap.artifact->bind_layout;
                const int vw = snap.viewport[2] < 0 ? snap.target_width : snap.viewport[2];
                const int vh = snap.viewport[3] < 0 ? snap.target_height : snap.viewport[3];
                const double viewport_y = double(snap.viewport[1]);
                pass.SetViewport(static_cast<float>(snap.viewport[0]), static_cast<float>(viewport_y),
                                 static_cast<float>(vw), static_cast<float>(vh),
                                 snap.state.depth_range[0], snap.state.depth_range[1]);
                const auto scissor = effective_draw_scissor(snap.state, snap.logical_topology,
                    snap.origin == vispy::render::SnapshotOrigin::UserDraw, snap.scissor_enabled,
                    {snap.scissor[0], snap.scissor[1], snap.scissor[2], snap.scissor[3]},
                    snap.target_width, snap.target_height);
                // Set every draw, including full-target restoration after a
                // zero cull rectangle or an explicitly clipped predecessor.
                pass.SetScissorRect(scissor[0], scissor[1], scissor[2], scissor[3]);
                const auto stencil_route = stencil_face_route(snap.state, snap.logical_topology,
                    snap.origin == vispy::render::SnapshotOrigin::UserDraw);
                if ((stencil_route == StencilFaceRoute::OrderedTwoFaces) != snap.stencil_face_split)
                    throw std::runtime_error("DRAW stencil faces: captured route differs from prepared owner");
                const auto face0 = stencil_face_state(snap.state, stencil_route);
                const auto face1 = snap.stencil_face_split ? stencil_face_state(snap.state, stencil_route, 1) : face0;
                const auto pipeline0 = draw_pipeline(snap, &face0);
                const auto pipeline1 = snap.stencil_face_split ? draw_pipeline(snap, &face1) : pipeline0;
                pass.SetPipeline(pipeline0);
                const auto blend_constant = blend_constant_for_state(snap.state);
                pass.SetBlendConstant(&blend_constant);
                pass.SetStencilReference(face0.stencil_front.reference);
                std::vector<wgpu::BindGroupEntry> entries;
                std::vector<std::shared_ptr<BufferRev>> group_buffers;
                wgpu::Buffer ubo;
                if (consumer_render || (!snap.artifact->portable->uniforms.empty() && snap.artifact->portable->uniform_stage_mask)) {
                    if (line_slot) {
                        ubo = line_slot->render_uniforms;
                        write_line_uniforms(ubo, line_slot->control->render_shadow, snap.uniforms);
                    } else {
                        ubo = upload_buffer(snap.uniforms.data(), snap.uniforms.size(), wgpu::BufferUsage::Uniform);
                        ticket->transient_buffers.push_back(ubo);
                        probe.uniform_upload_bytes += snap.uniforms.size();
                    }
                    wgpu::BindGroupEntry entry;
                    entry.binding = 0;
                    entry.buffer = ubo;
                    entry.size = consumer_render ? snap.line_work->consumer->uniform_bytes : snap.artifact->portable->uniform_bytes;
                    entries.push_back(entry);
                }
                if (consumer_render) {
                    if (!line_slot || !line_slot->output || snap.line_work->consumer_draw.endpoint_bytes > line_slot->output.GetSize())
                        throw std::runtime_error("lines: render rows have no matching endpoint lease");
                    wgpu::BindGroupEntry entry;
                    entry.binding = snap.line_work->consumer->output_binding;
                    entry.buffer = line_slot->output;
                    entry.size = snap.line_work->consumer_draw.endpoint_bytes;
                    entries.push_back(entry);
                }
                for (size_t s = 0; s < snap.textures.size() && s < render_samplers.size(); ++s) {
                    wgpu::BindGroupEntry tex;
                    tex.binding = render_samplers[s].texture_binding;
                    tex.textureView = snap.textures[s]->view;
                    if (render_samplers[s].texture_stage_mask) entries.push_back(tex);
                    wgpu::BindGroupEntry samp;
                    samp.binding = render_samplers[s].sampler_binding;
                    samp.sampler = snap.textures[s]->sampler;
                    if (render_samplers[s].sampler_stage_mask) entries.push_back(samp);
                    ticket->textures.push_back(snap.textures[s]);
                }
                const auto common_entry_count = entries.size();
                uint64_t physical_draws = 0;
                auto encode_inputs = [&](const auto& vertex_at,
                        const std::shared_ptr<BufferRev>& index, const std::string& index_type,
                        const std::shared_ptr<BufferRev>& identity,
                        const std::shared_ptr<BufferRev>& origin,
                        const std::shared_ptr<BufferRev>& point_identity,
                        uint32_t count, uint32_t instances, uint32_t first, uint32_t first_instance, uint32_t first_index = 0) {
                    entries.resize(common_entry_count);
                    group_buffers.clear();
                    auto bind_buffer = [&](const std::shared_ptr<BufferRev>& revision,
                                           uint32_t binding, wgpu::BufferUsage usage) {
                        if (!binding) return;
                        if (!revision) throw std::runtime_error("DRAW batches: missing reflected identity resource");
                        upload_revision(*revision, usage);
                        wgpu::BindGroupEntry entry;
                        entry.binding = binding; entry.buffer = revision->gpu; entry.size = revision->cpu.size();
                        entries.push_back(entry);
                        ticket->buffers.push_back(revision);
                        group_buffers.push_back(revision);
                    };
                    // The point route retains its original identity binding.
                    if (point_identity)
                        bind_buffer(point_identity, snap.artifact->portable->point_identity_binding,
                                    wgpu::BufferUsage::Storage);
                    bind_buffer(identity, snap.artifact->portable->vertex_identity_binding, wgpu::BufferUsage::Storage);
                    bind_buffer(origin, snap.artifact->portable->batch_instance_binding, wgpu::BufferUsage::Uniform);
                    if (!entries.empty()) {
                        wgpu::BindGroup group;
                        if (line_slot) {
                            group = cached_line_group(line_slot->control->render, snap.artifact, false,
                                render_layout, entries, group_buffers, snap.textures,
                                consumer_render ? snap.line_work->consumer_device : std::shared_ptr<LineConsumerDevice>{});
                        } else {
                            wgpu::BindGroupDescriptor bgd;
                            bgd.layout = render_layout; bgd.entryCount = entries.size(); bgd.entries = entries.data();
                            group = device.CreateBindGroup(&bgd);
                            ++probe.bind_group_creations;
                        }
                        ticket->bind_groups.push_back(group);
                        pass.SetBindGroup(0, group);
                    }
                    for (size_t v = 0; v < snap.vertex_streams.size(); ++v) {
                        const auto& revision = vertex_at(v);
                        if (!revision) throw std::runtime_error("DRAW batches: missing physical vertex stream");
                        upload_revision(*revision, wgpu::BufferUsage::Vertex);
                        pass.SetVertexBuffer(static_cast<uint32_t>(v), revision->gpu, snap.vertex_streams[v].offset);
                        ticket->buffers.push_back(revision);
                    }
                    if (index) {
                        upload_revision(*index, wgpu::BufferUsage::Index);
                        pass.SetIndexBuffer(index->gpu, index_type == "unsigned_int" ?
                            wgpu::IndexFormat::Uint32 : wgpu::IndexFormat::Uint16);
                        pass.DrawIndexed(count, instances, first_index, 0, first_instance);
                        ticket->buffers.push_back(index);
                    } else pass.Draw(count, instances, first, first_instance);
                    ++physical_draws;
                };
                if (snap.batch_inputs) {
                    const auto& data = *snap.batch_inputs->batch_data;
                    // Retain the complete immutable CPU/native graph through
                    // real Ticket retirement, including currently unbound leaves.
                    ticket->buffers.push_back(snap.batch_inputs);
                    auto encode_batch = [&](const vispy::inputs::batches::DrawRef& ref, uint32_t first, uint32_t count) {
                        const auto& geometry = data.geometry.at(ref.geometry);
                        const auto& block = data.blocks.at(static_cast<size_t>(ref.instance_block));
                        const auto vertex_at = [&](size_t slot) -> const std::shared_ptr<BufferRev>& {
                            return data.plan.layout.streams[slot].instance ? block.instances.at(slot) : geometry.vertices.at(slot);
                        };
                        // firstInstance selects a row within the immutable block;
                        // its UBO supplies block.first to the user's original ID.
                        encode_inputs(vertex_at, geometry.index, snap.index_type, geometry.identity, block.origin, {},
                            count, static_cast<uint32_t>(ref.instance_count), first, static_cast<uint32_t>(ref.row_offset), first);
                    };
                    if (snap.stencil_face_split) {
                        vispy::inputs::batches::for_each_stencil_draw(data.plan, [&](const vispy::inputs::batches::StencilDrawRef& ref) {
                            pass.SetPipeline(ref.face ? pipeline1 : pipeline0);
                            pass.SetStencilReference((ref.face ? face1 : face0).stencil_front.reference);
                            encode_batch(ref.draw, ref.first, ref.count);
                        });
                    } else data.plan.for_each_draw([&](const vispy::inputs::batches::DrawRef& ref) {
                        encode_batch(ref, 0, static_cast<uint32_t>(data.plan.geometry.at(ref.geometry).element_count));
                    });
                    const auto expected = snap.stencil_face_split ? vispy::inputs::batches::stencil_face_draw_count(data.plan) : data.plan.encoded_draws;
                    if (physical_draws != expected)
                        throw std::runtime_error("DRAW batches: encoded draw count differs from admitted implicit plan");
                } else if (snap.point_batch_inputs) {
                    const auto& data = *snap.point_batch_inputs->point_batch_data;
                    ticket->buffers.push_back(snap.point_batch_inputs);
                    for (const auto& draw : data.draws) {
                        const auto vertex_at = [&](size_t slot) -> const std::shared_ptr<BufferRev>& { return draw.users.at(slot); };
                        // Each range owns rebased identity/user buffers. Local
                        // instance zero reads the first row; stored IDs retain
                        // the user's original vertex and global instance.
                        encode_inputs(vertex_at, {}, {}, {}, {}, draw.identity,
                            6, draw.instances, 0, vispy::points::batches::physical_first_instance);
                    }
                    if (physical_draws != data.draws.size())
                        throw std::runtime_error("DRAW point batches: encoded draw count differs from prepared owner");
                } else {
                    const auto vertex_at = [&](size_t slot) -> const std::shared_ptr<BufferRev>& { return snap.vertices.at(slot); };
                    encode_inputs(vertex_at, snap.index, snap.index_type, snap.vertex_identity, {}, snap.point_identity,
                        static_cast<uint32_t>(snap.index ? snap.index_count : snap.count),
                        static_cast<uint32_t>(snap.instances), static_cast<uint32_t>(snap.first), 0);
                }
                log("DRAW snapshots-kept mode=" + snap.mode + " count=" + std::to_string(snap.count));
                if (snap.semantic_draw)
                    vispy::render::count_encoded_draw(snap.origin, probe.draw_calls, probe.native_draw_calls, physical_draws);
                else probe.native_draw_calls += physical_draws;
            }
            pass.End();
        }
        target.present_swapchain = false;
        wgpu::TextureView swap_view;
        if (present && target.surface && target.width > 0 && target.height > 0) {
            configure_surface(target);
            wgpu::SurfaceTexture current;
            target.surface.GetCurrentTexture(&current);
            if ((current.status == wgpu::SurfaceGetCurrentTextureStatus::SuccessOptimal ||
                 current.status == wgpu::SurfaceGetCurrentTextureStatus::SuccessSuboptimal) &&
                current.texture) {
                swap_view = current.texture.CreateView();
                target.present_swapchain = true;
            } else {
                log("swapchain unavailable");
                unavailable_paint_surface(owner, target, "requested paint surface texture acquisition is unavailable");
            }
        } else if (present && !target.surface) {
            unavailable_paint_surface(owner, target, "requested paint surface is detached or expired");
        }
        if (present && target.color_view && target.presented_view) {
            ticket->owned_textures.push_back(target.color);
            ticket->owned_textures.push_back(target.presented);
            blit_present(encoder, target, target.presented_view, ticket.get(), "present_capture");
            if (swap_view) {
                blit_present(encoder, target, swap_view, ticket.get(), "surface_conversion");
                log("swapchain present");
            }
            probe.application_presents++;
        }
        resolve_ticket_queries(encoder, *ticket);
        wgpu::CommandBuffer commands = encoder.Finish();
        encoding_scope.close();
        if (ticket->line_resources) {
            // Allocate the Engine's ownership before submitting. Later query
            // map/receipt errors cannot lose the actual submitted lease.
            tickets.push_back(ticket);
            ticket->submission_owner_retained = true;
        }
        try { queue.Submit(1, &commands); }
        catch (...) {
            if (ticket->submission_owner_retained) {
                tickets.pop_back();
                ticket->submission_owner_retained = false;
            }
            throw;
        }
        if (ticket->line_resources) ticket->line_resources->mark_submitted();
        commit_texture_uploads(*ticket);
        probe.dawn_queue_submits++;
        ticket->submit_ns = monotonic_ns();
        draws.clear();
        target.clear_pending = false;
        track_submission(ticket);
        log("dawn Queue.Submit count=" + std::to_string(probe.dawn_queue_submits));
        if (target.present_swapchain && target.surface) {
            if (target.surface.Present() != wgpu::Status::Success) {
                target.surface_configured = false;
                freeze_submission_counters(*ticket, submit_timer);
                throw std::runtime_error("surface: presentation failed");
            }
            ticket->presented = true;
            if (ticket->queries) {
                ticket->queries->work.presented();
                ticket->queries->last_present_submission_index = ticket->queries->work.last_present_submission_index;
            }
            target.present_swapchain = false;
            target.swapchain_current = true;
        }
        freeze_submission_counters(*ticket, submit_timer);
        if (ticket->queries && ticket->queries->final_requested && target.queued_frames.empty())
            finalize_query_frame(ticket->queries);
    }

    void discard_point_geometry(int buffer_id) {
        for (auto& [program_id, program] : objects) {
            const bool reads_attribute =
                std::any_of(program.attributes.begin(), program.attributes.end(), [&](const auto& named) {
                    return !named.second.constant && named.second.buffer_id == buffer_id;
                });
            const bool reads_buffer = program.point_geometry_index_owner == buffer_id || reads_attribute;
            if (program.input_index_owner == buffer_id || reads_attribute) {
                discard_input_category(program, vispy::inputs::CurrentCategory::LineEndpoint, "line-endpoint:");
                discard_input_category(program, vispy::inputs::CurrentCategory::Batch, "batch:");
                discard_input_category(program, vispy::inputs::CurrentCategory::CompactFit, "compact-fit:");
            }
            if (reads_buffer && program.point_geometry_cache) {
                program.point_geometry_cache->derived.clear();
                program.point_geometry_sources.clear();
            }
            if (program.input_index_owner == buffer_id) {
                discard_input_category(program, vispy::inputs::CurrentCategory::IndexWiden, "index:u8:");
                discard_input_category(program, vispy::inputs::CurrentCategory::Topology, "index:");
                discard_input_category(program, vispy::inputs::CurrentCategory::Selection, "selection:");
                discard_input_category(program, vispy::inputs::CurrentCategory::Bounds, "bounds:");
                discard_input_category(program, vispy::inputs::CurrentCategory::Vertex, "vertex:");
                program.input_index_source.clear();
            }
            for (const auto& [name, binding] : program.attributes) {
                if (binding.constant || binding.buffer_id != buffer_id) continue;
                if (binding.divisor) {
                    discard_input_category(program, vispy::inputs::CurrentCategory::Instance, "instance:");
                    program.input_instance_sources.clear();
                } else {
                    discard_input_category(program, vispy::inputs::CurrentCategory::Vertex, "vertex:");
                    program.input_vertex_sources.clear();
                }
            }
        }
    }

    void update_descriptor_accounting() {
        auto& eng = *this;
        prune_line_bindings();
        std::unordered_set<WGPUBuffer> buffers;
        std::unordered_set<WGPUTexture> textures;
        std::unordered_set<const BufferRev*> buffer_revisions;
        eng.probe.live_buffer_bytes = eng.probe.live_texture_bytes = 0;
        eng.probe.live_cpu_buffer_bytes = 0;
        eng.probe.vertex_input_current_entries = eng.probe.vertex_input_current_bytes = 0;
        eng.probe.vertex_input_cache_entries = eng.probe.vertex_input_cache_bytes = 0;
        eng.probe.vertex_input_oversized_entries = eng.probe.vertex_input_oversized_bytes = 0;
        eng.probe.queued_frames = 0;
        eng.probe.frame_slots = eng.frame_slots;
        eng.probe.canvas_texture_bytes = eng.probe.transient_buffer_bytes = 0;
        eng.probe.line_resource_pool_slots = eng.probe.line_resource_pool_busy_slots = 0;
        eng.probe.line_resource_pool_bytes = line_canary ? line_canary.GetSize() : 0;
        if (line_pool) {
            const auto stats = line_pool->stats();
            eng.probe.line_resource_pool_slots = stats.slots;
            eng.probe.line_resource_pool_busy_slots = stats.busy_slots;
            eng.probe.line_resource_pool_bytes += stats.owned_capacity_bytes + stats.control_bytes;
        }
        eng.probe.artifact_cache_entries = eng.shader_artifacts.portable_size();
        eng.probe.portable_shader_bytes = eng.shader_artifacts.portable_storage_bytes();
        eng.probe.shader_cache_bytes = eng.shader_artifacts.storage_bytes();
        eng.probe.shader_cache_limit = eng.shader_artifacts.byte_limit();
        eng.probe.device_generation = eng.device_generation;
        eng.probe.bresenham_line_pipelines = eng.layer_bresenham_pipelines ? eng.layer_bresenham_pipelines() : 0;
        eng.probe.last_vertex_pipelines = eng.layer_last_vertex_pipelines ? eng.layer_last_vertex_pipelines() : 0;
        eng.probe.pipeline_cache_entries = 0;
        std::unordered_set<const Artifact*> cached_artifacts;
        vispy::lines::LineDeviceDescriptorAccounting device_descriptors;
        auto observe_device_record = [&](const std::shared_ptr<LineConsumerDevice>& record) {
            if (record) device_descriptors.observe_record(record.get(), record->storage_bytes());
        };
        auto observe_device_artifact = [&](const std::shared_ptr<Artifact>& artifact, bool cached) {
            using Base = vispy::shader::DeviceShaderArtifact<
                wgpu::ShaderModule, wgpu::RenderPipeline, wgpu::BindGroupLayout>;
            device_descriptors.observe_artifact(artifact.get(), cached,
                artifact->storage_bytes(sizeof(Artifact) - sizeof(Base)));
            artifact->consumer_devices.for_each_record([&](const auto& record) {
                observe_device_record(record);
                device_descriptors.contains(artifact.get(), record.get());
            });
        };
        eng.shader_artifacts.for_each_device([&](const auto& artifact) {
            cached_artifacts.insert(artifact.get());
            observe_device_artifact(artifact, true);
            eng.probe.pipeline_cache_entries += artifact->render_variant_count() + (artifact->pipeline ? 1 : 0) +
                                               (artifact->line_pipeline_ok ? 1 : 0);
        });
        std::vector<std::shared_ptr<const vispy::shader::PortableShaderArtifact>> live_portable;
        std::vector<std::shared_ptr<const vispy::shader::LineEvaluatorArtifact>> live_evaluators;
        std::vector<std::shared_ptr<const vispy::shader::GeneratedLineConsumerArtifact>> live_consumers;
        std::unordered_set<const Artifact*> counted_external_artifacts;
        auto count_consumer_device = [&](const std::shared_ptr<LineConsumerDevice>& record) {
            if (!record) return;
            live_consumers.push_back(record->consumer);
            observe_device_record(record);
        };
        auto count_artifact = [&](const std::shared_ptr<Artifact>& artifact) {
            if (!artifact) return;
            live_portable.push_back(artifact->portable);
            if (artifact->evaluator) live_evaluators.push_back(artifact->evaluator);
            artifact->for_each_consumer([&](std::string_view, const auto& consumer) {
                live_consumers.push_back(consumer);
            });
            if (!cached_artifacts.contains(artifact.get()) && counted_external_artifacts.insert(artifact.get()).second) {
                observe_device_artifact(artifact, false);
            }
        };
        for (const auto& [id, canvas] : eng.canvases) eng.probe.queued_frames += canvas.queued_frames.size();
        std::function<void(const std::shared_ptr<const BufferRev>&)> count_buffer;
        count_buffer = [&](const std::shared_ptr<const BufferRev>& rev) {
            if (!rev || !buffer_revisions.insert(rev.get()).second) return;
            eng.probe.live_cpu_buffer_bytes += rev->cpu.capacity();
            if (rev->batch_data) eng.probe.live_cpu_buffer_bytes += rev->batch_data->metadata_storage_bytes();
            if (rev->point_batch_data) eng.probe.live_cpu_buffer_bytes += rev->point_batch_data->metadata_storage_bytes();
            if (rev->gpu && buffers.insert(rev->gpu.Get()).second)
                eng.probe.live_buffer_bytes += rev->gpu.GetSize();
            for (const auto& [key, derived] : rev->derived) count_buffer(derived);
        };
        std::unordered_set<const BufferRev*> current_buffer_revisions;
        std::unordered_set<const void*> oversized_buffer_revisions;
        std::function<uint64_t(const std::shared_ptr<BufferRev>&)> current_record_bytes;
        current_record_bytes = [&](const std::shared_ptr<BufferRev>& rev) -> uint64_t {
            if (!rev || !current_buffer_revisions.insert(rev.get()).second) return 0;
            uint64_t bytes = sizeof(BufferRev) + 2 * sizeof(void*) + rev->cpu.capacity();
            if (rev->batch_data) bytes += rev->batch_data->metadata_storage_bytes();
            if (rev->point_batch_data) bytes += rev->point_batch_data->metadata_storage_bytes();
            for (const auto& [key, child] : rev->derived) {
                bytes += sizeof(decltype(rev->derived)::value_type) +
                    vispy::inputs::cache_entry_bookkeeping + key.capacity();
                bytes += current_record_bytes(child);
            }
            return bytes;
        };
        std::unordered_set<const TextureRev*> texture_revisions;
        std::function<void(const std::shared_ptr<TextureRev>&)> count_texture;
        count_texture = [&](const std::shared_ptr<TextureRev>& rev) {
            if (!rev || !texture_revisions.insert(rev.get()).second) return;
            if (rev->texture && textures.insert(rev->texture.Get()).second)
                eng.probe.live_texture_bytes += rev->gpu_bytes;
            count_texture(rev->base);
        };
        auto count_target = [&](const wgpu::Texture& texture) {
            if (!texture || !textures.insert(texture.Get()).second) return;
            // Requested format bytes; driver padding and opaque depth backing
            // allocations are outside this renderer-owned descriptor accounting.
            const uint64_t bytes = uint64_t(texture.GetWidth()) * texture.GetHeight() *
                texture.GetDepthOrArrayLayers() * texture.GetSampleCount() * 4;
            eng.probe.live_texture_bytes += bytes;
            eng.probe.canvas_texture_bytes += bytes;
        };
        auto count_native_buffer = [&](const wgpu::Buffer& buffer) {
            if (buffer && buffers.insert(buffer.Get()).second)
                eng.probe.live_buffer_bytes += buffer.GetSize();
        };
        auto count_line_slot = [&](const NativeLineSlot& slot) {
            count_native_buffer(slot.output);
            count_native_buffer(slot.compute_uniforms);
            count_native_buffer(slot.render_uniforms);
            if (!slot.control) return;
            for (const auto* cache : {&slot.control->compute, &slot.control->render}) {
                for (const auto& borrowed : cache->buffers) count_native_buffer(borrowed.handle);
                for (const auto& borrowed : cache->textures)
                    if (borrowed.texture && textures.insert(borrowed.texture.Get()).second)
                        eng.probe.live_texture_bytes += borrowed.bytes;
            }
        };
        count_native_buffer(line_canary);
        if (line_pool) line_pool->for_each_slot([&](const auto& slot) { count_line_slot(slot.payload); });
        std::function<void(const DrawSnap&)> count_snapshot;
        count_snapshot = [&](const DrawSnap& snap) {
            if (snap.line_chunks) {
                for (const auto& leaf : *snap.line_chunks) count_snapshot(leaf);
            }
            count_artifact(snap.artifact);
            if (snap.line_inputs) {
                count_artifact(snap.line_inputs->original_artifact);
                live_portable.push_back(snap.line_inputs->portable);
                if (snap.line_inputs->evaluator) live_evaluators.push_back(snap.line_inputs->evaluator);
                if (snap.line_inputs->consumer) live_consumers.push_back(snap.line_inputs->consumer);
                count_consumer_device(snap.line_inputs->consumer_device);
                // The original index/attribute owners precede topology and
                // compact-layout rewriting, and may differ from render inputs.
                count_buffer(snap.line_inputs->selection.index);
                for (const auto& buffer : snap.line_inputs->vertices) count_buffer(buffer);
                for (const auto& texture : snap.line_inputs->textures) count_texture(texture);
            }
            if (snap.line_work) {
                count_artifact(snap.line_work->original);
                live_evaluators.push_back(snap.line_work->evaluator);
                if (snap.line_work->consumer) live_consumers.push_back(snap.line_work->consumer);
                count_consumer_device(snap.line_work->consumer_device);
                count_buffer(snap.line_work->packed_inputs);
                for (const auto& texture : snap.line_work->textures) count_texture(texture);
            }
            for (const auto& buffer : snap.vertices) count_buffer(buffer);
            count_buffer(snap.index);
            count_buffer(snap.point_identity);
            count_buffer(snap.vertex_identity);
            count_buffer(snap.batch_inputs);
            count_buffer(snap.point_batch_inputs);
            for (const auto& texture : snap.textures) count_texture(texture);
            count_texture(snap.attachment);
            count_texture(snap.depth_attachment);
            count_target(snap.target_texture);
            count_target(snap.resolve_texture);
            count_target(snap.depth_texture);
        };
        for (const auto& [id, obj] : eng.objects) {
            count_artifact(obj.artifact);
            count_artifact(obj.point_artifact);
            count_artifact(obj.affine_artifact);
            count_artifact(obj.indexed_artifact);
            count_artifact(obj.batch_affine_artifact);
            count_artifact(obj.batch_indexed_artifact);
            count_buffer(obj.buffer);
            count_buffer(obj.primitive_indices);
            count_buffer(obj.point_geometry_cache);
            count_buffer(obj.input_geometry_cache);
            obj.input_current.for_each([&](auto, const auto& key, const auto& record) {
                ++eng.probe.vertex_input_current_entries;
                eng.probe.vertex_input_current_bytes +=
                    sizeof(typename decltype(obj.input_current)::Entry) + key.capacity() + current_record_bytes(record);
                count_buffer(record);
            });
            eng.probe.vertex_input_oversized_entries += obj.input_oversized.size();
            eng.probe.vertex_input_oversized_bytes += obj.input_oversized.storage_bytes(
                [](const auto& record, auto& visited) { return input_graph_bytes(record, visited); },
                oversized_buffer_revisions);
            obj.input_oversized.for_each([&](auto, const auto&, const auto& record) { count_buffer(record); });
            if (obj.input_geometry_cache) {
                for (const auto& [key, record] : obj.input_geometry_cache->derived) {
                    ++eng.probe.vertex_input_cache_entries;
                    eng.probe.vertex_input_cache_bytes += sizeof(decltype(obj.input_geometry_cache->derived)::value_type) +
                        vispy::inputs::cache_entry_bookkeeping + key.capacity() + input_record_bytes(record);
                }
            }
            count_texture(obj.texture);
            for (const auto& [name, binding] : obj.attributes) count_buffer(binding.constant_buffer);
        }
        for (const auto& texture : eng.dummy_textures) count_texture(texture);
        for (const auto& [id, canvas] : eng.canvases) {
            count_target(canvas.color);
            count_target(canvas.multisampled_color);
            count_target(canvas.depth);
            count_target(canvas.presented);
            for (const auto& snap : canvas.pending) count_snapshot(snap);
            for (const auto& frame : canvas.queued_frames)
                for (const auto& snap : frame.draws) count_snapshot(snap);
        }
        for (const auto& ticket : eng.tickets) {
            for (const auto& artifact : ticket->artifacts) count_artifact(artifact);
            if (ticket->line_resources)
                for (size_t i = 0; i < ticket->line_resources->size(); ++i)
                    count_line_slot(ticket->line_resources->at(i).inspect_payload());
            for (const auto& original : ticket->line_inputs) {
                count_artifact(original->original_artifact);
                live_portable.push_back(original->portable);
                if (original->evaluator) live_evaluators.push_back(original->evaluator);
                if (original->consumer) live_consumers.push_back(original->consumer);
                count_consumer_device(original->consumer_device);
                count_buffer(original->selection.index);
                for (const auto& buffer : original->vertices) count_buffer(buffer);
                for (const auto& texture : original->textures) count_texture(texture);
            }
            for (const auto& work : ticket->line_work) {
                count_artifact(work->original);
                live_evaluators.push_back(work->evaluator);
                if (work->consumer) live_consumers.push_back(work->consumer);
                count_consumer_device(work->consumer_device);
                count_buffer(work->packed_inputs);
                for (const auto& texture : work->textures) count_texture(texture);
            }
            for (const auto& rev : ticket->buffers) count_buffer(rev);
            for (const auto& rev : ticket->textures) count_texture(rev);
            for (const auto& texture : ticket->owned_textures) count_target(texture);
            for (const auto& buffer : ticket->transient_buffers) {
                if (buffer && buffers.insert(buffer.Get()).second) {
                    eng.probe.transient_buffer_bytes += buffer.GetSize();
                    eng.probe.live_buffer_bytes += buffer.GetSize();
                }
            }
        }
        for (const auto& capture : eng.line_captures) {
            live_evaluators.push_back(capture->evaluator);
            if (capture->readback && buffers.insert(capture->readback.Get()).second) {
                eng.probe.transient_buffer_bytes += capture->readback.GetSize();
                eng.probe.live_buffer_bytes += capture->readback.GetSize();
            }
            for (const auto& part : capture->parts) if (part.readback && buffers.insert(part.readback.Get()).second) {
                eng.probe.transient_buffer_bytes += part.readback.GetSize();
                eng.probe.live_buffer_bytes += part.readback.GetSize();
            }
        }
        for (const auto& segment : query_segments) {
            for (const auto& buffer : {segment->resolve_buffer, segment->readback_buffer}) {
                if (buffer && buffers.insert(buffer.Get()).second) {
                    eng.probe.transient_buffer_bytes += buffer.GetSize();
                    eng.probe.live_buffer_bytes += buffer.GetSize();
                }
            }
        }
        const auto shader_bytes = eng.shader_artifacts.external_portable_bytes(live_portable, live_evaluators, live_consumers);
        eng.probe.live_portable_shader_bytes = shader_bytes.live_bytes;
        eng.probe.uncached_live_portable_shader_bytes = shader_bytes.uncached_bytes;
        const auto evaluator_bytes = eng.shader_artifacts.external_auxiliary_bytes(live_evaluators, live_consumers);
        eng.probe.live_line_evaluator_bytes = evaluator_bytes.live_bytes;
        eng.probe.uncached_live_line_evaluator_bytes = evaluator_bytes.uncached_bytes;
        const auto consumer_bytes = eng.shader_artifacts.external_consumer_bytes(live_consumers);
        eng.probe.live_line_consumer_bytes = consumer_bytes.live_bytes;
        eng.probe.uncached_live_line_consumer_bytes = consumer_bytes.uncached_bytes;
        const auto device_bytes = device_descriptors.finish();
        eng.probe.live_device_shader_bytes = device_bytes.live_bytes;
        eng.probe.uncached_live_device_shader_bytes = device_bytes.uncached_bytes;
        if (eng.layer_count != nullptr) eng.probe.vk_queue_submits = eng.layer_count();
        update_memory_snapshot();
        update_work_peaks();
        ++probe.descriptor_samples;
        probe.sampled_peak_live_buffer_bytes = std::max(probe.sampled_peak_live_buffer_bytes, probe.live_buffer_bytes);
        probe.sampled_peak_live_cpu_buffer_bytes = std::max(probe.sampled_peak_live_cpu_buffer_bytes, probe.live_cpu_buffer_bytes);
        probe.sampled_peak_live_texture_bytes = std::max(probe.sampled_peak_live_texture_bytes, probe.live_texture_bytes);
    }

    void finish_target(Canvas& target, bool present) {
        update_work_peaks();
        if (target.width <= 0 || target.height <= 0) {
            cancel_canvas_frames(target, "cancelled", "zero drawable before complete frame retirement");
            target.pending.clear();
            target.queued_frames.clear();
            target.deferred_present = false;
            update_work_peaks();
            return;
        }
        if (tickets.size() >= frame_slots) wait_queue();
        if (target.queued_frames.size() >= frame_slots) {
            submit_canvas(target, false, true);
            if (queue) wait_queue();
        }
        bool requested = false;
        do {
            submit_canvas(target, present, requested);
            requested = true;
            if (queue) wait_queue();
        } while (!target.queued_frames.empty() || !target.pending.empty());
    }
};

Engine& engine() {
    static Engine g;
    return g;
}

int arg_id(const Command& cmd, size_t index) {
    if (index >= cmd.args.size()) return 0;
    return static_cast<int>(cmd.args[index].i);
}

}  // namespace

std::string runtime_revision() {
    return "117b054598f4758b598f4b8f48feea48c11fe7b0+dawn-499e5c6ff9b37d5de70c6493fb74c251e0d35c1c";
}

DeviceInfo ensure_device() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    eng.init_device();
    return eng.info;
}

Probe probe_counters() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    eng.update_descriptor_accounting();
    return eng.probe;
}

uint64_t layer_submit_count() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    return eng.layer_count == nullptr ? 0 : eng.layer_count();
}

int register_canvas(int width, int height, int samples, bool vsync) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.init_device();
    static int next = 1;
    int id = next++;
    Canvas canvas;
    canvas.id = id;
    canvas.vsync = vsync;
    canvas.width = std::max(0, width);
    canvas.height = std::max(0, height);
    if (samples > 1 && samples != 4) throw std::runtime_error("Dawn supports MSAA sample counts 1 and 4");
    canvas.samples = std::max(1, samples);
    eng.canvases[id] = canvas;
    if (eng.device_ready) eng.ensure_target(eng.canvases[id]);
    return id;
}

void configure_canvas(int canvas_id, int width, int height, int samples) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto& canvas = eng.canvas(canvas_id);
    canvas.width = width;
    canvas.height = height;
    if (samples > 1 && samples != 4) throw std::runtime_error("Dawn supports MSAA sample counts 1 and 4");
    canvas.samples = std::max(1, samples);
    canvas.swapchain_current = false;
    if (width <= 0 || height <= 0) {
        eng.cancel_canvas_frames(canvas, "cancelled", "canvas became a zero drawable before complete paint retirement");
        canvas.pending.clear(); canvas.queued_frames.clear(); canvas.deferred_present = false;
        eng.log("minimize or zero size");
        return;
    }
    if (eng.device_ready) eng.ensure_target(canvas);
}

FramebufferConfiguration framebuffer_config(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto& canvas = eng.canvas(canvas_id);
    if (!eng.init_device())
        throw std::runtime_error("framebuffer configuration: " + eng.info.error);
    using vispy::framebuffer::ColorStorage;
    using vispy::framebuffer::DepthStorage;
    FramebufferConfiguration result;
    if (canvas.fbo == 0) {
        if (canvas.width <= 0 || canvas.height <= 0)
            throw std::runtime_error("framebuffer configuration: empty canvas target");
        eng.ensure_target(canvas);
        const auto& color = canvas.samples > 1 ? canvas.multisampled_color : canvas.color;
        if (!color || !canvas.depth || color.GetFormat() != wgpu::TextureFormat::RGBA8Unorm ||
            canvas.depth.GetFormat() != wgpu::TextureFormat::Depth24PlusStencil8 ||
            color.GetSampleCount() != canvas.depth.GetSampleCount())
            throw std::runtime_error("framebuffer configuration: unexpected canvas attachment storage");
        result = vispy::framebuffer::describe({4, 8, "rgba8unorm", false},
            DepthStorage::Depth24PlusStencil8, true, true,
            static_cast<int>(color.GetSampleCount()), bool(canvas.surface) && canvas.surface_configured);
        result.width = static_cast<int>(color.GetWidth());
        result.height = static_cast<int>(color.GetHeight());
        result.configuration_source = "allocated_target";
        return result;
    }

    auto framebuffer = eng.objects.find(canvas.fbo);
    if (framebuffer == eng.objects.end() || framebuffer->second.class_name != "FrameBuffer")
        throw std::runtime_error("framebuffer configuration: missing framebuffer object");
    auto attachment = [&](int id, const char* kind) -> const TextureRev& {
        const auto object = eng.objects.find(id);
        if (id == 0 || object == eng.objects.end() || !object->second.texture)
            throw std::runtime_error(std::string("framebuffer configuration: missing ") + kind + " attachment");
        return *object->second.texture;
    };
    auto allocation = [](const TextureRev& revision) -> const TextureData& {
        return revision.allocation_descriptor ? *revision.allocation_descriptor :
            static_cast<const TextureData&>(revision);
    };
    const auto& color = attachment(framebuffer->second.fb_color, "color");
    const auto& storage = allocation(color);
    if (storage.dimensions != 2 || storage.width <= 0 || storage.height <= 0)
        throw std::runtime_error("framebuffer configuration: invalid 2D color attachment");
    const auto description = texture_detail::describe(storage);
    const auto native_format = texture_detail::native_format(description);
    if (color.texture && color.texture.GetFormat() != native_format)
        throw std::runtime_error("framebuffer configuration: color storage differs from frozen descriptor");
    const char* encoding = nullptr;
    using S = texture_detail::Storage;
    switch (description.storage) {
    case S::Float16: case S::Float32: encoding = "float"; break;
    case S::Unorm8: case S::Unorm16: encoding = "unorm"; break;
    case S::Snorm8: encoding = "snorm"; break;
    case S::Uint8: case S::Uint16: case S::Uint32: encoding = "uint"; break;
    case S::Sint8: case S::Sint16: case S::Sint32: encoding = "sint"; break;
    }
    if (!encoding)
        throw std::runtime_error("framebuffer configuration: unsupported color storage encoding");
    ColorStorage color_storage;
    color_storage.channels = description.channels;
    color_storage.component_bits = static_cast<int>(description.component_bytes * 8);
    color_storage.format = std::string(description.channels == 1 ? "r" : description.channels == 2 ? "rg" : "rgba") +
        std::to_string(color_storage.component_bits) + encoding;
    const bool depth_attached = framebuffer->second.fb_depth != 0;
    const bool stencil_attached = framebuffer->second.fb_stencil != 0;
    bool native_allocations = bool(color.texture);
    auto depth_kind = DepthStorage::None;
    for (const auto& [id, kind] : {std::pair{framebuffer->second.fb_depth, "depth"},
                                  std::pair{framebuffer->second.fb_stencil, "stencil"}}) {
        if (id == 0) continue;
        const auto& depth = attachment(id, kind);
        const auto& depth_storage = allocation(depth);
        if ((depth_storage.format != "depth" && depth_storage.format != "stencil" &&
             depth_storage.format != "depth_stencil" && depth_storage.format != "depth_component") || depth_storage.width != storage.width ||
            depth_storage.height != storage.height)
            throw std::runtime_error("framebuffer configuration: invalid depth/stencil attachment");
        const bool float_depth = depth_storage.format == "depth_component";
        const auto current_kind = float_depth ? DepthStorage::Depth32Float : DepthStorage::Depth24PlusStencil8;
        if (float_depth && (id != framebuffer->second.fb_depth || stencil_attached))
            throw std::runtime_error("framebuffer configuration: depth_component has no stencil aspect");
        if (depth_kind != DepthStorage::None && current_kind != depth_kind)
            throw std::runtime_error("framebuffer configuration: incompatible depth/stencil attachments");
        depth_kind = current_kind;
        if (depth.texture && depth.texture.GetFormat() != (float_depth ? wgpu::TextureFormat::Depth32Float :
                                                                         wgpu::TextureFormat::Depth24PlusStencil8))
            throw std::runtime_error("framebuffer configuration: unexpected depth/stencil storage");
        native_allocations = native_allocations && bool(depth.texture);
    }
    // FBO render targets currently have one sample, even on an MSAA canvas.
    // Inspect retained allocation descriptors without uploading DATA, encoding
    // queued draws, or waiting for GPU completion merely to answer a query.
    result = vispy::framebuffer::describe(color_storage,
        depth_kind, depth_attached, stencil_attached, 1, false);
    result.framebuffer_id = canvas.fbo;
    result.width = storage.width;
    result.height = storage.height;
    result.configuration_source = native_allocations ? "allocated_target" : "retained_attachment_descriptor";
    return result;
}

void destroy_canvas(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto it = eng.canvases.find(canvas_id);
    if (it == eng.canvases.end()) return;
    eng.cancel_canvas_frames(it->second, "cancelled", "canvas destroyed before complete paint retirement");
    for (const auto& frame : eng.query_frames) if (frame->canvas_id == canvas_id) {
        frame->fail(vispy::timing::Status::Cancelled, "canvas destroyed before timing collection");
        frame->finalized = true;
    }
    if (!eng.tickets.empty() && eng.queue) eng.wait_queue();
    eng.retire_surface(it->second);
    it->second.alive = false;
    it->second.pending.clear();
    eng.terminal_canvases.push_back(canvas_id);
    if (eng.terminal_canvases.size() > 128) eng.terminal_canvases.pop_front();
    eng.canvases.erase(it);
    eng.log("destroy canvas " + std::to_string(canvas_id));
}

static void install_native_surface(int canvas_id, const vispy::platform::NativeSurfaceDescriptor& descriptor) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end()) return;
    auto& canvas = found->second;
    if (!eng.init_device()) return;
    auto owner = vispy::platform::make_native_surface_owner(descriptor);
    eng.retire_surface(canvas);
    canvas.surface_owner = std::move(owner);
    eng.ensure_native_surface(canvas);
}

void clear_surface(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto found = eng.canvases.find(canvas_id);
    if (found != eng.canvases.end()) eng.retire_surface(found->second);
}

void set_surface(int canvas_id, std::uintptr_t hwnd, std::uintptr_t hinstance) {
    if (!hwnd) { clear_surface(canvas_id); return; }
    vispy::platform::NativeSurfaceDescriptor descriptor;
    descriptor.kind = vispy::platform::NativeSurfaceKind::Win32;
    descriptor.window = hwnd;
    descriptor.hinstance = hinstance;
    install_native_surface(canvas_id, descriptor);
}

void set_surface_x11(int canvas_id, std::uintptr_t display, uint64_t window, bool owned_display) {
    if (!window) { clear_surface(canvas_id); return; }
    vispy::platform::NativeSurfaceDescriptor descriptor;
    descriptor.kind = vispy::platform::NativeSurfaceKind::Xlib;
    descriptor.window = window;
    descriptor.display = display;
    descriptor.open_owned_display = owned_display;
    install_native_surface(canvas_id, descriptor);
}

void set_surface_metal_view(int canvas_id, std::uintptr_t view) {
    if (!view) { clear_surface(canvas_id); return; }
    vispy::platform::NativeSurfaceDescriptor descriptor;
    descriptor.kind = vispy::platform::NativeSurfaceKind::Metal;
    descriptor.window = view;
    install_native_surface(canvas_id, descriptor);
}

void update_surface_scale(int canvas_id, double scale) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    if (!std::isfinite(scale) || scale <= 0) throw std::runtime_error("invalid canvas surface scale");
    auto& canvas = eng.canvas(canvas_id);
    canvas.surface_scale = scale;
    if (canvas.surface_owner && canvas.surface_owner->is_alive())
        canvas.surface_owner->update(canvas.width, canvas.height, scale);
}

static void execute_commands_impl(int canvas_id, const std::vector<Command>& commands,
                                  std::vector<Command>* owned_commands,
                                  uint64_t binding_decode_ns, uint64_t binding_decode_bytes,
                                  const UploadCaptureStats& capture_stats) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    HostTimer interpret_timer(eng.probe.native_interpret_ns);
    eng.probe.binding_decode_ns += binding_decode_ns;
    eng.probe.binding_decode_bytes += binding_decode_bytes;
    eng.probe.owned_upload_captures += capture_stats.captures;
    eng.probe.owned_upload_capture_bytes += capture_stats.bytes;
    eng.probe.owned_upload_fallback_dtypes += capture_stats.fallback_dtypes;
    eng.probe.owned_upload_fallback_exports += capture_stats.fallback_exports;
    ++eng.probe.native_batches;
    if (!eng.init_device()) throw std::runtime_error(eng.info.error);
    eng.poll();
    for (int id : eng.drop_next) eng.objects.erase(id);
    eng.drop_next.clear();
    eng.deleted_now.clear();
    auto& canvas = eng.canvas(canvas_id);
    for (size_t command_index = 0; command_index < commands.size(); ++command_index) {
      const Command& cmd = commands[command_index];
      ++eng.probe.native_commands;
      try {
        static const bool stderr_trace = std::getenv("VISPY_DAWN_TRACE") != nullptr;
        if (stderr_trace) eng.log("GLIR begin " + cmd.op + " object=" + std::to_string(arg_id(cmd, 0)));
        static const std::unordered_map<std::string, size_t> arities = {
            {"CURRENT", 2}, {"CREATE", 2}, {"DELETE", 1}, {"FUNC", 1},
            {"DATA", 3}, {"SIZE", 2}, {"INTERPOLATION", 3}, {"WRAPPING", 2},
            {"ATTACH", 2}, {"LINK", 1}, {"UNIFORM", 4}, {"TEXTURE", 3},
            {"ATTRIBUTE", 4}, {"FRAMEBUFFER", 2}, {"DRAW", 3}
        };
        auto arity = arities.find(cmd.op);
        if (arity == arities.end()) throw std::runtime_error("unsupported operation");
        if (cmd.args.size() < arity->second) throw std::runtime_error("missing command arguments");
        if (cmd.op == "CURRENT") {
            canvas.fbo = cmd.args.size() > 1 ? arg_id(cmd, 1) : 0;
            canvas.framebuffer_stack.clear();
            canvas.framebuffer_stack.push_back(canvas.fbo);
            eng.log("CURRENT fbo=" + std::to_string(canvas.fbo));
            continue;
        }
        if (cmd.op == "CREATE") {
            GpuObject obj;
            obj.class_name = cmd.args.size() > 1 ? cmd.args[1].s : "";
            if (!texture_detail::supported_glir_object_class(obj.class_name))
                throw std::runtime_error("unsupported object class " + obj.class_name);
            obj.generation = 1;
            eng.objects[arg_id(cmd, 0)] = obj;
            continue;
        }
        if (cmd.op == "DELETE") {
            int id = arg_id(cmd, 0);
            eng.deleted_now.insert(id);
            eng.discard_point_geometry(id);
            auto it = eng.objects.find(id);
            if (it != eng.objects.end()) {
                it->second.alive = false;
                if (it->second.class_name == "Program") {
                    // Object removal is delayed until the next parse. Release
                    // this Program's ordinary owners now; immutable snapshots
                    // and Tickets keep their already-selected records alive.
                    it->second.input_current.clear();
                    it->second.input_oversized.clear();
                    it->second.input_geometry_cache.reset();
                }
            }
            eng.log("DELETE id=" + std::to_string(id));
            continue;
        }
        if (cmd.op == "FUNC") {
            const std::string name = cmd.args.empty() ? "" : cmd.args[0].s;
            if (name == "glClear") {
                DrawSnap clear;
                clear.origin = vispy::render::SnapshotOrigin::Clear;
                eng.capture_target(canvas, clear);
                const int mask = arg_id(cmd, 1);
                clear.clear = (mask & 0x4000) != 0;
                clear.clear_depth = (mask & 0x100) != 0 && canvas.state.depth_mask;
                clear.clear_stencil = (mask & 0x400) != 0;
                std::memcpy(clear.clear_color, canvas.clear_color, sizeof(clear.clear_color));
                const bool partial_color = clear.clear &&
                    std::find(clear.state.color_mask.begin(), clear.state.color_mask.end(), false) != clear.state.color_mask.end();
                if (clear.scissor_enabled || partial_color ||
                    (clear.clear_stencil && clear.state.stencil_front.write_mask != 0xffffffffu))
                    eng.lower_masked_clear(clear);
                canvas.pending.push_back(std::move(clear));
                eng.update_work_peaks();
                canvas.swapchain_current = false;
            } else if (name == "glFinish") {
                eng.probe.finish_calls++;
                eng.finish_target(canvas, true);
            } else if (name == "glFlush") {
                eng.log("glFlush parsed without GPU wait");
            } else {
                parse_render_state(cmd, canvas.state);
                std::copy(canvas.state.viewport.begin(), canvas.state.viewport.end(), canvas.viewport);
                std::copy(canvas.state.scissor.begin(), canvas.state.scissor.end(), canvas.scissor);
                std::copy(canvas.state.clear_color.begin(), canvas.state.clear_color.end(), canvas.clear_color);
                canvas.scissor_enabled = canvas.state.scissor_enabled;
            }
            continue;
        }
        int id = arg_id(cmd, 0);
        if (eng.deleted_now.count(id)) continue;
        auto it = eng.objects.find(id);
        if (it == eng.objects.end()) throw std::runtime_error("object does not exist");
        auto& obj = it->second;
        if (cmd.op == "DATA") {
            if (obj.class_name.find("Shader") != std::string::npos && cmd.args.size() >= 3) {
                obj.shader = cmd.args[2].s;
            } else if (obj.class_name.find("Buffer") != std::string::npos && cmd.args.size() >= 3) {
                const bool reuse = obj.buffer && obj.buffer.use_count() == 1;
                auto rev = reuse ? obj.buffer : std::make_shared<BufferRev>();
                rev->owner = id;
                rev->generation = obj.generation;
                rev->revision = obj.buffer ? obj.buffer->revision + 1 : 1;
                if (obj.buffer && !reuse) rev->cpu = obj.buffer->cpu;
                const auto& blob = cmd.args[2].blob;
                int offset = static_cast<int>(cmd.args[1].i);
                if (offset < 0 || static_cast<uint64_t>(offset) + blob.bytes.size() > rev->cpu.size())
                    throw std::runtime_error("buffer update exceeds allocation bounds");
                if (!blob.bytes.empty()) {
                    std::memcpy(rev->cpu.data() + offset, blob.bytes.data(), blob.bytes.size());
                }
                rev->derived.clear();
                obj.buffer = rev;
                eng.discard_point_geometry(id);
                eng.log("DATA buffer id=" + std::to_string(id) + " rev=" + std::to_string(rev->revision));
            } else if (cmd.args.size() >= 3 && cmd.args[2].kind == Value::Kind::Blob) {
                const bool reuse = obj.texture && obj.texture.use_count() == 1 &&
                    (!obj.texture->allocation_token || obj.texture->allocation_token.use_count() == 1);
                auto rev = reuse ? obj.texture : std::make_shared<TextureRev>();
                if (obj.texture && !reuse) *rev = *obj.texture;
                rev->owner = id;
                rev->revision++;
                if (!reuse) {
                    rev->texture = nullptr;
                    rev->view = nullptr;
                    rev->sampler = nullptr;
                    rev->allocation_token.reset();
                }
                const auto& blob = cmd.args[2].blob;
                std::vector<int> offset;
                for (const auto& axis : cmd.args[1].list) offset.push_back(static_cast<int>(axis.i));
                bool transferred = false;
                {
                    HostTimer timer(eng.probe.texture_conversion_ns);
                    if (owned_commands) {
                        // Validate inside the helper before inspecting shape metadata.
                        // Keep 1D and depth/stencil uploads on the canonical copy path.
                        const bool allow_transfer = (rev->dimensions == 2 || rev->dimensions == 3) &&
                            rev->format != "depth" && rev->format != "stencil" && rev->format != "depth_stencil" &&
                            rev->format != "depth_component";
                        transferred = vispy::textures::apply_owned_texture_data(*rev,
                            (*owned_commands)[command_index].args[2].blob, offset,
                            allow_transfer, rev->allocation_descriptor.get());
                    } else {
                        apply_texture_data(*rev, blob, offset, rev->allocation_descriptor.get());
                    }
                }
                if (transferred) {
                    ++eng.probe.owned_texture_transfers;
                    eng.probe.owned_texture_transfer_bytes += rev->pixels.size();
                }
                eng.freeze_texture_allocation(*rev);
                const bool full = texture_detail::texture_upload_is_entire(*rev, blob, offset);
                // A transferred full payload cannot enter partial-update history.
                if (transferred && !full) throw std::logic_error("owned texture transfer differs from full DATA classification");
                if (full) {
                    rev->base.reset();
                    rev->updates.clear();
                } else {
                    if (!reuse) {
                        rev->base = obj.texture;
                        rev->updates.clear();
                    }
                    rev->updates.push_back({blob, offset});
                }
                obj.texture = rev;
                obj.width = rev->width;
                obj.height = rev->height;
                eng.log("DATA texture id=" + std::to_string(id) + " rev=" + std::to_string(rev->revision));
            }
        } else if (cmd.op == "SIZE") {
            // RenderBuffer contains "Buffer" but it is a texture target.
            const bool data_buffer = obj.class_name.find("Buffer") != std::string::npos &&
                                     obj.class_name.find("Render") == std::string::npos;
            if (data_buffer) {
                int nbytes = arg_id(cmd, 1);
                if (nbytes < 0 || static_cast<uint64_t>(nbytes) > eng.info.max_buffer_size)
                    throw std::runtime_error("buffer size exceeds granted device limit");
                if (!obj.buffer || static_cast<int>(obj.buffer->cpu.size()) != nbytes) {
                    auto rev = std::make_shared<BufferRev>();
                    rev->owner = id;
                    rev->generation = ++obj.generation;
                    rev->cpu.resize(static_cast<size_t>(std::max(0, nbytes)));
                    obj.buffer = rev;
                    eng.discard_point_geometry(id);
                }
            } else if (cmd.args.size() >= 2 && cmd.args[1].kind == Value::Kind::List && cmd.args[1].list.size() >= (obj.class_name == "Texture1D" ? 1u : 2u)) {
                auto rev = std::make_shared<TextureRev>();
                rev->renderbuffer = obj.class_name == "RenderBuffer";
                if (obj.texture) {
                    rev->min_filter = obj.texture->min_filter;
                    rev->mag_filter = obj.texture->mag_filter;
                    rev->wrapping = obj.texture->wrapping;
                    rev->revision = obj.texture->revision + 1;
                }
                const auto& shape = cmd.args[1].list;
                rev->dimensions = texture_detail::texture_dimensions_for_class(obj.class_name);
                std::vector<int64_t> shape_values;
                shape_values.reserve(shape.size());
                for (const auto& value : shape) {
                    if (rev->dimensions == 1 && value.kind != Value::Kind::Int)
                        throw std::runtime_error("SIZE texture shape requires integers");
                    shape_values.push_back(value.i);
                }
                const auto layout = texture_detail::texture_shape_layout(rev->dimensions, shape_values);
                rev->width = layout.width;
                rev->height = layout.height;
                rev->depth = layout.depth;
                rev->channels = layout.channels;
                rev->format = cmd.args.size() > 2 && !cmd.args[2].s.empty() ? lower_token(cmd.args[2].s) : "rgba";
                if (rev->format == "color") rev->format = "rgba";
                rev->internal_format = cmd.args.size() > 3 ? lower_token(cmd.args[3].s) : "";
                // GLIR permits desktop enums as well as named formats. The
                // integer external red format has the same channel layout;
                // its fixed R32I/UI allocation determines sampled signedness.
                if (obj.class_name != "RenderBuffer" && cmd.args.size() > 2 &&
                    cmd.args[2].kind == Value::Kind::Int && cmd.args[2].i == 0x8d94) {
                    rev->format = "red";
                    if (cmd.args.size() <= 3 || cmd.args[3].kind != Value::Kind::Int ||
                        (cmd.args[3].i != 0x8235 && cmd.args[3].i != 0x8236))
                        throw std::runtime_error("SIZE integer red requires explicit R32I or R32UI storage");
                    rev->internal_format = cmd.args[3].i == 0x8235 ? "r32i" : "r32ui";
                }
                if (obj.class_name == "RenderBuffer" && cmd.args.size() > 2 &&
                    cmd.args[2].kind == Value::Kind::Int) {
                    // The public RenderBuffer API accepts desktop GL enums.
                    if (cmd.args[2].i == 0x88f0) rev->format = "depth_stencil";
                    else if (cmd.args[2].i == 0x8058) rev->internal_format = "rgba8";
                    else throw std::runtime_error("SIZE unsupported renderbuffer format enum " +
                                                  std::to_string(cmd.args[2].i));
                }
                rev->owner = id;
                obj.width = rev->width;
                obj.height = rev->height;
                if (obj.texture && obj.texture->width == rev->width && obj.texture->height == rev->height &&
                    obj.texture->depth == rev->depth && obj.texture->dimensions == rev->dimensions &&
                    obj.texture->channels == rev->channels && obj.texture->format == rev->format &&
                    obj.texture->internal_format == rev->internal_format) continue;
                obj.texture = std::move(rev);
            }
        } else if (cmd.op == "INTERPOLATION" || cmd.op == "WRAPPING") {
            auto rev = std::make_shared<TextureRev>();
            if (obj.texture) *rev = *obj.texture;
            if (cmd.op == "INTERPOLATION" && cmd.args.size() >= 3) {
                rev->min_filter = lower_token(cmd.args[1].s);
                rev->mag_filter = lower_token(cmd.args[2].s);
            } else if (cmd.args.size() >= 2) {
                rev->wrapping.clear();
                for (const auto& wrap : cmd.args[1].list) rev->wrapping.push_back(lower_token(wrap.s));
            }
            rev->sampler = nullptr;
            // A previous draw retains its own sampler and allocation revision.
            if (rev->texture) eng.refresh_sampler(*rev);
            obj.texture = std::move(rev);
        } else if (cmd.op == "ATTACH") {
            if (obj.class_name == "Program" && cmd.args.size() >= 2) {
                int sid = arg_id(cmd, 1);
                auto sh = eng.objects.find(sid);
                if (sh != eng.objects.end()) {
                    if (sh->second.class_name == "VertexShader") obj.vert_id = sid;
                    else if (sh->second.class_name == "FragmentShader") obj.frag_id = sid;
                    else if (sh->second.class_name == "GeometryShader") obj.geom_id = sid;
                    else throw std::runtime_error("attached object is not a shader");
                } else throw std::runtime_error("attached shader does not exist");
            } else if (cmd.args.size() >= 3 && cmd.args[1].s == "color") {
                obj.fb_color = arg_id(cmd, 2);
            } else if (cmd.args.size() >= 3 && cmd.args[1].s == "depth") {
                obj.fb_depth = arg_id(cmd, 2);
            } else if (cmd.args.size() >= 3 && cmd.args[1].s == "stencil") {
                obj.fb_stencil = arg_id(cmd, 2);
            }
        } else if (cmd.op == "LINK") {
            obj.point_artifact.reset();
            obj.affine_artifact.reset();
            obj.indexed_artifact.reset();
            obj.batch_affine_artifact.reset();
            obj.batch_indexed_artifact.reset();
            obj.input_geometry_cache.reset();
            obj.input_current.clear();
            obj.input_oversized.clear();
            obj.input_vertex_sources.clear(); obj.input_instance_sources.clear(); obj.input_index_source.clear();
            obj.input_index_owner = 0;
            if (obj.geom_id != 0) {
                throw std::runtime_error("LINK Program " + std::to_string(id) + ": geometry shader unsupported");
            }
            std::string error;
            std::string vert = eng.objects.count(obj.vert_id) ? eng.objects[obj.vert_id].shader : "";
            std::string frag = eng.objects.count(obj.frag_id) ? eng.objects[obj.frag_id].shader : "";
            obj.artifact = eng.make_artifact(vert, frag, error, false, true,
                frag.find("gl_PointCoord") != std::string::npos,
                VertexIdentityPolicy::Native, SpirvDerivativeMode::AllowNonUniform, false);
            if (obj.point_geometry_cache) obj.point_geometry_cache->derived.clear();
            obj.point_geometry_sources.clear();
            if (!error.empty()) throw std::runtime_error("LINK Program " + std::to_string(id) + ": " + error);
        } else if (cmd.op == "UNIFORM" && cmd.args.size() >= 4) {
            const std::string& gtype = cmd.args[2].s;
            std::vector<float> floats;
            std::vector<int32_t> ints;
            if (cmd.args[3].kind == Value::Kind::Blob) {
                if (cmd.args[3].blob.dtype == "bool") {
                    for (uint8_t byte : cmd.args[3].blob.bytes) ints.push_back(byte ? 1 : 0);
                } else if (cmd.args[3].blob.dtype == "i32") {
                    ints.resize(cmd.args[3].blob.bytes.size() / 4);
                    std::memcpy(ints.data(), cmd.args[3].blob.bytes.data(), ints.size() * 4);
                } else {
                    floats.resize(cmd.args[3].blob.bytes.size() / 4);
                    std::memcpy(floats.data(), cmd.args[3].blob.bytes.data(), floats.size() * 4);
                }
            }
            if (gtype == "int" || gtype == "bool" || gtype.find("ivec") == 0 || gtype.find("bvec") == 0)
                obj.i_uniforms[cmd.args[1].s] = ints;
            else obj.f_uniforms[cmd.args[1].s] = floats;
        } else if (cmd.op == "TEXTURE" && cmd.args.size() >= 3) {
            obj.textures[cmd.args[1].s] = arg_id(cmd, 2);
        } else if (cmd.op == "ATTRIBUTE" && cmd.args.size() >= 4) {
            if (cmd.args[1].s == vispy::points::identity_attribute)
                throw std::runtime_error("ATTRIBUTE vispy_point_identity: reserved native point identity cannot be bound");
            if (cmd.args[1].s == "vispy_vertex_identity")
                throw std::runtime_error("ATTRIBUTE vispy_vertex_identity: reserved native vertex identity cannot be bound");
            AttrBinding binding;
            binding.type = cmd.args[2].s;
            binding.divisor = cmd.args.size() > 4 ? arg_id(cmd, 4) : 0;
            const Value& value = cmd.args[3];
            if (value.kind == Value::Kind::List && !value.list.empty() && value.list[0].i == 0 &&
                value.list.size() > 1) {
                binding.constant = true;
                for (size_t c = 1; c < value.list.size(); ++c) {
                    const auto& component = value.list[c];
                    if (component.kind != Value::Kind::Int && component.kind != Value::Kind::Bool &&
                        component.kind != Value::Kind::Float)
                        throw std::runtime_error("ATTRIBUTE constant requires a numeric component");
                    binding.constant_words.push_back(vispy::lines::endpoint_constant_word(binding.type,
                        component.kind != Value::Kind::Float,
                        component.kind == Value::Kind::Bool ? int64_t(component.b) : component.i, component.f));
                }
            } else if (value.kind == Value::Kind::List && value.list.size() >= 3) {
                binding.buffer_id = static_cast<int>(value.list[0].i);
                binding.stride = static_cast<int>(value.list[1].i);
                binding.offset = static_cast<int>(value.list[2].i);
            }
            const auto previous = obj.attributes.find(cmd.args[1].s);
            const bool same_binding = previous != obj.attributes.end() &&
                previous->second.constant == binding.constant && previous->second.buffer_id == binding.buffer_id &&
                previous->second.stride == binding.stride && previous->second.offset == binding.offset &&
                previous->second.divisor == binding.divisor && previous->second.type == binding.type &&
                previous->second.constant_words == binding.constant_words;
            if (!same_binding) {
                eng.discard_input_category(obj, vispy::inputs::CurrentCategory::LineEndpoint, "line-endpoint:");
                eng.discard_input_category(obj, vispy::inputs::CurrentCategory::Batch, "batch:");
                eng.discard_input_category(obj, vispy::inputs::CurrentCategory::CompactFit, "compact-fit:");
                if (obj.input_geometry_cache) {
                    // Pending snapshots retain their old children. A change
                    // between vertex/instance steps invalidates both owners.
                    const bool old_instance = previous != obj.attributes.end() && !previous->second.constant && previous->second.divisor > 0;
                    const bool new_instance = !binding.constant && binding.divisor > 0;
                    if (!old_instance || !new_instance) {
                        eng.discard_input_category(obj, vispy::inputs::CurrentCategory::Vertex, "vertex:");
                        obj.input_vertex_sources.clear();
                    }
                    if (old_instance || new_instance) {
                        eng.discard_input_category(obj, vispy::inputs::CurrentCategory::Instance, "instance:");
                        obj.input_instance_sources.clear();
                    }
                }
                obj.attributes[cmd.args[1].s] = std::move(binding);
                if (obj.point_geometry_cache) obj.point_geometry_cache->derived.clear();
                obj.point_geometry_sources.clear();
            }
        } else if (cmd.op == "FRAMEBUFFER") {
            bool use = cmd.args.size() > 1 && (cmd.args[1].b || cmd.args[1].i != 0);
            if (canvas.framebuffer_stack.empty()) canvas.framebuffer_stack.push_back(canvas.fbo);
            if (use) {
                if (canvas.framebuffer_stack.back() != id) canvas.framebuffer_stack.push_back(id);
            }
            else {
                auto& stack = canvas.framebuffer_stack;
                stack.erase(std::remove(stack.begin() + 1, stack.end(), id), stack.end());
            }
            canvas.fbo = canvas.framebuffer_stack.back();
            eng.log(std::string("FRAMEBUFFER ") + (use ? "push " : "pop ") + std::to_string(id));
        } else if (cmd.op == "DRAW") {
            if (obj.artifact && !obj.artifact->linked_for(eng.device_generation)) {
                std::string error;
                obj.artifact = eng.materialize_artifact(obj.artifact->portable,
                    obj.artifact->default_has_depth, error, obj.artifact->evaluator, {}, false);
                if (!error.empty()) throw std::runtime_error("DRAW Program " + std::to_string(id) + ": " + error);
            }
            // Native handle wrappers do not promise noexcept moves. Prepare
            // directly in a reserved queue slot; rollback pops it on failure.
            vispy::inputs::batches::ReservedBack admission(canvas.pending);
            auto& snap = admission.value();
            snap.staged_admission = true;
            snap.artifact = obj.artifact;
            if (!snap.artifact) throw std::runtime_error("program has not been linked");
            snap.canvas_id = canvas_id;
            snap.mode = cmd.args.size() > 1 ? cmd.args[1].s : "triangles";
            snap.logical_topology = logical_draw_topology(snap.mode);
            const bool line_draw = snap.mode == "lines" || snap.mode == "line_strip" || snap.mode == "line_loop";
            snap.artifact = vispy::points::select_draw_artifact(snap.mode == "points", obj.artifact,
                obj.point_artifact, [&](const auto& original) {
                std::string error;
                auto point = eng.make_artifact(original->portable->source_vertex, original->portable->source_fragment,
                    error, original->portable->options.base_level_sampling, original->default_has_depth, true,
                    original->portable->options.vertex_identity, original->portable->derivative_mode, false);
                if (!error.empty()) throw std::runtime_error("DRAW points: " + error);
                return point;
            });
            if (!snap.artifact->linked_for(eng.device_generation)) {
                std::string error;
                obj.point_artifact = eng.materialize_artifact(snap.artifact->portable,
                    snap.artifact->default_has_depth, error, snap.artifact->evaluator, {}, false);
                if (!error.empty()) throw std::runtime_error("DRAW points: " + error);
                snap.artifact = obj.point_artifact;
            }
            eng.capture_target(canvas, snap);
            snap.stencil_face_split = stencil_face_route(snap.state, snap.logical_topology, true) == StencilFaceRoute::OrderedTwoFaces;
            bool generated_line = false;
            if (line_draw) {
                vispy::lines::OrdinaryLineInterfaceUsage usage;
                for (const auto& varying : snap.artifact->portable->varyings) {
                    const uint64_t end = uint64_t(varying.location) +
                        uint64_t(varying.value_type.columns) * (varying.array_size ? varying.array_size : 1);
                    // Normalization declares the same typed varying interface
                    // in both render stages, including matrix/array spans.
                    usage.vertex_locations = std::max(usage.vertex_locations, end);
                    usage.fragment_locations = std::max(usage.fragment_locations, end);
                }
                usage.fragment_builtin_variables = vispy::lines::fragment_inter_stage_builtin_variables(
                    snap.artifact->portable->spv_frag);
                generated_line = vispy::lines::select_line_render_route(
                    vispy::lines::state(snap.state.line_width, snap.state.line_smooth), usage,
                    eng.info.max_inter_stage_shader_variables) == vispy::lines::LineRenderRoute::Generated;
            }
            snap.clear = false;
            std::memcpy(snap.clear_color, canvas.clear_color, sizeof(snap.clear_color));
            auto draw_integer = [&](int64_t value, const char* name) -> int {
                if (value < 0 || value > std::numeric_limits<int>::max())
                    throw std::runtime_error(std::string("DRAW ") + name + " exceeds native nonnegative count range");
                return static_cast<int>(value);
            };
            int original_index_owner = 0;
            snap.instances = cmd.args.size() > 3 ? draw_integer(cmd.args[3].i, "instances") : 1;
            if (cmd.args.size() > 2 && cmd.args[2].kind == Value::Kind::List) {
                const auto& sel = cmd.args[2].list;
                if (sel.size() == 2) {
                    snap.first = draw_integer(sel[0].i, "first");
                    snap.count = draw_integer(sel[1].i, "count");
                } else if (sel.size() >= 3) {
                    int index_id = static_cast<int>(sel[0].i);
                    original_index_owner = index_id;
                    snap.index_type = lower_token(sel[1].s);
                    snap.index_count = draw_integer(sel[2].i, "index count");
                    snap.count = snap.index_count;
                    if (eng.objects.count(index_id)) snap.index = eng.objects[index_id].buffer;
                    if (!snap.index) throw std::runtime_error("DRAW missing index buffer " + std::to_string(index_id));
                    if (snap.index_type != "unsigned_byte" && snap.index_type != "unsigned_short" && snap.index_type != "unsigned_int")
                        throw std::runtime_error("DRAW unsupported index type " + snap.index_type);
                    const size_t index_bytes = snap.index_type == "unsigned_int" ? 4 : snap.index_type == "unsigned_byte" ? 1 : 2;
                    if (snap.index_count < 0 || static_cast<size_t>(snap.index_count) * index_bytes > snap.index->cpu.size())
                        throw std::runtime_error("DRAW index range exceeds index buffer");
                }
            }
            if (snap.first < 0 || snap.count < 0)
                throw std::runtime_error("DRAW first/count must be nonnegative");
            std::shared_ptr<DrawSnap::LineInputs> original_line;
            if (line_draw) {
                original_line = std::make_shared<DrawSnap::LineInputs>();
                auto& original = original_line->selection;
                original.primitive = vispy::lines::mode(snap.mode);
                original.state = vispy::lines::state(snap.state.line_width, snap.state.line_smooth);
                original.first = static_cast<uint64_t>(snap.first);
                original.count = static_cast<uint64_t>(snap.count);
                original.instances = static_cast<uint64_t>(snap.instances);
                original.index = snap.index;
                if (snap.index) original.index_bytes = snap.index_type == "unsigned_int" ? 4 :
                    snap.index_type == "unsigned_byte" ? 1 : 2;
                // Construct only the constant-sized original table here. GPU
                // endpoint budgets apply when preparing the evaluator inputs.
                (void)original.segments();
                original_line->portable = snap.artifact->portable;
                original_line->evaluator = snap.artifact->evaluator;
                original_line->original_artifact = snap.artifact;
            }
            if (!generated_line) eng.prepare_index_inputs(obj, snap, id, original_index_owner);
            if (snap.artifact) {
                const bool point_sprites = snap.artifact->portable->point_sprites;
                vispy::points::Selection point_selection;
                uint64_t point_rows = 0, point_index_identity = 0, point_index_revision = 0;
                if (point_sprites) {
                    point_selection.first = snap.first;
                    point_selection.count = snap.count;
                    point_selection.instances = snap.instances;
                    if (snap.index) {
                        point_selection.indices = snap.index->cpu;
                        point_selection.index_bytes = snap.index_type == "unsigned_int" ? 4 : snap.index_type == "unsigned_byte" ? 1 : 2;
                        point_index_identity = snap.index->identity;
                        point_index_revision = snap.index->revision;
                    }
                    vispy::inputs::validate_selection(point_selection);
                    point_rows = vispy::points::batches::checked_product(point_selection.count, point_selection.instances);
                }
                snap.uniforms.assign(snap.artifact->portable->uniform_bytes, 0);
                for (const auto& uni : snap.artifact->portable->uniforms) {
                    if (uni.name == "vispy_point_viewport") {
                        const float viewport[] = {static_cast<float>(snap.viewport[2] < 0 ? snap.target_width : snap.viewport[2]),
                                                  static_cast<float>(snap.viewport[3] < 0 ? snap.target_height : snap.viewport[3])};
                        std::string error;
                        if (!pack_uniform_value(uni, viewport, sizeof(viewport), snap.uniforms.data(), snap.uniforms.size(), &error))
                            throw std::runtime_error("point viewport: " + error);
                        continue;
                    }
                    auto fit = obj.f_uniforms.find(uni.name);
                    std::string error;
                    if (fit != obj.f_uniforms.end() && !pack_uniform_value(uni, fit->second.data(), fit->second.size() * 4,
                            snap.uniforms.data(), snap.uniforms.size(), &error)) {
                        throw std::runtime_error("UNIFORM " + uni.name + ": " + error);
                    }
                    auto iit = obj.i_uniforms.find(uni.name);
                    if (iit != obj.i_uniforms.end() && !pack_uniform_value(uni, iit->second.data(), iit->second.size() * 4,
                            snap.uniforms.data(), snap.uniforms.size(), &error)) {
                        throw std::runtime_error("UNIFORM " + uni.name + ": " + error);
                    }
                    for (int n = 0; n < uni.array_size; ++n) {
                        NormUniform element = uni;
                        element.offset += n * uni.array_stride;
                        element.array_size = 0;
                        element.size = uni.array_stride;
                        element.array_stride = 0;
                        std::string name = uni.name + "[" + std::to_string(n) + "]";
                        auto floats = obj.f_uniforms.find(name);
                        auto ints = obj.i_uniforms.find(name);
                        if (floats != obj.f_uniforms.end() && !pack_uniform_value(element, floats->second.data(),
                            floats->second.size() * 4, snap.uniforms.data(), snap.uniforms.size(), &error))
                            throw std::runtime_error("UNIFORM " + name + ": " + error);
                        if (ints != obj.i_uniforms.end() && !pack_uniform_value(element, ints->second.data(),
                            ints->second.size() * 4, snap.uniforms.data(), snap.uniforms.size(), &error))
                            throw std::runtime_error("UNIFORM " + name + ": " + error);
                    }
                }
                for (const auto& attr : snap.artifact->portable->attributes) {
                    auto bit = obj.attributes.find(attr.name);
                    if (bit == obj.attributes.end()) {
                        AttrBinding default_value;
                        default_value.type = attr.type;
                        default_value.constant = true;
                        int components = attribute_components(attr.type);
                        default_value.constant_words.assign(components, 0);
                        if (components == 4) default_value.constant_words[3] =
                            vispy::lines::endpoint_constant_word(attr.type, true, 1, 1.0);
                        bit = obj.attributes.emplace(attr.name, std::move(default_value)).first;
                    }
                    AttrBinding binding = bit->second;
                    if (binding.stride < 0 || binding.offset < 0 || binding.divisor < 0)
                        throw std::runtime_error("ATTRIBUTE " + attr.name + ": negative stride/offset/divisor");
                    const int components = attribute_components(attr.type);
                    const int element_bytes = components * 4;
                    if (bit->second.constant) {
                        if (!bit->second.constant_buffer) {
                            auto rev = std::make_shared<BufferRev>();
                            rev->owner = id;
                            rev->cpu.resize(element_bytes, 0);
                            std::memcpy(rev->cpu.data(), bit->second.constant_words.data(),
                                std::min(rev->cpu.size(), bit->second.constant_words.size() * 4));
                            bit->second.constant_buffer = std::move(rev);
                        }
                        binding.stride = 0;
                        binding.offset = 0;
                        binding.divisor = 0;
                        snap.vertices.push_back(bit->second.constant_buffer);
                    } else if (eng.objects.count(bit->second.buffer_id)) {
                        auto rev = eng.objects[bit->second.buffer_id].buffer;
                        if (!rev) throw std::runtime_error("ATTRIBUTE " + attr.name + ": missing buffer allocation");
                        if (binding.stride == 0) binding.stride = element_bytes;
                        snap.vertices.push_back(rev);
                    } else throw std::runtime_error("ATTRIBUTE " + attr.name + ": missing buffer");
                    snap.bindings.push_back(std::move(binding));
                }
                for (const auto& sampler : snap.artifact->portable->samplers) {
                    std::shared_ptr<TextureRev> bound;
                    auto sit = obj.textures.find(sampler.name);
                    if (sit != obj.textures.end() && eng.objects.count(sit->second)) {
                        bound = eng.objects[sit->second].texture;
                    }
                    // Every active reflected sampler needs its layout entry.
                    // Declaration-only sampler uniforms were removed from
                    // portable metadata and cannot consume binding limits.
                    if (!bound) bound = eng.placeholder_texture(sampler);
                    validate_sampler_storage(sampler, *bound);
                    snap.textures.push_back(bound);
                }
                eng.capture_integer_sampling(snap);
                if (original_line) {
                    // Endpoint GLSL is regenerated as compute. Carry the exact
                    // retained sampler policy in its immutable original identity
                    // before that generated stage is lowered, without preparing
                    // an unused ordinary graphics pipeline for generated lines.
                    if (!snap.integer_sampling_policies.empty()) {
                        eng.prepare_draw_sampling(snap, false);
                        original_line->original_artifact = snap.artifact;
                        original_line->portable = snap.artifact->portable;
                    }
                    original_line->vertices = snap.vertices;
                    original_line->bindings = snap.bindings;
                    original_line->uniforms = snap.uniforms;
                    original_line->textures = snap.textures;
                    const int vw = snap.viewport[2] < 0 ? snap.target_width : snap.viewport[2];
                    const int vh = snap.viewport[3] < 0 ? snap.target_height : snap.viewport[3];
                    if (generated_line && original_line->selection.segments().size() && vw > 0 && vh > 0) {
                        eng.prepare_line_render(snap, *original_line, obj, id);
                    } else if (generated_line) {
                        // Empty selections/viewport have no procedural draw.
                        // Optional endpoint diagnostics retain their existing
                        // capture behavior without activating a render consumer.
                        snap.count = 0;
                        snap.instances = 0;
                    }
                    if (!snap.line_work && !snap.line_chunks && canvas.diagnostic_line_endpoints) {
                        snap.line_work = std::make_shared<LineWork>(eng.prepare_line_resources(
                            *original_line, original_line->original_artifact, obj, id));
                        original_line->evaluator = snap.line_work->evaluator;
                    }
                    snap.line_inputs = std::move(original_line);
                }
                if (point_sprites) {
                    std::vector<uint32_t> widths;
                    std::vector<vispy::points::PackedSource> sources;
                    for (size_t n = 0; n < snap.bindings.size(); ++n) {
                        const auto& attr = snap.artifact->portable->attributes[n];
                        const auto& binding = snap.bindings[n];
                        const auto& source = snap.vertices[n];
                        const uint32_t width = attribute_components(attr.type) * 4;
                        widths.push_back(width);
                        sources.push_back({source->cpu, source->identity, source->revision,
                            static_cast<uint64_t>(binding.offset), static_cast<uint64_t>(binding.stride),
                            width, static_cast<uint64_t>(binding.divisor), attr.name});
                    }
                    const auto layout = vispy::points::partitioned_layout(widths, eng.info.max_vertex_attributes,
                        eng.info.max_vertex_buffers, eng.info.max_vertex_buffer_stride);
                    const vispy::points::PackedLayout packed{layout.offsets,
                        layout.streams.empty() ? 0 : layout.streams.front().stride};
                    const bool whole_fits = layout.streams.size() <= 1 && point_rows <= INT32_MAX &&
                        (sources.empty() || point_rows <= eng.input_buffer_limit() / packed.stride) &&
                        (!snap.artifact->portable->point_identity_binding ||
                         point_rows <= std::min(eng.input_buffer_limit(), eng.info.max_storage_buffer_size) / 8);
                    if (!point_rows) {
                        snap.vertices.clear(); snap.point_identity.reset();
                        snap.vertex_slots = layout.slots;
                    } else if (!whole_fits) {
                        eng.prepare_batched_point_inputs(obj, snap, id, original_index_owner,
                            point_selection, sources, layout);
                    } else {
                        // Geometry cache owns only derived children. Source revisions
                        // are represented by identities, never retained parents.
                        if (!obj.point_geometry_cache) obj.point_geometry_cache = std::make_shared<BufferRev>();
                        const auto source_key = vispy::points::packed_source_key(sources,
                            point_index_identity, point_index_revision, point_selection.index_bytes);
                        obj.point_geometry_index_owner = snap.index ? snap.index->owner : 0;
                        vispy::points::refresh_sources(obj.point_geometry_sources, source_key, obj.point_geometry_cache->derived);
                        if (!sources.empty()) {
                            const auto key = vispy::points::conversion_key("packed-users", point_selection,
                                obj.point_geometry_cache->identity, 0, point_index_identity, point_index_revision) + source_key;
                            auto [converted, built] = vispy::points::cached_conversion(obj.point_geometry_cache->derived, key, [&] {
                                auto result = std::make_shared<BufferRev>();
                                result->owner = id;
                                result->cpu = vispy::points::packed_data(point_selection, sources, packed, eng.input_buffer_limit());
                                return result;
                            });
                            if (built) {
                                ++eng.probe.point_conversion_builds;
                                eng.probe.point_conversion_bytes += converted->cpu.size();
                            }
                            snap.vertices.assign(1, std::move(converted));
                        } else snap.vertices.clear();
                        snap.vertex_slots.assign(snap.bindings.size(), 0);
                        if (!snap.vertices.empty()) snap.vertex_streams.push_back({0, packed.stride, true});
                        if (snap.artifact->portable->point_identity_binding) {
                            if (!obj.primitive_indices) obj.primitive_indices = std::make_shared<BufferRev>();
                            const auto source = snap.index ? snap.index : obj.primitive_indices;
                            const auto key = vispy::points::conversion_key("identity-storage", point_selection,
                                source->identity, source->revision, point_index_identity, point_index_revision);
                            auto [converted, built] = vispy::points::cached_conversion(source->derived, key, [&] {
                                auto result = std::make_shared<BufferRev>();
                                result->owner = id;
                                result->cpu = vispy::points::identity_data(point_selection,
                                    std::min(eng.input_buffer_limit(), eng.info.max_storage_buffer_size));
                                return result;
                            });
                            if (built) {
                                ++eng.probe.point_conversion_builds;
                                eng.probe.point_conversion_bytes += converted->cpu.size();
                            }
                            snap.point_identity = std::move(converted);
                        }
                    }
                    for (size_t n = 0; n < snap.bindings.size(); ++n) {
                        snap.bindings[n].offset = static_cast<int>(layout.offsets[n]);
                        snap.bindings[n].stride = static_cast<int>(layout.streams[layout.slots[n]].stride);
                        snap.bindings[n].divisor = 1;
                    }
                    snap.packed_point_inputs = true;
                    // A batched snapshot is one semantic draw. Its immutable
                    // owner supplies each physical instance count at encoding.
                    snap.instances = snap.point_batch_inputs ? 1 : static_cast<int>(point_rows);
                    snap.count = point_rows ? 6 : 0;
                    snap.first = 0;
                    snap.index.reset();
                    snap.index_count = 0;
                    snap.index_type.clear();
                    snap.mode = "triangles";
                    snap.state.cull_enabled = false;
                    snap.state.polygon_offset_fill = false;
                    snap.state.stencil_back = snap.state.stencil_front;
                } else if (!generated_line)
                    eng.prepare_vertex_inputs(obj, snap, id, original_index_owner);
            }
            // Only the final structural identity (ordinary/point/compact/
            // batch) and its captured sampler policy may reach Dawn/Tint.
            // Generated consumers prepare their own modules above. Empty
            // generated selections retain the existing no-pipeline route.
            if (!generated_line) eng.prepare_draw_sampling(snap);
            if (snap.stencil_face_split && snap.count > 0 && snap.instances > 0) {
                if (!snap.batch_inputs || snap.mode != "triangles") throw std::runtime_error("DRAW stencil faces: ordered triangle-list owner required");
                const auto error = ordinary_stencil_replay_error(snap.artifact->portable->spv_vert, snap.artifact->portable->spv_frag);
                if (!error.empty()) throw std::runtime_error(error);
            }
            if (snap.line_work && canvas.diagnostic_line_endpoints && canvas.capture_line_endpoints)
                snap.line_work->capture = eng.reserve_line_capture(canvas_id, *snap.line_work);
            snap.staged_admission = false;
            admission.publish();
            canvas.clear_pending = false;
            eng.update_work_peaks();
            canvas.swapchain_current = false;
            eng.log("record DRAW program=" + std::to_string(id));
        }
      } catch (const std::exception& error) {
        eng.drop_next = eng.deleted_now;
        throw std::runtime_error("GLIR " + cmd.op + " object=" +
            (cmd.op == "FUNC" && !cmd.args.empty() ? std::string("context ") + cmd.args.front().s : std::to_string(arg_id(cmd, 0))) +
            ": " + error.what());
      }
    }
    eng.drop_next = eng.deleted_now;
}

void execute_commands(int canvas_id, const std::vector<Command>& commands,
                      uint64_t binding_decode_ns, uint64_t binding_decode_bytes) {
    execute_commands_impl(canvas_id, commands, nullptr, binding_decode_ns, binding_decode_bytes, {});
}

void execute_owned_commands(int canvas_id, std::vector<Command>&& commands,
                            uint64_t binding_decode_ns, uint64_t binding_decode_bytes,
                            const UploadCaptureStats& capture_stats) {
    // Own even the non-transferred payloads until the interpreter returns or throws.
    auto owned = std::move(commands);
    execute_commands_impl(canvas_id, owned, &owned, binding_decode_ns, binding_decode_bytes, capture_stats);
}

void finish_canvas(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.probe.finish_calls++;
    auto it = eng.canvases.find(canvas_id);
    if (it == eng.canvases.end()) return;
    eng.finish_target(it->second, true);
}

vispy::lines::LineOwnershipSnapshot diagnostic_peek_line_ownership(int canvas_id) {
    using Snapshot = vispy::lines::LineOwnershipSnapshot;
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    // No init_device, poll, ProcessEvents, WaitAny, native descriptor query,
    // collector or cache access. Only scalar/owned value copies leave the lock.
    auto bounded = [](size_t count, size_t limit, const char* message) {
        if (count > limit) throw std::length_error(message);
    };
    auto text = [&](std::pmr::string& destination, const std::string& value) {
        bounded(value.size(), Snapshot::max_error_bytes, "line ownership: diagnostic string exceeds bound");
        destination.assign(value.data(), value.size());
    };
    bounded(eng.tickets.size(), eng.frame_slots, "line ownership: Ticket retention exceeds frame slots");
    bounded(eng.frame_slots, Snapshot::max_frame_slots, "line ownership: frame-slot observation limit");
    bounded(eng.line_captures.size(), Snapshot::max_captures, "line ownership: capture retention limit");
    bounded(eng.query_segments.size(), eng.frame_slots * vispy::timing::max_submissions_per_frame,
            "line ownership: query-segment retention limit");
    Snapshot result;
    result.canvas_id = canvas_id;
    result.generation = eng.device_generation;
    result.frame_slots = eng.frame_slots;
    result.capture_charge_bytes = eng.line_capture_bytes;
    result.terminal_record_limit = eng.terminal_record_limit;
    const auto& probe = eng.probe;
#define COPY_OWNERSHIP_COUNTER(name) result.counters.name = probe.name
    COPY_OWNERSHIP_COUNTER(dawn_queue_submits);
    COPY_OWNERSHIP_COUNTER(draw_calls);
    COPY_OWNERSHIP_COUNTER(line_endpoint_dispatches);
    COPY_OWNERSHIP_COUNTER(line_endpoint_rows);
    COPY_OWNERSHIP_COUNTER(compute_passes);
    COPY_OWNERSHIP_COUNTER(retired_tickets);
    COPY_OWNERSHIP_COUNTER(completion_waits);
    COPY_OWNERSHIP_COUNTER(finish_calls);
    COPY_OWNERSHIP_COUNTER(timestamp_query_sets);
    COPY_OWNERSHIP_COUNTER(timestamp_resolves);
    COPY_OWNERSHIP_COUNTER(timestamp_readbacks);
    COPY_OWNERSHIP_COUNTER(buffer_allocations);
    COPY_OWNERSHIP_COUNTER(bind_group_creations);
    COPY_OWNERSHIP_COUNTER(deferred_frames);
    COPY_OWNERSHIP_COUNTER(uniform_upload_bytes);
    COPY_OWNERSHIP_COUNTER(line_endpoint_conversion_builds);
    COPY_OWNERSHIP_COUNTER(line_endpoint_conversion_bytes);
    COPY_OWNERSHIP_COUNTER(line_endpoint_upload_bytes);
#undef COPY_OWNERSHIP_COUNTER
    result.counters.successful_ticket_retirements = eng.successful_ticket_retirements;
    result.counters.failed_ticket_retirements = eng.failed_ticket_retirements;
    result.counters.query_map_callbacks_completed = eng.query_map_callbacks_completed->load(std::memory_order_relaxed);
    if (eng.line_pool) {
        result.pool_limits = eng.line_pool->limits();
        bounded(result.pool_limits.max_slots, Snapshot::max_pool_slots, "line ownership: pool-slot observation limit");
        const auto count = eng.line_pool->slot_snapshot_count();
        bounded(count, result.pool_limits.max_slots, "line ownership: retained pool exceeds its declared limit");
        std::array<NativeLinePool::SlotSnapshot, Snapshot::max_pool_slots> rows;
        eng.line_pool->snapshot_slots(rows);
        result.slots.reserve(count);
        for (size_t index = 0; index < count; ++index) {
            const auto& row = rows[index];
            result.slots.push_back({row.slot_id, row.generation, row.state, row.capacities, row.extra_control_bytes});
        }
        const auto stats = eng.line_pool->stats();
        result.pool = {stats.slots, stats.busy_slots, stats.owned_capacity_bytes, stats.control_bytes};
        result.counters.line_resource_pool_hits = stats.hits;
        result.counters.line_resource_pool_evictions = stats.evictions;
        result.counters.line_resource_pool_deferrals = stats.deferrals;
    }
    result.tickets.reserve(eng.tickets.size());
    size_t external_count = 0;
    for (const auto& ticket : eng.tickets) if (ticket->line_resources) {
        bounded(ticket->line_resources->size(), Snapshot::max_pool_slots, "line ownership: Ticket lease observation limit");
        external_count += ticket->line_resources->size();
    }
    bounded(external_count, Snapshot::max_external_slots, "line ownership: external lease observation limit");
    result.external_slots.reserve(external_count);
    for (const auto& ticket : eng.tickets) {
        vispy::lines::OwnershipTicket row(result.memory_resource());
        row.canvas_id = ticket->canvas_id;
        row.ticket_id = ticket->id;
        row.generation = ticket->generation;
        row.callback_complete = ticket->complete.load();
        row.retirement_processed = ticket->diagnostic_retirement_counted;
        if (row.callback_complete) {
            row.callback_ok = ticket->ok;
            text(row.error, ticket->error);
        }
        row.has_encoding_validation = bool(ticket->encoding_validation);
        if (row.has_encoding_validation) {
            row.encoding_validation_complete = ticket->encoding_validation->done.load();
            if (row.encoding_validation_complete) {
                row.encoding_validation_ok = ticket->encoding_validation->ok;
                text(row.validation_error, ticket->encoding_validation->error);
            }
        }
        if (ticket->queries) {
            row.frame_id = ticket->queries->frame_id;
            row.paint_token = ticket->queries->work.paint_token;
        }
        if (ticket->line_resources) {
            const auto count = ticket->line_resources->size();
            bounded(count, Snapshot::max_pool_slots, "line ownership: Ticket lease observation limit");
            row.slot_ids.reserve(count);
            for (size_t index = 0; index < count; ++index) {
                const auto& lease = ticket->line_resources->at(index);
                row.slot_ids.push_back(lease.id());
                auto retained = [&](const auto& value) {
                    return value.slot_id == lease.id() && value.generation == lease.generation();
                };
                if (std::none_of(result.slots.begin(), result.slots.end(), retained) &&
                        std::none_of(result.external_slots.begin(), result.external_slots.end(), retained)) {
                    result.external_slots.push_back({lease.id(), lease.generation(), lease.state(),
                        lease.capacities(), lease.extra_control_bytes()});
                }
            }
        }
        result.tickets.push_back(std::move(row));
    }
    result.captures.reserve(eng.line_captures.size());
    for (const auto& capture : eng.line_captures) {
        if (capture->canvas_id != canvas_id) continue;
        const auto& native = capture->result;
        vispy::lines::OwnershipCapture row(result.memory_resource());
        row.canvas_id = capture->canvas_id;
        row.capture_id = native.capture_id;
        row.ticket_id = native.ticket_id;
        row.frame_id = capture->frame_id;
        row.paint_token = capture->paint_token;
        row.generation = native.device_generation;
        row.charged_bytes = capture->charged_bytes;
        row.readback_capacity = capture->readback ? capture->allocation_bytes : 0;
        for (size_t index = 0; index < capture->parts.size(); ++index)
            if (capture->parts[index].readback) row.readback_capacity += capture->chunk_plan.parts[index].raw_bytes;
        row.ticket_finished = capture->ticket_finished;
        text(row.status, native.status);
        text(row.error, native.error);
        result.captures.push_back(std::move(row));
    }
    result.query_segments.reserve(eng.query_segments.size());
    for (const auto& segment : eng.query_segments) {
        std::lock_guard<std::mutex> segment_lock(segment->mutex);
        result.query_segments.push_back({segment->canvas_id, segment->ticket_id, segment->generation,
            segment->frame_id, segment->paint_token, segment->submission_index,
            segment->buffer_capacity, segment->buffer_capacity,
            segment->map_requested, segment->map_callback_complete});
    }
    std::array<const FrameMark::Queries*, Snapshot::max_frames> frames{};
    size_t frame_count = 0;
    auto add_frame = [&](const auto& frame) {
        if (!frame || frame->canvas_id != canvas_id) return;
        if (std::find(frames.begin(), frames.begin() + frame_count, frame.get()) != frames.begin() + frame_count) return;
        bounded(frame_count + 1, frames.size(), "line ownership: frame observation limit");
        frames[frame_count++] = frame.get();
    };
    for (const auto& frame : eng.frame_works) add_frame(frame);
    for (const auto& frame : eng.query_frames) add_frame(frame);
    for (const auto& ticket : eng.tickets) add_frame(ticket->queries);
    const auto canvas = eng.canvases.find(canvas_id);
    if (canvas != eng.canvases.end()) {
        if (canvas->second.frame_mark) add_frame(canvas->second.frame_mark->queries);
        const auto& queued = canvas->second.queued_frames;
        bounded(queued.size(), eng.frame_slots, "line ownership: queued batch observation limit");
        result.queued.reserve(queued.size());
        for (const auto& batch : queued) {
            vispy::lines::OwnershipQueuedBatch row(result.memory_resource());
            row.queue_id = batch.id;
            row.generation = batch.generation;
            row.draw_count = std::count_if(batch.draws.begin(), batch.draws.end(),
                [](const auto& draw) { return draw.origin == vispy::render::SnapshotOrigin::UserDraw; });
            if (batch.mark) {
                add_frame(batch.mark->queries);
                if (batch.mark->queries) {
                    row.frame_id = batch.mark->queries->frame_id;
                    row.paint_token = batch.mark->queries->work.paint_token;
                }
            }
            std::array<uint64_t, Snapshot::max_captures> capture_ids{};
            size_t count = 0;
            Engine::for_each_draw_leaf(batch.draws, [&](const auto& draw) {
                if (!draw.line_work || !draw.line_work->capture) return;
                const auto id = draw.line_work->capture->result.capture_id;
                if (std::find(capture_ids.begin(), capture_ids.begin() + count, id) != capture_ids.begin() + count) return;
                bounded(count + 1, Snapshot::max_captures, "line ownership: queued capture observation limit");
                capture_ids[count++] = id;
            });
            row.capture_ids.assign(capture_ids.begin(), capture_ids.begin() + count);
            result.queued.push_back(std::move(row));
        }
    }
    result.frames.reserve(frame_count);
    for (size_t index = 0; index < frame_count; ++index) {
        const auto& frame = *frames[index];
        const auto& work = frame.work;
        vispy::lines::OwnershipFrame row(result.memory_resource());
        row.frame_id = frame.frame_id;
        row.paint_token = work.paint_token;
        row.generation = frame.device_generation;
        row.submissions = work.submissions;
        row.outstanding = work.outstanding;
        row.queued_batches = work.queued_batches;
        row.gpu_timing = frame.gpu_timing;
        row.closed = work.closed;
        row.receipt_emitted = work.emitted;
        row.gpu_result_emitted = frame.gpu_result_emitted;
        text(row.failure, work.failure);
        text(row.error, work.error);
        result.frames.push_back(std::move(row));
    }
    if (result.control_capacity_bytes() > Snapshot::max_control_bytes)
        throw std::length_error("line ownership: diagnostic control capacity limit");
    return result;
}

void diagnostic_configure_line_endpoints(int canvas_id, bool enabled, bool capture) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end()) throw std::runtime_error("lines: diagnostic canvas does not exist");
    found->second.diagnostic_line_endpoints = enabled;
    found->second.capture_line_endpoints = capture;
}

std::vector<LineEndpointReadback> diagnostic_line_endpoints(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    // This explicit quality collector flushes owned work and may wait. It is
    // never called by interactive submission or the normal event-loop path.
    try {
        eng.poll();
        const auto canvas = eng.canvases.find(canvas_id);
        // A drained canvas has no submitted work to finish. Retired failed
        // captures and repeated empty collection must not register fresh
        // queue-completion waits or process unrelated canvas ownership.
        if (canvas != eng.canvases.end() &&
                (!canvas->second.pending.empty() || !canvas->second.queued_frames.empty() ||
                 canvas->second.clear_pending ||
                 std::any_of(eng.tickets.begin(), eng.tickets.end(), [canvas_id](const auto& ticket) {
                     return ticket->canvas_id == canvas_id;
                 }))) {
            eng.finish_target(canvas->second, false);
        }
        for (const auto& ticket : eng.tickets) if (ticket->canvas_id == canvas_id && ticket->encoding_validation &&
                !ticket->encoding_validation->done.load()) {
            ++eng.probe.completion_waits;
            eng.wait_result(ticket->encoding_validation_future, ticket->encoding_validation);
        }
        eng.poll();
    } catch (const std::exception& error) {
        for (const auto& capture : eng.line_captures) if (capture->canvas_id == canvas_id &&
                (capture->result.status == "pending" || capture->result.status == "encoded" ||
                 capture->result.status == "submitted")) {
            capture->result.status = "failed";
            capture->set_error(error.what());
        }
    }
    std::vector<LineEndpointReadback> records;
    for (auto iterator = eng.line_captures.begin(); iterator != eng.line_captures.end();) {
        auto capture = *iterator;
        if (capture->canvas_id != canvas_id) { ++iterator; continue; }
        auto& result = capture->result;
        if (result.status == "pending" || result.status == "encoded" || result.status == "submitted" ||
                (result.ticket_id && !capture->ticket_finished)) {
            // A timeout is not retirement or failure. Keep the same actual
            // owner and its buffers available for a later explicit collection.
            ++iterator;
            continue;
        }
        if (result.status == "retired" && !capture->parts.empty()) {
            if (!eng.collect_chunk_capture(*capture)) { ++iterator; continue; }
        } else if (result.status == "retired") {
            if (!capture->map_result) {
                auto wait = capture->map_result = std::make_shared<AsyncResult>();
                wait->error.reserve(LineCapture::error_limit);
                capture->map_future = capture->readback.MapAsync(wgpu::MapMode::Read, 0, capture->allocation_bytes,
                    wgpu::CallbackMode::AllowProcessEvents,
                    [wait, owner = capture->readback](wgpu::MapAsyncStatus status, wgpu::StringView message) {
                    wait->ok = status == wgpu::MapAsyncStatus::Success;
                    const auto error = view_to_string(message);
                    wait->error.assign(error.data(), std::min(error.size(), LineCapture::error_limit));
                    wait->done.store(true);
                });
            }
            auto wait = capture->map_result;
            if (!wait->done.load()) {
                ++eng.probe.completion_waits;
                eng.wait_result(capture->map_future, wait);
            }
            if (!wait->done.load()) { ++iterator; continue; }
            if (!wait->ok) {
                result.status = "map_error";
                capture->set_error(wait->error);
            } else {
                const auto* bytes = static_cast<const uint8_t*>(
                    capture->readback.GetConstMappedRange(0, capture->allocation_bytes));
                if (!bytes) {
                    result.status = "map_error";
                    capture->set_error("successful endpoint map returned no owned range");
                } else {
                    result.raw_data.assign(bytes, bytes + capture->allocation_bytes);
                    const uint64_t logical_bytes = uint64_t(result.rows) * result.row_bytes;
                    const auto overwritten = std::find_if(result.raw_data.begin() + logical_bytes,
                        result.raw_data.end(), [](uint8_t value) { return value != 0xcd; });
                    if (overwritten != result.raw_data.end()) {
                        result.status = "padding_error";
                        capture->set_error("endpoint output canary changed at byte=" +
                            std::to_string(overwritten - result.raw_data.begin()));
                    } else {
                        result.data.assign(bytes, bytes + logical_bytes);
                        result.status = "completed";
                    }
                }
                capture->readback.Unmap();
            }
        }
        records.push_back(std::move(result));
        eng.line_capture_bytes -= capture->charged_bytes;
        iterator = eng.line_captures.erase(iterator);
    }
    eng.update_descriptor_accounting();
    return records;
}

void present_canvas(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto it = eng.canvases.find(canvas_id);
    if (it == eng.canvases.end()) return;
    auto& canvas = it->second;
    auto frame = canvas.frame_mark ? canvas.frame_mark->queries : nullptr;
    if (frame) frame->presentation_requested = true;
    try { eng.submit_canvas(canvas, true); }
    catch (const std::exception& error) {
        eng.cancel_frame(frame, "failed", error.what());
        throw;
    }
    // Qt closes explicitly after its alpha tail and existing final present.
    // Standalone native callers retain their historical final-present API.
    if (frame && !canvas.active_paint_token) eng.finalize_query_frame(frame);
}

void benchmark_submit_intermediate(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto& canvas = eng.canvas(canvas_id);
    auto frame = canvas.frame_mark ? canvas.frame_mark->queries : nullptr;
    if (!frame) throw std::runtime_error("benchmark intermediate submission requires an active frame");
    try { eng.submit_canvas(canvas, false); }
    catch (const std::exception& error) {
        eng.cancel_frame(frame, "failed", error.what());
        throw;
    }
}

bool process_events() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    for (auto& [id, canvas] : eng.canvases) {
        if (!canvas.deferred_present) continue;
        auto frame = !canvas.queued_frames.empty() && canvas.queued_frames.front().mark ?
            canvas.queued_frames.front().mark->queries : nullptr;
        try { eng.submit_canvas(canvas, false, true); }
        catch (const std::exception& error) {
            eng.cancel_frame(frame, "failed", error.what());
            throw;
        }
    }
    eng.poll_query_results();
    return !eng.tickets.empty() || !eng.query_segments.empty() || !eng.query_frames.empty() ||
        std::any_of(eng.canvases.begin(), eng.canvases.end(), [](const auto& item) { return item.second.deferred_present; });
}

std::vector<int> canvas_viewport(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end()) throw std::runtime_error("viewport: missing canvas");
    const auto& canvas = found->second;
    return {canvas.viewport[0], canvas.viewport[1],
            canvas.viewport[2] < 0 ? canvas.width : canvas.viewport[2],
            canvas.viewport[3] < 0 ? canvas.height : canvas.viewport[3]};
}

bool frame_ready(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end() || !found->second.alive || found->second.active_paint_token ||
        found->second.width <= 0 || found->second.height <= 0) return false;
    if (!eng.init_device()) return false;
    const auto& canvas = found->second;
    const auto owner = canvas.frame_mark ? canvas.frame_mark->queries : nullptr;
    const bool reserved = owner && owner->measured && owner->work.reserved_unpainted();
    return eng.frame_capacity(canvas).ready(reserved, reserved && owner->gpu_timing);
}

bool benchmark_frame_request_ready(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    const auto found = eng.canvases.find(canvas_id);
    if (!eng.device_ready || found == eng.canvases.end()) return false;
    const auto& canvas = found->second;
    if (!canvas.alive || canvas.width <= 0 || canvas.height <= 0 || canvas.frame_mark ||
        canvas.active_paint_token || !canvas.pending.empty() || !canvas.queued_frames.empty()) return false;
    // The collector already pumps callbacks before observing this predicate.
    // This API neither polls nor creates a second owner for the same paint.
    return eng.frame_capacity(canvas).ready();
}

void configure_frame_slots(int slots) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    if (slots < 1 || slots > 8) throw std::runtime_error("frame slots must be between 1 and 8");
    eng.poll();
    if (!eng.tickets.empty() || !eng.query_frames.empty() || !eng.query_segments.empty() || !eng.frame_works.empty() || !eng.gpu_records.empty())
        throw std::runtime_error("frame slots can change only when submissions and query callbacks are idle");
    for (const auto& [id, canvas] : eng.canvases)
        if (!canvas.pending.empty() || !canvas.queued_frames.empty() || canvas.frame_mark)
            throw std::runtime_error("frame slots can change only when frames are idle");
    eng.frame_slots = static_cast<size_t>(slots);
}

void benchmark_begin_frame(int canvas_id, uint64_t frame_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end() || !found->second.alive)
        throw std::runtime_error("benchmark begin: missing canvas");
    auto& canvas = found->second;
    if (!eng.init_device()) throw std::runtime_error(eng.info.error);
    if (canvas.frame_mark)
        throw std::runtime_error("benchmark begin: previous frame has not reached presentation");
    if (!canvas.queued_frames.empty())
        throw std::runtime_error("benchmark begin: deferred frames must drain before recording another frame");
    if (!canvas.pending.empty())
        throw std::runtime_error("benchmark begin: commands already recorded before frame timestamp");
    if (canvas.last_frame_id && frame_id <= *canvas.last_frame_id)
        throw std::runtime_error("benchmark begin: frame IDs must increase");
    eng.start_frame(canvas, frame_id, true);
    canvas.last_frame_id = frame_id;
}

VulkanMemoryWindow benchmark_memory_window_begin() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    if (eng.memory_window_token) throw std::runtime_error("allocation window: overlapping runtime owner");
    VulkanMemoryWindow record;
    if (!eng.layer_memory_window_begin || !eng.layer_memory_window_end) return record;
    if (!eng.memory_window_idle()) throw std::runtime_error("allocation window: begin requires retired warm work");
    if (!eng.layer_memory_window_begin(&record, sizeof(record))) return {};
    if (record.status == VulkanMemoryWindowStatus::Active && record.token) {
        eng.memory_window_token = record.token;
        eng.memory_window_generation = eng.device_generation;
        eng.memory_window_invalidations = eng.device_lost ? WindowDeviceLost : 0;
    }
    return record;
}

VulkanMemoryWindow benchmark_memory_window_end(uint64_t token, bool cancel) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    if (!token || token != eng.memory_window_token) throw std::runtime_error("allocation window: missing or stale token");
    return finish_vulkan_memory_window(cancel, [&eng] { eng.poll(); },
        [&eng] { return eng.memory_window_idle(); },
        [&eng](bool cancelled) { return eng.close_memory_window(cancelled); });
}

uint64_t begin_canvas_paint(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end() || !found->second.alive)
        throw std::runtime_error("begin canvas paint: missing canvas");
    auto& canvas = found->second;
    if (canvas.active_paint_token) throw std::runtime_error("begin canvas paint: nested paint ownership");
    if (!eng.init_device()) throw std::runtime_error(eng.info.error);
    if (!eng.next_paint_token || eng.next_paint_token == UINT64_MAX)
        throw std::runtime_error("begin canvas paint: token overflow");
    auto frame = canvas.frame_mark ? canvas.frame_mark->queries : eng.start_frame(canvas, 0, false);
    const auto token = eng.next_paint_token++;
    frame->work.bind_paint(token);
    frame->work.expect_surface(bool(canvas.surface) || bool(canvas.surface_owner));
    frame->paint_token = token; frame->frame_scope = "qt_paint";
    canvas.active_paint_token = token;
    return token;
}

void end_canvas_paint(int canvas_id, uint64_t token) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto& canvas = eng.canvas(canvas_id);
    if (token && canvas.last_paint_aborted && canvas.last_closed_paint_token == token) return;
    if (!token || canvas.active_paint_token != token || !canvas.frame_mark)
        throw std::runtime_error("end canvas paint: stale or inactive token");
    auto frame = canvas.frame_mark->queries;
    if (!canvas.pending.empty() || !frame->presentation_requested) {
        eng.cancel_frame(frame, "failed", "paint ended with unsubmitted work or without its final present request");
        throw std::runtime_error("end canvas paint: final present must precede paint closure");
    }
    canvas.last_closed_paint_token = token; canvas.last_paint_aborted = false;
    canvas.active_paint_token = 0; canvas.frame_mark.reset();
    eng.finalize_query_frame(frame);
    eng.poll_query_results();
}

void abort_canvas_paint(int canvas_id, uint64_t token, const std::string& reason) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end()) return; // destruction already cancelled this owner
    auto& canvas = found->second;
    if (token && canvas.last_closed_paint_token == token && !canvas.active_paint_token) return;
    if (!token || canvas.active_paint_token != token || !canvas.frame_mark)
        throw std::runtime_error("abort canvas paint: stale or inactive token");
    auto frame = canvas.frame_mark->queries;
    eng.cancel_frame(frame, "failed", reason);
    eng.poll_query_results();
}

void benchmark_cancel_frame(int canvas_id, uint64_t frame_id, const std::string& reason) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto& canvas = eng.canvas(canvas_id);
    auto frame = canvas.frame_mark ? canvas.frame_mark->queries : nullptr;
    if (!frame || !frame->measured || frame->frame_id != frame_id ||
        frame->work.paint_token || frame->work.submissions || frame->work.queued_batches)
        throw std::runtime_error("benchmark cancel: request is not the matching unpainted frame");
    eng.cancel_frame(frame, "cancelled", reason);
    eng.poll_query_results();
}

void benchmark_configure_gpu_timing(int canvas_id, bool enabled) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    if (!eng.init_device()) throw std::runtime_error(eng.info.error);
    auto& canvas = eng.canvas(canvas_id);
    if (canvas.frame_mark || !canvas.pending.empty() || !canvas.queued_frames.empty())
        throw std::runtime_error("benchmark GPU timing configuration requires an idle frame");
    for (const auto& frame : eng.query_frames) if (frame->canvas_id == canvas_id)
        throw std::runtime_error("benchmark GPU timing configuration requires collected timing records");
    canvas.gpu_timing_enabled = enabled;
}

std::vector<vispy::timing::FrameResult> benchmark_gpu_timings(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    auto found = eng.gpu_records.find(canvas_id);
    if (!eng.canvases.contains(canvas_id) && found == eng.gpu_records.end() &&
        std::find(eng.terminal_canvases.begin(), eng.terminal_canvases.end(), canvas_id) == eng.terminal_canvases.end())
        throw std::runtime_error("benchmark GPU timings: missing canvas");
    std::vector<vispy::timing::FrameResult> records;
    if (found != eng.gpu_records.end()) {
        records.reserve(found->second.size());
        while (!found->second.empty()) {
            records.push_back(std::move(found->second.front())); found->second.pop_front(); --eng.gpu_record_count;
        }
        eng.gpu_records.erase(found);
    }
    eng.poll_query_results();
    return records;
}

std::vector<BenchmarkCompletion> benchmark_completions(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.poll();
    auto found = eng.completion_records.find(canvas_id);
    if (!eng.canvases.contains(canvas_id) && found == eng.completion_records.end() &&
        std::find(eng.terminal_canvases.begin(), eng.terminal_canvases.end(), canvas_id) == eng.terminal_canvases.end())
        throw std::runtime_error("benchmark completions: missing canvas");
    std::vector<BenchmarkCompletion> records;
    if (found != eng.completion_records.end()) {
        records.reserve(found->second.size());
        while (!found->second.empty()) {
            records.push_back(std::move(found->second.front())); found->second.pop_front(); --eng.completion_record_count;
        }
        eng.completion_records.erase(found);
    }
    return records;
}

SurfaceInfo benchmark_surface_info(int canvas_id) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    auto found = eng.canvases.find(canvas_id);
    if (found == eng.canvases.end())
        throw std::runtime_error("benchmark surface: missing canvas");
    auto& canvas = found->second;
    SurfaceInfo result;
    result.vsync_requested = canvas.vsync;
    result.attached = static_cast<bool>(canvas.surface);
    if (!canvas.surface || !eng.init_device()) {
        result.present_mode = "unconfigured";
        return result;
    }
    eng.configure_surface(canvas);
    if (!canvas.surface_configured) result.present_mode = "unconfigured";
    else if (canvas.present_mode == wgpu::PresentMode::Immediate) result.present_mode = "immediate";
    else if (canvas.present_mode == wgpu::PresentMode::Mailbox) result.present_mode = "mailbox";
    else result.present_mode = "fifo";
    result.pacing_disabled = !canvas.vsync && canvas.surface_configured &&
        canvas.present_mode == wgpu::PresentMode::Immediate;
    return result;
}

Readback read_canvas(int canvas_id, int x, int y, int width, int height, bool alpha, bool floating,
                     const std::string& mode) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    Readback result;
    if (mode != "color" && mode != "depth" && mode != "stencil") {
        result.error = "read_pixels: unknown buffer mode " + mode;
        return result;
    }
    auto it = eng.canvases.find(canvas_id);
    if (it == eng.canvases.end()) {
        result.error = "missing canvas";
        return result;
    }
    eng.finish_target(it->second, true);
    auto& canvas = it->second;
    HostTimer submit_timer(eng.probe.native_submit_ns);
    auto encoder = eng.device.CreateCommandEncoder();
    ++eng.probe.command_encoders;
    auto ticket = std::make_shared<Ticket>();
    ticket->canvas_id = canvas_id;
    uint64_t depth_upload_passes = 0;
    if (canvas.fbo != 0) {
        const auto framebuffer = eng.objects.find(canvas.fbo);
        if (framebuffer != eng.objects.end()) {
            const auto attachment = eng.objects.find(mode == "color" ? framebuffer->second.fb_color :
                mode == "depth" ? framebuffer->second.fb_depth : framebuffer->second.fb_stencil);
            if (attachment != eng.objects.end()) {
                std::unordered_set<TextureRev*> visited;
                depth_upload_passes = eng.pending_depth_upload_passes(attachment->second.texture, visited);
            }
        }
    }
    if (canvas.frame_mark && canvas.frame_mark->queries)
        eng.attach_query_frame(canvas, *ticket,
            ((mode == "depth" || (mode == "stencil" && canvas.fbo == 0 && canvas.samples > 1)) ? 1 : 0) + depth_upload_passes);
    wgpu::Texture source = mode == "color" ? canvas.color : canvas.depth;
    if (canvas.fbo != 0) {
        auto framebuffer = eng.objects.find(canvas.fbo);
        if (framebuffer != eng.objects.end()) {
            const int attachment_id = mode == "color" ? framebuffer->second.fb_color :
                (mode == "depth" ? framebuffer->second.fb_depth : framebuffer->second.fb_stencil);
            source = nullptr;
            auto attachment = eng.objects.find(attachment_id);
            if (attachment != eng.objects.end() && attachment->second.texture) {
                eng.upload_texture(*attachment->second.texture, encoder, ticket.get());
                source = attachment->second.texture->texture;
                ticket->textures.push_back(attachment->second.texture);
            }
        }
    }
    if (!source || width <= 0 || height <= 0) {
        result.error = "empty target";
        return result;
    }
    if (x < 0 || y < 0 || static_cast<uint64_t>(x) + width > source.GetWidth() ||
        static_cast<uint64_t>(y) + height > source.GetHeight()) {
        result.error = "read_pixels rectangle exceeds target bounds";
        return result;
    }
    const bool sample_zero_stencil = mode == "stencil" && source.GetSampleCount() > 1;
    if (mode != "color" && source.GetSampleCount() > 1)
        source = eng.encode_sample_zero_capture(source, encoder, *ticket, mode == "stencil");
    else if (mode == "depth") source = eng.encode_depth_capture(source, encoder, *ticket);
    const auto format = mode == "stencil" ? CaptureFormat{1, 1, 1, CaptureStorage::Unorm8, false} :
                                           capture_format(source.GetFormat());
    // WebGPU requires a whole depth/stencil subresource copy. Crop stencil
    // after mapping instead of issuing an invalid partial texture copy.
    const uint32_t copy_width = mode == "stencil" ? source.GetWidth() : static_cast<uint32_t>(width);
    const uint32_t copy_height = mode == "stencil" ? source.GetHeight() : static_cast<uint32_t>(height);
    const uint32_t copy_x = mode == "stencil" ? 0 : static_cast<uint32_t>(x);
    const uint32_t copy_y = mode == "stencil" ? 0 : static_cast<uint32_t>(y);
    const uint64_t row_bytes = static_cast<uint64_t>(copy_width) * format.texel_bytes;
    const uint64_t padded_row_bytes = (row_bytes + 255u) & ~uint64_t{255};
    const uint64_t buffer_bytes = padded_row_bytes * copy_height;
    if (padded_row_bytes > std::numeric_limits<uint32_t>::max() ||
        buffer_bytes > eng.info.max_buffer_size) {
        result.error = "read_pixels staging buffer exceeds device limits";
        return result;
    }
    const uint32_t bpr = static_cast<uint32_t>(padded_row_bytes);
    wgpu::BufferDescriptor bd;
    bd.size = buffer_bytes;
    bd.usage = wgpu::BufferUsage::CopyDst | wgpu::BufferUsage::MapRead;
    auto buffer = eng.device.CreateBuffer(&bd);
    ++eng.probe.buffer_allocations;
    wgpu::TexelCopyTextureInfo src;
    src.texture = source;
    src.aspect = mode == "stencil" && !sample_zero_stencil ? wgpu::TextureAspect::StencilOnly : wgpu::TextureAspect::All;
    src.origin = {copy_x, copy_y, 0};
    wgpu::TexelCopyBufferInfo dest;
    dest.buffer = buffer;
    dest.layout.bytesPerRow = bpr;
    dest.layout.rowsPerImage = copy_height;
    wgpu::Extent3D extent{copy_width, copy_height, 1};
    encoder.CopyTextureToBuffer(&src, &dest, &extent);
    eng.resolve_ticket_queries(encoder, *ticket);
    auto commands = encoder.Finish();
    eng.queue.Submit(1, &commands);
    eng.commit_texture_uploads(*ticket);
    eng.probe.dawn_queue_submits++;
    ticket->submit_ns = monotonic_ns();
    eng.track_submission(ticket);
    if (ticket->queries) ticket->transient_buffers.push_back(buffer);
    eng.freeze_submission_counters(*ticket, submit_timer);
    auto wait = std::make_shared<AsyncResult>();
    auto future = buffer.MapAsync(wgpu::MapMode::Read, 0, bd.size, wgpu::CallbackMode::WaitAnyOnly,
        [wait](wgpu::MapAsyncStatus status, wgpu::StringView message) {
            wait->ok = status == wgpu::MapAsyncStatus::Success;
            wait->error = view_to_string(message);
            wait->done.store(true);
        });
    ++eng.probe.completion_waits;
    if (!eng.wait_result(future, wait)) {
        result.error = eng.last_error;
        return result;
    }
    const auto* mapped = static_cast<const uint8_t*>(buffer.GetConstMappedRange(0, bd.size));
    int channels = mode == "color" ? (alpha ? 4 : 3) : 1;
    result.width = width;
    result.height = height;
    result.channels = channels;
    const size_t components = static_cast<size_t>(width) * height * channels;
    if (floating) result.floating_rgba.resize(components);
    else result.rgba.resize(components);
    for (int row = 0; row < height; ++row) {
        int src_row = height - 1 - row + (mode == "stencil" ? y : 0);
        const uint8_t* srcp = mapped + static_cast<size_t>(src_row) * bpr +
                              (mode == "stencil" ? static_cast<size_t>(x) : 0);
        for (int col = 0; col < width; ++col) {
            const auto color = read_color(srcp + static_cast<size_t>(col) * format.texel_bytes, format);
            const size_t offset = (static_cast<size_t>(row) * width + col) * channels;
            for (int channel = 0; channel < channels; ++channel) {
                if (floating) result.floating_rgba[offset + channel] = mode == "stencil" ?
                    static_cast<float>(srcp[col]) : color[channel];
                else result.rgba[offset + channel] = capture_byte(color[channel]);
            }
        }
    }
    buffer.Unmap();
    eng.probe.copy_bytes += bd.size;
    return result;
}

Readback read_presented(int canvas_id, int x, int y, int width, int height) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    Readback result;
    auto it = eng.canvases.find(canvas_id);
    if (it == eng.canvases.end() || !it->second.presented || width <= 0 || height <= 0) {
        result.error = "missing presented target";
        return result;
    }
    if (x < 0 || y < 0 || static_cast<uint64_t>(x) + width > it->second.presented.GetWidth() ||
        static_cast<uint64_t>(y) + height > it->second.presented.GetHeight()) {
        result.error = "read_presented rectangle exceeds target bounds";
        return result;
    }
    HostTimer submit_timer(eng.probe.native_submit_ns);
    std::shared_ptr<Ticket> ticket;
    if (it->second.frame_mark && it->second.frame_mark->queries) {
        ticket = std::make_shared<Ticket>();
        ticket->canvas_id = canvas_id;
        eng.attach_query_frame(it->second, *ticket, 0);
        ticket->owned_textures.push_back(it->second.presented);
    }
    uint32_t bpr = (static_cast<uint32_t>(width) * 4u + 255u) & ~255u;
    wgpu::BufferDescriptor bd;
    bd.size = bpr * static_cast<uint32_t>(height);
    bd.usage = wgpu::BufferUsage::CopyDst | wgpu::BufferUsage::MapRead;
    auto buffer = eng.device.CreateBuffer(&bd);
    ++eng.probe.buffer_allocations;
    auto encoder = eng.device.CreateCommandEncoder();
    ++eng.probe.command_encoders;
    wgpu::TexelCopyTextureInfo src;
    src.texture = it->second.presented;
    src.aspect = wgpu::TextureAspect::All;
    src.origin = {static_cast<uint32_t>(std::max(0, x)), static_cast<uint32_t>(std::max(0, y)), 0};
    wgpu::TexelCopyBufferInfo dest;
    dest.buffer = buffer;
    dest.layout.bytesPerRow = bpr;
    dest.layout.rowsPerImage = static_cast<uint32_t>(height);
    wgpu::Extent3D extent{static_cast<uint32_t>(width), static_cast<uint32_t>(height), 1};
    encoder.CopyTextureToBuffer(&src, &dest, &extent);
    auto commands = encoder.Finish();
    eng.queue.Submit(1, &commands);
    eng.probe.dawn_queue_submits++;
    if (ticket) {
        ticket->transient_buffers.push_back(buffer);
        ticket->submit_ns = monotonic_ns();
        eng.track_submission(ticket);
        eng.freeze_submission_counters(*ticket, submit_timer);
    } else submit_timer.finish();
    auto wait = std::make_shared<AsyncResult>();
    auto future = buffer.MapAsync(wgpu::MapMode::Read, 0, bd.size, wgpu::CallbackMode::WaitAnyOnly,
        [wait](wgpu::MapAsyncStatus status, wgpu::StringView message) {
            wait->ok = status == wgpu::MapAsyncStatus::Success;
            wait->error = view_to_string(message);
            wait->done.store(true);
        });
    ++eng.probe.completion_waits;
    if (!eng.wait_result(future, wait)) {
        result.error = eng.last_error;
        return result;
    }
    const auto* mapped = static_cast<const uint8_t*>(buffer.GetConstMappedRange(0, bd.size));
    result.width = width;
    result.height = height;
    result.channels = 4;
    result.rgba.resize(static_cast<size_t>(width * height * 4));
    for (int row = 0; row < height; ++row) {
        std::memcpy(result.rgba.data() + static_cast<size_t>(row) * width * 4,
                    mapped + static_cast<size_t>(row) * bpr,
                    static_cast<size_t>(width) * 4);
    }
    buffer.Unmap();
    eng.probe.copy_bytes += result.rgba.size();
    return result;
}

CompileInfo compile_variant(const std::string& vertex, const std::string& fragment, bool base_level, bool has_depth,
                            bool point_sprites, bool allow_non_uniform_derivatives) {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    CompileInfo info;
    info.compiler_entry = kCompilerEntry;
    info.allow_non_uniform_derivatives = allow_non_uniform_derivatives;
    const auto derivative_mode = allow_non_uniform_derivatives ?
        SpirvDerivativeMode::AllowNonUniform : SpirvDerivativeMode::Strict;
    info.spirv_derivative_mode = vispy::shader::spirv_derivative_mode_name(derivative_mode);
    if (!eng.init_device()) {
        info.error = eng.last_error;
        return info;
    }
    std::string error;
    uint64_t hits_before = eng.probe.pipeline_hits;
    auto artifact = eng.make_artifact(vertex, fragment, error, base_level, has_depth, point_sprites,
        VertexIdentityPolicy::Native, derivative_mode);
    info.allow_non_uniform_derivatives = artifact->portable->derivative_mode == SpirvDerivativeMode::AllowNonUniform;
    info.spirv_derivative_mode = vispy::shader::spirv_derivative_mode_name(artifact->portable->derivative_mode);
    info.cache_key = artifact->portable->cache_key;
    info.normalized_vertex = artifact->portable->vertex;
    info.normalized_fragment = artifact->portable->fragment;
    info.vertex_log = artifact->portable->vertex_log;
    info.fragment_log = artifact->portable->fragment_log;
    info.spirv_vertex = artifact->portable->spv_vert;
    info.spirv_fragment = artifact->portable->spv_frag;
    info.pipeline = artifact->pipeline_ok;
    info.ok = artifact->pipeline_ok;
    info.cache_hit = eng.probe.pipeline_hits > hits_before;
    if (!error.empty()) {
        info.ok = false;
        info.error = error;
        // The compiler already mapped each stage's log using that stage's
        // composer source. A combined error cannot be mapped through the
        // fragment map first: it may start with a vertex diagnostic. Dawn
        // validation refers to its own generated representation, so retain
        // its text without inventing a composer line for device-only errors.
        if (!artifact->portable->ok) info.mapped_line = artifact->portable->mapped_line;
    }
    return info;
}

std::vector<std::string> debug_trace() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    return eng.trace;
}

void configure_shader_cache(int entries, uint64_t bytes) {
    constexpr uint64_t maximum_bytes = 64ull * 1024ull * 1024ull;
    if (entries < 1 || entries > 128 || bytes < 1 || bytes > maximum_bytes)
        throw std::runtime_error("shader cache requires 1..128 entries and 1..67108864 bytes");
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    // Dropping cache ownership leaves programs and queued snapshots intact.
    // No GPU completion barrier is necessary for changing cache admission.
    eng.shader_artifacts = NativeShaderCache(
        static_cast<size_t>(entries), static_cast<size_t>(bytes));
}

void lose_device() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    if (eng.device) {
        eng.device.ForceLoss(wgpu::DeviceLostReason::Unknown, "forced device loss for recovery qualification");
        eng.poll();
    }
}

void shutdown_runtime() {
    auto& eng = engine();
    std::lock_guard<std::mutex> lock(eng.mu);
    eng.shutdown();
}
