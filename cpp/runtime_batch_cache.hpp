#pragma once

#include "runtime_point.hpp"
#include <type_traits>

namespace vispy::inputs::batches {

// The historical selection key intentionally describes only geometry.
// Batch plans and fit decisions also own/depend on the instance domain.
inline std::string draw_domain_key(const std::string& selection, uint64_t instances) {
    return selection + ":instances:" + std::to_string(instances);
}

// Construct the eventual queue element before preparing converted resources.
// No snapshot move or node allocation occurs after cache publication. The
// engine lock prevents another writer from changing this vector while staged.
template<class Queue> class ReservedBack {
    static_assert(std::is_nothrow_destructible_v<typename Queue::value_type>);
    Queue& queue_;
    bool published_ = false;
public:
    explicit ReservedBack(Queue& queue) : queue_(queue) {
        if (queue_.size() == queue_.max_size()) throw std::length_error("DRAW queue capacity exhausted");
        queue_.reserve(queue_.size() + 1);
        queue_.emplace_back();
    }
    ReservedBack(const ReservedBack&) = delete;
    ReservedBack& operator=(const ReservedBack&) = delete;
    ReservedBack(ReservedBack&&) = delete;
    ReservedBack& operator=(ReservedBack&&) = delete;
    ~ReservedBack() noexcept { if (!published_) queue_.pop_back(); }
    auto& value() noexcept { return queue_.back(); }
    void publish() noexcept { published_ = true; }
};

// A cold batch publishes current/history/oversized owners together. The copied
// caches borrow complete immutable graphs; payload bytes are never copied here.
// The caller stages its snapshot layout and queue capacity before this commit.
template<class Current, class Oversized, class Map, class Build, class Bytes,
         class GraphBytes, class Prepare = PrepareCurrentConversion>
auto transactional_conversion(Current& current, Oversized& oversized, Map& history,
        CurrentCategory category, const std::string& key, Build&& build, Bytes&& bytes,
        GraphBytes&& graph_bytes, Prepare prepare = {}, size_t entry_limit = cache_entry_limit,
        uint64_t byte_limit = cache_byte_limit) {
    using Record = typename Map::mapped_type;
    if (auto record = current.find(category, key)) {
        oversized.find(category, key);
        return std::pair<Record, bool>{std::move(record), false};
    }
    auto next_current = current;
    auto next_oversized = oversized;
    auto next_history = history;
    auto result = working_cached_conversion(next_current, next_oversized, category,
        next_history, key, std::forward<Build>(build), std::forward<Bytes>(bytes),
        std::forward<GraphBytes>(graph_bytes), entry_limit, byte_limit, std::move(prepare));
    static_assert(std::is_nothrow_swappable_v<Current>);
    static_assert(std::is_nothrow_swappable_v<Oversized>);
    static_assert(std::is_nothrow_swappable_v<Map>);
    using std::swap;
    swap(current, next_current);
    swap(oversized, next_oversized);
    swap(history, next_history);
    return result;
}

} // namespace vispy::inputs::batches
