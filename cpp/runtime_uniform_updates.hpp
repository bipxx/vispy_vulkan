// SPDX-License-Identifier: AGPL-3.0-only
#pragma once

#include <algorithm>
#include <string>
#include <unordered_map>
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
    const auto superseded = [&](const auto& item) { return item.first.starts_with(descendant); };
    std::erase_if(destination, superseded);
    std::erase_if(other_type, superseded);
    other_type.erase(name);
}

} // namespace vispy::uniforms
