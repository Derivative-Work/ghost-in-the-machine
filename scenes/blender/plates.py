"""Render Blender plates for the shot list. Each plate builds one set, then update(t) sets every animated value from
the global time t alone (step 4: frames are pure functions of (t, seed)). A job picks the set, a named camera and
effects (shots/shots.json "render_jobs").

Usage:
  blender -b --factory-startup --python scenes/blender/plates.py -- job <job_index> <out_root> <width> <height> <samples> <step>
  blender -b --factory-startup --python scenes/blender/plates.py -- tiles <out_dir> <width> <height> <samples> <t>
  blender -b --factory-startup --python scenes/blender/plates.py -- probe <job_index> <out_dir> <width> <height> <samples> <fraction>

Frames are written as <out_root>/<job dir>/<frame:05d>.png with global frame numbers; with step > 1 only every
step-th frame of a job is rendered (animatic).
"""
import json
import math
import random
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
SCREEN_NAMES = ["consent", "counter", "chat", "terminal"]


def seed_value(spec):
    """'main' | 'split_extra.3' | an int."""
    if isinstance(spec, int):
        return spec
    name, _, idx = spec.partition(".")
    return SEEDS[name][int(idx)] if idx else SEEDS[name]


def beats_since(t, t0):
    return sum(1 for b in G.BEATS if t0 <= b <= t)


def cam_path(cam, t, t0, t1, a, b, target_a, target_b):
    x = G.ease((t - t0) / max(1e-6, t1 - t0))
    cam.location = [a[i] + (b[i] - a[i]) * x for i in range(3)]
    G.look_at(cam, [target_a[i] + (target_b[i] - target_a[i]) * x for i in range(3)])


def float_objs(objs, t, amp=0.08):
    for ob, z0, ph in objs:
        ob.location.z = z0 + G.bob(t, amp, 2.0, ph)


def idle(rig, t):
    rig["root"].location.z = rig["rest"]["root"].z + G.bob(t, 0.02, 1.0)
    rig["head"].rotation_euler.y = 0.04 * math.sin(2 * math.pi * t / (G.BAR * 2))


def react(t, lights=(), screens=(), floor=None):
    """v3 music reactions: lights punch on the kick, screens follow the synth, the floor ripples on bass notes."""
    k = G.env("kick", t)
    for ob, base_energy in lights:
        ob.data.energy = base_energy * (1 + 0.6 * k)
    sy = G.env("synth", t)
    for node, base_strength in screens:
        node.inputs["Strength"].default_value = base_strength * (0.75 + 0.6 * sy)
    if floor is not None:
        nodes = floor.active_material.node_tree.nodes
        b = G.last_onset(G.STEMS["bass_on"], t)
        age = t - b if b is not None else 99
        nodes["ripple_r"].outputs[0].default_value = age * 9.0
        nodes["ripple_amp"].outputs[0].default_value = 0.7 * math.exp(-age / 0.6)


def lights_of(names):
    return [(ob, ob.data.energy) for ob in bpy.data.objects if ob.type == "LIGHT" and ob.name.startswith(names)]


def screens_of(objs):
    out = []
    for ob in objs:
        mat = ob.active_material
        node = next((n for n in mat.node_tree.nodes if n.type == "EMISSION"), None) if mat else None
        if node:
            out.append((node, node.inputs["Strength"].default_value))
    return out


def dof(cam, distance, fstop=2.0):
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = fstop
    cam.data.dof.focus_distance = distance


def checker_material():
    """Blender's missing-texture look: a magenta/black checker."""
    m = bpy.data.materials.new("missing_texture")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value = 6.0
    chk.inputs["Color1"].default_value = G.lin("#ff00ff")
    chk.inputs["Color2"].default_value = G.lin("#000000")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.2
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Generated"], chk.inputs["Vector"])
    nt.links.new(chk.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def apply_missing_texture(keep=("eye",)):
    m = checker_material()
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "CURVE") and ob.name != "floor" and not ob.name.startswith(keep):
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = m


# ---------- set: robot on the grid among floating screens (Intro, Verse 1, Bridge 1) ----------

def plate_robot(job, seed):
    r = random.Random(seed)
    scene = bpy.context.scene
    fx = set(job["fx"])
    G.void_world(scene)
    floor = G.grid_floor()
    reroll = "reroll" in fx  # S31: each regeneration visibly re-rolls the layout
    cx = 1.4 + ((r.random() - 0.5) * 1.6 if reroll else 0)
    rig = G.build_character((cx, 0, 0), height_scale=1.0 + (r.random() - 0.5) * (0.25 if reroll else 0.04))
    slots = [(-1.6, 3.2, 2.6, 14), (5.2, 4.6, 2.4, -24), (-4.2, 6.5, 1.6, 26), (2.4, 8.0, 3.6, -8)]
    if reroll:
        r.shuffle(slots)
        slots = [(x + (r.random() - 0.5) * 3, y, z + (r.random() - 0.5) * 1.5, rz + r.randint(-30, 30)) for x, y, z, rz in slots]
    screens = []
    for i, (x, y, z, rz) in enumerate(slots):
        x += (r.random() - 0.5) * 0.6
        z += (r.random() - 0.5) * 0.4
        m = G.mat_image_screen(f"scr_{i}", PANELS / f"panel_{SCREEN_NAMES[i]}.png", 1.5)
        screens.append((G.plane(f"screen_{i}", (2.2, 1.283), (x, y, z), (math.radians(90), 0, math.radians(rz)), m),
                        z, r.random(), m))
    G.standard_lights(target=(cx, 0, 1.2))
    cam = G.camera(35)
    G.bloom(scene)
    s = SHOT[job["shot"]]
    t0, t1 = s["start_s"], s["end_s"]
    eye_nodes = [G.emission_node(e.active_material) for e in rig["eyes"]]
    screen_nodes = [next(n for n in m.node_tree.nodes if n.type == "EMISSION") for *_, m in screens]
    head_z = 1.80
    lights = lights_of(("key", "rim"))
    scr = screens_of([o for o, *_ in screens])
    mobile = None
    if "mobile" in fx:  # S17: a crib mobile of tiny server racks turning above the robot
        mobile = G.empty("mobile", (cx, 0, 2.75))
        rack = G.mat_principled("mini_rack", G.PAL["surface"], 0.4)
        led = G.mat_emission("mini_led", G.PAL["accent"], 6)
        G.capsule("mobile_hook", 0.01, 0.5, (cx, 0, 3.0), G.mat_principled("string", G.PAL["line"]), parent=mobile)
        for i in range(6):
            a = i / 6 * 2 * math.pi
            x, y = cx + 0.55 * math.cos(a), 0.55 * math.sin(a)
            G.capsule(f"string_{i}", 0.004, 0.35, (x, y, 2.6), G.mat_principled(f"str_{i}", G.PAL["line"]), parent=mobile)
            G.rounded_box(f"mini_rack_{i}", (0.12, 0.09, 0.2), (x, y, 2.33), rack, 0.01, parent=mobile)
            G.rounded_box(f"mini_led_{i}", (0.004, 0.07, 0.01), (x - 0.062, y, 2.36), led, 0.002, parent=mobile)
        G.capsule("mobile_arm_a", 0.008, 1.1, (cx, 0, 2.75), G.mat_principled("arm_a", G.PAL["line"]), rot=(0, 1.5708, 0), parent=mobile)
        G.capsule("mobile_arm_b", 0.008, 1.1, (cx, 0, 2.75), G.mat_principled("arm_b", G.PAL["line"]), rot=(1.5708, 0, 0), parent=mobile)

    def update(t):
        tl = t - t0
        idle(rig, t)
        G.perform(rig, t)
        float_objs([(o, z, ph) for o, z, ph, _ in screens], t)
        react(t, lights, scr, floor)
        hz = head_z + rig["root"].location.z
        cam.data.lens = 35
        cam.data.dof.use_dof = False
        if job["cam"] == "wide":
            cam_path(cam, t, t0, t1, (-0.6, -6.6, 0.8), (-0.35, -5.6, 0.9), (0.9, 0.5, 1.45), (1.1, 0.4, 1.4))
            dof(cam, 9.0 + (6.4 - 9.0) * G.ease(tl / 0.8))  # focus pulls from the screens to the robot
        elif job["cam"] == "medium":
            cam_path(cam, t, t0, t1, (0.2, -4.6, 1.2), (0.35, -4.1, 1.25), (cx, 0, 1.3), (cx, 0, 1.35))
            dof(cam, 4.4, 1.8)
        elif job["cam"] == "lullaby":
            cam.data.lens = 28
            cam_path(cam, t, t0, t1, (cx - 1.4, -2.6, 1.1), (cx - 0.6, -2.9, 1.0), (cx, 0, 2.2), (cx, 0, 2.3))
            mobile.rotation_euler.z = t * 0.6
            rig["root"].rotation_euler.y = 0.06 * math.sin(2 * math.pi * t / (G.BAR * 2))  # slow sway
        elif job["cam"] == "low":
            cam.data.lens = 24
            cam_path(cam, t, t0, t1, (0.3, -3.0, 0.3), (0.9, -3.1, 0.35), (cx, 0, 1.7), (cx, 0, 1.7))
        elif job["cam"] == "face":
            cam.data.lens = 40
            cam.location = (cx - 0.35, -1.35, hz + 0.02)
            G.look_at(cam, (cx + 0.05, 0, hz - 0.02))
        elif job["cam"] == "screens":
            cam.data.lens = 24
            cam_path(cam, t, t0, t1, (0.4, -2.2, 1.7), (0.6, -1.6, 1.9), (0.8, 5, 2.5), (1.4, 5, 2.6))
        elif job["cam"] == "screen_close":
            sx, sy, sz = screens[1][0].location
            cam_path(cam, t, t0, t1, (sx - 1.6, sy - 3.0, sz - 0.1), (sx - 1.3, sy - 2.5, sz), (sx, sy, sz), (sx, sy, sz))
        # Effects.
        on = 1.0
        if "screens_power_on" in fx:
            n = beats_since(t, t0)
            for i, node in enumerate(screen_nodes):
                node.inputs["Strength"].default_value = node.inputs["Strength"].default_value if i < n else 0.0
        if "eyes_wake" in fx:
            on = 1.0 if beats_since(t, t0) >= 2 else 0.0
        if "eyes_dim" in fx:
            on = 0.3
        for n in eye_nodes:
            n.inputs["Strength"].default_value = 12.0 * on
        if "shrug" in fx:
            k = G.ease((tl - 0.9) / 0.35) - G.ease((tl - 3.0) / 0.4)
            for side, sh in rig["shoulders"].items():
                sh.rotation_euler.y = -side * 0.9 * k
            rig["head"].rotation_euler.y = 0.18 * k
    return update


# ---------- set: the chorus orbit (Chorus 1, Chorus 2, final chorus) ----------

def plate_chorus(job, seed):
    r = random.Random(seed)
    scene = bpy.context.scene
    G.void_world(scene)
    floor = G.grid_floor()
    rig = G.build_character((0, 0, 0), height_scale=1.0 + (r.random() - 0.5) * 0.04)
    ring = []
    for i in range(8):
        a = i / 8 * 2 * math.pi + (r.random() - 0.5) * 0.3
        rad = 6.0 + (r.random() - 0.5) * 0.8
        z = 1.6 + (r.random() - 0.5) * 1.2
        m = G.mat_image_screen(f"ring_{i}", PANELS / f"panel_{SCREEN_NAMES[r.randrange(4)]}.png", 1.4)
        ob = G.plane(f"ring_{i}", (2.0, 1.167), (rad * math.cos(a), rad * math.sin(a), z),
                     (math.radians(90), 0, a - math.pi / 2), m)
        ring.append((ob, z, r.random()))
    tokens = []
    cm = G.mat_emission("token", G.PAL["accent"], 3)
    for i in range(30):
        a, rad = r.random() * 2 * math.pi, 1.5 + r.random() * 5
        z = 0.4 + r.random() * 3.2
        tokens.append((G.rounded_box(f"tok_{i}", (0.12, 0.12, 0.12), (rad * math.cos(a), rad * math.sin(a), z), cm, 0.02),
                       z, r.random()))
    # Two soft keys on opposite sides and a weak rim, so no orbit angle is washed in accent.
    lights = [G.area_light("key_a", "#b8c4ff", 450, 4, (-4, -4, 5), (0, 0, 1.2)),
              G.area_light("key_b", "#b8c4ff", 300, 4, (4, 4, 5), (0, 0, 1.2)),
              G.area_light("rim", G.PAL["accent"], 60, 1.0, (0, 0, 4.2), (0, 0, 1.2))]
    cam = G.camera(30)
    G.bloom(scene)
    fx = set(job["fx"])
    if "missing_texture" in fx:
        apply_missing_texture()
    s = SHOT[job["shot"]]
    t0, t1 = s["start_s"], s["end_s"]
    grid = floor.active_material.node_tree.nodes["grid_amount"]
    energies = [l.data.energy for l in lights]
    clip_t = t0 + 1.5
    beat_len = 60 / G.TIMING["tempo_bpm"]
    lights_e = list(zip(lights, energies))
    scr = screens_of([o for o, *_ in ring])
    letters = []
    if "tokens_3d" in fx:  # "TOKENS" falls as solid letters around the robot
        font = bpy.data.fonts.load(str(ROOT / "assets" / "fonts" / "Inter[opsz,wght].ttf"), check_existing=True)
        lm = G.mat_emission("letters", G.PAL["paper"], 2.5)
        for i, ch in enumerate("TOKENS"):
            cu = bpy.data.curves.new(f"tok3d_{i}", "FONT")
            cu.body, cu.font, cu.extrude, cu.size, cu.align_x = ch, font, 0.06, 0.6, "CENTER"
            ob = bpy.data.objects.new(f"tok3d_{i}", cu)
            scene.collection.objects.link(ob)
            ob.data.materials.append(lm)
            a = (i - 2.5) * 0.5
            letters.append((ob, (1.6 * math.sin(a), -0.2 + 0.9 * math.cos(a), r.random() * 0.8, r.random())))

    def orbit(t, speed_deg, rad, h, offset=0.0, target=(0, 0, 1.35)):
        a = -math.pi / 2 + (t / G.BAR) * math.radians(speed_deg) + offset
        rig["root"].rotation_euler.z = a + math.pi / 2  # the robot turns to face the camera
        cam.location = (rad * math.cos(a), rad * math.sin(a), h)
        G.look_at(cam, target)
        return a

    def update(t):
        tl = t - t0
        rig["root"].rotation_euler.z = 0.0
        rig["head"].rotation_euler.x = 0.0
        idle(rig, t)
        G.perform(rig, t)
        float_objs(ring, t)
        float_objs(tokens, t)
        react(t, lights_e, scr, floor)
        cam.data.lens = 30
        c = job["cam"]
        if c == "orbit":
            # Chorus entries sweep a fast 180 degrees into the orbit.
            sweep = -math.pi * (1 - G.ease(tl / 1.2)) if "fast_entry" in fx else 0.0
            a = orbit(t, 15, 3.4, 1.5, offset=sweep)
            if "clip" in fx and 0 <= (t - clip_t) <= 2.0:
                # Dolly in through the head and out the back, eased.
                k = (t - clip_t) / 2.0
                rad = max(0.02, 3.4 * abs(1 - 2 * G.ease(k)))
                side = 1 if k <= 0.5 else -1
                cam.location = (side * rad * math.cos(a), side * rad * math.sin(a), 1.8)
                G.look_at(cam, (-side * 3 * math.cos(a), -side * 3 * math.sin(a), 1.8))
        elif c == "orbit2":
            orbit(t, 15, 2.4, 2.1, offset=math.pi / 2, target=(0, 0, 1.5))
        elif c == "dance_wide":
            orbit(t, 40, 4.2, 1.3)
        elif c == "dolly_zoom":
            # Vertigo: dolly in while widening the lens so the robot stays the same size and the world stretches.
            d = 5.0 - 3.1 * G.ease(tl / max(1e-6, t1 - t0))
            cam.data.lens = 47.0 * d / 5.0
            cam.location = (0, -d, 1.55)
            G.look_at(cam, (0, 0, 1.55))
        elif c == "low_up":
            cam.data.lens = 24
            cam.location = (0.5, -1.7, 0.35)
            G.look_at(cam, (0, 0, 2.2))
        elif c == "wide_static":
            cam.data.lens = 28
            cam.location = (0, -7.5, 2.4)
            G.look_at(cam, (0, 0, 1.2))
        elif c == "topdown":
            cam.location = (0, -0.001, 11 - 1.5 * G.ease(tl / max(1e-6, t1 - t0)))
            G.look_at(cam, (0, 0, 0))
        elif c == "dance_low":
            cam.data.lens = 24
            cam.location = (0.8, -2.4, 0.4)
            G.look_at(cam, (0, 0, 1.4))
        if "head_up" in fx:
            rig["head"].rotation_euler.x = 0.35 * G.ease(tl / 0.6)
        for i, (ob, (x, y, z0, ph)) in enumerate(letters):
            # Each letter drops in on its own half beat and settles, spinning.
            k = G.ease((tl - 0.15 * i) / 0.9)
            ob.location = (x, y, 4.2 - (4.2 - (0.9 + z0)) * k)
            ob.rotation_euler = (math.pi / 2, 0, (1 - k) * 4 * math.pi + ph)
            ob.hide_render = tl < 0.15 * i
        if "dance" in fx:
            prior = [b for b in G.BEATS if b <= t]
            n = len(prior)
            ph = (t - prior[-1]) / beat_len if prior else 0.0
            swing = math.sin(math.pi * min(1.0, ph))
            for side, sh in rig["shoulders"].items():
                # Arms pump alternately on each beat.
                sh.rotation_euler.y = -side * (0.3 + 0.9 * swing * (1 if (n + (side > 0)) % 2 else 0.2))
            rig["root"].location.z = rig["rest"]["root"].z + 0.07 * swing
            rig["root"].rotation_euler.z += 0.2 * (1 if (n // 2) % 2 else -1)
        if "lights_fade" in fx:
            n = beats_since(t, t0)
            for ob, *_ in tokens:
                ob.hide_render = n >= 1
            for i, (ob, *_) in enumerate(ring):
                ob.hide_render = n >= 2 + i // 2
            lights[1].data.energy = 0 if n >= 6 else energies[1]
            grid.inputs[1].default_value = 0 if n >= 6 else 0.4
            lights[0].data.energy = 0 if n >= 7 else energies[0]
            lights[2].data.energy = 0 if n >= 8 else energies[2]
    return update


# ---------- set: the server racks (Pre-Chorus 1, Pre-Chorus 2) ----------

def plate_racks(job, seed):
    scene = bpy.context.scene
    r = random.Random(seed)
    G.void_world(scene, haze=0.006)
    G.grid_floor()
    rack = G.mat_principled("rack", G.PAL["surface"], 0.4)
    leds = [G.mat_emission(f"led_{i}", G.PAL["accent"] if i % 3 else G.PAL["accent2"], 4) for i in range(6)]
    for side in (-1, 1):
        for i in range(10):
            y = 2 + i * 1.6
            G.rounded_box(f"rack_{side}_{i}", (0.9, 1.2, 2.4), (side * 1.6, y, 1.2), rack, 0.03)
            for j in range(5):
                G.rounded_box(f"led_{side}_{i}_{j}", (0.02, 0.9, 0.04), (side * 1.13, y, 0.5 + j * 0.42),
                              leds[r.randrange(6)], 0.01)
    curve = bpy.data.curves.new("chart", "CURVE")
    curve.dimensions = "3D"
    sp = curve.splines.new("POLY")
    pts = [(-4 + i * 0.8, 20, 3 + (i ** 1.35) * 0.35 + r.random() * 0.3) for i in range(11)]
    sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x, y, z, 1)
    curve.bevel_depth = 0.08
    chart = bpy.data.objects.new("chart", curve)
    scene.collection.objects.link(chart)
    chart.data.materials.append(G.mat_emission("chart_mat", G.PAL["accent"], 10))
    G.area_light("aisle_key", "#b8c4ff", 500, 6, (0, 4, 6), (0, 10, 0))
    cam = G.camera(28)
    G.bloom(scene)
    s = SHOT[job["shot"]]
    t0, t1 = s["start_s"], s["end_s"]
    floor = bpy.data.objects["floor"]
    lights = lights_of(("aisle",))

    def update(t):
        react(t, lights, (), floor)
        for i, m in enumerate(leds):
            G.emission_node(m).inputs["Strength"].default_value = 1.0 + 9.0 * G.beat_pulse(t + i * 0.03)
        if job["cam"] == "aisle":
            curve.bevel_factor_end = 0.4 * G.ease((t - t0) / max(1e-6, t1 - t0))
            cam_path(cam, t, t0, t1, (0, -1.5, 1.4), (0, 3.5, 1.7), (0, 12, 2.2), (0, 14, 3.0))
        elif job["cam"] == "crane":  # rises out of the aisle as the drums come back
            curve.bevel_factor_end = 0.5 * G.ease((t - t0) / max(1e-6, t1 - t0))
            cam_path(cam, t, t0, t1, (0, -1.0, 0.7), (0, 4.0, 4.6), (0, 14, 2.0), (0, 16, 1.2))
        else:  # chart: tilt up from the aisle to the chart as it climbs
            curve.bevel_factor_end = 0.3 + 0.7 * G.ease((t - t0) / max(1e-6, t1 - t0))
            cam_path(cam, t, t0, t1, (0, 5, 1.4), (0, 6.5, 1.2), (0, 14, 2.0), (0, 20, 5.2))
    return update


# ---------- set: the theater seats (Verse 2) ----------

def plate_seats(job, seed):
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
    rig = None
    if "robot_seated" in job["fx"]:  # S32: the robot alone in the front row, facing the stage
        rig = G.build_character((0, 0, 0))
        rig["root"].location = (0, 0, -0.16)
        rig["root"].rotation_euler.z = math.pi
        for side in (-1, 1):
            leg = bpy.data.objects[f"leg_{side}"]
            leg.rotation_euler.x = math.pi / 2
            leg.location = (side * 0.15, -0.33, 0.66)
    end = G.mat_image_screen("the_end", PANELS / "panel_the_end.png", 1.6)
    G.plane("the_end", (7.2, 4.05), (0, 9, 2.6), (math.radians(90), 0, 0), end)
    G.area_light("stage", G.PAL["accent"], 220, 8, (0, 7, 4), (0, 0, 0.5))
    G.area_light("fill", "#b8c4ff", 260, 5, (-2, 5, 3), (0, 0, 0.6))
    cam = G.camera(30)
    G.bloom(scene)
    s = SHOT[job["shot"]]
    t0, t1 = s["start_s"], s["end_s"]

    floor = bpy.data.objects["floor"]

    def update(t):
        react(t, (), (), floor)
        if rig:
            rig["root"].rotation_euler.z = math.pi
            G.perform(rig, t)
        if job["cam"] == "front":  # the seats face the camera
            cam_path(cam, t, t0, t1, (0.8, 5.0, 1.3), (0.4, 4.2, 1.2), (0, 0, 0.6), (0, 0, 0.7))
        else:  # reverse: from behind the empty seats toward THE END
            cam_path(cam, t, t0, t1, (0, -4.6, 2.3), (0, -4.0, 2.3), (0, 9, 2.5), (0, 9, 2.7))
    return update


# ---------- set: the tear close-up (Verse 2) ----------

def plate_tear(job, seed):
    scene = bpy.context.scene
    update_robot = plate_robot(dict(job, cam="face", fx=[]), seed)
    s = SHOT[job["shot"]]
    hx, hz = 1.4, 1.80
    circ = bpy.data.curves.new("spinner", "CURVE")
    circ.dimensions = "3D"
    sp = circ.splines.new("NURBS")
    sp.points.add(11)
    for i, p in enumerate(sp.points):
        a = i / 12 * 2 * math.pi
        p.co = (0.02 * math.cos(a), 0, 0.02 * math.sin(a), 1)
    sp.use_cyclic_u = True
    circ.bevel_depth = 0.006
    circ.bevel_factor_end = 0.75
    spinner = bpy.data.objects.new("spinner", circ)
    scene.collection.objects.link(spinner)
    spinner.data.materials.append(G.mat_emission("spin_mat", G.PAL["paper"], 10))
    root = bpy.data.objects["char_root"]

    def update(t):
        tl = t - s["start_s"]
        update_robot(t)
        z = root.location.z
        # Starts under one eye and slides down the screen face.
        spinner.location = (hx + 0.1, -0.245, hz - 0.03 + z - 0.09 * G.ease((tl - 0.6) / 2.6))
        spinner.rotation_euler = (0, -tl * 2 * math.pi * 1.25, 0)
        spinner.hide_render = tl < 0.4
    return update


# ---------- set: Blender's default scene, then the boot (Intro, Ending) ----------

def plate_default_cube_boot(job, seed):
    scene = bpy.context.scene
    boot = G.DOWNBEATS[0]
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    cube = bpy.context.object
    cube.name = "default_cube"
    cube.data.materials.append(G.mat_principled("default_grey", "#cccccc", 0.5))
    pl = bpy.data.lights.new("Light", "POINT")
    pl.energy = 1000
    plo = bpy.data.objects.new("Light", pl)
    plo.location = (4.08, 1.0, 5.9)
    scene.collection.objects.link(plo)
    update_robot = plate_robot(dict(job, cam="wide", fx=[]), seed)
    cam = scene.camera
    floor = bpy.data.objects["floor"]
    world_bg = scene.world.node_tree.nodes["Background"]
    neon = [o for o in bpy.data.objects if o.name.startswith(("screen_", "key", "rim"))]
    char_objs = [o for o in bpy.data.objects if o.parent is not None or o.name == "char_root"]
    root = bpy.data.objects["char_root"]
    default_cam = ((7.36, -6.93, 4.96), (0, 0, 1))
    wide = ((-0.6, -6.6, 0.8), (0.9, 0.5, 1.45))

    def update(t):
        update_robot(t)
        booted = t >= boot
        cube.hide_render = booted and t >= boot + 0.25
        cube.scale = ((1 - G.ease((t - boot) / 0.25)),) * 3 if booted else (1, 1, 1)
        plo.hide_render = booted
        floor.hide_render = not booted
        world_bg.inputs["Color"].default_value = G.lin(G.PAL["base"]) if booted else G.lin("#3d3d3d")
        for i, o in enumerate(neon):
            o.hide_render = t < boot + G.BAR / 4 * (1 + i % 4)
        floor.active_material.node_tree.nodes["grid_amount"].inputs[1].default_value = 0.4 * G.ease((t - boot) / G.BAR)
        for o in char_objs:
            o.hide_render = t < boot + 0.15
        root.scale = (G.ease((t - boot - 0.15) / 0.4),) * 3 if booted else (0.001,) * 3
        if booted:
            cam_path(cam, t, boot, boot + G.BAR, default_cam[0], wide[0], default_cam[1], wide[1])
        else:
            cam.location = default_cam[0]
            G.look_at(cam, default_cam[1])
    return update


PLATES = {
    "default_cube_boot": plate_default_cube_boot,
    "robot": plate_robot,
    "chorus": plate_chorus,
    "racks": plate_racks,
    "seats": plate_seats,
    "tear": plate_tear,
}


def render_job(index, out_root, width, height, samples, step):
    job = SHOTS["render_jobs"][index]
    seed = seed_value(job["seed"])
    scene = G.reset(width, height, samples)
    strip_metadata(scene)
    update = PLATES[job["plate"]](job, seed)
    out = Path(out_root) / job["dir"]
    out.mkdir(parents=True, exist_ok=True)
    s0 = job["start"] + job["lag_frames"]  # split renders: keep the step grid aligned with the shot's frames
    for f in range(job["start"], job["end"]):
        if (f - s0) % step:
            continue
        update(f / FPS - job["clock_offset_s"])
        scene.render.filepath = str(out / f"{f:05d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"JOB {index} {job['shot']} {job['dir']} frames {job['start']}-{job['end']} step {step} done")


def render_tiles(out_dir, width, height, samples, t):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for seed in SEEDS["thumbnail_tiles"]:
        scene = G.reset(width, height, samples)
        strip_metadata(scene)
        update = plate_chorus({"shot": "S50", "cam": "orbit", "fx": []}, seed)
        update(t)
        scene.render.filepath = str(out / f"tile_{seed}.png")
        bpy.ops.render.render(write_still=True)
    print("TILES done")


def render_probe(index, out_dir, width, height, samples, frac):
    """One frame at a fraction of a job's range, for smoke tests."""
    job = SHOTS["render_jobs"][index]
    scene = G.reset(width, height, samples)
    strip_metadata(scene)
    update = PLATES[job["plate"]](job, seed_value(job["seed"]))
    f = job["start"] + int((job["end"] - job["start"]) * frac)
    update(f / FPS - job["clock_offset_s"])
    scene.render.filepath = str(Path(out_dir) / f"{job['shot']}_{index:02d}_{job['dir']}.png")
    bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "probe":
        render_probe(int(args[1]), args[2], int(args[3]), int(args[4]), int(args[5]), float(args[6]))
    elif args[0] == "job":
        render_job(int(args[1]), args[2], int(args[3]), int(args[4]), int(args[5]), int(args[6]))
    elif args[0] == "tiles":
        render_tiles(args[1], int(args[2]), int(args[3]), int(args[4]), float(args[5]))


main()
