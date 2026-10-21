#include "runtime_readback.hpp"

#include <bit>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {
void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

template <typename Function> void rejects(Function function, const std::string& expected) {
    try { function(); }
    catch (const std::runtime_error& error) {
        require(std::string(error.what()).find(expected) != std::string::npos, "wrong rejection diagnostic");
        return;
    }
    throw std::runtime_error("unsupported capture was accepted");
}

void append16(std::vector<uint8_t>& bytes, uint16_t value) {
    bytes.push_back(static_cast<uint8_t>(value));
    bytes.push_back(static_cast<uint8_t>(value >> 8));
}

void append32(std::vector<uint8_t>& bytes, uint32_t value) {
    for (int offset = 0; offset < 32; offset += 8) bytes.push_back(static_cast<uint8_t>(value >> offset));
}

void normalized_channels() {
    using F = wgpu::TextureFormat;
    const uint8_t bytes[] = {17, 83, 191, 229};
    for (auto format : {F::R8Unorm, F::RG8Unorm, F::RGBA8Unorm, F::RGBA8UnormSrgb}) {
        auto descriptor = capture_format(format);
        auto color = read_color(bytes, descriptor);
        require(descriptor.component_bytes == 1 && descriptor.texel_bytes == static_cast<size_t>(descriptor.channels), "unorm8 byte stride");
        for (int channel = 0; channel < 4; ++channel) {
            const float expected = channel < descriptor.channels ? bytes[channel] / 255.0f : channel == 3 ? 1.0f : 0.0f;
            require(color[channel] == expected, "asymmetric normalized or absent component differs");
        }
    }
    for (auto format : {F::BGRA8Unorm, F::BGRA8UnormSrgb}) {
        auto color = read_color(bytes, capture_format(format));
        require(color == std::array<float,4>{191 / 255.0f, 83 / 255.0f, 17 / 255.0f, 229 / 255.0f}, "BGRA capture swizzle");
    }
    std::vector<uint8_t> words;
    for (uint16_t value : {1, 32767, 32768, 65535}) append16(words, value);
    for (auto format : {F::R16Unorm, F::RG16Unorm, F::RGBA16Unorm}) {
        auto descriptor = capture_format(format);
        auto color = read_color(words.data(), descriptor);
        const float expected[] = {1 / 65535.0f, 32767 / 65535.0f, 32768 / 65535.0f, 1.0f};
        require(descriptor.texel_bytes == static_cast<size_t>(descriptor.channels) * 2, "unorm16 texel stride");
        for (int channel = 0; channel < descriptor.channels; ++channel)
            require(color[channel] == expected[channel], "unorm16 conversion");
        if (descriptor.channels < 4) require(color[2] == 0 && color[3] == 1, "unorm16 absent blue/alpha");
    }
    const uint8_t signed_bytes[] = {128, 192, 63, 127};
    for (auto format : {F::R8Snorm, F::RG8Snorm, F::RGBA8Snorm}) {
        auto descriptor = capture_format(format);
        auto color = read_color(signed_bytes, descriptor);
        const float expected[] = {-1, -64 / 127.0f, 63 / 127.0f, 1};
        for (int channel = 0; channel < descriptor.channels; ++channel)
            require(color[channel] == expected[channel], "signed normalized conversion/clamp");
    }
    const uint8_t minus127 = 129;
    require(read_color(&minus127, capture_format(F::R8Snorm))[0] == -1.0f, "snorm negative endpoint");
}

void floating_channels() {
    using F = wgpu::TextureFormat;
    std::vector<uint8_t> single;
    const uint32_t bits[] = {std::bit_cast<uint32_t>(-23.5f), std::bit_cast<uint32_t>(100000.0f), 0x7fc12345u, 0x80000000u};
    for (uint32_t value : bits) append32(single, value);
    for (auto format : {F::R32Float, F::RG32Float, F::RGBA32Float}) {
        auto descriptor = capture_format(format);
        auto color = read_color(single.data(), descriptor);
        require(descriptor.component_bytes == 4 && descriptor.texel_bytes == static_cast<size_t>(descriptor.channels) * 4, "float32 strides");
        for (int channel = 0; channel < descriptor.channels; ++channel)
            require(std::bit_cast<uint32_t>(color[channel]) == bits[channel], "float32 range/NaN payload/signed zero changed");
        if (descriptor.channels < 4) require(color[2] == 0 && color[3] == 1, "float32 absent components");
    }
    std::vector<uint8_t> halves;
    for (uint16_t value : {0xc580, 0x7bff, 0x7e55, 0x8000}) append16(halves, value);
    for (auto format : {F::R16Float, F::RG16Float, F::RGBA16Float}) {
        auto descriptor = capture_format(format);
        auto color = read_color(halves.data(), descriptor);
        require(color[0] == -5.5f, "negative half float scientific range");
        if (descriptor.channels >= 2) require(color[1] == 65504.0f, "maximum finite half");
        if (descriptor.channels == 4) {
            require(std::isnan(color[2]), "half NaN was clamped");
            require(std::bit_cast<uint32_t>(color[3]) == 0x80000000u, "half negative zero lost");
        }
    }
    // Exhaustive binary16 finite/subnormal/infinity/NaN classification against
    // an independent arithmetic reference; no native device or upload helper.
    auto descriptor = capture_format(F::R16Float);
    for (uint32_t half = 0; half <= 65535; ++half) {
        const uint8_t bytes[] = {static_cast<uint8_t>(half), static_cast<uint8_t>(half >> 8)};
        const float actual = read_color(bytes, descriptor)[0];
        const int exponent = (half >> 10) & 31;
        const int fraction = half & 1023;
        const bool negative = (half & 0x8000) != 0;
        if (exponent == 31) {
            require(fraction ? std::isnan(actual) : std::isinf(actual), "half special classification");
            require(std::signbit(actual) == negative, "half special sign");
        } else {
            float expected = exponent == 0 ? std::ldexp(static_cast<float>(fraction), -24) :
                std::ldexp(1.0f + fraction / 1024.0f, exponent - 15);
            if (negative) expected = -expected;
            require(std::bit_cast<uint32_t>(actual) == std::bit_cast<uint32_t>(expected), "half arithmetic reference mismatch");
        }
    }
}

void byte_output_and_rejections() {
    using F = wgpu::TextureFormat;
    const float nan = std::numeric_limits<float>::quiet_NaN();
    require(capture_byte(nan) == 0 && capture_byte(-0.0f) == 0, "NaN/negative zero byte output");
    require(capture_byte(-std::numeric_limits<float>::infinity()) == 0 &&
            capture_byte(std::numeric_limits<float>::infinity()) == 255, "infinity byte clamp");
    require(capture_byte(-3) == 0 && capture_byte(4) == 255, "scientific range byte clamp");
    require(capture_byte(.25f) == 64 && capture_byte(.5f) == 128 && capture_byte(.75f) == 191, "byte rounding");
    for (int byte = 0; byte < 256; ++byte)
        require(capture_byte(byte / 255.0f) == byte, "unorm8 capture identity");
    for (auto format : {F::R8Uint, F::R8Sint, F::RG8Uint, F::RG8Sint, F::RGBA8Uint, F::RGBA8Sint,
                       F::R16Uint, F::R16Sint, F::RG16Uint, F::RG16Sint, F::RGBA16Uint, F::RGBA16Sint,
                       F::R32Uint, F::R32Sint, F::RG32Uint, F::RG32Sint, F::RGBA32Uint, F::RGBA32Sint, F::RGB10A2Uint})
        rejects([&] { capture_format(format); }, "integer color");
    for (auto format : {F::Undefined, F::Depth24Plus, F::Depth32Float, F::BC1RGBAUnorm, F::RGB10A2Unorm})
        rejects([&] { capture_format(format); }, "unsupported color");
    const uint8_t bytes[] = {1, 2, 3, 4};
    auto descriptor = capture_format(F::RGBA8Unorm);
    rejects([&] { read_color(nullptr, descriptor); }, "source pointer");
    descriptor.component_bytes = 2;
    rejects([&] { read_color(bytes, descriptor); }, "descriptor");
    descriptor.texel_bytes = 8;
    rejects([&] { read_color(bytes, descriptor); }, "component width");
}
}  // namespace

int main() {
    try {
        normalized_channels();
        floating_channels();
        byte_output_and_rejections();
        std::cout << "readback CPU contracts passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
