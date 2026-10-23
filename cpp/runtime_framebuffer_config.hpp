#pragma once

#include <optional>
#include <stdexcept>
#include <string>

// The public configuration describes logical attachment channels and the
// retained native storage. Depth24Plus does not expose its physical precision;
// an absent exact depth_size must never be replaced by a guessed GL default.
struct FramebufferConfiguration {
    int red_size = 0, green_size = 0, blue_size = 0, alpha_size = 0;
    std::optional<int> depth_size = 0;
    int depth_size_minimum = 0, stencil_size = 0;
    bool depth_size_exact = true;
    int backing_depth_size_minimum = 0, backing_stencil_size = 0;
    int sample_count = 1, samples = 0;
    bool double_buffer = false, stereo = false, srgb = false;
    bool has_depth_attachment = false, has_stencil_attachment = false;
    int framebuffer_id = 0, width = 0, height = 0;
    std::string color_format, depth_stencil_format = "undefined";
    std::string configuration_source;
};

namespace vispy::framebuffer {

struct ColorStorage {
    int channels = 0, component_bits = 0;
    std::string format;
    bool srgb = false;
};

enum class DepthStorage { None, Depth24PlusStencil8, Depth32Float };

inline FramebufferConfiguration describe(const ColorStorage& color, DepthStorage depth,
                                         bool depth_attached, bool stencil_attached,
                                         int sample_count, bool double_buffer) {
    if ((color.channels != 1 && color.channels != 2 && color.channels != 4) ||
        (color.component_bits != 8 && color.component_bits != 16 && color.component_bits != 32) ||
        color.format.empty())
        throw std::runtime_error("framebuffer configuration: unsupported color storage");
    if (sample_count != 1 && sample_count != 4)
        throw std::runtime_error("framebuffer configuration: unsupported sample count");
    if (depth != DepthStorage::None && depth != DepthStorage::Depth24PlusStencil8 && depth != DepthStorage::Depth32Float)
        throw std::runtime_error("framebuffer configuration: unsupported depth/stencil storage");
    if (depth == DepthStorage::None && (depth_attached || stencil_attached))
        throw std::runtime_error("framebuffer configuration: missing depth/stencil storage");
    if (depth == DepthStorage::Depth32Float && stencil_attached)
        throw std::runtime_error("framebuffer configuration: Depth32Float has no stencil aspect");
    FramebufferConfiguration result;
    result.red_size = color.component_bits;
    if (color.channels >= 2) result.green_size = color.component_bits;
    if (color.channels == 4) result.blue_size = result.alpha_size = color.component_bits;
    result.color_format = color.format;
    result.srgb = color.srgb;
    result.sample_count = sample_count;
    // GL_SAMPLES and the existing public configuration use zero for a
    // single-sampled target, independently of WebGPU's sampleCount of one.
    result.samples = sample_count == 1 ? 0 : sample_count;
    result.double_buffer = double_buffer;
    result.has_depth_attachment = depth_attached;
    result.has_stencil_attachment = stencil_attached;
    if (depth == DepthStorage::Depth24PlusStencil8) {
        result.depth_stencil_format = "depth24plus-stencil8";
        result.backing_depth_size_minimum = 24;
        result.backing_stencil_size = 8;
        if (depth_attached) {
            result.depth_size = std::nullopt;
            result.depth_size_minimum = 24;
            result.depth_size_exact = false;
        }
        if (stencil_attached) result.stencil_size = 8;
    }
    if (depth == DepthStorage::Depth32Float) {
        result.depth_stencil_format = "depth32float";
        result.backing_depth_size_minimum = 32;
        if (depth_attached) result.depth_size = result.depth_size_minimum = 32;
    }
    return result;
}

}  // namespace vispy::framebuffer
