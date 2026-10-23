#include "runtime_framebuffer_config.hpp"

#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
template <typename Function> void rejects(Function&& function, const char* message) {
    bool threw = false;
    try { function(); } catch (const std::runtime_error&) { threw = true; }
    require(threw, message);
}
}

int main() {
    using vispy::framebuffer::describe;
    using vispy::framebuffer::DepthStorage;
    const auto normal = describe({4, 8, "rgba8unorm", false}, DepthStorage::Depth24PlusStencil8,
                                 true, true, 1, false);
    require(normal.red_size == 8 && normal.green_size == 8 && normal.blue_size == 8 && normal.alpha_size == 8,
            "default color sizes do not describe RGBA8 storage");
    require(!normal.depth_size.has_value() && !normal.depth_size_exact && normal.depth_size_minimum == 24,
            "opaque Depth24Plus precision must not be reported as exact");
    require(normal.stencil_size == 8 && normal.backing_stencil_size == 8,
            "stencil storage precision differs");
    require(normal.samples == 0 && normal.sample_count == 1 && !normal.double_buffer && !normal.stereo,
            "headless single-sample target configuration differs");
    const auto msaa = describe({4, 8, "rgba8unorm", false}, DepthStorage::Depth24PlusStencil8,
                               true, true, 4, true);
    require(msaa.samples == 4 && msaa.sample_count == 4 && msaa.double_buffer,
            "MSAA/surface metadata differs from actual configuration");
    for (int channels : {1, 2, 4}) for (int bits : {8, 16, 32}) {
        const auto color = describe({channels, bits, "retained-native-format", false}, DepthStorage::None,
                                    false, false, 1, false);
        require(color.red_size == bits && color.green_size == (channels >= 2 ? bits : 0) &&
                color.blue_size == (channels == 4 ? bits : 0) && color.alpha_size == (channels == 4 ? bits : 0),
                "missing color channels must not inherit GL defaults");
        require(color.depth_size == 0 && color.depth_size_minimum == 0 && color.depth_size_exact &&
                color.stencil_size == 0 && color.depth_stencil_format == "undefined",
                "color-only FBO must not inherit canvas depth/stencil");
    }
    const auto depth_only = describe({4, 16, "rgba16float", false}, DepthStorage::Depth24PlusStencil8,
                                     true, false, 1, false);
    require(!depth_only.depth_size && depth_only.stencil_size == 0 && depth_only.backing_stencil_size == 8,
            "logical depth attachment and combined native backing must remain distinct");
    const auto stencil_only = describe({4, 8, "rgba8unorm", false}, DepthStorage::Depth24PlusStencil8,
                                       false, true, 1, false);
    require(stencil_only.depth_size == 0 && stencil_only.depth_size_exact &&
            stencil_only.depth_size_minimum == 0 && stencil_only.stencil_size == 8 &&
            stencil_only.backing_depth_size_minimum == 24,
            "stencil-only logical attachment must not advertise depth availability");
    const auto srgb = describe({4, 8, "rgba8unorm-srgb", true}, DepthStorage::None, false, false, 1, false);
    require(srgb.srgb && srgb.color_format == "rgba8unorm-srgb", "color encoding must be retained");
    rejects([&] { describe({3, 8, "rgb8", false}, DepthStorage::None, false, false, 1, false); },
            "unsupported physical RGB layout was guessed");
    rejects([&] { describe({4, 0, "rgba", false}, DepthStorage::None, false, false, 1, false); },
            "unspecified component precision was guessed");
    rejects([&] { describe({4, 8, "", false}, DepthStorage::None, false, false, 1, false); },
            "missing storage identity was accepted");
    rejects([&] { describe({4, 8, "rgba8unorm", false}, DepthStorage::None, true, false, 1, false); },
            "missing depth backing was accepted");
    rejects([&] { describe({4, 8, "rgba8unorm", false}, DepthStorage::None, false, false, 2, false); },
            "unsupported sample count was accepted");
    rejects([&] { describe({4, 8, "rgba8unorm", false}, static_cast<DepthStorage>(99), false, false, 1, false); },
            "unknown depth backing was accepted");
    std::cout << "framebuffer configuration contract passed\n";
}
