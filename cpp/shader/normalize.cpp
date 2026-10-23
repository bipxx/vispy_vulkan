#include "shader/normalize.hpp"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <limits>
#include <sstream>
#include <unordered_map>
#include <unordered_set>

namespace {

struct Tok {
    std::string text;
    int line = 1;
    bool ident = false;
};

bool custom_predicate(const std::vector<Tok>& tokens, const std::string& name) {
    for (size_t i = 1; i + 1 < tokens.size(); ++i)
        if (tokens[i].text == name && (tokens[i - 1].text == "bool" || tokens[i - 1].text.rfind("bvec", 0) == 0) &&
            tokens[i + 1].text == "(") return true;
    return false;
}

uint32_t align_up(uint32_t value, uint32_t alignment) {
    return (value + alignment - 1u) & ~(alignment - 1u);
}

bool boolean_type(const std::string& type) {
    return type == "bool" || type.rfind("bvec", 0) == 0;
}

std::string storage_type(const std::string& type) {
    if (type == "bool") return "int";
    if (type.rfind("bvec", 0) == 0) return "ivec" + type.substr(4);
    return type;
}

std::vector<Tok> tokenize(const std::string& src) {
    std::vector<Tok> out;
    int line = 1;
    for (size_t i = 0; i < src.size();) {
        char c = src[i];
        if (std::isspace(static_cast<unsigned char>(c))) {
            if (c == '\n') ++line;
            ++i;
            continue;
        }
        if (c == '/' && i + 1 < src.size() && src[i + 1] == '/') {
            i += 2;
            while (i < src.size() && src[i] != '\n') ++i;
            continue;
        }
        if (c == '/' && i + 1 < src.size() && src[i + 1] == '*') {
            i += 2;
            while (i + 1 < src.size() && !(src[i] == '*' && src[i + 1] == '/')) {
                if (src[i] == '\n') ++line;
                ++i;
            }
            i = std::min(i + 2, src.size());
            continue;
        }
        Tok tok;
        tok.line = line;
        if (c == '#') {
            do {
                while (i < src.size() && src[i] != '\n') tok.text.push_back(src[i++]);
                if (i == src.size() || tok.text.empty() || tok.text.back() != '\\') break;
                tok.text.push_back(src[i++]);
                ++line;
            } while (i < src.size());
        } else if (std::isalpha(static_cast<unsigned char>(c)) || c == '_') {
            tok.ident = true;
            while (i < src.size() && (std::isalnum(static_cast<unsigned char>(src[i])) || src[i] == '_'))
                tok.text.push_back(src[i++]);
        } else if (std::isdigit(static_cast<unsigned char>(c)) ||
                   (c == '.' && i + 1 < src.size() && std::isdigit(static_cast<unsigned char>(src[i + 1])))) {
            // A sign belongs to a number only immediately after an exponent.
            while (i < src.size()) {
                char n = src[i];
                if (std::isalnum(static_cast<unsigned char>(n)) || n == '.') tok.text.push_back(src[i++]);
                else if ((n == '+' || n == '-') && !tok.text.empty() &&
                         (tok.text.back() == 'e' || tok.text.back() == 'E')) tok.text.push_back(src[i++]);
                else break;
            }
        } else {
            tok.text.push_back(src[i++]);
            if (i < src.size()) {
                const std::string pair = tok.text + src[i];
                static const std::string ops = " ++ -- == != <= >= && || += -= *= /= %= << >> &= |= ^= ";
                if (ops.find(" " + pair + " ") != std::string::npos) tok.text.push_back(src[i++]);
            }
        }
        out.push_back(std::move(tok));
    }
    return out;
}

bool is_type(const std::string& text) {
    static const char* types[] = {
        "float", "int", "uint", "bool", "vec2", "vec3", "vec4", "ivec2", "ivec3", "ivec4",
        "uvec2", "uvec3", "uvec4", "bvec2", "bvec3", "bvec4", "mat2", "mat3", "mat4",
        "mat2x3", "mat2x4", "mat3x2", "mat3x4", "mat4x2", "mat4x3",
        "sampler1D", "sampler2D", "sampler3D", "samplerCube", "usampler2D", "isampler2D", "void"};
    for (const char* type : types) if (text == type) return true;
    return false;
}

bool is_sampler(const std::string& type) {
    return type == "sampler1D" || type == "sampler2D" || type == "sampler3D" || type == "samplerCube" ||
           type == "usampler2D" || type == "isampler2D";
}

ShaderScalarType sampler_scalar(const std::string& type) {
    return type == "usampler2D" ? ShaderScalarType::Uint :
           type == "isampler2D" ? ShaderScalarType::Sint : ShaderScalarType::Float;
}

std::string sampler_prefix(ShaderScalarType scalar) {
    return scalar == ShaderScalarType::Uint ? "u" : scalar == ShaderScalarType::Sint ? "i" : "";
}

std::string sampler_type(const NormSampler& sampler) {
    return sampler_prefix(sampler.sample_scalar) +
        (sampler.dim == "1d" ? "sampler1D" : sampler.dim == "3d" ? "sampler3D" : sampler.dim == "cube" ? "samplerCube" : "sampler2D");
}

std::string texture_type(const std::string& sampler) {
    return sampler_prefix(sampler_scalar(sampler)) +
        (sampler == "sampler1D" ? "texture1D" : sampler == "sampler3D" ? "texture3D" : sampler == "samplerCube" ? "textureCube" : "texture2D");
}

std::string sampler_dim(const std::string& type) {
    if (type == "sampler1D") return "1d";
    if (type == "sampler3D") return "3d";
    if (type == "samplerCube") return "cube";
    return "2d";
}

struct Decl {
    std::string storage;
    std::string type;
    std::string name;
    std::string interpolation;
    bool centroid = false, sample = false;
    int array_size = 0;
    int line = 1;
    size_t begin = 0;
    size_t end = 0;
};

bool qualifier(const std::string& word) {
    return word == "highp" || word == "mediump" || word == "lowp" || word == "flat" ||
           word == "smooth" || word == "noperspective" || word == "centroid" || word == "sample";
}

std::vector<Decl> find_decls(const std::vector<Tok>& tokens, std::string& error,
                           const std::string& stage) {
    std::vector<Decl> decls;
    int depth = 0, parentheses = 0;
    for (size_t i = 0; i < tokens.size(); ++i) {
        if (tokens[i].text == "{") ++depth;
        else if (tokens[i].text == "}") --depth;
        else if (tokens[i].text == "(") ++parentheses;
        else if (tokens[i].text == ")") --parentheses;
        // A composed helper can declare `in`/`out` parameters while its brace
        // depth is zero. They are function parameters, not stage interfaces.
        if (depth != 0 || parentheses != 0) continue;
        const std::string& word = tokens[i].text;
        if (word != "uniform" && word != "attribute" && word != "varying" && word != "in" && word != "out")
            continue;
        size_t j = i + 1;
        std::string interpolation;
        bool centroid = false, sample = false;
        while (j < tokens.size() && qualifier(tokens[j].text)) {
            if (tokens[j].text == "flat" || tokens[j].text == "noperspective") interpolation = tokens[j].text;
            centroid |= tokens[j].text == "centroid";
            sample |= tokens[j].text == "sample";
            ++j;
        }
        if (j >= tokens.size() || !is_type(tokens[j].text)) continue;
        const std::string type = tokens[j++].text;
        size_t begin = i;
        while (begin > 0 && qualifier(tokens[begin - 1].text)) {
            --begin;
            if (tokens[begin].text == "flat" || tokens[begin].text == "noperspective") interpolation = tokens[begin].text;
            centroid |= tokens[begin].text == "centroid";
            sample |= tokens[begin].text == "sample";
        }
        while (begin > 0 && tokens[begin - 1].text == ")") {
            size_t open = begin - 1;
            int nested = 1;
            while (open > 0 && nested) {
                --open;
                if (tokens[open].text == ")") ++nested;
                else if (tokens[open].text == "(") --nested;
            }
            if (nested || open == 0 || tokens[open - 1].text != "layout") break;
            begin = open - 1;
        }
        std::vector<Decl> declaration;
        while (j < tokens.size()) {
            if (!tokens[j].ident) break;
            Decl decl;
            decl.storage = word;
            decl.type = type;
            decl.begin = begin;
            decl.line = tokens[i].line;
            decl.name = tokens[j++].text;
            decl.interpolation = interpolation;
            decl.centroid = centroid; decl.sample = sample;
            if (j < tokens.size() && tokens[j].text == "[") {
                if (j + 2 >= tokens.size() || tokens[j + 2].text != "]" ||
                    tokens[j + 1].text.empty() ||
                    !std::all_of(tokens[j + 1].text.begin(), tokens[j + 1].text.end(),
                                 [](unsigned char c) { return std::isdigit(c); })) {
                    error = stage + " line=" + std::to_string(decl.line) + " uniform/interface " +
                            decl.name + ": array length must be a positive literal";
                    return {};
                }
                try { decl.array_size = std::stoi(tokens[j + 1].text); }
                catch (...) { decl.array_size = 0; }
                if (decl.array_size <= 0) {
                    error = stage + " line=" + std::to_string(decl.line) + " uniform/interface " +
                            decl.name + ": invalid array length";
                    return {};
                }
                j += 3;
                if (j < tokens.size() && tokens[j].text == "[") {
                    error = stage + " line=" + std::to_string(decl.line) + " interface " + decl.name +
                            ": multidimensional arrays are unsupported";
                    return {};
                }
            }
            declaration.push_back(decl);
            if (j >= tokens.size() || tokens[j].text != ",") break;
            ++j;
        }
        while (j < tokens.size() && tokens[j].text != ";") ++j;
        for (auto& decl : declaration) {
            decl.end = j;
            decls.push_back(std::move(decl));
        }
        i = j;
    }
    return decls;
}

void place_uniform(NormUniform& uni, uint32_t& cursor) {
    uni.storage_type = storage_type(uni.type);
    uint32_t alignment = 4;
    uint32_t element_size = 4;
    if (uni.type.rfind("mat", 0) == 0) {
        uni.matrix_columns = static_cast<uint32_t>(uni.type[3] - '0');
        uni.matrix_rows = uni.type.size() > 4 ? static_cast<uint32_t>(uni.type[5] - '0') : uni.matrix_columns;
        uni.component_count = uni.matrix_columns * uni.matrix_rows;
        uni.matrix_stride = 16;
        alignment = 16;
        element_size = uni.matrix_columns * uni.matrix_stride;
    } else if (uni.type.find("vec") != std::string::npos) {
        uni.component_count = static_cast<uint32_t>(uni.type.back() - '0');
        alignment = uni.component_count == 2 ? 8 : 16;
        element_size = uni.component_count * 4;
    }
    if (uni.array_size > 0) {
        alignment = std::max(16u, alignment);
        uni.array_stride = align_up(element_size, 16);
        element_size = uni.array_stride * static_cast<uint32_t>(uni.array_size);
    }
    cursor = align_up(cursor, alignment);
    uni.offset = cursor;
    uni.size = element_size;
    cursor += element_size;
}

std::string bool_storage_name(const NormUniform& uniform) {
    return "vispy_bool_storage_" + uniform.name;
}

// Generated lines map to zero; transformed expressions keep their source line.
class SourceWriter {
  public:
    explicit SourceWriter(std::vector<int>& map) : map_(map) {}
    void token(const std::string& text, int line) {
        if (!started_ || line != line_) {
            if (started_) out_ << '\n';
            map_.push_back(line);
            line_ = line;
            started_ = true;
        }
        out_ << ' ' << text;
    }
    void directive(const Tok& tok) {
        if (started_) out_ << '\n';
        out_ << tok.text << '\n';
        int source_line = tok.line;
        map_.push_back(source_line++);
        for (char ch : tok.text) if (ch == '\n') map_.push_back(source_line++);
        started_ = false;
    }
    std::string finish() {
        if (started_) out_ << '\n';
        return out_.str();
    }
  private:
    std::ostringstream out_;
    std::vector<int>& map_;
    int line_ = 0;
    bool started_ = false;
};

// GLIR keeps array element names (images[0]); generated resources need legal,
// collision-free names separate from the existing scalar resource namespace.
std::string sampler_texture_name(const NormSampler& sampler) {
    return sampler.name.find('[') == std::string::npos ? "vispy_tex_" + sampler.name :
        "vispy_array_tex_" + std::to_string(sampler.texture_binding);
}
std::string sampler_sampler_name(const NormSampler& sampler) {
    return sampler.name.find('[') == std::string::npos ? "vispy_samp_" + sampler.name :
        "vispy_array_samp_" + std::to_string(sampler.sampler_binding);
}
struct SamplerReference {
    std::string type, texture, sampler;
};
struct SamplerFunction {
    std::string name;
    size_t begin = 0, end = 0, name_token = 0;
    std::vector<std::pair<size_t, size_t>> parameters;
    std::unordered_map<size_t, SamplerReference> sampler_parameters;
    std::unordered_map<std::string, SamplerReference> locals;
};
std::vector<std::pair<size_t, size_t>> argument_ranges(const std::vector<Tok>& tokens, size_t open, size_t& close) {
    std::vector<std::pair<size_t, size_t>> ranges;
    int parens = 1, brackets = 0;
    size_t start = open + 1;
    close = start;
    for (; close < tokens.size(); ++close) {
        const auto& text = tokens[close].text;
        if (text == "(") ++parens;
        else if (text == ")") {
            if (--parens == 0) {
                if (close > start) ranges.emplace_back(start, close);
                break;
            }
        } else if (text == "[") ++brackets;
        else if (text == "]") --brackets;
        else if (text == "," && parens == 1 && brackets == 0) {
            ranges.emplace_back(start, close);
            start = close + 1;
        }
    }
    if (ranges.size() == 1 && ranges[0].second == ranges[0].first + 1 && tokens[ranges[0].first].text == "void") ranges.clear();
    return ranges;
}
bool lower_sampler_functions(const std::vector<Tok>& tokens, const std::vector<NormSampler>& samplers,
                             std::vector<bool>& skip, std::unordered_map<size_t, std::string>& replacements,
                             std::unordered_map<size_t, SamplerReference>& uses,
                             const std::vector<bool>& array_references, std::string& error) {
    std::unordered_map<std::string, SamplerReference> globals;
    std::unordered_map<std::string, uint32_t> array_sizes;
    for (const auto& sampler : samplers) {
        auto type = sampler_type(sampler);
        globals[sampler.name] = {type, sampler_texture_name(sampler), sampler_sampler_name(sampler)};
        const auto bracket = sampler.name.find('[');
        if (bracket != std::string::npos) {
            const auto index = static_cast<uint32_t>(std::stoul(sampler.name.substr(bracket + 1)));
            auto& count = array_sizes[sampler.name.substr(0, bracket)];
            count = std::max(count, index + 1);
        }
    }
    std::vector<SamplerFunction> functions;
    std::vector<bool> signature_names(tokens.size(), false);
    int braces = 0;
    for (size_t i = 0; i + 2 < tokens.size(); ++i) {
        if (tokens[i].text == "{") ++braces;
        else if (tokens[i].text == "}") --braces;
        if (braces || !is_type(tokens[i].text) || !tokens[i + 1].ident || tokens[i + 2].text != "(") continue;
        size_t close;
        auto parameters = argument_ranges(tokens, i + 2, close);
        if (close + 1 >= tokens.size() || (tokens[close + 1].text != "{" && tokens[close + 1].text != ";")) continue;
        SamplerFunction function;
        function.name = tokens[i + 1].text;
        function.name_token = i + 1;
        function.begin = i;
        function.end = close + 1;
        function.parameters = parameters;
        signature_names[i + 1] = true;
        if (tokens[close + 1].text == "{") {
            int nested = 1;
            for (function.end = close + 2; function.end < tokens.size(); ++function.end) {
                if (tokens[function.end].text == "{") ++nested;
                else if (tokens[function.end].text == "}" && --nested == 0) break;
            }
        }
        for (size_t index = 0; index < parameters.size(); ++index) {
            auto [first, last] = parameters[index];
            for (size_t type = first; type < last; ++type) {
                if (!is_sampler(tokens[type].text)) continue;
                size_t name = type + 1;
                while (name < last && qualifier(tokens[name].text)) ++name;
                if (name + 1 != last || !tokens[name].ident ||
                    std::any_of(tokens.begin() + first, tokens.begin() + type, [](const Tok& token) {
                        return token.text == "out" || token.text == "inout";
                    })) {
                    error = "line=" + std::to_string(tokens[type].line) + " helper " + function.name +
                            ": sampler parameter requires a named scalar input";
                    return false;
                }
                SamplerReference reference{tokens[type].text, "vispy_param_tex_" + tokens[name].text,
                                            "vispy_param_samp_" + tokens[name].text};
                function.sampler_parameters[index] = reference;
                function.locals[tokens[name].text] = reference;
                replacements[type] = texture_type(reference.type) + " " + reference.texture + ", sampler " + reference.sampler;
                for (size_t part = type + 1; part < last; ++part) skip[part] = true;
            }
        }
        functions.push_back(std::move(function));
        i = close;
    }
    auto resolve = [&](size_t position, const std::string& name) -> const SamplerReference* {
        for (const auto& function : functions) if (position >= function.begin && position <= function.end) {
            auto found = function.locals.find(name);
            if (found != function.locals.end()) return &found->second;
        }
        auto found = globals.find(name);
        return found == globals.end() ? nullptr : &found->second;
    };
    // Resolve literal element syntax before sampler helper argument splitting.
    // Local scalar sampler parameters still take precedence over global arrays.
    auto resolve_at = [&](size_t position, size_t first, size_t& end) -> const SamplerReference* {
        end = first + 1;
        if (auto scalar = resolve(position, tokens[first].text)) return scalar;
        auto array = array_sizes.find(tokens[first].text);
        if (array == array_sizes.end() || !array_references[first]) return nullptr;
        const auto fail = [&](const std::string& reason) -> const SamplerReference* {
            error = "line=" + std::to_string(tokens[first].line) + " sampler array " + tokens[first].text + ": " + reason;
            return nullptr;
        };
        if (first + 3 >= tokens.size() || tokens[first + 1].text != "[" || tokens[first + 3].text != "]")
            return fail("a literal nonnegative element index is required; dynamic indexing remains unsupported");
        uint64_t index = UINT64_MAX;
        size_t consumed = 0;
        const auto& literal = tokens[first + 2].text;
        // GLSL integer literals include decimal, octal and hexadecimal forms,
        // optionally with an unsigned suffix. Never reinterpret a leading-zero
        // index as decimal or accept a numeric prefix of a float/expression.
        try { index = std::stoull(literal, &consumed, 0); } catch (...) {}
        if (!consumed || (consumed != literal.size() &&
            !(consumed + 1 == literal.size() && (literal.back() == 'u' || literal.back() == 'U'))))
            return fail("a literal nonnegative integer index is required; dynamic indexing remains unsupported");
        if (index >= array->second) return fail("literal element index exceeds the declared length");
        end = first + 4;
        const auto key = tokens[first].text + '[' + std::to_string(index) + ']';
        return &globals.at(key);
    };
    for (size_t i = 0; i < tokens.size(); ++i) {
        if (!skip[i] && !replacements.contains(i) && tokens[i].ident &&
            (i + 1 >= tokens.size() || tokens[i + 1].text != "(")) {
            size_t end;
            if (auto reference = resolve_at(i, i, end)) {
                uses[i] = *reference;
                for (size_t part = i + 1; part < end; ++part) skip[part] = true;
            }
            if (!error.empty()) return false;
        }
        if (signature_names[i] || !tokens[i].ident || i + 1 >= tokens.size() || tokens[i + 1].text != "(") continue;
        bool sampler_function = false, nonsampler_overload = false;
        for (const auto& function : functions) if (function.name == tokens[i].text) {
            sampler_function |= !function.sampler_parameters.empty();
            nonsampler_overload |= function.sampler_parameters.empty();
        }
        if (!sampler_function) continue;
        size_t close;
        auto arguments = argument_ranges(tokens, i + 1, close);
        const SamplerFunction* selected = nullptr;
        std::unordered_map<size_t, const SamplerReference*> references;
        for (const auto& function : functions) {
            if (function.name != tokens[i].text || function.parameters.size() != arguments.size() || function.sampler_parameters.empty()) continue;
            bool matches = true;
            references.clear();
            for (const auto& [index, parameter] : function.sampler_parameters) {
                auto [first, last] = arguments[index];
                while (first + 1 < last && tokens[first].text == "(" && tokens[last - 1].text == ")") { ++first; --last; }
                size_t end = first;
                auto reference = first < last ? resolve_at(i, first, end) : nullptr;
                if (!error.empty()) return false;
                if (end != last) reference = nullptr;
                if (!reference || reference->type != parameter.type) { matches = false; break; }
                references[index] = reference;
            }
            if (matches) { selected = &function; break; }
        }
        if (!selected) {
            if (nonsampler_overload) continue;
            error = "line=" + std::to_string(tokens[i].line) + " helper " + tokens[i].text +
                    ": sampler argument must resolve to a declared texture or sampler parameter";
            return false;
        }
        for (const auto& [index, reference] : references) {
            const auto [first, last] = arguments[index];
            replacements[first] = reference->texture + ", " + reference->sampler;
            uses.erase(first);
            for (size_t part = first + 1; part < last; ++part) skip[part] = true;
        }
    }
    return true;
}

// End (exclusive) of a GLSL statement, used only to delimit for/while bindings.
// Expressions are not interpreted; balanced expression groups are skipped.
size_t boolean_statement_end(const std::vector<Tok>& tokens,
                             const std::vector<size_t>& mate, size_t first) {
    const size_t count = tokens.size();
    if (first >= count) return count;
    if (tokens[first].text == "{") return mate[first] < count ? mate[first] + 1 : count;
    if ((tokens[first].text == "if" || tokens[first].text == "for" || tokens[first].text == "while" ||
         tokens[first].text == "switch") &&
        first + 1 < count && tokens[first + 1].text == "(" && mate[first + 1] < count) {
        size_t end = boolean_statement_end(tokens, mate, mate[first + 1] + 1);
        if (tokens[first].text == "if" && end < count && tokens[end].text == "else")
            end = boolean_statement_end(tokens, mate, end + 1);
        return end;
    }
    if (tokens[first].text == "do") {
        const size_t end = boolean_statement_end(tokens, mate, first + 1);
        if (end + 1 < count && tokens[end].text == "while" && tokens[end + 1].text == "(" &&
            mate[end + 1] < count)
            return std::min(mate[end + 1] + 2, count);
        return end;
    }
    for (size_t i = first; i < count; ++i) {
        if (tokens[i].text == ";") return i + 1;
        if ((tokens[i].text == "(" || tokens[i].text == "[" || tokens[i].text == "{") && mate[i] < count)
            i = mate[i];
    }
    return count;
}

// Classify references without changing declarations, logical types, or storage.
// GLSL 1.20 sections 4.1.8/4.2: members have their own namespace; parameters,
// blocks and loops hide an outer name; a declarator becomes visible only after
// its initializer. This is a lexical pass over the existing tokenizer, not a
// preprocessor or type checker. Conditional/macro directives retain the exact
// legacy spelling-based behavior until a separately qualified preprocessing pass.
std::vector<bool> global_uniform_references(
        const std::vector<Tok>& tokens, const std::vector<Decl>& decls,
        const std::unordered_set<std::string>& names, bool boolean_only) {
    const size_t count = tokens.size();
    std::vector<bool> references(count, false);
    if (names.empty()) return references;
    for (size_t i = 0; i < count; ++i) references[i] = names.contains(tokens[i].text);
    for (const auto& token : tokens) if (!token.text.empty() && token.text[0] == '#') {
        size_t end = 1;
        while (end < token.text.size() && std::isspace(static_cast<unsigned char>(token.text[end]))) ++end;
        const size_t begin = end;
        while (end < token.text.size() && std::isalpha(static_cast<unsigned char>(token.text[end]))) ++end;
        const auto directive = token.text.substr(begin, end - begin);
        if (directive != "version" && directive != "line" && directive != "extension" && directive != "pragma")
            return references;
    }
    // A merged program uniform need not be declared in both shader stages.
    std::unordered_map<std::string, bool> stage_uniforms;
    for (const auto& decl : decls)
        if (decl.storage == "uniform" && names.contains(decl.name) && (!boolean_only || boolean_type(decl.type))) stage_uniforms[decl.name] = true;
    if (stage_uniforms.empty()) return std::vector<bool>(count, false);
    for (size_t i = 0; i < count; ++i)
        references[i] = references[i] && stage_uniforms.contains(tokens[i].text);

    std::vector<size_t> mate(count, count), stack;
    for (size_t i = 0; i < count; ++i) {
        const auto& text = tokens[i].text;
        if (text == "(" || text == "[" || text == "{") stack.push_back(i);
        else if (text == ")" || text == "]" || text == "}") {
            if (stack.empty()) continue;  // Original compiler diagnoses malformed syntax.
            const auto& open = tokens[stack.back()].text;
            if ((open == "(" && text == ")") || (open == "[" && text == "]") || (open == "{" && text == "}")) {
                mate[i] = stack.back(); mate[stack.back()] = i; stack.pop_back();
            }
        }
    }
    struct Scope { size_t begin, end; };
    struct Shadow { std::string name; size_t begin, end; };
    std::vector<Scope> scopes;
    std::vector<Shadow> shadows;
    std::vector<bool> member(count, false), global_decl(count, false);
    std::unordered_map<std::string, bool> struct_types;
    std::unordered_map<size_t, size_t> struct_end;
    for (const auto& decl : decls)
        for (size_t i = decl.begin; i <= decl.end && i < count; ++i) global_decl[i] = true;
    for (size_t i = 0; i < count; ++i) {
        if (tokens[i].text == "struct") {
            size_t open = i + 1;
            if (open < count && tokens[open].ident) { struct_types[tokens[open].text] = true; ++open; }
            if (open < count && tokens[open].text == "{" && mate[open] < count) {
                struct_end[i] = mate[open];
                for (size_t j = open; j <= mate[open]; ++j) member[j] = true;
            }
        }
        if (tokens[i].text == "{" && mate[i] < count) scopes.push_back({i + 1, mate[i] + 1});
        if ((tokens[i].text == "for" || tokens[i].text == "while") && i + 1 < count &&
            tokens[i + 1].text == "(" && mate[i + 1] < count)
            scopes.push_back({i + 2, boolean_statement_end(tokens, mate, mate[i + 1] + 1)});
    }
    auto type = [&](size_t i) { return is_type(tokens[i].text) || struct_types.contains(tokens[i].text); };
    // Parameter scope includes the signature and the entire function body, but
    // ends at a prototype's semicolon. A body block remains a nested scope.
    int braces = 0;
    for (size_t i = 0; i + 2 < count; ++i) {
        if (tokens[i].text == "{") ++braces;
        else if (tokens[i].text == "}") --braces;
        if (braces || !type(i) || !tokens[i + 1].ident || tokens[i + 2].text != "(" || mate[i + 2] >= count) continue;
        const size_t close = mate[i + 2];
        if (close + 1 < count && tokens[close + 1].text == "{")
            scopes.push_back({i + 3, mate[close + 1] < count ? mate[close + 1] + 1 : count});
        else if (close + 1 < count && tokens[close + 1].text == ";") scopes.push_back({i + 3, close + 1});
        i = close;
    }
    auto scope_end = [&](size_t position) {
        size_t end = count;
        bool local = false;
        for (const auto& scope : scopes) if (position >= scope.begin && position < scope.end) {
            end = std::min(end, scope.end); local = true;
        }
        return std::pair<bool, size_t>{local, end};
    };
    for (size_t i = 0; i < count; ++i) {
        if (member[i] || global_decl[i]) continue;
        // A local struct type can itself hide a global uniform name. Its
        // members are suppressed separately, never installed as local variables.
        auto structure = struct_end.find(i);
        if (structure != struct_end.end() && i + 1 < count && tokens[i + 1].ident) {
            auto [local, end] = scope_end(i);
            if (local && names.contains(tokens[i + 1].text)) {
                references[i + 1] = false;
                shadows.push_back({tokens[i + 1].text, i + 2, end});
            }
        }
        const bool inline_struct = structure != struct_end.end();
        if (!inline_struct && (!type(i) || (i && tokens[i - 1].text == "."))) continue;
        size_t name = inline_struct ? structure->second + 1 : i + 1;
        if (name < count && tokens[name].text == "[" && mate[name] < count) name = mate[name] + 1;
        if (name >= count || !tokens[name].ident || (name + 1 < count && tokens[name + 1].text == "(")) continue;
        auto [local, end] = scope_end(name);
        if (!local) continue;  // Do not legalize conflicting global declarations.
        for (; name < end && tokens[name].ident;) {
            const size_t declared = name++;
            if (name < end && tokens[name].text == "[" && mate[name] < count) name = mate[name] + 1;
            size_t visible = declared + 1;
            if (name < end && tokens[name].text == "=") {
                for (++name; name < end; ++name) {
                    const auto& text = tokens[name].text;
                    if (text == "," || text == ";" || text == ")") break;
                    if ((text == "(" || text == "[" || text == "{") && mate[name] < count) name = mate[name];
                }
                visible = name;
            }
            if (names.contains(tokens[declared].text)) {
                references[declared] = false;
                shadows.push_back({tokens[declared].text, visible, end});
            }
            if (name >= end || tokens[name].text != ",") break;
            ++name;
            // A comma in a parameter list introduces a new type, not another
            // declarator of this type; the outer scan handles that parameter.
            if (name < end && (type(name) || tokens[name].text == "const" || tokens[name].text == "in" ||
                               tokens[name].text == "out" || tokens[name].text == "inout" || qualifier(tokens[name].text))) break;
        }
    }
    for (size_t i = 0; i < count; ++i) {
        if (member[i] || (i && tokens[i - 1].text == ".")) references[i] = false;
        if (!references[i]) continue;
        for (const auto& shadow : shadows)
            if (tokens[i].text == shadow.name && i >= shadow.begin && i < shadow.end) { references[i] = false; break; }
    }
    return references;
}

std::string emit_body(const std::vector<Tok>& tokens, const std::vector<Decl>& decls,
                      const std::vector<NormUniform>& uniforms,
                      const std::vector<NormSampler>& samplers, bool vertex,
                      const NormalizeOptions& options, std::vector<int>& line_map,
                      std::string& error) {
    std::vector<bool> skip(tokens.size(), false);
    for (const Decl& decl : decls)
        for (size_t i = decl.begin; i <= decl.end && i < skip.size(); ++i) skip[i] = true;
    std::unordered_map<std::string, const NormUniform*> bools;
    for (const auto& uniform : uniforms) if (boolean_type(uniform.type)) bools[uniform.name] = &uniform;
    std::unordered_set<std::string> boolean_names, array_names;
    for (const auto& [name, uniform] : bools) boolean_names.insert(name);
    for (const auto& sampler : samplers) {
        const auto bracket = sampler.name.find('[');
        if (bracket != std::string::npos) array_names.insert(sampler.name.substr(0, bracket));
    }
    const auto boolean_references = global_uniform_references(tokens, decls, boolean_names, true);
    const auto array_references = global_uniform_references(tokens, decls, array_names, false);
    std::unordered_map<size_t, std::string> sampler_replacements;
    std::unordered_map<size_t, SamplerReference> sampler_uses;
    if (!lower_sampler_functions(tokens, samplers, skip, sampler_replacements, sampler_uses, array_references, error)) return {};
    std::unordered_map<size_t, std::vector<std::string>> suffixes;
    const bool user_isnan = custom_predicate(tokens, "isnan");
    const bool user_isinf = custom_predicate(tokens, "isinf");
    bool user_sample = false;
    for (size_t i = 1; i + 1 < tokens.size(); ++i)
        user_sample |= tokens[i].text == "sample" && is_type(tokens[i - 1].text) && tokens[i + 1].text == "(";
    SourceWriter writer(line_map);
    for (size_t i = 0; i < tokens.size(); ++i) {
        if (skip[i]) continue;
        const Tok& tok = tokens[i];
        std::string text = tok.text;
        if (auto replacement = sampler_replacements.find(i); replacement != sampler_replacements.end()) {
            writer.token(replacement->second, tok.line);
            continue;
        }
        if (!text.empty() && text[0] == '#') {
            if (text.rfind("#version", 0) != 0) writer.directive(tok);
            continue;
        }
        if (text == "precision") {
            while (i < tokens.size() && tokens[i].text != ";") ++i;
            continue;
        }
        if (text == "highp" || text == "mediump" || text == "lowp") continue;
        if (vertex && text == "main" && i > 0 && tokens[i - 1].text == "void" &&
            i + 1 < tokens.size() && tokens[i + 1].text == "(") text = "vispy_user_main";
        if (text == "gl_FragColor") text = "vispy_out_color";
        else if (text == "gl_Position" && options.line_evaluator && vertex) text = "vispy_line_clip_position";
        else if (text == "gl_VertexID") {
            if (options.line_evaluator) text = "int(vispy_line_vertex_id)";
            else if (options.point_sprites) text = "int(vispy_point_identity[gl_InstanceIndex].x)";
            else if (options.vertex_identity == VertexIdentityPolicy::Affine ||
                     options.vertex_identity == VertexIdentityPolicy::BatchAffine)
                text = "int(vispy_vertex_identity[0] + uint(gl_VertexIndex))";
            else if (options.vertex_identity == VertexIdentityPolicy::Indexed ||
                     options.vertex_identity == VertexIdentityPolicy::BatchIndexed)
                text = "int(vispy_vertex_identity[gl_VertexIndex])";
            else text = "gl_VertexIndex";
        }
        else if (text == "gl_InstanceID") text = options.line_evaluator ? "int(vispy_line_instance_id)" :
            options.point_sprites ? "int(vispy_point_identity[gl_InstanceIndex].y)" :
            batch_identity_policy(options.vertex_identity) ?
                "int(vispy_batch_instance_origin.x + uint(gl_InstanceIndex))" : "gl_InstanceIndex";
        else if (text == "gl_FrontFacing" && options.point_sprites && !vertex) text = "true";
        else if (text == "gl_FragDepthEXT") text = "gl_FragDepth";
        else if (text == "gl_PointSize") text = "vispy_point_size";
        else if (text == "gl_PointCoord") {
            if (!options.point_sprites) {
                error = "fragment line=" + std::to_string(tok.line) + ": gl_PointCoord requires admitted point-sprite lowering";
                return {};
            }
            text = "vispy_point_coord";
        }
        // Tint's pinned reader rejects OpIsNan/OpIsInf, although sampled
        // float textures can contain those bit patterns. Test exponent and
        // mantissa bits rather than relying on undefined WGSL NaN constants.
        else if (text == "isnan") text = user_isnan ? "vispy_user_isnan" : "vispy_isnan";
        else if (text == "isinf") text = user_isinf ? "vispy_user_isinf" : "vispy_isinf";
        // `sample` became an interpolation keyword after upstream's GLSL 1.20
        // Text shader was written. Preserve its helper under a distinct name.
        else if (text == "sample" && user_sample) text = "vispy_user_sample";
        const bool sample_call = tok.ident && (text == "texture1D" || text == "texture2D" || text == "texture3D" ||
                                 text == "textureCube" || text == "texture");
        if (sample_call && i + 1 < tokens.size() && tokens[i + 1].text == "(") {
            text = "texture";
            if (options.base_level_sampling) {
                size_t close = i + 2;
                int parens = 1;
                int brackets = 0;
                size_t commas = 0;
                for (; close < tokens.size(); ++close) {
                    const auto& part = tokens[close].text;
                    if (part == "(") ++parens;
                    else if (part == ")") { if (--parens == 0) break; }
                    else if (part == "[") ++brackets;
                    else if (part == "]") --brackets;
                    else if (part == "," && parens == 1 && brackets == 0) ++commas;
                }
                if (close == tokens.size() || commas != 1) {
                    error = std::string(vertex ? "vertex" : "fragment") + " line=" + std::to_string(tok.line) +
                            ": base-level texture admission requires exactly sampler and coordinate; bias is unsupported";
                    return {};
                }
                text = "textureLod";
                suffixes[close].push_back(", 0.0");
            }
        } else if (options.base_level_sampling && tok.ident &&
                   (text == "textureLod" || text == "texture1DLod" || text == "texture2DLod" || text == "texture3DLod" ||
                    text == "textureCubeLod" || text == "textureGrad" || text == "texture2DGradEXT")) {
            error = std::string(vertex ? "vertex" : "fragment") + " line=" + std::to_string(tok.line) +
                    ": explicit LOD/gradient sampling is outside base-level texture admission";
            return {};
        }
        if (auto found = sampler_uses.find(i); found != sampler_uses.end()) {
            const auto& sampler = found->second;
            text = sampler.type + "(" + sampler.texture + ", " + sampler.sampler + ")";
        }
        if (auto found = bools.find(tok.text); found != bools.end() && boolean_references[i]) {
            const auto& uniform = *found->second;
            const std::string prefix = uniform.type == "bool" ? "(" : "notEqual(";
            const std::string suffix = uniform.type == "bool" ? " != 0)" : ", " + uniform.storage_type + "(0))";
            text = prefix + bool_storage_name(uniform);
            if (uniform.array_size > 0) {
                if (i + 1 >= tokens.size() || tokens[i + 1].text != "[") {
                    error = std::string(vertex ? "vertex" : "fragment") + " line=" + std::to_string(tok.line) +
                            " uniform " + uniform.name + ": whole boolean arrays are unsupported; index the uniform";
                    return {};
                }
                size_t close = i + 2;
                int brackets = 1;
                for (; close < tokens.size(); ++close) {
                    if (tokens[close].text == "[") ++brackets;
                    if (tokens[close].text == "]" && --brackets == 0) break;
                }
                if (close == tokens.size()) {
                    error = "unterminated boolean uniform index at line=" + std::to_string(tok.line);
                    return {};
                }
                suffixes[close].push_back(suffix);
            } else text += suffix;
        }
        if (tok.text == ")") {
            auto additions = suffixes.find(i);
            if (additions != suffixes.end()) {
                for (const auto& suffix : additions->second) writer.token(suffix, tok.line);
                suffixes.erase(additions);
            }
        }
        writer.token(text, tok.line);
        if (auto additions = suffixes.find(i); additions != suffixes.end())
            for (auto suffix = additions->second.rbegin(); suffix != additions->second.rend(); ++suffix)
                writer.token(*suffix, tok.line);
    }
    return writer.finish();
}

void append_generated(std::ostringstream& output, const std::string& source, std::vector<int>& map) {
    output << source;
    for (char ch : source) if (ch == '\n') map.push_back(0);
}

}  // namespace

bool shader_value_type(const std::string& type, ShaderValueType& value) {
    value = {};
    if (type == "float") return true;
    if (type == "int" || type == "uint" || type == "bool") {
        value.scalar = type == "int" ? ShaderScalarType::Sint : type == "uint" ? ShaderScalarType::Uint : ShaderScalarType::Bool;
        return true;
    }
    for (const auto& prefix : {std::string("vec"), std::string("ivec"), std::string("uvec"), std::string("bvec")}) {
        if (type.size() == prefix.size() + 1 && type.starts_with(prefix) && type.back() >= '2' && type.back() <= '4') {
            value.rows = static_cast<uint32_t>(type.back() - '0');
            value.scalar = prefix == "vec" ? ShaderScalarType::Float : prefix == "ivec" ? ShaderScalarType::Sint :
                           prefix == "uvec" ? ShaderScalarType::Uint : ShaderScalarType::Bool;
            return true;
        }
    }
    if (type.starts_with("mat") && (type.size() == 4 || type.size() == 6) && type[3] >= '2' && type[3] <= '4') {
        value.columns = static_cast<uint32_t>(type[3] - '0');
        value.rows = value.columns;
        if (type.size() == 6) {
            if (type[4] != 'x' || type[5] < '2' || type[5] > '4') return false;
            value.rows = static_cast<uint32_t>(type[5] - '0');
        }
        return true;
    }
    return false;
}

NormalizedShader normalize_program(const std::string& vertex, const std::string& fragment) {
    return normalize_program(vertex, fragment, NormalizeOptions{});
}

NormalizedShader normalize_program(const std::string& vertex_src, const std::string& fragment_src,
                                   const NormalizeOptions& options) {
    NormalizedShader result;
    result.point_sprites = options.point_sprites;
    if (options.line_evaluator && (options.point_sprites || options.vertex_identity != VertexIdentityPolicy::Native)) {
        result.error = "line evaluator conflicts with render vertex identity/point policy";
        return result;
    }
    if ((options.point_sprites && options.vertex_identity != VertexIdentityPolicy::Native) ||
        (options.vertex_identity != VertexIdentityPolicy::Native &&
         options.vertex_identity != VertexIdentityPolicy::Affine && options.vertex_identity != VertexIdentityPolicy::Indexed &&
         !batch_identity_policy(options.vertex_identity))) {
        result.error = "vertex identity policy is invalid or conflicts with point-sprite lowering";
        return result;
    }
    auto vert_toks = tokenize(vertex_src);
    auto frag_toks = tokenize(fragment_src);
    if (batch_identity_policy(options.vertex_identity)) {
        for (const auto* tokens : {&vert_toks, &frag_toks}) for (const auto& token : *tokens) {
            // Directives are retained by the tokenizer. Reject macro aliases
            // as well as declarations that could replace either generated ABI.
            const auto words = !token.text.empty() && token.text.front() == '#' ?
                tokenize(token.text.substr(1)) : std::vector<Tok>{token};
            for (const auto& word : words) if (word.ident &&
                    (word.text == "vispy_vertex_identity" || word.text == "VispyVertexIdentity" ||
                     word.text == "vispy_batch_instance_origin" || word.text == "VispyBatchInstance")) {
                result.error = "batch identity line=" + std::to_string(token.line) + ": reserved name " + word.text;
                return result;
            }
        }
    }
    if (options.line_evaluator) {
        auto reserved = [&](const std::vector<Tok>& tokens, const std::string& stage) {
            for (const auto& token : tokens) {
                // Directives are emitted intact. Inspect their identifiers as
                // well, so a macro cannot silently replace generated ABI names.
                auto words = !token.text.empty() && token.text.front() == '#' ? tokenize(token.text.substr(1)) : std::vector<Tok>{token};
                for (const auto& word : words) if (word.ident && (word.text.starts_with("vispy_line_") || word.text.starts_with("VispyLine"))) {
                    result.error = "line evaluator " + stage + " line=" + std::to_string(token.line) + ": reserved name " + word.text;
                    return false;
                }
            }
            return true;
        };
        if (!reserved(vert_toks, "vertex") || !reserved(frag_toks, "fragment")) return result;
        for (const auto& token : vert_toks) {
            if (token.text == "buffer" || token.text == "shared" || token.text == "atomic_uint" ||
                token.text == "imageStore" || token.text.starts_with("imageAtomic")) {
                result.error = "line evaluator vertex line=" + std::to_string(token.line) + ": shared storage/side effects are unsupported (" + token.text + ")";
                return result;
            }
            if (token.text.starts_with("gl_") && token.text != "gl_Position" && token.text != "gl_VertexID" &&
                token.text != "gl_InstanceID" && token.text != "gl_PointSize") {
                result.error = "line evaluator vertex line=" + std::to_string(token.line) + ": unsupported builtin " + token.text;
                return result;
            }
        }
    }
    if (options.point_sprites) {
        for (const auto* tokens : {&vert_toks, &frag_toks}) for (const auto& token : *tokens) {
            if (token.text == "vispy_point_identity" || token.text == "VispyPointIdentity") {
                result.error = "point line=" + std::to_string(token.line) +
                    ": " + token.text + " is reserved for native vertex/instance identities";
                return result;
            }
        }
    }
    if (options.vertex_identity != VertexIdentityPolicy::Native) {
        for (const auto* tokens : {&vert_toks, &frag_toks}) for (const auto& token : *tokens) {
            if (token.text == "vispy_vertex_identity" || token.text == "VispyVertexIdentity") {
                result.error = "vertex line=" + std::to_string(token.line) + ": " + token.text +
                    " is reserved for native original vertex identities";
                return result;
            }
        }
    }
    auto vert_decls = find_decls(vert_toks, result.error, "vertex");
    if (!result.error.empty()) return result;
    auto frag_decls = find_decls(frag_toks, result.error, "fragment");
    if (!result.error.empty()) return result;
    uint32_t cursor = 0;
    std::unordered_map<std::string, int> sampler_shapes;
    auto add_uniform = [&](const Decl& decl) {
        if (!result.error.empty()) return;
        if (is_sampler(decl.type)) {
            if (decl.array_size > 0 && decl.type != "sampler2D") {
                result.error = "uniform " + decl.name + ": sampler arrays currently require floating sampler2D";
                return;
            }
            auto [shape, inserted] = sampler_shapes.emplace(decl.name, decl.array_size);
            if (!inserted && shape->second != decl.array_size) {
                result.error = "uniform " + decl.name + ": stage sampler array lengths differ";
                return;
            }
            const uint32_t count = decl.array_size > 0 ? static_cast<uint32_t>(decl.array_size) : 1;
            if (count > (UINT32_MAX - 1u) / 2u - result.samplers.size()) {
                result.error = "uniform " + decl.name + ": sampler binding extent overflows";
                return;
            }
            for (uint32_t index = 0; index < count; ++index) {
                const auto name = decl.array_size ? decl.name + '[' + std::to_string(index) + ']' : decl.name;
                auto found = std::find_if(result.samplers.begin(), result.samplers.end(),
                    [&](const auto& sampler) { return sampler.name == name; });
                if (found != result.samplers.end()) {
                    if (found->dim != sampler_dim(decl.type) || found->sample_scalar != sampler_scalar(decl.type))
                        result.error = "uniform " + decl.name + ": stage sampler types differ";
                    continue;
                }
                NormSampler sampler;
                sampler.name = name;
                sampler.dim = sampler_dim(decl.type);
                sampler.sample_scalar = sampler_scalar(decl.type);
                sampler.texture_binding = 1 + static_cast<uint32_t>(result.samplers.size()) * 2;
                sampler.sampler_binding = sampler.texture_binding + 1;
                result.samplers.push_back(std::move(sampler));
            }
            return;
        }
        for (const auto& existing : result.uniforms) {
            if (existing.name != decl.name) continue;
            if (existing.type != decl.type || existing.array_size != decl.array_size)
                result.error = "uniform " + decl.name + ": stage types or array lengths differ";
            return;
        }
        NormUniform uniform;
        uniform.name = decl.name;
        uniform.type = decl.type;
        uniform.array_size = decl.array_size;
        place_uniform(uniform, cursor);
        result.uniforms.push_back(std::move(uniform));
    };
    for (const auto& decl : vert_decls) if (decl.storage == "uniform") add_uniform(decl);
    for (const auto& decl : frag_decls) if (decl.storage == "uniform") add_uniform(decl);
    if (!result.error.empty()) return result;
    if (options.point_sprites) {
        // Reserved runtime value, appended after composer uniforms. It is
        // packed by the same reflected std140 helper as every user uniform.
        for (const auto& uniform : result.uniforms) if (uniform.name == "vispy_point_viewport") {
            result.error = "uniform vispy_point_viewport: reserved for point-sprite lowering";
            return result;
        }
        NormUniform viewport;
        viewport.name = "vispy_point_viewport";
        viewport.type = "vec2";
        place_uniform(viewport, cursor);
        result.uniforms.push_back(std::move(viewport));
    }
    result.uniform_bytes = align_up(cursor, 16);
    uint32_t location = 0;
    for (const auto& decl : vert_decls) {
        if (decl.storage != "attribute" && decl.storage != "in") continue;
        if (is_sampler(decl.type) || decl.type == "void") continue;
        if (decl.array_size > 0 || decl.type.rfind("mat", 0) == 0 || boolean_type(decl.type)) {
            result.error = "vertex attribute " + decl.name + ": matrix, array, and boolean attributes are unsupported";
            return result;
        }
        result.attributes.push_back({decl.name, decl.type, location++});
    }
    if (options.point_sprites)
        result.point_identity_binding = 1 + static_cast<uint32_t>(result.samplers.size()) * 2;
    else if (options.vertex_identity != VertexIdentityPolicy::Native)
        result.vertex_identity_binding = 1 + static_cast<uint32_t>(result.samplers.size()) * 2;
    if (batch_identity_policy(options.vertex_identity)) {
        result.batch_instance_binding = result.vertex_identity_binding + 1;
        result.batch_instance_stage_mask = 1;
    }
    std::vector<Decl> varyings;
    for (const auto& decl : vert_decls)
        if ((decl.storage == "varying" || decl.storage == "out") && decl.type != "void") varyings.push_back(decl);
    for (const auto& decl : frag_decls) {
        if ((decl.storage != "varying" && decl.storage != "in") || decl.type == "void") continue;
        bool found = false;
        for (const auto& existing : varyings) {
            if (existing.name != decl.name) continue;
            found = true;
            if (existing.type != decl.type || existing.array_size != decl.array_size ||
                existing.interpolation != decl.interpolation || existing.centroid != decl.centroid ||
                existing.sample != decl.sample) result.error = "varying " + decl.name + ": stage interfaces differ";
        }
        if (!found) varyings.push_back(decl);
    }
    if (!result.error.empty()) return result;
    uint64_t varying_location = 0;
    for (const auto& varying : varyings) {
        NormVarying value;
        value.name = varying.name; value.type = varying.type; value.interpolation = varying.interpolation.empty() ? "smooth" : varying.interpolation;
        value.array_size = varying.array_size; value.source_line = varying.line;
        value.centroid = varying.centroid; value.sample = varying.sample;
        if (!shader_value_type(value.type, value.value_type)) {
            result.error = "varying " + value.name + ": unsupported typed interface";
            return result;
        }
        for (const auto& decl : vert_decls) value.vertex_declared |= decl.name == value.name && (decl.storage == "out" || decl.storage == "varying");
        for (const auto& decl : frag_decls) value.fragment_declared |= decl.name == value.name && (decl.storage == "in" || decl.storage == "varying");
        const uint64_t span = static_cast<uint64_t>(value.value_type.columns) * (value.array_size ? value.array_size : 1);
        if (span > UINT32_MAX || varying_location > UINT32_MAX - span) {
            result.error = "varying " + value.name + ": interface location overflow";
            return result;
        }
        value.location = static_cast<uint32_t>(varying_location); varying_location += span;
        result.varyings.push_back(std::move(value));
    }
    result.has_flat_varyings = std::any_of(varyings.begin(), varyings.end(), [](const Decl& varying) {
        return varying.interpolation == "flat";
    });
    std::vector<Decl> fragment_outputs;
    for (const auto& decl : frag_decls) {
        if (decl.storage != "out") continue;
        // The GLIR framebuffer contract currently has one color attachment.
        // Keep the user's GLSL 1.30+ output name/type instead of removing its
        // declaration and leaving writes to an undeclared identifier.
        if (decl.array_size > 0) {
            result.error = "fragment line=" + std::to_string(decl.line) + " output " + decl.name +
                           ": color output arrays require multiple attachments";
            return result;
        }
        for (size_t token = decl.begin; token + 2 < frag_toks.size() && token < decl.end; ++token) {
            if ((frag_toks[token].text == "component" || frag_toks[token].text == "index") &&
                frag_toks[token + 1].text == "=") {
                result.error = "fragment line=" + std::to_string(decl.line) + " output " + decl.name +
                               ": unsupported color output layout qualifier " + frag_toks[token].text;
                return result;
            }
            if (frag_toks[token].text == "location" && frag_toks[token + 1].text == "=" &&
                (frag_toks[token + 2].text != "0" ||
                 (token + 3 < frag_toks.size() && frag_toks[token + 3].text != "," && frag_toks[token + 3].text != ")"))) {
                result.error = "fragment line=" + std::to_string(decl.line) + " output " + decl.name +
                               ": the single color attachment requires location 0";
                return result;
            }
        }
        fragment_outputs.push_back(decl);
    }
    if (fragment_outputs.size() > 1) {
        result.error = "fragment line=" + std::to_string(fragment_outputs[1].line) +
                       ": multiple color outputs require multiple attachments";
        return result;
    }
    result.has_fragment_depth = std::any_of(frag_toks.begin(), frag_toks.end(), [](const Tok& token) {
        return token.text == "gl_FragDepth" || token.text == "gl_FragDepthEXT";
    });
    std::ostringstream header;
    header << "#version 450\n";
    auto used = [&](const std::string& name) {
        auto predicate = [&](const Tok& token) { return token.text == name; };
        return std::any_of(vert_toks.begin(), vert_toks.end(), predicate) ||
               std::any_of(frag_toks.begin(), frag_toks.end(), predicate);
    };
    for (const std::string& predicate : {std::string("isnan"), std::string("isinf")}) {
        if (!used(predicate) || (custom_predicate(vert_toks, predicate) && custom_predicate(frag_toks, predicate))) continue;
        const bool nan = predicate == "isnan";
        header << "bool vispy_" << predicate << "(float value) { return (floatBitsToUint(value) & 0x7fffffffu) "
               << (nan ? ">" : "==") << " 0x7f800000u; }\n";
        for (int dimension = 2; dimension <= 4; ++dimension) {
            header << "bvec" << dimension << " vispy_" << predicate << "(vec" << dimension << " value) { return "
                   << (nan ? "greaterThan" : "equal") << "(floatBitsToUint(value) & uvec" << dimension
                   << "(0x7fffffffu), uvec" << dimension << "(0x7f800000u)); }\n";
        }
    }
    if (!result.uniforms.empty()) {
        header << "layout(set = 0, binding = 0, std140) uniform VispyUniforms {\n";
        for (const auto& uniform : result.uniforms) {
            header << "    layout(offset = " << uniform.offset << ") " << uniform.storage_type << " "
                   << (boolean_type(uniform.type) ? bool_storage_name(uniform) : uniform.name);
            if (uniform.array_size > 0) header << "[" << uniform.array_size << "]";
            header << ";\n";
        }
        header << "};\n";
    }
    for (const auto& sampler : result.samplers) {
        const std::string texture = texture_type(sampler_type(sampler));
        header << "layout(set = 0, binding = " << sampler.texture_binding << ") uniform " << texture
               << " " << sampler_texture_name(sampler) << ";\n";
        header << "layout(set = 0, binding = " << sampler.sampler_binding << ") uniform sampler "
               << sampler_sampler_name(sampler) << ";\n";
    }
    auto stage_header = [&](bool vertex) {
        std::ostringstream stage;
        stage << header.str();
        if (vertex) {
            for (const auto& attr : result.attributes)
                if (options.line_evaluator) stage << attr.type << " " << attr.name << ";\n";
                else stage << "layout(location = " << attr.location << ") in " << attr.type << " " << attr.name << ";\n";
            if (options.line_evaluator) stage << "vec4 vispy_line_clip_position;\nuint vispy_line_vertex_id, vispy_line_instance_id;\n";
            if (options.point_sprites)
                stage << "layout(std430, set = 0, binding = " << result.point_identity_binding
                      << ") readonly buffer VispyPointIdentity { uvec2 vispy_point_identity[]; };\n";
            else if (options.vertex_identity != VertexIdentityPolicy::Native)
                stage << "layout(std430, set = 0, binding = " << result.vertex_identity_binding
                      << ") readonly buffer VispyVertexIdentity { uint vispy_vertex_identity[]; };\n";
            if (batch_identity_policy(options.vertex_identity))
                stage << "layout(std140, set = 0, binding = " << result.batch_instance_binding
                      << ") uniform VispyBatchInstance { uvec4 vispy_batch_instance_origin; };\n";
        } else if (fragment_outputs.empty()) {
            stage << "layout(location = 0) out vec4 vispy_out_color;\n";
        } else {
            const auto& output = fragment_outputs.front();
            stage << "layout(location = 0) out " << output.type << " " << output.name << ";\n";
        }
        if (vertex && (options.point_sprites || vertex_src.find("gl_PointSize") != std::string::npos))
            stage << "float vispy_point_size = 1.0;\n";
        uint32_t var_location = 0;
        for (const auto& varying : result.varyings) {
            if (!(vertex && options.line_evaluator)) {
                stage << "layout(location = " << varying.location << ") ";
                if (varying.centroid) stage << "centroid ";
                if (varying.sample) stage << "sample ";
                if (varying.interpolation != "smooth") stage << varying.interpolation << " ";
                stage << (vertex ? "out " : "in ");
            }
            var_location = varying.location + varying.value_type.columns * (varying.array_size ? varying.array_size : 1);
            stage << varying.type << " " << varying.name;
            if (varying.array_size > 0) stage << "[" << varying.array_size << "]";
            stage << ";\n";
        }
        if (options.point_sprites)
            stage << "layout(location = " << var_location << ") noperspective " << (vertex ? "out" : "in") << " vec2 vispy_point_coord;\n";
        return stage.str();
    };
    std::ostringstream vert;
    append_generated(vert, stage_header(true), result.vertex_line_map);
    vert << emit_body(vert_toks, vert_decls, result.uniforms, result.samplers, true, options,
                      result.vertex_line_map, result.error);
    if (!result.error.empty()) return result;
    // User code may modify gl_Position several times or return early. The
    // coordinate transform runs exactly once on its final value.
    std::string point_wrapper;
    if (options.point_sprites) {
        point_wrapper =
            "    vec4 vispy_center = gl_Position;\n"
            "    if (vispy_center.w <= 0.0 || any(greaterThan(abs(vispy_center.xyz), vec3(vispy_center.w))) ||\n"
            "        !(vispy_point_size > 0.0) || (floatBitsToUint(vispy_point_size) & 0x7fffffffu) >= 0x7f800000u) {\n"
            "        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);\n"
            "        vispy_point_coord = vec2(0.5);\n"
            "        return;\n"
            "    }\n"
            "    const vec2 vispy_corners[6] = vec2[6](vec2(-1,-1), vec2(1,-1), vec2(-1,1),\n"
            "                                            vec2(-1,1), vec2(1,-1), vec2(1,1));\n"
            "    vec2 vispy_corner = vispy_corners[gl_VertexIndex];\n"
            "    vispy_point_coord = vec2(vispy_corner.x * 0.5 + 0.5, 0.5 - vispy_corner.y * 0.5);\n"
            "    gl_Position.xy += vispy_corner * vispy_point_size * gl_Position.w / vispy_point_viewport;\n";
    }
    if (!options.line_evaluator)
        append_generated(vert, "void main() {\n    vispy_user_main();\n" + point_wrapper + "    gl_Position.y = -gl_Position.y;\n"
                               "    gl_Position.z = (gl_Position.z + gl_Position.w) * 0.5;\n}\n", result.vertex_line_map);
    result.vertex = vert.str();
    std::ostringstream frag;
    append_generated(frag, stage_header(false), result.fragment_line_map);
    frag << emit_body(frag_toks, frag_decls, result.uniforms, result.samplers, false, options,
                      result.fragment_line_map, result.error);
    result.fragment = frag.str();
    return result;
}

bool pack_uniform_value(const NormUniform& uniform, const void* source, size_t source_bytes,
                        void* destination, size_t destination_bytes, std::string* error) {
    auto fail = [&](const std::string& reason) {
        if (error) *error = "uniform " + uniform.name + ": " + reason;
        return false;
    };
    const size_t elements = uniform.array_size > 0 ? static_cast<size_t>(uniform.array_size) : 1;
    const size_t components = uniform.component_count;
    if (components == 0 || elements > std::numeric_limits<size_t>::max() / (components * 4))
        return fail("invalid reflected component count");
    const size_t expected = elements * components * 4;
    if (source_bytes != expected) return fail("expected " + std::to_string(expected) + " source bytes, received " + std::to_string(source_bytes));
    if (!source || !destination) return fail("null source or destination");
    if (uniform.offset > destination_bytes || uniform.size > destination_bytes - uniform.offset)
        return fail("reflected layout exceeds uniform buffer bounds");
    const auto* input = static_cast<const uint8_t*>(source);
    auto* output = static_cast<uint8_t*>(destination);
    const bool matrix = uniform.matrix_stride != 0;
    if (matrix && uniform.matrix_columns * uniform.matrix_rows != components)
        return fail("inconsistent reflected matrix dimensions");
    const size_t stride = elements > 1 ? uniform.array_stride : uniform.size;
    if (elements > 1 && stride == 0) return fail("array stride is zero");
    // Validate every write before touching the destination.
    std::vector<size_t> offsets;
    offsets.reserve(elements * components);
    for (size_t element = 0; element < elements; ++element) {
        for (size_t component = 0; component < components; ++component) {
            size_t offset = element * stride;
            if (matrix) {
                const size_t column = component / uniform.matrix_rows;
                const size_t row = component % uniform.matrix_rows;
                offset += uniform.row_major ? row * uniform.matrix_stride + column * 4
                                            : column * uniform.matrix_stride + row * 4;
            } else offset += component * 4;
            if (offset > uniform.size || 4 > uniform.size - offset) return fail("component lies outside reflected member size");
            offsets.push_back(uniform.offset + offset);
        }
    }
    std::memset(output + uniform.offset, 0, uniform.size);
    for (size_t component = 0; component < offsets.size(); ++component) {
        if (boolean_type(uniform.type)) {
            int32_t value = 0;
            std::memcpy(&value, input + component * 4, 4);
            value = value != 0 ? 1 : 0;
            std::memcpy(output + offsets[component], &value, 4);
        } else std::memcpy(output + offsets[component], input + component * 4, 4);
    }
    if (error) error->clear();
    return true;
}
