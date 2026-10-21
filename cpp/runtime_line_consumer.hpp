#pragma once

#include <cstddef>
#include <cstdint>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>

#include "runtime_line.hpp"

namespace vispy::lines {

enum class LineRenderRoute { Native, Generated };

struct OrdinaryLineInterfaceUsage {
    uint64_t vertex_locations = 0, fragment_locations = 0;
    uint32_t fragment_builtin_variables = 0;
};

// The ordinary pipeline still performs its full device admission. This only
// keeps thin, unsmoothed lines on that route when its declared interface fits.
inline LineRenderRoute select_line_render_route(State snapshot,
        OrdinaryLineInterfaceUsage usage, uint32_t max_inter_stage_variables) {
    snapshot = state(snapshot.width, snapshot.smooth);
    const uint64_t limit = max_inter_stage_variables;
    return snapshot.width == 1 && !snapshot.smooth && limit &&
        usage.vertex_locations <= limit && usage.fragment_builtin_variables <= limit &&
        usage.fragment_locations <= limit - usage.fragment_builtin_variables ?
        LineRenderRoute::Native : LineRenderRoute::Generated;
}

// Pinned Dawn counts these fragment-input builtins in addition to location
// variables (ShaderModule.cpp). FragCoord and fragment outputs are not charged.
// Reading retained SPIR-V declarations is conservative if Tint removes inputs.
inline uint32_t fragment_inter_stage_builtin_variables(std::span<const uint32_t> words) {
    if (words.size() < 5 || words[0] != 0x07230203u)
        throw std::invalid_argument("lines: invalid retained fragment SPIR-V");
    std::map<uint32_t, uint32_t> pointers;
    std::map<uint32_t, uint32_t> inputs;
    auto walk = [&](auto visit) {
        for (size_t at = 5; at < words.size();) {
            const size_t count = words[at] >> 16;
            if (!count || count > words.size() - at)
                throw std::invalid_argument("lines: malformed retained fragment SPIR-V");
            visit(at, count, words[at] & 0xffffu);
            at += count;
        }
    };
    walk([&](size_t at, size_t count, uint32_t op) {
        if (op == 32 && count == 4) pointers[words[at + 1]] = words[at + 3]; // OpTypePointer
        if (op == 59 && count >= 4 && words[at + 3] == 1) // OpVariable Input
            inputs[words[at + 2]] = words[at + 1];
    });
    std::map<uint32_t, bool> charged;
    walk([&](size_t at, size_t count, uint32_t op) {
        uint32_t builtin = 0;
        if (op == 71 && count == 4 && words[at + 2] == 11 && inputs.contains(words[at + 1]))
            builtin = words[at + 3]; // OpDecorate BuiltIn
        else if (op == 72 && count == 5 && words[at + 3] == 11) { // OpMemberDecorate BuiltIn
            bool input_struct = false;
            for (const auto& [id, type] : inputs) {
                (void)id;
                const auto found = pointers.find(type);
                input_struct |= found != pointers.end() && found->second == words[at + 1];
            }
            if (input_struct) builtin = words[at + 4];
        }
        // PrimitiveId, FrontFacing, SampleId, SampleMask, SubgroupSize,
        // SubgroupLocalInvocationId; each is a boolean usage flag in Dawn.
        if (builtin == 7 || builtin == 17 || builtin == 18 || builtin == 20 ||
                builtin == 36 || builtin == 41) charged[builtin] = true;
    });
    return static_cast<uint32_t>(charged.size());
}

namespace detail {
inline size_t consumer_device_add_bytes(size_t a, size_t b) {
    return b > std::numeric_limits<size_t>::max() - a ?
        std::numeric_limits<size_t>::max() : a + b;
}
inline size_t consumer_device_mul_bytes(size_t a, size_t b) {
    return a && b > std::numeric_limits<size_t>::max() / a ?
        std::numeric_limits<size_t>::max() : a * b;
}
}  // namespace detail

// Native handle types are injected by the runtime. This header has no Dawn,
// shader compiler or device dependency. The consumer pins its exact CPU graph
// and full policy key. Neither that owner nor this generation may be retagged.
// Caller serializes record and set operations (the runtime holds Engine::mu).
template <class Consumer, class Module, class Pipeline, class Layout>
struct LineConsumerDeviceRecord {
    using ConsumerType = Consumer;
    using ConsumerPtr = std::shared_ptr<const Consumer>;
    const ConsumerPtr consumer;
    const uint64_t device_generation;
    Module vert_module, frag_module;
    Layout bind_layout;
    std::string error;
    std::unordered_map<std::string, Pipeline> variants;

    LineConsumerDeviceRecord(ConsumerPtr value, uint64_t generation)
        : consumer(std::move(value)), device_generation(generation) {}

    template <class PortablePtr, class EvaluatorPtr>
    bool ready_for(uint64_t generation, const PortablePtr& portable,
                   const EvaluatorPtr& evaluator) const {
        if (!generation || device_generation != generation || !consumer ||
            consumer->policy_identity.empty() || !portable || !evaluator ||
            consumer->original != portable || consumer->evaluator != evaluator ||
            evaluator->original != portable || !vert_module || !frag_module ||
            !bind_layout || !error.empty()) return false;
        if constexpr (requires { consumer->ok; }) if (!consumer->ok) return false;
        if constexpr (requires { portable->ok; }) if (!portable->ok) return false;
        if constexpr (requires { evaluator->ok; }) if (!evaluator->ok) return false;
        return true;
    }

    // CPU record/handle metadata only. CPU consumer/original/evaluator payloads
    // are charged once by the shader cache; physical driver allocations are not
    // measured here. The runtime owns one GLOBAL variant FIFO/bound across its
    // ordinary pipelines and all these maps, rather than one bound per policy.
    size_t storage_bytes() const {
        size_t bytes = detail::consumer_device_add_bytes(sizeof(*this), error.capacity() + 1);
        bytes = detail::consumer_device_add_bytes(bytes,
            detail::consumer_device_mul_bytes(variants.bucket_count(), sizeof(void*)));
        for (const auto& [key, pipeline] : variants) {
            (void)pipeline;
            bytes = detail::consumer_device_add_bytes(bytes,
                sizeof(typename decltype(variants)::value_type) + 2 * sizeof(void*));
            bytes = detail::consumer_device_add_bytes(bytes, key.capacity() + 1);
        }
        return bytes;
    }
};

// This is a bounded subrecord collection INSIDE one joint device-artifact
// charge, not a separate shader cache. Borrowed full keys remain backed by the
// immutable consumer owners in records_. FIFO drops only set owners; DRAW,
// queued/submitted Ticket and callback owners may retain detached records.
template <class Record>
class LineConsumerDeviceSet {
  public:
    using RecordPtr = std::shared_ptr<Record>;
    using ConsumerPtr = typename Record::ConsumerPtr;
    explicit LineConsumerDeviceSet(size_t capacity = 128) : capacity_(capacity) {}
    LineConsumerDeviceSet(const LineConsumerDeviceSet&) = delete;
    LineConsumerDeviceSet& operator=(const LineConsumerDeviceSet&) = delete;
    LineConsumerDeviceSet(LineConsumerDeviceSet&& other) noexcept {
        *this = std::move(other);
    }
    LineConsumerDeviceSet& operator=(LineConsumerDeviceSet&& other) noexcept {
        if (this == &other) return *this;
        clear();
        capacity_ = other.capacity_;
        records_ = std::move(other.records_);
        order_ = std::move(other.order_);
        other.clear();
        return *this;
    }

    RecordPtr find(std::string_view full_policy_identity, uint64_t generation) const {
        auto found = records_.find(full_policy_identity);
        if (found == records_.end() || !joined(found->first, found->second) ||
            found->second->device_generation != generation) return {};
        return found->second;
    }

    bool publish(const RecordPtr& record) {
        if (!capacity_ || !record || !record->consumer) return false;
        const std::string_view policy = record->consumer->policy_identity;
        if (!joined(policy, record)) return false;
        auto found = records_.find(policy);
        if (found != records_.end()) return found->second == record && joined(found->first, found->second);
        if (!records_.empty()) {
            const auto& first = records_.begin()->second;
            if (!joined(records_.begin()->first, first) ||
                first->consumer->original != record->consumer->original ||
                first->consumer->evaluator != record->consumer->evaluator ||
                first->device_generation != record->device_generation) return false;
        }
        // Allocate both bookkeeping nodes before releasing any resident owner.
        Records prospective;
        prospective.emplace(policy, record);
        std::list<std::string_view> prospective_order;
        prospective_order.push_back(policy);
        auto node = prospective.extract(prospective.begin());
        while (records_.size() >= capacity_) {
            const auto oldest = order_.front();
            order_.pop_front();  // Drop borrowed view before its backing owner.
            records_.erase(oldest);
        }
        records_.insert(std::move(node));
        order_.splice(order_.end(), prospective_order);
        return true;
    }

    bool detach(std::string_view full_policy_identity, uint64_t generation) {
        auto found = records_.find(full_policy_identity);
        if (found == records_.end() || found->second->device_generation != generation) return false;
        for (auto item = order_.begin(); item != order_.end(); ++item)
            if (*item == full_policy_identity) { order_.erase(item); break; }
        records_.erase(found);
        return true;
    }

    void clear() {
        order_.clear();
        records_.clear();
    }
    size_t size() const { return records_.size(); }
    template <class Visitor>
    void for_each_consumer(Visitor&& visitor) const {
        for (const auto& [policy, record] : records_) visitor(policy, record->consumer);
    }
    template <class Visitor>
    void for_each_record(Visitor&& visitor) const {
        for (const auto& [policy, record] : records_) { (void)policy; visitor(record); }
    }

    // Detached external records are intentionally excluded. Runtime live-owner
    // probes must deduplicate their pointers across snapshots and Tickets, and
    // account their storage in addition to this resident joint-artifact charge.
    size_t storage_bytes() const {
        size_t bytes = sizeof(*this);
        for (const auto& [policy, record] : records_) {
            (void)policy;
            bytes = detail::consumer_device_add_bytes(bytes,
                sizeof(typename Records::value_type) + 3 * sizeof(void*) + 2 * sizeof(void*));
            bytes = detail::consumer_device_add_bytes(bytes, record->storage_bytes());
        }
        return detail::consumer_device_add_bytes(bytes,
            detail::consumer_device_mul_bytes(order_.size(), sizeof(std::string_view) + 2 * sizeof(void*)));
    }

  private:
    using Records = std::map<std::string_view, RecordPtr, std::less<>>;
    static bool joined(std::string_view policy, const RecordPtr& record) {
        return record && record->consumer && !policy.empty() &&
            policy == record->consumer->policy_identity &&
            record->ready_for(record->device_generation, record->consumer->original,
                              record->consumer->evaluator);
    }
    size_t capacity_ = 128;
    Records records_;
    std::list<std::string_view> order_;
};

}  // namespace vispy::lines
