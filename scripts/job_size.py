"""Print '<width> <height> <samples>' for a render job under a profile in config/render_profiles.json.

Usage: .venv/bin/python scripts/job_size.py <profile> <job_index|tiles>
"""
import json
import sys
from pathlib import Path

profile = json.loads(Path("config/render_profiles.json").read_text())[sys.argv[1]]
if sys.argv[2] == "tiles":
    size = profile["tiles"]
else:
    job = json.loads(Path("shots/shots.json").read_text())["render_jobs"][int(sys.argv[2])]
    size = profile["default"]
    for r in profile["rules"]:
        if (r.get("shot", job["shot"]) == job["shot"] and r.get("seed", job["seed"]) == job["seed"]
                and job["seed"].startswith(r.get("seed_prefix", ""))):
            size = r["size"]
            break
print(*size)
