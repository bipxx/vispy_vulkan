// Reuse the retained owner-byte readers and run all prior triangle controls.
#define main retained_triangle_contract_main
#include "ordered_strip_runtime_contract.cpp"
#undef main

static std::vector<std::pair<uint32_t, uint32_t>> line_oracle(batch::Topology topology,
                                                           std::span<const uint32_t> ids) {
    std::vector<std::pair<uint32_t, uint32_t>> result;
    if (topology == batch::Topology::Lines) {
        for (size_t n = 0; n + 1 < ids.size(); n += 2) result.emplace_back(ids[n], ids[n + 1]);
    } else {
        for (size_t n = 1; n < ids.size(); ++n) result.emplace_back(ids[n - 1], ids[n]);
        if (topology == batch::Topology::LineLoop && ids.size() > 1) result.emplace_back(ids.back(), ids.front());
    }
    return result;
}

static owner::PreparedOwner<Record> prepare_lines(batch::Topology topology, const Selection& selected,
                                                 std::span<const Source> sources, uint64_t cap) {
    auto layout = compact_layout(sources, 30, 8, 2048);
    auto payload = batch::plan_ordinary_input_batches(topology, selected, sources, layout,
                                                     {cap, cap, 1ULL << 24, 100000});
    // The runtime returns before batch shader preparation for a no-op draw.
    // Keep selection validation in the planner, without imposing a live ABI.
    if (!selected.count || !selected.instances) {
        require(payload.geometry.empty() && !payload.encoded_draws, "validated no-op plan has no physical payload");
        return {};
    }
    const auto expected = batch::expected_ordinary_input_policy(topology, selected);
    batch::validate_ordinary_input_policy(topology, payload, expected);
    require(expected.mode == "lines", "thin lines lower to native independent line pairs");
    return owner::prepare_owner<Record>(std::move(payload), sources, owner_limits(), cap, Builder{});
}

static void verify_lines(batch::Topology topology, const Selection& selected,
                         std::span<const uint32_t> ids, std::span<const Source> sources, uint64_t cap) {
    auto prepared = prepare_lines(topology, selected, sources, cap);
    if (!selected.count || !selected.instances) {
        require(!prepared.root && !prepared.data, "no-op line draw creates no owner");
        return;
    }
    require(prepared.root && prepared.data, "nonempty selection has complete owned ABI2 leaves");
    const auto& data = *prepared.data;
    using Atom = std::array<uint32_t, 3>;
    std::vector<Atom> actual, expected;
    for (uint32_t instance = 0; instance < selected.instances; ++instance)
        for (const auto [a, b] : line_oracle(topology, ids)) expected.push_back({instance, a, b});
    uint64_t calls = 0;
    data.plan.for_each_draw([&](const batch::DrawRef& draw) {
        ++calls;
        const auto& geometry = data.geometry.at(draw.geometry);
        const auto& block = data.blocks.at(static_cast<size_t>(draw.instance_block));
        const auto& shape = data.plan.geometry.at(draw.geometry);
        require(block.origin && block.origin->cpu.size() == 16, "instance block retains exact origin UBO");
        auto original = [&](uint64_t n) {
            return data.plan.indexed ? word(geometry.identity->cpu, size_t(word(geometry.index->cpu, size_t(n * 4))) * 4) :
                                       word(geometry.identity->cpu, 0) + static_cast<uint32_t>(n);
        };
        for (uint64_t row = 0; row < draw.instance_count; ++row) {
            const auto instance = word(block.origin->cpu, 0) + static_cast<uint32_t>(draw.row_offset + row);
            require(instance == draw.instance_base + row, "base/row offset contributes to original instance exactly once");
            for (uint64_t n = 0; n + 1 < shape.element_count; n += 2)
                actual.push_back({instance, original(n), original(n + 1)});
            for (size_t slot = 0; slot < data.plan.layout.streams.size(); ++slot) {
                const auto& stream = data.plan.layout.streams[slot];
                const auto& record = stream.instance ? block.instances[slot] : geometry.vertices[slot];
                require(record && record->cpu.size() <= cap, "each actual physical line stream fits its granted cap");
                const auto rows = stream.instance ? 1 : data.plan.indexed ? shape.original_vertices.size() : shape.element_count;
                for (size_t n = 0; n < rows; ++n) for (const auto field : stream.fields) {
                    const auto& source = sources[field];
                    const uint32_t id = stream.instance ? instance / static_cast<uint32_t>(source.divisor) :
                        data.plan.indexed ? shape.original_vertices[n] : shape.vertex_base + static_cast<uint32_t>(n);
                    const auto from = static_cast<size_t>(source.offset + source.stride * id);
                    const auto target_row = stream.instance ? draw.row_offset + row : n;
                    for (uint64_t offset = 0; offset < source.element_bytes; offset += 4)
                        require(word(record->cpu, size_t(target_row * stream.stride + data.plan.layout.offsets[field] + offset)) ==
                                word(source.bytes, from + size_t(offset)), "line vertex/constant/divisor packing preserves all raw32 words");
                }
            }
        }
    });
    require(actual == expected, "physical line pairs preserve original order, strip seams, loop closure, LAST and instance order");
    require(calls == data.plan.encoded_draws && calls == data.counts.encoded_draws, "implicit native draw schedule matches retained owner count");
    require(data.counts.metadata_bytes == data.metadata_storage_bytes(), "line owner charges actual retained metadata capacities");
}

static void line_cases() {
    for (const auto* mode : {"lines", "line_strip", "line_loop"}) {
        require(batch::ordinary_line_batches(mode) && batch::ordinary_input_batches(mode), "all native thin-line topologies route to bounded admission");
        require(batch::defer_ordinary_u8_widening(mode, 49, 96) && !batch::defer_ordinary_u8_widening(mode, 48, 96), "line uint8 widening preserves exact allocation boundary");
    }
    require(!batch::ordinary_input_batches("points"), "point sprites keep their dedicated route");
    require(batch::loop_expansion_fits(23, 96) && !batch::loop_expansion_fits(24, 96), "loop closure index allocation includes exactly one extra index");
    require(batch::loop_expansion_fits(1, 0) && !batch::loop_expansion_fits(UINT64_MAX, UINT64_MAX), "loop allocation guard handles short and overflowing counts");
    require(batch::loop_expansion_fits(uint64_t(INT32_MAX) - 1, UINT64_MAX) &&
            !batch::loop_expansion_fits(INT32_MAX, UINT64_MAX), "loop closure obeys independent native count limit");
    require(batch::ordinary_input_domain("line_strip", "id", 13) != batch::ordinary_input_domain("line_loop", "id", 13), "line source topologies occupy separate cache domains");
    auto vertex = rows(64, 16), inst2 = rows(7, 16), inst3 = rows(5, 16), constant = rows(1, 4);
    std::vector<Source> sources{{vertex,1,1,0,16,16,0,"vertex"},
        {inst2,2,1,0,16,16,2,"divisor2"},{inst3,3,1,0,16,16,3,"divisor3"}};
    const std::vector<Source> constants{{constant,4,1,0,0,4,0,"constant"},sources[1],sources[2]};
    for (const auto topology : {batch::Topology::Lines, batch::Topology::LineStrip, batch::Topology::LineLoop}) {
        for (uint64_t count = 0; count < 20; ++count) {
            std::vector<uint32_t> ids;
            for (uint32_t n = 0; n < count; ++n) ids.push_back(5 + n);
            verify_lines(topology, {5,count,13}, ids, sources, 32);
            for (const uint32_t width : {1u,2u,4u}) {
                for (auto& id : ids) id = id % 7 + 3;
                auto bytes = indices(ids, width);
                verify_lines(topology, {0,count,13,bytes,width}, ids, sources, 32);
            }
        }
        for (const uint32_t width : {1u,2u,4u}) {
            const auto last = width == 1 ? UINT8_MAX : width == 2 ? UINT16_MAX : UINT32_MAX;
            const std::vector<uint32_t> ids{last,7,last,last,42,9,11,last,5};
            auto bytes = indices(ids, width);
            verify_lines(topology, {0,ids.size(),13,bytes,width}, ids, constants, 32);
        }
        const std::vector<uint32_t> high{0x01000001u, UINT32_MAX, 0x80000001u, 42, 42};
        auto bytes = indices(high, 4);
        verify_lines(topology, {0,high.size(),13,bytes,4}, high, constants, 32);
        verify_lines(topology, {5,high.size(),0}, high, sources, 32);
        verify_lines(topology, {0,high.size(),0,bytes,4}, high, constants, 32);
        rejects([&] { (void)prepare_lines(topology,{0,0,13,{},3},constants,32); },
                "zero-count line selections still reject malformed index widths");
        rejects([&] { (void)prepare_lines(topology,{0,2,0,{},4},constants,32); },
                "zero-instance line selections still reject truncated index revisions");
        const std::vector<Source> single_constant{constants[0]};
        const auto layout = compact_layout(single_constant, 30, 8, 2048);
        rejects([&] { (void)batch::plan_ordinary_input_batches(topology,{0,high.size(),13,bytes,4},single_constant,layout,{7,7,1ULL<<20,1000}); }, "line identity/storage minimum remains enforced");
        rejects([&] { (void)batch::plan_ordinary_input_batches(topology,{0,high.size(),13,bytes,4},single_constant,layout,{32,32,0,1000}); }, "line topology control admission remains bounded");
        const auto split = batch::plan_ordinary_input_batches(topology,{0,high.size(),13,bytes,4},single_constant,layout,{16,16,1ULL<<20,1000});
        require(split.geometry.size() > 1, "line draw-budget control actually needs multiple geometry chunks");
        rejects([&] { (void)batch::plan_ordinary_input_batches(topology,{0,high.size(),13,bytes,4},single_constant,layout,{16,16,1ULL<<20,1}); }, "line physical draw budget remains bounded");
        const std::vector<Source> missing{{{},5,1,0,4,4,0,"missing"}};
        rejects([&] { (void)prepare_lines(topology,{0,1,1},missing,32); }, "even incomplete line selections validate original source payload");
        auto held = [&] { auto local = rows(1,4); std::vector<Source> local_sources{{local,6,1,0,0,4,0,"local"}};
            return prepare_lines(topology,{0,high.size(),13,bytes,4},local_sources,32); }();
        require(held.root && held.data && held.data->geometry.front().vertices.front()->cpu.size() > 0,
                "line payload remains owned after source descriptor and backing bytes die");
    }
    batch::Plan bad;
    rejects([&] { (void)batch::ordinary_input_policy(batch::Topology::LineStrip,bad); }, "lowered strips cannot use affine index policy");
    rejects([&] { (void)batch::ordinary_input_policy(batch::Topology::LineLoop,bad); }, "lowered loops cannot use affine index policy");
}

int main() {
    if (retained_triangle_contract_main()) return 1;
    try { line_cases(); std::cout << "PASS native thin-line ABI2: " << checks << " total CPU checks; no GPU qualification\n"; return 0; }
    catch (const std::exception& error) { std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n'; return 1; }
}
