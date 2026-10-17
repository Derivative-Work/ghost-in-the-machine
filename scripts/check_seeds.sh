#!/usr/bin/env bash
# Step 4: confirm that re-running a seed reproduces its frames exactly, and that different seeds differ.
# Checks both pipelines: a JS overlay (the "the" rain, frame 90) and a Blender/Eevee scene (seeded scatter).
# Also fails if any scene code uses unseeded randomness.
set -euo pipefail
out=renders/draft/seed_check
rm -rf "$out.tmp"; mkdir -p "$out.tmp"
if grep -rnE 'Math\.random|random\.random\(\)|np\.random\.(rand|random|randn|choice)\(' overlays scenes --include=*.js --include=*.html --include=*.py | grep -v 'never used\|Never call'; then
  echo "FAIL: unseeded randomness above"; exit 1
fi
for run in a b; do node scripts/render_frames.mjs overlays/scenes/the_rain.html "$out.tmp/js_41_$run" 90 91 main 960 540; done
node scripts/render_frames.mjs overlays/scenes/the_rain.html "$out.tmp/js_42" 90 91 bridge_second_run 960 540
for run in a b; do blender -b --factory-startup --python scenes/blender/seed_test.py -- main "$PWD/$out.tmp/bl_41_$run.png" >/dev/null 2>&1; done
blender -b --factory-startup --python scenes/blender/seed_test.py -- bridge_second_run "$PWD/$out.tmp/bl_42.png" >/dev/null 2>&1
h() { sha256sum "$1" | cut -c1-16; }
js41a=$(h "$out.tmp/js_41_a/00090.png"); js41b=$(h "$out.tmp/js_41_b/00090.png"); js42=$(h "$out.tmp/js_42/00090.png")
bl41a=$(h "$out.tmp/bl_41_a.png"); bl41b=$(h "$out.tmp/bl_41_b.png"); bl42=$(h "$out.tmp/bl_42.png")
echo "js  seed41 run a $js41a | run b $js41b | seed42 $js42"
echo "bl  seed41 run a $bl41a | run b $bl41b | seed42 $bl42"
ok=1
[ "$js41a" = "$js41b" ] || { echo "FAIL: JS seed 41 not reproducible"; ok=0; }
[ "$js41a" != "$js42" ] || { echo "FAIL: JS seeds 41 and 42 identical"; ok=0; }
[ "$bl41a" = "$bl41b" ] || { echo "FAIL: Blender seed 41 not reproducible"; ok=0; }
[ "$bl41a" != "$bl42" ] || { echo "FAIL: Blender seeds 41 and 42 identical"; ok=0; }
mkdir -p "$out"; stamp=$(date +%Y%m%dT%H%M%S); mv "$out.tmp" "$out/$stamp"
[ $ok = 1 ] && echo "PASS ($out/$stamp)" || exit 1
