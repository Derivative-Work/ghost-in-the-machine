#!/usr/bin/env bash
# Pull reference stills from one inspiration video: one per scene change (scene score > 0.3) and one every 5 s.
# Usage: scripts/extract_stills.sh <video> <slug>   -> reference/stills/<slug>/{scene,every5s}/*.jpg + scene_times.txt
set -euo pipefail
in=$1; slug=$2
out="reference/stills/$slug"
mkdir -p "$out/scene" "$out/every5s"
ffmpeg -hide_banner -nostdin -loglevel info -i "$in" -an \
  -vf "scale=1280:-2,select='gt(scene,0.3)',showinfo" -fps_mode vfr -q:v 3 "$out/scene/%04d.jpg" 2> "$out/scene.log"
grep -o 'pts_time:[0-9.]*' "$out/scene.log" | cut -d: -f2 > "$out/scene_times.txt"
ffmpeg -hide_banner -nostdin -loglevel error -i "$in" -an -vf "fps=1/5,scale=1280:-2" -q:v 3 "$out/every5s/%04d.jpg"
echo "$slug: $(ls "$out/scene" | wc -l) scene stills, $(ls "$out/every5s" | wc -l) interval stills"
