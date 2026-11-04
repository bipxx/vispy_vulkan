#pragma once
// SPDX-License-Identifier: AGPL-3.0-only
// Python ownership stays in this binding layer, outside runtime headers.
#include "python_buffer_capture.hpp"
#include <nanobind/nanobind.h>
#include <memory>
#include <unordered_set>
#include <utility>
#include <vector>

namespace vispy_binding {
namespace nb = nanobind;
inline constexpr const char* snapshot_name = "vispy.owned_upload.v1";

struct OwnedSnapshot {
    std::vector<uint8_t> bytes;
    vispy::memory::HostBytes host;  // a payload of at least 1 MiB (plan P5); bytes is then empty
    bool consumed = false;
};

inline OwnedSnapshot* snapshot_if_valid(nb::handle obj) noexcept {
    if (!PyCapsule_IsValid(obj.ptr(), snapshot_name)) return nullptr;
    return static_cast<OwnedSnapshot*>(PyCapsule_GetPointer(obj.ptr(), snapshot_name));
}

inline OwnedSnapshot& owned_snapshot(nb::handle obj) {
    auto* snapshot = snapshot_if_valid(obj);
    if (!snapshot) throw nb::value_error("invalid owned upload snapshot");
    if (snapshot->consumed) throw nb::value_error("owned upload snapshot was consumed or discarded");
    return *snapshot;
}

inline nb::capsule capture_upload(nb::handle obj) {
    // Nanobind translates C++ exceptions. The buffer helper releases its
    // Py_buffer on both successful copy and allocation failure.
    auto snapshot = std::make_unique<OwnedSnapshot>();
    if (!vispy_binding::detail::capture_buffer(obj.ptr(), snapshot->bytes, snapshot->host))
        throw nb::python_error();
    nb::capsule result(snapshot.get(), snapshot_name, [](void* ptr) noexcept {
        delete static_cast<OwnedSnapshot*>(ptr);
    });
    snapshot.release();
    return result;
}

class OwnedBatch {
    nb::list root_;
    bool enabled_;
    std::vector<nb::object> snapshots_;

    static void discard_snapshot(PyObject* obj) noexcept {
        if (auto* snapshot = snapshot_if_valid(nb::handle(obj))) {
            snapshot->consumed = true;
            std::vector<uint8_t>().swap(snapshot->bytes);
            snapshot->host.reset();
        }
    }

    static void discard_tree(PyObject* obj) noexcept {
        // No Python iteration, key allocation, or container allocation here.
        // GLIR's internal wire format is an acyclic list/tuple tree with dict
        // payload leaves. Keep this root so even collection bad_alloc discards
        // payloads which snapshots_ has not reached or pinned yet.
        if (PyList_Check(obj)) {
            for (Py_ssize_t i = 0; i < PyList_GET_SIZE(obj); ++i)
                discard_tree(PyList_GET_ITEM(obj, i));
        } else if (PyTuple_Check(obj)) {
            for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(obj); ++i)
                discard_tree(PyTuple_GET_ITEM(obj, i));
        } else if (PyDict_Check(obj)) {
            PyObject *key = nullptr, *value = nullptr, *owned = nullptr;
            Py_ssize_t position = 0;
            bool has_bytes = false;
            while (PyDict_Next(obj, &position, &key, &value)) {
                if (!PyUnicode_Check(key)) continue;
                if (PyUnicode_CompareWithASCIIString(key, "__bytes__") == 0) has_bytes = true;
                if (PyUnicode_CompareWithASCIIString(key, "__owned_blob__") == 0) owned = value;
            }
            if (!has_bytes && owned) discard_snapshot(owned);
        }
    }
public:
    explicit OwnedBatch(const nb::list& root, bool enabled) : root_(root), enabled_(enabled) {}
    OwnedBatch(const OwnedBatch&) = delete;
    OwnedBatch& operator=(const OwnedBatch&) = delete;

    void collect(nb::handle obj) {
        if (nb::isinstance<nb::dict>(obj)) {
            auto dict = nb::borrow<nb::dict>(obj);
            // Match from_py: a bytes dictionary takes precedence, and other
            // dictionaries are opaque. Ignore capsules not decoded by it.
            if (!dict.contains("__bytes__") && dict.contains("__owned_blob__"))
                snapshots_.push_back(nb::borrow<nb::object>(dict["__owned_blob__"]));
        } else if (nb::isinstance<nb::list>(obj) || nb::isinstance<nb::tuple>(obj)) {
            for (nb::handle item : obj) collect(item);
        }
    }

    void validate() const {
        std::unordered_set<const OwnedSnapshot*> seen;
        for (const auto& capsule : snapshots_) {
            auto& snapshot = owned_snapshot(capsule);
            if (!seen.insert(&snapshot).second)
                throw nb::value_error("owned upload snapshot appears more than once in batch");
        }
    }

    ~OwnedBatch() noexcept {
        if (!enabled_) return;
        PyObject *type = nullptr, *value = nullptr, *traceback = nullptr;
        PyErr_Fetch(&type, &value, &traceback);
        discard_tree(root_.ptr());
        // Also discard pinned originals removed by any reentrant conversion.
        for (const auto& capsule : snapshots_) discard_snapshot(capsule.ptr());
        PyErr_Restore(type, value, traceback);
    }

};
} // namespace vispy_binding
