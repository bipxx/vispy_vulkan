#pragma once
// SPDX-License-Identifier: AGPL-3.0-only
#include "runtime_texture.hpp"
#include "runtime_byte_recycler.hpp"
#include <algorithm>
namespace vispy::textures {
// *copied reports whether a patch first copied a host block shadow that something else still holds (plan P5).
inline bool apply_owned_texture_data(TextureData& data, ByteBlob& upload, const std::vector<int>& offset, bool allow_transfer,
                               const TextureData* allocation = nullptr, bool* copied = nullptr) {
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
    if (upload.size() != multiply(upload_texels, upload_pixel_bytes)) throw error("DATA byte size differs from declared shape/dtype");
    if (entire && allow_transfer) {
        auto dtype=upload.dtype;
        // The replaced shadow's storage serves the next payload snapshot (runtime_byte_recycler.hpp); a replaced
        // host block returns to its pool once nothing else holds it (plan P5).
        vispy::memory::ByteRecycler::shared().give(std::move(data.pixels));
        data.pixels=std::move(upload.bytes);
        data.host=std::move(upload.host);
        data.dtype=std::move(dtype);
        return true;
    }
    // Partial/mixed-dtype behavior remains the exact canonical const helper.
    const bool copied_block = apply_texture_data(data,upload,offset,allocation);
    if (copied) *copied = copied_block;
    return false;
}
} // namespace vispy::textures
