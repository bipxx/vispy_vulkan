#include "shader/tint_wgsl.hpp"

// The matching public umbrella intentionally guards these declarations by
// producer feature. Both features are required by the VisPy Dawn build.
#define TINT_BUILD_SPV_READER 1
#define TINT_BUILD_WGSL_WRITER 1
// The SDK exposes the public include target. Tint's private headers also
// use Dawn's utility build config, whose default enables debug assertions.
#define DAWN_HAVE_UTILS_BUILD_CONFIG 1
#ifndef NDEBUG
#define DAWN_ENABLE_ASSERTS 1
#endif
#include <tint/tint.h>

#include "src/tint/lang/core/ir/module.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <span>
#include <stdexcept>
#include <utility>

namespace vispy::shader {
namespace {

uint64_t shader_hash(const std::vector<uint32_t>& words, SpirvDerivativeMode mode) {
    uint64_t hash = 14695981039346656037ull;
    for (auto byte : std::as_bytes(std::span{words})) {
        hash ^= std::to_integer<uint8_t>(byte);
        hash *= 1099511628211ull;
    }
    return (hash ^ static_cast<uint64_t>(mode)) * 1099511628211ull;
}

[[noreturn]] void translation_error(const std::vector<uint32_t>& words, SpirvDerivativeMode mode,
                                    const char* label, const char* phase, const std::string& reason) {
    const auto key = std::to_string(shader_hash(words, mode));
    std::string message = "Tint " + std::string(phase) + " failed for " + label +
                          " (shader " + key + "): " + reason;
    if (const char* directory = std::getenv("VISPY_DAWN_SHADER_DUMP"); directory && *directory) {
        const auto root = std::filesystem::u8path(directory);
        std::filesystem::create_directories(root);
        std::ofstream binary(root / ("tint-" + key + ".spv"), std::ios::binary);
        binary.write(reinterpret_cast<const char*>(words.data()),
                     static_cast<std::streamsize>(words.size() * sizeof(uint32_t)));
        std::ofstream log(root / ("tint-" + key + ".txt"));
        log << message << "\nallow_non_uniform_derivatives="
            << (mode == SpirvDerivativeMode::AllowNonUniform) << '\n';
        if (!binary || !log) message += "\nTint shader diagnostic dump failed";
    }
    throw std::runtime_error(message);
}

}  // namespace

size_t TintWgslCache::Hash::operator()(const Key& key) const {
    return static_cast<size_t>(shader_hash(key.words, key.derivative_mode));
}

std::shared_ptr<const std::string> TintWgslCache::translate(
    const std::vector<uint32_t>& words, SpirvDerivativeMode derivative_mode, const char* label) {
    Key key{words, derivative_mode};
    if (auto found = shaders_.find(key); found != shaders_.end()) return found->second;

    auto ir = tint::spirv::reader::ReadIR(words);
    if (ir != tint::Success) translation_error(words, derivative_mode, label, "SPIR-V reader", ir.Failure().reason);

    tint::wgsl::writer::Options options;
    options.allow_non_uniform_derivatives = derivative_mode == SpirvDerivativeMode::AllowNonUniform;
    options.disable_unreachable_code_warning = true;
    // Dawn checks the emitted module against the actual device's features.
    options.allowed_features = tint::wgsl::AllowedFeatures::Everything();
    auto wgsl = tint::wgsl::writer::WgslFromIR(ir.Get(), options);
    if (wgsl != tint::Success) translation_error(words, derivative_mode, label, "WGSL writer", wgsl.Failure().reason);

    auto source = std::make_shared<const std::string>(std::move(wgsl.Get().wgsl));
    constexpr size_t byte_limit = 8 * 1024 * 1024;
    constexpr size_t entry_limit = 256;
    const auto bytes = words.size() * sizeof(uint32_t) + source->size();
    if (bytes > byte_limit) return source;
    if (shaders_.size() == entry_limit || bytes_ + bytes > byte_limit) clear();
    shaders_.emplace(std::move(key), source);
    bytes_ += bytes;
    return source;
}

void TintWgslCache::clear() {
    shaders_.clear();
    bytes_ = 0;
}

}  // namespace vispy::shader
