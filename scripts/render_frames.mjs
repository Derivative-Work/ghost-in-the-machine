// Render frames of an HTML scene to transparent PNGs. The page must export window.renderFrame(t) (t in seconds)
// and may set window.ready (a Promise). Every frame is a pure function of (t, seed), so ranges can run in any order.
// Usage: node scripts/render_frames.mjs <scene.html> <out_dir> <start_frame> <end_frame> [seed_name=main] [w=1920] [h=1080] [fps=30] [extra query]
// --no-sandbox: Ubuntu AppArmor blocks Chrome's user-namespace sandbox on this machine; only local files are loaded.
import fs from 'fs';
import path from 'path';
import puppeteer from 'puppeteer';

const [scene, outDir, start, end, seedName = 'main', w = '1920', h = '1080', fps = '30', extra = ''] = process.argv.slice(2);
const seeds = JSON.parse(fs.readFileSync('config/seeds.json', 'utf8'));
if (!(seedName in seeds)) throw new Error(`unknown seed name: ${seedName}`);
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox', '--allow-file-access-from-files'] });
const page = await browser.newPage();
page.on('pageerror', (e) => { console.error('PAGE ERROR:', e.message); process.exitCode = 1; });
page.on('console', (m) => { if (m.type() === 'error') console.error('CONSOLE:', m.text()); });
await page.setViewport({ width: Number(w), height: Number(h) });
const url = `file://${path.resolve(scene)}?seed=${seeds[seedName]}&fps=${fps}&w=${w}&h=${h}${extra ? '&' + extra : ''}`;
await page.goto(url, { waitUntil: 'load' });
await page.evaluate(async () => { await document.fonts.ready; if (window.ready) await window.ready; });
for (let f = Number(start); f < Number(end); f++) {
  await page.evaluate((t) => window.renderFrame(t), f / Number(fps));
  await page.screenshot({ path: path.join(outDir, `${String(f).padStart(5, '0')}.png`), omitBackground: true });
}
await browser.close();
