// Seeded randomness for overlays. Math.random is never used: every frame must be a pure function of (t, seed).
// The seed arrives as ?seed=<n> from scripts/render_frames.mjs, which resolves names in config/seeds.json.

// mulberry32: small, fast, deterministic 32-bit PRNG.
export function rng(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function params() {
  const q = new URLSearchParams(location.search);
  return {
    seed: Number(q.get('seed') ?? 41),
    fps: Number(q.get('fps') ?? 30),
    width: Number(q.get('w') ?? 1920),
    height: Number(q.get('h') ?? 1080),
  };
}
