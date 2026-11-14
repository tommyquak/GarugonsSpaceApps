// Written with Super Intelligence (SI) assistance.
// Takes screenshots of the running app, one per address, by driving headless Chrome over its
// DevTools port. Used by demo_gif.py. Real waiting time is used so that map images and data
// files have loaded before each screenshot.
//
//   node app/scripts/demo_shots.mjs <out-folder> <width> <height> <wait-ms> <url> [<url> ...]
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";

const [outDir, width, height, waitMs, ...urls] = process.argv.slice(2);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9400 + Math.floor(Math.random() * 400);
const profile = `${outDir}/.chrome-profile`;
mkdirSync(outDir, { recursive: true });
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--hide-scrollbars",
  "--no-first-run", `--window-size=${width},${height}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

let page;
for (let tries = 0; tries < 60 && !page; tries++) {
  await sleep(250);
  try {
    page = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page");
  } catch { /* Chrome is still starting */ }
}
if (!page) { chrome.kill(); throw new Error("Chrome did not start"); }

const socket = new WebSocket(page.webSocketDebuggerUrl);
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

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: Number(width), height: Number(height), deviceScaleFactor: 1, mobile: false });
for (let i = 0; i < urls.length; i++) {
  await send("Page.navigate", { url: "about:blank" });
  await sleep(150);
  await send("Page.navigate", { url: urls[i] });
  await sleep(Number(waitMs) + (i === 0 ? 5000 : 0));      // the first load also fetches the app itself
  const shot = await send("Page.captureScreenshot", { format: "png" });
  const file = `${outDir}/shot_${String(i).padStart(2, "0")}.png`;
  writeFileSync(file, Buffer.from(shot.result.data, "base64"));
  console.log(file);
}
socket.close();
chrome.kill();
await sleep(300);
rmSync(profile, { recursive: true, force: true });
