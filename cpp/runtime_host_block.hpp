#pragma once
// SPDX-License-Identifier: AGPL-3.0-only
// Plan P5 (user, 2026-10-31: D26). A DATA payload snapshot of at least 1 MiB lives in a host block: page-aligned
// memory that a full texture update makes the texture's CPU shadow, and that the GPU can copy from directly once the
// runtime imports it (Dawn's HostMappedPointer), so the upload makes no staging copy. A block is shared by its
// owners and written only while one owner holds it. The last owner returns it to a pool that keeps a few warm, as the
// byte recycler keeps vectors (runtime_byte_recycler.hpp). An imported block's pages stay allocated until the
// runtime has released the import and knows that Dawn has freed it: a frame submitted after the release has
// retired, or the device is destroyed.
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <memory>
#include <mutex>
#include <new>
#include <vector>
#if defined(_WIN32)
#include <malloc.h>
#endif

namespace vispy::memory {

class HostBlockPool;

class HostBlock {
public:
    // A multiple of every page size Dawn's imports need (4 KiB on Vulkan, 16 KiB on Apple GPUs).
    static constexpr size_t alignment = size_t{64} << 10;

    HostBlock(const HostBlock&) = delete;
    HostBlock& operator=(const HostBlock&) = delete;
    uint8_t* data() const noexcept { return data_; }
    size_t size() const noexcept { return size_; }
    size_t capacity() const noexcept { return capacity_; }

private:
    friend class HostBlockPool;
    HostBlock(uint8_t* data, size_t capacity) noexcept : data_(data), capacity_(capacity) {}
    uint8_t* data_;
    size_t size_ = 0;
    size_t capacity_;
    // True from an import's creation until it is disposed of (HostBlockPool::imported and disposed).
    std::atomic<bool> imported_{false};
};

using HostBytes = std::shared_ptr<HostBlock>;

class HostBlockPool {
public:
    static constexpr size_t min_bytes = size_t{1} << 20;  // smaller payloads stay vectors
    static constexpr size_t max_blocks = 4;
    static constexpr size_t max_bytes = size_t{2} << 30;

    // A block of `size` bytes with unspecified contents: a kept block whose capacity is between size and twice size,
    // else a new one. Throws std::bad_alloc when memory runs out.
    HostBytes take(size_t size) {
        if (size < min_bytes || size > SIZE_MAX - HostBlock::alignment) throw std::bad_alloc();
        HostBlock* block = nullptr;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            auto best = kept_.end();
            for (auto it = kept_.begin(); it != kept_.end(); ++it)
                if ((*it)->capacity_ >= size && (*it)->capacity_ / 2 <= size &&
                    (best == kept_.end() || (*it)->capacity_ < (*best)->capacity_)) best = it;
            if (best != kept_.end()) {
                block = *best;
                kept_.erase(best);
                kept_bytes_ -= block->capacity_;
                ++reuses_;
            }
        }
        if (!block) {
            const size_t capacity = (size + HostBlock::alignment - 1) / HostBlock::alignment * HostBlock::alignment;
            void* pages = allocate(capacity);
            if (!pages) throw std::bad_alloc();
            block = new (std::nothrow) HostBlock(static_cast<uint8_t*>(pages), capacity);
            if (!block) {
                deallocate(pages);
                throw std::bad_alloc();
            }
            std::lock_guard<std::mutex> lock(mutex_);
            ++allocations_;
        }
        block->size_ = size;
        // If the owner's control block cannot be allocated, the deleter returns the block before the throw.
        return HostBytes(block, [this](HostBlock* returned) { give(returned); });
    }

    // The runtime's import cache: an import of `block` was created, or it was disposed of (Dawn has freed it).
    void imported(HostBlock& block) noexcept {
        pinned_bytes_.fetch_add(block.capacity_);
        block.imported_.store(true);
    }
    void disposed(HostBlock& block) noexcept {
        pinned_bytes_.fetch_sub(block.capacity_);
        block.imported_.store(false);
    }
    static bool is_imported(const HostBlock& block) noexcept { return block.imported_.load(); }
    // Bytes of imports not yet disposed of, released ones included.
    uint64_t pinned_bytes() const noexcept { return pinned_bytes_.load(); }

    // Whether the pool dropped this imported block, which now only waits for its import to be released.
    bool waiting(const HostBlock* block) {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto* candidate : waiting_)
            if (candidate == block) return true;
        return false;
    }

    // Frees dropped blocks whose imports have been disposed of. The runtime calls it after disposing of imports.
    void free_disposed() noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto it = waiting_.begin(); it != waiting_.end();) {
            if ((*it)->imported_.load()) {
                ++it;
                continue;
            }
            destroy(*it);
            it = waiting_.erase(it);
        }
    }

    void clear() noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto* block : kept_) drop(block);
        kept_.clear();
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
    size_t allocations() {
        std::lock_guard<std::mutex> lock(mutex_);
        return allocations_;
    }

    // Never destroyed: an owner released during process teardown still returns its block here.
    static HostBlockPool& shared() {
        static HostBlockPool* pool = new HostBlockPool;
        return *pool;
    }

private:
    static void* allocate(size_t capacity) noexcept {
#if defined(_WIN32)
        return _aligned_malloc(capacity, HostBlock::alignment);
#else
        return std::aligned_alloc(HostBlock::alignment, capacity);
#endif
    }
    static void deallocate(void* pages) noexcept {
#if defined(_WIN32)
        _aligned_free(pages);
#else
        std::free(pages);
#endif
    }
    static void destroy(HostBlock* block) noexcept {
        deallocate(block->data_);
        delete block;
    }

    // Under the lock: an imported block waits until its import is disposed of; any other block is freed now.
    void drop(HostBlock* block) noexcept {
        if (!block->imported_.load()) {
            destroy(block);
            return;
        }
        try {
            waiting_.push_back(block);
        } catch (...) {
            // Never free pages an import may still hold: without room to wait, the block is left allocated.
        }
    }

    // The deleter of every HostBytes: keep the block warm if there is room, the oldest leaving first.
    void give(HostBlock* block) noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        try {
            kept_.push_back(block);
        } catch (...) {
            drop(block);
            return;
        }
        kept_bytes_ += block->capacity_;
        while (kept_.size() > max_blocks || kept_bytes_ > max_bytes) {
            HostBlock* oldest = kept_.front();
            kept_.erase(kept_.begin());
            kept_bytes_ -= oldest->capacity_;
            drop(oldest);
        }
    }

    std::mutex mutex_;
    std::vector<HostBlock*> kept_;     // oldest first
    std::vector<HostBlock*> waiting_;  // dropped while imported
    size_t kept_bytes_ = 0;
    size_t reuses_ = 0;
    size_t allocations_ = 0;
    std::atomic<uint64_t> pinned_bytes_{0};
};

}  // namespace vispy::memory
