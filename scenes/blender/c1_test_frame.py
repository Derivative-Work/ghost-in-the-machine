"""C1 test frame: the averaged look from style/style_spec.md in one still (S02 framing).

Dark void, faint perspective grid floor, faceless primitive humanoid with a screen face, two floating UI screens
textured with Puppeteer renders, accent rim light, compositor bloom. Deterministic (no random calls).

Usage: blender -b --factory-startup --python scenes/blender/c1_test_frame.py -- <panel_dir> <out.png> [scale%]
"""
import math
import sys

import bpy
from mathutils import Vector

panel_dir, out_path = sys.argv[sys.argv.index("--") + 1:][:2]
scale = int(sys.argv[sys.argv.index("--") + 3]) if len(sys.argv) > sys.argv.index("--") + 3 else 100

PAL = {  # style_spec.md palette, sRGB hex
    "base": "#09080b", "surface": "#1d1d24", "line": "#4a4550", "mid": "#847d77",
    "paper": "#e6e4dc", "accent": "#d9502f", "accent2": "#396ad3",
}


def lin(hexstr, a=1.0):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hexstr.lstrip("#")
    return (ch(int(h[0:2], 16)), ch(int(h[2:4], 16)), ch(int(h[4:6], 16)), a)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


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


def mat_image_screen(name, path, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def mat_grid_floor():
    """Base-colored floor with thin grid lines in --line that fade toward the horizon."""
    m = bpy.data.materials.new("grid_floor")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    geo = N("ShaderNodeNewGeometry")  # world-space position: 1 m grid regardless of plane scale
    sep = N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs[0])

    def line_mask(sock):
        fr = N("ShaderNodeMath"); fr.operation = "FRACT"
        L(sock, fr.inputs[0])
        sub = N("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.5
        L(fr.outputs[0], sub.inputs[0])
        ab = N("ShaderNodeMath"); ab.operation = "ABSOLUTE"
        L(sub.outputs[0], ab.inputs[0])
        gt = N("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.49
        L(ab.outputs[0], gt.inputs[0])
        return gt.outputs[0]

    mx = N("ShaderNodeMath"); mx.operation = "MAXIMUM"
    L(line_mask(sep.outputs["X"]), mx.inputs[0])
    L(line_mask(sep.outputs["Y"]), mx.inputs[1])
    # Fade by distance from the character's spot: 1 near, 0 at ~22 m.
    vlen = N("ShaderNodeVectorMath"); vlen.operation = "LENGTH"
    L(geo.outputs["Position"], vlen.inputs[0])
    fade = N("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = 3.0
    fade.inputs["From Max"].default_value = 22.0
    fade.inputs["To Min"].default_value = 1.0
    fade.inputs["To Max"].default_value = 0.0
    L(vlen.outputs["Value"], fade.inputs["Value"])
    amt = N("ShaderNodeMath"); amt.operation = "MULTIPLY"
    L(mx.outputs[0], amt.inputs[0]); L(fade.outputs["Result"], amt.inputs[1])
    amt2 = N("ShaderNodeMath"); amt2.operation = "MULTIPLY"; amt2.inputs[1].default_value = 0.4
    L(amt.outputs[0], amt2.inputs[0])
    floor_bsdf = N("ShaderNodeBsdfPrincipled")
    floor_bsdf.inputs["Base Color"].default_value = lin(PAL["base"])
    floor_bsdf.inputs["Roughness"].default_value = 0.35
    line_em = N("ShaderNodeEmission")
    line_em.inputs["Color"].default_value = lin(PAL["line"])
    line_em.inputs["Strength"].default_value = 2.5
    mix = N("ShaderNodeMixShader")
    L(amt2.outputs[0], mix.inputs[0]); L(floor_bsdf.outputs[0], mix.inputs[1]); L(line_em.outputs[0], mix.inputs[2])
    o = N("ShaderNodeOutputMaterial")
    L(mix.outputs[0], o.inputs[0])
    return m


def rounded_box(name, size, loc, mat, bevel=0.06, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = bevel, 4
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def capsule(name, radius, length, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=loc, rotation=rot, vertices=24)
    ob = bpy.context.object
    ob.name = name
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = radius * 0.9, 6
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def plane(name, size, loc, rot, mat):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (size[0], size[1], 1)
    ob.data.materials.append(mat)
    return ob


def build_character(origin):
    """Faceless primitive humanoid: matte mid-grey body, rounded-box head with a dark screen face and accent glyph eyes."""
    ox, oy, oz = origin
    body = mat_principled("body", PAL["mid"], 0.55)
    joint = mat_principled("joint", PAL["line"], 0.5)
    screen = mat_emission("screen_face", PAL["surface"], 0.6)
    eye = mat_emission("eyes", PAL["accent"], 12.0)
    rounded_box("torso", (0.62, 0.38, 0.72), (ox, oy, oz + 1.12), body, 0.12)
    rounded_box("pelvis", (0.5, 0.32, 0.18), (ox, oy, oz + 0.70), joint, 0.06)
    for side in (-1, 1):
        capsule(f"leg_{side}", 0.11, 0.66, (ox + side * 0.15, oy, oz + 0.33), body)
        capsule(f"arm_{side}", 0.085, 0.62, (ox + side * 0.43, oy, oz + 1.08), body, rot=(0, side * 0.12, 0))
    capsule("neck", 0.07, 0.12, (ox, oy, oz + 1.53), joint)
    rounded_box("head", (0.56, 0.44, 0.40), (ox, oy, oz + 1.80), body, 0.12)
    # Screen face sits on the head's front (-Y) side.
    rounded_box("face", (0.46, 0.02, 0.30), (ox, oy - 0.225, oz + 1.80), screen, 0.008)
    for side in (-1, 1):
        rounded_box(f"eye_{side}", (0.07, 0.01, 0.11), (ox + side * 0.1, oy - 0.238, oz + 1.82), eye, 0.03)


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_world(scene):
    w = bpy.data.worlds.new("void")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = lin(PAL["base"])
    bg.inputs["Strength"].default_value = 1.0
    # Faint haze so the screens and rim light read as volumes.
    vol = w.node_tree.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.004
    w.node_tree.links.new(vol.outputs[0], w.node_tree.nodes["World Output"].inputs["Volume"])


def setup_compositor(scene):
    ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 0.8
    glare.inputs["Strength"].default_value = 0.6
    glare.inputs["Size"].default_value = 0.6
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs[0], out.inputs[0])
    scene.compositing_node_group = ng


def main():
    scene = reset()
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_shadows = True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = scale
    scene.render.fps = 30
    scene.view_settings.view_transform = "Standard"  # keep palette hex values faithful
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = out_path

    setup_world(scene)
    floor = plane("floor", (80, 80), (0, 0, 0), (0, 0, 0), mat_grid_floor())
    build_character((1.4, 0.0, 0.0))

    consent = mat_image_screen("consent", f"{panel_dir}/panel_consent.png", 1.6)
    counter = mat_image_screen("counter", f"{panel_dir}/panel_counter.png", 1.4)
    # 1200x700 textures -> 1.714:1 planes, standing up and angled toward camera.
    plane("screen_consent", (2.4, 1.4), (-1.6, 3.2, 2.6), (math.radians(90), 0, math.radians(14)), consent)
    plane("screen_counter", (2.1, 1.225), (5.2, 4.6, 2.4), (math.radians(90), 0, math.radians(-24)), counter)

    key = bpy.data.lights.new("key", "AREA")
    key.energy, key.size = 600, 4
    key.color = lin("#b8c4ff")[:3]
    ko = bpy.data.objects.new("key", key)
    ko.location = (-3, -4, 5)
    scene.collection.objects.link(ko)
    look_at(ko, (1.4, 0, 1.2))
    rim = bpy.data.lights.new("rim", "AREA")
    rim.energy, rim.size = 160, 1.0
    rim.color = lin(PAL["accent"])[:3]
    ro = bpy.data.objects.new("rim", rim)
    ro.location = (2.6, 1.6, 2.4)
    scene.collection.objects.link(ro)
    look_at(ro, (1.4, 0, 1.3))

    cam = bpy.data.cameras.new("cam")
    cam.lens = 35
    co = bpy.data.objects.new("cam", cam)
    co.location = (-0.6, -6.2, 0.75)
    scene.collection.objects.link(co)
    look_at(co, (0.9, 0.5, 1.45))
    scene.camera = co

    setup_compositor(scene)
    bpy.ops.render.render(write_still=True)


main()
