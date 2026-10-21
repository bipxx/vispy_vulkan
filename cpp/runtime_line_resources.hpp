#pragma once

#include "shader/line_evaluator.hpp"
#include "shader/line_consumer.hpp"

#include <algorithm>
#include <cstring>
#include <span>
#include <stdexcept>
#include <vector>

namespace vispy::lines {

// Resolve compute-only resources against the immutable original draw, never
// against the Program's later state or another shader's positional bindings.
inline std::vector<size_t> endpoint_attribute_order(
    const std::vector<NormAttribute>& original,
    const std::vector<shader::LineInputField>& requested) {
    std::vector<size_t> order;
    for (const auto& field : requested) {
        const auto found = std::find_if(original.begin(), original.end(), [&](const auto& value) {
            return value.name == field.attribute.name;
        });
        if (found == original.end() || found->type != field.attribute.type)
            throw std::runtime_error("lines: captured attribute " + field.attribute.name + ": missing or incompatible type");
        if (std::find_if(found + 1, original.end(), [&](const auto& value) {
                return value.name == field.attribute.name;
            }) != original.end())
            throw std::runtime_error("lines: captured attribute " + field.attribute.name + ": duplicate reflected name");
        order.push_back(static_cast<size_t>(found - original.begin()));
    }
    return order;
}

inline std::vector<size_t> endpoint_sampler_order(
    const std::vector<NormSampler>& original,
    const std::vector<NormSampler>& requested) {
    std::vector<size_t> order;
    for (const auto& field : requested) {
        const auto found = std::find_if(original.begin(), original.end(), [&](const auto& value) {
            return value.name == field.name;
        });
        if (found == original.end() || found->dim != field.dim)
            throw std::runtime_error("lines: captured sampler " + field.name + ": missing or incompatible dimension");
        if (found->sample_scalar != field.sample_scalar)
            throw std::runtime_error("lines: captured sampler " + field.name + ": incompatible sampled scalar");
        if (std::find_if(found + 1, original.end(), [&](const auto& value) {
                return value.name == field.name;
            }) != original.end())
            throw std::runtime_error("lines: captured sampler " + field.name + ": duplicate reflected name");
        order.push_back(static_cast<size_t>(found - original.begin()));
    }
    return order;
}

namespace endpoint_resources_detail {
inline uint64_t elements(const NormUniform& uniform) {
    return uniform.array_size > 0 ? static_cast<uint64_t>(uniform.array_size) : 1;
}

inline uint64_t component_offset(const NormUniform& uniform, uint64_t element, uint64_t component) {
    uint64_t offset = element * (elements(uniform) > 1 ? uniform.array_stride : uniform.size);
    if (uniform.matrix_stride) {
        const uint64_t column = component / uniform.matrix_rows;
        const uint64_t row = component % uniform.matrix_rows;
        offset += uniform.row_major ? row * uniform.matrix_stride + column * 4
                                    : column * uniform.matrix_stride + row * 4;
    } else offset += component * 4;
    return offset;
}

inline void validate(const NormUniform& uniform, uint64_t buffer_bytes) {
    auto fail = [&](const char* reason) {
        throw std::runtime_error("lines: captured uniform " + uniform.name + ": " + reason);
    };
    ShaderValueType type;
    if (!shader_value_type(uniform.type, type) || uniform.array_size < 0 ||
        uniform.component_count != type.components() ||
        uniform.matrix_columns != type.columns || uniform.matrix_rows != (type.columns > 1 ? type.rows : 1))
        fail("inconsistent reflected type");
    if (uniform.offset > buffer_bytes || uniform.size > buffer_bytes - uniform.offset)
        fail("reflected member exceeds buffer");
    if (elements(uniform) * uint64_t(uniform.component_count) * 4 > uniform.size)
        fail("reflected member cannot contain logical components");
    if ((type.columns > 1 && !uniform.matrix_stride) || (type.columns == 1 && uniform.matrix_stride) ||
        (uniform.array_size > 0 && !uniform.array_stride))
        fail("missing or incompatible reflected stride");
    if (uniform.offset % 4 || uniform.size % 4 || uniform.matrix_stride % 4 || uniform.array_stride % 4)
        fail("unaligned reflected component storage");
    uint64_t element_extent = uint64_t(uniform.component_count) * 4;
    if (uniform.matrix_stride) {
        const uint64_t vectors = uniform.row_major ? uniform.matrix_rows : uniform.matrix_columns;
        const uint64_t vector_bytes = uint64_t(uniform.row_major ? uniform.matrix_columns : uniform.matrix_rows) * 4;
        if (uniform.matrix_stride < vector_bytes)
            fail("matrix stride aliases logical components");
        element_extent = (vectors - 1) * uniform.matrix_stride + vector_bytes;
    }
    if (uniform.array_size > 0 && uniform.array_stride < element_extent)
        fail("array stride aliases logical elements");
    for (uint64_t element = 0; element < elements(uniform); ++element) {
        for (uint64_t component = 0; component < uniform.component_count; ++component) {
            const uint64_t offset = component_offset(uniform, element, component);
            if (offset > uniform.size || 4 > uniform.size - offset)
                fail("component exceeds reflected member");
        }
    }
}
}  // namespace endpoint_resources_detail

inline std::vector<uint8_t> repack_endpoint_uniforms(
    const std::vector<NormUniform>& original, std::span<const uint8_t> captured,
    const std::vector<NormUniform>& requested, uint32_t destination_bytes,
    uint64_t granted_uniform_bytes) {
    using namespace endpoint_resources_detail;
    if (destination_bytes > granted_uniform_bytes)
        throw std::length_error("lines: evaluator uniform buffer exceeds granted binding size");
    std::vector<size_t> order;
    for (const auto& field : requested) {
        const auto found = std::find_if(original.begin(), original.end(), [&](const auto& value) {
            return value.name == field.name;
        });
        if (found == original.end() || found->type != field.type || found->array_size != field.array_size)
            throw std::runtime_error("lines: captured uniform " + field.name + ": missing or incompatible type/array");
        if (std::find_if(found + 1, original.end(), [&](const auto& value) {
                return value.name == field.name;
            }) != original.end())
            throw std::runtime_error("lines: captured uniform " + field.name + ": duplicate reflected name");
        validate(*found, captured.size());
        validate(field, destination_bytes);
        for (size_t prior = 0; prior < order.size(); ++prior) {
            const auto& previous = requested[prior];
            if (previous.name == field.name)
                throw std::runtime_error("lines: captured uniform " + field.name + ": duplicate requested name");
            auto overlaps = [](const NormUniform& left, const NormUniform& right) {
                return uint64_t(left.offset) < uint64_t(right.offset) + right.size &&
                       uint64_t(right.offset) < uint64_t(left.offset) + left.size;
            };
            if (overlaps(previous, field) || overlaps(original[order[prior]], *found))
                throw std::runtime_error("lines: captured uniform " + field.name + ": overlapping reflected members");
        }
        order.push_back(static_cast<size_t>(found - original.begin()));
    }
    // Validate all resource layouts before publishing or allocating the UBO.
    std::vector<uint8_t> output(destination_bytes, 0);
    for (size_t field_index = 0; field_index < requested.size(); ++field_index) {
        const auto& source = original[order[field_index]];
        const auto& target = requested[field_index];
        std::vector<uint8_t> logical(static_cast<size_t>(elements(source) * source.component_count * 4));
        for (uint64_t element = 0; element < elements(source); ++element) {
            for (uint64_t component = 0; component < source.component_count; ++component) {
                const uint64_t from = source.offset + component_offset(source, element, component);
                const uint64_t to = (element * source.component_count + component) * 4;
                std::memcpy(logical.data() + to, captured.data() + from, 4);
            }
        }
        std::string error;
        if (!pack_uniform_value(target, logical.data(), logical.size(), output.data(), output.size(), &error))
            throw std::runtime_error("lines: evaluator " + error);
    }
    return output;
}

// Pack the generated render ABI from the immutable original DRAW uniform
// snapshot. The evaluator and render wrappers can reflect different member
// offsets, so only logical original values are copied before overlaying ABI2.
inline std::vector<uint8_t> pack_generated_line_consumer_uniforms(
    const shader::GeneratedLineConsumerArtifact& consumer,
    std::span<const uint8_t> captured,
    const shader::GeneratedLineConsumerDraw& draw,
    uint64_t granted_uniform_bytes) {
    constexpr uint64_t parameter_bytes = sizeof(shader::GeneratedLineConsumerParameters);
    if (!consumer.ok || !consumer.original || !consumer.evaluator ||
            consumer.evaluator->original != consumer.original)
        throw std::invalid_argument("lines: consumer has a different original/evaluator snapshot");
    const auto& original = *consumer.original;
    if (captured.size() != original.uniform_bytes ||
            consumer.parameters_offset != original.uniform_bytes || consumer.parameters_offset % 16 ||
            uint64_t(consumer.parameters_offset) + parameter_bytes != consumer.uniform_bytes ||
            draw.render_uniform_bytes != consumer.uniform_bytes ||
            draw.parameters.header[0] != shader::kGeneratedLineConsumerAbi ||
            consumer.uniform_stage_mask != 3)
        throw std::invalid_argument("lines: generated paired uniform ABI differs");
    if (consumer.uniforms.size() != original.uniforms.size() + 4)
        throw std::invalid_argument("lines: generated uniform member count differs");
    static constexpr std::array<const char*, 4> names{
        "vispy_line_consumer_header", "vispy_line_consumer_ranges",
        "vispy_line_consumer_viewport", "vispy_line_consumer_raster"};
    for (size_t index = 0; index < names.size(); ++index) {
        const auto& field = consumer.uniforms[original.uniforms.size() + index];
        if (field.name != names[index] || field.type != (index < 2 ? "uvec4" : "vec4") ||
                field.offset != uint64_t(consumer.parameters_offset) + index * 16 ||
                field.size != 16 || field.array_size || field.array_stride || field.matrix_stride ||
                field.component_count != 4)
            throw std::invalid_argument("lines: reflected generated parameter member differs");
        endpoint_resources_detail::validate(field, consumer.uniform_bytes);
    }
    std::vector<NormUniform> requested(consumer.uniforms.begin(),
                                    consumer.uniforms.begin() + original.uniforms.size());
    for (const auto& field : requested)
        endpoint_resources_detail::validate(field, consumer.parameters_offset);
    auto output = repack_endpoint_uniforms(original.uniforms, captured, requested,
                                          consumer.uniform_bytes, granted_uniform_bytes);
    std::memcpy(output.data() + consumer.parameters_offset, &draw.parameters, parameter_bytes);
    return output;
}

}  // namespace vispy::lines
