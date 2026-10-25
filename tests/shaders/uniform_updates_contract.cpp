// SPDX-License-Identifier: AGPL-3.0-only
#include "runtime_uniform_updates.hpp"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

int main() {
    std::unordered_map<std::string, std::vector<float>> floating;
    std::unordered_map<std::string, std::vector<int32_t>> integer;
    floating["values[0]"] = {1};
    floating["values_extra[0]"] = {2};
    floating["values2[0]"] = {3};
    integer["values[1]"] = {4};
    integer["values"] = {5};
    vispy::uniforms::replace(floating, integer, "values", std::vector<float>{6, 7});
    require(floating.at("values") == std::vector<float>({6, 7}), "whole replacement missing");
    require(!floating.contains("values[0]") && !integer.contains("values[1]"), "stale indexed overrides survive whole write");
    require(!integer.contains("values"), "stale other-type value survives replacement");
    require(floating.at("values_extra[0]")[0] == 2 && floating.at("values2[0]")[0] == 3,
            "unrelated prefix was erased");
    vispy::uniforms::replace(floating, integer, "values[0]", std::vector<float>{8});
    require(floating.at("values[0]")[0] == 8 && floating.at("values")[1] == 7,
            "later element write loses its parent or replacement");
    floating["grid[0][1]"] = {9};
    integer["grid[1][2]"] = {10};
    vispy::uniforms::replace(floating, integer, "grid[1]", std::vector<float>{11, 12, 13});
    require(floating.at("grid[0][1]")[0] == 9 && !integer.contains("grid[1][2]"),
            "indexed parent must retire its descendants and preserve siblings");
    vispy::uniforms::replace(integer, floating, "grid[1][2]", std::vector<int32_t>{14});
    require(integer.at("grid[1][2]")[0] == 14 && floating.contains("grid[1]"),
            "later nested element must preserve its parent");
    std::cout << "Uniform parent/element update ordering and typed replacement pass\n";
}
