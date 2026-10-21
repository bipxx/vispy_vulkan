#include "runtime_batch_topology.hpp"
#include <iostream>
#include <tuple>

using namespace vispy::inputs;
namespace b=vispy::inputs::batches;
static uint64_t checks=0, plans=0;
static void require(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F> static void rejects(F&& f,const char* reason){
    ++checks;try{f();}catch(const std::exception& e){
        if(std::string(e.what()).find(reason)!=std::string::npos)return;
        throw std::runtime_error(std::string("wrong refusal: ")+e.what()+" expected "+reason);
    }throw std::runtime_error(std::string("missing refusal: ")+reason);
}
static b::Limits grants(uint64_t buffer=48,uint64_t storage=48){return{buffer,storage,8*1024*1024,100000};}
static uint32_t word(const std::vector<uint8_t>& bytes,size_t n){uint32_t v;std::memcpy(&v,bytes.data()+n*4,4);return v;}
static std::vector<uint8_t> indices(const std::vector<uint32_t>& values,uint32_t width){
    std::vector<uint8_t> result(values.size()*width);
    for(size_t n=0;n<values.size();++n){
        if(width==1)result[n]=static_cast<uint8_t>(values[n]);
        else if(width==2){const auto v=static_cast<uint16_t>(values[n]);std::memcpy(result.data()+n*2,&v,2);}
        else std::memcpy(result.data()+n*4,&values[n],4);
    }return result;
}
struct Expected{
    uint64_t instance=0,run=0,ordinal=0;
    std::array<uint32_t,3> ids{};
    uint32_t width=0,last=0,previous=0,next=0;
    bool odd=false,closes=false,has_previous=false,has_next=false;
    bool operator==(const Expected&)const=default;
};
static uint32_t width_of(b::Topology t){
    if(t==b::Topology::Points)return 1;
    if(t==b::Topology::Lines||t==b::Topology::LineStrip||t==b::Topology::LineLoop)return 2;
    return 3;
}
// Independent unsplit oracle materializes only the bounded test inputs.
// It does not call the planner's run/count/origin/enumeration helpers.
static std::vector<Expected> oracle(b::Topology topology,const std::vector<uint32_t>& selected,
                                    uint64_t instances,b::RestartPolicy restart,uint32_t index_width){
    std::vector<std::vector<uint32_t>> runs(1);
    uint32_t marker=restart.index;
    if(restart.mode==b::RestartMode::FixedIndex)marker=index_width==1?255u:index_width==2?65535u:UINT32_MAX;
    for(uint32_t id:selected){
        if(index_width&&restart.mode!=b::RestartMode::Disabled&&id==marker)runs.emplace_back();
        else runs.back().push_back(id);
    }
    std::vector<Expected> result;
    for(uint64_t instance=0;instance<instances;++instance)for(size_t r=0;r<runs.size();++r){
        const auto& ids=runs[r];uint64_t ordinal=0;
        auto emit=[&](std::array<uint32_t,3> v,uint32_t w,bool odd=false,bool closes=false,
                      bool has_previous=false,uint32_t previous=0,bool has_next=false,uint32_t next=0){
            result.push_back({instance,r,ordinal++,v,w,v[w-1],previous,next,odd,closes,has_previous,has_next});
        };
        if(topology==b::Topology::Points){for(uint32_t id:ids)emit({id,0,0},1);}
        else if(topology==b::Topology::Lines){for(size_t n=0;n+1<ids.size();n+=2)emit({ids[n],ids[n+1],0},2);}
        else if(topology==b::Topology::Triangles){for(size_t n=0;n+2<ids.size();n+=3)emit({ids[n],ids[n+1],ids[n+2]},3);}
        else if(topology==b::Topology::TriangleStrip){for(size_t n=2;n<ids.size();++n){
            const bool odd=n%2!=0;emit(odd?std::array<uint32_t,3>{ids[n-1],ids[n-2],ids[n]}:
                std::array<uint32_t,3>{ids[n-2],ids[n-1],ids[n]},3,odd);
        }}
        else if(topology==b::Topology::TriangleFan){for(size_t n=2;n<ids.size();++n)emit({ids.front(),ids[n-1],ids[n]},3);}
        else if(ids.size()>1){
            const bool loop=topology==b::Topology::LineLoop;
            const auto count=loop?ids.size():ids.size()-1;
            for(size_t n=0;n<count;++n){
                const bool previous=loop||n!=0,next=loop||n+2<ids.size();
                emit({ids[n],ids[(n+1)%ids.size()],0},2,false,loop&&n+1==ids.size(),
                    previous,previous?ids[(n+ids.size()-1)%ids.size()]:0,next,next?ids[(n+2)%ids.size()]:0);
            }
        }
    }return result;
}
static std::vector<Expected> decode(const b::TopologyPlan& topology,bool wrong_chunk_major=false){
    std::vector<Expected> result;const auto& plan=topology.payload;const auto width=width_of(topology.original_topology);
    auto draw=[&](const b::DrawRef& ref){
        const auto& geometry=plan.geometry.at(ref.geometry);const auto identity=b::identity_data(plan,ref);
        const auto& metadata=topology.origins.at(ref.geometry);
        require(metadata.size()==geometry.element_count/width,"one origin per complete primitive, no bridged tail");
        for(uint64_t instance=0;instance<ref.instance_count;++instance)for(size_t n=0;n<metadata.size();++n){
            const auto& source=metadata[n];std::array<uint32_t,3> ids{};
            for(uint32_t k=0;k<width;++k){const auto position=n*width+k;
                ids[k]=plan.indexed?word(identity,2+geometry.remapped_indices.at(position)):
                    static_cast<uint32_t>(word(identity,0)+position);
            }
            require(ids[width-1]==source.last,"LAST is original final corner after parity repair");
            result.push_back({word(identity,1)+instance,source.run,source.ordinal,ids,width,source.last,source.previous,
                source.next,source.odd_strip,source.closes_loop,source.has_previous,source.has_next});
        }
    };
    if(!wrong_chunk_major)plan.for_each_draw(draw);
    else for(size_t geometry=0;geometry<plan.geometry.size();++geometry)for(uint64_t i=0;i<plan.instances;++i)
        draw({geometry,i,1,i/plan.instance_rows_per_block,i%plan.instance_rows_per_block});
    return result;
}
struct State {uint32_t blend=0,depth=UINT32_MAX,depth_color=0,stencil=0;bool operator==(const State&)const=default;};
static State scalar_state(const std::vector<Expected>& primitives){
    State result;
    for(const auto& p:primitives){
        const auto color=static_cast<uint32_t>((p.instance*71+p.ids[0]*uint64_t(13)+p.ids[1]*uint64_t(7)+p.last)%251);
        const auto depth=p.last%4;
        result.blend=(result.blend+color)/2;
        if(depth<=result.depth){result.depth=depth;result.depth_color=color;result.stencil=(result.stencil+1)&255;}
        else result.stencil=(result.stencil-1)&255;
    }return result;
}
static void verify(b::Topology topology,const Selection& selection,const std::vector<uint32_t>& original,
                    std::span<const Source> fields,const Layout& layout,b::Limits limits,b::RestartPolicy restart={}){
    const auto result=b::plan_topology(topology,selection,fields,layout,limits,restart);++plans;
    require(decode(result)==oracle(topology,original,selection.instances,restart,selection.index_bytes),"rendered primitive/order/identity/adjacency equals independent oracle");
    uint64_t calls=0;result.payload.for_each_draw([&](const auto&){++calls;});
    require(calls==result.payload.encoded_draws&&calls<=limits.max_encoded_draws,"actual implicit draw schedule bounded");
    require(result.payload.control_bytes<=limits.max_control_bytes,"complete logical control charge bounded");
    require(result.original_count==selection.count&&result.source_indexed==(selection.index_bytes!=0),"original selection identity retained");
    for(size_t g=0;g<result.payload.geometry.size();++g){const auto& geometry=result.payload.geometry[g];
        require(geometry.remapped_indices.size()*4<=limits.buffer_bytes,"index buffer bound");
        if(result.payload.indexed)require(8+geometry.original_vertices.size()*4<=limits.storage_bytes,"identity header plus table storage bound");
        for(size_t slot=0;slot<layout.streams.size();++slot)if(!layout.streams[slot].instance){
            const auto packed=b::pack_vertex_stream(result.payload,g,slot,fields);
            require(packed.size()<=limits.buffer_bytes,"each physical vertex stream bounded");
            for(uint64_t row=0;row<b::vertex_rows(result.payload,geometry);++row){
                const auto id=result.payload.indexed?geometry.original_vertices.at(static_cast<size_t>(row)):geometry.vertex_base+row;
                for(size_t field:layout.streams[slot].fields){const auto& source=fields[field];
                    const auto at=source.offset+id*source.stride;
                    require(std::memcmp(packed.data()+row*layout.streams[slot].stride+layout.offsets[field],
                        source.bytes.data()+at,static_cast<size_t>(source.element_bytes))==0,"every vertex field bit preserved");
                }
            }
        }
    }
    for(uint64_t block=0;block<result.payload.instance_block_count;++block)for(size_t slot=0;slot<layout.streams.size();++slot)
        if(layout.streams[slot].instance&&!result.payload.geometry.empty()){
            const auto packed=b::pack_instance_stream(result.payload,block,slot,fields);const auto range=result.payload.instance_block(block);
            require(packed.size()<=limits.buffer_bytes,"each instance stream bounded");
            for(uint64_t row=0;row<range.count;++row)for(size_t field:layout.streams[slot].fields){const auto& source=fields[field];
                const auto at=source.offset+((range.first+row)/source.divisor)*source.stride;
                require(std::memcmp(packed.data()+row*layout.streams[slot].stride+layout.offsets[field],
                    source.bytes.data()+at,static_cast<size_t>(source.element_bytes))==0,"divisor origin preserved across blocks");
            }
        }
}
static void matrix(){
    const std::array<b::Topology,7> modes{b::Topology::Points,b::Topology::Lines,b::Topology::LineStrip,b::Topology::LineLoop,
        b::Topology::Triangles,b::Topology::TriangleStrip,b::Topology::TriangleFan};
    std::array<uint32_t,1> constant{0x80000000u};std::array<uint32_t,4> inst{0x7FC00001u,0xFFFFFFFFu,0x01000001u,0};
    const std::vector<Source> fields{{{reinterpret_cast<const uint8_t*>(constant.data()),sizeof(constant)},1,1,0,0,4,0,"bits"},
        {{reinterpret_cast<const uint8_t*>(inst.data()),sizeof(inst)},2,1,0,4,4,2,"instance"}};
    const auto layout=compact_layout(fields,32,8,2048);
    for(auto mode:modes)for(uint64_t count=0;count<=12;++count)for(uint32_t width:{0u,1u,2u,4u})
        for(auto restart:std::array<b::RestartPolicy,3>{{{}, {b::RestartMode::Index,17}, {b::RestartMode::FixedIndex,0}}})
            for(uint64_t instance_count:{1ull,7ull})for(uint64_t cap:{24ull,48ull}){
                std::vector<uint32_t> ids;
                for(uint64_t n=0;n<count;++n){
                    uint32_t id=static_cast<uint32_t>(n+1);
                    if(width&&n%5==1)id=17;
                    if(width&&n%7==3)id=width==1?255u:width==2?65535u:UINT32_MAX;
                    ids.push_back(width?id:static_cast<uint32_t>(16777217+n));
                }
                const auto raw=indices(ids,width?width:4);
                verify(mode,{16777217,count,instance_count,raw,width},ids,fields,layout,grants(cap,cap),restart);
            }
}
static void boundaries_and_carry(){
    const std::array<uint32_t,1> bits{0x7FC00001u};
    const std::vector<Source> fields{{{reinterpret_cast<const uint8_t*>(bits.data()),sizeof(bits)},1,1,0,0,4,0,"constant"}};
    const auto layout=compact_layout(fields,32,8,2048);
    const std::vector<uint32_t> ids{9,3,5,8,13,21};const auto raw=indices(ids,4);const Selection selection{0,ids.size(),3,raw,4};
    for(auto mode:{b::Topology::TriangleStrip,b::Topology::TriangleFan,b::Topology::LineStrip,b::Topology::LineLoop}){
        const uint64_t cap=width_of(mode)==3?20:16;
        verify(mode,selection,ids,fields,layout,grants(cap,cap));
        const auto result=b::plan_topology(mode,selection,fields,layout,grants(cap,cap));
        require(result.payload.geometry.size()>1,"tiny grant forces an actual seam");
        require(decode(result)!=decode(result,true),"wrong chunk-major all-instance order is detected");
        const auto expected=oracle(mode,ids,selection.instances,{},selection.index_bytes);
        require(scalar_state(decode(result))==scalar_state(expected),"independent overlapping blend/depth/stencil scalar oracle agrees");
        require(!(scalar_state(decode(result,true))==scalar_state(expected)),"scalar oracle detects wrong chunk-major order");
        auto exact=grants(cap,cap);exact.max_control_bytes=result.payload.control_bytes;
        require(b::plan_topology(mode,selection,fields,layout,exact).payload.control_bytes==exact.max_control_bytes,"exact complete control charge admitted");
        --exact.max_control_bytes;rejects([&]{(void)b::plan_topology(mode,selection,fields,layout,exact);},"control-byte budget");
        auto calls=grants(cap,cap);calls.max_encoded_draws=result.payload.encoded_draws;
        require(b::plan_topology(mode,selection,fields,layout,calls).payload.encoded_draws==calls.max_encoded_draws,"exact draw budget admitted");
        --calls.max_encoded_draws;rejects([&]{(void)b::plan_topology(mode,selection,fields,layout,calls);},"encoded-draw budget");
    }
    const auto strip=b::plan_topology(b::Topology::TriangleStrip,selection,fields,layout,grants(20,20));
    const auto tuples=decode(strip);
    require(tuples[1].ids==std::array<uint32_t,3>{5,3,8}&&tuples[1].last==8&&tuples[1].odd,"odd seam winding swaps first two only");
    const auto loop=b::plan_topology(b::Topology::LineLoop,selection,fields,layout,grants(16,16));
    const auto lines=decode(loop);require(lines[5].ids==std::array<uint32_t,3>{21,9,0}&&lines[5].closes&&
        lines[5].previous==13&&lines[5].next==3,"single closure keeps both join neighbours at wrap seam");
    rejects([&]{(void)b::plan_topology(b::Topology::TriangleStrip,selection,fields,layout,grants(20,19));},"one primitive");
    for(auto mode:{b::Topology::Points,b::Topology::Lines}){
        const std::vector<uint32_t> affine_ids{16777217,16777218,16777219,16777220,16777221,16777222};
        const Selection affine{16777217,affine_ids.size(),3};
        verify(mode,affine,affine_ids,fields,layout,grants(8,8));
        require(!b::plan_topology(mode,affine,fields,layout,grants(8,8)).payload.indexed,
            "affine independent lists retain eight-byte-only storage rather than requiring an indexed table");
    }
}
static void restart_tails_and_bounds(){
    std::array<uint32_t,5> values{0,1,2,3,4};
    const std::vector<Source> fields{{{reinterpret_cast<const uint8_t*>(values.data()),sizeof(values)},1,1,0,4,4,0,"position"}};
    const auto layout=compact_layout(fields,32,8,2048);
    const std::vector<uint32_t> ids{UINT32_MAX,0,1,UINT32_MAX,UINT32_MAX,2,3,4,UINT32_MAX};
    auto raw=indices(ids,4);const Selection selected{0,ids.size(),1,raw,4};
    const b::RestartPolicy restart{b::RestartMode::FixedIndex,0};
    verify(b::Topology::TriangleStrip,selected,ids,fields,layout,grants(20,20),restart);
    const auto result=b::plan_topology(b::Topology::TriangleStrip,selected,fields,layout,grants(20,20),restart);
    require(result.restart_markers==4&&result.runs.size()==5&&result.runs[1].incomplete_count==2&&
        result.runs[1].incomplete_ids==std::array<uint32_t,2>{0,1},"restart resets assembly and owns tiny incomplete runs");
    require(decode(result).size()==1&&decode(result)[0].ids==std::array<uint32_t,3>{2,3,4},"no primitive crosses restart marker");
    rejects([&]{(void)b::plan_topology(b::Topology::TriangleStrip,selected,fields,layout,grants());},"position");
    const auto saved=decode(result);std::fill(raw.begin(),raw.end(),uint8_t(0));require(decode(result)==saved,"batch IDs and seam metadata own their index revision");
    const std::vector<uint32_t> tail_ids{0,1,9};const auto tail_raw=indices(tail_ids,4);
    rejects([&]{(void)b::plan_topology(b::Topology::Lines,{0,3,1,tail_raw,4},fields,layout,grants());},"position");
    const std::vector<uint32_t> markers{UINT32_MAX,UINT32_MAX};const auto only=indices(markers,4);
    const auto empty=b::plan_topology(b::Topology::TriangleStrip,{0,2,1,only,4},{},{},grants(0,0),restart);
    require(empty.payload.geometry.empty()&&empty.restart_markers==2,"restart-only selection has no ABI payload or draw");
    const auto zero=b::plan_topology(b::Topology::TriangleStrip,{0,1234,0},{},{},{});
    require(zero.payload.geometry.empty()&&zero.payload.control_bytes==0,"zero instances need no source layout budget or ABI");
    auto limited=grants();limited.max_control_bytes=256;
    rejects([&]{(void)b::plan_topology(b::Topology::TriangleStrip,{0,INT32_MAX,1},{},{},limited);},"control-byte budget");
    rejects([&]{(void)b::plan_topology(static_cast<b::Topology>(99),{0,0,0},{},{},{});},"unsupported topology");
}
static void multistream(){
    std::array<uint32_t,4> vertex{0x7FC00001u,0x80000000u,UINT32_MAX,0x01000001u};
    std::array<uint32_t,16> instances{};for(size_t n=0;n<instances.size();++n)instances[n]=0xF0000000u+static_cast<uint32_t>(n);
    const auto vb=std::span<const uint8_t>(reinterpret_cast<const uint8_t*>(vertex.data()),sizeof(vertex));
    const auto ib=std::span<const uint8_t>(reinterpret_cast<const uint8_t*>(instances.data()),sizeof(instances));
    const std::vector<Source> fields{{vb,1,1,0,0,16,0,"v16"},{vb,1,1,0,0,12,0,"v12"},
        {ib,2,1,0,16,16,2,"i16"},{ib,2,1,0,8,8,3,"i8"}};
    const auto layout=compact_layout(fields,32,4,16);std::vector<uint32_t> ids{16777217,16777218,16777219,16777220,16777221,16777222};
    for(auto mode:{b::Topology::TriangleStrip,b::Topology::TriangleFan,b::Topology::LineStrip,b::Topology::LineLoop})
        verify(mode,{16777217,ids.size(),7},ids,fields,layout,grants(48,48));
}
int main(){try{matrix();boundaries_and_carry();restart_tails_and_bounds();multistream();
    std::cout<<"PASS portable topology batches: "<<checks<<" checks; "<<plans<<" independent plans; CPU only\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
