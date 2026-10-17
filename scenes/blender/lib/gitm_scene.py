"""Shared scene building blocks for the plates: palette, materials, the averaged character, the void world.

Distilled from scenes/blender/c1_test_frame.py (the C1-approved look). Animation is applied per frame by the plate
functions in plates.py; nothing here is keyframed.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
TIMING = json.loads((ROOT / "timing" / "timing_map.json").read_text())
BEATS = TIMING["beats"]
DOWNBEATS = TIMING["downbeats"]
BAR = 4 * 60 / TIMING["tempo_bpm"]
# v3: per-frame music envelopes (scripts/stem_envelopes.py) and the robot's performance (shots/build_shots.py).
STEMS = json.loads((ROOT / "timing" / "stems.json").read_text())
PERF = json.loads((ROOT / "shots" / "shots.json").read_text()).get("performance", [])


def env(name, t):
    """A stem envelope (kick, synth, vocal) at time t, 0..1."""
    a = STEMS[name]
    f = int(round(t * STEMS["fps"]))
    return a[f] if 0 <= f < len(a) else 0.0


def mouth_levels(t):
    f = int(round(t * STEMS["fps"]))
    return [b[f] if 0 <= f < len(b) else 0.0 for b in STEMS["mouth"]]


def last_onset(times, t):
    prior = [x for x in times if x <= t]
    return prior[-1] if prior else None


def perf_at(kind, t):
    """The performance value (expression or gesture) active at t, the latest-listed winning, with its window."""
    hit = None
    for e in PERF:
        if e["kind"] == kind and e["t0"] <= t < e["t1"]:
            hit = e
    return hit

PAL = {  # style/style_spec.md palette, sRGB hex
    "base": "#09080b", "surface": "#1d1d24", "line": "#4a4550", "mid": "#847d77",
    "paper": "#e6e4dc", "accent": "#d9502f", "accent2": "#396ad3",
}


def lin(hexstr, a=1.0):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hexstr.lstrip("#")
    return (ch(int(h[0:2], 16)), ch(int(h[2:4], 16)), ch(int(h[4:6], 16)), a)


def ease(x):
    """The video's single easing curve (style spec): cubic ease-in-out."""
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def beat_pulse(t, decay=0.18, beats=None):
    """1 on each beat, decaying exponentially until the next."""
    prior = [b for b in (beats or BEATS) if b <= t]
    return math.exp(-(t - prior[-1]) / decay) if prior else 0.0


def bob(t, amp=0.04, period_bars=1.0, phase=0.0):
    """Uniform eased bob shared by every floating object (the 'same ease-in-out' joke)."""
    x = ((t / (BAR * period_bars)) + phase) % 1.0
    return amp * (ease(x * 2) if x < 0.5 else ease((1 - x) * 2))


# ---------- materials ----------

def mat_principled(name, color, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(color)
    b.inputs["Roughness"].default_value = rough
    return m


def mat_emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = lin(color)
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def emission_node(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "EMISSION")


def mat_image_screen(name, path, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def mat_grid_floor():
    """Base-colored floor with 1 m grid lines in --line, fading with distance from the origin."""
    m = bpy.data.materials.new("grid_floor")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    geo = N("ShaderNodeNewGeometry")
    sep = N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs[0])

    def line_mask(sock):
        fr = N("ShaderNodeMath"); fr.operation = "FRACT"; L(sock, fr.inputs[0])
        sub = N("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.5
        L(fr.outputs[0], sub.inputs[0])
        ab = N("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L(sub.outputs[0], ab.inputs[0])
        gt = N("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.49
        L(ab.outputs[0], gt.inputs[0])
        return gt.outputs[0]

    mx = N("ShaderNodeMath"); mx.operation = "MAXIMUM"
    L(line_mask(sep.outputs["X"]), mx.inputs[0]); L(line_mask(sep.outputs["Y"]), mx.inputs[1])
    vlen = N("ShaderNodeVectorMath"); vlen.operation = "LENGTH"; L(geo.outputs["Position"], vlen.inputs[0])
    fade = N("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = 3.0, 22.0
    fade.inputs["To Min"].default_value, fade.inputs["To Max"].default_value = 1.0, 0.0
    L(vlen.outputs["Value"], fade.inputs["Value"])
    amt = N("ShaderNodeMath"); amt.operation = "MULTIPLY"
    L(mx.outputs[0], amt.inputs[0]); L(fade.outputs["Result"], amt.inputs[1])
    amt2 = N("ShaderNodeMath"); amt2.operation = "MULTIPLY"; amt2.inputs[1].default_value = 0.4
    amt2.name = "grid_amount"
    L(amt.outputs[0], amt2.inputs[0])
    # Bass ripple: a ring of light travelling out from the origin (radius and amplitude set per frame).
    rr = N("ShaderNodeValue"); rr.name = "ripple_r"; rr.outputs[0].default_value = -10.0
    ra = N("ShaderNodeValue"); ra.name = "ripple_amp"; ra.outputs[0].default_value = 0.0
    d = N("ShaderNodeMath"); d.operation = "SUBTRACT"; L(vlen.outputs["Value"], d.inputs[0]); L(rr.outputs[0], d.inputs[1])
    dd = N("ShaderNodeMath"); dd.operation = "DIVIDE"; dd.inputs[1].default_value = 0.35; L(d.outputs[0], dd.inputs[0])
    sq = N("ShaderNodeMath"); sq.operation = "MULTIPLY"; L(dd.outputs[0], sq.inputs[0]); L(dd.outputs[0], sq.inputs[1])
    ng = N("ShaderNodeMath"); ng.operation = "MULTIPLY"; ng.inputs[1].default_value = -1.0; L(sq.outputs[0], ng.inputs[0])
    ex = N("ShaderNodeMath"); ex.operation = "EXPONENT"; L(ng.outputs[0], ex.inputs[0])
    ring = N("ShaderNodeMath"); ring.operation = "MULTIPLY"; L(ex.outputs[0], ring.inputs[0]); L(ra.outputs[0], ring.inputs[1])
    lines_and_ring = N("ShaderNodeMath"); lines_and_ring.operation = "MAXIMUM"
    L(amt2.outputs[0], lines_and_ring.inputs[0]); L(ring.outputs[0], lines_and_ring.inputs[1])
    floor_bsdf = N("ShaderNodeBsdfPrincipled")
    floor_bsdf.inputs["Base Color"].default_value = lin(PAL["base"])
    floor_bsdf.inputs["Roughness"].default_value = 0.35
    line_em = N("ShaderNodeEmission")
    line_em.inputs["Color"].default_value = lin(PAL["line"])
    line_em.inputs["Strength"].default_value = 2.5
    mix = N("ShaderNodeMixShader")
    L(lines_and_ring.outputs[0], mix.inputs[0]); L(floor_bsdf.outputs[0], mix.inputs[1]); L(line_em.outputs[0], mix.inputs[2])
    o = N("ShaderNodeOutputMaterial")
    L(mix.outputs[0], o.inputs[0])
    return m


# ---------- geometry ----------

def _finish(ob, name, mat, parent):
    ob.name = name
    if mat:
        ob.data.materials.append(mat)
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def rounded_box(name, size, loc, mat, bevel=0.06, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = size
    # Apply the scale only: the defaults also bake location/rotation, leaving every origin at the world origin.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = bevel, 4
    bpy.ops.object.shade_smooth()
    return _finish(ob, name, mat, parent)


def capsule(name, radius, length, loc, mat, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=loc, rotation=rot, vertices=24)
    ob = bpy.context.object
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = radius * 0.9, 6
    bpy.ops.object.shade_smooth()
    return _finish(ob, name, mat, parent)


def plane(name, size, loc, rot, mat, parent=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = (size[0], size[1], 1)
    return _finish(ob, name, mat, parent)


def empty(name, loc, parent=None):
    ob = bpy.data.objects.new(name, None)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------- the character (style spec) ----------

def build_character(origin=(0, 0, 0), height_scale=1.0):
    """Faceless primitive humanoid. Returns its rig: root, head pivot, shoulder pivots, eye objects, face."""
    ox, oy, oz = origin
    body = mat_principled("body", PAL["mid"], 0.55)
    joint = mat_principled("joint", PAL["line"], 0.5)
    screen = mat_emission("screen_face", PAL["surface"], 0.6)
    eye = mat_emission("eyes", PAL["accent"], 12.0)
    root = empty("char_root", (ox, oy, oz))
    root.scale = (height_scale,) * 3
    bpy.context.view_layer.update()
    rounded_box("torso", (0.62, 0.38, 0.72), (ox, oy, oz + 1.12), body, 0.12, parent=root)
    rounded_box("pelvis", (0.5, 0.32, 0.18), (ox, oy, oz + 0.70), joint, 0.06, parent=root)
    shoulders = {}
    for side in (-1, 1):
        capsule(f"leg_{side}", 0.11, 0.66, (ox + side * 0.15, oy, oz + 0.33), body, parent=root)
        sh = empty(f"shoulder_{side}", (ox + side * 0.43, oy, oz + 1.38), parent=root)
        capsule(f"arm_{side}", 0.085, 0.62, (ox + side * 0.43, oy, oz + 1.08), body, rot=(0, side * 0.12, 0), parent=sh)
        shoulders[side] = sh
    capsule("neck", 0.07, 0.12, (ox, oy, oz + 1.53), joint, parent=root)
    head = empty("head_pivot", (ox, oy, oz + 1.58), parent=root)
    rounded_box("head", (0.56, 0.44, 0.40), (ox, oy, oz + 1.80), body, 0.12, parent=head)
    face = rounded_box("face", (0.46, 0.02, 0.30), (ox, oy - 0.225, oz + 1.80), screen, 0.008, parent=head)
    eyes = [rounded_box(f"eye_{side}", (0.07, 0.01, 0.11), (ox + side * 0.1, oy - 0.238, oz + 1.82), eye, 0.03,
                        parent=head) for side in (-1, 1)]
    # Eye expressions (v3), drawn as glyphs on the screen face; one set is visible at a time.
    fy, ez = oy - 0.24, oz + 1.82
    bar = lambda name, x, z, w, h, rot: rounded_box(name, (w, 0.008, h), (x, fy, z), eye, 0.004, rot=(0, rot, 0), parent=head)
    sets = {"normal": eyes, "happy": [], "squint": [], "sleepy": [], "xx": [], "heart": []}
    for side in (-1, 1):
        x = ox + side * 0.1
        sets["happy"] += [bar(f"eyeh_{side}_a", x - 0.018, ez, 0.05, 0.014, 0.75), bar(f"eyeh_{side}_b", x + 0.018, ez, 0.05, 0.014, -0.75)]
        tip = 0.75 if side < 0 else -0.75  # ">" on the left eye, "<" on the right
        sets["squint"] += [bar(f"eyes_{side}_a", x, ez + 0.017, 0.06, 0.014, tip), bar(f"eyes_{side}_b", x, ez - 0.017, 0.06, 0.014, -tip)]
        sets["sleepy"] += [bar(f"eyez_{side}", x, ez - 0.02, 0.08, 0.014, 0.0)]
        sets["xx"] += [bar(f"eyex_{side}_a", x, ez, 0.08, 0.014, 0.785), bar(f"eyex_{side}_b", x, ez, 0.08, 0.014, -0.785)]
        sets["heart"] += [bar(f"eyeheart_{side}_a", x - 0.014, ez + 0.006, 0.045, 0.03, 0.785),
                          bar(f"eyeheart_{side}_b", x + 0.014, ez + 0.006, 0.045, 0.03, -0.785)]
    # Equalizer mouth: five bars driven by the lead vocal (v3).
    mouth = [rounded_box(f"mouth_{i}", (0.022, 0.008, 0.012), (ox + (i - 2) * 0.04, fy, oz + 1.715), eye, 0.003,
                         parent=head) for i in range(5)]
    return {"root": root, "head": head, "shoulders": shoulders, "eyes": eyes, "face": face, "eye_sets": sets,
            "mouth": mouth, "rest": {"root": Vector(root.location), "head_rot": head.rotation_euler.copy()}}


def perform(rig, t, default_expr="normal", sing=True):
    """Apply the performance at time t: expression glyphs, the singing mouth, and gestures (eased in and out)."""
    for sh in rig["shoulders"].values():
        sh.rotation_euler = (0.0, 0.0, 0.0)
    e = perf_at("expr", t)
    expr = e["value"] if e else default_expr
    for name, objs in rig["eye_sets"].items():
        for o in objs:
            o.hide_render = name != expr
    levels = mouth_levels(t) if sing else [0.0] * 5
    for bar_ob, lv in zip(rig["mouth"], levels):
        bar_ob.scale.z = 0.4 + 5.0 * lv
    g = perf_at("gesture", t)
    if g:
        k = ease((t - g["t0"]) / 0.25) * (1 - ease((t - (g["t1"] - 0.25)) / 0.25))
        for side, sh in rig["shoulders"].items():
            if g["value"] == "point" and side > 0:
                sh.rotation_euler.x = -1.45 * k   # arm straight out toward the camera
            if g["value"] == "reach_up":
                sh.rotation_euler.y = -side * 2.6 * k


# ---------- world, lights, camera, compositor ----------

def reset(width, height, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = samples
    scene.eevee.use_shadows = True
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.view_settings.view_transform = "Standard"  # keep palette hex values faithful
    scene.render.image_settings.file_format = "PNG"
    return scene


def void_world(scene, haze=0.004):
    w = bpy.data.worlds.new("void")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = lin(PAL["base"])
    if haze:
        vol = w.node_tree.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = haze
        w.node_tree.links.new(vol.outputs[0], w.node_tree.nodes["World Output"].inputs["Volume"])
    return w


def grid_floor():
    return plane("floor", (80, 80), (0, 0, 0), (0, 0, 0), mat_grid_floor())


def area_light(name, color, energy, size, loc, target):
    lt = bpy.data.lights.new(name, "AREA")
    lt.energy, lt.size = energy, size
    lt.color = lin(color)[:3]
    ob = bpy.data.objects.new(name, lt)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    look_at(ob, target)
    return ob


def standard_lights(target=(0, 0, 1.2)):
    tx, ty, tz = target
    key = area_light("key", "#b8c4ff", 600, 4, (tx - 4.4, ty - 4, 5), target)
    rim = area_light("rim", PAL["accent"], 160, 1.0, (tx + 1.2, ty + 1.6, 2.4), target)
    return key, rim


def camera(lens=35):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.clip_start = 0.05
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def bloom(scene, strength=0.6):
    ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Quality"].default_value = "Medium"
    glare.inputs["Threshold"].default_value = 0.8
    glare.inputs["Strength"].default_value = strength
    glare.inputs["Size"].default_value = 0.6
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs[0], out.inputs[0])
    scene.compositing_node_group = ng
