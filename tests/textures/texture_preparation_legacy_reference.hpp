// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "runtime_texture.hpp"

// Frozen pre-optimization oracle. Keep independent of the product helper.
inline PreparedTexture legacy_prepare_texture(const TextureData& data, const TextureData* allocation = nullptr) {
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
    const bool direct_f32 = data.dtype == "f32" && description.storage == Storage::Float32;
    const bool direct_u8 = data.dtype == "u8" && description.storage == Storage::Unorm8;
    const bool direct_integer = description.integer && data.dtype ==
        std::string(description.signed_integer ? "i" : "u") + std::to_string(description.component_bytes * 8);
    if (description.channels == data.channels && (direct_f32 || direct_u8 || direct_integer)) {
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

