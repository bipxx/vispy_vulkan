#include "runtime_batch_plan.hpp"
#include <iostream>

using namespace vispy::inputs;
namespace batch = vispy::inputs::batches;

static uint64_t checks = 0;
static void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
static void put(std::vector<uint8_t>& bytes, size_t offset, uint32_t value) {
    std::memcpy(bytes.data() + offset, &value, 4);
}
static uint32_t word(std::span<const uint8_t> bytes, size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < 4) throw std::runtime_error("oracle word outside bytes");
    uint32_t result = 0;
    std::memcpy(&result, bytes.data() + offset, 4);
    return result;
}
static std::vector<uint8_t> vec2_rows(size_t backing_bytes = 24) {
    std::vector<uint8_t> result(backing_bytes, 0x6b);
    const uint32_t words[]{0x7fc01234u, 0x80000000u, 0x01000001u, 0xffffffffu, 0x91827364u, 0x12345678u};
    for (size_t w = 0; w < 6; ++w) put(result, w * 4, words[w]);
    return result;
}
static std::vector<uint8_t> u16_indices(size_t backing_bytes) {
    std::vector<uint8_t> result(backing_bytes, 0xff);
    const uint16_t indices[]{0, 1, 2};
    std::memcpy(result.data(), indices, sizeof(indices));
    return result;
}
static Source vec2_source(std::span<const uint8_t> bytes) {
    return {bytes, 17, 3, 0, 8, 8, 0, "positions"};
}
static void prove_sources(const Selection& selection, std::span<const Source> sources) {
    validate_selection(selection);
    validate_sources(selection, sources, maximum_vertex(selection));
}
static void verify_plan(const Selection& selection, std::span<const Source> sources, uint64_t cap,
                        std::initializer_list<uint64_t> expected_counts) {
    prove_sources(selection, sources);
    const auto layout = compact_layout(sources, 30, 8, 2048);
    const auto plan = batch::plan_triangle_list(selection, sources, layout, {cap, cap, 1ULL << 20, 1000});
    require(plan.indexed, "u8 original input produces compact uint32 index children");
    require(plan.selected_count == selection.count, "planner retains complete selected count");
    require(plan.geometry.size() == expected_counts.size(), "expected geometry child count");
    size_t g = 0;
    uint64_t element = 0;
    for (uint64_t count : expected_counts) {
        const auto& geometry = plan.geometry[g];
        require(geometry.element_count == count, "exact geometry element-count boundary");
        require(geometry.element_offset == element, "ordered element offset");
        require(geometry.original_vertices == std::vector<uint32_t>{0, 1, 2}, "stable exact original ID table0/1/2");
        require(geometry.remapped_indices.size() == count, "one remapped index per selected element");
        require(geometry.remapped_indices.size() * 4 <= cap, "actual uint32 index child allocation fits");
        for (size_t n = 0; n < geometry.remapped_indices.size(); ++n) {
            const auto local = geometry.remapped_indices[n];
            require(local == (element + n) % 3, "every remapped index retains original0/1/2 order");
            require(geometry.original_vertices.at(local) == selection.vertex(element + n), "decoded compact ID matches original selected ID");
        }
        for (size_t slot = 0; slot < layout.streams.size(); ++slot) {
            if (layout.streams[slot].instance) continue;
            const auto packed = batch::pack_vertex_stream(plan, g, slot, sources);
            require(packed.size() <= cap, "packed physical stream fits grant");
            for (size_t row = 0; row < geometry.original_vertices.size(); ++row)
                for (size_t field : layout.streams[slot].fields)
                    for (uint64_t at = 0; at < sources[field].element_bytes; at += 4)
                        require(word(packed, row * layout.streams[slot].stride + layout.offsets[field] + static_cast<size_t>(at)) ==
                            word(sources[field].bytes, static_cast<size_t>(sources[field].offset + geometry.original_vertices[row] * sources[field].stride + at)),
                            "all packed words preserve raw NaN/negative-zero/integer bits");
        }
        element += count; ++g;
    }
    require(element == selection.count, "no selected index omitted or duplicated");
    uint64_t calls = 0, restored_rows = 0;
    plan.for_each_draw([&](const batch::DrawRef& draw) {
        ++calls;
        const auto identities = batch::identity_data(plan, draw);
        const auto& geometry = plan.geometry[draw.geometry];
        for (uint64_t instance = 0; instance < draw.instance_count; ++instance) {
            require(word(identities, 4) + instance == draw.instance_base + instance, "original instance domain retained");
            for (const auto local : geometry.remapped_indices) {
                require(word(identities, 8 + static_cast<size_t>(local) * 4) == restored_rows % 3,
                    "implicit schedule restores all original selected IDs");
                ++restored_rows;
            }
        }
    });
    require(calls == plan.encoded_draws, "implicit native call count honest");
    require(restored_rows == selection.count * selection.instances, "schedule retains full logical invocation domain");
}

static void u8_direct_and_split_regression() {
    auto vertices = vec2_rows();
    std::vector<Source> sources{vec2_source(vertices)};
    std::vector<uint8_t> indices(60);
    for (size_t n = 0; n < indices.size(); ++n) indices[n] = static_cast<uint8_t>(n % 3);
    const Selection selection{0, 60, 1, indices, 1};
    prove_sources(selection, sources);
    require(indices.size() == 60 && vertices.size() == 24, "all original u8/vec2 source bounds are safe");
    require(direct_layout(sources, 30, 8, 2048).direct, "fixture has an otherwise native-compatible vertex layout");
    require(!u8_widening_fits(selection.count, 96), "60 widened uint16 indices exceed96-byte grant");
    require(!direct_uploads_fit(selection, sources, 96), "raw u8 direct binding rejected even though60-byte backing fits");
    verify_plan(selection, sources, 96, {24, 24, 12});
    require(!u8_widening_fits(selection.count, 95) && !direct_uploads_fit(selection, sources, 95), "95-byte grant also enters compact batching");
    verify_plan(selection, sources, 95, {21, 21, 18});
    const Selection repeated_instances{0, 60, 3, indices, 1};
    verify_plan(repeated_instances, sources, 96, {24, 24, 12});
}

static void direct_widths_and_whole_backings() {
    auto vertices = vec2_rows();
    std::vector<Source> sources{vec2_source(vertices)};
    auto index96 = u16_indices(96);
    Selection indexed{0, 3, 1, index96, 2};
    prove_sources(indexed, sources);
    require(direct_uploads_fit(indexed, sources, 96), "entire96-byte index backing admitted at96");
    require(!direct_uploads_fit(indexed, sources, 95), "entire96-byte index backing refused at95 despite six selected bytes");
    verify_plan(indexed, sources, 95, {3});
    std::vector<uint8_t> index32(96, 0xff);
    put(index32, 0, 0); put(index32, 4, 1); put(index32, 8, 2);
    const Selection valid32{0, 3, 1, index32, 4};
    prove_sources(valid32, sources);
    require(direct_uploads_fit(valid32, sources, 96), "validated uint32 selection admits exact96-byte backing");
    require(!direct_uploads_fit(valid32, sources, 95), "validated uint32 whole backing refuses95");
    auto source96 = vec2_rows(96);
    std::vector<Source> exact_sources{vec2_source(source96)};
    const Selection arrays{0, 3, 1};
    prove_sources(arrays, exact_sources);
    require(direct_uploads_fit(arrays, exact_sources, 96), "whole96-byte source backing fits exactly");
    require(!direct_uploads_fit(arrays, exact_sources, 95), "whole96-byte source backing refused at95 despite24 selected bytes");
    std::vector<uint8_t> unused_indices(4096);
    const Selection unused{0, 3, 1, unused_indices, 0};
    require(direct_uploads_fit(unused, sources, 96), "array draws ignore an unused index span");
    for (uint32_t width : {0u, 1u, 2u, 3u, 4u, 8u, 255u}) {
        Selection probe{0, 3, 1, index96, width};
        require(direct_uploads_fit(probe, sources, 96) == (width == 0 || width == 2 || width == 4),
            "direct route permits only no index or native uint16/uint32 widths");
    }
    auto large_vertices = vec2_rows(4096);
    auto large_indices = u16_indices(4096);
    std::vector<Source> large_sources{vec2_source(large_vertices)};
    Selection small_selected{0, 3, 1, large_indices, 2};
    prove_sources(small_selected, large_sources);
    require(!direct_uploads_fit(small_selected, large_sources, 96), "large whole index/source backings refuse direct despite tiny valid subset");
    verify_plan(small_selected, large_sources, 96, {3});
    auto small_indices = u16_indices(6);
    small_selected.indices = small_indices;
    prove_sources(small_selected, large_sources);
    require(!direct_uploads_fit(small_selected, large_sources, 96), "large source backing alone refuses direct");
    small_selected.indices = large_indices;
    require(!direct_uploads_fit(small_selected, sources, 96), "large index backing alone refuses direct");

    std::vector<uint8_t> instance96(96), instance97(97), constant97(97);
    auto with_instance = sources;
    with_instance.push_back({instance97, 31, 1, 0, 4, 4, 1, "instance"});
    Selection instanced{0, 3, 2};
    prove_sources(instanced, with_instance);
    require(!direct_uploads_fit(instanced, with_instance, 96), "every whole instance source participates in direct admission");
    with_instance.back().bytes = instance96;
    require(direct_uploads_fit(instanced, with_instance, 96), "all whole vertex/instance sources fit at exact96");
    with_instance.push_back({constant97, 39, 1, 0, 0, 4, 0, "constant"});
    prove_sources(instanced, with_instance);
    require(!direct_uploads_fit(instanced, with_instance, 96), "stride-zero source also obeys whole-backing upload limit");
}

static void widening_arithmetic() {
    require(u8_widening_fits(48, 96) && !u8_widening_fits(48, 95), "exact96 versus95 widened-byte boundary");
    require(u8_widening_fits(60, 120) && !u8_widening_fits(60, 119), "count60 widened boundary120 versus119");
    require(u8_widening_fits(0, 0), "zero widening requires zero payload bytes");
    require(!u8_widening_fits(UINT64_MAX, UINT64_MAX), "max count cannot wrap count times2 into admission");
    require(u8_widening_fits(UINT64_MAX / 2, UINT64_MAX), "largest representable doubled count fits max grant");
    require(!u8_widening_fits(UINT64_MAX / 2 + 1, UINT64_MAX), "one above maximum doubled count refuses");
    const uint64_t counts[]{0, 1, 47, 48, 49, 59, 60, 61, UINT64_MAX / 2, UINT64_MAX / 2 + 1, UINT64_MAX};
    const uint64_t grants[]{0, 1, 2, 95, 96, 119, 120, UINT64_MAX};
    for (const auto count : counts) for (const auto grant : grants) {
        // An independently overflow-guarded multiplication oracle.
        const bool expected = count <= UINT64_MAX / 2 && count * 2 <= grant;
        require(u8_widening_fits(count, grant) == expected, "widening admission matches guarded exact-byte oracle");
    }
}

int main() {
    try {
        u8_direct_and_split_regression();
        direct_widths_and_whole_backings();
        widening_arithmetic();
        std::cout << "PASS actual staged routing helpers plus portable planner: " << checks
                  << " CPU checks; u8 cap96=24/24/12 cap95=21/21/18; no runtime/GPU qualification\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
