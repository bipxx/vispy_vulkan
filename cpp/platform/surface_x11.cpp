#include "native_surface.hpp"

#if defined(__linux__)
#include <X11/Xlib.h>

#include <limits>
#include <atomic>
#include <mutex>

namespace vispy::platform {
namespace {
// Xlib error handlers are process-wide. Confine this short probe to the GUI
// thread, delegate unrelated Display errors, and restore the caller's handler.
std::mutex probe_mutex;
std::atomic<Display*> probe_display{nullptr};
std::atomic<bool> probe_error{false};
std::atomic<XErrorHandler> prior_handler{nullptr};
int liveness_error(Display* display, XErrorEvent* error) {
    if (display == probe_display.load()) { probe_error = true; return 0; }
    auto previous = prior_handler.load();
    return previous ? previous(display, error) : 0;
}
class XlibSurfaceOwner final : public NativeSurfaceOwner {
  public:
    explicit XlibSurfaceOwner(const NativeSurfaceDescriptor& descriptor) : NativeSurfaceOwner(descriptor) {
        if (descriptor.kind != NativeSurfaceKind::Xlib || !descriptor.window ||
            descriptor.window > std::numeric_limits<unsigned long>::max())
            throw std::runtime_error("X11 surface: expected a nonzero Xlib Window descriptor");
        if (descriptor.open_owned_display) {
            if (descriptor.display)
                throw std::runtime_error("X11 surface: owned connection must be opened by the helper, not adopted");
            // This private Display is confined to the GUI thread; no late
            // process-wide XInitThreads call is made after Qt has used Xlib.
            display_ = XOpenDisplay(descriptor.display_name.empty() ? nullptr : descriptor.display_name.c_str());
            owned_ = true;
        } else {
            display_ = reinterpret_cast<Display*>(descriptor.display);
        }
        if (!display_) throw std::runtime_error("X11 surface: display connection is null or XOpenDisplay failed");
        descriptor_.display = reinterpret_cast<uintptr_t>(display_);
    }
    ~XlibSurfaceOwner() override {
        // Runtime releases after surface retirement, on the GUI thread. The
        // borrowed connection is never closed here.
        if (owned_ && display_) XCloseDisplay(display_);
    }
    wgpu::Surface create_surface(const wgpu::Instance& instance) override {
        check_thread("X11 CreateSurface");
        if (!is_alive()) throw std::runtime_error("X11 CreateSurface: native window has been destroyed");
        if (!instance) throw std::runtime_error("X11 CreateSurface: Dawn instance is null");
        wgpu::SurfaceSourceXlibWindow source;
        source.display = display_;
        source.window = descriptor_.window;
        wgpu::SurfaceDescriptor descriptor;
        descriptor.nextInChain = &source;
        // Dawn validates the window with its scoped X error handler. Calling
        // XGetWindowAttributes here would invoke the caller's fatal X handler.
        auto surface = instance.CreateSurface(&descriptor);
        if (!surface) throw std::runtime_error("X11 CreateSurface: Dawn returned a null surface");
        return surface;
    }
    bool is_alive() const override {
        check_thread("X11 surface liveness");
        if (!display_) return false;
        std::lock_guard lock(probe_mutex);
        XSync(display_, False);
        probe_display = display_;
        probe_error = false;
        prior_handler = XSetErrorHandler(liveness_error);
        XWindowAttributes attributes{};
        int status = XGetWindowAttributes(display_, static_cast<Window>(descriptor_.window), &attributes);
        XSync(display_, False);
        XSetErrorHandler(prior_handler.load());
        probe_display = nullptr;
        return status != 0 && !probe_error.load();
    }
    void update(int width, int height, double scale) override {
        check_thread("X11 surface update");
        check_size(width, height, scale);
    }
    void detach() override { check_thread("X11 surface detach"); }

  private:
    Display* display_ = nullptr;
    bool owned_ = false;
};
}  // namespace

std::shared_ptr<NativeSurfaceOwner> make_native_surface_owner(const NativeSurfaceDescriptor& descriptor) {
    return std::make_shared<XlibSurfaceOwner>(descriptor);
}
}  // namespace vispy::platform
#endif
