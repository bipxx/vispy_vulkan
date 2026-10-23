// SPDX-License-Identifier: AGPL-3.0-only
// Test-only CPU inspection. No Dawn/device initialization or linking.
#include "command_decode.hpp"
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
namespace nb = nanobind;
#include <cstdlib>
#include <new>
// Test-only deterministic allocation failure, scoped to this extension DLL.
thread_local long failure_after = -1;
void* operator new(std::size_t size) {
    if (failure_after == 0) { failure_after = -1; throw std::bad_alloc(); }
    if (failure_after > 0) --failure_after;
    if (void* p = std::malloc(size ? size : 1)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }


nb::object inspect_value(const Value& value) {
    if (value.kind == Value::Kind::Blob) {
        nb::dict out;
        out["bytes"] = nb::bytes(reinterpret_cast<const char*>(value.blob.bytes.data()), value.blob.bytes.size());
        out["address"] = reinterpret_cast<uintptr_t>(value.blob.bytes.data());
        out["shape"] = value.blob.shape;
        out["dtype"] = value.blob.dtype;
        return out;
    }
    if (value.kind == Value::Kind::List) {
        nb::list out;
        for (const auto& item : value.list) out.append(inspect_value(item));
        return out;
    }
    return nb::none();
}

NB_MODULE(_owned_upload_contract, m) {
    m.def("capture", &vispy_binding::capture_upload);
    m.def("allocation_failure", [](nb::list commands, long after) {
        struct Reset { ~Reset() { failure_after = -1; } } reset;
        failure_after = after;
        uint64_t bytes = 0;
        auto decoded = vispy_binding::decode(commands, nb::list(), bytes, true);
    });
    m.def("legacy_decode", [](nb::list commands) {
        uint64_t bytes = 0;
        return vispy_binding::decode(commands, nb::list(), bytes).size();
    });
    m.def("address", [](nb::handle obj) {
        return reinterpret_cast<uintptr_t>(vispy_binding::owned_snapshot(obj).bytes.data());
    });
    m.def("decode", [](nb::list commands) {
        uint64_t bytes = 0;
        auto decoded = vispy_binding::decode(commands, nb::list(), bytes, true);
        nb::list values;
        for (const auto& cmd : decoded) {
            nb::list args;
            for (const auto& value : cmd.args) args.append(inspect_value(value));
            values.append(args);
        }
        return nb::make_tuple(values, bytes);
    });
}
