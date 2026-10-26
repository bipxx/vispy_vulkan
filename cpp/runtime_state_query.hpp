// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "runtime_state.hpp"
#include <type_traits>

namespace render_state_query {
inline Value integer(int64_t number) {
    Value out; out.kind = Value::Kind::Int; out.i = number; return out;
}
inline Value floating(double number) {
    // Pinned VisPy glGetParameter uses GLfloat for these selectors.
    Value out; out.kind = Value::Kind::Float; out.f = static_cast<float>(number); return out;
}
inline Value mask(uint32_t bits) {
    // GL 4.6 section 2.2.2: bitmask queries preserve the signed 32-bit pattern.
    return integer(bits <= 0x7fffffffu ? int64_t(bits) : int64_t(bits) - 0x100000000ll);
}
inline Value enumeration(const std::string& name) {
    if (name == "zero") return integer(0x0);
    if (name == "one") return integer(0x1);
    if (name == "never") return integer(0x200);
    if (name == "less") return integer(0x201);
    if (name == "equal") return integer(0x202);
    if (name == "lequal") return integer(0x203);
    if (name == "greater") return integer(0x204);
    if (name == "notequal") return integer(0x205);
    if (name == "gequal") return integer(0x206);
    if (name == "always") return integer(0x207);
    if (name == "src_color") return integer(0x300);
    if (name == "one_minus_src_color") return integer(0x301);
    if (name == "src_alpha") return integer(0x302);
    if (name == "one_minus_src_alpha") return integer(0x303);
    if (name == "dst_alpha") return integer(0x304);
    if (name == "one_minus_dst_alpha") return integer(0x305);
    if (name == "dst_color") return integer(0x306);
    if (name == "one_minus_dst_color") return integer(0x307);
    if (name == "src_alpha_saturate") return integer(0x308);
    if (name == "front") return integer(0x404);
    if (name == "back") return integer(0x405);
    if (name == "front_and_back") return integer(0x408);
    if (name == "cw") return integer(0x900);
    if (name == "ccw") return integer(0x901);
    if (name == "keep") return integer(0x1e00);
    if (name == "replace") return integer(0x1e01);
    if (name == "incr") return integer(0x1e02);
    if (name == "decr") return integer(0x1e03);
    if (name == "invert") return integer(0x150a);
    if (name == "incr_wrap") return integer(0x8507);
    if (name == "decr_wrap") return integer(0x8508);
    if (name == "constant_color") return integer(0x8001);
    if (name == "one_minus_constant_color") return integer(0x8002);
    if (name == "constant_alpha") return integer(0x8003);
    if (name == "one_minus_constant_alpha") return integer(0x8004);
    if (name == "func_add") return integer(0x8006);
    if (name == "min") return integer(0x8007);
    if (name == "max") return integer(0x8008);
    if (name == "func_subtract") return integer(0x800a);
    if (name == "func_reverse_subtract") return integer(0x800b);
    throw std::runtime_error("state query: unknown committed enum " + name);
}
template <typename T, size_t N> inline Value vector(const std::array<T, N>& values) {
    Value out; out.kind = Value::Kind::List;
    for (const auto value : values) {
        if constexpr (std::is_floating_point_v<T>) out.list.push_back(floating(value));
        else out.list.push_back(integer(value));
    }
    return out;
}
inline std::array<int, 4> rectangle(std::array<int, 4> value, int width, int height) {
    if (value[2] < 0) value[2] = width;
    if (value[3] < 0) value[3] = height;
    return value;
}
inline Value parameter(const RenderState& s, int pname, int width, int height) {
    switch (pname) {
        case 0xb20: return integer(s.line_smooth);
        case 0xb21: return floating(s.line_width);
        case 0xb44: return integer(s.cull_enabled);
        case 0xb45: return enumeration(s.cull_face);
        case 0xb46: return enumeration(s.front_face);
        case 0xb71: return integer(s.depth_test);
        case 0xb72: return integer(s.depth_mask);
        case 0xb73: return floating(s.clear_depth);
        case 0xb74: return enumeration(s.depth_func);
        case 0xb90: return integer(s.stencil_test);
        case 0xb91: return mask(s.clear_stencil);
        case 0xb92: return enumeration(s.stencil_front.compare);
        case 0xb93: return mask(s.stencil_front.read_mask);
        case 0xb94: return enumeration(s.stencil_front.fail);
        case 0xb95: return enumeration(s.stencil_front.depth_fail);
        case 0xb96: return enumeration(s.stencil_front.pass);
        case 0xb97: return integer(s.stencil_front.reference);
        case 0xb98: return mask(s.stencil_front.write_mask);
        case 0xbe2: return integer(s.blend_enabled);
        case 0xc11: return integer(s.scissor_enabled);
        case 0x2a00: return floating(s.polygon_offset_units);
        case 0x8009: return enumeration(s.blend_equation_rgb);
        case 0x8037: return integer(s.polygon_offset_fill);
        case 0x8038: return floating(s.polygon_offset_factor);
        case 0x809d: return integer(s.multisample);
        case 0x809e: return integer(s.sample_alpha_to_coverage);
        case 0x80a0: return integer(s.sample_coverage_enabled);
        case 0x80aa: return floating(s.sample_coverage);
        case 0x80ab: return integer(s.sample_coverage_invert);
        case 0x80c8: return enumeration(s.blend_dst_rgb);
        case 0x80c9: return enumeration(s.blend_src_rgb);
        case 0x80ca: return enumeration(s.blend_dst_alpha);
        case 0x80cb: return enumeration(s.blend_src_alpha);
        case 0x8800: return enumeration(s.stencil_back.compare);
        case 0x8801: return enumeration(s.stencil_back.fail);
        case 0x8802: return enumeration(s.stencil_back.depth_fail);
        case 0x8803: return enumeration(s.stencil_back.pass);
        case 0x883d: return enumeration(s.blend_equation_alpha);
        case 0x8ca3: return integer(s.stencil_back.reference);
        case 0x8ca4: return mask(s.stencil_back.read_mask);
        case 0x8ca5: return mask(s.stencil_back.write_mask);
        case 0x8005: return vector(s.blend_color);
        case 0xb70: return vector(s.depth_range);
        case 0xc22: return vector(s.clear_color);
        case 0xc23: return vector(s.color_mask);
        case 0xc10: return vector(rectangle(s.scissor, width, height));
        case 0xba2: return vector(rectangle(s.viewport, width, height));
        default: throw std::runtime_error("state query: unsupported selector " + std::to_string(pname));
    }
}
}  // namespace render_state_query
