#pragma once

#include "runtime_line.hpp"

#include <bit>
#include <charconv>
#include <cstdint>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>

namespace vispy::lines {

// Ordered compute input fields, after name/type remapping against the captured
// original shader. Constants use their immutable raw-word allocation identity
// and revision with stride zero; values must not be converted through float.
// Identities are monotonic allocation IDs, never recyclable pointer addresses.
struct EndpointInputStamp {
    std::string name, type;
    uint64_t identity = 0, revision = 0, offset = 0, stride = 0, divisor = 0;
    uint32_t components = 0;
};

// Internal native constant ABI only. The caller supplies the actual numeric
// carrier rather than silently treating an integer GLSL input as float bits.
// This does not add integer constant support to public upstream GLIR setters.
inline uint32_t endpoint_constant_word(std::string_view type, bool integer_value,
        int64_t integer, double floating) {
    if (type == "float" || type == "vec2" || type == "vec3" || type == "vec4") {
        const float value = integer_value ? static_cast<float>(integer) : static_cast<float>(floating);
        return std::bit_cast<uint32_t>(value);
    }
    const bool signed_type = type == "int" || type == "ivec2" || type == "ivec3" || type == "ivec4";
    const bool unsigned_type = type == "uint" || type == "uvec2" || type == "uvec3" || type == "uvec4";
    if (!signed_type && !unsigned_type)
        throw std::invalid_argument("lines: unsupported endpoint constant type " + std::string(type));
    if (!integer_value)
        throw std::invalid_argument("lines: endpoint integer constant " + std::string(type) + " requires an integer carrier");
    if (signed_type) {
        if (integer < INT32_MIN || integer > INT32_MAX)
            throw std::out_of_range("lines: endpoint signed constant exceeds int32 range");
        return std::bit_cast<uint32_t>(static_cast<int32_t>(integer));
    }
    if (integer < 0 || static_cast<uint64_t>(integer) > UINT32_MAX)
        throw std::out_of_range("lines: endpoint unsigned constant exceeds uint32 range");
    return static_cast<uint32_t>(integer);
}

namespace endpoint_key_detail {
inline void append(std::string& key, std::string_view value) {
    if (value.size() > key.max_size() - key.size())
        throw std::length_error("lines: endpoint input identity exceeds string capacity");
    if (!value.empty()) key.append(value.data(), value.size());
}

inline void number(std::string& key, uint64_t value) {
    char digits[20];  // UINT64_MAX has twenty decimal digits.
    const auto result = std::to_chars(digits, digits + sizeof(digits), value);
    if (result.ec != std::errc{})
        throw std::overflow_error("lines: endpoint input identity integer encoding failed");
    append(key, {digits, static_cast<size_t>(result.ptr - digits)});
    append(key, ":");
}

inline void framed(std::string& key, std::string_view value) {
    static_assert(sizeof(size_t) <= sizeof(uint64_t));
    number(key, static_cast<uint64_t>(value.size()));
    append(key, value);
    append(key, ":");
}
} // namespace endpoint_key_detail

// Exact, length-framed identity rather than a short digest. The evaluator's
// complete identity includes its input ABI/compiler policy. Primitive and
// original selection are retained even where the same packed bytes result.
// Field order is significant because it determines the evaluator row layout.
// Uniforms/textures are deliberately absent: they require fresh evaluation,
// while unchanged endpoint geometry can reuse its immutable packed input.
// This key owns no source revisions. Use CurrentCategory::LineEndpoint in the
// existing shared current/history/oversized caches, not a separate side cache.
inline std::string endpoint_input_key(std::string_view evaluator_identity,
        Mode primitive, uint64_t first, uint64_t count, uint64_t instances,
        uint64_t index_identity, uint64_t index_revision, uint32_t index_bytes,
        std::span<const EndpointInputStamp> fields) {
    uint64_t primitive_id;
    switch (primitive) {
        case Mode::List: primitive_id = 0; break;
        case Mode::Strip: primitive_id = 1; break;
        case Mode::Loop: primitive_id = 2; break;
        default: throw std::invalid_argument("lines: endpoint input identity has invalid primitive mode");
    }
    if (index_bytes != 0 && index_bytes != 1 && index_bytes != 2 && index_bytes != 4)
        throw std::invalid_argument("lines: endpoint input identity index width must be zero, one, two or four bytes");

    std::string key = "line-endpoint:v1:";
    endpoint_key_detail::framed(key, evaluator_identity);
    for (uint64_t value : {primitive_id, first, count, instances, index_identity,
                          index_revision, uint64_t(index_bytes), uint64_t(fields.size())})
        endpoint_key_detail::number(key, value);
    for (const auto& field : fields) {
        endpoint_key_detail::framed(key, field.name);
        endpoint_key_detail::framed(key, field.type);
        for (uint64_t value : {field.identity, field.revision, field.offset, field.stride,
                              field.divisor, uint64_t(field.components)})
            endpoint_key_detail::number(key, value);
    }
    return key;
}

} // namespace vispy::lines
