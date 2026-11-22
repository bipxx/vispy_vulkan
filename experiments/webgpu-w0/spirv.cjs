const fs = require("node:fs");
const path = require("node:path");
const [tools, output] = process.argv.slice(2);
const createGlslang = require(path.resolve(tools, "glslang-0.0.15/dist/node-devel/glslang.js"));

createGlslang().then(glslang => {
    for (const [suffix, stage] of [["vert", "vertex"], ["frag", "fragment"]]) {
        const base = path.join(output, "mesh." + suffix);
        const words = glslang.compileGLSL(fs.readFileSync(base + ".glsl", "utf8"), stage);
        if (words[0] !== 0x07230203) throw new Error("Missing SPIR-V magic");
        const bytes = Buffer.alloc(words.length * 4);
        words.forEach((word, index) => bytes.writeUInt32LE(word, index * 4));
        fs.writeFileSync(base + ".spv", bytes);
        console.log(stage, bytes.length, "SPIR-V bytes");
    }
});
