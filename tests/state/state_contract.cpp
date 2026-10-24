#include "runtime_state.hpp"

#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}
Value arg(const char* text) { Value result; result.kind = Value::Kind::Str; result.s = text; return result; }
Value arg(int64_t value) { Value result; result.kind = Value::Kind::Int; result.i = value; return result; }
Value arg(double value) { Value result; result.kind = Value::Kind::Float; result.f = value; return result; }
template <typename... Args> Command func(const char* name, Args... args) {
    return Command{"FUNC", {arg(name), arg(args)...}};
}
template <typename Function> void rejects(Function&& function, const std::string& needle) {
    bool failed = false;
    try { function(); }
    catch (const std::runtime_error& error) {
        failed = true;
        require(std::string(error.what()).find(needle) != std::string::npos, "missing contextual diagnostic: " + std::string(error.what()));
    }
    require(failed, "required rejection: " + needle);
}

void defaults_and_parsing() {
    RenderState state;
    require(!state.blend_enabled && !state.depth_test && state.depth_mask && !state.stencil_test, "OpenGL test/write defaults");
    require(state.depth_func == "less" && state.front_face == "ccw" && state.cull_face == "back", "OpenGL function/face defaults");
    require(state.clear_color == std::array<double, 4>{0, 0, 0, 0} && state.clear_depth == 1, "OpenGL clear defaults");
    require(!parse_render_state(func("glFinish"), state) && !parse_render_state(func("glFlush"), state) &&
            !parse_render_state(func("glClear", int64_t(0x4000)), state), "submission/ordered-clear routing");
    require(parse_render_state(func("glEnable", "depth_test"), state) && state.depth_test, "depth enable");
    parse_render_state(func("glDisable", int64_t(0x0b71)), state);
    require(!state.depth_test, "numeric capability");
    parse_render_state(func("glDepthFunc", int64_t(0x0203)), state);
    require(state.depth_func == "lequal", "numeric comparison enum");
    parse_render_state(func("glViewport", int64_t(-1), int64_t(2), int64_t(8), int64_t(7)), state);
    require(state.viewport == std::array<int, 4>{-1, 2, 8, 7}, "viewport values");
    parse_render_state(func("glScissor", int64_t(1), int64_t(2), int64_t(3), int64_t(4)), state);
    parse_render_state(func("glEnable", "scissor_test"), state);
    require(state.scissor_enabled && state.scissor[3] == 4, "dynamic scissor");
    parse_render_state(func("glDepthRange", -2.0, 3.0), state);
    require(state.depth_range == std::array<float, 2>{0, 1}, "depth range clamps");
    const auto before = state_key(state);
    rejects([&] { parse_render_state(func("glEnable", "unknown_capability"), state); }, "glEnable");
    rejects([&] { parse_render_state(func("glLineWidth", 0.0), state); }, "finite and positive");
    rejects([&] { parse_render_state(func("glBogus", int64_t(1)), state); }, "glBogus");
    rejects([&] { parse_render_state(func("glViewport", int64_t(0), int64_t(0), int64_t(-1), int64_t(4)), state); }, "nonnegative");
    require(before == state_key(state) && state.viewport[0] == -1, "failed state change is atomic");
}

void line_width_and_smooth_state() {
    RenderState state;
    const auto defaults = state_key(state);
    require(state.line_width == 1 && !state.line_smooth, "line width/smooth defaults");
    require(parse_render_state(func("glLineWidth", 2.0), state) && state.line_width == 2,
            "positive width parses independently of DRAW coverage availability");
    require(state_key(state) != defaults, "line width changes state key");
    require(parse_render_state(func("glLineWidth", int64_t(4)), state) && state.line_width == 4,
            "integer positive width parses");
    require(parse_render_state(func("glLineWidth", 0.25), state) && state.line_width == 0.25f,
            "fractional positive width parses");
    require(parse_render_state(func("glEnable", "line_smooth"), state) && state.line_smooth,
            "smooth capability records requested state");
    const auto unchanged = state_key(state);
    const auto unchanged_width = state.line_width;
    for (double invalid : std::array<double, 8>{0.0, -0.0, -1.0,
            std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity(), std::numeric_limits<double>::max(),
            std::numeric_limits<double>::min()}) {
        rejects([&] { parse_render_state(func("glLineWidth", invalid), state); }, "finite");
        require(state_key(state) == unchanged && state.line_width == unchanged_width && state.line_smooth,
                "invalid width preserves complete state and smooth request atomically");
    }
    rejects([&] { parse_render_state(func("glLineWidth", "wide"), state); }, "numeric");
    require(state_key(state) == unchanged && state.line_width == unchanged_width && state.line_smooth,
            "nonnumeric width preserves state atomically");
    parse_render_state(func("glDisable", int64_t(0x0b20)), state);
    require(!state.line_smooth && state_key(state) != unchanged, "numeric smooth disable changes key");
    parse_render_state(func("glLineWidth", 1.0), state);
    require(state_key(state) == defaults, "restored default width/smooth restores key");
    parse_render_state(func("glEnable", int64_t(0x0b20)), state);
    require(state.line_smooth && state_key(state) != defaults, "numeric smooth enable changes key");
    parse_render_state(func("glDisable", "line_smooth"), state);
    require(!state.line_smooth && state_key(state) == defaults, "string smooth disable restores key");
}

void polygon_offset_float_range_is_atomic() {
    RenderState state;
    parse_render_state(func("glEnable", "polygon_offset_fill"), state);
    parse_render_state(func("glPolygonOffset", 2.0, 3.0), state);
    const auto original = state_key(state);
    for (double invalid : {1e300, -1e300, std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::quiet_NaN()}) {
        rejects([&] { parse_render_state(func("glPolygonOffset", invalid, 0.0), state); }, "glPolygonOffset");
        require(state_key(state) == original && state.polygon_offset_factor == 2 && state.polygon_offset_units == 3,
                "invalid factor preserves the entire committed state");
        rejects([&] { parse_render_state(func("glPolygonOffset", 0.0, invalid), state); }, "glPolygonOffset");
        require(state_key(state) == original && state.polygon_offset_factor == 2 && state.polygon_offset_units == 3,
                "invalid units do not commit a valid preceding factor");
    }
    const double maximum = std::numeric_limits<float>::max();
    parse_render_state(func("glPolygonOffset", maximum, -maximum), state);
    require(state.polygon_offset_factor == maximum && state.polygon_offset_units == -maximum,
            "finite float range endpoints remain accepted at parse time");
    parse_render_state(func("glPolygonOffset", 0.0, 1.0), state);
    require(state.polygon_offset_factor == 0 && state.polygon_offset_units == 1,
            "a valid operation succeeds after rejected overflow");
}

void multisample_descriptor_refusals() {
    RenderState state;
    wgpu::RenderPipelineDescriptor pipeline;
    wgpu::ColorTargetState color;
    wgpu::DepthStencilState depth;
    wgpu::BlendState blend;
    for (uint32_t invalid : std::array<uint32_t, 3>{0, 2, 8}) {
        state.sample_count = invalid;
        rejects([&] { fill_pipeline_state(state, pipeline, color, depth, blend); }, "sample counts 1 and 4");
    }
    state.sample_count = 4; state.multisample = false;
    rejects([&] { fill_pipeline_state(state, pipeline, color, depth, blend); }, "separate single-sample target");
    state.sample_count = 1;
    fill_pipeline_state(state, pipeline, color, depth, blend);
    require(pipeline.multisample.count == 1, "disabled multisampling admits a single-sample descriptor");
}

void descriptors() {
    RenderState state;
    wgpu::RenderPipelineDescriptor pipeline;
    pipeline.primitive.topology = wgpu::PrimitiveTopology::TriangleList;
    wgpu::ColorTargetState color;
    color.format = wgpu::TextureFormat::RGBA8Unorm;
    wgpu::DepthStencilState depth;
    depth.format = wgpu::TextureFormat::Depth24PlusStencil8;
    wgpu::BlendState blend;
    fill_pipeline_state(state, pipeline, color, depth, blend);
    require(color.blend == nullptr && color.writeMask == wgpu::ColorWriteMask::All, "disabled blending/color default");
    require(depth.depthWriteEnabled == wgpu::OptionalBool::False && depth.depthCompare == wgpu::CompareFunction::Always, "disabled depth never writes");
    require(depth.stencilFront.passOp == wgpu::StencilOperation::Keep && depth.stencilWriteMask == 0, "disabled stencil never modifies");
    parse_render_state(func("glEnable", "blend"), state);
    parse_render_state(func("glBlendFuncSeparate", "src_alpha", "one_minus_src_alpha", "zero", "one"), state);
    fill_pipeline_state(state, pipeline, color, depth, blend);
    require(color.blend == &blend && blend.color.srcFactor == wgpu::BlendFactor::SrcAlpha && blend.alpha.srcFactor == wgpu::BlendFactor::Zero && blend.alpha.dstFactor == wgpu::BlendFactor::One, "RGB/alpha factors separate");
    parse_render_state(func("glBlendEquationSeparate", "min", "max"), state);
    fill_pipeline_state(state, pipeline, color, depth, blend);
    require(blend.color.operation == wgpu::BlendOperation::Min && blend.color.srcFactor == wgpu::BlendFactor::One && blend.color.dstFactor == wgpu::BlendFactor::One, "min ignores prior factors");
    parse_render_state(func("glEnable", "depth_test"), state);
    parse_render_state(func("glDepthFunc", "lequal"), state);
    parse_render_state(func("glColorMask", int64_t(1), int64_t(0), int64_t(1), int64_t(0)), state);
    parse_render_state(func("glEnable", "polygon_offset_fill"), state);
    parse_render_state(func("glPolygonOffset", 1.25, 2.0), state);
    state.sample_count = 4;
    parse_render_state(func("glEnable", "sample_alpha_to_coverage"), state);
    fill_pipeline_state(state, pipeline, color, depth, blend);
    require(depth.depthWriteEnabled == wgpu::OptionalBool::True && depth.depthCompare == wgpu::CompareFunction::LessEqual, "depth write/test descriptors");
    require(depth.depthBias == 2 && depth.depthBiasSlopeScale == 1.25f, "polygon bias descriptors");
    require(color.writeMask == (wgpu::ColorWriteMask::Red | wgpu::ColorWriteMask::Blue), "component write mask");
    require(pipeline.multisample.count == 4 && pipeline.multisample.alphaToCoverageEnabled, "MSAA descriptors");
    parse_render_state(func("glEnable", "stencil_test"), state);
    parse_render_state(func("glStencilFuncSeparate", "front_and_back", "equal", int64_t(7), int64_t(0xff)), state);
    parse_render_state(func("glStencilOpSeparate", "front", "incr", "decr_wrap", "replace"), state);
    parse_render_state(func("glStencilOpSeparate", "back", "invert", "keep", "zero"), state);
    fill_pipeline_state(state, pipeline, color, depth, blend);
    require(depth.stencilFront.failOp == wgpu::StencilOperation::IncrementClamp && depth.stencilFront.depthFailOp == wgpu::StencilOperation::DecrementWrap && depth.stencilFront.passOp == wgpu::StencilOperation::Replace, "front stencil operations");
    require(depth.stencilBack.failOp == wgpu::StencilOperation::Invert && depth.stencilBack.passOp == wgpu::StencilOperation::Zero, "back stencil operations");
    parse_render_state(func("glStencilFuncSeparate", "back", "equal", int64_t(8), int64_t(0xff)), state);
    rejects([&] { fill_pipeline_state(state, pipeline, color, depth, blend); }, "distinct front/back");
}

void selected_stencil_faces() {
    RenderState s; s.stencil_test = true; s.stencil_front.reference = 7; s.stencil_back.reference = 9;
    s.stencil_front.read_mask = 0x0f; s.stencil_back.read_mask = 0xf0;
    s.stencil_front.write_mask = 0x33; s.stencil_back.write_mask = 0xcc;
    s.stencil_front.pass = "incr"; s.stencil_back.pass = "replace";
    require(stencil_face_route(s, LogicalDrawTopology::Polygon, true) == StencilFaceRoute::OrderedTwoFaces, "two-face polygon route");
    for (uint32_t face = 0; face < 2; ++face) {
        const auto p = stencil_face_state(s, StencilFaceRoute::OrderedTwoFaces, face);
        const auto& original = face ? s.stencil_back : s.stencil_front;
        require(p.cull_enabled && p.cull_face == (face ? "front" : "back"), "complementary cull preserves facing");
        require(p.front_face == s.front_face && p.stencil_front.reference == original.reference && p.stencil_back.reference == original.reference, "selected shared reference");
        require(p.stencil_front.read_mask == original.read_mask && p.stencil_back.write_mask == original.write_mask, "selected shared masks");
        require(p.stencil_front.pass == "incr" && p.stencil_back.pass == "replace", "actual face operations remain distinct");
        wgpu::RenderPipelineDescriptor pipeline; pipeline.primitive.topology = wgpu::PrimitiveTopology::TriangleList;
        wgpu::ColorTargetState color; wgpu::DepthStencilState depth; wgpu::BlendState blend;
        fill_pipeline_state(p, pipeline, color, depth, blend);
        require(depth.stencilReadMask == original.read_mask && depth.stencilWriteMask == original.write_mask, "selected descriptor masks");
    }
    require(s.stencil_front.reference == 7 && s.stencil_back.reference == 9, "captured state immutable");
    for (const std::string cull : {"front", "back", "front_and_back"}) {
        s.cull_enabled = true; s.cull_face = cull;
        require(stencil_face_route(s, LogicalDrawTopology::Polygon, true) ==
            (cull == "front" ? StencilFaceRoute::BackOnly : StencilFaceRoute::FrontOnly), "one-face fast path");
    }
    require(stencil_face_route(s, LogicalDrawTopology::NonPolygon, true) == StencilFaceRoute::FrontOnly, "points/lines use front");
    s.stencil_test = false;
    require(stencil_face_route(s, LogicalDrawTopology::Polygon, true) == StencilFaceRoute::Unchanged, "disabled stencil stays original");
    s.stencil_test = true;
    require(stencil_face_route(s, LogicalDrawTopology::Polygon, false) == StencilFaceRoute::Unchanged, "clear is not a user polygon");
}

void cache_dimensions() {
    RenderState state;
    const std::string initial = state_key(state);
    state.viewport = {1, 2, 3, 4}; state.scissor = {5, 6, 7, 8}; state.scissor_enabled = true;
    state.depth_range = {0.25f, 0.75f}; state.blend_color = {0.1, 0.2, 0.3, 0.4};
    state.clear_color = {1, 0, 0, 1}; state.clear_depth = 0.5;
    state.stencil_front.reference = state.stencil_back.reference = 2;
    require(state_key(state) == initial, "dynamic values excluded from pipeline key");
    state.blend_enabled = true;
    require(state_key(state) != initial, "blend enable changes pipeline key");
    const auto blended = state_key(state);
    state.blend_dst_alpha = "one";
    require(state_key(state) != blended, "separate alpha changes pipeline key");
    state.blend_src_rgb = "constant_alpha"; state.blend_dst_rgb = "one_minus_constant_alpha";
    auto constant = blend_constant_for_state(state);
    require(constant.r == 0.4 && constant.g == 0.4 && constant.b == 0.4 && constant.a == 0.4, "constant alpha replication");
    state.blend_dst_rgb = "constant_color";
    rejects([&] { blend_constant_for_state(state); }, "mixed constant-alpha");
    state.blend_equation_rgb = "min";
    blend_constant_for_state(state);
    const auto minimum = state_key(state);
    state.blend_src_rgb = "src_alpha";
    state.blend_dst_rgb = "one_minus_src_alpha";
    require(state_key(state) == minimum, "min/max ignored factors excluded from pipeline key");
}
void cull_both_and_scissor() {
    RenderState state;
    parse_render_state(func("glEnable", "cull_face"), state);
    parse_render_state(func("glCullFace", "front_and_back"), state);
    const RenderState captured = state;
    const std::array<int, 4> rectangle = {7, 9, 17, 23};
    const std::array<uint32_t, 4> full = {0, 0, 64, 48};
    const std::array<uint32_t, 4> explicit_rectangle = {7, 9, 17, 23};
    const std::array<uint32_t, 4> empty = {0, 0, 0, 0};
    for (const std::string mode : {"triangles", "triangle_strip", "triangle_fan"}) {
        const auto topology = logical_draw_topology(mode);
        require(topology == LogicalDrawTopology::Polygon, "original polygon mode captured");
        for (bool enabled : {false, true})
            require(effective_draw_scissor(captured, topology, true, enabled, rectangle, 64, 48) == empty,
                "both faces suppress polygon fragments with real draws retained");
        require(effective_draw_scissor(captured, topology, false, false, rectangle, 64, 48) == full,
            "unmasked clear is never culled");
        require(effective_draw_scissor(captured, topology, false, true, rectangle, 64, 48) == explicit_rectangle,
            "shader-backed masked clear retains original scissor");
    }
    for (const std::string mode : {"points", "lines", "line_strip", "line_loop"}) {
        const auto topology = logical_draw_topology(mode);
        require(topology == LogicalDrawTopology::NonPolygon, "point and line originals remain nonpolygon after expansion");
        require(effective_draw_scissor(captured, topology, true, false, rectangle, 64, 48) == full,
            "both-face culling does not affect point or line raster");
        require(effective_draw_scissor(captured, topology, true, true, rectangle, 64, 48) == explicit_rectangle,
            "point and line explicit scissor remains active");
    }
    parse_render_state(func("glDisable", "cull_face"), state);
    require(effective_draw_scissor(state, LogicalDrawTopology::Polygon, true, false, rectangle, 64, 48) == full,
        "following disabled-cull draw restores whole target");
    require(effective_draw_scissor(state, LogicalDrawTopology::Polygon, true, true, rectangle, 64, 48) == explicit_rectangle,
        "following disabled-cull draw restores explicit rectangle");
    require(effective_draw_scissor(captured, LogicalDrawTopology::Polygon, true, false, rectangle, 64, 48) == empty,
        "later state mutation cannot alter earlier snapshot");
    require(effective_draw_scissor(state, LogicalDrawTopology::Polygon, true, true, {60, 45, 17, 23}, 64, 48) ==
        std::array<uint32_t, 4>{60, 45, 4, 3}, "explicit scissor clipping unchanged");
    require(effective_draw_scissor(state, LogicalDrawTopology::Polygon, true, false, rectangle, 0, 0) == empty,
        "zero target remains an empty rectangle");
    const auto original_key = state_key(state);
    rejects([&] { parse_render_state(func("glCullFace", "all"), state); }, "unsupported cull mode");
    require(state_key(state) == original_key, "invalid cull enum leaves state unchanged");
    for (const auto topology : {wgpu::PrimitiveTopology::TriangleList, wgpu::PrimitiveTopology::TriangleStrip,
            wgpu::PrimitiveTopology::LineList, wgpu::PrimitiveTopology::LineStrip, wgpu::PrimitiveTopology::PointList}) {
        wgpu::RenderPipelineDescriptor pipeline;
        pipeline.primitive.topology = topology;
        wgpu::ColorTargetState color;
        wgpu::DepthStencilState depth;
        wgpu::BlendState blend;
        state = captured;
        fill_pipeline_state(state, pipeline, color, depth, blend);
        require(pipeline.primitive.cullMode == wgpu::CullMode::None, "front_and_back descriptor delegates polygon coverage to scissor");
        for (const std::string face : {"front", "back"}) {
            state.cull_face = face;
            fill_pipeline_state(state, pipeline, color, depth, blend);
            const bool polygon = topology == wgpu::PrimitiveTopology::TriangleList || topology == wgpu::PrimitiveTopology::TriangleStrip;
            require(pipeline.primitive.cullMode == (!polygon ? wgpu::CullMode::None :
                face == "front" ? wgpu::CullMode::Front : wgpu::CullMode::Back), "front/back descriptors affect polygons only");
        }
    }
}

}  // namespace

int main() {
    try {
        defaults_and_parsing(); descriptors(); cache_dimensions(); line_width_and_smooth_state(); multisample_descriptor_refusals();
        cull_both_and_scissor(); selected_stencil_faces(); polygon_offset_float_range_is_atomic();
        std::cout << "render state parsing, defaults, descriptors, stencil faces, and pipeline keys passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
