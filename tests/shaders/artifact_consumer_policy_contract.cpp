#include "shader/line_consumer.hpp"

#include <iostream>
#include <stdexcept>

using namespace vispy::shader;

namespace {
size_t checks = 0;
void require(bool condition, const char* message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}

// Construct immutable CPU graphs directly. No GLSL compiler, device, payload,
// or runtime is involved in this contract.
struct Evaluator {
    std::shared_ptr<const PortableShaderArtifact> original;
    std::string identity;
    std::vector<uint32_t> words{7, 11, 13};
    size_t storage_bytes() const { return 512; }
};
struct Consumer {
    std::shared_ptr<const PortableShaderArtifact> original;
    std::shared_ptr<const Evaluator> evaluator;
    std::string identity;
    std::vector<uint32_t> words{17, 19, 23};
    size_t footprint = 768;
    bool fail_footprint = false;
    size_t storage_bytes() const {
        if (fail_footprint) throw std::runtime_error("controlled consumer footprint failure");
        return footprint;
    }
};
struct Device {
    std::shared_ptr<const PortableShaderArtifact> portable;
    std::shared_ptr<const Evaluator> evaluator;
    std::shared_ptr<const Consumer> consumer;
    std::shared_ptr<int> handle = std::make_shared<int>(29);
};
struct EvaluatorDevice {
    std::shared_ptr<const PortableShaderArtifact> portable;
    std::shared_ptr<const Evaluator> evaluator;
};
struct PlainDevice { std::shared_ptr<const PortableShaderArtifact> portable; };
using Cache = ShaderArtifactCache<Device, Evaluator, Consumer>;
using Legacy = ShaderArtifactCache<EvaluatorDevice, Evaluator>;
using Original = std::shared_ptr<const PortableShaderArtifact>;
using Eval = std::shared_ptr<const Evaluator>;
using Cons = std::shared_ptr<const Consumer>;

std::shared_ptr<PortableShaderArtifact> original(const char* label) {
    auto value = std::make_shared<PortableShaderArtifact>();
    value->identity = label;
    value->source_vertex = "independent original vertex bytes";
    value->source_fragment = "independent original fragment bytes";
    value->spv_vert = {31, 37, 41};
    value->spv_frag = {43, 47, 53};
    value->ok = true;
    return value;
}
std::shared_ptr<Evaluator> evaluator(const Original& portable) {
    auto value = std::make_shared<Evaluator>();
    value->original = portable;
    value->identity = portable->identity + ";evaluator";
    return value;
}
std::shared_ptr<Consumer> consumer(const Original& portable, const Eval& eval) {
    auto value = std::make_shared<Consumer>();
    value->original = portable;
    value->evaluator = eval;
    value->identity = portable->identity + ";consumer-policy-one";
    return value;
}
std::shared_ptr<Device> device(const Original& portable, const Eval& eval = {}, const Cons& cons = {}) {
    auto value = std::make_shared<Device>();
    value->portable = portable;
    value->evaluator = eval;
    value->consumer = cons;
    return value;
}
void admit(Cache& cache, const Original& portable, const Eval& eval, const Cons& cons) {
    require(cache.store_auxiliary(portable, eval), "exact evaluator admission");
    require(cache.store_consumer(portable, cons), "exact consumer admission");
}

void exact_owners_and_loss() {
    Cache cache;
    auto p = original("owner-A");
    auto e = evaluator(p);
    auto c = consumer(p, e);
    require(!cache.find_consumer(p->identity) && cache.consumer_size() == 0 &&
            cache.consumer_storage_bytes() == 0, "empty consumer slot");
    require(!cache.store_consumer(p, c) && cache.size() == 0,
            "consumer cannot implicitly admit an evaluator");
    require(!cache.store_consumer({}, c) && !cache.store_consumer(p, {}), "null owners refuse");
    require(cache.store_auxiliary(p, e), "admit evaluator before consumer");
    const auto evaluator_only_bytes = cache.storage_bytes();
    auto clone = std::make_shared<PortableShaderArtifact>(*p);
    auto clone_eval = evaluator(clone);
    auto clone_consumer = consumer(clone, clone_eval);
    require(!cache.store_consumer(p, clone_consumer) && !cache.store_consumer(clone, clone_consumer),
            "identity-equal original allocations cannot reparent the cached graph");
    auto unadmitted_eval = evaluator(p);
    require(!cache.store_consumer(p, consumer(p, unadmitted_eval)),
            "consumer must retain the exact admitted evaluator allocation");
    auto no_eval = consumer(p, {});
    require(!cache.store_consumer(p, no_eval), "missing consumer evaluator refuses");
    require(!cache.store_consumer(p, consumer(p, clone_eval)), "mismatched evaluator original refuses");
    require(cache.store_consumer(p, c) && cache.find_consumer(p->identity) == c &&
            cache.find_auxiliary(p->identity) == e && cache.find_portable(p->identity) == p,
            "all three exact allocations remain simultaneously canonical");
    const auto cpu_bytes = cache.storage_bytes();
    require(cpu_bytes >= evaluator_only_bytes + c->storage_bytes() &&
            cache.auxiliary_storage_bytes() == 512 && cache.consumer_storage_bytes() == 768,
            "consumer contributes its owned footprint once to the joint budget");
    require(cache.store_consumer(p, c) && cache.storage_bytes() == cpu_bytes,
            "idempotent admission does not duplicate consumer charging");
    auto same_policy = consumer(p, e);
    auto other_policy = consumer(p, e);
    other_policy->identity += ";smooth";
    require(!cache.store_consumer(p, same_policy) &&
            cache.find_consumer(p->identity) == c && cache.storage_bytes() == cpu_bytes,
            "same-policy identity-equal allocation cannot replace the retained canonical owner");

    auto missing_eval = device(p, {}, c);
    require(!cache.store_device(p, {1, false}, missing_eval, sizeof(Device)),
            "consumer device itself must retain the same evaluator");
    auto wrong_consumer = device(p, e, same_policy);
    require(!cache.store_device(p, {1, false}, wrong_consumer, sizeof(Device)),
            "correct evaluator must not bypass the subsequent consumer check");
    require(!cache.store_device(p, {1, false}, device(p, unadmitted_eval, c), sizeof(Device)) &&
            !cache.store_device(p, {1, false}, device(clone, e, c), sizeof(Device)),
            "device evaluator and original pointer mismatches refuse");
    auto d = device(p, e, c);
    auto second = device(p, e, c);
    require(!cache.store_device(p, {0, false}, d, sizeof(Device)), "zero generation refuses");
    require(cache.store_device(p, {1, false}, d, sizeof(Device)) &&
            cache.store_device(p, {2, true}, second, sizeof(Device)) && cache.device_size() == 2,
            "generation and attachment variants share the exact CPU triple");
    size_t consumers = 0, evaluators = 0, devices = 0;
    cache.for_each_consumer([&](const auto& value) { require(value == c, "consumer traversal owner"); ++consumers; });
    cache.for_each_auxiliary([&](const auto& value) { require(value == e, "evaluator traversal owner"); ++evaluators; });
    cache.for_each_device([&](const auto& value) { require(value->consumer == c, "device traversal consumer"); ++devices; });
    require(consumers == 1 && evaluators == 1 && devices == 2, "traversals reflect admitted counts");
    std::weak_ptr<Device> weak_first = d, weak_second = second;
    d.reset(); second.reset();
    cache.clear_devices();
    require(weak_first.expired() && weak_second.expired() && cache.device_size() == 0 &&
            cache.storage_bytes() == cpu_bytes && cache.consumer_size() == 1 &&
            cache.find_consumer(p->identity) == c && cache.find_auxiliary(p->identity) == e,
            "loss releases devices while retaining the entire charged CPU triple");
    require(!cache.store_auxiliary(p, unadmitted_eval) && cache.find_auxiliary(p->identity) == e &&
            cache.storage_bytes() == cpu_bytes, "retained consumer blocks evaluator replacement after loss");
    auto recovered = device(p, e, c);
    require(cache.store_device(p, {3, false}, recovered, sizeof(Device)) &&
            cache.find_device(p->identity, {3, false}) == recovered,
            "recovery rematerializes exact retained graph without recompilation");
    Cache moved;
    moved = std::move(cache);
    require(cache.size() == 0 && cache.storage_bytes() == 0 && moved.find_consumer(p->identity) == c,
            "move preserves borrowed identity backing and consumer ownership");
    moved.clear();
    require(c->words == std::vector<uint32_t>({17, 19, 23}) && e->words == std::vector<uint32_t>({7, 11, 13}),
            "cache release cannot mutate externally retained immutable data");
}

void evaluator_only_compatibility() {
    auto p = original("legacy");
    auto first = evaluator(p), replacement = evaluator(p);
    Legacy legacy;
    require(legacy.store_auxiliary(p, first), "old two-template evaluator admission");
    auto d = std::make_shared<EvaluatorDevice>(); d->portable = p; d->evaluator = first;
    require(legacy.store_device(p, {1, false}, d, sizeof(EvaluatorDevice)), "old device signature");
    require(!legacy.store_auxiliary(p, replacement), "old device prevents evaluator replacement");
    legacy.clear_devices();
    require(legacy.store_auxiliary(p, replacement) && legacy.find_auxiliary(p->identity) == replacement,
            "without a consumer, replacement after loss preserves inherited behavior");
    require(!legacy.store_consumer(p, std::make_shared<NoConsumer>()) &&
            legacy.consumer_size() == 0 && legacy.consumer_storage_bytes() == 0,
            "default third template introduces no consumer allocation");
    const auto old_portable = legacy.external_portable_bytes(std::vector<Original>{p}, std::vector<Eval>{replacement});
    const auto old_evaluator = legacy.external_auxiliary_bytes(std::vector<Eval>{replacement});
    require(old_portable.live_bytes == p->storage_bytes() && old_portable.uncached_bytes == 0 &&
            old_evaluator.live_bytes == replacement->storage_bytes() && old_evaluator.uncached_bytes == 0,
            "old external accounting signatures and allocation deduplication remain valid");
    ShaderArtifactCache<PlainDevice> plain;
    auto render = std::make_shared<PlainDevice>(); render->portable = p;
    require(plain.store_device(p, {1, false}, render, sizeof(PlainDevice)) && plain.consumer_size() == 0,
            "original one-template device caller remains supported");
}

void budget_refusals_and_eviction() {
    auto p = original("budget-A"); auto e = evaluator(p); auto c = consumer(p, e);
    Cache measured; admit(measured, p, e, c);
    const auto cpu_budget = measured.storage_bytes();
    Cache exact(1, cpu_budget); admit(exact, p, e, c);
    require(exact.storage_bytes() == cpu_budget, "exact joint CPU budget admits all three owners");
    Cache short_by_one(1, cpu_budget - 1);
    require(short_by_one.store_auxiliary(p, e), "short budget retains useful evaluator");
    const auto previous = short_by_one.storage_bytes();
    require(!short_by_one.store_consumer(p, c) && short_by_one.storage_bytes() == previous &&
            short_by_one.find_auxiliary(p->identity) == e && !short_by_one.find_consumer(p->identity),
            "one-byte consumer overrun refuses without evicting useful current owners");
    auto overflow = consumer(p, e); overflow->footprint = SIZE_MAX;
    require(!short_by_one.store_consumer(p, overflow) && short_by_one.storage_bytes() == previous,
            "saturated footprint arithmetic refuses before publishing or evicting");
    Cache disabled(0, cpu_budget), no_bytes(1, 0);
    require(!disabled.store_auxiliary(p, e) && !disabled.store_consumer(p, c) &&
            !no_bytes.store_auxiliary(p, e) && !no_bytes.store_consumer(p, c), "disabled budgets admit no graph");

    auto q = original("budget-B"); auto qe = evaluator(q); auto qc = consumer(q, qe);
    Cache both; require(both.store_auxiliary(p, e) && both.store_auxiliary(q, qe), "measure two evaluator entries");
    Cache throwing(2, both.storage_bytes());
    require(throwing.store_auxiliary(p, e) && throwing.store_auxiliary(q, qe), "two useful entries admitted");
    const auto before_throw = throwing.storage_bytes();
    qc->fail_footprint = true;
    bool caught = false;
    try { throwing.store_consumer(q, qc); } catch (const std::runtime_error&) { caught = true; }
    require(caught && throwing.storage_bytes() == before_throw && throwing.size() == 2 &&
            throwing.find_auxiliary(p->identity) == e && !throwing.find_consumer(q->identity),
            "throwing prospective footprint cannot evict another useful entry");
    qc->fail_footprint = false;
    require(throwing.store_consumer(q, qc) && throwing.size() == 1 &&
            !throwing.find_portable(p->identity) && throwing.find_consumer(q->identity) == qc &&
            throwing.storage_bytes() <= throwing.byte_limit(),
            "valid consumer growth evicts another whole graph inside the same budget");

    std::weak_ptr<const PortableShaderArtifact> wp;
    std::weak_ptr<const Evaluator> we;
    std::weak_ptr<const Consumer> wc;
    Cache one(1);
    {
        auto retired = original("retired"); auto retired_eval = evaluator(retired);
        auto retired_consumer = consumer(retired, retired_eval);
        wp = retired; we = retired_eval; wc = retired_consumer;
        admit(one, retired, retired_eval, retired_consumer);
    }
    require(!wp.expired() && !we.expired() && !wc.expired(), "cache really owns the entire old CPU graph");
    admit(one, p, e, c);
    require(wp.expired() && we.expired() && wc.expired() && one.consumer_size() == 1,
            "entry-limit eviction releases original evaluator and consumer together");
}

void complete_external_graph_accounting() {
    auto p = original("outside"); auto e = evaluator(p); auto c = consumer(p, e);
    Cache cache; admit(cache, p, e, c);
    auto duplicate_p = std::make_shared<PortableShaderArtifact>(*p);
    auto duplicate_e = evaluator(duplicate_p); auto duplicate_c = consumer(duplicate_p, duplicate_e);
    std::vector<Cons> refs{c, c, duplicate_c, nullptr};
    const auto portable = cache.external_portable_bytes(std::vector<Original>{p, p}, std::vector<Eval>{e, e}, refs);
    const auto auxiliary = cache.external_auxiliary_bytes(std::vector<Eval>{e, e}, refs);
    const auto consumers = cache.external_consumer_bytes(refs);
    require(portable.live_bytes == p->storage_bytes() + duplicate_p->storage_bytes() &&
            portable.uncached_bytes == duplicate_p->storage_bytes(), "external originals deduplicate by allocation");
    require(auxiliary.live_bytes == 1024 && auxiliary.uncached_bytes == 512,
            "external evaluator closure includes consumer-only duplicate allocation");
    require(consumers.live_bytes == 1536 && consumers.uncached_bytes == 768,
            "external consumers distinguish identity-equal allocations");
    const auto old_signature = cache.external_portable_bytes(std::vector<Original>{p}, std::vector<Eval>{e});
    require(old_signature.live_bytes == p->storage_bytes() && old_signature.uncached_bytes == 0,
            "two-range portable accounting is unchanged");
    cache.clear();
    // Only a consumer remains at the call site; this is the actual missing
    // observation graph that explicit original/evaluator ranges cannot cover.
    const auto only_original = cache.external_portable_bytes(std::vector<Original>{}, std::vector<Eval>{}, std::vector<Cons>{c, c});
    const auto only_evaluator = cache.external_auxiliary_bytes(std::vector<Eval>{}, std::vector<Cons>{c, c});
    const auto only_consumer = cache.external_consumer_bytes(std::vector<Cons>{c, c});
    require(only_original.live_bytes == p->storage_bytes() && only_original.uncached_bytes == p->storage_bytes() &&
            only_evaluator.live_bytes == 512 && only_evaluator.uncached_bytes == 512 &&
            only_consumer.live_bytes == 768 && only_consumer.uncached_bytes == 768,
            "consumer-only outside retention accounts the complete three-allocation closure");
    auto malformed = consumer(p, duplicate_e);
    const auto both_originals = cache.external_portable_bytes(std::vector<Original>{}, std::vector<Eval>{},
                                                            std::vector<Cons>{malformed});
    require(both_originals.live_bytes == p->storage_bytes() + duplicate_p->storage_bytes(),
            "malformed outside graph cannot hide a separately retained evaluator original");
}

void mutable_device_rejection() {
    for (int mutation = 0; mutation < 5; ++mutation) {
        auto p = original("mutable"); auto e = evaluator(p); auto c = consumer(p, e);
        Cache cache; admit(cache, p, e, c);
        auto d = device(p, e, c);
        require(cache.store_device(p, {9, false}, d, sizeof(Device)), "mutable device starts with exact triple");
        auto duplicate_p = std::make_shared<PortableShaderArtifact>(*p);
        auto other_eval = evaluator(p);
        if (mutation == 0) d->consumer = consumer(p, e);
        if (mutation == 1) d->evaluator = other_eval;
        if (mutation == 2) d->portable = duplicate_p;
        if (mutation == 3) c->evaluator = other_eval;
        if (mutation == 4) c->original = duplicate_p;
        require(!cache.refresh_device(p->identity, {9, false}, sizeof(Device)) && cache.size() == 0 &&
                cache.device_size() == 0 && cache.consumer_size() == 0 && cache.storage_bytes() == 0 && d->handle,
                "changed device graph evicts the complete cache entry while external live record survives");
    }
    auto p = original("oversized-device"); auto e = evaluator(p); auto c = consumer(p, e);
    Cache measured; admit(measured, p, e, c);
    auto d = device(p, e, c);
    require(measured.store_device(p, {1, false}, d, sizeof(Device)), "measure complete CPU plus device entry");
    Cache exact(1, measured.storage_bytes()); admit(exact, p, e, c);
    require(exact.store_device(p, {1, false}, d, sizeof(Device)), "exact full graph budget admits device");
    require(!exact.refresh_device(p->identity, {1, false}, SIZE_MAX) && exact.storage_bytes() == 0 &&
            c->original == p && c->evaluator == e, "device overflow releases every cache charge but preserves live graph");
}
// New policy tests use independent synthetic CPU artifacts; admitting a cache
// variant does not claim smooth/MSAA generation or physical rendering support.
void policy_identity_fields() {
    auto p = original("key-original");
    p->compiler_identity = "actual compiler revision";
    LineEvaluatorArtifact e;
    e.original = p; e.identity = "exact evaluator code/ABI/reflection identity";
    LineConsumerPolicy policy{LineCoveragePolicy::AliasedMajorAxis, 1, "exact coverage algorithm"};
    const auto key = generated_line_consumer_policy_identity(e, policy);
    require(key.find("abi=2;") != std::string::npos && key.find("samples=1;") != std::string::npos,
            "generated ABI and sample count explicitly participate in the full policy key");
    auto changed = policy; changed.coverage = LineCoveragePolicy::SmoothReference;
    require(key != generated_line_consumer_policy_identity(e, changed), "coverage enum cannot alias");
    changed = policy; changed.sample_count = 4;
    require(key != generated_line_consumer_policy_identity(e, changed), "MSAA count cannot alias");
    changed = policy; changed.coverage_identity += ";different";
    require(key != generated_line_consumer_policy_identity(e, changed), "algorithm identity cannot alias");
    auto changed_e = e; changed_e.identity += ";different";
    require(key != generated_line_consumer_policy_identity(changed_e, policy), "evaluator shader/reflection identity cannot alias");
    auto changed_p = std::make_shared<PortableShaderArtifact>(*p);
    changed_e = e; changed_e.original = changed_p;
    changed_p->identity += ";different source";
    require(key != generated_line_consumer_policy_identity(changed_e, policy), "full original shader identity cannot alias");
    changed_p->identity = p->identity; changed_p->compiler_identity += ";different";
    require(key != generated_line_consumer_policy_identity(changed_e, policy), "compiler identity cannot alias");
    changed_p->compiler_identity = p->compiler_identity; changed_p->options.base_level_sampling = true;
    require(key != generated_line_consumer_policy_identity(changed_e, policy), "sampling profile cannot alias");
    changed_p->options = p->options; changed_p->derivative_mode = SpirvDerivativeMode::AllowNonUniform;
    require(key != generated_line_consumer_policy_identity(changed_e, policy), "render derivative profile cannot alias");
    changed_e = e; changed_e.derivative_mode = SpirvDerivativeMode::AllowNonUniform;
    require(key != generated_line_consumer_policy_identity(changed_e, policy), "evaluator derivative profile remains independent");
    for (int bad = 0; bad != 4; ++bad) {
        changed = policy; changed_e = e;
        if (bad == 0) changed.sample_count = 0;
        if (bad == 1) changed.coverage_identity.clear();
        if (bad == 2) changed.coverage = static_cast<LineCoveragePolicy>(99);
        if (bad == 3) changed_e.original.reset();
        bool refused = false;
        try { generated_line_consumer_policy_identity(changed_e, changed); }
        catch (const std::invalid_argument&) { refused = true; }
        require(refused, "incomplete policy/original cannot produce an authoritative key");
    }
    // Embedded separators and NULs are length-delimited, never digest-only keys.
    changed = policy; changed.coverage_identity = std::string("a\0b", 3);
    const auto embedded = generated_line_consumer_policy_identity(e, changed);
    changed.coverage_identity = "a";
    require(embedded != generated_line_consumer_policy_identity(e, changed), "binary/full string lengths cannot alias");
}

void simultaneous_variants_and_loss() {
    auto p = original("simultaneous"); auto e = evaluator(p);
    auto a = consumer(p, e), b = consumer(p, e);
    b->identity += ";smooth-samples4-derivative-profile";
    Cache cache;
    require(cache.store_auxiliary(p, e) && cache.store_consumer(p, a), "legacy admission creates first exact variant");
    const auto first_bytes = cache.storage_bytes();
    require(cache.store_consumer(p, b->identity, b), "explicit admission adds second policy on same original/evaluator");
    const auto cpu_bytes = cache.storage_bytes();
    require(cache.consumer_size() == 2 && !cache.find_consumer(p->identity) &&
            cache.find_consumer(p->identity, a->identity) == a && cache.find_consumer(p->identity, b->identity) == b,
            "ambiguous compatibility lookup refuses and exact policy lookups retain both owners");
    require(cpu_bytes >= first_bytes + b->storage_bytes() && cache.consumer_storage_bytes() == 1536 &&
            cache.portable_size() == 1 && cache.auxiliary_size() == 1,
            "variants share one original/evaluator charge and add their own key/node footprint");
    require(cache.store_consumer(p, a) && cache.store_consumer(p, b->identity, b) && cache.storage_bytes() == cpu_bytes,
            "both overloads are idempotent in the same collection");
    auto clone = consumer(p, e); clone->identity = b->identity;
    require(!cache.store_consumer(p, clone) && !cache.store_consumer(p, a->identity, b) &&
            !cache.find_consumer(p->identity, "missing"), "key/allocation mismatch and absent policy refuse");
    require(!cache.store_auxiliary(p, evaluator(p)) && cache.find_auxiliary(p->identity) == e,
            "all retained variants pin the original evaluator");
    auto da = device(p, e, a), db = device(p, e, b);
    require(cache.store_device(p, {1, false}, da, sizeof(Device)) &&
            cache.store_device(p, {1, true}, db, sizeof(Device)), "device records may retain either exact admitted policy");
    require(!cache.store_device(p, {2, false}, device(p, e, clone), sizeof(Device)),
            "same-key unadmitted allocation cannot become a device owner");
    size_t observed = 0;
    cache.for_each_consumer([&](const auto& value) {
        require(value == a || value == b, "traversal returns exact variant pointers"); ++observed;
    });
    require(observed == 2, "traversal visits both policies exactly once");
    cache.clear_devices();
    require(cache.device_size() == 0 && cache.consumer_size() == 2 && cache.storage_bytes() == cpu_bytes &&
            cache.find_consumer(p->identity, a->identity) == a && cache.find_consumer(p->identity, b->identity) == b,
            "loss drops device owners while retaining both charged immutable policy graphs");
    require(da->handle && db->handle && da->consumer == a && db->consumer == b,
            "externally retained active device/lease graph survives cache device clearing");
    require(cache.store_device(p, {2, false}, device(p, e, b), sizeof(Device)),
            "recovery can rematerialize either retained policy without replacing CPU owners");
    Cache moved(std::move(cache));
    require(cache.size() == 0 && moved.consumer_size() == 2 && moved.find_consumer(p->identity, b->identity) == b,
            "moving map retains borrowed immutable policy key backing");
    auto changed_device = device(p, e, a);
    require(moved.store_device(p, {3, false}, changed_device, sizeof(Device)), "mutable record begins canonical");
    changed_device->consumer = clone;
    require(!moved.refresh_device(p->identity, {3, false}, sizeof(Device)) && moved.storage_bytes() == 0 &&
            a->evaluator == e && b->evaluator == e && da->handle,
            "mutable consumer mismatch evicts the whole collection without releasing active outside owners");

    struct PolicyConsumer : Consumer { std::string policy_identity; bool ok = true; };
    struct PolicyDevice { Original portable; Eval evaluator; std::shared_ptr<const PolicyConsumer> consumer; };
    ShaderArtifactCache<PolicyDevice, Evaluator, PolicyConsumer> explicit_cache;
    auto explicit_consumer = std::make_shared<PolicyConsumer>();
    explicit_consumer->original = p; explicit_consumer->evaluator = e;
    explicit_consumer->identity = "compiled full source identity differs from lookup policy";
    explicit_consumer->policy_identity = "full immutable pre-generation policy key";
    require(explicit_cache.store_auxiliary(p, e) && explicit_cache.store_consumer(p, explicit_consumer) &&
            explicit_cache.find_consumer(p->identity, explicit_consumer->policy_identity) == explicit_consumer,
            "legacy overload derives the actual policy_identity field rather than compiled source label");
    require(!explicit_cache.store_consumer(p, explicit_consumer->identity, explicit_consumer),
            "explicit key must exactly equal the consumer-owned full policy key");
    auto failed = std::make_shared<PolicyConsumer>(*explicit_consumer);
    failed->policy_identity += ";unsupported"; failed->ok = false;
    require(!explicit_cache.store_consumer(p, failed), "failed shader compilation cannot be admitted as a policy artifact");
}

void variant_budgets_and_outside_owners() {
    auto p = original("variant-budget"); auto e = evaluator(p);
    auto a = consumer(p, e), b = consumer(p, e); b->identity += ";MSAA-policy";
    Cache measured; admit(measured, p, e, a);
    require(measured.store_consumer(p, b), "measure joint two-policy budget");
    const auto all_bytes = measured.storage_bytes();
    Cache exact(1, all_bytes); admit(exact, p, e, a);
    require(exact.store_consumer(p, b) && exact.storage_bytes() == all_bytes,
            "exact combined budget includes every variant key/node and immutable owner");
    Cache short_by_one(1, all_bytes - 1); admit(short_by_one, p, e, a);
    const auto before = short_by_one.storage_bytes();
    require(!short_by_one.store_consumer(p, b) && short_by_one.storage_bytes() == before &&
            short_by_one.find_consumer(p->identity) == a, "one-byte overrun preserves all previously useful owners");
    auto overflow = consumer(p, e); overflow->identity += ";overflow"; overflow->footprint = SIZE_MAX;
    require(!exact.store_consumer(p, overflow) && exact.storage_bytes() == all_bytes && exact.consumer_size() == 2,
            "variant overflow refuses without dropping either policy");
    auto throwing = consumer(p, e); throwing->identity += ";throw"; throwing->fail_footprint = true;
    bool caught = false; try { exact.store_consumer(p, throwing); } catch (const std::runtime_error&) { caught = true; }
    require(caught && exact.storage_bytes() == all_bytes && exact.consumer_size() == 2,
            "throwing prospective variant footprint has no eviction/publication side effect");
    std::vector<Cons> live{a, b, a, nullptr};
    auto pc = exact.external_portable_bytes(std::vector<Original>{}, std::vector<Eval>{}, live);
    auto ec = exact.external_auxiliary_bytes(std::vector<Eval>{}, live);
    auto cc = exact.external_consumer_bytes(live);
    require(pc.live_bytes == p->storage_bytes() && pc.uncached_bytes == 0 && ec.live_bytes == 512 && ec.uncached_bytes == 0 &&
            cc.live_bytes == 1536 && cc.uncached_bytes == 0, "consumer-only live variants deduplicate their shared original/evaluator");
    auto active = device(p, e, b);
    require(exact.store_device(p, {1, false}, active, sizeof(Device)) == false && exact.size() == 0,
            "whole-entry device-budget overflow releases cache owners, never active live owners");
    pc = exact.external_portable_bytes(std::vector<Original>{}, std::vector<Eval>{}, live);
    ec = exact.external_auxiliary_bytes(std::vector<Eval>{}, live);
    cc = exact.external_consumer_bytes(live);
    require(pc.uncached_bytes == p->storage_bytes() && ec.uncached_bytes == 512 && cc.uncached_bytes == 1536 && active->handle,
            "evicted outside variants account all unique CPU owners and retain their active device graph");
    Cache fifo(1); admit(fifo, p, e, a); require(fifo.store_consumer(p, b), "two variants in one FIFO entry");
    auto q = original("new-FIFO-entry"); auto qe = evaluator(q); auto qc = consumer(q, qe);
    admit(fifo, q, qe, qc);
    require(!fifo.find_portable(p->identity) && fifo.consumer_size() == 1 && fifo.find_consumer(q->identity) == qc &&
            a->original == p && b->evaluator == e, "entry eviction releases every cached policy together, preserving outside owners");
    // Release all external owners to prove cache map keys do not outlive their backing.
    std::weak_ptr<const Consumer> weak_a, weak_b;
    Cache sole;
    {
        auto owned_p = original("sole-key-owner"); auto owned_e = evaluator(owned_p);
        auto owned_a = consumer(owned_p, owned_e), owned_b = consumer(owned_p, owned_e);
        owned_b->identity.assign(4096, 'z');
        weak_a = owned_a; weak_b = owned_b;
        admit(sole, owned_p, owned_e, owned_a); require(sole.store_consumer(owned_p, owned_b), "long full policy key retained");
    }
    require(!weak_a.expired() && !weak_b.expired() && sole.consumer_size() == 2 && sole.consumer_storage_bytes() > 4096,
            "cache pins both borrowed-key owners and cannot undercharge a long full policy key");
    sole.clear();
    require(weak_a.expired() && weak_b.expired() && sole.storage_bytes() == 0, "clear releases keys and backing owners together");
}

} // namespace

int main() {
    try {
        exact_owners_and_loss();
        evaluator_only_compatibility();
        budget_refusals_and_eviction();
        complete_external_graph_accounting();
        mutable_device_rejection();
        policy_identity_fields();
        simultaneous_variants_and_loss();
        variant_budgets_and_outside_owners();
        std::cout << "artifact consumer policy contract: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
