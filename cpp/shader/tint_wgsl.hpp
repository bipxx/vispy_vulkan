#pragma once

#include "shader/artifact.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace vispy::shader {

// The render engine owns this portable cache across device generations.
class TintWgslCache {
public:
    std::shared_ptr<const std::string> translate(const std::vector<uint32_t>& words,
                                                 SpirvDerivativeMode derivative_mode, const char* label);
    void clear();

private:
    struct Key {
        std::vector<uint32_t> words;
        SpirvDerivativeMode derivative_mode;
        bool operator==(const Key&) const = default;
    };

    struct Hash {
        size_t operator()(const Key& key) const;
    };

    std::unordered_map<Key, std::shared_ptr<const std::string>, Hash> shaders_;
    size_t bytes_ = 0;
};

}  // namespace vispy::shader
