#pragma once

#include <cstddef>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>

namespace vispy::lines {

// Descriptor/host bookkeeping, never an estimate of opaque driver memory.
// Gather the complete owner graph under the runtime mutex before finish().
// Identity pointers are borrowed only for this observation: the caller retains
// all Artifact/record owners through gathering and classification.
class LineDeviceDescriptorAccounting {
  public:
    struct Result {
        size_t cached_container_bytes = 0, uncached_container_bytes = 0;
        size_t cached_record_bytes = 0, uncached_record_bytes = 0;
        size_t cached_bytes = 0, uncached_bytes = 0, live_bytes = 0;
        size_t artifact_count = 0, cached_artifact_count = 0, uncached_artifact_count = 0;
        size_t record_count = 0, cached_record_count = 0, uncached_record_count = 0;
        bool saturated = false;
    };

    // total includes the Artifact's inline state, map/FIFO nodes and each
    // contained record contribution. Repeated identity has one stable cost;
    // cached observations upgrade external ones and never downgrade them.
    void observe_artifact(const void* identity, bool cached, size_t total_bytes) {
        if (!identity) throw std::invalid_argument("line device accounting: null Artifact identity");
        auto [item, added] = artifacts_.try_emplace(identity, Artifact{cached, total_bytes, {}});
        if (!added) {
            if (item->second.total_bytes != total_bytes)
                throw std::invalid_argument("line device accounting: Artifact footprint changed during observation");
            item->second.cached = item->second.cached || cached;
        }
    }

    // Matches LineConsumerDeviceSet's contribution: payload storage_bytes()
    // plus one shared-owner allocation's control bookkeeping. Per-container
    // map/FIFO/shared_ptr fields remain in the Artifact's residual footprint.
    void observe_record(const void* identity, size_t payload_bytes,
                        size_t shared_owner_bytes = 2 * sizeof(void*)) {
        if (!identity) throw std::invalid_argument("line device accounting: null record identity");
        auto [item, added] = records_.try_emplace(identity, Record{payload_bytes, shared_owner_bytes});
        if (!added && (item->second.payload_bytes != payload_bytes ||
                       item->second.shared_owner_bytes != shared_owner_bytes))
            throw std::invalid_argument("line device accounting: record footprint changed during observation");
    }

    void contains(const void* artifact_identity, const void* record_identity) {
        auto artifact = artifacts_.find(artifact_identity);
        if (artifact == artifacts_.end() || !records_.contains(record_identity))
            throw std::invalid_argument("line device accounting: containment edge lacks an observed owner");
        // Duplicate routes to the same contained allocation never subtract it
        // twice. Multiple Artifact containers may own the same record.
        artifact->second.records.insert(record_identity);
    }

    Result finish() const {
        Result result;
        std::set<const void*, std::less<const void*>> cached_records;
        // First establish complete containment and preserve every container's
        // exclusive bookkeeping. Saturated totals stay saturated after removal
        // of any finite or saturated record contribution.
        for (const auto& [identity, artifact] : artifacts_) {
            (void)identity;
            size_t included = 0;
            for (const auto* record_identity : artifact.records) {
                const auto& record = records_.at(record_identity);
                included = add(included, record.bytes());
                if (artifact.cached) cached_records.insert(record_identity);
            }
            size_t residual = maximum;
            if (artifact.total_bytes != maximum) {
                if (included == maximum || artifact.total_bytes < included)
                    throw std::invalid_argument("line device accounting: finite Artifact footprint omits contained record costs");
                residual = artifact.total_bytes - included;
            }
            ++result.artifact_count;
            if (artifact.cached) {
                ++result.cached_artifact_count;
                result.cached_container_bytes = add(result.cached_container_bytes, residual);
            } else {
                ++result.uncached_artifact_count;
                result.uncached_container_bytes = add(result.uncached_container_bytes, residual);
            }
        }
        // Charge every allocation once. Any resident container covers its
        // record; otherwise it is an uncached owner, including detached records
        // reached only through DRAW snapshots or submitted Tickets.
        for (const auto& [identity, record] : records_) {
            ++result.record_count;
            if (cached_records.contains(identity)) {
                ++result.cached_record_count;
                result.cached_record_bytes = add(result.cached_record_bytes, record.bytes());
            } else {
                ++result.uncached_record_count;
                result.uncached_record_bytes = add(result.uncached_record_bytes, record.bytes());
            }
        }
        result.cached_bytes = add(result.cached_container_bytes, result.cached_record_bytes);
        result.uncached_bytes = add(result.uncached_container_bytes, result.uncached_record_bytes);
        result.live_bytes = add(result.cached_bytes, result.uncached_bytes);
        result.saturated = result.live_bytes == maximum;
        return result;
    }

    void clear() { artifacts_.clear(); records_.clear(); }

  private:
    static constexpr size_t maximum = std::numeric_limits<size_t>::max();
    static size_t add(size_t left, size_t right) {
        return right > maximum - left ? maximum : left + right;
    }
    struct Record {
        size_t payload_bytes, shared_owner_bytes;
        size_t bytes() const { return add(payload_bytes, shared_owner_bytes); }
    };
    struct Artifact {
        bool cached;
        size_t total_bytes;
        std::set<const void*, std::less<const void*>> records;
    };
    std::map<const void*, Artifact, std::less<const void*>> artifacts_;
    std::map<const void*, Record, std::less<const void*>> records_;
};

}  // namespace vispy::lines
