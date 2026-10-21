#include <cstdint>
#if defined(_WIN32)
#define VISPY_TEST_EXPORT __declspec(dllexport)
#else
#define VISPY_TEST_EXPORT __attribute__((visibility("default")))
#endif
extern "C" VISPY_TEST_EXPORT uint64_t vispy_native_contract_value() { return 42; }
