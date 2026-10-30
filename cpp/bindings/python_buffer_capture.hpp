#pragma once
// SPDX-License-Identifier: AGPL-3.0-only
#include <Python.h>
#include <cstdint>
#include <cstring>
#include <new>
#include <utility>
#include <vector>
#include "runtime_byte_recycler.hpp"

namespace vispy_binding::detail {
// Called while Python's GIL is held. The exporter is pinned only for this
// synchronous native copy. No Py_buffer or Python address escapes the call.
inline bool capture_buffer(PyObject* object,std::vector<uint8_t>& destination) {
    Py_buffer view{};
    if(PyObject_GetBuffer(object,&view,PyBUF_CONTIG_RO)!=0)return false;
    struct Release {Py_buffer* view;~Release(){PyBuffer_Release(view);}} release{&view};
    try {
        std::vector<uint8_t> snapshot;
        if(view.len) {
            const auto* begin=static_cast<const uint8_t*>(view.buf);
            const auto size=static_cast<size_t>(view.len);
            // Copy into a recycled block's committed pages when one fits (runtime_byte_recycler.hpp).
            snapshot=vispy::memory::ByteRecycler::shared().take(size);
            if(snapshot.size()==size)std::memcpy(snapshot.data(),begin,size);
            else snapshot.assign(begin,begin+view.len);
        }
        destination=std::move(snapshot);
        return true;
    } catch(const std::bad_alloc&) {PyErr_NoMemory();return false;}
}
}
