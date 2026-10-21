#pragma once

#include <dawn/webgpu_cpp.h>

#include <filesystem>
#include <string>
#include <vector>

namespace vispy::platform {

wgpu::BackendType default_backend();
const char* default_backend_name();
std::filesystem::path module_directory(const void* address);
std::vector<std::string> default_runtime_search_paths();
const char* submit_layer_library_name();

// No bare DLL/.so search: installed-module-relative, absolute filenames only.
// Keep this owner alive until all Vulkan instances/devices using it retire.
class NativeLibrary {
  public:
    NativeLibrary() = default;
    explicit NativeLibrary(const std::filesystem::path& filename);
    ~NativeLibrary();
    NativeLibrary(const NativeLibrary&) = delete;
    NativeLibrary& operator=(const NativeLibrary&) = delete;
    NativeLibrary(NativeLibrary&& other) noexcept;
    NativeLibrary& operator=(NativeLibrary&& other) noexcept;
    void* symbol(const char* name) const;
    explicit operator bool() const { return handle_ != nullptr; }
    const std::filesystem::path& filename() const { return filename_; }

  private:
    void reset() noexcept;
    void* handle_ = nullptr;
    std::filesystem::path filename_;
};

struct EnvironmentChange {
    std::string name;
    std::string before;
    std::string after;
};
// Append the module directory and required layer to existing caller choices.
// Do not touch ICD selection, driver paths, or disabled-layer settings.
std::vector<EnvironmentChange> enable_submit_layer_environment(const std::filesystem::path& directory);

}  // namespace vispy::platform
