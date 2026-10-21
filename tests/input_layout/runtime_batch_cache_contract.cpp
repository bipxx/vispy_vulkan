#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4267) // Unchanged runtime_point.hpp size_t -> uint32_t definition.
#endif
#include "runtime_batch_cache.hpp"
#ifdef _MSC_VER
#pragma warning(pop)
#endif
#include "runtime_render_semantics.hpp"
#include "runtime_batch_capacity.hpp"
#include "runtime_batch_plan.hpp"
#include <iostream>
#include <tuple>

using namespace vispy::inputs;
namespace b=vispy::inputs::batches;
static uint64_t checks=0;
static void require(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F> static void throws(F&& f,const char* expected){
    ++checks;try{f();}catch(const std::runtime_error& e){
        if(std::string(e.what())==expected)return;
        throw std::runtime_error(std::string("wrong exception: ")+e.what());
    }throw std::runtime_error(std::string("missing exception: ")+expected);
}
struct Node;
using NodeRecord=std::shared_ptr<Node>;
struct Node{
    static inline int live=0;
    int id;
    uint64_t payload;
    std::vector<NodeRecord> children;
    Node(int number,uint64_t bytes):id(number),payload(bytes){++live;}
    ~Node(){--live;}
};
using Current=CurrentConversions<NodeRecord>;
using Oversized=OversizedConversions<NodeRecord>;
using History=std::unordered_map<std::string,NodeRecord>;
static constexpr auto batch_category=CurrentCategory::Batch;
static NodeRecord leaf(int id,uint64_t cost=32){return std::make_shared<Node>(id,cost);}
static NodeRecord tree(int id,uint64_t cost=64){auto result=leaf(id,cost);result->children={leaf(id+1),leaf(id+2)};return result;}
static uint64_t total(const NodeRecord& node){uint64_t value=node->payload;for(const auto& child:node->children)value+=total(child);return value;}
struct Faults{
    size_t builds=0,prepares=0,bytes=0,graph_visits=0;
    size_t fail_bytes=0,fail_graph=0;
    bool fail_prepare=false,fail_builder=false;
    std::weak_ptr<Node> built_root,built_child;
};
struct Bytes{
    Faults* state;
    uint64_t operator()(const NodeRecord& node)const{
        ++state->bytes;
        if(state->fail_bytes==state->bytes)throw std::runtime_error("injected bytes footprint");
        return total(node);
    }
};
struct Graph{
    Faults* state;
    uint64_t operator()(const NodeRecord& node,std::unordered_set<const void*>& visited)const{
        ++state->graph_visits;
        if(state->fail_graph==state->graph_visits)throw std::runtime_error("injected graph footprint");
        if(!visited.insert(node.get()).second)return 0;
        uint64_t value=node->payload;
        for(const auto& child:node->children)value+=(*this)(child,visited);
        return value;
    }
};
struct Prepare{
    Faults* state;
    auto operator()(const Current& current,CurrentCategory slot,const std::string& key,NodeRecord record)const{
        ++state->prepares;
        auto prepared=current.prepare(slot,key,std::move(record));
        if(state->fail_prepare)throw std::runtime_error("injected current prepare");
        return prepared;
    }
};
struct Caches{
    Current current;
    Oversized oversized{2,4096};
    History history;
    std::weak_ptr<Node> original_current,original_child,historical_a,historical_b,oversized_b,oversized_c;
    Caches(){
        auto old=tree(10);original_current=old;original_child=old->children[1];current.replace(batch_category,"old",old);
        current.replace(CurrentCategory::Vertex,"other-category",leaf(90));
        auto ha=tree(20),hb=tree(30);historical_a=ha;historical_b=hb;history.emplace("history-a",ha);history.emplace("history-b",hb);
        auto ob=tree(40),oc=tree(50);oversized_b=ob;oversized_c=oc;
        Faults unused;require(oversized.admit(batch_category,"oversized-b",ob,Graph{&unused}),"seed oversized B");
        require(oversized.admit(batch_category,"oversized-c",oc,Graph{&unused}),"seed oversized C");
    }
};
using Row=std::tuple<size_t,std::string,const Node*>;
struct Snapshot{
    std::vector<Row> current,oversized,history;
    uint64_t evictions=0;
    size_t current_size=0,oversized_size=0,history_size=0;
    int live=0;
    std::array<long,6> owner_counts{};
    bool operator==(const Snapshot&)const=default;
};
static Snapshot snapshot(const Caches& cache){
    Snapshot result;
    cache.current.for_each([&](auto cat,const auto& key,const auto& record){result.current.emplace_back(static_cast<size_t>(cat),key,record.get());});
    cache.oversized.for_each([&](auto cat,const auto& key,const auto& record){result.oversized.emplace_back(static_cast<size_t>(cat),key,record.get());});
    for(const auto& [key,record]:cache.history)result.history.emplace_back(0,key,record.get());
    std::sort(result.history.begin(),result.history.end());
    result.evictions=cache.oversized.evictions();result.current_size=cache.current.size();
    result.oversized_size=cache.oversized.size();result.history_size=cache.history.size();result.live=Node::live;
    result.owner_counts={cache.original_current.use_count(),cache.original_child.use_count(),cache.historical_a.use_count(),cache.historical_b.use_count(),cache.oversized_b.use_count(),cache.oversized_c.use_count()};
    return result;
}
static std::vector<std::string> lru(const Caches& cache){std::vector<std::string> result;
    cache.oversized.for_each([&](auto,const auto& key,const auto&){result.push_back(key);});return result;}
static auto convert(Caches& cache,Faults& state,const std::string& key,uint64_t bytes=4096,size_t entries=1){
    return b::transactional_conversion(cache.current,cache.oversized,cache.history,batch_category,key,[&]{
        ++state.builds;auto root=tree(100);state.built_root=root;state.built_child=root->children.back();
        if(state.fail_builder)throw std::runtime_error("injected late builder");
        return root;
    },Bytes{&state},Graph{&state},Prepare{&state},entries,bytes);
}
static void unchanged_after_failure(const Caches& cache,const Snapshot& before){
    require(snapshot(cache)==before,"all current keys/history/oversized order/evictions and owner count unchanged");
    require(!cache.original_current.expired()&&!cache.original_child.expired()&&!cache.historical_a.expired()&&
        !cache.historical_b.expired()&&!cache.oversized_b.expired()&&!cache.oversized_c.expired(),"all previous graph owners survive failed transaction");
}
static void late_builder_and_prepare(){
    {
        Caches cache;Faults state;state.fail_builder=true;const auto before=snapshot(cache);
        throws([&]{(void)convert(cache,state,"new");},"injected late builder");
        unchanged_after_failure(cache,before);
        require(state.builds==1&&state.prepares==0&&state.built_root.expired()&&state.built_child.expired(),"late builder children destroyed without publication");
    }
    for(const auto& key:std::array<std::string,3>{"new","history-a","oversized-b"}){
        Caches cache;Faults state;state.fail_prepare=true;const auto before=snapshot(cache);
        throws([&]{(void)convert(cache,state,key);},"injected current prepare");
        unchanged_after_failure(cache,before);
        require(state.prepares==1,"fault follows actual current key preparation");
        require(state.builds==(key=="new"?1u:0u),"history/oversized hit never calls builder on prepare failure");
        if(key=="new")require(state.built_root.expired()&&state.built_child.expired(),"new history candidate rolled back after prepare failure");
    }
}
static void every_footprint_failure(){
    size_t byte_calls=0,graph_calls=0;
    {Caches cache;Faults state;auto value=convert(cache,state,"new");require(value.second,"new small graph built");byte_calls=state.bytes;}
    require(Node::live==0&&byte_calls>2,"byte controls include prior history accounting and admission");
    for(size_t fault=1;fault<=byte_calls;++fault){
        Caches cache;Faults state;state.fail_bytes=fault;const auto before=snapshot(cache);
        throws([&]{(void)convert(cache,state,"new");},"injected bytes footprint");
        unchanged_after_failure(cache,before);
        require(state.built_root.expired()&&state.built_child.expired(),"footprint failure drops new staged children");
    }
    {Caches cache;Faults state;auto value=convert(cache,state,"new",64);require(value.second,"oversized candidate built");graph_calls=state.graph_visits;}
    require(Node::live==0&&graph_calls>=6,"graph controls reach new children and retained working graphs");
    for(size_t fault=1;fault<=graph_calls;++fault){
        Caches cache;Faults state;state.fail_graph=fault;const auto before=snapshot(cache);
        throws([&]{(void)convert(cache,state,"new",64);},"injected graph footprint");
        unchanged_after_failure(cache,before);
        require(state.prepares==1&&state.built_root.expired()&&state.built_child.expired(),"graph failure after current prepare still publishes nothing");
    }
    // The same late graph failure must not mutate a historical-hit graph.
    {
        Caches cache;Faults state;state.fail_graph=3;const auto before=snapshot(cache);
        throws([&]{(void)convert(cache,state,"history-a",64);},"injected graph footprint");
        unchanged_after_failure(cache,before);require(state.builds==0&&state.prepares==1,"history hit uses existing complete graph before late failure");
    }
    std::cout<<"OBSERVE injected byte-footprint positions="<<byte_calls<<" graph-footprint positions="<<graph_calls<<'\n';
}
static void successful_joined_publication(){
    {
        Caches cache;Faults state;const auto old=cache.original_current;const auto old_child=cache.original_child;
        auto pending=old.lock();const auto old_hist_a=cache.historical_a,old_hist_b=cache.historical_b;
        const auto previous_lru=lru(cache);const auto evictions=cache.oversized.evictions();
        const auto value=convert(cache,state,"new");
        require(value.second&&value.first==cache.current.find(batch_category,"new")&&cache.history.size()==1&&cache.history.at("new")==value.first,
            "current and evicted/replaced history publish same complete new owner");
        require(lru(cache)==previous_lru&&cache.oversized.evictions()==evictions,"small history transaction does not alter unrelated working LRU");
        require(old_hist_a.expired()&&old_hist_b.expired(),"superseded history owners retire after successful publication");
        require(!old.expired()&&!old_child.expired(),"pending old root retains its complete child graph");
        pending.reset();require(old.expired()&&old_child.expired(),"old graph drops after final pending owner release");
        const auto before=snapshot(cache);Faults warm;
        const auto hit=convert(cache,warm,"new");
        require(!hit.second&&hit.first==value.first&&snapshot(cache)==before,"warm current hit retains exact graph/cache state");
        require(warm.builds==warm.prepares&&warm.prepares==warm.bytes&&warm.bytes==warm.graph_visits&&warm.graph_visits==0,
            "warm current hit has no builder/key prepare/byte scan/recursive footprint scan");
    }
    {
        Caches cache;Faults state;const auto prior=snapshot(cache);auto expected=cache.historical_a.lock();
        const auto value=convert(cache,state,"history-a");
        require(!value.second&&value.first==expected&&cache.current.find(batch_category,"history-a")==expected,"history hit publishes existing owner into current");
        const auto after=snapshot(cache);
        require(after.history==prior.history&&after.oversized==prior.oversized&&after.evictions==prior.evictions,"history hit leaves history and working graph identities intact");
        require(state.builds==0&&state.prepares==1&&state.bytes==1&&state.graph_visits==0,"history hit scans only its required classification footprint");
    }
    {
        Caches cache;Faults state;const auto prior=snapshot(cache);auto expected=cache.oversized_b.lock();
        const auto value=convert(cache,state,"oversized-b");
        require(!value.second&&value.first==expected&&cache.current.find(batch_category,"oversized-b")==expected,"oversized hit adopts exact existing graph");
        require(lru(cache)==std::vector<std::string>{"oversized-b","oversized-c"},"oversized hit promotes LRU only after prepare succeeds");
        require(snapshot(cache).history==prior.history&&cache.oversized.evictions()==prior.evictions,"oversized hit leaves history and eviction count unchanged");
        require(state.builds==0&&state.prepares==1&&state.bytes==0&&state.graph_visits==0,"oversized hit does not rebuild or scan payload graphs");
    }
    {
        Caches cache;Faults state;const auto prior=snapshot(cache);const auto victim=cache.oversized_b;
        auto pending=victim.lock();const auto value=convert(cache,state,"new",64);
        require(value.second&&cache.current.find(batch_category,"new")==value.first&&cache.oversized.peek(batch_category,"new")==value.first,
            "new oversized graph publishes current and working owner together");
        require(lru(cache)==std::vector<std::string>{"new","oversized-c"}&&cache.oversized.evictions()==prior.evictions+1,
            "one successful capacity eviction keeps original LRU survivor");
        require(snapshot(cache).history==prior.history&&!victim.expired(),"history unchanged and pending snapshot keeps evicted working graph");
        pending.reset();require(victim.expired(),"capacity victim releases only after pending snapshot drops");
    }
}
static void actual_semantic_counter_helper(){
    uint64_t logical=0,native=0;
    vispy::render::count_encoded_draw(vispy::render::SnapshotOrigin::UserDraw,logical,native,14);
    require(logical==1&&native==14,"actual helper counts one logical draw versus fourteen physical batch draws");
    vispy::render::count_encoded_draw(vispy::render::SnapshotOrigin::Clear,logical,native,2);
    require(logical==1&&native==16,"clear physical draws do not add scene draws");
    vispy::render::count_encoded_draw(vispy::render::SnapshotOrigin::UserDraw,logical,native);
    require(logical==2&&native==17,"legacy default remains one logical and native draw");
}

// Test the actual queue helper with an element whose move is deliberately
// throwing, as permitted by the pinned Dawn handle-wrapper signatures.
struct QueueItem {
    static inline int live=0;
    static inline size_t defaults=0,copies=0,moves=0,fail_copy=0;
    static inline bool fail_default=false,forbid_moves=false;
    int id=0;
    NodeRecord owner;
    bool staged_admission=false;
    QueueItem(){
        ++defaults;
        if(fail_default)throw std::runtime_error("injected default construction");
        ++live;
    }
    QueueItem(const QueueItem& other):id(other.id),owner(other.owner),staged_admission(other.staged_admission){
        ++copies;
        if(fail_copy&&copies==fail_copy)throw std::runtime_error("injected queue copy");
        ++live;
    }
    QueueItem(QueueItem&& other) noexcept(false):id(other.id),staged_admission(other.staged_admission){
        ++moves;
        if(forbid_moves)throw std::runtime_error("forbidden snapshot move");
        owner=std::move(other.owner);++live;
    }
    QueueItem& operator=(const QueueItem&)=delete;
    QueueItem& operator=(QueueItem&&)=delete;
    ~QueueItem() noexcept{--live;}
    static void reset_faults(){defaults=copies=moves=fail_copy=0;fail_default=forbid_moves=false;}
};
using Queue=std::vector<QueueItem>;
using QueueRows=std::vector<std::pair<int,const Node*>>;
static_assert(std::is_copy_constructible_v<QueueItem>);
static_assert(!std::is_nothrow_move_constructible_v<QueueItem>);
static_assert(std::is_nothrow_destructible_v<QueueItem>);
static_assert(!std::is_copy_constructible_v<b::ReservedBack<Queue>>);
static_assert(!std::is_move_constructible_v<b::ReservedBack<Queue>>);
static_assert(std::is_nothrow_destructible_v<b::ReservedBack<Queue>>);
static_assert(noexcept(std::declval<b::ReservedBack<Queue>&>().value()));
static_assert(noexcept(std::declval<b::ReservedBack<Queue>&>().publish()));
static QueueRows queue_rows(const auto& queue){
    QueueRows rows;for(const auto& item:queue)rows.emplace_back(item.id,item.owner.get());return rows;
}
static void seed_queue(auto& queue,const Caches& cache){
    queue.reserve(2);queue.emplace_back();queue.back().id=11;queue.back().owner=cache.original_current.lock();
    queue.emplace_back();queue.back().id=22;queue.back().owner=cache.historical_a.lock();
    require(queue.size()==queue.capacity(),"queue fixture forces reserve reallocation before admission");
}
template<class Error,class F>static void throws_type(F&& function,const char* message){
    ++checks;try{function();}catch(const Error&){return;}
    throw std::runtime_error(message);
}
struct AllocationFault {static inline bool fail=false;};
template<class T>struct FaultAllocator {
    using value_type=T;
    FaultAllocator()=default;
    template<class U>FaultAllocator(const FaultAllocator<U>&)noexcept{}
    T* allocate(size_t count){if(AllocationFault::fail)throw std::bad_alloc();return std::allocator<T>{}.allocate(count);}
    void deallocate(T* pointer,size_t count)noexcept{std::allocator<T>{}.deallocate(pointer,count);}
    template<class U>bool operator==(const FaultAllocator<U>&)const noexcept{return true;}
};
template<class T>struct TwoElementAllocator {
    using value_type=T;
    TwoElementAllocator()=default;
    template<class U>TwoElementAllocator(const TwoElementAllocator<U>&)noexcept{}
    size_t max_size()const noexcept{return 2;}
    T* allocate(size_t count){if(count>2)throw std::bad_alloc();return std::allocator<T>{}.allocate(count);}
    void deallocate(T* pointer,size_t count)noexcept{std::allocator<T>{}.deallocate(pointer,count);}
    template<class U>bool operator==(const TwoElementAllocator<U>&)const noexcept{return true;}
};
static void queue_construction_failures(){
    {
        Caches cache;Queue queue;QueueItem::reset_faults();seed_queue(queue,cache);
        const auto before=snapshot(cache);const auto rows=queue_rows(queue);
        QueueItem::fail_default=true;size_t builders=0;
        throws([&]{b::ReservedBack staged(queue);++builders;},"injected default construction");
        QueueItem::fail_default=false;
        require(builders==0&&queue_rows(queue)==rows&&queue.size()==2&&QueueItem::live==2,
            "default failure cannot reach builder or retain provisional element");
        unchanged_after_failure(cache,before);
        require(QueueItem::copies==2&&QueueItem::moves==0,"reserve copies old throwing-move elements before default failure");
    }
    for(size_t fault=1;fault<=2;++fault){
        Caches cache;Queue queue;QueueItem::reset_faults();seed_queue(queue,cache);
        const auto before=snapshot(cache);const auto rows=queue_rows(queue);
        const auto* old_data=queue.data();const auto capacity=queue.capacity();size_t builders=0;
        QueueItem::fail_copy=fault;
        throws([&]{b::ReservedBack staged(queue);++builders;},"injected queue copy");
        QueueItem::fail_copy=0;
        require(builders==0&&queue_rows(queue)==rows&&queue.data()==old_data&&queue.capacity()==capacity&&QueueItem::live==2,
            "every reserve copy failure preserves old vector payload/storage/owners before builder");
        unchanged_after_failure(cache,before);
        require(QueueItem::copies==fault&&QueueItem::moves==0,"fault occurs in actual vector reserve copy fallback");
    }
    {
        Caches cache;std::vector<QueueItem,FaultAllocator<QueueItem>> queue;
        QueueItem::reset_faults();seed_queue(queue,cache);
        const auto before=snapshot(cache);const auto rows=queue_rows(queue);const auto* old_data=queue.data();
        AllocationFault::fail=true;size_t builders=0;
        throws_type<std::bad_alloc>([&]{b::ReservedBack staged(queue);++builders;},"missing reserve allocation failure");
        AllocationFault::fail=false;
        require(builders==0&&queue_rows(queue)==rows&&queue.data()==old_data&&QueueItem::live==2,"allocation failure precedes builder and preserves old queue");
        unchanged_after_failure(cache,before);
    }
    {
        Caches cache;std::vector<QueueItem,TwoElementAllocator<QueueItem>> queue;
        QueueItem::reset_faults();seed_queue(queue,cache);
        const auto before=snapshot(cache);const auto rows=queue_rows(queue);size_t builders=0;
        require(queue.size()==queue.max_size(),"capacity-exhausted fixture reaches actual max_size check");
        throws_type<std::length_error>([&]{b::ReservedBack staged(queue);++builders;},"missing queue max_size refusal");
        require(builders==0&&queue_rows(queue)==rows&&QueueItem::live==2,"max_size refusal publishes no queue element or builder");
        unchanged_after_failure(cache,before);
    }
}
static void one_queued_failure(Faults& faults,const std::string& key,const char* error,uint64_t byte_limit=4096){
    Caches cache;Queue queue;QueueItem::reset_faults();seed_queue(queue,cache);
    const auto before=snapshot(cache);const auto rows=queue_rows(queue);
    QueueItem::forbid_moves=true;
    throws([&]{
        b::ReservedBack admission(queue);auto& item=admission.value();
        item.id=33;item.staged_admission=true;
        require(&item==&queue.back()&&queue.size()==3,"actual helper owns stable final tail before conversion");
        auto value=convert(cache,faults,key,byte_limit);
        item.owner=std::move(value.first);item.staged_admission=false;admission.publish();
    },error);
    require(queue_rows(queue)==rows&&queue.size()==2&&QueueItem::live==2,"late conversion failure pops only unpublished tail");
    require(QueueItem::moves==0,"rollback never requires throwing snapshot move");
    unchanged_after_failure(cache,before);
    require(faults.built_root.expired()&&faults.built_child.expired(),"failed queued transaction retains no new graph");
}
static void queue_conversion_failures(){
    {Faults fault;fault.fail_builder=true;one_queued_failure(fault,"new","injected late builder");}
    for(const auto& key:std::array<std::string,3>{"new","history-a","oversized-b"}){
        Faults fault;fault.fail_prepare=true;one_queued_failure(fault,key,"injected current prepare");
    }
    size_t byte_calls=0,graph_calls=0;
    {Caches cache;Faults state;(void)convert(cache,state,"new");byte_calls=state.bytes;}
    {Caches cache;Faults state;(void)convert(cache,state,"new",64);graph_calls=state.graph_visits;}
    for(size_t position=1;position<=byte_calls;++position){
        Faults fault;fault.fail_bytes=position;one_queued_failure(fault,"new","injected bytes footprint");
    }
    for(size_t position=1;position<=graph_calls;++position){
        Faults fault;fault.fail_graph=position;one_queued_failure(fault,"new","injected graph footprint",64);
    }
    {Faults fault;fault.fail_graph=3;one_queued_failure(fault,"history-a","injected graph footprint",64);}
    std::cout<<"OBSERVE queue rollback byte positions="<<byte_calls<<" graph positions="<<graph_calls<<'\n';
}
static void queue_success_without_final_move(){
    for(const auto& key:std::array<std::string,3>{"new","history-a","oversized-b"}){
        Caches cache;Queue queue;QueueItem::reset_faults();seed_queue(queue,cache);
        const auto rows=queue_rows(queue);const auto old=cache.original_current,child=cache.original_child;
        QueueItem::forbid_moves=true;QueueItem* final_slot=nullptr;Faults state;
        {
            b::ReservedBack admission(queue);auto& item=admission.value();final_slot=&item;
            item.id=33;item.staged_admission=true;
            auto value=convert(cache,state,key);
            item.owner=std::move(value.first);item.staged_admission=false;
            require(final_slot==&queue.back()&&QueueItem::moves==0,"final slot stays in place across actual cache transaction");
            admission.publish();admission.publish();
        }
        require(queue.size()==3&&&queue.back()==final_slot&&QueueItem::live==3,"publish retains same final queue element and is idempotent");
        const auto after=queue_rows(queue);
        require(std::equal(rows.begin(),rows.end(),after.begin())&&after.back().first==33,"logical queue order and prior owner identities preserved");
        require(queue.back().owner==cache.current.find(batch_category,key)&&!queue.back().staged_admission,"admitted tail owns complete published root");
        require(QueueItem::moves==0&&QueueItem::copies==2,"successful full-queue growth copies before conversion and never moves after commit");
        require(!old.expired()&&!child.expired(),"old pending snapshot retains its full graph after current publication");
    }
    {
        Caches cache;Queue queue;QueueItem::reset_faults();queue.reserve(3);queue.emplace_back();queue.back().id=11;
        const auto* original=&queue.front();QueueItem::forbid_moves=true;
        {b::ReservedBack admission(queue);admission.value().id=22;}
        require(queue.size()==1&&&queue.front()==original&&queue.front().id==11&&QueueItem::moves==0&&QueueItem::copies==0,
            "unpublished default slot rolls back without conversion, allocation or relocation when capacity exists");
    }
}
// Exercise the production key helper and real decision/Plan payloads through
// actual cache APIs. Production source separately binds the untouched outer
// partition/source/grant/liveness key components; do not mirror those strings.
struct DomainRecord {
    WholeCompactFit fit;
    std::shared_ptr<const b::Plan> plan;
};
using DomainPtr=std::shared_ptr<DomainRecord>;
struct DomainCaches {
    CurrentConversions<DomainPtr> current;
    OversizedConversions<DomainPtr> oversized;
    std::unordered_map<std::string,DomainPtr> history;
    size_t builders=0,bytes=0,graphs=0;
    uint64_t scanned=0;
};
static uint64_t domain_bytes(DomainCaches& cache,const DomainPtr& record){
    ++cache.bytes;return sizeof(DomainRecord)+(record->plan?record->plan->control_bytes:0);
}
static uint64_t domain_graph(DomainCaches& cache,const DomainPtr& record,std::unordered_set<const void*>& visited){
    ++cache.graphs;if(!visited.insert(record.get()).second)return 0;
    return sizeof(DomainRecord)+(record->plan?record->plan->control_bytes:0);
}
static DomainPtr cached_fit(DomainCaches& cache,const Selection& selection,const Layout& layout,bool fail=false){
    const auto key=b::draw_domain_key(selection_key(selection,41,7),selection.instances);
    auto value=working_cached_conversion(cache.current,cache.oversized,CurrentCategory::CompactFit,cache.history,key,[&]{
        ++cache.builders;auto result=std::make_shared<DomainRecord>();
        result->fit=probe_whole_compact_fit(selection,layout,96,128,true);
        cache.scanned+=result->fit.indices_scanned;
        if(fail)throw std::runtime_error("injected fit decision builder");
        return result;
    },[&](const auto& item){return domain_bytes(cache,item);},
      [&](const auto& item,auto& seen){return domain_graph(cache,item,seen);});
    return value.first;
}
static DomainPtr cached_plan(DomainCaches& cache,const Selection& selection,std::span<const Source> sources,const Layout& layout){
    const auto key=b::draw_domain_key(selection_key(selection,41,7),selection.instances);
    auto value=b::transactional_conversion(cache.current,cache.oversized,cache.history,CurrentCategory::Batch,key,[&]{
        ++cache.builders;auto result=std::make_shared<DomainRecord>();
        result->plan=std::make_shared<const b::Plan>(b::plan_triangle_list(selection,sources,layout,{96,128,1024*1024,1000}));
        return result;
    },[&](const auto& item){return domain_bytes(cache,item);},
      [&](const auto& item,auto& seen){return domain_graph(cache,item,seen);});
    return value.first;
}
static void actual_domain_keys(){
    const Selection original{17,9,1};
    const auto geometry=selection_key(original,41,7);
    auto changed_instances=original;changed_instances.instances=13;
    require(selection_key(changed_instances,41,7)==geometry,"legacy geometry selection key intentionally remains independent of instance count");
    const auto one=b::draw_domain_key(geometry,1),thirteen=b::draw_domain_key(geometry,13);
    require(one!=thirteen&&one==b::draw_domain_key(geometry,1),"actual domain helper distinguishes1/13 and reverts exactly1");
    require(one.starts_with(geometry)&&thirteen.starts_with(geometry),"actual helper preserves complete geometry dependency key bytes");
    std::unordered_set<std::string> keys;
    for(uint64_t instance:std::array<uint64_t,7>{0,1,7,13,UINT32_MAX,uint64_t(UINT32_MAX)+1,UINT64_MAX}){
        const auto key=b::draw_domain_key(geometry,instance);
        require(keys.insert(key).second,"zero/high/extreme instance domain keys cannot alias");
        require(key.ends_with(std::to_string(instance)),"instance key decimal preserves full uint64 value");
    }
    require(b::draw_domain_key(geometry,13)!=b::draw_domain_key(geometry+":instances:1",3),"existing delimiters in prefix cannot alias appended domain");
    auto next=original;next.first=18;
    require(one!=b::draw_domain_key(selection_key(next,41,7),1),"first remains part of domain key");
    next=original;next.count=12;
    require(one!=b::draw_domain_key(selection_key(next,41,7),1),"count remains part of domain key");
    require(one!=b::draw_domain_key(selection_key(original,42,7),1)&&one!=b::draw_domain_key(selection_key(original,41,8),1),
        "index identity and revision remain independent key dependencies");
    std::vector<uint8_t> backing(18);next=original;next.first=0;next.count=9;next.indices=backing;next.index_bytes=2;
    const auto width2=b::draw_domain_key(selection_key(next,41,7),1);backing.resize(36);next.indices=backing;next.index_bytes=4;
    require(width2!=b::draw_domain_key(selection_key(next,41,7),1),"index representation width remains part of domain key");
}
static void actual_fit_domain_reuse(){
    std::vector<uint32_t> ids{0,1,2,0,1,2};
    std::vector<uint8_t> indexed(ids.size()*4);std::memcpy(indexed.data(),ids.data(),indexed.size());
    std::vector<uint8_t> vertex(48),instance(128);
    const std::vector<Source> sources{{vertex,101,1,0,16,16,0,"position"},{instance,102,1,0,8,8,1,"instance"}};
    const auto layout=compact_layout(sources,30,8,2048);
    Selection selection{0,6,1,indexed,4};DomainCaches cache;
    const auto one=cached_fit(cache,selection,layout);
    require(one->fit.fits&&one->fit.indices_scanned==6&&cache.builders==1&&cache.scanned==6,"real one-instance whole-fit decision scans exact selected index prefix");
    const auto bytes=cache.bytes,graphs=cache.graphs;
    require(cached_fit(cache,selection,layout)==one&&cache.builders==1&&cache.scanned==6&&cache.bytes==bytes&&cache.graphs==graphs,
        "actual warm decision hit performs no probe/builder/footprint scan");
    selection.instances=13;
    const auto thirteen=cached_fit(cache,selection,layout);
    require(thirteen!=one&&!thirteen->fit.fits&&thirteen->fit.reason==WholeCompactReason::InstanceRows&&cache.builders==2,
        "changing only instances1to13 cannot reuse true capacity decision");
    require(thirteen->fit.indices_scanned==0&&cache.scanned==6,"instance overflow declines before reading indices");
    selection.instances=1;
    require(cached_fit(cache,selection,layout)==one&&cache.builders==2&&cache.scanned==6,"1to13to1 restores exact historical decision without new scan");
    const auto current=cache.current.find(CurrentCategory::CompactFit,b::draw_domain_key(selection_key(selection,41,7),1));
    const auto history_size=cache.history.size();
    const auto evictions=cache.oversized.evictions();
    selection.instances=2;
    throws([&]{(void)cached_fit(cache,selection,layout,true);},"injected fit decision builder");
    require(cache.current.find(CurrentCategory::CompactFit,b::draw_domain_key(selection_key(selection,41,7),1))==current&&
        cache.history.size()==history_size&&cache.oversized.evictions()==evictions,"failed new-domain decision build keeps current/history/evictions exact");
    require(cache.current.size()==1&&cache.current.category_count==9,"ninth actual current category is independent and bounded");
}
static void actual_batch_domain_reuse(){
    std::vector<uint32_t> ids{0,1,2,3,4,5,6,7,8};
    std::vector<uint8_t> indexed(ids.size()*4);std::memcpy(indexed.data(),ids.data(),indexed.size());
    std::vector<uint8_t> vertex(9*16),instance(13*8);
    const std::vector<Source> sources{{vertex,101,1,0,16,16,0,"position"},{instance,102,1,0,8,8,1,"instance"}};
    const auto layout=compact_layout(sources,30,8,2048);
    Selection selection{0,9,1,indexed,4};DomainCaches cache;
    const auto one=cached_plan(cache,selection,sources,layout);
    require(one->plan->geometry.size()==2&&one->plan->instances==1&&one->plan->encoded_draws==2,"actual Plan1instance has two complete geometry draws");
    selection.instances=13;
    const auto thirteen=cached_plan(cache,selection,sources,layout);
    require(thirteen!=one&&thirteen->plan->instances==13&&thirteen->plan->encoded_draws==26&&thirteen->plan->instance_block_count==2,
        "actual Plan13instances keeps independent2block26draw frozen domain");
    uint64_t visits=0;
    thirteen->plan->for_each_draw([&](const b::DrawRef& ref){
        require(ref.instance_count==1&&ref.instance_base==visits/2&&ref.geometry==visits%2,"actual cached Plan remains instance-major across26draws");++visits;
    });
    require(visits==26,"all13 original instance identities have exactly two geometry visits");
    const auto bytes=cache.bytes,graphs=cache.graphs;
    require(cached_plan(cache,selection,sources,layout)==thirteen&&cache.builders==2&&cache.bytes==bytes&&cache.graphs==graphs,
        "warm actual batch owner hit rebuilds/scans no Plan");
    selection.instances=1;
    require(cached_plan(cache,selection,sources,layout)==one&&cache.builders==2&&one->plan->instances==1&&thirteen->plan->instances==13,
        "1to13to1 reuses historical original Plan without mutating retained13instance owner");
    auto retained=thirteen;cache.current.clear();cache.history.clear();cache.oversized.clear();
    require(retained->plan->instances==13&&retained->plan->encoded_draws==26,"independent pending owner keeps frozen draw domain after cacheclear");
}
int main(){try{
    late_builder_and_prepare();require(Node::live==0,"failure fixtures release all nodes");
    every_footprint_failure();require(Node::live==0,"all footprint fault fixtures release nodes");
    successful_joined_publication();require(Node::live==0,"successful cache/snapshot fixtures release all nodes");
    actual_semantic_counter_helper();
    queue_construction_failures();require(Node::live==0&&QueueItem::live==0,"construction fault queues release all owners/elements");
    queue_conversion_failures();require(Node::live==0&&QueueItem::live==0,"queued conversion fault fixtures release all owners/elements");
    queue_success_without_final_move();require(Node::live==0&&QueueItem::live==0,"successful queue fixtures release all owners/elements");
    actual_domain_keys();actual_fit_domain_reuse();actual_batch_domain_reuse();
    std::cout<<"PASS actual transactional cache and semantic draw helpers: "<<checks<<" independent checks; CPU only\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
