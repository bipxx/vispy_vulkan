#include "runtime_batch_plan.hpp"
#include <iostream>
#include <tuple>

using namespace vispy::inputs;
namespace b = vispy::inputs::batches;
static uint64_t checks = 0;
static void require(bool condition, const char* message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}
template<class Visit> static void rejects(Visit&& visit, const char* expected) {
    ++checks;
    try { visit(); }
    catch (const std::exception& e) {
        if (std::string(e.what()).find(expected) != std::string::npos) return;
        throw std::runtime_error(std::string("wrong refusal: ") + e.what() + " expected " + expected);
    }
    throw std::runtime_error(std::string("missing refusal: ") + expected);
}
template<class T> static std::vector<uint8_t> bytes(std::initializer_list<T> values) {
    std::vector<uint8_t> result(values.size() * sizeof(T));
    std::memcpy(result.data(), values.begin(), result.size()); return result;
}
static uint32_t word(const std::vector<uint8_t>& data, size_t number) {
    uint32_t result; std::memcpy(&result, data.data() + number * 4, 4); return result;
}
static b::Limits grants(uint64_t buffer = 1024, uint64_t storage = 1024) {
    return {buffer, storage, 1024 * 1024, 100000};
}
using Invocation = std::tuple<uint64_t, uint64_t, uint32_t>;
using Primitive = std::tuple<uint64_t, uint32_t, uint32_t, uint32_t>;
static std::vector<Invocation> original_invocations(const Selection& selection) {
    std::vector<Invocation> result;
    for (uint64_t i = 0; i < selection.instances; ++i)
        for (uint64_t v = 0; v < selection.count; ++v) result.emplace_back(i, v, selection.vertex(v));
    return result;
}
static std::vector<Primitive> original_primitives(const Selection& selection) {
    std::vector<Primitive> result;
    for (uint64_t i = 0; i < selection.instances; ++i)
        for (uint64_t v = 0; v + 2 < selection.count; v += 3)
            result.emplace_back(i, selection.vertex(v), selection.vertex(v + 1), selection.vertex(v + 2));
    return result;
}
struct Trace { std::vector<Invocation> selected; std::vector<Primitive> primitives; };
static Trace decode(const b::Plan& plan, bool wrong_chunk_major = false) {
    Trace result;
    auto draw = [&](const b::DrawRef& ref) {
        const auto& geometry = plan.geometry.at(ref.geometry);
        const auto identity = b::identity_data(plan, ref);
        require(word(identity, 1) == ref.instance_base, "identity header original instance base");
        const auto block = plan.instance_block(ref.instance_block);
        require(block.first + ref.row_offset == ref.instance_base && ref.row_offset + ref.instance_count <= block.count,
                "draw instance row range stays in immutable block");
        auto vertex = [&](uint64_t n) {
            return plan.indexed ? word(identity, 2 + geometry.remapped_indices.at(static_cast<size_t>(n))) :
                static_cast<uint32_t>(word(identity, 0) + n);
        };
        for (uint64_t i = 0; i < ref.instance_count; ++i) {
            for (uint64_t n = 0; n < geometry.element_count; ++n)
                result.selected.emplace_back(word(identity, 1) + i, geometry.element_offset + n, vertex(n));
            for (uint64_t n = 0; n + 2 < geometry.element_count; n += 3)
                result.primitives.emplace_back(word(identity, 1) + i, vertex(n), vertex(n + 1), vertex(n + 2));
        }
    };
    if (!wrong_chunk_major) plan.for_each_draw(draw);
    else for (size_t g = 0; g < plan.geometry.size(); ++g)
        for (uint64_t i = 0; i < plan.instances; ++i)
            draw({g, i, 1, i / plan.instance_rows_per_block, i % plan.instance_rows_per_block});
    return result;
}
static void verify_shape(const b::Plan& plan, const Selection& selected, std::span<const Source> sources) {
    const auto trace = decode(plan);
    require(trace.selected == original_invocations(selected), "selected invocation sequence equals independent unsplit oracle including tails");
    require(trace.primitives == original_primitives(selected), "complete triangle sequence equals independent unsplit oracle");
    require(plan.incomplete_tail == selected.count % 3, "tail count observed separately");
    uint64_t calls = 0;
    plan.for_each_draw([&](const auto&) { ++calls; });
    require(calls == plan.encoded_draws && calls <= plan.limits.max_encoded_draws, "encoded draw budget and implicit schedule agree");
    for (size_t g = 0; g < plan.geometry.size(); ++g) {
        const auto& geometry = plan.geometry[g];
        require(geometry.element_offset % 3 == 0, "geometry starts on original triangle boundary");
        if (g + 1 != plan.geometry.size()) require(geometry.element_count % 3 == 0, "only last chunk may contain incomplete atom");
        if (plan.indexed) {
            require(geometry.remapped_indices.size() * 4 <= plan.limits.buffer_bytes, "remapped index grant");
            require(8 + geometry.original_vertices.size() * 4 <= plan.limits.storage_bytes, "identity table includes eight-byte header");
        }
        for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot) {
            const auto& stream = plan.layout.streams[slot];
            if (!stream.instance) {
                const auto packed = b::pack_vertex_stream(plan, g, slot, sources);
                require(packed.size() == b::vertex_rows(plan, geometry) * stream.stride && packed.size() <= plan.limits.buffer_bytes,
                        "every physical vertex stream obeys byte grant");
            }
        }
    }
    for (uint64_t block = 0; block < plan.instance_block_count; ++block)
        for (size_t slot = 0; slot < plan.layout.streams.size(); ++slot)
            if (plan.layout.streams[slot].instance) {
                const auto packed = b::pack_instance_stream(plan, block, slot, sources);
                require(packed.size() <= plan.limits.buffer_bytes, "every physical instance stream obeys byte grant");
            }
}

// An independent scalar, all-overlapping-fragment model. It is an order oracle,
// not a GPU/raster reference: source-over blend, LESS_EQUAL depth, and stencil
// increment/decrement on depth pass/fail are deliberately noncommutative.
struct RasterState {
    uint32_t blend = 0, depth = UINT32_MAX, depth_color = 0, stencil = 0;
    bool operator==(const RasterState&) const = default;
};
static RasterState simulate(const std::vector<Primitive>& primitives) {
    RasterState state;
    for (const auto& [instance, a, c, last] : primitives) {
        const uint32_t color = static_cast<uint32_t>((instance * 71 + a * uint64_t(13) + c * uint64_t(7) + last) % 251);
        const uint32_t depth = last % 4;
        state.blend = (state.blend + color) / 2;
        if (depth <= state.depth) {
            state.depth = depth; state.depth_color = color; state.stencil = (state.stencil + 1) & 255;
        } else state.stencil = (state.stencil - 1) & 255;
    }
    return state;
}

static void boundaries_and_identity() {
    const auto constant = bytes<uint32_t>({0xFEDCBA98});
    const std::vector<Source> fields{{constant,1,1,0,0,4,0,"constant"}};
    const auto layout = compact_layout(fields, 32, 8, 2048);
    const Selection first{16777217, 6, 3};
    const auto exact = b::plan_triangle_list(first, fields, layout, grants(24, 8));
    require(exact.geometry.size() == 1 && exact.encoded_draws == 1, "exact affine buffer and constant-size header fit");
    verify_shape(exact, first, fields);
    const auto split = b::plan_triangle_list(first, fields, layout, grants(23, 8));
    require(split.geometry.size() == 2 && split.encoded_draws == 6, "one byte less splits complete triangles instance-major");
    verify_shape(split, first, fields);
    const auto packed = b::pack_vertex_stream(split, 1, 0, fields);
    for (size_t n = 0; n < packed.size()/4; ++n) require(word(packed,n) == 0xFEDCBA98, "constant stride zero retains exact bits");
    rejects([&] { b::plan_triangle_list(first, fields, layout, grants(24,7)); }, "eight granted bytes");
    rejects([&] { b::plan_triangle_list(first, fields, layout, grants(11,8)); }, "complete triangle");

    const auto sparse = bytes<uint32_t>({UINT32_MAX, 16777217, 7, UINT32_MAX, 16777217, 7});
    const Selection indexed{0,6,2,sparse,4};
    const auto s = b::plan_triangle_list(indexed, fields, layout, grants(24,20));
    require(s.geometry.size() == 1 && s.geometry[0].original_vertices == std::vector<uint32_t>({UINT32_MAX,16777217,7}),
            "sparse high IDs use stable unique table without dense maximum allocation");
    verify_shape(s,indexed,fields);
    rejects([&] { b::plan_triangle_list(indexed, fields, layout, grants(24,19)); }, "one selected primitive");
    const auto same = bytes<uint8_t>({255,255,255,255,255,255,255,255,255});
    const Selection repeat{0,9,2,same,1};
    const auto repeated = b::plan_triangle_list(repeat,fields,layout,grants(24,12));
    require(repeated.geometry.size() == 2 && repeated.geometry[0].element_count == 6 && repeated.geometry[1].element_count == 3,
            "index-only overflow splits repeated IDs despite one-row identity tables");
    verify_shape(repeated,repeat,fields);
    const auto wide = bytes<uint16_t>({UINT16_MAX,UINT16_MAX,UINT16_MAX});
    verify_shape(b::plan_triangle_list({0,3,1,wide,2},fields,layout,grants(12,12)),{0,3,1,wide,2},fields);

    auto budget = grants(24,20); budget.max_control_bytes = s.control_bytes;
    require(b::plan_triangle_list(indexed,fields,layout,budget).control_bytes == s.control_bytes,"exact charged control budget succeeds");
    --budget.max_control_bytes;
    rejects([&] { b::plan_triangle_list(indexed,fields,layout,budget); },"control-byte budget");
    budget = grants(23,8); budget.max_encoded_draws = 6;
    require(b::plan_triangle_list(first,fields,layout,budget).encoded_draws == 6,"exact encoded draw budget succeeds");
    --budget.max_encoded_draws;
    rejects([&] { b::plan_triangle_list(first,fields,layout,budget); },"encoded-draw budget");

    const auto vectors = bytes<uint32_t>({1,2,3,4});
    const std::vector<Source> vector_field{{vectors,2,1,0,0,16,0,"vec4"}};
    const auto vector_layout = compact_layout(vector_field,32,8,2048);
    require(b::plan_triangle_list({0,3,1},vector_field,vector_layout,grants(48,8)).geometry.size()==1,"exact vertex row bytes succeed");
    rejects([&] { b::plan_triangle_list({0,3,1},vector_field,vector_layout,grants(47,8)); },"complete triangle");
}

static void instance_blocks_and_divisors() {
    const auto vertex = bytes<uint32_t>({99});
    const auto source2 = bytes<uint32_t>({10,20,30,40});
    const auto source3 = bytes<uint32_t>({101,202,303});
    const std::vector<Source> fields{{vertex,1,1,0,0,4,0,"vertex"},
        {source2,2,1,0,4,4,2,"divisor2"},{source3,3,1,0,4,4,3,"divisor3"}};
    const auto layout=compact_layout(fields,32,8,2048);
    const Selection selected{100,3,7};
    const auto plan=b::plan_triangle_list(selected,fields,layout,grants(20,8));
    require(plan.instance_rows_per_block==2 && plan.instance_block_count==4 && plan.encoded_draws==4,"instance capacity creates bounded consecutive blocks");
    verify_shape(plan,selected,fields);
    for(uint64_t block=0;block<plan.instance_block_count;++block){
        const auto range=plan.instance_block(block);
        const auto packed=b::pack_instance_stream(plan,block,1,fields);
        for(uint64_t row=0;row<range.count;++row){
            const uint64_t original=range.first+row;
            require(word(packed,static_cast<size_t>(row*2))==(original/2+1)*10,"divisor two uses original instance across block boundary");
            require(word(packed,static_cast<size_t>(row*2+1))==(original/3+1)*101,"divisor three uses original instance across block boundary");
        }
    }
    const Selection both{100,6,7};
    const auto split=b::plan_triangle_list(both,fields,layout,grants(20,8));
    require(split.geometry.size()==2 && split.encoded_draws==14,"geometry splits force one-instance native calls");
    verify_shape(split,both,fields);
    const auto original=original_primitives(both);
    require(simulate(decode(split).primitives)==simulate(original),"blend depth stencil order model matches unsplit oracle");
    const auto wrong=decode(split,true);
    require(wrong.primitives!=original && !(simulate(wrong.primitives)==simulate(original)),"order oracle rejects all-instances-of-A-then-B regression");
}

static void tails_zero_and_refusals() {
    const auto constant=bytes<uint32_t>({42});
    const std::vector<Source> fields{{constant,1,1,0,0,4,0,"field"}};
    const auto layout=compact_layout(fields,32,8,2048);
    for(uint64_t count=1;count<12;++count){
        const Selection selected{19,count,2};
        const auto plan=b::plan_triangle_list(selected,fields,layout,grants(12,8));
        verify_shape(plan,selected,fields);
    }
    const auto finite=bytes<uint32_t>({1,2,3});
    const std::vector<Source> short_fields{{finite,1,1,0,4,4,0,"tail"}};
    const auto short_layout=compact_layout(short_fields,32,8,2048);
    rejects([&]{b::plan_triangle_list({0,4,1},short_fields,short_layout,grants(12,8));},"ATTRIBUTE tail");
    const auto index_tail=bytes<uint32_t>({0,1,2,99});
    rejects([&]{b::plan_triangle_list({0,4,1,index_tail,4},short_fields,short_layout,grants(20,20));},"ATTRIBUTE tail");
    require(b::plan_triangle_list({0,0,INT32_MAX},{},{},{}).geometry.empty(),"zero count needs no converted layout or ABI grant");
    require(b::plan_triangle_list({0,INT32_MAX,0},short_fields,{},{}).geometry.empty(),"zero instances do not read out-of-bounds attribute");
    rejects([&]{b::plan_triangle_list({UINT32_MAX,2,0},{},{},{});},"identity exceeds uint32");
    rejects([&]{b::plan_triangle_list({0,uint64_t(INT32_MAX)+1,0},{},{},{});},"native draw limit");
    rejects([&]{b::plan_triangle_list({0,4,1,index_tail,3},fields,layout,grants());},"unsupported index width");
    rejects([&]{b::plan_triangle_list({0,5,1,index_tail,4},fields,layout,grants());},"index selection");
    auto malformed=layout;malformed.offsets[0]=4;
    rejects([&]{b::plan_triangle_list({0,3,1},fields,malformed,grants());},"field map");
    auto huge=grants(12,8);huge.max_encoded_draws=8;
    rejects([&]{b::plan_triangle_list({0,INT32_MAX,1},fields,layout,huge);},"encoded-draw budget");
    rejects([&]{b::plan_triangle_list({0,6,INT32_MAX},fields,layout,huge);},"encoded-draw budget");
    huge=grants(12,8);huge.max_encoded_draws=UINT64_MAX;huge.max_control_bytes=512;
    rejects([&]{b::plan_triangle_list({0,INT32_MAX,1},fields,layout,huge);},"control-byte budget");
    rejects([&]{(void)b::multiply(UINT64_MAX,2);},"multiplication overflow");
    rejects([&]{(void)b::add(UINT64_MAX,1);},"addition overflow");

    const auto empty_layout=compact_layout({},0,0,0);
    const auto no_fields=b::plan_triangle_list({77,12,3},{},empty_layout,grants(8,8));
    verify_shape(no_fields,{77,12,3},{});
    require(no_fields.geometry.size()==1,"affine count is not constrained by constant header storage rows");
}

static void deterministic_matrix() {
    const auto constant=bytes<uint32_t>({0x7FC00001});
    const auto instances=bytes<uint32_t>({100,200,300,400});
    const std::vector<Source> fields{{constant,1,9,0,0,4,0,"bits"},{instances,2,4,0,4,4,2,"instance"}};
    const auto layout=compact_layout(fields,32,8,2048);
    for(uint64_t count=1;count<=18;++count)
        for(uint64_t instance_count=1;instance_count<=7;++instance_count)
            for(uint64_t capacity : {uint64_t(3),uint64_t(4),uint64_t(6)}){
                const Selection arrays{16777217,count,instance_count};
                verify_shape(b::plan_triangle_list(arrays,fields,layout,grants(capacity*4,8)),arrays,fields);
                std::vector<uint8_t> indices(static_cast<size_t>(count*4));
                for(uint64_t n=0;n<count;++n){
                    const uint32_t value=n%5==0 ? UINT32_MAX : n%3==0 ? 16777217 : static_cast<uint32_t>(n%4);
                    std::memcpy(indices.data()+n*4,&value,4);
                }
                const Selection indexed{0,count,instance_count,indices,4};
                verify_shape(b::plan_triangle_list(indexed,fields,layout,grants(capacity*4+8,capacity*4+8)),indexed,fields);
            }
}

static void multiple_physical_streams() {
    std::vector<uint8_t> vertex16(160,0xA5),vertex12(192,0xA5),instance16(100,0xA5),instance8(64,0xA5);
    auto store=[](auto& data,size_t offset,uint32_t value){std::memcpy(data.data()+offset,&value,4);};
    for(uint32_t row=0;row<7;++row){
        for(uint32_t lane=0;lane<4;++lane){
            const uint32_t value=lane==0 ? 0x7FC00001u+row : lane==1 ? 0x80000000u : lane==2 ? UINT32_MAX-row : 0x3F800000u+row;
            store(vertex16,4+row*20+lane*4,value);
        }
        for(uint32_t lane=0;lane<3;++lane)store(vertex12,8+row*24+lane*4,lane==0 ? 0x01000001u+row : lane==1 ? 0x7F800001u : 0xFF800000u);
    }
    for(uint32_t row=0;row<4;++row)
        for(uint32_t lane=0;lane<4;++lane)store(instance16,4+row*20+lane*4,0xF0000000u+row*16+lane);
    for(uint32_t row=0;row<3;++row){store(instance8,8+row*16,0x7FC00005u+row);store(instance8,12+row*16,0x80000000u);}
    const std::vector<Source> fields{{vertex16,11,3,4,20,16,0,"v16"},{vertex12,12,4,8,24,12,0,"v12"},
        {instance16,13,5,4,20,16,2,"i16"},{instance8,14,6,8,16,8,3,"i8"}};
    const auto layout=compact_layout(fields,32,4,16);
    require(layout.streams.size()==4 && !layout.streams[0].instance && !layout.streams[1].instance &&
        layout.streams[2].instance && layout.streams[3].instance,"stride sixteen yields two physical streams in each step domain");
    const Selection selected{1,6,7};
    const auto plan=b::plan_triangle_list(selected,fields,layout,grants(48,8));
    require(plan.geometry.size()==2 && plan.instance_rows_per_block==3 && plan.instance_block_count==3,
        "capacity is minimum across different-width physical vertex and instance streams");
    verify_shape(plan,selected,fields);
    auto compare_field=[&](const std::vector<uint8_t>& packed,uint64_t row,size_t field,uint64_t original){
        const auto& source=fields[field];
        for(uint64_t lane=0;lane<source.element_bytes/4;++lane){
            uint32_t expected;const auto offset=source.offset+original*source.stride+lane*4;
            std::memcpy(&expected,source.bytes.data()+offset,4);
            require(word(packed,static_cast<size_t>(row*(source.element_bytes/4)+lane))==expected,
                "every packed physical-stream word preserves original offset stride NaN minus-zero and integer bits");
        }
    };
    for(size_t g=0;g<plan.geometry.size();++g)
        for(size_t field=0;field<2;++field){
            const auto packed=b::pack_vertex_stream(plan,g,layout.slots[field],fields);
            for(uint64_t row=0;row<plan.geometry[g].element_count;++row)
                compare_field(packed,row,field,plan.geometry[g].vertex_base+row);
        }
    for(uint64_t block=0;block<plan.instance_block_count;++block)
        for(size_t field=2;field<4;++field){
            const auto range=plan.instance_block(block);
            const auto packed=b::pack_instance_stream(plan,block,layout.slots[field],fields);
            for(uint64_t row=0;row<range.count;++row)compare_field(packed,row,field,(range.first+row)/fields[field].divisor);
        }
    rejects([&]{b::plan_triangle_list(selected,fields,layout,grants(47,8));},"complete triangle");
    const Selection one_geometry{1,3,7};
    const auto exact=b::plan_triangle_list(one_geometry,fields,layout,grants(64,8));
    const auto below=b::plan_triangle_list(one_geometry,fields,layout,grants(63,8));
    require(exact.instance_block_count==2 && below.instance_block_count==3,"one byte below instance-row boundary adds block without changing original IDs");
    verify_shape(exact,one_geometry,fields);verify_shape(below,one_geometry,fields);
    const auto probe=b::DrawRef{0,0,0,0,0};
    rejects([&]{b::identity_data(exact,probe);},"identity instance range");
    std::cout<<"OBSERVE multistream affine: widths=16,12/16,8 buffer=48 storage=8 geometry=2 instance-blocks=3 native-calls=14\n";
    std::cout<<"OBSERVE multistream instance boundary: buffer=64/63 geometry=1 instance-blocks=2/3 native-calls=2/3\n";
}

struct Prepared { b::Plan plan; std::vector<std::vector<uint8_t>> vertices; };
static void publication_and_owned_selection() {
    const auto constant=bytes<uint32_t>({9});
    const std::vector<Source> fields{{constant,1,1,0,0,4,0,"constant"}};
    const auto layout=compact_layout(fields,32,8,2048);
    auto indices=bytes<uint32_t>({UINT32_MAX,3,7,9,3,7});
    const Selection selected{0,6,2,indices,4};
    const auto plan=b::plan_triangle_list(selected,fields,layout,grants(20,20));
    const auto retained=decode(plan);
    std::fill(indices.begin(),indices.end(),uint8_t(0));
    require(decode(plan).selected==retained.selected,"plan owns selected IDs independently of mutable input index span");
    std::shared_ptr<const Prepared> current=std::make_shared<const Prepared>(Prepared{plan,{}});
    const auto previous=current;
    rejects([&]{b::prepare_and_publish(current,[&]{
        Prepared next{plan,{}};
        next.vertices.push_back(b::pack_vertex_stream(plan,0,0,fields));
        throw std::runtime_error("injected late child build failure");
        return next;
    });},"late child build");
    require(current==previous && current->vertices.empty(),"late conversion failure preserves previous complete prototype owner");
    b::prepare_and_publish(current,[&]{
        Prepared next{plan,{}};
        for(size_t g=0;g<plan.geometry.size();++g)next.vertices.push_back(b::pack_vertex_stream(plan,g,0,fields));
        return next;
    });
    require(current!=previous && current->vertices.size()==plan.geometry.size(),"all child conversions publish as one prototype owner");
}

void ordered_stencil_faces_contract() {
    using namespace vispy::inputs::batches;
    Plan p; p.instances = 2; p.instance_rows_per_block = 2; p.instance_block_count = 1;
    p.limits.max_encoded_draws = 100;
    GeometryBatch g; g.element_count = 7; p.geometry.push_back(g);
    std::vector<StencilDrawRef> draws;
    for_each_stencil_draw(p, [&](const auto& d) { draws.push_back(d); });
    require(draws.size() == 10 && stencil_face_draw_count(p) == 10, "two triangles twice plus tail per instance");
    for (size_t n = 0; n < draws.size(); ++n) {
        const auto& d = draws[n]; const auto local = n % 5;
        require(d.draw.instance_base == n / 5 && d.draw.instance_count == 1 && d.draw.row_offset == n / 5, "instance-major, no block coalescing");
        require(d.first == (local < 2 ? 0 : local < 4 ? 3 : 6) && d.count == (local == 4 ? 1 : 3) && d.face == (local < 4 ? local % 2 : 0), "exact first/count/face order");
    }
    p.limits.max_encoded_draws = 9; bool called = false, refused = false;
    try { for_each_stencil_draw(p, [&](const auto&) { called = true; }); } catch (const std::length_error&) { refused = true; }
    require(refused && !called, "expanded budget refusal precedes all encoding");
    p.instances = 0;
    require(stencil_face_draw_count(p) == 0, "zero-instance no calls");
}

int main() {
    try {
        ordered_stencil_faces_contract();
        boundaries_and_identity();instance_blocks_and_divisors();tails_zero_and_refusals();
        deterministic_matrix();multiple_physical_streams();publication_and_owned_selection();
        std::cout << "PASS triangle-list batch planner: " << checks << " checks; portable CPU only; identity ABI " << b::identity_abi << '\n';
        return 0;
    } catch(const std::exception& e) {
        std::cerr << "FAIL after " << checks << " checks: " << e.what() << '\n';return 1;
    }
}
