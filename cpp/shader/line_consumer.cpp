#include "line_consumer.hpp"
#include "shader/glslang_spv.hpp"
#include <SPIRV/spirv.hpp11>

#include <cctype>
#include <cmath>
#include <cstring>
#include <sstream>
#include <unordered_map>
#include <unordered_set>

namespace vispy::shader {
namespace {

constexpr std::string_view prefix = "vispy_line_consumer_";

// Operate on identifier tokens only. Comments, quoted preprocessing operands,
// and line count remain intact; user expressions and helper bodies are not
// parsed/rebuilt. The normalized global declarations have separate exact joins.
struct Token { size_t begin = 0, end = 0; std::string text; };
std::vector<Token> tokens(const std::string& source) {
    std::vector<Token> result;
    for (size_t i = 0; i < source.size();) {
        const unsigned char c = static_cast<unsigned char>(source[i]);
        if (std::isspace(c)) { ++i; continue; }
        if (i + 1 < source.size() && source[i] == '/' && source[i + 1] == '/') {
            i = source.find('\n', i + 2); if (i == std::string::npos) break; continue;
        }
        if (i + 1 < source.size() && source[i] == '/' && source[i + 1] == '*') {
            const auto end = source.find("*/", i + 2);
            if (end == std::string::npos) throw std::invalid_argument("unterminated normalized comment");
            i = end + 2; continue;
        }
        if (source[i] == '"' || source[i] == '\'') {
            const char quote = source[i++];
            while (i < source.size()) {
                if (source[i] == '\\') { i += std::min<size_t>(2, source.size() - i); continue; }
                if (source[i++] == quote) break;
            }
            continue;
        }
        const size_t begin = i++;
        if (std::isalpha(c) || c == '_')
            while (i < source.size() && (std::isalnum(static_cast<unsigned char>(source[i])) || source[i] == '_')) ++i;
        result.push_back({begin, i, source.substr(begin, i - begin)});
    }
    return result;
}

struct FragmentHelpers {
    bool builtin = false, query = false;
    bool needed() const { return builtin || query; }
};

std::string fragment_identifiers(const std::string& source, FragmentHelpers& helpers, bool depth_output) {
    const auto lexed = tokens(source);
    std::unordered_map<size_t, std::string> replace;
    size_t mains = 0;
    for (size_t i = 0; i < lexed.size(); ++i) {
        const auto& token = lexed[i];
        if (token.text == "main" && i && lexed[i - 1].text == "void" && i + 3 < lexed.size() &&
            lexed[i + 1].text == "(" && lexed[i + 2].text == ")" && lexed[i + 3].text == "{") {
            replace.emplace(token.begin, "vispy_line_consumer_original_fragment"); ++mains;
        } else if (token.text == "gl_FragCoord") replace.emplace(token.begin, "vispy_line_consumer_fragment_coord");
        else if (!depth_output && token.text == "gl_FragDepth")
            replace.emplace(token.begin, "vispy_line_consumer_fragment_depth");
        else if (token.text == "gl_HelperInvocation") {
            replace.emplace(token.begin, "vispy_line_consumer_helper_invocation"); helpers.builtin = true;
        } else if (token.text == "helperInvocationEXT" && i + 1 < lexed.size() && lexed[i + 1].text == "(") {
            replace.emplace(token.begin, "vispy_line_consumer_query_helper"); helpers.query = true;
        }
        else if (token.text == "gl_FrontFacing") replace.emplace(token.begin, "true");
        else if (token.text == "gl_PrimitiveID") replace.emplace(token.begin, "int(vispy_line_consumer_ids.w)");
    }
    if (mains != 1) throw std::invalid_argument("exactly one normalized fragment main is required");
    std::string result; size_t cursor = 0;
    for (const auto& token : lexed) if (auto found = replace.find(token.begin); found != replace.end()) {
        result.append(source, cursor, token.begin - cursor); result += found->second; cursor = token.end;
    }
    result.append(source, cursor, source.size() - cursor); return result;
}

void replace_one(std::string& source, const std::string& old, const std::string& replacement) {
    const auto at = source.find(old);
    if (at == std::string::npos || source.find(old, at + old.size()) != std::string::npos)
        throw std::invalid_argument("canonical declaration is missing or repeated: " + old);
    source.replace(at, old.size(), replacement);
}

std::string uniform_member_name(const NormUniform& uniform) {
    return uniform.type == "bool" || uniform.type.rfind("bvec", 0) == 0 ?
        "vispy_bool_storage_" + uniform.name : uniform.name;
}

std::string uniform_block(const std::vector<NormUniform>& uniforms) {
    std::ostringstream out;
    out << "layout(set = 0, binding = 0, std140) uniform VispyUniforms {\n";
    for (const auto& uniform : uniforms) {
        out << "    layout(offset = " << uniform.offset << ") "
            << (uniform.storage_type.empty() ? uniform.type : uniform.storage_type) << ' ' << uniform_member_name(uniform);
        if (uniform.array_size) out << '[' << uniform.array_size << ']';
        out << ";\n";
    }
    out << "};\n"; return out.str();
}

std::string storage_block(const LineEvaluatorArtifact& evaluator) {
    std::ostringstream out;
    out << "struct VispyLineConsumerRow {\n    vec4 clip_position;\n";
    for (size_t i = 0; i < evaluator.outputs.size(); ++i) {
        const auto& field = evaluator.outputs[i];
        out << "    " << field.storage_type << " varying_" << i;
        if (field.varying.array_size) out << '[' << field.varying.array_size << ']';
        out << ";\n";
    }
    out << "};\nlayout(set = 0, binding = " << evaluator.output_binding
        << ", std430) readonly buffer VispyLineConsumerRows { VispyLineConsumerRow vispy_line_consumer_rows[]; };\n";
    return out.str();
}

// Common GL homogeneous clipping and explicit interpolation. Scale both
// endpoints together before plane sums; ratios/parameters remain unchanged.
// Zero-w, nonfinite and projected-degenerate centerlines are rejected explicitly.
const char* geometry = R"GLSL(
// The pinned production reader rejects OpIsNan/OpIsInf. This exact IEEE-754
// bit rule admits both signed zeros, subnormals and finite values; it rejects
// either infinity and every NaN payload without floating-point comparisons.
bool vispy_line_consumer_finite(float v) { return (floatBitsToUint(v) & 0x7fffffffu) < 0x7f800000u; }
bool vispy_line_consumer_finite2(vec2 v) { return all(lessThan(floatBitsToUint(v) & uvec2(0x7fffffffu), uvec2(0x7f800000u))); }
bool vispy_line_consumer_finite4(vec4 v) { return all(lessThan(floatBitsToUint(v) & uvec4(0x7fffffffu), uvec4(0x7f800000u))); }
float vispy_line_consumer_plane(vec4 p, int plane) {
    if (plane == 0) return p.w + p.x;
    if (plane == 1) return p.w - p.x;
    if (plane == 2) return p.w + p.y;
    if (plane == 3) return p.w - p.y;
    if (plane == 4) return p.w + p.z;
    return p.w - p.z;
}
bool vispy_line_consumer_clip(vec4 original_a, vec4 original_b,
    out vec4 a, out vec4 b, out vec2 interval, out float scale) {
    if (!vispy_line_consumer_finite4(original_a) || !vispy_line_consumer_finite4(original_b)) return false;
    scale = max(1.0, max(max(max(abs(original_a.x), abs(original_a.y)), max(abs(original_a.z), abs(original_a.w))),
                         max(max(abs(original_b.x), abs(original_b.y)), max(abs(original_b.z), abs(original_b.w)))));
    vec4 p0 = original_a / scale, p1 = original_b / scale;
    interval = vec2(0.0, 1.0);
    for (int plane = 0; plane < 6; ++plane) {
        float d0 = vispy_line_consumer_plane(p0, plane), d1 = vispy_line_consumer_plane(p1, plane);
        if (d0 < 0.0 && d1 < 0.0) return false;
        if ((d0 < 0.0) != (d1 < 0.0)) {
            float denominator = d0 - d1;
            if (denominator == 0.0 || !vispy_line_consumer_finite(denominator)) return false;
            float t = d0 / denominator;
            if (d0 < 0.0) interval.x = max(interval.x, t); else interval.y = min(interval.y, t);
        }
    }
    if (interval.x >= interval.y) return false;
    a = mix(p0, p1, interval.x); b = mix(p0, p1, interval.y);
    if (!vispy_line_consumer_finite4(a) || !vispy_line_consumer_finite4(b) || a.w <= 0.0 || b.w <= 0.0) return false;
    vec2 da = a.xy / a.w, db = b.xy / b.w;
    return any(notEqual(da, db));
}
vec2 vispy_line_consumer_window(vec4 p) {
    return vispy_line_consumer_viewport.xy + (p.xy / p.w * 0.5 + 0.5) * vispy_line_consumer_viewport.zw;
}
bool vispy_line_consumer_parameters() {
    if (vispy_line_consumer_header.x != 2u || vispy_line_consumer_header.z != VISPY_LINE_CONSUMER_ROW_BYTES ||
        vispy_line_consumer_header.y > uint(vispy_line_consumer_rows.length())) return false;
    if (vispy_line_consumer_header.w >= 3u) {
        if (vispy_line_consumer_header.w > 7u || vispy_line_consumer_ranges.z != 0u ||
            vispy_line_consumer_ranges.w == 0u || vispy_line_consumer_ranges.w > 0x7fffffffu) return false;
        uint flags = vispy_line_consumer_header.w - 3u;
        uint previous = flags & 1u, closing = (flags >> 1u) & 1u;
        if (vispy_line_consumer_ranges.y > 0xffffffffu - (vispy_line_consumer_ranges.w - 1u)) return false;
        if (flags == 4u) {
            if (vispy_line_consumer_ranges.w > 0x7fffffffu ||
                vispy_line_consumer_header.y != vispy_line_consumer_ranges.w * 2u) return false;
        } else if (vispy_line_consumer_header.y != vispy_line_consumer_ranges.w + 1u) return false;
        if (vispy_line_consumer_header.y < previous + closing ||
            vispy_line_consumer_ranges.x != vispy_line_consumer_header.y - previous - closing) return false;
    } else {
    if (vispy_line_consumer_ranges.x < 2u || vispy_line_consumer_ranges.y == 0u) return false;
    if (vispy_line_consumer_header.y % vispy_line_consumer_ranges.x != 0u) return false;
    uint expected_segments = vispy_line_consumer_header.w == 0u ? vispy_line_consumer_ranges.x / 2u :
        vispy_line_consumer_header.w == 1u ? vispy_line_consumer_ranges.x - 1u : vispy_line_consumer_ranges.x;
    if (expected_segments == 0u) return false;
    if (expected_segments != vispy_line_consumer_ranges.y || (vispy_line_consumer_header.w == 0u &&
        vispy_line_consumer_ranges.x % 2u != 0u)) return false;
    uint instances = vispy_line_consumer_header.y / vispy_line_consumer_ranges.x;
    // q=floor(Y/X), E<=X: q*E<=Y<=UINT_MAX, so this product cannot overflow.
    uint total = instances * expected_segments;
    if (vispy_line_consumer_ranges.z > total || vispy_line_consumer_ranges.w > total - vispy_line_consumer_ranges.z) return false;
    }
    if (!vispy_line_consumer_finite4(vispy_line_consumer_viewport) || !vispy_line_consumer_finite4(vispy_line_consumer_raster) ||
        any(lessThanEqual(vispy_line_consumer_viewport.zw, vec2(0.0))) || vispy_line_consumer_raster.x < 1.0 ||
        vispy_line_consumer_raster.x > 16777216.0 || floor(vispy_line_consumer_raster.x) != vispy_line_consumer_raster.x ||
        vispy_line_consumer_raster.y <= 0.0 || any(lessThan(vispy_line_consumer_raster.zw, vec2(0.0))) ||
        any(greaterThan(vispy_line_consumer_raster.zw, vec2(1.0)))) return false;
    return true;
}
bool vispy_line_consumer_segment(uint segment, out uvec4 ids) {
    if (!vispy_line_consumer_parameters()) return false;
    if (vispy_line_consumer_header.w >= 3u) {
        if (segment >= vispy_line_consumer_ranges.w) return false;
        uint flags = vispy_line_consumer_header.w - 3u;
        uint previous = flags & 1u, closing = (flags >> 1u) & 1u;
        uint first = flags == 4u ? segment * 2u :
            previous != 0u && segment == 0u ? vispy_line_consumer_ranges.x : segment - previous;
        uint last = flags == 4u ? first + 1u :
            closing != 0u && segment + 1u == vispy_line_consumer_ranges.w ?
                vispy_line_consumer_ranges.x + previous : segment + 1u - previous;
        if (first >= vispy_line_consumer_header.y || last >= vispy_line_consumer_header.y) return false;
        ids = uvec4(first, last, last, vispy_line_consumer_ranges.y + segment);
        return true;
    }
    uint per_instance = vispy_line_consumer_ranges.y;
    uint instance = segment / per_instance, ordinal = segment % per_instance;
    uint instances = vispy_line_consumer_header.y / vispy_line_consumer_ranges.x;
    if (instance >= instances) return false;
    uint first = vispy_line_consumer_header.w == 0u ? ordinal * 2u : ordinal;
    uint last = vispy_line_consumer_header.w == 2u && ordinal == per_instance - 1u ? 0u : first + 1u;
    uint base = instance * vispy_line_consumer_ranges.x;
    if (first >= vispy_line_consumer_ranges.x || last >= vispy_line_consumer_ranges.x) return false;
    ids = uvec4(base + first, base + last, base + last, segment);
    return true;
}
// Compare symbolic coefficients (constant, epsilon, epsilon^2), implementing
// the specified endpoint shift (-epsilon,-epsilon^2) without a guessed epsilon.
bool vispy_line_consumer_lex_less(vec3 a, vec3 b) {
    return a.x < b.x || (a.x == b.x && (a.y < b.y || (a.y == b.y && a.z < b.z)));
}
float vispy_line_consumer_diamond_plane(vec4 p, vec2 n, vec2 center) {
    vec2 ndc = p.xy / p.w;
    vec2 half_viewport = vispy_line_consumer_viewport.zw * 0.5;
    vec2 viewport_center = vispy_line_consumer_viewport.xy + half_viewport;
    float offset = dot(n, viewport_center - center) - 0.5;
    // Keep the original binary32 projection residual until the plane sum.
    // Rounding translated window endpoints first can turn a strict side into
    // an exact diamond tie. Explicit fma preserves the affine plane ordering.
    return fma(n.y * half_viewport.y, ndc.y,
               fma(n.x * half_viewport.x, ndc.x, offset));
}
bool vispy_line_consumer_diamond(vec4 a, vec4 b, vec2 center, bool original_terminal) {
    vec3 lo = vec3(0.0), hi = vec3(1.0, 0.0, 0.0);
    bool endpoint_inside = true;
    for (int i = 0; i < 4; ++i) {
        vec2 n = vec2((i & 1) == 0 ? 1.0 : -1.0, (i & 2) == 0 ? 1.0 : -1.0);
        vec3 h0 = vec3(vispy_line_consumer_diamond_plane(a, n, center), -n.x, -n.y);
        vec3 h1 = vec3(vispy_line_consumer_diamond_plane(b, n, center), -n.x, -n.y);
        endpoint_inside = endpoint_inside && vispy_line_consumer_lex_less(h1, vec3(0.0));
        float d = h1.x - h0.x;
        if (d == 0.0) { if (!vispy_line_consumer_lex_less(h0, vec3(0.0))) return false; }
        else {
            vec3 crossing = -h0 / d;
            if (d > 0.0) { if (vispy_line_consumer_lex_less(crossing, hi)) hi = crossing; }
            else { if (vispy_line_consumer_lex_less(lo, crossing)) lo = crossing; }
        }
    }
    // Clipping may replace LAST with a viewport boundary. That artificial
    // endpoint must not suppress the last intersected pixel diamond.
    return (!endpoint_inside || !original_terminal) && vispy_line_consumer_lex_less(lo, hi);
}
bool vispy_line_consumer_aliased(vec4 a, vec4 b, vec2 pixel, bool original_terminal) {
    vec2 pa = vispy_line_consumer_window(a), pb = vispy_line_consumer_window(b);
    vec2 delta = pb - pa;
    bool x_major = abs(delta.x) >= abs(delta.y);
    float width = vispy_line_consumer_raster.x;
    vec2 minor = x_major ? vec2(0.0, 1.0) : vec2(1.0, 0.0);
    vec2 base_a = pa - minor * ((width - 1.0) * 0.5);
    float major_delta = x_major ? delta.x : delta.y;
    if (major_delta == 0.0) return false;
    float major_q = ((x_major ? pixel.x : pixel.y) - (x_major ? base_a.x : base_a.y)) / major_delta;
    vec2 projected = base_a + major_q * delta;
    float nearest = floor(dot(pixel - projected, minor));
    // An x-major (y-major) diamond has at most two candidate base rows
    // (columns); three adjacent integer candidates include boundary ties.
    for (int k = -1; k <= 1; ++k) {
        float replicate = nearest + float(k);
        if (replicate >= 0.0 && replicate < width &&
            vispy_line_consumer_diamond(a, b,
                pixel - minor * (replicate - (width - 1.0) * 0.5), original_terminal)) return true;
    }
    return false;
}
)GLSL";

const char* vertex_main = R"GLSL(
layout(location = 0) flat out uvec4 vispy_line_consumer_ids;
void main() {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    vispy_line_consumer_ids = uvec4(0u);
    if (gl_VertexIndex < 0 || gl_VertexIndex >= 6 || gl_InstanceIndex < 0) return;
    uint local_segment = uint(gl_InstanceIndex);
    if (local_segment >= vispy_line_consumer_ranges.w || !vispy_line_consumer_parameters()) return;
    uvec4 ids;
    uint addressed_segment = vispy_line_consumer_header.w >= 3u ? local_segment : vispy_line_consumer_ranges.z + local_segment;
    if (!vispy_line_consumer_segment(addressed_segment, ids)) return;
    vec4 a, b; vec2 interval; float scale;
    if (!vispy_line_consumer_clip(vispy_line_consumer_rows[ids.x].clip_position,
        vispy_line_consumer_rows[ids.y].clip_position, a, b, interval, scale)) return;
    vec2 pa = vispy_line_consumer_window(a), pb = vispy_line_consumer_window(b);
    float padding = vispy_line_consumer_raster.x * 0.5 + 1.0;
    vec2 lower = min(pa, pb) - vec2(padding), upper = max(pa, pb) + vec2(padding);
    const vec2 corners[6] = vec2[6](vec2(0,0), vec2(1,0), vec2(0,1), vec2(0,1), vec2(1,0), vec2(1,1));
    vec2 window = mix(lower, upper, corners[gl_VertexIndex]);
    vec2 ndc = (window - vispy_line_consumer_viewport.xy) / vispy_line_consumer_viewport.zw * 2.0 - 1.0;
    if (!vispy_line_consumer_finite2(ndc)) return;
    // Original GL six-plane clipping precedes expansion. Fragment depth is
    // reconstructed separately. Match ordinary GL-window rendering; the
    // presentation pass flips the color target into display row order.
    gl_Position = vec4(ndc.x, -ndc.y, 0.5, 1.0);
    vispy_line_consumer_ids = ids;
}
)GLSL";

// A separable one-pixel filter of a butt-ended rectangle in line coordinates.
// Fractional widths retain their area, including widths below one pixel. The
// rotated filter is deliberately an approximation to hardware GL line smoothing.
const char* smooth_geometry = R"GLSL(
float vispy_line_consumer_smooth(vec2 a, vec2 b, vec2 pixel) {
    vec2 delta = b - a;
    float segment_length = length(delta);
    if (segment_length <= 0.0 || !vispy_line_consumer_finite(segment_length)) return 0.0;
    vec2 tangent = delta / segment_length;
    vec2 relative = pixel - a;
    float along = dot(relative, tangent);
    float across = abs(dot(relative, vec2(-tangent.y, tangent.x)));
    float width = vispy_line_consumer_raster.x;
    float side = clamp(min(width, width * 0.5 + 0.5 - across), 0.0, 1.0);
    float cap = clamp(min(segment_length, min(along + 0.5, segment_length - along + 0.5)), 0.0, 1.0);
    return side * cap;
}
)GLSL";

// Normalization emits one canonical global output. Respect its original name;
// function parameters also use 'out', so only inspect top-level declarations.
std::string smooth_color_output(const std::string& fragment) {
    const auto lexed = tokens(fragment);
    int braces = 0, parentheses = 0;
    for (size_t i = 0; i < lexed.size(); ++i) {
        const auto& t = lexed[i].text;
        if (t == "{") ++braces;
        else if (t == "}") --braces;
        else if (t == "(") ++parentheses;
        else if (t == ")") --parentheses;
        else if (t == "out" && !braces && !parentheses && i + 3 < lexed.size()) {
            if (lexed[i + 1].text != "vec4" || lexed[i + 3].text != ";")
                throw std::invalid_argument("smooth lines require a vec4 color output for coverage alpha");
            return lexed[i + 2].text;
        }
    }
    throw std::invalid_argument("smooth line color output is missing");
}

std::string varying_declaration(const NormVarying& varying) {
    std::string out = "layout(location = " + std::to_string(varying.location) + ") ";
    if (varying.centroid) out += "centroid "; if (varying.sample) out += "sample ";
    if (varying.interpolation == "flat" || varying.interpolation == "noperspective") out += varying.interpolation + ' ';
    out += "in " + varying.type + ' ' + varying.name;
    if (varying.array_size) out += '[' + std::to_string(varying.array_size) + ']';
    return out + ";\n";
}

std::string private_declaration(const NormVarying& varying) {
    std::string out = varying.type + ' ' + varying.name;
    if (varying.array_size) out += '[' + std::to_string(varying.array_size) + ']';
    return out + ";\n";
}

std::string value_expression(const LineOutputField& field, size_t n, const std::string& index) {
    const auto tail = ".varying_" + std::to_string(n) + index;
    const auto first = "vispy_line_consumer_rows[vispy_line_consumer_ids.x]" + tail;
    const auto last = "vispy_line_consumer_rows[vispy_line_consumer_ids.z]" + tail;
    if (field.varying.interpolation == "flat") {
        if (field.varying.value_type.scalar == ShaderScalarType::Bool) {
            if (field.varying.value_type.rows == 1) return '(' + last + " != 0u)";
            return "notEqual(" + last + ", " + field.storage_type + "(0u))";
        }
        return last;
    }
    const auto second = "vispy_line_consumer_rows[vispy_line_consumer_ids.y]" + tail;
    const std::string parameter = field.varying.interpolation == "noperspective" ?
        "vispy_line_consumer_screen_original" : "vispy_line_consumer_homogeneous_original";
    return "((1.0 - " + parameter + ") * " + first + " + " + parameter + " * " + second + ')';
}

std::string fragment_main(const LineEvaluatorArtifact& evaluator, const FragmentHelpers& helpers, bool depth_output) {
    std::string out = R"GLSL(
void vispy_line_consumer_initialize_globals() {}
void main() {
    if (!vispy_line_consumer_parameters()) discard;
    uint first_segment = vispy_line_consumer_header.w >= 3u ? vispy_line_consumer_ranges.y : vispy_line_consumer_ranges.z;
    if (vispy_line_consumer_ids.w < first_segment ||
        vispy_line_consumer_ids.w - first_segment >= vispy_line_consumer_ranges.w) discard;
    uint addressed_segment = vispy_line_consumer_header.w >= 3u ? vispy_line_consumer_ids.w - first_segment : vispy_line_consumer_ids.w;
    uvec4 expected;
    if (!vispy_line_consumer_segment(addressed_segment, expected) || any(notEqual(expected, vispy_line_consumer_ids))) discard;
    vec4 original_a = vispy_line_consumer_rows[vispy_line_consumer_ids.x].clip_position;
    vec4 original_b = vispy_line_consumer_rows[vispy_line_consumer_ids.y].clip_position;
    vec4 a, b; vec2 interval; float scale;
    if (!vispy_line_consumer_clip(original_a, original_b, a, b, interval, scale)) discard;
    vec2 pa = vispy_line_consumer_window(a), pb = vispy_line_consumer_window(b);
    vec2 pixel = gl_FragCoord.xy;
    // Coverage is deliberately a value, not a pre-call kill. Neighboring
    // helper pixels must reach the original fragment's derivatives/implicit
    // texture samples after reconstructing their extrapolated inputs.
    bool vispy_line_consumer_covered = vispy_line_consumer_aliased(a, b, pixel, interval.y == 1.0);
    vec2 delta = pb - pa;
    float squared = dot(delta, delta);
    // This refusal is per primitive, independent of the fragment coordinate.
    if (squared <= 0.0 || !vispy_line_consumer_finite(squared)) discard;
    float q = dot(pixel - pa, delta) / squared;
    bool vispy_line_consumer_valid = vispy_line_consumer_finite(q);
    q = vispy_line_consumer_valid ? q : 0.0;
    float inverse_denominator = (1.0 - q) * b.w + q * a.w;
    bool denominator_valid = inverse_denominator != 0.0 && vispy_line_consumer_finite(inverse_denominator);
    vispy_line_consumer_valid = vispy_line_consumer_valid && denominator_valid;
    inverse_denominator = denominator_valid ? inverse_denominator : 1.0;
    float homogeneous_local = q * a.w / inverse_denominator;
    float vispy_line_consumer_homogeneous_original = mix(interval.x, interval.y, homogeneous_local);
    vec4 p0 = original_a / scale, p1 = original_b / scale;
    float dlo = mix(p0.w, p1.w, interval.x), dhi = mix(p0.w, p1.w, interval.y);
    if (dlo == 0.0 || dhi == 0.0) discard;
    float screen_lo = interval.x * p1.w / dlo, screen_hi = interval.y * p1.w / dhi;
    float vispy_line_consumer_screen_original = mix(screen_lo, screen_hi, q);
    float reciprocal_w = ((1.0 - q) / a.w + q / b.w) / scale;
    float ndc_depth = mix(a.z / a.w, b.z / b.w, q);
    float depth = mix(vispy_line_consumer_raster.z, vispy_line_consumer_raster.w, ndc_depth * 0.5 + 0.5);
    bool homogeneous_valid = vispy_line_consumer_finite(vispy_line_consumer_homogeneous_original);
    bool screen_valid = vispy_line_consumer_finite(vispy_line_consumer_screen_original);
    bool reciprocal_valid = vispy_line_consumer_finite(reciprocal_w);
    bool depth_valid = vispy_line_consumer_finite(depth);
    vispy_line_consumer_valid = vispy_line_consumer_valid && homogeneous_valid && screen_valid && reciprocal_valid && depth_valid;
    // Sanitization reconverges before user code; invalid helper arithmetic
    // cannot introduce an additional divergent discard before derivatives.
    vispy_line_consumer_homogeneous_original = homogeneous_valid ? vispy_line_consumer_homogeneous_original : 0.0;
    vispy_line_consumer_screen_original = screen_valid ? vispy_line_consumer_screen_original : 0.0;
    reciprocal_w = reciprocal_valid ? reciprocal_w : 1.0;
    depth = depth_valid ? depth : 0.0;
    vispy_line_consumer_fragment_coord = vec4(pixel, depth, reciprocal_w);
    gl_FragDepth = depth;
)GLSL";
    // The original builtin is captured before original private initialization.
    // Extension queries instead read native helper state dynamically at each
    // original query (including after demote). No unused native helper builtin
    // is introduced for fragments which do not read it.
    if (helpers.needed()) out += std::string("    vispy_line_consumer_helper_invocation = ") +
        (helpers.builtin ? "gl_HelperInvocation || " : "") +
        "!vispy_line_consumer_covered || !vispy_line_consumer_valid;\n";
    for (size_t n = 0; n < evaluator.outputs.size(); ++n) {
        const auto& field = evaluator.outputs[n];
        const auto count = field.varying.array_size ? field.varying.array_size : 1;
        for (int i = 0; i < count; ++i) {
            const auto index = field.varying.array_size ? '[' + std::to_string(i) + ']' : "";
            out += "    " + field.varying.name + index + " = " + value_expression(field, n, index) + ";\n";
        }
    }
    out += "    vispy_line_consumer_initialize_globals();\n    vispy_line_consumer_original_fragment();\n"
        "    if (!vispy_line_consumer_covered || !vispy_line_consumer_valid) discard;\n}\n";
    if (!depth_output) replace_one(out, "    gl_FragDepth = depth;",
        "    vispy_line_consumer_fragment_depth = depth;");
    return out;
}

NormUniform parameter_uniform(std::string name, std::string type, uint32_t offset) {
    NormUniform u; u.name = std::move(name); u.type = std::move(type); u.storage_type = u.type;
    u.offset = offset; u.size = 16; u.component_count = 4; u.matrix_rows = 4; return u;
}

void verify_rows(const LineEvaluatorArtifact& evaluator, const SpvStorageLayout& actual) {
    if (actual.row_stride != evaluator.output_row_bytes || actual.members.size() != evaluator.outputs.size() + 1)
        throw std::invalid_argument("compiled consumer output-row stride/member count differs");
    const auto& clip = actual.members.front();
    if (clip.name != "clip_position" || clip.offset != 0 || clip.size != 16 || clip.array_size ||
        clip.value_type.scalar != ShaderScalarType::Float || clip.value_type.rows != 4 || clip.value_type.columns != 1)
        throw std::invalid_argument("compiled consumer original GL clip_position differs");
    for (size_t n = 0; n < evaluator.outputs.size(); ++n) {
        const auto& field = evaluator.outputs[n]; const auto& member = actual.members[n + 1];
        auto expected = field.varying.value_type;
        if (expected.scalar == ShaderScalarType::Bool) expected.scalar = ShaderScalarType::Uint;
        if (member.name != "varying_" + std::to_string(n) || member.offset != field.offset || member.size != field.size ||
            member.array_size != static_cast<uint32_t>(field.varying.array_size) || member.array_stride != field.array_stride ||
            member.matrix_stride != field.matrix_stride || member.value_type.scalar != expected.scalar ||
            member.value_type.rows != expected.rows || member.value_type.columns != expected.columns)
            throw std::invalid_argument("compiled consumer typed varying row differs: " + field.varying.name);
    }
}

uint32_t resource_stages(std::span<const SpvResourceUsage> resources, uint32_t binding) {
    uint32_t mask = 0; for (const auto& resource : resources) if (resource.binding == binding) mask |= resource.stage_mask;
    return mask;
}

void verify_interface(const std::vector<uint32_t>& words, spv::StorageClass direction) {
    struct Type { spv::Op op; std::vector<uint32_t> args; };
    struct Variable { uint32_t pointer = 0, storage = 0; };
    std::unordered_map<uint32_t, Type> types;
    std::unordered_map<uint32_t, Variable> variables;
    std::unordered_map<uint32_t, std::string> names;
    std::unordered_map<uint32_t, uint32_t> locations;
    std::unordered_set<uint32_t> flat;
    for (size_t p = 5; p < words.size();) {
        const size_t count = words[p] >> 16;
        if (!count || count > words.size() - p) throw std::invalid_argument("truncated compiled consumer interface");
        const auto op = static_cast<spv::Op>(words[p] & 0xffffu); const auto* args = words.data() + p + 1;
        if (op == spv::Op::OpName && count >= 3) {
            const char* begin = reinterpret_cast<const char*>(args + 1);
            const auto end = std::memchr(begin, 0, (count - 2) * 4);
            if (!end) throw std::invalid_argument("unterminated compiled consumer name");
            names[args[0]] = std::string(begin, static_cast<const char*>(end) - begin);
        } else if ((op == spv::Op::OpTypeInt || op == spv::Op::OpTypeVector || op == spv::Op::OpTypePointer) && count >= 2)
            types.emplace(args[0], Type{op, {args + 1, args + count - 1}});
        else if (op == spv::Op::OpVariable && count >= 4) variables[args[1]] = {args[0], args[2]};
        else if (op == spv::Op::OpDecorate && count >= 3) {
            if (args[1] == uint32_t(spv::Decoration::Flat)) flat.insert(args[0]);
            if (args[1] == uint32_t(spv::Decoration::Location) && count >= 4) locations[args[0]] = args[2];
        }
        p += count;
    }
    uint32_t located = 0;
    for (const auto& [id, variable] : variables) if (variable.storage == uint32_t(direction) && locations.contains(id)) {
        ++located;
        if (names[id] != "vispy_line_consumer_ids" || locations[id] != 0 || !flat.contains(id))
            throw std::invalid_argument("compiled consumer interface must contain only flat original row IDs");
        const auto pointer = types.find(variable.pointer);
        if (pointer == types.end() || pointer->second.op != spv::Op::OpTypePointer || pointer->second.args.size() != 2)
            throw std::invalid_argument("compiled consumer interface pointer type differs");
        const auto vector = types.find(pointer->second.args[1]);
        if (vector == types.end() || vector->second.op != spv::Op::OpTypeVector || vector->second.args.size() != 2 ||
            vector->second.args[1] != 4) throw std::invalid_argument("compiled consumer interface vector type differs");
        const auto scalar = types.find(vector->second.args[0]);
        if (scalar == types.end() || scalar->second.op != spv::Op::OpTypeInt || scalar->second.args != std::vector<uint32_t>{32, 0})
            throw std::invalid_argument("compiled consumer row IDs are not exact uint32");
    }
    if (located != 1) throw std::invalid_argument("compiled consumer interface location count differs");
}

float representable(double value, const char* what, bool preserve_positive_extent = false) {
    // Check the double domain before conversion. Values outside the finite
    // float range must not rely on a platform's out-of-range cast behavior.
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument(std::string("line consumer: unrepresentable ") + what);
    const float result = static_cast<float>(value);
    // Device f32 arithmetic may flush subnormal operands. Nonempty extents
    // must remain positive in that arithmetic; coordinate/depth values may
    // legitimately round to zero and are not subjected to this extent rule.
    if (preserve_positive_extent && value > 0 && result < std::numeric_limits<float>::min())
        throw std::invalid_argument(std::string("line consumer: shader extent underflows ") + what);
    return result;
}

// Deferred coverage invokes user code for helper pixels outside the line.
// Output/private/function writes are discarded or invocation-local. External
// stores, images, atomics and synchronization cannot be made harmless by a
// later discard, and early depth/stencil tests would observe the quad depth.
// Inspect the already validated original SPIR-V, rather than matching words
// in comments or approximating user function bodies.
std::string fragment_context_error(const std::vector<uint32_t>& words) {
    if (words.size() < 5 || words[0] != 0x07230203u) return "original fragment SPIR-V header differs";
    std::unordered_map<uint32_t, spv::StorageClass> pointer_types, pointer_values;
    for (size_t p = 5; p < words.size();) {
        const size_t count = words[p] >> 16;
        if (!count || count > words.size() - p) return "original fragment SPIR-V instruction differs";
        const auto op = static_cast<spv::Op>(words[p] & 0xffffu); const auto* a = words.data() + p + 1;
        if (op == spv::Op::OpTypePointer && count == 4) pointer_types.emplace(a[0], static_cast<spv::StorageClass>(a[1]));
        p += count;
    }
    for (size_t p = 5; p < words.size();) {
        const size_t count = words[p] >> 16;
        const auto op = static_cast<spv::Op>(words[p] & 0xffffu); const auto* a = words.data() + p + 1;
        switch (op) {
        case spv::Op::OpVariable: case spv::Op::OpFunctionParameter:
        case spv::Op::OpAccessChain: case spv::Op::OpInBoundsAccessChain:
        case spv::Op::OpPtrAccessChain: case spv::Op::OpInBoundsPtrAccessChain:
        case spv::Op::OpCopyObject: case spv::Op::OpPhi: case spv::Op::OpSelect:
        case spv::Op::OpLoad: case spv::Op::OpFunctionCall:
            if (count >= 3 && pointer_types.contains(a[0])) pointer_values.emplace(a[1], pointer_types.at(a[0]));
            break;
        default: break;
        }
        p += count;
    }
    for (size_t p = 5; p < words.size();) {
        const size_t count = words[p] >> 16;
        const auto op = static_cast<spv::Op>(words[p] & 0xffffu); const auto* a = words.data() + p + 1;
        if ((op == spv::Op::OpExecutionMode || op == spv::Op::OpExecutionModeId) && count >= 3 &&
            a[1] == static_cast<uint32_t>(spv::ExecutionMode::EarlyFragmentTests))
            return "early_fragment_tests requires true line coverage/depth integration; conservative quad policy remains unsupported";
        if (op == spv::Op::OpStore || op == spv::Op::OpCopyMemory || op == spv::Op::OpCopyMemorySized) {
            if (count < 3 || !pointer_values.contains(a[0])) return "original fragment store pointer is not admitted";
            const auto storage = pointer_values.at(a[0]);
            if (storage != spv::StorageClass::Output && storage != spv::StorageClass::Private && storage != spv::StorageClass::Function)
                return "fragment external storage writes cannot execute outside line coverage";
        }
        if (op == spv::Op::OpImageWrite || (op >= spv::Op::OpAtomicLoad && op <= spv::Op::OpAtomicXor) ||
            op == spv::Op::OpAtomicFlagTestAndSet || op == spv::Op::OpAtomicFlagClear ||
            op == spv::Op::OpAtomicFMinEXT || op == spv::Op::OpAtomicFMaxEXT || op == spv::Op::OpAtomicFAddEXT ||
            op == spv::Op::OpControlBarrier || op == spv::Op::OpMemoryBarrier ||
            op == spv::Op::OpBeginInvocationInterlockEXT || op == spv::Op::OpEndInvocationInterlockEXT)
            return "fragment image/atomic/synchronization side effects cannot execute outside line coverage";
        p += count;
    }
    return {};
}

} // namespace

std::shared_ptr<const GeneratedLineConsumerArtifact> build_generated_line_consumer(
    std::shared_ptr<const LineEvaluatorArtifact> evaluator, const LineConsumerPolicy& policy,
    const LineConsumerLimits& limits) {
    auto result = std::make_shared<GeneratedLineConsumerArtifact>();
    result->evaluator = std::move(evaluator); result->policy = policy;
    const auto started = shader_host_ns();
    struct Timer { GeneratedLineConsumerArtifact& value; uint64_t started;
        ~Timer() { value.timings.total_ns = shader_host_ns() - started; } } timer{*result, started};
    auto fail = [&](const std::string& reason) -> std::shared_ptr<const GeneratedLineConsumerArtifact> {
        result->error = "line consumer: " + reason; return result;
    };
    try {
        if (!result->evaluator || !result->evaluator->ok || !result->evaluator->original || !result->evaluator->original->ok)
            return fail("a compiled evaluator and its exact original are required");
        result->original = result->evaluator->original;
        result->policy_identity = generated_line_consumer_policy_identity(*result->evaluator, policy);
        const bool smooth = policy.coverage == LineCoveragePolicy::SmoothAnalytic;
        if ((policy.sample_count != 1 && policy.sample_count != 4) ||
            (!smooth && policy.coverage != LineCoveragePolicy::AliasedMajorAxis) ||
            policy.coverage_identity != line_coverage_identity(smooth, policy.sample_count))
            return fail("explicit one- or four-sample aliased or analytic-smooth policy required");
        const auto& evaluator_ref = *result->evaluator; const auto& original = *result->original;
        if (original.point_sprites || original.options.line_evaluator) return fail("original line render snapshot required");
        if (const auto error = fragment_context_error(original.spv_frag); !error.empty()) return fail(error);
        for (const auto* source : {&original.source_vertex, &original.source_fragment})
            for (const auto& token : tokens(*source)) if (token.text.rfind(prefix, 0) == 0 || token.text == "VISPY_LINE_CONSUMER_ROW_BYTES")
                return fail("original source collides with the reserved generated namespace");
        validate_line_output_layout(evaluator_ref.output_row_bytes, evaluator_ref.outputs);
        if (!limits.max_storage_buffers_per_stage || evaluator_ref.output_row_bytes > limits.max_storage_binding_bytes ||
            evaluator_ref.output_row_bytes > limits.max_buffer_bytes || limits.max_inter_stage_shader_variables < 1) return fail("actual grants do not admit the two-stage typed row/interface");
        result->parameters_offset = original.uniform_bytes;
        if (result->parameters_offset % 16 || result->parameters_offset > UINT32_MAX - 64u)
            return fail("original UBO plus generated parameter extent overflows");
        result->uniform_bytes = result->parameters_offset + 64;
        if (result->uniform_bytes > limits.max_uniform_binding_bytes || result->uniform_bytes > limits.max_buffer_bytes)
            return fail("paired render UBO exceeds actual grant");
        result->uniforms = original.uniforms;
        result->uniforms.push_back(parameter_uniform("vispy_line_consumer_header", "uvec4", result->parameters_offset));
        result->uniforms.push_back(parameter_uniform("vispy_line_consumer_ranges", "uvec4", result->parameters_offset + 16));
        result->uniforms.push_back(parameter_uniform("vispy_line_consumer_viewport", "vec4", result->parameters_offset + 32));
        result->uniforms.push_back(parameter_uniform("vispy_line_consumer_raster", "vec4", result->parameters_offset + 48));
        result->output_binding = evaluator_ref.output_binding;
        if (!result->output_binding || result->output_binding >= limits.max_bindings_per_group)
            return fail("output binding exceeds actual grant");
        const auto block = uniform_block(result->uniforms);
        auto common = "#define VISPY_LINE_CONSUMER_ROW_BYTES " + std::to_string(evaluator_ref.output_row_bytes) +
            "u\n" + block + storage_block(evaluator_ref) + geometry;
        if (smooth) {
            replace_one(common, "vispy_line_consumer_raster.x < 1.0", "vispy_line_consumer_raster.x <= 0.0");
            replace_one(common, "floor(vispy_line_consumer_raster.x) != vispy_line_consumer_raster.x", "false");
            common += smooth_geometry;
        }
        result->vertex = "#version 450\n" + common + vertex_main;
        std::string fragment = original.fragment;
        if (fragment.rfind("#version 450\n", 0) != 0) return fail("unexpected canonical fragment version header");
        if (original.frag_map.size() != static_cast<size_t>(std::count(fragment.begin(), fragment.end(), '\n')))
            return fail("original fragment diagnostic map differs");
        auto canonical_map = original.frag_map;
        if (!original.uniforms.empty()) {
            const auto old_block = uniform_block(original.uniforms);
            const auto at = fragment.find(old_block);
            if (at == std::string::npos) return fail("original canonical UBO header differs");
            const auto first_line = static_cast<size_t>(std::count(fragment.begin(), fragment.begin() + at, '\n'));
            const auto removed_lines = static_cast<size_t>(std::count(old_block.begin(), old_block.end(), '\n'));
            replace_one(fragment, old_block, "");
            canonical_map.erase(canonical_map.begin() + first_line, canonical_map.begin() + first_line + removed_lines);
        }
        for (const auto& field : evaluator_ref.outputs) {
            if ((field.varying.centroid || field.varying.sample) && policy.sample_count != 4)
                return fail("centroid/sample interpolation requires the explicit four-sample policy");
            replace_one(fragment, varying_declaration(field.varying), private_declaration(field.varying));
        }
        FragmentHelpers helpers;
        fragment = fragment_identifiers(fragment, helpers, policy.depth_output);
        fragment.erase(0, std::string("#version 450\n").size());
        std::string generated_prefix = "#version 450\n";
        if (helpers.query) generated_prefix += "#extension GL_EXT_demote_to_helper_invocation : require\n";
        generated_prefix += common +
            "layout(location = 0) flat in uvec4 vispy_line_consumer_ids;\nvec4 vispy_line_consumer_fragment_coord;\n";
        if (!policy.depth_output) generated_prefix += "float vispy_line_consumer_fragment_depth;\n";
        if (helpers.needed()) generated_prefix += "bool vispy_line_consumer_helper_invocation;\n";
        if (helpers.query) generated_prefix +=
            "bool vispy_line_consumer_query_helper() {\n"
            "    return vispy_line_consumer_helper_invocation || helperInvocationEXT();\n}\n";
        auto suffix = fragment_main(evaluator_ref, helpers, policy.depth_output);
        if (policy.sample_count == 4) {
            // SampleId makes this a sample-rate fragment. On Vulkan FragCoord.xy
            // then identifies the actual raster sample; no sample pattern is
            // assumed or synthesized. The output mask retains just that sample.
            // Keep this before original code so an explicit user sample mask can
            // still narrow coverage, and preserve the deferred kill/derivatives.
            const std::string depth_assignment = policy.depth_output ?
                "    gl_FragDepth = depth;" : "    vispy_line_consumer_fragment_depth = depth;";
            replace_one(suffix, depth_assignment,
                "    gl_SampleMask[0] = int(1u << uint(gl_SampleID));\n" + depth_assignment);
        }
        if (smooth) {
            replace_one(suffix,
                "    bool vispy_line_consumer_covered = vispy_line_consumer_aliased(a, b, pixel, interval.y == 1.0);",
                "    float vispy_line_consumer_coverage = vispy_line_consumer_smooth(pa, pb, pixel);\n"
                "    bool vispy_line_consumer_covered = vispy_line_consumer_coverage > 0.0;");
            replace_one(suffix, "    if (!vispy_line_consumer_covered || !vispy_line_consumer_valid) discard;\n",
                "    if (!vispy_line_consumer_covered || !vispy_line_consumer_valid) discard;\n    " +
                smooth_color_output(fragment) + ".a *= vispy_line_consumer_coverage;\n");
        }
        result->fragment = generated_prefix + fragment + suffix;
        result->vertex_line_map.assign(std::count(result->vertex.begin(), result->vertex.end(), '\n'), 0);
        result->fragment_line_map.assign(std::count(generated_prefix.begin(), generated_prefix.end(), '\n'), 0);
        // Preserve composer lines after the exact generated UBO/version removal.
        result->fragment_line_map.insert(result->fragment_line_map.end(), canonical_map.begin() + 1, canonical_map.end());
        result->fragment_line_map.insert(result->fragment_line_map.end(), std::count(suffix.begin(), suffix.end(), '\n'), 0);
        if (result->fragment_line_map.size() != static_cast<size_t>(std::count(result->fragment.begin(), result->fragment.end(), '\n')))
            return fail("generated fragment diagnostic map differs");
        result->identity = result->policy_identity + ";consumer=typed-storage-both-stages-v2;fragment=private-inputs-AST-initializers-once;"
            "helper=logical-or-current-native-query-v1;finite=ieee754-signmask-unsigned-v1;product=topology-bounded-v1;coordinate=gl-window-present-y-v1;"
            "mapping=whole-or-local-chunk-original-primitive-v1;";
        const std::string* const identity_parts[] = {&policy.coverage_identity, &result->vertex, &result->fragment};
        for (const auto* text : identity_parts)
            result->identity += std::to_string(text->size()) + ':' + *text;
        result->cache_key = shader_identity_digest(result->identity);
        auto compiled = compile_line_consumer_glsl(result->vertex, result->fragment);
        result->log = compiled.stages.log; result->relocated_fragment_initializers = compiled.relocated_fragment_initializers;
        result->timings.parse_ns = compiled.stages.parse_ns; result->timings.link_ns = compiled.stages.link_ns;
        result->timings.spirv_ns = compiled.stages.spirv_ns; result->timings.reflect_ns = compiled.stages.resource_reflect_ns;
        result->timings.parse_calls = compiled.stages.parse_calls; result->timings.link_calls = compiled.stages.link_calls;
        result->timings.spirv_stages = compiled.stages.spirv_stages;
        if (!compiled.stages.ok) return fail("actual generated parse/link/SPIR-V failed: " + result->log);
        result->vertex_spv = std::move(compiled.stages.vertex.words); result->fragment_spv = std::move(compiled.stages.fragment.words);
        result->resource_usage = std::move(compiled.stages.resource_usage);
        verify_interface(result->vertex_spv, spv::StorageClass::Output);
        verify_interface(result->fragment_spv, spv::StorageClass::Input);
        std::string error;
        if (!reflect_storage_rows(result->vertex_spv, "VispyLineConsumerRows", result->vertex_rows, error) ||
            !reflect_storage_rows(result->fragment_spv, "VispyLineConsumerRows", result->fragment_rows, error)) return fail(error);
        verify_rows(evaluator_ref, result->vertex_rows); verify_rows(evaluator_ref, result->fragment_rows);
        auto vertex_uniforms = result->uniforms; uint32_t vertex_bytes = result->uniform_bytes;
        if (!reflect_uniform_layout(result->vertex_spv, vertex_uniforms, vertex_bytes, error) ||
            !reflect_uniform_layout(result->fragment_spv, result->uniforms, result->uniform_bytes, error) ||
            vertex_bytes != result->uniform_bytes) return fail("compiled paired UBO layout differs: " + error);
        result->uniform_stage_mask = resource_stages(result->resource_usage, 0);
        if (result->uniform_stage_mask != 3 || resource_stages(result->resource_usage, result->output_binding) != 3)
            return fail("actual UBO/storage stages do not include both render stages");
        std::unordered_set<uint32_t> bindings;
        for (const auto& resource : result->resource_usage) {
            if (resource.binding >= limits.max_bindings_per_group) return fail("reflected live binding exceeds actual grant");
            bindings.insert(resource.binding);
        }
        if (bindings.size() > limits.max_bindings_per_group) return fail("reflected live resource count exceeds actual grant");
        for (auto sampler : original.samplers) {
            sampler.texture_stage_mask = resource_stages(result->resource_usage, sampler.texture_binding);
            sampler.sampler_stage_mask = resource_stages(result->resource_usage, sampler.sampler_binding);
            if ((sampler.texture_stage_mask | sampler.sampler_stage_mask) & 1u)
                return fail("generated vertex unexpectedly reads an original sampler");
            if (sampler.texture_stage_mask || sampler.sampler_stage_mask) result->samplers.push_back(std::move(sampler));
        }
        result->vertex_storage_bindings = result->fragment_storage_bindings = 1;
        result->internal_inter_stage_locations = 1; result->internal_inter_stage_components = 4;
        result->ok = true; return result;
    } catch (const std::exception& e) { return fail(e.what()); }
}

std::shared_ptr<const LineConsumerArtifact> build_line_consumer(
    std::shared_ptr<const LineEvaluatorArtifact> evaluator, const LineConsumerPolicy& policy,
    const LineConsumerLimits& limits) {
    return build_generated_line_consumer(std::move(evaluator), policy, limits);
}

GeneratedLineConsumerDraw plan_generated_line_consumer_draw(
    const GeneratedLineConsumerArtifact& artifact, const lines::LineConsumerSelection& selection,
    lines::LineDrawSlice slice, lines::State state, lines::LineConsumerViewport viewport,
    double framebuffer_height, double depth_near, double depth_far, const LineConsumerLimits& limits) {
    using namespace line_consumer_detail;
    if (!artifact.ok || !artifact.evaluator || artifact.original != artifact.evaluator->original)
        throw std::invalid_argument("line consumer: compiled exact original/evaluator pair required");
    lines::validate_line_draw_slice(selection, slice); state = lines::state(state.width, state.smooth);
    const bool smooth = artifact.policy.coverage == LineCoveragePolicy::SmoothAnalytic;
    if (state.smooth != smooth || (!smooth && artifact.policy.coverage != LineCoveragePolicy::AliasedMajorAxis) ||
        (artifact.policy.sample_count != 1 && artifact.policy.sample_count != 4) ||
        artifact.policy.coverage_identity != line_coverage_identity(smooth, artifact.policy.sample_count))
        throw std::invalid_argument("line consumer: runtime smoothing/samples must match the compiled coverage policy");
    GeneratedLineConsumerDraw draw;
    draw.parameters.viewport = {representable(viewport.x, "viewport x"), representable(viewport.y, "viewport y"),
        representable(viewport.width, "viewport width", true), representable(viewport.height, "viewport height", true)};
    if (viewport.width < 0 || viewport.height < 0 || framebuffer_height <= 0 || depth_near < 0 || depth_near > 1 ||
        depth_far < 0 || depth_far > 1) throw std::invalid_argument("line consumer: invalid viewport/framebuffer/depth range");
    const auto rounded_width = smooth ? state.width : std::max(1.0, std::floor(state.width + 0.5));
    if (rounded_width > 16777216.0) throw std::length_error("line consumer: aliased width exceeds exact shader integer range");
    draw.parameters.raster = {representable(rounded_width, "width", true), representable(framebuffer_height, "framebuffer height", true),
        representable(depth_near, "depth near"), representable(depth_far, "depth far")};
    if (!slice.segment_count || !viewport.width || !viewport.height) return draw;
    const auto& rows = selection.rows();
    if (slice.first_segment > UINT32_MAX || slice.segment_count > INT32_MAX || rows.size() > UINT32_MAX ||
        rows.per_instance() > UINT32_MAX) throw std::length_error("line consumer: draw/row addresses exceed shader range");
    const auto mode = selection.primitive();
    const auto per_instance = mode == lines::Mode::List ? rows.per_instance() / 2 :
        mode == lines::Mode::Strip ? rows.per_instance() - 1 : rows.per_instance();
    if (!per_instance || per_instance > UINT32_MAX || rows.segment_count() > UINT32_MAX)
        throw std::length_error("line consumer: total segment address exceeds uint32");
    draw.endpoint_bytes = multiply(rows.size(), artifact.evaluator->output_row_bytes, "line consumer: output size overflow");
    draw.render_uniform_bytes = artifact.uniform_bytes;
    if (draw.endpoint_bytes > std::min(limits.max_storage_binding_bytes, limits.max_buffer_bytes) ||
        draw.render_uniform_bytes > std::min(limits.max_uniform_binding_bytes, limits.max_buffer_bytes) ||
        limits.max_storage_buffers_per_stage < 1 || limits.max_inter_stage_shader_variables < 1 ||
        artifact.output_binding >= limits.max_bindings_per_group)
        throw std::length_error("line consumer: draw exceeds actual grants; partitioning is still open");
    draw.parameters.header = {kGeneratedLineConsumerAbi, static_cast<uint32_t>(rows.size()), artifact.evaluator->output_row_bytes,
        mode == lines::Mode::List ? 0u : mode == lines::Mode::Strip ? 1u : 2u};
    draw.parameters.ranges = {static_cast<uint32_t>(rows.per_instance()), static_cast<uint32_t>(per_instance),
        static_cast<uint32_t>(slice.first_segment), static_cast<uint32_t>(slice.segment_count)};
    draw.vertex_count = 6; draw.instance_count = static_cast<uint32_t>(slice.segment_count); return draw;
}

GeneratedLineConsumerDraw plan_generated_line_consumer_chunk_draw(
    const GeneratedLineConsumerArtifact& artifact, uint32_t new_rows, uint32_t output_rows,
    uint32_t segment_count, bool previous, bool closing, bool list,
    uint32_t original_first_segment, lines::State state, lines::LineConsumerViewport viewport,
    double framebuffer_height, double depth_near, double depth_far, const LineConsumerLimits& limits) {
    if (list && (previous || closing))
        throw std::invalid_argument("line consumer: list chunk cannot contain strip seams");
    if (!segment_count) {
        if (new_rows || output_rows || previous || closing)
            throw std::invalid_argument("line consumer: empty chunk must have no endpoint rows or seams");
    } else {
        if (segment_count > INT32_MAX || segment_count - 1u > UINT32_MAX - original_first_segment)
            throw std::length_error("line consumer: chunk segment address exceeds shader range");
        const uint64_t expected_rows = list ? uint64_t(segment_count) * 2 : uint64_t(segment_count) + 1;
        const uint64_t seams = uint64_t(previous) + uint64_t(closing);
        if (expected_rows != output_rows || expected_rows - seams != new_rows)
            throw std::invalid_argument("line consumer: chunk endpoint/seam shape differs from segment count");
    }
    // A constant-sized synthetic strip has the same local output allocation
    // and at least this many segments. Reuse all original pair, policy, float,
    // actual-grant and no-op validation before replacing only the row mapping.
    const lines::LineConsumerSelection local(lines::Mode::Strip, lines::Selection{0, output_rows, 1});
    auto draw = plan_generated_line_consumer_draw(artifact, local, {0, segment_count}, state, viewport,
        framebuffer_height, depth_near, depth_far, limits);
    if (!draw.instance_count) return draw;
    draw.parameters.header = {kGeneratedLineConsumerAbi, output_rows, artifact.evaluator->output_row_bytes,
        3u + uint32_t(previous) + 2u * uint32_t(closing) + 4u * uint32_t(list)};
    draw.parameters.ranges = {new_rows, original_first_segment, 0, segment_count};
    return draw;
}

size_t GeneratedLineConsumerArtifact::storage_bytes() const {
    // Artifact-owned capacities only. Original/evaluator are separately
    // deduplicated graph owners; no allocator/driver/physical-memory claim.
    size_t bytes = sizeof(*this) + (vertex_spv.capacity() + fragment_spv.capacity()) * sizeof(uint32_t) +
        (vertex_line_map.capacity() + fragment_line_map.capacity()) * sizeof(int) +
        uniforms.capacity() * sizeof(NormUniform) + samplers.capacity() * sizeof(NormSampler) +
        resource_usage.capacity() * sizeof(SpvResourceUsage);
    for (const auto* text : {&identity, &policy_identity, &cache_key, &vertex, &fragment, &log, &error, &policy.coverage_identity}) bytes += text->capacity() + 1;
    for (const auto& u : uniforms) bytes += u.name.capacity() + u.type.capacity() + u.storage_type.capacity() + 3;
    for (const auto& s : samplers) bytes += s.name.capacity() + s.dim.capacity() + 2;
    for (const auto* layout : {&vertex_rows, &fragment_rows}) {
        bytes += layout->members.capacity() * sizeof(SpvStorageMember);
        for (const auto& member : layout->members) bytes += member.name.capacity() + 1;
    }
    return bytes;
}

} // namespace vispy::shader
