# Blender side of tools/standalone-terrain.py --trees: the trees of the temperate maps (tree01-tree28 share them).
#
#   blender -b --factory-startup -P tools/terrain/blender_trees.py -- <job.json> <out.png> <threads>
#
# job.json: {"size": [W, H], "target": [x, y, z], "samples": n, "slots": [{"cx": .., "cy": .., "kind": .., "scale": ..,
# "seed": ..}]}. Each slot is one tree standing on its cell centre. Broadleaf crowns are clumps of noisy leaf puffs,
# pines are stacked jagged tiers, bushes are low puffs. Same camera, sun and shadow catcher as the ore mine
# (blender_oremine.py), so the trees sit in the same light as the terrain and ore. Cell coordinates map like the
# terrain batches (cell x -> +X, cell y -> -Y); 1 Blender unit is one cell.
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
PX_PER_UNIT = 30 * math.sqrt(2)

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = job.get("samples", 128)
scene.cycles.use_denoising = False
scene.render.threads_mode = "FIXED"
scene.render.threads = threads
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.film_transparent = True
scene.render.filter_size = 0.9
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.color_mode = "RGBA"


def lin(c):
    return (*[(v / 255) ** 2.2 for v in c], 1)


def foliage(name, dark, light, scale=9.0):
    """Leaf material: a noise texture mixes two greens, so a crown reads as many leaf clusters, not one blob."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.85
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.38, 0.66
    ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[1].color = lin(dark), lin(light)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def plain(name, base, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(base)
    b.inputs["Roughness"].default_value = rough
    return m


LEAVES = [foliage("oak", (26, 50, 18), (70, 104, 34)), foliage("elm", (34, 58, 20), (88, 116, 38)),
          foliage("birch", (58, 90, 30), (128, 152, 60), 12.0)]
NEEDLES = foliage("pine", (18, 40, 24), (50, 80, 42), 14.0)
BUSH = foliage("bush", (32, 58, 22), (86, 110, 40), 16.0)
BARK = plain("bark", (78, 58, 40), 0.9)
BIRCH_BARK = plain("birch_bark", (196, 190, 172), 0.8)


def add(bm, name, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    scene.collection.objects.link(o)
    return o


def trunk(base, height, r0, r1, lean, mat, name):
    """A tapered, slightly bent trunk from `base` (ground) up `height`."""
    bm = bmesh.new()
    rings, segs = 6, 10
    rows = []
    for i in range(rings + 1):
        t = i / rings
        r = r0 + (r1 - r0) * t
        off = lean * t * t
        rows.append([bm.verts.new((base.x + off.x + r * math.cos(2 * math.pi * j / segs),
                                   base.y + off.y + r * math.sin(2 * math.pi * j / segs), base.z + height * t)) for j in range(segs)])
    for i in range(rings):
        for j in range(segs):
            bm.faces.new((rows[i][j], rows[i][(j + 1) % segs], rows[i + 1][(j + 1) % segs], rows[i + 1][j]))
    bm.faces.new(rows[-1])
    add(bm, name, mat)
    return base + lean + Vector((0, 0, height))


def puff(c, r, rnd, mat, name, squash=0.85, rough=0.32):
    """A leaf clump: an icosphere pushed in and out by fractal noise, so its silhouette is ragged like foliage."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    o = Vector((rnd.uniform(0, 100), rnd.uniform(0, 100), rnd.uniform(0, 100)))
    for v in bm.verts:
        n = v.co.normalized()
        d = noise.fractal(n * 2.6 + o, 0.6, 2.0, 4)
        v.co = n * r * (1 + rough * d)
        v.co.z *= squash
        v.co += c
    add(bm, name, mat)


def broadleaf(c, s, rnd, i, birch=False, wide=False):
    leaves = LEAVES[2] if birch else LEAVES[rnd.randrange(2)]
    height = (0.42 if birch else 0.36) * s
    top = trunk(c, height, 0.055 * s, 0.035 * s, Vector((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), 0)) * s,
                BIRCH_BARK if birch else BARK, f"t{i}")
    crown = top + Vector((0, 0, 0.28 * s))
    rx, rz = (0.46 if wide else 0.36) * s, (0.30 if birch else 0.34) * s
    puff(crown, 0.27 * s, rnd, leaves, f"c{i}", 0.9)
    clumps = 13 if wide else 11
    for k in range(clumps):
        a = 2 * math.pi * k / clumps + rnd.uniform(-0.3, 0.3)
        e = rnd.uniform(-0.35, 0.75)
        p = crown + Vector((math.cos(a) * rx * math.cos(e), math.sin(a) * rx * math.cos(e), math.sin(e) * rz))
        puff(p, rnd.uniform(0.15, 0.22) * s, rnd, leaves, f"c{i}_{k}")
    if birch:
        puff(crown + Vector((0, 0, 0.3 * s)), 0.17 * s, rnd, leaves, f"c{i}_top")


def pine(c, s, rnd, i):
    trunk(c, 0.3 * s, 0.05 * s, 0.03 * s, Vector((0, 0, 0)), BARK, f"t{i}")
    tiers = 5
    for k in range(tiers):
        t = k / (tiers - 1)
        z0 = (0.18 + 0.27 * k) * s
        r = (0.40 - 0.24 * t) * s
        h = (0.42 - 0.12 * t) * s
        bm = bmesh.new()
        apex = bm.verts.new((c.x, c.y, c.z + z0 + h))
        points = 18
        rim = []
        for j in range(points):
            a = 2 * math.pi * j / points + k * 0.4
            rr = r * (1.0 if j % 2 == 0 else 0.72) * rnd.uniform(0.9, 1.08)
            droop = (0.0 if j % 2 == 0 else 0.05 * s)
            rim.append(bm.verts.new((c.x + rr * math.cos(a), c.y + rr * math.sin(a), c.z + z0 + droop)))
        for j in range(points):
            bm.faces.new((apex, rim[j], rim[(j + 1) % points]))
        bm.faces.new(rim[::-1])
        add(bm, f"p{i}_{k}", NEEDLES, smooth=False)


def bush(c, s, rnd, i):
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.4, 0.4)
        d = rnd.uniform(0.08, 0.2) * s
        r = rnd.uniform(0.14, 0.2) * s
        puff(c + Vector((d * math.cos(a), d * math.sin(a), r * 0.7)), r, rnd, BUSH, f"b{i}_{k}", 0.75, 0.4)


for i, slot in enumerate(job["slots"]):
    rnd = random.Random(slot["seed"])
    c = Vector((slot["cx"] + 0.5, -(slot["cy"] + 0.5), 0))
    kind, s = slot["kind"], slot["scale"]
    if kind == "broadleaf":
        broadleaf(c, s, rnd, i)
    elif kind == "wide":
        broadleaf(c, s, rnd, i, wide=True)
    elif kind == "birch":
        broadleaf(c, s, rnd, i, birch=True)
    elif kind == "pine":
        pine(c, s, rnd, i)
    else:
        bush(c, s, rnd, i)

bpy.ops.mesh.primitive_plane_add(size=1)
ground = bpy.context.active_object
xs = [s["cx"] for s in job["slots"]]
ys = [s["cy"] for s in job["slots"]]
ground.location = ((min(xs) + max(xs) + 1) / 2, -(min(ys) + max(ys) + 1) / 2, 0)
ground.scale = (max(xs) - min(xs) + 8, max(ys) - min(ys) + 8, 1)
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
