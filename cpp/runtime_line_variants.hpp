#pragma once

#include "runtime_line_consumer.hpp"

#include <list>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>

namespace vispy::lines {

// One FIFO belongs to an Artifact, across ordinary and all policy pipelines.
// Record maps remain owned by their exact records after policy-set eviction.
// Runtime callers serialize access and retain the selected record throughout.
template <class Record, class Pipeline>
class LineRenderVariantCache {
  public:
    using RecordPtr = std::shared_ptr<Record>;
    using Variants = std::unordered_map<std::string, Pipeline>;

    explicit LineRenderVariantCache(size_t capacity = 128) : capacity_(capacity) {}

    bool publish(const std::string& key, const Pipeline& pipeline,
                 const RecordPtr& record, Variants& ordinary) {
        if (!capacity_) return false;
        auto& target = record ? record->variants : ordinary;
        if (target.contains(key)) return true;
        // Allocate every prospective node/key/bucket before evicting an owner.
        Variants prospective;
        prospective.emplace(key, pipeline);
        std::list<Owner> pending;
        pending.push_back({bool(record), record, key});
        target.reserve(target.size() + 1);
        order_.remove_if([](const Owner& owner) {
            return owner.consumer && owner.record.expired();
        });
        while (order_.size() >= capacity_) {
            const auto& oldest = order_.front();
            if (oldest.consumer) {
                if (auto previous = oldest.record.lock()) previous->variants.erase(oldest.key);
            } else ordinary.erase(oldest.key);
            order_.pop_front();
        }
        target.insert(prospective.extract(prospective.begin()));
        order_.splice(order_.end(), pending);
        return true;
    }

    // Invalidation drops FIFO bookkeeping, not externally held record maps.
    void clear() { order_.clear(); }
    size_t size() const { return order_.size(); }
    size_t storage_bytes() const {
        size_t bytes = sizeof(*this);
        std::set<std::weak_ptr<Record>, std::owner_less<std::weak_ptr<Record>>> expired_controls;
        for (const auto& owner : order_) {
            bytes = detail::consumer_device_add_bytes(bytes, sizeof(Owner) + 2 * sizeof(void*));
            bytes = detail::consumer_device_add_bytes(bytes,
                detail::consumer_device_add_bytes(owner.key.capacity(), 1));
            // An expired weak owner can keep its control metadata alive until
            // the next insertion prunes it; no record footprint covers it.
            if (owner.consumer && owner.record.expired() && expired_controls.insert(owner.record).second)
                bytes = detail::consumer_device_add_bytes(bytes, 2 * sizeof(void*));
        }
        return bytes;
    }

  private:
    struct Owner {
        bool consumer;
        std::weak_ptr<Record> record;
        std::string key;
    };
    size_t capacity_;
    std::list<Owner> order_;
};

}  // namespace vispy::lines
