#pragma once

#include "runtime_line.hpp"

namespace vispy::lines::batches {

struct Limits {
    uint64_t max_new_rows = 0;
    uint64_t max_output_rows = 0;
    uint64_t max_segments_per_chunk = 0;
    uint64_t max_chunks = 0;
    uint64_t max_control_bytes = 0;
};

inline uint64_t add(uint64_t a, uint64_t b) {
    if (b > UINT64_MAX - a) throw std::overflow_error("line batches: checked addition overflow");
    return a + b;
}
inline uint64_t multiply(uint64_t a, uint64_t b) {
    if (a && b > UINT64_MAX / a) throw std::overflow_error("line batches: checked multiplication overflow");
    return a * b;
}
inline uint64_t ceil_div(uint64_t a, uint64_t b) {
    if (!b) throw std::length_error("line batches: zero chunk capacity");
    return a / b + (a % b != 0);
}

struct Chunk {
    uint64_t number = 0, instance = 0, first_segment = 0, segment_count = 0;
    uint64_t first_new_ordinal = 0, new_rows = 0, output_rows = 0;
    bool previous = false, closing = false;
    uint64_t previous_chunk = 0, head_chunk = 0;
    uint32_t previous_source_row = 0, head_source_row = 0;
    Mode primitive = Mode::List;

    SegmentRows segment_rows(uint64_t local) const {
        if (local >= segment_count)
            throw std::out_of_range("line batches: local segment exceeds chunk");
        if (primitive == Mode::List) {
            const auto first = static_cast<uint32_t>(local * 2);
            return {first, first + 1, first + 1};
        }
        const uint64_t seam = previous ? 1 : 0;
        const uint64_t first = previous && local == 0 ? new_rows : local - seam;
        const uint64_t last = closing && local + 1 == segment_count ? new_rows + seam : local + 1 - seam;
        return {static_cast<uint32_t>(first), static_cast<uint32_t>(last), static_cast<uint32_t>(last)};
    }
};

class Plan {
public:
    Mode primitive() const { return primitive_; }
    const Selection& selection() const { return selection_; }
    const Limits& limits() const { return limits_; }
    uint64_t chunk_count() const { return chunks_; }
    uint64_t size() const { return chunks_; }
    uint64_t chunks_per_instance() const { return per_instance_chunks_; }
    uint64_t segment_count() const { return segments_; }
    uint64_t segments_per_instance() const { return per_instance_segments_; }
    uint64_t endpoint_rows_per_instance() const { return per_instance_rows_; }
    uint64_t control_bytes() const { return segments_ ? sizeof(Plan) : 0; }

    Chunk chunk(uint64_t number) const {
        auto result = scalar_chunk(number);
        if (result.previous) {
            const auto prior = scalar_chunk(number - 1);
            result.previous_source_row = prior.segment_rows(prior.segment_count - 1).last;
        }
        return result;
    }

private:
    Mode primitive_ = Mode::List;
    Selection selection_;
    Limits limits_;
    uint64_t per_instance_segments_ = 0, per_instance_rows_ = 0, segments_ = 0;
    uint64_t first_capacity_ = 0, later_capacity_ = 0;
    uint64_t per_instance_chunks_ = 0, chunks_ = 0;

    Chunk scalar_chunk(uint64_t number) const {
        if (number >= chunks_) throw std::out_of_range("line batches: chunk ordinal exceeds plan");
        Chunk result;
        result.number = number;
        result.instance = number / per_instance_chunks_;
        result.primitive = primitive_;
        const uint64_t local = number % per_instance_chunks_;
        const uint64_t first = local ? add(first_capacity_, multiply(local - 1, later_capacity_)) : 0;
        const bool final = local + 1 == per_instance_chunks_;
        const uint64_t capacity = local ? later_capacity_ : first_capacity_;
        result.segment_count = final ? per_instance_segments_ - first : capacity;
        result.first_segment = add(multiply(result.instance, per_instance_segments_), first);
        result.previous = primitive_ != Mode::List && local != 0;
        result.closing = primitive_ == Mode::Loop && final;
        result.first_new_ordinal = primitive_ == Mode::List ? first * 2 : first + (result.previous ? 1 : 0);
        result.new_rows = primitive_ == Mode::List ? result.segment_count * 2 :
            result.segment_count + (result.previous ? 0 : 1) - (result.closing ? 1 : 0);
        result.output_rows = result.new_rows + (result.previous ? 1 : 0) + (result.closing ? 1 : 0);
        if (result.previous) result.previous_chunk = number - 1;
        if (result.closing) result.head_chunk = number - local;
        return result;
    }

    friend Plan plan(Mode, Selection, Limits);
};

// No whole EndpointRows or chunk vector is formed. The index span is borrowed
// only while preparing immutable owning chunks; never retain this Plan in a
// producer cache without retaining its immutable index revision as well.
inline Plan plan(Mode primitive, Selection selection, Limits limits) {
    const Segments segments(primitive, selection);
    Plan result;
    result.primitive_ = primitive;
    result.selection_ = selection;
    result.limits_ = limits;
    result.per_instance_segments_ = segments.per_instance();
    result.segments_ = segments.size();
    result.per_instance_rows_ = !segments.per_instance() ? 0 :
        primitive == Mode::List ? selection.count - selection.count % 2 : selection.count;
    if (!segments.size()) return result;
    // Fragment/diagnostic segment identity is the original flattened ordinal.
    // UINT32_MAX itself is legal; only the following ordinal is refused.
    if (segments.size() - 1 > UINT32_MAX)
        throw std::length_error("line batches: original flat segment identity exceeds uint32");
    if (sizeof(Plan) > limits.max_control_bytes)
        throw std::length_error("line batches: explicit plan control-byte budget exceeded");
    const uint64_t fresh = std::min(limits.max_new_rows, uint64_t(UINT32_MAX));
    const uint64_t output = std::min(limits.max_output_rows, uint64_t(UINT32_MAX));
    const uint64_t calls = std::min(limits.max_segments_per_chunk, uint64_t(INT32_MAX));
    if (primitive == Mode::List) {
        result.first_capacity_ = result.later_capacity_ = std::min({calls, fresh / 2, output / 2});
        result.per_instance_chunks_ = ceil_div(segments.per_instance(), result.first_capacity_);
    } else {
        if (fresh < 2 || output < 2 || !calls)
            throw std::length_error("line batches: first segment needs two new output rows");
        result.first_capacity_ = std::min({calls, fresh - 1, output - 1});
        result.later_capacity_ = std::min({calls, fresh, output - 1});
        if (primitive == Mode::Strip) {
            result.first_capacity_ = std::min(result.first_capacity_, segments.per_instance());
            result.per_instance_chunks_ = add(1, ceil_div(segments.per_instance() - result.first_capacity_,
                                                         result.later_capacity_));
        } else {
            // Reserve a distinct final chunk so loop head carry is always a
            // cross-buffer copy. A two-vertex loop may end in a closing-only
            // chunk with zero new rows and two carried outputs.
            result.first_capacity_ = std::min(result.first_capacity_, segments.per_instance() - 1);
            const uint64_t terminal = std::min({calls, add(fresh, 1), output - 1});
            const uint64_t remaining = segments.per_instance() - result.first_capacity_;
            const uint64_t middle = remaining > terminal ? ceil_div(remaining - terminal, result.later_capacity_) : 0;
            result.per_instance_chunks_ = add(2, middle);
        }
    }
    result.chunks_ = multiply(result.per_instance_chunks_, selection.instances);
    if (result.chunks_ > limits.max_chunks)
        throw std::length_error("line batches: explicit chunk-count budget exceeded");
    return result;
}

class Rows {
public:
    uint64_t size() const { return chunk_.new_rows; }
    uint64_t per_instance() const { return size(); }
    Endpoint at(uint64_t local) const {
        if (local >= size()) throw std::out_of_range("line batches: fresh row exceeds chunk");
        return {selected_vertex(selection_, chunk_.first_new_ordinal + local),
                static_cast<uint32_t>(chunk_.instance)};
    }
private:
    Selection selection_;
    Chunk chunk_;
    Rows(Selection selection, Chunk chunk) : selection_(selection), chunk_(chunk) {}
    friend Rows rows(const Plan&, const Chunk&);
};

inline Rows rows(const Plan& plan, const Chunk& chunk) {
    // Use the canonical scalar schedule. A caller cannot forge a range beyond
    // admitted bounds by changing public Chunk fields after planning.
    return Rows(plan.selection(), plan.chunk(chunk.number));
}

}  // namespace vispy::lines::batches
