"""Render Blender plates for the shot list. Each plate builds one set, then update(t) sets every animated value from
the global time t alone (step 4: frames are pure functions of (t, seed)). A job picks the set, a named camera and
effects (shots/shots.json "render_jobs").

Usage:
  blender -b --factory-startup --python scenes/blender/plates.py -- job <job_index> <out_root> <width> <height> <samples> <step>
  blender -b --factory-startup --python scenes/blender/plates.py -- tiles <out_dir> <width> <height> <samples> <t>
  blender -b --factory-startup --python scenes/blender/plates.py -- probe <job_index> <out_dir> <width> <height> <samples> <fraction>
  blender -b --factory-startup --python scenes/blender/plates.py -- bench <job_index> <out_dir> <width> <height> <samples> <n_frames>

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
from mathutils import Matrix, Vector  # noqa: E402

ROOT = G.ROOT
SHOTS = json.loads((ROOT / "shots" / "shots.json").read_text())
FPS = SHOTS["fps"]
PANELS = ROOT / "renders" / "animatic" / "panels"
SHOT = {s["id"]: s for s in SHOTS["shots"]}
OUT_ROOT = None  # renders/<tier>/plates of the current run (set by render_job/probe): the river screen reads frames here
SCREEN_NAMES = ["consent", "counter", "chat", "terminal", "playlist", "rating"]


FEED = json.loads((ROOT / "config" / "feed_layout.json").read_text())


def mulberry32(seed):
    """The overlay's seeded PRNG (overlays/lib/seed.js), ported bit for bit so both sides make the same choices."""
    a = seed & 0xFFFFFFFF

    def imul(x, y):
        return (x * y) & 0xFFFFFFFF

    def r():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = imul(t ^ (t >> 15), t | 1)
        t ^= (t + imul(t ^ (t >> 7), t | 61)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return r


def feed_dark_order(seed):
    """Same shuffle as video.js DARK_ORDER: which of the first 24 tiles go dark in S51, in order."""
    r = mulberry32(seed + FEED["dark_seed_offset"])
    idx = [i for i in range(24) if i != 9]
    for i in range(len(idx) - 1, 0, -1):
        j = int(r() * (i + 1))
        idx[i], idx[j] = idx[j], idx[i]
    return idx


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
    # Eight screens; the last four sit close to the camera, flanking the shot (v5).
    slots = [(-1.6, 3.2, 2.6, 14), (5.2, 4.6, 2.4, -24), (-4.2, 6.5, 1.6, 26), (2.4, 8.0, 3.6, -8),
             (-1.4, -3.0, 0.9, 32), (2.3, -2.7, 2.7, -30), (-0.6, 0.8, 3.5, 6), (6.6, 2.2, 3.1, -30)]
    if reroll:
        r.shuffle(slots)
        slots = [(x + (r.random() - 0.5) * 3, y, z + (r.random() - 0.5) * 1.5, rz + r.randint(-30, 30)) for x, y, z, rz in slots]
    screens = []
    for i, (x, y, z, rz) in enumerate(slots):
        x += (r.random() - 0.5) * 0.6
        z += (r.random() - 0.5) * 0.4
        m = G.mat_image_screen(f"scr_{i}", PANELS / f"panel_{SCREEN_NAMES[i % len(SCREEN_NAMES)]}.png", 1.5)
        size = (1.5, 0.875) if i >= 4 else (2.2, 1.283)
        screens.append((G.plane(f"screen_{i}", size, (x, y, z), (math.radians(90), 0, math.radians(rz)), m),
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
    river, river_ob = None, screens[0][0]
    if "river_screen" in fx:  # screen_0 plays the river (this video's feed render), 16:9 and a little larger
        so, *_rest, rm = screens[0]
        so.scale = (2.5, 1.406, 1)
        river = next(n for n in rm.node_tree.nodes if n.type == "TEX_IMAGE")
        river_job = next(j for j in SHOTS["render_jobs"] if j["shot"] == "S50" and j["seed"] == "main")
        screens = screens[1:]  # the river screen does not bob or follow the synth
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
        if river is not None:
            f = round(t * FPS)
            for back in range(4):  # the animatic renders every 2nd frame: use the nearest earlier one
                path = OUT_ROOT / river_job["dir"] / f"{f - back:05d}.png"
                if path.exists():
                    river.image = bpy.data.images.load(str(path), check_existing=True)
                    break
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
        elif job["cam"] in ("screen_pullback", "wide_hold"):
            # S54: start filling the frame with the river playing on screen_0, pull back to the robot among its
            # screens; S55 holds that wide shot under the Regenerate click.
            so = river_ob
            bpy.context.view_layer.update()
            front = so.matrix_world.to_3x3().normalized() @ Vector((0, 0, 1))
            start = so.location + front * 2.25
            wide_pos, wide_tgt = (-0.9, -7.2, 1.3), (0.6, 0.6, 1.6)
            if job["cam"] == "screen_pullback":
                cam_path(cam, t, t0 + 0.2, t1, tuple(start), wide_pos, tuple(so.location), wide_tgt)
            else:
                cam.location = (wide_pos[0] + 0.15 * tl, wide_pos[1], wide_pos[2])
                G.look_at(cam, wide_tgt)
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
    for i in range(12):  # v5: more screens, closer to the camera's orbit (radius 3.4)
        a = i / 12 * 2 * math.pi + (r.random() - 0.5) * 0.25
        rad = 4.5 + (r.random() - 0.5) * 0.7
        z = 1.5 + (r.random() - 0.5) * 1.6
        m = G.mat_image_screen(f"ring_{i}", PANELS / f"panel_{SCREEN_NAMES[r.randrange(len(SCREEN_NAMES))]}.png", 1.4)
        ob = G.plane(f"ring_{i}", (1.7, 0.99), (rad * math.cos(a), rad * math.sin(a), z),
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
    s = SHOT[job["shot"]]
    swaps = []
    if "missing_texture" in fx:  # v5: textures go missing one object at a time over the first 1.6 s
        chk = checker_material()
        order = [o for o, *_ in ring] + [o for o, *_ in tokens] + \
                [o for o in bpy.data.objects if o.type == "MESH" and (o.parent is not None) and not o.name.startswith(("eye", "mouth"))]
        for o in order:
            swaps.append((o, [m for m in o.data.materials]))
        swap_rng = random.Random(seed + 7)
        swap_rng.shuffle(swaps)
    t0, t1 = s["start_s"], s["end_s"]
    grid = floor.active_material.node_tree.nodes["grid_amount"]
    energies = [l.data.energy for l in lights]
    clip_t = t0 + 1.5
    beat_len = 60 / G.TIMING["tempo_bpm"]
    lights_e = list(zip(lights, energies))
    scr = screens_of([o for o, *_ in ring])
    font = bpy.data.fonts.load(str(ROOT / "assets" / "fonts" / "Inter[opsz,wght].ttf"), check_existing=True)
    ghost = None
    if "sheet_ghost" in fx:  # S20: the literal ghost; the sheet is whipped off on the whip pan
        sheet = G.mat_principled("sheet", G.PAL["paper"], 0.8)
        hole = G.mat_principled("hole", "#000000", 1.0)
        ghost = G.empty("ghost", (0, 0, 0), parent=rig["root"])
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.85, radius2=0.42, depth=1.75, location=(0, 0, 0.95))
        G._finish(bpy.context.object, "sheet_body", sheet, ghost)
        bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.46, location=(0, 0, 1.82))
        G._finish(bpy.context.object, "sheet_head", sheet, ghost)
        bpy.ops.object.shade_smooth()
        for side in (-1, 1):
            G.rounded_box(f"sheet_eye_{side}", (0.09, 0.05, 0.13), (side * 0.15, -0.43, 1.88), hole, 0.04, parent=ghost)
    neon = []
    if "neon_lights" in fx:  # S24: a neon LIGHTS sign behind the robot goes out one letter per beat
        for i, ch in enumerate("LIGHTS"):
            cu = bpy.data.curves.new(f"neon_{i}", "FONT")
            cu.body, cu.font, cu.extrude, cu.size, cu.align_x = ch, font, 0.04, 1.5, "CENTER"
            ob = bpy.data.objects.new(f"neon_{i}", cu)
            scene.collection.objects.link(ob)
            ob.data.materials.append(G.mat_emission(f"neon_mat_{i}", G.PAL["accent"], 9))
            ob.location, ob.rotation_euler = ((i - 2.5) * 1.1, 3.4, 2.5), (math.pi / 2, 0, 0)
            neon.append(ob)
    clouds, rays = [], []
    if "cloud" in fx:  # S25: looking down from inside the cloud, rays falling on the lone robot
        scene.world.node_tree.nodes["Principled Volume"].inputs["Density"].default_value = 0.02
        cl = bpy.data.materials.new("cloud")
        cl.use_nodes = True
        nt = cl.node_tree
        nt.nodes.clear()
        tc, nz = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 0.45, 3.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.45, 0.8
        em, tr, mix = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeMixShader")
        em.inputs["Color"].default_value, em.inputs["Strength"].default_value = G.lin("#d8dae4"), 0.9
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
        cl.blend_method = "BLEND" if hasattr(cl, "blend_method") else None
        for i in range(4):
            ob = G.plane(f"cloud_{i}", (9, 9), ((r.random() - 0.5) * 3, (r.random() - 0.5) * 3, 6.5 + i * 0.9), (0, 0, r.random() * 3), cl)
            clouds.append((ob, ob.location.copy(), r.random()))
        for i in range(3):
            sp = bpy.data.lights.new(f"ray_{i}", "SPOT")
            sp.energy, sp.spot_size, sp.spot_blend, sp.color = 700, 0.22, 0.6, G.lin("#e8d9b0")[:3]
            ob = bpy.data.objects.new(f"ray_{i}", sp)
            scene.collection.objects.link(ob)
            ob.location = ((i - 1) * 1.4, 0.5 * (i - 1), 9)
            G.look_at(ob, (0, 0, 0))
            rays.append(ob)
    letters = []
    if "tokens_3d" in fx:  # "TOKENS" falls as solid letters around the robot
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
        if swaps:
            n = int(len(swaps) * min(1.0, max(0.0, tl / 1.6)))
            for i, (o, mats) in enumerate(swaps):
                for k in range(len(o.data.materials)):
                    o.data.materials[k] = chk if i < n else mats[k]
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
            d = 3.9 - 2.3 * G.ease(tl / max(1e-6, t1 - t0))  # stays inside the screen ring (radius ~4.5)
            cam.data.lens = 44.0 * d / 3.9
            cam.location = (0, -d, 1.55)
            G.look_at(cam, (0, 0, 1.55))
        elif c == "low_up":
            cam.data.lens = 24
            cam.location = (0.5, -1.7, 0.35)
            G.look_at(cam, (0, 0, 2.2))
        elif c == "wide_static":  # inside the screen ring, so nothing blocks the robot or the sign
            cam.data.lens = 20
            cam.location = (0, -2.9, 1.7)  # well inside the screen ring (radius >= 4.15), so nothing blocks the view
            G.look_at(cam, (0, 0, 1.5))
        elif c == "topdown":
            cam.location = (0, -0.001, 11 - 1.5 * G.ease(tl / max(1e-6, t1 - t0)))
            G.look_at(cam, (0, 0, 0))
        elif c == "rise":  # v5: start at the floor looking UP at the robot, then arc up and over it, rolling
            k = G.ease(tl / max(1e-6, t1 - t0))
            phi = math.radians(-24 + 112 * k)        # elevation around the robot's centre
            head = math.radians(-90 + 140 * k)       # heading swings round as it rises
            rad, c0 = 3.0, (0, 0, 1.3)
            cam.data.lens = 22
            cam.location = (c0[0] + rad * math.cos(phi) * math.cos(head), c0[1] + rad * math.cos(phi) * math.sin(head),
                            max(0.08, c0[2] + rad * math.sin(phi)))
            G.look_at(cam, c0)
            cam.rotation_euler.rotate_axis("Z", math.radians(35) * k)
        elif c == "dance_low":
            cam.data.lens = 24
            cam.location = (0.8, -2.4, 0.4)
            G.look_at(cam, (0, 0, 1.4))
        if "head_up" in fx:
            rig["head"].rotation_euler.x = 0.35 * G.ease(tl / 0.6)
        if ghost is not None:
            k = G.ease((tl - 0.3) / 0.4)  # whipped off up and out of frame
            ghost.location = (2.5 * k, 0, 4.0 * k)
            ghost.rotation_euler = (0, -1.2 * k, 0)
            for o in ghost.children:
                o.hide_render = tl > 0.75
        for i, ob in enumerate(neon):
            on = beats_since(t, t0) < i + 2
            ob.active_material.node_tree.nodes["Emission"].inputs["Strength"].default_value = 9.0 if on else 0.0
        for ob, base, ph in clouds:
            ob.location = (base.x + 0.4 * t, base.y + 0.25 * math.sin(t * 0.5 + ph * 6), base.z)
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
                ob.hide_render = n >= 2 + i // 3
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
        elif job["cam"] == "crane_chart":  # v5: crane up out of the aisle and tilt to the climbing chart in one move
            k = (t - t0) / max(1e-6, t1 - t0)
            curve.bevel_factor_end = 0.15 + 0.85 * G.ease(k)
            cam_path(cam, t, t0, t1, (0, -1.0, 0.7), (0, 6.0, 3.2), (0, 14, 2.0), (0, 20, 5.6))
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
    if "arena" in job["fx"]:  # S33: the front row isn't alone; the whole arena is the same robot
        unit = bpy.data.collections.new("seat_unit")
        scene.collection.children.link(unit)
        before = set(bpy.data.objects)
        G.rounded_box("u_seat", (0.8, 0.7, 0.18), (0, 0, 0.45), seat, 0.06)
        G.rounded_box("u_back", (0.8, 0.14, 0.9), (0, -0.35, 0.95), seat, 0.06)
        urig = G.build_character((0, 0, 0))
        urig["root"].location, urig["root"].rotation_euler.z = (0, 0, -0.16), math.pi
        for side in (-1, 1):
            leg = bpy.data.objects[f"leg_{side}"]
            leg.rotation_euler.x, leg.location = math.pi / 2, (side * 0.15, -0.33, 0.66)
        for name, objs in urig["eye_sets"].items():  # no performance for the crowd: plain eyes only
            for e in objs:
                e.hide_render = name != "normal"
        for ob in set(bpy.data.objects) - before:
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            unit.objects.link(ob)
        bpy.context.view_layer.layer_collection.children["seat_unit"].exclude = True
        for row in range(1, 11):
            for i in range(-10, 11):
                inst = bpy.data.objects.new(f"crowd_{row}_{i}", None)
                inst.instance_type, inst.instance_collection = "COLLECTION", unit
                inst.location = (i * 1.0, -row * 1.4, row * 0.38)
                scene.collection.objects.link(inst)
        # Light the crowd's backs from behind the camera so the rows read as robots, not silhouettes.
        G.area_light("crowd_back", "#b8c4ff", 2500, 14, (0, -22, 12), (0, -7, 1))
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
        elif "arena" in job["fx"]:  # from just behind our robot, pull back and up to reveal the rows behind it
            cam_path(cam, t, t0, t1, (0, -0.85, 2.15), (0, -17.5, 7.8), (0, 9, 2.0), (0, 6, 1.2))
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
    cam = scene.camera
    fade_order = ["arm_-1", "arm_1", "leg_-1", "leg_1", "pelvis", "torso"]  # "a little more would go"

    def update(t):
        tl = t - s["start_s"]
        update_robot(t)
        z = root.location.z
        if job["cam"] == "pullback":  # from the tear out to the whole robot, which loses a piece per score
            k = G.ease(tl / (s["end_s"] - s["start_s"]))
            cam.data.lens = 40 - 8 * k
            cam.location = (hx - 0.35 + 0.2 * k, -1.35 - 3.6 * k, hz + 0.02 - 0.55 * k + z)
            G.look_at(cam, (hx + 0.05 - 0.05 * k, 0, hz - 0.02 - 0.6 * k + z))
        if "score_fade" in job["fx"]:
            n = beats_since(t, s["start_s"] + 1.0)
            for i, name in enumerate(fade_order):
                bpy.data.objects[name].hide_render = n > i
        # Starts under one eye and slides down the screen face.
        spinner.location = (hx + 0.1, -0.245, hz - 0.03 + z - 0.09 * G.ease((tl - 0.6) / 2.6))
        spinner.rotation_euler = (0, -tl * 2 * math.pi * 1.25, 0)
        spinner.hide_render = tl < 0.4
    return update


# ---------- set: Blender's default scene, then the boot (Intro, Ending) ----------

def plate_default_cube_boot(job, seed):
    """S01/S02: Blender's default scene; on the first downbeat the box opens and the world springs out of it.
    S56 ("vacuum", local clock): the box reappears and vacuums the world back in, then snaps shut."""
    import bmesh
    scene = bpy.context.scene
    boot = G.DOWNBEATS[0]
    fx = set(job["fx"])
    grey = G.mat_principled("default_grey", "#cccccc", 0.5)
    inner = G.mat_principled("box_inside", "#1a1a1e", 0.9)
    # An open-topped default cube (so it can open), with two hinged lid flaps closing the top.
    box = G.empty("box", (0, 0, 0))
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    body = bpy.context.object
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9], context="FACES")
    bm.to_mesh(body.data)
    bm.free()
    body.data.materials.append(grey)
    sol = body.modifiers.new("solid", "SOLIDIFY")
    sol.thickness, sol.material_offset = 0.04, 1
    body.data.materials.append(inner)
    # The underside is unlit black: at the very end the cube tips onto it and it becomes the end card's black.
    body.data.materials.append(G.mat_emission("box_underside", "#000000", 0.0))
    for poly in body.data.polygons:
        if poly.normal.z < -0.9:
            poly.material_index = 2
    G._finish(body, "default_cube", None, box)
    hinges = []
    for side in (-1, 1):
        h = G.empty(f"hinge_{side}", (side * 1.0, 0, 2.0), parent=box)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(side * 0.5, 0, 2.0))
        flap = bpy.context.object
        flap.scale = (1.0, 2.0, 0.04)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        G._finish(flap, f"flap_{side}", grey, h)
        hinges.append((h, side))
    pl = bpy.data.lights.new("Light", "POINT")
    pl.energy = 1000
    plo = bpy.data.objects.new("Light", pl)
    plo.location = (4.08, 1.0, 5.9)
    scene.collection.objects.link(plo)
    update_robot = plate_robot(dict(job, cam="wide", fx=[]), seed)
    cam = scene.camera
    floor = bpy.data.objects["floor"]
    world_bg = scene.world.node_tree.nodes["Background"]
    lights = [o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith(("key", "rim"))]
    screens = [o for o in bpy.data.objects if o.name.startswith("screen_")]
    root = bpy.data.objects["char_root"]
    char_objs = [o for o in bpy.data.objects if o.parent is not None and o.name not in ("default_cube",) and
                 not o.name.startswith(("flap_", "hinge_"))] + [root]
    default_cam = ((7.36, -6.93, 4.96), (0, 0, 1))
    wide = ((-0.6, -6.6, 0.8), (0.9, 0.5, 1.45))
    spread_cam = ((-2.5, -13.0, 5.2), (1.0, 1.5, 1.6))
    mouth = (0.0, 0.0, 1.6)  # where things spring out of / get sucked into

    # Home positions, recorded once before any animation: the unpack/pack must aim for these, not for wherever the
    # previous frame left an object (that collapsed every target toward the box and stacked things in a column).
    home = {o.name: o.location.copy() for o in screens + [root]}

    def spring(objs, k_of):
        """Unpack (k: 0 -> 1) or pack (1 -> 0) each object along an arc: up out of the box's open top, around, and
        over to where the robot set put it, so nothing passes through the box's walls."""
        for o, k in objs:
            target = home[o.name].copy()
            target.z = o.location.z  # keep the per-frame bob the robot set just applied
            r0, th0 = math.hypot(target.x, target.y), math.atan2(target.y, target.x)
            r = r0 * G.ease(min(1.0, max(0.0, (k - 0.25) / 0.75)))         # leaves the box only once above its rim
            th = th0 + 1.6 * (1 - k)                                          # swings round the box as it goes
            z = (0.9 + (target.z - 0.9) * k) + 2.4 * math.sin(math.pi * min(1.0, k * 1.15))  # rises over the rim first
            o.location = (r * math.cos(th), r * math.sin(th), z)
            o.scale = (max(min(1.0, k * 2.5), 0.001),) * 3

    def update(t):
        if "vacuum" in fx:
            tl = t  # local clock (clock_offset applied by the job)
            update_robot(boot + 4.0 + tl)  # the restarted world, fully booted
            # The exact reverse of the S02 unpack: robot first, then each screen, lifted up over the rim and
            # dropped in along the same arcs, at the same 0.09 s stagger and 0.75 s per item.
            items = [root] + screens[::-1]
            k_of = lambda i: 1.0 - min(1.0, max(0.0, (tl - 0.3 - 0.09 * i) / 0.75))
            spring([(o, k_of(i)) for i, o in enumerate(items)], None)
            v = min(1.0, max(0.0, (tl - 0.3) / (0.09 * len(items) + 0.75)))
            floor.active_material.node_tree.nodes["grid_amount"].inputs[1].default_value = 0.4 * (1 - v)
            box.scale = (G.ease(tl / 0.25),) * 3
            t_closed = 0.3 + 0.09 * len(items) + 0.75
            close = G.ease((tl - t_closed) / 0.25)
            for h, side in hinges:
                h.rotation_euler.y = side * 2.3 * (1 - close)
            # Then the cube tips toward the camera onto its unlit underside, and the camera pushes into that black face.
            tip = G.ease((tl - t_closed - 0.25) / 0.5)
            to_cam = Vector((default_cam[0][0], default_cam[0][1], 0)).normalized()
            axis = Vector((0, 0, 1)).cross(to_cam).normalized()
            from mathutils import Matrix
            rot = Matrix.Rotation(-math.pi / 2 * tip, 4, axis)
            c = Vector((0, 0, 1))
            box.matrix_world = Matrix.Translation(c - (rot.to_3x3() @ c)) @ rot
            for o in lights:
                o.hide_render = v > 0.9
            plo.hide_render = v < 0.9
            world_bg.inputs["Color"].default_value = G.lin("#3d3d3d") if v > 0.95 else G.lin(G.PAL["base"])
            cam_path(cam, t, 0.2, t_closed, wide[0], default_cam[0], wide[1], default_cam[1])
            if tl > t_closed + 0.2:
                face = c + (rot.to_3x3() @ Vector((0, 0, -1)))  # centre of the underside, now facing the camera
                push = G.ease((tl - t_closed - 0.2) / 0.6)
                start = Vector(default_cam[0])
                end = face + to_cam * 0.6 + Vector((0, 0, 0.05))
                cam.location = start.lerp(end, push)
                G.look_at(cam, Vector(default_cam[1]).lerp(face, push))
            return
        update_robot(t)
        booted = t >= boot
        opening = G.ease((t - boot) / 0.3)
        for h, side in hinges:
            h.rotation_euler.y = side * 2.3 * opening   # the lid flaps fly open on the downbeat
        out = lambda i: min(1.0, max(0.0, (t - boot - 0.12 - 0.06 * i) / 0.7))
        if "box_open" in fx or booted:
            spring([(o, out(i)) for i, o in enumerate(screens)] + [(root, out(len(screens)))], None)
        else:
            for o in screens + [root]:
                o.scale = (0.001,) * 3
        box.scale = (1.0 - G.ease((t - boot - 1.0) / 0.5),) * 3 if booted else (1, 1, 1)
        plo.hide_render = booted
        floor.hide_render = not booted
        world_bg.inputs["Color"].default_value = G.lin(G.PAL["base"]) if booted else G.lin("#3d3d3d")
        for o in lights:
            o.hide_render = not booted
        floor.active_material.node_tree.nodes["grid_amount"].inputs[1].default_value = 0.4 * G.ease((t - boot) / G.BAR)
        if booted:
            # Pull back wide enough to watch everything spread out of the box to its place across the set.
            cam_path(cam, t, boot, boot + G.BAR, default_cam[0], spread_cam[0], default_cam[1], spread_cam[1])
        else:
            cam.location = default_cam[0]
            G.look_at(cam, default_cam[1])
    return update


# ---------- set: the data stream (loss landscape) ----------

def stream_path(u):
    """The river's centre line, u in 0..1 from the far ridge down to the minimum near camera."""
    return (3.2 * math.sin(u * 5.0) * (1 - u) + 0.4, 30 - 34 * u)


def plate_stream(job, seed):
    """S26/S27 and the feed: a river of tokens running down a contoured loss landscape to a glowing minimum,
    the robot dancing on a rock mid-stream (gradient descent, literally)."""
    r = random.Random(seed)
    scene = bpy.context.scene
    G.void_world(scene, haze=0.006)
    pts = [stream_path(i / 240) for i in range(241)]

    def height(x, y):
        d = min((x - px) ** 2 + (y - py) ** 2 for px, py in pts[::3]) ** 0.5
        hills = 0.11 * (y + 4) + 0.9 * math.sin(x * 0.45) * math.cos(y * 0.3) + 0.5 * math.sin(x * 0.9 + y * 0.2)
        return max(0.0, hills) * (1 - 0.85 * math.exp(-(d / 2.2) ** 2)) - 0.25 * math.exp(-(d / 1.0) ** 2)

    bpy.ops.mesh.primitive_grid_add(x_subdivisions=110, y_subdivisions=110, size=44, location=(0, 12, 0))
    terrain = bpy.context.object
    terrain.name = "terrain"
    for v in terrain.data.vertices:
        w = terrain.matrix_world @ v.co
        v.co.z = height(w.x, w.y)
    bpy.ops.object.shade_smooth()
    # Contour lines in --line over the base colour, every 0.33 m of height.
    m = bpy.data.materials.new("contours")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    geo, sep = N("ShaderNodeNewGeometry"), N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs[0])
    mul = N("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 3.0; L(sep.outputs["Z"], mul.inputs[0])
    fr = N("ShaderNodeMath"); fr.operation = "FRACT"; L(mul.outputs[0], fr.inputs[0])
    lt = N("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.06; L(fr.outputs[0], lt.inputs[0])
    # No line on the flat ground where the hills clamp to z = 0 (C5 fix: z = 0 sits on a contour, so whole plains
    # rendered in the line colour, big pale blobs under S53's top-down camera).
    ab = N("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L(sep.outputs["Z"], ab.inputs[0])
    gt = N("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.004; L(ab.outputs[0], gt.inputs[0])
    both = N("ShaderNodeMath"); both.operation = "MULTIPLY"; L(lt.outputs[0], both.inputs[0]); L(gt.outputs[0], both.inputs[1])
    lt = both
    base = N("ShaderNodeBsdfPrincipled"); base.inputs["Base Color"].default_value = G.lin("#121117"); base.inputs["Roughness"].default_value = 0.6
    line = N("ShaderNodeEmission"); line.inputs["Color"].default_value = G.lin("#6a6276"); line.inputs["Strength"].default_value = 2.0
    mix = N("ShaderNodeMixShader"); L(lt.outputs[0], mix.inputs[0]); L(base.outputs[0], mix.inputs[1]); L(line.outputs[0], mix.inputs[2])
    out = N("ShaderNodeOutputMaterial"); L(mix.outputs[0], out.inputs[0])
    terrain.data.materials.append(m)
    # The glowing minimum where the stream ends.
    mx, my = stream_path(1.0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.9, minor_radius=0.05, location=(mx, my, height(mx, my) + 0.05))
    G._finish(bpy.context.object, "minimum", G.mat_emission("min_mat", G.PAL["accent"], 14), None)
    # Tokens flowing down the stream.
    tok_mats = [G.mat_emission("tk_a", G.PAL["accent2"], 6), G.mat_emission("tk_p", G.PAL["paper"], 4),
                G.mat_emission("tk_o", G.PAL["accent"], 6)]
    flow = []
    for i in range(170):
        ob = G.rounded_box(f"flow_{i}", (0.16, 0.16, 0.05), (0, 0, 0), tok_mats[0 if r.random() < 0.65 else 1 + (r.random() < 0.3)], 0.01)
        flow.append((ob, r.random(), (r.random() - 0.5) * 1.4, 0.035 + r.random() * 0.03))
    # The robot dances on a rock beside the stream, two-thirds of the way down.
    ru = 0.72
    rx, ry = stream_path(ru)
    rx += 1.6
    rz = height(rx, ry)
    G.rounded_box("rock", (1.3, 1.1, 0.7), (rx, ry, rz + 0.1), G.mat_principled("rock_m", G.PAL["surface"], 0.8), 0.2)
    rig = G.build_character((rx, ry, rz + 0.45))
    lights = [G.area_light("key_a", "#b8c4ff", 900, 6, (rx - 5, ry - 6, rz + 7), (rx, ry, rz)),
              G.area_light("rim", G.PAL["accent"], 120, 2, (rx + 1, ry + 3, rz + 3), (rx, ry, rz + 1))]
    cam = G.camera(28)
    G.bloom(scene)
    s = SHOT[job["shot"]]
    t0, t1 = s["start_s"], s["end_s"]
    le = [(l, l.data.energy) for l in lights]
    beat_len = 60 / G.TIMING["tempo_bpm"]

    face = -math.pi / 2 if job["cam"] == "low" else 0.0  # the low shot looks across the stream at the robot's front
    tiles = []
    page = None
    if "video_tiles" in job["fx"]:
        # S53 on: the feed's videos as panels. At the cut they sit exactly where the 2D feed (S52) draws them, seen by
        # a straight-down camera, still scrolling at the feed's speed; then they peel off one by one, arc down into the
        # river and flow on with the tokens (the same motion in the S53 shot and in the main river render S54 plays).
        s51, s52, s53 = SHOT["S51"], SHOT["S52"], SHOT["S53"]
        tile_jobs = {j["seed"]: j for j in SHOTS["render_jobs"] if j["shot"] == "S50"}
        f_ = FEED
        o53 = f_["v0"] * (s53["start_s"] - s52["start_s"])
        n_dark = f_["dark_per_beat"] * sum(1 for bt in G.BEATS if s51["start_s"] <= bt <= s51["end_s"])
        dark_order = feed_dark_order(SEEDS["main"])
        cam_h, lens = 12.0, 28.0
        plane_w = cam_h * 36.0 / lens
        plane_h = plane_w * 1080 / 1920
        gcx, gcy, gz = rx - 0.6, ry + 2.0, 12.0
        to_world = lambda px, py: (gcx + (px / 1920 - 0.5) * plane_w, gcy + (0.5 - py / 1080) * plane_h)
        tw = f_["tile_w"] / 1920 * plane_w
        r0 = int((o53 - f_["y0"]) // f_["row_h"]) - 1
        k = 0
        for row in range(r0, r0 + 7):
            for col in range(f_["cols"]):
                cell = row * f_["cols"] + col
                live = col == f_["live_col"] and row % f_["live_every"] == 1
                idx = cell % f_["tiles_per_cycle"]
                dark = n_dark > 0 and 0 <= row < 4 and cell in dark_order and dark_order.index(cell) < n_dark
                m = G.mat_image_screen(f"vt_{k}", PANELS / "panel_playlist.png", 0.0 if dark else 1.0)
                ob = G.plane(f"vtile_{k}", (tw, tw * f_["tile_h"] / f_["tile_w"]), (0, 0, gz), (0, 0, 0), m)
                node = next(n for n in m.node_tree.nodes if n.type == "TEX_IMAGE")
                tj = tile_jobs["main"] if live else tile_jobs[f"thumbnail_tiles.{idx}"]
                px = f_["x0"] + col * (f_["tile_w"] + f_["gap"]) + f_["tile_w"] / 2
                py0 = f_["y0"] + row * f_["row_h"] + f_["tile_h"] / 2 - o53
                tiles.append((ob, node, tj, (px, py0), (k * 0.29) % 0.55, 0.45 + 0.045 * k, dark))
                k += 1
        # The feed's dark page behind the tiles, fading away as they peel off to reveal the landscape below.
        pm = bpy.data.materials.new("page")
        pm.use_nodes = True
        nt = pm.node_tree
        nt.nodes.clear()
        em, tr, mx, out = (nt.nodes.new(n) for n in ("ShaderNodeEmission", "ShaderNodeBsdfTransparent", "ShaderNodeMixShader", "ShaderNodeOutputMaterial"))
        em.inputs["Color"].default_value, em.inputs["Strength"].default_value = G.lin(G.PAL["base"]), 1.0
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
        page = (G.plane("page", (60, 60), (gcx, gcy, gz - 0.05), (0, 0, 0), pm), mx)
        feed_world = (to_world, o53, gz)

    def tile_frame(job_, f):
        for back in range(4):
            path = OUT_ROOT / job_["dir"] / f"{f - back:05d}.png"
            if path.exists():
                return bpy.data.images.load(str(path), check_existing=True)
        return None

    gen = None
    if "gen_button" in job["fx"]:  # v6: a Generate button orbits the robot; in S27 the robot presses it (the music stops)
        gen = G.empty("gen_button", (rx, ry, rz + 1.5))
        G.rounded_box("gen_pill", (0.75, 0.12, 0.26), (rx, ry, rz + 1.5), G.mat_principled("gen_body", G.PAL["surface"], 0.4), 0.12, parent=gen)
        font = bpy.data.fonts.load(str(ROOT / "assets" / "fonts" / "Inter[opsz,wght].ttf"), check_existing=True)
        cu = bpy.data.curves.new("gen_text", "FONT")
        cu.body, cu.font, cu.size, cu.align_x, cu.align_y = "Generate", font, 0.13, "CENTER", "CENTER"
        gt = bpy.data.objects.new("gen_text", cu)
        scene.collection.objects.link(gt)
        gen_glow = G.mat_emission("gen_glow", G.PAL["paper"], 3)
        gt.data.materials.append(gen_glow)
        gt.location, gt.rotation_euler = (rx, ry - 0.065, rz + 1.5), (math.pi / 2, 0, 0)
        gt.parent = gen
        gt.matrix_parent_inverse = gen.matrix_world.inverted()
    props = []
    if "refs" in job["fx"]:  # v5: props from the other videos float down the stream and fly around the robot
        names = ["check", "ticket", "cookie", "version", "flap"]
        for i in range(10):
            m = G.mat_image_screen(f"ref_{i}", PANELS / f"ref_{names[i % 5]}.png", 1.6)
            ob = G.plane(f"prop_{i}", (0.9, 0.51), (0, 0, 0), (0, 0, 0), m)
            props.append((ob, i, r.random()))

    def update(t):
        tl = t - t0
        rig["root"].rotation_euler.z = face
        idle(rig, t)
        G.perform(rig, t)
        react(t, le)
        for ob, ph, lat, sp in flow:
            u = (ph + sp * t) % 1.0
            x, y = stream_path(u)
            ob.location = (x + lat * (1 - u * 0.6), y, height(x, y) + 0.08)
            ob.rotation_euler.z = u * 20
        if "dance" in job["fx"]:
            prior = [b for b in G.BEATS if b <= t]
            n = len(prior)
            ph = (t - prior[-1]) / beat_len if prior else 0.0
            swing = math.sin(math.pi * min(1.0, ph))
            for side, sh in rig["shoulders"].items():
                sh.rotation_euler.y = -side * (0.3 + 0.9 * swing * (1 if (n + (side > 0)) % 2 else 0.2))
            rig["root"].location.z = rig["rest"]["root"].z + 0.07 * swing
            rig["root"].rotation_euler.z = face + 0.2 * (1 if (n // 2) % 2 else -1)
        if page is not None:
            ts = t - SHOT["S53"]["start_s"] + 0.5 / FPS  # half a frame of tolerance: S53's first frame must show them
            page[0].hide_render = ts < 0 or ts > 1.2
            page[1].inputs[0].default_value = 1.0 - G.ease((ts - 0.35) / 0.6)
        for ob, node, tj, (px, py0), u0, delay, dark in tiles:
            ts = t - SHOT["S53"]["start_s"] + 0.5 / FPS
            ob.hide_render = ts < 0
            if ts < 0:
                continue
            if not dark:
                img = tile_frame(tj, round(t * FPS))
                if img is not None:
                    node.image = img
            to_world, o53, gz = feed_world
            # Where the 2D feed would draw this tile now: the scroll keeps going at the feed's speed.
            sx, sy = to_world(px, py0 - FEED["v0"] * min(ts, delay))
            land = delay + 1.3
            if ts < land:  # peel off the page and arc down into the river
                k = G.ease(max(0.0, (ts - delay) / 1.3))
                ex, ey = stream_path(u0)
                ez = height(ex, ey) + 0.2
                ob.location = (sx + (ex - sx) * k, sy + (ey - sy) * k, gz + (ez - gz) * k + 2.0 * math.sin(math.pi * k))
                ob.rotation_euler = (math.radians(55) * k, 0, math.radians(20) * math.sin(math.pi * k))
            else:  # part of the stream now, flowing down it with the tokens
                u = min(0.999, u0 + 0.05 * (ts - land))
                x, y = stream_path(u)
                ob.location = (x + 0.3 * math.sin(u * 30 + delay), y, height(x, y) + 0.22)
                ob.rotation_euler = (math.radians(55), 0, 0.15 * math.sin(t * 1.5 + delay))
        if gen is not None:
            press_t = t1 - 0.35
            k = G.ease((t - (t1 - 1.1)) / 0.6) if "gen_press" in job["fx"] else 0.0
            a = t * 1.3
            orbit_pos = (rx + 1.3 * math.cos(a), ry + 1.3 * math.sin(a), rz + 1.5 + 0.25 * math.sin(t * 2.1))
            front_pos = (rx - 0.62, ry, rz + 1.45)  # in front of the robot (it faces -X in the low shot)
            gen.location = [orbit_pos[i] + (front_pos[i] - orbit_pos[i]) * k for i in range(3)]
            gen.rotation_euler = (0, 0, (a + math.pi / 2) * (1 - k) + (-math.pi / 2) * k)
            pressed = "gen_press" in job["fx"] and t >= press_t
            gen.scale = (1, 0.6 if pressed and t < press_t + 0.15 else 1, 1)
            G.emission_node(gen_glow).inputs["Strength"].default_value = 14 if pressed else 3
            if "gen_press" in job["fx"]:
                reach = G.ease((t - (press_t - 0.45)) / 0.35)
                rig["shoulders"][1].rotation_euler.x = -1.45 * reach  # the robot pushes the button
        for ob, i, ph in props:
            if i % 2 == 0:  # riding the stream
                u = (ph + 0.05 * t) % 1.0
                x, y = stream_path(u)
                ob.location = (x, y, height(x, y) + 0.35 + 0.1 * math.sin(t * 3 + i))
                ob.rotation_euler = (math.radians(70), 0, u * 6)
            else:  # orbiting the dancing robot
                a = t * (0.9 + 0.2 * i % 3) + ph * 6.28
                ob.location = (rx + 1.6 * math.cos(a), ry + 1.6 * math.sin(a), rz + 1.2 + 0.5 * math.sin(t * 1.7 + i))
                ob.rotation_euler = (math.radians(90), 0, a + math.pi / 2)
        if job["cam"] == "feed_dive":
            # Top-down on the grid of videos, then descend to the river view the main render holds (S54 opens on it).
            k = G.ease((tl - 0.9) / max(1e-6, (t1 - t0) - 1.1))
            cam.data.lens = 28
            top, top_t = (rx - 0.6, ry + 2.0 - 1e-4, 24.0), (rx - 0.6, ry + 2.0, 0)  # 12 m above the grid, lens 28
            end, end_t = (rx + 3, ry - 8, rz + 5.5), (rx - 0.5, ry + 4, rz + 0.5)
            cam.location = [top[i] + (end[i] - top[i]) * k for i in range(3)]
            # Not look_at: straight down, to_track_quat takes the roll from the tiny horizontal part of the view and
            # flipped it 180 degrees and back as the descent began. The up vector hands over from the feed's +Y to world up.
            fwd = (Vector([top_t[i] + (end_t[i] - top_t[i]) * k for i in range(3)]) - cam.location).normalized()
            right = fwd.cross(Vector((0, 1 - k, k)).normalized()).normalized()
            cam.rotation_euler = Matrix((right, right.cross(fwd), -fwd)).transposed().to_euler()
        elif job["cam"] == "wide":  # high, looking down the descent with the robot on its rock
            cam_path(cam, t, t0, t1, (rx + 5, ry - 9, rz + 6.5), (rx + 3, ry - 8, rz + 5.5), (rx - 1, ry + 6, rz), (rx - 0.5, ry + 4, rz + 0.5))
        else:  # low, from the far bank: the stream rushes between camera and robot
            cam.data.lens = 22
            # v5: a slow arc across the bank so the shot keeps moving
            k = G.ease(tl / max(1e-6, t1 - t0))
            a = math.radians(-12 + 30 * k)
            cam.location = (rx - 4.4 * math.cos(a), ry - 4.4 * math.sin(a) - 0.6, rz + 1.9 - 0.4 * k)
            G.look_at(cam, (rx - 0.5, ry, rz + 1.0))
    return update


# ---------- set: the container ship (Verse 2) ----------

def plate_ship(job, seed):
    """S30b: the merged lines ship out; containers spell LOOKS GOOD (the stamp lands in the overlay)."""
    scene = bpy.context.scene
    G.void_world(scene)
    floor = G.grid_floor()
    hullm = G.mat_principled("hull", G.PAL["surface"], 0.5)
    deck = G.mat_principled("deck", G.PAL["line"], 0.6)
    win = G.mat_emission("win", "#ffd27a", 5)
    ship = G.empty("ship", (0, 0, 0))
    G.rounded_box("hull", (12.5, 2.6, 1.4), (0, 0, 0.5), hullm, 0.3, parent=ship)
    G.rounded_box("bow", (1.8, 2.0, 1.2), (6.6, 0, 0.6), hullm, 0.5, parent=ship)
    G.rounded_box("bridge", (1.6, 2.2, 2.4), (-5.4, 0, 2.4), deck, 0.08, parent=ship)
    for i in range(4):
        G.rounded_box(f"win_{i}", (0.24, 0.02, 0.2), (-6.0 + i * 0.4, -1.11, 3.1), win, 0.02, parent=ship)
    font = bpy.data.fonts.load(str(ROOT / "assets" / "fonts" / "Inter[opsz,wght].ttf"), check_existing=True)
    cmats = [G.mat_principled("cont_a", "#2a2a35", 0.5), G.mat_principled("cont_b", "#33303b", 0.5)]
    lm = G.mat_emission("cont_letter", G.PAL["paper"], 3)
    for i, ch in enumerate("LOOKS GOOD"):
        x = -4.0 + i * 0.98
        G.rounded_box(f"cont_{i}", (0.92, 2.3, 1.05), (x, 0, 1.75), cmats[i % 2], 0.03, parent=ship)
        if ch != " ":
            cu = bpy.data.curves.new(f"cl_{i}", "FONT")
            cu.body, cu.font, cu.size, cu.align_x, cu.align_y = ch, font, 0.8, "CENTER", "CENTER"
            ob = bpy.data.objects.new(f"cl_{i}", cu)
            scene.collection.objects.link(ob)
            ob.data.materials.append(lm)
            ob.location, ob.rotation_euler = (x, -1.17, 1.75), (math.pi / 2, 0, 0)
            ob.parent = ship
    lights = [G.area_light("key", "#b8c4ff", 700, 8, (-3, -9, 7), (0, 0, 1)),
              G.area_light("rim", G.PAL["accent"], 200, 3, (2, 5, 4), (0, 0, 1))]
    cam = G.camera(30)
    G.bloom(scene)
    s = SHOT[job["shot"]]
    t0, t1 = s["start_s"], s["end_s"]
    le = [(l, l.data.energy) for l in lights]

    def update(t):
        react(t, le, (), floor)
        ship.location = (0.6 * (t - t0), 0, 0.06 * math.sin(t * 1.3))
        ship.rotation_euler = (0.02 * math.sin(t * 1.1), 0, 0)
        cam_path(cam, t, t0, t1, (-1.5, -11.5, 1.6), (0.5, -10.5, 1.9), (0, 0, 1.5), (1.4, 0, 1.6))
    return update


def fit_vertical():
    """Fit every camera to the frame height (36 mm x 9/16), so a frame wider than 16:9 only adds margin at the sides
    and its centre 16:9 matches the 1920x1080 framing exactly (the C5 plates are 20% wider for the vertical cut)."""
    for c in bpy.data.cameras:
        c.sensor_fit = "VERTICAL"
        c.sensor_height = 36.0 * 9 / 16


PLATES = {
    "default_cube_boot": plate_default_cube_boot,
    "stream": plate_stream,
    "ship": plate_ship,
    "robot": plate_robot,
    "chorus": plate_chorus,
    "racks": plate_racks,
    "seats": plate_seats,
    "tear": plate_tear,
}


def render_job(index, out_root, width, height, samples, step):
    global OUT_ROOT
    OUT_ROOT = Path(out_root)
    job = SHOTS["render_jobs"][index]
    seed = seed_value(job["seed"])
    scene = G.reset(width, height, samples)
    strip_metadata(scene)
    update = PLATES[job["plate"]](job, seed)
    fit_vertical()
    out = Path(out_root) / job["dir"]
    out.mkdir(parents=True, exist_ok=True)
    s0 = job["start"] + job["lag_frames"]  # split renders: keep the step grid aligned with the shot's frames
    for f in range(job["start"], job["end"]):
        if (f - s0) % step or (out / f"{f:05d}.png").exists():  # resume: frames on disk are kept
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
        fit_vertical()
        update(t)
        scene.render.filepath = str(out / f"tile_{seed}.png")
        bpy.ops.render.render(write_still=True)
    print("TILES done")


def render_probe(index, out_dir, width, height, samples, frac):
    """One frame at a fraction of a job's range, for smoke tests (reads video frames from the animatic_v7 plates)."""
    global OUT_ROOT
    OUT_ROOT = ROOT / "renders" / "animatic_v7" / "plates"
    job = SHOTS["render_jobs"][index]
    scene = G.reset(width, height, samples)
    strip_metadata(scene)
    update = PLATES[job["plate"]](job, seed_value(job["seed"]))
    fit_vertical()
    f = job["start"] + int((job["end"] - job["start"]) * frac)
    update(f / FPS - job["clock_offset_s"])
    scene.render.filepath = str(Path(out_dir) / f"{job['shot']}_{index:02d}_{job['dir']}.png")
    bpy.ops.render.render(write_still=True)


def render_bench(index, out_dir, width, height, samples, n):
    """Time n consecutive frames from the middle of a job (scene build excluded), for render-time estimates."""
    import time
    global OUT_ROOT
    OUT_ROOT = ROOT / "renders" / "animatic_v8" / "plates"
    job = SHOTS["render_jobs"][index]
    scene = G.reset(width, height, samples)
    strip_metadata(scene)
    update = PLATES[job["plate"]](job, seed_value(job["seed"]))
    fit_vertical()
    f0 = (job["start"] + job["end"]) // 2
    times = []
    for f in range(f0, f0 + n):
        update(f / FPS - job["clock_offset_s"])
        scene.render.filepath = str(Path(out_dir) / f"{job['shot']}_{f:05d}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        times.append(time.time() - t0)
    print(f"BENCH {job['shot']} {job['dir']} {width}x{height} s{samples}: " + " ".join(f"{x:.2f}" for x in times))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "bench":
        render_bench(int(args[1]), args[2], int(args[3]), int(args[4]), int(args[5]), int(args[6]))
    elif args[0] == "probe":
        render_probe(int(args[1]), args[2], int(args[3]), int(args[4]), int(args[5]), float(args[6]))
    elif args[0] == "job":
        render_job(int(args[1]), args[2], int(args[3]), int(args[4]), int(args[5]), int(args[6]))
    elif args[0] == "tiles":
        render_tiles(args[1], int(args[2]), int(args[3]), int(args[4]), float(args[5]))


main()
