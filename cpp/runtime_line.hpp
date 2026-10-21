#pragma once

// Portable line selection, compute-input packing and clipping semantics.
// Shader execution, raster coverage, WebGPU z conversion and graphics API
// operations stay in the compiler/runtime paths.
// GL 4.6 core sections 13.6, 13.7.1 and 14.5.1:
// https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace vispy::lines {

enum class Mode { List, Strip, Loop };

inline Mode mode(std::string_view name) {
    if (name == "lines") return Mode::List;
    if (name == "line_strip") return Mode::Strip;
    if (name == "line_loop") return Mode::Loop;
    throw std::invalid_argument("lines: unsupported primitive mode");
}

struct State { double width = 1; bool smooth = false; };
inline State state(double width, bool smooth) {
    if (!std::isfinite(width) || width <= 0)
        throw std::invalid_argument("lines: snapshot width must be finite and positive");
    return {width, smooth};
}

struct Selection {
    uint64_t first = 0, count = 0, instances = 1;
    // Borrowed immutable native-endian capture bytes, never an owning cache.
    // The capture owner MUST outlive the table and every at() call. With indices,
    // first selects an index element (not a byte offset); callers may instead
    // supply an already-sliced span and first=0. Unselected prefix/suffix bytes
    // are not decoded. Without indices, first is the original vertex identity.
    std::span<const uint8_t> indices{};
    uint8_t index_bytes = 0;
};

struct Segment {
    uint32_t first = 0, last = 0, provoking = 0, instance = 0;
    uint64_t ordinal = 0;  // Within one original instance.
};

inline uint32_t selected_vertex(const Selection& selection, uint64_t ordinal) {
    if (ordinal >= selection.count)
        throw std::out_of_range("lines: endpoint ordinal exceeds original selection");
    if (!selection.index_bytes) {
        if (selection.first > UINT32_MAX || ordinal > UINT32_MAX - selection.first)
            throw std::overflow_error("lines: original vertex identity exceeds uint32");
        return static_cast<uint32_t>(selection.first + ordinal);
    }
    if (selection.index_bytes != 1 && selection.index_bytes != 2 && selection.index_bytes != 4)
        throw std::invalid_argument("lines: index width must be one, two or four bytes");
    const uint64_t available = selection.indices.size() / selection.index_bytes;
    if (selection.first > available || ordinal >= available - selection.first)
        throw std::out_of_range("lines: endpoint exceeds immutable index capture");
    const auto* source = selection.indices.data() + static_cast<size_t>((selection.first + ordinal) * selection.index_bytes);
    if (selection.index_bytes == 1) return *source;
    if (selection.index_bytes == 2) {
        uint16_t value; std::memcpy(&value, source, 2); return value;
    }
    uint32_t value; std::memcpy(&value, source, 4); return value;
}

// Constant-sized, O(1)-construction/random-access original segment table.
// No unconditional index scan or vector proportional to DRAW size.
class Segments {
public:
    explicit Segments(Mode primitive, Selection selection,
                      uint64_t maximum_segments = UINT64_MAX)
        : mode_(primitive), selection_(selection) {
        if (primitive != Mode::List && primitive != Mode::Strip && primitive != Mode::Loop)
            throw std::invalid_argument("lines: invalid primitive enum");
        constexpr uint64_t identities = uint64_t(UINT32_MAX) + 1;
        if (selection.instances > identities)
            throw std::overflow_error("lines: original instance identity exceeds uint32");
        if (selection.index_bytes) {
            if (selection.index_bytes != 1 && selection.index_bytes != 2 && selection.index_bytes != 4)
                throw std::invalid_argument("lines: index width must be one, two or four bytes");
            const uint64_t available = selection.indices.size() / selection.index_bytes;
            if (selection.first > available || selection.count > available - selection.first)
                throw std::out_of_range("lines: selected index prefix exceeds immutable capture");
        } else if (selection.count &&
                   (selection.first > UINT32_MAX || selection.count - 1 > UINT32_MAX - selection.first)) {
            throw std::overflow_error("lines: original vertex identity exceeds uint32");
        }
        per_instance_ = primitive == Mode::List ? selection.count / 2 :
                        selection.count < 2 ? 0 : primitive == Mode::Strip ? selection.count - 1 : selection.count;
        if (per_instance_ && selection.instances > UINT64_MAX / per_instance_)
            throw std::overflow_error("lines: segment count overflows uint64");
        total_ = per_instance_ * selection.instances;
        if (total_ > maximum_segments)
            throw std::length_error("lines: segment count exceeds caller budget");
    }
    uint64_t size() const { return total_; }
    uint64_t per_instance() const { return per_instance_; }
    Segment at(uint64_t index) const {
        if (index >= total_) throw std::out_of_range("lines: segment ordinal exceeds DRAW");
        const uint64_t instance = index / per_instance_, ordinal = index % per_instance_;
        const uint64_t first = mode_ == Mode::List ? ordinal * 2 : ordinal;
        const uint64_t last = mode_ == Mode::Loop && ordinal == selection_.count - 1 ? 0 : first + 1;
        const uint32_t a = vertex(first), b = vertex(last);
        // LAST convention: closing loop edge is last source vertex -> first
        // source vertex, so its flat output comes from that original first.
        return {a, b, b, static_cast<uint32_t>(instance), ordinal};
    }
private:
    uint32_t vertex(uint64_t ordinal) const {
        return selected_vertex(selection_, ordinal);
    }
    Mode mode_;
    Selection selection_;
    uint64_t per_instance_ = 0, total_ = 0;
};

struct Endpoint { uint32_t vertex = 0, instance = 0; };
struct SegmentRows { uint32_t first = 0, last = 0, provoking = 0; };

// One isolated invocation per selected endpoint occurrence and instance. Strip
// adjacency and loop closure reference the same output row, never another call
// to mutable vertex main. Repeated index values keep their original occurrences.
class EndpointRows {
public:
    EndpointRows(Mode primitive, Selection selection, uint64_t maximum_rows = UINT32_MAX)
        : primitive_(primitive), selection_(selection), segments_(primitive, selection) {
        per_instance_ = segments_.per_instance() == 0 ? 0 :
                        primitive == Mode::List ? selection.count - selection.count % 2 : selection.count;
        if (per_instance_ && selection.instances > UINT64_MAX / per_instance_)
            throw std::overflow_error("lines: endpoint row count overflows uint64");
        total_ = per_instance_ * selection.instances;
        if (total_ > std::min<uint64_t>(maximum_rows, UINT32_MAX))
            throw std::length_error("lines: endpoint rows exceed compute input count/budget");
    }
    uint64_t size() const { return total_; }
    uint64_t per_instance() const { return per_instance_; }
    uint64_t segment_count() const { return segments_.size(); }
    Endpoint at(uint64_t row) const {
        if (row >= total_) throw std::out_of_range("lines: endpoint row exceeds DRAW");
        return {selected_vertex(selection_, row % per_instance_), static_cast<uint32_t>(row / per_instance_)};
    }
    SegmentRows segment_rows(uint64_t segment) const {
        if (segment >= segments_.size()) throw std::out_of_range("lines: segment row reference exceeds DRAW");
        const uint64_t instance = segment / segments_.per_instance();
        const uint64_t ordinal = segment % segments_.per_instance();
        const uint64_t first = primitive_ == Mode::List ? ordinal * 2 : ordinal;
        const uint64_t last = primitive_ == Mode::Loop && ordinal == selection_.count - 1 ? 0 : first + 1;
        const uint64_t base = instance * per_instance_;
        return {static_cast<uint32_t>(base + first), static_cast<uint32_t>(base + last),
                static_cast<uint32_t>(base + last)};
    }
private:
    Mode primitive_;
    Selection selection_;
    Segments segments_;
    uint64_t per_instance_ = 0, total_ = 0;
};

// Recreate borrowed tables from the owned, immutable index revision on demand.
// Never retain a span into a temporary conversion or a replaced Program owner.
template<class IndexRevision> struct CapturedSelection {
    Mode primitive = Mode::List;
    State state;
    uint64_t first = 0, count = 0, instances = 1;
    std::shared_ptr<const IndexRevision> index;
    uint8_t index_bytes = 0;
    Selection selection() const {
        if (bool(index) != bool(index_bytes))
            throw std::invalid_argument("lines: captured index owner/width differs");
        Selection result{first, count, instances};
        if (index) { result.indices = index->cpu; result.index_bytes = index_bytes; }
        return result;
    }
    Segments segments(uint64_t maximum = UINT64_MAX) const { return Segments(primitive, selection(), maximum); }
    EndpointRows endpoints(uint64_t maximum = UINT32_MAX) const { return EndpointRows(primitive, selection(), maximum); }
};

inline constexpr uint32_t endpoint_input_abi = 1;
inline constexpr uint32_t endpoint_header_words = 4;
struct EndpointInputLayout {
    std::vector<uint32_t> attribute_words;
    std::vector<uint32_t> word_offsets;
    uint32_t stride_words = 2;  // Exact original uint32 vertex and instance IDs.
};
inline EndpointInputLayout endpoint_input_layout(std::span<const uint32_t> attribute_words) {
    EndpointInputLayout result;
    uint64_t stride = 2;
    for (uint32_t words : attribute_words) {
        if (!words || words > UINT32_MAX - stride)
            throw std::length_error("lines: endpoint input field/stride exceeds ABI");
        result.word_offsets.push_back(static_cast<uint32_t>(stride));
        result.attribute_words.push_back(words);
        stride += words;
    }
    result.stride_words = static_cast<uint32_t>(stride);
    return result;
}
struct EndpointSource {
    std::span<const uint8_t> bytes;
    uint64_t offset = 0, stride = 0, divisor = 0;
    uint32_t words = 0;
    std::string_view name;
};

// All source reads and the whole header+payload allocation are proved before
// allocating. Raw components preserve signed/unsigned/float bits; only the
// evaluator interprets their declared shader types. Constant stride zero and
// instance divisors are resolved independently of the original vertex ID.
template<class Rows>
inline std::vector<uint8_t> pack_endpoint_inputs(const Rows& rows,
        std::span<const EndpointSource> sources, const EndpointInputLayout& layout,
        uint64_t maximum_bytes) {
    if (layout.attribute_words.size() != sources.size() || layout.word_offsets.size() != sources.size())
        throw std::invalid_argument("lines: endpoint input layout/source count differs");
    uint64_t stride = 2;
    for (size_t field = 0; field < sources.size(); ++field) {
        if (!sources[field].words || sources[field].words != layout.attribute_words[field] ||
            layout.word_offsets[field] != stride || sources[field].words > UINT32_MAX - stride)
            throw std::invalid_argument("lines: endpoint input layout/source field differs");
        stride += sources[field].words;
    }
    if (stride != layout.stride_words)
        throw std::invalid_argument("lines: endpoint input row stride differs");
    constexpr uint64_t header_bytes = endpoint_header_words * sizeof(uint32_t);
    const uint64_t row_bytes = stride * sizeof(uint32_t);
    const uint64_t bound = std::min<uint64_t>(maximum_bytes, std::numeric_limits<size_t>::max());
    if (bound < header_bytes || rows.size() > (bound - header_bytes) / row_bytes)
        throw std::length_error("lines: endpoint input exceeds granted storage/allocation size");
    // Both indexing and OpArrayLength use uint32 words. The total length must
    // remain representable, including the header, even with larger host grants.
    if (rows.size() > (uint64_t(UINT32_MAX) - endpoint_header_words) / stride)
        throw std::length_error("lines: endpoint input uint word address exceeds ABI");
    auto address = [&](const EndpointSource& source, uint64_t element) -> size_t {
        if (source.offset > source.bytes.size() ||
            (source.stride && element > (source.bytes.size() - source.offset) / source.stride))
            throw std::out_of_range("ATTRIBUTE " + std::string(source.name) + ": line endpoint exceeds source revision");
        const uint64_t start = source.offset + element * source.stride;
        if (uint64_t(source.words) * sizeof(uint32_t) > source.bytes.size() - start)
            throw std::out_of_range("ATTRIBUTE " + std::string(source.name) + ": line endpoint payload exceeds source revision");
        return static_cast<size_t>(start);
    };
    if (rows.size()) {
        uint32_t maximum_vertex = 0;
        for (uint64_t row = 0; row < rows.per_instance(); ++row)
            maximum_vertex = std::max(maximum_vertex, rows.at(row).vertex);
        const uint64_t last_instance = rows.at(rows.size() - 1).instance;
        for (const auto& source : sources)
            address(source, source.divisor ? last_instance / source.divisor : maximum_vertex);
    }
    std::vector<uint8_t> result(static_cast<size_t>(header_bytes + rows.size() * row_bytes));
    const uint32_t header[] = {static_cast<uint32_t>(rows.size()), endpoint_input_abi, layout.stride_words, 0};
    std::memcpy(result.data(), header, sizeof(header));
    for (uint64_t row = 0; row < rows.size(); ++row) {
        const auto endpoint = rows.at(row);
        const uint32_t identity[] = {endpoint.vertex, endpoint.instance};
        auto* destination = result.data() + static_cast<size_t>(header_bytes + row * row_bytes);
        std::memcpy(destination, identity, sizeof(identity));
        for (size_t field = 0; field < sources.size(); ++field) {
            const auto& source = sources[field];
            const uint64_t element = source.divisor ? endpoint.instance / source.divisor : endpoint.vertex;
            std::memcpy(destination + uint64_t(layout.word_offsets[field]) * sizeof(uint32_t),
                        source.bytes.data() + address(source, element), uint64_t(source.words) * sizeof(uint32_t));
        }
    }
    return result;
}

using Position = std::array<double, 4>;
enum class ClipStatus { Visible, Outside, BehindEye, Degenerate, ZeroW, NonFinite, PrecisionLoss };
struct Clip {
    ClipStatus status = ClipStatus::Outside;
    double begin = 0, end = 1;  // P(t) = (1-t)*original_a + t*original_b.
    Position first{}, last{};
    bool visible() const { return status == ClipStatus::Visible; }
};

inline bool finite(const Position& point) {
    return std::all_of(point.begin(), point.end(), [](double value) { return std::isfinite(value); });
}
inline Position position(const Position& a, const Position& b, double t) {
    Position result;
    for (size_t n = 0; n < result.size(); ++n) result[n] = std::lerp(a[n], b[n], t);
    return result;
}

// Closed GL homogeneous clip volume: -w <= x,y,z <= w. The caller must keep
// original evaluated endpoint/flat outputs; clipped vertices do not invoke the
// user evaluator again. A WebGPU depth transform belongs to a subsequent stage.
inline Clip clip(const Position& a, const Position& b) {
    Clip result;
    if (!finite(a) || !finite(b)) { result.status = ClipStatus::NonFinite; return result; }
    if (a[3] < 0 && b[3] < 0) { result.status = ClipStatus::BehindEye; return result; }
    double scale = 0;
    for (size_t n = 0; n < 4; ++n) scale = std::max({scale, std::abs(a[n]), std::abs(b[n])});
    if (!scale) { result.status = ClipStatus::ZeroW; return result; }
    Position x{}, y{};
    for (size_t n = 0; n < 4; ++n) {
        x[n] = a[n] / scale; y[n] = b[n] / scale;
        if ((a[n] && !x[n]) || (b[n] && !y[n])) {
            result.status = ClipStatus::PrecisionLoss; return result;
        }
    }
    // Common normalization prevents overflow of signed plane sums/differences.
    for (size_t axis = 0; axis < 3; ++axis) for (double sign : {-1., 1.}) {
        const double da = x[3] + sign * x[axis], db = y[3] + sign * y[axis];
        if (da < 0 && db < 0) return result;
        if (da < 0 || db < 0) {
            const double crossing = da / (da - db);
            if (da < 0) result.begin = std::max(result.begin, crossing);
            else result.end = std::min(result.end, crossing);
            if (result.begin > result.end) return result;
        }
    }
    result.first = position(a, b, result.begin);
    result.last = position(a, b, result.end);
    if (!finite(result.first) || !finite(result.last)) { result.status = ClipStatus::NonFinite; return result; }
    if (result.first[3] == 0 || result.last[3] == 0) { result.status = ClipStatus::ZeroW; return result; }
    if (result.first[3] < 0 || result.last[3] < 0) { result.status = ClipStatus::BehindEye; return result; }
    const double ax = result.first[0] / result.first[3], ay = result.first[1] / result.first[3];
    const double bx = result.last[0] / result.last[3], by = result.last[1] / result.last[3];
    result.status = result.begin == result.end || (ax == bx && ay == by) ?
                    ClipStatus::Degenerate : ClipStatus::Visible;
    return result;
}

struct ClippedSegment { Segment original; Clip geometry; };
inline ClippedSegment clip_segment(Segment original, const Position& a, const Position& b) {
    return {original, clip(a, b)};  // Preserve provoking identity, including outside-clipped LAST.
}

inline std::array<double, 2> weights(double w0, double w1) {
    if (!std::isfinite(w0) || !std::isfinite(w1))
        throw std::invalid_argument("lines: interpolation weights must be finite");
    if (!w0 || !w1) throw std::domain_error("lines: original endpoint projection has zero w");
    const double scale = std::max(std::abs(w0), std::abs(w1));
    const std::array<double, 2> result{w0 / scale, w1 / scale};
    if (!result[0] || !result[1]) throw std::range_error("lines: weight ratio underflows finite precision");
    return result;
}

// Original-endpoint screen parameter for noperspective clipping. With opposite
// signs it may lie outside [0,1]; it is valid only at a positive-w clipped point.
inline double screen_parameter(double t, double w0, double w1) {
    if (!std::isfinite(t) || t < 0 || t > 1)
        throw std::invalid_argument("lines: homogeneous parameter must be in [0,1]");
    const auto w = weights(w0, w1);
    const double denominator = std::lerp(w[0], w[1], t);
    if (denominator <= 0) throw std::domain_error("lines: interpolated point is at or behind the eye");
    const double q = t * w[1] / denominator;
    if (!std::isfinite(q)) throw std::range_error("lines: screen parameter is not representable");
    return q;
}

// Inverse for perspective reconstruction: t=q*w0/((1-q)*w1+q*w0).
inline double homogeneous_parameter(double q, double w0, double w1) {
    if (!std::isfinite(q)) throw std::invalid_argument("lines: screen parameter must be finite");
    const auto w = weights(w0, w1);
    const double denominator = std::lerp(w[1], w[0], q);
    if (!std::isfinite(denominator) || !denominator)
        throw std::domain_error("lines: inverse projective parameter is singular");
    const double t = q * w[0] / denominator;
    if (!std::isfinite(t) || t < 0 || t > 1)
        throw std::domain_error("lines: inverse parameter is outside original segment");
    if (std::lerp(w[0], w[1], t) <= 0)
        throw std::domain_error("lines: inverse point is at or behind the eye");
    return t;
}

}  // namespace vispy::lines
