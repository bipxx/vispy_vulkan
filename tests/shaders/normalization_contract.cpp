// CPU compiler/layout contract; run independently of Dawn device creation.
#include "shader/normalize.hpp"
#include "shader/glslang_spv.hpp"
#include <glslang/Public/ResourceLimits.h>
#include <glslang/Public/ShaderLang.h>
#include <SPIRV/spirv.hpp11>

#ifdef VISPY_TEST_TINT_READER
#include "src/tint/lang/core/ir/module.h"
#include "src/tint/lang/spirv/reader/reader.h"
#endif

#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_set>

namespace {
const std::string vertex = "attribute vec2 a_position; void main() { gl_Position = vec4(a_position, 0.0, 1.0); }";

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

std::string read(const std::filesystem::path& file) {
    std::ifstream input(file);
    require(input.good(), "missing corpus file " + file.string());
    return std::string(std::istreambuf_iterator<char>(input), {});
}

void compile_and_reflect(NormalizedShader& normalized) {
    require(normalized.error.empty(), normalized.error);
    require(static_cast<size_t>(std::count(normalized.vertex.begin(), normalized.vertex.end(), '\n')) == normalized.vertex_line_map.size(),
            "vertex source map length");
    require(static_cast<size_t>(std::count(normalized.fragment.begin(), normalized.fragment.end(), '\n')) == normalized.fragment_line_map.size(),
            "fragment source map length");
    auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
    require(compiled.ok, compiled.log + "\n" + normalized.fragment);
#ifdef VISPY_TEST_TINT_READER
    // Exercise the same pinned reader as native CreateShaderModule without
    // constructing an instance, device or surface. SPIR-V validation alone
    // does not catch reader transform crashes.
    for (const auto* stage : {&compiled.vertex, &compiled.fragment}) {
        auto ir = tint::spirv::reader::ReadIR(stage->words);
        require(ir == tint::Success, ir == tint::Success ? "" : ir.Failure().reason);
    }
#endif
    std::string error;
    require(reflect_uniform_layout(compiled.vertex.words, normalized.uniforms, normalized.uniform_bytes, error), error);
    require(reflect_uniform_layout(compiled.fragment.words, normalized.uniforms, normalized.uniform_bytes, error), error);
}

float read_float(const std::vector<uint8_t>& buffer, size_t offset) {
    float result;
    std::memcpy(&result, buffer.data() + offset, 4);
    return result;
}

void uniform_layouts() {
    for (int dimension : {2, 3, 4}) {
        const std::string matrix = "mat" + std::to_string(dimension);
        auto normalized = normalize_program(vertex,
            "uniform float u_scalars[3]; uniform vec2 u_vectors[2]; uniform " + matrix +
            " u_matrix; uniform " + matrix + " u_matrices[2]; void main() { gl_FragColor = vec4(u_scalars[2] + u_vectors[1].x + u_matrix[0][0] + u_matrices[1][0][0]); }");
        compile_and_reflect(normalized);
        std::vector<uint8_t> bytes(normalized.uniform_bytes, 0xcc);
        std::string error;
        float scalars[] = {0.1f, 0.2f, 0.3f};
        require(pack_uniform_value(normalized.uniforms[0], scalars, sizeof(scalars), bytes.data(), bytes.size(), &error), error);
        require(read_float(bytes, normalized.uniforms[0].offset + 32) == 0.3f, "scalar array stride");
        require(bytes[normalized.uniforms[0].offset + 4] == 0, "scalar array padding zeroed");
        float vectors[] = {1, 2, 3, 4};
        require(pack_uniform_value(normalized.uniforms[1], vectors, sizeof(vectors), bytes.data(), bytes.size(), &error), error);
        require(read_float(bytes, normalized.uniforms[1].offset + 16) == 3, "vector array stride");
        std::vector<float> values(static_cast<size_t>(dimension * dimension));
        for (size_t i = 0; i < values.size(); ++i) values[i] = static_cast<float>(i + 1);
        require(pack_uniform_value(normalized.uniforms[2], values.data(), values.size() * 4, bytes.data(), bytes.size(), &error), error);
        for (int col = 0; col < dimension; ++col)
            for (int row = 0; row < dimension; ++row)
                require(read_float(bytes, normalized.uniforms[2].offset + col * 16 + row * 4) == values[col * dimension + row], "matrix column stride");
        auto row_major = normalized.uniforms[2];
        row_major.row_major = true;
        require(pack_uniform_value(row_major, values.data(), values.size() * 4, bytes.data(), bytes.size(), &error), error);
        require(read_float(bytes, row_major.offset + 16) == values[1], "row-major destination orientation");
        std::vector<float> arrays(values);
        arrays.insert(arrays.end(), values.begin(), values.end());
        require(pack_uniform_value(normalized.uniforms[3], arrays.data(), arrays.size() * 4, bytes.data(), bytes.size(), &error), error);
        require(read_float(bytes, normalized.uniforms[3].offset + normalized.uniforms[3].array_stride) == 1, "matrix array stride");
        auto before = bytes;
        require(!pack_uniform_value(normalized.uniforms[3], values.data(), values.size() * 4, bytes.data(), bytes.size(), &error), "partial source rejected");
        require(bytes == before, "failed packing is atomic");
    }
    auto vec3_scalar = normalize_program(vertex, "uniform vec3 u_three; uniform float u_scalar; void main(){ gl_FragColor=vec4(u_three,u_scalar); }");
    compile_and_reflect(vec3_scalar);
    require(vec3_scalar.uniforms[1].offset == 12, "std140 scalar may use vec3 tail");
}

void multidimensional_uniforms() {
    for (const std::string type : {"float", "int", "bool", "vec3", "bvec2", "mat2", "mat2x3"}) {
        const std::string expression = type == "bool" ? "float(grid[1][2])" :
            type == "bvec2" ? "float(grid[1][2].x)" :
            type.find("mat") == 0 ? "grid[1][2][0][1]" :
            type == "vec3" ? "grid[1][2].x" : "float(grid[1][2])";
        auto normalized = normalize_program(vertex, "uniform " + type + " grid[2][3];"
            "void main(){gl_FragColor=vec4(" + expression + ");}");
        compile_and_reflect(normalized);
        const auto& uniform = normalized.uniforms.at(0);
        require(uniform.array_dimensions == std::vector<uint32_t>({2, 3}) && uniform.array_size == 6,
            "ordered shape and flattened count survive reflection");
        NormUniform row, leaf;
        std::string error;
        require(uniform_indexed_view(uniform, "grid[1]", row, &error), error);
        require(row.array_dimensions == std::vector<uint32_t>({3}) && row.array_size == 3 &&
            row.offset == uniform.offset + 3 * uniform.array_stride, "row subview layout");
        require(uniform_indexed_view(uniform, "grid[1][2]", leaf, &error), error);
        require(leaf.array_dimensions.empty() && !leaf.array_size && !leaf.array_stride &&
            leaf.offset == uniform.offset + 5 * uniform.array_stride, "leaf subview layout");
        std::vector<uint8_t> bytes(normalized.uniform_bytes, 0xCD);
        std::vector<float> values(6 * uniform.component_count, 0.25f);
        require(pack_uniform_value(uniform, values.data(), values.size() * 4,
            bytes.data(), bytes.size(), &error), error);
        auto before = bytes;
        require(!pack_uniform_value(row, values.data(), values.size() * 4,
            bytes.data(), bytes.size(), &error) && bytes == before, "wrong subarray size is atomic");
        for (const std::string name : {"grid[2]", "grid[1][3]", "grid[-1]", "grid[]", "grid[1]x",
                "grid[1][2][0]", "grid[4294967296]", "other[1]"}) {
            NormUniform rejected; rejected.name = "unchanged";
            require(!uniform_indexed_view(uniform, name, rejected, &error) && rejected.name == "unchanged",
                "invalid index rejected before mutation: " + name);
        }
        auto mismatched = normalized.uniforms;
        mismatched[0].array_dimensions = {3, 2};
        auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
        require(compiled.ok, compiled.log);
        uint32_t block_bytes = normalized.uniform_bytes;
        require(!reflect_uniform_layout(compiled.fragment.words, mismatched, block_bytes, error),
            "reflection rejects equal-product different-shape metadata");
    }
    auto mismatch = normalize_program("uniform float grid[2][3];" + vertex,
        "uniform float grid[3][2];void main(){gl_FragColor=vec4(grid[0][0]);}");
    require(mismatch.error.find("array shapes differ") != std::string::npos, "cross-stage shape mismatch");
    for (const std::string declaration : {"uniform float grid[2147483647][2];",
            "uniform mat4 grid[67108864];", "uniform float grid[0][2];"}) {
        auto overflow = normalize_program(vertex, declaration + "void main(){gl_FragColor=vec4(1);}");
        require(!overflow.error.empty(), "array overflow/invalid dimension rejected");
    }
    auto nested_bool = normalize_program(vertex,
        "uniform bool flags[2][3];void main(){gl_FragColor=vec4(float(flags[int(flags[0][1])][2]));}");
    compile_and_reflect(nested_bool);
    auto cube = normalize_program(vertex,
        "uniform float grid[2][3][4];void main(){gl_FragColor=vec4(grid[1][2][3]);}");
    compile_and_reflect(cube);
    NormUniform leaf;
    require(uniform_indexed_view(cube.uniforms[0], "grid[1][2][3]", leaf) && leaf.offset == 23 * 16,
        "three-dimensional row-major subview offset");
}

void boolean_lowering() {
    auto normalized = normalize_program(vertex,
        "uniform bool u_flag; uniform bool u_flags[2]; uniform bvec3 u_channels;\n"
        "void main() { bool local = u_flag && !u_flags[0];\n"
        "if (local && any(u_channels) && u_flags[int(u_flags[0]) + 1]) gl_FragColor=vec4(1);\n"
        "else gl_FragColor=vec4(0); }");
    compile_and_reflect(normalized);
    require(normalized.uniforms[0].type == "bool", "logical bool type retained");
    require(normalized.uniforms[0].storage_type == "int", "physical bool is integer");
    int32_t source[] = {-3, 0, 42};
    std::vector<uint8_t> bytes(normalized.uniform_bytes, 0);
    std::string error;
    require(pack_uniform_value(normalized.uniforms[2], source, sizeof(source), bytes.data(), bytes.size(), &error), error);
    int32_t output[3] = {};
    std::memcpy(output, bytes.data() + normalized.uniforms[2].offset, sizeof(output));
    require(output[0] == 1 && output[1] == 0 && output[2] == 1, "bool components canonicalized");
}

void boolean_scope_original_baseline(const std::filesystem::path& directory) {
    // Deliberately bypass normalize_program and Vulkan/SPIR-V rules: admit the
    // original paired programs under their declared OpenGL GLSL versions.
    const std::vector<std::string> names = {
        "parameter", "local", "member", "initializer", "comma_initializer", "nested_initializer",
        "uninitialized_local", "for_scope", "for_if_else_scope", "while_condition_scope",
        "parameter_then_nested_local", "struct_typed_local", "local_array", "prototype_scope",
        "array", "array_initializer", "vector", "stages", "mapped", "conditional", "macro", "switch_scope"
    };
    require(glslang::InitializeProcess(), "original bool scope baseline: glslang initialization failed");
    // Each shader/program is destroyed before process finalization, including
    // the exception path. No native provider, instance or device is constructed.
    struct Process { ~Process() { glslang::FinalizeProcess(); } } process;
    for (const auto& name : names) {
        const auto vertex_source = read(directory / (name + ".vert"));
        const auto fragment_source = read(directory / (name + ".frag"));
        const char* vertex_text = vertex_source.c_str();
        const char* fragment_text = fragment_source.c_str();
        glslang::TShader vertex_shader(EShLangVertex), fragment_shader(EShLangFragment);
        vertex_shader.setStrings(&vertex_text, 1);
        fragment_shader.setStrings(&fragment_text, 1);
        const bool vertex_parsed = vertex_shader.parse(GetDefaultResources(), 120, false, EShMsgDefault);
        require(vertex_parsed,
                name + ": original vertex parse failed\n" + vertex_shader.getInfoLog() + vertex_shader.getInfoDebugLog());
        const bool fragment_parsed = fragment_shader.parse(GetDefaultResources(), 120, false, EShMsgDefault);
        require(fragment_parsed,
                name + ": original fragment parse failed\n" + fragment_shader.getInfoLog() + fragment_shader.getInfoDebugLog());
        glslang::TProgram program;
        program.addShader(&vertex_shader);
        program.addShader(&fragment_shader);
        const bool linked = program.link(EShMsgDefault);
        require(linked, name + ": original link failed\n" + program.getInfoLog() + program.getInfoDebugLog());
        std::cout << "original_glsl_link_pass " << name << '\n';
    }
    std::cout << "original bool scope programs passed: " << names.size() << '\n';
}

void boolean_scope_lowering() {
    // GLSL 1.20 section 4.2 places a binding after its initializer. These
    // original programs must also be admitted by the Root's legacy compiler;
    // compiling only the normalized output is not that baseline admission.
    struct Case { const char* name; const char* body; size_t uniform_reads; };
    const Case cases[] = {
        {"parameter", "bool helper(bool u_flag){return u_flag;}\n"
            "void main(){gl_FragColor=(u_flag && !helper(false))?vec4(1.0):vec4(0.0);}", 1},
        {"local", "void main(){bool ok=false;{bool u_flag=false;ok=!u_flag;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 1},
        {"member", "struct S{bool u_flag;};\n"
            "void main(){S s=S(false);gl_FragColor=(u_flag && !s.u_flag)?vec4(1.0):vec4(0.0);}", 1},
        {"initializer", "void main(){bool ok=false;{bool u_flag=!u_flag;ok=u_flag;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 2},
        {"comma_initializer", "void main(){bool result=false;{bool u_flag=!u_flag, other=u_flag;result=other;}\n"
            "gl_FragColor=(u_flag && result)?vec4(1.0):vec4(0.0);}", 2},
        {"nested_initializer", "void main(){bool ok=false;{bool u_flag=false;\n"
            "{bool u_flag=!u_flag;ok=u_flag;}ok=ok && !u_flag;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 1},
        {"uninitialized_local", "void main(){bool ok=false;{bool u_flag;u_flag=false;ok=!u_flag;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 1},
        {"for_scope", "void main(){bool ok=false;for(bool u_flag=!u_flag;u_flag;u_flag=false){ok=u_flag;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 2},
        {"for_if_else_scope", "void main(){bool ok=false;\n"
            "for(bool u_flag=false;u_flag;u_flag=false) if(u_flag) ok=true;else ok=false;\n"
            "gl_FragColor=(u_flag && !ok)?vec4(1.0):vec4(0.0);}", 1},
        {"while_condition_scope", "void main(){bool ok=false;while(bool u_flag=!u_flag){ok=u_flag;break;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 2},
        {"parameter_then_nested_local", "bool helper(in bool u_flag){bool ok=u_flag;\n"
            "{const bool u_flag=false;ok=ok && !u_flag;}return ok && u_flag;}\n"
            "void main(){gl_FragColor=(u_flag && helper(true))?vec4(1.0):vec4(0.0);}", 1},
        {"struct_typed_local", "struct Cell{bool u_flag;};\n"
            "void main(){bool ok=false;{Cell u_flag=Cell(false);ok=!u_flag.u_flag;}\n"
            "gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 1},
        {"local_array", "void main(){bool ok=false;{bool u_flag[2];u_flag[0]=false;u_flag[1]=true;\n"
            "ok=!u_flag[0] && u_flag[1];}gl_FragColor=(u_flag && ok)?vec4(1.0):vec4(0.0);}", 1},
        {"prototype_scope", "bool helper(bool u_flag);\n"
            "bool helper(bool value){return value;}\n"
            "void main(){gl_FragColor=(u_flag && helper(true))?vec4(1.0):vec4(0.0);}", 1},
    };
    const std::string cast = "(vispy_bool_storage_u_flag != 0)";
    for (const auto& test : cases) {
        auto normalized = normalize_program(vertex, std::string("#version 120\nuniform bool u_flag;\n") + test.body);
        compile_and_reflect(normalized);
        size_t uses = 0, position = 0;
        while ((position = normalized.fragment.find(cast, position)) != std::string::npos) { ++uses; position += cast.size(); }
        require(uses == test.uniform_reads, std::string(test.name) + ": only lexically visible uniform reads lower");
        require(normalized.uniforms.size() == 1 && normalized.uniforms[0].name == "u_flag" &&
                normalized.uniforms[0].type == "bool" && normalized.uniforms[0].storage_type == "int" &&
                normalized.uniforms[0].offset == 0 && normalized.uniforms[0].size == 4,
                std::string(test.name) + ": uniform storage ABI held");
    }
    auto array = normalize_program(vertex,
        "#version 120\nuniform bool u_flags[2];\n"
        "bool helper(bool u_flags[2]){return u_flags[1];}\n"
        "void main(){bool values[2];values[0]=false;values[1]=true;\n"
        "gl_FragColor=(u_flags[0] && helper(values))?vec4(1.0):vec4(0.0);}");
    compile_and_reflect(array);
    require(array.fragment.find("bool u_flags [ 2 ]") != std::string::npos, "array parameter declaration retained");
    require(array.fragment.find("return u_flags [ 1 ]") != std::string::npos, "array parameter read retained");
    require(array.fragment.find("(vispy_bool_storage_u_flags [ 0 ]  != 0)") != std::string::npos,
            "global boolean array indexed cast retained");
    auto array_initializer = normalize_program(vertex,
        "#version 120\nuniform bool u_flags[2];\n"
        "void main(){bool ok=false;{bool u_flags[2]=bool[2](u_flags[0],u_flags[1]);ok=u_flags[0];}\n"
        "gl_FragColor=(u_flags[1] && ok)?vec4(1.0):vec4(0.0);}");
    compile_and_reflect(array_initializer);
    size_t array_reads = 0, position = 0;
    while ((position = array_initializer.fragment.find("(vispy_bool_storage_u_flags", position)) != std::string::npos) {
        ++array_reads; ++position;
    }
    require(array_reads == 3, "array constructor initializer reads outer array before local binding");
    auto vector = normalize_program(vertex,
        "#version 120\nuniform bvec3 u_channels;\n"
        "bool helper(bvec3 u_channels){return any(u_channels);}\n"
        "void main(){bool ok=false;{bvec3 u_channels=not(u_channels);ok=helper(u_channels);}\n"
        "gl_FragColor=(any(u_channels) && ok)?vec4(1.0):vec4(0.0);}");
    compile_and_reflect(vector);
    require(vector.fragment.find("bvec3 u_channels = not ( notEqual(vispy_bool_storage_u_channels, ivec3(0)) )") != std::string::npos,
            "bvec initializer lowers outer uniform, retains local declaration");
    require(vector.uniforms[0].type == "bvec3" && vector.uniforms[0].storage_type == "ivec3",
            "vector logical and storage types held");

    // The two stages have separate lexical namespaces even though the storage
    // layout is merged for the program.
    auto stages = normalize_program(
        "uniform bool u_flag;void main(){gl_Position=vec4(u_flag?1.0:0.0);}",
        "bool helper(bool u_flag){return u_flag;}void main(){gl_FragColor=vec4(helper(true)?1.0:0.0);}");
    compile_and_reflect(stages);
    require(stages.fragment.find(cast) == std::string::npos, "other stage uniform cannot rewrite fragment parameter");

    auto switch_scope = normalize_program(
        "#version 330\nin vec2 a_position;void main(){gl_Position=vec4(a_position,0.0,1.0);}",
        "#version 330\nuniform bool u_flag;out vec4 color;\n"
        "void main(){bool ok=false;for(bool u_flag=false;u_flag;u_flag=false)\n"
        "switch (0) { case 0: ok=u_flag; break; default: break; }\n"
        "color=vec4(u_flag && !ok?1.0:0.0);}");
    compile_and_reflect(switch_scope);
    require(switch_scope.fragment.find(cast) != std::string::npos,
            "GLSL330 switch loop body ends before following global uniform read");

    auto mapped = normalize_program(vertex,
        "#version 120\nuniform bool u_flag;\nvoid main(){\n {bool u_flag=false;}\n gl_FragColor=vec4(u_flag?1.0:0.0);\n}\n");
    compile_and_reflect(mapped);
    const size_t use = mapped.fragment.find(cast);
    require(use != std::string::npos, "mapped global read exists");
    const size_t line = std::count(mapped.fragment.begin(), mapped.fragment.begin() + use, '\n');
    require(mapped.fragment_line_map[line] == 5, "rewritten reference retains original line five");

    // Compatibility boundary: this pass does not decide conditional branches or
    // macro expansion. The inactive shadow declaration retains the old spelling
    // rewrite byte-for-byte, while the active reference still compiles.
    auto conditional = normalize_program(vertex,
        "#version 120\nuniform bool u_flag;\n#if 0\n"
        "bool helper(bool u_flag){return u_flag;}\n#endif\n"
        "void main(){gl_FragColor=vec4(u_flag?1.0:0.0);}\n");
    compile_and_reflect(conditional);
    require(conditional.fragment.find("bool helper ( bool " + cast + " ) { return " + cast + " ; }") != std::string::npos,
            "conditional branch retains exact legacy boolean spelling rewrite");
    auto macro = normalize_program(vertex,
        "#version 120\n#define HAS_FLAG 1\nuniform bool u_flag;\n"
        "void main(){gl_FragColor=vec4(u_flag?1.0:0.0);}");
    compile_and_reflect(macro);
    require(macro.fragment.find("#define HAS_FLAG 1") != std::string::npos && macro.fragment.find(cast) != std::string::npos,
            "macro path keeps legacy directive and cast");
    auto whole = normalize_program(vertex,
        "uniform bool u_flags[2];bool helper(bool flags[2]){return flags[0];}"
        "void main(){gl_FragColor=vec4(helper(u_flags)?1.0:0.0);}");
    require(whole.error.find("whole boolean arrays are unsupported") != std::string::npos,
            "whole uniform array refusal retained");
    auto write = normalize_program(vertex,
        "uniform bool u_flag;void main(){u_flag=false;gl_FragColor=vec4(1.0);}");
    require(write.error.empty(), "illegal uniform write reaches strict compiler");
    require(!compile_vulkan_glsl(write.vertex, write.fragment).ok, "uniform write is not legalized by shadow support");
}

void coordinate_entry() {
    auto normalized = normalize_program(
        "attribute vec2 a_position; void set_position() { gl_Position=vec4(a_position,0,1); }\n"
        "void main() { set_position(); gl_Position.y += 0.25; if(a_position.x > 0.0) return; gl_Position.z=0.5; }",
        "void main() { gl_FragColor=vec4(1); }");
    compile_and_reflect(normalized);
    require(normalized.vertex.find("vispy_fix_clip") == std::string::npos, "no per-assignment conversion");
    require(normalized.vertex.find("vispy_user_main();") < normalized.vertex.find("gl_Position.y = -gl_Position.y"), "wrapper converts final user output");
}

void sampler1d_fragment_case(const std::string& body,bool base){
    NormalizeOptions options;options.base_level_sampling=base;
    auto normalized=normalize_program("attribute vec2 a_position; varying float v_uv; void main(){v_uv=(a_position.x+1.)*.5;gl_Position=vec4(a_position,0.,1.);}","uniform sampler1D u_source; varying float v_uv; "+body,options);
    require(normalized.error.empty(),normalized.error);
    require(normalized.samplers.size()==1,"sampler1D must have a resource binding");
    require(normalized.samplers[0].dim=="1d","1D normalized metadata");
    require(normalized.fragment.find("texture1D vispy_")!=std::string::npos || normalized.fragment.find("texture1D ")!=std::string::npos,"separate texture1D declaration");
    auto compiled=compile_vulkan_glsl(normalized.vertex,normalized.fragment);
    require(compiled.ok,compiled.log+"\n"+normalized.fragment);
#ifdef VISPY_TEST_TINT_READER
    for (const auto* stage : {&compiled.vertex, &compiled.fragment}) {
        auto ir = tint::spirv::reader::ReadIR(stage->words);
        require(ir == tint::Success, ir == tint::Success ? "" : ir.Failure().reason);
    }
#endif
    std::string error;
    require(reflect_sampler_types(compiled.fragment.words,normalized.samplers,2,error),error);
    auto wrong=normalized.samplers;wrong[0].dim="2d";
    require(!reflect_sampler_types(compiled.fragment.words,wrong,2,error),"1D SPIR-V must not masquerade as 2D");
    require(error.find("shape differs")!=std::string::npos,"dimension mismatch diagnostic");
}
void one_dimensional_sampling(){
    for(bool base:{false,true}){
        sampler1d_fragment_case("void main(){gl_FragColor=texture1D(u_source,v_uv);}",base);
        sampler1d_fragment_case("vec4 sample_value(sampler1D source,float x){return texture1D(source,x);} void main(){gl_FragColor=sample_value(u_source,v_uv);}",base);
        sampler1d_fragment_case("vec4 nested(sampler1D s,float x){return texture1D(s,x);} vec4 forwarded(sampler1D s,float x){return nested(s,x);} void main(){gl_FragColor=forwarded(u_source,v_uv);}",base);
    }
    NormalizeOptions options;options.base_level_sampling=true;
    auto bias=normalize_program("attribute vec2 a_position; varying float v_uv; void main(){v_uv=(a_position.x+1.)*.5;gl_Position=vec4(a_position,0.,1.);}","uniform sampler1D u_source; varying float v_uv;void main(){gl_FragColor=texture1D(u_source,v_uv,1.);}",options);
    require(!bias.error.empty()&&bias.error.find("bias is unsupported")!=std::string::npos,"base-level 1D bias must reject");
    auto lod=normalize_program("attribute vec2 a_position; varying float v_uv; void main(){v_uv=(a_position.x+1.)*.5;gl_Position=vec4(a_position,0.,1.);}","uniform sampler1D u_source; varying float v_uv;void main(){gl_FragColor=texture1DLod(u_source,v_uv,0.);}",options);
    compile_and_reflect(lod);
    require(lod.fragment.find("textureLod") != std::string::npos,
        "single-level legacy1D explicit LOD retains an actual sampling instruction");
}

void multidimensional_sampler_arrays() {
    for (const std::string type : {"sampler1D", "sampler2D", "sampler3D", "samplerCube", "isampler2D", "usampler2D"}) {
        const std::string coord = type == "sampler1D" ? ".5" :
            type == "sampler3D" || type == "samplerCube" ? "vec3(.5)" : "vec2(.5)";
        std::string reads;
        for (int row = 0; row < 2; ++row) for (int col = 0; col < 3; ++col) {
            if (!reads.empty()) reads += '+';
            reads += "vec4(texture(images[" + std::to_string(row) + "][" + std::to_string(col) + "]," + coord + "))";
        }
        auto normalized = normalize_program(vertex, "uniform " + type + " images[2][3];"
            "void main(){gl_FragColor=" + reads + ";}");
        compile_and_reflect(normalized);
        require(normalized.samplers.size() == 6, "all nested sampler leaves retain independent resources");
        for (size_t i = 0; i < normalized.samplers.size(); ++i) {
            auto& sampler = normalized.samplers[i];
            require(sampler.name == "images[" + std::to_string(i / 3) + "][" + std::to_string(i % 3) + "]" &&
                sampler.array_dimensions == std::vector<uint32_t>({2, 3}), "ordered sampler shape/public names");
            require(sampler.texture_binding == 1 + i * 2 && sampler.sampler_binding == 2 + i * 2,
                "sampler array has one static texture/sampler pair per leaf");
            sampler.texture_stage_mask = sampler.sampler_stage_mask = 2;
        }
        auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
        std::string error;
        require(compiled.ok && reflect_sampler_types(compiled.fragment.words, normalized.samplers, 2, error),
            "typed nested sampler reflection: " + error);
    }
    auto helper = normalize_program(vertex,
        "uniform sampler2D images[2][3];vec4 fetch(sampler2D image,vec2 uv){return texture(image,uv);}"
        "void main(){gl_FragColor=fetch((images[1][0x2u]),vec2(.5));}");
    compile_and_reflect(helper);
    auto cube = normalize_program(vertex,
        "uniform sampler2D images[2][2][2];void main(){gl_FragColor=texture(images[1][0][1],vec2(.5));}");
    compile_and_reflect(cube);
    require(cube.samplers.size() == 8, "three-dimensional sampler declarations retain every leaf");
    auto mismatch = normalize_program("uniform sampler2D images[3][2];void main(){gl_Position=vec4(0);}",
        "uniform sampler2D images[2][3];void main(){gl_FragColor=texture(images[1][2],vec2(.5));}");
    require(mismatch.error.find("array shapes differ") != std::string::npos, "equal products cannot alias sampler shapes");
    for (const std::string index : {"[2][0]", "[1][3]", "[1]", "[1][2][0]", "[1][1.0]", "[1][which]"}) {
        auto rejected = normalize_program(vertex, "uniform int which;uniform sampler2D images[2][3];"
            "void main(){gl_FragColor=texture(images" + index + ",vec2(.5));}");
        require(!rejected.error.empty(), "partial/out-of-bounds/nonliteral sampler index must fail explicitly");
    }
}

void literal_sampler_arrays() {
    const std::string fragment = "uniform sampler2D images[2]; void main(){gl_FragColor="
        "texture2D(images[0],vec2(.25))+texture2D(images[1],vec2(.75));}";
    auto normalized = normalize_program(vertex, fragment);
    compile_and_reflect(normalized);
    require(normalized.samplers.size() == 2 && normalized.samplers[0].name == "images[0]" &&
        normalized.samplers[1].name == "images[1]", "literal sampler array retains public GLIR element names");
    require(normalized.samplers[0].texture_binding != normalized.samplers[1].texture_binding &&
        normalized.samplers[0].sampler_binding != normalized.samplers[1].sampler_binding,
        "literal sampler array has distinct native texture/sampler resource pairs");
    auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
    require(compiled.ok, compiled.log);
    for (const auto& sampler : normalized.samplers) {
        for (uint32_t binding : {sampler.texture_binding, sampler.sampler_binding})
            require(std::any_of(compiled.resource_usage.begin(), compiled.resource_usage.end(),
                [&](const auto& resource) { return resource.binding == binding && resource.stage_mask == 2; }),
                "real SPIR-V fragment reflection uses each array element resource");
    }
    for (const std::string spelling : {"0x1", "01", "1u", "1U"}) {
        auto integer_index = normalize_program(vertex,
            "uniform sampler2D images[2];void main(){gl_FragColor=texture2D(images[" + spelling + "],vec2(.5));}");
        compile_and_reflect(integer_index);
    }
    auto fractional_index = normalize_program(vertex,
        "uniform sampler2D images[2];void main(){gl_FragColor=texture2D(images[1.0],vec2(.5));}");
    require(fractional_index.error.find("integer index") != std::string::npos,
        "floating numeric prefixes cannot masquerade as literal integer array indices");
    auto helper = normalize_program(vertex,
        "uniform sampler2D images[2]; vec4 fetch(sampler2D image,vec2 uv){return texture2D(image,uv);}"
        "void main(){gl_FragColor=fetch((images[0]),vec2(.25))+fetch(images[1],vec2(.75));}");
    compile_and_reflect(helper);
    auto shadowed = normalize_program(vertex,
        "uniform sampler2D images[2]; struct Cell{vec4 images;};float local(float images){return images;}"
        "void main(){Cell c;c.images=vec4(0);{float images=local(0.0);c.images+=vec4(images);}"
        "gl_FragColor=texture2D(images[0],vec2(.25))+texture2D(images[1],vec2(.75))+c.images;}");
    compile_and_reflect(shadowed);
    auto shadow_sampler = normalize_program(vertex,
        "uniform sampler2D images[2];vec4 fetch(sampler2D images,vec2 uv){return texture2D(images,uv);}"
        "void main(){gl_FragColor=fetch(images[1],vec2(.5));}");
    compile_and_reflect(shadow_sampler);
    auto both = normalize_program(
        "attribute vec2 a_position;uniform sampler2D images[2];void main(){gl_Position=vec4(a_position+texture2D(images[1],vec2(.25)).xy*.01,0,1);}",
        fragment);
    compile_and_reflect(both);
    require(both.samplers.size() == 2, "same array declared in both stages shares resource pairs");
    auto mismatch = normalize_program("uniform sampler2D images[3];void main(){gl_Position=vec4(0);}", fragment);
    require(mismatch.error.find("stage sampler array shapes differ") != std::string::npos,
        "stage array shape disagreement cannot alias an admitted resource graph");
    auto dynamic = normalize_program(vertex,
        "uniform sampler2D images[2];uniform int index;void main(){gl_FragColor=texture2D(images[index],vec2(.5));}");
    require(dynamic.error.find("literal") != std::string::npos, "dynamic array index remains an explicit pending policy");
    auto outside = normalize_program(vertex,
        "uniform sampler2D images[2];void main(){gl_FragColor=texture2D(images[2],vec2(.5));}");
    require(outside.error.find("declared length") != std::string::npos, "out-of-bounds sampler index refuses before code generation");
    auto typed = normalize_program(vertex,
        "uniform usampler2D images[2];void main(){gl_FragColor=vec4(texture(images[0],vec2(.5)));}");
    compile_and_reflect(typed);
    require(typed.samplers[0].sample_scalar == ShaderScalarType::Uint,
        "typed sampler arrays preserve integer sampled words");
}

void explicit_single_level_sampling() {
    for (bool base : {false, true}) for (const std::string function :
        {"textureLod", "texture2DLod", "textureGrad", "texture2DGradEXT"}) {
        const bool gradients = function.find("Grad") != std::string::npos;
        const auto expression = function + "(image,vec2(.5)," +
            (gradients ? "next_dx(),next_dy()" : "next_level()") + ')';
        auto n = normalize_program(vertex,
            "uniform sampler2D image;uniform float level;uniform vec2 gx,gy;float counter=0.;"
            "float next_level(){counter+=1.;return level;}vec2 next_dx(){counter+=2.;return gx;}"
            "vec2 next_dy(){counter+=3.;return gy;}void main(){gl_FragColor=" + expression + "+vec4(0,counter*.01,0,0);}",
            NormalizeOptions{base});
        compile_and_reflect(n);
        const auto compiled = compile_vulkan_glsl(n.vertex, n.fragment);
        require(compiled.ok, compiled.log);
        std::unordered_set<uint32_t> calls;
        for (size_t at=5;at<compiled.fragment.words.size();) {
            const auto count=compiled.fragment.words[at]>>16;
            if (spv::Op(compiled.fragment.words[at]&0xffffu)==spv::Op::OpFunctionCall)
                calls.insert(compiled.fragment.words[at+2]);
            at+=count;
        }
        size_t actual_samples=0;
        for (size_t at=5;at<compiled.fragment.words.size();) {
            const auto count=compiled.fragment.words[at]>>16;
            if (spv::Op(compiled.fragment.words[at]&0xffffu)==spv::Op::OpImageSampleExplicitLod) {
                const auto* args=compiled.fragment.words.data()+at+1;
                if (gradients) {
                    require(count==8 && args[4]==uint32_t(spv::ImageOperandsMask::Grad) &&
                        calls.contains(args[5]) && calls.contains(args[6]),
                        "real gradient sample consumes both evaluated helper results");
                } else {
                    require(count==7 && args[4]==uint32_t(spv::ImageOperandsMask::Lod) && calls.contains(args[5]),
                        "real explicit LOD sample consumes its evaluated helper result, not a replacement zero");
                }
                ++actual_samples;
            }
            at+=count;
        }
        require(actual_samples==1, "one supplied explicit sampling operation survives normalization");
    }
}

void sampling_policy() {
    const std::string fragment = "uniform sampler2D u_image; void main(){ gl_FragColor=texture2D(u_image,vec2(0.5)); }";
    auto implicit = normalize_program(vertex, fragment);
    compile_and_reflect(implicit);
    require(implicit.fragment.find("textureLod") == std::string::npos, "implicit sampling preserved by default");
    auto base = normalize_program(vertex, fragment, NormalizeOptions{true});
    compile_and_reflect(base);
    require(base.fragment.find("textureLod") != std::string::npos, "base-only admission uses explicit level");
    auto biased = normalize_program(vertex, "uniform sampler2D u_image; void main(){ gl_FragColor=texture2D(u_image,vec2(0.5),2.0); }", NormalizeOptions{true});
    require(biased.error.find("bias") != std::string::npos, "bias rejected under base-only policy");
    auto mismatched = normalize_program("uniform bool u_flag; void main(){ gl_Position=vec4(0); }",
                                        "uniform float u_flag; void main(){ gl_FragColor=vec4(u_flag); }");
    require(mismatched.error.find("u_flag") != std::string::npos, "stage uniform mismatch identified");
}

void composer_diagnostics() {
    const std::string fragment = "void main() {\n gl_FragColor=vec4(1);\n this_is_not_valid_glsl;\n}\n";
    auto normalized = normalize_program(vertex, fragment);
    auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
    require(!compiled.ok, "invalid composer snippet must fail");
    const auto needle = std::string("this_is_not_valid_glsl");
    size_t position = normalized.fragment.find(needle);
    require(position != std::string::npos, "snippet preserved");
    size_t line = std::count(normalized.fragment.begin(), normalized.fragment.begin() + position, '\n');
    require(normalized.fragment_line_map[line] == 3, "invalid snippet maps to composer line 3");
    require(compiled.fragment.log.find("ERROR") != std::string::npos, "compiler stage diagnostics retained");
}

void composed_parameter_qualifiers() {
    auto normalized = normalize_program(
        "layout(location=3) in vec2 a_position;\n"
        "void helper(in vec2 p, out vec4 result);\n"
        "void helper(in vec2 p, out vec4 result){ result=vec4(p,0,1); }\n"
        "void main(){ helper(a_position, gl_Position); }\n",
        "uniform float u_value;\n"
        "float helper(in float x, out float copy, inout float running){ copy=x; running+=x; return x; }\n"
        "void main(){ float copy=0; float running=0; float value=helper(u_value,copy,running); gl_FragColor=vec4(value+copy+running); }\n");
    compile_and_reflect(normalized);
    require(normalized.attributes.size() == 1 && normalized.attributes[0].name == "a_position", "function parameter is not a vertex attribute");
    require(normalized.uniforms.size() == 1 && normalized.uniforms[0].name == "u_value", "function parameters are not uniforms");
    require(normalized.fragment.find("out float copy") != std::string::npos, "composer out parameter preserved");
    require(normalized.vertex.find("location = 3") == std::string::npos, "old layout is removed with replaced stage declaration");
}

void composed_sampler_parameters() {
    auto normalized = normalize_program(vertex,
        "uniform sampler2D u_image; uniform sampler2D u_kernel; uniform sampler3D u_volume;\n"
        "float kernel_value(in sampler2D kernel, vec2 uv){ return texture2D(kernel,uv).r; }\n"
        "vec4 filtered(sampler2D texture, sampler2D kernel, vec2 uv){ return texture2D(texture,uv)*kernel_value(kernel,uv); }\n"
        "float sample(sampler2D texture,vec2 uv,float width){ return filtered(texture,u_kernel,uv).r+width; }\n"
        "float sample(sampler3D texture,vec3 uv,float width){ return texture3D(texture,uv).r+width; }\n"
        "void main(){ gl_FragColor=vec4(sample(u_image,vec2(.5),0.1)+sample(u_volume,vec3(.5),0.2)); }\n",
        NormalizeOptions{true});
    compile_and_reflect(normalized);
    require(normalized.samplers.size() == 3, "only uniform samplers have resource bindings");
    require(normalized.fragment.find("sampler2D texture") == std::string::npos, "combined opaque function parameters split");
    require(normalized.fragment.find("vispy_tex_u_image, vispy_samp_u_image") != std::string::npos, "uniform helper argument expands to paired resources");
    require(normalized.fragment.find("vispy_param_tex_texture, vispy_param_samp_texture") != std::string::npos, "nested helper argument retains parameter resources");
    require(normalized.fragment.find("vispy_user_sample") != std::string::npos, "legacy sample helper renamed around modern reserved word");
    auto rejected = normalize_program(vertex,
        "uniform sampler2D u_image; void helper(out sampler2D texture){} void main(){ helper(u_image); gl_FragColor=vec4(1); }");
    require(rejected.error.find("named scalar input") != std::string::npos, "unsupported sampler output parameter diagnosed");
}

void opaque_helper_lowering() {
    // Reduced composed Text filter: opaque resources pass through two helper
    // levels; a repeated call and branch used to enter Tint's function cloning
    // path. Numeric helper calls and the original sampling policy must survive.
    const std::string fragment =
        "uniform sampler2D u_atlas; uniform sampler2D u_kernel; varying vec2 uv;\n"
        "float numeric_weight(float x){ return x*x*(3.0-2.0*x); }\n"
        "float kernel_value(in sampler2D kernel,float x){ return texture2D(kernel,vec2(x,.5)).r; }\n"
        "float filtered(sampler2D atlas,sampler2D kernel,vec2 p){ float value=0.0; "
        "for(int i=0;i<2;++i){ float x=float(i)*.5; value+=texture2D(atlas,p+vec2(x,0)).r*kernel_value(kernel,x); } return value; }\n"
        "float coverage(sampler2D atlas,sampler2D kernel,vec2 p){ "
        "if(p.x<.5) return filtered(atlas,kernel,p); return filtered(atlas,kernel,p*.5); }\n"
        "void main(){ float a=coverage(u_atlas,u_kernel,uv); float b=coverage(u_atlas,u_kernel,uv+vec2(.1)); "
        "gl_FragColor=vec4(numeric_weight(a)+numeric_weight(b)); }\n";
    const std::string source_vertex = "attribute vec2 a_position; varying vec2 uv; void main(){ uv=a_position; gl_Position=vec4(a_position,0,1); }";
    for (bool base_level : {false, true}) {
        auto normalized = normalize_program(source_vertex, fragment, NormalizeOptions{base_level});
        compile_and_reflect(normalized);
        auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
        require(compiled.ok, compiled.log);
        const auto& words = compiled.fragment.words;
        std::unordered_set<uint32_t> opaque;
        std::unordered_set<uint32_t> bindings;
        uint32_t numeric_function = 0;
        size_t explicit_samples = 0, implicit_samples = 0;
        bool numeric_body = false;
        for (size_t position = 5; position < words.size();) {
            const size_t count = words[position] >> 16;
            const auto op = static_cast<spv::Op>(words[position] & 0xffffu);
            if (op == spv::Op::OpTypeImage || op == spv::Op::OpTypeSampler || op == spv::Op::OpTypeSampledImage)
                opaque.insert(words[position + 1]);
            if (op == spv::Op::OpTypePointer && opaque.contains(words[position + 3])) opaque.insert(words[position + 1]);
            if (op == spv::Op::OpFunctionParameter) require(!opaque.contains(words[position + 1]), "opaque helper parameter reached Dawn");
            if (op == spv::Op::OpFunction) {
                require(!opaque.contains(words[position + 1]), "opaque helper result reached Dawn");
                numeric_body |= words[position + 2] == numeric_function;
            }
            if (op == spv::Op::OpName) {
                const char* name = reinterpret_cast<const char*>(words.data() + position + 2);
                if (std::string(name).find("numeric_weight") != std::string::npos) numeric_function = words[position + 1];
            }
            if (op == spv::Op::OpDecorate && static_cast<spv::Decoration>(words[position + 2]) == spv::Decoration::Binding)
                bindings.insert(words[position + 3]);
            explicit_samples += op == spv::Op::OpImageSampleExplicitLod;
            implicit_samples += op == spv::Op::OpImageSampleImplicitLod;
            position += count;
        }
        require(numeric_function && numeric_body, "numeric helper retained by selective pass");
        require(bindings == std::unordered_set<uint32_t>{1, 2, 3, 4}, "paired atlas/kernel resource bindings retained");
        require(base_level ? explicit_samples > 0 && implicit_samples == 0 : implicit_samples > 0 && explicit_samples == 0,
                "opaque inlining retains implicit or base-level sampling policy");
    }
}

void explicit_fragment_output() {
    const std::string flat_vertex =
        "#version 130\nin vec2 a_position; in vec4 a_color; flat out vec4 v_color;\n"
        "void main(){gl_Position=vec4(a_position,0.,1.); v_color=a_color;}";
    const std::string flat_fragment =
        "#version 130\nflat in vec4 v_color; out vec4 out_color;\nvoid main(){out_color=v_color;}";
    auto flat = normalize_program(flat_vertex, flat_fragment);
    compile_and_reflect(flat);
    require(flat.has_flat_varyings, "flat interpolation requires last-vertex metadata");
    require(flat.fragment.find("out vec4 out_color;") != std::string::npos,
            "explicit output declaration and identifier retained");
    require(flat.fragment.find("vispy_out_color") == std::string::npos,
            "single explicit output does not introduce a second color attachment");
    auto scalar = normalize_program(vertex, "layout(location=0) out float result; void main(){result=.25;}");
    compile_and_reflect(scalar);
    require(!scalar.has_flat_varyings, "ordinary shaders do not require provoking-vertex policy");
    auto multiple = normalize_program(vertex, "out vec4 first, second; void main(){first=second=vec4(1);}");
    require(multiple.error.find("multiple color outputs") != std::string::npos,
            "multiple outputs must not silently write attachment zero");
    auto array = normalize_program(vertex, "out vec4 result[2]; void main(){result[0]=vec4(1);}");
    require(array.error.find("color output arrays") != std::string::npos, "output arrays require actual attachment support");
    auto location = normalize_program(vertex, "layout(location=1) out vec4 result; void main(){result=vec4(1);}");
    require(location.error.find("location 0") != std::string::npos, "nonzero output location must not be redirected");
    auto component = normalize_program(vertex,
        "layout(location=0,component=1) out vec3 result; void main(){result=vec3(1);}");
    require(component.error.find("component") != std::string::npos, "component routing must not be silently removed");
    auto dual = normalize_program(vertex,
        "layout(location=0,index=1) out vec4 result; void main(){result=vec4(1);}");
    require(dual.error.find("index") != std::string::npos, "dual-source routing requires actual backend support");
    auto expression = normalize_program(vertex,
        "layout(location=0+1) out vec4 result; void main(){result=vec4(1);}");
    require(expression.error.find("location 0") != std::string::npos, "location expressions must not be discarded");
}

void scientific_predicates() {
    auto normalized = normalize_program(vertex,
        "uniform vec4 u_values; void main(){ bool scalar=isnan(u_values.x)||isinf(u_values.y); "
        "bvec4 vectors=isnan(u_values); bvec3 triples=isinf(u_values.xyz); "
        "gl_FragColor=vec4(scalar && any(vectors) && any(triples) ? 1.0 : 0.0); }");
    compile_and_reflect(normalized);
    require(normalized.fragment.find("floatBitsToUint") != std::string::npos, "scientific predicates inspect float bits");
    auto compiled = compile_vulkan_glsl(normalized.vertex, normalized.fragment);
    // OpIsNan=156 and OpIsInf=157 are intentionally absent from the generated
    // module. Verify instruction opcodes rather than matching GLSL strings.
    for (size_t position = 5; position < compiled.fragment.words.size();) {
        const uint32_t instruction = compiled.fragment.words[position];
        require((instruction & 0xffffu) != 156 && (instruction & 0xffffu) != 157, "unsupported SPIR-V predicate present");
        position += instruction >> 16;
    }
}
void depth_range_lowering() {
    NormalizeOptions reverse;
    reverse.reverse_depth = true;
    auto normalized = normalize_program(vertex, "void main(){gl_FragColor=vec4(1);}", reverse);
    compile_and_reflect(normalized);
    require(normalized.vertex.find("gl_Position.w - gl_Position.z") != std::string::npos,
        "reverse clip conversion runs in the final vertex wrapper");
    auto depth = normalize_program(vertex,
        "#define COORD gl_FragCoord\n#define DEPTH gl_FragDepth\n"
        "void main(){DEPTH=.1;gl_FragColor=vec4(COORD.z);}");
    compile_and_reflect(depth);
    require(depth.fragment.find("mix(vispy_fragment_depth_range.x") != std::string::npos,
        "fragment-coordinate alias retains the logical depth range");
    auto invalid = normalize_program(vertex,
        "uniform vec2 vispy_fragment_depth_range;void main(){gl_FragColor=gl_FragCoord;}");
    require(invalid.error.find("reserved") != std::string::npos, "private depth control cannot alias a user uniform");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc > 1 && std::string(argv[1]) == "--bool-scope-original-baseline") {
            require(argc == 3, "--bool-scope-original-baseline requires the exact program directory");
            boolean_scope_original_baseline(argv[2]);
            return 0;
        }
        uniform_layouts();
        multidimensional_uniforms();
        boolean_lowering();
        boolean_scope_lowering();
        coordinate_entry();
        one_dimensional_sampling();
        sampling_policy(); literal_sampler_arrays(); multidimensional_sampler_arrays(); explicit_single_level_sampling();
        composer_diagnostics();
        composed_parameter_qualifiers();
        composed_sampler_parameters();
        opaque_helper_lowering();
        explicit_fragment_output();
        scientific_predicates();
        depth_range_lowering();
        if (argc > 1) {
            const std::filesystem::path corpus(argv[1]);
            for (const auto& file : std::filesystem::directory_iterator(corpus)) {
                if (file.path().extension() != ".vert") continue;
                auto fragment = file.path();
                fragment.replace_extension(".frag");
                auto normalized = normalize_program(read(file.path()), read(fragment), NormalizeOptions{true});
                compile_and_reflect(normalized);
                std::cout << "validated " << file.path().stem().string() << '\n';
            }
        }
        std::cout << "shader normalization, reflection, SPIR-V validation, and packing contracts passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
