#include "runtime_texture.hpp"

#include <array>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {
using vispy::shader::IntegerSamplePolicy;
using vispy::shader::IntegerWrap;
size_t checks = 0;
void require(bool value, const std::string& message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
template<class Function> void rejects(Function&& function, const std::string& message) {
    bool failed = false;
    try { function(); }
    catch (const std::runtime_error&) { failed = true; }
    require(failed, message);
}
TextureData image(bool sint) {
    TextureData data;
    data.width = 8;
    data.height = 4;
    data.channels = 1;
    data.format = "red";
    data.internal_format = sint ? "r32i" : "r32ui";
    data.dtype = sint ? "i32" : "u32";
    // Exact high words/extremes are deliberately irrelevant to sampler policy.
    const uint32_t words[] = {0x01000001u, 0xffffffffu, 0x80000000u, 0x7fffffffu};
    data.pixels.resize(sizeof(words));
    std::memcpy(data.pixels.data(), words, sizeof(words));
    return data;
}
NormSampler sampler(bool sint) {
    NormSampler result;
    result.name = "u_words";
    result.dim = "2d";
    result.texture_binding = 3;
    result.sampler_binding = 4;
    result.sample_scalar = sint ? ShaderScalarType::Sint : ShaderScalarType::Uint;
    return result;
}
bool equal(const IntegerSamplePolicy& a, const IntegerSamplePolicy& b) {
    return a.texture_binding == b.texture_binding && a.sampler_binding == b.sampler_binding &&
           a.scalar == b.scalar && a.s == b.s && a.t == b.t &&
           a.nearest == b.nearest && a.base_level_only == b.base_level_only;
}

void wrap_and_scalar_domain() {
    const std::array<std::string, 3> names = {"clamp_to_edge", "repeat", "mirrored_repeat"};
    const std::array<IntegerWrap, 3> expected = {IntegerWrap::ClampToEdge, IntegerWrap::Repeat, IntegerWrap::MirroredRepeat};
    for (bool sint : {false, true}) {
        auto data = image(sint);
        const auto bytes = data.pixels;
        const auto reflected = sampler(sint);
        auto p = snapshot_integer_sample_policy(reflected, data, nullptr, true);
        require(p.s == IntegerWrap::ClampToEdge && p.t == IntegerWrap::ClampToEdge,
                "empty 2D wrap must snapshot clamp-to-edge on both axes");
        require(p.texture_binding == 3 && p.sampler_binding == 4 && p.scalar == reflected.sample_scalar &&
                p.nearest && p.base_level_only, "snapshot must retain actual binding/scalar/admission metadata");
        for (size_t s = 0; s < names.size(); ++s) {
            data.wrapping = {names[s]};
            p = snapshot_integer_sample_policy(reflected, data, nullptr, true);
            require(p.s == expected[s] && p.t == expected[s], "single wrap must broadcast to S and T");
            for (size_t t = 0; t < names.size(); ++t) {
                data.wrapping = {names[s], names[t]};
                p = snapshot_integer_sample_policy(reflected, data, nullptr, true);
                require(p.s == expected[s] && p.t == expected[t], "2D wrapping must preserve distinct S/T ordering");
                const auto descriptor = prepare_sampler_descriptor(data);
                require(descriptor.minFilter == wgpu::FilterMode::Nearest && descriptor.magFilter == wgpu::FilterMode::Nearest &&
                        descriptor.lodMinClamp == 0 && descriptor.lodMaxClamp == 0,
                        "snapshot policy must agree with authoritative native sampler descriptor");
            }
        }
        require(data.pixels == bytes, "policy capture must not convert or touch exact integer pixel words");
    }
}

void fixed_allocation_and_retained_values() {
    auto data = image(false);
    const auto allocation = std::make_shared<const TextureData>(data);
    const auto reflected = sampler(false);
    data.dtype = "f64";  // Numeric CPU shadow after a mixed DATA update.
    data.wrapping = {"repeat", "mirrored_repeat"};
    const auto old = snapshot_integer_sample_policy(reflected, data, allocation.get(), true);
    const auto descriptor = sampler_texture_descriptor(data, allocation.get());
    require(descriptor.dtype == "u32" && descriptor.internal_format == "r32ui" && descriptor.dimensions == 2,
            "sampling storage must use the frozen allocation rather than the DATA shadow scalar");
    require(descriptor.wrapping == data.wrapping && descriptor.min_filter == data.min_filter &&
            descriptor.mag_filter == data.mag_filter, "current revision sampler state must override allocation-time defaults");
    require(descriptor.pixels.empty() && descriptor.pixels.capacity() == 0,
            "sampler descriptor capture must not copy image payload capacity");
    data.wrapping = {"clamp_to_edge", "repeat"};
    const auto next = snapshot_integer_sample_policy(reflected, data, allocation.get(), true);
    require(old.s == IntegerWrap::Repeat && old.t == IntegerWrap::MirroredRepeat &&
            next.s == IntegerWrap::ClampToEdge && next.t == IntegerWrap::Repeat,
            "retained policy values must survive a later wrapping revision");
    data.min_filter = "linear";
    rejects([&] { snapshot_integer_sample_policy(reflected, data, allocation.get(), true); },
            "later invalid filter must not reinterpret a retained nearest policy");
    require(old.nearest && old.base_level_only && old.s == IntegerWrap::Repeat,
            "rejected later state must leave the captured prior policy unchanged");
    data.min_filter = "nearest";
    data.wrapping = {"repeat", "mirrored_repeat"};
    data.width = 2048; data.height = 1024; data.pixels.assign(1, 17);
    const auto same = snapshot_integer_sample_policy(reflected, data, allocation.get(), true);
    require(equal(old, same), "data bytes and texture dimensions must not enter the semantic sampling policy");
    auto replacement = image(false);
    replacement.width = 7; replacement.height = 5;
    replacement.wrapping = data.wrapping;
    require(equal(old, snapshot_integer_sample_policy(reflected, replacement, nullptr, true)),
            "a new same-policy allocation must share shader policy independently of object/size/payload");
    auto signed_data = image(true);
    signed_data.wrapping = replacement.wrapping;
    const auto signed_policy = snapshot_integer_sample_policy(sampler(true), signed_data, nullptr, true);
    require(old.scalar != signed_policy.scalar, "signed/unsigned storage policies must remain distinct");
}

void admission_refusals() {
    const auto reflected = sampler(false);
    const auto original = image(false);
    for (const auto& name : {"linear", "linear_mipmap_linear", "nearest_mipmap_nearest", "unsupported"}) {
        for (bool minification : {false, true}) {
            auto data = original;
            (minification ? data.min_filter : data.mag_filter) = name;
            const auto bytes = data.pixels;
            rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); },
                    "non-nearest or unsupported min/mag interpolation must refuse before native preparation");
            require(data.pixels == bytes, "failed sampler capture must not mutate pixel bytes");
        }
    }
    auto data = original;
    data.wrapping = {"repeat", "clamp_to_edge", "mirrored_repeat"};
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); }, "2D wrapping rank mismatch");
    data.wrapping = {"unsupported"};
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); }, "unsupported wrapping mode");
    data = original;
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, false); }, "missing explicit one-level contract");
    rejects([&] { snapshot_integer_sample_policy(sampler(true), data, nullptr, true); }, "sampled signedness/storage mismatch");
    auto bad_sampler = reflected;
    bad_sampler.sample_scalar = ShaderScalarType::Float;
    rejects([&] { snapshot_integer_sample_policy(bad_sampler, data, nullptr, true); }, "float shader cannot request integer lowering");
    bad_sampler = reflected; bad_sampler.sample_scalar = ShaderScalarType::Bool;
    rejects([&] { snapshot_integer_sample_policy(bad_sampler, data, nullptr, true); }, "boolean sampled scalar is unsupported");
    bad_sampler = reflected; bad_sampler.sampler_binding = bad_sampler.texture_binding;
    rejects([&] { snapshot_integer_sample_policy(bad_sampler, data, nullptr, true); }, "combined binding alias is invalid");
    for (const auto& dim : {"3d", "cube"}) {
        bad_sampler = reflected; bad_sampler.dim = dim;
        rejects([&] { snapshot_integer_sample_policy(bad_sampler, data, nullptr, true); }, "non-2D sampler dimension");
    }
    data.dimensions = 3; data.depth = 2;
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); }, "non-2D retained allocation");
    data = original; data.internal_format = "r32f"; data.dtype = "f32";
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); }, "float fixed storage is not integer");
    data = TextureData{};
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); }, "float placeholder cannot acquire integer policy");
    data = original; data.width = 0;
    rejects([&] { snapshot_integer_sample_policy(reflected, data, nullptr, true); }, "invalid fixed allocation dimensions");
}

void legacy_sampler_descriptor() {
    TextureData data;
    data.width = 5; data.height = 7; data.min_filter = "linear";
    data.wrapping = {"repeat", "mirrored_repeat"};
    data.pixels.assign(140, 0x7f);
    const auto old = prepare_sampler_descriptor(data);
    const auto no_pixels = sampler_texture_descriptor(data);
    const auto now = prepare_sampler_descriptor(no_pixels);
    require(no_pixels.pixels.empty(), "float descriptor must also avoid a payload copy");
    require(old.minFilter == now.minFilter && old.magFilter == now.magFilter &&
            old.addressModeU == now.addressModeU && old.addressModeV == now.addressModeV &&
            old.lodMinClamp == now.lodMinClamp && old.lodMaxClamp == now.lodMaxClamp,
            "effective descriptor extraction must preserve legacy float sampling state");
    data.dimensions = 3; data.depth = 2;
    data.wrapping = {"clamp_to_edge", "repeat", "mirrored_repeat"};
    const auto volume = prepare_sampler_descriptor(sampler_texture_descriptor(data));
    require(volume.addressModeW == wgpu::AddressMode::ClampToEdge && volume.addressModeU == wgpu::AddressMode::Repeat &&
            volume.addressModeV == wgpu::AddressMode::MirrorRepeat, "legacy 3D R/S/T ordering must stay unchanged");
}
}  // namespace

int main() {
    try {
        wrap_and_scalar_domain();
        fixed_allocation_and_retained_values();
        admission_refusals();
        legacy_sampler_descriptor();
        std::cout << "PASS retained integer sampler policy: " << checks << " checks; CPU metadata only\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
