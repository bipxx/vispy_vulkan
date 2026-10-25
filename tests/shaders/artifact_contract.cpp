#include "shader/artifact.hpp"
#include "attribute_binding_contract.hpp"

#include <SPIRV/spirv.hpp11>

#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using namespace vispy::shader;
const std::string vertex = "attribute vec2 p; void main(){ gl_Position=vec4(p,0,1); }";
const std::string fragment = "uniform mat3 matrix; void main(){ gl_FragColor=vec4(matrix[1][2]); }";
const std::string pins = "contract-compiler-pins";
const std::string sampled_fragment = "uniform sampler2D u_image; void main(){ "
    "vec4 value=texture2D(u_image,vec2(0.5)); "
    "if(gl_FragCoord.x > 0.5) value += vec4(dFdx(gl_FragCoord.x)); gl_FragColor=value; }";

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

void identity_and_provenance() {
    NormalizeOptions options;
    auto first = portable_shader_identity("ab", "c", options, pins);
    auto second = portable_shader_identity("a", "bc", options, pins);
    require(first != second, "vertex/fragment boundary must not alias");
    require(first != portable_shader_identity("ab", "c", options, pins + "-changed"), "compiler pin identity participates");
    auto reversed = options;
    reversed.reverse_depth = true;
    require(first != portable_shader_identity("ab", "c", reversed, pins), "depth orientation participates");
    auto base = options;
    base.base_level_sampling = true;
    require(first != portable_shader_identity("ab", "c", base, pins), "sampling policy participates");
    auto points = options;
    points.point_sprites = true;
    require(first != portable_shader_identity("ab", "c", points, pins), "point policy participates");

    PortableShaderCache cache;
    bool hit = true;
    uint64_t lookup_ns = 0;
    auto artifact = cache.get_or_build(vertex, fragment, options, pins, &hit, &lookup_ns);
    require(artifact->ok && !hit, artifact->error);
    require(lookup_ns > 0 && artifact->timings.normalizations == 1 && artifact->timings.parse_calls == 2 &&
            artifact->timings.link_calls == 1 && artifact->timings.spirv_stages == 2,
            "actual compiler stage calls and lookup interval are retained");
    const auto timings = artifact->timings;
    require(timings.normalize_ns > 0 && timings.parse_ns > 0 && timings.link_ns > 0 && timings.spirv_ns > 0 &&
            timings.reflect_ns > 0 && timings.total_ns >= timings.normalize_ns + timings.parse_ns +
                timings.link_ns + timings.spirv_ns + timings.reflect_ns,
            "monotonic host compiler stages are contained in the inclusive build interval");
    lookup_ns = 0;
    auto again = cache.get_or_build(vertex, fragment, options, pins, &hit, &lookup_ns);
    require(hit && artifact == again, "cache reuses immutable portable artifact");
    require(lookup_ns > 0 && again->timings.total_ns == timings.total_ns &&
            again->timings.parse_ns == timings.parse_ns && again->timings.spirv_ns == timings.spirv_ns,
            "cache hits expose lookup time without replacing retained historical stage times");
    require(artifact->uniforms.size() == 1 && artifact->uniforms[0].matrix_stride == 16, "portable artifact retains reflected matrix packing");
    require(!artifact->spv_vert.empty() && !artifact->spv_frag.empty(), "validated SPIR-V retained");
    require(artifact->source_fragment == fragment && !artifact->frag_map.empty(), "original source and mapping retained");
    auto changed_source = cache.get_or_build(vertex, "// composer provenance\n" + fragment, options, pins, &hit);
    require(!hit && changed_source != artifact && changed_source->ok, "source provenance cannot alias another artifact");
    require(changed_source->source_fragment != artifact->source_fragment, "cached sources are immutable");
}

void device_loss_preserves_portable() {
    PortableShaderCache cache;
    auto portable = cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    const auto words = portable->spv_frag;
    const auto map = portable->frag_map;
    using Handle = std::shared_ptr<int>;
    DeviceShaderArtifact<Handle, Handle, Handle> device;
    device.device_generation = 7;
    device.vert_module = std::make_shared<int>(1);
    device.frag_module = std::make_shared<int>(2);
    device.pipeline = std::make_shared<int>(3);
    device.bind_layout = std::make_shared<int>(4);
    device.variants.emplace("draw-state", std::make_shared<int>(5));
    device.variant_order.push_back("draw-state");
    device.pipeline_ok = true;
    std::weak_ptr<int> old_module = device.vert_module;
    std::weak_ptr<int> old_variant = device.variants.begin()->second;
    require(device.valid_for(7) && !device.valid_for(8) && !device.valid_for(0), "device generation gates reuse");
    device.error = "old device diagnostic";
    device.invalidate();
    require(!device.valid_for(7) && old_module.expired() && old_variant.expired(), "invalidation releases GPU ownership");
    require(!device.bind_layout && device.variants.empty() && device.variant_order.empty() && device.error.empty(), "all device state is invalidated");
    bool hit = false;
    auto recovered = cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit);
    require(hit && recovered == portable && recovered->spv_frag == words && recovered->frag_map == map,
            "device recovery reuses SPIR-V and source maps without recompilation");

    auto depth = cache.get_or_build(vertex, "void main(){ gl_FragDepth=.25; gl_FragColor=vec4(1); }", NormalizeOptions{}, pins);
    require(depth->ok && depth->has_fragment_depth, "fragment depth is portable metadata, attachment availability is device policy");
}

void bounded_ownership_and_failures() {
    PortableShaderCache one(1);
    auto retained = one.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    auto next = one.get_or_build(vertex, "void main(){ gl_FragColor=vec4(1); }", NormalizeOptions{}, pins);
    require(one.size() == 1 && next->ok && retained->ok && !retained->spv_frag.empty(), "eviction preserves live program ownership");
    bool hit = true;
    auto rebuilt = one.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit);
    require(!hit && rebuilt != retained && one.size() == 1, "entry bound enforced");
    one.clear();
    require(one.size() == 0 && one.storage_bytes() == 0 && retained->ok, "shutdown drops cache ownership without mutating snapshots");

    PortableShaderCache tiny(128, 1);
    auto uncached = tiny.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit);
    require(uncached->ok && !hit && tiny.size() == 0 && tiny.storage_bytes() == 0, "oversized artifacts are returned without cache admission");

    PortableShaderCache measured;
    measured.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    const size_t budget = measured.storage_bytes();
    PortableShaderCache byte_limited(128, budget);
    auto resident = byte_limited.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    const std::string large_fragment = "//" + std::string(budget, 'x') + "\n" + fragment;
    auto large = byte_limited.get_or_build(vertex, large_fragment, NormalizeOptions{}, pins, &hit);
    require(large->ok && !hit && byte_limited.size() == 1 && byte_limited.storage_bytes() <= budget,
            "oversized admission keeps the existing bounded cache resident");
    require(byte_limited.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit) == resident && hit,
            "uncached large shaders do not evict useful resident artifacts");

    PortableShaderCache failures;
    const std::string invalid = "void main(){\n gl_FragColor=vec4(1);\n missing_name;\n}\n";
    auto failed = failures.get_or_build(vertex, invalid, NormalizeOptions{}, pins, &hit);
    require(!hit && !failed->ok && !failed->error.empty() && failed->mapped_line == 3, "compiler failure retains original diagnostic line");
    require(failed->error.find("fragment source line=3:  missing_name;") != std::string::npos,
            "compiler failure includes original source context");
    auto same_failure = failures.get_or_build(vertex, invalid, NormalizeOptions{}, pins, &hit);
    require(hit && failed == same_failure && same_failure->source_fragment == invalid, "deterministic CPU failures retain diagnostics across device changes");
    auto vertex_failure = failures.get_or_build("void main(){\n gl_Position=vec4(0);\n missing_vertex;\n}\n",
        "void main(){gl_FragColor=vec4(1);}", NormalizeOptions{}, pins);
    require(!vertex_failure->ok && vertex_failure->mapped_line == 3 && !vertex_failure->vertex_log.empty(),
            "vertex error uses its original source map despite a different fragment header shift");

    const auto both = build_portable_shader("void main(){\n error on this line\n}",
        "void main(){ glFragColor = vec4(1); }", {}, pins);
    require(!both->ok && both->error.find("vertex source line=2:  error on this line") != std::string::npos &&
        both->error.find("fragment source line=1: void main(){ glFragColor = vec4(1); }") != std::string::npos,
        "simultaneous stage failures retain each original source line");
    auto normalized_failure = failures.get_or_build(vertex,
        "uniform sampler2D image; void main(){ gl_FragColor=texture2D(image,vec2(.5),1.0); }",
        NormalizeOptions{true}, pins);
    require(!normalized_failure->ok && normalized_failure->error.find("bias") != std::string::npos,
            "normalizer admission diagnostics survive the portable boundary");
    require(normalized_failure->timings.normalizations == 1 && normalized_failure->timings.total_ns > 0 &&
            normalized_failure->timings.parse_calls == 0 && normalized_failure->timings.link_calls == 0 &&
            normalized_failure->timings.spirv_stages == 0,
            "normalization rejection charges no compiler stages that never ran");
}

void per_stage_resource_limits() {
    auto sampler = [](const char* name, uint32_t texture_stages, uint32_t sampler_stages) {
        NormSampler value;
        value.name = name;
        value.dim = "2d";
        value.texture_stage_mask = texture_stages;
        value.sampler_stage_mask = sampler_stages;
        return value;
    };
    const std::vector<NormSampler> compute{sampler("image_a", 4, 4), sampler("image_b", 4, 4)};
    require(resource_limit_error(compute, 1, 2) == "compute active samplers=2 exceed granted limit=1",
            "compute-only active samplers must obey the actual granted compute limit");
    require(resource_limit_error(compute, 2, 1) == "compute active sampled textures=2 exceed granted limit=1",
            "compute sampled texture capacity is independently admitted");
    require(resource_limit_error(compute, 2, 2).empty(), "exact compute sampler and texture limits are legal");
    const std::vector<NormSampler> compute_loads{sampler("load_a", 4, 0), sampler("load_b", 4, 0)};
    require(resource_limit_error(compute_loads, 0, 1) == "compute active sampled textures=2 exceed granted limit=1" &&
            resource_limit_error(compute_loads, 0, 2).empty(),
            "compute texture loads consume textures without inventing sampler bindings");
    const std::vector<NormSampler> mixed{sampler("vertex_image", 1, 1), sampler("fragment_image", 2, 2),
        sampler("compute_image", 4, 4), sampler("inactive", 0, 0)};
    require(resource_limit_error(mixed, 1, 1).empty(), "limits apply per stage, not to a combined render/compute resource sum");
    auto shared = mixed;
    shared.push_back(sampler("shared_image", 7, 7));
    require(resource_limit_error(shared, 2, 2).empty(), "shared resource bindings count once in each participating stage");
    shared.push_back(sampler("compute_extra", 4, 0));
    require(resource_limit_error(shared, 2, 2) == "compute active sampled textures=3 exceed granted limit=2",
            "compute overflow is still checked after legal mixed vertex and fragment usage");
    require(resource_limit_error({sampler("v1", 1, 1), sampler("v2", 1, 1)}, 1, 1) ==
                "vertex active samplers=2 exceed granted limit=1" &&
            resource_limit_error({sampler("f1", 2, 2), sampler("f2", 2, 2)}, 2, 1) ==
                "fragment active sampled textures=2 exceed granted limit=1",
            "existing vertex and fragment diagnostics retain their stage labels and priority");
}

using Handle = std::shared_ptr<int>;
using DeviceBase = DeviceShaderArtifact<Handle, Handle, Handle>;
struct FakeDevice : DeviceBase {
    std::shared_ptr<const PortableShaderArtifact> portable;
};
using UnifiedCache = ShaderArtifactCache<FakeDevice>;

std::shared_ptr<FakeDevice> fake_device(const std::shared_ptr<const PortableShaderArtifact>& portable,
                                      uint64_t generation) {
    auto device = std::make_shared<FakeDevice>();
    device->portable = portable;
    device->device_generation = generation;
    device->pipeline = std::make_shared<int>(1);
    device->pipeline_ok = true;
    return device;
}

size_t record_bytes(const FakeDevice& record) {
    return record.storage_bytes(sizeof(FakeDevice) - sizeof(DeviceBase));
}

void derivative_policy_identity_and_recovery() {
    require(PortableShaderArtifact{}.derivative_mode == SpirvDerivativeMode::Strict,
            "new portable artifacts default to strict SPIR-V ingestion");
    UnifiedCache cache;
    bool hit = true;
    auto strict = cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit);
    require(strict->ok && !hit && strict->derivative_mode == SpirvDerivativeMode::Strict,
            "legacy cache callers capture strict ingestion by default");
    auto compatible = cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit, nullptr,
        SpirvDerivativeMode::AllowNonUniform);
    require(compatible->ok && !hit && compatible->derivative_mode == SpirvDerivativeMode::AllowNonUniform &&
            strict->identity != compatible->identity && strict->cache_key != compatible->cache_key,
            "explicit render compatibility has a distinct identity and display key");
    const auto framed_pins = std::to_string(pins.size()) + ':' + pins;
    require(strict->identity.find("render-spirv-derivatives=strict-v1;") < strict->identity.find(framed_pins) &&
            compatible->identity.find("render-spirv-derivatives=allow-nonuniform-v1;") < compatible->identity.find(framed_pins),
            "versioned render ingestion policy precedes framed compiler provenance");
    require(strict->vertex == compatible->vertex && strict->fragment == compatible->fragment &&
            strict->spv_vert == compatible->spv_vert && strict->spv_frag == compatible->spv_frag &&
            strict->vert_map == compatible->vert_map && strict->frag_map == compatible->frag_map,
            "ingestion permission preserves normalized shaders, SPIR-V and source mappings");
    require(cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit) == strict && hit,
            "strict warm lookup reuses its own immutable portable record");
    require(cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins, &hit, nullptr,
                SpirvDerivativeMode::AllowNonUniform) == compatible && hit,
            "compatibility warm lookup reuses its own immutable portable record");
    auto strict_device = fake_device(strict, 7);
    auto compatible_device = fake_device(compatible, 7);
    require(cache.store_device(strict, {7, false}, strict_device, record_bytes(*strict_device)) &&
            cache.store_device(compatible, {7, false}, compatible_device, record_bytes(*compatible_device)) &&
            cache.portable_size() == 2 && cache.device_size() == 2 &&
            cache.find_device(strict->identity, {7, false}) == strict_device &&
            cache.find_device(compatible->identity, {7, false}) == compatible_device,
            "same generation and attachment state retain separate strict and compatible device records");
    std::weak_ptr<FakeDevice> old_strict = strict_device, old_compatible = compatible_device;
    strict_device.reset(); compatible_device.reset();
    cache.clear_devices();
    require(old_strict.expired() && old_compatible.expired() && cache.device_size() == 0 &&
            cache.find_portable(strict->identity) == strict && cache.find_portable(compatible->identity) == compatible &&
            strict->derivative_mode == SpirvDerivativeMode::Strict &&
            compatible->derivative_mode == SpirvDerivativeMode::AllowNonUniform,
            "device loss leaves both captured ingestion policies on their retained portable owners");
    // Recovery and variants consume retained policy instead of a mutable
    // process setting or a new default chosen after the program was linked.
    for (const auto& retained : {strict, compatible}) {
        require(cache.get_or_build(retained->source_vertex, retained->source_fragment, retained->options,
                    retained->compiler_identity, &hit, nullptr, retained->derivative_mode) == retained && hit,
                "recovery source API preserves captured mode and warm reuse");
        auto recovered = fake_device(retained, 8);
        require(cache.store_device(retained, {8, false}, recovered, record_bytes(*recovered)) &&
                cache.find_device(retained->identity, {8, false}) == recovered,
                "recovery republishes each policy under the new device generation");
        for (const auto policy : {VertexIdentityPolicy::Affine, VertexIdentityPolicy::Indexed}) {
            auto options = retained->options;
            options.vertex_identity = policy;
            auto variant = cache.get_or_build(retained->source_vertex, retained->source_fragment, options,
                retained->compiler_identity, &hit, nullptr, retained->derivative_mode);
            require(variant->ok && !hit && variant->derivative_mode == retained->derivative_mode &&
                    variant->identity != retained->identity,
                    "compact input variants retain original render ingestion policy");
        }
        auto points = retained->options;
        points.point_sprites = true;
        auto point = cache.get_or_build(retained->source_vertex, retained->source_fragment, points,
            retained->compiler_identity, &hit, nullptr, retained->derivative_mode);
        require(point->ok && !hit && point->point_sprites && point->derivative_mode == retained->derivative_mode,
                "point variant source API retains original render ingestion policy");
    }
}

size_t instruction_count(const std::vector<uint32_t>& words, spv::Op requested) {
    size_t found = 0;
    for (size_t position = 5; position < words.size();) {
        const size_t count = words[position] >> 16;
        require(count && count <= words.size() - position, "sampling control has well-formed SPIR-V instructions");
        found += static_cast<spv::Op>(words[position] & 0xffffu) == requested;
        position += count;
    }
    return found;
}

void derivative_permission_preserves_sampling() {
    // Reuse the admitted sampling fixture with user control flow and a
    // derivative. Permission must not repair it by changing shader semantics.
    for (const bool base_level : {false, true}) {
        NormalizeOptions options;
        options.base_level_sampling = base_level;
        auto strict = build_portable_shader(vertex, sampled_fragment, options, pins);
        auto compatible = build_portable_shader(vertex, sampled_fragment, options, pins, SpirvDerivativeMode::AllowNonUniform);
        require(strict->ok && compatible->ok, strict->error + compatible->error);
        require(strict->fragment == compatible->fragment && strict->spv_frag == compatible->spv_frag &&
                strict->samplers.size() == 1 && compatible->samplers.size() == 1,
                "render derivative permission preserves sampler normalization and emitted shader");
        const auto implicit = instruction_count(compatible->spv_frag, spv::Op::OpImageSampleImplicitLod);
        const auto explicit_lod = instruction_count(compatible->spv_frag, spv::Op::OpImageSampleExplicitLod);
        require(base_level ? explicit_lod > 0 && implicit == 0 : implicit > 0 && explicit_lod == 0,
                "base-level option alone controls implicit versus explicit sampling");
        require(instruction_count(compatible->spv_frag, spv::Op::OpDPdx) > 0 &&
                instruction_count(compatible->spv_frag, spv::Op::OpBranchConditional) > 0,
                "user derivative and conditional control flow survive compatibility permission");
    }
}

void sampling_policy_cache_and_retained_variants() {
    UnifiedCache cache;
    NormalizeOptions implicit_options;
    auto base_options = implicit_options;
    base_options.base_level_sampling = true;
    bool hit = true;
    auto implicit = cache.get_or_build(vertex, sampled_fragment, implicit_options, pins, &hit, nullptr,
        SpirvDerivativeMode::AllowNonUniform);
    require(implicit->ok && !hit && !implicit->options.base_level_sampling, implicit->error);
    auto base = cache.get_or_build(vertex, sampled_fragment, base_options, pins, &hit, nullptr,
        SpirvDerivativeMode::AllowNonUniform);
    require(base->ok && !hit && base->options.base_level_sampling, base->error);
    require(implicit->source_vertex == base->source_vertex && implicit->source_fragment == base->source_fragment &&
            implicit->derivative_mode == SpirvDerivativeMode::AllowNonUniform &&
            base->derivative_mode == SpirvDerivativeMode::AllowNonUniform &&
            implicit->identity != base->identity && implicit->cache_key != base->cache_key &&
            implicit->fragment != base->fragment && implicit->spv_frag != base->spv_frag,
            "same original shader and render permission retain distinct actual sampling artifacts");
    require(implicit->samplers.size() == 1 && base->samplers.size() == 1 &&
            implicit->samplers[0].texture_binding == base->samplers[0].texture_binding &&
            implicit->samplers[0].sampler_binding == base->samplers[0].sampler_binding &&
            implicit->samplers[0].texture_stage_mask == base->samplers[0].texture_stage_mask &&
            implicit->samplers[0].sampler_stage_mask == base->samplers[0].sampler_stage_mask,
            "sampling choice preserves admitted resource bindings and actual stage visibility");
    auto check_sampling = [&](const std::shared_ptr<const PortableShaderArtifact>& artifact) {
        const auto implicit_count = instruction_count(artifact->spv_frag, spv::Op::OpImageSampleImplicitLod);
        const auto explicit_count = instruction_count(artifact->spv_frag, spv::Op::OpImageSampleExplicitLod);
        require(artifact->options.base_level_sampling ? explicit_count > 0 && implicit_count == 0 :
                    implicit_count > 0 && explicit_count == 0,
                "actual emitted sampling instruction agrees with retained source option");
        require(instruction_count(artifact->spv_frag, spv::Op::OpDPdx) > 0 &&
                instruction_count(artifact->spv_frag, spv::Op::OpBranchConditional) > 0,
                "both retained sampling policies preserve the original derivative and conditional flow");
    };
    check_sampling(implicit);
    check_sampling(base);
    auto implicit_device = fake_device(implicit, 7);
    auto base_device = fake_device(base, 7);
    require(cache.store_device(implicit, {7, false}, implicit_device, record_bytes(*implicit_device)) &&
            cache.store_device(base, {7, false}, base_device, record_bytes(*base_device)) &&
            cache.portable_size() == 2 && cache.device_size() == 2 &&
            cache.find_device(implicit->identity, {7, false}) == implicit_device &&
            cache.find_device(base->identity, {7, false}) == base_device,
            "implicit and explicit sampling never share a device record at equal generation/depth");
    std::weak_ptr<FakeDevice> old_implicit = implicit_device, old_base = base_device;
    implicit_device.reset(); base_device.reset();
    cache.clear_devices();
    require(old_implicit.expired() && old_base.expired() && cache.device_size() == 0 &&
            cache.find_portable(implicit->identity) == implicit && cache.find_portable(base->identity) == base,
            "device loss releases handles while retaining each original sampling artifact");
    for (const auto& retained : {implicit, base}) {
        const auto words = retained->spv_frag;
        const auto source_map = retained->frag_map;
        auto recovered = cache.get_or_build(retained->source_vertex, retained->source_fragment, retained->options,
            retained->compiler_identity, &hit, nullptr, retained->derivative_mode);
        require(hit && recovered == retained && recovered->spv_frag == words && recovered->frag_map == source_map,
                "warm recovery consumes retained sampling/derivative options without rebuilding shaders");
        auto recovered_device = fake_device(recovered, 8);
        require(cache.store_device(recovered, {8, false}, recovered_device, record_bytes(*recovered_device)) &&
                cache.find_device(recovered->identity, {8, false}) == recovered_device,
                "recovered device keeps the retained sampling identity");
        for (const auto vertex_policy : {VertexIdentityPolicy::Affine, VertexIdentityPolicy::Indexed,
                                         VertexIdentityPolicy::Native}) {
            auto options = retained->options;
            options.vertex_identity = vertex_policy;
            options.point_sprites = vertex_policy == VertexIdentityPolicy::Native;
            auto variant = cache.get_or_build(retained->source_vertex, retained->source_fragment, options,
                retained->compiler_identity, &hit, nullptr, retained->derivative_mode);
            require(variant->ok && !hit && variant->identity != retained->identity &&
                    variant->options.base_level_sampling == retained->options.base_level_sampling &&
                    variant->derivative_mode == retained->derivative_mode,
                    "compact and point variants capture both original sampling and derivative policies");
            check_sampling(variant);
            auto warm_variant = cache.get_or_build(variant->source_vertex, variant->source_fragment, variant->options,
                variant->compiler_identity, &hit, nullptr, variant->derivative_mode);
            require(hit && warm_variant == variant,
                    "each actual sampling variant reuses its own immutable identity");
        }
    }
}

void unified_device_ownership() {
    UnifiedCache cache;
    const std::string comments = "//" + std::string(8192, 'x') + "\n" + fragment;
    auto portable = cache.get_or_build(vertex, comments, NormalizeOptions{}, pins);
    require(portable->ok, portable->error);
    const size_t portable_charge = cache.storage_bytes();
    require(cache.portable_storage_bytes() == portable->storage_bytes(), "portable data is charged once");
    auto plain = fake_device(portable, 7);
    require(!cache.store_device(portable, {0, false}, plain, record_bytes(*plain)), "zero generation cannot enter the device cache");
    require(cache.store_device(portable, {7, false}, plain, record_bytes(*plain)), "first device is admitted");
    const size_t device_charge = cache.storage_bytes() - portable_charge;
    require(device_charge >= record_bytes(*plain), "device object and fixed-key bookkeeping are charged");
    // A long identity is owned only by portable data. Repeated device variants
    // cost fixed keys/records, not another source-sized identity copy.
    auto depth = fake_device(portable, 7);
    auto recovered = fake_device(portable, 8);
    require(cache.store_device(portable, {7, true}, depth, record_bytes(*depth)) &&
            cache.store_device(portable, {8, false}, recovered, record_bytes(*recovered)), "depth and generation variants admitted");
    require(cache.device_size() == 3 && cache.portable_size() == 1 &&
            cache.storage_bytes() == portable_charge + 3 * device_charge,
            "mixed device variants share one portable allocation and use fixed-size keys");
    require(cache.find_device(portable->identity, {7, false}) == plain &&
            cache.find_device(portable->identity, {7, true}) == depth &&
            cache.find_device(portable->identity, {8, false}) == recovered &&
            !cache.find_device(portable->identity, {9, false}), "generation and attachment availability gate device reuse");
    size_t visited = 0;
    cache.for_each_device([&](const auto& record) { require(record->portable == portable, "canonical owner in device traversal"); ++visited; });
    require(visited == 3, "device traversal includes every cache-owned variant");

    auto duplicate = std::make_shared<PortableShaderArtifact>(*portable);
    auto duplicate_record = fake_device(duplicate, 9);
    const size_t before_duplicate = cache.storage_bytes();
    require(!cache.store_device(duplicate, {9, false}, duplicate_record, record_bytes(*duplicate_record)) &&
            cache.find_portable(duplicate->identity) == portable && cache.storage_bytes() == before_duplicate,
            "identity-equal allocations must canonicalize before device admission");
    auto wrong_owner = fake_device(duplicate, 10);
    require(!cache.store_device(portable, {10, false}, wrong_owner, record_bytes(*wrong_owner)),
            "record cannot hide a different portable allocation behind a canonical argument");

    auto live_bytes = cache.external_portable_bytes(std::vector<std::shared_ptr<const PortableShaderArtifact>>{
        portable, portable, duplicate, nullptr});
    require(live_bytes.live_bytes == portable->storage_bytes() + duplicate->storage_bytes() &&
            live_bytes.uncached_bytes == duplicate->storage_bytes(), "live accounting deduplicates allocations, not identities");

    std::weak_ptr<FakeDevice> old_plain = plain;
    std::weak_ptr<FakeDevice> old_depth = depth;
    std::weak_ptr<FakeDevice> old_recovered = recovered;
    plain.reset(); depth.reset(); recovered.reset();
    cache.clear_devices();
    require(old_plain.expired() && old_depth.expired() && old_recovered.expired() &&
            cache.device_size() == 0 && cache.storage_bytes() == portable_charge,
            "device loss releases device owners and preserves portable budget accounting");
    bool hit = false;
    require(cache.get_or_build(vertex, comments, NormalizeOptions{}, pins, &hit) == portable && hit,
            "loss preserves immutable portable cache hits");

    UnifiedCache moved;
    moved = std::move(cache);
    require(cache.size() == 0 && cache.storage_bytes() == 0 && moved.find_portable(portable->identity) == portable,
            "move assignment transfers borrowed-key backing ownership and empties the source");
    moved.clear();
    require(moved.storage_bytes() == 0 && portable->ok, "clear preserves external immutable owners");
}

void unified_budget_eviction_and_recovery() {
    UnifiedCache measured;
    const std::string comments = "//" + std::string(4096, 'c') + "\n" + fragment;
    auto portable = measured.get_or_build(vertex, comments, NormalizeOptions{}, pins);
    auto device = fake_device(portable, 3);
    require(measured.store_device(portable, {3, false}, device, record_bytes(*device)), "measure one whole entry");
    const size_t budget = measured.storage_bytes();
    UnifiedCache cache(128, budget);
    auto resident = cache.get_or_build(vertex, comments, NormalizeOptions{}, pins);
    auto resident_device = fake_device(resident, 3);
    require(cache.store_device(resident, {3, false}, resident_device, record_bytes(*resident_device)), "exact whole-entry budget admits record");
    std::weak_ptr<const PortableShaderArtifact> resident_weak = resident;
    std::weak_ptr<FakeDevice> device_weak = resident_device;
    resident.reset(); resident_device.reset();
    auto next = cache.get_or_build(vertex, "// other\n" + comments, NormalizeOptions{}, pins);
    require(next->ok && cache.storage_bytes() <= budget && !cache.find_portable(portable->identity) &&
            resident_weak.expired() && device_weak.expired(),
            "byte eviction drops portable and device cache owners together; no hidden device retention");

    // A live program survives eviction and can rematerialize from its saved
    // artifact after loss, without invoking get_or_build (the CPU compiler).
    UnifiedCache one(1, budget);
    auto live = one.get_or_build(vertex, comments, NormalizeOptions{}, pins);
    const auto words = live->spv_frag;
    const auto maps = live->frag_map;
    auto live_device = fake_device(live, 4);
    require(one.store_device(live, {4, false}, live_device, record_bytes(*live_device)), "live device admitted");
    auto replacement = one.get_or_build(vertex, "void main(){gl_FragColor=vec4(.5);}", NormalizeOptions{}, pins);
    require(!one.find_portable(live->identity) && live->spv_frag == words && live->frag_map == maps,
            "entry eviction cannot mutate program or snapshot data");
    auto outside = one.external_portable_bytes(std::vector{live, live, replacement});
    require(outside.uncached_bytes == live->storage_bytes(), "evicted live program storage is separately visible");
    live_device->invalidate();
    one.clear_devices();
    auto new_device = fake_device(live, 5);
    require(one.store_device(live, {5, false}, new_device, record_bytes(*new_device)) &&
            one.find_portable(live->identity) == live && one.find_device(live->identity, {5, false}) == new_device &&
            live->spv_frag == words && live->frag_map == maps && one.storage_bytes() <= budget,
            "saved uncached program rematerializes into the bounded cache without rebuilding portable data");

    // A new depth variant would exceed this complete-entry budget. Do not
    // retain either GPU record through an otherwise evicted portable artifact.
    auto extra = fake_device(live, 5);
    require(!one.store_device(live, {5, true}, extra, record_bytes(*extra)) &&
            one.portable_size() == 0 && one.device_size() == 0 && one.storage_bytes() == 0 && live->ok,
            "oversized combined variant graph is not cached");
}

void oversized_and_mutable_records() {
    UnifiedCache measured;
    auto normal = measured.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    auto normal_record = fake_device(normal, 1);
    require(measured.store_device(normal, {1, false}, normal_record, record_bytes(*normal_record)), "measure baseline graph");
    const size_t budget = measured.storage_bytes();
    UnifiedCache cache(128, budget);
    auto resident = cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    auto resident_record = fake_device(resident, 1);
    require(cache.store_device(resident, {1, false}, resident_record, record_bytes(*resident_record)), "baseline whole-entry admission");
    const std::string large = "//" + std::string(budget, 'x') + "\n" + fragment;
    for (int attempt = 0; attempt < 3; ++attempt) {
        bool hit = true;
        auto oversized = cache.get_or_build(vertex, large, NormalizeOptions{}, pins, &hit);
        auto gpu = fake_device(oversized, 1);
        std::weak_ptr<const PortableShaderArtifact> weak_portable = oversized;
        std::weak_ptr<FakeDevice> weak_device = gpu;
        require(oversized->ok && !hit && !cache.store_device(oversized, {1, false}, gpu, record_bytes(*gpu)) &&
                cache.find_portable(resident->identity) == resident && cache.find_device(resident->identity, {1, false}) == resident_record &&
                cache.storage_bytes() == budget, "repeated oversized shader requests have no hidden GPU-cache admission");
        oversized.reset(); gpu.reset();
        require(weak_portable.expired() && weak_device.expired(), "uncached oversized graph releases every owner after caller release");
    }

    std::weak_ptr<FakeDevice> old_record = resident_record;
    auto replacement = fake_device(resident, 1);
    require(cache.store_device(resident, {1, false}, replacement, record_bytes(*replacement)), "same-key replacement is charged once");
    resident_record.reset();
    require(old_record.expired() && cache.device_size() == 1 && cache.storage_bytes() == budget,
            "replacement drops old cache record without double charging");
    const std::string key(1024, 's');
    replacement->variants.emplace(key, std::make_shared<int>(2));
    replacement->variant_order.push_back(key);
    replacement->error.assign(2048, 'e');
    require(record_bytes(*replacement) > record_bytes(*normal_record) + 2 * key.size() + replacement->error.size(),
            "record charge covers map and FIFO keys plus full diagnostic capacity");
    require(!cache.refresh_device(resident->identity, {1, false}, record_bytes(*replacement)) &&
            cache.storage_bytes() == 0 && cache.device_size() == 0 && !cache.find_portable(resident->identity) &&
            replacement->portable == resident && resident->ok,
            "variant/error growth enforces the whole cache budget while live records survive");

    UnifiedCache retained(128, budget + record_bytes(*replacement) + 4096);
    require(retained.store_device(resident, {1, false}, replacement, record_bytes(*replacement)), "saved large live record can fit a larger explicit budget");
    const size_t grown_charge = retained.storage_bytes();
    replacement->invalidate();
    require(retained.refresh_device(resident->identity, {1, false}, record_bytes(*replacement)) &&
            retained.storage_bytes() < grown_charge && retained.storage_bytes() <= retained.byte_limit(),
            "refresh also accounts key/container release without undercounting retained error capacity");
    UnifiedCache disabled(0, budget);
    require(!disabled.store_device(resident, {1, false}, replacement, record_bytes(*replacement)) && disabled.storage_bytes() == 0,
            "disabled cache cannot admit device-only ownership");
}

void refresh_evicts_other_identity() {
    UnifiedCache measured;
    auto first = measured.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    auto second = measured.get_or_build(vertex, "// second identity\n" + fragment, NormalizeOptions{}, pins);
    auto first_record = fake_device(first, 1);
    auto second_record = fake_device(second, 1);
    require(measured.store_device(first, {1, false}, first_record, record_bytes(*first_record)) &&
            measured.store_device(second, {1, false}, second_record, record_bytes(*second_record)), "measure two identities");
    const size_t budget = measured.storage_bytes();
    measured.clear();
    UnifiedCache cache(128, budget);
    require(cache.store_device(first, {1, false}, first_record, record_bytes(*first_record)) &&
            cache.store_device(second, {1, false}, second_record, record_bytes(*second_record)), "two saved identities share the exact explicit budget");
    std::weak_ptr<const PortableShaderArtifact> evicted_portable = second;
    std::weak_ptr<FakeDevice> evicted_record = second_record;
    second.reset(); second_record.reset();
    first_record->error.assign(1024, 'e');
    require(cache.refresh_device(first->identity, {1, false}, record_bytes(*first_record)) &&
            cache.size() == 1 && cache.find_device(first->identity, {1, false}) == first_record &&
            cache.storage_bytes() <= budget && evicted_portable.expired() && evicted_record.expired(),
            "growing oldest retained entry evicts another whole identity rather than its live target");
}

struct FakeAuxiliary {
    std::shared_ptr<const PortableShaderArtifact> original;
    std::string identity;
    std::vector<uint32_t> spv{0x07230203u, 7, 11};
    std::vector<int> line_map{0, 2, 3};
    size_t reported_bytes = 0;
    bool throw_footprint = false;
    size_t storage_bytes() const {
        if (throw_footprint) throw std::runtime_error("auxiliary footprint failure");
        return reported_bytes ? reported_bytes : sizeof(*this) + identity.capacity() + 1 +
            spv.capacity() * sizeof(uint32_t) + line_map.capacity() * sizeof(int);
    }
};
struct FakeEvaluatorDevice : DeviceBase {
    std::shared_ptr<const PortableShaderArtifact> portable;
    std::shared_ptr<const FakeAuxiliary> evaluator;
};
using AuxiliaryCache = ShaderArtifactCache<FakeEvaluatorDevice, FakeAuxiliary>;

std::shared_ptr<FakeAuxiliary> fake_auxiliary(const std::shared_ptr<const PortableShaderArtifact>& portable) {
    auto result = std::make_shared<FakeAuxiliary>();
    result->original = portable;
    result->identity = portable->identity + ";fake-evaluator-policy=2";
    return result;
}
std::shared_ptr<FakeEvaluatorDevice> evaluator_device(const std::shared_ptr<const PortableShaderArtifact>& portable,
        uint64_t generation, std::shared_ptr<const FakeAuxiliary> evaluator = {}) {
    auto result = std::make_shared<FakeEvaluatorDevice>();
    result->portable = portable;
    result->evaluator = std::move(evaluator);
    result->device_generation = generation;
    result->pipeline = std::make_shared<int>(2);
    result->pipeline_ok = true;
    return result;
}
size_t evaluator_record_bytes(const FakeEvaluatorDevice& record) {
    // Shared original/evaluator allocations are excluded; the cache owns their
    // one charge. The device's pointer fields and handles still count here.
    return record.storage_bytes(sizeof(FakeEvaluatorDevice) - sizeof(DeviceBase));
}

void auxiliary_canonical_ownership_and_loss() {
    AuxiliaryCache cache;
    auto portable = cache.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    const auto portable_charge = cache.storage_bytes();
    auto render = evaluator_device(portable, 1);
    require(cache.store_device(portable, {1, false}, render, evaluator_record_bytes(*render)), "render device precedes first evaluator admission");
    const auto before_auxiliary = cache.storage_bytes();
    auto auxiliary = fake_auxiliary(portable);
    require(cache.store_auxiliary(portable, auxiliary) && cache.auxiliary_size() == 1 && cache.device_size() == 1 &&
            !render->evaluator && cache.storage_bytes() >= before_auxiliary + auxiliary->storage_bytes() &&
            cache.auxiliary_storage_bytes() == auxiliary->storage_bytes(),
            "first auxiliary can coexist with existing null-evaluator render devices; capacities and owner bookkeeping enter joint budget");
    render->evaluator = auxiliary;
    require(cache.refresh_device(portable->identity, {1, false}, evaluator_record_bytes(*render)), "existing device can attach exact admitted evaluator then refresh its charge");
    const size_t first_device_bytes = cache.storage_bytes();
    auto recovered = evaluator_device(portable, 2, auxiliary);
    require(cache.store_device(portable, {2, true}, recovered, evaluator_record_bytes(*recovered)) &&
            cache.auxiliary_size() == 1 && cache.device_size() == 2 &&
            cache.storage_bytes() - first_device_bytes == before_auxiliary - portable_charge,
            "generation/depth device variants share the auxiliary allocation instead of charging its source/SPIR-V twice");
    const size_t whole = cache.storage_bytes();
    require(cache.store_auxiliary(portable, auxiliary) && cache.storage_bytes() == whole, "same immutable auxiliary admission is idempotent");
    auto replacement = fake_auxiliary(portable);
    require(!cache.store_auxiliary(portable, replacement) && cache.find_auxiliary(portable->identity) == auxiliary &&
            cache.storage_bytes() == whole, "different auxiliary cannot replace one retained by cached devices");
    auto duplicate_portable = std::make_shared<PortableShaderArtifact>(*portable);
    auto duplicate_original_auxiliary = fake_auxiliary(duplicate_portable);
    require(!cache.store_auxiliary(portable, duplicate_original_auxiliary) &&
            !cache.store_auxiliary(duplicate_portable, duplicate_original_auxiliary) && cache.storage_bytes() == whole,
            "both argument and auxiliary must use exact canonical original allocation, not just equal identity");
    require(!cache.store_auxiliary(portable, {}) && !cache.store_auxiliary({}, auxiliary), "null owners cannot be admitted");
    auto wrong_device = evaluator_device(portable, 1, replacement);
    require(!cache.store_device(portable, {1, true}, wrong_device, evaluator_record_bytes(*wrong_device)) &&
            cache.device_size() == 2, "device cannot retain different uncharged auxiliary allocation");
    AuxiliaryCache no_auxiliary;
    require(!no_auxiliary.store_device(portable, {1, false}, render, evaluator_record_bytes(*render)) &&
            no_auxiliary.storage_bytes() == 0, "evaluator device requires prior matching auxiliary admission");
    size_t auxiliaries = 0;
    cache.for_each_auxiliary([&](const auto& value) { require(value == auxiliary, "auxiliary traversal is typed and canonical"); ++auxiliaries; });
    require(auxiliaries == 1, "auxiliary traversal visits one allocation per original identity");
    const auto portable_live = cache.external_portable_bytes(
        std::vector<std::shared_ptr<const PortableShaderArtifact>>{portable, portable, duplicate_portable},
        std::vector<AuxiliaryCache::AuxiliaryPtr>{auxiliary, auxiliary, replacement, duplicate_original_auxiliary, nullptr});
    const auto auxiliary_live = cache.external_auxiliary_bytes(
        std::vector<AuxiliaryCache::AuxiliaryPtr>{auxiliary, auxiliary, replacement, duplicate_original_auxiliary, nullptr});
    require(portable_live.live_bytes == portable->storage_bytes() + duplicate_portable->storage_bytes() &&
            portable_live.uncached_bytes == duplicate_portable->storage_bytes(),
            "explicit and auxiliary original ranges share one portable allocation dedup set");
    require(auxiliary_live.live_bytes == auxiliary->storage_bytes() + replacement->storage_bytes() + duplicate_original_auxiliary->storage_bytes() &&
            auxiliary_live.uncached_bytes == replacement->storage_bytes() + duplicate_original_auxiliary->storage_bytes(),
            "auxiliary live accounting deduplicates allocations and reports pointer-distinct uncached graphs");
    const auto words = auxiliary->spv;
    const auto maps = auxiliary->line_map;
    const auto original_words = portable->spv_vert;
    const auto original_maps = portable->vert_map;
    std::weak_ptr<FakeEvaluatorDevice> weak_device = render;
    std::weak_ptr<FakeEvaluatorDevice> weak_recovered = recovered;
    render.reset(); recovered.reset();
    cache.clear_devices();
    require(weak_device.expired() && weak_recovered.expired() && cache.device_size() == 0 && cache.auxiliary_size() == 1 &&
            cache.find_auxiliary(portable->identity) == auxiliary && auxiliary->spv == words && auxiliary->line_map == maps &&
            portable->spv_vert == original_words && portable->vert_map == original_maps &&
            cache.storage_bytes() < whole && cache.portable_storage_bytes() == portable->storage_bytes(),
            "clear_devices drops GPU owners but keeps original plus exact immutable evaluator SPIR-V/maps and charge");
    require(cache.store_auxiliary(portable, replacement) && cache.find_auxiliary(portable->identity) == replacement,
            "after device owners leave cache an immutable auxiliary replacement is safe; external old owners survive");
    auto old_live = cache.external_auxiliary_bytes(std::vector<AuxiliaryCache::AuxiliaryPtr>{auxiliary, replacement});
    require(old_live.uncached_bytes == auxiliary->storage_bytes() && auxiliary->spv == words, "live old evaluator remains usable and separately visible after replacement");
    AuxiliaryCache moved;
    moved = std::move(cache);
    require(cache.size() == 0 && cache.auxiliary_size() == 0 && cache.storage_bytes() == 0 &&
            moved.find_auxiliary(portable->identity) == replacement && moved.storage_bytes() <= moved.byte_limit(),
            "moving cache retains borrowed original key backing and auxiliary owner accounting");
    moved.clear();
    require(moved.storage_bytes() == 0 && replacement->original == portable && auxiliary->line_map == maps, "shutdown drops cache owners without modifying live originals/evaluators");
    UnifiedCache default_cache;
    require(!default_cache.store_auxiliary(portable, {}) && default_cache.auxiliary_size() == 0 &&
            default_cache.auxiliary_storage_bytes() == 0, "default NoAuxiliary template keeps existing callers compatible");
}

void auxiliary_joint_budget_and_publication() {
    AuxiliaryCache measured;
    auto portable = measured.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    auto auxiliary = fake_auxiliary(portable);
    require(measured.store_auxiliary(portable, auxiliary), "measure joint portable plus auxiliary graph");
    const size_t base = measured.storage_bytes();
    auto device = evaluator_device(portable, 1, auxiliary);
    require(measured.store_device(portable, {1, false}, device, evaluator_record_bytes(*device)), "measure whole original/auxiliary/device graph");
    const size_t whole = measured.storage_bytes();
    require(whole > base && base > portable->storage_bytes() + auxiliary->storage_bytes(), "joint charge includes device, entry/control and identity policy capacities");
    AuxiliaryCache exact(128, whole);
    require(exact.store_auxiliary(portable, auxiliary) && exact.store_device(portable, {1, false}, device, evaluator_record_bytes(*device)) &&
            exact.storage_bytes() == whole, "exact complete graph budget includes shared original once");
    auto next = exact.get_or_build(vertex, "// other identity\n" + fragment, NormalizeOptions{}, pins);
    require(!exact.find_portable(portable->identity) && !exact.find_auxiliary(portable->identity) && exact.device_size() == 0 &&
            exact.find_portable(next->identity) == next && exact.storage_bytes() <= whole,
            "joint budget evicts whole portable/evaluator/device entry, including otherwise hidden device-held auxiliary refs");
    AuxiliaryCache useful(128, whole);
    require(useful.store_auxiliary(portable, auxiliary), "retain useful auxiliary graph");
    const auto useful_bytes = useful.storage_bytes();
    auto oversized = fake_auxiliary(next);
    oversized->spv.resize(whole / sizeof(uint32_t) + 1);
    require(!useful.store_auxiliary(next, oversized) && useful.find_auxiliary(portable->identity) == auxiliary &&
            useful.storage_bytes() == useful_bytes && !useful.find_portable(next->identity),
            "oversized new auxiliary is returned to caller without hidden cache admission or evicting useful owners");
    auto oversized_replacement = fake_auxiliary(portable);
    oversized_replacement->spv.resize(whole / sizeof(uint32_t) + 1);
    require(!useful.store_auxiliary(portable, oversized_replacement) && useful.find_auxiliary(portable->identity) == auxiliary &&
            useful.storage_bytes() == useful_bytes, "oversized replacement preserves immutable old cached graph");
    auto throwing = fake_auxiliary(portable);
    throwing->throw_footprint = true;
    bool threw = false;
    try { useful.store_auxiliary(portable, throwing); } catch (const std::runtime_error&) { threw = true; }
    require(threw && useful.find_auxiliary(portable->identity) == auxiliary && useful.storage_bytes() == useful_bytes,
            "failed footprint calculation precedes publication/eviction and preserves owners");
    auto overflow = fake_auxiliary(portable);
    overflow->reported_bytes = SIZE_MAX;
    AuxiliaryCache maximum(128, SIZE_MAX);
    require(!maximum.store_auxiliary(portable, overflow) && maximum.storage_bytes() == 0, "overflowing capacity plus control bookkeeping is rejected even at maximal host budget");
    require(maximum.store_auxiliary(portable, auxiliary) &&
            !maximum.store_device(portable, {1, false}, device, SIZE_MAX) && maximum.storage_bytes() == 0,
            "saturating device bookkeeping cannot silently admit an overflowing joint graph at maximal host budget");
    require(maximum.store_auxiliary(portable, auxiliary) &&
            maximum.store_device(portable, {1, false}, device, evaluator_record_bytes(*device)) &&
            !maximum.refresh_device(portable->identity, {1, false}, SIZE_MAX) && maximum.storage_bytes() == 0,
            "mutable device growth to an overflowing charge releases the whole cached CPU graph");
    AuxiliaryCache too_small(128, base);
    require(too_small.store_auxiliary(portable, auxiliary) &&
            !too_small.store_device(portable, {1, false}, device, evaluator_record_bytes(*device)) &&
            too_small.size() == 0 && too_small.auxiliary_size() == 0 && too_small.storage_bytes() == 0,
            "oversized combined device variant drops complete cache graph, while live auxiliary stays usable");
    AuxiliaryCache disabled(0, whole);
    require(!disabled.store_auxiliary(portable, auxiliary) && disabled.storage_bytes() == 0, "zero-entry cache cannot admit auxiliary-only ownership");
}

void auxiliary_eviction_lifetime_and_mutable_device_guard() {
    AuxiliaryCache one(1);
    auto portable = one.get_or_build(vertex, fragment, NormalizeOptions{}, pins);
    auto auxiliary = fake_auxiliary(portable);
    auto device = evaluator_device(portable, 1, auxiliary);
    require(one.store_auxiliary(portable, auxiliary) && one.store_device(portable, {1, false}, device, evaluator_record_bytes(*device)), "snapshot graph admitted");
    AuxiliaryCache::AuxiliaryPtr snapshot = auxiliary;
    std::weak_ptr<const PortableShaderArtifact> weak_original = portable;
    std::weak_ptr<const FakeAuxiliary> weak_auxiliary = auxiliary;
    std::weak_ptr<FakeEvaluatorDevice> weak_device = device;
    portable.reset(); auxiliary.reset(); device.reset();
    auto replacement = one.get_or_build(vertex, "// eviction\n" + fragment, NormalizeOptions{}, pins);
    require(weak_device.expired() && !weak_original.expired() && !weak_auxiliary.expired() && snapshot->spv.front() == 0x07230203u,
            "eviction releases cache/device owners but immutable pending snapshot retains evaluator and its original");
    auto live = one.external_auxiliary_bytes(std::vector<AuxiliaryCache::AuxiliaryPtr>{snapshot, snapshot});
    auto origins = one.external_portable_bytes(std::vector<std::shared_ptr<const PortableShaderArtifact>>{},
        std::vector<AuxiliaryCache::AuxiliaryPtr>{snapshot, snapshot});
    require(live.live_bytes == snapshot->storage_bytes() && live.uncached_bytes == live.live_bytes &&
            origins.live_bytes == snapshot->original->storage_bytes() && origins.uncached_bytes == origins.live_bytes,
            "auxiliary-only snapshot contributes its original and auxiliary exactly once after cache eviction");
    snapshot.reset();
    require(weak_auxiliary.expired() && weak_original.expired(), "retiring final immutable snapshot releases the entire uncached CPU graph without cycles");
    auto current = fake_auxiliary(replacement);
    auto current_device = evaluator_device(replacement, 2, current);
    require(one.store_auxiliary(replacement, current) && one.store_device(replacement, {2, false}, current_device, evaluator_record_bytes(*current_device)), "mutable device guard baseline");
    current_device->evaluator = fake_auxiliary(replacement);
    require(!one.refresh_device(replacement->identity, {2, false}, evaluator_record_bytes(*current_device)) &&
            one.storage_bytes() == 0 && one.device_size() == 0 && one.auxiliary_size() == 0,
            "refresh rejects changed evaluator pointer and removes otherwise uncharged cached allocation graph");
    require(current->original == replacement && current->spv.front() == 0x07230203u, "mutable-device rejection never mutates saved evaluator provenance");
}
}  // namespace

void dimension_metadata_counts_toward_storage() {
    PortableShaderArtifact artifact;
    artifact.uniforms.resize(1);
    artifact.samplers.resize(1);
    artifact.varyings.resize(1);
    const size_t before = artifact.storage_bytes();
    artifact.uniforms[0].array_dimensions.reserve(7);
    artifact.samplers[0].array_dimensions.reserve(11);
    artifact.varyings[0].array_dimensions.reserve(13);
    const size_t reserved = artifact.uniforms[0].array_dimensions.capacity() +
                            artifact.samplers[0].array_dimensions.capacity() + artifact.varyings[0].array_dimensions.capacity();
    require(artifact.storage_bytes() == before + reserved * sizeof(uint32_t),
        "uniform, sampler and varying dimension metadata must count toward cache storage");
}

int main() {
    try {
        attribute_binding_contract();
        dimension_metadata_counts_toward_storage();
        identity_and_provenance();
        device_loss_preserves_portable();
        bounded_ownership_and_failures();
        per_stage_resource_limits();
        derivative_policy_identity_and_recovery();
        derivative_permission_preserves_sampling();
        sampling_policy_cache_and_retained_variants();
        unified_device_ownership();
        unified_budget_eviction_and_recovery();
        oversized_and_mutable_records();
        refresh_evicts_other_identity();
        auxiliary_canonical_ownership_and_loss();
        auxiliary_joint_budget_and_publication();
        auxiliary_eviction_lifetime_and_mutable_device_guard();
        std::cout << "portable/evaluator identity, unified bounded ownership, device invalidation, per-stage limits, reflection and diagnostic contracts passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
