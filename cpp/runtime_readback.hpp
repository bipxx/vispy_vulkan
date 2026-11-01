#pragma once

#include <webgpu/webgpu_cpp.h>

#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>

// Color read_pixels converts normalized or floating storage to public RGBA.
// Integer attachments require an integer API and are deliberately rejected.
enum class CaptureStorage { Unorm8, Unorm16, Snorm8, Float16, Float32 };

struct CaptureFormat {
    int channels;
    size_t component_bytes;
    size_t texel_bytes;
    CaptureStorage storage;
    bool bgra;
};

inline CaptureFormat capture_format(wgpu::TextureFormat format) {
    using F = wgpu::TextureFormat;
    using S = CaptureStorage;
    switch (format) {
        case F::R8Unorm: return {1, 1, 1, S::Unorm8, false};
        case F::RG8Unorm: return {2, 1, 2, S::Unorm8, false};
        case F::RGBA8Unorm:
        case F::RGBA8UnormSrgb: return {4, 1, 4, S::Unorm8, false};
        case F::BGRA8Unorm:
        case F::BGRA8UnormSrgb: return {4, 1, 4, S::Unorm8, true};
        case F::R16Unorm: return {1, 2, 2, S::Unorm16, false};
        case F::RG16Unorm: return {2, 2, 4, S::Unorm16, false};
        case F::RGBA16Unorm: return {4, 2, 8, S::Unorm16, false};
        case F::R8Snorm: return {1, 1, 1, S::Snorm8, false};
        case F::RG8Snorm: return {2, 1, 2, S::Snorm8, false};
        case F::RGBA8Snorm: return {4, 1, 4, S::Snorm8, false};
        case F::R16Float: return {1, 2, 2, S::Float16, false};
        case F::RG16Float: return {2, 2, 4, S::Float16, false};
        case F::RGBA16Float: return {4, 2, 8, S::Float16, false};
        case F::R32Float: return {1, 4, 4, S::Float32, false};
        case F::RG32Float: return {2, 4, 8, S::Float32, false};
        case F::RGBA32Float: return {4, 4, 16, S::Float32, false};
        case F::R8Uint: case F::R8Sint: case F::RG8Uint: case F::RG8Sint:
        case F::RGBA8Uint: case F::RGBA8Sint:
        case F::R16Uint: case F::R16Sint: case F::RG16Uint: case F::RG16Sint:
        case F::RGBA16Uint: case F::RGBA16Sint:
        case F::R32Uint: case F::R32Sint: case F::RG32Uint: case F::RG32Sint:
        case F::RGBA32Uint: case F::RGBA32Sint: case F::RGB10A2Uint:
            throw std::runtime_error("read_pixels: integer color attachments require an integer capture API");
        default:
            throw std::runtime_error("read_pixels: unsupported color capture format");
    }
}

namespace capture_detail {

inline uint16_t little_u16(const uint8_t* bytes) {
    return static_cast<uint16_t>(bytes[0] | (static_cast<uint16_t>(bytes[1]) << 8));
}

inline uint32_t little_u32(const uint8_t* bytes) {
    return static_cast<uint32_t>(bytes[0]) | (static_cast<uint32_t>(bytes[1]) << 8) |
           (static_cast<uint32_t>(bytes[2]) << 16) | (static_cast<uint32_t>(bytes[3]) << 24);
}

inline float half_float(uint16_t half) {
    const uint32_t sign = static_cast<uint32_t>(half & 0x8000u) << 16;
    uint32_t exponent = (half >> 10) & 31u;
    uint32_t fraction = half & 1023u;
    uint32_t bits;
    if (exponent == 0) {
        if (fraction == 0) bits = sign;
        else {
            int unbiased = -14;
            while ((fraction & 1024u) == 0) { fraction <<= 1; --unbiased; }
            bits = sign | (static_cast<uint32_t>(unbiased + 127) << 23) |
                   ((fraction & 1023u) << 13);
        }
    } else if (exponent == 31) {
        bits = sign | 0x7f800000u | (fraction << 13);
    } else {
        bits = sign | ((exponent + 112u) << 23) | (fraction << 13);
    }
    return std::bit_cast<float>(bits);
}

inline float component(const uint8_t* bytes, CaptureStorage storage) {
    switch (storage) {
        case CaptureStorage::Unorm8: return static_cast<float>(bytes[0]) / 255.0f;
        case CaptureStorage::Unorm16: return static_cast<float>(little_u16(bytes)) / 65535.0f;
        case CaptureStorage::Snorm8: {
            const int value = bytes[0] < 128 ? bytes[0] : static_cast<int>(bytes[0]) - 256;
            return value == -128 ? -1.0f : static_cast<float>(value) / 127.0f;
        }
        case CaptureStorage::Float16: return half_float(little_u16(bytes));
        case CaptureStorage::Float32: return std::bit_cast<float>(little_u32(bytes));
    }
    throw std::runtime_error("read_pixels: invalid capture storage");
}

}  // namespace capture_detail

inline std::array<float, 4> read_color(const uint8_t* bytes, const CaptureFormat& format) {
    if (!bytes || format.channels < 1 || format.channels > 4 ||
        format.texel_bytes != static_cast<size_t>(format.channels) * format.component_bytes ||
        (format.bgra && format.channels != 4))
        throw std::runtime_error("read_pixels: invalid capture descriptor or source pointer");
    const size_t width = format.storage == CaptureStorage::Float32 ? 4 :
        (format.storage == CaptureStorage::Float16 || format.storage == CaptureStorage::Unorm16) ? 2 : 1;
    if (format.component_bytes != width)
        throw std::runtime_error("read_pixels: capture component width differs from storage");
    std::array<float, 4> color{0.0f, 0.0f, 0.0f, 1.0f};
    for (int channel = 0; channel < format.channels; ++channel) {
        const int output = format.bgra && channel < 3 ? 2 - channel : channel;
        color[output] = capture_detail::component(bytes + channel * width, format.storage);
    }
    return color;
}

inline uint8_t capture_byte(float value) {
    // NaN and signed zero deterministically produce zero. Infinities clamp.
    if (!(value > 0.0f)) return 0;
    if (value >= 1.0f) return 255;
    return static_cast<uint8_t>(std::lround(value * 255.0f));
}

// An 8-bit normalized RGBA or BGRA color read gives each byte v back as
// capture_byte(v / 255.0f), which is v (readback_contract checks every value),
// so its rows are copied, swizzled or stripped of alpha without per-texel
// conversion (B19). Every other storage keeps read_color and capture_byte.
inline bool unorm8_rgba_rows(const CaptureFormat& format) {
    return format.storage == CaptureStorage::Unorm8 && format.channels == 4 && format.texel_bytes == 4;
}

inline void copy_unorm8_rgba_row(const uint8_t* source, uint8_t* destination, size_t width, bool bgra,
                                 int channels) {
    if (!bgra && channels == 4) {
        std::memcpy(destination, source, width * 4);
        return;
    }
    for (size_t texel = 0; texel < width; ++texel, source += 4, destination += channels) {
        destination[0] = source[bgra ? 2 : 0];
        destination[1] = source[1];
        destination[2] = source[bgra ? 0 : 2];
        if (channels == 4) destination[3] = source[3];
    }
}
