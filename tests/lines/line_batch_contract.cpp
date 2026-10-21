#include "runtime_line_batch.hpp"

#include <iostream>
#include <string>

namespace {
using namespace vispy::lines;
namespace batch = vispy::lines::batches;

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
template<class Call> void rejects(Call&& call, const char* message) {
    try { call(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
template<class T> std::vector<uint8_t> indices(const std::vector<uint32_t>& ids) {
    std::vector<uint8_t> output(ids.size() * sizeof(T));
    for (size_t n = 0; n < ids.size(); ++n) {
        const T value = static_cast<T>(ids[n]);
        std::memcpy(output.data() + n * sizeof(T), &value, sizeof(T));
    }
    return output;
}
uint32_t word(const std::vector<uint8_t>& bytes, size_t n) {
    uint32_t result;
    require(n < bytes.size() / 4, "packed word address");
    std::memcpy(&result, bytes.data() + n * 4, 4);
    return result;
}
uint32_t payload(size_t field, uint64_t element, uint32_t component) {
    constexpr uint32_t bits[] = {0x80000000, 0x7fc01234, 0xff800000};
    return bits[component % 3] ^ static_cast<uint32_t>(field * 0x20000 + element * 0x101);
}
struct Sources {
    std::array<std::vector<uint8_t>, 4> storage;
    std::array<EndpointSource, 4> fields;
    EndpointInputLayout layout;
    Sources(uint64_t vertices, uint64_t instances) {
        const uint64_t offsets[] = {3, 5, 1, 7};
        const uint64_t strides[] = {11, 13, 17, 0};
        const uint32_t widths[] = {1, 2, 3, 1};
        const uint64_t divisors[] = {0, 2, 3, 0};
        for (size_t field = 0; field < 4; ++field) {
            const uint64_t elements = !strides[field] ? 1 :
                divisors[field] ? (instances - 1) / divisors[field] + 1 : vertices;
            storage[field].resize(static_cast<size_t>(offsets[field] + (elements - 1) * strides[field] + widths[field] * 4), 0xda);
            for (uint64_t element = 0; element < elements; ++element)
                for (uint32_t component = 0; component < widths[field]; ++component) {
                    const auto value = payload(field, element, component);
                    std::memcpy(storage[field].data() + offsets[field] + element * strides[field] + component * 4,
                                &value, 4);
                }
            fields[field] = {storage[field], offsets[field], strides[field], divisors[field], widths[field], "field"};
        }
        layout = endpoint_input_layout(widths);
    }
};

struct Token {
    uint64_t occurrence = UINT64_MAX, call = 0;
    uint32_t vertex = 0, instance = 0;
    bool operator==(const Token&) const = default;
};

void verify(const batch::Plan& plan, const std::vector<uint32_t>& ids, const Sources* sources = nullptr) {
    const auto mode = plan.primitive();
    const uint64_t segments = mode == Mode::List ? ids.size() / 2 : ids.size() < 2 ? 0 :
                              mode == Mode::Strip ? ids.size() - 1 : ids.size();
    const uint64_t evaluated = !segments ? 0 : mode == Mode::List ? ids.size() - ids.size() % 2 : ids.size();
    require(plan.segments_per_instance() == segments && plan.endpoint_rows_per_instance() == evaluated,
            "original domains preserve list tail and connected endpoint occurrences");
    std::vector<uint32_t> calls(static_cast<size_t>(evaluated * plan.selection().instances));
    std::vector<std::vector<Token>> outputs;
    uint64_t cursor = 0, invocation = 0;
    for (uint64_t number = 0; number < plan.chunk_count(); ++number) {
        const auto chunk = plan.chunk(number);
        const auto fresh = batch::rows(plan, chunk);
        require(chunk.number == number && chunk.first_segment == cursor && chunk.segment_count &&
                chunk.segment_count <= INT32_MAX && chunk.segment_count <= plan.limits().max_segments_per_chunk,
                "ordered original flattened segment schedule within native draw cap");
        require(chunk.new_rows <= plan.limits().max_new_rows && chunk.output_rows <= plan.limits().max_output_rows &&
                fresh.size() == chunk.new_rows && chunk.output_rows == chunk.new_rows + chunk.previous + chunk.closing,
                "bounded fresh outputs and trailing carry placement");
        require(chunk.first_segment / segments == chunk.instance &&
                (chunk.first_segment + chunk.segment_count - 1) / segments == chunk.instance,
                "chunk never crosses an original instance boundary");
        require(chunk.previous == (mode != Mode::List && number % plan.chunks_per_instance() != 0),
                "previous carry exactly at connected chunk seams");
        require(chunk.closing == (mode == Mode::Loop && number % plan.chunks_per_instance() + 1 == plan.chunks_per_instance()),
                "head carry exactly at final loop chunk");
        std::vector<Token> output(static_cast<size_t>(chunk.output_rows));
        std::vector<uint8_t> packed;
        if (sources) {
            packed = pack_endpoint_inputs(fresh, sources->fields, sources->layout, 16 + chunk.new_rows * 36);
            require(packed.size() == 16 + chunk.new_rows * 36 && word(packed, 0) == chunk.new_rows &&
                    word(packed, 1) == endpoint_input_abi && word(packed, 2) == 9, "bounded packed fresh-row header");
        }
        for (uint64_t row = 0; row < fresh.size(); ++row) {
            const uint64_t ordinal = chunk.first_new_ordinal + row;
            require(ordinal < evaluated, "fresh ordinal stays in evaluated occurrence domain");
            const uint64_t occurrence = chunk.instance * evaluated + ordinal;
            const auto endpoint = fresh.at(row);
            require(endpoint.vertex == ids[static_cast<size_t>(ordinal)] && endpoint.instance == chunk.instance,
                    "fresh rows retain original selected vertex and global instance IDs");
            require(++calls[static_cast<size_t>(occurrence)] == 1, "each selected occurrence invokes mutable main once");
            output[static_cast<size_t>(row)] = {occurrence, ++invocation, endpoint.vertex, endpoint.instance};
            if (sources) {
                const size_t base = static_cast<size_t>(4 + row * 9);
                require(word(packed, base) == endpoint.vertex && word(packed, base + 1) == endpoint.instance,
                        "packed identity words retain raw original IDs");
                size_t offset = base + 2;
                for (size_t field = 0; field < 4; ++field) {
                    const uint64_t element = field == 0 ? endpoint.vertex : field == 1 ? endpoint.instance / 2 :
                                             field == 2 ? endpoint.instance / 3 : 0;
                    const uint32_t width = field == 3 ? 1 : static_cast<uint32_t>(field + 1);
                    for (uint32_t component = 0; component < width; ++component)
                        require(word(packed, offset++) == payload(field, element, component),
                                "raw float bits and original global divisor 2/3 fetches");
                }
            }
        }
        rejects([&] { fresh.at(fresh.size()); }, "fresh row range accepted past end");
        if (chunk.previous) {
            require(chunk.previous_chunk + 1 == number && chunk.previous_chunk < outputs.size(), "previous carry reads earlier output owner");
            const auto& prior = outputs[static_cast<size_t>(chunk.previous_chunk)];
            require(chunk.previous_source_row < prior.size(), "previous copy source row bounded");
            output[static_cast<size_t>(chunk.new_rows)] = prior[chunk.previous_source_row];
        }
        if (chunk.closing) {
            require(plan.chunks_per_instance() >= 2 && chunk.head_chunk < number && chunk.head_source_row == 0,
                    "loop head copy is earlier distinct output buffer, never self-copy");
            output[static_cast<size_t>(chunk.new_rows + chunk.previous)] =
                outputs[static_cast<size_t>(chunk.head_chunk)][chunk.head_source_row];
        }
        for (uint64_t local = 0; local < chunk.segment_count; ++local) {
            const auto map = chunk.segment_rows(local);
            require(map.first < output.size() && map.last < output.size() && map.provoking == map.last,
                    "local consumer output map and LAST provoking row");
            const uint64_t original = cursor % segments;
            const uint64_t first = mode == Mode::List ? original * 2 : original;
            const uint64_t last = mode == Mode::Loop && original + 1 == segments ? 0 : first + 1;
            const auto& a = output[map.first]; const auto& b = output[map.last];
            require(a.occurrence == chunk.instance * evaluated + first && b.occurrence == chunk.instance * evaluated + last &&
                    a.vertex == ids[static_cast<size_t>(first)] && b.vertex == ids[static_cast<size_t>(last)] &&
                    a.instance == chunk.instance && b.instance == chunk.instance && a.call && b.call,
                    "independent original primitive occurrence sequence survives seams and loop closure");
            ++cursor;
        }
        rejects([&] { chunk.segment_rows(chunk.segment_count); }, "local segment range accepted past end");
        outputs.push_back(std::move(output));
    }
    require(cursor == segments * plan.selection().instances && invocation == calls.size(), "all original segments and once-only calls covered");
    for (const auto count : calls) require(count == 1, "every selected occurrence evaluated exactly once");
    rejects([&] { plan.chunk(plan.chunk_count()); }, "chunk range accepted past end");
}

void exhaustive_seams() {
    for (Mode mode : {Mode::List, Mode::Strip, Mode::Loop})
        for (uint64_t count = 0; count <= 17; ++count)
            for (uint64_t fresh = 2; fresh <= 6; ++fresh)
                for (uint64_t output = 2; output <= 6; ++output)
                    for (uint64_t segments = 1; segments <= 4; ++segments) {
                        std::vector<uint32_t> ids;
                        for (uint32_t n = 0; n < count; ++n) ids.push_back(17 + n);
                        verify(batch::plan(mode, {17, count, 2}, {fresh, output, segments, 1000, sizeof(batch::Plan)}), ids);
                    }
}

void selected_ids_and_raw_sources() {
    Sources sources(32, 13);
    for (Mode mode : {Mode::List, Mode::Strip, Mode::Loop}) {
        const std::vector<uint32_t> arrays = {11, 12, 13, 14, 15, 16, 17};
        verify(batch::plan(mode, {11, arrays.size(), 13}, {4, 5, 3, 1000, sizeof(batch::Plan)}), arrays, &sources);
        for (uint8_t width : {uint8_t(1), uint8_t(2), uint8_t(4)}) {
            const std::vector<uint32_t> captured = {29, 30, 6, 1, 4, 1, 7, 6, 6, 31};
            const std::vector<uint32_t> selected(captured.begin() + 2, captured.end() - 1);
            auto data = width == 1 ? indices<uint8_t>(captured) :
                        width == 2 ? indices<uint16_t>(captured) : indices<uint32_t>(captured);
            verify(batch::plan(mode, {2, selected.size(), 13, data, width}, {4, 5, 3, 1000, sizeof(batch::Plan)}),
                   selected, &sources);
        }
    }
    for (uint8_t width : {uint8_t(1), uint8_t(2), uint8_t(4)}) {
        const std::vector<uint32_t> selected = width == 1 ? std::vector<uint32_t>{255, 0, 255, 1, 1} :
            width == 2 ? std::vector<uint32_t>{65535, 0, 65535, 258, 258} :
                         std::vector<uint32_t>{UINT32_MAX, 0x80000001, UINT32_MAX, 0x80000001, 0x80000001};
        auto data = width == 1 ? indices<uint8_t>(selected) :
                    width == 2 ? indices<uint16_t>(selected) : indices<uint32_t>(selected);
        for (Mode mode : {Mode::List, Mode::Strip, Mode::Loop})
            verify(batch::plan(mode, {0, selected.size(), 13, data, width}, {2, 2, 1, 1000, sizeof(batch::Plan)}), selected);
    }
    verify(batch::plan(Mode::Loop, {UINT32_MAX - 1, 2, 13}, {2, 2, 1, 100, sizeof(batch::Plan)}),
           {UINT32_MAX - 1, UINT32_MAX});
}

void grants_zero_and_large_domains() {
    static_assert(sizeof(batch::Plan) <= 256);
    const auto exact = batch::plan(Mode::Loop, {9, 2, 13}, {2, 2, 1, 26, sizeof(batch::Plan)});
    require(exact.chunk_count() == 26 && exact.control_bytes() == sizeof(batch::Plan), "exact chunk/control budget accepted");
    const auto closing = exact.chunk(1);
    require(closing.closing && closing.previous && closing.new_rows == 0 && closing.output_rows == 2 &&
            closing.segment_rows(0).first == 0 && closing.segment_rows(0).last == 1, "closing-only chunk has two carried outputs");
    rejects([] { batch::plan(Mode::Loop, {0, 2, 13}, {2, 2, 1, 25, sizeof(batch::Plan)}); }, "chunk budget ignored");
    rejects([] { batch::plan(Mode::Strip, {0, 2, 1}, {2, 2, 1, 1, sizeof(batch::Plan) - 1}); }, "control budget ignored");
    for (Mode mode : {Mode::List, Mode::Strip, Mode::Loop}) {
        rejects([&] { batch::plan(mode, {0, 2, 1}, {1, 2, 1, 10, sizeof(batch::Plan)}); }, "one-row fresh grant accepted");
        rejects([&] { batch::plan(mode, {0, 2, 1}, {2, 1, 1, 10, sizeof(batch::Plan)}); }, "one-row output grant accepted");
        rejects([&] { batch::plan(mode, {0, 2, 1}, {2, 2, 0, 10, sizeof(batch::Plan)}); }, "zero segment grant accepted");
        for (uint64_t count : {0ull, 1ull}) {
            const auto zero = batch::plan(mode, {0, count, 13}, {});
            require(!zero.chunk_count() && !zero.segment_count() && !zero.control_bytes(), "zero primitive domain needs no resources");
        }
        require(!batch::plan(mode, {0, 9, 0}, {}).chunk_count(), "zero instances need no resources");
    }
    constexpr uint64_t identities = uint64_t(UINT32_MAX) + 1;
    const auto huge = batch::plan(Mode::List, {0, 2, identities}, {2, 2, 1, identities, sizeof(batch::Plan)});
    const auto last = huge.chunk(UINT32_MAX);
    require(huge.chunk_count() == identities && last.instance == UINT32_MAX && last.first_segment == UINT32_MAX &&
            batch::rows(huge, last).at(1).instance == UINT32_MAX, "UINT32_MAX flat segment and instance IDs remain inclusive");
    rejects([] { batch::plan(Mode::List, {0, 4, identities}, {4, 4, 2, UINT64_MAX, sizeof(batch::Plan)}); }, "flat segment identity overflow accepted");
    const auto wide = batch::plan(Mode::Loop, {0, identities, 1},
                                 {UINT64_MAX, UINT64_MAX, UINT64_MAX, 4, sizeof(batch::Plan)});
    require(wide.chunk_count() >= 2 && wide.chunk(wide.chunk_count() - 1).segment_count <= INT32_MAX,
            "huge loop schedule stays implicit within native count and uint32 row caps");
    const uint8_t data[] = {1, 2, 3};
    rejects([&] { batch::plan(Mode::List, {1, 3, 1, data, 1}, {}); }, "truncated immutable selection accepted");
    rejects([&] { batch::plan(Mode::List, {0, 2, 1, data, 3}, {}); }, "unsupported index width accepted");
    rejects([] { batch::plan(Mode::List, {UINT32_MAX, 2, 1}, {}); }, "array original ID overflow accepted");
    rejects([] { batch::plan(static_cast<Mode>(10), {}, {}); }, "invalid primitive enum accepted");
    rejects([] { batch::plan(Mode::Loop, {0, identities, identities}, {}); }, "segment product overflow accepted");
    rejects([] { batch::multiply(UINT64_MAX, 2); }, "checked multiplication wrapped");
    rejects([] { batch::add(UINT64_MAX, 1); }, "checked addition wrapped");
}

void raw_read_refusals() {
    Sources sources(32, 13);
    const auto plan = batch::plan(Mode::Strip, {11, 7, 13}, {3, 4, 3, 100, sizeof(batch::Plan)});
    const auto chunk = plan.chunk(plan.chunk_count() - 1);
    const auto fresh = batch::rows(plan, chunk);
    auto fields = sources.fields;
    fields[0].bytes = fields[0].bytes.first(5);
    rejects([&] { pack_endpoint_inputs(fresh, fields, sources.layout, 1024); }, "truncated original vertex source copied");
    fields = sources.fields; fields[1].bytes = fields[1].bytes.first(12);
    rejects([&] { pack_endpoint_inputs(fresh, fields, sources.layout, 1024); }, "global divisor source tail omitted");
    fields = sources.fields; fields[0].offset = UINT64_MAX; fields[0].stride = UINT64_MAX;
    rejects([&] { pack_endpoint_inputs(fresh, fields, sources.layout, 1024); }, "overflowing source address accepted");
    rejects([&] { pack_endpoint_inputs(fresh, sources.fields, sources.layout, 15 + fresh.size() * 36); }, "exact input byte cap ignored");
    const auto closing = batch::plan(Mode::Loop, {0, 2, 1}, {2, 2, 1, 2, sizeof(batch::Plan)});
    auto empty_rows = batch::rows(closing, closing.chunk(1));
    fields[0].bytes = {};
    const auto empty = pack_endpoint_inputs(empty_rows, fields, sources.layout, 16);
    require(empty.size() == 16 && word(empty, 0) == 0, "closing-only chunk does not read any original endpoint input");
    const std::vector<uint32_t> high = {UINT32_MAX, 0x80000001};
    auto bytes = indices<uint32_t>(high);
    const auto sparse = batch::plan(Mode::List, {0, 2, 1, bytes, 4}, {2, 2, 1, 1, sizeof(batch::Plan)});
    auto sparse_rows = batch::rows(sparse, sparse.chunk(0));
    const uint32_t constant = 0x7fc54321;
    const auto constant_bytes = std::span<const uint8_t>(reinterpret_cast<const uint8_t*>(&constant), 4);
    const EndpointSource constant_source{constant_bytes, 0, 0, 0, 1, "constant"};
    const uint32_t one[] = {1}; const auto layout = endpoint_input_layout(one);
    const auto packed = pack_endpoint_inputs(sparse_rows, std::span(&constant_source, 1), layout, 40);
    require(word(packed, 4) == UINT32_MAX && word(packed, 7) == 0x80000001 &&
            word(packed, 6) == constant && word(packed, 9) == constant, "high sparse IDs preserve stride-zero raw constants");
}
}  // namespace

int main() {
    try {
        exhaustive_seams();
        selected_ids_and_raw_sources();
        grants_zero_and_large_domains();
        raw_read_refusals();
        std::cout << "line_batch_contract: PASS (CPU bounded once-only endpoint schedule)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "line_batch_contract: " << error.what() << '\n';
        return 1;
    }
}
