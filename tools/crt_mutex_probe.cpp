// CPU-only MSVC STL/redistributable compatibility witness. No Qt or renderer.
#include <mutex>

extern "C" __declspec(dllexport) int vispy_mutex_probe() {
    std::mutex mutex;
    std::lock_guard<std::mutex> lock(mutex);
    return 73;
}
