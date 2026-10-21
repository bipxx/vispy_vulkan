#include "runtime_line_variants.hpp"

#include <iostream>
#include <stdexcept>

namespace {
size_t checks = 0;
void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
struct Pipeline { int id; };
using Handle = std::shared_ptr<Pipeline>;
struct Record { std::unordered_map<std::string, Handle> variants; };
using RecordPtr = std::shared_ptr<Record>;
using Cache = vispy::lines::LineRenderVariantCache<Record, Handle>;
Handle pipeline(int id) { return std::make_shared<Pipeline>(Pipeline{id}); }

void shared_bound_and_fifo() {
    Cache cache(3);
    Cache::Variants ordinary;
    auto a = std::make_shared<Record>(), b = std::make_shared<Record>();
    auto submitted = pipeline(11);
    require(cache.publish("ordinary", submitted, {}, ordinary), "ordinary first admission");
    require(cache.publish("full A / variant 1", pipeline(21), a, ordinary), "A first admission");
    require(cache.publish("full B / variant 1", pipeline(31), b, ordinary), "B first admission");
    require(cache.size() == 3, "three routes share one FIFO");
    require(cache.publish("ordinary", pipeline(999), {}, ordinary), "warm ordinary hit");
    require(ordinary.at("ordinary") == submitted, "warm lookup preserves exact pipeline allocation");
    require(cache.publish("full A / variant 2", pipeline(22), a, ordinary), "A second variant");
    require(ordinary.empty() && a->variants.size() == 2 && b->variants.size() == 1,
            "warm access does not reorder FIFO; fourth joint admission evicts ordinary");
    require(submitted->id == 11, "encoded owner survives cache eviction");
    require(cache.publish("ordinary replacement", pipeline(12), {}, ordinary), "ordinary replacement");
    require(!a->variants.contains("full A / variant 1") && b->variants.contains("full B / variant 1"),
            "cross-policy eviction targets precise oldest map");
    require(cache.size() == 3, "joint FIFO never exceeds declared bound");
}

void detached_and_replacement_records() {
    Cache cache(2);
    Cache::Variants ordinary;
    auto old = std::make_shared<Record>();
    auto other = std::make_shared<Record>();
    cache.publish("same full policy and variant", pipeline(1), old, ordinary);
    cache.publish("B", pipeline(2), other, ordinary);
    auto snapshot = old;
    auto replacement = std::make_shared<Record>();
    cache.publish("same full policy and variant", pipeline(3), replacement, ordinary);
    require(snapshot->variants.empty(), "eviction reaches externally retained old record map");
    require(replacement->variants.at("same full policy and variant")->id == 3,
            "same-key replacement survives stale allocation FIFO entry");
    cache.publish("ordinary", pipeline(4), {}, ordinary);
    require(other->variants.empty() && replacement->variants.size() == 1,
            "subsequent eviction does not confuse identical full keys");
    cache.clear();
    require(cache.size() == 0 && replacement->variants.size() == 1,
            "generation invalidation releases FIFO owners without retagging captured record");

    Cache cleanup(2);
    auto transient = std::make_shared<Record>();
    cleanup.publish("expired", pipeline(5), transient, ordinary);
    std::weak_ptr<Record> weak = transient;
    transient.reset();
    require(weak.expired(), "FIFO never becomes a strong owner of detached record");
    cleanup.publish("next", pipeline(6), {}, ordinary);
    require(cleanup.size() == 1, "expired-record bookkeeping pruned before joint eviction");

    Cache accounting(3);
    auto shared = std::make_shared<Record>();
    accounting.publish("same record / first", pipeline(7), shared, ordinary);
    accounting.publish("same record / second", pipeline(8), shared, ordinary);
    const auto live = accounting.storage_bytes();
    shared.reset();
    require(accounting.storage_bytes() == live + 2 * sizeof(void*),
            "two expired variants retain one deduplicated weak control allocation");
}

void default_bound_and_storage() {
    Cache cache;
    Cache::Variants ordinary;
    auto a = std::make_shared<Record>(), b = std::make_shared<Record>();
    const auto empty = cache.storage_bytes();
    for (int i = 0; i < 129; ++i)
        require(cache.publish("full variant " + std::to_string(i), pipeline(i),
                i % 3 == 0 ? RecordPtr{} : (i % 3 == 1 ? a : b), ordinary), "default insertion");
    require(cache.size() == 128 && ordinary.size() + a->variants.size() + b->variants.size() == 128,
            "actual default128 bound is shared across ordinary and both policies");
    require(!ordinary.contains("full variant 0") && b->variants.contains("full variant 128"),
            "default FIFO evicts earliest and retains newest");
    auto before = cache.storage_bytes();
    cache.publish(std::string(4096, 'k'), pipeline(130), a, ordinary);
    require(cache.storage_bytes() >= before + 4000 && before > empty,
            "FIFO nodes and full key allocations are charged");
    Cache disabled(0);
    const auto count = ordinary.size();
    require(!disabled.publish("refused", pipeline(999), {}, ordinary) && ordinary.size() == count && disabled.size() == 0,
            "zero bound has no fallback allocation");
}
}  // namespace

int main() {
    try {
        shared_bound_and_fifo();
        detached_and_replacement_records();
        default_bound_and_storage();
        std::cout << "runtime line variants contract: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
