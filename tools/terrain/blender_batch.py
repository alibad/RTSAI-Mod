# Blender side of tools/standalone-terrain.py: render one batch of terrain templates.
#
#   blender -b --factory-startup -P tools/terrain/blender_batch.py -- <batch.npz> <out.png> <threads>
#
# The batch file holds everything already laid out by the driver: vertices in Blender units (cell x -> +X, cell y ->
# -Y, one height level = 1/sqrt(6)), triangles, per-vertex material weights (one column per material class), the
# camera target and the image size. This script only builds one mesh, the procedural materials, a sun and sky, and
# renders on the CPU. Every material is node-generated here: no image textures, no external assets.
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
batch_path, out_path, threads = argv[0], argv[1], int(argv[2])
d = np.load(batch_path)
verts, tris, weights = d["verts"], d["tris"], d["weights"]
W, H = int(d["size"][0]), int(d["size"][1])
target = Vector(d["target"].tolist())
classes = [str(c) for c in d["classes"]]
seed = int(d["seed"][0])

PX_PER_UNIT = 30 * 2 ** 0.5   # one cell edge (1 unit along X) projects to 30 px across the screen

# ------------------------------------------------------------------------------------------------ scene
scene = bpy.context.scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(d["samples"][0]) if "samples" in d else 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = False   # the denoiser smears the fine detail at 1x
scene.cycles.max_bounces = 3
scene.cycles.seed = seed
scene.render.threads_mode = "FIXED"
scene.render.threads = threads
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.filter_size = 0.9
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0

# ------------------------------------------------------------------------------------------------ mesh
# Skirts (geometry past each template's border, only there so border pixels sample terrain) overlap each other at
# corners: they live in their own object that casts no shadow, otherwise the overlaps self-shadow into black specks.
skirt = d["skirt"] if "skirt" in d else np.zeros(len(tris), bool)
objs = []
for name, sel in (("terrain", ~skirt), ("skirts", skirt)):
    if not sel.any():
        continue
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [], tris[sel].tolist())
    mesh.update()
    for i, c in enumerate(classes):
        a = mesh.attributes.new(name="w_" + c, type="FLOAT", domain="POINT")
        a.data.foreach_set("value", weights[:, i].astype(np.float32))
    o = bpy.data.objects.new(name, mesh)
    if name == "skirts":
        o.visible_shadow = False
    scene.collection.objects.link(o)
    objs.append(o)
obj = objs[0]

# ------------------------------------------------------------------------------------------------ materials
mat = bpy.data.materials.new("terrain")
try:
    mat.use_nodes = True
except AttributeError:
    pass
nt = mat.node_tree
N, L = nt.nodes, nt.links
for n in list(N):
    N.remove(n)


def node(kind, **kw):
    n = N.new(kind)
    for k, v in kw.items():
        if k == "inputs":
            for name, val in v.items():
                n.inputs[name].default_value = val
        else:
            setattr(n, k, v)
    return n


geo = node("ShaderNodeNewGeometry")
pos = geo.outputs["Position"]


def noise(scale, detail=4.0, rough=0.55, distortion=0.0, offset=(0, 0, 0)):
    m = node("ShaderNodeVectorMath", operation="ADD")
    m.inputs[1].default_value = offset
    L.new(pos, m.inputs[0])
    t = node("ShaderNodeTexNoise", inputs={"Scale": scale, "Detail": detail, "Roughness": rough, "Distortion": distortion})
    L.new(m.outputs[0], t.inputs["Vector"])
    return t.outputs["Fac"]


def voronoi(scale, feature="F1", offset=(0, 0, 0)):
    m = node("ShaderNodeVectorMath", operation="ADD")
    m.inputs[1].default_value = offset
    L.new(pos, m.inputs[0])
    t = node("ShaderNodeTexVoronoi", feature=feature, inputs={"Scale": scale})
    L.new(m.outputs[0], t.inputs["Vector"])
    return t.outputs["Distance"]


def ramp(fac, stops):
    r = node("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    for p, c in stops[1:]:
        e = els.new(p)
        e.color = (*c, 1)
    L.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def sock(sockets, name, kind):
    return next(s for s in sockets if s.name == name and s.type == kind)


def mix(a, b, fac, blend="MIX"):
    m = node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
    f = sock(m.inputs, "Factor", "VALUE")
    if isinstance(fac, (int, float)):
        f.default_value = fac
    else:
        L.new(fac, f)
    for name, val in (("A", a), ("B", b)):
        s = sock(m.inputs, name, "RGBA")
        if isinstance(val, tuple):
            s.default_value = (*val, 1)
        else:
            L.new(val, s)
    return sock(m.outputs, "Result", "RGBA")


def math(op, a, b=None, clamp=False):
    m = node("ShaderNodeMath", operation=op, use_clamp=clamp)
    for i, v in enumerate([a, b]):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            L.new(v, m.inputs[i])
    return m.outputs[0]


def srgb(c):
    return tuple(((x / 255) ** 2.2) for x in c)


# Each class: albedo socket + bump height socket + roughness. Colours are authored for this project (warm,
# saturated, readable at 1x like a classic isometric RTS, but drawn from scratch here).
classes_out = {}
o1, o2, o3 = (11.3, 4.7, 0), (-7.1, 13.9, 0), (3.3, -9.2, 0)

g_big = noise(1.6, 3, 0.5, offset=o1)
g_mid = noise(7.0, 6, 0.6, offset=o2)
g_fine = noise(46.0, 3, 0.65, offset=o3)
grass = ramp(g_mid, [(0.25, srgb((58, 92, 34))), (0.55, srgb((84, 124, 48))), (0.85, srgb((110, 146, 62)))])
grass = mix(grass, ramp(g_big, [(0.3, srgb((70, 98, 36))), (0.7, srgb((104, 132, 52)))]), 0.35)
tufts = math("GREATER_THAN", g_fine, 0.6)
grass = mix(grass, srgb((40, 66, 24)), math("MULTIPLY", tufts, 0.6))
blades = math("GREATER_THAN", noise(90.0, 1, 0.5, offset=(2.5, 0.5, 0)), 0.64)
grass = mix(grass, srgb((136, 166, 76)), math("MULTIPLY", blades, 0.45))
classes_out["grass"] = (grass, math("ADD", math("MULTIPLY", g_fine, 0.9), math("MULTIPLY", blades, 0.4)), 0.85)

dirt_n = noise(5.5, 5, 0.6, offset=(1.7, 2.9, 0))
dirt = ramp(dirt_n, [(0.3, srgb((112, 86, 56))), (0.7, srgb((146, 116, 78)))])
pebble = math("LESS_THAN", voronoi(26, offset=(5.5, 1.1, 0)), 0.11)
dirt_p = mix(dirt, srgb((96, 88, 80)), math("MULTIPLY", pebble, 0.8))
classes_out["dirt"] = (dirt_p, math("ADD", math("MULTIPLY", g_fine, 0.4), math("MULTIPLY", pebble, 0.5)), 0.95)

patch = math("GREATER_THAN", noise(4.0, 4, 0.6, offset=(9.1, 0.4, 0)), 0.52)
rough = mix(grass, dirt_p, math("MULTIPLY", patch, 0.85))
rough = mix(rough, srgb((120, 112, 98)), math("MULTIPLY", math("LESS_THAN", voronoi(14, offset=(2.2, 7.7, 0)), 0.09), 0.9))
classes_out["rough"] = (rough, math("ADD", math("MULTIPLY", g_fine, 0.5), math("MULTIPLY", patch, 0.3)), 0.9)

sand_n = noise(9.0, 3, 0.5, offset=(4.4, 4.4, 0))
sand = ramp(sand_n, [(0.3, srgb((188, 164, 116))), (0.7, srgb((214, 192, 142)))])
classes_out["sand"] = (sand, math("MULTIPLY", sand_n, 0.25), 0.9)

pave_n = noise(16.0, 4, 0.6, offset=(0.9, 6.6, 0))
pave = ramp(pave_n, [(0.3, srgb((88, 88, 90))), (0.7, srgb((112, 112, 114)))])
crack = math("LESS_THAN", voronoi(6, "DISTANCE_TO_EDGE", offset=(3.1, 3.1, 0)), 0.025)
pave = mix(pave, srgb((60, 60, 62)), math("MULTIPLY", crack, 0.7))
classes_out["pave"] = (pave, math("MULTIPLY", pave_n, 0.2), 0.8)

water_n = noise(3.0, 4, 0.55, offset=(7.7, 1.3, 0))
water = ramp(water_n, [(0.3, srgb((30, 66, 104))), (0.7, srgb((44, 90, 132)))])
glint = math("GREATER_THAN", noise(22.0, 2, 0.5, offset=(6.0, 6.0, 0)), 0.66)
water = mix(water, srgb((92, 140, 176)), math("MULTIPLY", glint, 0.35))
classes_out["water"] = (water, math("MULTIPLY", water_n, 0.08), 0.35)

rock_n = noise(5.0, 8, 0.65, distortion=0.4, offset=(2.0, 8.0, 0))
strata = node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", inputs={"Scale": 6.0, "Distortion": 3.0})
L.new(pos, strata.inputs["Vector"])
rock = ramp(rock_n, [(0.2, srgb((70, 60, 52))), (0.5, srgb((124, 108, 90))), (0.8, srgb((170, 154, 132)))])
rock = mix(rock, srgb((56, 48, 42)), math("MULTIPLY", math("GREATER_THAN", strata.outputs["Fac"], 0.6), 0.6))
cracks = math("LESS_THAN", voronoi(9, "DISTANCE_TO_EDGE", offset=(4.4, 2.2, 0)), 0.03)
rock = mix(rock, srgb((40, 34, 30)), math("MULTIPLY", cracks, 0.8))
classes_out["rock"] = (rock, math("ADD", rock_n, math("MULTIPLY", strata.outputs["Fac"], 0.3)), 0.95)

rubble = mix(rock, dirt_p, math("GREATER_THAN", noise(7, 4, 0.6, offset=(1.0, 1.0, 0)), 0.5))
classes_out["rubble"] = (rubble, math("MULTIPLY", rock_n, 0.8), 0.95)

gravel = ramp(noise(30, 3, 0.6, offset=(3.0, 3.0, 0)), [(0.3, srgb((92, 88, 82))), (0.7, srgb((128, 122, 112)))])
classes_out["gravel"] = (gravel, math("MULTIPLY", g_fine, 0.5), 0.95)

# Weighted sum of the classes by the per-vertex weights.
color = None
height = None
roughness = None
for c in classes:
    attr = node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="w_" + c)
    w = attr.outputs["Fac"]
    col, h, r = classes_out[c]
    term = mix((0, 0, 0), col, w)
    color = term if color is None else mix(color, term, 1.0, blend="ADD")
    hh = math("MULTIPLY", h, w)
    height = hh if height is None else math("ADD", height, hh)
    rr = math("MULTIPLY", w, r)
    roughness = rr if roughness is None else math("ADD", roughness, rr)

# Beaches: a sand band where water meets land, from the water weight itself.
w_water = node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="w_water").outputs["Fac"]
band = math("MULTIPLY", math("MULTIPLY", w_water, math("SUBTRACT", 1.0, w_water)), 4.0, clamp=True)
band = math("POWER", band, 1.5)
color = mix(color, classes_out["sand"][0], math("MULTIPLY", band, 0.85))

bump = node("ShaderNodeBump", inputs={"Strength": 0.6, "Distance": 0.02})
L.new(height, bump.inputs["Height"])
bsdf = node("ShaderNodeBsdfPrincipled", inputs={"Specular IOR Level": 0.25})
L.new(color, bsdf.inputs["Base Color"])
L.new(roughness, bsdf.inputs["Roughness"])
L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
outp = node("ShaderNodeOutputMaterial")
L.new(bsdf.outputs["BSDF"], outp.inputs["Surface"])
for o in objs:
    o.data.materials.append(mat)

# ------------------------------------------------------------------------------------------------ light
world = bpy.data.worlds.new("sky")
try:
    world.use_nodes = True
except AttributeError:
    pass
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.62, 0.70, 0.82, 1)
bg.inputs["Strength"].default_value = 0.55
scene.world = world

sun_data = bpy.data.lights.new("sun", type="SUN")
sun_data.energy = 3.6
sun_data.angle = 0.06
sun_data.color = (1.0, 0.96, 0.88)
sun = bpy.data.objects.new("sun", sun_data)
# Light from the screen's upper left: cell -x is screen up-left; Blender (-X), high in the sky.
sun.matrix_world = Matrix.Translation((0, 0, 50)) @ Vector((-0.55, -0.15, 0.82)).to_track_quat("Z", "Y").to_matrix().to_4x4()
scene.collection.objects.link(sun)

# ------------------------------------------------------------------------------------------------ camera
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.sensor_fit = "HORIZONTAL"
cam_data.ortho_scale = W / PX_PER_UNIT
cam_data.clip_start = 0.1
cam_data.clip_end = 1000
cam = bpy.data.objects.new("cam", cam_data)
xc = Vector((0.70710678, 0.70710678, 0))
yc = Vector((-0.35355339, 0.35355339, 0.8660254))
zc = Vector((0.61237244, -0.61237244, 0.5))
rot = Matrix((xc, yc, zc)).transposed()
m = rot.to_4x4()
m.translation = target + zc * 200
cam.matrix_world = m
scene.collection.objects.link(cam)
scene.camera = cam

scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
