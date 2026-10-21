#pragma once

#include <cstdint>

// Versioned, coherent process-wide observation of intercepted Vulkan device
// memory handles. allocationSize includes allocator slabs/padding; it is not
// resource descriptor size, physical residency, or opaque driver memory.
// vkFreeMemory releases the handle; implementations may retain its payload
// until bound resources are destroyed. Retired records are not counted as frees.
struct VulkanMemoryTelemetry {
    uint64_t schema = 1;
    uint64_t active_devices = 0;
    uint64_t tracking_devices = 0;
    uint64_t allocate_calls = 0;
    uint64_t allocate_failures = 0;
    uint64_t allocation_count = 0;
    uint64_t allocated_bytes = 0;
    uint64_t free_calls = 0;
    uint64_t free_count = 0;
    uint64_t freed_bytes = 0;
    uint64_t null_free_calls = 0;
    uint64_t unknown_free_calls = 0;
    uint64_t live_allocations = 0;
    uint64_t live_bytes = 0;
    uint64_t peak_live_allocations = 0;
    uint64_t peak_live_bytes = 0;
    uint64_t retired_allocations = 0;
    uint64_t retired_bytes = 0;
    uint64_t tracking_errors = 0;
};

using VulkanMemorySnapshotFn = uint32_t (*)(VulkanMemoryTelemetry*, uint32_t);

#include <stdexcept>
#include <string>

// Additive ABI: never change the lifetime snapshot above. A window observes
// process-wide intercepted allocationSize totals and handle ownership, not
// physical/opaque driver memory or external-import payload sizes.
enum class VulkanMemoryWindowStatus : uint64_t {
    Unavailable = 0, Active = 1, Complete = 2, Incomplete = 3,
    Overlap = 4, InvalidToken = 5, TokenExhausted = 6, Cancelled = 7, Busy = 8,
};
enum VulkanMemoryWindowInvalidation : uint64_t {
    WindowTrackingError = 1, WindowOverflow = 2, WindowDeviceRetired = 4,
    WindowDeviceLost = 8, WindowCancelled = 16, WindowUnavailable = 32,
    WindowBusy = 64,
};
struct VulkanMemoryWindow {
    uint64_t schema = 1;
    uint64_t token = 0;
    VulkanMemoryWindowStatus status = VulkanMemoryWindowStatus::Unavailable;
    uint64_t supported = 0, available = 0, complete = 0, invalidations = 0;
    uint64_t seed_live_allocations = 0, seed_live_bytes = 0;
    // Event fields are window deltas. Live and peak fields retain absolute
    // tracked ownership including the seed; retired records are never frees.
    VulkanMemoryTelemetry counters;
};
using VulkanMemoryWindowBeginFn = uint32_t (*)(VulkanMemoryWindow*, uint32_t);
using VulkanMemoryWindowEndFn = uint32_t (*)(uint64_t, VulkanMemoryWindow*, uint32_t);

struct VulkanMemoryWindowFunctions {
    VulkanMemoryWindowBeginFn begin = nullptr;
    VulkanMemoryWindowEndFn end = nullptr;
};

// NativeLibrary::symbol is deliberately strict. Only these two additive names
// may be absent on an older layer; every other loader error must propagate.
template <typename Library>
VulkanMemoryWindowFunctions optional_vulkan_memory_window_functions(const Library& library) {
    auto optional = [&library](const char* name) -> void* {
        try { return library.symbol(name); }
        catch (const std::runtime_error& error) {
            if (std::string(error.what()) != std::string("native loader: required symbol is absent: ") + name) throw;
            return nullptr;
        }
    };
    VulkanMemoryWindowFunctions functions;
    functions.begin = reinterpret_cast<VulkanMemoryWindowBeginFn>(optional("vispy_layer_vk_memory_window_begin"));
    functions.end = reinterpret_cast<VulkanMemoryWindowEndFn>(optional("vispy_layer_vk_memory_window_end"));
    if (!functions.begin || !functions.end) return {}; // A partial pair is unsupported.
    return functions;
}

// Cancellation closes an exact owner without running fallible completion
// polling. Normal end still polls and verifies retirement before closing.
template <typename Poll, typename Idle, typename Close>
VulkanMemoryWindow finish_vulkan_memory_window(bool cancel, Poll poll, Idle idle, Close close) {
    if (cancel) return close(true);
    poll();
    if (!idle()) throw std::runtime_error("allocation window: end requires retired measured work");
    return close(false);
}

// Pure CPU state machine. The layer calls every method under dispatch_mutex.
// No dynamic storage, blocking work, counter reset or backend allocation occurs.
class VulkanMemoryWindowState {
public:
    explicit VulkanMemoryWindowState(uint64_t last_token = 0) : next_(last_token) {}
    VulkanMemoryWindow begin(const VulkanMemoryTelemetry& source, bool available, bool idle = true) {
        VulkanMemoryWindow refused;
        refused.supported = 1;
        if (active_) { refused.status = VulkanMemoryWindowStatus::Overlap; return refused; }
        refused.available = available;
        if (!available) return refused;
        if (!idle) { refused.status = VulkanMemoryWindowStatus::Busy; return refused; }
        if (source.tracking_errors || source.retired_allocations || history_invalidations_) {
            refused.status = VulkanMemoryWindowStatus::Incomplete;
            refused.invalidations = history_invalidations_ | WindowTrackingError;
            return refused;
        }
        if (next_ == UINT64_MAX) { refused.status = VulkanMemoryWindowStatus::TokenExhausted; return refused; }
        current_ = {};
        current_.token = ++next_;
        current_.status = VulkanMemoryWindowStatus::Active;
        current_.supported = 1;
        current_.available = current_.complete = 1;
        current_.seed_live_allocations = current_.counters.live_allocations = source.live_allocations;
        current_.seed_live_bytes = current_.counters.live_bytes = source.live_bytes;
        current_.counters.peak_live_allocations = source.live_allocations;
        current_.counters.peak_live_bytes = source.live_bytes;
        previous_ = source;
        active_ = true;
        return current_;
    }
    void invalidate(uint64_t reason) {
        if (active_) { current_.invalidations |= reason; current_.complete = 0; }
    }
    void observe(const VulkanMemoryTelemetry& source) {
        // Continue detecting cumulative overflow during cold/warm intervals;
        // it must not become a plausible but corrupted seed for a later window.
#define VISPY_WINDOW_HISTORY(field) if (source.field < previous_.field) history_invalidations_ |= WindowOverflow
        VISPY_WINDOW_HISTORY(allocate_calls); VISPY_WINDOW_HISTORY(allocate_failures);
        VISPY_WINDOW_HISTORY(allocation_count); VISPY_WINDOW_HISTORY(allocated_bytes);
        VISPY_WINDOW_HISTORY(free_calls); VISPY_WINDOW_HISTORY(free_count);
        VISPY_WINDOW_HISTORY(freed_bytes); VISPY_WINDOW_HISTORY(null_free_calls);
        VISPY_WINDOW_HISTORY(unknown_free_calls); VISPY_WINDOW_HISTORY(retired_allocations);
        VISPY_WINDOW_HISTORY(retired_bytes); VISPY_WINDOW_HISTORY(tracking_errors);
#undef VISPY_WINDOW_HISTORY
        if (!active_) { previous_ = source; return; }
        if (history_invalidations_) invalidate(history_invalidations_);
#define VISPY_WINDOW_DELTA(field) delta(current_.counters.field, previous_.field, source.field)
        VISPY_WINDOW_DELTA(allocate_calls); VISPY_WINDOW_DELTA(allocate_failures);
        VISPY_WINDOW_DELTA(allocation_count); VISPY_WINDOW_DELTA(allocated_bytes);
        VISPY_WINDOW_DELTA(free_calls); VISPY_WINDOW_DELTA(free_count);
        VISPY_WINDOW_DELTA(freed_bytes); VISPY_WINDOW_DELTA(null_free_calls);
        VISPY_WINDOW_DELTA(unknown_free_calls); VISPY_WINDOW_DELTA(retired_allocations);
        VISPY_WINDOW_DELTA(retired_bytes); VISPY_WINDOW_DELTA(tracking_errors);
#undef VISPY_WINDOW_DELTA
        auto& c = current_.counters;
        c.live_allocations = source.live_allocations;
        c.live_bytes = source.live_bytes;
        if (c.live_allocations > c.peak_live_allocations) c.peak_live_allocations = c.live_allocations;
        if (c.live_bytes > c.peak_live_bytes) c.peak_live_bytes = c.live_bytes;
        if (c.tracking_errors || c.unknown_free_calls) invalidate(WindowTrackingError);
        if (c.retired_allocations) invalidate(WindowDeviceRetired);
        conservation(current_.seed_live_allocations, c.allocation_count, c.free_count,
                     c.retired_allocations, c.live_allocations);
        conservation(current_.seed_live_bytes, c.allocated_bytes, c.freed_bytes,
                     c.retired_bytes, c.live_bytes);
        previous_ = source;
    }
    VulkanMemoryWindow end(uint64_t token, const VulkanMemoryTelemetry& source,
                           bool available, bool idle = true) {
        if (!active_ || !token || token != current_.token) {
            VulkanMemoryWindow refused; refused.token = token;
            refused.supported = 1;
            refused.status = VulkanMemoryWindowStatus::InvalidToken;
            return refused; // A foreign/stale token never consumes the owner.
        }
        observe(source);
        current_.available = available;
        if (!available) invalidate(WindowUnavailable);
        if (!idle) invalidate(WindowBusy);
        current_.status = current_.complete ? VulkanMemoryWindowStatus::Complete : VulkanMemoryWindowStatus::Incomplete;
        active_ = false;
        return current_;
    }
private:
    void delta(uint64_t& destination, uint64_t before, uint64_t after) {
        if (after < before || UINT64_MAX - destination < after - before) {
            history_invalidations_ |= WindowOverflow;
            invalidate(WindowOverflow); return;
        }
        destination += after - before;
    }
    void conservation(uint64_t seed, uint64_t allocated, uint64_t freed,
                      uint64_t retired, uint64_t live) {
        if (UINT64_MAX - seed < allocated) { history_invalidations_ |= WindowOverflow; invalidate(WindowOverflow); return; }
        const uint64_t sum = seed + allocated;
        if (freed > sum || retired > sum - freed || sum - freed - retired != live)
            invalidate(WindowTrackingError);
    }
    bool active_ = false;
    uint64_t next_ = 0;
    uint64_t history_invalidations_ = 0;
    VulkanMemoryWindow current_;
    VulkanMemoryTelemetry previous_;
};
