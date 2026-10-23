#pragma once

#include "runtime.hpp"
#include "shader/integer_sampling.hpp"
#include <webgpu/webgpu_cpp.h>

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>

// CPU source allocation. SIZE establishes dimensions; DATA updates regions
// within that allocation. Mixed source dtypes use a numeric f64 CPU shadow;
// native storage still comes from the original allocation descriptor.
struct TextureData {
    std::vector<uint8_t> pixels;
    int width = 1;
    int height = 1;
    int depth = 1;
    int channels = 4;
    std::string dtype = "u8";
    std::string format = "rgba";
    std::string internal_format;
    int dimensions = 2;
    std::string min_filter = "nearest";
    std::string mag_filter = "nearest";
    std::vector<std::string> wrapping;
};

// Sampling state belongs to the retained revision; storage belongs to its
// immutable allocation. Construct this descriptor without copying the image
// shadow, which can be a large volume or a mixed-dtype DATA representation.
inline TextureData sampler_texture_descriptor(const TextureData& data,
                                              const TextureData* allocation = nullptr) {
    const auto& storage = allocation ? *allocation : data;
    TextureData result;
    result.width = storage.width;
    result.height = storage.height;
    result.depth = storage.depth;
    result.channels = storage.channels;
    result.dtype = storage.dtype;
    result.format = storage.format;
    result.internal_format = storage.internal_format;
    result.dimensions = storage.dimensions;
    result.min_filter = data.min_filter;
    result.mag_filter = data.mag_filter;
    result.wrapping = data.wrapping;
    return result;
}

struct PreparedTexture {
    wgpu::TextureFormat format = wgpu::TextureFormat::Undefined;
    wgpu::TextureDimension dimension = wgpu::TextureDimension::e2D;
    wgpu::TextureViewDimension view_dimension = wgpu::TextureViewDimension::e2D;
    wgpu::TextureSampleType sample_type = wgpu::TextureSampleType::Float;
    size_t texel_size = 0;
    int channels = 4;
    std::vector<uint8_t> bytes;
    bool requires_float32_filterable = false;
    bool requires_unorm16 = false;
};

namespace texture_detail {

inline std::runtime_error error(const std::string& message) {
    return std::runtime_error("texture: " + message);
}

// Shared with the command interpreter: texture rank must agree from CREATE
// through SIZE, DATA history and the native upload origin/extent.
inline bool supported_glir_object_class(const std::string& name) {
    return name == "Program" || name == "VertexShader" || name == "FragmentShader" ||
        name == "GeometryShader" || name == "VertexBuffer" || name == "IndexBuffer" ||
        name == "Texture1D" || name == "Texture2D" || name == "Texture3D" ||
        name == "RenderBuffer" || name == "FrameBuffer";
}
inline int texture_dimensions_for_class(const std::string& name) {
    if (name == "Texture1D") return 1;
    if (name == "Texture2D" || name == "RenderBuffer") return 2;
    if (name == "Texture3D") return 3;
    throw error("SIZE object is not a texture or renderbuffer");
}
struct TextureShapeLayout { int width = 1, height = 1, depth = 1, channels = 4; };
inline TextureShapeLayout texture_shape_layout(int dimensions, const std::vector<int64_t>& shape) {
    if (dimensions < 1 || dimensions > 3 || shape.size() < static_cast<size_t>(dimensions) ||
        (dimensions == 1 && shape.size() > 2)) throw error("SIZE invalid texture shape rank");
    auto component = [&](size_t axis) {
        // Existing 2D/3D and renderbuffer SIZE accepts transient zero extents
        // and defers storage validation until DATA/upload. Keep that contract.
        if (dimensions == 1 && (shape[axis] < 1 || shape[axis] > std::numeric_limits<int>::max()))
            throw error("SIZE texture extent/channel count is outside positive native range");
        return static_cast<int>(shape[axis]);
    };
    TextureShapeLayout result;
    result.width = component(dimensions - 1);
    if (dimensions >= 2) result.height = component(dimensions - 2);
    if (dimensions == 3) result.depth = component(0);
    if (shape.size() > static_cast<size_t>(dimensions)) result.channels = component(dimensions);
    if (dimensions == 1 && result.channels > 4) throw error("SIZE invalid channel count");
    return result;
}
struct TextureRegionLayout : TextureShapeLayout { int x = 0, y = 0, z = 0; };
inline TextureRegionLayout texture_region_layout(int dimensions, const std::vector<int>& shape,
                                                  const std::vector<int>& offset) {
    if (offset.size() != static_cast<size_t>(dimensions) ||
        shape.size() != static_cast<size_t>(dimensions + 1)) throw error("DATA region rank differs from texture rank");
    TextureRegionLayout result;
    static_cast<TextureShapeLayout&>(result) = texture_shape_layout(dimensions,
        std::vector<int64_t>(shape.begin(), shape.end()));
    for (int value : offset) if (value < 0) throw error("DATA negative texture origin");
    result.x = offset[dimensions - 1];
    if (dimensions >= 2) result.y = offset[dimensions - 2];
    if (dimensions == 3) result.z = offset[0];
    return result;
}
inline bool texture_upload_is_entire(const TextureData& data, const ByteBlob& upload,
                                      const std::vector<int>& offset) {
    if (data.dimensions < 1 || data.dimensions > 3 ||
        upload.shape.size() != static_cast<size_t>(data.dimensions + 1) ||
        offset.size() != static_cast<size_t>(data.dimensions) || upload.shape.back() != data.channels)
        return false;
    if (!std::all_of(offset.begin(), offset.end(), [](int value) { return value == 0; })) return false;
    return upload.shape[data.dimensions - 1] == data.width &&
        (data.dimensions < 2 || upload.shape[data.dimensions - 2] == data.height) &&
        (data.dimensions != 3 || upload.shape[0] == data.depth);
}

inline size_t dtype_size(const std::string& dtype) {
    if (dtype == "u8" || dtype == "i8") return 1;
    if (dtype == "u16" || dtype == "i16" || dtype == "f16") return 2;
    if (dtype == "u32" || dtype == "i32" || dtype == "f32") return 4;
    if (dtype == "f64") return 8;
    throw error("unsupported upload dtype " + dtype);
}

inline size_t multiply(size_t left, size_t right) {
    if (right && left > std::numeric_limits<size_t>::max() / right) throw error("allocation byte size overflows");
    return left * right;
}

inline size_t texels(const TextureData& data) {
    if (data.dimensions < 1 || data.dimensions > 3 || data.width < 1 || data.height < 1 || data.depth < 1 ||
        data.channels < 1 || data.channels > 4) throw error("invalid allocation dimensions/channels");
    if (data.dimensions == 1 && (data.height != 1 || data.depth != 1)) throw error("1D allocation has nonunit height/depth");
    if (data.dimensions == 2 && data.depth != 1) throw error("2D allocation has nonunit depth");
    return multiply(multiply(static_cast<size_t>(data.width), data.height), data.depth);
}

inline int format_channels(const std::string& format) {
    if (format == "red" || format == "r" || format == "luminance" || format == "alpha") return 1;
    if (format == "rg" || format == "luminance_alpha") return 2;
    if (format == "rgb") return 3;
    if (format == "rgba") return 4;
    throw error("unsupported source/internal format " + format);
}

enum class Storage { Float32, Float16, Unorm8, Unorm16, Snorm8, Uint8, Uint16, Uint32, Sint8, Sint16, Sint32 };

struct Description {
    Storage storage = Storage::Unorm8;
    int channels = 4;
    std::string semantic;
    size_t component_bytes = 1;
    bool integer = false;
    bool signed_integer = false;
};

inline Description describe(const TextureData& data) {
    Description result;
    if (format_channels(data.format) != data.channels) throw error("source format and channel count differ");
    result.semantic = data.format;
    const std::string& internal = data.internal_format;
    if (!internal.empty() && internal != "red" && internal != "luminance" && internal != "alpha" &&
        internal != "luminance_alpha" && internal != "rg" && internal != "rgb" && internal != "rgba") {
        std::string base;
        if (internal.rfind("rgba", 0) == 0) base = "rgba";
        else if (internal.rfind("rgb", 0) == 0) base = "rgb";
        else if (internal.rfind("rg", 0) == 0) base = "rg";
        else if (internal.rfind("r", 0) == 0) base = "r";
        else throw error("unsupported internal format " + internal);
        if (format_channels(base) != data.channels) throw error("internal format and channel count differ");
        result.semantic = base == "r" ? "red" : base;
        const std::string suffix = internal.substr(base.size());
        if (suffix == "32f") result.storage = Storage::Float32;
        else if (suffix == "16f") result.storage = Storage::Float16;
        else if (suffix == "8") result.storage = Storage::Unorm8;
        else if (suffix == "16") result.storage = Storage::Unorm16;
        else if (suffix == "8ui") result.storage = Storage::Uint8;
        else if (suffix == "16ui") result.storage = Storage::Uint16;
        else if (suffix == "32ui") result.storage = Storage::Uint32;
        else if (suffix == "8i") result.storage = Storage::Sint8;
        else if (suffix == "16i") result.storage = Storage::Sint16;
        else if (suffix == "32i") result.storage = Storage::Sint32;
        else throw error("unsupported internal format " + internal);
    } else {
        if (!internal.empty()) result.semantic = internal;
        // Pinned gloo allocates unsized textures with unsigned-byte storage
        // before typed subimage uploads. Upload dtype does not resize that
        // allocation: range and NaNs require an explicit sized float format.
        dtype_size(data.dtype);
        result.storage = Storage::Unorm8;
    }
    const auto storage = result.storage;
    result.integer = storage == Storage::Uint8 || storage == Storage::Uint16 || storage == Storage::Uint32 ||
                     storage == Storage::Sint8 || storage == Storage::Sint16 || storage == Storage::Sint32;
    result.signed_integer = storage == Storage::Sint8 || storage == Storage::Sint16 || storage == Storage::Sint32;
    result.component_bytes = storage == Storage::Float32 || storage == Storage::Uint32 || storage == Storage::Sint32 ? 4 :
                             storage == Storage::Float16 || storage == Storage::Unorm16 ||
                             storage == Storage::Uint16 || storage == Storage::Sint16 ? 2 : 1;
    // WebGPU has no RGB or legacy luminance/alpha sampling formats. Expand
    // their channel values, rather than pretending they sample as red/rg.
    result.channels = result.semantic == "rgb" || result.semantic == "luminance" ||
                      result.semantic == "luminance_alpha" || result.semantic == "alpha" ? 4 : data.channels;
    return result;
}

inline wgpu::TextureFormat native_format(const Description& description) {
    const int channels = description.channels;
    if (channels != 1 && channels != 2 && channels != 4) throw error("invalid native channel count");
#define VISPY_TEXTURE_FORMAT(kind, suffix) case Storage::kind: return channels == 1 ? wgpu::TextureFormat::R##suffix : channels == 2 ? wgpu::TextureFormat::RG##suffix : wgpu::TextureFormat::RGBA##suffix
    switch (description.storage) {
        VISPY_TEXTURE_FORMAT(Float32, 32Float);
        VISPY_TEXTURE_FORMAT(Float16, 16Float);
        VISPY_TEXTURE_FORMAT(Unorm8, 8Unorm);
        VISPY_TEXTURE_FORMAT(Unorm16, 16Unorm);
        VISPY_TEXTURE_FORMAT(Snorm8, 8Snorm);
        VISPY_TEXTURE_FORMAT(Uint8, 8Uint);
        VISPY_TEXTURE_FORMAT(Uint16, 16Uint);
        VISPY_TEXTURE_FORMAT(Uint32, 32Uint);
        VISPY_TEXTURE_FORMAT(Sint8, 8Sint);
        VISPY_TEXTURE_FORMAT(Sint16, 16Sint);
        VISPY_TEXTURE_FORMAT(Sint32, 32Sint);
    }
#undef VISPY_TEXTURE_FORMAT
    throw error("invalid native storage format");
}

template <typename T> inline T load(const uint8_t* source) {
    T value;
    std::memcpy(&value, source, sizeof(T));
    return value;
}

template <typename T> inline void store(uint8_t* destination, T value) {
    std::memcpy(destination, &value, sizeof(T));
}

inline float half_to_float(uint16_t half) {
    const uint32_t sign = static_cast<uint32_t>(half & 0x8000u) << 16;
    const uint32_t exponent = (half >> 10) & 31u;
    uint32_t mantissa = half & 1023u;
    uint32_t bits;
    if (exponent == 0) {
        if (!mantissa) bits = sign;
        else {
            int shift = 0;
            while ((mantissa & 1024u) == 0) { mantissa <<= 1; ++shift; }
            bits = sign | (static_cast<uint32_t>(113 - shift) << 23) | ((mantissa & 1023u) << 13);
        }
    } else if (exponent == 31) bits = sign | 0x7f800000u | (mantissa << 13);
    else bits = sign | ((exponent + 112u) << 23) | (mantissa << 13);
    return std::bit_cast<float>(bits);
}

inline uint16_t float_to_half(float value) {
    const uint32_t bits = std::bit_cast<uint32_t>(value);
    const uint16_t sign = static_cast<uint16_t>((bits >> 16) & 0x8000u);
    const int exponent = static_cast<int>((bits >> 23) & 255u) - 127 + 15;
    const uint32_t mantissa = bits & 0x7fffffu;
    if (((bits >> 23) & 255u) == 255u) return sign | (mantissa ? 0x7e00u : 0x7c00u);
    if (exponent >= 31) return sign | 0x7c00u;
    if (exponent <= 0) {
        if (exponent < -10) return sign;
        const uint32_t significand = mantissa | 0x800000u;
        const int shift = 14 - exponent;
        const uint32_t rounded = significand + ((1u << (shift - 1)) - 1u) + ((significand >> shift) & 1u);
        return sign | static_cast<uint16_t>(rounded >> shift);
    }
    const uint32_t rounded = mantissa + 0xfffu + ((mantissa >> 13) & 1u);
    return sign | static_cast<uint16_t>((static_cast<uint32_t>(exponent) << 10) + (rounded >> 13));
}

inline double source_value(const uint8_t* source, const std::string& dtype, bool integer) {
    if (dtype == "f32") return load<float>(source);
    if (dtype == "f64") return load<double>(source);
    if (dtype == "f16") return half_to_float(load<uint16_t>(source));
    double value = 0;
    double maximum = 1;
    if (dtype == "u8") { value = load<uint8_t>(source); maximum = 255; }
    else if (dtype == "i8") { value = load<int8_t>(source); maximum = 127; }
    else if (dtype == "u16") { value = load<uint16_t>(source); maximum = 65535; }
    else if (dtype == "i16") { value = load<int16_t>(source); maximum = 32767; }
    else if (dtype == "u32") { value = load<uint32_t>(source); maximum = 4294967295.0; }
    else if (dtype == "i32") { value = load<int32_t>(source); maximum = 2147483647.0; }
    else throw error("unsupported upload dtype " + dtype);
    return integer ? value : std::max(-1.0, value / maximum);
}

// Match the pinned GL transfer corpus. Float destinations retain the rounded
// transfer value; normalized byte destinations have their own narrowing rules.
inline float float_transfer(const uint8_t* source, const std::string& dtype) {
    if (dtype == "u8") return static_cast<float>(load<uint8_t>(source)) * (1.0f / 255.0f);
    if (dtype == "u16") return static_cast<float>(load<uint16_t>(source)) * (1.0f / 65535.0f);
    if (dtype == "u32") return static_cast<float>(load<uint32_t>(source)) * (1.0f / 4294967040.0f);
    if (dtype == "i8") return static_cast<float>(2 * static_cast<int>(load<int8_t>(source)) + 1) * (1.0f / 255.0f);
    if (dtype == "i16") return static_cast<float>(2 * static_cast<int>(load<int16_t>(source)) + 1) * (1.0f / 65535.0f);
    return static_cast<float>(source_value(source, dtype, false));
}

inline uint8_t nearest_even_byte(float value) {
    if (std::isnan(value)) return 0;
    const float scaled = std::clamp(value, 0.0f, 1.0f) * 255.0f;
    const auto lower = static_cast<unsigned int>(std::floor(scaled));
    const float fraction = scaled - static_cast<float>(lower);
    return static_cast<uint8_t>(lower + (fraction > .5f || (fraction == .5f && (lower & 1u))));
}

inline uint8_t unorm8_transfer(const uint8_t* source, const std::string& dtype) {
    if (dtype == "u8") return load<uint8_t>(source);
    if (dtype == "u16") return static_cast<uint8_t>(load<uint16_t>(source) >> 8);
    if (dtype == "u32") return static_cast<uint8_t>(load<uint32_t>(source) >> 24);
    // The pinned legacy signed 8/16-bit transfer uses the biased mapping from
    // GL 2.1 table 2.9. Quantize that exact rational, before float rounding.
    if (dtype == "i8" || dtype == "i16") {
        const double input = dtype == "i8" ? load<int8_t>(source) : load<int16_t>(source);
        const double maximum = dtype == "i8" ? 255.0 : 65535.0;
        return static_cast<uint8_t>(std::round(std::clamp((2 * input + 1) / maximum, 0.0, 1.0) * 255));
    }
    return nearest_even_byte(float_transfer(source, dtype));
}

inline double storage_value(const uint8_t* source, const std::string& dtype, const Description& description) {
    if (description.storage == Storage::Unorm8) return unorm8_transfer(source, dtype) / 255.0;
    if (description.storage == Storage::Float32 || description.storage == Storage::Float16)
        return float_transfer(source, dtype);
    return source_value(source, dtype, description.integer);
}

inline void encode(uint8_t* destination, double value, const Description& description) {
    if (description.storage == Storage::Float32) { store(destination, static_cast<float>(value)); return; }
    if (description.storage == Storage::Float16) { store(destination, float_to_half(static_cast<float>(value))); return; }
    if (description.integer) {
        const int bits = static_cast<int>(description.component_bytes * 8);
        const double maximum = description.signed_integer ? std::ldexp(1.0, bits - 1) - 1 : std::ldexp(1.0, bits) - 1;
        const double minimum = description.signed_integer ? -std::ldexp(1.0, bits - 1) : 0;
        if (!std::isfinite(value) || value < minimum || value > maximum || std::trunc(value) != value)
            throw error("integer upload value cannot be represented by internal format");
        if (description.signed_integer) {
            if (bits == 8) store(destination, static_cast<int8_t>(value));
            else if (bits == 16) store(destination, static_cast<int16_t>(value));
            else store(destination, static_cast<int32_t>(value));
        } else {
            if (bits == 8) store(destination, static_cast<uint8_t>(value));
            else if (bits == 16) store(destination, static_cast<uint16_t>(value));
            else store(destination, static_cast<uint32_t>(value));
        }
        return;
    }
    if (std::isnan(value)) value = 0;  // Normalized storage has no NaN representation.
    if (description.storage == Storage::Snorm8) store(destination, static_cast<int8_t>(std::round(std::clamp(value, -1.0, 1.0) * 127)));
    else if (description.storage == Storage::Unorm16) store(destination, static_cast<uint16_t>(std::round(std::clamp(value, 0.0, 1.0) * 65535)));
    else store(destination, static_cast<uint8_t>(std::round(std::clamp(value, 0.0, 1.0) * 255)));
}

inline wgpu::FilterMode filter(const std::string& name) {
    if (name == "nearest") return wgpu::FilterMode::Nearest;
    if (name == "linear") return wgpu::FilterMode::Linear;
    throw error("unsupported interpolation " + name + "; mipmapped filters require mip allocation");
}

inline wgpu::AddressMode wrapping(const std::string& name) {
    if (name == "clamp_to_edge") return wgpu::AddressMode::ClampToEdge;
    if (name == "repeat") return wgpu::AddressMode::Repeat;
    if (name == "mirrored_repeat") return wgpu::AddressMode::MirrorRepeat;
    throw error("unsupported wrapping " + name);
}
}  // namespace texture_detail

inline void apply_texture_data(TextureData& data, const ByteBlob& upload, const std::vector<int>& offset,
                               const TextureData* allocation = nullptr) {
    using namespace texture_detail;
    const size_t count = texels(data);
    if (upload.shape.size() != static_cast<size_t>(data.dimensions + 1) ||
        offset.size() != static_cast<size_t>(data.dimensions)) throw error("DATA shape/offset rank differs from SIZE allocation");
    if (upload.shape.back() != data.channels) throw error("DATA channel count differs from SIZE allocation");
    const std::vector<int> extent = data.dimensions == 1 ? std::vector<int>{data.width} :
                                        data.dimensions == 2 ? std::vector<int>{data.height, data.width} :
                                                              std::vector<int>{data.depth, data.height, data.width};
    size_t upload_texels = 1;
    bool entire = true;
    for (int axis = 0; axis < data.dimensions; ++axis) {
        if (offset[axis] < 0 || upload.shape[axis] < 1 || offset[axis] > extent[axis] ||
            upload.shape[axis] > extent[axis] - offset[axis]) throw error("DATA region exceeds SIZE allocation at axis " + std::to_string(axis));
        upload_texels = multiply(upload_texels, upload.shape[axis]);
        entire = entire && offset[axis] == 0 && upload.shape[axis] == extent[axis];
    }
    const size_t component_bytes = dtype_size(upload.dtype);
    const size_t upload_pixel_bytes = multiply(component_bytes, data.channels);
    if (upload.bytes.size() != multiply(upload_texels, upload_pixel_bytes)) throw error("DATA byte size differs from declared shape/dtype");
    if (entire) {
        data.pixels = upload.bytes;
        data.dtype = upload.dtype;
        return;
    }
    const bool mixed = !data.pixels.empty() && data.dtype != upload.dtype;
    const size_t pixel_bytes = mixed ? multiply(sizeof(double), data.channels) : upload_pixel_bytes;
    const size_t total = multiply(count, pixel_bytes);
    std::vector<uint8_t> result;
    Description description;
    if (mixed) {
        const auto& storage = allocation ? *allocation : data;
        if (storage.channels != data.channels || storage.dimensions != data.dimensions)
            throw error("DATA descriptor differs from fixed allocation");
        description = describe(storage);
        const size_t resident_component = dtype_size(data.dtype);
        const size_t components = multiply(count, data.channels);
        if (data.pixels.size() != multiply(components, resident_component))
            throw error("resident byte size differs from SIZE allocation");
        result.resize(total);
        for (size_t component = 0; component < components; ++component) {
            const double value = storage_value(data.pixels.data() + component * resident_component, data.dtype, description);
            store(result.data() + component * sizeof(double), value);
        }
    }
    else if (data.pixels.empty()) result.assign(total, 0);
    else {
        if (data.pixels.size() != total) throw error("resident byte size differs from SIZE allocation");
        result = data.pixels;
    }
    const int patch_w = upload.shape[data.dimensions - 1];
    const int patch_h = data.dimensions >= 2 ? upload.shape[data.dimensions - 2] : 1;
    const int patch_d = data.dimensions == 3 ? upload.shape[0] : 1;
    const int x = offset[data.dimensions - 1];
    const int y = data.dimensions >= 2 ? offset[data.dimensions - 2] : 0;
    const int z = data.dimensions == 3 ? offset[0] : 0;
    const size_t row_bytes = multiply(patch_w, pixel_bytes);
    for (int slice = 0; slice < patch_d; ++slice) {
        for (int row = 0; row < patch_h; ++row) {
            const size_t destination = ((static_cast<size_t>(z + slice) * data.height + y + row) * data.width + x) * pixel_bytes;
            const size_t source = (static_cast<size_t>(slice) * patch_h + row) * patch_w * upload_pixel_bytes;
            if (mixed) {
                for (size_t component = 0; component < static_cast<size_t>(patch_w) * data.channels; ++component) {
                    const double value = storage_value(upload.bytes.data() + source + component * component_bytes,
                                                       upload.dtype, description);
                    store(result.data() + destination + component * sizeof(double), value);
                }
            } else std::memcpy(result.data() + destination, upload.bytes.data() + source, row_bytes);
        }
    }
    data.pixels = std::move(result);
    data.dtype = mixed ? "f64" : upload.dtype;
}

struct TexturePreparation {
    PreparedTexture descriptor;
    texture_detail::Description storage;
    size_t count,input_component,input_pixel;
    bool direct;
};
inline bool texture_source_is_direct(const TextureData& data,const texture_detail::Description& description) {
    using namespace texture_detail;
    const bool direct_f32 = data.dtype == "f32" && description.storage == Storage::Float32;
    const bool direct_u8 = data.dtype == "u8" && description.storage == Storage::Unorm8;
    const bool direct_integer = description.integer && data.dtype ==
        std::string(description.signed_integer ? "i" : "u") + std::to_string(description.component_bytes * 8);
    return description.channels == data.channels && (direct_f32 || direct_u8 || direct_integer);
}
inline TexturePreparation describe_texture_preparation(const TextureData& data,const TextureData* allocation=nullptr) {

    using namespace texture_detail;
    const size_t count = texels(data);
    // DATA may change the source dtype while the allocated GL internal format
    // stays fixed. Regions use their upload extent, not the allocation extent.
    const auto& storage = allocation ? *allocation : data;
    if (storage.channels != data.channels) throw error("DATA channel count differs from fixed allocation");
    if (storage.dimensions != data.dimensions) throw error("DATA dimension rank differs from fixed allocation");
    if (format_channels(data.format) != data.channels) throw error("source format and channel count differ");
    const auto description = describe(storage);
    const size_t input_component = dtype_size(data.dtype);
    const size_t input_pixel = multiply(input_component, data.channels);
    if (!data.pixels.empty() && data.pixels.size() != multiply(count, input_pixel)) throw error("resident byte size differs from allocation");
    PreparedTexture result;
    result.format = native_format(description);
    result.dimension = data.dimensions == 1 ? wgpu::TextureDimension::e1D : data.dimensions == 3 ? wgpu::TextureDimension::e3D : wgpu::TextureDimension::e2D;
    result.view_dimension = data.dimensions == 1 ? wgpu::TextureViewDimension::e1D : data.dimensions == 3 ? wgpu::TextureViewDimension::e3D : wgpu::TextureViewDimension::e2D;
    result.channels = description.channels;
    result.texel_size = description.channels * description.component_bytes;
    result.sample_type = description.integer ? (description.signed_integer ? wgpu::TextureSampleType::Sint : wgpu::TextureSampleType::Uint) :
                         description.storage == Storage::Float32 || description.storage == Storage::Unorm16 ? wgpu::TextureSampleType::UnfilterableFloat : wgpu::TextureSampleType::Float;
    result.requires_float32_filterable = description.storage == Storage::Float32 && (data.min_filter == "linear" || data.mag_filter == "linear");
    result.requires_unorm16 = description.storage == Storage::Unorm16;
    return {std::move(result),description,count,input_component,input_pixel,texture_source_is_direct(data,description)};
}
inline PreparedTexture prepare_texture(const TextureData& data,const TextureData* allocation=nullptr) {
    using namespace texture_detail;
    auto layout=describe_texture_preparation(data,allocation);
    auto result=std::move(layout.descriptor);
    const auto& description=layout.storage;
    const auto count=layout.count,input_component=layout.input_component,input_pixel=layout.input_pixel;
    if (layout.direct) {
        // Preserve float bits (including signed zero and NaN payloads), exact
        // categorical identity, and avoid per-texel conversion for resident
        // image/volume uploads already in their native format.
        if (data.pixels.empty()) result.bytes.assign(multiply(count, result.texel_size), 0);
        else result.bytes = data.pixels;
        return result;
    }
    result.bytes.resize(multiply(count, result.texel_size));
    std::vector<uint8_t> zero(input_pixel, 0);
    for (size_t pixel = 0; pixel < count; ++pixel) {
        const uint8_t* source = data.pixels.empty() ? zero.data() : data.pixels.data() + pixel * input_pixel;
        double values[4] = {0, 0, 0, 1};
        for (int channel = 0; channel < data.channels; ++channel)
            values[channel] = storage_value(source + channel * input_component, data.dtype, description);
        if (description.semantic == "luminance") { values[1] = values[0]; values[2] = values[0]; }
        else if (description.semantic == "luminance_alpha") { values[3] = values[1]; values[1] = values[0]; values[2] = values[0]; }
        else if (description.semantic == "alpha") { values[3] = values[0]; values[0] = values[1] = values[2] = 0; }
        for (int channel = 0; channel < description.channels; ++channel)
            encode(result.bytes.data() + pixel * result.texel_size + channel * description.component_bytes, values[channel], description);
    }
    return result;
}

namespace vispy::textures {
class FullUpload {
    PreparedTexture prepared_;
    const std::vector<uint8_t>* borrowed_=nullptr;
    const uint8_t* address_=nullptr;
    size_t byte_count_=0;
    int width_=0,height_=0,depth_=0;
    friend FullUpload prepare_full_upload(const TextureData&,const TextureData*);
    void check_source() const {
        if(borrowed_ && (borrowed_->data()!=address_ || borrowed_->size()!=byte_count_))
            throw texture_detail::error("borrowed upload source storage changed");
    }
public:
    FullUpload()=default;
    FullUpload(FullUpload&&)=default;
    FullUpload& operator=(FullUpload&&)=default;
    FullUpload(const FullUpload&)=delete;
    FullUpload& operator=(const FullUpload&)=delete;
    const PreparedTexture& prepared() const {return prepared_;}
    bool is_borrowed() const {return borrowed_!=nullptr;}
    const uint8_t* data() const {check_source();return borrowed_?borrowed_->data():prepared_.bytes.data();}
    size_t size() const {check_source();return borrowed_?byte_count_:prepared_.bytes.size();}
    int width() const {return width_;}
    int height() const {return height_;}
    int depth() const {return depth_;}
};

inline FullUpload prepare_full_upload(const TextureData& data,const TextureData* allocation=nullptr) {
    auto layout=describe_texture_preparation(data,allocation);
    FullUpload upload;
    upload.width_=data.width;upload.height_=data.height;upload.depth_=data.depth;
    if(layout.direct && !data.pixels.empty()) {
        upload.prepared_=std::move(layout.descriptor);
        upload.borrowed_=&data.pixels;upload.address_=data.pixels.data();upload.byte_count_=data.pixels.size();
    } else upload.prepared_=prepare_texture(data,allocation);
    return upload;
}
FullUpload prepare_full_upload(TextureData&&,const TextureData* =nullptr)=delete;
FullUpload prepare_full_upload(const TextureData&&,const TextureData* =nullptr)=delete;

template<class Consume>
inline void with_upload_rows(const FullUpload& upload,Consume&& consume) {
    using namespace texture_detail;
    const size_t row_bytes=multiply(static_cast<size_t>(upload.width()),upload.prepared().texel_size);
    const size_t rows=multiply(static_cast<size_t>(upload.height()),upload.depth());
    if(upload.size()!=multiply(row_bytes,rows))throw error("upload layout byte size differs");
    if(row_bytes>UINT32_MAX-255u)throw error("upload row pitch overflows");
    const uint32_t pitch=(static_cast<uint32_t>(row_bytes)+255u)&~255u;
    if(pitch==row_bytes) {
        consume(upload.prepared(),upload.data(),upload.size(),pitch,upload.height());
        return;
    }
    std::vector<uint8_t> padded(multiply(pitch,rows),0);
    for(size_t row=0;row<rows;++row)
        std::memcpy(padded.data()+row*pitch,upload.data()+row*row_bytes,row_bytes);
    consume(upload.prepared(),padded.data(),padded.size(),pitch,upload.height());
}
} // namespace vispy::textures


inline PreparedTexture prepare_region(const TextureData& allocation, const ByteBlob& upload) {
    using namespace texture_detail;
    (void)texels(allocation);
    if (upload.shape.size() != static_cast<size_t>(allocation.dimensions + 1))
        throw error("DATA shape rank differs from fixed allocation");
    if (upload.shape.back() != allocation.channels)
        throw error("DATA channel count differs from fixed allocation");
    // Copy only descriptor fields. The resident pixels can be a full volume,
    // and none of them are needed to convert a separately recorded DATA region.
    TextureData region;
    region.dimensions = allocation.dimensions;
    region.width = upload.shape[allocation.dimensions - 1];
    region.height = allocation.dimensions >= 2 ? upload.shape[allocation.dimensions - 2] : 1;
    region.depth = allocation.dimensions == 3 ? upload.shape[0] : 1;
    region.channels = allocation.channels;
    region.dtype = upload.dtype;
    region.format = allocation.format;
    region.internal_format = allocation.internal_format;
    region.min_filter = allocation.min_filter;
    region.mag_filter = allocation.mag_filter;
    region.pixels = upload.bytes;
    const size_t expected = multiply(multiply(texels(region), region.channels), dtype_size(region.dtype));
    if (region.pixels.size() != expected) throw error("DATA byte size differs from declared shape/dtype");
    return prepare_texture(region, &allocation);
}

inline wgpu::SamplerDescriptor prepare_sampler_descriptor(const TextureData& data) {
    using namespace texture_detail;
    const auto description = describe(data);
    wgpu::SamplerDescriptor descriptor;
    descriptor.minFilter = filter(data.min_filter);
    descriptor.magFilter = filter(data.mag_filter);
    descriptor.mipmapFilter = wgpu::MipmapFilterMode::Nearest;
    descriptor.lodMinClamp = 0;
    // Vulkan's documented emulation of GL_NEAREST/GL_LINEAR uses maxLod=.25:
    // it selects only mip zero while preserving min-vs-mag filter selection.
    // maxLod=0 is sufficient only when both filters are equal. Integer nearest
    // retains that exact zero clamp and its captured one-level policy.
    descriptor.lodMaxClamp = descriptor.minFilter == descriptor.magFilter ? 0.f : .25f;
    if (description.integer && (descriptor.minFilter == wgpu::FilterMode::Linear || descriptor.magFilter == wgpu::FilterMode::Linear))
        throw error("integer textures require nearest interpolation");
    const auto& modes = data.wrapping;
    if (!modes.empty() && modes.size() != 1 && modes.size() != static_cast<size_t>(data.dimensions))
        throw error("wrapping count differs from texture dimensions");
    auto address = [&](size_t index) { return modes.empty() ? wgpu::AddressMode::ClampToEdge : wrapping(modes[modes.size() == 1 ? 0 : index]); };
    // Match upstream GlirTexture.set_wrapping: 2D=(S,T), 3D=(R,S,T).
    descriptor.addressModeU = address(data.dimensions == 3 ? 1 : 0);
    descriptor.addressModeV = data.dimensions == 1 ? wgpu::AddressMode::ClampToEdge : address(data.dimensions == 3 ? 2 : 1);
    descriptor.addressModeW = data.dimensions == 3 ? address(0) : wgpu::AddressMode::ClampToEdge;
    return descriptor;
}

// Only the native runtime's one-level allocation contract authorizes
// base_level_only. Callers must not infer it from GLSL spelling or defaults.
// This is a CPU-only snapshot: no upload, pixel conversion or native handle.
inline vispy::shader::IntegerSamplePolicy snapshot_integer_sample_policy(
        const NormSampler& sampler, const TextureData& data,
        const TextureData* allocation, bool base_level_only) {
    using namespace texture_detail;
    using namespace vispy::shader;
    const auto effective = sampler_texture_descriptor(data, allocation);
    (void)texels(effective);
    const auto storage = describe(effective);
    if (sampler.dim != "2d" || effective.dimensions != 2)
        throw error("normalized integer sampling requires a retained 2D allocation");
    if (!storage.integer || (sampler.sample_scalar != ShaderScalarType::Sint &&
                             sampler.sample_scalar != ShaderScalarType::Uint) ||
        storage.signed_integer != (sampler.sample_scalar == ShaderScalarType::Sint))
        throw error("normalized integer sampling scalar differs from fixed allocation storage");
    if (!base_level_only)
        throw error("normalized integer sampling requires an explicit one-level allocation contract");
    if (sampler.texture_binding == sampler.sampler_binding)
        throw error("normalized integer sampling requires distinct texture and sampler bindings");
    const auto descriptor = prepare_sampler_descriptor(effective);
    if (descriptor.minFilter != wgpu::FilterMode::Nearest || descriptor.magFilter != wgpu::FilterMode::Nearest ||
        descriptor.mipmapFilter != wgpu::MipmapFilterMode::Nearest ||
        descriptor.lodMinClamp != 0 || descriptor.lodMaxClamp != 0)
        throw error("normalized integer sampling requires nearest base-level interpolation");
    auto wrap = [](wgpu::AddressMode mode) {
        if (mode == wgpu::AddressMode::ClampToEdge) return IntegerWrap::ClampToEdge;
        if (mode == wgpu::AddressMode::Repeat) return IntegerWrap::Repeat;
        if (mode == wgpu::AddressMode::MirrorRepeat) return IntegerWrap::MirroredRepeat;
        throw error("normalized integer sampling wrapping is unsupported");
    };
    return {sampler.texture_binding, sampler.sampler_binding, sampler.sample_scalar,
            wrap(descriptor.addressModeU), wrap(descriptor.addressModeV), true, true};
}

inline wgpu::Sampler create_sampler(const wgpu::Device& device, const TextureData& data) {
    const auto description = texture_detail::describe(data);
    const bool linear = data.min_filter == "linear" || data.mag_filter == "linear";
    if (description.storage == texture_detail::Storage::Float32 && linear && !device.HasFeature(wgpu::FeatureName::Float32Filterable))
        throw texture_detail::error("linear float32 sampling requires granted Float32Filterable feature");
    if (description.storage == texture_detail::Storage::Unorm16 && !device.HasFeature(wgpu::FeatureName::Unorm16TextureFormats))
        throw texture_detail::error("unorm16 storage requires granted Unorm16TextureFormats feature");
    const auto descriptor = prepare_sampler_descriptor(data);
    return device.CreateSampler(&descriptor);
}
