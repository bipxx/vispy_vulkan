#pragma once
// SPDX-License-Identifier: AGPL-3.0-only
// Large byte blocks that would otherwise be freed every frame -- a texture shadow replaced by a transferred
// upload, a DATA payload already copied into a buffer -- keep their committed pages here, so the next payload
// snapshot of a similar size copies into warm memory instead of faulting in a fresh allocation. On this desktop a
// 64 MiB copy into fresh memory takes 12.3 ms and into reused memory 5.6 ms (run perf-profile-261).
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <utility>
#include <vector>

namespace vispy::memory {

class ByteRecycler {
public:
    static constexpr size_t min_bytes = size_t{1} << 20;  // smaller blocks go back to the allocator
    static constexpr size_t max_blocks = 4;
    static constexpr size_t max_bytes = size_t{2} << 30;

    // Keep the block's storage if it is large; contents are not preserved. The oldest blocks leave first. Never
    // throws: callers give a shadow's storage just before replacing it, and a block that cannot be kept is freed.
    void give(std::vector<uint8_t>&& bytes) noexcept {
        std::vector<uint8_t> block = std::move(bytes);
        if (block.capacity() < min_bytes || block.capacity() > max_bytes) return;
        try {
            block.resize(block.capacity());  // a taken block shrinks without touching memory
            std::lock_guard<std::mutex> lock(mutex_);
            kept_.push_back(std::move(block));
            kept_bytes_ += kept_.back().capacity();
            while (kept_.size() > max_blocks || kept_bytes_ > max_bytes) {
                kept_bytes_ -= kept_.front().capacity();
                kept_.erase(kept_.begin());
            }
        } catch (...) {
        }
    }

    // A block of exactly `size` bytes with unspecified contents, or an empty vector when no kept block has a
    // capacity between size and twice size; the caller then allocates as before.
    std::vector<uint8_t> take(size_t size) {
        if (size < min_bytes) return {};
        std::lock_guard<std::mutex> lock(mutex_);
        auto best = kept_.end();
        for (auto it = kept_.begin(); it != kept_.end(); ++it)
            if (it->capacity() >= size && it->capacity() / 2 <= size &&
                (best == kept_.end() || it->capacity() < best->capacity())) best = it;
        if (best == kept_.end()) return {};
        std::vector<uint8_t> block = std::move(*best);
        kept_.erase(best);
        kept_bytes_ -= block.capacity();
        block.resize(size);
        ++reuses_;
        return block;
    }

    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        kept_.clear();
        kept_.shrink_to_fit();
        kept_bytes_ = 0;
    }

    size_t kept_bytes() {
        std::lock_guard<std::mutex> lock(mutex_);
        return kept_bytes_;
    }

    size_t reuses() {
        std::lock_guard<std::mutex> lock(mutex_);
        return reuses_;
    }

    static ByteRecycler& shared() {
        static ByteRecycler recycler;
        return recycler;
    }

private:
    std::mutex mutex_;
    std::vector<std::vector<uint8_t>> kept_;
    size_t kept_bytes_ = 0;
    size_t reuses_ = 0;
};

}  // namespace vispy::memory
