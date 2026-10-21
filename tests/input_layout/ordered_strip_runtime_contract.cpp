#include "runtime_batch_strip.hpp"
#include "runtime_batch_owner.hpp"
#include "runtime_batch_capacity.hpp"
#include <iostream>
#include <map>

using namespace vispy::inputs;
namespace batch = vispy::inputs::batches;
namespace owner = vispy::inputs::batches::owners;
static uint64_t checks = 0;
static void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
template<class Call> static void rejects(Call&& call, const char* message) {
    bool failed = false;
    try { call(); } catch (const std::exception&) { failed = true; }
    require(failed, message);
}
static uint32_t word(std::span<const uint8_t> bytes, size_t at) {
    if (at > bytes.size() || bytes.size() - at < 4) throw std::runtime_error("oracle word outside bytes");
    uint32_t value; std::memcpy(&value, bytes.data() + at, 4); return value;
}
static std::vector<uint8_t> rows(uint32_t count, uint32_t stride) {
    std::vector<uint8_t> result(size_t(count) * stride);
    for (uint32_t row = 0; row < count; ++row) for (uint32_t offset = 0; offset < stride; offset += 4) {
        const uint32_t value = offset == 4 ? 0x80000000u : offset == 8 ? 0x7fc01234u :
                               offset == 12 ? 0xffffffffu ^ row : 0x01000001u + row;
        std::memcpy(result.data() + size_t(row) * stride + offset, &value, 4);
    }
    return result;
}
static std::vector<uint8_t> indices(std::span<const uint32_t> ids, uint32_t width) {
    std::vector<uint8_t> result(ids.size() * width);
    for (size_t n = 0; n < ids.size(); ++n) {
        const uint32_t value = ids[n];
        if (width == 1) result[n] = static_cast<uint8_t>(value);
        else if (width == 2) { const uint16_t small = static_cast<uint16_t>(value); std::memcpy(result.data() + n * 2, &small, 2); }
        else std::memcpy(result.data() + n * 4, &value, 4);
    }
    return result;
}
struct Node {
    std::vector<uint8_t> cpu;
    std::map<std::string, std::shared_ptr<Node>> derived;
};
using Record = std::shared_ptr<Node>;
struct Builder {
    Record make_root() const { return std::make_shared<Node>(); }
    Record make_leaf(std::vector<uint8_t>&& bytes, owner::LeafKind) const {
        auto node = make_root(); node->cpu = std::move(bytes); return node;
    }
    void attach(Record& root, std::string key, const Record& leaf) const {
        if (!root->derived.emplace(std::move(key), leaf).second) throw std::runtime_error("repeated owner edge");
    }
};
static owner::Limits owner_limits() { return {1ULL << 26, 1ULL << 26, 1ULL << 27, 100000, 100000, sizeof(Node), 64}; }
static owner::PreparedOwner<Record> prepare(const Selection& selected, std::span<const Source> sources, uint64_t cap,
                                           batch::Topology topology = batch::Topology::TriangleStrip) {
    auto layout = compact_layout(sources, 30, 8, 2048);
    auto payload = batch::plan_ordinary_triangle_batches(topology,
        selected, sources, layout, {cap, cap, 1ULL << 24, 100000});
    const auto policy = batch::ordinary_batch_policy(topology, payload);
    batch::validate_ordinary_batch_policy(topology, payload,
        batch::expected_ordinary_batch_policy(topology, selected));
    require(policy.identity == ::VertexIdentityPolicy::BatchIndexed && policy.index_type == "unsigned_int" && policy.mode == "triangles",
            "actual lowered arrays/indexed Plan selects BatchIndexed uint32 triangle-list policy");
    return owner::prepare_owner<Record>(std::move(payload), sources, owner_limits(), cap, Builder{});
}

// Independent GL strip oracle: original primitive number decides only the
// first-two-corner swap. All repeated-ID primitives and original LAST remain.
static std::vector<uint32_t> expected_strip(std::span<const uint32_t> selected) {
    std::vector<uint32_t> result;
    for (size_t primitive = 0; primitive + 2 < selected.size(); ++primitive) {
        result.push_back(selected[primitive + (primitive & 1)]);
        result.push_back(selected[primitive + ((primitive & 1) ? 0 : 1)]);
        result.push_back(selected[primitive + 2]);
    }
    if (selected.size() < 3) result.assign(selected.begin(), selected.end());
    return result;
}
// Independent fan oracle: the original center and previous corner are repeated
// at every seam. The final corner remains LAST, including degenerate triangles.
static std::vector<uint32_t> expected_fan(std::span<const uint32_t> selected) {
    std::vector<uint32_t> result;
    for (size_t corner = 2; corner < selected.size(); ++corner) {
        result.push_back(selected[0]);
        result.push_back(selected[corner - 1]);
        result.push_back(selected[corner]);
    }
    if (selected.size() < 3) result.assign(selected.begin(), selected.end());
    return result;
}
static void verify(const Selection& selected, std::span<const uint32_t> original,
                   std::span<const Source> sources, uint64_t cap, bool require_seam,
                   batch::Topology topology = batch::Topology::TriangleStrip) {
    auto prepared = prepare(selected, sources, cap, topology);
    require(prepared.root && prepared.data, "complete ABI2 owner built before any snapshot publication");
    const auto& data = *prepared.data;
    const auto expected = topology == batch::Topology::TriangleFan ? expected_fan(original) : expected_strip(original);
    require(data.plan.indexed && data.plan.selected_count == expected.size(), "owning lowered index domain matches independent primitive oracle");
    if (require_seam) require(data.geometry.size() > 1, "fixture forces a real geometry seam");
    std::vector<std::pair<uint32_t, uint32_t>> actual;
    uint64_t calls = 0;
    data.plan.for_each_draw([&](const batch::DrawRef& draw) {
        ++calls;
        const auto& geometry = data.geometry.at(draw.geometry);
        const auto& block = data.blocks.at(static_cast<size_t>(draw.instance_block));
        require(geometry.index && geometry.identity && block.origin, "ABI2 retains separate indexed identity and16-byte block origin");
        const auto block_base = word(block.origin->cpu, 0);
        require(block.origin->cpu.size() == 16 && block_base == data.plan.instance_block(draw.instance_block).first, "actual origin UBO and block first agree");
        for (uint64_t row = 0; row < draw.instance_count; ++row) {
            const uint32_t instance = block_base + static_cast<uint32_t>(draw.row_offset + row);
            require(instance == draw.instance_base + row, "native firstInstance row_offset adds block origin exactly once");
            for (size_t at = 0; at < geometry.index->cpu.size(); at += 4) {
                const uint32_t local = word(geometry.index->cpu, at);
                const uint32_t id = word(geometry.identity->cpu, size_t(local) * 4);
                actual.emplace_back(instance, id);
            }
            for (size_t slot = 0; slot < data.plan.layout.streams.size(); ++slot) {
                const auto& stream = data.plan.layout.streams[slot];
                const auto record = stream.instance ? block.instances[slot] : geometry.vertices[slot];
                require(record && record->cpu.size() <= cap, "every actual packed physical stream fits explicit cap");
                const size_t count = stream.instance ? 1 : geometry.identity->cpu.size() / 4;
                for (size_t n = 0; n < count; ++n) for (const size_t field : stream.fields) {
                    const auto& source = sources[field];
                    const uint32_t id = stream.instance ? instance / static_cast<uint32_t>(source.divisor) : word(geometry.identity->cpu, n * 4);
                    const size_t from = static_cast<size_t>(source.offset + source.stride * id);
                    const size_t target_row = stream.instance ? static_cast<size_t>(draw.row_offset + row) : n;
                    for (uint64_t offset = 0; offset < source.element_bytes; offset += 4)
                        require(word(record->cpu, target_row * stream.stride + data.plan.layout.offsets[field] + offset) == word(source.bytes, from + offset),
                                "actual ABI2 packed vertex/constant/divisor words retain raw32 bits");
                }
            }
        }
    });
    std::vector<std::pair<uint32_t,uint32_t>> wanted;
    for (uint32_t instance = 0; instance < selected.instances; ++instance)
        for (uint32_t id : expected) wanted.emplace_back(instance, id);
    require(actual == wanted, "actual ABI2 identity/index leaves preserve full instance-major GL primitive sequence including odd seams, LAST and degenerates");
    require(calls == data.plan.encoded_draws && data.counts.encoded_draws == calls, "implicit native schedule count equals actual retained owner accounting");
    require(data.counts.metadata_bytes == data.metadata_storage_bytes(), "retained owner metadata charges Plan capacities only; diagnostics not retained");
    require(data.counts.packed_bytes > 0 && data.counts.retained_bytes >= data.counts.packed_bytes, "actual retained payload and control charges remain bounded");
}
static void routing_and_identity() {
    require(batch::ordinary_triangle_batches("triangles") && batch::ordinary_triangle_batches("triangle_strip") && batch::ordinary_triangle_batches("triangle_fan"), "only admitted triangle modes enable new route");
    require(batch::ordinary_triangle_topology("triangle_fan") == batch::Topology::TriangleFan, "fan mode preserves original planner topology");
    for (const auto* mode : {"points", "lines", "line_strip", "line_loop", ""}) {
        require(!batch::ordinary_triangle_batches(mode) && !batch::defer_triangle_u8_widening(mode, 60, 96), "other primitive/u8 paths unchanged");
        rejects([&] { (void)batch::ordinary_triangle_topology(mode); }, "unsupported batch topology refused");
    }
    require(batch::defer_triangle_u8_widening("triangle_strip",60,96) && !batch::defer_triangle_u8_widening("triangle_strip",48,96), "u8 widening exact96 boundary routes strips correctly");
    const auto list = batch::ordinary_triangle_domain("triangles", "selected", 7);
    const auto strip = batch::ordinary_triangle_domain("triangle_strip", "selected", 7);
    const auto fan = batch::ordinary_triangle_domain("triangle_fan", "selected", 7);
    require(list != strip && list != fan && strip != fan && strip != batch::ordinary_triangle_domain("triangle_strip", "selected", 1), "cache key distinguishes original topology AND instance domain");
    batch::Plan bad; bad.indexed = false;
    rejects([&] { (void)batch::ordinary_batch_policy(batch::Topology::TriangleStrip,bad); }, "array source width cannot incorrectly select affine lowered strip policy");
    rejects([&] { (void)batch::ordinary_batch_policy(batch::Topology::TriangleFan,bad); }, "array fan cannot select an affine lowered payload");
    require(batch::ordinary_batch_policy(batch::Topology::Triangles,bad).identity == ::VertexIdentityPolicy::BatchAffine, "unchanged array triangle lists keep affine batch ABI");
}
static void fan_cases() {
    constexpr auto fan = batch::Topology::TriangleFan;
    require(batch::fan_expansion_fits(10,96) && !batch::fan_expansion_fits(11,96), "whole-fan exact96-byte expansion boundary");
    require(batch::fan_expansion_fits(2,0) && !batch::fan_expansion_fits(3,11) && batch::fan_expansion_fits(3,12), "empty/one-primitive expansion capacity boundary");
    require(!batch::fan_expansion_fits(UINT64_MAX,UINT64_MAX), "fan allocation admission does not overflow");
    const uint64_t last_count = uint64_t(INT32_MAX) / 3 + 2;
    require(batch::fan_expansion_fits(last_count,UINT64_MAX) && !batch::fan_expansion_fits(last_count+1,UINT64_MAX), "expanded native count limit is independent of allocation grant");
    require(batch::defer_triangle_u8_widening("triangle_fan",60,96), "oversized fan keeps original u8 selection until batching");
    auto vertex=rows(40,16), inst2=rows(7,16), inst3=rows(5,16);
    std::vector<Source> sources{{vertex,1,1,0,16,16,0,"vertex"},
        {inst2,2,1,0,16,16,2,"divisor2"},{inst3,3,1,0,16,16,3,"divisor3"}};
    std::vector<uint32_t> arrays;
    for(uint32_t n=5;n<25;++n) arrays.push_back(n);
    verify({5,arrays.size(),13},arrays,sources,96,true,fan);
    for(uint32_t width : {1u,2u,4u}) {
        const std::vector<uint32_t> ids{7,11,7,7,19,11,23,7,29,31,7,37};
        auto bytes=indices(ids,width);
        verify({0,ids.size(),13,bytes,width},ids,sources,80,true,fan);
    }
    auto constant=rows(1,4);
    std::vector<Source> constants{{constant,4,2,0,0,4,0,"constant"},sources[1],sources[2]};
    for(uint32_t width : {1u,2u,4u}) {
        const uint32_t all_ones=width==1 ? UINT8_MAX : width==2 ? UINT16_MAX : UINT32_MAX;
        const std::vector<uint32_t> ids{all_ones,7,all_ones,all_ones,42,9,11,all_ones};
        auto bytes=indices(ids,width);
        verify({0,ids.size(),13,bytes,width},ids,constants,32,true,fan);
    }
    std::vector<Source> constant_only{constants[0]};
    const std::vector<uint32_t> high{0x01000001u,UINT32_MAX,0x80000001u,42,42,UINT32_MAX,7,9};
    auto high_bytes=indices(high,4);
    verify({0,high.size(),13,high_bytes,4},high,constant_only,32,true,fan);
    for(const uint32_t first : {0x01000001u,UINT32_MAX-7}) {
        std::vector<uint32_t> ids;
        for(uint32_t n=0;n<8;++n) ids.push_back(first+n);
        verify({first,8,13},ids,constant_only,32,true,fan);
    }
    for(uint64_t count : {1ULL,2ULL}) {
        std::vector<uint32_t> ids(count,3); auto bytes=indices(ids,4);
        verify({0,count,1,bytes,4},ids,constant_only,96,false,fan);
        std::vector<Source> missing{{{},5,1,0,4,4,0,"missing"}};
        rejects([&] { (void)prepare({0,count,1,bytes,4},missing,96,fan); }, "incomplete fan still validates original source reads");
    }
    const auto layout=compact_layout(constant_only,30,8,2048);
    const Selection selected{7,20,13};
    rejects([&] { (void)batch::plan_ordinary_triangle_batches(fan,selected,constant_only,layout,{19,19,1ULL<<20,1000}); }, "fan retains conservative header/storage admission");
    rejects([&] { (void)batch::plan_ordinary_triangle_batches(fan,selected,constant_only,layout,{32,32,0,1000}); }, "fan control budget is enforced");
    rejects([&] { (void)batch::plan_ordinary_triangle_batches(fan,selected,constant_only,layout,{32,32,1ULL<<20,1}); }, "fan native draw budget is enforced");
    for(const Selection empty : {Selection{0,0,1},Selection{0,20,0}}) {
        auto payload=batch::plan_ordinary_triangle_batches(fan,empty,constant_only,layout,{0,0,0,0});
        require(payload.geometry.empty() && payload.encoded_draws==0,"zero fan draw creates no batch payload");
    }
    rejects([&] { (void)batch::plan_ordinary_triangle_batches(fan,{UINT32_MAX-6,8,1},constant_only,layout,{32,32,1ULL<<20,1000}); }, "fan original array ID overflow is refused");
}
static void cases() {
    auto vertex = rows(32,16), inst = rows(8,16);
    std::vector<Source> sources{{vertex,1,1,0,16,16,0,"vertex"},{inst,2,1,0,16,16,2,"instance"}};
    std::vector<uint32_t> arrays;
    for(uint32_t n=5;n<19;++n) arrays.push_back(n);
    verify({5,arrays.size(),7}, arrays, sources,80,true); //5 vertex rows =>3 primitive children: odd next seam.
    for(uint32_t width : {1u,2u,4u}) {
        const std::vector<uint32_t> ids{7,11,7,7,19,11,23,7,29,31};
        auto bytes=indices(ids,width);
        verify({0,ids.size(),7,bytes,width},ids,sources,80,true);
    }
    auto constant=rows(1,4), divisor=rows(5,16);
    std::vector<Source> constants{{constant,3,2,0,0,4,0,"constant"},{divisor,4,2,0,16,16,3,"divisor3"}};
    const std::vector<uint32_t> high{UINT32_MAX,0x01000001u,42,42,0x80000001u,UINT32_MAX,7,9};
    auto high_bytes=indices(high,4);
    verify({0,high.size(),13,high_bytes,4},high,constants,32,true);
    const std::vector<uint32_t> small{0,1,2,3,4};
    auto bytes=indices(small,4);
    auto one=prepare({0,small.size(),13,bytes,4},constants,96);
    require(one.data->geometry.size()==1 && one.data->blocks.size()==3 && one.data->plan.encoded_draws==3, "single geometry uses real instance blocks rather than per-instance native calls");
    verify({0,small.size(),13,bytes,4},small,constants,96,false);
    // Portable planner remains deliberately conservative relative to actual
    // headerless ABI2: three unique IDs need8+12 bytes at admission.
    const std::vector<uint32_t> tri{1,2,3}; auto tri_bytes=indices(tri,4);
    std::vector<Source> constant_only{constants[0]};
    for (const uint32_t first : {0x01000001u, UINT32_MAX - 7}) {
        std::vector<uint32_t> ids;
        for (uint32_t n=0;n<8;++n) ids.push_back(first+n);
        verify({first,8,13},ids,constant_only,32,true);
    }
    rejects([&] { (void)prepare({UINT32_MAX-6,8,1},constant_only,32); }, "array first+count beyond uint32 original-ID domain is refused");
    rejects([&] { (void)prepare({0,3,1,tri_bytes,4},constant_only,19); }, "retained ABI1 header admission is not broadened to unsupported storage");
    verify({0,3,1,tri_bytes,4},tri,constant_only,20,false);
    for(uint64_t count : {1ULL,2ULL}) {
        std::vector<uint32_t> ids(count,3); auto input=indices(ids,4);
        verify({0,count,1,input,4},ids,constant_only,96,false);
        std::vector<Source> too_short{{{},7,1,0,4,4,0,"invalid-tail"}};
        rejects([&] { (void)prepare({0,count,1,input,4},too_short,96); }, "incomplete strip1/2 still validate original source reads");
    }
    const auto layout=compact_layout(constant_only,30,8,2048);
    auto empty=batch::plan_ordinary_triangle_batches(batch::Topology::TriangleStrip,{0,0,1},constant_only,layout,{0,0,0,0});
    require(empty.selected_count==0 && empty.geometry.empty(), "empty selection creates no lowered owner payload");
    rejects([&] { (void)batch::plan_ordinary_triangle_batches(batch::Topology::TriangleStrip,{0,0,1,{},3},constant_only,layout,{96,96,1ULL<<20,1000}); }, "empty strip still validates invalid index width");
}
static void policy_failure_transaction(batch::Topology topology) {
    CurrentConversions<Record> current;
    OversizedConversions<Record> oversized{2,4096};
    std::map<std::string,Record> history;
    auto old=std::make_shared<Node>(); old->cpu={1,2,3,4};
    current.replace(CurrentCategory::Batch,"old",old);
    history.emplace("old",old);
    const auto bytes=[](const Record& value) {return static_cast<uint64_t>(value->cpu.size());};
    const auto graph=[](const Record& value,auto& visited) {return visited.insert(value.get()).second ? static_cast<uint64_t>(value->cpu.size()) : 0ULL;};
    require(oversized.admit(CurrentCategory::Batch,"old",old,graph),"seed old working owner");
    const auto evictions=oversized.evictions();
    auto constant=rows(1,4);
    std::vector<Source> sources{{constant,1,1,0,0,4,0,"constant"}};
    const auto layout=compact_layout(sources,30,8,2048);
    const Selection selected{7,8,1};
    bool built=false;
    rejects([&] { (void)batch::transactional_conversion(current,oversized,history,CurrentCategory::Batch,"new",[&] {
        built=true;
        auto payload=batch::plan_ordinary_triangle_batches(topology,selected,sources,layout,{32,32,1ULL<<20,1000});
        const auto wrong=batch::expected_ordinary_batch_policy(batch::Topology::Triangles,selected);
        batch::validate_ordinary_batch_policy(topology,payload,wrong);
        return std::make_shared<Node>();
    },bytes,graph); },"actual lowered-policy mismatch throws inside private conversion before cache commit");
    require(built && current.size()==1 && current.find(CurrentCategory::Batch,"old")==old && !current.find(CurrentCategory::Batch,"new") &&
            history.size()==1 && history.at("old")==old && oversized.size()==1 && oversized.peek(CurrentCategory::Batch,"old")==old && oversized.evictions()==evictions,
            "actual policy failure preserves previous current/history/working owners and eviction count");
}
int main() {
    try { routing_and_identity(); cases(); fan_cases();
        policy_failure_transaction(batch::Topology::TriangleStrip);
        policy_failure_transaction(batch::Topology::TriangleFan);
        std::cout<<"PASS ordered strip/fan runtime adapter/ABI2: "<<checks<<" CPU checks; no native/GPU qualification\n"; return 0; }
    catch(const std::exception& error) { std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n'; return 1; }
}
