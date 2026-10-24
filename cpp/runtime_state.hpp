#pragma once

#include "runtime.hpp"
#include <webgpu/webgpu_cpp.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

struct StencilState {
    std::string compare = "always";
    uint32_t reference = 0;
    uint32_t read_mask = 0xffffffffu;
    uint32_t write_mask = 0xffffffffu;
    std::string fail = "keep";
    std::string depth_fail = "keep";
    std::string pass = "keep";
};

// Defaults are OpenGL context defaults, not a VisPy state preset. Every draw
// snapshots these values; viewport/scissor/constants/reference stay dynamic.
struct RenderState {
    bool blend_enabled = false;
    std::string blend_src_rgb = "one", blend_dst_rgb = "zero";
    std::string blend_src_alpha = "one", blend_dst_alpha = "zero";
    std::string blend_equation_rgb = "func_add", blend_equation_alpha = "func_add";
    std::array<double, 4> blend_color = {0, 0, 0, 0};
    bool depth_test = false;
    bool depth_mask = true;
    std::string depth_func = "less";
    std::array<float, 2> depth_range = {0, 1};
    bool stencil_test = false;
    StencilState stencil_front, stencil_back;
    bool cull_enabled = false;
    std::string cull_face = "back";
    std::string front_face = "ccw";
    std::array<bool, 4> color_mask = {true, true, true, true};
    bool polygon_offset_fill = false;
    float polygon_offset_factor = 0, polygon_offset_units = 0;
    bool multisample = true;
    bool sample_alpha_to_coverage = false;
    bool sample_coverage_enabled = false;
    float sample_coverage = 1;
    bool sample_coverage_invert = false;
    uint32_t sample_count = 1;
    float line_width = 1;
    bool line_smooth = false;
    std::array<int, 4> viewport = {0, 0, -1, -1};
    std::array<int, 4> scissor = {0, 0, -1, -1};
    bool scissor_enabled = false;
    std::array<double, 4> clear_color = {0, 0, 0, 0};
    double clear_depth = 1;
    uint32_t clear_stencil = 0;
};

// Capture the original GLIR primitive before point/line/fan lowering.
// Expanded point or line triangles are never polygon culling candidates.
enum class LogicalDrawTopology { NonPolygon, Polygon };

inline LogicalDrawTopology logical_draw_topology(const std::string& mode) {
    return mode == "triangles" || mode == "triangle_strip" || mode == "triangle_fan" ?
        LogicalDrawTopology::Polygon : LogicalDrawTopology::NonPolygon;
}

// WebGPU has no CullMode::FrontAndBack. Keep the real draw and its vertex
// execution, but give original polygon draws an empty raster rectangle.
// Clear operations are not user draws, including shader-backed masked clears.
inline std::array<uint32_t, 4> effective_draw_scissor(const RenderState& state,
        LogicalDrawTopology topology, bool user_draw, bool scissor_enabled,
        const std::array<int, 4>& scissor, int width, int height) {
    if (width < 0 || height < 0)
        throw std::invalid_argument("DRAW scissor: negative target dimensions");
    if (user_draw && topology == LogicalDrawTopology::Polygon &&
            state.cull_enabled && state.cull_face == "front_and_back") return {0, 0, 0, 0};
    if (!scissor_enabled) return {0, 0, static_cast<uint32_t>(width), static_cast<uint32_t>(height)};
    const int x = std::clamp(scissor[0], 0, width);
    const int y = std::clamp(scissor[1], 0, height);
    return {static_cast<uint32_t>(x), static_cast<uint32_t>(y),
        static_cast<uint32_t>(std::clamp(scissor[2] < 0 ? width : scissor[2], 0, width - x)),
        static_cast<uint32_t>(std::clamp(scissor[3] < 0 ? height : scissor[3], 0, height - y))};
}

// Selected face projection is explicit; the shared-mask descriptor refusal
// below remains the guard for every path that did not perform this conversion.
enum class StencilFaceRoute { Unchanged, FrontOnly, BackOnly, OrderedTwoFaces };
inline StencilFaceRoute stencil_face_route(const RenderState& s, LogicalDrawTopology topology, bool user_draw) {
    if (!user_draw || !s.stencil_test || (s.stencil_front.reference == s.stencil_back.reference &&
        s.stencil_front.read_mask == s.stencil_back.read_mask && s.stencil_front.write_mask == s.stencil_back.write_mask))
        return StencilFaceRoute::Unchanged;
    if (topology == LogicalDrawTopology::NonPolygon || (s.cull_enabled && s.cull_face == "front_and_back"))
        return StencilFaceRoute::FrontOnly;
    if (s.cull_enabled && s.cull_face == "back") return StencilFaceRoute::FrontOnly;
    if (s.cull_enabled && s.cull_face == "front") return StencilFaceRoute::BackOnly;
    return StencilFaceRoute::OrderedTwoFaces;
}
inline RenderState stencil_face_state(const RenderState& captured, StencilFaceRoute route, uint32_t face = 0) {
    if (face > 1 || (face && route != StencilFaceRoute::OrderedTwoFaces))
        throw std::runtime_error("DRAW stencil faces: invalid selected face");
    auto state = captured;
    if (route == StencilFaceRoute::Unchanged) return state;
    const auto& selected = route == StencilFaceRoute::BackOnly ||
        (route == StencilFaceRoute::OrderedTwoFaces && face) ? captured.stencil_back : captured.stencil_front;
    for (auto* dst : {&state.stencil_front, &state.stencil_back}) {
        dst->reference = selected.reference; dst->read_mask = selected.read_mask; dst->write_mask = selected.write_mask;
    }
    if (route == StencilFaceRoute::OrderedTwoFaces) {
        state.cull_enabled = true; state.cull_face = face ? "front" : "back";
    }
    return state;
}

namespace render_state_detail {
inline std::runtime_error error(const std::string& operation, const std::string& message) {
    return std::runtime_error("FUNC " + operation + ": " + message);
}

inline double number(const Value& value, const std::string& operation) {
    double result;
    if (value.kind == Value::Kind::Float) result = value.f;
    else if (value.kind == Value::Kind::Int) result = static_cast<double>(value.i);
    else if (value.kind == Value::Kind::Bool) result = value.b ? 1 : 0;
    else throw error(operation, "expected numeric argument");
    if (!std::isfinite(result)) throw error(operation, "argument must be finite");
    return result;
}
inline int integer(const Value& value, const std::string& operation) {
    const double result = number(value, operation);
    if (std::trunc(result) != result || result < std::numeric_limits<int>::min() || result > std::numeric_limits<int>::max())
        throw error(operation, "expected representable integer argument");
    return static_cast<int>(result);
}
inline float finite_float(const Value& value, const std::string& operation) {
    const double result = number(value, operation);
    const double maximum = std::numeric_limits<float>::max();
    if (result < -maximum || result > maximum)
        throw error(operation, "argument must fit the finite native float range");
    return static_cast<float>(result);
}
inline uint32_t mask(const Value& value, const std::string& operation) {
    if (value.kind != Value::Kind::Int || value.i < std::numeric_limits<int32_t>::min() || value.i > std::numeric_limits<uint32_t>::max())
        throw error(operation, "expected 32-bit mask");
    return static_cast<uint32_t>(value.i);
}
inline std::string text(const Value& value, const std::string& operation) {
    // The public wrappers also admit GL enum objects, which serialize as
    // integers. Keep their established meanings alongside string names.
    if (value.kind == Value::Kind::Int) {
        switch (value.i) {
            case 0: return "zero"; case 1: return "one";
            case 0x0200: return "never"; case 0x0201: return "less";
            case 0x0202: return "equal"; case 0x0203: return "lequal";
            case 0x0204: return "greater"; case 0x0205: return "notequal";
            case 0x0206: return "gequal"; case 0x0207: return "always";
            case 0x0300: return "src_color"; case 0x0301: return "one_minus_src_color";
            case 0x0302: return "src_alpha"; case 0x0303: return "one_minus_src_alpha";
            case 0x0304: return "dst_alpha"; case 0x0305: return "one_minus_dst_alpha";
            case 0x0306: return "dst_color"; case 0x0307: return "one_minus_dst_color";
            case 0x0308: return "src_alpha_saturate";
            case 0x0404: return "front"; case 0x0405: return "back"; case 0x0408: return "front_and_back";
            case 0x0900: return "cw"; case 0x0901: return "ccw";
            case 0x1e00: return "keep"; case 0x1e01: return "replace";
            case 0x1e02: return "incr"; case 0x1e03: return "decr";
            case 0x150a: return "invert"; case 0x8507: return "incr_wrap"; case 0x8508: return "decr_wrap";
            case 0x8001: return "constant_color"; case 0x8002: return "one_minus_constant_color";
            case 0x8003: return "constant_alpha"; case 0x8004: return "one_minus_constant_alpha";
            case 0x8006: return "func_add"; case 0x8007: return "min"; case 0x8008: return "max";
            case 0x800a: return "func_subtract"; case 0x800b: return "func_reverse_subtract";
        }
    }
    if (value.kind != Value::Kind::Str) throw error(operation, "expected enum name");
    return value.s;
}
inline wgpu::CompareFunction compare(const std::string& name) {
    if (name == "never") return wgpu::CompareFunction::Never;
    if (name == "less") return wgpu::CompareFunction::Less;
    if (name == "equal") return wgpu::CompareFunction::Equal;
    if (name == "lequal") return wgpu::CompareFunction::LessEqual;
    if (name == "greater") return wgpu::CompareFunction::Greater;
    if (name == "notequal") return wgpu::CompareFunction::NotEqual;
    if (name == "gequal") return wgpu::CompareFunction::GreaterEqual;
    if (name == "always") return wgpu::CompareFunction::Always;
    throw error("compare", "unsupported comparison " + name);
}
inline wgpu::StencilOperation stencil(const std::string& name) {
    if (name == "keep") return wgpu::StencilOperation::Keep;
    if (name == "zero") return wgpu::StencilOperation::Zero;
    if (name == "replace") return wgpu::StencilOperation::Replace;
    if (name == "incr") return wgpu::StencilOperation::IncrementClamp;
    if (name == "decr") return wgpu::StencilOperation::DecrementClamp;
    if (name == "incr_wrap") return wgpu::StencilOperation::IncrementWrap;
    if (name == "decr_wrap") return wgpu::StencilOperation::DecrementWrap;
    if (name == "invert") return wgpu::StencilOperation::Invert;
    throw error("stencil", "unsupported stencil operation " + name);
}
inline wgpu::BlendFactor factor(const std::string& name, bool alpha) {
    if (name == "zero") return wgpu::BlendFactor::Zero;
    if (name == "one") return wgpu::BlendFactor::One;
    if (name == "src_color") return wgpu::BlendFactor::Src;
    if (name == "one_minus_src_color") return wgpu::BlendFactor::OneMinusSrc;
    if (name == "dst_color") return wgpu::BlendFactor::Dst;
    if (name == "one_minus_dst_color") return wgpu::BlendFactor::OneMinusDst;
    if (name == "src_alpha") return wgpu::BlendFactor::SrcAlpha;
    if (name == "one_minus_src_alpha") return wgpu::BlendFactor::OneMinusSrcAlpha;
    if (name == "dst_alpha") return wgpu::BlendFactor::DstAlpha;
    if (name == "one_minus_dst_alpha") return wgpu::BlendFactor::OneMinusDstAlpha;
    if (name == "src_alpha_saturate") return alpha ? wgpu::BlendFactor::One : wgpu::BlendFactor::SrcAlphaSaturated;
    if (name == "constant_color" || name == "constant_alpha") return wgpu::BlendFactor::Constant;
    if (name == "one_minus_constant_color" || name == "one_minus_constant_alpha") return wgpu::BlendFactor::OneMinusConstant;
    throw error("blend", "unsupported blend factor " + name);
}
inline wgpu::BlendOperation equation(const std::string& name) {
    if (name == "func_add") return wgpu::BlendOperation::Add;
    if (name == "func_subtract") return wgpu::BlendOperation::Subtract;
    if (name == "func_reverse_subtract") return wgpu::BlendOperation::ReverseSubtract;
    if (name == "min") return wgpu::BlendOperation::Min;
    if (name == "max") return wgpu::BlendOperation::Max;
    throw error("blend", "unsupported blend equation " + name);
}
inline void face(const std::string& name, RenderState& state, auto&& apply) {
    if (name == "front" || name == "front_and_back") apply(state.stencil_front);
    if (name == "back" || name == "front_and_back") apply(state.stencil_back);
    if (name != "front" && name != "back" && name != "front_and_back") throw error("stencil", "unsupported face " + name);
}
inline std::string capability(const Value& value, const std::string& operation) {
    if (value.kind == Value::Kind::Str) return value.s;
    if (value.kind == Value::Kind::Int) {
        switch (value.i) {
            case 0x0be2: return "blend";
            case 0x0b71: return "depth_test";
            case 0x0b90: return "stencil_test";
            case 0x0b44: return "cull_face";
            case 0x0c11: return "scissor_test";
            case 0x8037: return "polygon_offset_fill";
            case 0x809d: return "multisample";
            case 0x809e: return "sample_alpha_to_coverage";
            case 0x80a0: return "sample_coverage";
            case 0x0b20: return "line_smooth";
            case 0x0bd0: return "dither";
        }
    }
    throw error(operation, "unsupported capability " + (value.kind == Value::Kind::Int ? std::to_string(value.i) : "argument"));
}
}  // namespace render_state_detail

inline bool parse_render_state(const Command& command, RenderState& state) {
    using namespace render_state_detail;
    if (command.op != "FUNC") return false;
    if (command.args.empty()) throw error("<missing>", "missing function name");
    const std::string op = text(command.args[0], "<name>");
    if (op == "glFinish" || op == "glFlush" || op == "glClear") return false;
    auto count = [&](size_t size) { if (command.args.size() != size + 1) throw error(op, "wrong argument count"); };
    auto numeric = [&](size_t n) { return number(command.args[n + 1], op); };
    auto name = [&](size_t n) { return text(command.args[n + 1], op); };
    // Apply atomically, so a bad enum never partially changes the current state.
    RenderState result = state;
    if (op == "glEnable" || op == "glDisable") {
        count(1);
        const bool enabled = op == "glEnable";
        const std::string cap = capability(command.args[1], op);
        if (cap == "blend") result.blend_enabled = enabled;
        else if (cap == "depth_test") result.depth_test = enabled;
        else if (cap == "stencil_test") result.stencil_test = enabled;
        else if (cap == "cull_face") result.cull_enabled = enabled;
        else if (cap == "scissor_test") result.scissor_enabled = enabled;
        else if (cap == "polygon_offset_fill") result.polygon_offset_fill = enabled;
        else if (cap == "multisample") result.multisample = enabled;
        else if (cap == "sample_alpha_to_coverage") result.sample_alpha_to_coverage = enabled;
        else if (cap == "sample_coverage") result.sample_coverage_enabled = enabled;
        else if (cap == "line_smooth") result.line_smooth = enabled;
        else if (cap == "dither" && !enabled) { /* disabled state is represented */ }
        else throw error(op, "unsupported capability " + cap);
    } else if (op == "glViewport" || op == "glScissor") {
        count(4);
        auto& rectangle = op == "glViewport" ? result.viewport : result.scissor;
        for (size_t i = 0; i < 4; ++i) rectangle[i] = integer(command.args[i + 1], op);
        if (rectangle[2] < 0 || rectangle[3] < 0) throw error(op, "width and height must be nonnegative");
    } else if (op == "glClearColor" || op == "glBlendColor") {
        count(4);
        auto& color = op == "glClearColor" ? result.clear_color : result.blend_color;
        for (size_t i = 0; i < 4; ++i) color[i] = std::clamp(numeric(i), 0.0, 1.0);
    } else if (op == "glClearDepth" || op == "glClearDepthf") {
        count(1); result.clear_depth = std::clamp(numeric(0), 0.0, 1.0);
    } else if (op == "glClearStencil") {
        count(1); result.clear_stencil = mask(command.args[1], op);
    } else if (op == "glDepthRange" || op == "glDepthRangef") {
        count(2);
        result.depth_range = {static_cast<float>(std::clamp(numeric(0), 0.0, 1.0)), static_cast<float>(std::clamp(numeric(1), 0.0, 1.0))};

    } else if (op == "glDepthFunc") {
        count(1); result.depth_func = name(0); compare(result.depth_func);
    } else if (op == "glDepthMask") {
        count(1); result.depth_mask = numeric(0) != 0;
    } else if (op == "glColorMask") {
        count(4); for (size_t i = 0; i < 4; ++i) result.color_mask[i] = numeric(i) != 0;
    } else if (op == "glFrontFace") {
        count(1); result.front_face = name(0);
        if (result.front_face != "ccw" && result.front_face != "cw") throw error(op, "unsupported face orientation " + result.front_face);
    } else if (op == "glCullFace") {
        count(1); result.cull_face = name(0);
        if (result.cull_face != "front" && result.cull_face != "back" && result.cull_face != "front_and_back") throw error(op, "unsupported cull mode " + result.cull_face);
    } else if (op == "glLineWidth") {
        count(1); result.line_width = static_cast<float>(numeric(0));
        if (!std::isfinite(result.line_width) || result.line_width <= 0)
            throw error(op, "line width must be finite and positive");
    } else if (op == "glPolygonOffset") {
        count(2);
        result.polygon_offset_factor = finite_float(command.args[1], op);
        result.polygon_offset_units = finite_float(command.args[2], op);
    } else if (op == "glBlendFuncSeparate" || op == "glBlendFunc") {
        count(op == "glBlendFunc" ? 2 : 4);
        result.blend_src_rgb = name(0); result.blend_dst_rgb = name(1);
        result.blend_src_alpha = op == "glBlendFunc" ? result.blend_src_rgb : name(2);
        result.blend_dst_alpha = op == "glBlendFunc" ? result.blend_dst_rgb : name(3);
        factor(result.blend_src_rgb, false); factor(result.blend_dst_rgb, false);
        factor(result.blend_src_alpha, true); factor(result.blend_dst_alpha, true);
    } else if (op == "glBlendEquationSeparate" || op == "glBlendEquation") {
        count(op == "glBlendEquation" ? 1 : 2);
        result.blend_equation_rgb = name(0); result.blend_equation_alpha = op == "glBlendEquation" ? result.blend_equation_rgb : name(1);
        equation(result.blend_equation_rgb); equation(result.blend_equation_alpha);
    } else if (op == "glStencilFuncSeparate" || op == "glStencilFunc") {
        const bool separate = op == "glStencilFuncSeparate";
        count(separate ? 4 : 3);
        const size_t first = separate ? 1 : 0;
        const std::string func = name(first); compare(func);
        const uint32_t reference = static_cast<uint32_t>(std::clamp(integer(command.args[first + 2], op), 0, 255));
        const uint32_t read_mask = mask(command.args[first + 3], op);
        face(separate ? name(0) : "front_and_back", result, [&](StencilState& stencil) { stencil.compare = func; stencil.reference = reference; stencil.read_mask = read_mask; });
    } else if (op == "glStencilMaskSeparate" || op == "glStencilMask") {
        const bool separate = op == "glStencilMaskSeparate";
        count(separate ? 2 : 1);
        const uint32_t write_mask = mask(command.args[separate ? 2 : 1], op);
        face(separate ? name(0) : "front_and_back", result, [&](StencilState& stencil) { stencil.write_mask = write_mask; });
    } else if (op == "glStencilOpSeparate" || op == "glStencilOp") {
        const bool separate = op == "glStencilOpSeparate";
        count(separate ? 4 : 3);
        const size_t first = separate ? 1 : 0;
        const std::string fail = name(first), depth_fail = name(first + 1), pass = name(first + 2);
        stencil(fail); stencil(depth_fail); stencil(pass);
        face(separate ? name(0) : "front_and_back", result, [&](StencilState& stencil) { stencil.fail = fail; stencil.depth_fail = depth_fail; stencil.pass = pass; });
    } else if (op == "glSampleCoverage") {
        count(2); result.sample_coverage = static_cast<float>(std::clamp(numeric(0), 0.0, 1.0)); result.sample_coverage_invert = numeric(1) != 0;
    } else throw error(op, "unsupported render state function");
    state = std::move(result);
    return true;
}

inline wgpu::Color blend_constant_for_state(const RenderState& state) {
    auto alpha_constant = [](const std::string& factor) { return factor == "constant_alpha" || factor == "one_minus_constant_alpha"; };
    auto color_constant = [](const std::string& factor) { return factor == "constant_color" || factor == "one_minus_constant_color"; };
    const bool extrema = state.blend_equation_rgb == "min" || state.blend_equation_rgb == "max";
    const bool alpha = !extrema && (alpha_constant(state.blend_src_rgb) || alpha_constant(state.blend_dst_rgb));
    const bool color = !extrema && (color_constant(state.blend_src_rgb) || color_constant(state.blend_dst_rgb));
    if (state.blend_enabled && alpha && color) throw render_state_detail::error("blend", "mixed constant-alpha/constant-color RGB factors require independent constants");
    const auto& value = state.blend_color;
    return alpha ? wgpu::Color{value[3], value[3], value[3], value[3]} : wgpu::Color{value[0], value[1], value[2], value[3]};
}

inline void fill_pipeline_state(const RenderState& state, wgpu::RenderPipelineDescriptor& pipeline,
                                wgpu::ColorTargetState& color, wgpu::DepthStencilState& depth,
                                wgpu::BlendState& blend) {
    using namespace render_state_detail;
    blend_constant_for_state(state);
    auto component = [&](const std::string& op, const std::string& src, const std::string& dst, bool alpha) {
        wgpu::BlendComponent result;
        result.operation = equation(op);
        // GL min/max ignores blend factors; WebGPU requires both to be One.
        const bool extrema = op == "min" || op == "max";
        result.srcFactor = extrema ? wgpu::BlendFactor::One : factor(src, alpha);
        result.dstFactor = extrema ? wgpu::BlendFactor::One : factor(dst, alpha);
        return result;
    };
    blend.color = component(state.blend_equation_rgb, state.blend_src_rgb, state.blend_dst_rgb, false);
    blend.alpha = component(state.blend_equation_alpha, state.blend_src_alpha, state.blend_dst_alpha, true);
    color.blend = state.blend_enabled ? &blend : nullptr;
    color.writeMask = wgpu::ColorWriteMask::None;
    if (state.color_mask[0]) color.writeMask |= wgpu::ColorWriteMask::Red;
    if (state.color_mask[1]) color.writeMask |= wgpu::ColorWriteMask::Green;
    if (state.color_mask[2]) color.writeMask |= wgpu::ColorWriteMask::Blue;
    if (state.color_mask[3]) color.writeMask |= wgpu::ColorWriteMask::Alpha;
    pipeline.primitive.frontFace = state.front_face == "ccw" ? wgpu::FrontFace::CCW : wgpu::FrontFace::CW;
    const bool polygon_cull = pipeline.primitive.topology == wgpu::PrimitiveTopology::TriangleList ||
        pipeline.primitive.topology == wgpu::PrimitiveTopology::TriangleStrip;
    // front_and_back uses the captured logical topology's zero scissor at
    // encoding. Points/lines ignore face culling; keep their raster unchanged.
    pipeline.primitive.cullMode = !polygon_cull || !state.cull_enabled || state.cull_face == "front_and_back" ?
        wgpu::CullMode::None : state.cull_face == "front" ? wgpu::CullMode::Front : wgpu::CullMode::Back;
    if (state.sample_count != 1 && state.sample_count != 4) throw error("multisample", "only sample counts 1 and 4 are admitted");
    if (!state.multisample && state.sample_count > 1) throw error("glDisable", "disabled multisample rasterization requires a separate single-sample target");
    pipeline.multisample.count = state.sample_count;
    pipeline.multisample.alphaToCoverageEnabled = state.sample_alpha_to_coverage && state.sample_count > 1;
    pipeline.multisample.mask = 0xffffffffu;
    if (state.sample_coverage_enabled) {
        const uint32_t covered = static_cast<uint32_t>(std::round(state.sample_coverage * state.sample_count));
        uint32_t mask = covered == 32 ? 0xffffffffu : (1u << covered) - 1;
        if (state.sample_coverage_invert) mask = ~mask;
        pipeline.multisample.mask = mask;
    }
    depth.depthWriteEnabled = state.depth_test && state.depth_mask ? wgpu::OptionalBool::True : wgpu::OptionalBool::False;
    depth.depthCompare = state.depth_test ? compare(state.depth_func) : wgpu::CompareFunction::Always;
    auto stencil_face = [&](const StencilState& stencil) {
        wgpu::StencilFaceState result;
        result.compare = state.stencil_test ? compare(stencil.compare) : wgpu::CompareFunction::Always;
        result.failOp = state.stencil_test ? render_state_detail::stencil(stencil.fail) : wgpu::StencilOperation::Keep;
        result.depthFailOp = state.stencil_test ? render_state_detail::stencil(stencil.depth_fail) : wgpu::StencilOperation::Keep;
        result.passOp = state.stencil_test ? render_state_detail::stencil(stencil.pass) : wgpu::StencilOperation::Keep;
        return result;
    };
    if (state.stencil_test && (state.stencil_front.reference != state.stencil_back.reference ||
        state.stencil_front.read_mask != state.stencil_back.read_mask || state.stencil_front.write_mask != state.stencil_back.write_mask))
        throw error("stencil", "distinct front/back references or masks require a draw conversion");
    depth.stencilFront = stencil_face(state.stencil_front);
    depth.stencilBack = stencil_face(state.stencil_back);
    depth.stencilReadMask = state.stencil_test ? state.stencil_front.read_mask : 0xffffffffu;
    depth.stencilWriteMask = state.stencil_test ? state.stencil_front.write_mask : 0;
    depth.depthBias = 0; depth.depthBiasSlopeScale = 0; depth.depthBiasClamp = 0;
    const bool polygon = pipeline.primitive.topology == wgpu::PrimitiveTopology::TriangleList || pipeline.primitive.topology == wgpu::PrimitiveTopology::TriangleStrip;
    if (state.polygon_offset_fill && polygon) {
        if (std::trunc(state.polygon_offset_units) != state.polygon_offset_units ||
            static_cast<double>(state.polygon_offset_units) < std::numeric_limits<int32_t>::min() ||
            static_cast<double>(state.polygon_offset_units) > std::numeric_limits<int32_t>::max())
            throw error("glPolygonOffset", "fractional/out-of-range constant bias requires a shader conversion");
        depth.depthBias = static_cast<int32_t>(state.polygon_offset_units);
        depth.depthBiasSlopeScale = state.polygon_offset_factor;
    }
    pipeline.depthStencil = depth.format == wgpu::TextureFormat::Undefined ? nullptr : &depth;
}

inline std::string state_key(const RenderState& state) {
    std::ostringstream key;
    key << "blend=" << state.blend_enabled;
    if (state.blend_enabled) {
        auto component = [&](const std::string& operation, const std::string& src, const std::string& dst, bool alpha) {
            const bool extrema = operation == "min" || operation == "max";
            key << ':' << static_cast<uint32_t>(render_state_detail::equation(operation)) << ':'
                << static_cast<uint32_t>(extrema ? wgpu::BlendFactor::One : render_state_detail::factor(src, alpha)) << ':'
                << static_cast<uint32_t>(extrema ? wgpu::BlendFactor::One : render_state_detail::factor(dst, alpha));
        };
        component(state.blend_equation_rgb, state.blend_src_rgb, state.blend_dst_rgb, false);
        component(state.blend_equation_alpha, state.blend_src_alpha, state.blend_dst_alpha, true);
    }
    key << ";depth=" << state.depth_test;
    if (state.depth_test) key << ':' << state.depth_mask << ':' << state.depth_func;
    key << ";stencil=" << state.stencil_test;
    if (state.stencil_test) for (const auto* face : {&state.stencil_front, &state.stencil_back})
        key << ':' << face->compare << ':' << face->read_mask << ':' << face->write_mask << ':' << face->fail << ':' << face->depth_fail << ':' << face->pass;
    key << ";cull=" << state.cull_enabled << ':' << state.front_face;
    if (state.cull_enabled) key << ':' << state.cull_face;
    key << ";mask="; for (bool enabled : state.color_mask) key << enabled;
    key << ";offset=" << state.polygon_offset_fill;
    if (state.polygon_offset_fill) key << ':' << std::bit_cast<uint32_t>(state.polygon_offset_factor) << ':' << std::bit_cast<uint32_t>(state.polygon_offset_units);
    key << ";samples=" << state.sample_count << ':' << state.multisample << ':' << state.sample_alpha_to_coverage << ':' << state.sample_coverage_enabled;
    if (state.sample_coverage_enabled) key << ':' << std::bit_cast<uint32_t>(state.sample_coverage) << ':' << state.sample_coverage_invert;
    key << ";line=" << std::bit_cast<uint32_t>(state.line_width) << ':' << state.line_smooth;
    return key.str();
}
