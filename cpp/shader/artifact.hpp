#pragma once

#include "shader/glslang_spv.hpp"
#include "shader/normalize.hpp"
#include "shader/integer_sampling.hpp"
#include <SPIRV/spirv.hpp11>

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace vispy::shader {

inline uint64_t shader_host_ns() {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}

struct ShaderBuildTimings {
    uint64_t normalize_ns = 0, parse_ns = 0, link_ns = 0, spirv_ns = 0, reflect_ns = 0, total_ns = 0;
    uint64_t normalizations = 0, parse_calls = 0, link_calls = 0, spirv_stages = 0;
    uint64_t integer_sampling_ns = 0, integer_sampling_builds = 0, integer_samples_lowered = 0;
};

// SPIR-V ingestion policy is captured separately from GLSL normalization and
// sampler lowering. Callers must opt in to the render compatibility profile.
enum class SpirvDerivativeMode : uint32_t { Strict, AllowNonUniform };

inline const char* spirv_derivative_mode_name(SpirvDerivativeMode mode) {
    return mode == SpirvDerivativeMode::AllowNonUniform ? "allow-nonuniform-v1" : "strict-v1";
}

// This identity is independent of the device, attachment formats, and depth
// attachment availability. Exact input sources retain composer provenance;
// normalized text alone can alias sources with different diagnostic mappings.
inline std::string portable_shader_identity(const std::string& vertex, const std::string& fragment,
                                           const NormalizeOptions& options,
                                           const std::string& compiler_identity,
                                           SpirvDerivativeMode derivative_mode = SpirvDerivativeMode::Strict) {
    std::string identity = "vispy-portable-shader-v1;opaque=merge-return,inline-opaque,dead-functions;resources=linked-live-all-block-separate-buffer-stage-reflection;sample-scalars=float-sint-uint-v1;inputs=live-vs-compact;";
    identity += options.base_level_sampling ? "base=1;" : "base=0;";
    identity += options.reverse_depth ? "depth=reverse-clip-v1;" : "depth=forward-clip-v1;";
    identity += "fragment-depth=window-coordinate-v1;";
    identity += options.point_sprites ? "points=1;point-id=std430-uint32x2-instance-major;" : "points=0;";
    identity += "vertex-id=" + std::to_string(static_cast<uint32_t>(options.vertex_identity)) + ";std430-uint32;";
    if (batch_identity_policy(options.vertex_identity)) {
        identity += "batch-instance-abi=";
        identity += kBatchInstanceAbi;
        identity += ";native-first-instance=row-offset;";
    }
    identity += options.line_evaluator ? "endpoint=isolated-compute-v1;" : "endpoint=render;";
    identity += "render-spirv-derivatives=";
    identity += spirv_derivative_mode_name(derivative_mode);
    identity += ';';
    for (const auto* field : {&compiler_identity, &vertex, &fragment}) {
        identity += std::to_string(field->size()) + ':';
        identity.append(*field);
    }
    return identity;
}

inline std::string shader_identity_digest(const std::string& identity) {
    uint64_t hash = 14695981039346656037ull;
    for (unsigned char value : identity) {
        hash ^= value;
        hash *= 1099511628211ull;
    }
    std::ostringstream stream;
    stream << std::hex << hash;
    return stream.str();
}

inline int shader_composer_line(const std::string& log, const std::vector<int>& map) {
    auto position = log.find("ERROR:");
    if (position == std::string::npos) position = log.find("error:");
    if (position == std::string::npos) return 0;
    int numbers = 0;
    size_t line = 0;
    for (size_t i = position; i < log.size();) {
        if (log[i] >= '0' && log[i] <= '9') {
            size_t value = 0;
            while (i < log.size() && log[i] >= '0' && log[i] <= '9') {
                if (value > 1'000'000) return 0;
                value = value * 10 + static_cast<unsigned>(log[i++] - '0');
            }
            if (++numbers == 2) { line = value; break; }
        } else ++i;
    }
    if (line >= 1 && line <= map.size()) return map[line - 1] == 0 ? static_cast<int>(line) : map[line - 1];
    return static_cast<int>(line);
}

struct PortableShaderArtifact {
    NormalizeOptions options;
    SpirvDerivativeMode derivative_mode = SpirvDerivativeMode::Strict;
    bool point_sprites = false;
    bool has_fragment_depth = false;
    bool early_fragment_tests = false;
    bool window_depth_output() const { return has_fragment_depth && !early_fragment_tests; }
    bool has_flat_varyings = false;
    bool ok = false;
    // cache_key is a short display label, never the identity used for lookup.
    std::string cache_key;
    std::string identity;
    std::string compiler_identity;
    std::string source_vertex;
    std::string source_fragment;
    std::string vertex;
    std::string fragment;
    std::vector<int> vert_map;
    std::vector<int> frag_map;
    std::vector<uint32_t> spv_vert;
    std::vector<uint32_t> spv_frag;
    std::vector<NormUniform> uniforms;
    std::vector<NormSampler> samplers;
    std::vector<IntegerSampleBinding> integer_sample_uses;
    std::vector<IntegerSamplePolicy> integer_sampling_policies;
    std::string integer_sampling_identity;
    std::vector<NormAttribute> attributes;
    std::vector<NormVarying> varyings;
    uint32_t uniform_bytes = 0;
    uint32_t uniform_stage_mask = 0;
    uint32_t point_identity_binding = 0;
    uint32_t vertex_identity_binding = 0;
    uint32_t batch_instance_binding = 0;
    uint32_t batch_instance_stage_mask = 0;
    std::string vertex_log;
    std::string fragment_log;
    std::string error;
    int mapped_line = 0;
    ShaderBuildTimings timings;

    // Account owned capacities, including reflection strings. This bounds
    // cached shader storage, rather than claiming to measure allocator/RSS use.
    size_t storage_bytes() const {
        size_t bytes = sizeof(*this);
        for (const auto* text : {&cache_key, &identity, &compiler_identity, &source_vertex, &source_fragment,
                                 &vertex, &fragment, &vertex_log, &fragment_log, &error,
                                 &integer_sampling_identity}) bytes += text->capacity() + 1;
        bytes += integer_sample_uses.capacity() * sizeof(IntegerSampleBinding) +
                 integer_sampling_policies.capacity() * sizeof(IntegerSamplePolicy);
        bytes += (vert_map.capacity() + frag_map.capacity()) * sizeof(int);
        bytes += (spv_vert.capacity() + spv_frag.capacity()) * sizeof(uint32_t);
        bytes += uniforms.capacity() * sizeof(NormUniform) + samplers.capacity() * sizeof(NormSampler) +
                 attributes.capacity() * sizeof(NormAttribute);
        bytes += varyings.capacity() * sizeof(NormVarying);
        for (const auto& uniform : uniforms)
            bytes += uniform.name.capacity() + uniform.type.capacity() + uniform.storage_type.capacity() + 3 +
                     uniform.array_dimensions.capacity() * sizeof(uint32_t);
        for (const auto& sampler : samplers)
            bytes += sampler.name.capacity() + sampler.dim.capacity() + 2 +
                     sampler.array_dimensions.capacity() * sizeof(uint32_t);
        for (const auto& attribute : attributes) bytes += attribute.name.capacity() + attribute.type.capacity() + 2;
        for (const auto& varying : varyings)
            bytes += varying.name.capacity() + varying.type.capacity() + varying.interpolation.capacity() + 3;
        return bytes;
    }
};

inline std::shared_ptr<const PortableShaderArtifact> build_portable_shader(
    const std::string& vertex, const std::string& fragment, const NormalizeOptions& options,
    const std::string& compiler_identity,
    SpirvDerivativeMode derivative_mode = SpirvDerivativeMode::Strict) {
    const auto started = shader_host_ns();
    auto artifact = std::make_shared<PortableShaderArtifact>();
    struct TotalTimer {
        ShaderBuildTimings& timings;
        uint64_t start;
        ~TotalTimer() { timings.total_ns = shader_host_ns() - start; }
    } total_timer{artifact->timings, started};
    artifact->options = options;
    artifact->derivative_mode = derivative_mode;
    artifact->compiler_identity = compiler_identity;
    artifact->identity = portable_shader_identity(vertex, fragment, options, compiler_identity, derivative_mode);
    artifact->cache_key = shader_identity_digest(artifact->identity);
    artifact->source_vertex = vertex;
    artifact->source_fragment = fragment;
    auto stage_start = shader_host_ns();
    ++artifact->timings.normalizations;
    auto normalized = normalize_program(vertex, fragment, options);
    artifact->timings.normalize_ns = shader_host_ns() - stage_start;
    artifact->point_sprites = normalized.point_sprites;
    artifact->has_fragment_depth = normalized.has_fragment_depth;
    artifact->has_flat_varyings = normalized.has_flat_varyings;
    artifact->vertex = std::move(normalized.vertex);
    artifact->fragment = std::move(normalized.fragment);
    artifact->vert_map = std::move(normalized.vertex_line_map);
    artifact->frag_map = std::move(normalized.fragment_line_map);
    artifact->uniforms = std::move(normalized.uniforms);
    artifact->samplers = std::move(normalized.samplers);
    artifact->attributes = std::move(normalized.attributes);
    artifact->varyings = std::move(normalized.varyings);
    artifact->uniform_bytes = std::max(16u, normalized.uniform_bytes);
    if (!normalized.error.empty()) {
        artifact->error = std::move(normalized.error);
        return artifact;
    }
    if (options.line_evaluator) {
        artifact->error = "endpoint compute policy requires build_line_evaluator, not a render pipeline";
        return artifact;
    }
    auto compiled = compile_vulkan_glsl(artifact->vertex, artifact->fragment, true);
    artifact->timings.parse_ns = compiled.parse_ns;
    artifact->timings.link_ns = compiled.link_ns;
    artifact->timings.spirv_ns = compiled.spirv_ns;
    artifact->timings.reflect_ns = compiled.resource_reflect_ns;
    artifact->timings.parse_calls = compiled.parse_calls;
    artifact->timings.link_calls = compiled.link_calls;
    artifact->timings.spirv_stages = compiled.spirv_stages;
    artifact->spv_vert = std::move(compiled.vertex.words);
    artifact->spv_frag = std::move(compiled.fragment.words);
    artifact->vertex_log = std::move(compiled.vertex.log);
    artifact->fragment_log = std::move(compiled.fragment.log);
    if (!compiled.ok) {
        artifact->error = compiled.log.empty() ? artifact->vertex_log + artifact->fragment_log : std::move(compiled.log);
        artifact->mapped_line = shader_composer_line(artifact->fragment_log, artifact->frag_map);
        if (!artifact->mapped_line) artifact->mapped_line = shader_composer_line(artifact->vertex_log, artifact->vert_map);
        return artifact;
    }
    // Cleanup only programs containing integer normalized samples. This lets
    // discovery exclude dead sample operations while float/fetch-only portable
    // words retain the existing compilation path byte for byte.
    auto integer_vertex = integer_sample_bindings(artifact->spv_vert, 1);
    auto integer_fragment = integer_sample_bindings(artifact->spv_frag, 2);
    if (!integer_vertex.ok || !integer_fragment.ok) {
        artifact->error = !integer_vertex.ok ? integer_vertex.error : integer_fragment.error;
        return artifact;
    }
    const bool integer_cleanup = !integer_vertex.bindings.empty() || !integer_fragment.bindings.empty();
    if (integer_cleanup) {
        stage_start = shader_host_ns();
        auto live_vertex = finalize_sampled_stage(artifact->spv_vert, 1);
        auto live_fragment = finalize_sampled_stage(artifact->spv_frag, 2);
        if (!live_vertex.ok || !live_fragment.ok) {
            artifact->error = !live_vertex.ok ? live_vertex.error : live_fragment.error; return artifact;
        }
        artifact->spv_vert = std::move(live_vertex.words);
        artifact->spv_frag = std::move(live_fragment.words);
        compiled.resource_usage = std::move(live_vertex.resource_usage);
        compiled.resource_usage.insert(compiled.resource_usage.end(), live_fragment.resource_usage.begin(), live_fragment.resource_usage.end());
        integer_vertex = integer_sample_bindings(artifact->spv_vert, 1);
        integer_fragment = integer_sample_bindings(artifact->spv_frag, 2);
        artifact->timings.reflect_ns += shader_host_ns() - stage_start;
        if (!integer_vertex.ok || !integer_fragment.ok) {
            artifact->error = !integer_vertex.ok ? integer_vertex.error : integer_fragment.error; return artifact;
        }
    }
    artifact->integer_sample_uses = std::move(integer_vertex.bindings);
    for (const auto& use : integer_fragment.bindings) {
        auto found = std::find_if(artifact->integer_sample_uses.begin(), artifact->integer_sample_uses.end(), [&](const auto& old) {
            return old.texture_binding == use.texture_binding && old.sampler_binding == use.sampler_binding && old.scalar == use.scalar;
        });
        if (found == artifact->integer_sample_uses.end()) artifact->integer_sample_uses.push_back(use);
        else found->stage_mask |= use.stage_mask;
    }
    std::erase_if(artifact->attributes, [&](const NormAttribute& attribute) {
        return !std::binary_search(compiled.vertex_input_locations.begin(),
                                  compiled.vertex_input_locations.end(), attribute.location);
    });
    for (auto& attribute : artifact->attributes)
        attribute.location = static_cast<uint32_t>(std::lower_bound(compiled.vertex_input_locations.begin(),
            compiled.vertex_input_locations.end(), attribute.location) - compiled.vertex_input_locations.begin());
    auto binding_stages = [&](uint32_t binding) {
        uint32_t stages = 0;
        for (const auto& usage : compiled.resource_usage) if (usage.binding == binding) stages |= usage.stage_mask;
        return stages;
    };
    artifact->uniform_stage_mask = binding_stages(0);
    if (normalized.point_identity_binding && binding_stages(normalized.point_identity_binding))
        artifact->point_identity_binding = normalized.point_identity_binding;
    if (normalized.vertex_identity_binding && binding_stages(normalized.vertex_identity_binding))
        artifact->vertex_identity_binding = normalized.vertex_identity_binding;
    if (normalized.batch_instance_binding) {
        artifact->batch_instance_stage_mask = binding_stages(normalized.batch_instance_binding);
        if (artifact->batch_instance_stage_mask)
            artifact->batch_instance_binding = normalized.batch_instance_binding;
    }
    for (auto& sampler : artifact->samplers) {
        sampler.texture_stage_mask = binding_stages(sampler.texture_binding);
        sampler.sampler_stage_mask = binding_stages(sampler.sampler_binding);
    }
    std::erase_if(artifact->samplers, [](const NormSampler& sampler) {
        return !sampler.texture_stage_mask && !sampler.sampler_stage_mask;
    });
    stage_start = shader_host_ns();
    const bool reflected = reflect_sampler_types(artifact->spv_vert, artifact->samplers, 1, artifact->error) &&
                           reflect_sampler_types(artifact->spv_frag, artifact->samplers, 2, artifact->error) &&
                           ((!integer_cleanup || (artifact->uniform_stage_mask & 1)) ? reflect_uniform_layout(artifact->spv_vert, artifact->uniforms, artifact->uniform_bytes, artifact->error) : true) &&
                           ((!integer_cleanup || (artifact->uniform_stage_mask & 2)) ? reflect_uniform_layout(artifact->spv_frag, artifact->uniforms, artifact->uniform_bytes, artifact->error) : true);
    artifact->timings.reflect_ns += shader_host_ns() - stage_start;
    if (!reflected) return artifact;
    // Inspect actual compiled modes/builtins, including preprocessor aliases
    // and dead helper removal. Early tests use raster depth, not shader writes.
    artifact->has_fragment_depth = false;
    for (size_t at = 5; at < artifact->spv_frag.size();) {
        const uint32_t words = artifact->spv_frag[at] >> 16;
        const auto opcode = static_cast<spv::Op>(artifact->spv_frag[at] & 0xffffu);
        if (!words || words > artifact->spv_frag.size() - at) break;
        if (opcode == spv::Op::OpExecutionMode && words >= 3 &&
                artifact->spv_frag[at + 2] == static_cast<uint32_t>(spv::ExecutionMode::EarlyFragmentTests))
            artifact->early_fragment_tests = true;
        if (opcode == spv::Op::OpDecorate && words >= 4 &&
                artifact->spv_frag[at + 2] == static_cast<uint32_t>(spv::Decoration::BuiltIn) &&
                artifact->spv_frag[at + 3] == static_cast<uint32_t>(spv::BuiltIn::FragDepth))
            artifact->has_fragment_depth = true;
        at += words;
    }
    artifact->ok = true;
    return artifact;
}

inline std::string integer_sampling_artifact_identity(const PortableShaderArtifact& base,
                                                      const std::vector<IntegerSamplePolicy>& policies) {
    const auto policy = integer_sample_policy_identity(policies);
    if (policy.empty()) return {};
    return "vispy-integer-sampling-specialization-v1;cleanup=preserve-io-dce-reachable-id-resources-v1;" +
        std::to_string(base.identity.size()) + ':' + base.identity + std::to_string(policy.size()) + ':' + policy;
}

inline std::string integer_sampling_generated_stage_error(const PortableShaderArtifact& original,
                                                         uint32_t stage_mask, const std::string& path) {
    for (const auto& use : original.integer_sample_uses) if (use.stage_mask & stage_mask)
        return path + ": integer normalized texture sampling requires specialization of the generated stage; this path is not implemented";
    return {};
}

inline std::shared_ptr<const PortableShaderArtifact> specialize_integer_sampled_shader(
    const std::shared_ptr<const PortableShaderArtifact>& base, const std::vector<IntegerSamplePolicy>& policies) {
    if (!base || !base->ok || base->integer_sample_uses.empty()) return base;
    auto artifact = std::make_shared<PortableShaderArtifact>(*base);
    artifact->timings = {};
    artifact->ok = false;
    artifact->error.clear();
    artifact->identity = integer_sampling_artifact_identity(*base, policies);
    artifact->cache_key = shader_identity_digest(artifact->identity);
    artifact->integer_sampling_identity = integer_sample_policy_identity(policies);
    artifact->integer_sampling_policies = policies;
    const auto started = shader_host_ns();
    auto fail = [&](const std::string& error) -> std::shared_ptr<const PortableShaderArtifact> {
        artifact->error = "integer sampling specialization: " + error;
        artifact->timings.integer_sampling_ns = artifact->timings.total_ns = shader_host_ns() - started;
        return artifact;
    };
    if (!base->integer_sampling_identity.empty()) return fail("a structural base artifact is required");
    if (artifact->identity.empty() || policies.size() != base->integer_sample_uses.size())
        return fail("exact valid policies for the active integer image pairs are required");
    for (const auto& use : base->integer_sample_uses) {
        const auto found = std::find_if(policies.begin(), policies.end(), [&](const auto& p) {
            return p.texture_binding == use.texture_binding && p.sampler_binding == use.sampler_binding && p.scalar == use.scalar;
        });
        if (found == policies.end()) return fail("policy differs from the active emitted image pair");
    }
    ++artifact->timings.integer_sampling_builds;
    auto vertex = lower_integer_nearest_2d(base->spv_vert, policies);
    auto fragment = lower_integer_nearest_2d(base->spv_frag, policies);
    if (!vertex.ok || !fragment.ok) return fail(!vertex.ok ? vertex.error : fragment.error);
    artifact->timings.integer_samples_lowered = vertex.samples_lowered + fragment.samples_lowered;
    auto live_vertex = finalize_sampled_stage(vertex.words, 1);
    auto live_fragment = finalize_sampled_stage(fragment.words, 2);
    if (!live_vertex.ok || !live_fragment.ok) return fail(!live_vertex.ok ? live_vertex.error : live_fragment.error);
    auto binding_stages = [&](uint32_t binding) {
        uint32_t stages = 0;
        for (const auto* uses : {&live_vertex.resource_usage, &live_fragment.resource_usage})
            for (const auto& use : *uses) if (use.binding == binding) stages |= use.stage_mask;
        return stages;
    };
    artifact->spv_vert = std::move(live_vertex.words);
    artifact->spv_frag = std::move(live_fragment.words);
    artifact->uniform_stage_mask = binding_stages(0);
    artifact->point_identity_binding = binding_stages(base->point_identity_binding) ? base->point_identity_binding : 0;
    artifact->vertex_identity_binding = binding_stages(base->vertex_identity_binding) ? base->vertex_identity_binding : 0;
    artifact->batch_instance_stage_mask = base->batch_instance_binding ? binding_stages(base->batch_instance_binding) : 0;
    artifact->batch_instance_binding = artifact->batch_instance_stage_mask ? base->batch_instance_binding : 0;
    // Stable sampler order preserves DrawSnap's value vector. Zero stage bits
    // mean that binding is absent from the actual specialized stage interface.
    for (auto& sampler : artifact->samplers) {
        sampler.texture_stage_mask = binding_stages(sampler.texture_binding);
        sampler.sampler_stage_mask = binding_stages(sampler.sampler_binding);
    }
    const auto reflection_started = shader_host_ns();
    if (!reflect_sampler_types(artifact->spv_vert, artifact->samplers, 1, artifact->error) ||
        !reflect_sampler_types(artifact->spv_frag, artifact->samplers, 2, artifact->error) ||
        ((artifact->uniform_stage_mask & 1) && !reflect_uniform_layout(artifact->spv_vert, artifact->uniforms, artifact->uniform_bytes, artifact->error)) ||
        ((artifact->uniform_stage_mask & 2) && !reflect_uniform_layout(artifact->spv_frag, artifact->uniforms, artifact->uniform_bytes, artifact->error)))
        return fail(artifact->error);
    artifact->timings.reflect_ns = shader_host_ns() - reflection_started;
    artifact->timings.integer_sampling_ns = artifact->timings.total_ns = shader_host_ns() - started;
    artifact->ok = true;
    return artifact;
}

inline std::string resource_limit_error(const std::vector<NormSampler>& samplers,
                                       uint32_t sampler_limit, uint32_t texture_limit) {
    for (uint32_t stage : {1u, 2u, 4u}) {
        uint32_t textures = 0, bindings = 0;
        for (const auto& sampler : samplers) {
            textures += (sampler.texture_stage_mask & stage) != 0;
            bindings += (sampler.sampler_stage_mask & stage) != 0;
        }
        const std::string label = stage == 1 ? "vertex" : stage == 2 ? "fragment" : "compute";
        if (bindings > sampler_limit) return label + " active samplers=" + std::to_string(bindings) +
            " exceed granted limit=" + std::to_string(sampler_limit);
        if (textures > texture_limit) return label + " active sampled textures=" + std::to_string(textures) +
            " exceed granted limit=" + std::to_string(texture_limit);
    }
    return {};
}

struct DeviceArtifactKey {
    uint64_t generation = 0;
    bool has_depth = false;

    friend bool operator==(const DeviceArtifactKey&, const DeviceArtifactKey&) = default;
    friend bool operator<(const DeviceArtifactKey& left, const DeviceArtifactKey& right) {
        return left.generation < right.generation ||
               (left.generation == right.generation && left.has_depth < right.has_depth);
    }
};

struct ExternalPortableBytes {
    size_t live_bytes = 0;
    size_t uncached_bytes = 0;
};

struct NoAuxiliary {};
struct ExternalAuxiliaryBytes {
    size_t live_bytes = 0;
    size_t uncached_bytes = 0;
};
struct NoConsumer {};
struct ExternalConsumerBytes {
    size_t live_bytes = 0;
    size_t uncached_bytes = 0;
};

// One identity owns portable data, optional auxiliary, policy-keyed consumers and device records.
// All lookup and FIFO identity views borrow the immutable portable's identity; neither copies
// a potentially enormous source key. The declared budget counts owned data
// capacities, records, fixed keys and conservative node/owner bookkeeping. It
// does not claim to measure driver allocations or allocator/RSS overhead.
// Caller serializes access (runtime already holds Engine::mu). Whole-entry
// eviction drops cache owners only; programs/snapshots remain usable.
template <class DeviceRecord, class AuxiliaryRecord = NoAuxiliary, class ConsumerRecord = NoConsumer>
class ShaderArtifactCache {
  public:
    using PortablePtr = std::shared_ptr<const PortableShaderArtifact>;
    using DevicePtr = std::shared_ptr<DeviceRecord>;
    using AuxiliaryPtr = std::shared_ptr<const AuxiliaryRecord>;
    using ConsumerPtr = std::shared_ptr<const ConsumerRecord>;

    explicit ShaderArtifactCache(size_t entries = 128, size_t bytes = 64u * 1024u * 1024u)
        : entry_limit_(entries), byte_limit_(bytes) {}
    ShaderArtifactCache(const ShaderArtifactCache&) = delete;
    ShaderArtifactCache& operator=(const ShaderArtifactCache&) = delete;
    ShaderArtifactCache(ShaderArtifactCache&& other) noexcept { *this = std::move(other); }
    ShaderArtifactCache& operator=(ShaderArtifactCache&& other) noexcept {
        if (this == &other) return *this;
        clear();
        entry_limit_ = other.entry_limit_;
        byte_limit_ = other.byte_limit_;
        entries_ = std::move(other.entries_);
        order_ = std::move(other.order_);
        storage_bytes_ = other.storage_bytes_;
        other.clear();
        return *this;
    }

    PortablePtr get_or_build(
        const std::string& vertex, const std::string& fragment, const NormalizeOptions& options,
        const std::string& compiler_identity, bool* cache_hit = nullptr, uint64_t* lookup_ns = nullptr,
        SpirvDerivativeMode derivative_mode = SpirvDerivativeMode::Strict) {
        const auto started = shader_host_ns();
        auto identity = portable_shader_identity(vertex, fragment, options, compiler_identity, derivative_mode);
        auto found = entries_.find(identity);
        if (cache_hit) *cache_hit = found != entries_.end();
        if (found != entries_.end()) {
            if (lookup_ns) *lookup_ns = shader_host_ns() - started;
            return found->second.portable;
        }
        const auto build_started = shader_host_ns();
        auto artifact = build_portable_shader(vertex, fragment, options, compiler_identity, derivative_mode);
        const auto build_finished = shader_host_ns();
        admit_portable(artifact);
        if (lookup_ns) *lookup_ns = (build_started - started) + (shader_host_ns() - build_finished);
        return artifact;
    }

    PortablePtr find_portable(std::string_view identity) const {
        auto found = entries_.find(identity);
        return found == entries_.end() ? nullptr : found->second.portable;
    }

    PortablePtr specialize_integer_sampling(const PortablePtr& base,
        const std::vector<IntegerSamplePolicy>& policies, bool* cache_hit = nullptr, uint64_t* lookup_ns = nullptr) {
        const auto started = shader_host_ns();
        if (cache_hit) *cache_hit = false;
        if (!base || !base->ok || base->integer_sample_uses.empty()) {
            if (cache_hit) *cache_hit = bool(base && base->ok);
            if (lookup_ns) *lookup_ns = shader_host_ns() - started;
            return base;
        }
        if (!base->integer_sampling_identity.empty() &&
            base->integer_sampling_identity == integer_sample_policy_identity(policies)) {
            if (cache_hit) *cache_hit = true;
            if (lookup_ns) *lookup_ns = shader_host_ns() - started;
            return base;
        }
        const auto identity = integer_sampling_artifact_identity(*base, policies);
        const auto found = identity.empty() ? entries_.end() : entries_.find(identity);
        if (found != entries_.end()) {
            if (cache_hit) *cache_hit = true;
            if (lookup_ns) *lookup_ns = shader_host_ns() - started;
            return found->second.portable;
        }
        const auto build_started = shader_host_ns();
        auto artifact = specialize_integer_sampled_shader(base, policies);
        const auto build_finished = shader_host_ns();
        if (artifact && artifact->ok) admit_portable(artifact);
        if (lookup_ns) *lookup_ns = (build_started - started) + (shader_host_ns() - build_finished);
        return artifact;
    }

    AuxiliaryPtr find_auxiliary(std::string_view identity) const {
        auto found = entries_.find(identity);
        return found == entries_.end() ? nullptr : found->second.auxiliary;
    }

    // The compatibility lookup must never choose one of several policies.
    ConsumerPtr find_consumer(std::string_view identity) const {
        auto found = entries_.find(identity);
        if (found == entries_.end() || found->second.consumers.size() != 1) return nullptr;
        const auto& value = *found->second.consumers.begin();
        return consistent_consumer(found->second.portable, found->second.auxiliary,
                                   value.first, value.second.record) ? value.second.record : nullptr;
    }

    ConsumerPtr find_consumer(std::string_view identity, std::string_view policy_identity) const {
        auto found = entries_.find(identity);
        if (found == entries_.end()) return nullptr;
        auto consumer = found->second.consumers.find(policy_identity);
        if (consumer == found->second.consumers.end()) return nullptr;
        return consistent_consumer(found->second.portable, found->second.auxiliary,
                                   consumer->first, consumer->second.record) ? consumer->second.record : nullptr;
    }

    // AuxiliaryRecord::original must be this exact portable allocation.
    // storage_bytes() includes all auxiliary-owned capacities (including any
    // policy/identity copies), but excludes the separately shared original.
    // Null-evaluator render device records may already exist at first admission.
    // Replacing an existing auxiliary with any cached device or consumer is
    // refused, including a retained consumer after device loss. External live
    // records remain independently usable and separately measured after loss
    // or whole-entry eviction; they never authorize pointer reparenting here.
    bool store_auxiliary(const PortablePtr& portable, const AuxiliaryPtr& auxiliary) {
        if constexpr (std::is_same_v<AuxiliaryRecord, NoAuxiliary>) return false;
        else {
            if (!portable || !auxiliary || auxiliary->original != portable) return false;
            auto found = entries_.find(portable->identity);
            if (found != entries_.end() && found->second.portable != portable) return false;
            if (found != entries_.end() && found->second.auxiliary &&
                found->second.auxiliary != auxiliary &&
                (!found->second.devices.empty() || !found->second.consumers.empty())) return false;
            if (found != entries_.end()) {
                for (const auto& [key, device] : found->second.devices)
                    if (!consistent_device(portable, auxiliary, found->second.consumers, device.record)) return false;
            }
            // A throwing footprint calculation cannot change existing owners.
            const size_t charge = auxiliary_bytes(*auxiliary);
            const size_t base = portable_bytes(*portable);
            const size_t existing = found == entries_.end() ? base : found->second.bytes;
            const size_t previous = found == entries_.end() ? 0 : found->second.auxiliary_bytes;
            const size_t requested = add_bytes(existing - previous, charge);
            if (!entry_limit_ || charge == SIZE_MAX || requested == SIZE_MAX || requested > byte_limit_)
                return false;  // No new owner was published; useful cached owners survive.
            if (found == entries_.end()) {
                make_room(requested, nullptr);
                found = insert_portable(portable, base);
            } else make_room(requested, &found->second);
            auto& entry = found->second;
            entry.auxiliary = auxiliary;
            entry.auxiliary_bytes = charge;
            storage_bytes_ = storage_bytes_ - entry.bytes + requested;
            entry.bytes = requested;
            return true;
        }
    }

    // Both overloads admit into the SAME variant collection and joint budget.
    // Keys borrow immutable strings owned by the retained consumer; its footprint
    // includes that string. Tree-node/shared-owner bookkeeping is charged here.
    // A policy key never authorizes replacing an identity-equal allocation.
    bool store_consumer(const PortablePtr& portable, const ConsumerPtr& consumer) {
        return store_consumer(portable, consumer_identity(consumer), consumer);
    }

    bool store_consumer(const PortablePtr& portable, std::string_view policy_identity,
                        const ConsumerPtr& consumer) {
        if constexpr (std::is_same_v<ConsumerRecord, NoConsumer> ||
                      std::is_same_v<AuxiliaryRecord, NoAuxiliary>) return false;
        else {
            if (!portable || !consumer || policy_identity.empty() ||
                policy_identity != consumer_identity(consumer)) return false;
            auto found = entries_.find(portable->identity);
            if (found == entries_.end() || found->second.portable != portable ||
                !consistent_consumer(portable, found->second.auxiliary, policy_identity, consumer)) return false;
            auto previous = found->second.consumers.find(policy_identity);
            if (previous != found->second.consumers.end() && previous->second.record != consumer) return false;
            for (const auto& [key, device] : found->second.devices)
                if (!consistent_device(portable, found->second.auxiliary,
                                       found->second.consumers, device.record)) return false;
            // A throwing footprint or overflow cannot evict existing owners.
            const size_t charge = consumer_bytes(*consumer);
            const size_t prior = previous == found->second.consumers.end() ? 0 : previous->second.bytes;
            const size_t requested = add_bytes(found->second.bytes - prior, charge);
            if (!entry_limit_ || charge == SIZE_MAX || requested == SIZE_MAX || requested > byte_limit_) return false;
            // Allocate a prospective node before eviction/publication. Node-handle
            // transfer into this map cannot allocate, and keys have equal allocators.
            Consumers pending;
            if (previous == found->second.consumers.end())
                pending.emplace(consumer_identity(consumer), CachedConsumer{consumer, charge});
            make_room(requested, &found->second);
            auto& entry = found->second;
            if (previous == entry.consumers.end()) entry.consumers.insert(pending.extract(pending.begin()));
            else previous->second.bytes = charge;
            entry.consumer_bytes = entry.consumer_bytes - prior + charge;
            storage_bytes_ = storage_bytes_ - entry.bytes + requested;
            entry.bytes = requested;
            return true;
        }
    }

    DevicePtr find_device(std::string_view identity, DeviceArtifactKey key) const {
        auto found = entries_.find(identity);
        if (found == entries_.end()) return nullptr;
        auto device = found->second.devices.find(key);
        return device == found->second.devices.end() ? nullptr : device->second.record;
    }

    // The record must retain only this supplied portable allocation. Callers
    // canonicalize saved artifacts with find_portable before constructing GPU
    // records; an identity-equal but different allocation is rejected here.
    // owned_record_bytes includes sizeof(DeviceRecord), nested key/diagnostic
    // capacities and containers, but excludes shared portable/auxiliary/consumer
    // allocations. Nonnull evaluator/consumer fields must match their admitted
    // owners; consumer-backed devices retain the full exact triple.
    bool store_device(const PortablePtr& portable, DeviceArtifactKey key,
                      const DevicePtr& record, size_t owned_record_bytes) {
        if (!portable || !record || !key.generation) return false;
        if constexpr (requires { record->portable != portable; })
            if (record->portable != portable) return false;
        auto found = entries_.find(portable->identity);
        if (found != entries_.end() && found->second.portable != portable) return false;
        const Consumers empty_consumers;
        const auto& consumers = found == entries_.end() ? empty_consumers : found->second.consumers;
        if (!consistent_device(portable, found == entries_.end() ? AuxiliaryPtr{} : found->second.auxiliary,
                               consumers, record))
            return false;
        const size_t record_bytes = device_bytes(owned_record_bytes);
        const size_t base = portable_bytes(*portable);
        size_t previous = 0;
        if (found != entries_.end()) {
            auto device = found->second.devices.find(key);
            if (device != found->second.devices.end()) previous = device->second.bytes;
        }
        const size_t existing = found == entries_.end() ? base : found->second.bytes;
        const size_t requested = add_bytes(existing - previous, record_bytes);
        if (!entry_limit_ || requested == SIZE_MAX || requested > byte_limit_) {
            if (found != entries_.end()) erase_entry(found);
            return false;
        }
        if (found == entries_.end()) {
            make_room(requested, nullptr);
            found = insert_portable(portable, base);
        } else make_room(requested, &found->second);
        auto& entry = found->second;
        entry.devices.insert_or_assign(key, CachedDevice{record, record_bytes});
        storage_bytes_ = storage_bytes_ - entry.bytes + requested;
        entry.bytes = requested;
        return true;
    }

    // Device variants/errors are mutable. Runtime refreshes this charge after
    // changing them; growth beyond the budget releases the entire cache entry.
    bool refresh_device(std::string_view identity, DeviceArtifactKey key, size_t owned_record_bytes) {
        auto found = entries_.find(identity);
        if (found == entries_.end()) return false;
        auto device = found->second.devices.find(key);
        if (device == found->second.devices.end()) return false;
        if (!consistent_device(found->second.portable, found->second.auxiliary,
                               found->second.consumers, device->second.record)) {
            erase_entry(found);  // Mutable records cannot retain an uncharged CPU graph.
            return false;
        }
        const size_t record_bytes = device_bytes(owned_record_bytes);
        const size_t requested = add_bytes(found->second.bytes - device->second.bytes, record_bytes);
        if (requested == SIZE_MAX || requested > byte_limit_) { erase_entry(found); return false; }
        make_room(requested, &found->second);
        storage_bytes_ = storage_bytes_ - found->second.bytes + requested;
        found->second.bytes = requested;
        device->second.bytes = record_bytes;
        return true;
    }

    template <class Callback>
    void for_each_device(Callback&& callback) const {
        for (const auto& [identity, entry] : entries_)
            for (const auto& [key, device] : entry.devices) callback(device.record);
    }

    template <class Callback>
    void for_each_auxiliary(Callback&& callback) const {
        for (const auto& [identity, entry] : entries_)
            if (entry.auxiliary) callback(entry.auxiliary);
    }

    template <class Callback>
    void for_each_consumer(Callback&& callback) const {
        for (const auto& [identity, entry] : entries_)
            for (const auto& [policy, consumer] : entry.consumers) callback(consumer.record);
    }

    // Root supplies all live program/pending references. Count each immutable
    // allocation once, including identity-equal allocations created while an
    // earlier live program was uncached. uncached_bytes is the portion whose
    // exact allocation is retained only outside this cache.
    template <class Range>
    ExternalPortableBytes external_portable_bytes(const Range& references) const {
        return external_portable_bytes(references, std::vector<AuxiliaryPtr>{});
    }

    // Include auxiliary originals in the SAME allocation set as explicit
    // portable references. The immutable original owner must not disappear
    // from measurements merely because a program retains only its evaluator.
    template <class Range, class AuxiliaryRange>
    ExternalPortableBytes external_portable_bytes(const Range& references,
                                                 const AuxiliaryRange& auxiliaries) const {
        return external_portable_bytes(references, auxiliaries, std::vector<ConsumerPtr>{});
    }

    // Follow consumer -> evaluator -> original even when no explicit original
    // or evaluator reference was supplied. Allocation identity, not text identity,
    // determines deduplication, including malformed outside graphs.
    template <class Range, class AuxiliaryRange, class ConsumerRange>
    ExternalPortableBytes external_portable_bytes(const Range& references,
                                                 const AuxiliaryRange& auxiliaries,
                                                 const ConsumerRange& consumers) const {
        ExternalPortableBytes result;
        std::unordered_set<const PortableShaderArtifact*> seen;
        auto count = [&](const PortablePtr& portable) {
            if (!portable || !seen.insert(portable.get()).second) return;
            const size_t bytes = portable->storage_bytes();
            result.live_bytes = add_bytes(result.live_bytes, bytes);
            auto cached = find_portable(portable->identity);
            if (cached != portable) result.uncached_bytes = add_bytes(result.uncached_bytes, bytes);
        };
        for (const auto& portable : references) count(portable);
        if constexpr (!std::is_same_v<AuxiliaryRecord, NoAuxiliary>)
            for (const auto& auxiliary : auxiliaries) if (auxiliary) count(auxiliary->original);
        if constexpr (!std::is_same_v<ConsumerRecord, NoConsumer>)
            for (const auto& consumer : consumers) if (consumer) {
                count(consumer->original);
                if (consumer->evaluator) count(consumer->evaluator->original);
            }
        return result;
    }

    template <class Range>
    ExternalAuxiliaryBytes external_auxiliary_bytes(const Range& references) const {
        return external_auxiliary_bytes(references, std::vector<ConsumerPtr>{});
    }

    template <class Range, class ConsumerRange>
    ExternalAuxiliaryBytes external_auxiliary_bytes(const Range& references,
                                                    const ConsumerRange& consumers) const {
        ExternalAuxiliaryBytes result;
        if constexpr (!std::is_same_v<AuxiliaryRecord, NoAuxiliary>) {
            std::unordered_set<const AuxiliaryRecord*> seen;
            auto count = [&](const AuxiliaryPtr& auxiliary) {
                if (!auxiliary || !seen.insert(auxiliary.get()).second) return;
                const size_t bytes = auxiliary->storage_bytes();
                result.live_bytes = add_bytes(result.live_bytes, bytes);
                if (!auxiliary->original ||
                    find_portable(auxiliary->original->identity) != auxiliary->original ||
                    find_auxiliary(auxiliary->original->identity) != auxiliary)
                    result.uncached_bytes = add_bytes(result.uncached_bytes, bytes);
            };
            for (const auto& auxiliary : references) count(auxiliary);
            if constexpr (!std::is_same_v<ConsumerRecord, NoConsumer>)
                for (const auto& consumer : consumers) if (consumer) count(consumer->evaluator);
        }
        return result;
    }

    template <class Range>
    ExternalConsumerBytes external_consumer_bytes(const Range& references) const {
        ExternalConsumerBytes result;
        if constexpr (!std::is_same_v<ConsumerRecord, NoConsumer>) {
            std::unordered_set<const ConsumerRecord*> seen;
            for (const auto& consumer : references) {
                if (!consumer || !seen.insert(consumer.get()).second) continue;
                const size_t bytes = consumer_owned_bytes(*consumer);
                result.live_bytes = add_bytes(result.live_bytes, bytes);
                bool cached = consumer->original &&
                    find_portable(consumer->original->identity) == consumer->original &&
                    find_consumer(consumer->original->identity, consumer_identity(consumer)) == consumer;
                if constexpr (std::is_same_v<AuxiliaryRecord, NoAuxiliary>) cached = false;
                else cached = cached && consumer->evaluator &&
                    consumer->evaluator->original == consumer->original &&
                    find_auxiliary(consumer->original->identity) == consumer->evaluator;
                if (!cached)
                    result.uncached_bytes = add_bytes(result.uncached_bytes, bytes);
            }
        }
        return result;
    }

    size_t size() const { return portable_size(); }
    size_t portable_size() const { return entries_.size(); }
    size_t device_size() const {
        size_t count = 0;
        for (const auto& [identity, entry] : entries_) count += entry.devices.size();
        return count;
    }
    size_t auxiliary_size() const {
        size_t count = 0;
        for (const auto& [identity, entry] : entries_) count += bool(entry.auxiliary);
        return count;
    }
    size_t consumer_size() const {
        size_t count = 0;
        for (const auto& [identity, entry] : entries_) count += entry.consumers.size();
        return count;
    }
    size_t storage_bytes() const { return storage_bytes_; }
    size_t byte_limit() const { return byte_limit_; }
    size_t portable_storage_bytes() const {
        size_t bytes = 0;
        for (const auto& [identity, entry] : entries_) bytes = add_bytes(bytes, entry.portable->storage_bytes());
        return bytes;
    }
    // Owned allocation capacities only; original and cache bookkeeping are
    // excluded. storage_bytes() is the complete joint cache budget charge.
    size_t auxiliary_storage_bytes() const {
        size_t bytes = 0;
        if constexpr (!std::is_same_v<AuxiliaryRecord, NoAuxiliary>)
            for (const auto& [identity, entry] : entries_)
                if (entry.auxiliary) bytes = add_bytes(bytes, entry.auxiliary->storage_bytes());
        return bytes;
    }
    size_t consumer_storage_bytes() const {
        size_t bytes = 0;
        if constexpr (!std::is_same_v<ConsumerRecord, NoConsumer>)
            for (const auto& [identity, entry] : entries_)
                for (const auto& [policy, consumer] : entry.consumers)
                    bytes = add_bytes(bytes, consumer_owned_bytes(*consumer.record));
        return bytes;
    }
    void clear_devices() {
        for (auto& [identity, entry] : entries_) {
            entry.devices.clear();
            const size_t base = add_bytes(add_bytes(portable_bytes(*entry.portable), entry.auxiliary_bytes),
                                          entry.consumer_bytes);
            storage_bytes_ -= entry.bytes - base;
            entry.bytes = base;
        }
    }
    void clear() { order_.clear(); entries_.clear(); storage_bytes_ = 0; }

  private:
    struct CachedDevice { DevicePtr record; size_t bytes; };
    struct CachedConsumer { ConsumerPtr record; size_t bytes; };
    using Consumers = std::map<std::string_view, CachedConsumer, std::less<>>;
    struct Entry {
        PortablePtr portable;
        size_t bytes;
        std::map<DeviceArtifactKey, CachedDevice> devices;
        AuxiliaryPtr auxiliary;
        size_t auxiliary_bytes = 0;
        Consumers consumers;
        size_t consumer_bytes = 0;
    };
    using Entries = std::map<std::string_view, Entry, std::less<>>;
    // Tree nodes need links/color/alignment; shared owners need their control
    // bookkeeping. Charge these fixed allowances in addition to value sizes.
    static constexpr size_t node_bookkeeping = 4 * sizeof(void*);
    static constexpr size_t owner_bookkeeping = 4 * sizeof(void*);
    static size_t add_bytes(size_t left, size_t right) {
        return right > std::numeric_limits<size_t>::max() - left
                   ? std::numeric_limits<size_t>::max() : left + right;
    }
    static size_t portable_bytes(const PortableShaderArtifact& portable) {
        return add_bytes(portable.storage_bytes(), sizeof(typename Entries::value_type) + node_bookkeeping +
                         sizeof(std::string_view) + 2 * sizeof(void*) + owner_bookkeeping);
    }
    static size_t device_bytes(size_t owned_record_bytes) {
        using DeviceMap = std::map<DeviceArtifactKey, CachedDevice>;
        return add_bytes(std::max(sizeof(DeviceRecord), owned_record_bytes),
                         sizeof(typename DeviceMap::value_type) + node_bookkeeping + owner_bookkeeping);
    }
    static size_t auxiliary_bytes(const AuxiliaryRecord& auxiliary) {
        if constexpr (std::is_same_v<AuxiliaryRecord, NoAuxiliary>) return 0;
        else return add_bytes(std::max(sizeof(AuxiliaryRecord), auxiliary.storage_bytes()), owner_bookkeeping);
    }
    static size_t consumer_owned_bytes(const ConsumerRecord& consumer) {
        if constexpr (std::is_same_v<ConsumerRecord, NoConsumer>) return 0;
        else {
            // Even a generic footprint cannot undercharge the full borrowed key.
            const size_t key_capacity = [&] {
                if constexpr (requires { consumer.policy_identity; }) return consumer.policy_identity.capacity();
                else return consumer.identity.capacity();
            }();
            return std::max(consumer.storage_bytes(), add_bytes(sizeof(ConsumerRecord), add_bytes(key_capacity, 1)));
        }
    }
    static size_t consumer_bytes(const ConsumerRecord& consumer) {
        if constexpr (std::is_same_v<ConsumerRecord, NoConsumer>) return 0;
        else return add_bytes(consumer_owned_bytes(consumer),
                              sizeof(typename Consumers::value_type) + node_bookkeeping + owner_bookkeeping);
    }
    static std::string_view consumer_identity(const ConsumerPtr& consumer) {
        if constexpr (std::is_same_v<ConsumerRecord, NoConsumer>) return {};
        else {
            if (!consumer) return {};
            if constexpr (requires { consumer->policy_identity; }) return consumer->policy_identity;
            else return consumer->identity;  // Inherited generic record's full immutable identity.
        }
    }
    static bool consistent_consumer(const PortablePtr& portable, const AuxiliaryPtr& auxiliary,
                                    std::string_view policy, const ConsumerPtr& consumer) {
        if constexpr (std::is_same_v<ConsumerRecord, NoConsumer> ||
                      std::is_same_v<AuxiliaryRecord, NoAuxiliary>) return false;
        else {
            if (!consumer || !portable || policy.empty() || policy != consumer_identity(consumer) ||
                consumer->original != portable || !consumer->evaluator || consumer->evaluator != auxiliary ||
                consumer->evaluator->original != portable) return false;
            if constexpr (requires { consumer->ok; }) if (!consumer->ok) return false;
            return true;
        }
    }
    static bool consistent_device(const PortablePtr& portable, const AuxiliaryPtr& auxiliary,
                                  const Consumers& consumers, const DevicePtr& record) {
        for (const auto& [policy, consumer] : consumers)
            if (!consistent_consumer(portable, auxiliary, policy, consumer.record)) return false;
        if constexpr (requires { record->portable != portable; })
            if (record->portable != portable) return false;
        if constexpr (requires { record->evaluator; }) {
            if constexpr (std::is_same_v<AuxiliaryRecord, NoAuxiliary>) {
                if (record->evaluator) return false;
            } else if (record->evaluator && record->evaluator != auxiliary) return false;
        }
        if constexpr (requires { record->consumer; }) {
            if constexpr (std::is_same_v<ConsumerRecord, NoConsumer> ||
                          std::is_same_v<AuxiliaryRecord, NoAuxiliary>) {
                if (record->consumer) return false;
            } else if (record->consumer) {
                auto admitted = consumers.find(consumer_identity(record->consumer));
                if (admitted == consumers.end() || admitted->second.record != record->consumer ||
                    !consistent_consumer(portable, auxiliary, admitted->first, record->consumer)) return false;
                if constexpr (requires { record->evaluator; })
                    if (record->evaluator != auxiliary) return false;
            }
        }
        // Optional runtime subrecords must all retain canonical admitted CPU
        // consumers. Checking a selected singleton must not hide a foreign
        // policy graph elsewhere in the same mutable device record.
        if constexpr (requires { record->for_each_consumer([](std::string_view, const auto&) {}); }) {
            bool valid = true;
            record->for_each_consumer([&](std::string_view policy, const auto& candidate) {
                if constexpr (std::is_same_v<ConsumerRecord, NoConsumer> ||
                              std::is_same_v<AuxiliaryRecord, NoAuxiliary> ||
                              !std::is_convertible_v<decltype(candidate), ConsumerPtr>) {
                    valid = false;
                } else {
                    auto admitted = consumers.find(policy);
                    if (admitted == consumers.end() || admitted->second.record != candidate ||
                        !consistent_consumer(portable, auxiliary, policy, candidate)) valid = false;
                    if constexpr (requires { record->evaluator; })
                        if (record->evaluator != auxiliary) valid = false;
                }
            });
            if (!valid) return false;
        }
        return true;
    }
    typename Entries::iterator insert_portable(const PortablePtr& portable, size_t bytes) {
        const std::string_view identity = portable->identity;
        auto inserted = entries_.emplace(identity, Entry{portable, bytes, {}, {}, 0, {}, 0}).first;
        try { order_.push_back(identity); }
        catch (...) { entries_.erase(inserted); throw; }
        storage_bytes_ += bytes;
        return inserted;
    }
    void erase_entry(typename Entries::iterator entry) {
        // Destroy borrowed FIFO views before releasing their backing owner.
        auto order = std::find(order_.begin(), order_.end(), entry->first);
        if (order != order_.end()) order_.erase(order);
        storage_bytes_ -= entry->second.bytes;
        entries_.erase(entry);
    }
    void make_room(size_t requested, const Entry* retained) {
        while ((!retained && entries_.size() >= entry_limit_) ||
               requested > byte_limit_ - (storage_bytes_ - (retained ? retained->bytes : 0))) {
            auto oldest = order_.begin();
            while (oldest != order_.end() && &entries_.find(*oldest)->second == retained) ++oldest;
            if (oldest == order_.end()) break;  // requested alone was checked by the caller.
            erase_entry(entries_.find(*oldest));
        }
    }
    void admit_portable(const PortablePtr& portable) {
        const size_t bytes = portable_bytes(*portable);
        if (!entry_limit_ || bytes == SIZE_MAX || bytes > byte_limit_) return;
        make_room(bytes, nullptr);
        insert_portable(portable, bytes);
    }
    size_t entry_limit_ = 0;
    size_t byte_limit_ = 0;
    size_t storage_bytes_ = 0;
    Entries entries_;
    std::list<std::string_view> order_;
};

struct NoDeviceShaderRecord {};
using PortableShaderCache = ShaderArtifactCache<NoDeviceShaderRecord>;

// Handle types are supplied by runtime, keeping this header CPU-testable and
// independent of Dawn. Device generation is checked before reusing GPU state.
template <class ShaderModule, class RenderPipeline, class BindGroupLayout>
struct DeviceShaderArtifact {
    uint64_t device_generation = 0;
    ShaderModule vert_module;
    ShaderModule frag_module;
    RenderPipeline pipeline;
    BindGroupLayout bind_layout;
    std::unordered_map<std::string, RenderPipeline> variants;
    std::list<std::string> variant_order;
    bool pipeline_ok = false;
    std::string error;

    bool valid_for(uint64_t generation) const {
        return generation != 0 && generation == device_generation && pipeline_ok;
    }
    // Includes variant map/FIFO key copies and diagnostic capacity. The caller
    // supplies sizeof(derived record)-sizeof(this base), excluding shared
    // portable/auxiliary data counted once at its owning identity entry.
    size_t storage_bytes(size_t extra_record_bytes = 0) const {
        size_t bytes = sizeof(*this) + extra_record_bytes + error.capacity() + 1;
        bytes += variants.bucket_count() * 2 * sizeof(void*);
        for (const auto& [key, pipeline] : variants)
            bytes += sizeof(typename decltype(variants)::value_type) + 4 * sizeof(void*) + key.capacity() + 1;
        for (const auto& key : variant_order)
            bytes += sizeof(std::string) + 2 * sizeof(void*) + key.capacity() + 1;
        bytes += 2 * sizeof(void*);  // list sentinel bookkeeping.
        return bytes;
    }
    void invalidate() {
        vert_module = ShaderModule{};
        frag_module = ShaderModule{};
        pipeline = RenderPipeline{};
        bind_layout = BindGroupLayout{};
        variants.clear();
        variant_order.clear();
        pipeline_ok = false;
        device_generation = 0;
        error.clear();
    }
};

}  // namespace vispy::shader
