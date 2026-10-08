# Blender batch script: the main-menu backdrop, one flagship vehicle per faction at golden hour.
#   blender -b --factory-startup -noaudio -P tools/menu/blender_lineup.py -- <job.json>
# The job (written by tools/standalone-menu.py) lists the GLBs, their placement and the render settings.
# Everything in the frame is ours: the vehicles are the project's own GLB meshes (RTSAI-Art), the ground, hills and
# sky are procedural.
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- render settings
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = job["samples"]
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.threads_mode = "FIXED"
scene.render.threads = job["threads"]
scene.render.resolution_x, scene.render.resolution_y = job["width"], job["height"]
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Punchy"
scene.view_settings.exposure = job.get("exposure", 0.0)

HAZE = job["haze_color"]


def add_haze(mat, scale):
    """Aerial perspective: blend each surface toward the horizon colour with camera distance."""
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if out is None or not out.inputs["Surface"].links:
        return
    src = out.inputs["Surface"].links[0].from_socket
    cam = nt.nodes.new("ShaderNodeCameraData")
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = -1.0 / scale
    nt.links.new(cam.outputs["View Distance"], k.inputs[0])
    e = nt.nodes.new("ShaderNodeMath")
    e.operation = "EXPONENT"
    nt.links.new(k.outputs[0], e.inputs[0])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "SUBTRACT"
    f.inputs[0].default_value = 1.0
    nt.links.new(e.outputs[0], f.inputs[1])
    c = nt.nodes.new("ShaderNodeMath")
    c.operation = "MINIMUM"
    c.inputs[1].default_value = job["haze_max"]
    nt.links.new(f.outputs[0], c.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*HAZE, 1.0)
    em.inputs["Strength"].default_value = job["haze_strength"]
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(c.outputs[0], mix.inputs[0])
    nt.links.new(src, mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


# ---------------------------------------------------------------- vehicles
for v in job["vehicles"]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=v["glb"])
    new = [o for o in bpy.data.objects if o not in before]
    rig = bpy.data.objects.new(v["name"], None)
    scene.collection.objects.link(rig)
    for o in new:
        if o.parent is None:
            o.parent = rig
    meshes = [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    length = max(p.y for p in pts) - min(p.y for p in pts)     # the GLBs are 1 unit long, forward -Y
    s = v["length_m"] / length
    zmin = min(p.z for p in pts)
    rig.scale = (s, s, s)
    rig.rotation_euler = (0.0, 0.0, math.radians(v["yaw_deg"]))
    rig.location = (v["x"], v["y"], -zmin * s - v.get("sink_m", 0.0))
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if m and not m.get("hazed"):
                m["hazed"] = True
                bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf is not None:
                    bsdf.inputs["Roughness"].default_value = max(0.45, bsdf.inputs["Roughness"].default_value)
                add_haze(m, job["haze_distance"])

# ---------------------------------------------------------------- ground: flat pad under the vehicles, dunes, far ridges
g = job["ground"]
n = g["cells"]
half = g["half_size"]
xs = np.linspace(-half, half, n + 1)
X, Y = np.meshgrid(xs + g["centre"][0], xs + g["centre"][1])
rng = np.random.default_rng(7)
H = np.zeros_like(X)
for amp, wl in g["dunes"]:                    # sum of oriented sines: soft dune ripples
    for _ in range(3):
        a = rng.uniform(0, math.pi)
        ph = rng.uniform(0, 2 * math.pi)
        H += amp / 3 * np.sin((X * math.cos(a) + Y * math.sin(a)) * 2 * math.pi / wl + ph)
pad = np.hypot(X - g["pad"][0], (Y - g["pad"][1]) * 0.8)
w = np.clip((pad - g["pad_radius"]) / g["pad_falloff"], 0, 1)
w = w * w * (3 - 2 * w)
dist = np.hypot(X - job["camera"]["location"][0], Y - job["camera"]["location"][1])
ridge = np.clip((dist - g["ridge_start"]) / g["ridge_falloff"], 0, 1) ** 1.5
R = np.zeros_like(X)
for amp, wl in g["ridges"]:
    a = rng.uniform(0, math.pi)
    R += amp * (0.5 + 0.5 * np.sin((X * math.cos(a) + Y * math.sin(a)) * 2 * math.pi / wl + rng.uniform(0, 6.3)))
H = H * w + R * ridge
step = 2 * half / n


def ground_h(x, y):
    fx, fy = (x - (g["centre"][0] - half)) / step, (y - (g["centre"][1] - half)) / step
    i, j = int(fx), int(fy)
    u, v = fx - i, fy - j
    return ((1 - u) * (1 - v) * H[j, i] + u * (1 - v) * H[j, i + 1] + (1 - u) * v * H[j + 1, i] + u * v * H[j + 1, i + 1])


verts = np.stack([X.ravel(), Y.ravel(), H.ravel()], 1)
idx = np.arange((n + 1) * (n + 1)).reshape(n + 1, n + 1)
faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
me = bpy.data.meshes.new("ground")
me.from_pydata(verts.tolist(), [], faces.tolist())
me.update()
for p in me.polygons:
    p.use_smooth = True
ground = bpy.data.objects.new("ground", me)
scene.collection.objects.link(ground)

gm = bpy.data.materials.new("ground")
gm.use_nodes = True
nt = gm.node_tree
bsdf = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord")
big = nt.nodes.new("ShaderNodeTexNoise")
big.inputs["Scale"].default_value = g["tint_scale"]
big.inputs["Detail"].default_value = 4.0
nt.links.new(tc.outputs["Object"], big.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.35
ramp.color_ramp.elements[0].color = (*g["sand_dark"], 1)
ramp.color_ramp.elements[1].position = 0.7
ramp.color_ramp.elements[1].color = (*g["sand_light"], 1)
nt.links.new(big.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.95
fine = nt.nodes.new("ShaderNodeTexNoise")
fine.inputs["Scale"].default_value = g["grain_scale"]
fine.inputs["Detail"].default_value = 6.0
nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.35
bump.inputs["Distance"].default_value = 0.05
nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
ground.data.materials.append(gm)
add_haze(gm, job["haze_distance"])

# ---------------------------------------------------------------- scatter: rocks and dry shrubs, clear of the vehicles
sc = job.get("scatter")
if sc:
    srng = np.random.default_rng(11)

    def material(name, color, rough):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1)
        b.inputs["Roughness"].default_value = rough
        add_haze(m, job["haze_distance"])
        return m

    rock_mat = material("rock", sc["rock_color"], 0.9)
    shrub_mat = material("shrub", sc["shrub_color"], 1.0)

    def lump(name, subdiv, jitter, mat, parts, smooth):
        bm_verts, bm_faces = [], []
        for (cx, cy, cz), r in parts:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1.0)
            tmp = bpy.context.object
            off = len(bm_verts)
            for vtx in tmp.data.vertices:
                k = 1.0 + srng.uniform(-jitter, jitter)
                bm_verts.append((cx + vtx.co.x * r * k, cy + vtx.co.y * r * k, cz + vtx.co.z * r * k * 0.7))
            bm_faces += [[off + i for i in p.vertices] for p in tmp.data.polygons]
            bpy.data.objects.remove(tmp, do_unlink=True)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(bm_verts, [], bm_faces)
        for poly in mesh.polygons:
            poly.use_smooth = smooth
        mesh.materials.append(mat)
        return mesh

    rocks = [lump(f"rock{i}", 2, 0.3, rock_mat, [((0, 0, 0), 1.0)], False) for i in range(6)]
    shrubs = [lump(f"shrub{i}", 2, 0.35, shrub_mat,
                   [((srng.uniform(-0.6, 0.6), srng.uniform(-0.6, 0.6), srng.uniform(0, 0.3)), srng.uniform(0.35, 0.6))
                    for _ in range(5)], True) for i in range(4)]
    occupied = [(v["x"], v["y"]) for v in job["vehicles"]]
    placed = 0
    for kind, meshes, count, (smin, smax) in (("rock", rocks, sc["rocks"], sc["rock_size"]),
                                              ("shrub", shrubs, sc["shrubs"], sc["shrub_size"])):
        made = 0
        while made < count:
            y = sc["near"] + (sc["far"] - sc["near"]) * srng.random() ** 1.6
            x = srng.uniform(-1, 1) * y * sc["spread"]
            if min(math.hypot(x - ox, y - oy) for ox, oy in occupied) < sc["clearance"]:
                continue
            o = bpy.data.objects.new(f"{kind}{made}", meshes[made % len(meshes)])
            scene.collection.objects.link(o)
            s = srng.uniform(smin, smax)
            o.scale = (s * srng.uniform(0.8, 1.3), s * srng.uniform(0.8, 1.3), s)
            o.rotation_euler = (0, 0, srng.uniform(0, 6.3))
            o.location = (x, y, ground_h(x, y) - (0.25 * s if kind == "rock" else 0.05))
            made += 1
        placed += made
    print("scatter", placed)

# ---------------------------------------------------------------- sky: gradient by elevation plus a glow toward the sun
sky = job["sky"]
world = bpy.data.worlds.new("sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
wtc = wn.nodes.new("ShaderNodeTexCoord")
sep = wn.nodes.new("ShaderNodeSeparateXYZ")
nt_link = wn.links.new
nt_link(wtc.outputs["Generated"], sep.inputs[0])
wr = wn.nodes.new("ShaderNodeValToRGB")
els = wr.color_ramp.elements
stops = sky["stops"]                        # [elevation z, [r,g,b]] with z in [-1, 1] mapped to [0, 1]
els[0].position, els[0].color = (stops[0][0] + 1) / 2, (*stops[0][1], 1)
els[1].position, els[1].color = (stops[1][0] + 1) / 2, (*stops[1][1], 1)
for z, col in stops[2:]:
    e = els.new((z + 1) / 2)
    e.color = (*col, 1)
mapz = wn.nodes.new("ShaderNodeMath")
mapz.operation = "MULTIPLY_ADD"
mapz.inputs[1].default_value = 0.5
mapz.inputs[2].default_value = 0.5
nt_link(sep.outputs["Z"], mapz.inputs[0])
nt_link(mapz.outputs[0], wr.inputs["Fac"])
az, el = math.radians(job["sun"]["azimuth_deg"]), math.radians(job["sun"]["elevation_deg"])
sun_dir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
dot = wn.nodes.new("ShaderNodeVectorMath")
dot.operation = "DOT_PRODUCT"
dot.inputs[1].default_value = sun_dir
nt_link(wtc.outputs["Generated"], dot.inputs[0])
glow = wn.nodes.new("ShaderNodeMath")
glow.operation = "POWER"
clampd = wn.nodes.new("ShaderNodeMath")
clampd.operation = "MAXIMUM"
clampd.inputs[1].default_value = 0.0
nt_link(dot.outputs["Value"], clampd.inputs[0])
nt_link(clampd.outputs[0], glow.inputs[0])
glow.inputs[1].default_value = sky["glow_power"]
gmul = wn.nodes.new("ShaderNodeMath")
gmul.operation = "MULTIPLY"
gmul.inputs[1].default_value = sky["glow_strength"]
nt_link(glow.outputs[0], gmul.inputs[0])
gmix = wn.nodes.new("ShaderNodeMix")
gmix.data_type = "RGBA"
gmix.blend_type = "ADD"
nt_link(gmul.outputs[0], gmix.inputs["Factor"])
nt_link(wr.outputs["Color"], gmix.inputs["A"])
gmix.inputs["B"].default_value = (*sky["glow_color"], 1)
nt_link(gmix.outputs["Result"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = sky["strength"]

# ---------------------------------------------------------------- sun
sd = bpy.data.lights.new("sun", "SUN")
sd.energy = job["sun"]["strength"]
sd.color = job["sun"]["color"]
sd.angle = math.radians(job["sun"]["angle_deg"])
sun = bpy.data.objects.new("sun", sd)
scene.collection.objects.link(sun)
sun.rotation_euler = (-sun_dir).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- camera
c = job["camera"]
cd = bpy.data.cameras.new("cam")
cd.lens = c["lens_mm"]
cd.sensor_width = 36.0
cd.clip_end = 5000.0
cd.shift_x, cd.shift_y = c.get("shift", [0.0, 0.0])
cam = bpy.data.objects.new("cam", cd)
scene.collection.objects.link(cam)
cam.location = c["location"]
cam.rotation_euler = (Vector(c["target"]) - Vector(c["location"])).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

scene.render.filepath = job["out"]
bpy.ops.render.render(write_still=True)
print("LINEUP_DONE", job["out"])
