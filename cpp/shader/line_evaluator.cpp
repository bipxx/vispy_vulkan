#include "shader/line_evaluator.hpp"

#include <sstream>

namespace vispy::shader {
namespace {

uint64_t aligned(uint64_t value, uint64_t alignment) {
    return (value + alignment - 1) & ~(alignment - 1);
}

uint32_t vector_alignment(uint32_t rows) { return rows == 1 ? 4 : rows == 2 ? 8 : 16; }

std::string physical_type(const NormVarying& varying) {
    if (varying.value_type.scalar != ShaderScalarType::Bool) return varying.type;
    return varying.value_type.rows == 1 ? "uint" : "uvec" + std::to_string(varying.value_type.rows);
}

void generated(LineEvaluatorArtifact& artifact, const std::string& source) {
    artifact.compute += source;
    for (char c : source) if (c == '\n') artifact.line_map.push_back(0);
}

std::string decode(const LineInputField& field) {
    const auto& type = field.value_type;
    auto component = [&](uint32_t n) {
        const auto source = "vispy_line_words[vispy_line_base + " + std::to_string(field.word_offset + n) + "u]";
        if (type.scalar == ShaderScalarType::Float) return "uintBitsToFloat(" + source + ")";
        if (type.scalar == ShaderScalarType::Sint) return "int(" + source + ")";
        if (type.scalar == ShaderScalarType::Bool) return "(" + source + " != 0u)";
        return source;
    };
    if (type.rows == 1) return component(0);
    std::string expression = field.attribute.type + "(";
    for (uint32_t n = 0; n < type.rows; ++n) expression += (n ? ", " : "") + component(n);
    return expression + ")";
}

}  // namespace

size_t LineEvaluatorArtifact::storage_bytes() const {
    size_t bytes = sizeof(*this) + line_map.capacity() * sizeof(int) + spv.capacity() * 4 +
        inputs.capacity() * sizeof(LineInputField) + outputs.capacity() * sizeof(LineOutputField) +
        uniforms.capacity() * sizeof(NormUniform) + samplers.capacity() * sizeof(NormSampler);
    for (const auto* text : {&identity, &cache_key, &compute, &log, &error}) bytes += text->capacity() + 1;
    for (const auto& field : inputs) bytes += field.attribute.name.capacity() + field.attribute.type.capacity() + 2;
    for (const auto& field : outputs) bytes += field.varying.name.capacity() + field.varying.type.capacity() +
        field.varying.interpolation.capacity() + field.storage_type.capacity() + 4 +
        field.varying.array_dimensions.capacity() * sizeof(uint32_t);
    for (const auto& value : uniforms) bytes += value.name.capacity() + value.type.capacity() + value.storage_type.capacity() + 3 + value.array_dimensions.capacity() * sizeof(uint32_t);
    for (const auto& value : samplers) bytes += value.name.capacity() + value.dim.capacity() + 2 + value.array_dimensions.capacity() * sizeof(uint32_t);
    return bytes;
}

std::shared_ptr<const LineEvaluatorArtifact> build_line_evaluator(
    std::shared_ptr<const PortableShaderArtifact> original, const LineEvaluatorLimits& limits) {
    const auto started = shader_host_ns();
    auto result = std::make_shared<LineEvaluatorArtifact>();
    struct Timer { LineEvaluatorArtifact& value; uint64_t start; ~Timer() { value.timings.total_ns = shader_host_ns() - start; } } timer{*result, started};
    result->original = std::move(original);
    auto fail = [&](const std::string& reason) -> std::shared_ptr<const LineEvaluatorArtifact> {
        result->error = "line endpoint evaluator: " + reason; return result;
    };
    if (!result->original || !result->original->ok) return fail("a validated original render artifact is required");
    if (result->original->point_sprites) return fail("point-quad render artifacts cannot evaluate original line endpoints");
    if (limits.max_storage_buffers < 2) return fail("two granted compute storage bindings are required");
    if (limits.max_workgroup_size_x < kLineEvaluatorWorkgroup || limits.max_workgroup_invocations < kLineEvaluatorWorkgroup)
        return fail("granted compute workgroup limits do not admit 64 isolated invocations");
    auto options = result->original->options;
    options.vertex_identity = VertexIdentityPolicy::Native;
    options.line_evaluator = true;
    const auto normalize_start = shader_host_ns();
    auto normalized = normalize_program(result->original->source_vertex, result->original->source_fragment, options);
    result->timings.normalize_ns = shader_host_ns() - normalize_start; result->timings.normalizations = 1;
    if (!normalized.error.empty()) return fail(normalized.error);
    result->identity = result->original->identity + ";endpoint-spirv-derivatives=" +
        spirv_derivative_mode_name(result->derivative_mode) +
        ";endpoint=isolated-main-once-v3;initializers=original-AST-after-guarded-inputs;input=uint32-header4-id2-raw-components;output=std430-typed-GL-clip;output-access=read-write-storage;group=64;";
    result->cache_key = shader_identity_digest(result->identity);
    for (const auto& attribute : result->original->attributes) {
        LineInputField field; field.attribute = attribute;
        if (!shader_value_type(attribute.type, field.value_type) || field.value_type.columns != 1)
            return fail("attribute " + attribute.name + ": unsupported endpoint input type " + attribute.type);
        field.word_offset = result->input_row_words;
        if (field.value_type.components() > UINT32_MAX - result->input_row_words) return fail("endpoint input row overflow");
        result->input_row_words += field.value_type.components(); result->inputs.push_back(std::move(field));
    }
    uint64_t cursor = 16;
    for (const auto& varying : normalized.varyings) {
        if (!varying.vertex_declared) return fail("varying " + varying.name + ": missing original vertex output");
        // Endpoint evaluation stores the original values without rasterizing.
        // Preserve sample/centroid metadata for the consumer's explicit sample
        // policy; only that render stage decides whether it can interpolate it.
        LineOutputField field; field.varying = varying; field.storage_type = physical_type(varying);
        const auto alignment = vector_alignment(varying.value_type.rows);
        uint64_t element = varying.value_type.rows * 4;
        if (varying.value_type.columns > 1) {
            field.matrix_stride = static_cast<uint32_t>(aligned(element, alignment));
            element = uint64_t(field.matrix_stride) * varying.value_type.columns;
        }
        cursor = aligned(cursor, alignment);
        uint64_t size = element;
        if (varying.array_size > 0) {
            field.array_stride = static_cast<uint32_t>(aligned(element, alignment));
            size = uint64_t(field.array_stride) * static_cast<uint32_t>(varying.array_size);
        }
        if (cursor > UINT32_MAX || size > UINT32_MAX - cursor) return fail("varying " + varying.name + ": output row overflow");
        field.offset = static_cast<uint32_t>(cursor); field.size = static_cast<uint32_t>(size);
        cursor += size; result->outputs.push_back(std::move(field));
    }
    cursor = aligned(cursor, 16);
    if (cursor > UINT32_MAX) return fail("aligned output row overflow");
    result->output_row_bytes = static_cast<uint32_t>(cursor);
    if (cursor > limits.max_storage_buffer_binding_size || cursor > limits.max_buffer_size ||
        uint64_t(result->input_row_words) * 4 + 16 > limits.max_storage_buffer_binding_size ||
        uint64_t(result->input_row_words) * 4 + 16 > limits.max_buffer_size) return fail("one endpoint row exceeds granted storage/allocation size");
    uint64_t binding = 1;
    for (const auto& sampler : normalized.samplers) binding = std::max(binding, uint64_t(sampler.sampler_binding) + 1);
    if (binding >= UINT32_MAX || binding + 1 >= limits.max_bindings) return fail("internal storage binding exceeds granted binding range");
    result->input_binding = static_cast<uint32_t>(binding); result->output_binding = result->input_binding + 1;
    result->compute = std::move(normalized.vertex); result->line_map = std::move(normalized.vertex_line_map);
    result->uniforms = std::move(normalized.uniforms); result->uniform_bytes = normalized.uniform_bytes;
    std::ostringstream storage;
    storage << "layout(local_size_x = 64, local_size_y = 1, local_size_z = 1) in;\n"
            << "layout(std430, set = 0, binding = " << result->input_binding << ") readonly buffer VispyLineInputs { uint vispy_line_words[]; };\n"
            << "struct VispyLineOutput {\n    vec4 clip_position;\n";
    for (size_t n = 0; n < result->outputs.size(); ++n) {
        const auto& field = result->outputs[n];
        storage << "    " << field.storage_type << " varying_" << n;
        if (field.varying.array_size) storage << "[" << field.varying.array_size << "]";
        storage << ";\n";
    }
    storage << "};\nlayout(std430, set = 0, binding = " << result->output_binding
            << ") buffer VispyLineOutputs { VispyLineOutput vispy_line_outputs[]; };\n"
            << "void vispy_line_initialize_globals() {}\n"
            << "void main() {\n    uint vispy_line_row = gl_GlobalInvocationID.x;\n"
            << "    if (vispy_line_words.length() < 4) return;\n"
            << "    uint vispy_line_count = vispy_line_words[0];\n"
            << "    if (vispy_line_words[1] != 1u || vispy_line_words[2] != " << result->input_row_words
            << "u || vispy_line_words[3] != 0u || vispy_line_count > (uint(vispy_line_words.length()) - 4u) / " << result->input_row_words << "u) return;\n"
            << "    if (vispy_line_row >= vispy_line_count) return;\n"
            << "    if (vispy_line_row >= uint(vispy_line_outputs.length())) return;\n"
            << "    uint vispy_line_base = 4u + vispy_line_row * " << result->input_row_words << "u;\n"
            << "    vispy_line_vertex_id = vispy_line_words[vispy_line_base];\n"
            << "    vispy_line_instance_id = vispy_line_words[vispy_line_base + 1u];\n";
    for (const auto& field : result->inputs) storage << "    " << field.attribute.name << " = " << decode(field) << ";\n";
    storage << "    vispy_line_initialize_globals();\n    vispy_user_main();\n    vispy_line_outputs[vispy_line_row].clip_position = vispy_line_clip_position;\n";
    for (size_t n = 0; n < result->outputs.size(); ++n) {
        const auto& field = result->outputs[n];
        const auto expression = field.varying.name + varying_element_suffix(field.varying, "vispy_line_element");
        const auto converted = field.varying.value_type.scalar == ShaderScalarType::Bool ? field.storage_type + "(" + expression + ")" : expression;
        if (field.varying.array_size) storage << "    for (uint vispy_line_element = 0u; vispy_line_element < " << field.varying.array_size << "u; ++vispy_line_element)\n";
        storage << "    vispy_line_outputs[vispy_line_row].varying_" << n << (field.varying.array_size ? "[vispy_line_element]" : "") << " = " << converted << ";\n";
    }
    storage << "}\n"; generated(*result, storage.str());
    auto compiled = compile_vulkan_compute(result->compute, ComputeInitializerPolicy::EndpointInputsFirst);
    result->relocated_global_initializers = compiled.relocated_global_initializers;
    result->timings.parse_ns = compiled.parse_ns; result->timings.link_ns = compiled.link_ns;
    result->timings.spirv_ns = compiled.spirv_ns; result->timings.reflect_ns = compiled.resource_reflect_ns;
    result->timings.parse_calls = compiled.parse_calls; result->timings.link_calls = compiled.link_calls; result->timings.spirv_stages = compiled.spirv_stages;
    result->spv = std::move(compiled.compute.words); result->log = std::move(compiled.log);
    if (!compiled.ok) {
        result->mapped_line = shader_composer_line(result->log, result->line_map);
        return fail(result->log);
    }
    // Compute regenerated from source must receive the same actual one-level
    // nearest/wrap policy as the captured vertex stage. Lowering the original
    // render SPIR-V alone cannot change this newly compiled module.
    const auto integer_uses = integer_sample_bindings(result->spv, 4);
    if (!integer_uses.ok) return fail(integer_uses.error);
    if (!integer_uses.bindings.empty()) {
        if (result->original->integer_sampling_identity.empty())
            return fail("integer endpoint sampling requires the actual retained DRAW policy");
        const auto lowering_start = shader_host_ns();
        auto lowered = lower_integer_nearest_2d(result->spv, result->original->integer_sampling_policies);
        if (!lowered.ok) return fail(lowered.error);
        auto finalized = finalize_sampled_stage(lowered.words, 4);
        if (!finalized.ok) return fail(finalized.error);
        result->spv = std::move(finalized.words);
        compiled.resource_usage = std::move(finalized.resource_usage);
        result->timings.integer_sampling_ns += shader_host_ns() - lowering_start;
        result->timings.integer_sampling_builds++;
        result->timings.integer_samples_lowered += lowered.samples_lowered;
        result->identity += ";endpoint-integer-sampling=captured-compute-query-fetch-v1;";
        result->cache_key = shader_identity_digest(result->identity);
    }
    auto stage_mask = [&](uint32_t requested) {
        uint32_t mask = 0;
        for (const auto& usage : compiled.resource_usage) if (usage.binding == requested) mask |= usage.stage_mask;
        return mask;
    };
    result->uniform_stage_mask = stage_mask(0);
    result->samplers = std::move(normalized.samplers);
    for (auto& sampler : result->samplers) {
        sampler.texture_stage_mask = stage_mask(sampler.texture_binding); sampler.sampler_stage_mask = stage_mask(sampler.sampler_binding);
    }
    std::erase_if(result->samplers, [](const NormSampler& sampler) { return !sampler.texture_stage_mask && !sampler.sampler_stage_mask; });
    const auto reflection_start = shader_host_ns();
    std::string reflection_error;
    if (!reflect_uniform_layout(result->spv, result->uniforms, result->uniform_bytes, reflection_error)) return fail(reflection_error);
    SpvStorageLayout reflected;
    if (!reflect_storage_rows(result->spv, "VispyLineOutputs", reflected, reflection_error)) return fail(reflection_error);
    if (reflected.row_stride != result->output_row_bytes || reflected.members.size() != result->outputs.size() + 1)
        return fail("compiler output row stride/member count differs");
    const auto& clip = reflected.members.front();
    if (clip.name != "clip_position" || clip.offset != 0 || clip.size != 16 || clip.value_type.scalar != ShaderScalarType::Float || clip.value_type.rows != 4 || clip.value_type.columns != 1)
        return fail("compiler GL clip-position layout differs");
    for (size_t n = 0; n < result->outputs.size(); ++n) {
        const auto& field = result->outputs[n]; const auto& actual = reflected.members[n + 1];
        const auto scalar = field.varying.value_type.scalar == ShaderScalarType::Bool ? ShaderScalarType::Uint : field.varying.value_type.scalar;
        if (actual.name != "varying_" + std::to_string(n) || actual.offset != field.offset || actual.size != field.size ||
            actual.array_size != static_cast<uint32_t>(field.varying.array_size) || actual.array_stride != field.array_stride || actual.matrix_stride != field.matrix_stride ||
            actual.value_type.scalar != scalar || actual.value_type.columns != field.varying.value_type.columns || actual.value_type.rows != field.varying.value_type.rows)
            return fail("varying " + field.varying.name + ": compiler std430 layout differs");
    }
    result->timings.reflect_ns += shader_host_ns() - reflection_start;
    result->ok = true; return result;
}

bool line_evaluator_dispatch(const LineEvaluatorArtifact& artifact, uint64_t count, const LineEvaluatorLimits& limits,
                             LineEvaluatorDispatch& dispatch, std::string& error) {
    auto fail = [&](const std::string& reason) { error = "line endpoint dispatch: " + reason; return false; };
    if (!artifact.ok || artifact.input_row_words < 2 || artifact.output_row_bytes < 16) return fail("invalid evaluator artifact");
    LineEvaluatorDispatch candidate;
    if (count == 0) { dispatch = candidate; error.clear(); return true; }
    if (count > UINT32_MAX) return fail("endpoint count exceeds exact uint32 range");
    const uint64_t words = 4 + count * artifact.input_row_words;
    if (words > UINT32_MAX || count > UINT64_MAX / artifact.output_row_bytes) return fail("input indexing/output byte overflow");
    candidate.input_bytes = words * 4; candidate.output_bytes = count * artifact.output_row_bytes;
    if (candidate.input_bytes > limits.max_storage_buffer_binding_size || candidate.output_bytes > limits.max_storage_buffer_binding_size ||
        candidate.input_bytes > limits.max_buffer_size || candidate.output_bytes > limits.max_buffer_size) return fail("endpoint payload exceeds granted storage/allocation size; ordered partitioning required");
    const uint64_t groups = (count + kLineEvaluatorWorkgroup - 1) / kLineEvaluatorWorkgroup;
    if (groups > limits.max_workgroups_x || limits.max_workgroup_size_x < kLineEvaluatorWorkgroup || limits.max_workgroup_invocations < kLineEvaluatorWorkgroup)
        return fail("endpoint dispatch exceeds granted compute workgroup limits; ordered partitioning required");
    candidate.workgroups_x = static_cast<uint32_t>(groups);
    candidate.input_header = {static_cast<uint32_t>(count), kLineEvaluatorAbi, artifact.input_row_words, 0};
    dispatch = candidate; error.clear(); return true;
}

}  // namespace vispy::shader
