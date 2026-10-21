#include "native_library.hpp"

#include <algorithm>
#include <cstdlib>
#include <mutex>
#include <stdexcept>
#include <utility>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace vispy::platform {
namespace {
std::string utf8_path(const std::filesystem::path& path) {
    const auto value = path.u8string();
    return std::string(value.begin(), value.end());
}
#if defined(_WIN32)
std::string utf8(const std::wstring& value) {
    if (value.empty()) return {};
    int count = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    if (!count) throw std::runtime_error("Windows loader: invalid Unicode environment value");
    std::string output(static_cast<size_t>(count), '\0');
    WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), output.data(), count, nullptr, nullptr);
    return output;
}
std::wstring wide(const std::string& value) {
    if (value.empty()) return {};
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
    if (!count) throw std::runtime_error("Windows loader: invalid UTF-8 environment value");
    std::wstring output(static_cast<size_t>(count), L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), output.data(), count);
    return output;
}
#endif
std::string environment(const char* name) {
#if defined(_WIN32)
    const auto variable = wide(name);
    DWORD size = GetEnvironmentVariableW(variable.c_str(), nullptr, 0);
    if (!size) return {};
    std::wstring value(size, L'\0');
    DWORD written = GetEnvironmentVariableW(variable.c_str(), value.data(), size);
    if (!written || written >= size) throw std::runtime_error(std::string("Windows loader: environment changed while reading ") + name);
    value.resize(written);
    return utf8(value);
#else
    const char* value = std::getenv(name);
    return value ? value : "";
#endif
}
void set_environment(const char* name, const std::string& value) {
#if defined(_WIN32)
    if (!SetEnvironmentVariableW(wide(name).c_str(), wide(value).c_str()))
        throw std::runtime_error(std::string("Windows loader: cannot update environment ") + name);
#else
    if (setenv(name, value.c_str(), 1) != 0)
        throw std::runtime_error(std::string("native loader: cannot update environment ") + name);
#endif
}
std::string append_unique(const std::string& previous, const std::string& value, char delimiter) {
    size_t start = 0;
    while (start <= previous.size()) {
        auto end = previous.find(delimiter, start);
        if (previous.substr(start, end == std::string::npos ? end : end - start) == value) return previous;
        if (end == std::string::npos) break;
        start = end + 1;
    }
    return previous.empty() ? value : previous + delimiter + value;
}
}  // namespace

wgpu::BackendType default_backend() {
#if defined(__APPLE__)
    return wgpu::BackendType::Metal;
#else
    return wgpu::BackendType::Vulkan;
#endif
}
const char* default_backend_name() {
#if defined(__APPLE__)
    return "Metal";
#else
    return "Vulkan";
#endif
}
const char* submit_layer_library_name() {
#if defined(_WIN32)
    return "VkLayer_vispy_submit.dll";
#elif defined(__APPLE__)
    return "";  // Metal does not load or enable a Vulkan layer.
#else
    return "VkLayer_vispy_submit.so";
#endif
}

std::filesystem::path module_directory(const void* address) {
    if (!address) throw std::runtime_error("native loader: module discovery address is null");
#if defined(_WIN32)
    HMODULE module = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCWSTR>(address), &module))
        throw std::runtime_error("Windows loader: cannot locate the installed native module");
    std::wstring buffer(512, L'\0');
    for (;;) {
        DWORD size = GetModuleFileNameW(module, buffer.data(), static_cast<DWORD>(buffer.size()));
        if (!size) throw std::runtime_error("Windows loader: cannot read the native module filename");
        if (size < buffer.size()) {
            buffer.resize(size);
            return std::filesystem::path(buffer).parent_path();
        }
        if (buffer.size() >= 32768) throw std::runtime_error("Windows loader: native module filename is too long");
        buffer.resize(std::min<size_t>(buffer.size() * 2, 32768));
    }
#else
    Dl_info info{};
    if (!dladdr(address, &info) || !info.dli_fname || !*info.dli_fname)
        throw std::runtime_error("native loader: dladdr cannot locate the installed native module");
    return std::filesystem::weakly_canonical(std::filesystem::absolute(info.dli_fname)).parent_path();
#endif
}

std::vector<std::string> default_runtime_search_paths() {
#if defined(_WIN32)
    std::wstring directory(512, L'\0');
    UINT written = GetSystemDirectoryW(directory.data(), static_cast<UINT>(directory.size()));
    if (!written) throw std::runtime_error("Windows loader: system Vulkan loader directory is unavailable");
    if (written >= directory.size()) {
        directory.resize(static_cast<size_t>(written) + 1);
        written = GetSystemDirectoryW(directory.data(), static_cast<UINT>(directory.size()));
        if (!written || written >= directory.size()) throw std::runtime_error("Windows loader: cannot read system directory");
    }
    directory.resize(written);
    return {utf8(directory) + "\\"};
#else
    // Dawn's native backend uses system Metal or dlopen(libvulkan.so.1).
    // An empty override preserves caller LD_LIBRARY_PATH and loader/ICD setup.
    return {};
#endif
}

NativeLibrary::NativeLibrary(const std::filesystem::path& filename) : filename_(filename) {
    if (!filename.is_absolute() || !std::filesystem::is_regular_file(filename))
        throw std::runtime_error("native loader: expected an existing absolute library filename: " + utf8_path(filename));
#if defined(_WIN32)
    handle_ = reinterpret_cast<void*>(LoadLibraryExW(filename.c_str(), nullptr,
                                                   LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS));
    if (!handle_) throw std::runtime_error("Windows loader: LoadLibraryExW failed (error " +
                                          std::to_string(GetLastError()) + "): " + utf8_path(filename));
#else
    handle_ = dlopen(filename.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!handle_) {
        const char* error = dlerror();
        throw std::runtime_error("native loader: dlopen failed: " + std::string(error ? error : "unknown error") + ": " + utf8_path(filename));
    }
#endif
}
NativeLibrary::~NativeLibrary() { reset(); }
NativeLibrary::NativeLibrary(NativeLibrary&& other) noexcept
    : handle_(std::exchange(other.handle_, nullptr)), filename_(std::move(other.filename_)) {}
NativeLibrary& NativeLibrary::operator=(NativeLibrary&& other) noexcept {
    if (this != &other) {
        reset();
        handle_ = std::exchange(other.handle_, nullptr);
        filename_ = std::move(other.filename_);
    }
    return *this;
}
void NativeLibrary::reset() noexcept {
    if (!handle_) return;
#if defined(_WIN32)
    FreeLibrary(reinterpret_cast<HMODULE>(handle_));
#else
    dlclose(handle_);
#endif
    handle_ = nullptr;
}
void* NativeLibrary::symbol(const char* name) const {
    if (!handle_ || !name || !*name) throw std::runtime_error("native loader: symbol lookup needs a loaded library and name");
#if defined(_WIN32)
    void* value = reinterpret_cast<void*>(GetProcAddress(reinterpret_cast<HMODULE>(handle_), name));
#else
    dlerror();
    void* value = dlsym(handle_, name);
#endif
    if (!value) throw std::runtime_error(std::string("native loader: required symbol is absent: ") + name);
    return value;
}

std::vector<EnvironmentChange> enable_submit_layer_environment(const std::filesystem::path& directory) {
#if defined(__APPLE__)
    return {};
#else
    if (!directory.is_absolute() || !std::filesystem::is_directory(directory))
        throw std::runtime_error("submit layer: installed module directory is missing or not absolute");
    static std::mutex environment_mutex;
    std::lock_guard lock(environment_mutex);
#if defined(_WIN32)
    constexpr char list_delimiter = ';';
#else
    constexpr char list_delimiter = ':';
#endif
    std::vector<EnvironmentChange> changes;
    auto append = [&](const char* name, const std::string& value, char delimiter) {
        auto before = environment(name);
        auto after = append_unique(before, value, delimiter);
        if (after != before) set_environment(name, after);
        changes.push_back({name, std::move(before), std::move(after)});
    };
    // Preserve the loader's default system layer search when the caller has
    // not requested an explicit override. VK_LAYER_PATH suppresses defaults.
    append(environment("VK_LAYER_PATH").empty() ? "VK_ADD_LAYER_PATH" : "VK_LAYER_PATH",
           utf8_path(directory), list_delimiter);
    append("VK_INSTANCE_LAYERS", "VK_LAYER_VISPY_submit_count", list_delimiter);
    append("VK_LOADER_LAYERS_ENABLE", "VK_LAYER_VISPY_submit_count", ',');
    return changes;
#endif
}

}  // namespace vispy::platform
