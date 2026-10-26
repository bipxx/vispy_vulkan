#include "shader/line_consumer.hpp"
#include "shader/glslang_spv.hpp"
#include <SPIRV/spirv.hpp11>
#include <SPIRV/GLSL.std.450.h>

#include <array>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <unordered_map>
#include <unordered_set>

namespace {
using namespace vispy::shader;
uint32_t checks = 0;
std::filesystem::path diagnostics_directory;
void require(bool condition, const std::string& message) {
    ++checks; if (!condition) throw std::runtime_error(message);
}
void refusal(const std::function<void()>& run, const std::string& message) {
    bool rejected = false; try { run(); } catch (const std::exception&) { rejected = true; }
    require(rejected, message);
}
LineConsumerLimits grants() { return {256ull << 20, 256ull << 20, 65536, 8, 1000, 0, 0, 1}; }
LineConsumerPolicy policy() { return {LineCoveragePolicy::AliasedMajorAxis, 1, kAliasedLineCoverageIdentity}; }

void diagnostic_bytes(const std::string& name, const void* data, size_t bytes) {
    if (diagnostics_directory.empty()) return;
    const auto path = diagnostics_directory / name;
    if (std::filesystem::exists(path)) throw std::runtime_error("diagnostic artifact already exists: " + path.string());
    std::ofstream out(path, std::ios::binary);
    if (bytes) out.write(static_cast<const char*>(data), static_cast<std::streamsize>(bytes));
    out.close();
    if (!out) throw std::runtime_error("diagnostic artifact write failed: " + path.string());
}
void diagnostic_text(const std::string& name, const std::string& text) { diagnostic_bytes(name, text.data(), text.size()); }
void diagnostic_opcodes(const std::string& name, const std::vector<uint32_t>& words) {
    std::map<uint32_t, size_t> counts;
    for (size_t p = 5; p < words.size();) {
        const size_t count = words[p] >> 16;
        if (!count || count > words.size() - p) throw std::runtime_error("malformed opcode diagnostic module");
        ++counts[words[p] & 0xffffu]; p += count;
    }
    std::ostringstream out;
    for (const auto& [opcode, count] : counts) {
        const auto op = static_cast<spv::Op>(opcode);
        const char* label = op == spv::Op::OpIsHelperInvocationEXT ? "OpIsHelperInvocationEXT" :
            op == spv::Op::OpDemoteToHelperInvocationEXT ? "OpDemoteToHelperInvocationEXT" :
            op == spv::Op::OpIsNan ? "OpIsNan" : op == spv::Op::OpIsInf ? "OpIsInf" :
            op == spv::Op::OpBitcast ? "OpBitcast" : op == spv::Op::OpBitwiseAnd ? "OpBitwiseAnd" :
            op == spv::Op::OpULessThan ? "OpULessThan" : "";
        out << opcode << ' ' << label << ' ' << count << '\n';
    }
    diagnostic_text(name + ".opcodes.txt", out.str());
}
void diagnostics(const std::string& name, const GeneratedLineConsumerArtifact& c) {
    if (diagnostics_directory.empty()) return;
    diagnostic_text(name + ".vert.glsl", c.vertex); diagnostic_text(name + ".frag.glsl", c.fragment);
    diagnostic_bytes(name + ".vert.spv", c.vertex_spv.data(), c.vertex_spv.size() * sizeof(uint32_t));
    diagnostic_bytes(name + ".frag.spv", c.fragment_spv.data(), c.fragment_spv.size() * sizeof(uint32_t));
    diagnostic_text(name + ".log.txt", c.error + '\n' + c.log);
    std::ostringstream reflection;
    reflection << "ok=" << c.ok << "\nrow_bytes=" << c.fragment_rows.row_stride << "\nparams_offset=" << c.parameters_offset
        << "\nuniform_bytes=" << c.uniform_bytes << "\nuniform_stages=" << c.uniform_stage_mask
        << "\nprivate_initializers=" << c.relocated_fragment_initializers << '\n';
    for (const auto& f : c.fragment_rows.members) reflection << f.name << " offset=" << f.offset << " size=" << f.size
        << " array=" << f.array_size << " array_stride=" << f.array_stride << " matrix_stride=" << f.matrix_stride << '\n';
    for (const auto& r : c.resource_usage) reflection << "resource binding=" << r.binding << " stages=" << r.stage_mask << '\n';
    diagnostic_text(name + ".reflection.txt", reflection.str());
    diagnostic_opcodes(name + ".vert", c.vertex_spv); diagnostic_opcodes(name + ".frag", c.fragment_spv);
}

const std::string basic_vertex = R"(
attribute vec4 position;
varying vec4 color;
void main() {
    gl_Position = position;
    color = vec4(float(gl_VertexID), float(gl_InstanceID), 0.5, 1.0);
}
)";
const std::string basic_fragment = R"(
varying vec4 color;
void main() {
    if (color.z < 0.0) discard;
    gl_FragColor = color + vec4(gl_FragCoord.w, gl_FrontFacing ? 1.0 : 0.0, 0.0, 0.0);
    if (color.x < 0.0) gl_FragDepth = 0.25;
}
)";
std::shared_ptr<const LineEvaluatorArtifact> evaluator(const std::string& vertex = basic_vertex,
        const std::string& fragment = basic_fragment) {
    auto original = build_portable_shader(vertex, fragment, {}, "sdk3-standalone-consumer-contract");
    require(original->ok, "actual original shader compile: " + original->error);
    auto result = build_line_evaluator(original);
    require(result->ok, "actual evaluator shader compile: " + result->error);
    return result;
}

struct Instruction { spv::Op op; uint32_t function, block; size_t offset; std::vector<uint32_t> args; };
struct Trace {
    uint32_t entry = 0, first_block = 0;
    std::vector<Instruction> code;
    std::unordered_map<uint32_t, std::string> names;
    std::unordered_map<uint32_t, std::vector<uint32_t>> successors;
    std::unordered_map<uint32_t, uint32_t> roots;
    std::unordered_map<uint32_t, uint32_t> function_first_block, loaded_from, constants;
    std::unordered_map<uint32_t, uint32_t> variable_functions, variable_types, pointer_types, loaded_pointers;
    std::unordered_map<uint32_t, std::vector<uint32_t>> access_indices;
    std::map<std::pair<uint32_t, uint32_t>, std::string> member_names;
    std::map<std::pair<uint32_t, uint32_t>, spv::BuiltIn> member_builtins;
    std::unordered_map<uint32_t, spv::BuiltIn> builtins;
    std::unordered_map<uint32_t, std::vector<uint32_t>> composite_constants;
    std::unordered_set<uint32_t> false_constants, true_constants;
    explicit Trace(const std::vector<uint32_t>& words) {
        uint32_t function = 0, block = 0;
        for (size_t p = 5; p < words.size();) {
            const size_t count = words[p] >> 16;
            if (!count || count > words.size() - p) throw std::runtime_error("malformed real compiler SPIR-V");
            const auto op = static_cast<spv::Op>(words[p] & 0xffffu); const auto* a = words.data() + p + 1;
            if (op == spv::Op::OpName) {
                const char* begin = reinterpret_cast<const char*>(a + 1);
                const auto end = std::memchr(begin, 0, (count - 2) * 4);
                if (!end) throw std::runtime_error("compiler name is not terminated");
                names[a[0]] = std::string(begin, static_cast<const char*>(end) - begin);
            }
            if (op == spv::Op::OpEntryPoint) entry = a[1];
            if (op == spv::Op::OpMemberName) member_names[{a[0], a[1]}] = reinterpret_cast<const char*>(a + 2);
            if (op == spv::Op::OpMemberDecorate && count == 5 && a[2] == static_cast<uint32_t>(spv::Decoration::BuiltIn))
                member_builtins[{a[0], a[1]}] = static_cast<spv::BuiltIn>(a[3]);
            if (op == spv::Op::OpTypePointer) pointer_types[a[0]] = a[2];
            if (op == spv::Op::OpDecorate && count == 4 && a[1] == static_cast<uint32_t>(spv::Decoration::BuiltIn))
                builtins[a[0]] = static_cast<spv::BuiltIn>(a[2]);
            if (op == spv::Op::OpConstant && count == 4) constants[a[1]] = a[2];
            if (op == spv::Op::OpConstantComposite) composite_constants[a[1]] = std::vector<uint32_t>(a + 2, a + count - 1);
            if (op == spv::Op::OpConstantFalse) false_constants.insert(a[1]);
            if (op == spv::Op::OpConstantTrue) true_constants.insert(a[1]);
            if (op == spv::Op::OpVariable) {
                roots[a[1]] = a[1]; variable_functions[a[1]] = function; variable_types[a[1]] = a[0];
            }
            if ((op == spv::Op::OpAccessChain || op == spv::Op::OpInBoundsAccessChain || op == spv::Op::OpCopyObject) && count >= 4)
                roots[a[1]] = roots.contains(a[2]) ? roots[a[2]] : a[2];
            if (op == spv::Op::OpAccessChain || op == spv::Op::OpInBoundsAccessChain)
                access_indices[a[1]] = std::vector<uint32_t>(a + 3, a + count - 1);
            if (op == spv::Op::OpFunction) { function = a[1]; block = 0; }
            if (op == spv::Op::OpLabel) {
                block = a[0]; function_first_block.try_emplace(function, block);
                if (function == entry && !first_block) first_block = block;
            }
            if (op == spv::Op::OpLoad) {
                loaded_from[a[1]] = roots.contains(a[2]) ? roots[a[2]] : a[2]; loaded_pointers[a[1]] = a[2];
            }
            if (function && op == spv::Op::OpBranch) successors[block] = {a[0]};
            if (function && op == spv::Op::OpBranchConditional) successors[block] = {a[1], a[2]};
            if (function && op == spv::Op::OpSwitch) {
                std::vector<uint32_t> target{a[1]}; for (size_t n = 3; n < count - 1; n += 2) target.push_back(a[n]);
                successors[block] = std::move(target);
            }
            code.push_back({op, function, block, p, {a, a + count - 1}});
            if (op == spv::Op::OpFunctionEnd) { function = 0; block = 0; }
            p += count;
        }
    }
    uint32_t id(const std::string& name, bool begins = false) const {
        for (const auto& [id, text] : names) if (begins ? text.rfind(name, 0) == 0 : text == name) return id;
        throw std::runtime_error("missing real compiler symbol " + name);
    }
    bool dominates(const Instruction& earlier, const Instruction& later) const {
        if (!earlier.function || earlier.function != later.function) return false;
        if (earlier.block == later.block) return earlier.offset < later.offset;
        std::unordered_set<uint32_t> visited;
        std::vector<uint32_t> todo{function_first_block.at(earlier.function)};
        while (!todo.empty()) {
            const auto block = todo.back(); todo.pop_back();
            if (block == earlier.block || !visited.insert(block).second) continue;
            if (block == later.block) return false;
            if (auto next = successors.find(block); next != successors.end())
                todo.insert(todo.end(), next->second.begin(), next->second.end());
        }
        return true;
    }
    bool reaches(uint32_t from, uint32_t to) const {
        std::unordered_set<uint32_t> visited; std::vector<uint32_t> todo{from};
        while (!todo.empty()) {
            const auto block = todo.back(); todo.pop_back();
            if (block == to) return true;
            if (!visited.insert(block).second) continue;
            if (auto next = successors.find(block); next != successors.end())
                todo.insert(todo.end(), next->second.begin(), next->second.end());
        }
        return false;
    }
    bool constant_is(uint32_t id, uint32_t bits) const {
        if (auto scalar = constants.find(id); scalar != constants.end()) return scalar->second == bits;
        if (auto vector = composite_constants.find(id); vector != composite_constants.end())
            return !vector->second.empty() && std::all_of(vector->second.begin(), vector->second.end(),
                [&](uint32_t component) { return constant_is(component, bits); });
        return false;
    }
    uint32_t local_id(uint32_t function, const std::string& name) const {
        for (const auto& [id, text] : names) if (text == name && variable_functions.contains(id) &&
                variable_functions.at(id) == function) return id;
        throw std::runtime_error("missing function-local compiler symbol " + name);
    }
    bool field_load(uint32_t value, const std::string& member, uint32_t component) const {
        if (!loaded_pointers.contains(value)) return false;
        const auto pointer = loaded_pointers.at(value);
        if (!access_indices.contains(pointer) || !loaded_from.contains(value)) return false;
        const auto& indices = access_indices.at(pointer);
        const auto root = loaded_from.at(value);
        if (indices.size() != 2 || !constants.contains(indices[0]) || !constant_is(indices[1], component) ||
                !variable_types.contains(root) || !pointer_types.contains(variable_types.at(root))) return false;
        const auto key = std::make_pair(pointer_types.at(variable_types.at(root)), constants.at(indices[0]));
        return member_names.contains(key) && member_names.at(key) == member;
    }
    // glslang's short-circuit OR can merge the refusal condition through a
    // Boolean Phi. Check that exact path as well as a standalone comparison.
    bool refusal_dominates(const Instruction& compare, const Instruction& operation) const {
        const auto false_return = [&](uint32_t block) {
            for (const auto& i : code) if (i.function == compare.function && i.block == block &&
                    i.op == spv::Op::OpReturnValue && false_constants.contains(i.args[0])) return true;
            return false;
        };
        const auto refuses = [&](const Instruction& branch) {
            return branch.function == compare.function && branch.op == spv::Op::OpBranchConditional &&
                dominates(compare, branch) && dominates(branch, operation) && false_return(branch.args[1]) &&
                !reaches(branch.args[1], operation.block) && reaches(branch.args[2], operation.block);
        };
        for (const auto& branch : code) if (refuses(branch) && branch.args[0] == compare.args[1]) return true;
        for (const auto& negated : code) if (negated.function == compare.function &&
                negated.op == spv::Op::OpLogicalNot && negated.args[2] == compare.args[1])
            for (const auto& split : code) if (split.function == compare.function &&
                    split.op == spv::Op::OpBranchConditional && split.args[0] == negated.args[1])
                for (const auto& phi : code) if (phi.function == compare.function && phi.op == spv::Op::OpPhi &&
                        split.args[2] == phi.block)
                    for (size_t n = 2; n + 1 < phi.args.size(); n += 2)
                        if (phi.args[n] == compare.args[1] && phi.args[n + 1] == split.block)
                            for (const auto& branch : code) if (refuses(branch) && branch.args[0] == phi.args[1]) return true;
        return false;
    }
    const Instruction& entry_store(uint32_t variable) const {
        for (const auto& i : code) if (i.function == entry && i.op == spv::Op::OpStore &&
            (roots.contains(i.args[0]) ? roots.at(i.args[0]) : i.args[0]) == variable) return i;
        throw std::runtime_error("missing entry store for " + std::to_string(variable));
    }
    const Instruction& entry_call(uint32_t callee) const {
        for (const auto& i : code) if (i.function == entry && i.op == spv::Op::OpFunctionCall && i.args[2] == callee) return i;
        throw std::runtime_error("missing actual original fragment call");
    }
};

// Inspect the emitted data flow, not generated source spelling. The actual
// unsigned comparison must consume the sign-masked float bitcast and the
// infinity boundary. Scalar and vector forms use the same exact bit rule.
void finite_bits_contract(const GeneratedLineConsumerArtifact& consumer) {
    require(consumer.ok, consumer.error);
    for (size_t stage = 0; stage < 2; ++stage) {
        Trace trace(stage ? consumer.fragment_spv : consumer.vertex_spv);
        for (const auto& i : trace.code) require(i.op != spv::Op::OpIsNan && i.op != spv::Op::OpIsInf,
                "neither generated stage emits reader-incompatible OpIsNan/OpIsInf");
        const std::vector<std::string> names = stage ?
            std::vector<std::string>{"vispy_line_consumer_finite(", "vispy_line_consumer_finite4("} :
            std::vector<std::string>{"vispy_line_consumer_finite(", "vispy_line_consumer_finite2(", "vispy_line_consumer_finite4("};
        for (const auto& name : names) {
            const auto function = trace.id(name, true);
            bool classified = false;
            for (const auto& cast : trace.code) if (cast.function == function && cast.op == spv::Op::OpBitcast)
                for (const auto& mask : trace.code) if (mask.function == function && mask.op == spv::Op::OpBitwiseAnd &&
                    ((mask.args[2] == cast.args[1] && trace.constant_is(mask.args[3], 0x7fffffffu)) ||
                     (mask.args[3] == cast.args[1] && trace.constant_is(mask.args[2], 0x7fffffffu))))
                    for (const auto& compare : trace.code) if (compare.function == function && compare.op == spv::Op::OpULessThan &&
                        compare.args[2] == mask.args[1] && trace.constant_is(compare.args[3], 0x7f800000u)) {
                        // The scalar comparison is the returned value; vectors
                        // reduce this comparison through OpAll before returning.
                        for (const auto& returned : trace.code) if (returned.function == function && returned.op == spv::Op::OpReturnValue) {
                            classified |= returned.args[0] == compare.args[1];
                            for (const auto& all : trace.code) if (all.function == function && all.op == spv::Op::OpAll &&
                                all.args[2] == compare.args[1] && returned.args[0] == all.args[1]) classified = true;
                        }
                    }
            require(classified, "actual finite helper returns unsigned IEEE-754 classification: " + name);
        }
        if (!stage) {
            const auto finite2 = trace.id("vispy_line_consumer_finite2(", true);
            require(std::any_of(trace.code.begin(), trace.code.end(), [&](const Instruction& i) {
                return i.function == trace.entry && i.op == spv::Op::OpFunctionCall && i.args[2] == finite2;
            }), "actual vertex NDC refusal calls bit-finite vector classification");
        }
    }
}

// A real dynamic extension query may use short-circuit CFG+Phi or an OpLogicalOr.
// Both must combine the logical line flag with the native query result, rather
// than a startup snapshot. This predicate also distinguishes a real compiled
// native-only counterfactual below.
bool logical_dynamic_query(const Trace& trace, uint32_t function, uint32_t logical_helper) {
    for (const auto& query : trace.code) if (query.function == function && query.op == spv::Op::OpIsHelperInvocationEXT)
        for (const auto& load : trace.code) if (load.function == function && load.op == spv::Op::OpLoad &&
                trace.loaded_from.at(load.args[1]) == logical_helper) {
            for (const auto& combined : trace.code) if (combined.function == function) {
                if (combined.op == spv::Op::OpLogicalOr &&
                    ((combined.args[2] == load.args[1] && combined.args[3] == query.args[1]) ||
                     (combined.args[3] == load.args[1] && combined.args[2] == query.args[1])))
                    for (const auto& returned : trace.code) if (returned.function == function && returned.op == spv::Op::OpReturnValue &&
                            returned.args[0] == combined.args[1]) return true;
                if (combined.op != spv::Op::OpPhi) continue;
                bool native = false, logical = false;
                for (size_t n = 2; n + 1 < combined.args.size(); n += 2) {
                    native |= combined.args[n] == query.args[1];
                    logical |= combined.args[n] == load.args[1] || trace.true_constants.contains(combined.args[n]);
                }
                if (!native || !logical) continue;
                for (const auto& branch : trace.code) if (branch.function == function && branch.op == spv::Op::OpBranchConditional) {
                    bool false_queries = branch.args[0] == load.args[1] && trace.reaches(branch.args[2], query.block) &&
                        !trace.reaches(branch.args[1], query.block);
                    for (const auto& negated : trace.code) if (negated.function == function && negated.op == spv::Op::OpLogicalNot &&
                        negated.args[2] == load.args[1] && branch.args[0] == negated.args[1] &&
                        trace.reaches(branch.args[1], query.block) && !trace.reaches(branch.args[2], query.block)) false_queries = true;
                    if (false_queries) for (const auto& returned : trace.code)
                        if (returned.function == function && returned.op == spv::Op::OpReturnValue && returned.args[0] == combined.args[1]) return true;
                }
            }
        }
    return false;
}

void generated_position_contract(const GeneratedLineConsumerArtifact& consumer) {
    Trace trace(consumer.vertex_spv);
    const auto ndc = trace.local_id(trace.entry, "ndc");
    const auto ndc_component = [&](uint32_t value, uint32_t component) {
        if (!trace.loaded_from.contains(value) || trace.loaded_from.at(value) != ndc ||
                !trace.loaded_pointers.contains(value)) return false;
        const auto pointer = trace.loaded_pointers.at(value);
        return trace.access_indices.contains(pointer) && trace.access_indices.at(pointer).size() == 1 &&
            trace.constant_is(trace.access_indices.at(pointer)[0], component);
    };
    const auto negated_ndc_y = [&](uint32_t value) {
        return std::any_of(trace.code.begin(), trace.code.end(), [&](const Instruction& operation) {
            return operation.function == trace.entry && operation.op == spv::Op::OpFNegate &&
                operation.args.size() == 3 && operation.args[1] == value && ndc_component(operation.args[2], 1);
        });
    };
    const auto position_pointer = [&](uint32_t pointer) {
        const auto root = trace.roots.contains(pointer) ? trace.roots.at(pointer) : pointer;
        if (trace.builtins.contains(root) && trace.builtins.at(root) == spv::BuiltIn::Position) return true;
        if (!trace.access_indices.contains(pointer) || trace.access_indices.at(pointer).size() != 1 ||
                !trace.variable_types.contains(root) || !trace.pointer_types.contains(trace.variable_types.at(root))) return false;
        const auto member = trace.access_indices.at(pointer)[0];
        if (!trace.constants.contains(member)) return false;
        const auto key = std::make_pair(trace.pointer_types.at(trace.variable_types.at(root)), trace.constants.at(member));
        return trace.member_builtins.contains(key) && trace.member_builtins.at(key) == spv::BuiltIn::Position;
    };
    size_t valid_stores = 0; bool clipped_sentinel = false;
    for (const auto& store : trace.code) if (store.function == trace.entry && store.op == spv::Op::OpStore &&
            position_pointer(store.args[0])) {
        if (trace.composite_constants.contains(store.args[1])) {
            const auto& values = trace.composite_constants.at(store.args[1]);
            clipped_sentinel |= values.size() == 4 && trace.constant_is(values[0], 0x40000000u) &&
                trace.constant_is(values[1], 0x40000000u) && trace.constant_is(values[2], 0x40000000u) &&
                trace.constant_is(values[3], 0x3f800000u);
        }
        for (const auto& value : trace.code) if (value.function == trace.entry &&
                value.op == spv::Op::OpCompositeConstruct && value.args.size() == 6 && value.args[1] == store.args[1] &&
                trace.dominates(value, store) && ndc_component(value.args[2], 0) && negated_ndc_y(value.args[3]) &&
                trace.constant_is(value.args[4], 0x3f000000u) && trace.constant_is(value.args[5], 0x3f800000u)) ++valid_stores;
    }
    require(clipped_sentinel, "actual rejected vertex retains its outside-clip Position sentinel");
    require(valid_stores == 1, "actual valid Position stores ndc.x and negated ndc.y with z=0.5 and w=1, matching ordinary rendering");
}

void generated_fragment_coordinate_contract(const GeneratedLineConsumerArtifact& consumer) {
    Trace trace(consumer.fragment_spv);
    const auto pixel = trace.local_id(trace.entry, "pixel");
    const auto frag_coord_load = [&](uint32_t value) {
        if (!trace.loaded_from.contains(value)) return false;
        const auto root = trace.loaded_from.at(value);
        return trace.builtins.contains(root) && trace.builtins.at(root) == spv::BuiltIn::FragCoord;
    };
    const auto frag_coord_component = [&](uint32_t value, uint32_t component) {
        if (!frag_coord_load(value) || !trace.loaded_pointers.contains(value)) return false;
        const auto pointer = trace.loaded_pointers.at(value);
        return trace.access_indices.contains(pointer) && trace.access_indices.at(pointer).size() == 1 &&
            trace.constant_is(trace.access_indices.at(pointer)[0], component);
    };
    size_t direct_stores = 0;
    for (const auto& store : trace.code) if (store.function == trace.entry && store.op == spv::Op::OpStore &&
            store.args[0] == pixel) {
        for (const auto& value : trace.code) if (value.function == trace.entry && value.args.size() >= 2 &&
                value.args[1] == store.args[1] && trace.dominates(value, store)) {
            const bool direct_swizzle = value.op == spv::Op::OpVectorShuffle && value.args.size() == 6 &&
                frag_coord_load(value.args[2]) && value.args[2] == value.args[3] &&
                value.args[4] == 0 && value.args[5] == 1;
            const bool direct_components = value.op == spv::Op::OpCompositeConstruct && value.args.size() == 4 &&
                frag_coord_component(value.args[2], 0) && frag_coord_component(value.args[3], 1);
            direct_stores += direct_swizzle || direct_components;
        }
    }
    require(direct_stores == 1, "actual fragment pixel store uses BuiltIn FragCoord.xy directly, without H-y arithmetic");
}

void compiled_contract(const GeneratedLineConsumerArtifact& consumer, const LineEvaluatorArtifact& e) {
    require(consumer.ok, consumer.error);
    finite_bits_contract(consumer);
    generated_position_contract(consumer);
    generated_fragment_coordinate_contract(consumer);
    require(consumer.original == e.original && consumer.evaluator.get() == &e, "exact immutable allocation provenance");
    require(consumer.timings.parse_calls == 2 && consumer.timings.link_calls == 1 && consumer.timings.spirv_stages == 2,
            "real vertex+fragment parse/link/SPIR-V emission");
    require(consumer.vertex_rows.row_stride == e.output_row_bytes && consumer.fragment_rows.row_stride == e.output_row_bytes,
            "both actual storage reflections use original evaluator row bytes");
    require(consumer.uniform_stage_mask == 3 && consumer.vertex_storage_bindings == 1 && consumer.fragment_storage_bindings == 1,
            "render params and output storage are used in both stages");
    require(consumer.internal_inter_stage_locations == 1 && consumer.internal_inter_stage_components == 4,
            "one reflected flat uint32x4 interface");
    require(consumer.parameters_offset == e.original->uniform_bytes && consumer.uniform_bytes == e.original->uniform_bytes + 64,
            "mandatory reflected render params even with no original UBO");
    require(consumer.vertex_line_map.size() == static_cast<size_t>(std::count(consumer.vertex.begin(), consumer.vertex.end(), '\n')) &&
            consumer.fragment_line_map.size() == static_cast<size_t>(std::count(consumer.fragment.begin(), consumer.fragment.end(), '\n')),
            "generated source diagnostic maps are exact");
    require(consumer.requires_cull_none && consumer.requires_zero_polygon_bias, "generated polygon state requirements are explicit");
    Trace vertex(consumer.vertex_spv), fragment(consumer.fragment_spv);
    for (const auto& [id, text] : vertex.names) require(text.rfind("vispy_user_main", 0) != 0,
            "expansion SPIR-V contains no original vertex entry");
    const auto original_fragment = fragment.id("vispy_line_consumer_original_fragment", true);
    uint32_t fragment_depth = 0;
    for (const auto& [id, builtin] : fragment.builtins) if (builtin == spv::BuiltIn::FragDepth) fragment_depth = id;
    require(fragment_depth != 0, "real compiled fragment depth output exists");
    size_t original_calls = 0, depth_stores_in_user = 0, kills_in_user = 0;
    for (const auto& i : fragment.code) {
        if (i.op == spv::Op::OpFunctionCall && i.args[2] == original_fragment) ++original_calls;
        if (i.function == original_fragment && i.op == spv::Op::OpStore &&
            (fragment.roots.contains(i.args[0]) ? fragment.roots.at(i.args[0]) : i.args[0]) == fragment_depth) ++depth_stores_in_user;
        if (i.function == original_fragment && i.op == spv::Op::OpKill) ++kills_in_user;
    }
    require(original_calls == 1, "original fragment entry called exactly once in compiled module");
    require(depth_stores_in_user > 0 && kills_in_user > 0, "original body retains actual FragDepth writes and discard");
    const auto& call = fragment.entry_call(original_fragment);
    const auto& input = fragment.entry_store(fragment.id("color"));
    require(fragment.dominates(input, call), "typed reconstruction dominates original fragment call");
    size_t deferred_kills = 0;
    for (const auto& i : fragment.code) if (i.function == fragment.entry && i.op == spv::Op::OpKill && fragment.dominates(call, i))
        ++deferred_kills;
    require(deferred_kills == 1, "generated final coverage/validity kill follows original fragment call in real CFG");
    require(fragment.dominates(fragment.entry_store(fragment.id("vispy_line_consumer_covered")), call),
            "coverage is computed as a value before the unconditional original call");
    require(consumer.storage_bytes() > consumer.vertex_spv.size() * 4 + consumer.fragment_spv.size() * 4,
            "derived artifact counts owned metadata/source capacities");
}

void basic() {
    auto e = evaluator(); auto c = build_generated_line_consumer(e, policy(), grants()); diagnostics("basic", *c); compiled_contract(*c, *e);
    for (const auto* words : {&c->vertex_spv, &c->fragment_spv}) {
        Trace trace(*words);
        for (const auto& [id, builtin] : trace.builtins) require(builtin != spv::BuiltIn::HelperInvocation,
                "ordinary original introduces no unsupported native helper builtin");
        for (const auto& i : trace.code) require(i.op != spv::Op::OpIsHelperInvocationEXT && i.op != spv::Op::OpDemoteToHelperInvocationEXT,
                "ordinary original introduces no helper-query or demote extension opcode");
    }
    require(e->original->uniforms.size() == 1 && e->original->uniform_bytes == 16,
            "FragCoord original retains exactly one runtime depth-range uniform in a16-byte UBO");
    const auto& depth_range = e->original->uniforms.front();
    require(depth_range.name == "vispy_fragment_depth_range" && depth_range.type == "vec2" &&
            depth_range.storage_type == "vec2" && depth_range.offset == 0 && depth_range.size == 8 &&
            depth_range.array_size == 0 && depth_range.component_count == 2,
            "runtime depth-range uniform has exact reflected vec2 std140 metadata");
    require(c->uniforms.size() == 5 && c->uniforms.front().name == depth_range.name &&
            c->uniforms.front().type == depth_range.type && c->uniforms.front().offset == 0 &&
            c->uniforms.front().size == 8 && c->parameters_offset == 16 && c->uniform_bytes == 80,
            "generated consumer preserves runtime depth-range metadata before appended render params64");
    auto empty = evaluator(basic_vertex, "varying vec4 color; void main() { gl_FragColor = color; }");
    auto empty_consumer = build_generated_line_consumer(empty, policy(), grants());
    require(empty_consumer->ok, "actually empty semantic UBO consumer compiles: " + empty_consumer->error);
    require(empty->original->uniforms.empty() && empty->original->uniform_bytes == 16 &&
            empty_consumer->parameters_offset == 16 && empty_consumer->uniform_bytes == 80 &&
            empty_consumer->uniforms.size() == 4,
            "original empty-UBO case still retains reserved16 plus mandatory actual render params64");
    auto limits = grants(); limits.max_storage_buffers_per_stage = 0;
    auto rejected = build_generated_line_consumer(e, policy(), limits);
    require(!rejected->ok && rejected->timings.parse_calls == 0, "missing storage grant refuses before compiler");
    limits = grants(); limits.max_inter_stage_shader_variables = 0;
    require(!build_generated_line_consumer(e, policy(), limits)->ok, "missing actual interstage-variable grant refused");
    limits = grants(); limits.max_uniform_binding_bytes = 63;
    require(!build_generated_line_consumer(e, policy(), limits)->ok, "mandatory params UBO grant refused");
    auto p = policy(); p.coverage = LineCoveragePolicy::SmoothReference;
    require(!build_generated_line_consumer(e, p, grants())->ok, "unresolved smooth policy cannot become successful artifact");
    p = policy(); p.sample_count = 4;
    require(!build_generated_line_consumer(e, p, grants())->ok, "multisample coverage not silently substituted");
    p = policy(); p.coverage_identity += "-different";
    require(!build_generated_line_consumer(e, p, grants())->ok, "exact coverage identity refused");
    auto bad_metadata = std::make_shared<LineEvaluatorArtifact>(*e); bad_metadata->outputs[0].offset += 4;
    require(!build_generated_line_consumer(bad_metadata, policy(), grants())->ok, "corrupt typed row metadata refuses");
    std::string without_marker = c->fragment;
    const auto marker = without_marker.find("    vispy_line_consumer_initialize_globals();\n");
    require(marker != std::string::npos, "generated direct initializer marker exists");
    without_marker.erase(marker, std::string("    vispy_line_consumer_initialize_globals();\n").size());
    require(!compile_line_consumer_glsl(c->vertex, without_marker).stages.ok, "missing actual linked-AST marker refused");
    std::string duplicate = c->fragment;
    duplicate.insert(marker, "    vispy_line_consumer_initialize_globals();\n");
    require(!compile_line_consumer_glsl(c->vertex, duplicate).stages.ok, "duplicate actual linked-AST marker refused");

    require(c->policy_identity.rfind("vispy-generated-line-consumer-policy-v5;abi=2;", 0) == 0 &&
            c->policy_identity.find("finite=ieee754-signmask-unsigned-v1;product=topology-bounded-v1;") != std::string::npos &&
            c->policy_identity.find("coordinate=gl-window-present-y-v1;") != std::string::npos &&
            c->policy_identity.find("mapping=whole-or-local-chunk-original-primitive-v1;") != std::string::npos,
            "pre-generation identity records chunk mapping without changing ABI, coverage, product or finite policy");
    require(c->identity.rfind(c->policy_identity, 0) == 0 &&
            c->identity.find("consumer=typed-storage-both-stages-v2;") != std::string::npos &&
            c->cache_key == shader_identity_digest(c->identity), "artifact and cache digest retain the full revised policy");
    const std::string coordinate_marker = "coordinate=gl-window-present-y-v1;";
    const std::string mapping_marker = "mapping=whole-or-local-chunk-original-primitive-v1;";
    const auto artifact_policy_end = c->policy_identity.size();
    require(c->identity.find(coordinate_marker, artifact_policy_end) != std::string::npos,
            "artifact identity independently records the same coordinate convention as its policy");
    require(c->identity.find(mapping_marker, artifact_policy_end) != std::string::npos,
            "artifact identity independently records chunk mapping policy");
    std::string prior_v4_policy = c->policy_identity;
    prior_v4_policy.replace(0, std::string("vispy-generated-line-consumer-policy-v5;").size(), "vispy-generated-line-consumer-policy-v4;");
    prior_v4_policy.erase(prior_v4_policy.find(mapping_marker), mapping_marker.size());
    std::string prior_v4_artifact = c->identity;
    prior_v4_artifact.replace(0, c->policy_identity.size(), prior_v4_policy);
    prior_v4_artifact.erase(prior_v4_artifact.find(mapping_marker), mapping_marker.size());
    require(prior_v4_policy != c->policy_identity && shader_identity_digest(prior_v4_artifact) != c->cache_key,
            "whole-table-only consumers cannot reuse the local-chunk mapping cache key");
    std::string prior_v3_policy = c->policy_identity;
    prior_v3_policy.replace(0, std::string("vispy-generated-line-consumer-policy-v5;").size(), "vispy-generated-line-consumer-policy-v3;");
    const std::string prior_coordinate_marker = "coordinate=webgpu-viewport-y-v1;";
    prior_v3_policy.replace(prior_v3_policy.find(coordinate_marker), coordinate_marker.size(), prior_coordinate_marker);
    std::string prior_v3_artifact = c->identity;
    prior_v3_artifact.replace(0, c->policy_identity.size(), prior_v3_policy);
    prior_v3_artifact.replace(prior_v3_artifact.find(coordinate_marker), coordinate_marker.size(), prior_coordinate_marker);
    require(prior_v3_policy != c->policy_identity && shader_identity_digest(prior_v3_artifact) != c->cache_key,
            "prior-v3 pre-presentation-only coordinate convention cannot reuse the presented-coordinate cache key");
    std::string prior_policy = c->policy_identity;
    prior_policy.replace(0, std::string("vispy-generated-line-consumer-policy-v5;").size(), "vispy-generated-line-consumer-policy-v2;");
    prior_policy.erase(prior_policy.find(coordinate_marker), coordinate_marker.size());
    std::string prior_artifact = c->identity;
    prior_artifact.replace(0, c->policy_identity.size(), prior_policy);
    prior_artifact.erase(prior_artifact.find(coordinate_marker), coordinate_marker.size());
    require(prior_policy != c->policy_identity && shader_identity_digest(prior_artifact) != c->cache_key,
            "prior-v2 coordinate metadata cannot reuse the revised cache key even with identical shader text");
    std::string legacy_policy = c->policy_identity;
    legacy_policy.replace(0, std::string("vispy-generated-line-consumer-policy-v5;").size(), "vispy-generated-line-consumer-policy-v1;");
    const std::string product_marker = "product=topology-bounded-v1;";
    legacy_policy.erase(legacy_policy.find(product_marker), product_marker.size());
    legacy_policy.erase(legacy_policy.find(coordinate_marker), coordinate_marker.size());
    std::string legacy_artifact = c->identity;
    legacy_artifact.replace(0, c->policy_identity.size(), legacy_policy);
    legacy_artifact.erase(legacy_artifact.find(product_marker), product_marker.size());
    legacy_artifact.erase(legacy_artifact.find(coordinate_marker), coordinate_marker.size());
    require(legacy_policy != c->policy_identity && shader_identity_digest(legacy_artifact) != c->cache_key,
            "old arithmetic-policy metadata cannot reuse the new artifact cache key even with identical shader text");

    // Inspect actual operands and refusal paths in both compiled stages.
    for (const auto* words : {&c->vertex_spv, &c->fragment_spv}) {
        Trace trace(*words);
        const auto parameters = trace.id("vispy_line_consumer_parameters", true);
        const auto expected = trace.local_id(parameters, "expected_segments");
        const auto instances = trace.local_id(parameters, "instances");
        const auto total = trace.local_id(parameters, "total");
        const auto local_load = [&](uint32_t value, uint32_t variable) {
            return trace.loaded_from.contains(value) && trace.loaded_from.at(value) == variable;
        };
        const Instruction* division = nullptr; const Instruction* product = nullptr;
        size_t divisions = 0, products = 0;
        for (const auto& i : trace.code) if (i.function == parameters) {
            if (i.op == spv::Op::OpUDiv) {
                require(!(trace.constant_is(i.args[2], UINT32_MAX) && local_load(i.args[3], expected)),
                        "generated parameters do not divide UINT32_MAX by a dynamic segment count");
                if (trace.field_load(i.args[2], "vispy_line_consumer_header", 1) &&
                        trace.field_load(i.args[3], "vispy_line_consumer_ranges", 0)) { division = &i; ++divisions; }
            }
            if (i.op == spv::Op::OpIMul && local_load(i.args[2], instances) && local_load(i.args[3], expected))
                { product = &i; ++products; }
        }
        require(divisions == 1 && products == 1, "actual parameters compute row_count / rows_per_instance and instances * expected_segments");
        bool divided_into_instances = false, multiplied_into_total = false;
        for (const auto& i : trace.code) if (i.function == parameters && i.op == spv::Op::OpStore) {
            divided_into_instances |= i.args[0] == instances && i.args[1] == division->args[1];
            multiplied_into_total |= i.args[0] == total && i.args[1] == product->args[1];
        }
        require(divided_into_instances && multiplied_into_total && trace.dominates(*division, *product),
                "actual quotient and product feed the instances and total variables in order");
        bool denominator_guard = false, segment_guard = false;
        for (const auto& compare : trace.code) if (compare.function == parameters) {
            if (compare.op == spv::Op::OpULessThan &&
                    trace.field_load(compare.args[2], "vispy_line_consumer_ranges", 0) && trace.constant_is(compare.args[3], 2))
                denominator_guard |= trace.refusal_dominates(compare, *division);
            if (compare.op == spv::Op::OpIEqual &&
                    ((local_load(compare.args[2], expected) && trace.constant_is(compare.args[3], 0)) ||
                     (trace.constant_is(compare.args[2], 0) && local_load(compare.args[3], expected))))
                segment_guard |= trace.refusal_dominates(compare, *product);
        }
        require(denominator_guard, "actual X < 2 refusal dominates the row-count division through the compiled CFG");
        require(segment_guard, "actual zero-segment refusal dominates multiplication and the total store");
    }
}


void depth_attachment_specialization() {
    const std::string fragment = "varying vec4 color; void main() { gl_FragDepth = .25; gl_FragColor = vec4(color.rgb, gl_FragDepth * 4.0); }";
    for (const auto& source : {basic_fragment, fragment}) {
        auto e = evaluator(basic_vertex, source);
        auto attached = policy(); auto color_only = attached; color_only.depth_output = false;
        auto with_depth = build_generated_line_consumer(e, attached, grants());
        auto without_depth = build_generated_line_consumer(e, color_only, grants());
        require(with_depth->ok, "attached-depth generated consumer: " + with_depth->error);
        require(without_depth->ok, "color-only generated consumer: " + without_depth->error);
        require(with_depth->policy_identity != without_depth->policy_identity &&
            with_depth->identity != without_depth->identity && with_depth->cache_key != without_depth->cache_key,
            "actual depth output is part of complete CPU/module/pipeline identity");
        require(without_depth->fragment.find("gl_FragDepth") == std::string::npos &&
            without_depth->fragment.find("float vispy_line_consumer_fragment_depth;") != std::string::npos &&
            without_depth->fragment.find("vispy_line_consumer_fragment_depth = depth;") != std::string::npos,
            "color-only wrapper keeps depth computations in private storage");
        if (source == fragment) require(without_depth->fragment.find("vispy_line_consumer_fragment_depth = .25") != std::string::npos &&
            without_depth->fragment.find("vispy_line_consumer_fragment_depth * 4.0") != std::string::npos,
            "user depth assignment and following expression remain invocation-local computations");
        for (const auto& consumer : {with_depth, without_depth}) {
            bool depth_builtin = false, depth_replacing = false;
            for (size_t p = 5; p < consumer->fragment_spv.size();) {
                const auto& words = consumer->fragment_spv; const size_t count = words[p] >> 16;
                if (!count || count > words.size() - p) throw std::runtime_error("depth-specialization SPIR-V instruction bounds");
                const auto op = static_cast<spv::Op>(words[p] & 0xffffu);
                if (op == spv::Op::OpDecorate && count == 4 && words[p+2] == uint32_t(spv::Decoration::BuiltIn) &&
                    words[p+3] == uint32_t(spv::BuiltIn::FragDepth)) depth_builtin = true;
                if (op == spv::Op::OpExecutionMode && count >= 3 && words[p+2] == uint32_t(spv::ExecutionMode::DepthReplacing)) depth_replacing = true;
                p += count;
            }
            require(depth_builtin == consumer->policy.depth_output && depth_replacing == consumer->policy.depth_output,
                "compiled fragment depth interface agrees with captured attachment policy");
            require(consumer->fragment_line_map.size() == size_t(std::count(consumer->fragment.begin(), consumer->fragment.end(), '\n')),
                "depth specialization preserves composer diagnostic line mapping");
        }
    }
}

void bounded_product_arithmetic() {
    using vispy::lines::Mode;
    // Independent wide arithmetic covers all topologies, including values
    // where a uint32 product would wrap if its topology bound were lost.
    constexpr uint64_t maximum = std::numeric_limits<uint32_t>::max();
    std::set<uint64_t> rows_per_instance{2, 3, maximum - 1, maximum};
    for (unsigned bit = 1; bit < 32; ++bit) {
        const uint64_t power = uint64_t{1} << bit;
        rows_per_instance.insert(power); if (power > 2) rows_per_instance.insert(power - 1);
        rows_per_instance.insert(power + 1);
    }
    for (const auto x : rows_per_instance) for (const auto topology : {Mode::List, Mode::Strip, Mode::Loop}) {
        if (topology == Mode::List && x % 2) continue; // odd lists are refused by the topology contract
        const uint64_t e = topology == Mode::List ? x / 2 : topology == Mode::Strip ? x - 1 : x;
        require(1 <= e && e <= x, "every admitted topology has a positive segment count bounded by its row count");
        std::set<uint64_t> row_counts{0, 1, x - 1, x, maximum - 1, maximum};
        if (x < maximum) row_counts.insert(x + 1);
        const auto last_multiple = maximum / x * x;
        row_counts.insert(last_multiple); if (last_multiple) row_counts.insert(last_multiple - 1);
        if (last_multiple < maximum) row_counts.insert(last_multiple + 1);
        for (const auto y : row_counts) {
            const uint64_t q = y / x, wide_product = q * e;
            require(wide_product <= y && y <= maximum, "wide reference proves floor(Y/X) * E <= Y <= UINT32_MAX at quotient/remainder boundaries");
            const auto actual_product = static_cast<uint32_t>(q) * static_cast<uint32_t>(e);
            require(uint64_t{actual_product} == wide_product, "bounded uint32 product equals independent uint64 reference without wrap");
        }
    }
}

void viewport_coordinate_contract() {
    // Independent reference arithmetic, not a runtime API invocation. Both
    // rendering paths pass ordinary vy/sy; Dawn lowers a negative-height Vk
    // viewport, and the presentation shader subsequently samples 1-uv.y.
    const auto target_y = [](double gl_y, double viewport_y, double viewport_height,
                             double framebuffer_height, bool shader_negates_y, bool mirrored_viewport = false) {
        double ndc_y = (gl_y - viewport_y) / viewport_height * 2.0 - 1.0;
        if (shader_negates_y) ndc_y = -ndc_y;
        const double dawn_y = mirrored_viewport ? framebuffer_height - viewport_y - viewport_height : viewport_y;
        const double vk_y = dawn_y + viewport_height, vk_height = -viewport_height;
        return vk_y + (ndc_y + 1.0) * 0.5 * vk_height;
    };
    require(std::abs(target_y(6.5, 0, 24, 24, true) - 6.5) < 1e-12,
            "internal target and direct FragCoord retain GL window y=6.5");
    require(std::abs(24 - target_y(6.5, 0, 24, 24, true) - 17.5) < 1e-12,
            "presentation UV flip maps internal y=6.5 to the unchanged reference y=17.5");
    const double asymmetric_y = 11 + (1.0 - 0.75) * 29 * 0.5;
    require(std::abs(asymmetric_y - 14.625) < 1e-12 &&
            std::abs(target_y(asymmetric_y, 11, 29, 73, true) - 14.625) < 1e-12 &&
            std::abs(73 - target_y(asymmetric_y, 11, 29, 73, true) - 58.375) < 1e-12,
            "nonzero vy=11/vh=29/H=73 preserves physical14.625 and presented58.375");
    require(std::abs(target_y(asymmetric_y, 11, 29, 73, true, true) - 36.625) < 1e-12,
            "counterfactual consumer-only mirrored viewport produces the rejected36.625 row");
    for (const auto& viewport : {std::array<double, 5>{7, 9, 40, 24, 100},
                                 std::array<double, 5>{3, 17, 70, 30, 128}}) {
        const auto [vx, vy, width, height, framebuffer_height] = viewport;
        for (const double fraction : {0.125, 0.25, 0.75, 0.875}) {
            const double gl_y = vy + height * fraction, gl_x = vx + width * fraction;
            const double ndc_x = (gl_x - vx) / width * 2.0 - 1.0;
            require(std::abs(vx + (ndc_x + 1.0) * width * 0.5 - gl_x) < 1e-12,
                    "nonzero asymmetric viewport preserves GL window X");
            require(std::abs(target_y(gl_y, vy, height, framebuffer_height, true) - gl_y) < 1e-12,
                    "nonzero asymmetric viewport and direct FragCoord agree on internal GL window Y");
            require(std::abs(framebuffer_height - target_y(gl_y, vy, height, framebuffer_height, true) -
                    (framebuffer_height - gl_y)) < 1e-12,
                    "presentation maps asymmetric GL window Y to H-Y exactly once");
            require(std::abs(framebuffer_height - target_y(gl_y, vy, height, framebuffer_height, false) -
                    (framebuffer_height - gl_y)) > 1,
                    "counterfactual missing shader negation fails the presented asymmetric reference");
            require(std::abs(target_y(gl_y, vy, height, framebuffer_height, true, true) - gl_y) > 1,
                    "counterfactual consumer-only viewport mirror breaks the internal coverage coordinate");
        }
        const double sy = vy + 3, sh = height - 7;
        require(sy < sy + sh && framebuffer_height - (sy + sh) < framebuffer_height - sy,
                "ordinary scissor's internal half-open interval maps to the presented half-open interval");
        require(std::abs((framebuffer_height - sy - sh) - sy) > 1,
                "counterfactual consumer-only scissor mirror differs from the ordinary scissor origin");
        for (const double offset : {0.5, sh - 0.5}) {
            const double physical_y = sy + offset, presented_y = framebuffer_height - physical_y;
            require(physical_y >= sy && physical_y < sy + sh &&
                    presented_y > framebuffer_height - (sy + sh) && presented_y <= framebuffer_height - sy,
                    "interior scissor pixel centers remain inside the flipped presentation interval");
        }
    }
}

void fragment_contexts() {
    const std::string fragment = R"(
uniform sampler2D fragment_texture;
varying vec4 color;
bool initial_helper = gl_HelperInvocation;
void main() {
    gl_FragColor = texture2D(fragment_texture, color.xy) +
        vec4(dFdx(color.x), dFdy(color.y), fwidth(color.z),
            gl_HelperInvocation && initial_helper ? 0.0 : 1.0);
}
)";
    auto e = evaluator(basic_vertex, fragment);
    auto c = build_generated_line_consumer(e, policy(), grants()); diagnostics("fragment-contexts", *c); require(c->ok, c->error);
    finite_bits_contract(*c);
    Trace trace(c->fragment_spv);
    const auto original = trace.id("vispy_line_consumer_original_fragment", true);
    const auto& call = trace.entry_call(original);
    size_t derivatives = 0, implicit_samples = 0, after_call_kills = 0;
    for (const auto& i : trace.code) {
        if (i.function == original && i.op >= spv::Op::OpDPdx && i.op <= spv::Op::OpFwidthCoarse) ++derivatives;
        if (i.function == original && i.op == spv::Op::OpImageSampleImplicitLod) ++implicit_samples;
        if (i.function == trace.entry && i.op == spv::Op::OpKill && trace.dominates(call, i)) ++after_call_kills;
    }
    require(derivatives == 3 && implicit_samples == 1 && after_call_kills == 1,
            "actual implicit sample and three derivatives retained before generated coverage kill");
    const auto logical_helper = trace.id("vispy_line_consumer_helper_invocation");
    const auto& helper_store = trace.entry_store(logical_helper);
    require(trace.dominates(helper_store, trace.entry_store(trace.id("initial_helper"))) && trace.dominates(helper_store, call),
            "logical line helper value precedes original private initializer and fragment entry");
    size_t initial_native_loads = 0;
    for (const auto& i : trace.code) if (i.function == trace.entry && i.op == spv::Op::OpLoad) {
        const auto root = trace.loaded_from.at(i.args[1]);
        if (trace.builtins.contains(root) && trace.builtins.at(root) == spv::BuiltIn::HelperInvocation) {
            ++initial_native_loads;
            require(trace.dominates(i, helper_store), "actual requested native builtin read precedes logical helper snapshot");
        }
    }
    require(initial_native_loads == 1, "original builtin reads preserve exactly one generated native helper read");
    size_t user_logical_helper_loads = 0, user_native_helper_loads = 0;
    for (const auto& i : trace.code) if (i.function == original && i.op == spv::Op::OpLoad) {
        const auto root = trace.loaded_from.at(i.args[1]);
        user_logical_helper_loads += root == logical_helper;
        user_native_helper_loads += trace.builtins.contains(root) && trace.builtins.at(root) == spv::BuiltIn::HelperInvocation;
    }
    require(user_logical_helper_loads > 0 && user_native_helper_loads == 0,
            "compiled original helper reads use logical line coverage rather than conservative quad helper status");

    const std::string early = R"(
layout(early_fragment_tests) in;
varying vec4 color;
void main() { gl_FragColor = color; }
)";
    auto early_e = evaluator(basic_vertex, early);
    auto early_c = build_generated_line_consumer(early_e, policy(), grants());
    require(!early_c->ok && early_c->timings.parse_calls == 0 && early_c->error.find("early_fragment_tests") != std::string::npos,
            "real accepted original early-fragment-test module contextually refuses conservative coverage/depth");

    const std::string external = R"(
layout(std430, set = 0, binding = 9) buffer FragmentEffects { uint result; };
varying vec4 color;
void main() { result = uint(color.x); gl_FragColor = color; }
)";
    auto external_e = evaluator(basic_vertex, external);
    auto external_c = build_generated_line_consumer(external_e, policy(), grants());
    require(!external_c->ok && external_c->timings.parse_calls == 0 && external_c->error.find("external storage writes") != std::string::npos,
            "real original SSBO store refuses helper execution outside line coverage");
    const std::string atomic = R"(
layout(std430, set = 0, binding = 9) buffer FragmentEffects { uint result; };
varying vec4 color;
void main() { atomicAdd(result, 1u); gl_FragColor = color; }
)";
    auto atomic_e = evaluator(basic_vertex, atomic);
    auto atomic_c = build_generated_line_consumer(atomic_e, policy(), grants());
    require(!atomic_c->ok && atomic_c->timings.parse_calls == 0 && atomic_c->error.find("image/atomic/synchronization") != std::string::npos,
            "real original atomic write refuses helper execution outside line coverage");
    const std::string image = R"(
layout(rgba32f, set = 0, binding = 9) uniform image2D side_image;
varying vec4 color;
void main() { imageStore(side_image, ivec2(0), color); gl_FragColor = color; }
)";
    auto image_e = evaluator(basic_vertex, image);
    auto image_c = build_generated_line_consumer(image_e, policy(), grants());
    require(!image_c->ok && image_c->timings.parse_calls == 0 && image_c->error.find("image/atomic/synchronization") != std::string::npos,
            "real original image write refuses helper execution outside line coverage");
}

void dynamic_helper_queries() {
    const std::string fragment = R"(
#extension GL_EXT_demote_to_helper_invocation : require
varying vec4 color;
bool initial_query = helperInvocationEXT();
void main() {
    bool before = helperInvocationEXT();
    if (color.x < 0.0) demote;
    bool after = helperInvocationEXT();
    gl_FragColor = vec4(initial_query ? 1.0 : 0.0, before ? 1.0 : 0.0, after ? 1.0 : 0.0, color.w);
}
)";
    auto e = evaluator(basic_vertex, fragment);
    Trace original_trace(e->original->spv_frag);
    size_t original_native_queries = 0, original_demotes = 0;
    for (const auto& i : original_trace.code) {
        original_native_queries += i.op == spv::Op::OpIsHelperInvocationEXT;
        original_demotes += i.op == spv::Op::OpDemoteToHelperInvocationEXT;
    }
    require(original_native_queries == 3 && original_demotes == 1,
            "real accepted original emits initializer/before/after dynamic queries and demote");
    auto c = build_generated_line_consumer(e, policy(), grants());
    diagnostics("dynamic-helper-queries", *c); require(c->ok, c->error); finite_bits_contract(*c);
    Trace trace(c->fragment_spv);
    const auto user = trace.id("vispy_line_consumer_original_fragment", true);
    const auto wrapper = trace.id("vispy_line_consumer_query_helper", true);
    const auto logical = trace.id("vispy_line_consumer_helper_invocation");
    require(logical_dynamic_query(trace, wrapper, logical),
            "actual query wrapper combines current native query with logical line helper state");
    size_t native_queries = 0, user_queries = 0, user_demotes = 0;
    const Instruction* demote = nullptr;
    std::vector<const Instruction*> calls;
    for (const auto& i : trace.code) {
        if (i.op == spv::Op::OpIsHelperInvocationEXT) {
            ++native_queries; user_queries += i.function == user;
            require(i.function == wrapper, "all original dynamic queries are lowered through one logical/native wrapper");
        }
        if (i.function == user && i.op == spv::Op::OpDemoteToHelperInvocationEXT) { ++user_demotes; demote = &i; }
        if (i.function == user && i.op == spv::Op::OpFunctionCall && i.args[2] == wrapper) calls.push_back(&i);
    }
    require(native_queries == 1 && user_queries == 0 && user_demotes == 1 && calls.size() == 2,
            "native query is dynamic per call, original demote and two original query calls retained");
    for (const auto& [id, builtin] : trace.builtins) require(builtin != spv::BuiltIn::HelperInvocation,
            "query-only original does not acquire a startup native helper builtin");
    require(demote && calls[0]->offset < demote->offset && calls[1]->offset > demote->offset &&
            trace.reaches(calls[0]->block, demote->block) && trace.reaches(demote->block, calls[1]->block),
            "real original call -> conditional demote -> later dynamic query call CFG path preserved");
    const auto& helper_store = trace.entry_store(logical);
    const auto& initial_store = trace.entry_store(trace.id("initial_query"));
    const auto& user_call = trace.entry_call(user);
    size_t initial_calls = 0;
    for (const auto& i : trace.code) if (i.function == trace.entry && i.op == spv::Op::OpFunctionCall && i.args[2] == wrapper) {
        ++initial_calls;
        require(trace.dominates(helper_store, i) && trace.dominates(i, initial_store),
                "logical helper store precedes actual original query initializer call/store");
    }
    require(initial_calls == 1 && trace.dominates(initial_store, user_call),
            "one relocated dynamic initializer finishes before the original fragment entry");

    // A compiler-successful native-only wrapper is a real negative control:
    // its extension query is valid SPIR-V but does not represent logical line
    // helper pixels on the conservative quad.
    std::string native_only = c->fragment;
    const std::string correct = "return vispy_line_consumer_helper_invocation || helperInvocationEXT();";
    const auto at = native_only.find(correct);
    require(at != std::string::npos && native_only.find(correct, at + correct.size()) == std::string::npos,
            "exact generated dynamic-query counterfactual seam exists once");
    native_only.replace(at, correct.size(), "return helperInvocationEXT();");
    auto counterfactual = compile_line_consumer_glsl(c->vertex, native_only);
    diagnostic_bytes("native-only-query.frag.spv", counterfactual.stages.fragment.words.data(),
        counterfactual.stages.fragment.words.size() * sizeof(uint32_t));
    diagnostic_text("native-only-query.log.txt", counterfactual.stages.log);
    diagnostic_opcodes("native-only-query.frag", counterfactual.stages.fragment.words);
    require(counterfactual.stages.ok, "real native-only query counterfactual successfully compiles and validates");
    Trace wrong(counterfactual.stages.fragment.words);
    require(!logical_dynamic_query(wrong, wrong.id("vispy_line_consumer_query_helper", true),
            wrong.id("vispy_line_consumer_helper_invocation")),
            "actual SPIR-V data-flow control rejects valid native-only helper query semantics");
}

void initializer_order() {
    const std::string fragment = R"(
uniform float scale;
varying vec4 color;
float private_seed = color.x + scale;
float mutate_private() { private_seed += color.y; return private_seed; }
void main() {
    float result = mutate_private();
    if (result < -100.0) { gl_FragColor=vec4(result); return; }
    if (color.z < 0.0) discard;
    gl_FragColor = vec4(result, private_seed, color.z, color.w);
}
)";
    auto e = evaluator(basic_vertex, fragment); auto c = build_generated_line_consumer(e, policy(), grants());
    diagnostics("private-initializers", *c);
    require(c->ok, c->error); require(c->relocated_fragment_initializers > 0, "real original private initializer relocated");
    finite_bits_contract(*c);
    Trace trace(c->fragment_spv);
    const auto& input = trace.entry_store(trace.id("color"));
    const auto& initializer = trace.entry_store(trace.id("private_seed"));
    const auto& call = trace.entry_call(trace.id("vispy_line_consumer_original_fragment", true));
    require(trace.dominates(input, initializer) && trace.dominates(initializer, call),
            "input reconstruction -> original private initializer -> one fragment entry CFG dominance");
    auto counterfactual = compile_vulkan_glsl(c->vertex, c->fragment);
    diagnostic_bytes("default-initializers.vert.spv", counterfactual.vertex.words.data(), counterfactual.vertex.words.size() * sizeof(uint32_t));
    diagnostic_bytes("default-initializers.frag.spv", counterfactual.fragment.words.data(), counterfactual.fragment.words.size() * sizeof(uint32_t));
    diagnostic_text("default-initializers.log.txt", counterfactual.log);
    require(counterfactual.ok, "default compiler counterfactual really compiles");
    Trace default_trace(counterfactual.fragment.words);
    require(!default_trace.dominates(default_trace.entry_store(default_trace.id("color")),
            default_trace.entry_store(default_trace.id("private_seed"))),
            "counterfactual default initializer order is genuinely distinguished");
}

void multidimensional_varying_storage() {
    const std::string declarations = "varying mat2x3 matrices[2][2];flat varying int labels[2][2];";
    const std::string vertex = "attribute vec4 position;" + declarations +
        "void main(){gl_Position=position;for(int i=0;i<2;++i)for(int j=0;j<2;++j){"
        "matrices[i][j]=mat2x3(float(i*2+j));labels[i][j]=i*2+j+gl_VertexID;}}";
    const std::string fragment = declarations +
        "void main(){gl_FragColor=vec4(matrices[1][0][1][2]+float(labels[0][1]));}";
    auto e = evaluator(vertex,fragment); auto c = build_generated_line_consumer(e,policy(),grants());
    require(c->ok,c->error);
    require(e->outputs.size()==2 && e->outputs[0].varying.array_dimensions==std::vector<uint32_t>({2,2}),
        "endpoint retains logical multidimensional interface shape");
    require(c->fragment_rows.members[1].array_size==4 && c->fragment_rows.members[1].array_stride==32,
        "generated storage is four reflected matrix leaves, independent of logical rank");
    require(e->compute.find("matrices[(vispy_line_element / 2u) % 2u][(vispy_line_element) % 2u]")!=std::string::npos,
        "endpoint serializes every logical nested element into its flat storage leaf");
    require(c->fragment.find("matrices[(2 / 2u) % 2u][(2) % 2u]")!=std::string::npos,
        "fragment reconstructs nested private values before original code");
    auto broken=e->outputs;broken[0].varying.array_dimensions={3,2};
    bool rejected=false;
    try { validate_line_output_layout(e->output_row_bytes,broken); } catch(const std::exception&) { rejected=true; }
    require(rejected,"line layout rejects shape metadata that differs from reflected leaf count");
}

void typed_and_resources() {
    const std::string vertex = R"(
attribute vec4 position;
uniform mat3 uniform_matrix[2]; uniform bvec2 branches;
uniform sampler2D vertex_texture;
noperspective varying vec2 uv; flat varying ivec2 label; varying mat3 matrices[2];
void main() {
    gl_Position=position; uv=position.xy; label=ivec2(gl_VertexID,gl_InstanceID);
    matrices[0]=uniform_matrix[0]; matrices[1]=uniform_matrix[1];
    gl_Position.z += texture2D(vertex_texture, vec2(0.5)).x * 0.001;
}
)";
    const std::string fragment = R"(
uniform bvec2 branches; uniform sampler2D fragment_texture;
noperspective varying vec2 uv; flat varying ivec2 label; varying mat3 matrices[2];
void main() {
    if (label.x < 0) discard;
    gl_FragColor = texture2D(fragment_texture, uv) + vec4(matrices[0][0][0], matrices[1][2][1],
        branches.x ? float(label.y) : 0.0, gl_FrontFacing ? 1.0 : 0.0);
}
)";
    auto e = evaluator(vertex, fragment); auto c = build_generated_line_consumer(e, policy(), grants());
    diagnostics("typed-resources", *c);
    require(c->ok, c->error);
    finite_bits_contract(*c);
    require(c->vertex_rows.members.size() == 4 && c->fragment_rows.members.size() == 4, "actual typed scalar/vector/matrix-array row reflection");
    const auto& matrix = c->fragment_rows.members[3];
    require(matrix.array_size == 2 && matrix.matrix_stride == 16 && matrix.array_stride == 48 && matrix.size == 96,
            "real mat3[2] std430 matrix and array strides");
    require(c->samplers.size() == 1 && c->samplers[0].name == "fragment_texture" &&
            c->samplers[0].texture_stage_mask == 2 && c->samplers[0].sampler_stage_mask == 2,
            "actual fragment resource reflection excludes original vertex sampler");
    const auto named_uniform = [&](const std::vector<NormUniform>& uniforms, const std::string& name) -> const NormUniform& {
        require(std::count_if(uniforms.begin(), uniforms.end(), [&](const NormUniform& u) { return u.name == name; }) == 1,
                "exactly one original/consumer uniform named " + name);
        return *std::find_if(uniforms.begin(), uniforms.end(), [&](const NormUniform& u) { return u.name == name; });
    };
    const auto same_uniform = [](const NormUniform& a, const NormUniform& b) {
        return a.name == b.name && a.type == b.type && a.storage_type == b.storage_type &&
            a.offset == b.offset && a.size == b.size && a.array_size == b.array_size &&
            a.component_count == b.component_count && a.matrix_columns == b.matrix_columns &&
            a.matrix_rows == b.matrix_rows && a.matrix_stride == b.matrix_stride &&
            a.array_stride == b.array_stride && a.row_major == b.row_major;
    };
    const auto& original_branches = named_uniform(e->original->uniforms, "branches");
    const auto& consumer_branches = named_uniform(c->uniforms, "branches");
    require(original_branches.type == "bvec2" && original_branches.storage_type == "ivec2" &&
            original_branches.offset == 96 && original_branches.size == 8 && original_branches.array_size == 0 &&
            same_uniform(original_branches, consumer_branches),
            "named original bvec2/ivec2 std140 metadata is preserved exactly, distinct from uint output-row transport");
    const auto& original_matrix = named_uniform(e->original->uniforms, "uniform_matrix");
    const auto& consumer_matrix = named_uniform(c->uniforms, "uniform_matrix");
    require(original_matrix.type == "mat3" && original_matrix.storage_type == "mat3" &&
            original_matrix.offset == 0 && original_matrix.size == 96 && original_matrix.array_size == 2 &&
            original_matrix.component_count == 9 && original_matrix.matrix_columns == 3 && original_matrix.matrix_rows == 3 &&
            original_matrix.matrix_stride == 16 && original_matrix.array_stride == 48 && !original_matrix.row_major &&
            same_uniform(original_matrix, consumer_matrix),
            "named original mat3[2] std140 metadata is preserved exactly");
    require(c->uniforms.size() == e->original->uniforms.size() + 4 && e->original->uniform_bytes == 112 &&
            c->parameters_offset == e->original->uniform_bytes && c->uniform_bytes == e->original->uniform_bytes + 64,
            "original typed UBO retains mandatory appended render parameters64");
    Trace trace(c->fragment_spv);
    const auto& call = trace.entry_call(trace.id("vispy_line_consumer_original_fragment", true));
    for (const auto& field : e->outputs) require(trace.dominates(trace.entry_store(trace.id(field.varying.name)), call),
            "every typed private fragment input store dominates original entry");
    const auto list = c->fragment;
    require(list.find("vispy_line_consumer_screen_original") != std::string::npos &&
            list.find("vispy_line_consumer_rows[vispy_line_consumer_ids.z].varying_1") != std::string::npos,
            "noperspective parameter and original flat LAST source are retained");
}

// Execute the actual compiled integer segment-address function. Parameter
// validation is tested separately; its call is stubbed true here so this
// bounded interpreter needs no floating-point/raster implementation.
std::array<uint32_t, 4> compiled_segment(const std::vector<uint32_t>& words,
        const GeneratedLineConsumerParameters& parameters, uint32_t segment, bool& accepted) {
    Trace trace(words);
    const auto function = trace.id("vispy_line_consumer_segment", true);
    const auto validation = trace.id("vispy_line_consumer_parameters", true);
    struct Pointer { uint32_t root = 0; std::vector<uint32_t> path; };
    std::unordered_map<uint32_t, Pointer> pointers;
    std::unordered_map<uint32_t, std::vector<uint32_t>> values, memory;
    std::unordered_map<uint32_t, size_t> labels;
    std::vector<const Instruction*> instructions;
    constexpr uint32_t input_root = UINT32_MAX, output_root = UINT32_MAX - 1;
    memory[input_root] = {segment}; memory[output_root] = {0,0,0,0};
    size_t parameter = 0;
    for (const auto& i : trace.code) if (i.function == function) {
        if (i.op == spv::Op::OpLabel) labels[i.args[0]] = instructions.size();
        if (i.op == spv::Op::OpFunctionParameter) pointers[i.args[1]] = {parameter++ ? output_root : input_root, {}};
        instructions.push_back(&i);
    }
    require(parameter == 2, "compiled segment has exactly the original two pointer arguments");
    const auto value = [&](uint32_t id) -> std::vector<uint32_t> {
        if (values.contains(id)) return values.at(id);
        if (trace.constants.contains(id)) return {trace.constants.at(id)};
        if (trace.true_constants.contains(id)) return {1};
        if (trace.false_constants.contains(id)) return {0};
        if (trace.composite_constants.contains(id)) {
            std::vector<uint32_t> result;
            for (auto component : trace.composite_constants.at(id)) result.push_back(trace.constants.at(component));
            return result;
        }
        throw std::runtime_error("unsupported/missing compiled segment value " + std::to_string(id));
    };
    const auto scalar = [&](uint32_t id) { const auto v = value(id); require(v.size() == 1, "compiled scalar operand"); return v[0]; };
    const auto load = [&](const Pointer& p) -> std::vector<uint32_t> {
        if (memory.contains(p.root)) {
            const auto& v = memory.at(p.root);
            if (p.path.empty()) return v;
            require(p.path.size() == 1 && p.path[0] < v.size(), "compiled local vector component is bounded");
            return {v[p.path[0]]};
        }
        require(p.path.size() == 2 && p.path[1] < 4, "compiled generated UBO component is bounded");
        const auto structure = trace.pointer_types.at(trace.variable_types.at(p.root));
        const auto& member = trace.member_names.at({structure, p.path[0]});
        if (member == "vispy_line_consumer_header") return {parameters.header[p.path[1]]};
        if (member == "vispy_line_consumer_ranges") return {parameters.ranges[p.path[1]]};
        throw std::runtime_error("segment unexpectedly reads non-mapping UBO field");
    };
    uint32_t block = 0, previous_block = 0;
    size_t pc = 0;
    for (size_t steps = 0; steps < 4096 && pc < instructions.size(); ++steps) {
        const auto& i = *instructions[pc++]; const auto& a = i.args;
        switch (i.op) {
        case spv::Op::OpFunction: case spv::Op::OpFunctionParameter:
        case spv::Op::OpSelectionMerge: case spv::Op::OpFunctionEnd: break;
        case spv::Op::OpLabel: block = a[0]; break;
        case spv::Op::OpVariable: pointers[a[1]] = {a[1], {}}; break;
        case spv::Op::OpAccessChain: case spv::Op::OpInBoundsAccessChain: {
            auto p = pointers.contains(a[2]) ? pointers.at(a[2]) : Pointer{a[2], {}};
            for (size_t n = 3; n < a.size(); ++n) p.path.push_back(scalar(a[n]));
            pointers[a[1]] = std::move(p); break;
        }
        case spv::Op::OpLoad: values[a[1]] = load(pointers.at(a[2])); break;
        case spv::Op::OpStore: {
            const auto& p = pointers.at(a[0]); auto v = value(a[1]);
            if (p.path.empty()) memory[p.root] = std::move(v);
            else { require(p.path.size() == 1 && v.size() == 1 && p.path[0] < memory.at(p.root).size(), "bounded compiled component store");
                memory.at(p.root)[p.path[0]] = v[0]; }
            break;
        }
        case spv::Op::OpCopyObject: values[a[1]] = value(a[2]); break;
        case spv::Op::OpCompositeConstruct: {
            auto& out = values[a[1]];
            for (size_t n = 2; n < a.size(); ++n) { const auto v = value(a[n]); out.insert(out.end(),v.begin(),v.end()); }
            break;
        }
        case spv::Op::OpCompositeExtract: { const auto v = value(a[2]); require(a.size() == 4 && a[3] < v.size(), "bounded compiled extract"); values[a[1]] = {v[a[3]]}; break; }
        case spv::Op::OpIAdd: values[a[1]] = {scalar(a[2]) + scalar(a[3])}; break;
        case spv::Op::OpISub: values[a[1]] = {scalar(a[2]) - scalar(a[3])}; break;
        case spv::Op::OpIMul: values[a[1]] = {scalar(a[2]) * scalar(a[3])}; break;
        case spv::Op::OpUDiv: { const auto d = scalar(a[3]); require(d != 0, "compiled segment denominator is nonzero"); values[a[1]] = {scalar(a[2]) / d}; break; }
        case spv::Op::OpUMod: { const auto d = scalar(a[3]); require(d != 0, "compiled segment remainder divisor is nonzero"); values[a[1]] = {scalar(a[2]) % d}; break; }
        case spv::Op::OpBitwiseAnd: values[a[1]] = {scalar(a[2]) & scalar(a[3])}; break;
        case spv::Op::OpShiftRightLogical: values[a[1]] = {scalar(a[2]) >> scalar(a[3])}; break;
        case spv::Op::OpIEqual: case spv::Op::OpLogicalEqual: values[a[1]] = {uint32_t(scalar(a[2]) == scalar(a[3]))}; break;
        case spv::Op::OpINotEqual: case spv::Op::OpLogicalNotEqual: values[a[1]] = {uint32_t(scalar(a[2]) != scalar(a[3]))}; break;
        case spv::Op::OpULessThan: values[a[1]] = {uint32_t(scalar(a[2]) < scalar(a[3]))}; break;
        case spv::Op::OpUGreaterThan: values[a[1]] = {uint32_t(scalar(a[2]) > scalar(a[3]))}; break;
        case spv::Op::OpUGreaterThanEqual: values[a[1]] = {uint32_t(scalar(a[2]) >= scalar(a[3]))}; break;
        case spv::Op::OpLogicalAnd: values[a[1]] = {uint32_t(scalar(a[2]) && scalar(a[3]))}; break;
        case spv::Op::OpLogicalOr: values[a[1]] = {uint32_t(scalar(a[2]) || scalar(a[3]))}; break;
        case spv::Op::OpLogicalNot: values[a[1]] = {uint32_t(!scalar(a[2]))}; break;
        case spv::Op::OpSelect: values[a[1]] = value(scalar(a[2]) ? a[3] : a[4]); break;
        case spv::Op::OpPhi: {
            bool found = false;
            for (size_t n = 2; n + 1 < a.size(); n += 2) if (a[n + 1] == previous_block) { values[a[1]] = value(a[n]); found = true; break; }
            require(found, "compiled Phi has an incoming block"); break;
        }
        case spv::Op::OpBranch: previous_block = block; pc = labels.at(a[0]); break;
        case spv::Op::OpBranchConditional: previous_block = block; pc = labels.at(scalar(a[0]) ? a[1] : a[2]); break;
        case spv::Op::OpFunctionCall: require(a[2] == validation, "segment calls only parameter validation"); values[a[1]] = {1}; break;
        case spv::Op::OpReturnValue: {
            accepted = scalar(a[0]) != 0; const auto& ids = memory.at(output_root);
            return {ids[0],ids[1],ids[2],ids[3]};
        }
        default: throw std::runtime_error("unsupported actual segment opcode " + std::to_string(static_cast<uint32_t>(i.op)));
        }
    }
    throw std::runtime_error("compiled segment exceeded bounded instruction budget");
}

void chunk_mapping_contract() {
    auto e = evaluator(); auto c = build_generated_line_consumer(e, policy(), grants());
    require(c->ok, c->error); diagnostics("chunks", *c);
    using namespace vispy::lines;
    struct Case {
        uint32_t fresh, rows, segments; bool previous, closing, list; uint32_t first;
        std::vector<std::array<uint32_t,2>> endpoints;
    };
    const std::vector<Case> cases{
        {6,6,3,false,false,true,4000000001u,{{0,1},{2,3},{4,5}}},
        {4,4,3,false,false,false,0,{{0,1},{1,2},{2,3}}},
        {3,4,3,true,false,false,3,{{3,0},{0,1},{1,2}}},
        {3,4,3,false,true,false,0,{{0,1},{1,2},{2,3}}},
        {2,4,3,true,true,false,6,{{2,0},{0,1},{1,3}}},
        {0,2,1,true,true,false,UINT32_MAX,{{0,1}}},
        {2,2,1,false,false,true,UINT32_MAX,{{0,1}}},
    };
    for (const auto& item : cases) {
        const auto draw = plan_generated_line_consumer_chunk_draw(*c,item.fresh,item.rows,item.segments,
            item.previous,item.closing,item.list,item.first,state(3,false),{7,9,32,24},100,0.2,0.8,grants());
        require(draw.vertex_count == 6 && draw.instance_count == item.segments &&
                draw.endpoint_bytes == uint64_t(item.rows) * e->output_row_bytes && draw.render_uniform_bytes == c->uniform_bytes,
                "chunk draw charges local table including copied seam rows");
        require(draw.parameters.header == std::array<uint32_t,4>{2,item.rows,e->output_row_bytes,
                    3u + uint32_t(item.previous) + 2u*uint32_t(item.closing) + 4u*uint32_t(item.list)} &&
                draw.parameters.ranges == std::array<uint32_t,4>{item.fresh,item.first,0,item.segments},
                "64-byte paired chunk mapping stores original segment origin separately from local rows");
        require(draw.parameters.viewport == std::array<float,4>{7,9,32,24} &&
                draw.parameters.raster == std::array<float,4>{3,100,0.2f,0.8f}, "chunk retains GL-window and depth state");
        for (const auto* words : {&c->vertex_spv,&c->fragment_spv}) {
            for (uint32_t j = 0; j < item.segments; ++j) {
                bool accepted = false; const auto actual = compiled_segment(*words,draw.parameters,j,accepted);
                require(accepted && actual == std::array<uint32_t,4>{item.endpoints[j][0],item.endpoints[j][1],
                        item.endpoints[j][1],item.first+j}, "actual compiled chunk mapping preserves ordered endpoints, LAST and original PrimitiveID");
            }
            bool accepted = true; compiled_segment(*words,draw.parameters,item.segments,accepted);
            require(!accepted,"actual compiled mapping refuses a local segment at the exclusive end");
        }
    }
    // Ordinary ABI2 modes still address a complete instance-major output table.
    for (const auto primitive : {Mode::List,Mode::Strip,Mode::Loop}) {
        LineConsumerSelection selection(primitive,Selection{0,4,2});
        const auto draw = plan_generated_line_consumer_draw(*c,selection,{0,selection.segment_count()},state(3,false),{0,0,32,24},100,0,1,grants());
        for (uint32_t j = 0; j < selection.segment_count(); ++j) {
            const auto expected = selection.rows().segment_rows(j);
            for (const auto* words : {&c->vertex_spv,&c->fragment_spv}) {
                bool accepted = false; const auto actual = compiled_segment(*words,draw.parameters,j,accepted);
                require(accepted && actual == std::array<uint32_t,4>{expected.first,expected.last,expected.provoking,j},
                        "actual compiled whole-table mapping remains instance-major for list/strip/loop");
            }
        }
    }
    const auto plan = [&](uint32_t fresh,uint32_t rows,uint32_t segments,bool previous,bool closing,bool list,uint32_t first,
            LineConsumerLimits limits = grants(), State s = state(3,false), LineConsumerViewport viewport = {0,0,32,24}) {
        return plan_generated_line_consumer_chunk_draw(*c,fresh,rows,segments,previous,closing,list,first,s,viewport,100,0,1,limits);
    };
    const auto empty = plan(0,0,0,false,false,false,UINT32_MAX);
    require(!empty.vertex_count && !empty.instance_count && !empty.endpoint_bytes && !empty.render_uniform_bytes,
            "zero-segment chunk is a scalar no-op");
    const auto viewport_empty = plan(0,2,1,true,true,false,0,grants(),state(3,false),{0,0,0,24});
    require(!viewport_empty.instance_count && !viewport_empty.endpoint_bytes,"empty viewport skips copied-only closure draw");
    refusal([&]{plan(2,2,1,true,false,true,0);},"list refuses strip seam flags");
    refusal([&]{plan(1,2,1,true,true,false,0);},"closure shape cannot invent a new endpoint invocation");
    refusal([&]{plan(0,0,0,true,false,false,0);},"empty chunk cannot retain a seam flag");
    refusal([&]{plan(2,2,0,false,false,false,0);},"empty chunk cannot retain endpoint rows");
    refusal([&]{plan(3,3,2,false,false,true,0);},"list endpoint parity/segment shape refused");
    refusal([&]{plan(2,3,2,false,false,false,0);},"strip fresh row count must include initial endpoint");
    refusal([&]{plan(3,3,2,false,false,false,UINT32_MAX);},"original PrimitiveID addition cannot wrap");
    refusal([&]{plan(UINT32_MAX,UINT32_MAX,0x80000000u,false,false,false,0);},"chunk instance count exceeds signed shader builtin range");
    auto small = grants(); small.max_storage_binding_bytes = e->output_row_bytes;
    refusal([&]{plan(0,2,1,true,true,false,0,small);},"copied seam rows count toward output storage limit");
    auto exact = grants(); exact.max_storage_binding_bytes = 2u * e->output_row_bytes;
    require(plan(0,2,1,true,true,false,0,exact).instance_count == 1,"copied-only closure fits exact two-row output grant");
    exact.max_uniform_binding_bytes = c->uniform_bytes - 1;
    refusal([&]{plan(0,2,1,true,true,false,0,exact);},"chunk retains original reflected UBO limit checks");
    refusal([&]{plan(0,2,1,true,true,false,0,grants(),state(3,true));},"chunk does not enable unresolved smooth coverage");
    auto bad = *c; bad.policy.sample_count = 4;
    refusal([&]{plan_generated_line_consumer_chunk_draw(bad,0,2,1,true,true,false,0,state(3,false),{0,0,32,24},100,0,1,grants());},
            "chunk does not enable multisample coverage");
    for (const auto* words : {&c->vertex_spv,&c->fragment_spv}) {
        Trace trace(*words); const auto parameters = trace.id("vispy_line_consumer_parameters",true);
        bool mode_guard = false, count_guard = false;
        for (const auto& i : trace.code) if (i.function == parameters && i.op == spv::Op::OpUGreaterThan) {
            mode_guard |= trace.field_load(i.args[2],"vispy_line_consumer_header",3) && trace.constant_is(i.args[3],7);
            count_guard |= trace.field_load(i.args[2],"vispy_line_consumer_ranges",3) && trace.constant_is(i.args[3],INT32_MAX);
        }
        require(mode_guard && count_guard,"both compiled stages validate chunk mode and signed instance-count range");
        const auto addressed = trace.local_id(trace.entry,"addressed_segment");
        const auto segment_function = trace.id("vispy_line_consumer_segment",true);
        const auto& mapping_call = trace.entry_call(segment_function);
        bool local_feeds_mapping = false;
        for (const auto& i : trace.code) if (i.function == trace.entry && i.op == spv::Op::OpStore &&
                i.args[0] == mapping_call.args[3] && trace.loaded_from.contains(i.args[1]) &&
                trace.loaded_from.at(i.args[1]) == addressed && trace.dominates(i,mapping_call)) local_feeds_mapping = true;
        require(local_feeds_mapping,"both compiled entries pass the addressed local/global segment into tuple reconstruction");
        if (words == &c->fragment_spv) {
            const auto first = trace.local_id(trace.entry,"first_segment"), ids = trace.id("vispy_line_consumer_ids");
            bool rebased = false;
            for (const auto& i : trace.code) if (i.function == trace.entry && i.op == spv::Op::OpISub &&
                    trace.loaded_from.contains(i.args[2]) && trace.loaded_from.at(i.args[2]) == ids &&
                    trace.loaded_from.contains(i.args[3]) && trace.loaded_from.at(i.args[3]) == first &&
                    trace.reaches(i.block,mapping_call.block)) rebased = true;
            require(rebased,"actual fragment rebases original PrimitiveID before local endpoint tuple validation");
        }
    }
}

void plans_and_clip() {
    auto e = evaluator(); auto c = build_generated_line_consumer(e, policy(), grants()); diagnostics("plans", *c); require(c->ok, c->error);
    finite_bits_contract(*c);
    using namespace vispy::lines;
    const std::array<uint32_t, 3> indices{4000000001u, 7u, 4000000001u};
    const auto bytes = std::as_bytes(std::span(indices));
    Selection source{0, 3, 2}; source.indices = {reinterpret_cast<const uint8_t*>(bytes.data()), bytes.size()}; source.index_bytes = 4;
    LineConsumerSelection selection(Mode::Loop, source);
    auto draw = plan_generated_line_consumer_draw(*c, selection, {0, 6}, state(3, false), {7, 9, 32, 24}, 100, 0.2, 0.8, grants());
    require(draw.vertex_count == 6 && draw.instance_count == 6 && draw.parameters.header == std::array<uint32_t,4>{2,6,e->output_row_bytes,2},
            "actual ABI2 loop/instance-major range packed from one topology source");
    require(draw.parameters.ranges == std::array<uint32_t,4>{3,3,0,6} && draw.parameters.raster == std::array<float,4>{3,100,0.2f,0.8f},
            "GL viewport/depth/framebuffer parameters explicit");
    auto closing = selection.rows().segment_rows(5);
    require(closing.first == 5 && closing.last == 3 && closing.provoking == 3, "loop closure retains actual original LAST first vertex");
    auto empty = plan_generated_line_consumer_draw(*c, selection, {0,0}, state(3,false), {0,0,32,24},100,0,1,grants());
    require(empty.instance_count == 0 && empty.endpoint_bytes == 0, "zero selection is a true scalar plan no-op");
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,true),{0,0,32,24},100,0,1,grants());}, "smooth runtime plan refuses");
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{0,0,1e-300,24},100,0,1,grants());}, "positive float-underflow viewport refused");
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{0,0,1e-40,24},100,0,1,grants());}, "subnormal shader viewport extent refused");
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{0,0,32,24},1e-40,0,1,grants());}, "subnormal framebuffer extent refused");
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{1e300,0,32,24},100,0,1,grants());}, "out-of-float-range coordinate refused before conversion");
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{0,0,32,24},1e300,0,1,grants());}, "out-of-float-range framebuffer refused before conversion");
    auto rounded_zero = plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{1e-300,-1e-300,32,24},100,1e-300,1,grants());
    require(rounded_zero.instance_count == 6 && rounded_zero.parameters.viewport[0] == 0 && rounded_zero.parameters.viewport[1] == 0 &&
            rounded_zero.parameters.raster[2] == 0, "coordinates and depth may legitimately round to zero");
    LineConsumerSelection short_strip(Mode::Strip, Selection{0,1,1});
    auto no_segments = plan_generated_line_consumer_draw(*c,short_strip,{0,0},state(3,false),{0,0,32,24},100,0,1,grants());
    require(short_strip.size() == 0 && no_segments.instance_count == 0, "one-point strip remains empty without segment division");
    auto missing_interface = grants(); missing_interface.max_inter_stage_shader_variables = 0;
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{0,0,32,24},100,0,1,missing_interface);},
            "draw requires the actual interstage-variable grant");
    auto small = grants(); small.max_storage_binding_bytes = 1;
    refusal([&]{plan_generated_line_consumer_draw(*c,selection,{0,6},state(3,false),{0,0,32,24},100,0,1,small);}, "oversized output refuses pending partition implementation");
    const Position a{-2,0,0,1}, b{6,0,0,3};
    const auto clipped = clip_segment({}, a, b);
    require(clipped.geometry.status == ClipStatus::Visible && std::abs(clipped.geometry.begin - 0.1) < 1e-12 &&
            std::abs(clipped.geometry.end - 0.5) < 1e-12,
            "independent portable clip interval matches six-plane reference example");
    require(std::abs(screen_parameter(0.1,1,3) - 0.25) < 1e-12 && std::abs(screen_parameter(0.5,1,3) - 0.75) < 1e-12,
            "noperspective clip parameters are screen adjusted");
}

enum class DiamondArithmetic { ExactAffine, RoundedWindow, FusedAffine };
using CoveragePosition = std::array<float, 4>;
using CoveragePixel = std::array<double, 2>;
using Symbolic = std::array<double, 3>;

bool symbolic_less(const Symbolic& a, const Symbolic& b) {
    return a[0] < b[0] || (a[0] == b[0] &&
        (a[1] < b[1] || (a[1] == b[1] && a[2] < b[2])));
}

// Independent scalar model of the diamond half-planes. ExactAffine keeps the
// real affine projection of the original binary32 inputs; the two float modes
// distinguish premature window rounding from the emitted explicit FMA order.
double coverage_plane(const CoveragePosition& p, const CoveragePixel& n,
                      const CoveragePixel& center, DiamondArithmetic arithmetic) {
    const double offset = n[0] * (16.0 - center[0]) + n[1] * (12.0 - center[1]) - 0.5;
    if (arithmetic == DiamondArithmetic::ExactAffine)
        return n[0] * (double(p[0]) / p[3] * 16.0) +
               n[1] * (double(p[1]) / p[3] * 12.0) + offset;
    if (arithmetic == DiamondArithmetic::FusedAffine)
        return std::fma(float(n[1] * 12.0), p[1] / p[3],
               std::fma(float(n[0] * 16.0), p[0] / p[3], float(offset)));
    const float x = (p[0] / p[3] * 0.5f + 0.5f) * 32.0f;
    const float y = (p[1] / p[3] * 0.5f + 0.5f) * 24.0f;
    return float(float(n[0]) * float(x - float(center[0])) +
                 float(n[1]) * float(y - float(center[1])) - 0.5f);
}

bool coverage_diamond(const CoveragePosition& a, const CoveragePosition& b,
                      const CoveragePixel& center, bool original_terminal,
                      DiamondArithmetic arithmetic) {
    Symbolic lo{0, 0, 0}, hi{1, 0, 0};
    bool endpoint_inside = true;
    for (int i = 0; i < 4; ++i) {
        const CoveragePixel n{(i & 1) ? -1.0 : 1.0, (i & 2) ? -1.0 : 1.0};
        const Symbolic h0{coverage_plane(a, n, center, arithmetic), -n[0], -n[1]};
        const Symbolic h1{coverage_plane(b, n, center, arithmetic), -n[0], -n[1]};
        endpoint_inside = endpoint_inside && symbolic_less(h1, Symbolic{});
        const double d = arithmetic == DiamondArithmetic::ExactAffine ?
            h1[0] - h0[0] : double(float(h1[0] - h0[0]));
        if (d == 0) {
            if (!symbolic_less(h0, Symbolic{})) return false;
        } else {
            Symbolic crossing;
            for (size_t j = 0; j < crossing.size(); ++j)
                crossing[j] = arithmetic == DiamondArithmetic::ExactAffine ?
                    -h0[j] / d : double(float(-h0[j] / d));
            if (d > 0) { if (symbolic_less(crossing, hi)) hi = crossing; }
            else if (symbolic_less(lo, crossing)) lo = crossing;
        }
    }
    return (!endpoint_inside || !original_terminal) && symbolic_less(lo, hi);
}

bool coverage_three_rows(const CoveragePosition& a, const CoveragePosition& b,
                         const CoveragePixel& pixel, bool original_terminal,
                         DiamondArithmetic arithmetic) {
    // Exhaust the independently declared three major-axis replicas rather
    // than reproducing the shader's optimization selecting nearby replicas.
    for (int replica = 0; replica < 3; ++replica)
        if (coverage_diamond(a, b, {pixel[0], pixel[1] - (replica - 1)},
                             original_terminal, arithmetic)) return true;
    return false;
}

void aliased_projection_and_clipped_terminal() {
    const CoveragePosition a{-0.71875f, -0.625f, 0, 1};
    // Exact source binary32 from ((18.5f / 24.0f) * 2.0f - 1.0f).
    const CoveragePosition b{0.53125f, std::bit_cast<float>(uint32_t{0x3f0aaaaa}), 0, 1};
    const double exact_end_y = (double(b[1]) * 0.5 + 0.5) * 24;
    require(exact_end_y < 18.5 && float(exact_end_y) == 18.5f,
            "original binary32 diagonal has a strict residual erased by rounded window projection");
    require(4.5 + (exact_end_y - 4.5) * 0.25 < 8 &&
            4.5 + (exact_end_y - 4.5) * 0.75 < 15,
            "both diagonal boundary crossings are strictly below the mathematical integer ties");
    size_t exact_count = 0, fused_count = 0, old_differences = 0;
    for (int y = 0; y < 24; ++y) for (int x = 0; x < 32; ++x) {
        const CoveragePixel pixel{x + 0.5, y + 0.5};
        const bool exact = coverage_three_rows(a, b, pixel, true, DiamondArithmetic::ExactAffine);
        const bool fused = coverage_three_rows(a, b, pixel, true, DiamondArithmetic::FusedAffine);
        const bool old = coverage_three_rows(a, b, pixel, true, DiamondArithmetic::RoundedWindow);
        require(fused == exact, "explicit binary32 FMA planes preserve exact-input diagonal coverage");
        exact_count += exact; fused_count += fused; old_differences += old != exact;
    }
    require(exact_count == 60 && fused_count == exact_count && old_differences == 4,
            "old endpoint-rounding counterfactual changes exactly four diagonal coverage pixels");

    // The viewport clips the original [-16, 48] segment to [0, 32]. Only a
    // genuine original LAST inside a diamond suppresses that final fragment.
    const CoveragePosition left{-1, 0, 0, 1}, right{1, 0, 0, 1};
    require(!coverage_diamond(left, right, {31.5, 12}, true, DiamondArithmetic::FusedAffine) &&
             coverage_diamond(left, right, {31.5, 12}, false, DiamondArithmetic::FusedAffine),
            "synthetic right-clip endpoint includes the final intersected diamond while true LAST excludes it");
    require(!coverage_diamond(left, right, {32.5, 12}, false, DiamondArithmetic::FusedAffine) &&
            !coverage_diamond(left, right, {31.5, 13}, false, DiamondArithmetic::FusedAffine),
            "synthetic endpoint flag cannot admit diamonds outside the clipped segment intersection");
    require(coverage_diamond(right, left, {0.5, 12}, true, DiamondArithmetic::FusedAffine) &&
            coverage_diamond(right, left, {0.5, 12}, false, DiamondArithmetic::FusedAffine),
            "reversed left boundary exits the diamond under the unchanged symbolic negative-X shift");

    auto e = evaluator(); auto c = build_generated_line_consumer(e, policy(), grants());
    require(c->ok, "coverage-repair consumer compiles: " + c->error);
    Trace trace(c->fragment_spv);
    const auto plane = trace.id("vispy_line_consumer_diamond_plane", true);
    std::vector<const Instruction*> fused;
    for (const auto& instruction : trace.code)
        if (instruction.function == plane && instruction.op == spv::Op::OpExtInst &&
            instruction.args.size() == 7 && instruction.args[3] == GLSLstd450Fma)
            fused.push_back(&instruction);
    require(fused.size() == 2 && fused[1]->args[6] == fused[0]->args[1],
            "actual compiled diamond plane retains two explicitly nested FMA operations");
    require(trace.id("original_terminal") != 0 &&
            c->policy_identity.find(kAliasedLineCoverageIdentity) != std::string::npos,
            "compiled terminal predicate and pre-generation identity retain the revised coverage policy");
    auto prior = policy(); prior.coverage_identity =
        "gl46-14.5.1-14.5.2.2-symbolic-diamond-exit-major-axis-v1";
    require(generated_line_consumer_policy_identity(*e, prior) != c->policy_identity,
            "old rounded-plane/clipped-terminal policy cannot reuse the repaired CPU cache entry");
}
void analytic_smooth_contract() {
    namespace lines = vispy::lines;
    auto e = evaluator();
    auto p = policy(); p.coverage = LineCoveragePolicy::SmoothAnalytic;
    p.coverage_identity = kSmoothLineCoverageIdentity;
    auto c = build_generated_line_consumer(e, p, grants());
    require(c->ok, "analytic smooth consumer compiles: " + c->error);
    diagnostics("analytic-smooth", *c);
    Trace trace(c->fragment_spv);
    require(trace.id("vispy_line_consumer_smooth", true) != 0,
            "real fragment SPIR-V contains analytic coverage");
    require(c->fragment.find("vispy_out_color.a *= vispy_line_consumer_coverage;") >
            c->fragment.find("    vispy_line_consumer_original_fragment();"),
            "coverage modulates user alpha after the original fragment call");
    require(c->policy_identity != generated_line_consumer_policy_identity(*e, policy()),
            "smooth and aliased consumers cannot share a cache entry");
    const lines::LineConsumerSelection selection(lines::Mode::Strip, lines::Selection{0, 3, 1});
    for (double width : {0.25, 1.0, 1.5, 3.75}) {
        auto draw = plan_generated_line_consumer_draw(*c, selection, {0, 2}, lines::state(width, true),
            {0, 0, 32, 24}, 24, 0, 1, grants());
        require(draw.parameters.raster[0] == width && draw.instance_count == 2,
                "smooth widths remain fractional and use the existing topology");
        auto chunk = plan_generated_line_consumer_chunk_draw(*c, 2, 3, 2, true, false, false, 5,
            lines::state(width, true), {0, 0, 32, 24}, 24, 0, 1, grants());
        require(chunk.parameters.raster[0] == width && chunk.parameters.ranges[1] == 5,
                "smooth chunk preserves fractional width and original primitive identity");
    }
    refusal([&]{plan_generated_line_consumer_draw(*c, selection, {0, 2}, lines::state(1, false),
        {0, 0, 32, 24}, 24, 0, 1, grants());}, "aliased draws cannot reuse smooth artifacts");
    p.sample_count = 4;
    require(!build_generated_line_consumer(e, p, grants())->ok, "analytic policy does not silently enable MSAA");
    p.sample_count = 1; p.depth_output = false;
    auto named = evaluator(basic_vertex,
        "out vec4 result_color; void helper(out float x) { x = 0.5; } "
        "void main() { float x; helper(x); result_color = vec4(1, 0, 0, x); }");
    auto color_only = build_generated_line_consumer(named, p, grants());
    require(color_only->ok, "named smooth color-only output compiles: " + color_only->error);
    require(color_only->fragment.find("result_color.a *= vispy_line_consumer_coverage;") != std::string::npos,
            "coverage finds the named global output instead of out function parameters");
    auto rgb = evaluator(basic_vertex, "out vec3 result_color; void main() { result_color = vec3(1); }");
    require(!build_generated_line_consumer(rgb, p, grants())->ok,
            "output without alpha explicitly refuses smooth coverage");
}
// Positive multisample admission inspects emitted SPIR-V, not just policy flags.
void multisample_contract() {
    using namespace vispy::lines;
    auto e = evaluator();
    auto single = build_generated_line_consumer(e, policy(), grants());
    require(single->ok, single->error);
    for (bool smooth : {false, true}) {
        auto p = policy(); p.sample_count = 4;
        p.coverage = smooth ? LineCoveragePolicy::SmoothAnalytic : LineCoveragePolicy::AliasedMajorAxis;
        p.coverage_identity = line_coverage_identity(smooth, 4);
        auto c = build_generated_line_consumer(e, p, grants());
        diagnostics(smooth ? "multisample_smooth" : "multisample_aliased", *c);
        compiled_contract(*c, *e);
        require(c->policy_identity != single->policy_identity && c->cache_key != single->cache_key,
                "four-sample generated semantics have a distinct complete cache identity");
        Trace fragment(c->fragment_spv);
        const auto& call = fragment.entry_call(fragment.id("vispy_line_consumer_original_fragment", true));
        size_t sample_reads = 0, sample_mask_stores = 0;
        for (const auto& i : fragment.code) {
            if (i.function != fragment.entry) continue;
            if (i.op == spv::Op::OpLoad && fragment.loaded_from.contains(i.args[1])) {
                const auto root = fragment.loaded_from.at(i.args[1]);
                if (fragment.builtins.contains(root) && fragment.builtins.at(root) == spv::BuiltIn::SampleId) {
                    ++sample_reads; require(fragment.dominates(i, call), "native SampleId read precedes user execution");
                }
            }
            if (i.op == spv::Op::OpStore) {
                const auto root = fragment.roots.contains(i.args[0]) ? fragment.roots.at(i.args[0]) : i.args[0];
                if (fragment.builtins.contains(root) && fragment.builtins.at(root) == spv::BuiltIn::SampleMask) {
                    ++sample_mask_stores;
                    require(fragment.dominates(i, call), "native sample-mask initialization precedes user execution");
                }
            }
        }
        require(sample_reads > 0 && sample_mask_stores == 1,
                "real fragment consumes SampleId and writes its per-sample coverage mask");
        LineConsumerSelection selection(Mode::List, Selection{0, 2, 1});
        const auto draw = plan_generated_line_consumer_draw(*c, selection, {0, 1},
            state(3, smooth), {0, 0, 32, 24}, 24, 0, 1, grants());
        require(draw.vertex_count == 6 && draw.instance_count == 1,
                "four-sample draw planning positively retains one generated line quad");
        p.depth_output = false;
        auto color_only = build_generated_line_consumer(e, p, grants());
        require(color_only->ok, "four-sample color-only consumer compiles: " + color_only->error);
        Trace color_trace(color_only->fragment_spv);
        for (const auto& [id, builtin] : color_trace.builtins)
            require(builtin != spv::BuiltIn::FragDepth, "color-only multisampling has no actual depth output");
    }
    for (const std::string qualifier : {"sample", "centroid"}) {
        auto qualified = evaluator(
            "attribute vec4 position; " + qualifier + " out float value; void main(){gl_Position=position;value=float(gl_VertexID);}",
            qualifier + " in float value; void main(){gl_FragColor=vec4(value,0,0,1);}");
        auto p = policy(); p.sample_count = 4; p.coverage_identity = line_coverage_identity(false, 4);
        auto c = build_generated_line_consumer(qualified, p, grants());
        require(c->ok, "four-sample " + qualifier + " input compiles and reconstructs: " + c->error);
        require(c->fragment_rows.row_stride == qualified->output_row_bytes,
                "qualified multisample interpolation retains the exact typed endpoint layout");
    }
}

void captured_integer_endpoint_sampling() {
    for (const bool signed_texture : {false, true}) for (const bool gradients : {false, true}) {
        const std::string sampler = signed_texture ? "isampler2D" : "usampler2D";
        const std::string vector = signed_texture ? "ivec4" : "uvec4";
        const std::string vertex = "attribute vec2 position;uniform " + sampler + " image;out vec2 sampled;"
            "float counter=0.;float level(){counter+=1.;return 2.;}"
            "vec2 dx(){counter+=2.;return vec2(2.,0.);}vec2 dy(){counter+=3.;return vec2(0.,2.);}"
            "void main(){" + vector + " value=" + (gradients ? "textureGrad(image,vec2(.75,.25),dx(),dy())" :
                "textureLod(image,vec2(.75,.25),level())") + ";sampled=vec2(float(value.r),counter);gl_Position=vec4(position,0,1);}";
        auto original = build_portable_shader(vertex, "in vec2 sampled;void main(){gl_FragColor=vec4(sampled,0,1);}",
            {}, "integer-endpoint-captured-policy-contract");
        require(original->ok && original->integer_sample_uses.size() == 1, "compiled endpoint integer sample has semantic binding metadata");
        require(!build_line_evaluator(original)->ok, "generated endpoint must not invent a default sampler policy");
        const auto& use = original->integer_sample_uses.front();
        IntegerSamplePolicy actual;
        actual.texture_binding = use.texture_binding; actual.sampler_binding = use.sampler_binding; actual.scalar = use.scalar;
        actual.s = IntegerWrap::Repeat; actual.t = IntegerWrap::MirroredRepeat;
        const auto specialized = specialize_integer_sampled_shader(original, {actual});
        require(specialized->ok, "captured original sampling policy specializes: " + specialized->error);
        const auto endpoint = build_line_evaluator(specialized);
        require(endpoint->ok, "generated compute receives actual sampling policy: " + endpoint->error);
        require(endpoint->timings.integer_samples_lowered == 1 && endpoint->relocated_global_initializers >= 1,
            "one endpoint sample lowered after private initializer relocation");
        const auto remaining = integer_sample_bindings(endpoint->spv, 4);
        require(remaining.ok && remaining.bindings.empty(), "actual generated compute contains no unresolved integer samples");
        require(endpoint->samplers.size() == 1 && endpoint->samplers.front().texture_stage_mask == 4 &&
            endpoint->samplers.front().sampler_stage_mask == 0, "generated bind layout reflects fetch texture but no dead sampler");
        auto other = actual; other.s = IntegerWrap::ClampToEdge;
        const auto other_endpoint = build_line_evaluator(specialize_integer_sampled_shader(original, {other}));
        require(other_endpoint->ok && other_endpoint->identity != endpoint->identity,
            "generated endpoint caches include captured wrap policy");
        const auto consumer = build_generated_line_consumer(endpoint, policy(), grants());
        require(consumer->ok, "specialized endpoint retains a compatible ordinary generated consumer: " + consumer->error);
    }
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc > 2) throw std::runtime_error("at most one fresh diagnostics directory argument is accepted");
        if (argc == 2) {
            diagnostics_directory = argv[1];
            if (!std::filesystem::create_directory(diagnostics_directory)) throw std::runtime_error("diagnostics directory must be fresh");
        }
        basic(); depth_attachment_specialization(); bounded_product_arithmetic(); viewport_coordinate_contract(); initializer_order(); multidimensional_varying_storage(); typed_and_resources(); fragment_contexts(); dynamic_helper_queries(); plans_and_clip(); chunk_mapping_contract(); aliased_projection_and_clipped_terminal();
        analytic_smooth_contract(); multisample_contract(); captured_integer_endpoint_sampling();
        std::cout << "line consumer generated compiler contract: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
