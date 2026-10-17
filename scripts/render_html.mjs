// Render a local HTML file to a PNG with a transparent background.
// Usage: node scripts/render_html.mjs <in.html> <out.png> <width> <height>
// --no-sandbox: Ubuntu AppArmor blocks Chrome's user-namespace sandbox on this machine; only local files are loaded.
import puppeteer from 'puppeteer';
import path from 'path';
const [input, output, w, h] = process.argv.slice(2);
const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox', '--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.setViewport({ width: Number(w), height: Number(h) });
await page.goto('file://' + path.resolve(input), { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: output, omitBackground: true });
await browser.close();
