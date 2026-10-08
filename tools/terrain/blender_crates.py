# Blender side of tools/standalone-terrain.py --crates: the bonus crate on land and afloat.
#
#   blender -b --factory-startup -P tools/terrain/blender_crates.py -- <job.json> <out.png> <threads>
#
# job.json: {"size": [W, H], "target": [x, y, z], "slots": [{"cx": .., "cy": .., "kind": "land"|"water"}]}. A military
# supply case (olive steel, darker bands, pale stencil panel on the lid, corner guards); afloat it rides an orange
# flotation collar. Same camera and light as the ore piles and the ore mine (blender_resources.py); the land crate
# bakes its shadow on a shadow catcher, the water crate casts none (the water layer has no catcher).
import json
import math
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
scene.cycles.samples = 128
scene.cycles.use_denoising = False
scene.render.threads_mode = "FIXED"
scene.render.threads = threads
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.film_transparent = True
scene.render.filter_size = 0.9
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.color_mode = "RGBA"


def material(name, base, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*[(c / 255) ** 2.2 for c in base], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


OLIVE = material("olive", (92, 98, 64), 0.6, 0.15)
BAND = material("band", (58, 62, 42), 0.55, 0.3)
STENCIL = material("stencil", (176, 168, 128), 0.75)
STEEL = material("steel", (150, 150, 146), 0.35, 0.8)
FLOAT = material("float", (232, 112, 36), 0.5)


def box(name, center, size, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    scene.collection.objects.link(o)
    return o


def crate(c, lift):
    """c: centre of the crate's footprint on the ground (Blender units, z = 0)."""
    sx, sy, sz = 0.46, 0.34, 1.15 * LEVEL          # a case about half a cell long
    z0 = lift + sz / 2
    box("body", (c.x, c.y, z0), (sx, sy, sz), OLIVE)
    for t in (-0.3, 0.3):                           # two strap bands around the case
        box("band", (c.x + t * sx, c.y, z0), (0.05, sy + 0.012, sz + 0.012), BAND)
    box("lid", (c.x, c.y, lift + sz + 0.01), (sx * 0.45, sy * 0.55, 0.02), STENCIL)     # stencil panel
    for dx in (-1, 1):                              # steel corner guards
        for dy in (-1, 1):
            box("corner", (c.x + dx * sx / 2, c.y + dy * sy / 2, z0), (0.05, 0.05, sz + 0.02), STEEL)


for i, s in enumerate(job["slots"]):
    c = Vector((s["cx"] + 0.5, -(s["cy"] + 0.5), 0))
    if s["kind"] == "water":
        bpy.ops.mesh.primitive_torus_add(major_radius=0.32, minor_radius=0.07, location=(c.x, c.y, 0.03))
        ring = bpy.context.active_object
        ring.scale = (1.0, 0.85, 1.0)
        ring.data.materials.append(FLOAT)
        crate(c, 0.02)
    else:
        crate(c, 0.0)

land = [s for s in job["slots"] if s["kind"] == "land"]
if land:
    bpy.ops.mesh.primitive_plane_add(size=1)
    ground = bpy.context.active_object
    ground.location = (land[0]["cx"] + 0.5, -(land[0]["cy"] + 0.5), 0)
    ground.scale = (3, 3, 1)
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
