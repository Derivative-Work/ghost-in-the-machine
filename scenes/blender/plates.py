"""Render Blender plates for the shot list. Each plate builds its scene once and returns update(t), which sets
every animated value from the global time t alone (step 4: frames are pure functions of (t, seed)).

Usage:
  blender -b --factory-startup --python scenes/blender/plates.py -- job <job_index> <out_root> <width> <height> <samples> <step>
  blender -b --factory-startup --python scenes/blender/plates.py -- tiles <out_dir> <width> <height> <samples> <t>

Jobs come from shots/shots.json ("render_jobs"). Frames are written as <out_root>/<plate>__<seed>/<frame:05d>.png
with global frame numbers; with step > 1 only every step-th frame of a job is rendered (animatic).
"""
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import gitm_scene as G  # noqa: E402
from gitm_render import strip_metadata  # noqa: E402
from gitm_seeds import SEEDS  # noqa: E402

ROOT = G.ROOT
SHOTS = json.loads((ROOT / "shots" / "shots.json").read_text())
FPS = SHOTS["fps"]
PANELS = ROOT / "renders" / "animatic" / "panels"
SHOT = {s["id"]: s for s in SHOTS["shots"]}


def seed_value(name):
    return SEEDS[name] if isinstance(name, str) else name


def rng_for(seed):
    import random
    return random.Random(seed)


# ---------- shared set: character on the grid among floating screens ----------

def robot_set(seed, char_at=(1.4, 0, 0), screens=4):
    r = rng_for(seed)
    G.void_world(bpy.context.scene)
    G.grid_floor()
    rig = G.build_character(char_at, height_scale=1.0 + (r.random() - 0.5) * 0.04)
    names = ["consent", "counter", "chat", "terminal"]
    slots = [(-1.6, 3.2, 2.6, 14), (5.2, 4.6, 2.4, -24), (-4.2, 6.5, 1.6, 26), (2.4, 8.0, 3.6, -8)]
    objs = []
    for i in range(screens):
        x, y, z, rz = slots[i]
        x += (r.random() - 0.5) * 0.6
        z += (r.random() - 0.5) * 0.4
        m = G.mat_image_screen(f"scr_{i}", PANELS / f"panel_{names[i % 4]}.png", 1.5)
        objs.append((G.plane(f"screen_{i}", (2.2, 1.283), (x, y, z), (math.radians(90), 0, math.radians(rz)), m),
                     z, r.random()))
    key, rim = G.standard_lights(target=(char_at[0], 0, 1.2))
    cam = G.camera(35)
    G.bloom(bpy.context.scene)
    return rig, objs, cam, (key, rim)


def float_screens(objs, t):
    for ob, z0, ph in objs:
        ob.location.z = z0 + G.bob(t, 0.08, 2.0, ph)


def idle(rig, t):
    rig["root"].location.z = rig["rest"]["root"].z + G.bob(t, 0.02, 1.0)
    rig["head"].rotation_euler.y = 0.04 * math.sin(2 * math.pi * t / (G.BAR * 2))


def cam_path(cam, t, t0, t1, a, b, target_a, target_b):
    x = G.ease((t - t0) / max(1e-6, t1 - t0))
    cam.location = [a[i] + (b[i] - a[i]) * x for i in range(3)]
    G.look_at(cam, [target_a[i] + (target_b[i] - target_a[i]) * x for i in range(3)])


# ---------- plates ----------

def plate_default_cube_boot(job, seed):
    """S01/S22: Blender's untouched default scene, then the neon world boots on the first downbeat."""
    scene = bpy.context.scene
    boot = G.DOWNBEATS[0]
    # The default scene: grey cube, point light, camera, grey world.
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    cube = bpy.context.object
    cube.data.materials.append(G.mat_principled("default_grey", "#cccccc", 0.5))
    pl = bpy.data.lights.new("Light", "POINT")
    pl.energy = 1000
    plo = bpy.data.objects.new("Light", pl)
    plo.location = (4.08, 1.0, 5.9)
    scene.collection.objects.link(plo)
    rig, objs, cam, lights = robot_set(seed, char_at=(1.4, 0, 0))
    floor = bpy.data.objects["floor"]
    world_bg = scene.world.node_tree.nodes["Background"]
    neon = [floor, *[o for o, _, _ in objs], *lights]
    char_objs = [o for o in bpy.data.objects if o.parent is not None or o.name == "char_root"]
    default_cam = ((7.36, -6.93, 4.96), (0, 0, 1))
    s02_cam = ((-0.6, -6.6, 0.8), (0.9, 0.5, 1.45))
    shot_end = SHOT["S01"]["end_s"]

    def update(t):
        booted = t >= boot
        cube.hide_render = booted and t >= boot + 0.25
        if booted:
            k = G.ease((t - boot) / 0.25)
            cube.scale = (1 - k,) * 3
        else:
            cube.scale = (1, 1, 1)
        plo.hide_render = booted
        world_bg.inputs["Color"].default_value = G.lin(G.PAL["base"]) if booted else G.lin("#3d3d3d")
        for i, o in enumerate(neon):
            # Screens and lights switch on one beat apart after the boot.
            on_at = boot + (0 if o is floor else G.BAR / 4 * (1 + i % 4))
            o.hide_render = t < on_at
        grid = floor.active_material.node_tree.nodes["grid_amount"]
        grid.inputs[1].default_value = 0.4 * G.ease((t - boot) / G.BAR)
        for o in char_objs:
            o.hide_render = t < boot + 0.15
        rig["root"].scale = (G.ease((t - boot - 0.15) / 0.4),) * 3 if booted else (0.001,) * 3
        idle(rig, t)
        float_screens(objs, t)
        if booted:
            cam_path(cam, t, boot, shot_end, default_cam[0], s02_cam[0], default_cam[1], s02_cam[1])
        else:
            cam.location = default_cam[0]
            G.look_at(cam, default_cam[1])
    return update


def plate_robot_screens(job, seed):
    """S02/S05: medium shot on the robot among the screens, slow push-in across the shot."""
    rig, objs, cam, _ = robot_set(seed)
    s = SHOT[job["shot"]]

    def update(t):
        idle(rig, t)
        float_screens(objs, t)
        cam_path(cam, t, s["start_s"], s["end_s"], (-0.6, -6.6, 0.8), (-0.35, -5.4, 0.9),
                 (0.9, 0.5, 1.45), (1.1, 0.4, 1.4))
    return update


def plate_robot_shrug(job, seed):
    """S04: the robot shrugs (arms out, head tilt) and holds it."""
    rig, objs, cam, _ = robot_set(seed)
    s = SHOT[job["shot"]]
    cam.location = (0.2, -4.4, 1.2)
    G.look_at(cam, (1.4, 0, 1.3))

    def update(t):
        tl = t - s["start_s"]
        idle(rig, t)
        float_screens(objs, t)
        k = G.ease((tl - 0.9) / 0.35) - G.ease((tl - 3.0) / 0.4)
        for side, sh in rig["shoulders"].items():
            sh.rotation_euler.y = -side * 0.9 * k
        rig["head"].rotation_euler.y = 0.18 * k
    return update


def plate_server_racks(job, seed):
    """S08/S17: an aisle of server racks with LEDs pulsing on the beat; a line chart climbs into the sky."""
    scene = bpy.context.scene
    r = rng_for(seed)
    G.void_world(scene, haze=0.006)
    G.grid_floor()
    rack = G.mat_principled("rack", G.PAL["surface"], 0.4)
    leds = [G.mat_emission(f"led_{i}", G.PAL["accent"] if i % 3 else G.PAL["accent2"], 4) for i in range(6)]
    for side in (-1, 1):
        for i in range(10):
            y = 2 + i * 1.6
            G.rounded_box(f"rack_{side}_{i}", (0.9, 1.2, 2.4), (side * 1.6, y, 1.2), rack, 0.03)
            for j in range(5):
                m = leds[r.randrange(6)]
                G.rounded_box(f"led_{side}_{i}_{j}", (0.02, 0.9, 0.04), (side * 1.13, y, 0.5 + j * 0.42), m, 0.01)
    # Line chart: a rising polyline above the far end of the aisle, revealed left to right.
    curve = bpy.data.curves.new("chart", "CURVE")
    curve.dimensions = "3D"
    sp = curve.splines.new("POLY")
    pts = [(-4 + i * 0.8, 20, 3 + (i ** 1.35) * 0.35 + r.random() * 0.3) for i in range(11)]
    sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x, y, z, 1)
    curve.bevel_depth = 0.05
    chart = bpy.data.objects.new("chart", curve)
    scene.collection.objects.link(chart)
    chart.data.materials.append(G.mat_emission("chart_mat", G.PAL["accent"], 8))
    G.area_light("aisle_key", "#b8c4ff", 500, 6, (0, 4, 6), (0, 10, 0))
    cam = G.camera(28)
    G.bloom(scene)
    t0, t1 = job["start"] / FPS, job["end"] / FPS

    def update(t):
        for i, m in enumerate(leds):
            G.emission_node(m).inputs["Strength"].default_value = 1.0 + 9.0 * G.beat_pulse(t + i * 0.03)
        curve.bevel_factor_end = G.ease((t - t0) / max(1e-6, t1 - t0))
        cam_path(cam, t, t0, t1, (0, -1.5, 1.4), (0, 3.5, 1.7), (0, 12, 2.2), (0, 14, 3.6))
    return update


def chorus_set(seed):
    scene = bpy.context.scene
    r = rng_for(seed)
    G.void_world(scene)
    G.grid_floor()
    rig = G.build_character((0, 0, 0), height_scale=1.0 + (r.random() - 0.5) * 0.04)
    names = ["consent", "counter", "chat", "terminal"]
    ring = []
    for i in range(8):
        a = i / 8 * 2 * math.pi + (r.random() - 0.5) * 0.3
        rad = 6.0 + (r.random() - 0.5) * 0.8
        z = 1.6 + (r.random() - 0.5) * 1.2
        m = G.mat_image_screen(f"ring_{i}", PANELS / f"panel_{names[r.randrange(4)]}.png", 1.4)
        # Facing the centre: a backdrop all around the orbit.
        ob = G.plane(f"ring_{i}", (2.0, 1.167), (rad * math.cos(a), rad * math.sin(a), z),
                     (math.radians(90), 0, a - math.pi / 2), m)
        ring.append((ob, z, r.random()))
    cubes = []
    cm = G.mat_emission("token", G.PAL["accent"], 3)
    for i in range(30):
        a, rad = r.random() * 2 * math.pi, 1.5 + r.random() * 5
        z = 0.4 + r.random() * 3.2
        ob = G.rounded_box(f"tok_{i}", (0.12, 0.12, 0.12), (rad * math.cos(a), rad * math.sin(a), z), cm, 0.02)
        cubes.append((ob, z, r.random()))
    # Two soft keys on opposite sides and a weak rim, so no orbit angle is washed in accent.
    G.area_light("key_a", "#b8c4ff", 450, 4, (-4, -4, 5), (0, 0, 1.2))
    G.area_light("key_b", "#b8c4ff", 300, 4, (4, 4, 5), (0, 0, 1.2))
    G.area_light("rim", G.PAL["accent"], 60, 1.0, (0, 0, 4.2), (0, 0, 1.2))
    cam = G.camera(30)
    G.bloom(scene)
    return rig, ring, cubes, cam


def plate_chorus_orbit(job, seed):
    """S09/S18/S19/S20: slow orbit around the robot, every object on the same ease; S19's camera clips through
    the head."""
    rig, ring, cubes, cam = chorus_set(seed)
    s19 = SHOT["S19"]
    clip_t = s19["start_s"] + 5.5  # inside the split, after the slam has landed

    def update(t):
        idle(rig, t)
        float_screens(ring, t)
        float_screens(cubes, t)
        a = -math.pi / 2 + (t / G.BAR) * math.radians(15)
        rad, h = 3.4, 1.5
        target = (0, 0, 1.35)
        if s19["start_s"] <= t < s19["end_s"]:
            # Dolly in through the head and out the back over 2 s, eased.
            k = (t - clip_t) / 2.0
            if 0 <= k <= 1:
                rad = 3.4 * abs(1 - 2 * G.ease(k))
                h = 1.6 + 0.2 * (1 - abs(1 - 2 * k))
                target = (0, 0, 1.8)
            if k > 0.5:
                a += math.pi  # came out the back
        # The robot turns with the camera so it always faces it (front is -Y); the orbit moves the world behind it.
        face = -math.pi / 2 + (t / G.BAR) * math.radians(15)
        rig["root"].rotation_euler.z = face + math.pi / 2
        cam.location = (rad * math.cos(a), rad * math.sin(a), h) if rad > 0.05 else (0.02 * math.cos(a), 0.02 * math.sin(a), 1.8)
        if rad > 0.05:
            G.look_at(cam, target)
        else:
            G.look_at(cam, (math.cos(a) * -1, math.sin(a) * -1, 1.8))
    return update


def plate_theater_seats(job, seed):
    """S12: two rows of empty theater seats facing the grid."""
    scene = bpy.context.scene
    G.void_world(scene)
    G.grid_floor()
    seat = G.mat_principled("seat", G.PAL["surface"], 0.7)
    arm = G.mat_principled("arm", G.PAL["line"], 0.5)
    for row in range(2):
        for i in range(9):
            x, y, z0 = -4 + i * 1.0, -row * 1.4, row * 0.35
            G.rounded_box(f"seat_{row}_{i}", (0.8, 0.7, 0.18), (x, y, z0 + 0.45), seat, 0.06)
            G.rounded_box(f"back_{row}_{i}", (0.8, 0.14, 0.9), (x, y - 0.35, z0 + 0.95), seat, 0.06)
            G.rounded_box(f"arm_{row}_{i}", (0.08, 0.6, 0.5), (x + 0.5, y - 0.05, z0 + 0.5), arm, 0.02)
    G.area_light("stage", G.PAL["accent"], 300, 8, (0, 8, 4), (0, 0, 0.5))
    G.area_light("fill", "#b8c4ff", 120, 4, (-3, -5, 3), (0, 0, 0.6))
    cam = G.camera(30)
    G.bloom(scene)
    s = SHOT[job["shot"]]

    def update(t):
        cam_path(cam, t, s["start_s"], s["end_s"], (-1.2, -5.5, 1.6), (-0.6, -4.2, 1.5), (0, 6, 0.9), (0, 6, 1.0))
    return update


def plate_robot_tear(job, seed):
    """S13: close-up of the screen face; the single tear is a loading spinner sliding down it."""
    scene = bpy.context.scene
    rig, objs, cam, _ = robot_set(seed)
    s = SHOT[job["shot"]]
    hx, hz = 1.4, 1.80
    circ = bpy.data.curves.new("spinner", "CURVE")
    circ.dimensions = "3D"
    sp = circ.splines.new("NURBS")
    n = 12
    sp.points.add(n - 1)
    for i, p in enumerate(sp.points):
        a = i / n * 2 * math.pi
        p.co = (0.022 * math.cos(a), 0, 0.022 * math.sin(a), 1)
    sp.use_cyclic_u = True
    circ.bevel_depth = 0.006
    circ.bevel_factor_end = 0.75
    spinner = bpy.data.objects.new("spinner", circ)
    scene.collection.objects.link(spinner)
    spinner.data.materials.append(G.mat_emission("spin_mat", G.PAL["paper"], 10))
    cam.data.lens = 40

    def update(t):
        tl = t - s["start_s"]
        idle(rig, t)
        float_screens(objs, t)
        spinner.location = (hx + 0.1, -0.245, hz - 0.03 - 0.10 * G.ease((tl - 0.6) / 2.6))
        spinner.rotation_euler = (0, -tl * 2 * math.pi * 1.25, 0)
        spinner.hide_render = tl < 0.4
        cam.location = (hx - 0.35, -1.35, hz + 0.02 + rig["root"].location.z)
        G.look_at(cam, (hx + 0.05, 0, hz - 0.02 + rig["root"].location.z))
    return update


PLATES = {
    "default_cube_boot": plate_default_cube_boot,
    "robot_screens": plate_robot_screens,
    "robot_shrug": plate_robot_shrug,
    "server_racks": plate_server_racks,
    "chorus_orbit": plate_chorus_orbit,
    "theater_seats": plate_theater_seats,
    "robot_tear": plate_robot_tear,
}


def render_job(index, out_root, width, height, samples, step):
    job = SHOTS["render_jobs"][index]
    seed = seed_value(job["seed"])
    scene = G.reset(width, height, samples)
    strip_metadata(scene)
    update = PLATES[job["plate"]](job, seed)
    out = Path(out_root) / f"{job['plate']}__{job['seed']}"
    out.mkdir(parents=True, exist_ok=True)
    for f in range(job["start"], job["end"], step):
        t = f / FPS - job["clock_offset_s"]
        update(t)
        scene.render.filepath = str(out / f"{f:05d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"JOB {index} {job['plate']} {job['seed']} frames {job['start']}-{job['end']} step {step} done")


def render_tiles(out_dir, width, height, samples, t):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for seed in SEEDS["thumbnail_tiles"]:
        scene = G.reset(width, height, samples)
        strip_metadata(scene)
        update = plate_chorus_orbit({"shot": "S20"}, seed)
        update(t)
        scene.render.filepath = str(out / f"tile_{seed}.png")
        bpy.ops.render.render(write_still=True)
    print("TILES done")


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "job":
        render_job(int(args[1]), args[2], int(args[3]), int(args[4]), int(args[5]), int(args[6]))
    elif args[0] == "tiles":
        render_tiles(args[1], int(args[2]), int(args[3]), int(args[4]), float(args[5]))


main()
