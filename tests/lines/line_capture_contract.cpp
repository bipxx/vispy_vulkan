#include "runtime_line_capture.hpp"

#include <iostream>

namespace {
using namespace vispy::lines;
namespace batch = vispy::lines::batches;
namespace capture = vispy::lines::captures;

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
template<class Call> void rejects(Call&& call, const char* message) {
    try { call(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}

struct Token {
    uint32_t occurrence = 0, vertex = 0, instance = 0, raw_bits = 0;
    bool operator==(const Token&) const = default;
};
static_assert(sizeof(Token) == 16);

template<class T> std::vector<uint8_t> index_bytes(const std::vector<uint32_t>& ids) {
    std::vector<uint8_t> result(ids.size() * sizeof(T));
    for (size_t n = 0; n < ids.size(); ++n) {
        const auto value = static_cast<T>(ids[n]);
        std::memcpy(result.data() + n * sizeof(T), &value, sizeof(T));
    }
    return result;
}

capture::Plan capture_plan(const batch::Plan& source, uint32_t row_bytes = sizeof(Token)) {
    return capture::plan(source, row_bytes, UINT64_MAX, 10000, UINT64_MAX, UINT64_MAX);
}

std::vector<uint8_t> physical(const batch::Plan& source, const capture::Plan& plan, size_t number) {
    const auto chunk = source.chunk(number);
    const auto rows = batch::rows(source, chunk);
    const auto& part = plan.parts[number];
    std::vector<uint8_t> result(static_cast<size_t>(part.raw_bytes), 0xcd);
    for (uint64_t n = 0; n < rows.size(); ++n) {
        const auto row = rows.at(n);
        const Token token{static_cast<uint32_t>(chunk.instance * source.endpoint_rows_per_instance() +
                                               chunk.first_new_ordinal + n),
                          row.vertex, row.instance, 0x7fc01234 ^ static_cast<uint32_t>(n)};
        std::memcpy(result.data() + n * sizeof(Token), &token, sizeof(token));
    }
    return result;
}

void verify(const batch::Plan& source, const std::vector<uint32_t>& ids) {
    const auto plan = capture_plan(source);
    const auto per_instance = ids.size() < 2 ? 0 :
        source.primitive() == Mode::List ? ids.size() - ids.size() % 2 : ids.size();
    require(plan.rows == per_instance * source.selection().instances &&
            plan.logical_bytes == uint64_t(plan.rows) * sizeof(Token) &&
            plan.parts.size() == source.chunk_count(), "original occurrence capture extent");
    if (plan.parts.empty()) {
        require(!plan.raw_bytes && !plan.metadata_storage_bytes(), "empty capture needs no allocation");
        return;
    }
    require(plan.metadata_storage_bytes() == sizeof(capture::Plan) + plan.parts.capacity() * sizeof(capture::Part),
            "retained metadata capacity is charged");
    std::vector<uint8_t> raw, logical, expected_raw;
    raw.reserve(static_cast<size_t>(plan.raw_bytes));
    logical.reserve(static_cast<size_t>(plan.logical_bytes));
    const auto raw_capacity = raw.capacity(), logical_capacity = logical.capacity();
    for (size_t number = 0; number < plan.parts.size(); ++number) {
        const auto input = physical(source, plan, number);
        expected_raw.insert(expected_raw.end(), input.begin(), input.end());
        capture::append_part(plan, number, input, raw, logical);
        require(raw == expected_raw, "actual pre-carry physical allocations are concatenated byte for byte");
        require(raw.capacity() == raw_capacity && logical.capacity() == logical_capacity,
                "append does not grow either admitted destination");
    }
    require(raw.size() == plan.raw_bytes && logical.size() == plan.logical_bytes,
            "all physical and fresh rows complete once");
    for (uint32_t row = 0; row < plan.rows; ++row) {
        Token token;
        std::memcpy(&token, logical.data() + uint64_t(row) * sizeof(Token), sizeof(Token));
        require(token.occurrence == row && token.vertex == ids[static_cast<size_t>(row % per_instance)] &&
                token.instance == row / per_instance, "independent instance-major original occurrence oracle");
    }
}

void original_domains() {
    for (const auto mode : {Mode::List, Mode::Strip, Mode::Loop})
        for (uint64_t count = 0; count <= 19; ++count)
            for (uint64_t fresh = 2; fresh <= 5; ++fresh)
                for (uint64_t outputs = 2; outputs <= 5; ++outputs)
                    for (uint64_t segments = 1; segments <= 3; ++segments) {
                        std::vector<uint32_t> ids;
                        for (uint32_t n = 0; n < count; ++n) ids.push_back(21 + n);
                        verify(batch::plan(mode, {21, count, 3}, {fresh, outputs, segments, 1000, sizeof(batch::Plan)}), ids);
                    }
    for (const auto mode : {Mode::List, Mode::Strip, Mode::Loop}) {
        for (const uint8_t width : {uint8_t(1), uint8_t(2), uint8_t(4)}) {
            const std::vector<uint32_t> ids = width == 1 ? std::vector<uint32_t>{255, 1, 255, 1, 1} :
                width == 2 ? std::vector<uint32_t>{65535, 258, 65535, 258, 258} :
                std::vector<uint32_t>{UINT32_MAX, 0x80000001, UINT32_MAX, 0x80000001, 0x80000001};
            auto captured = width == 1 ? index_bytes<uint8_t>(ids) :
                            width == 2 ? index_bytes<uint16_t>(ids) : index_bytes<uint32_t>(ids);
            verify(batch::plan(mode, {0, ids.size(), 13, captured, width},
                               {2, 2, 1, 1000, sizeof(batch::Plan)}), ids);
        }
    }
}

void bounds_and_lifetime() {
    const auto source = batch::plan(Mode::Loop, {0, 2, 1}, {2, 2, 1, 2, sizeof(batch::Plan)});
    const auto admitted = capture_plan(source);
    require(admitted.parts.size() == 2 && admitted.parts[0].rows == 2 && admitted.parts[1].rows == 0 &&
            admitted.parts[1].output_rows == 2 && !admitted.parts[1].raw_bytes &&
            admitted.parts[1].first_row == 2, "zero-new closure carries render rows without readback");
    const auto exact = capture::plan(source, sizeof(Token), admitted.parts[0].raw_bytes, 2,
                                      admitted.raw_bytes, admitted.metadata_storage_bytes());
    require(exact.raw_bytes == 64 * sizeof(Token) + 16, "exact physical guard-bound admission");
    rejects([&] { capture::plan(source, sizeof(Token), exact.raw_bytes - 1, 2, UINT64_MAX, UINT64_MAX); },
            "binding limit ignored padding and canary allocation");
    rejects([&] { capture::plan(source, sizeof(Token), UINT64_MAX, 1, UINT64_MAX, UINT64_MAX); }, "part budget ignored");
    rejects([&] { capture::plan(source, sizeof(Token), UINT64_MAX, 2, exact.raw_bytes - 1, UINT64_MAX); }, "raw budget ignored");
    rejects([&] { capture::plan(source, sizeof(Token), UINT64_MAX, 2, UINT64_MAX, exact.metadata_storage_bytes() - 1); },
            "metadata retained allocation ignored");
    rejects([&] { capture_plan(source, 0); }, "nonempty zero-width capture accepted");
    const auto empty = capture::plan(batch::plan(Mode::Strip, {0, 1, 1}, {}), 0, 0, 0, 0, 0);
    require(!empty.rows && empty.parts.empty() && !empty.logical_bytes && !empty.raw_bytes, "empty plan respects zero grants");
    const auto huge = batch::plan(Mode::List, {0, 2, uint64_t(UINT32_MAX) / 2 + 1},
                                  {2, 2, 1, UINT64_MAX, sizeof(batch::Plan)});
    rejects([&] { capture_plan(huge); }, "flattened fresh rows above uint32 accepted");
    const auto lifetime = [] {
        auto bytes = index_bytes<uint32_t>({UINT32_MAX, 1, UINT32_MAX});
        return capture_plan(batch::plan(Mode::Loop, {0, 3, 2, bytes, 4}, {2, 2, 1, 20, sizeof(batch::Plan)}));
    }();
    capture::validate_parts(lifetime.rows, lifetime.row_bytes, lifetime.parts, lifetime.raw_bytes);
    require(lifetime.rows == 6, "owning capture metadata survives original index and source plan lifetime");
    // Carry rows can extend beyond the workgroup padding plus the fixed guard.
    const auto crowded = batch::plan(Mode::Loop, {0, 127, 1}, {64, 65, 64, 4, sizeof(batch::Plan)});
    const auto crowd_capture = capture_plan(crowded);
    require(crowd_capture.parts.back().rows == 63 && crowd_capture.parts.back().output_rows == 65 &&
            crowd_capture.parts.back().raw_bytes == 65 * sizeof(Token), "future carry slots included in physical raw extent");
}

void malformed_metadata() {
    const auto source = batch::plan(Mode::Strip, {0, 7, 2}, {3, 4, 2, 100, sizeof(batch::Plan)});
    const auto good = capture_plan(source);
    auto bad = good.parts;
    auto check = [&] { capture::validate_parts(good.rows, good.row_bytes, bad, good.raw_bytes); };
    bad[0].first_row = 1; rejects(check, "logical gap accepted"); bad = good.parts;
    std::swap(bad[0], bad[1]); rejects(check, "reordered parts accepted"); bad = good.parts;
    bad[1].first_row -= 1; rejects(check, "overlapping rows accepted"); bad = good.parts;
    bad[1].raw_offset += 1; rejects(check, "physical gap accepted"); bad = good.parts;
    bad[0].raw_bytes -= 1; rejects(check, "physical extent mismatch accepted"); bad = good.parts;
    bad[0].output_rows = bad[0].rows - 1; rejects(check, "short output extent accepted"); bad = good.parts;
    bad[0].output_rows = bad[0].rows + 3; rejects(check, "excess carries accepted"); bad = good.parts;
    bad.pop_back(); rejects(check, "missing terminal part accepted"); bad = good.parts;
    rejects([&] { capture::validate_parts(good.rows, 0, bad, good.raw_bytes); }, "zero-width saved metadata accepted");
    rejects([&] { capture::validate_parts(good.rows, good.row_bytes, bad, UINT64_MAX); }, "uncovered raw extent accepted");
    rejects([&] { capture::validate_parts(0, good.row_bytes, bad, good.raw_bytes); }, "nonempty zero-row parts accepted");
    const capture::Part zero{0, 0, 1, 0, 0};
    rejects([&] { capture::validate_parts(1, 16, std::span(&zero, 1), 0); }, "invalid empty output accepted");
}

void failed_canary_and_append_contract() {
    const auto source = batch::plan(Mode::Strip, {0, 7, 1}, {3, 4, 2, 100, sizeof(batch::Plan)});
    const auto plan = capture_plan(source);
    const auto first = physical(source, plan, 0), next = physical(source, plan, 1);
    std::vector<uint8_t> raw, logical;
    raw.reserve(static_cast<size_t>(plan.raw_bytes)); logical.reserve(static_cast<size_t>(plan.logical_bytes));
    rejects([&] { capture::append_part(plan, 1, next, raw, logical); }, "out-of-order part accepted");
    rejects([&] { capture::append_part(plan, plan.parts.size(), {}, raw, logical); }, "out-of-range ordinal accepted");
    rejects([&] { capture::append_part(plan, 0, std::span(first).first(first.size() - 1), raw, logical); }, "short mapping accepted");
    require(raw.empty() && logical.empty(), "preflight failures do not append evidence");
    std::vector<uint8_t> unreserved;
    rejects([&] { capture::append_part(plan, 0, first, unreserved, logical); }, "unadmitted destination growth accepted");
    auto malformed = plan; ++malformed.logical_bytes;
    rejects([&] { capture::append_part(malformed, 0, first, raw, logical); }, "forged plan byte extent accepted");
    rejects([&] { capture::append_part(plan, 0, first, raw, raw); }, "aliased raw/logical destinations accepted");
    capture::append_part(plan, 0, first, raw, logical);
    const auto before_raw = raw, before_logical = logical;
    rejects([&] { capture::append_part(plan, 1, std::span<const uint8_t>(raw), raw, logical); },
            "incoming mapped bytes borrowed from growing destination accepted");
    rejects([&] { capture::append_part(plan, 0, first, raw, logical); }, "completed part retry accepted");
    require(raw == before_raw && logical == before_logical, "retry refusal preserves captured evidence");
    // The first trailing row is a future carry destination for this chunk.
    for (const size_t corrupt : {size_t(plan.parts[1].rows) * sizeof(Token), next.size() - 1}) {
        raw = before_raw; logical = before_logical;
        auto bytes = next; bytes[corrupt] = 0;
        rejects([&] { capture::append_part(plan, 1, bytes, raw, logical); }, "corrupted pre-carry canary accepted");
        auto expected = before_raw; expected.insert(expected.end(), bytes.begin(), bytes.end());
        require(raw == expected && logical == before_logical, "failed physical bytes retained before guard refusal");
        rejects([&] { capture::append_part(plan, 1, next, raw, logical); }, "failed part retry accepted");
        const auto later = physical(source, plan, 2);
        rejects([&] { capture::append_part(plan, 2, later, raw, logical); }, "logical completion after failed part accepted");
    }
}
}  // namespace

int main() {
    try {
        original_domains();
        bounds_and_lifetime();
        malformed_metadata();
        failed_canary_and_append_contract();
        require(capture::capture_phase == "evaluated_before_carry", "public capture phase declaration");
        std::cout << "line_capture_contract: PASS (CPU physical pre-carry evidence and bounded logical capture)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "line_capture_contract: " << error.what() << '\n';
        return 1;
    }
}
