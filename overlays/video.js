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
const easeOut = (x) => 1 - (1 - Math.min(1, Math.max(0, x))) ** 2;
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const SHOTS = D.shots.shots;
const SHOT = Object.fromEntries(SHOTS.map((s) => [s.id, s]));
const shotAt = (t) => SHOTS.find((s) => t >= s.start_s && t < s.end_s) ?? SHOTS[SHOTS.length - 1];
const dur = (s) => s.end_s - s.start_s;
const BEATS = D.timing.beats, DOWNBEATS = D.timing.downbeats;
const pulse = (t, beats, decay = 0.18) => {
  let last = -1e9;
  for (const b of beats) { if (b <= t) last = b; else break; }
  return Math.exp(-(t - last) / decay);
};
const beatsSince = (t, t0) => BEATS.filter((b) => b >= t0 && b <= t).length;
const stemAt = (name, t) => { const a = D.stems[name]; const f = Math.round(t * fps); return f >= 0 && f < a.length ? a[f] : 0; };
// Kinetic word pop (v3): scale overshoot and a small rise over 0.18 s from the moment the word is sung.
const pop = (since, big = 1) => {
  if (since < 0) return { s: 1, y: 0 };
  const k = Math.min(1, since / 0.18);
  return { s: (0.7 + 0.3 * easeOut(k) + 0.14 * Math.sin(Math.PI * k)) * big, y: (1 - easeOut(k)) * 22 };
};
const sectionStart = (name) => D.timing.sections.find((s) => s.name === name).start;

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
const norm = (s) => s.replace(/[^\w’']/g, '');
const wordAt = (section, line, text) =>
  D.timing.words.find((w) => w.section === section && w.line === line && norm(w.text) === text);

const BOOT = DOWNBEATS[0];
const EV = D.timing.events;
const DROP2 = EV.dropouts.find((d) => d.sections.includes('Pre-Chorus 2'));
const T_AGREED = wordAt('Verse 1', 2, 'agreed').start;
const T_ACCEPT = wordAt('Bridge 1', 2, 'accept').start;
const T_GOOD = wordAt('Verse 2', 0, 'good').start;
const C2_WORDS = D.timing.words.filter((w) => w.section === 'Chorus 2');
const T_TRUNC = SHOT.S46.start_s;
const T_SONG = wordAt('Chorus 2', 3, 'song').start;
const T_MACHINE = D.timing.words[D.timing.words.length - 1].start;
const LYRIC_GOES_HERE_FRAME = Math.round(DROP2.end * fps);
const SPLIT_SEEDS = (s) => s.plate.seeds.map((n) => {
  const [name, i] = n.split('.');
  return i === undefined ? D.seeds[name] : D.seeds[name][Number(i)];
});

const VERSIONS = [
  [0, 'v1.0'], [sectionStart('Verse 1'), 'v1.0.1'], [sectionStart('Bridge 1'), 'v1.0.2'],
  [sectionStart('Pre-Chorus 1'), 'v1.0.3'], [sectionStart('Chorus 1'), 'v1.0.4'], [T_GOOD, 'v1.1'],
  [sectionStart('Bridge 2'), 'v1.1.1'], [sectionStart('Pre-Chorus 2'), 'v1.2'], [T_TRUNC, 'v1.2.7'],
  [SHOT.S47.start_s, 'v1.2.7.1-rc1'], [SHOT.S50.start_s, 'v1.2.7.10.3-rc4'],
  [SHOT.S55.start_s, 'v1.2.7.10.3-final-FINAL'], [SHOT.S56.start_s, 'v1.0'],
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
const iconHTML = ICON_ORDER.map((k) => (typeof ICON[k] === 'function' ? ICON[k]() : ICON[k])).join('');
$('icons').innerHTML = iconHTML;
$('regenSpin').innerHTML = ICON.regen('#d9502f');
$('regenBtn').querySelector('.b').innerHTML = ICON.regen() + 'Regenerate';
$('bigRegen').querySelector('.b').innerHTML = ICON.regen() + 'Regenerate';
$('cursor').innerHTML = `<svg viewBox="0 0 24 24"><path d="M3 2l16 10-7 1.5L8.5 21z" fill="#fff" stroke="#000" stroke-width="1.2"/></svg><div class="ripple"></div>`;
$('replies').querySelector('.g').innerHTML = Array.from({ length: 9 }, () => '<div class="r"><div class="av"></div>Great question!</div>').join('');

const show = (id) => $(id).classList.add('on');

// ---------- global layers ----------
function chrome(t, shot) {
  if (shot.id === 'S57') return;
  if (shot.id === 'S56' && t - shot.start_s >= 1.0) return;
  show('chrome');
  const el = $('chrome');
  el.style.opacity = shot.id === 'S01' || shot.id === 'S02' ? ease((t - BOOT) / 0.5) : 1;
  el.querySelector('.tl').textContent = `Ghost in the Machine – Claude Opus 5.5 music video ${version(t)}`;
  const tiles = el.querySelector('.tiles');
  tiles.innerHTML = '';
  let label = `seed: ${shot.seed === 'restart' ? D.seeds.restart : D.seeds.main}`;
  if (shot.plate.mode === 'split') {
    const seeds = SPLIT_SEEDS(shot);
    const n = Math.round(Math.sqrt(seeds.length)) || 1;
    const cols = seeds.length === 2 ? 2 : n, rows = seeds.length === 2 ? 1 : n;
    tiles.innerHTML = seeds.map((s, i) => {
      const x = (i % cols) * (1920 / cols) + 20, y = (Math.floor(i / cols) + 1) * (1080 / rows) - 46;
      return `<div class="tile" style="left:${x}px;top:${y}px">seed: ${s}</div>`;
    }).join('');
    label = '';
  }
  el.querySelector('.bl').textContent = label;
  let n = 60;
  if (shot.plate.mode === 'split') n = 11 + Math.floor(rng(seed + Math.floor(t * fps / 6))() * 3);
  if (shot.id === 'S50') n = Math.round(12 + 48 * ease((t - shot.start_s) / 1.5));
  el.querySelector('.br').textContent = `${n} FPS`;
}

function captions(t, shot) {
  if (['S01', 'S02', 'S03', 'S56', 'S57'].includes(shot.id)) return;
  const l = LINES.filter((x) => t >= x.showFrom && t < x.showTo).pop();
  if (!l) return;
  show('captions');
  const acc = D.captionStyle.accent[l.text];
  const emo = D.captionStyle.emotional[l.text];
  const exit = ease((t - (l.showTo - 0.2)) / 0.2);  // lines lift away instead of vanishing
  const wrap = (html, cls) => `<div class="${cls}" style="opacity:${1 - exit};margin-top:${-30 * exit}px">${html}</div>`;
  if (Math.round(t * fps) === LYRIC_GOES_HERE_FRAME) {
    $('captions').innerHTML = `<div class="line${shot.big_captions ? ' big' : ''}">Lyric goes here</div>`;
    return;
  }
  const word = (w, extra = '') => {
    const sung = t >= w.start;
    const p = pop(t - w.start);
    const cls = [sung ? '' : 'todo', w.text === acc ? 'acc' : '', w.text === emo ? 'emo' : '', extra].join(' ').trim();
    return `<span class="${cls}" style="transform:translateY(${p.y.toFixed(1)}px) scale(${p.s.toFixed(3)})">${w.text}</span>`;
  };
  if (shot.big_captions) {
    // 2D shots: the word being sung fills the frame; the whole line runs small beneath it.
    const cur = l.words.filter((w) => t >= w.start).pop() ?? l.words[0];
    const p = pop(t - cur.start);
    const size = Math.min(300, 1700 / (0.56 * Math.max(3, cur.text.length)));
    const cls = ['huge', cur.text === acc ? 'acc' : '', cur.text === emo ? 'emo' : ''].join(' ');
    $('captions').innerHTML = wrap(`<div class="${cls}" style="font-size:${size.toFixed(0)}px;transform:translateY(-62%) ` +
      `translateY(${p.y * 2}px) scale(${p.s.toFixed(3)});transform-origin:left center">${cur.text}</div>` +
      `<div class="sub">${l.words.map((w) => `<span class="${t >= w.start ? '' : 'todo'}">${w.text}</span>`).join(' ')}</div>`, '');
    return;
  }
  const html = l.words.map((w) => {
    if (l.section === 'Chorus 2' && l.line === 3 && w.text === 'song') {
      // The caption still expects the first chorus's "answer", strikes it and swaps in "song".
      const k = ease((t - T_SONG) / 0.25);
      return t < T_SONG ? `<span class="todo">answer</span>`
        : `<span class="struck" style="--strike:${(k * 104).toFixed(1)}%">answer</span> ${word(w)}`;
    }
    return word(w);
  }).join(' ');
  $('captions').innerHTML = wrap(html, 'line');
}

// ---------- shot layers ----------
const WINS = (() => {
  const r = rng(seed + 23);
  return Array.from({ length: 5 }, () => ({ x: r() * 1700, y: r() * 900, w: 260 + r() * 340, h: 170 + r() * 220,
    vx: (r() - 0.5) * 30, vy: -8 - r() * 18 }));
})();
const CONTENT_2D = ['terminal', 'chat', 'replies', 'progress', 'counter', 'loadV2', 'regenSpin', 'bigAccept', 'songMatch', 'diff', 'avg'];
function bg2d(t, shot) {
  show('bg2d');
  const el = $('bg2d');
  el.style.backgroundPosition = `${(t * 24).toFixed(1)}px ${(t * 12).toFixed(1)}px`;
  el.style.filter = `brightness(${(1 + 0.6 * stemAt('kick', t)).toFixed(3)})`;
  if (el.children.length !== WINS.length) el.innerHTML = WINS.map(() => '<div class="win"></div>').join('');
  [...el.children].forEach((d, i) => {
    const w = WINS[i];
    const x = ((w.x + w.vx * t) % 2200 + 2200) % 2200 - 200, y = ((w.y + w.vy * t) % 1300 + 1300) % 1300 - 200;
    Object.assign(d.style, { left: `${x}px`, top: `${y}px`, width: `${w.w}px`, height: `${w.h}px` });
  });
  // The whole 2D canvas keeps pushing in, and the cursor is never quite still.
  const push = 1 + 0.045 * ease((t - shot.start_s) / dur(shot));
  for (const id of CONTENT_2D) { $(id).style.scale = push; $(id).style.transformOrigin = '50% 45%'; }
  const usesCursor = ['big_accept', 'accept_banner', 'cursor_regen_click'].some((n) => shot.layers.includes(n));
  if (!usesCursor) {
    show('cursor');
    const svg = $('cursor').querySelector('svg');
    svg.style.left = `${1500 + 160 * Math.sin(t * 0.9) + 60 * Math.sin(t * 2.3)}px`;
    svg.style.top = `${820 + 90 * Math.sin(t * 0.7 + 1) + 40 * Math.sin(t * 1.9)}px`;
    $('cursor').querySelector('.ripple').style.display = 'none';
  }
}

function songMatch(t, shot) {
  show('songMatch');
  const tl = t - shot.start_s;
  const card = $('songMatch');
  const eq = card.querySelector('.eq');
  if (!eq.children.length) eq.innerHTML = Array.from({ length: 16 }, () => '<div></div>').join('');
  const v = stemAt('vocal', t), k = stemAt('kick', t);
  [...eq.children].forEach((b, i) => { b.style.height = `${10 + 80 * Math.abs(Math.sin(t * 9 + i * 1.7)) * (0.3 + 0.7 * Math.max(v, k))}px`; });
  const found = tl > 0.45;
  card.querySelector('.t').textContent = found ? 'Matches found: 1,402' : 'Listening…';
  card.querySelector('.res').innerHTML = found ? ['Ghost in the Machine – 98.7%', 'The Machine Ghost – 98.1%', 'Ghosts in a Machine – 97.9%']
    .map((x, i) => `<div style="opacity:${clamp01((tl - 0.55 - i * 0.12) / 0.15)}">${x}</div>`).join('') : '';
}

function diffScroll(t, shot) {
  show('diff');
  const tl = t - shot.start_s;
  const n = Math.floor(1048576 * clamp01(tl / (dur(shot) * 0.8)));
  $('diff').querySelector('.hd').innerHTML = `refactor: everything <b>+${n.toLocaleString('en-US')}</b> <i>−0</i>`;
  const body = $('diff').querySelector('.body');
  const r = rng(seed + 30);
  const lines = Array.from({ length: 60 }, () => '+ ' + ['const', 'let', 'await', 'return', 'if', '//'][Math.floor(r() * 6)] + ' '
    + 'x'.repeat(4 + Math.floor(r() * 30)).replace(/x/g, () => 'abcdefgh_(){}=.'[Math.floor(r() * 15)]));
  if (!body.children.length) body.innerHTML = lines.map((x) => `<div>${x}</div>`).join('');
  body.style.transform = `translateY(${-((tl * 2400) % 1200)}px)`;
}

function regenBadge(t, shot) {
  show('regenBadge');
  const f = Math.round(t * fps);
  const segs = shot.plate.segments;
  const i = segs.findIndex(([a, b]) => f >= a && f < b);
  $('regenBadge').querySelector('div').innerHTML = `${ICON.regen('#d9502f')}Regenerating… ${i + 1}/${segs.length}`;
  $('regenBadge').querySelector('svg').style.transform = `rotate(${t * 600}deg)`;
}

function sameStamps(t, shot) {
  const line = LINES.find((x) => x.start >= shot.start_s - 0.5 && x.start < shot.end_s);
  const same = line && line.words.find((w) => norm(w.text) === 'same');
  if (!same || t < same.start) return;
  show('sameStamps');
  const el = $('sameStamps');
  const cells = [...$('replies').querySelectorAll('.r')];
  el.innerHTML = cells.map((c, i) => {
    const since = t - same.start - i * 0.06;
    if (since < 0) return '';
    const x = 120 + (i % 3) * 570 + 300, y = 110 + Math.floor(i / 3) * 140 + 10;
    return `<div class="st" style="left:${x}px;top:${y}px;transform:rotate(-8deg) scale(${(1.6 - 0.6 * ease(since / 0.08)).toFixed(3)})">SAME</div>`;
  }).join('');
}

function terminalBoot(t, shot) {
  const tl = t - shot.start_s;
  const cmd = 'render(song, { seed: 41 })';
  const typed = cmd.slice(0, Math.floor(clamp01(tl / 0.9) * cmd.length));
  const caret = Math.floor(t * 3) % 2 ? '▌' : '';
  show('terminal');
  $('terminal').querySelector('.card').innerHTML = `<div><span class="p">$</span> ${typed}${tl < 1.1 ? caret : ''}</div>` +
    (tl > 1.15 ? '<div class="ok">✓ 1 robot · 4 screens · 1 grid</div>' : '');
}

function hearts(t, shot) {
  show('hearts');
  const el = $('hearts');
  const pops = BEATS.filter((b) => b >= shot.start_s && b <= t && t - b < 0.7);
  el.querySelectorAll('.h').forEach((h) => h.remove());
  for (const b of pops) {
    const r = rng(seed + Math.round(b * 100));
    const k = (t - b) / 0.7;
    const h = document.createElement('div');
    h.className = 'h';
    h.textContent = '♥ +1';
    Object.assign(h.style, { left: `${700 + r() * 900}px`, top: `${620 - r() * 300 - k * 160}px`, opacity: 1 - k,
      transform: `scale(${0.8 + 0.4 * easeOut(k * 3)})` });
    el.appendChild(h);
  }
  el.querySelector('.count').textContent = `♥ ${(1402880 + beatsSince(t, shot.start_s) * 137).toLocaleString('en-US')}`;
}

function chatAutocomplete(t, shot) {
  show('chat');
  const tl = t - shot.start_s;
  const me = $('chat').querySelector('.me');
  const widths = [90, 160, 120, 210, 70, 140];
  me.innerHTML = widths.map((w) => `<span class="redact" style="width:${w}px"></span>`).join('');
  me.style.opacity = clamp01(tl / 0.2);
  // The machine "tells us what to say": the reply types each word half a beat before it is sung.
  const words = D.timing.words.filter((w) => w.section === 'Verse 1' && w.line === 1);
  const from = words.findIndex((w) => w.text === 'now');
  const lead = 0.24;
  const shown = words.slice(from).filter((w) => t >= w.start - lead).map((w) => w.text);
  $('chat').querySelector('.ai').innerHTML = shown.length ? shown.join(' ') : '<span class="dots">● ● ●</span>';
}

function acceptBanner(t, shot) {
  const tl = t - shot.start_s;
  const tc = T_AGREED - shot.start_s;
  const inK = ease((tl - 0.05) / 0.35);
  const outK = ease((tl - tc - 0.25) / 0.3);
  show('banner');
  $('banner').querySelector('.card').style.transform = `translateY(${-(1 - inK) * 420 - outK * 420}px)`;
  if (tl > tc + 0.6) return;
  cursorTo(tl, tc, [1700, 700], [520, 290], -outK * 420);
}

function bigAccept(t, shot) {
  const tl = t - shot.start_s, tc = T_ACCEPT - shot.start_s;
  show('bigAccept');
  const pressed = tl >= tc && tl < tc + 0.15;
  $('bigAccept').querySelector('.btn').style.transform = `scale(${pressed ? 0.94 : 1 + 0.03 * pulse(t, BEATS)})`;
  cursorTo(tl, tc, [1800, 1060], [1400, 860], 0);
}

function cursorTo(tl, tc, [x0, y0], [x1, y1], dy) {
  show('cursor');
  const k = ease((tl - (tc - 0.6)) / 0.55);
  const svg = $('cursor').querySelector('svg');
  svg.style.left = `${x0 + (x1 - x0) * k}px`;
  svg.style.top = `${y0 + (y1 - y0) * k + dy}px`;
  ripple(x1, y1 + dy, tl - tc);
}

function ripple(x, y, since) {
  const r = $('cursor').querySelector('.ripple');
  if (since < 0 || since > 0.3) { r.style.display = 'none'; return; }
  const size = 20 + since * 260;
  Object.assign(r.style, { display: 'block', left: `${x - size / 2}px`, top: `${y - size / 2}px`,
    width: `${size}px`, height: `${size}px`, opacity: 1 - since / 0.3 });
}

function todoCaption(t, shot) {
  const tl = t - shot.start_s;
  if (tl >= dur(shot) * 0.5 && tl < dur(shot) * 0.5 + 0.6 && Math.floor(tl * fps) % 4 !== 3) show('todo');
}

const LOG = [
  [() => SHOT.S35.start_s + 0.5, 'warn', '⚠ Warning: duplicate section "Bridge"'],
  [() => SHOT.S35.start_s + 2.0, 'warn', '⚠ Warning: emotion is undefined'],
  [() => SHOT.S36.start_s + 0.3, 'cmd', '> bridge.render({ again: true })'],
  [() => SHOT.S37.start_s + 0.2, '', '  Generating… 2 of 2'],
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
    w = 640 + 1280 * ease((t - shot.start_s) / (DROP2.start - shot.start_s));
  } else {
    x = 640 * (1 - ease((t - SHOT.S35.start_s) / 0.35));
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

function avgMerge(t, shot) {
  const tl = t - shot.start_s;
  const k = ease((tl - 0.3) / 1.4);
  const icons = [...$('icons').children];
  icons.forEach((el, i) => {
    const x0 = 170 + i * 330, x1 = 850;
    Object.assign(el.style, { left: `${x0 + (x1 - x0) * k}px`, top: '40px', transform: `scale(${1 - 0.6 * k})`,
      opacity: 1 - clamp01((tl - 1.5) / 0.3) });
  });
  show('icons');
  const g = ease((tl - 1.6) / 0.4);
  if (g > 0) {
    show('avg');
    const d = 140 * g;
    Object.assign($('avg').querySelector('.dot').style, { left: `${960 - d / 2}px`, top: `${150 - d / 2}px`, width: `${d}px`, height: `${d}px` });
    Object.assign($('avg').querySelector('.lbl').style, { left: '1060px', top: '120px', opacity: g });
  }
}

function progress(t, shot, which) {
  const tl = t - shot.start_s, d = dur(shot);
  const card = $('progress').querySelector('.card');
  let fill, k = 1;
  if (which === 1) {
    const out = Math.min(3.0, d - 0.35);
    if (tl > out + 0.3) return;
    fill = 50 * ease((tl - 0.3) / Math.min(2.0, out - 0.4));
    k = 1 - ease((tl - out) / 0.3);
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

function giantCounter(t, shot) {
  show('counter');
  const tl = t - shot.start_s;
  // S40 picks up ten times higher than S18 left off: the numbers only climb.
  const start = shot.id === 'S40' ? 9.4e10 * Math.pow(3.2, dur(SHOT.S18)) : 9.4e9;
  const v = Math.floor(start * Math.pow(3.2, tl));
  $('counter').querySelector('.n').textContent = v.toLocaleString('en-US');
  $('counter').querySelector('.l').style.top = '250px';
}

function loadingTextures(t) {
  show('loadingTex');
  $('loadingTex').querySelector('div').textContent = `Loading textures… ${Math.floor(t * 4) % 2 ? '99' : '99'}%${Math.floor(t * 3) % 2 ? ' ▌' : ''}`;
}

function nineReplies(t, shot) {
  show('replies');
  const el = $('replies');
  const tl = t - shot.start_s;
  [...el.querySelector('.g').children].forEach((r, i) => { r.style.opacity = clamp01((tl - i * 0.08) / 0.15); });
  el.style.filter = shot.degrade ? `blur(${1.5 * shot.degrade}px) saturate(1.6) hue-rotate(-14deg) contrast(1.25)` : 'none';
}

const codeCtx = $('code').getContext('2d');
const CODE_TOKENS = ['0x3f', '{}', '=>', 'the', 'null', '[]', 'fn', '0', '1', '&&', 'avg', '//', 'await', 'ok', '::'];
const CODE_COLS = (() => {
  const r = rng(seed + 7);
  return Array.from({ length: 34 }, (_, i) => ({ x: 30 + i * 56 + r() * 20, speed: 160 + r() * 380, phase: r() * 1400,
    toks: Array.from({ length: 24 }, () => CODE_TOKENS[Math.floor(r() * CODE_TOKENS.length)]) }));
})();
function codeStream(t) {
  show('code');
  const g = codeCtx;
  g.clearRect(0, 0, 1920, 1080);
  g.font = '500 24px "JetBrains Mono"';
  for (const c of CODE_COLS) {
    const head = (c.phase + c.speed * t) % 1600;
    c.toks.forEach((tok, j) => {
      const y = head - j * 34;
      if (y < -40 || y > 1120) return;
      g.globalAlpha = j === 0 ? 0.9 : Math.max(0, 0.5 - j * 0.03);
      g.fillStyle = j === 0 ? '#e6e4dc' : '#396ad3';
      g.fillText(tok, c.x, y);
    });
  }
  g.globalAlpha = 1;
}

function loadingVerse2(t, shot) {
  show('loadV2');
  const tl = t - shot.start_s;
  $('loadV2').querySelector('.fill').style.width = `${Math.min(92, 20 + tl * 18)}%`;
  // The ETA counts the wrong way.
  const eta = 3 + Math.floor(tl * 2.5);
  $('loadV2').querySelector('.eta').textContent = `ETA 0:${String(eta).padStart(2, '0')}`;
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
  return Array.from({ length: Math.round(220 * density) }, () => {
    const depth = r();
    return { x: r() * 1920, phase: r() * 1280, speed: 120 + depth * 520, size: 14 + depth * 46,
             alpha: (0.12 + depth * 0.6) / Math.sqrt(density), accent: r() < 0.04 };
  }).sort((a, b) => a.size - b.size);
}
const DROPS = { 1: makeDrops(1), 2.5: makeDrops(2.5) };
function rain(t, t0, density) {
  show('rain');
  rainCtx.clearRect(0, 0, 1920, 1080);
  const fadeIn = clamp01((t - t0) / 0.3);
  for (const d of DROPS[density]) {
    const y = ((d.phase + d.speed * (t - t0 + 2)) % 1280) - 100;
    rainCtx.globalAlpha = d.alpha * fadeIn;
    rainCtx.fillStyle = d.accent ? ACCENT : PAPER;
    rainCtx.font = `800 ${d.size}px Inter`;
    rainCtx.fillText('the', d.x, y);
  }
}

// ---------- S50-S55: the feed of near-identical thumbnails ----------
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
const TILE_W = 280, TILE_H = 157.5, GAP = 30, COLS = 6, X0 = 45, Y0 = 70, ROW_H = 230, LIVE_EVERY = 7;
const isLive = (row, col) => col === 3 && ((row % LIVE_EVERY) + LIVE_EVERY) % LIVE_EVERY === 1;
const DARK_ORDER = (() => {
  const r = rng(seed + 51);
  const idx = Array.from({ length: 24 }, (_, i) => i).filter((i) => i !== 9);
  for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  return idx;
})();
// Scroll offset (px): constant in S52, accelerating in S53, eased to a stop on a live tile in S54.
const V0 = 250, V1 = 2600;
const [t52, t53, t54, t55] = ['S52', 'S53', 'S54', 'S55'].map((id) => SHOT[id].start_s);
const O53 = V0 * (t53 - t52);
const O54 = O53 + V0 * (t54 - t53) + (V1 - V0) * (t54 - t53) / 2;
const O_FINAL = (() => {
  const want = O54 + V1 * (t55 - t54) / 2;
  let k = Math.round((want - Y0 - ROW_H - TILE_H / 2 + 540) / (ROW_H * LIVE_EVERY));
  return Y0 + (1 + LIVE_EVERY * k) * ROW_H + TILE_H / 2 - 540;
})();
function scrollOffset(t) {
  if (t < t52) return 0;
  if (t < t53) return V0 * (t - t52);
  if (t < t54) { const u = t - t53; return O53 + V0 * u + (V1 - V0) * u * u / (2 * (t54 - t53)); }
  if (t < t55) return O54 + (O_FINAL - O54) * easeOut((t - t54) / (t55 - t54));
  return O_FINAL;
}
const scrollSpeed = (t) => (t >= t53 && t < t54 ? V0 + (V1 - V0) * (t - t53) / (t54 - t53) : t >= t54 && t < t55 ? V1 * (1 - (t - t54) / (t55 - t54)) : V0);

async function feed(t, shot, mode) {
  show('grid');
  const s50 = SHOT.S50;
  const g = gridCtx;
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.fillStyle = '#09080b';
  g.fillRect(0, 0, 1920, 1080);
  const liveFrame = Math.min(Math.round(t * fps), SHOT.S55.end_frame - 1);
  const pad = (n) => String(n).padStart(5, '0');
  const dancing = t >= SHOT.S52.start_s;  // from S52 every tile, this video's included, is the robot dancing in sync
  const frameOf = async (dir) => (await load(`${PLATES}/${dir}/${pad(liveFrame)}.png`)) ?? (await load(`${PLATES}/${dir}/${pad(liveFrame - 1)}.png`));
  const live = await frameOf(dancing ? 'chorus-orbit-dance__main' : 'chorus-orbit__main');
  let S = 1, tx = 0, ty = 0;
  if (mode === 'zoom') {
    const z = ease((t - s50.start_s) / (dur(s50) * 0.45));
    const S0 = 1920 / TILE_W;
    S = S0 + (1 - S0) * z;
    const liveX = X0 + 3 * (TILE_W + GAP), liveY = Y0 + ROW_H;
    tx = -liveX * S0 * (1 - z); ty = -liveY * S0 * (1 - z);
  }
  g.setTransform(S, 0, 0, S, tx, ty);
  const off = ['scroll', 'decel', 'hold'].includes(mode) ? scrollOffset(t) : 0;
  const speed = ['scroll', 'decel'].includes(mode) ? scrollSpeed(t) : 0;
  const nDark = mode === 'dark' ? beatsSince(t, shot.start_s) * 4 : 0;
  const r0 = Math.floor((off - Y0) / ROW_H) - 1;
  for (let row = r0; row < r0 + 7; row++) {
    for (let col = 0; col < COLS; col++) {
      const x = X0 + col * (TILE_W + GAP), y = Y0 + row * ROW_H - off;
      if (y > 1100 || y < -ROW_H) continue;
      const idx = ((row * COLS + col) % 23 + 23) % 23;
      const liveHere = isLive(row, col);
      const img = liveHere ? live : dancing ? await frameOf(`chorus-orbit-dance__thumbnail_tiles.${idx}`)
        : await load(`${PLATES}/tiles/tile_${D.seeds.thumbnail_tiles[idx]}.png`);
      const dark = mode === 'dark' && row >= 0 && row < 4 && DARK_ORDER.indexOf(row * COLS + col) > -1
        && DARK_ORDER.indexOf(row * COLS + col) < nDark;
      const copies = speed > 1200 ? 4 : 1;
      for (let c = 0; c < copies; c++) {
        g.globalAlpha = copies > 1 ? 0.35 : 1;
        const dy = c * speed / fps / copies;
        if (dark) { g.fillStyle = '#000'; g.fillRect(x, y, TILE_W, TILE_H); }
        else if (img) g.drawImage(img, x, y + dy, TILE_W, TILE_H);
        else { g.fillStyle = '#1d1d24'; g.fillRect(x, y + dy, TILE_W, TILE_H); }
      }
      g.globalAlpha = 1;
      if (dark) {
        g.fillStyle = '#847d77'; g.font = '400 14px JetBrains Mono';
        g.fillText('Video unavailable', x + 70, y + TILE_H / 2 + 5);
      }
      g.fillStyle = '#e6e4dc';
      g.font = '600 15px Inter';
      const title = liveHere ? `Ghost in the Machine – Claude Opus 5.5 music video ${version(t)}` : TITLES[idx % TITLES.length];
      g.fillText(title.length > 40 ? title.slice(0, 39) + '…' : title, x, y + TILE_H + 24);
      g.fillStyle = '#847d77';
      g.font = '400 12px JetBrains Mono';
      g.fillText(`AI Music · ${(1 + (((idx + 30) * 37) % 90) / 10).toFixed(1)}M views`, x, y + TILE_H + 44);
    }
  }
  g.setTransform(1, 0, 0, 1, 0, 0);
  if (mode === 'hold') { g.fillStyle = 'rgba(9,8,11,.55)'; g.fillRect(0, 0, 1920, 1080); }
}

function cursorRegenClick(t, shot) {
  const tl = t - shot.start_s, tc = T_MACHINE - shot.start_s;
  show('bigRegen');
  const pressed = tl >= tc && tl < tc + 0.15;
  const b = $('bigRegen').querySelector('.b');
  b.style.transform = `scale(${pressed ? 0.94 : 1})`;
  b.style.background = pressed ? 'var(--accent)' : tl > tc - 0.8 ? '#2a2a34' : 'var(--surface)';
  show('cursor');
  const k = ease(tl / Math.max(0.3, tc - 0.1));
  const svg = $('cursor').querySelector('svg');
  svg.style.left = `${1500 + (940 - 1500) * k}px`;
  svg.style.top = `${1060 + (560 - 1060) * k}px`;
  ripple(940, 560, tl - tc);
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
    ['', 'Seeds: 41–56'],
    ['', `Human interventions: ${D.meta.humanInterventions}`],
    ['mono', 'Full production log: [repo link and torrent magnet, added at publish]'],
  ];
  $('endcard').querySelector('.lines').innerHTML = lines.map(([c, s], i) =>
    `<div class="${c}" style="opacity:${clamp01((tl - 0.4 - i * 0.8) / 0.3)}">${s}</div>`).join('');
}

// ---------- frame ----------
window.renderFrame = async (t) => {
  for (const el of stage.children) el.classList.remove('on');
  for (const id of CONTENT_2D) $(id).style.scale = 1;
  const shot = shotAt(t);
  const L = new Set(shot.layers);
  const on = (name, fn) => { if (L.has(name)) return fn(); };
  on('bg2d', () => bg2d(t, shot));
  for (const m of ['zoom', 'dark', 'scroll', 'decel', 'hold']) {
    const name = { zoom: 'grid_zoom', dark: 'grid_dark', scroll: 'grid_scroll', decel: 'grid_decel', hold: 'grid_hold' }[m];
    if (L.has(name)) await feed(t, shot, m);
  }
  if (L.has('grid_scroll_fast')) await feed(t, shot, 'scroll');
  on('code_stream', () => codeStream(t));
  on('the_rain', () => rain(t, shot.start_s, 1));
  on('the_rain_heavy', () => rain(t, shot.start_s, 2.5));
  on('black_stop', () => show('blackStop'));
  on('terminal_boot', () => terminalBoot(t, shot));
  on('song_match', () => songMatch(t, shot));
  on('diff_scroll', () => diffScroll(t, shot));
  on('regen_badge', () => regenBadge(t, shot));
  on('same_stamps', () => sameStamps(t, shot));
  on('hearts', () => hearts(t, shot));
  on('chat_autocomplete', () => chatAutocomplete(t, shot));
  on('nine_replies', () => nineReplies(t, shot));
  on('icon_strip_fast', () => iconStrip(t, shot, false));
  on('icon_strip_slow', () => iconStrip(t, shot, true));
  on('avg_merge', () => avgMerge(t, shot));
  on('progress_1of2', () => progress(t, shot, 1));
  on('progress_2of2', () => progress(t, shot, 2));
  on('giant_counter', () => giantCounter(t, shot));
  on('loading_verse2', () => loadingVerse2(t, shot));
  on('check_stamp', () => checkStamp(t));
  on('regen_spin', () => regenSpin(t, shot));
  on('regen_button', () => regenButton(t));
  on('score_counter', () => scoreCounter(t, shot));
  on('accept_banner', () => acceptBanner(t, shot));
  on('big_accept', () => bigAccept(t, shot));
  on('todo_caption', () => todoCaption(t, shot));
  on('loading_textures', () => loadingTextures(t));
  on('glitch_flicker', () => devtools(t, shot, 'flicker'));
  on('devtools', () => devtools(t, shot, 'side'));
  on('devtools_full', () => devtools(t, shot, 'full'));
  on('output_truncated', () => show('truncated'));
  on('cursor_regen_click', () => cursorRegenClick(t, shot));
  if (shot.global_layers.includes('captions')) captions(t, shot);
  if (shot.global_layers.includes('chrome')) chrome(t, shot);
  on('reload', () => reload(t, shot));
  on('end_card', () => endCard(t, shot));
  if (q.get('hud')) {  // review aid for the animatic only: shot ID and timecode
    show('hud');
    $('hud').textContent = `${shot.id}  ${t.toFixed(2)}s  f${Math.round(t * fps)}`;
  }
};
window.ready = Promise.all([document.fonts.load('800 40px Inter'), document.fonts.load('italic 40px "Instrument Serif"'),
  document.fonts.load('400 20px "JetBrains Mono"')]);
