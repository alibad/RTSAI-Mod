# Blender side of tools/standalone-terrain.py --resources: ore nuggets and gem crystals on single cells.
#
#   blender -b --factory-startup -P tools/terrain/blender_resources.py -- <job.json> <out.png> <threads>
#
# job.json: {"size": [W, H], "target": [x, y, z], "slots": [{"kind": "ore"|"gem", "cx": .., "cy": .., "density": 1-12,
# "seed": n}]}. Cell coordinates map to Blender like the terrain batches (cell x -> +X, cell y -> -Y). A shadow-catcher
# ground plane bakes each pile's shadow into the frame; everything else is transparent.
import json
import math
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
job = json.load(open(argv[0]))
out_path, threads = argv[1], int(argv[2])
W, H = job["size"]
LEVEL = 1 / math.sqrt(6)
PX_PER_UNIT = 30 * math.sqrt(2)

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 96
scene.cycles.use_denoising = False
scene.render.threads_mode = "FIXED"
scene.render.threads = threads
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.film_transparent = True
scene.render.filter_size = 0.9
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.color_mode = "RGBA"


def material(name, base, rough, metal=0.0, emission=None, transmission=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*[(c / 255) ** 2.2 for c in base], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if emission:
        b.inputs["Emission Color"].default_value = (*[(c / 255) ** 2.2 for c in emission], 1)
        b.inputs["Emission Strength"].default_value = 0.35
    return m


ORE = [material("ore_a", (214, 168, 64), 0.35, 0.55), material("ore_b", (186, 132, 48), 0.45, 0.4),
       material("ore_rock", (104, 90, 72), 0.85)]
GEM = [material("gem_a", (150, 92, 214), 0.12, 0.0, emission=(120, 70, 200)),
       material("gem_b", (88, 128, 236), 0.12, 0.0, emission=(70, 110, 220)),
       material("gem_rock", (92, 86, 98), 0.8)]


def nugget(bm, center, r, rnd):
    geom = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
    verts = geom["verts"]
    for v in verts:
        v.co = Vector((v.co.x * rnd.uniform(0.8, 1.25), v.co.y * rnd.uniform(0.8, 1.25), v.co.z * rnd.uniform(0.55, 0.9)))
        v.co += center
    return verts


def crystal(bm, center, r, h, rnd):
    geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=5, radius1=r, radius2=0.0, depth=h)
    tilt = Matrix.Rotation(rnd.uniform(-0.45, 0.45), 4, "X") @ Matrix.Rotation(rnd.uniform(-0.45, 0.45), 4, "Y")
    for v in geom["verts"]:
        v.co = tilt @ (v.co + Vector((0, 0, h / 2))) + center
    return geom["verts"]


for i, s in enumerate(job["slots"]):
    rnd = random.Random(s["seed"])
    ore = s["kind"] == "ore"
    mats = ORE if ore else GEM
    n = (3 + s["density"] * 3) if ore else (1 + s["density"])
    pieces = []
    for k in range(n):
        u, v = rnd.uniform(0.18, 0.82), rnd.uniform(0.18, 0.82)
        c = Vector((s["cx"] + u, -(s["cy"] + v), 0))
        bm = bmesh.new()
        if ore:
            nugget(bm, c, rnd.uniform(0.05, 0.075 + 0.004 * s["density"]), rnd)
            mat = mats[0] if k % 3 else mats[1]
            if rnd.random() < 0.18:
                mat = mats[2]
        else:
            crystal(bm, c, rnd.uniform(0.045, 0.07), rnd.uniform(0.12, 0.2 + 0.012 * s["density"]), rnd)
            mat = mats[k % 2] if rnd.random() > 0.12 else mats[2]
        me = bpy.data.meshes.new(f"p{i}_{k}")
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = ore
        o = bpy.data.objects.new(me.name, me)
        o.data.materials.append(mat)
        scene.collection.objects.link(o)

# shadow catcher ground under all slots
bpy.ops.mesh.primitive_plane_add(size=1)
ground = bpy.context.active_object
xs = [s["cx"] for s in job["slots"]]
ys = [s["cy"] for s in job["slots"]]
ground.location = ((min(xs) + max(xs) + 1) / 2, -(min(ys) + max(ys) + 1) / 2, 0)
ground.scale = (max(xs) - min(xs) + 4, max(ys) - min(ys) + 4, 1)
ground.is_shadow_catcher = True

world = bpy.data.worlds.new("sky")
try:
    world.use_nodes = True
except AttributeError:
    pass
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.70, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
scene.world = world
sun_data = bpy.data.lights.new("sun", type="SUN")
sun_data.energy = 3.6
sun_data.angle = 0.06
sun = bpy.data.objects.new("sun", sun_data)
sun.matrix_world = Matrix.Translation((0, 0, 50)) @ Vector((-0.55, -0.15, 0.82)).to_track_quat("Z", "Y").to_matrix().to_4x4()
scene.collection.objects.link(sun)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.sensor_fit = "HORIZONTAL"
cam_data.ortho_scale = W / PX_PER_UNIT
cam_data.clip_end = 1000
cam = bpy.data.objects.new("cam", cam_data)
xc = Vector((0.70710678, 0.70710678, 0))
yc = Vector((-0.35355339, 0.35355339, 0.8660254))
zc = Vector((0.61237244, -0.61237244, 0.5))
m = Matrix((xc, yc, zc)).transposed().to_4x4()
m.translation = Vector(job["target"]) + zc * 200
cam.matrix_world = m
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
