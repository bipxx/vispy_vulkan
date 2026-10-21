#include "native_surface.hpp"

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <limits>

namespace vispy::platform {
namespace {
class Win32SurfaceOwner final : public NativeSurfaceOwner {
  public:
    explicit Win32SurfaceOwner(const NativeSurfaceDescriptor& descriptor) : NativeSurfaceOwner(descriptor) {
        if (descriptor.kind != NativeSurfaceKind::Win32 || !descriptor.window ||
            descriptor.window > std::numeric_limits<uintptr_t>::max())
            throw std::runtime_error("Win32 surface: expected a nonzero pointer-sized HWND descriptor");
        validate_window();
        if (!descriptor_.hinstance)
            descriptor_.hinstance = static_cast<uintptr_t>(GetWindowLongPtrW(
                reinterpret_cast<HWND>(static_cast<uintptr_t>(descriptor_.window)), GWLP_HINSTANCE));
        if (!descriptor_.hinstance)
            descriptor_.hinstance = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        if (!descriptor_.hinstance)
            throw std::runtime_error("Win32 surface: process HINSTANCE is unavailable");
    }
    wgpu::Surface create_surface(const wgpu::Instance& instance) override {
        check_thread("Win32 CreateSurface");
        validate_window();
        if (!instance) throw std::runtime_error("Win32 CreateSurface: Dawn instance is null");
        wgpu::SurfaceSourceWindowsHWND source;
        source.hwnd = reinterpret_cast<void*>(static_cast<uintptr_t>(descriptor_.window));
        source.hinstance = reinterpret_cast<void*>(descriptor_.hinstance);
        wgpu::SurfaceDescriptor descriptor;
        descriptor.nextInChain = &source;
        auto surface = instance.CreateSurface(&descriptor);
        if (!surface) throw std::runtime_error("Win32 CreateSurface: Dawn returned a null surface");
        return surface;
    }
    bool is_alive() const override {
        check_thread("Win32 surface liveness");
        DWORD process = 0;
        HWND window = reinterpret_cast<HWND>(static_cast<uintptr_t>(descriptor_.window));
        DWORD thread = GetWindowThreadProcessId(window, &process);
        return IsWindow(window) && process == GetCurrentProcessId() && thread == GetCurrentThreadId();
    }
    void update(int width, int height, double scale) override {
        check_thread("Win32 surface update");
        check_size(width, height, scale);
        validate_window();
    }
    void detach() override { check_thread("Win32 surface detach"); }

  private:
    void validate_window() const {
        HWND window = reinterpret_cast<HWND>(static_cast<uintptr_t>(descriptor_.window));
        DWORD process = 0;
        DWORD thread = GetWindowThreadProcessId(window, &process);
        if (!IsWindow(window) || !thread || process != GetCurrentProcessId())
            throw std::runtime_error("Win32 surface: HWND is not a live window owned by this process");
        if (thread != GetCurrentThreadId())
            throw std::runtime_error("Win32 surface: HWND belongs to another GUI thread");
    }
};
}  // namespace

std::shared_ptr<NativeSurfaceOwner> make_native_surface_owner(const NativeSurfaceDescriptor& descriptor) {
    return std::make_shared<Win32SurfaceOwner>(descriptor);
}
}  // namespace vispy::platform
#endif
