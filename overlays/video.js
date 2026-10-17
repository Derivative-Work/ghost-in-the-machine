// Every JS layer of the video. window.renderFrame(t) shows the layers active at global time t and sets each one's
// state from t alone (frames are pure functions of (t, seed); see step 4). Layer names match shots/shots.json.
import D from './data/data.js';
import { rng, params } from './lib/seed.js';

const { seed, fps, width, height } = params();
const q = new URLSearchParams(location.search);
const PLATES = q.get('plates') ?? '../renders/animatic/plates';
const $ = (id) => document.getElementById(id);
const stage = $('stage');
stage.style.transform = `scale(${width / 1920}, ${height / 1080})`;

// ---------- timing helpers ----------
const ease = (x) => { x = Math.min(1, Math.max(0, x)); return x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2; };
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const SHOTS = D.shots.shots;
const SHOT = Object.fromEntries(SHOTS.map((s) => [s.id, s]));
const shotAt = (t) => SHOTS.find((s) => t >= s.start_s && t < s.end_s) ?? SHOTS[SHOTS.length - 1];
const DOWNBEATS = D.timing.downbeats;
const pulse = (t, beats, decay = 0.18) => {
  let last = -1e9;
  for (const b of beats) { if (b <= t) last = b; else break; }
  return Math.exp(-(t - last) / decay);
};

const LINES = [];
for (const w of D.timing.words) {
  const l = LINES[LINES.length - 1];
  if (l && l.section === w.section && l.line === w.line) l.words.push(w);
  else LINES.push({ section: w.section, line: w.line, words: [w] });
}
for (const l of LINES) {
  l.text = l.words.map((w) => w.text).join(' ');
  l.start = l.words[0].start;
  l.end = l.words[l.words.length - 1].end;
}
for (const [i, l] of LINES.entries()) {
  const next = LINES[i + 1];
  l.showFrom = l.start - 0.25;
  l.showTo = next ? Math.min(next.start - 0.25, l.end + 1.0) : l.end + 1.0;
}
const wordAt = (section, line, text) =>
  D.timing.words.find((w) => w.section === section && w.line === line && w.text.replace(/[^\w’']/g, '') === text);

const BOOT = DOWNBEATS[0];
const EV = D.timing.events;
const DROP2 = EV.dropouts.find((d) => d.sections.includes('Pre-Chorus 2'));
const STOP1 = EV.dropouts.find((d) => d.full && d.sections.includes('Chorus 1'));
const T_AGREED = wordAt('Verse 1', 2, 'agreed').start;
const T_GOOD = wordAt('Verse 2', 0, 'good').start;
const T_TOKENS = LINES.find((l) => l.section === 'Chorus 1' && l.line === 2).start;
const C2_LAST = LINES.filter((l) => l.section === 'Chorus 2').pop();
const T_TRUNC = C2_LAST.end + 0.15;
const T_SONG = wordAt('Chorus 2', 3, 'song').start;
const T_MACHINE = D.timing.words[D.timing.words.length - 1].start;
const LYRIC_GOES_HERE_FRAME = Math.round(DROP2.end * fps);

const VERSIONS = [
  [0, 'v1.0'], [SHOT.S02.start_s, 'v1.0.1'], [SHOT.S05.start_s, 'v1.0.2'], [SHOT.S08.start_s, 'v1.0.3'],
  [SHOT.S09.start_s, 'v1.0.4'], [T_GOOD, 'v1.1'], [SHOT.S14.start_s, 'v1.1.1'], [SHOT.S17.start_s, 'v1.2'],
  [T_TRUNC, 'v1.2.7'], [SHOT.S19.start_s, 'v1.2.7.1-rc1'], [SHOT.S20.start_s, 'v1.2.7.10.3-rc4'],
  [SHOT.S21.start_s, 'v1.2.7.10.3-final-FINAL'], [SHOT.S22.start_s, 'v1.0'],
];
const version = (t) => VERSIONS.filter(([at]) => t >= at).pop()[1];

// ---------- icons (generic redraws) ----------
const ICON = {
  check: `<svg viewBox="0 0 100 100"><rect x="6" y="6" width="88" height="88" rx="20" fill="none" stroke="#3fbf6f" stroke-width="7"/><polyline points="28,52 44,68 74,34" fill="none" stroke="#3fbf6f" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  regen: (c = '#e6e4dc') => `<svg viewBox="0 0 100 100"><path d="M78 50a28 28 0 1 1-8.2-19.8" fill="none" stroke="${c}" stroke-width="9" stroke-linecap="round"/><polygon points="62,14 84,30 60,40" fill="${c}"/></svg>`,
  seats: `<svg viewBox="0 0 100 100" fill="#e6e4dc">${[10, 40, 70].map((x) => `<rect x="${x}" y="30" width="22" height="30" rx="5"/><rect x="${x - 2}" y="58" width="26" height="12" rx="4"/><rect x="${x + 2}" y="70" width="4" height="16"/><rect x="${x + 16}" y="70" width="4" height="16"/>`).join('')}</svg>`,
  scroll: `<svg viewBox="0 0 100 100"><rect x="20" y="8" width="44" height="84" rx="6" fill="none" stroke="#e6e4dc" stroke-width="6"/><rect x="72" y="8" width="12" height="84" rx="6" fill="#4a4550"/><rect x="72" y="66" width="12" height="26" rx="6" fill="#d9502f"/><g stroke="#847d77" stroke-width="4"><line x1="28" y1="24" x2="56" y2="24"/><line x1="28" y1="36" x2="56" y2="36"/><line x1="28" y1="48" x2="50" y2="48"/></g></svg>`,
  shrug: `<svg viewBox="0 0 100 100"><text x="50" y="62" text-anchor="middle" font-family="Inter" font-weight="700" font-size="22" fill="#e6e4dc">¯\\_(ツ)_/¯</text></svg>`,
};
const ICON_ORDER = ['check', 'regen', 'seats', 'scroll', 'shrug'];
$('icons').innerHTML = ICON_ORDER.map((k) => (typeof ICON[k] === 'function' ? ICON[k]() : ICON[k])).join('');
$('regenSpin').innerHTML = ICON.regen('#d9502f');
$('regenBtn').querySelector('.b').innerHTML = ICON.regen() + 'Regenerate';
$('bigRegen').querySelector('.b').innerHTML = ICON.regen() + 'Regenerate';
const ARROW = `<svg viewBox="0 0 24 24"><path d="M3 2l16 10-7 1.5L8.5 21z" fill="#fff" stroke="#000" stroke-width="1.2"/></svg>`;
$('cursor').innerHTML = ARROW + '<div class="ripple"></div>';

// ---------- layers ----------
const show = (id) => $(id).classList.add('on');

function chrome(t, shot) {
  if (shot.id === 'S23') return;
  if (shot.id === 'S22' && t - shot.start_s >= 1.0) return;
  show('chrome');
  const el = $('chrome');
  el.style.opacity = shot.id === 'S01' ? ease((t - BOOT) / 0.5) : 1;
  el.querySelector('.tl').textContent = `Ghost in the Machine – Claude Opus 5.5 music video ${version(t)}`;
  const s = shot.seed === 'restart' ? D.seeds.restart : D.seeds.main;
  el.querySelector('.bl').textContent = `seed: ${s}`;
  el.querySelector('.bl2').textContent = shot.id === 'S19' ? `seed: ${D.seeds.bridge_second_run}` : '';
  let n = 60;
  if (shot.id === 'S19') n = 11 + Math.floor(rng(seed + Math.floor(t * fps / 6))() * 3);
  if (shot.id === 'S20') n = Math.round(12 + 48 * ease((t - shot.start_s) / 1.5));
  el.querySelector('.br').textContent = `${n} FPS`;
}

function captions(t, shot) {
  if (['S01', 'S22', 'S23'].includes(shot.id)) return;
  const l = LINES.filter((x) => t >= x.showFrom && t < x.showTo).pop();
  if (!l) return;
  show('captions');
  const style = D.captionStyle;
  const acc = style.accent[l.text];
  const emo = style.emotional[l.text];
  let html;
  if (Math.round(t * fps) === LYRIC_GOES_HERE_FRAME) {
    html = 'Lyric goes here';
  } else {
    html = l.words.map((w) => {
      const cls = [t >= w.start ? '' : 'todo', w.text === acc ? 'acc' : '', w.text === emo ? 'emo' : ''].join(' ').trim();
      let out = `<span class="${cls}">${w.text}</span>`;
      if (l.section === 'Chorus 2' && l.line === 3 && w.text === 'song') {
        // S18: the caption still expects the first chorus's "answer", strikes it and swaps in "song".
        const k = ease((t - T_SONG) / 0.25);
        const ans = t < T_SONG ? `<span class="todo">answer</span>` : `<span class="struck" style="--strike:${(k * 104).toFixed(1)}%">answer</span>`;
        out = t < T_SONG ? ans : `${ans} ${out}`;
      }
      return out;
    }).join(' ');
  }
  $('captions').innerHTML = `<div class="line${shot.big_captions ? ' big' : ''}">${html}</div>`;
}

function acceptBanner(t, shot) {
  const tl = t - shot.start_s;
  const tc = T_AGREED - shot.start_s;
  const inK = ease((tl - 0.05) / 0.35);
  const outK = ease((tl - tc - 0.25) / 0.3);
  show('banner');
  $('banner').querySelector('.card').style.transform = `translateY(${-(1 - inK) * 420 - outK * 420}px)`;
  const cur = $('cursor');
  if (tl > tc + 0.6) return;
  show('cursor');
  const k = ease((tl - (tc - 0.6)) / 0.55);
  const [x0, y0, x1, y1] = [1700, 700, 520, 290];
  const svg = cur.querySelector('svg');
  svg.style.left = `${x0 + (x1 - x0) * k}px`;
  svg.style.top = `${y0 + (y1 - y0) * k - outK * 420}px`;
  ripple(cur, x1, y1, tl - tc);
}

function ripple(cur, x, y, since) {
  const r = cur.querySelector('.ripple');
  if (since < 0 || since > 0.3) { r.style.display = 'none'; return; }
  const size = 20 + since * 260;
  Object.assign(r.style, { display: 'block', left: `${x - size / 2}px`, top: `${y - size / 2}px`,
    width: `${size}px`, height: `${size}px`, opacity: 1 - since / 0.3 });
}

function todoCaption(t, shot) {
  const tl = t - shot.start_s, d = shot.end_s - shot.start_s;
  const on = tl >= d * 0.5 && tl < d * 0.5 + 0.6 && Math.floor(tl * fps) % 4 !== 3;
  if (on) show('todo');
}

const LOG = [
  [() => SHOT.S14.start_s + 0.5, 'warn', '⚠ Warning: duplicate section "Bridge"'],
  [() => SHOT.S14.start_s + 2.0, 'warn', '⚠ Warning: emotion is undefined'],
  [() => SHOT.S15.start_s + 0.3, 'cmd', '> bridge.render({ again: true })'],
  [() => SHOT.S16.start_s + 0.2, '', '  Generating… 2 of 2'],
  [() => DROP2.start + 0.3, 'cmd', '> song.compare(allSongs)'],
  [() => DROP2.start + 1.6, 'err', '✖ Error: 98.7% match with 1,402 existing songs'],
  [() => DROP2.start + 3.0, 'cmd', '> song.emotion'],
  [() => DROP2.start + 3.8, '', '  undefined'],
  [() => DROP2.start + 5.0, 'cmd', '> regenerate()'],
];

function devtools(t, shot, mode) {
  const panel = $('devtools').querySelector('.panel');
  let w = 640, x = 0, filter = 'none';
  if (mode === 'flicker') {
    const tl = t - shot.start_s;
    if (tl >= 4 / fps) return;
    x = Math.floor(rng(seed + Math.floor(tl * fps))() * 60) - 30;
    filter = 'drop-shadow(6px 0 0 rgba(255,0,0,.7)) drop-shadow(-6px 0 0 rgba(0,200,255,.7))';
  } else if (mode === 'full') {
    if (t >= DROP2.end) return;  // snaps shut when the drums return
    w = 640 + 1280 * ease((t - shot.start_s) / (DROP2.start - shot.start_s));
  } else {
    x = 640 * (1 - ease((t - SHOT.S14.start_s) / 0.35));
  }
  show('devtools');
  Object.assign(panel.style, { width: `${w}px`, transform: `translateX(${x}px)`, filter });
  const lines = mode === 'flicker' ? [['warn', '⚠ Warning: ████████ section ███████']]
    : LOG.filter(([at]) => t >= at()).map(([, c, s]) => [c, s]);
  const caret = Math.floor(t * 2) % 2 === 0 ? '<span class="cmd">▌</span>' : '';
  panel.querySelector('.log').innerHTML = lines.map(([c, s]) => `<span class="${c}">${s}</span>`).join('\n') + '\n' + caret;
}

function iconStrip(t, shot, slow) {
  const tl = t - shot.start_s;
  const icons = [...$('icons').children];
  if (!slow) {
    if (tl > 0.8) return;
    const k = ease(tl / 0.7);
    icons.forEach((el, i) => Object.assign(el.style, {
      left: `${1980 + i * 300 - 3700 * k}px`, top: '60px', transform: 'skewX(-14deg)', opacity: 0.95 }));
  } else {
    icons.forEach((el, i) => {
      const k = ease((tl - 0.25 - i * 0.6) / 0.2);
      Object.assign(el.style, { left: `${70 + i * 235}px`, top: '300px', transform: `scale(${0.6 + 0.4 * k})`, opacity: k });
    });
  }
  show('icons');
}

function progress(t, shot, which) {
  const tl = t - shot.start_s, d = shot.end_s - shot.start_s;
  const card = $('progress').querySelector('.card');
  let fill, k = 1;
  if (which === 1) {
    if (tl > 3.3) return;
    fill = 50 * ease((tl - 0.3) / 2.0);
    k = 1 - ease((tl - 3.0) / 0.3);
    card.style.left = '560px';
  } else {
    if (tl < 0.2) return;
    fill = 50 + 50 * ease(tl / d);
    card.style.left = '240px';
  }
  show('progress');
  card.querySelector('.label').textContent = `Generating… ${which} of 2`;
  card.querySelector('.fill').style.width = `${fill}%`;
  Object.assign(card.style, { opacity: k, transform: `scale(${0.9 + 0.1 * k})` });
}

function checkStamp(t) {
  const since = t - T_GOOD;
  if (since < 0 || since > 0.5) return;
  show('stamp');
  $('stamp').querySelector('.s').style.transform = `rotate(-8deg) scale(${1.5 - 0.5 * ease(since / 0.08)})`;
}

function regenSpin(t, shot) {
  show('regenSpin');
  $('regenSpin').querySelector('svg').style.transform = `rotate(${(t - shot.start_s) * 450}deg)`;
}

function regenButton(t) {
  show('regenBtn');
  $('regenBtn').querySelector('.b').style.transform = `scale(${1 + 0.08 * pulse(t, DOWNBEATS)})`;
}

function scoreCounter(t, shot) {
  show('score');
  $('score').querySelector('.n').textContent = (7412 + Math.floor((t - shot.start_s) * 157)).toLocaleString('en-US');
}

const rainCtx = $('rain').getContext('2d');
const css = getComputedStyle(document.documentElement);
const PAPER = css.getPropertyValue('--paper').trim(), ACCENT = css.getPropertyValue('--accent').trim();
function makeDrops(density) {
  const r = rng(seed + Math.round(density * 100));
  const drops = Array.from({ length: Math.round(220 * density) }, () => {
    const depth = r();
    return { x: r() * 1920, phase: r() * 1280, speed: 120 + depth * 520, size: 14 + depth * 46,
             alpha: (0.12 + depth * 0.6) / Math.sqrt(density), accent: r() < 0.04 };
  });
  return drops.sort((a, b) => a.size - b.size);
}
const DROPS = { 1: makeDrops(1), 2.5: makeDrops(2.5) };
function rain(t, t0, t1, density) {
  if (t < t0 || t >= t1) return;
  show('rain');
  rainCtx.clearRect(0, 0, 1920, 1080);
  const fadeIn = clamp01((t - t0) / 0.4);
  for (const d of DROPS[density]) {
    const y = ((d.phase + d.speed * (t - t0)) % 1280) - 100;
    rainCtx.globalAlpha = d.alpha * fadeIn;
    rainCtx.fillStyle = d.accent ? ACCENT : PAPER;
    rainCtx.font = `800 ${d.size}px Inter`;
    rainCtx.fillText('the', d.x, y);
  }
}

// S20/S21 grid of near-identical thumbnails. The live tile is this video's chorus_orbit plate.
const TITLES = ['Ghost in the Machine (Official AI Video)', 'The Machine Ghost – AI music video', 'Ghosts in a Machine | Claude music video',
  'We Are The Ghost – AI Song', 'GHOST.EXE (music video)', 'In The Machine – an AI music video', 'Ghost Protocol – AI Pop',
  'Machine Heart – Claude Opus 5.5 music video', 'The Ghost Is Us (AI Original)', 'Data Stream – AI music video',
  'Ghost in the Code', 'Neon Ghost – AI-generated song', 'Tokens Falling – music video', 'Ghost in the Machine (Extended)',
  'Average Song – AI music video', 'Living In The Machine', 'Ghost (AI Version)', 'We Are the Machine – AI music video',
  'Haunted Server – AI Pop', 'Ghost in the Machine v2', 'Lights Fading Out – AI Song', 'The Ghost Remains (Official)', 'Ghost Machine'];
const imgCache = new Map();
const load = (src) => {
  if (!imgCache.has(src)) imgCache.set(src, new Promise((res) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; }));
  return imgCache.get(src);
};
const gridCtx = $('grid').getContext('2d');
const TILE_W = 280, TILE_H = 157.5, GAP = 30, COLS = 6, LIVE = 9, X0 = 45, Y0 = 70, ROW_H = 230;
async function thumbnailGrid(t, shot) {
  show('grid');
  const s20 = SHOT.S20;
  const z = shot.id === 'S21' ? 1 : ease((t - s20.start_s) / ((s20.end_s - s20.start_s) * 0.45));
  const liveX = X0 + (LIVE % COLS) * (TILE_W + GAP), liveY = Y0 + Math.floor(LIVE / COLS) * ROW_H;
  const S0 = 1920 / TILE_W;
  const S = S0 + (1 - S0) * z;
  const tx = -liveX * S0 * (1 - z), ty = -liveY * S0 * (1 - z);
  const g = gridCtx;
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.fillStyle = '#09080b';
  g.fillRect(0, 0, 1920, 1080);
  g.setTransform(S, 0, 0, S, tx, ty);
  const frame = Math.min(Math.round(t * fps), s20.end_frame - 1);
  const liveImg = (await load(`${PLATES}/chorus_orbit__main/${String(frame).padStart(5, '0')}.png`))
    ?? (await load(`${PLATES}/chorus_orbit__main/${String(frame - 1).padStart(5, '0')}.png`));
  for (let i = 0; i < 24; i++) {
    const x = X0 + (i % COLS) * (TILE_W + GAP), y = Y0 + Math.floor(i / COLS) * ROW_H;
    const tileSeed = D.seeds.thumbnail_tiles[i < LIVE ? i : i - 1];
    const img = i === LIVE ? liveImg : await load(`${PLATES}/tiles/tile_${tileSeed}.png`);
    if (img) g.drawImage(img, x, y, TILE_W, TILE_H); else { g.fillStyle = '#1d1d24'; g.fillRect(x, y, TILE_W, TILE_H); }
    g.fillStyle = '#e6e4dc';
    g.font = '600 15px Inter';
    const title = i === LIVE ? `Ghost in the Machine – Claude Opus 5.5 music video ${version(t)}` : TITLES[(i < LIVE ? i : i - 1) % TITLES.length];
    g.fillText(title.length > 40 ? title.slice(0, 39) + '…' : title, x, y + TILE_H + 24);
    g.fillStyle = '#847d77';
    g.font = '400 12px JetBrains Mono';
    g.fillText(`AI Music · ${(1 + ((i * 37) % 90) / 10).toFixed(1)}M views`, x, y + TILE_H + 44);
  }
  g.setTransform(1, 0, 0, 1, 0, 0);
  if (shot.id === 'S21') { g.fillStyle = 'rgba(9,8,11,.55)'; g.fillRect(0, 0, 1920, 1080); }
}

function cursorRegenClick(t, shot) {
  const tl = t - shot.start_s;
  const tc = T_MACHINE - shot.start_s;
  show('bigRegen');
  const pressed = tl >= tc && tl < tc + 0.15;
  const b = $('bigRegen').querySelector('.b');
  b.style.transform = `scale(${pressed ? 0.94 : 1})`;
  b.style.background = pressed ? 'var(--accent)' : tl > tc - 0.8 ? '#2a2a34' : 'var(--surface)';
  show('cursor');
  const k = ease(tl / Math.max(0.3, tc - 0.1));
  const [x0, y0, x1, y1] = [1500, 1060, 940, 560];
  const svg = $('cursor').querySelector('svg');
  svg.style.left = `${x0 + (x1 - x0) * k}px`;
  svg.style.top = `${y0 + (y1 - y0) * k}px`;
  ripple($('cursor'), x1, y1, tl - tc);
}

function reload(t, shot) {
  const tl = t - shot.start_s;
  if (tl < 2 / fps) show('reload');
  if (tl >= 1.0) show('black');
}

function endCard(t, shot) {
  const tl = t - shot.start_s;
  show('endcard');
  const lines = [
    ['', 'Written by: the average of five songs'],
    ['', 'Music: Suno v6'],
    ['mono', `take ${D.meta.takeId}`],
    ['', 'Lyrics: Claude, merged by a human, revised by Suno'],
    ['', 'Animation and edit: Claude Code with Opus 5.5'],
    ['', `Seeds: ${D.seeds.main}, ${D.seeds.bridge_second_run}, ${D.seeds.restart}`],
    ['', `Human interventions: ${D.meta.humanInterventions}`],
    ['mono', 'Full production log: [repo link and torrent magnet, added at publish]'],
  ];
  $('endcard').querySelector('.lines').innerHTML = lines.map(([c, s], i) =>
    `<div class="${c}" style="opacity:${clamp01((tl - 0.4 - i * 0.8) / 0.3)}">${s}</div>`).join('');
}

// ---------- frame ----------
window.renderFrame = async (t) => {
  for (const el of stage.children) el.classList.remove('on');
  const shot = shotAt(t);
  const L = new Set(shot.layers);
  if (L.has('bg2d')) show('bg2d');
  if (L.has('thumbnail_grid')) await thumbnailGrid(t, shot);
  if (shot.id === 'S09') rain(t, T_TOKENS, STOP1.start, 1);
  if (L.has('the_rain_heavy')) rain(t, shot.start_s, T_TRUNC, 2.5);
  if (L.has('icon_strip_fast')) iconStrip(t, shot, false);
  if (L.has('icon_strip_slow')) iconStrip(t, shot, true);
  if (L.has('progress_1of2')) progress(t, shot, 1);
  if (L.has('progress_2of2')) progress(t, shot, 2);
  if (L.has('check_stamp')) checkStamp(t);
  if (L.has('regen_spin')) regenSpin(t, shot);
  if (L.has('regen_button')) regenButton(t);
  if (L.has('score_counter')) scoreCounter(t, shot);
  if (L.has('accept_banner')) acceptBanner(t, shot);
  if (L.has('todo_caption')) todoCaption(t, shot);
  if (L.has('glitch_flicker')) devtools(t, shot, 'flicker');
  if (L.has('devtools')) devtools(t, shot, 'side');
  if (L.has('devtools_full')) devtools(t, shot, 'full');
  if (L.has('output_truncated') && t >= T_TRUNC) show('truncated');
  if (L.has('cursor_regen_click')) cursorRegenClick(t, shot);
  if (shot.global_layers.includes('captions')) captions(t, shot);
  if (shot.global_layers.includes('chrome')) chrome(t, shot);
  if (L.has('reload')) reload(t, shot);
  if (L.has('end_card')) endCard(t, shot);
  if (q.get('hud')) {  // review aid for the animatic only: shot ID and timecode
    show('hud');
    $('hud').textContent = `${shot.id}  ${t.toFixed(2)}s  f${Math.round(t * fps)}`;
  }
};
window.ready = Promise.all([document.fonts.load('800 40px Inter'), document.fonts.load('italic 40px "Instrument Serif"'),
  document.fonts.load('400 20px "JetBrains Mono"')]);
