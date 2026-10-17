"""Step 4 reproducibility check: a seeded scatter of cubes on the grid floor, rendered small.
Usage: blender -b --factory-startup --python scenes/blender/seed_test.py -- <seed_name> <out.png>
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from gitm_render import strip_metadata  # noqa: E402
from gitm_seeds import rng  # noqa: E402

seed_name, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 16
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1920, 1080, 25
scene.render.filepath = out
strip_metadata(scene)
r = rng(seed_name)
for i in range(60):
    bpy.ops.mesh.primitive_cube_add(size=0.3 + r.random() * 0.5, location=(r.uniform(-6, 6), r.uniform(0, 12), r.uniform(0, 3)),
                                    rotation=(r.random() * 3, r.random() * 3, r.random() * 3))
light = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
scene.collection.objects.link(light)
light.rotation_euler = (0.8, 0.2, 0.4)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
cam.location, cam.rotation_euler = (0, -8, 2), (1.45, 0, 0)
scene.camera = cam
bpy.ops.render.render(write_still=True)
