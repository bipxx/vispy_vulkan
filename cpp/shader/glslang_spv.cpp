#include "shader/glslang_spv.hpp"

#include <glslang/Public/ResourceLimits.h>
#include <glslang/Public/ShaderLang.h>
#include <glslang/MachineIndependent/localintermediate.h>
#include <SPIRV/GlslangToSpv.h>
#include <SPIRV/spirv.hpp11>
#include <spirv-tools/libspirv.h>
#include <spirv-tools/optimizer.hpp>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <functional>
#include <mutex>
#include <map>
#include <limits>
#include <set>
#include <unordered_map>
#include <unordered_set>

std::string ordinary_stencil_replay_error(const std::vector<uint32_t>& vertex,
                                          const std::vector<uint32_t>& fragment) {
    auto stage = [](const std::vector<uint32_t>& words, bool vertex_stage) -> std::string {
        const std::string label = vertex_stage ? "vertex" : "fragment";
        if (words.size() < 5 || words[0] != spv::MagicNumber) return label + " final SPIR-V header differs";
        auto context = spvContextCreate(SPV_ENV_VULKAN_1_2);
        spv_const_binary_t binary{words.data(), words.size()};
        spv_diagnostic diagnostic = nullptr;
        const auto valid = spvValidate(context, &binary, &diagnostic);
        std::string validation = diagnostic && diagnostic->error ? diagnostic->error : "invalid final module";
        spvDiagnosticDestroy(diagnostic); spvContextDestroy(context);
        if (valid != SPV_SUCCESS) return label + " final SPIR-V validation: " + validation;
        std::unordered_map<uint32_t, spv::StorageClass> pointer_types, pointer_values;
        std::unordered_set<uint32_t> ordinary_ext_sets;
        // Validated instruction boundaries/types permit conservative result-type
        // propagation through ALL pointer-producing operations, including phi,
        // function parameters/calls and access-chain aliases.
        for (size_t p = 5; p < words.size(); p += words[p] >> 16) {
            const auto count = words[p] >> 16; const auto op = spv::Op(words[p] & 0xffffu); const auto* a = words.data() + p + 1;
            if (op == spv::Op::OpTypePointer) pointer_types.emplace(a[0], spv::StorageClass(a[1]));
            if (op == spv::Op::OpExtInstImport) {
                if (std::string(reinterpret_cast<const char*>(a + 1)) != "GLSL.std.450")
                    return label + " extended instruction set is outside ordinary replay admission";
                ordinary_ext_sets.insert(a[0]);
            }
            if (((op == spv::Op::OpDecorate && count >= 4 && a[1] == uint32_t(spv::Decoration::BuiltIn)) ||
                 (op == spv::Op::OpMemberDecorate && count >= 5 && a[2] == uint32_t(spv::Decoration::BuiltIn))) &&
                a[count - 2] == uint32_t(spv::BuiltIn::PrimitiveId))
                return label + " PrimitiveId requires an exact original primitive identity path";
        }
        struct PointerResults { const std::unordered_map<uint32_t, spv::StorageClass>* types; std::unordered_map<uint32_t, spv::StorageClass>* values; } data{&pointer_types, &pointer_values};
        auto collect = [](void* opaque, const spv_parsed_instruction_t* inst) -> spv_result_t {
            auto& d = *static_cast<PointerResults*>(opaque);
            if (inst->result_id && d.types->contains(inst->type_id)) d.values->emplace(inst->result_id, d.types->at(inst->type_id));
            return SPV_SUCCESS;
        };
        context = spvContextCreate(SPV_ENV_VULKAN_1_2); diagnostic = nullptr;
        const auto parsed = spvBinaryParse(context, &data, words.data(), words.size(), nullptr, collect, &diagnostic);
        spvDiagnosticDestroy(diagnostic); spvContextDestroy(context);
        if (parsed != SPV_SUCCESS) return label + " final SPIR-V pointer proof failed";
        uint32_t entries = 0;
        for (size_t p = 5; p < words.size(); p += words[p] >> 16) {
            const auto op = spv::Op(words[p] & 0xffffu); const auto* a = words.data() + p + 1;
            if (op == spv::Op::OpEntryPoint) {
                if (a[0] != uint32_t(vertex_stage ? spv::ExecutionModel::Vertex : spv::ExecutionModel::Fragment)) return label + " execution model differs";
                ++entries;
            }
            if (op == spv::Op::OpExtension) return label + " extension capability is outside ordinary replay admission";
            if (op == spv::Op::OpCapability) {
                const auto cap = spv::Capability(a[0]);
                if (cap != spv::Capability::Shader && cap != spv::Capability::Matrix && cap != spv::Capability::ImageQuery &&
                    cap != spv::Capability::DerivativeControl && cap != spv::Capability::Sampled1D && cap != spv::Capability::SampledCubeArray)
                    return label + " capability is outside ordinary replay admission";
            }
            if (op == spv::Op::OpExtInst) {
                if (!ordinary_ext_sets.contains(a[2])) return label + " unproven extended instruction set";
                // GLSL Modf/Frexp have writable pointer parameters. A hidden
                // external write is not necessarily an OpStore instruction.
                const auto operands = (words[p] >> 16) - 1;
                for (uint32_t operand = 4; operand < operands; ++operand) if (pointer_values.contains(a[operand])) {
                    const auto storage = pointer_values.at(a[operand]);
                    if (storage != spv::StorageClass::Output && storage != spv::StorageClass::Private && storage != spv::StorageClass::Function)
                        return label + " extended instruction external pointer is not replay-safe";
                }
            }
            if (op == spv::Op::OpStore || op == spv::Op::OpCopyMemory || op == spv::Op::OpCopyMemorySized) {
                if (!pointer_values.contains(a[0])) return label + " final store has no proven pointer storage";
                const auto storage = pointer_values.at(a[0]);
                if (storage != spv::StorageClass::Output && storage != spv::StorageClass::Private && storage != spv::StorageClass::Function)
                    return label + " external storage write is not replay-safe";
            }
            if (op == spv::Op::OpImageWrite || (op >= spv::Op::OpAtomicLoad && op <= spv::Op::OpAtomicXor) ||
                op == spv::Op::OpAtomicFlagTestAndSet || op == spv::Op::OpAtomicFlagClear ||
                op == spv::Op::OpAtomicFMinEXT || op == spv::Op::OpAtomicFMaxEXT || op == spv::Op::OpAtomicFAddEXT ||
                op == spv::Op::OpControlBarrier || op == spv::Op::OpMemoryBarrier ||
                op == spv::Op::OpBeginInvocationInterlockEXT || op == spv::Op::OpEndInvocationInterlockEXT || op == spv::Op::OpReadClockKHR)
                return label + " image/atomic/synchronization/clock effect is not replay-safe";
        }
        if (entries != 1) return label + " requires one exact final entry point";
        return {};
    };
    auto error = stage(vertex, true); if (error.empty()) error = stage(fragment, false);
    return error.empty() ? error : "DRAW stencil faces: " + error;
}

bool same_sampled_stage_io(const std::vector<uint32_t>& before,
                          const std::vector<uint32_t>& after, std::string& error) {
    using Words = std::vector<uint32_t>;
    using Signature = std::map<std::pair<uint32_t,uint32_t>,Words>;
    auto signature = [&](const Words& words, Signature& result) {
        struct Parsed {
            std::map<uint32_t,Words> definitions, references;
            std::set<uint32_t> variables;
            std::vector<Words> decorations, entries;
        } parsed;
        auto instruction = [](void* data,const spv_parsed_instruction_t* inst)->spv_result_t {
            auto& p=*static_cast<Parsed*>(data);
            const auto* w=inst->words;
            const auto op=spv::Op(inst->opcode);
            if(inst->result_id) {
                p.definitions[inst->result_id]={w,w+inst->num_words};
                for(uint16_t n=0;n<inst->num_operands;++n) {
                    const auto& operand=inst->operands[n];
                    if(operand.type==SPV_OPERAND_TYPE_ID || operand.type==SPV_OPERAND_TYPE_TYPE_ID)
                        p.references[inst->result_id].push_back(w[operand.offset]);
                }
            }
            if(op==spv::Op::OpVariable && (w[3]==uint32_t(spv::StorageClass::Input) || w[3]==uint32_t(spv::StorageClass::Output)))
                p.variables.insert(inst->result_id);
            if(op==spv::Op::OpDecorate || op==spv::Op::OpMemberDecorate || op==spv::Op::OpDecorateId ||
               op==spv::Op::OpDecorationGroup || op==spv::Op::OpGroupDecorate || op==spv::Op::OpGroupMemberDecorate)
                p.decorations.emplace_back(w,w+inst->num_words);
            if(op==spv::Op::OpEntryPoint) p.entries.emplace_back(w,w+inst->num_words);
            return SPV_SUCCESS;
        };
        auto context=spvContextCreate(SPV_ENV_VULKAN_1_2);
        spv_diagnostic diagnostic=nullptr;
        const auto status=spvBinaryParse(context,&parsed,words.data(),words.size(),nullptr,instruction,&diagnostic);
        if(status!=SPV_SUCCESS) error=diagnostic&&diagnostic->error?diagnostic->error:"SPIR-V IO parse failed";
        spvDiagnosticDestroy(diagnostic);spvContextDestroy(context);
        if(status!=SPV_SUCCESS)return false;
        std::set<uint32_t> closure;
        Words pending(parsed.variables.begin(),parsed.variables.end());
        while(!pending.empty()) {
            const auto id=pending.back();pending.pop_back();
            if(!closure.insert(id).second)continue;
            const auto found=parsed.definitions.find(id);
            if(found==parsed.definitions.end()){error="SPIR-V IO definition missing";return false;}
            result[{0,id}]=found->second;
            const auto& refs=parsed.references[id];pending.insert(pending.end(),refs.begin(),refs.end());
        }
        std::vector<Words> decorations;
        for(const auto& decoration:parsed.decorations) {
            const auto op=spv::Op(decoration[0]&0xffffu);
            if(op==spv::Op::OpDecorationGroup || op==spv::Op::OpGroupDecorate || op==spv::Op::OpGroupMemberDecorate || closure.contains(decoration[1]))
                decorations.push_back(decoration);
        }
        std::sort(decorations.begin(),decorations.end());
        for(uint32_t n=0;n<decorations.size();++n)result[{1,n}]=std::move(decorations[n]);
        for(uint32_t n=0;n<parsed.entries.size();++n) {
            const auto& entry=parsed.entries[n];
            size_t first_interface=3;
            while(first_interface<entry.size()) {
                const uint32_t word=entry[first_interface++];
                if(!(word&0xffu)||!(word&0xff00u)||!(word&0xff0000u)||!(word&0xff000000u))break;
            }
            // Word count can change when a non-IO resource is removed. The
            // execution model/function/name and ordered IO references cannot.
            Words retained(entry.begin()+1,entry.begin()+first_interface);
            for(size_t at=first_interface;at<entry.size();++at)
                if(parsed.variables.contains(entry[at]))retained.push_back(entry[at]);
            result[{2,n}]=std::move(retained);
        }
        return true;
    };
    Signature a,b;
    if(!signature(before,a)||!signature(after,b))return false;
    if(a!=b){error="sampled-stage finalization changed the retained shader IO interface";return false;}
    error.clear();return true;
}

SpvSampledStage finalize_sampled_stage(const std::vector<uint32_t>& input, uint32_t stage_mask) {
    SpvSampledStage out;
    if (stage_mask != 1 && stage_mask != 2 && stage_mask != 4) {
        out.error = "sampled-stage finalization: invalid stage"; return out;
    }
    spvtools::Optimizer optimizer(SPV_ENV_VULKAN_1_2);
    optimizer.SetMessageConsumer([&](spv_message_level_t, const char*, const spv_position_t&, const char* text) {
        out.error += text; out.error += '\n';
    });
    optimizer.RegisterPass(spvtools::CreateEliminateDeadFunctionsPass());
    optimizer.RegisterPass(spvtools::CreateAggressiveDCEPass(true));
    optimizer.RegisterPass(spvtools::CreateDeadVariableEliminationPass());
    if (!optimizer.Run(input.data(), input.size(), &out.words)) return out;
    if (!same_sampled_stage_io(input, out.words, out.error)) { out.words.clear(); return out; }
    struct Uses {
        uint32_t function = 0;
        std::set<uint32_t> entries;
        std::map<uint32_t, std::set<uint32_t>> references, calls;
        std::map<uint32_t, uint32_t> bindings, sets;
        std::set<uint32_t> globals;
    } uses;
    auto parse = [](void* data, const spv_parsed_instruction_t* inst) -> spv_result_t {
        auto& uses = *static_cast<Uses*>(data);
        const auto* w = inst->words;
        const auto op = spv::Op(inst->opcode);
        if (op == spv::Op::OpEntryPoint) uses.entries.insert(w[2]);
        if (op == spv::Op::OpDecorate && inst->num_words == 4) {
            if (w[2] == uint32_t(spv::Decoration::Binding)) uses.bindings[w[1]] = w[3];
            if (w[2] == uint32_t(spv::Decoration::DescriptorSet)) uses.sets[w[1]] = w[3];
        }
        if (op == spv::Op::OpFunction) uses.function = inst->result_id;
        else if (op == spv::Op::OpFunctionEnd) uses.function = 0;
        else if (uses.function) {
            for (uint16_t n = 0; n < inst->num_operands; ++n) {
                const auto& operand = inst->operands[n];
                if (operand.type == SPV_OPERAND_TYPE_ID)
                    uses.references[uses.function].insert(w[operand.offset]);
            }
            if (op == spv::Op::OpFunctionCall) uses.calls[uses.function].insert(w[3]);
        } else if (op == spv::Op::OpVariable) uses.globals.insert(inst->result_id);
        return SPV_SUCCESS;
    };
    auto context = spvContextCreate(SPV_ENV_VULKAN_1_2);
    spv_diagnostic diagnostic = nullptr;
    const auto status = spvBinaryParse(context, &uses, out.words.data(), out.words.size(), nullptr, parse, &diagnostic);
    if (status != SPV_SUCCESS) out.error = diagnostic && diagnostic->error ? diagnostic->error : "SPIR-V resource parse failed";
    spvDiagnosticDestroy(diagnostic);
    if (status == SPV_SUCCESS) {
        spv_const_binary_t binary{out.words.data(), out.words.size()};
        diagnostic = nullptr;
        if (spvValidate(context, &binary, &diagnostic) != SPV_SUCCESS)
            out.error = diagnostic && diagnostic->error ? diagnostic->error : "SPIR-V cleanup validation failed";
        spvDiagnosticDestroy(diagnostic);
    }
    spvContextDestroy(context);
    if (!out.error.empty()) { out.words.clear(); return out; }
    std::set<uint32_t> reached, referenced;
    std::vector<uint32_t> pending(uses.entries.begin(), uses.entries.end());
    while (!pending.empty()) {
        const auto f = pending.back(); pending.pop_back();
        if (!reached.insert(f).second) continue;
        referenced.insert(uses.references[f].begin(), uses.references[f].end());
        pending.insert(pending.end(), uses.calls[f].begin(), uses.calls[f].end());
    }
    std::set<uint32_t> live_bindings;
    for (auto variable : uses.globals) if (referenced.contains(variable) && uses.bindings.contains(variable)) {
        if (!uses.sets.contains(variable) || uses.sets[variable] != 0) {
            out.words.clear(); out.error = "sampled-stage live resource must use descriptor set zero"; return out;
        }
        if (!live_bindings.insert(uses.bindings[variable]).second) {
            out.words.clear(); out.error = "sampled-stage duplicate live binding"; return out;
        }
        out.resource_usage.push_back({uses.bindings[variable], stage_mask});
    }
    std::sort(out.resource_usage.begin(), out.resource_usage.end(), [](const auto& a, const auto& b) { return a.binding < b.binding; });
    out.ok = true; return out;
}

namespace {

uint64_t host_ns() {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}

void ensure_process() {
    static std::once_flag initialized;
    std::call_once(initialized, [] { glslang::InitializeProcess(); });
}

bool parse_shader(glslang::TShader& shader, EShLanguage stage, const std::string& source,
                  std::string& log) {
    const char* src = source.c_str();
    shader.setStrings(&src, 1);
    shader.setEnvInput(glslang::EShSourceGlsl, stage, glslang::EShClientVulkan, 100);
    shader.setEnvClient(glslang::EShClientVulkan, glslang::EShTargetVulkan_1_2);
    shader.setEnvTarget(glslang::EShTargetSpv, glslang::EShTargetSpv_1_3);
    shader.setEntryPoint("main");
    shader.setSourceEntryPoint("main");
    const auto messages = static_cast<EShMessages>(EShMsgSpvRules | EShMsgVulkanRules);
    const bool parsed = shader.parse(GetDefaultResources(), 450, false, messages);
    log += shader.getInfoLog();
    log += shader.getInfoDebugLog();
    return parsed;
}

bool opaque_function_interfaces(const std::vector<uint32_t>& words) {
    std::unordered_set<uint32_t> opaque;
    bool changed;
    do {
        changed = false;
        for (size_t position = 5; position < words.size();) {
            const size_t count = words[position] >> 16;
            if (!count || count > words.size() - position) return true;
            const auto opcode = static_cast<spv::Op>(words[position] & 0xffffu);
            bool is_opaque = opcode == spv::Op::OpTypeImage || opcode == spv::Op::OpTypeSampler ||
                             opcode == spv::Op::OpTypeSampledImage;
            if (opcode == spv::Op::OpTypePointer && count >= 4) is_opaque = opaque.contains(words[position + 3]);
            else if ((opcode == spv::Op::OpTypeArray || opcode == spv::Op::OpTypeRuntimeArray) && count >= 3)
                is_opaque = opaque.contains(words[position + 2]);
            else if (opcode == spv::Op::OpTypeStruct)
                for (size_t member = 2; member < count; ++member) is_opaque |= opaque.contains(words[position + member]);
            if (is_opaque && count >= 2) changed |= opaque.insert(words[position + 1]).second;
            position += count;
        }
    } while (changed);
    for (size_t position = 5; position < words.size();) {
        const size_t count = words[position] >> 16;
        const auto opcode = static_cast<spv::Op>(words[position] & 0xffffu);
        if ((opcode == spv::Op::OpFunctionParameter || opcode == spv::Op::OpFunction) &&
            count >= 2 && opaque.contains(words[position + 1])) return true;
        position += count;
    }
    return false;
}

bool validate_spv(const std::vector<uint32_t>& words, std::string& log) {
    spv_context context = spvContextCreate(SPV_ENV_VULKAN_1_2);
    spv_diagnostic diagnostic = nullptr;
    spv_const_binary_t binary{words.data(), words.size()};
    const spv_result_t status = spvValidate(context, &binary, &diagnostic);
    if (status != SPV_SUCCESS) {
        log += "SPIR-V validation: ";
        log += diagnostic && diagnostic->error ? diagnostic->error : "validation failed";
        log += '\n';
    }
    spvDiagnosticDestroy(diagnostic);
    spvContextDestroy(context);
    return status == SPV_SUCCESS;
}

void emit_spv(glslang::TProgram& program, EShLanguage stage, SpvStage& out) {
    glslang::TIntermediate* ir = program.getIntermediate(stage);
    if (ir == nullptr) {
        out.ok = false;
        out.log += "glslang produced no intermediate for this stage";
        return;
    }
    glslang::SpvOptions options;
    options.validate = true;
    options.disableOptimizer = true;
    options.generateDebugInfo = false;
    spv::SpvBuildLogger logger;
    glslang::GlslangToSpv(*ir, out.words, &logger, &options);
    const std::string messages = logger.getAllMessages();
    out.log += messages;
    out.ok = !out.words.empty() && out.words[0] == 0x07230203u;
    if (messages.find("error:") != std::string::npos || messages.find("Missing functionality:") != std::string::npos ||
        messages.find("TBD functionality:") != std::string::npos) out.ok = false;
    if (!out.ok) {
        out.log += "GlslangToSpv did not produce SPIR-V";
        return;
    }
    // The vendored glslang is built without its optimizer, which also compiles
    // out SpvOptions::validate. Validate independently with Dawn's pinned tool.
    out.ok = validate_spv(out.words, out.log);
    if (!out.ok || !opaque_function_interfaces(out.words)) return;
    // Pinned Tint's texture lowering forks functions to convert opaque
    // parameters. Nested Text helpers can leave its raw-pointer worklists
    // referring to destroyed functions and crash ReadIR. Inline only calls
    // with image/sampler interfaces, then remove their unreferenced originals.
    // Merge early returns as required by the pinned inliner. Numeric functions
    // remain functions; resource bindings and sampling instructions keep their
    // semantics under the pinned SPIR-V compiler and validator.
    spvtools::Optimizer optimizer(SPV_ENV_VULKAN_1_2);
    optimizer.SetMessageConsumer([&](spv_message_level_t, const char*, const spv_position_t& position, const char* message) {
        out.log += "SPIR-V opaque helper lowering at instruction " + std::to_string(position.index) + ": " + message + '\n';
    });
    optimizer.RegisterPass(spvtools::CreateMergeReturnPass());
    optimizer.RegisterPass(spvtools::CreateInlineOpaquePass());
    optimizer.RegisterPass(spvtools::CreateEliminateDeadFunctionsPass());
    std::vector<uint32_t> lowered;
    if (!optimizer.Run(out.words.data(), out.words.size(), &lowered)) {
        out.ok = false;
        out.log += "SPIR-V opaque helper lowering failed\n";
        return;
    }
    if (!validate_spv(lowered, out.log) || opaque_function_interfaces(lowered)) {
        out.ok = false;
        out.log += "SPIR-V opaque helper lowering left unsupported function interfaces\n";
        return;
    }
    out.words = std::move(lowered);
}

bool relocate_endpoint_initializers(glslang::TIntermediate* intermediate, uint64_t& relocated,
                                   std::string& log) {
    auto fail = [&](const std::string& detail) {
        log += "endpoint initializer policy: unexpected pinned glslang tree (" + detail + ")\n";
        return false;
    };
    auto* root = intermediate && intermediate->getTreeRoot() ? intermediate->getTreeRoot()->getAsAggregate() : nullptr;
    if (!root || root->getOp() != glslang::EOpSequence) return fail("missing global sequence");
    auto& globals = root->getSequence();
    glslang::TIntermAggregate* entry = nullptr;
    std::vector<TIntermNode*> initializers;
    for (auto* node : globals) {
        auto* aggregate = node->getAsAggregate();
        if (!aggregate) return fail("non-aggregate global node");
        if (aggregate->getOp() == glslang::EOpFunction) {
            if (aggregate->getName().compare(intermediate->getEntryPointMangledName().c_str()) == 0) {
                if (entry) return fail("multiple entry functions");
                entry = aggregate;
            }
        } else if (aggregate->getOp() != glslang::EOpLinkerObjects) {
            // Match pinned GlslangToSpv::makeGlobalInitializers exactly: every
            // root aggregate other than a function/linker object is an
            // initializer. Keep the original nodes, order and source locations.
            initializers.push_back(node);
        }
    }
    if (!entry || entry->getSequence().size() != 2) return fail("entry parameters/body shape");
    auto* parameters = entry->getSequence()[0]->getAsAggregate();
    auto* body = entry->getSequence()[1]->getAsAggregate();
    if (!parameters || parameters->getOp() != glslang::EOpParameters || !parameters->getSequence().empty() ||
        !body || (body->getOp() != glslang::EOpSequence && body->getOp() != glslang::EOpScope))
        return fail("entry is not a parameterless statement sequence");
    auto& statements = body->getSequence();
    size_t marker = statements.size();
    for (size_t n = 0; n < statements.size(); ++n) {
        auto* call = statements[n]->getAsAggregate();
        if (!call || call->getOp() != glslang::EOpFunctionCall || call->getName() != "vispy_line_initialize_globals(") continue;
        if (marker != statements.size() || !call->getSequence().empty() || call->getBasicType() != glslang::EbtVoid)
            return fail("duplicate or malformed initializer marker");
        marker = n;
    }
    if (marker == statements.size()) return fail("missing direct generated initializer marker");
    // Stage both sequences before publishing either mutation. Node storage is
    // still owned by glslang's shader pool; no source or initializer is cloned.
    glslang::TIntermSequence new_globals(globals.get_allocator());
    new_globals.assign(globals.begin(), globals.end());
    new_globals.erase(std::remove_if(new_globals.begin(), new_globals.end(), [](TIntermNode* node) {
        const auto op = node->getAsAggregate()->getOp();
        return op != glslang::EOpFunction && op != glslang::EOpLinkerObjects;
    }), new_globals.end());
    glslang::TIntermSequence new_statements(statements.get_allocator());
    new_statements.assign(statements.begin(), statements.end());
    new_statements.erase(new_statements.begin() + marker);
    new_statements.insert(new_statements.begin() + marker, initializers.begin(), initializers.end());
    globals.swap(new_globals);
    statements.swap(new_statements);
    relocated = initializers.size();
    return true;
}

}  // namespace

SpvComputeCompile compile_vulkan_compute(const std::string& source, ComputeInitializerPolicy initializer_policy) {
    ensure_process();
    SpvComputeCompile result;
    if (initializer_policy != ComputeInitializerPolicy::Default && initializer_policy != ComputeInitializerPolicy::EndpointInputsFirst) {
        result.log = "endpoint initializer policy: unknown compute policy\n";
        return result;
    }
    glslang::TShader shader(EShLangCompute);
    auto started = host_ns();
    result.parse_calls = 1;
    result.compute.ok = parse_shader(shader, EShLangCompute, source, result.compute.log);
    result.parse_ns = host_ns() - started;
    if (!result.compute.ok) { result.log = result.compute.log; return result; }
    glslang::TProgram program;
    program.addShader(&shader);
    started = host_ns();
    result.link_calls = 1;
    const bool linked = program.link(static_cast<EShMessages>(EShMsgSpvRules | EShMsgVulkanRules));
    result.link_ns = host_ns() - started;
    if (!linked) {
        result.compute.ok = false;
        result.compute.log += program.getInfoLog(); result.log = result.compute.log;
        return result;
    }
    if (initializer_policy == ComputeInitializerPolicy::EndpointInputsFirst &&
        !relocate_endpoint_initializers(program.getIntermediate(EShLangCompute), result.relocated_global_initializers, result.compute.log)) {
        result.compute.ok = false;
        result.log = result.compute.log;
        return result;
    }
    started = host_ns();
    const bool reflected = program.buildReflection(EShReflectionAllBlockVariables | EShReflectionSeparateBuffers);
    auto resource = [&](const glslang::TObjectReflection& value) {
        if (value.getBinding() >= 0 && (value.stages & EShLangComputeMask))
            result.resource_usage.push_back({static_cast<uint32_t>(value.getBinding()), 4});
    };
    if (reflected) {
        for (int n = 0; n < program.getNumUniformVariables(); ++n) resource(program.getUniform(n));
        for (int n = 0; n < program.getNumUniformBlocks(); ++n) resource(program.getUniformBlock(n));
        for (int n = 0; n < program.getNumBufferBlocks(); ++n) resource(program.getBufferBlock(n));
    }
    result.resource_reflect_ns = host_ns() - started;
    if (!reflected) {
        result.compute.ok = false; result.compute.log += "glslang compute resource reflection failed\n";
        result.log = result.compute.log; return result;
    }
    started = host_ns(); result.spirv_stages = 1;
    emit_spv(program, EShLangCompute, result.compute);
    result.spirv_ns = host_ns() - started;
    result.ok = result.compute.ok; result.log = result.compute.log;
    return result;
}

bool reflect_storage_rows(const std::vector<uint32_t>& words, const std::string& block_name,
                          SpvStorageLayout& layout, std::string& error) {
    auto fail = [&](const std::string& reason) { error = "SPIR-V storage reflection " + block_name + ": " + reason; return false; };
    if (words.size() < 5 || words[0] != 0x07230203u) return fail("invalid header");
    struct Type { spv::Op opcode; std::vector<uint32_t> args; };
    struct Member { uint32_t offset = 0, matrix_stride = 0; bool has_offset = false, row_major = false; };
    auto key = [](uint32_t id, uint32_t member) { return (uint64_t(id) << 32) | member; };
    std::unordered_map<uint32_t, Type> types;
    std::unordered_map<uint32_t, std::string> names;
    std::unordered_map<uint64_t, std::string> member_names;
    std::unordered_map<uint64_t, Member> members;
    std::unordered_map<uint32_t, uint32_t> strides, constants;
    auto text = [](const uint32_t* data, size_t count) {
        const char* start = reinterpret_cast<const char*>(data);
        const void* end = std::memchr(start, 0, count * 4);
        return std::string(start, end ? static_cast<const char*>(end) - start : count * 4);
    };
    for (size_t p = 5; p < words.size();) {
        const size_t count = words[p] >> 16;
        if (!count || count > words.size() - p) return fail("truncated instruction");
        const auto op = static_cast<spv::Op>(words[p] & 0xffffu);
        const auto* a = words.data() + p + 1;
        if (op == spv::Op::OpName && count >= 3) names[a[0]] = text(a + 1, count - 2);
        else if (op == spv::Op::OpMemberName && count >= 4) member_names[key(a[0], a[1])] = text(a + 2, count - 3);
        else if (op >= spv::Op::OpTypeVoid && op <= spv::Op::OpTypePointer && count >= 2)
            types[a[0]] = {op, std::vector<uint32_t>(a + 1, a + count - 1)};
        else if (op == spv::Op::OpConstant && count == 4) constants[a[1]] = a[2];
        else if (op == spv::Op::OpDecorate && count == 4 && a[1] == uint32_t(spv::Decoration::ArrayStride)) strides[a[0]] = a[2];
        else if (op == spv::Op::OpMemberDecorate && count >= 4) {
            auto& m = members[key(a[0], a[1])];
            if (a[2] == uint32_t(spv::Decoration::Offset) && count == 5) { m.offset = a[3]; m.has_offset = true; }
            else if (a[2] == uint32_t(spv::Decoration::MatrixStride) && count == 5) m.matrix_stride = a[3];
            else if (a[2] == uint32_t(spv::Decoration::RowMajor)) m.row_major = true;
        }
        p += count;
    }
    uint32_t block = 0;
    for (const auto& [id, name] : names) if (name == block_name && types.contains(id) && types.at(id).opcode == spv::Op::OpTypeStruct) block = id;
    if (!block || types.at(block).args.size() != 1) return fail("expected one runtime-array block member");
    const auto array_id = types.at(block).args[0];
    if (!types.contains(array_id) || types.at(array_id).opcode != spv::Op::OpTypeRuntimeArray || types.at(array_id).args.size() != 1 || !strides.contains(array_id))
        return fail("missing runtime-array stride");
    const auto row_id = types.at(array_id).args[0];
    if (!types.contains(row_id) || types.at(row_id).opcode != spv::Op::OpTypeStruct) return fail("row is not a struct");
    SpvStorageLayout reflected; reflected.row_stride = strides.at(array_id);
    for (uint32_t n = 0; n < types.at(row_id).args.size(); ++n) {
        SpvStorageMember value; value.name = member_names[key(row_id, n)];
        const auto m = members[key(row_id, n)];
        if (!m.has_offset || m.row_major || value.name.empty()) return fail("missing offset/name or row-major matrix");
        value.offset = m.offset; value.matrix_stride = m.matrix_stride;
        auto type_id = types.at(row_id).args[n];
        if (!types.contains(type_id)) return fail("missing member type");
        if (types.at(type_id).opcode == spv::Op::OpTypeArray) {
            const auto& a = types.at(type_id).args;
            if (a.size() != 2 || !constants.contains(a[1]) || !strides.contains(type_id)) return fail("missing fixed-array layout");
            value.array_size = constants.at(a[1]); value.array_stride = strides.at(type_id); type_id = a[0];
        }
        if (!types.contains(type_id)) return fail("missing scalar/vector/matrix type");
        if (types.at(type_id).opcode == spv::Op::OpTypeMatrix) {
            const auto& a = types.at(type_id).args;
            if (a.size() != 2 || !value.matrix_stride) return fail("missing matrix layout");
            value.value_type.columns = a[1]; type_id = a[0];
        }
        if (!types.contains(type_id)) return fail("missing vector type");
        if (types.at(type_id).opcode == spv::Op::OpTypeVector) {
            const auto& a = types.at(type_id).args;
            if (a.size() != 2) return fail("invalid vector type");
            value.value_type.rows = a[1]; type_id = a[0];
        }
        if (!types.contains(type_id)) return fail("missing scalar type");
        const auto& t = types.at(type_id);
        if (t.opcode == spv::Op::OpTypeFloat && t.args == std::vector<uint32_t>{32}) value.value_type.scalar = ShaderScalarType::Float;
        else if (t.opcode == spv::Op::OpTypeInt && t.args.size() == 2 && t.args[0] == 32)
            value.value_type.scalar = t.args[1] ? ShaderScalarType::Sint : ShaderScalarType::Uint;
        else return fail("only 32-bit scalar storage admitted");
        const uint64_t element = value.value_type.columns > 1 ? uint64_t(value.matrix_stride) * value.value_type.columns : uint64_t(value.value_type.rows) * 4;
        const uint64_t size = value.array_size ? uint64_t(value.array_stride) * value.array_size : element;
        if (size > UINT32_MAX || value.offset > reflected.row_stride || size > reflected.row_stride - value.offset) return fail("member exceeds reflected row");
        value.size = static_cast<uint32_t>(size); reflected.members.push_back(std::move(value));
    }
    layout = std::move(reflected); error.clear(); return true;
}

SpvCompile compile_vulkan_glsl(const std::string& vertex, const std::string& fragment,
                              bool vertex_input_cleanup) {
    ensure_process();
    SpvCompile result;
    glslang::TShader vert_shader(EShLangVertex);
    glslang::TShader frag_shader(EShLangFragment);
    auto started = host_ns();
    result.parse_calls = 2;
    const bool vert_ok = parse_shader(vert_shader, EShLangVertex, vertex, result.vertex.log);
    const bool frag_ok = parse_shader(frag_shader, EShLangFragment, fragment, result.fragment.log);
    result.parse_ns = host_ns() - started;
    if (!vert_ok || !frag_ok) {
        result.log = result.vertex.log + result.fragment.log;
        return result;
    }
    glslang::TProgram program;
    program.addShader(&vert_shader);
    program.addShader(&frag_shader);
    started = host_ns();
    result.link_calls = 1;
    const bool linked = program.link(static_cast<EShMessages>(EShMsgSpvRules | EShMsgVulkanRules));
    result.link_ns = host_ns() - started;
    if (!linked) {
        result.log = result.vertex.log + result.fragment.log + program.getInfoLog();
        result.vertex.log += program.getInfoLog();
        result.fragment.log += program.getInfoLog();
        return result;
    }
    started = host_ns();
    // Visit live linked functions, not declaration-only linker objects.
    // AllBlockVariables retains UBO layout members and enables per-symbol
    // stage masks. Pinned glslang's default instead ORs each new stage into
    // *all* previously reflected uniforms, falsely marking vertex-only
    // textures as fragment-used. This option does not reflect inactive
    // standalone sampler declarations.
    const bool reflected = program.buildReflection(EShReflectionAllBlockVariables | EShReflectionSeparateBuffers);
    auto resource = [&](const glslang::TObjectReflection& uniform) {
        const int binding = uniform.getBinding();
        if (binding < 0) return;
        const uint32_t stages = ((uniform.stages & EShLangVertexMask) ? 1u : 0u) |
                                ((uniform.stages & EShLangFragmentMask) ? 2u : 0u);
        if (stages) result.resource_usage.push_back({static_cast<uint32_t>(binding), stages});
    };
    if (reflected) {
        for (int n = 0; n < program.getNumUniformVariables(); ++n) resource(program.getUniform(n));
        for (int n = 0; n < program.getNumUniformBlocks(); ++n) resource(program.getUniformBlock(n));
        for (int n = 0; n < program.getNumBufferBlocks(); ++n) resource(program.getBufferBlock(n));
    }
    result.resource_reflect_ns = host_ns() - started;
    if (!reflected) {
        result.vertex.log += "glslang live resource reflection failed\n";
        result.log = result.vertex.log + result.fragment.log;
        return result;
    }
    started = host_ns();
    result.spirv_stages = 2;
    emit_spv(program, EShLangVertex, result.vertex);
    emit_spv(program, EShLangFragment, result.fragment);
    if (result.vertex.ok && vertex_input_cleanup) {
        // An unused count VBO is legal with sparse, high uint32 indices in GL.
        // Keep the arithmetic and source mappings intact; trim only interfaces
        // unreferenced by the entry point's actual call tree.
        spvtools::Optimizer optimizer(SPV_ENV_VULKAN_1_2);
        optimizer.SetMessageConsumer([&](spv_message_level_t, const char*, const spv_position_t&, const char* message) {
            result.vertex.log += std::string("SPIR-V active vertex input cleanup: ") + message + '\n';
        });
        optimizer.RegisterPass(spvtools::CreateRemoveUnusedInterfaceVariablesPass());
        std::vector<uint32_t> cleaned;
        result.vertex.ok = optimizer.Run(result.vertex.words.data(), result.vertex.words.size(), &cleaned) &&
                           validate_spv(cleaned, result.vertex.log);
        if (result.vertex.ok) {
            result.vertex.words = std::move(cleaned);
            std::unordered_set<uint32_t> interfaces, inputs;
            std::unordered_map<uint32_t, uint32_t> locations, input_types, constants;
            struct InputType { spv::Op op; std::vector<uint32_t> args; };
            std::unordered_map<uint32_t, InputType> types;
            const auto& words = result.vertex.words;
            for (size_t position = 5; position < words.size();) {
                const size_t count = words[position] >> 16;
                const auto op = static_cast<spv::Op>(words[position] & 0xffffu);
                const auto* args = words.data() + position + 1;
                if (op == spv::Op::OpEntryPoint && args[0] == static_cast<uint32_t>(spv::ExecutionModel::Vertex)) {
                    // Model, function, NUL-terminated name, then interface IDs.
                    size_t name_end = 3;
                    while (name_end < count &&
                           !std::memchr(words.data() + position + name_end, 0, sizeof(uint32_t))) ++name_end;
                    for (size_t n = name_end + 1; n < count; ++n) interfaces.insert(words[position + n]);
                } else if (op == spv::Op::OpVariable && count >= 4 &&
                           args[2] == static_cast<uint32_t>(spv::StorageClass::Input)) {
                    inputs.insert(args[1]); input_types[args[1]] = args[0];
                } else if (op == spv::Op::OpTypePointer || op == spv::Op::OpTypeMatrix ||
                           op == spv::Op::OpTypeArray || op == spv::Op::OpTypeVector ||
                           op == spv::Op::OpTypeFloat || op == spv::Op::OpTypeInt) {
                    types.emplace(args[0], InputType{op, {args + 1, args + count - 1}});
                } else if (op == spv::Op::OpConstant && count == 4) constants[args[1]] = args[2];
                else if (op == spv::Op::OpDecorate && count >= 4 &&
                         args[1] == static_cast<uint32_t>(spv::Decoration::Location)) locations[args[0]] = args[2];
                position += count;
            }
            // A matrix column (and each array element's complete span) occupies
            // locations even though only the variable's base is decorated.
            // Bound expansion by the same resource limit used by the parser,
            // independently of the eventual device's granted binding limits.
            const uint32_t limit = static_cast<uint32_t>(GetDefaultResources()->maxVertexAttribs);
            std::unordered_map<uint32_t, uint32_t> spans;
            std::function<uint32_t(uint32_t)> span = [&](uint32_t id) -> uint32_t {
                if (spans.contains(id)) return spans.at(id);
                if (!types.contains(id)) return 0;
                const auto& t = types.at(id); const auto& a = t.args;
                uint64_t n = 0;
                if (t.op == spv::Op::OpTypePointer) n = span(a[1]);
                else if (t.op == spv::Op::OpTypeFloat || t.op == spv::Op::OpTypeInt)
                    n = a[0] <= 128 ? 1 : 0;
                else if (t.op == spv::Op::OpTypeVector && types.contains(a[0])) {
                    const auto& scalar = types.at(a[0]);
                    if (scalar.op == spv::Op::OpTypeFloat || scalar.op == spv::Op::OpTypeInt)
                        n = (uint64_t(scalar.args[0]) * a[1] + 127) / 128;
                } else if (t.op == spv::Op::OpTypeMatrix) n = uint64_t(span(a[0])) * a[1];
                else if (t.op == spv::Op::OpTypeArray && constants.contains(a[1]))
                    n = uint64_t(span(a[0])) * constants.at(a[1]);
                const uint32_t bounded = n <= limit ? static_cast<uint32_t>(n) : 0;
                spans.emplace(id, bounded); return bounded;
            };
            for (auto id : interfaces) if (inputs.contains(id) && locations.contains(id)) {
                const uint32_t base = locations.at(id), width = span(input_types.at(id));
                if (!width || base > UINT32_MAX - (width - 1) ||
                    result.vertex_input_locations.size() + width > limit) {
                    result.vertex.ok = false;
                    result.vertex.log += "SPIR-V active vertex input cleanup: unsupported or excessive location span\n";
                    break;
                }
                for (uint32_t n = 0; n < width; ++n) result.vertex_input_locations.push_back(base + n);
            }
            std::sort(result.vertex_input_locations.begin(), result.vertex_input_locations.end());
            // Only vertex Input decorations are relocated. Paired varying
            // locations remain identical to the fragment stage and preserve
            // the composer's interface and interpolation metadata.
            for (size_t position = 5; position < result.vertex.words.size();) {
                const size_t count = result.vertex.words[position] >> 16;
                const auto op = static_cast<spv::Op>(result.vertex.words[position] & 0xffffu);
                auto* args = result.vertex.words.data() + position + 1;
                if (op == spv::Op::OpDecorate && count >= 4 &&
                    args[1] == static_cast<uint32_t>(spv::Decoration::Location) &&
                    interfaces.contains(args[0]) && inputs.contains(args[0])) {
                    args[2] = static_cast<uint32_t>(std::lower_bound(result.vertex_input_locations.begin(),
                        result.vertex_input_locations.end(), args[2]) - result.vertex_input_locations.begin());
                }
                position += count;
            }
            result.vertex.ok = result.vertex.ok && validate_spv(result.vertex.words, result.vertex.log);
        } else result.vertex.log += "SPIR-V active vertex input cleanup failed\n";
    }
    result.spirv_ns = host_ns() - started;
    result.ok = result.vertex.ok && result.fragment.ok;
    result.log = result.vertex.log + result.fragment.log;
    return result;
}

bool reflect_uniform_layout(const std::vector<uint32_t>& words,
                            std::vector<NormUniform>& uniforms,
                            uint32_t& uniform_bytes, std::string& error) {
    if (uniforms.empty()) return true;
    auto fail = [&](const std::string& reason) {
        error = "SPIR-V uniform reflection: " + reason;
        return false;
    };
    if (words.size() < 5 || words[0] != 0x07230203u) return fail("invalid binary header");
    struct Type {
        spv::Op opcode = spv::Op::OpNop;
        std::vector<uint32_t> operands;
    };
    struct Member {
        uint32_t offset = 0;
        uint32_t matrix_stride = 0;
        bool offset_present = false;
        bool row_major = false;
    };
    auto key = [](uint32_t id, uint32_t member) {
        return (static_cast<uint64_t>(id) << 32) | member;
    };
    std::unordered_map<uint32_t, std::string> names;
    std::unordered_map<uint64_t, std::string> member_names;
    std::unordered_map<uint32_t, Type> types;
    std::unordered_map<uint32_t, uint32_t> constants;
    std::unordered_map<uint32_t, uint32_t> array_strides;
    std::unordered_map<uint64_t, Member> members;
    auto decode_name = [&](size_t start, size_t count) {
        const char* begin = reinterpret_cast<const char*>(words.data() + start);
        const size_t length = count * sizeof(uint32_t);
        const void* end = std::memchr(begin, 0, length);
        return std::string(begin, end ? static_cast<const char*>(end) - begin : length);
    };
    for (size_t position = 5; position < words.size();) {
        const uint32_t instruction = words[position];
        const size_t count = instruction >> 16;
        const spv::Op opcode = static_cast<spv::Op>(instruction & 0xffffu);
        if (count == 0 || count > words.size() - position) return fail("truncated instruction");
        const uint32_t* args = words.data() + position + 1;
        if (opcode == spv::Op::OpName && count >= 3) names[args[0]] = decode_name(position + 2, count - 2);
        else if (opcode == spv::Op::OpMemberName && count >= 4)
            member_names[key(args[0], args[1])] = decode_name(position + 3, count - 3);
        else if (opcode == spv::Op::OpDecorate && count >= 4 && static_cast<spv::Decoration>(args[1]) == spv::Decoration::ArrayStride)
            array_strides[args[0]] = args[2];
        else if (opcode == spv::Op::OpMemberDecorate && count >= 4) {
            auto& member = members[key(args[0], args[1])];
            if (static_cast<spv::Decoration>(args[2]) == spv::Decoration::Offset && count >= 5) {
                member.offset = args[3];
                member.offset_present = true;
            } else if (static_cast<spv::Decoration>(args[2]) == spv::Decoration::MatrixStride && count >= 5) member.matrix_stride = args[3];
            else if (static_cast<spv::Decoration>(args[2]) == spv::Decoration::RowMajor) member.row_major = true;
        } else if (opcode >= spv::Op::OpTypeVoid && opcode <= spv::Op::OpTypePointer && count >= 2) {
            types[args[0]] = {opcode, std::vector<uint32_t>(args + 1, args + count - 1)};
        } else if (opcode == spv::Op::OpConstant && count >= 4) constants[args[1]] = args[2];
        position += count;
    }
    uint32_t block = 0;
    for (const auto& [id, name] : names) {
        if (name == "VispyUniforms" && types.count(id) && types[id].opcode == spv::Op::OpTypeStruct) {
            block = id;
            break;
        }
    }
    if (!block) return fail("VispyUniforms block is missing");
    if (types[block].operands.size() != uniforms.size()) return fail("member count differs from normalized block");
    auto reflected = uniforms;
    uint32_t total = 0;
    for (size_t index = 0; index < reflected.size(); ++index) {
        auto& uniform = reflected[index];
        const std::string expected = uniform.type == "bool" || uniform.type.rfind("bvec", 0) == 0
                                   ? "vispy_bool_storage_" + uniform.name : uniform.name;
        const uint64_t member_key = key(block, static_cast<uint32_t>(index));
        if (member_names[member_key] != expected) return fail("member name differs for " + uniform.name);
        const auto member = members[member_key];
        if (!member.offset_present) return fail("member offset missing for " + uniform.name);
        uint32_t type_id = types[block].operands[index];
        if (!types.count(type_id)) return fail("unknown type for " + uniform.name);
        uint32_t array_stride = 0;
        uint32_t array_size = 0;
        std::vector<uint32_t> dimensions, strides;
        uint64_t leaves = 1;
        while (types.count(type_id) && types[type_id].opcode == spv::Op::OpTypeArray) {
            const auto& array = types[type_id].operands;
            if (array.size() != 2 || !constants.count(array[1]) || !array_strides.count(type_id))
                return fail("array size/stride missing for " + uniform.name);
            const uint32_t dimension = constants[array[1]];
            if (!dimension || leaves > uint64_t(std::numeric_limits<int>::max()) / dimension)
                return fail("array dimensions overflow for " + uniform.name);
            leaves *= dimension;
            dimensions.push_back(dimension);
            strides.push_back(array_strides[type_id]);
            type_id = array[0];
        }
        if (!dimensions.empty()) {
            array_size = static_cast<uint32_t>(leaves);
            array_stride = strides.back();
            uint64_t extent = array_stride;
            for (size_t depth = dimensions.size(); depth-- > 0;) {
                if (!extent || extent != strides[depth])
                    return fail("nested array stride differs for " + uniform.name);
                extent *= dimensions[depth];
                if (extent > std::numeric_limits<uint32_t>::max())
                    return fail("array layout overflow for " + uniform.name);
            }
        }
        if (array_size != static_cast<uint32_t>(uniform.array_size) ||
                dimensions != uniform.array_dimensions)
            return fail("array shape differs for " + uniform.name);
        uint32_t columns = 1;
        uint32_t rows = 1;
        uint32_t components = 1;
        uint32_t element_size = 4;
        if (!types.count(type_id)) return fail("unknown element type for " + uniform.name);
        if (types[type_id].opcode == spv::Op::OpTypeMatrix) {
            const auto& matrix = types[type_id].operands;
            if (matrix.size() != 2 || !types.count(matrix[0]) || types[matrix[0]].opcode != spv::Op::OpTypeVector ||
                types[matrix[0]].operands.size() != 2 || member.matrix_stride == 0)
                return fail("invalid matrix type/stride for " + uniform.name);
            columns = matrix[1];
            rows = types[matrix[0]].operands[1];
            components = columns * rows;
            element_size = member.matrix_stride * (member.row_major ? rows : columns);
        } else if (types[type_id].opcode == spv::Op::OpTypeVector) {
            if (types[type_id].operands.size() != 2) return fail("invalid vector type for " + uniform.name);
            components = types[type_id].operands[1];
            element_size = components * 4;
        }
        const uint32_t size = array_size ? array_stride * array_size : element_size;
        if (uniform.offset != member.offset || uniform.component_count != components ||
            uniform.matrix_stride != member.matrix_stride || uniform.array_stride != array_stride ||
            uniform.size != size || uniform.row_major != member.row_major)
            return fail("compiler layout differs from normalized layout for " + uniform.name);
        uniform.offset = member.offset;
        uniform.size = size;
        uniform.component_count = components;
        uniform.array_stride = array_stride;
        uniform.matrix_stride = member.matrix_stride;
        uniform.matrix_columns = columns;
        uniform.matrix_rows = rows;
        uniform.row_major = member.row_major;
        total = std::max(total, uniform.offset + uniform.size);
    }
    uniforms = std::move(reflected);
    uniform_bytes = (total + 15u) & ~15u;
    error.clear();
    return true;
}


// Generated-consumer AST seam; shared compiler initialization lives above.
namespace {
bool relocate_fragment_initializers(glslang::TIntermediate* intermediate, uint64_t& relocated,
                                   std::string& log) {
    auto fail = [&](const std::string& detail) {
        log += "line consumer fragment initializer policy: unexpected pinned glslang tree (" + detail + ")\n";
        return false;
    };
    auto* root = intermediate && intermediate->getTreeRoot() ? intermediate->getTreeRoot()->getAsAggregate() : nullptr;
    if (!root || root->getOp() != glslang::EOpSequence) return fail("missing global sequence");
    auto& globals = root->getSequence();
    glslang::TIntermAggregate* entry = nullptr;
    std::vector<TIntermNode*> initializers;
    for (auto* node : globals) {
        auto* aggregate = node->getAsAggregate();
        if (!aggregate) return fail("non-aggregate global node");
        if (aggregate->getOp() == glslang::EOpFunction) {
            if (aggregate->getName().compare(intermediate->getEntryPointMangledName().c_str()) == 0) {
                if (entry) return fail("multiple entry functions");
                entry = aggregate;
            }
        } else if (aggregate->getOp() != glslang::EOpLinkerObjects) {
            // Match pinned GlslangToSpv::makeGlobalInitializers exactly: every
            // root aggregate other than a function/linker object is an
            // initializer. Keep the original nodes, order and source locations.
            initializers.push_back(node);
        }
    }
    if (!entry || entry->getSequence().size() != 2) return fail("entry parameters/body shape");
    auto* parameters = entry->getSequence()[0]->getAsAggregate();
    auto* body = entry->getSequence()[1]->getAsAggregate();
    if (!parameters || parameters->getOp() != glslang::EOpParameters || !parameters->getSequence().empty() ||
        !body || (body->getOp() != glslang::EOpSequence && body->getOp() != glslang::EOpScope))
        return fail("entry is not a parameterless statement sequence");
    auto& statements = body->getSequence();
    size_t marker = statements.size();
    for (size_t n = 0; n < statements.size(); ++n) {
        auto* call = statements[n]->getAsAggregate();
        if (!call || call->getOp() != glslang::EOpFunctionCall || call->getName() != "vispy_line_consumer_initialize_globals(") continue;
        if (marker != statements.size() || !call->getSequence().empty() || call->getBasicType() != glslang::EbtVoid)
            return fail("duplicate or malformed initializer marker");
        marker = n;
    }
    if (marker == statements.size()) return fail("missing direct generated initializer marker");
    // Stage both sequences before publishing either mutation. Node storage is
    // still owned by glslang's shader pool; no source or initializer is cloned.
    glslang::TIntermSequence new_globals(globals.get_allocator());
    new_globals.assign(globals.begin(), globals.end());
    new_globals.erase(std::remove_if(new_globals.begin(), new_globals.end(), [](TIntermNode* node) {
        const auto op = node->getAsAggregate()->getOp();
        return op != glslang::EOpFunction && op != glslang::EOpLinkerObjects;
    }), new_globals.end());
    glslang::TIntermSequence new_statements(statements.get_allocator());
    new_statements.assign(statements.begin(), statements.end());
    new_statements.erase(new_statements.begin() + marker);
    new_statements.insert(new_statements.begin() + marker, initializers.begin(), initializers.end());
    globals.swap(new_globals);
    statements.swap(new_statements);
    relocated = initializers.size();
    return true;
}


} // namespace

bool reflect_sampler_types(const std::vector<uint32_t>& words,
                           const std::vector<NormSampler>& samplers,
                           uint32_t stage_mask, std::string& error) {
    auto fail = [&](const std::string& message) {
        error = "sampled texture reflection: " + message;
        return false;
    };
    if (words.size() < 5 || words.front() != 0x07230203u ||
        (stage_mask != 1 && stage_mask != 2 && stage_mask != 4))
        return fail("invalid SPIR-V or stage");
    struct Image { uint32_t scalar, dimension, arrayed, multisampled, sampled; };
    std::unordered_map<uint32_t, ShaderScalarType> scalars;
    std::unordered_map<uint32_t, Image> images;
    std::unordered_map<uint32_t, uint32_t> pointers, variables, bindings, sets;
    for (size_t at = 5; at < words.size();) {
        const size_t count = words[at] >> 16;
        if (!count || count > words.size() - at) return fail("malformed instruction length");
        const auto opcode = static_cast<spv::Op>(words[at] & 0xffffu);
        const uint32_t* a = words.data() + at + 1;
        if (opcode == spv::Op::OpTypeFloat && count == 3 && a[1] == 32)
            scalars[a[0]] = ShaderScalarType::Float;
        else if (opcode == spv::Op::OpTypeInt && count == 4 && a[1] == 32 && a[2] <= 1)
            scalars[a[0]] = a[2] ? ShaderScalarType::Sint : ShaderScalarType::Uint;
        else if (opcode == spv::Op::OpTypeImage && count >= 9)
            images.emplace(a[0], Image{a[1], a[2], a[4], a[5], a[6]});
        else if (opcode == spv::Op::OpTypePointer && count == 4 &&
                 a[1] == static_cast<uint32_t>(spv::StorageClass::UniformConstant))
            pointers[a[0]] = a[2];
        else if (opcode == spv::Op::OpVariable && count >= 4 &&
                 a[2] == static_cast<uint32_t>(spv::StorageClass::UniformConstant))
            variables[a[1]] = a[0];
        else if (opcode == spv::Op::OpDecorate && count == 4) {
            if (a[1] == static_cast<uint32_t>(spv::Decoration::Binding)) bindings[a[0]] = a[2];
            else if (a[1] == static_cast<uint32_t>(spv::Decoration::DescriptorSet)) sets[a[0]] = a[2];
        }
        at += count;
    }
    std::unordered_map<uint32_t, Image> textures;
    for (const auto& [id, pointer] : variables) {
        auto target = pointers.find(pointer);
        if (target == pointers.end() || !images.contains(target->second)) continue;
        if (!bindings.contains(id) || !sets.contains(id) || sets.at(id) != 0)
            return fail("sampled image has no set-zero binding");
        if (!textures.emplace(bindings.at(id), images.at(target->second)).second)
            return fail("duplicate sampled image binding");
    }
    for (const auto& sampler : samplers) {
        if (!(sampler.texture_stage_mask & stage_mask)) continue;
        const auto found = textures.find(sampler.texture_binding);
        if (found == textures.end()) return fail("missing live image " + sampler.name);
        const auto& image = found->second;
        if (!scalars.contains(image.scalar) || scalars.at(image.scalar) != sampler.sample_scalar)
            return fail("sampled scalar differs for " + sampler.name);
        const std::string dimension = image.dimension == static_cast<uint32_t>(spv::Dim::Dim1D) ? "1d" :
            image.dimension == static_cast<uint32_t>(spv::Dim::Dim2D) ? "2d" :
            image.dimension == static_cast<uint32_t>(spv::Dim::Dim3D) ? "3d" :
            image.dimension == static_cast<uint32_t>(spv::Dim::Cube) ? "cube" : "unsupported";
        if (dimension != sampler.dim || image.arrayed || image.multisampled || image.sampled != 1)
            return fail("sampled image shape differs for " + sampler.name);
    }
    error.clear();
    return true;
}

namespace vispy::shader {
LineConsumerCompile compile_line_consumer_glsl(const std::string& vertex, const std::string& fragment) {
    ensure_process();
    LineConsumerCompile result;
    auto& stages = result.stages;
    glslang::TShader vertex_shader(EShLangVertex), fragment_shader(EShLangFragment);
    auto started = host_ns(); stages.parse_calls = 2;
    const bool vertex_ok = parse_shader(vertex_shader, EShLangVertex, vertex, stages.vertex.log);
    const bool fragment_ok = parse_shader(fragment_shader, EShLangFragment, fragment, stages.fragment.log);
    stages.parse_ns = host_ns() - started;
    if (!vertex_ok || !fragment_ok) { stages.log = stages.vertex.log + stages.fragment.log; return result; }
    glslang::TProgram program; program.addShader(&vertex_shader); program.addShader(&fragment_shader);
    started = host_ns(); stages.link_calls = 1;
    const bool linked = program.link(static_cast<EShMessages>(EShMsgSpvRules | EShMsgVulkanRules));
    if (linked && !relocate_fragment_initializers(program.getIntermediate(EShLangFragment),
            result.relocated_fragment_initializers, stages.fragment.log)) {
        stages.link_ns = host_ns() - started;
        stages.log = stages.vertex.log + stages.fragment.log; return result;
    }
    stages.link_ns = host_ns() - started;
    if (!linked) {
        stages.vertex.log += program.getInfoLog(); stages.fragment.log += program.getInfoLog();
        stages.log = stages.vertex.log + stages.fragment.log; return result;
    }
    started = host_ns();
    const bool reflected = program.buildReflection(EShReflectionAllBlockVariables | EShReflectionSeparateBuffers);
    auto resource = [&](const glslang::TObjectReflection& uniform) {
        const int binding = uniform.getBinding(); if (binding < 0) return;
        const uint32_t mask = ((uniform.stages & EShLangVertexMask) ? 1u : 0u) |
                              ((uniform.stages & EShLangFragmentMask) ? 2u : 0u);
        if (mask) stages.resource_usage.push_back({static_cast<uint32_t>(binding), mask});
    };
    if (reflected) {
        for (int n = 0; n < program.getNumUniformVariables(); ++n) resource(program.getUniform(n));
        for (int n = 0; n < program.getNumUniformBlocks(); ++n) resource(program.getUniformBlock(n));
        for (int n = 0; n < program.getNumBufferBlocks(); ++n) resource(program.getBufferBlock(n));
    }
    stages.resource_reflect_ns = host_ns() - started;
    if (!reflected) { stages.log = "generated consumer live resource reflection failed"; return result; }
    started = host_ns(); stages.spirv_stages = 2;
    emit_spv(program, EShLangVertex, stages.vertex); emit_spv(program, EShLangFragment, stages.fragment);
    stages.spirv_ns = host_ns() - started;
    stages.ok = stages.vertex.ok && stages.fragment.ok;
    stages.log = stages.vertex.log + stages.fragment.log;
    return result;
}
} // namespace vispy::shader

