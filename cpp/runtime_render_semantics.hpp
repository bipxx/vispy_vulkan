#pragma once

#include <cstdint>

namespace vispy::render {

// Recording origin remains independent of attachment load operations. A
// masked/scissored glClear becomes a shader draw, but remains a clear operation
// in semantic telemetry. Every actual native Draw is still counted physically.
enum class SnapshotOrigin { UserDraw, Clear };

inline const char* pass_kind(SnapshotOrigin origin, bool framebuffer) {
    if (origin == SnapshotOrigin::Clear) return "clear";
    return framebuffer ? "framebuffer" : "scene";
}

inline void count_encoded_draw(SnapshotOrigin origin, uint64_t& scene_draws,
                               uint64_t& native_draws, uint64_t physical_draws = 1) {
    if (origin == SnapshotOrigin::UserDraw) ++scene_draws;
    native_draws += physical_draws;
}

}  // namespace vispy::render
