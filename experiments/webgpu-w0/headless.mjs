import { spawn } from "node:child_process";
import { createReadStream, createWriteStream } from "node:fs";
import { copyFile, stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join } from "node:path";
import { finished } from "node:stream/promises";
import { fileURLToPath } from "node:url";

const [tools, output, mode] = process.argv.slice(2);
const chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";
await copyFile(fileURLToPath(new URL("./index.html", import.meta.url)), join(output, "index.html"));
const mediaTypes = {
    ".html": "text/html",
    ".mjs": "text/javascript",
    ".wasm": "application/wasm",
    ".json": "application/json",
};
const allowed = new Set([
    "index.html", "spike.mjs", "spike.wasm",
    "mesh.vert.wgsl", "mesh.frag.wgsl",
    "pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm",
    "pyodide-lock.json", "python_stdlib.zip",
]);
const { promise: result, resolve: finish } = Promise.withResolvers();
const server = createServer(async (req, res) => {
    if (req.method === "POST" && req.url === "/result") {
        let data = "";
        for await (const chunk of req) data += chunk;
        res.writeHead(204).end();
        finish(JSON.parse(data));
        return;
    }
    const { pathname } = new URL(req.url, "http://127.0.0.1");
    const pyodide = pathname.startsWith("/pyodide/");
    const name = pathname === "/" ? "index.html" : pathname.split("/").at(-1);
    if (req.method !== "GET" || !allowed.has(name)) {
        res.writeHead(404).end();
        return;
    }
    const path = join(pyodide ? join(tools, "pyodide-314.0.7") : output, name);
    try {
        const { size } = await stat(path);
        res.writeHead(200, {
            "Content-Type": mediaTypes[extname(name)] ?? "application/octet-stream",
            "Content-Length": size,
        });
        createReadStream(path).pipe(res);
    } catch {
        res.writeHead(404).end();
    }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));

const child = spawn(chrome, [
    "--headless=new", "--enable-unsafe-webgpu", "--ignore-gpu-blocklist",
    ...(process.env.W0_CHROME_SWIFTSHADER === "1" ? [
        "--use-angle=swiftshader", "--use-webgpu-adapter=swiftshader", "--enable-unsafe-swiftshader",
    ] : ["--use-angle=d3d11"]),
    ...(process.env.W0_CHROME_NO_SANDBOX === "1" ? ["--no-sandbox"] : []), "--disable-background-networking",
    "--no-first-run", "--no-default-browser-check", "--disable-breakpad", "--enable-logging=stderr",
    `--user-data-dir=${join(output, `chrome-profile-${process.pid}`)}`,
    `http://127.0.0.1:${server.address().port}/${mode === "shader" ? "?shader" : ""}`,
], { windowsHide: true, env: { ...process.env, TEMP: output, TMP: output }, stdio: ["ignore", "ignore", "pipe"] });
const stderr = createWriteStream(join(output, "chrome-stderr.log"));
child.stderr.pipe(stderr, { end: false });
const exited = new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("exit", (code, signal) => resolve({ code, signal }));
});
let timer;
try {
    const report = await Promise.race([
        result,
        exited.then(status => { throw Error(`Chrome exited early ${JSON.stringify(status)}`); }),
        new Promise((_, reject) => {
            timer = setTimeout(() => reject(Error("No browser report after 45 seconds")), 45_000);
        }),
    ]);
    console.log(JSON.stringify(report, null, 2));
    process.exitCode = report.ok ? 0 : 1;
} finally {
    clearTimeout(timer);
    child.kill();
    console.log("Chrome child wait", await exited);
    child.stderr.destroy();
    stderr.end();
    await finished(stderr);
    server.closeAllConnections();
    server.close();
}
