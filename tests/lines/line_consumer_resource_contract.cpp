#include "runtime_line_resources.hpp"

#include <array>
#include <bit>
#include <cstring>
#include <functional>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using namespace vispy::shader;
using vispy::lines::pack_generated_line_consumer_uniforms;
uint32_t checks = 0;

void require(bool condition, const char* message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}

void word(std::vector<uint8_t>& bytes, uint32_t offset, uint32_t value) {
    if (uint64_t(offset) + 4 > bytes.size()) throw std::runtime_error("fixture write exceeds its fixed array");
    std::memcpy(bytes.data() + offset, &value, 4);
}

NormUniform field(const char* name, const char* type, const char* storage,
                  uint32_t offset, uint32_t size, uint32_t components) {
    NormUniform value;
    value.name = name; value.type = type; value.storage_type = storage;
    value.offset = offset; value.size = size; value.component_count = components;
    return value;
}

struct Fixture {
    std::shared_ptr<PortableShaderArtifact> original = std::make_shared<PortableShaderArtifact>();
    std::shared_ptr<LineEvaluatorArtifact> evaluator = std::make_shared<LineEvaluatorArtifact>();
    GeneratedLineConsumerArtifact consumer;
    GeneratedLineConsumerDraw draw;
    std::vector<uint8_t> captured;

    explicit Fixture(uint32_t original_bytes = 16) : captured(original_bytes, 0xa5) {
        original->ok = true;
        original->uniform_bytes = original_bytes;
        evaluator->ok = true;
        evaluator->original = original;
        consumer.ok = true;
        consumer.original = original;
        consumer.evaluator = evaluator;
        consumer.parameters_offset = original_bytes;
        consumer.uniform_bytes = original_bytes + 64;
        consumer.uniform_stage_mask = 3;
        draw.render_uniform_bytes = consumer.uniform_bytes;
        draw.parameters.header = {2, 7, 48, 2};
        draw.parameters.ranges = {7, 6, 1, 3};
        draw.parameters.viewport = {1.5f, -2.0f, 640.0f, 360.0f};
        draw.parameters.raster = {4.0f, 720.0f, 0.25f, 0.875f};
        layouts({}, {});
    }

    void layouts(std::vector<NormUniform> source, std::vector<NormUniform> target) {
        original->uniforms = std::move(source);
        consumer.uniforms = std::move(target);
        const std::array<const char*, 4> names{
            "vispy_line_consumer_header", "vispy_line_consumer_ranges",
            "vispy_line_consumer_viewport", "vispy_line_consumer_raster"};
        for (uint32_t i = 0; i < names.size(); ++i) {
            const char* type = i < 2 ? "uvec4" : "vec4";
            consumer.uniforms.push_back(field(names[i], type, type, consumer.parameters_offset + 16 * i, 16, 4));
        }
    }
};

// Fixed ABI words are independent of the production struct copy and packer.
// They include negative coordinates, fractional depth and nontrivial IDs.
void expected_parameters(std::vector<uint8_t>& expected, uint32_t offset) {
    constexpr std::array<uint32_t, 16> values{
        2, 7, 48, 2, 7, 6, 1, 3,
        0x3fc00000u, 0xc0000000u, 0x44200000u, 0x43b40000u,
        0x40800000u, 0x44340000u, 0x3e800000u, 0x3f600000u};
    for (uint32_t i = 0; i < values.size(); ++i) word(expected, offset + 4 * i, values[i]);
}

std::vector<uint8_t> pack(const Fixture& fixture, uint64_t grant) {
    return pack_generated_line_consumer_uniforms(fixture.consumer, fixture.captured, fixture.draw, grant);
}

void reject(const Fixture& fixture, uint64_t grant, const char* message) {
    const auto captured_before = fixture.captured;
    bool refused = false;
    try { (void)pack(fixture, grant); }
    catch (const std::invalid_argument&) { refused = true; }
    catch (const std::length_error&) { refused = true; }
    catch (const std::runtime_error&) { refused = true; }
    require(refused, message);
    require(fixture.captured == captured_before, "refusal changed immutable captured bytes");
}

void empty_original_and_exact_ABI() {
    Fixture fixture;
    const auto captured_before = fixture.captured;
    std::vector<uint8_t> expected(80, 0);
    expected_parameters(expected, 16);
    const auto actual = pack(fixture, 80);
    require(fixture.original->uniforms.empty() && fixture.original->uniform_bytes == 16,
            "empty semantic original retains its reserved 16-byte UBO allocation");
    require(actual == expected, "reserved original allocation plus exactly 64 ABI2 bytes differs");
    require(fixture.captured == captured_before, "packing changed original DRAW bytes");
    require(pack(fixture, std::numeric_limits<uint64_t>::max()) == expected,
            "large grant altered the fixed requested allocation or its byte contents");
    reject(fixture, 79, "one byte below the exact uniform grant was accepted");
    reject(fixture, 0, "zero uniform grant was accepted");
}

Fixture typed_fixture() {
    Fixture fixture(240);
    auto raw = field("raw", "vec4", "vec4", 0, 16, 4);
    auto signed_values = field("signed_values", "ivec2", "ivec2", 16, 8, 2);
    auto flags = field("flags", "bvec2", "ivec2", 32, 8, 2);
    auto matrices = field("matrices", "mat3", "mat3", 48, 96, 9);
    matrices.array_size = 2; matrices.matrix_columns = 3; matrices.matrix_rows = 3;
    matrices.matrix_stride = 16; matrices.array_stride = 48;
    auto vectors = field("vectors", "vec2", "vec2", 144, 32, 2);
    vectors.array_size = 2; vectors.array_stride = 16;
    auto scalar = field("scalar", "float", "float", 176, 4, 1);
    auto target_matrix = matrices;
    target_matrix.offset = 0; target_matrix.size = 128;
    target_matrix.array_stride = 64; target_matrix.row_major = true;
    auto target_vectors = vectors;
    target_vectors.offset = 128; target_vectors.size = 64; target_vectors.array_stride = 32;
    auto target_raw = raw; target_raw.offset = 192;
    auto target_signed = signed_values; target_signed.offset = 208;
    auto target_flags = flags; target_flags.offset = 216;
    auto target_scalar = scalar; target_scalar.offset = 224;
    fixture.layouts({raw, signed_values, flags, matrices, vectors, scalar},
                    {target_matrix, target_vectors, target_raw, target_flags, target_signed, target_scalar});
    const std::array<uint32_t, 4> raw_bits{0x80000000u, 0x7fc12345u, 0x3f800000u, 0xc0400000u};
    for (uint32_t i = 0; i < raw_bits.size(); ++i) word(fixture.captured, 4 * i, raw_bits[i]);
    word(fixture.captured, 16, 0x80000000u); word(fixture.captured, 20, 0x7fffffffu);
    word(fixture.captured, 32, 0xfffffffdu); word(fixture.captured, 36, 0);
    for (uint32_t array = 0; array < 2; ++array)
        for (uint32_t column = 0; column < 3; ++column)
            for (uint32_t row = 0; row < 3; ++row) {
                const float value = static_cast<float>(1 + array * 9 + column * 3 + row);
                word(fixture.captured, 48 + array * 48 + column * 16 + row * 4, std::bit_cast<uint32_t>(value));
            }
    word(fixture.captured, 144, 0x80000000u); word(fixture.captured, 148, 0x3e800000u);
    word(fixture.captured, 160, 0x7fc23456u); word(fixture.captured, 164, 0xbf800000u);
    word(fixture.captured, 176, 0x3f000000u);
    return fixture;
}

void typed_values_offsets_and_padding() {
    const auto fixture = typed_fixture();
    const auto captured_before = fixture.captured;
    std::vector<uint8_t> expected(304, 0);
    for (uint32_t array = 0; array < 2; ++array)
        for (uint32_t row = 0; row < 3; ++row)
            for (uint32_t column = 0; column < 3; ++column) {
                const float value = static_cast<float>(1 + array * 9 + column * 3 + row);
                word(expected, array * 64 + row * 16 + column * 4, std::bit_cast<uint32_t>(value));
            }
    word(expected, 128, 0x80000000u); word(expected, 132, 0x3e800000u);
    word(expected, 160, 0x7fc23456u); word(expected, 164, 0xbf800000u);
    word(expected, 192, 0x80000000u); word(expected, 196, 0x7fc12345u);
    word(expected, 200, 0x3f800000u); word(expected, 204, 0xc0400000u);
    word(expected, 208, 0x80000000u); word(expected, 212, 0x7fffffffu);
    word(expected, 216, 1); word(expected, 220, 0);
    word(expected, 224, 0x3f000000u);
    expected_parameters(expected, 240);
    require(pack(fixture, 304) == expected,
            "typed original values, name-based reordered offsets, matrix orientation, arrays, bools or zero padding differ");
    require(fixture.captured == captured_before, "typed packing changed immutable original snapshot");
    reject(fixture, 303, "typed UBO exceeds the uniform grant");
}

void identity_and_envelope_refusals() {
    const std::vector<std::function<void(Fixture&)>> changes{
        [](auto& f) { f.consumer.ok = false; },
        [](auto& f) { f.consumer.original.reset(); },
        [](auto& f) { f.consumer.evaluator.reset(); },
        [](auto& f) { f.evaluator->original = std::make_shared<PortableShaderArtifact>(); },
        [](auto& f) { f.captured.pop_back(); },
        [](auto& f) { f.captured.push_back(0); },
        [](auto& f) { f.consumer.parameters_offset += 16; },
        [](auto& f) { f.consumer.uniform_bytes -= 16; },
        [](auto& f) { f.consumer.uniform_bytes += 16; },
        [](auto& f) { --f.draw.render_uniform_bytes; },
        [](auto& f) { f.draw.parameters.header[0] = 1; },
        [](auto& f) { f.consumer.uniform_stage_mask = 0; },
        [](auto& f) { f.consumer.uniform_stage_mask = 1; },
        [](auto& f) { f.consumer.uniform_stage_mask = 2; },
        [](auto& f) { f.consumer.uniform_stage_mask = 4; },
        [](auto& f) { f.consumer.uniforms.pop_back(); },
        [](auto& f) { f.consumer.uniforms.push_back(f.consumer.uniforms.back()); },
        [](auto& f) { std::swap(f.consumer.uniforms[0], f.consumer.uniforms[1]); },
    };
    for (const auto& change : changes) {
        Fixture fixture; change(fixture);
        reject(fixture, 65536, "invalid paired artifact, snapshot or ABI envelope was accepted");
    }
    Fixture misaligned(20);
    reject(misaligned, 84, "four-byte aligned but non-std140 parameter envelope was accepted");
    for (uint32_t index = 0; index < 4; ++index) {
        const std::vector<std::function<void(NormUniform&)>> field_changes{
            [](auto& v) { v.name += "_wrong"; },
            [index](auto& v) { v.type = index < 2 ? "vec4" : "uvec4"; },
            [](auto& v) { v.offset += 4; },
            [](auto& v) { v.size = 12; },
            [](auto& v) { v.array_size = 1; },
            [](auto& v) { v.array_stride = 16; },
            [](auto& v) { v.matrix_stride = 16; },
            [](auto& v) { v.component_count = 3; },
            [](auto& v) { v.matrix_columns = 2; },
            [](auto& v) { v.matrix_rows = 2; },
        };
        for (const auto& change : field_changes) {
            Fixture fixture; change(fixture.consumer.uniforms[index]);
            reject(fixture, 80, "invalid reflected parameter member was accepted");
        }
    }
}

void original_prefix_refusals() {
    const std::vector<std::function<void(Fixture&)>> changes{
        [](auto& f) { f.consumer.uniforms[2].offset = 240; }, // Fits total UBO; aliases ABI2 header.
        [](auto& f) { f.consumer.uniforms[2].offset = 236; }, // Crosses prefix boundary.
        [](auto& f) { f.consumer.uniforms[2].offset = 208; }, // Overlaps signed member.
        [](auto& f) { f.consumer.uniforms[2].type = "vec3"; f.consumer.uniforms[2].component_count = 3; },
        [](auto& f) { f.consumer.uniforms[0].array_size = 1; },
        [](auto& f) { f.consumer.uniforms[0].array_stride = 16; },
        [](auto& f) { f.consumer.uniforms[0].matrix_stride = 4; },
        [](auto& f) { f.consumer.uniforms[0].component_count = 8; },
        [](auto& f) { f.consumer.uniforms[3].name = "raw"; f.consumer.uniforms[3].type = "vec4"; },
        [](auto& f) { f.original->uniforms[1].offset = 0; },
        [](auto& f) { f.original->uniforms[3].matrix_rows = 2; },
        [](auto& f) { f.original->uniforms[3].array_stride = 16; },
        [](auto& f) { f.original->uniforms[5].offset = 240; },
        [](auto& f) { f.original->uniforms[1].name = "raw"; },
    };
    for (const auto& change : changes) {
        auto fixture = typed_fixture(); change(fixture);
        reject(fixture, 304, "invalid original resource layout or ABI2 overlap was accepted");
    }
}
}  // namespace

int main() {
    try {
        empty_original_and_exact_ABI();
        typed_values_offsets_and_padding();
        identity_and_envelope_refusals();
        original_prefix_refusals();
        std::cout << "line consumer resource contract: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
