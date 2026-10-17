"""Seeded randomness for Blender scripts. Never call random.random() or bpy noise without a seed from here."""
import json
import random
from pathlib import Path

SEEDS = json.loads((Path(__file__).resolve().parents[3] / "config" / "seeds.json").read_text())


def seed(name):
    return SEEDS[name]


def rng(name):
    return random.Random(SEEDS[name])
