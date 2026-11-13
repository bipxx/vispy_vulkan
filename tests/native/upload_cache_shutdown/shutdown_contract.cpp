// SPDX-License-Identifier: AGPL-3.0-only
// Execute the real shutdown wrapper with actual CPU pools and a simulated engine teardown.
#include "runtime_byte_recycler.hpp"
#include "runtime_host_block.hpp"
#include <cstring>
#include <iostream>
#include <stdexcept>

struct Engine {
    std::mutex mu;
    vispy::memory::HostBytes live;
    bool imported = false;
    std::vector<uint8_t> bytes;

    void shutdown() {
        // Production Engine::shutdown destroys the device/imports and releases object owners first.
        if (imported) {
            vispy::memory::HostBlockPool::shared().disposed(*live);
            imported = false;
        }
        live.reset();
        vispy::memory::ByteRecycler::shared().give(std::move(bytes));
        vispy::memory::HostBlockPool::shared().free_disposed();
    }
};

Engine& engine() { static Engine value; return value; }

// Generated from cpp/runtime.cpp by the Python test, not a copy of the wrapper.
#include "shutdown_runtime_body.inc"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        auto& hosts = vispy::memory::HostBlockPool::shared();
        auto& bytes = vispy::memory::ByteRecycler::shared();
        constexpr size_t size = vispy::memory::HostBlockPool::min_bytes;
        {
            auto warm = hosts.take(size);
            std::memset(warm->data(), 0x37, warm->size());
        }
        bytes.give(std::vector<uint8_t>(size, 0x41));
        require(hosts.kept_bytes() >= size && bytes.kept_bytes() >= size, "warm-up did not fill both caches");
        shutdown_runtime();
        require(hosts.kept_bytes() == 0, "shutdown retained warm host blocks");
        require(bytes.kept_bytes() == 0, "shutdown retained recycled byte vectors");

        engine().live = hosts.take(size * 2);
        hosts.imported(*engine().live);
        engine().imported = true;
        engine().bytes.assign(size, 0x52);
        shutdown_runtime();
        require(hosts.pinned_bytes() == 0, "shutdown left an import pinned");
        require(hosts.kept_bytes() == 0, "shutdown cached a host block released by engine teardown");
        require(bytes.kept_bytes() == 0, "shutdown cached bytes released by engine teardown");

        auto external = hosts.take(size);
        std::memset(external->data(), 0x63, external->size());
        shutdown_runtime();
        require(hosts.kept_bytes() == 0 && external->data()[size - 1] == 0x63,
                "shutdown invalidated an independently owned host block");
        external.reset();
        shutdown_runtime();
        shutdown_runtime();
        require(hosts.kept_bytes() == 0 && bytes.kept_bytes() == 0, "repeated shutdown retained cache storage");
        std::cout << "PASS warm caches, engine-owned imports, external owners and repeated shutdown\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
