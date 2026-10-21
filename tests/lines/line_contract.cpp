#include "runtime_line.hpp"
#include <iostream>
#include <string>
#include <vector>

namespace {
using namespace vispy::lines;
unsigned checks = 0;
void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
void close(double actual, double expected, const char* message) {
    require(std::isfinite(actual) && std::abs(actual - expected) <= 1e-12, message);
}
template<class Call> void rejects(Call&& call, const char* message) {
    bool rejected = false;
    try { call(); } catch (const std::exception&) { rejected = true; }
    require(rejected, message);
}
template<class T, size_t N> auto bytes(const std::array<T, N>& values) {
    return std::span<const uint8_t>(reinterpret_cast<const uint8_t*>(values.data()), sizeof(values));
}
void segment(const Segment& value, uint32_t a, uint32_t b, uint32_t instance, uint64_t ordinal) {
    require(value.first == a && value.last == b && value.provoking == b &&
            value.instance == instance && value.ordinal == ordinal, "original ordered endpoint/LAST/instance identity");
}

void state_and_segments() {
    const auto snapshot = state(3, true);
    require(snapshot.width == 3 && snapshot.smooth, "finite width and smooth snapshot");
    require(state(.125, false).width == .125 && !state(1, false).smooth, "fractional width and aliased state");
    for (double bad : {0., -1., std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()})
        rejects([&] { state(bad, true); }, "invalid width rejected before expansion");
    require(mode("lines") == Mode::List && mode("line_strip") == Mode::Strip && mode("line_loop") == Mode::Loop, "exact public mode names");
    rejects([] { mode("triangles"); }, "wrong topology rejected");
    rejects([] { Segments(static_cast<Mode>(100), {}); }, "invalid enum rejected");
    const Segments list(Mode::List, {3, 5, 2});
    require(list.size() == 4 && list.per_instance() == 2, "unpaired list tail ignored and instances multiply count");
    segment(list.at(0), 3, 4, 0, 0); segment(list.at(1), 5, 6, 0, 1);
    segment(list.at(2), 3, 4, 1, 0); segment(list.at(3), 5, 6, 1, 1);
    rejects([&] { list.at(4); }, "table access bounded");
    const Segments strip(Mode::Strip, {17, 4, 1});
    require(strip.size() == 3, "strip count");
    segment(strip.at(0), 17, 18, 0, 0); segment(strip.at(1), 18, 19, 0, 1); segment(strip.at(2), 19, 20, 0, 2);
    const Segments loop(Mode::Loop, {17, 3, 2});
    require(loop.size() == 6, "loop count and closing edge");
    segment(loop.at(2), 19, 17, 0, 2); segment(loop.at(3), 17, 18, 1, 0); segment(loop.at(5), 19, 17, 1, 2);
    for (auto primitive : {Mode::List, Mode::Strip, Mode::Loop}) for (uint64_t count : {0ull, 1ull})
        require(Segments(primitive, {0, count, 9}).size() == 0, "zero and singleton create no line primitives");
    require(Segments(Mode::Loop, {0, 3, 0}).size() == 0, "zero original instances create no primitives");
    segment(Segments(Mode::Loop, {9, 2, 1}).at(1), 10, 9, 0, 1);
    const std::array<uint8_t, 6> u8{250, 251, 7, 4, 9, 99};
    segment(Segments(Mode::List, {2, 3, 1, bytes(u8), 1}).at(0), 7, 4, 0, 0);
    const std::array<uint16_t, 4> u16{1, 65535, 258, 0};
    segment(Segments(Mode::Strip, {1, 3, 1, bytes(u16), 2}).at(0), 65535, 258, 0, 0);
    const std::array<uint32_t, 5> u32{42, 16777218, UINT32_MAX, 7, 99};
    const Segments sparse(Mode::Loop, {1, 3, 2, bytes(u32), 4});
    segment(sparse.at(0), 16777218, UINT32_MAX, 0, 0); segment(sparse.at(5), 7, 16777218, 1, 2);
    // The borrowed capture may be sliced: first=0 then has the same identities.
    segment(Segments(Mode::Strip, {0, 2, 1, bytes(u32).subspan(4, 8), 4}).at(0), 16777218, UINT32_MAX, 0, 0);
    rejects([&] { Segments(Mode::List, {4, 2, 1, bytes(u32), 4}); }, "truncated selected index suffix rejected");
    rejects([&] { Segments(Mode::List, {UINT64_MAX, 1, 1, bytes(u32), 4}); }, "index prefix overflow rejected");
    rejects([&] { Segments(Mode::List, {0, 2, 1, bytes(u32), 3}); }, "invalid index width rejected");
    rejects([] { Segments(Mode::List, {UINT32_MAX, 2, 1}); }, "nonindexed vertex range overflow rejected");
    rejects([] { Segments(Mode::List, {UINT64_MAX, 2, 1}); }, "huge first cannot wrap into valid identity");
    rejects([] { Segments(Mode::Loop, {0, uint64_t(UINT32_MAX)+1, uint64_t(UINT32_MAX)+1}); }, "total primitive count overflow rejected without allocation");
    rejects([] { Segments(Mode::List, {0, 2, uint64_t(UINT32_MAX)+2}); }, "instance identity overflow rejected");
    rejects([] { Segments(Mode::Loop, {0, 7, 2}, 13); }, "caller primitive budget checked");
    const Segments huge(Mode::List, {0, uint64_t(UINT32_MAX)+1, 2});
    require(huge.size() == uint64_t(UINT32_MAX)+1 && sizeof(huge) <= 96, "huge legal DRAW has constant-sized table");
    segment(huge.at(huge.size()-1), UINT32_MAX-1, UINT32_MAX, 1, uint64_t(UINT32_MAX)/2);
    segment(Segments(Mode::List, {0, 2, uint64_t(UINT32_MAX)+1}).at(UINT32_MAX), 0, 1, UINT32_MAX, 0);
}

uint32_t word(const std::vector<uint8_t>& data, size_t index) {
    uint32_t result;
    if (index >= data.size() / sizeof(result)) throw std::out_of_range("test packed word");
    std::memcpy(&result, data.data() + index * sizeof(result), sizeof(result));
    return result;
}

void endpoint_rows_and_inputs() {
    const EndpointRows strip(Mode::Strip, {3, 4, 2});
    require(strip.size() == 8 && strip.segment_count() == 6 && strip.per_instance() == 4,
            "one endpoint evaluation per selected occurrence and instance");
    const auto first = strip.segment_rows(0), adjacent = strip.segment_rows(1);
    require(first.first == 0 && first.last == 1 && adjacent.first == first.last && adjacent.last == 2,
            "adjacent strip segments reuse one isolated endpoint output");
    require(strip.segment_rows(3).first == 4 && strip.at(4).vertex == 3 && strip.at(4).instance == 1,
            "endpoint rows and segment references retain instance-major ordering");
    const EndpointRows list(Mode::List, {0, 5, 1});
    require(list.size() == 4 && list.segment_rows(1).provoking == 3,
            "unused odd list tail is not evaluated and LAST uses original row");
    rejects([&] { list.at(4); }, "endpoint row access bounded");
    rejects([&] { list.segment_rows(2); }, "segment output row access bounded");
    rejects([] { EndpointRows(Mode::Loop, {0, 3, 2}, 5); }, "explicit endpoint row budget checked before allocation");
    rejects([] { EndpointRows(Mode::List, {0, uint64_t(UINT32_MAX) + 1, 1}); },
            "compute header count cannot wrap at 2^32 endpoints");
    rejects([] { pack_endpoint_inputs(EndpointRows(Mode::List, {0, UINT32_MAX - 1ull, 1}),
                                      {}, endpoint_input_layout({}), UINT64_MAX); },
            "raw compute uint word addresses cannot wrap before a huge allocation");
    bool word_count_rejected = false;
    try {
        // Four header words plus 2,147,483,646 identity-only rows is exactly
        // 2^32 words: the last index fits, but the array length cannot.
        pack_endpoint_inputs(EndpointRows(Mode::List, {0, 2147483646ull, 1}),
                             {}, endpoint_input_layout({}), UINT64_MAX);
    } catch (const std::length_error& error) {
        word_count_rejected = std::string(error.what()) == "lines: endpoint input uint word address exceeds ABI";
    }
    require(word_count_rejected, "exact 2^32 raw word count rejected by ABI before reads/allocation");
    const std::array<uint32_t, 5> indices{42, 16777218, UINT32_MAX, 7, 99};
    const EndpointRows loop(Mode::Loop, {1, 3, 3, bytes(indices), 4});
    const auto closing = loop.segment_rows(5);
    require(loop.size() == 9 && closing.first == 5 && closing.last == 3 && closing.provoking == 3,
            "loop closing edge and flat LAST reuse original first output in their own instance");
    require(loop.at(0).vertex == 16777218 && loop.at(1).vertex == UINT32_MAX && loop.at(8).instance == 2,
            "sparse uint identities and original instance IDs remain exact");
    const std::array<uint32_t, 4> constant{0x80000000u, 0x7fc01234u, 0xff800000u, 0x3f000000u};
    const std::array<int32_t, 2> categories{-17, 23};
    const std::array<uint32_t, 2> widths{4, 1};
    const auto layout = endpoint_input_layout(widths);
    const std::array<EndpointSource, 2> sources{{
        {bytes(constant), 0, 0, 0, 4, "constant_float_bits"},
        {bytes(categories), 0, 4, 2, 1, "categorical_divisor2"}
    }};
    const auto packed = pack_endpoint_inputs(loop, sources, layout, 16 + 9 * 28);
    require(layout.word_offsets == std::vector<uint32_t>{2, 6} && layout.stride_words == 7,
            "compute input tightly packs raw attributes after exact two-word IDs");
    require(packed.size() == 268 && word(packed, 0) == 9 && word(packed, 1) == 1 &&
            word(packed, 2) == 7 && word(packed, 3) == 0, "ABI header count/version/stride/reserved bytes");
    for (size_t row = 0; row < 9; ++row) {
        const auto endpoint = loop.at(row);
        const size_t begin = 4 + row * 7;
        require(word(packed, begin) == endpoint.vertex && word(packed, begin + 1) == endpoint.instance,
                "packed IDs are uint32, never float-rounded");
        for (size_t n = 0; n < constant.size(); ++n)
            require(word(packed, begin + 2 + n) == constant[n], "constant signed-zero/NaN/infinity bits preserved");
        require(word(packed, begin + 6) == static_cast<uint32_t>(categories[endpoint.instance / 2]),
                "signed categories and nonunit instance divisors resolved exactly");
    }
    const std::array<uint32_t, 7> interleaved{9, 11, 999, 22, 998, 33, 997};
    const std::array<uint32_t, 1> one_width{1};
    const auto one = endpoint_input_layout(one_width);
    const std::array<EndpointSource, 1> interleaved_source{{{bytes(interleaved), 4, 8, 0, 1, "offset_stride"}}};
    const auto fetched = pack_endpoint_inputs(EndpointRows(Mode::Strip, {0, 3, 1}), interleaved_source, one, 52);
    require(word(fetched, 6) == 11 && word(fetched, 9) == 22 && word(fetched, 12) == 33,
            "interleaved offset/stride follows original vertex identity");
    const std::array<uint32_t, 4> list_source{10, 20, 30, 40};
    const std::array<EndpointSource, 1> list_sources{{{bytes(list_source), 0, 4, 0, 1, "drawn_list"}}};
    require(pack_endpoint_inputs(list, list_sources, one, 64).size() == 64,
            "unused odd list tail does not require an unread source element");
    const auto original = packed;
    auto invalid = sources;
    invalid[1].bytes = bytes(categories).first(4);
    rejects([&] { pack_endpoint_inputs(loop, invalid, layout, 268); }, "truncated divisor source rejected before packing");
    invalid = sources; invalid[0].stride = UINT64_MAX;
    rejects([&] { pack_endpoint_inputs(loop, invalid, layout, 268); }, "sparse stride/address overflow rejected");
    invalid = sources; invalid[0].offset = UINT64_MAX;
    rejects([&] { pack_endpoint_inputs(loop, invalid, layout, 268); }, "offset overflow rejected");
    rejects([&] { pack_endpoint_inputs(loop, sources, layout, 267); }, "allocation header included in granted size check");
    auto wrong = layout; ++wrong.stride_words;
    rejects([&] { pack_endpoint_inputs(loop, sources, wrong, 1000); }, "foreign row stride rejected");
    wrong = layout; --wrong.word_offsets[1];
    rejects([&] { pack_endpoint_inputs(loop, sources, wrong, 1000); }, "overlapping raw field layout rejected");
    require(packed == original, "failed packing leaves earlier immutable bytes untouched");
    const std::array<uint32_t, 1> zero{0};
    rejects([&] { endpoint_input_layout(zero); }, "zero-width input field rejected");
    const std::array<uint32_t, 1> overflow{UINT32_MAX};
    rejects([&] { endpoint_input_layout(overflow); }, "identity words included in ABI stride overflow check");
    const auto empty = pack_endpoint_inputs(EndpointRows(Mode::Strip, {0, 1, 7}), {}, endpoint_input_layout({}), 16);
    require(empty.size() == 16 && word(empty, 0) == 0 && word(empty, 2) == 2,
            "zero primitives create only an empty ABI header without evaluating source rows");
    struct Revision { std::vector<uint8_t> cpu; };
    auto revision = std::make_shared<Revision>();
    revision->cpu.assign(bytes(indices).begin(), bytes(indices).end());
    const std::weak_ptr<Revision> lifetime = revision;
    CapturedSelection<Revision> captured{Mode::Loop, state(3, true), 1, 3, 2, revision, 4};
    revision.reset();
    require(!lifetime.expired() && captured.state.width == 3 && captured.state.smooth,
            "immutable capture owns original source after deletion with width/smoothing state");
    segment(captured.segments().at(5), 7, 16777218, 1, 2);
    require(captured.endpoints().segment_rows(5).provoking == 3,
            "captured pre-rewrite loop uses original closing endpoint output");
    auto queued_copy = captured;
    captured.index.reset();
    require(!lifetime.expired() && queued_copy.endpoints().at(0).vertex == 16777218,
            "queued copy retains original source independently of live capture replacement");
    queued_copy.index.reset();
    require(lifetime.expired(), "last capture retirement releases source owner");
    rejects([&] { captured.selection(); }, "missing original index owner is an explicit capture error");
}

void clip_and_interpolation() {
    // Same independently derived clip-space endpoints as the new six fixtures.
    const Position a{-2, .0625, 0, 1}, b{6, .1875, 0, 3};
    const auto value = clip(a, b);
    require(value.visible(), "left/right clipped source remains visible");
    close(value.begin, .1, "left homogeneous clip parameter"); close(value.end, .5, "right homogeneous clip parameter");
    close(value.first[0]/value.first[3], -1, "left GL clip boundary"); close(value.last[0]/value.last[3], 1, "right GL clip boundary");
    close(screen_parameter(value.begin, 1, 3), .25, "left noperspective screen parameter");
    close(screen_parameter(value.end, 1, 3), .75, "right noperspective screen parameter");
    close(homogeneous_parameter(.25, 1, 3), .1, "left perspective reconstruction");
    close(homogeneous_parameter(.75, 1, 3), .5, "right perspective reconstruction");
    // A flat value is selected from original LAST, even when LAST was clipped.
    const Segment original{13, 77, 77, 5, 9};
    const auto flat = clip_segment(original, {0, 0, 0, 1}, {3, 0, 0, 1});
    require(flat.geometry.visible() && flat.geometry.end < 1 && flat.original.provoking == 77 &&
            flat.original.last == 77 && flat.original.instance == 5, "clipping preserves outside LAST identity instead of clipped/generated endpoint");
    const std::array<double, 2> flat_outputs{.125, .875};
    require(flat_outputs[flat.original.provoking == original.last] == .875, "original provoking output bypasses clipping interpolation");
    auto near_far = clip({-.5, 0, -2, 1}, {.5, 0, 2, 1});
    require(near_far.visible(), "near/far clipped line visible"); close(near_far.begin, .25, "near plane"); close(near_far.end, .75, "far plane");
    close(near_far.first[2], -1, "GL keeps negative near clip z"); close(near_far.last[2], 1, "GL far clip z");
    auto bottom_top = clip({0, -3, 0, 1}, {.5, 3, 0, 1});
    close(bottom_top.begin, 1./3, "bottom plane"); close(bottom_top.end, 2./3, "top plane");
    require(clip({-3, 0, 0, 1}, {-2, 1, 0, 1}).status == ClipStatus::Outside, "same outside halfspace rejected");
    require(clip({0, 0, 0, -1}, {.5, 0, 0, -2}).status == ClipStatus::BehindEye, "both original endpoints behind eye explicit");
    const auto crosses_eye = clip({-2, 0, 0, -1}, {.5, .25, 0, 1});
    require(crosses_eye.visible() && crosses_eye.begin > .5 && crosses_eye.first[3] > 0, "six-plane clipping handles one original endpoint behind eye");
    close(screen_parameter(.75, -1, 1), 1.5, "signed original weights retain valid extrapolated screen parameter");
    close(homogeneous_parameter(1.5, -1, 1), .75, "signed original projection reconstructs clipped positive-w point");
    require(clip({-2, 0, 0, 1}, {0, 2, 0, 1}).status == ClipStatus::Degenerate, "touching corner is explicit screen-degenerate segment");
    require(clip({0, 0, 0, 1}, {0, 0, .5, 1}).status == ClipStatus::Degenerate, "same projected XY with differing depth explicit");
    require(clip({1, 0, 0, 1}, {1, .5, 0, 1}).visible(), "line touching boundary over nonzero length retained");
    require(clip({0, 0, 0, 0}, {0, 0, 0, 0}).status == ClipStatus::ZeroW, "all-zero homogeneous point explicit");
    require(clip({0, 0, 0, 0}, {.5, .5, 0, 1}).status == ClipStatus::ZeroW, "zero-w retained endpoint is not silently projected");
    Position bad{0, 0, 0, 1}; bad[0] = std::numeric_limits<double>::quiet_NaN();
    require(clip(bad, b).status == ClipStatus::NonFinite, "NaN clip input rejected by explicit status");
    bad[0] = std::numeric_limits<double>::infinity();
    require(clip(a, bad).status == ClipStatus::NonFinite, "infinite clip input rejected");
    const double big = std::numeric_limits<double>::max()/2;
    const auto scaled = clip({-big, 0, 0, big}, {big, big/2, 0, big});
    require(scaled.visible() && finite(scaled.first) && finite(scaled.last), "huge finite clip coordinates cannot overflow plane sums");
    require(clip({1e-300, 0, 0, 1e300}, {0, .5e300, 0, 1e300}).status == ClipStatus::PrecisionLoss,
            "unrepresentable common-scale ratio explicit instead of silently dropping coordinate");
    const auto reverse = clip(b, a);
    close(reverse.begin, 1-value.end, "clipping direction reversal entry"); close(reverse.end, 1-value.begin, "clipping direction reversal exit");
    for (unsigned n = 0; n <= 100; ++n) {
        const double t = n/100.;
        const auto q = screen_parameter(t, 1, 3);
        close(homogeneous_parameter(q, 1, 3), t, "projective mapping/inverse exact endpoint orientation across interval");
        close(screen_parameter(t, big, big), t, "normalized large equal weights avoid overflow");
    }
    for (double parameter : {-.1, 1.1, std::numeric_limits<double>::quiet_NaN()})
        rejects([&] { screen_parameter(parameter, 1, 3); }, "invalid homogeneous parameter rejected");
    rejects([] { screen_parameter(.5, 0, 3); }, "zero original weight has no invertible screen representation");
    rejects([] { screen_parameter(.5, -1, 1); }, "eye-plane denominator explicit");
    rejects([] { screen_parameter(.25, -1, 1); }, "behind-eye interpolation explicit");
    rejects([] { screen_parameter(.5, 1, std::numeric_limits<double>::infinity()); }, "nonfinite interpolation weight rejected");
    rejects([] { screen_parameter(.5, 1e-300, 1e300); }, "weight-ratio underflow explicit");
    rejects([] { homogeneous_parameter(1.5, 1, 3); }, "positive-weight screen parameter outside segment rejected");
    rejects([] { homogeneous_parameter(.5, -1, 1); }, "inverse singularity explicit");
    rejects([] { homogeneous_parameter(std::numeric_limits<double>::infinity(), 1, 3); }, "nonfinite inverse parameter rejected");
}
}  // namespace

int main() {
    try {
        state_and_segments(); endpoint_rows_and_inputs(); clip_and_interpolation();
        std::cout << "{\"status\":\"passed\",\"checks\":" << checks
                  << ",\"GPU_used\":false,\"native_imported\":false}" << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "line_contract failed after " << checks << " checks: " << error.what() << std::endl;
        return 1;
    }
}
