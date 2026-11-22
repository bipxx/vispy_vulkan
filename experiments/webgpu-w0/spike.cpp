#include <cstdint>
#include <cstdio>
#include <utility>
#include <webgpu/webgpu_cpp.h>

namespace {

constexpr auto wait_mode = wgpu::CallbackMode::WaitAnyOnly;
constexpr uint64_t row_bytes = 256;
constexpr uint32_t side = 4;

uint32_t fail(const char* stage) {
    std::fprintf(stderr, "read_pixel failed at %s\n", stage);
    return 0;
}

wgpu::ShaderModule shader(const wgpu::Device& device, const char* code) {
    wgpu::ShaderSourceWGSL source{};
    source.code = code;
    wgpu::ShaderModuleDescriptor descriptor{};
    descriptor.nextInChain = &source;
    return device.CreateShaderModule(&descriptor);
}

}  // namespace

extern "C" uint32_t read_pixel(const char* selector, const char* vert,
                              const char* frag, int cancel_map) {
    constexpr auto timed_wait = wgpu::InstanceFeatureName::TimedWaitAny;
    wgpu::InstanceDescriptor instance_desc{};
    instance_desc.requiredFeatureCount = 1;
    instance_desc.requiredFeatures = &timed_wait;
    auto instance = wgpu::CreateInstance(&instance_desc);
    if (!instance) return fail("create instance");

    wgpu::Adapter adapter;
    auto adapter_ready = instance.RequestAdapter(
        nullptr, wait_mode,
        [&adapter](wgpu::RequestAdapterStatus status, wgpu::Adapter value,
                   wgpu::StringView message) {
            if (status == wgpu::RequestAdapterStatus::Success) adapter = std::move(value);
            else std::fprintf(stderr, "adapter: %.*s\n", int(message.length), message.data);
        });
    if (instance.WaitAny(adapter_ready, UINT64_MAX) != wgpu::WaitStatus::Success || !adapter) {
        return fail("wait for adapter");
    }

    wgpu::Device device;
    auto device_ready = adapter.RequestDevice(
        nullptr, wait_mode,
        [&device](wgpu::RequestDeviceStatus status, wgpu::Device value,
                  wgpu::StringView message) {
            if (status == wgpu::RequestDeviceStatus::Success) device = std::move(value);
            else std::fprintf(stderr, "device: %.*s\n", int(message.length), message.data);
        });
    if (instance.WaitAny(device_ready, UINT64_MAX) != wgpu::WaitStatus::Success || !device) {
        return fail("wait for device");
    }

    wgpu::EmscriptenSurfaceSourceCanvasHTMLSelector canvas{};
    canvas.selector = selector;
    wgpu::SurfaceDescriptor surface_desc{};
    surface_desc.nextInChain = &canvas;
    auto surface = instance.CreateSurface(&surface_desc);
    if (!surface) return fail("create canvas surface");
    wgpu::SurfaceCapabilities capabilities{};
    if (surface.GetCapabilities(adapter, &capabilities) != wgpu::Status::Success ||
        capabilities.formatCount == 0) return fail("get surface capabilities");
    auto format = capabilities.formats[0];
    if (format != wgpu::TextureFormat::BGRA8Unorm && format != wgpu::TextureFormat::RGBA8Unorm) {
        return fail("select surface format");
    }
    wgpu::SurfaceConfiguration configuration{};
    configuration.device = device;
    configuration.format = format;
    configuration.usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::CopySrc;
    configuration.width = side;
    configuration.height = side;
    surface.Configure(&configuration);
    wgpu::SurfaceTexture current{};
    surface.GetCurrentTexture(&current);
    if (!current.texture) return fail("get canvas texture");

    wgpu::RenderPipeline pipeline;
    wgpu::Buffer positions;
    auto queue = device.GetQueue();
    if (vert && frag) {
        constexpr float vertices[] = {
            -1, -1, 0, 0.25f, 0.4f, 0.75f, 1,
             3, -1, 0, 0.25f, 0.4f, 0.75f, 1,
            -1,  3, 0, 0.25f, 0.4f, 0.75f, 1,
        };
        wgpu::BufferDescriptor buffer_desc{};
        buffer_desc.size = sizeof(vertices);
        buffer_desc.usage = wgpu::BufferUsage::Vertex | wgpu::BufferUsage::CopyDst;
        positions = device.CreateBuffer(&buffer_desc);
        queue.WriteBuffer(positions, 0, vertices, sizeof(vertices));
        wgpu::VertexAttribute attributes[2]{};
        attributes[0].format = wgpu::VertexFormat::Float32x3;
        attributes[1].format = wgpu::VertexFormat::Float32x4;
        attributes[1].offset = 3 * sizeof(float);
        attributes[1].shaderLocation = 1;
        wgpu::VertexBufferLayout layout{};
        layout.arrayStride = 7 * sizeof(float);
        layout.attributeCount = 2;
        layout.attributes = attributes;
        wgpu::ColorTargetState target{};
        target.format = format;
        wgpu::FragmentState fragment{};
        fragment.module = shader(device, frag);
        fragment.entryPoint = "main";
        fragment.targetCount = 1;
        fragment.targets = &target;
        wgpu::RenderPipelineDescriptor desc{};
        desc.vertex.module = shader(device, vert);
        desc.vertex.entryPoint = "main";
        desc.vertex.bufferCount = 1;
        desc.vertex.buffers = &layout;
        desc.fragment = &fragment;
        pipeline = device.CreateRenderPipeline(&desc);
    }

    wgpu::RenderPassColorAttachment color{};
    color.view = current.texture.CreateView();
    color.loadOp = wgpu::LoadOp::Clear;
    color.storeOp = wgpu::StoreOp::Store;
    color.clearValue = {1, 0, 102.0 / 255.0, 1};
    wgpu::RenderPassDescriptor pass_desc{};
    pass_desc.colorAttachmentCount = 1;
    pass_desc.colorAttachments = &color;
    auto encoder = device.CreateCommandEncoder();
    auto pass = encoder.BeginRenderPass(&pass_desc);
    if (pipeline) {
        pass.SetPipeline(pipeline);
        pass.SetVertexBuffer(0, positions);
        pass.Draw(3);
    }
    pass.End();
    wgpu::BufferDescriptor readback_desc{};
    readback_desc.size = row_bytes;
    readback_desc.usage = wgpu::BufferUsage::CopyDst | wgpu::BufferUsage::MapRead;
    auto readback = device.CreateBuffer(&readback_desc);
    wgpu::TexelCopyTextureInfo source{};
    source.texture = current.texture;
    source.origin = {1, 1, 0};
    wgpu::TexelCopyBufferInfo destination{};
    destination.buffer = readback;
    destination.layout.bytesPerRow = row_bytes;
    destination.layout.rowsPerImage = 1;
    constexpr wgpu::Extent3D pixel_size{1, 1, 1};
    encoder.CopyTextureToBuffer(&source, &destination, &pixel_size);
    auto command = encoder.Finish();
    queue.Submit(1, &command);

    wgpu::MapAsyncStatus map_status{};
    auto mapping = readback.MapAsync(
        wgpu::MapMode::Read, 0, 4, wait_mode,
        [&map_status](wgpu::MapAsyncStatus status, wgpu::StringView) { map_status = status; });
    if (cancel_map) readback.Unmap();
    if (instance.WaitAny(mapping, UINT64_MAX) != wgpu::WaitStatus::Success) return fail("wait for readback map");
    if (map_status == wgpu::MapAsyncStatus::Aborted) return 1;
    if (map_status != wgpu::MapAsyncStatus::Success) return fail("complete readback map");
    auto bytes = static_cast<const uint8_t*>(readback.GetConstMappedRange(0, 4));
    if (!bytes) return fail("read mapped bytes");
    const bool bgra = format == wgpu::TextureFormat::BGRA8Unorm;
    const uint32_t pixel = uint32_t(bytes[bgra ? 2 : 0]) << 24 |
                           uint32_t(bytes[1]) << 16 |
                           uint32_t(bytes[bgra ? 0 : 2]) << 8 |
                           uint32_t(bytes[3]);
    readback.Unmap();
    return pixel;
}
