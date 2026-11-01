#pragma once

#include <dawn/webgpu_cpp.h>

#include <cmath>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>

namespace vispy::platform {

enum class NativeSurfaceKind { Win32, Xlib, Metal };

// Windows and X11 native windows may be destroyed immediately after the GUI
// clear/close call. Drain Dawn's deferred Surface deletion before returning
// ownership to the GUI. Metal keeps its separate weak-view detach policy.
inline bool native_surface_requires_retirement_drain(NativeSurfaceKind kind) {
    return kind == NativeSurfaceKind::Win32 || kind == NativeSurfaceKind::Xlib;
}


struct NativeSurfaceDescriptor {
    NativeSurfaceKind kind = NativeSurfaceKind::Win32;
    uint64_t window = 0;  // HWND, Xlib Window (never narrowed), or borrowed NSView.
    uintptr_t display = 0;
    uintptr_t hinstance = 0;
    bool open_owned_display = false;
    std::string display_name;
};

// Runtime owns the Dawn surface and instance. Retain this owner through
// unconfiguration AND completion of work using the old surface. A borrowed
// native window/view must remain alive until its GUI-thread clear_surface;
// Metal additionally uses a weak view reference when detaching at retirement.
class NativeSurfaceOwner {
  public:
    virtual ~NativeSurfaceOwner() = default;
    virtual wgpu::Surface create_surface(const wgpu::Instance& instance) = 0;
    virtual bool is_alive() const = 0;
    virtual void update(int physical_width, int physical_height, double scale) = 0;
    virtual void detach() = 0;
    // The refresh interval of the display showing the window, in ns, or 0 when unknown (vsynced pacing, plan P2).
    virtual uint64_t refresh_interval_ns() const { return 0; }
    const NativeSurfaceDescriptor& descriptor() const { return descriptor_; }

  protected:
    explicit NativeSurfaceOwner(NativeSurfaceDescriptor descriptor)
        : descriptor_(std::move(descriptor)), owner_thread_(std::this_thread::get_id()) {}
    void check_thread(const char* operation) const {
        if (owner_thread_ != std::this_thread::get_id())
            throw std::runtime_error(std::string(operation) + ": native surface must be used on its GUI thread");
    }
    void check_size(int width, int height, double scale) const {
        if (width < 0 || height < 0 || !std::isfinite(scale) || scale <= 0)
            throw std::runtime_error("native surface update: invalid physical dimensions or scale");
    }
    NativeSurfaceDescriptor descriptor_;
    std::thread::id owner_thread_;
};

// The owner stays in its caller's existing slot on every failure. In
// particular, false from Tick is accepted only after the health check: Dawn
// also returns false on a lost/error device. No callback wait can overtake the
// Lowest-priority tick that drains a newly submitted deletion serial.
template <typename Owner, typename ReleaseSurface, typename SubmitEmpty,
          typename Tick, typename Healthy, typename Wait>
void retire_owned_surface(Owner& owner, ReleaseSurface release_surface,
                          SubmitEmpty submit_empty, Tick tick,
                          Healthy healthy, Wait wait) {
    if (!owner || owner.use_count() != 1)
        throw std::runtime_error("native surface retirement: outstanding surface owner references");
    healthy();
    release_surface();
    healthy();
    submit_empty();
    healthy();
    for (;;) {
        const bool pending = tick();
        healthy();
        if (!pending) {
            owner.reset();
            return;
        }
        wait();
    }
}

// Compile exactly one platform implementation. No Qt linkage is required.
std::shared_ptr<NativeSurfaceOwner> make_native_surface_owner(const NativeSurfaceDescriptor& descriptor);

}  // namespace vispy::platform
