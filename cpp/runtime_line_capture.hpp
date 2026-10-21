#pragma once

#include "runtime_line_batch.hpp"

namespace vispy::lines::captures {

// Physical readbacks are captured after endpoint evaluation and before any
// carried endpoint copies. Bytes after the fresh prefix must still be canaries,
// including output rows which the subsequent carry phase will overwrite.
inline constexpr std::string_view capture_phase = "evaluated_before_carry";

struct Part {
    uint32_t first_row = 0, rows = 0, output_rows = 0;
    uint64_t raw_offset = 0, raw_bytes = 0;
};

struct Plan {
    uint32_t rows = 0, row_bytes = 0;
    uint64_t logical_bytes = 0, raw_bytes = 0;
    std::vector<Part> parts;

    uint64_t metadata_storage_bytes() const {
        if (parts.empty()) return 0;
        return batches::add(sizeof(Plan), batches::multiply(parts.capacity(), sizeof(Part)));
    }
};

inline uint64_t part_raw_bytes(uint32_t rows, uint32_t output_rows, uint32_t row_bytes) {
    if (!rows) return 0;
    const auto padded_rows = batches::multiply(batches::ceil_div(rows, 64), 64);
    return std::max(batches::add(batches::multiply(padded_rows, row_bytes), 16),
                    batches::multiply(output_rows, row_bytes));
}

// This deliberately accepts only the exact physical layout emitted by plan().
// It is also usable by consumers of saved metadata without any source Plan,
// index capture, shader state or original attribute storage being alive.
inline void validate_parts(uint32_t rows, uint32_t row_bytes,
                           std::span<const Part> parts, uint64_t total_raw_bytes) {
    if ((!rows) != parts.empty())
        throw std::invalid_argument("line capture: fresh row count and parts differ");
    if ((!parts.empty() || total_raw_bytes) && !row_bytes)
        throw std::invalid_argument("line capture: nonempty capture has zero row width");
    uint64_t row_cursor = 0, raw_cursor = 0;
    for (const auto& part : parts) {
        if (part.first_row != row_cursor || part.raw_offset != raw_cursor)
            throw std::invalid_argument("line capture: parts are missing, reordered or noncontiguous");
        if (part.output_rows < part.rows || uint64_t(part.output_rows) > uint64_t(part.rows) + 2 ||
            (!part.rows && part.output_rows != 2))
            throw std::invalid_argument("line capture: invalid fresh/output row extent");
        const auto expected = part_raw_bytes(part.rows, part.output_rows, row_bytes);
        if (part.raw_bytes != expected)
            throw std::invalid_argument("line capture: physical readback extent differs");
        row_cursor = batches::add(row_cursor, part.rows);
        raw_cursor = batches::add(raw_cursor, part.raw_bytes);
        if (row_cursor > rows || raw_cursor > total_raw_bytes)
            throw std::invalid_argument("line capture: part exceeds admitted capture extent");
    }
    if (row_cursor != rows || raw_cursor != total_raw_bytes)
        throw std::invalid_argument("line capture: incomplete logical or physical coverage");
}

inline Plan plan(const batches::Plan& source, uint32_t row_bytes, uint64_t binding_limit,
                 uint64_t max_parts, uint64_t max_raw_bytes, uint64_t max_control_bytes) {
    Plan result;
    result.row_bytes = row_bytes;
    const auto count = source.chunk_count();
    const auto total_rows = batches::multiply(source.endpoint_rows_per_instance(), source.selection().instances);
    if (total_rows > UINT32_MAX)
        throw std::length_error("line capture: logical row count exceeds uint32");
    result.rows = static_cast<uint32_t>(total_rows);
    result.logical_bytes = batches::multiply(total_rows, row_bytes);
    if (!count) {
        validate_parts(result.rows, row_bytes, {}, 0);
        return result;
    }
    if (!row_bytes)
        throw std::invalid_argument("line capture: nonempty capture has zero row width");
    if (count > max_parts || count > std::numeric_limits<size_t>::max() / sizeof(Part))
        throw std::length_error("line capture: explicit part-count/allocation budget exceeded");
    if (batches::add(sizeof(Plan), batches::multiply(count, sizeof(Part))) > max_control_bytes)
        throw std::length_error("line capture: explicit metadata budget exceeded");
    if (result.logical_bytes > std::numeric_limits<size_t>::max())
        throw std::length_error("line capture: logical capture exceeds host allocation size");
    // Admit every physical byte before allocating the metadata vector. Source
    // chunks are scalar values; the returned plan never retains their source.
    uint64_t row_cursor = 0, raw_cursor = 0;
    for (uint64_t number = 0; number < count; ++number) {
        const auto chunk = source.chunk(number);
        const auto first = batches::add(batches::multiply(chunk.instance, source.endpoint_rows_per_instance()),
                                        chunk.first_new_ordinal);
        if (first != row_cursor || chunk.new_rows > UINT32_MAX || chunk.output_rows > UINT32_MAX)
            throw std::invalid_argument("line capture: source chunks do not cover contiguous fresh rows");
        const auto raw = part_raw_bytes(static_cast<uint32_t>(chunk.new_rows),
                                        static_cast<uint32_t>(chunk.output_rows), row_bytes);
        if (raw > binding_limit)
            throw std::length_error("line capture: physical readback exceeds granted binding limit");
        raw_cursor = batches::add(raw_cursor, raw);
        row_cursor = batches::add(row_cursor, chunk.new_rows);
        if (raw_cursor > max_raw_bytes || raw_cursor > std::numeric_limits<size_t>::max())
            throw std::length_error("line capture: explicit raw capture/allocation budget exceeded");
    }
    if (row_cursor != total_rows)
        throw std::invalid_argument("line capture: source chunks do not complete logical rows");
    result.raw_bytes = raw_cursor;
    result.parts.reserve(static_cast<size_t>(count));
    // Standard libraries may reserve a larger capacity than requested. Charge
    // the allocation actually retained rather than only populated metadata.
    if (batches::add(sizeof(Plan), batches::multiply(result.parts.capacity(), sizeof(Part))) > max_control_bytes)
        throw std::length_error("line capture: retained metadata capacity exceeds budget");
    raw_cursor = 0;
    for (uint64_t number = 0; number < count; ++number) {
        const auto chunk = source.chunk(number);
        Part part;
        part.first_row = static_cast<uint32_t>(batches::add(
            batches::multiply(chunk.instance, source.endpoint_rows_per_instance()), chunk.first_new_ordinal));
        part.rows = static_cast<uint32_t>(chunk.new_rows);
        part.output_rows = static_cast<uint32_t>(chunk.output_rows);
        part.raw_offset = raw_cursor;
        part.raw_bytes = part_raw_bytes(part.rows, part.output_rows, row_bytes);
        raw_cursor = batches::add(raw_cursor, part.raw_bytes);
        result.parts.push_back(part);
    }
    validate_parts(result.rows, result.row_bytes, result.parts, result.raw_bytes);
    return result;
}

inline void append_part(const Plan& plan, size_t ordinal, std::span<const uint8_t> bytes,
                        std::vector<uint8_t>& raw, std::vector<uint8_t>& logical) {
    validate_parts(plan.rows, plan.row_bytes, plan.parts, plan.raw_bytes);
    const auto logical_bytes = batches::multiply(plan.rows, plan.row_bytes);
    if (plan.logical_bytes != logical_bytes || logical_bytes > std::numeric_limits<size_t>::max() ||
        plan.raw_bytes > std::numeric_limits<size_t>::max())
        throw std::invalid_argument("line capture: plan byte extent differs");
    if (&raw == &logical)
        throw std::invalid_argument("line capture: raw and logical destinations alias");
    if (ordinal >= plan.parts.size())
        throw std::out_of_range("line capture: part ordinal exceeds plan");
    const auto& part = plan.parts[ordinal];
    const auto fresh_bytes = batches::multiply(part.rows, plan.row_bytes);
    const auto logical_prefix = batches::multiply(part.first_row, plan.row_bytes);
    if (bytes.size() != part.raw_bytes || raw.size() != part.raw_offset || logical.size() != logical_prefix)
        throw std::invalid_argument("line capture: incoming bytes or destination prefix differs");
    if (raw.capacity() < plan.raw_bytes || logical.capacity() < logical_bytes)
        throw std::length_error("line capture: destinations lack admitted total capacity");
    const auto aliases = [&](const std::vector<uint8_t>& destination) {
        if (bytes.empty() || !destination.capacity()) return false;
        const auto source = reinterpret_cast<uintptr_t>(bytes.data());
        const auto target = reinterpret_cast<uintptr_t>(destination.data());
        return source >= target ? source - target < destination.capacity() : target - source < bytes.size();
    };
    if (aliases(raw) || aliases(logical))
        throw std::invalid_argument("line capture: incoming mapping aliases a capture destination");
    // Preserve the actual failed physical payload before reporting a guard
    // violation. A failed part cannot be retried or followed by later parts:
    // its raw/logical prefixes then deliberately disagree with that schedule.
    raw.insert(raw.end(), bytes.begin(), bytes.end());
    for (uint64_t offset = fresh_bytes; offset < part.raw_bytes; ++offset)
        if (bytes[static_cast<size_t>(offset)] != 0xcd)
            throw std::runtime_error("line capture: evaluated output canary changed before carry");
    logical.insert(logical.end(), bytes.begin(), bytes.begin() + static_cast<size_t>(fresh_bytes));
}

}  // namespace vispy::lines::captures
