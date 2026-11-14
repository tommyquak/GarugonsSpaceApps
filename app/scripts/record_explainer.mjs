// Written with Super Intelligence (SI) assistance.
// Records the animated explainer (app/public/explainer/index.html) frame by frame: opens it in
// headless Chrome, steps its clock with window.seek, and saves one PNG per frame. Because every
// frame is a function of time, the recording is exact and repeatable.
//
//   node app/scripts/record_explainer.mjs <out-folder> [frames-per-second] [seconds]
//
// Then join the frames with ffmpeg, for example:
//   ffmpeg -framerate 25 -i <out-folder>/frame_%04d.png -pix_fmt yuv420p -crf 18 explainer.mp4
//   ffmpeg -framerate 25 -i <out-folder>/frame_%04d.png -vf "fps=12.5,scale=880:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" explainer.gif
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const [outDir, fpsText = "20", secondsText = ""] = process.argv.slice(2);
const fps = Number(fpsText);
const page = resolve(dirname(fileURLToPath(import.meta.url)), "../public/explainer/index.html");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9400 + Math.floor(Math.random() * 400);
const profile = `${outDir}/.chrome-profile`;
mkdirSync(outDir, { recursive: true });
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--hide-scrollbars",
  "--no-first-run", "--window-size=1280,720", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

let target;
for (let tries = 0; tries < 60 && !target; tries++) {
  await sleep(250);
  try {
    target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page");
  } catch { /* Chrome is still starting */ }
}
if (!target) { chrome.kill(); throw new Error("Chrome did not start"); }

const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((done) => (socket.onopen = done));
let nextId = 0;
const waiting = new Map();
socket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.id && waiting.has(message.id)) { waiting.get(message.id)(message); waiting.delete(message.id); }
};
const send = (method, params = {}) => new Promise((done) => {
  const id = ++nextId;
  waiting.set(id, done);
  socket.send(JSON.stringify({ id, method, params }));
});
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true })).result.result.value;

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: `file://${page}?still` });
await sleep(1500);
const seconds = secondsText ? Number(secondsText) : await evaluate("window.loopSeconds");
const frames = Math.round(seconds * fps);
for (let i = 0; i < frames; i++) {
  await evaluate(`window.seek(${i / fps})`);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${outDir}/frame_${String(i).padStart(4, "0")}.png`, Buffer.from(shot.result.data, "base64"));
}
console.log(`${frames} frames at ${fps} per second in ${outDir}`);
socket.close();
chrome.kill();
await sleep(300);
rmSync(profile, { recursive: true, force: true });
