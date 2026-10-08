# Blender side of tools/standalone-terrain.py --mines: the ore mine (a resource spawn that regrows the ore around it).
#
#   blender -b --factory-startup -P tools/terrain/blender_oremine.py -- <job.json> <out.png> <threads>
#
# job.json: {"size": [W, H], "target": [x, y, z], "slots": [{"cx": .., "cy": .., "frame": 0-10}]}. Frame 0 is the
# idle mine; frames 1-10 are its "active" cycle: a burst of ore nuggets thrown out of the vent, rising and falling
# onto the slope. Same camera, light and shadow catcher as the ore piles (blender_resources.py), so the mine sits in
# the fields it feeds. Cell coordinates map like the terrain batches (cell x -> +X, cell y -> -Y).
import json
import math
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:]
job = json.load(open(argv[0]))
out_path, threads = argv[1], int(argv[2])
W, H = job["size"]
LEVEL = 1 / math.sqrt(6)
PX_PER_UNIT = 30 * math.sqrt(2)
ACTIVE = 10

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 128
scene.cycles.use_denoising = False
scene.render.threads_mode = "FIXED"
scene.render.threads = threads
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.film_transparent = True
scene.render.filter_size = 0.9
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.color_mode = "RGBA"


def material(name, base, rough, metal=0.0, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*[(c / 255) ** 2.2 for c in base], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emission:
        b.inputs["Emission Color"].default_value = (*[(c / 255) ** 2.2 for c in emission], 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


ROCK = material("rock", (98, 84, 68), 0.9)
ROCK_DARK = material("rock_dark", (58, 48, 40), 0.95)
ORE = [material("ore_a", (214, 168, 64), 0.35, 0.55), material("ore_b", (186, 132, 48), 0.45, 0.4)]
VENT = material("vent", (255, 196, 90), 0.5, 0.0, emission=(255, 170, 60), strength=1.6)


def add(bm, name, mat, smooth):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    scene.collection.objects.link(o)
    return o


def mound(c, rnd):
    """A low rocky cone with a crater: radius ~0.42 cells, ~1.6 height levels."""
    bm = bmesh.new()
    rings, segs = 9, 28
    radius, height, crater = 0.47, 1.15 * LEVEL, 0.19
    verts = []
    for i in range(rings + 1):
        t = i / rings                                  # 0 = crater lip, 1 = foot
        row = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            r = crater + (radius - crater) * t
            n = noise.noise(Vector((math.cos(a) * 2.3, math.sin(a) * 2.3, t * 3)))
            r *= 1 + 0.12 * n
            z = height * (1 - t * t) ** 0.9 * (1 + 0.12 * n)
            row.append(bm.verts.new((c.x + r * math.cos(a), c.y + r * math.sin(a), z)))
        verts.append(row)
    for i in range(rings):
        for j in range(segs):
            bm.faces.new((verts[i][j], verts[i][(j + 1) % segs], verts[i + 1][(j + 1) % segs], verts[i + 1][j]))
    # the crater floor, a little below the lip
    floor = [bm.verts.new((c.x + v.co.x - c.x, c.y + v.co.y - c.y, height * 0.72)) for v in verts[0]]
    for j in range(segs):
        bm.faces.new((verts[0][(j + 1) % segs], verts[0][j], floor[j], floor[(j + 1) % segs]))
    bm.faces.new(floor[::-1])
    add(bm, "mound", ROCK, True)
    # glowing ore in the vent
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=crater * 0.8)
    for v in bm.verts:
        v.co = Vector((v.co.x + c.x, v.co.y + c.y, v.co.z * 0.4 + height * 0.74))
    add(bm, "vent", VENT, True)
    return height


def nugget(c, r, rnd, mat, name):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * rnd.uniform(0.8, 1.25), v.co.y * rnd.uniform(0.8, 1.25), v.co.z * rnd.uniform(0.55, 0.9))) + c
    add(bm, name, mat, True)


for i, s in enumerate(job["slots"]):
    rnd = random.Random(1234)                      # the same mine in every frame
    c = Vector((s["cx"] + 0.5, -(s["cy"] + 0.5), 0))
    h = mound(c, rnd)
    # loose rocks and ore on the slopes
    for k in range(34):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0.2, 0.52)
        t = (d - 0.19) / (0.47 - 0.19)
        z = h * max(0.0, 1 - t * t) ** 0.9 * 0.97
        mat = ROCK_DARK if k % 4 == 0 else ORE[k % 2]
        nugget(c + Vector((d * math.cos(a), d * math.sin(a), z)), rnd.uniform(0.035, 0.06), rnd, mat, f"n{i}_{k}")
    # the burst: 6 nuggets thrown out of the vent along parabolas, one cycle over the active frames
    f = s["frame"]
    if f > 0:
        brnd = random.Random(99)
        for k in range(6):
            a = 2 * math.pi * k / 6 + brnd.uniform(-0.3, 0.3)
            reach = brnd.uniform(0.32, 0.5)
            peak = brnd.uniform(0.55, 0.85)
            phase = (f - 1 - k * 0.6) / (ACTIVE - 2)       # staggered launches
            if not 0 <= phase <= 1:
                continue
            p = c + Vector((reach * phase * math.cos(a), reach * phase * math.sin(a), h * 0.8 + 4 * peak * phase * (1 - phase) * h))
            nugget(p, 0.04, brnd, ORE[k % 2], f"b{i}_{k}")

bpy.ops.mesh.primitive_plane_add(size=1)
ground = bpy.context.active_object
xs = [s["cx"] for s in job["slots"]]
ys = [s["cy"] for s in job["slots"]]
ground.location = ((min(xs) + max(xs) + 1) / 2, -(min(ys) + max(ys) + 1) / 2, 0)
ground.scale = (max(xs) - min(xs) + 6, max(ys) - min(ys) + 6, 1)
ground.is_shadow_catcher = True

world = bpy.data.worlds.new("sky")
world.use_nodes = True
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
