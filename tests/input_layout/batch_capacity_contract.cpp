#include "runtime_batch_capacity.hpp"
#include <iostream>

using namespace vispy::inputs;
static uint64_t checks = 0, probes = 0;
static void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
template<class Call> static void rejects(Call&& call, const char* message) {
    bool threw = false;
    try { call(); } catch (const std::exception&) { threw = true; }
    require(threw, message);
}
static std::vector<uint8_t> bytes_of(std::span<const uint32_t> values, uint32_t width) {
    std::vector<uint8_t> result(values.size() * width);
    for (size_t n = 0; n < values.size(); ++n) {
        if (width == 1) result[n] = static_cast<uint8_t>(values[n]);
        else if (width == 2) {
            const auto value = static_cast<uint16_t>(values[n]);
            std::memcpy(result.data() + n * 2, &value, 2);
        } else std::memcpy(result.data() + n * 4, &values[n], 4);
    }
    return result;
}
static Layout layout(uint32_t vertex_stride = 0, uint32_t instance_stride = 0,
                     uint32_t second_vertex = 0, uint32_t second_instance = 0) {
    Layout result;
    if (vertex_stride) result.streams.push_back({0, vertex_stride, false, {}});
    if (instance_stride) result.streams.push_back({0, instance_stride, true, {}});
    if (second_vertex) result.streams.push_back({0, second_vertex, false, {}});
    if (second_instance) result.streams.push_back({0, second_instance, true, {}});
    return result;
}
static WholeCompactFit probe(const Selection& selection, const Layout& streams,
                              uint64_t buffer, uint64_t storage, bool identity) {
    ++probes;
    return probe_whole_compact_fit(selection, streams, buffer, storage, identity);
}
// Independent bounded-input oracle: materialize IDs only for these tiny tests,
// use a linear deduplication vector and guarded exact-byte multiplication.
static bool oracle(const Selection& selection, const Layout& streams,
                    uint64_t buffer, uint64_t storage, bool identity) {
    if (!selection.count || !selection.instances) return true;
    std::vector<uint32_t> distinct;
    if (selection.index_bytes) {
        for (uint64_t n = 0; n < selection.count; ++n) {
            const auto id = selection.vertex(n);
            if (std::find(distinct.begin(), distinct.end(), id) == distinct.end()) distinct.push_back(id);
        }
        if (selection.count > UINT64_MAX / 4 || selection.count * 4 > buffer ||
            selection.count * 4 > SIZE_MAX || distinct.size() > INT32_MAX || distinct.size() * 4 > buffer) return false;
    }
    const uint64_t vertex_rows = selection.index_bytes ? distinct.size() : selection.count;
    for (const auto& stream : streams.streams) {
        const uint64_t rows = stream.instance ? selection.instances : vertex_rows;
        if (rows > UINT64_MAX / stream.stride || rows * stream.stride > buffer || rows * stream.stride > SIZE_MAX) return false;
    }
    const uint64_t identity_bytes = selection.index_bytes ? distinct.size() * 4 : 4;
    return !identity || (identity_bytes <= storage && identity_bytes <= buffer);
}
static void verify(const Selection& selection, const Layout& streams,
                    uint64_t buffer, uint64_t storage, bool identity) {
    const auto result = probe(selection, streams, buffer, storage, identity);
    require(result.fits == oracle(selection, streams, buffer, storage, identity), "exact whole-compact fit equals independent byte+distinct-ID oracle");
    require(result.indices_scanned <= selection.count, "selected index scan is finite");
    require(result.peak_scratch_keys <= result.scratch_key_bound && result.scratch_key_bound <= selection.count,
        "scratch never exceeds declared logical key bound or selected count");
    if (result.fits && selection.index_bytes && selection.count && selection.instances) {
        require(result.indices_scanned == selection.count, "successful indexed fit scans exact selected prefix");
        require(result.unique_vertices_observed == result.peak_scratch_keys, "successful unique count equals retained scratch keys");
    }
    // Join successful/failing probe decisions to the actual existing portable
    // compact-capacity and remapping functions for these bounded valid inputs.
    bool existing_fit = true;
    try {
        if (selection.count && selection.instances) {
            const auto capacity = compact_vertex_capacity(selection, streams, buffer, storage, identity);
            if (selection.index_bytes) (void)compact_indices(selection, buffer, capacity);
        }
    } catch (const std::exception&) { existing_fit = false; }
    require(result.fits == existing_fit, "decision joins actual existing whole-compact capacity/remap admission");
}

static void exact_boundaries() {
    const std::vector<uint32_t> ids{0, 1, 2, 0, 1, 2};
    const auto bytes = bytes_of(ids, 4);
    const Selection selected{0, ids.size(), 3, bytes, 4};
    const auto streams = layout(16, 16, 12, 8);
    auto exact = probe(selected, streams, 48, 12, true);
    require(exact.fits && exact.vertex_capacity == 3 && exact.unique_vertices_observed == 3,
        "joint four-stream/instance and headerless ID storage exact boundary");
    verify(selected, streams, 48, 12, true);
    const auto instance_fail = probe(selected, streams, 47, 12, true);
    require(!instance_fail.fits && instance_fail.reason == WholeCompactReason::InstanceRows && instance_fail.indices_scanned == 0,
        "instance limit refuses before index reads");
    const Selection one_instance{0, ids.size(), 1, bytes, 4};
    const auto vertex_fail = probe(one_instance, streams, 47, 12, true);
    require(!vertex_fail.fits && vertex_fail.reason == WholeCompactReason::UniqueVertices && vertex_fail.indices_scanned == 3 &&
        vertex_fail.unique_vertices_observed == 3 && vertex_fail.peak_scratch_keys == 2,
        "widest physical vertex stream controls unique capacity with capacity+1 early exit");
    verify(one_instance, streams, 47, 12, true);
    const auto storage_fail = probe(selected, streams, 48, 11, true);
    require(!storage_fail.fits && storage_fail.reason == WholeCompactReason::UniqueVertices && storage_fail.indices_scanned == 3,
        "headerless unique table12 exact versus11 storage boundary");
    require(probe(selected, streams, 48, 0, false).fits, "dead vertex identity ignores all storage grant bytes");
    const auto index_fail = probe(one_instance, layout(4), 23, 100, false);
    require(!index_fail.fits && index_fail.reason == WholeCompactReason::IndexBytes && index_fail.indices_scanned == 0,
        "six remapped uint32 indices24 exact versus23 allocation check precedes scan");
    require(probe(one_instance, layout(4), 24, 12, true).fits, "index byte boundary24 accepted");
    const Selection affine{16777217, 3, 3};
    require(probe(affine, streams, 48, 4, true).fits, "affine whole compact stores one four-byte base only");
    require(!probe(affine, streams, 47, 4, true).fits, "affine instance exact boundary enforced");
    const auto affine_fail = probe(Selection{16777217, 3, 1}, layout(16), 47, 4, true);
    require(!affine_fail.fits && affine_fail.reason == WholeCompactReason::VertexRows && affine_fail.indices_scanned == 0,
        "affine vertex rows checked without scanning IDs");
    const auto identity_fail = probe(Selection{0, 3, 1}, layout(4), 12, 3, true);
    require(!identity_fail.fits && identity_fail.reason == WholeCompactReason::IdentityBytes && identity_fail.indices_scanned == 0,
        "affine identity minimum four bytes is independent of count");
    require(probe(Selection{0, 3, 1}, layout(4), 12, 0, false).fits, "affine dead identity requires no storage");
    require(probe(Selection{0, 3, 1}, {}, 0, 0, false).fits, "no attributes and no live ID need no vertex buffer");
}

static void repeated_sparse_and_prefix() {
    std::vector<uint32_t> repeated(4096);
    const uint32_t sparse[]{UINT32_MAX, 16777217u, 0x80000001u};
    for (size_t n = 0; n < repeated.size(); ++n) repeated[n] = sparse[n % 3];
    const auto bytes = bytes_of(repeated, 4);
    const Selection selection{0, repeated.size(), 2, bytes, 4};
    const auto result = probe(selection, layout(4096), 16384, 12, true);
    require(result.fits && result.vertex_capacity == 3 && result.unique_vertices_observed == 3 &&
        result.indices_scanned == 4096 && result.peak_scratch_keys == 3 && result.scratch_key_bound == 3,
        "many repeated high IDs fit without count-based vertex refusal or remapped index payload");
    verify(selection, layout(4096), 16384, 12, true);
    // A count upper bound says4096 rows; actual unique rows are3. This is the
    // case the runtime must retain on whole compact instead of batch planning.
    require(selection.count > result.vertex_capacity, "fixture distinguishes selected count from actual unique rows");

    std::vector<uint32_t> long_tail{7, 9, 7, 9, 11};
    long_tail.resize(1000, 13);
    const auto early_bytes = bytes_of(long_tail, 4);
    const auto early = probe(Selection{0, long_tail.size(), 1, early_bytes, 4}, layout(4), 4000, 8, true);
    require(!early.fits && early.reason == WholeCompactReason::UniqueVertices && early.indices_scanned == 5 &&
        early.unique_vertices_observed == 3 && early.peak_scratch_keys == 2 && early.scratch_key_bound == 2,
        "capacity+1 distinct ID stops scan without inserting extra key or reading remaining995indices");
    const std::vector<uint32_t> suffix{7, 7, UINT32_MAX, 0x80000000u};
    const auto suffix_bytes = bytes_of(suffix, 4);
    const auto prefix = probe(Selection{0, 2, 1, suffix_bytes, 4}, layout(4), 8, 4, true);
    require(prefix.fits && prefix.indices_scanned == 2 && prefix.unique_vertices_observed == 1,
        "unused index backing suffix does not consume rows/storage or scan work");
    for (uint32_t width : {1u, 2u, 4u}) {
        const std::vector<uint32_t> values{1, 7, 1, 7, 1, 7};
        const auto raw = bytes_of(values, width);
        const auto fitted = probe(Selection{0, values.size(), 1, raw, width}, layout(12), 24, 8, true);
        require(fitted.fits && fitted.unique_vertices_observed == 2, "u8/u16/u32 source IDs use exact same whole-compact uint32 representation");
    }
}

static void matrix() {
    for (uint32_t width : {0u, 1u, 2u, 4u})
        for (uint64_t count = 0; count <= 12; ++count)
            for (uint64_t instances : {0ull, 1ull, 3ull})
                for (uint64_t buffer : {0ull, 3ull, 4ull, 11ull, 12ull, 23ull, 24ull, 47ull, 48ull, 96ull})
                    for (uint64_t storage : {0ull, 3ull, 4ull, 7ull, 8ull, 11ull, 12ull, 48ull})
                        for (bool identity : {false, true}) {
                            std::vector<uint32_t> ids(static_cast<size_t>(count));
                            for (size_t n = 0; n < ids.size(); ++n) ids[n] = static_cast<uint32_t>((n * 7 + n / 3) % 5);
                            const auto bytes = bytes_of(ids, width ? width : 4);
                            verify(Selection{1, count, instances, bytes, width}, layout(4, 8, 12, 4), buffer, storage, identity);
                        }
}

static void noops_invalid_and_overflow() {
    Layout malformed; malformed.direct = true; malformed.streams.push_back({0, 0, false, {}});
    require(probe(Selection{UINT32_MAX, 0, 1}, malformed, 0, 0, true).fits,
        "zero count requires no layout/storage/scratch or source index reads");
    const auto no_instances = probe(Selection{0, INT32_MAX, 0}, malformed, 0, 0, true);
    require(no_instances.fits && no_instances.indices_scanned == 0 && no_instances.peak_scratch_keys == 0,
        "zero instances bypass otherwise huge domains without allocating scratch");
    std::vector<uint8_t> empty;
    rejects([&] { probe(Selection{0, 1, 1, empty, 4}, {}, 100, 100, true); }, "invalid index read bound rejected before dereference");
    rejects([&] { probe(Selection{0, 0, 0, empty, 3}, {}, 0, 0, false); }, "invalid width still validated for noops");
    rejects([&] { probe(Selection{UINT32_MAX, 2, 1}, {}, 100, 100, false); }, "affine uint32 ID range overflow refused");
    rejects([&] { probe(Selection{0, UINT64_MAX, 1}, {}, UINT64_MAX, UINT64_MAX, false); }, "count admission refuses UINT64_MAX before byte arithmetic");
    rejects([&] { probe(Selection{0, 1, UINT64_MAX}, {}, UINT64_MAX, UINT64_MAX, false); }, "instance admission refuses UINT64_MAX before multiplication");
    rejects([&] { probe(Selection{0, 1, 1}, malformed, 100, 100, false); }, "nonzero direct layout refused");
    malformed.direct = false;
    rejects([&] { probe(Selection{0, 1, 1}, malformed, 100, 100, false); }, "zero physical stream stride refused");
    const uint32_t value = UINT32_MAX;
    const auto raw = bytes_of(std::span<const uint32_t>(&value, 1), 4);
    const auto maximum_grants = probe(Selection{0, 1, 1, raw, 4}, layout(UINT32_MAX, UINT32_MAX), UINT64_MAX, UINT64_MAX, true);
    require(maximum_grants.fits && maximum_grants.unique_vertices_observed == 1, "largest grants/strides use division without overflow");
    const auto huge_affine = probe(Selection{0, INT32_MAX, INT32_MAX}, layout(UINT32_MAX, UINT32_MAX), UINT64_MAX, 4, true);
    require(huge_affine.fits && huge_affine.indices_scanned == 0, "largest legal affine domains do not materialize or scan rows");
}

int main() {
    try {
        exact_boundaries(); repeated_sparse_and_prefix(); matrix(); noops_invalid_and_overflow();
        std::cout << "PASS exact whole-compact capacity probe: " << checks << " CPU checks; " << probes
                  << " probes; no remapped-index payload/native/GPU qualification\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n'; return 1;
    }
}
