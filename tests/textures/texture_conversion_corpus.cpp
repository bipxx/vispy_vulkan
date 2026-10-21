#include "runtime_texture.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>

namespace {
std::vector<uint8_t> read(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("cannot read corpus file " + path.string());
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}
}

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: texture_conversion_corpus DIRECTORY\n"; return 2; }
    const std::filesystem::path root(argv[1]);
    std::ifstream manifest(root / "cases.txt");
    if (!manifest) { std::cerr << "missing sealed corpus manifest\n"; return 2; }
    std::string name, dtype, internal, input, expected;
    size_t count = 0, cases = 0, failures = 0;
    while (manifest >> name >> dtype >> internal >> count >> input >> expected) {
        ++cases;
        try {
            if (!count || count > static_cast<size_t>(std::numeric_limits<int>::max()))
                throw std::runtime_error("invalid logical corpus extent");
            TextureData data;
            data.channels = 1; data.format = "red"; data.internal_format = internal;
            data.width = static_cast<int>(count);
            ByteBlob upload;
            upload.dtype = dtype; upload.shape = {1, data.width, 1}; upload.bytes = read(root / input);
            apply_texture_data(data, upload, {0, 0});
            const auto actual = prepare_texture(data);
            const auto wanted = read(root / expected);
            if (actual.bytes.size() != wanted.size()) throw std::runtime_error("converted byte extent differs");
            size_t mismatches = 0, first = 0;
            for (size_t i = 0; i < wanted.size(); ++i) {
                if (actual.bytes[i] != wanted[i]) { if (!mismatches) first = i; ++mismatches; }
            }
            if (mismatches) ++failures;
            std::cout << name << " logical_values=" << count << " mismatched_bytes=" << mismatches;
            if (mismatches) std::cout << " first_byte=" << first << " expected=" << int(wanted[first]) << " actual=" << int(actual.bytes[first]);
            std::cout << '\n';
        } catch (const std::exception& error) {
            ++failures; std::cout << name << " error=" << error.what() << '\n';
        }
    }
    if (!manifest.eof() || cases != 12) { std::cerr << "all twelve independent corpus cases required\n"; return 2; }
    std::cout << "cases=" << cases << " failures=" << failures << " GPU_used=false\n";
    return failures ? 1 : 0;
}
