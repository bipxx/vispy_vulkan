// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "shader/glslang_spv.hpp"
#include <SPIRV/spirv.hpp11>
#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>

inline void vertex_input_span_contract() {
    struct Case { const char* declaration; const char* expression; uint32_t width; };
    const Case cases[] = {
        {"float a", "vec4(a)", 1},
        {"ivec3 a", "vec4(a,1)", 1},
        {"mat2x3 a", "vec4(a[0]+a[1],1)", 2},
        {"mat4 a", "a[0]+a[1]+a[2]+a[3]", 4},
        {"vec3 a[2]", "vec4(a[0]+a[1],1)", 2},
        {"vec3 a[2][3]", "vec4(a[0][0]+a[1][2],1)", 6},
        {"mat2x3 a[2]", "vec4(a[0][0]+a[1][1],1)", 4},
        {"dvec3 a", "vec4(a,1)", 2},
        {"dmat2x3 a", "vec4(a[0]+a[1],1)", 4},
    };
    const std::string fragment = "#version 450\nlayout(location=0) in vec4 color;"
        "layout(location=0) out vec4 pixel;void main(){pixel=color;}";
    for (const auto& c : cases) for (bool global : {false, true}) {
        std::string source = "#version 450\nlayout(location=2) in " + std::string(c.declaration) +
            ";layout(location=19) in vec2 p;layout(location=31) in vec4 unused;"
            "layout(location=0) out vec4 color;";
        if (global) source += "vec4 seed=" + std::string(c.expression) + ";";
        source += "void main(){gl_Position=vec4(p,0,1);color=" +
            (global ? std::string("seed") : std::string(c.expression)) + ";}";
        const auto compiled = compile_vulkan_glsl(source, fragment, true);
        auto check = [&](bool good, const std::string& message) {
            if (!good) throw std::runtime_error(std::string(c.declaration) + ": " + message);
        };
        check(compiled.ok, compiled.log);
        std::vector<uint32_t> expected;
        for (uint32_t n=0; n<c.width; ++n) expected.push_back(2+n);
        expected.push_back(19);
        check(compiled.vertex_input_locations == expected, "occupied locations/dead input reflection differs");
        // Location decorations on vertex inputs must keep the aggregate at 0
        // and place p after its entire span. Output color also occupies 0.
        std::vector<uint32_t> decorated;
        for (size_t n=5; n<compiled.vertex.words.size(); n+=compiled.vertex.words[n]>>16) {
            const auto* words=compiled.vertex.words.data()+n;
            if (static_cast<spv::Op>(words[0]&0xffffu)==spv::Op::OpDecorate &&
                (words[0]>>16)==4 && words[2]==static_cast<uint32_t>(spv::Decoration::Location))
                decorated.push_back(words[3]);
        }
        check(std::find(decorated.begin(),decorated.end(),c.width)!=decorated.end(),
            "following input was not relocated after aggregate span");
    }
}
