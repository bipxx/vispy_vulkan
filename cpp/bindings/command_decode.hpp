#pragma once
// SPDX-License-Identifier: AGPL-3.0-only
// Native binding implementation for this fork. Original VisPy BSD notices
// remain in LICENSE-BSD and third_party/licenses/vispy-LICENSE.txt.
#include "runtime.hpp"
#include "owned_payload.hpp"
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
namespace vispy_binding {
namespace nb = nanobind;
inline Value from_py(nb::handle obj, const nb::list& arrays, uint64_t& decoded_bytes, bool owned_protocol) {
    Value value;
    if (obj.is_none()) return value;
    if (nb::isinstance<nb::bool_>(obj) && !nb::isinstance<nb::int_>(obj)) {
        value.kind = Value::Kind::Bool;
        value.b = nb::cast<bool>(obj);
        value.i = value.b ? 1 : 0;
        return value;
    }
    if (nb::isinstance<nb::int_>(obj)) {
        value.kind = Value::Kind::Int;
        value.i = nb::cast<int64_t>(obj);
        value.f = static_cast<double>(value.i);
        return value;
    }
    if (nb::isinstance<nb::float_>(obj)) {
        value.kind = Value::Kind::Float;
        value.f = nb::cast<double>(obj);
        value.i = static_cast<int64_t>(value.f);
        return value;
    }
    if (nb::isinstance<nb::str>(obj)) {
        value.kind = Value::Kind::Str;
        value.s = nb::cast<std::string>(obj);
        return value;
    }
    if (nb::isinstance<nb::dict>(obj)) {
        nb::dict dict = nb::cast<nb::dict>(obj);
        if (dict.contains("__bytes__")) {
            nb::bytes raw = nb::cast<nb::bytes>(dict["__bytes__"]);
            value.kind = Value::Kind::Blob;
            value.blob.bytes.assign(raw.c_str(), raw.c_str() + raw.size());
            decoded_bytes += raw.size();
            std::string dtype = nb::cast<std::string>(dict["dtype"]);
            if (dtype.find("f4") != std::string::npos) value.blob.dtype = "f32";
            else if (dtype.find("f2") != std::string::npos) value.blob.dtype = "f16";
            else if (dtype.find("f8") != std::string::npos) value.blob.dtype = "f64";
            else if (dtype.find("i4") != std::string::npos) value.blob.dtype = "i32";
            else if (dtype.find("u1") != std::string::npos) value.blob.dtype = "u8";
            else if (dtype.find("u2") != std::string::npos) value.blob.dtype = "u16";
            else if (dtype.find("i2") != std::string::npos) value.blob.dtype = "i16";
            else if (dtype.find("u4") != std::string::npos) value.blob.dtype = "u32";
            else if (dtype.find("i1") != std::string::npos) value.blob.dtype = "i8";
            else if (dtype.find("b1") != std::string::npos) value.blob.dtype = "bool";
            else value.blob.dtype = "bytes";
            for (nb::handle dim : nb::cast<nb::list>(dict["shape"])) {
                value.blob.shape.push_back(static_cast<int>(nb::cast<int64_t>(dim)));
            }
            return value;
        }
        if (owned_protocol && dict.contains("__owned_blob__")) {
            value.kind = Value::Kind::Blob;
            // Decode all metadata before irrevocably moving the payload.
            std::string dtype = nb::cast<std::string>(dict["dtype"]);
            if (dtype.find("f4") != std::string::npos) value.blob.dtype = "f32";
            else if (dtype.find("f2") != std::string::npos) value.blob.dtype = "f16";
            else if (dtype.find("f8") != std::string::npos) value.blob.dtype = "f64";
            else if (dtype.find("i4") != std::string::npos) value.blob.dtype = "i32";
            else if (dtype.find("u1") != std::string::npos) value.blob.dtype = "u8";
            else if (dtype.find("u2") != std::string::npos) value.blob.dtype = "u16";
            else if (dtype.find("i2") != std::string::npos) value.blob.dtype = "i16";
            else if (dtype.find("u4") != std::string::npos) value.blob.dtype = "u32";
            else if (dtype.find("i1") != std::string::npos) value.blob.dtype = "i8";
            else if (dtype.find("b1") != std::string::npos) value.blob.dtype = "bool";
            else value.blob.dtype = "bytes";
            for (nb::handle dim : nb::cast<nb::list>(dict["shape"])) {
                value.blob.shape.push_back(static_cast<int>(nb::cast<int64_t>(dim)));
            }
            auto& snapshot = owned_snapshot(dict["__owned_blob__"]);
            decoded_bytes += snapshot.bytes.size() + (snapshot.host ? snapshot.host->size() : 0);
            value.blob.bytes = std::move(snapshot.bytes);
            value.blob.host = std::move(snapshot.host);
            snapshot.consumed = true;
            return value;
        }
    }
    if (nb::isinstance<nb::list>(obj) || nb::isinstance<nb::tuple>(obj)) {
        value.kind = Value::Kind::List;
        for (nb::handle item : obj) value.list.push_back(from_py(item, arrays, decoded_bytes, owned_protocol));
        return value;
    }
    return value;
}

inline std::vector<Command> decode(nb::list commands, nb::list arrays, uint64_t& decoded_bytes, bool owned_protocol = false) {
    OwnedBatch batch(commands, owned_protocol);
    if (owned_protocol) {
        // The private protocol deliberately excludes user-defined sequences;
        // the legacy entry point retains its original sequence acceptance.
        for (nb::handle item : commands) {
            if (!nb::isinstance<nb::list>(item) && !nb::isinstance<nb::tuple>(item))
                throw nb::type_error("owned command must be a list or tuple");
        }
        batch.collect(commands);
        batch.validate();
    }
    std::vector<Command> out;
    for (nb::handle item : commands) {
        Command cmd;
        nb::sequence seq = nb::cast<nb::sequence>(item);
        cmd.op = nb::cast<std::string>(seq[0]);
        size_t n = nb::len(seq);
        for (size_t i = 1; i < n; ++i) cmd.args.push_back(from_py(seq[i], arrays, decoded_bytes, owned_protocol));
        out.push_back(std::move(cmd));
    }
    return out;
}


} // namespace vispy_binding
