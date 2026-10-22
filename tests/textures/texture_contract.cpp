#include "runtime_texture.hpp"
#include "texture_full_upload_contract.hpp"

#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}
template <typename T> ByteBlob blob(std::vector<T> values, std::vector<int> shape, const std::string& dtype) {
    ByteBlob result;
    result.bytes.resize(values.size() * sizeof(T));
    std::memcpy(result.bytes.data(), values.data(), result.bytes.size());
    result.shape = std::move(shape);
    result.dtype = dtype;
    return result;
}
template <typename Function> void rejects(Function&& function, const std::string& message) {
    bool failed = false;
    try { function(); }
    catch (const std::runtime_error&) { failed = true; }
    require(failed, message);
}

template <typename T>
void unsized_storage_case(const std::string& dtype, const std::vector<T>& values,
                          const std::vector<uint8_t>& quantized) {
    // Independently queried pinned GL allocations have eight-bit components
    // for each of these formats, regardless of the subimage upload dtype.
    for (const auto& semantic : {"luminance", "red", "rgb", "rgba"}) {
        const int channels = texture_detail::format_channels(semantic);
        for (const bool explicit_base : {false, true}) {
            TextureData data;
            data.width = static_cast<int>(values.size()); data.channels = channels;
            data.format = semantic; data.internal_format = explicit_base ? semantic : "";
            std::vector<T> pixels;
            for (const auto value : values) for (int c = 0; c < channels; ++c) pixels.push_back(value);
            apply_texture_data(data, blob<T>(pixels, {1, data.width, channels}, dtype), {0, 0});
            const auto prepared = prepare_texture(data);
            const auto expected_format = channels == 1 && data.format == "red" ?
                wgpu::TextureFormat::R8Unorm : wgpu::TextureFormat::RGBA8Unorm;
            require(prepared.format == expected_format && prepared.texel_size == (expected_format == wgpu::TextureFormat::R8Unorm ? 1 : 4),
                    "unsized " + data.format + "/" + dtype + " must retain eight-bit normalized allocation");
            std::vector<uint8_t> expected;
            for (const auto value : quantized) {
                if (data.format == "red") expected.push_back(value);
                else {
                    expected.insert(expected.end(), {value, value, value,
                        static_cast<uint8_t>(data.format == "rgba" ? value : 255)});
                }
            }
            require(prepared.bytes == expected, "unsized quantization/channel semantics " + data.format + "/" + dtype);
            require(prepared.sample_type == wgpu::TextureSampleType::Float && !prepared.requires_float32_filterable,
                    "unsized storage must not require float32 filtering");
        }
    }
}

void unsized_storage() {
    unsized_storage_case<uint8_t>("u8", {0, 64, 128, 255}, {0, 64, 128, 255});
    unsized_storage_case<uint16_t>("u16", {0, 16384, 32768, 65535}, {0, 64, 128, 255});
    unsized_storage_case<uint32_t>("u32", {0, 1073741824u, 2147483648u, 4294967295u}, {0, 64, 128, 255});
    // Actual pinned GL transfers preserve the legacy signed-byte bias.
    unsized_storage_case<int8_t>("i8", {-128, 0, 32, 127}, {0, 1, 65, 255});
    unsized_storage_case<int16_t>("i16", {-32768, 0, 8192, 32767}, {0, 0, 64, 255});
    unsized_storage_case<int32_t>("i32", {-2147483647 - 1, 0, 536870912, 2147483647}, {0, 0, 64, 255});
    unsized_storage_case<float>("f32", {std::bit_cast<float>(0x7fc12345u), .25f, .5f, 1.f}, {0, 64, 128, 255});
    unsized_storage_case<float>("f32", {-std::numeric_limits<float>::infinity(), -.5f, 1.5f,
                                      std::numeric_limits<float>::infinity()}, {0, 0, 255, 255});
}

void partial_regions() {
    TextureData data;
    data.width = 4; data.height = 3;
    apply_texture_data(data, blob<uint8_t>(std::vector<uint8_t>(4 * 3 * 4, 20), {3, 4, 4}, "u8"), {0, 0});
    apply_texture_data(data, blob<uint8_t>({255, 0, 0, 255}, {1, 1, 4}, "u8"), {1, 2});
    require(data.width == 4 && data.height == 3 && data.channels == 4, "patch changed allocation");
    for (size_t pixel = 0; pixel < 12; ++pixel) {
        const size_t position = pixel * 4;
        require(data.pixels[position] == (pixel == 6 ? 255 : 20), "2D patch changed untouched pixel");
    }
    auto before = data.pixels;
    rejects([&] { apply_texture_data(data, blob<uint8_t>({1, 2, 3, 4}, {1, 1, 4}, "u8"), {3, 0}); }, "bounds check");
    require(before == data.pixels, "bad region modified allocation");
    rejects([&] { apply_texture_data(data, blob<float>({1, 2, 3, 4}, {1, 1, 4}, "unsupported"), {0, 0}); }, "unsupported partial dtype check");
    data.dimensions = 3; data.depth = 2; data.pixels.clear();
    apply_texture_data(data, blob<uint8_t>({1, 2, 3, 4}, {1, 1, 1, 4}, "u8"), {1, 2, 3});
    require(data.pixels.size() == 4 * 3 * 2 * 4, "3D first patch initializes entire allocation");
    require(data.pixels[(1 * 3 * 4 + 2 * 4 + 3) * 4] == 1 && data.pixels[0] == 0, "3D offset semantics");
    require(prepare_texture(data).dimension == wgpu::TextureDimension::e3D, "3D native dimension");
}

void scientific_formats() {
    TextureData data;
    data.channels = 1; data.format = "red"; data.internal_format = "r32f"; data.width = 4;
    const float nan = std::bit_cast<float>(0x7fc12345u);
    apply_texture_data(data, blob<float>({15, -20, nan, -0.0f}, {1, 4, 1}, "f32"), {0, 0});
    auto prepared = prepare_texture(data);
    require(prepared.format == wgpu::TextureFormat::R32Float && prepared.texel_size == 4, "native r32f format");
    require(prepared.bytes == data.pixels, "float values, NaN payload, and signed zero preserved");
    data.internal_format = "r32ui"; data.pixels.clear();
    apply_texture_data(data, blob<uint32_t>({0, 123456789u, 4000000000u, 4294967295u}, {1, 4, 1}, "u32"), {0, 0});
    prepared = prepare_texture(data);
    require(prepared.sample_type == wgpu::TextureSampleType::Uint && prepared.bytes == data.pixels, "sparse uint32 identities preserved");
    data.internal_format = "r32i"; data.pixels.clear();
    apply_texture_data(data, blob<int32_t>({-2147483647 - 1, -123456789, 123456789, 2147483647}, {1, 4, 1}, "i32"), {0, 0});
    prepared = prepare_texture(data);
    require(prepared.sample_type == wgpu::TextureSampleType::Sint && prepared.bytes == data.pixels, "signed int32 identities preserved");
    for (uint32_t half = 0; half <= 65535; ++half) {
        if ((half & 0x7c00u) == 0x7c00u && (half & 1023u) != 0) continue;
        require(texture_detail::float_to_half(texture_detail::half_to_float(static_cast<uint16_t>(half))) == half, "half exact roundtrip");
    }
}

void channel_semantics() {
    TextureData data;
    data.channels = 1; data.format = "luminance";
    apply_texture_data(data, blob<uint8_t>({128}, {1, 1, 1}, "u8"), {0, 0});
    require(prepare_texture(data).bytes == std::vector<uint8_t>({128, 128, 128, 255}), "legacy luminance channels");
    data.format = "alpha";
    require(prepare_texture(data).bytes == std::vector<uint8_t>({0, 0, 0, 128}), "legacy alpha channels");
    data.format = "red";
    require(prepare_texture(data).format == wgpu::TextureFormat::R8Unorm, "red stays red");
    data.channels = 2; data.format = "luminance_alpha"; data.pixels.clear();
    apply_texture_data(data, blob<uint8_t>({40, 200}, {1, 1, 2}, "u8"), {0, 0});
    require(prepare_texture(data).bytes == std::vector<uint8_t>({40, 40, 40, 200}), "legacy luminance_alpha channels");
    data.channels = 3; data.format = "rgb"; data.pixels.clear();
    apply_texture_data(data, blob<uint8_t>({10, 20, 30}, {1, 1, 3}, "u8"), {0, 0});
    require(prepare_texture(data).bytes == std::vector<uint8_t>({10, 20, 30, 255}), "rgb expansion alpha");
}

void fixed_allocation_conversion() {
    TextureData data;
    apply_texture_data(data, blob<uint8_t>({10, 20, 30, 40}, {1, 1, 4}, "u8"), {0, 0});
    const TextureData rgba8 = data;
    apply_texture_data(data, blob<uint16_t>({0, 32768, 65535, 16384}, {1, 1, 4}, "u16"), {0, 0});
    auto prepared = prepare_texture(data, &rgba8);
    require(prepared.format == wgpu::TextureFormat::RGBA8Unorm && prepared.texel_size == 4,
            "source dtype change must retain allocated RGBA8 storage");
    require(prepared.bytes == std::vector<uint8_t>({0, 128, 255, 64}),
            "uint16 normalized conversion into existing RGBA8");
    require(prepare_texture(data).format == wgpu::TextureFormat::RGBA8Unorm,
            "unsized standalone allocation does not widen when source dtype changes");

    TextureData r32f;
    r32f.channels = 1; r32f.format = "red"; r32f.internal_format = "r32f";
    r32f.width = 3; r32f.dtype = "f32";
    TextureData source;
    source.channels = 1; source.format = "red"; source.width = 3;
    apply_texture_data(source, blob<uint16_t>({0, 32768, 65535}, {1, 3, 1}, "u16"), {0, 0});
    prepared = prepare_texture(source, &r32f);
    require(prepared.format == wgpu::TextureFormat::R32Float && prepared.bytes.size() == 12,
            "float allocation retains format for integer source");
    require(texture_detail::load<float>(prepared.bytes.data()) == 0 &&
            std::abs(texture_detail::load<float>(prepared.bytes.data() + 4) - 32768.0f / 65535.0f) < 1e-7f &&
            texture_detail::load<float>(prepared.bytes.data() + 8) == 1,
            "integer source normalizes before float storage conversion");
    const auto scientific = blob<float>({std::bit_cast<float>(0x7fc12345u), -0.0f, -19.25f}, {1, 3, 1}, "f32");
    apply_texture_data(source, scientific, {0, 0});
    require(prepare_texture(source, &r32f).bytes == scientific.bytes,
            "fixed float storage preserves source range, NaN payload, and signed zero");

    TextureData luminance;
    luminance.channels = 1; luminance.format = "luminance";
    source.width = 1; source.format = "red";
    apply_texture_data(source, blob<uint16_t>({32768}, {1, 1, 1}, "u16"), {0, 0});
    prepared = prepare_texture(source, &luminance);
    require(prepared.format == wgpu::TextureFormat::RGBA8Unorm &&
            prepared.bytes == std::vector<uint8_t>({128, 128, 128, 255}),
            "fixed legacy luminance storage retains sampling expansion after dtype change");
    source.channels = 2; source.format = "rg"; source.pixels.clear();
    rejects([&] { prepare_texture(source, &luminance); }, "fixed allocation source channel mismatch");
}

void region_conversion() {
    TextureData allocation;
    allocation.width = 4096; allocation.height = 4096;
    // The resident vector is deliberately unrelated to the allocation extent:
    // region conversion reads only its descriptor and the region's own bytes.
    allocation.pixels = {1, 2, 3};
    const auto patch = blob<uint16_t>({0, 32768, 65535, 16384, 65535, 0, 0, 65535}, {1, 2, 4}, "u16");
    auto prepared = prepare_region(allocation, patch);
    require(prepared.format == wgpu::TextureFormat::RGBA8Unorm && prepared.bytes.size() == 8 &&
            prepared.bytes == std::vector<uint8_t>({0, 128, 255, 64, 255, 0, 0, 255}),
            "region extent and dtype convert with fixed allocation storage");
    require(allocation.width == 4096 && allocation.height == 4096 && allocation.pixels == std::vector<uint8_t>({1, 2, 3}),
            "region preparation leaves resident allocation untouched");
    allocation.dimensions = 3; allocation.depth = 256;
    prepared = prepare_region(allocation, blob<uint16_t>({0, 32768, 65535, 16384, 65535, 0, 0, 65535}, {2, 1, 1, 4}, "u16"));
    require(prepared.dimension == wgpu::TextureDimension::e3D && prepared.bytes.size() == 8,
            "3D region uses upload depth instead of resident volume depth");
    allocation.dimensions = 2; allocation.depth = 1;
    allocation.channels = 2; allocation.format = "luminance_alpha";
    require(prepare_region(allocation, blob<uint16_t>({32768, 16384}, {1, 1, 2}, "u16")).bytes ==
                std::vector<uint8_t>({128, 128, 128, 64}), "region retains luminance-alpha semantics");
    rejects([&] { prepare_region(allocation, blob<uint8_t>({1}, {1, 1, 1}, "u8")); }, "region channel mismatch");
    rejects([&] { prepare_region(allocation, blob<uint8_t>({1, 2}, {1, 2}, "u8")); }, "region shape rank mismatch");
    rejects([&] { prepare_region(allocation, blob<uint8_t>({1}, {1, 1, 2}, "u8")); }, "region byte size mismatch");
    rejects([&] { prepare_region(allocation, blob<uint8_t>({}, {0, 1, 2}, "u8")); }, "zero region extent");
    allocation.dimensions = 0;
    rejects([&] { prepare_region(allocation, blob<uint8_t>({1, 2}, {2}, "u8")); }, "invalid allocation rank");
}

void mixed_source_partial_shadow() {
    TextureData data;
    data.width = 2;
    apply_texture_data(data, blob<uint8_t>({20, 40, 60, 255, 80, 100, 120, 255}, {1, 2, 4}, "u8"), {0, 0});
    const TextureData rgba8 = data;
    apply_texture_data(data, blob<uint16_t>({0, 32768, 65535, 16384}, {1, 1, 4}, "u16"), {0, 1}, &rgba8);
    require(data.dtype == "f64" && data.width == 2 && data.pixels.size() == 8 * sizeof(double),
            "mixed partial DATA retains a numeric shadow without changing extent");
    require(prepare_texture(data, &rgba8).bytes == std::vector<uint8_t>({20, 40, 60, 255, 0, 128, 255, 64}),
            "mixed normalized partial upload preserves untouched RGBA8 values");
    apply_texture_data(data, blob<uint8_t>({255, 0, 0, 255}, {1, 1, 4}, "u8"), {0, 0}, &rgba8);
    require(prepare_texture(data, &rgba8).bytes == std::vector<uint8_t>({255, 0, 0, 255, 0, 128, 255, 64}),
            "subsequent normalized patch does not renormalize the f64 shadow");

    data = TextureData{};
    data.width = 2; data.channels = 1; data.format = "red"; data.internal_format = "r32f";
    apply_texture_data(data, blob<uint8_t>({255, 128}, {1, 2, 1}, "u8"), {0, 0});
    const TextureData r32f = data;
    apply_texture_data(data, blob<float>({15}, {1, 1, 1}, "f32"), {0, 1}, &r32f);
    auto prepared = prepare_texture(data, &r32f);
    require(texture_detail::load<float>(prepared.bytes.data()) == 1 &&
            texture_detail::load<float>(prepared.bytes.data() + 4) == 15,
            "float partial source keeps scientific range over normalized integer resident values");

    data.width = 3;
    const auto scientific = blob<float>({std::bit_cast<float>(0x7fc12345u), -0.0f, 15}, {1, 3, 1}, "f32");
    apply_texture_data(data, scientific, {0, 0});
    const TextureData scientific_allocation = data;
    apply_texture_data(data, blob<uint16_t>({32768}, {1, 1, 1}, "u16"), {0, 2}, &scientific_allocation);
    prepared = prepare_texture(data, &scientific_allocation);
    require(texture_detail::load<uint32_t>(prepared.bytes.data()) == 0x7fc12345u &&
            texture_detail::load<uint32_t>(prepared.bytes.data() + 4) == 0x80000000u,
            "untouched float NaN payload and signed zero survive mixed CPU reconstruction");

    data = TextureData{};
    data.width = 3; data.channels = 1; data.format = "red"; data.internal_format = "r32ui";
    apply_texture_data(data, blob<uint8_t>({0, 127, 255}, {1, 3, 1}, "u8"), {0, 0});
    const TextureData integer_allocation = data;
    apply_texture_data(data, blob<uint32_t>({4000000000u}, {1, 1, 1}, "u32"), {0, 1}, &integer_allocation);
    prepared = prepare_texture(data, &integer_allocation);
    require(texture_detail::load<uint32_t>(prepared.bytes.data()) == 0 &&
            texture_detail::load<uint32_t>(prepared.bytes.data() + 4) == 4000000000u &&
            texture_detail::load<uint32_t>(prepared.bytes.data() + 8) == 255,
            "mixed integer source preserves sparse uint32 labels and original integer identities");

    const auto before = data.pixels;
    TextureData wrong = integer_allocation; wrong.channels = 2; wrong.format = "rg";
    rejects([&] { apply_texture_data(data, blob<uint16_t>({1}, {1, 1, 1}, "u16"), {0, 1}, &wrong); },
            "mixed partial update rejects incompatible allocation descriptor");
    require(data.pixels == before && data.dtype == "f64", "invalid mixed partial update leaves numeric shadow unchanged");
}

void mixed_storage_roundtrip() {
    // Untouched texels must retain their already-quantized storage value when
    // a different upload dtype forces the resident CPU shadow to be rebuilt.
    TextureData data;
    data.width = 257; data.channels = 1; data.format = "red";
    std::vector<uint16_t> source;
    std::vector<uint8_t> expected;
    for (unsigned int byte = 0; byte < 256; ++byte) {
        source.push_back(static_cast<uint16_t>((byte << 8) | 129));
        expected.push_back(static_cast<uint8_t>(byte));
    }
    source.push_back(0); expected.push_back(255);
    apply_texture_data(data, blob<uint16_t>(source, {1, 257, 1}, "u16"), {0, 0});
    const TextureData allocation = data;
    apply_texture_data(data, blob<float>({1}, {1, 1, 1}, "f32"), {0, 256}, &allocation);
    require(data.dtype == "f64" && prepare_texture(data, &allocation).bytes == expected,
            "all 256 stored byte values survive mixed shadow promotion at uint16 narrowing boundaries");
    apply_texture_data(data, blob<uint8_t>({9}, {1, 1, 1}, "u8"), {0, 0}, &allocation);
    expected[0] = 9;
    require(prepare_texture(data, &allocation).bytes == expected,
            "repeated mixed shadow promotion preserves the full stored byte domain");

    data = TextureData{};
    data.width = 4; data.channels = 1; data.format = "red";
    apply_texture_data(data, blob<int8_t>({-128, 0, 32, 127}, {1, 4, 1}, "i8"), {0, 0});
    const TextureData signed_allocation = data;
    apply_texture_data(data, blob<uint16_t>({129}, {1, 1, 1}, "u16"), {0, 0}, &signed_allocation);
    require(prepare_texture(data, &signed_allocation).bytes == std::vector<uint8_t>({0, 1, 65, 255}),
            "mixed patches preserve independently observed signed-byte bias in untouched texels");

    data = TextureData{};
    data.width = 3; data.channels = 1; data.format = "red";
    apply_texture_data(data, blob<uint32_t>({0x00ffffffu, 0x7fffffffu, 0xffffffffu}, {1, 3, 1}, "u32"), {0, 0});
    const TextureData wide_allocation = data;
    apply_texture_data(data, blob<uint8_t>({128}, {1, 1, 1}, "u8"), {0, 1}, &wide_allocation);
    require(prepare_texture(data, &wide_allocation).bytes == std::vector<uint8_t>({0, 128, 255}),
            "mixed patches preserve uint32 byte narrowing at upper-byte boundaries");
}

void interpreter_texture_dimensions() {
    using namespace texture_detail;
    for (const std::string name : {"Program", "VertexShader", "FragmentShader", "GeometryShader",
            "VertexBuffer", "IndexBuffer", "Texture1D", "Texture2D", "Texture3D", "RenderBuffer", "FrameBuffer"})
        require(supported_glir_object_class(name), "CREATE supported class " + name);
    require(!supported_glir_object_class("Texture4D"), "CREATE unknown class must reject");
    require(texture_dimensions_for_class("Texture1D") == 1 && texture_dimensions_for_class("Texture2D") == 2 &&
        texture_dimensions_for_class("Texture3D") == 3 && texture_dimensions_for_class("RenderBuffer") == 2,
        "actual SIZE class rank dispatch");
    rejects([] { texture_dimensions_for_class("Program"); }, "SIZE nontexture class must reject");
    for (int dimensions : {1, 2, 3}) {
        std::vector<int64_t> shape = dimensions == 1 ? std::vector<int64_t>{65, 4} :
            dimensions == 2 ? std::vector<int64_t>{7, 65, 4} : std::vector<int64_t>{3, 7, 65, 4};
        const auto layout = texture_shape_layout(dimensions, shape);
        require(layout.width == 65 && layout.height == (dimensions >= 2 ? 7 : 1) &&
            layout.depth == (dimensions == 3 ? 3 : 1) && layout.channels == 4, "SIZE shape axes");
        TextureData data; data.dimensions = dimensions; data.width = layout.width; data.height = layout.height;
        data.depth = layout.depth; data.channels = layout.channels;
        ByteBlob upload; upload.shape.assign(shape.begin(), shape.end()); upload.dtype = "u8";
        std::vector<int> offset(dimensions, 0);
        require(texture_upload_is_entire(data, upload, offset), "DATA complete shape classification");
        offset.back() = 1;
        require(!texture_upload_is_entire(data, upload, offset), "DATA offset must prevent full classification");
        const auto region = texture_region_layout(dimensions, upload.shape, offset);
        require(region.x == 1 && region.y == 0 && region.z == 0 && region.width == layout.width &&
            region.height == layout.height && region.depth == layout.depth, "upload region coordinates");
        shape.pop_back();
        require(texture_shape_layout(dimensions, shape).channels == 4, "legacy implicit four-channel SIZE");
    }
    for (int dimensions : {2, 3}) {
        const std::vector<int> shape = dimensions == 2 ? std::vector<int>{7, 65, 4} : std::vector<int>{3, 7, 65, 4};
        const std::vector<int> offset = dimensions == 2 ? std::vector<int>{5, 11} : std::vector<int>{2, 5, 11};
        const auto region = texture_region_layout(dimensions, shape, offset);
        require(region.x == 11 && region.y == 5 && region.z == (dimensions == 3 ? 2 : 0),
            "existing DATA all distinct nonzero origin axes");
        std::vector<int64_t> legacy = dimensions == 2 ? std::vector<int64_t>{0, 65, 7, 99} :
            std::vector<int64_t>{0, 7, 65, 7, 99};
        const auto layout = texture_shape_layout(dimensions, legacy);
        require(layout.width == 65 && layout.height == (dimensions == 2 ? 0 : 7) &&
            layout.depth == (dimensions == 3 ? 0 : 1) && layout.channels == 7,
            "existing SIZE transient zero extent, channel and ignored trailing axes preserved");
    }
    rejects([] { texture_shape_layout(1, {5, 4, 1}); }, "1D extra SIZE axis");
    rejects([] { texture_shape_layout(3, {5, 4}); }, "3D missing SIZE axis");
    rejects([] { texture_shape_layout(1, {0, 4}); }, "zero SIZE extent");
    rejects([] { texture_shape_layout(1, {int64_t(std::numeric_limits<int>::max()) + 1, 4}); }, "SIZE native overflow");
    rejects([] { texture_region_layout(1, {5, 4}, {0, 0}); }, "1D extra origin axis");
    rejects([] { texture_region_layout(1, {5, 4}, {-1}); }, "negative1D origin");
    const auto region = texture_region_layout(1, {9, 4}, {17});
    require(region.x == 17 && region.y == 0 && region.z == 0 && region.width == 9 &&
        region.height == 1 && region.depth == 1, "real partial1D patch box");
    TextureData one; one.dimensions = 1; one.width = 65;
    std::vector<uint8_t> original(65 * 4); for (size_t n = 0; n < original.size(); ++n) original[n] = uint8_t(n % 251);
    auto entire = blob<uint8_t>(original, {65, 4}, "u8");
    apply_texture_data(one, entire, {0});
    require(texture_upload_is_entire(one, entire, {0}), "full1D must clear history");
    const auto allocation = one;
    auto patch = blob<uint8_t>(std::vector<uint8_t>(9 * 4, 123), {9, 4}, "u8");
    apply_texture_data(one, patch, {17}, &allocation);
    std::fill(original.begin() + 17 * 4, original.begin() + 26 * 4, uint8_t(123));
    require(prepare_texture(one, &allocation).bytes == original, "partial1D CPU shadow bytes");
    require(prepare_region(allocation, patch).bytes == patch.bytes, "partial1D upload region bytes");
}

void sampler_contracts() {
    TextureData data;
    data.min_filter = "linear"; data.mag_filter = "nearest";
    data.wrapping = {"repeat", "mirrored_repeat"};
    auto descriptor = prepare_sampler_descriptor(data);
    require(descriptor.minFilter == wgpu::FilterMode::Linear && descriptor.magFilter == wgpu::FilterMode::Nearest, "separate min/mag filters");
    require(descriptor.addressModeU == wgpu::AddressMode::Repeat && descriptor.addressModeV == wgpu::AddressMode::MirrorRepeat, "2D wrapping contract");
    data.dimensions = 3; data.wrapping = {"clamp_to_edge", "repeat", "mirrored_repeat"};
    descriptor = prepare_sampler_descriptor(data);
    require(descriptor.addressModeW == wgpu::AddressMode::ClampToEdge && descriptor.addressModeU == wgpu::AddressMode::Repeat && descriptor.addressModeV == wgpu::AddressMode::MirrorRepeat, "3D wrapping contract");
    data.min_filter = "linear_mipmap_linear";
    rejects([&] { prepare_sampler_descriptor(data); }, "mip filter must fail explicitly");
    data.min_filter = "linear"; data.channels = 1; data.format = "red"; data.internal_format = "r32ui";
    rejects([&] { prepare_sampler_descriptor(data); }, "integer linear filter must fail explicitly");
}
}  // namespace

int main() {
    try {
        interpreter_texture_dimensions();
        unsized_storage(); partial_regions(); scientific_formats(); channel_semantics(); fixed_allocation_conversion(); region_conversion(); mixed_source_partial_shadow(); mixed_storage_roundtrip(); sampler_contracts();
        vispy::texture_contracts::full_upload_equivalence_contract();
        std::cout << "texture allocation, partial upload, scientific format, channel, and sampler contracts passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
