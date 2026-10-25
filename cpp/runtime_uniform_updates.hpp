// SPDX-License-Identifier: AGPL-3.0-only
#pragma once

#include <map>
#include <string>
#include <utility>

namespace vispy::uniforms {

// The draw packer applies parent values followed by indexed overrides. A new
// parent write therefore retires older descendants; later indexed writes remain.
// Keep unrelated uniforms and sibling elements, including names sharing a prefix.
template<class Map, class OtherMap, class Values>
void replace(Map& destination, OtherMap& other_type, const std::string& name, Values values) {
    const std::string descendant = name + '[';
    // Allocate the replacement first. Allocation failure must not erase prior
    // values before the replacement can be stored.
    destination.insert_or_assign(name, std::move(values));
    const auto retire = [&](auto& values) {
        auto item = values.lower_bound(descendant);
        while (item != values.end() && item->first.starts_with(descendant))
            item = values.erase(item);
    };
    retire(destination);
    retire(other_type);
    other_type.erase(name);
}

} // namespace vispy::uniforms
