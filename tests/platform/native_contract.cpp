#include "platform/native_library.hpp"
#include "platform/native_surface.hpp"

#include <atomic>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <optional>
#endif

using namespace vispy::platform;
namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
template <typename F> void rejected(F&& action, const char* message) {
    try { action(); } catch (const std::runtime_error&) { return; }
    throw std::runtime_error(message);
}

struct RetirementProbe {
    bool drained = false, closed_early = false;
    int closes = 0, wrappers = 0;
};
struct FakeSurfaceOwner {
    RetirementProbe& probe;
    bool owns_display;
    explicit FakeSurfaceOwner(RetirementProbe& p, bool owns = true) : probe(p), owns_display(owns) {}
    ~FakeSurfaceOwner() { ++probe.wrappers; if (owns_display) ++probe.closes; probe.closed_early |= !probe.drained; }
};
void retirement_contract() {
    require(native_surface_requires_retirement_drain(NativeSurfaceKind::Win32),
            "Win32 close returned without deferred Surface retirement policy");
    require(native_surface_requires_retirement_drain(NativeSurfaceKind::Xlib),
            "Xlib deferred Surface retirement policy removed");
    require(!native_surface_requires_retirement_drain(NativeSurfaceKind::Metal),
            "Metal weak-view policy changed without its own qualification");

    // Actual production template: the old completed serial is insufficient;
    // releasing the last Surface enqueues destruction at the next serial.
    RetirementProbe probe;
    auto owner = std::make_shared<FakeSurfaceOwner>(probe);
    std::vector<std::string> events;
    int submitted = 7, deletion = 0, ticks = 0;
    bool released = false;
    retire_owned_surface(owner,
        [&] { events.push_back("release"); released = true; deletion = submitted + 1; },
        [&] { events.push_back("submit"); require(released, "submit preceded final Surface release"); ++submitted; },
        [&] { events.push_back("tick"); require(owner && deletion == submitted, "owner or deletion serial missing");
              if (++ticks == 1) return true; probe.drained = true; return false; },
        [&] { events.push_back("healthy"); require(owner != nullptr, "owner closed before final healthy idle"); },
        [&] { events.push_back("wait"); require(owner != nullptr, "owner closed while unrelated work pending"); });
    require(!owner && probe.closes == 1 && !probe.closed_early && ticks == 2,
            "Display must close exactly once after deferred deletion/global idle");
    require(events == std::vector<std::string>{"healthy","release","healthy","submit","healthy",
        "tick","healthy","wait","tick","healthy"}, "public drain ordering changed");

    // A callback-hidden Surface/owner reference must refuse before release.
    RetirementProbe hidden_probe;
    auto hidden_owner = std::make_shared<FakeSurfaceOwner>(hidden_probe);
    auto callback_capture = hidden_owner;
    bool touched = false;
    rejected([&] { retire_owned_surface(hidden_owner, [&] { touched = true; }, [] {},
        [] { return false; }, [] {}, [] {}); }, "hidden owner capture accepted");
    require(hidden_owner && !touched && hidden_probe.closes == 0, "hidden capture refusal released native Display");
    callback_capture.reset(); hidden_probe.drained = true; hidden_owner.reset();

    // Every throw keeps the caller's owner for explicit later device teardown.
    for (int fail = 0; fail != 5; ++fail) {
        RetirementProbe p; auto retained = std::make_shared<FakeSurfaceOwner>(p);
        bool unhealthy = false;
        rejected([&] { retire_owned_surface(retained,
            [&] { if (fail == 0) throw std::runtime_error("release"); },
            [&] { if (fail == 1) throw std::runtime_error("submit"); },
            [&] { if (fail == 2) throw std::runtime_error("tick");
                  if (fail == 3) { unhealthy = true; return false; } return true; },
            [&] { if (unhealthy) throw std::runtime_error("lost/error false is not idle"); },
            [&] { throw std::runtime_error("timeout"); }); }, "retirement failure accepted");
        require(retained && p.closes == 0, "failure released Display before native device teardown");
        p.drained = true; retained.reset();
        require(p.closes == 1 && !p.closed_early, "failed retirement could not close after explicit device teardown");
    }
    // Missing owner and stale deferred deletion without a live Surface remain
    // explicit boundaries; no native object or GUI/provider is used by tests.
    std::shared_ptr<FakeSurfaceOwner> absent;
    rejected([&] { retire_owned_surface(absent, [] {}, [] {}, [] { return false; }, [] {}, [] {}); },
             "absent native owner accepted");
    RetirementProbe old; auto old_owner = std::make_shared<FakeSurfaceOwner>(old);
    bool submitted_after_release = false;
    retire_owned_surface(old_owner, [] {}, [&] { submitted_after_release = true; },
        [&] { require(submitted_after_release, "stale deletion did not get a new submit"); old.drained = true; return false; },
        [] {}, [] {});
    require(!old_owner && old.closes == 1 && !old.closed_early, "stale pending WSI deletion lost its owner");
}


struct FakeDeviceTeardownState {
    bool alive = true;
    int late_deletions = 0, enqueued = 0;
};
struct FakeTrackedSwapChain {
    FakeDeviceTeardownState& state;
    bool attached = true;
    explicit FakeTrackedSwapChain(FakeDeviceTeardownState& s) : state(s) {}
    void detach() {
        if (!attached) return;
        if (!state.alive) ++state.late_deletions;
        ++state.enqueued;
        attached = false;
    }
    ~FakeTrackedSwapChain() { detach(); }
};
void teardown_and_borrowed_contract() {
    // Borrowed Display ownership is untouched, but clear_surface must establish
    // the same safe caller lifetime boundary as the owned Display route.
    RetirementProbe borrowed;
    auto wrapper = std::make_shared<FakeSurfaceOwner>(borrowed, false);
    bool released = false, submitted = false;
    retire_owned_surface(wrapper, [&] { released = true; },
        [&] { require(released, "borrowed submit before release"); submitted = true; },
        [&] { require(submitted, "borrowed lifetime did not advance deletion serial"); borrowed.drained = true; return false; },
        [] {}, [] {});
    require(!wrapper && borrowed.wrappers == 1 && borrowed.closes == 0 && !borrowed.closed_early,
            "borrowed wrapper must drain without closing caller Display");
    ++borrowed.closes; // The caller may close immediately after the boundary.
    require(borrowed.drained && borrowed.closes == 1, "borrowed caller boundary returned before WSI deletion");

    // Pinned Dawn Device::Destroy eagerly destroys every tracked SwapChain,
    // including active/recycled chains whose Surface wrappers remain held by
    // Canvas and callback-owned Tickets. Model that exact teardown guarantee:
    // later wrapper destruction must not enqueue WSI after Display release.
    FakeDeviceTeardownState device;
    RetirementProbe probe;
    auto owner = std::make_shared<FakeSurfaceOwner>(probe);
    auto canvas_surface = std::make_shared<FakeTrackedSwapChain>(device);
    auto recycled_surface = std::make_shared<FakeTrackedSwapChain>(device);
    auto ticket_surface = canvas_surface;
    auto callback_surface = ticket_surface;
    std::vector<std::weak_ptr<FakeTrackedSwapChain>> tracked{canvas_surface, recycled_surface};
    auto destroy_device = [&] {
        for (auto weak : tracked) if (auto chain = weak.lock()) chain->detach();
        require(device.enqueued == 2, "device Destroy missed active/recycled SwapChain");
        probe.drained = true; // Disconnect/all-priority deleter then backend Destroy.
        device.alive = false;
    };
    destroy_device();
    require(canvas_surface.use_count() == 3 && callback_surface && recycled_surface,
            "test did not retain Canvas/Ticket/callback wrappers through Destroy");
    owner.reset();
    require(probe.closes == 1 && !probe.closed_early, "Display closed before synchronous device WSI teardown");
    canvas_surface.reset(); ticket_surface.reset(); callback_surface.reset(); recycled_surface.reset();
    require(device.late_deletions == 0 && device.enqueued == 2,
            "retained wrapper enqueued WSI after native device/Display teardown");

    RetirementProbe local, foreign;
    auto local_owner = std::make_shared<FakeSurfaceOwner>(local);
    auto foreign_owner = std::make_shared<FakeSurfaceOwner>(foreign);
    int polls = 0;
    retire_owned_surface(local_owner, [] {}, [] {},
        [&] { if (++polls == 1) return true; local.drained = true; return false; }, [] {}, [] {});
    require(!local_owner && foreign_owner && foreign.closes == 0,
            "per-Canvas drain released an unrelated Canvas owner");
    foreign.drained = true; foreign_owner.reset();
}

#if defined(_WIN32)
struct SavedEnvironment {
    std::wstring name;
    std::optional<std::wstring> value;
    explicit SavedEnvironment(const wchar_t* variable) : name(variable) {
        DWORD length = GetEnvironmentVariableW(variable, nullptr, 0);
        if (length) {
            std::wstring current(length, L'\0');
            current.resize(GetEnvironmentVariableW(variable, current.data(), length));
            value = current;
        }
    }
    ~SavedEnvironment() { SetEnvironmentVariableW(name.c_str(), value ? value->c_str() : nullptr); }
};
void environment_contract(const std::filesystem::path& directory) {
    SavedEnvironment path(L"VK_LAYER_PATH"), additional(L"VK_ADD_LAYER_PATH"), layers(L"VK_INSTANCE_LAYERS"),
                     enabled(L"VK_LOADER_LAYERS_ENABLE"), driver(L"VK_DRIVER_FILES");
    SetEnvironmentVariableW(L"VK_LAYER_PATH", L"C:\\Caller;D:\\Other");
    SetEnvironmentVariableW(L"VK_INSTANCE_LAYERS", L"VK_LAYER_CALLER");
    SetEnvironmentVariableW(L"VK_LOADER_LAYERS_ENABLE", L"VK_LAYER_OTHER,*debug*");
    SetEnvironmentVariableW(L"VK_DRIVER_FILES", L"caller-icd.json");
    auto changes = enable_submit_layer_environment(directory);
    require(changes.size() == 3 && changes[0].name == "VK_LAYER_PATH", "caller explicit loader override preserved");
    require(changes[0].after.rfind("C:\\Caller;D:\\Other;", 0) == 0, "caller paths retain order/platform delimiter");
    require(changes[1].after == "VK_LAYER_CALLER;VK_LAYER_VISPY_submit_count", "existing layer choices preserved");
    require(changes[2].after == "VK_LAYER_OTHER,*debug*,VK_LAYER_VISPY_submit_count", "layer enable filter uses commas");
    auto again = enable_submit_layer_environment(directory);
    for (size_t i = 0; i < changes.size(); ++i) require(again[i].after == changes[i].after, "layer environment is idempotent");
    wchar_t driver_value[64]{};
    GetEnvironmentVariableW(L"VK_DRIVER_FILES", driver_value, 64);
    require(std::wstring(driver_value) == L"caller-icd.json", "caller ICD selection preserved");
    SetEnvironmentVariableW(L"VK_LAYER_PATH", nullptr);
    SetEnvironmentVariableW(L"VK_ADD_LAYER_PATH", L"C:\\Additional");
    changes = enable_submit_layer_environment(directory);
    require(changes[0].name == "VK_ADD_LAYER_PATH" && changes[0].after.rfind("C:\\Additional;", 0) == 0,
            "default system layer discovery remains enabled");
    require(GetEnvironmentVariableW(L"VK_LAYER_PATH", driver_value, 64) == 0, "no replacement loader path invented");
}
void surface_contract() {
    NativeSurfaceDescriptor invalid;
    rejected([&] { make_native_surface_owner(invalid); }, "zero HWND accepted");
    HWND window = CreateWindowExW(0, L"STATIC", L"Vispy CPU native contract", WS_POPUP,
                                 0, 0, 64, 64, nullptr, nullptr, GetModuleHandleW(nullptr), nullptr);
    require(window != nullptr, "hidden contract HWND creation");
    NativeSurfaceDescriptor descriptor;
    descriptor.window = reinterpret_cast<uintptr_t>(window);
    auto owner = make_native_surface_owner(descriptor);
    require(owner->is_alive() && owner->descriptor().hinstance, "live GUI-thread HWND/default module");
    owner->update(64, 64, 1.25);
    rejected([&] { owner->update(-1, 64, 1); }, "negative dimensions accepted");
    rejected([&] { owner->create_surface(wgpu::Instance{}); }, "null Dawn instance accepted");
    std::atomic<bool> wrong_thread_rejected{false};
    std::thread other([&] {
        try { owner->update(64, 64, 1); } catch (const std::runtime_error&) { wrong_thread_rejected = true; }
    });
    other.join();
    require(wrong_thread_rejected, "foreign GUI-thread update accepted");
    DestroyWindow(window);
    require(!owner->is_alive(), "destroyed HWND considered live");
    rejected([&] { owner->update(64, 64, 1); }, "destroyed HWND update accepted");
    owner->detach();
}
#endif
}  // namespace
int main(int argc, char** argv) {
    try {
        retirement_contract();
        teardown_and_borrowed_contract();
        auto directory = module_directory(reinterpret_cast<const void*>(&default_backend));
        require(directory.is_absolute() && std::filesystem::is_directory(directory), "absolute module discovery");
        rejected([&] { module_directory(nullptr); }, "null discovery address accepted");
        rejected([&] { NativeLibrary library("relative-library.dll"); }, "relative library accepted");
        rejected([&] { NativeLibrary library(directory / "missing-vispy-contract-library"); }, "missing library accepted");
#if defined(_WIN32)
        require(default_backend() == wgpu::BackendType::Vulkan && std::string(default_backend_name()) == "Vulkan", "Windows backend");
        require(!default_runtime_search_paths().empty(), "Windows system runtime search path");
        environment_contract(directory);
        surface_contract();
#endif
        if (argc > 1) {
            auto fixture = std::filesystem::absolute(argv[1]);
            NativeLibrary library(fixture);
            auto value = reinterpret_cast<uint64_t (*)()>(library.symbol("vispy_native_contract_value"));
            require(value() == 42, "absolute native library symbol dispatch");
            rejected([&] { library.symbol("missing_vispy_contract_symbol"); }, "missing required symbol accepted");
            NativeLibrary moved(std::move(library));
            require(moved && !library, "library ownership move");
#if defined(_WIN32)
            auto unicode = directory / L"native-contract-\u5b50\u7f16\u7801.dll";
            std::filesystem::copy_file(fixture, unicode, std::filesystem::copy_options::overwrite_existing);
            { NativeLibrary unicode_library(unicode); require(reinterpret_cast<uint64_t (*)()>(unicode_library.symbol("vispy_native_contract_value"))() == 42, "Unicode absolute loader path"); }
            std::filesystem::remove(unicode);  // One known test-created file.
#endif
        }
        std::cout << "native module paths, loader environment, symbols, and surface lifetime CPU contracts passed\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
