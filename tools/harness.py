# Dev harness, not shipped in the extension. Run inside Blender while Blender
# Bites is active:  ns = {}; exec(open(path).read(), ns); ns["run_lesson"]("lesson03") For every bite: arm it, check FAILS, simulate
# the student's result, check PASSES. Mutates the scene like a real student.
import math
import time

import bmesh
import bpy

MOD = "bl_ext.user_default.blender_bites"
import sys
RN = sys.modules[MOD + ".runner"]
C = sys.modules[MOD + ".checks"]
LM = sys.modules[MOD + ".learnmode"]
R = RN.get()


def V():
    return LM.find_view3d()


def ov(**extra):
    win, area, region, _, _ = V()
    d = dict(window=win, screen=win.screen, area=area, region=region)
    d.update(extra)
    return d


def ck():
    return bool(C.run(R.bite["check"], R.snap, R.log))


def cube():
    return bpy.data.objects["Cube"]


def first(prefix, otype=None):
    for o in bpy.context.scene.objects:
        if o.name.startswith(prefix) and (otype is None or o.type == otype):
            return o
    return None


def of_type(t):
    return [o for o in bpy.context.scene.objects if o.type == t]


def space():
    return V()[3]


def rv3d():
    return V()[4]


def fake_op(idname, **props):
    R.log.records.append(dict(id=idname, **props))


def bm_edit():
    o = bpy.context.view_layer.objects.active
    bm = bmesh.from_edit_mesh(o.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return o, bm


def bm_done(o):
    bmesh.update_edit_mesh(o.data)


def top_face(bm):
    return max(bm.faces, key=lambda f: f.calc_center_median().z)


def sel(kind, n=1):
    o, bm = bm_edit()
    seq = {"v": bm.verts, "e": bm.edges, "f": bm.faces}[kind]
    for x in list(seq)[:n]:
        x.select = True
    bm_done(o)


def sel_top():
    o, bm = bm_edit()
    top_face(bm).select = True
    bm_done(o)


def extrude_top(dz=1.0):
    o, bm = bm_edit()
    f = top_face(bm)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    verts = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, dz))
    bmesh.ops.delete(bm, geom=[f], context='FACES')
    bm_done(o)


def inset_top():
    o, bm = bm_edit()
    bmesh.ops.inset_region(bm, faces=[top_face(bm)], thickness=0.1)
    bm_done(o)


def loopcut():
    o, bm = bm_edit()
    zs = [v.co.z for v in bm.verts]
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, (min(zs) + max(zs)) * 0.37), plane_no=(0, 0, 1))
    bm_done(o)


def bevel_edge():
    o, bm = bm_edit()
    e = bm.edges[0]
    bmesh.ops.bevel(bm, geom=[e, *e.verts], offset=0.1, segments=1, affect='EDGES')
    bm_done(o)


def merge_two():
    o, bm = bm_edit()
    e = bm.edges[0]
    a, b = e.verts
    bmesh.ops.pointmerge(bm, verts=[a, b], merge_co=(a.co + b.co) / 2)
    bm_done(o)


def delete_face():
    o, bm = bm_edit()
    bmesh.ops.delete(bm, geom=[bm.faces[0]], context='FACES_ONLY')
    bm_done(o)


def mode(m):
    RN._mode(m)


def selmode(v):
    bpy.context.scene.tool_settings.mesh_select_mode = v


def mat():
    return cube().active_material


def nt():
    return mat().node_tree


def node(t):
    return next(n for n in nt().nodes if n.type == t)


def add_node(bl_idname):
    return nt().nodes.new(bl_idname)


def principled():
    return node('BSDF_PRINCIPLED')


def new_area_light():
    ld = bpy.data.lights.new("Area", 'AREA')
    o = bpy.data.objects.new("Area", ld)
    bpy.context.scene.collection.objects.link(o)
    RN._select_only(o)
    return o


def cam():
    return bpy.context.scene.camera or of_type('CAMERA')[0]


def splice_ramp():
    noise = node('TEX_NOISE')
    ramp = add_node("ShaderNodeValToRGB")
    nt().links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    nt().links.new(ramp.outputs['Color'], principled().inputs['Base Color'])


def bump():
    b = add_node("ShaderNodeBump")
    nt().links.new(node('TEX_NOISE').outputs['Fac'], b.inputs['Height'])
    nt().links.new(b.outputs['Normal'], principled().inputs['Normal'])


def play(on):
    win = V()[0]
    with bpy.context.temp_override(window=win, screen=win.screen):
        if on and not win.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        elif not on and win.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)


def props_tab(ctx):
    a = C._root("area:PROPERTIES")
    a.spaces.active.context = ctx


def regions(**kw):
    LM._set_regions(V(), **kw)


def new_collection():
    s = first("Suzanne")
    col = bpy.data.collections.new("Props")
    bpy.context.scene.collection.children.link(col)
    for c in list(s.users_collection):
        c.objects.unlink(s)
    col.objects.link(s)


def parent_suzanne():
    s = first("Suzanne")
    mw = s.matrix_world.copy()
    s.parent = cube()
    s.matrix_world = mw


def S(*steps):
    return list(steps)


SIMS = {
    "lesson03": {
        "pick": S(lambda: RN._select_only(first("Suzanne"))),
        "rename": S(lambda: setattr(of_type('LIGHT')[0], "name", "Sun")),
        "eye": S(lambda: of_type('CAMERA')[0].hide_set(True)),
        "alt-h": S(lambda: [o.hide_set(False) for o in of_type('CAMERA')]),
        "parent": S(parent_suzanne),
        "ride": S(lambda: setattr(cube().location, "x", cube().location.x + 1.0), lambda: bpy.context.view_layer.update()),
        "collection": S(new_collection),
    },
    "lesson04": {
        "object-tab": S(lambda: setattr(cube().scale, "z", 2.0)),
        "reset": S(lambda: setattr(cube().scale, "z", 1.0)),
        "wrench": S(lambda: props_tab('MODIFIER')),
        "subsurf": S(lambda: cube().modifiers.new("Subdivision", 'SUBSURF')),
        "levels": S(lambda: setattr(cube().modifiers["Subdivision"], "levels", 3)),
        "shade-smooth": S(lambda: [setattr(p, "use_smooth", True) for p in cube().data.polygons]),
        "bevel": S(lambda: cube().modifiers.new("Bevel", 'BEVEL')),
        "reorder": S(lambda: cube().modifiers.move(1, 0)),
        "toggle": S(lambda: setattr(cube().modifiers["Subdivision"], "show_viewport", False),
                    lambda: setattr(cube().modifiers["Subdivision"], "show_viewport", True)),
    },
    "lesson05": {
        "tab": S(lambda: mode('EDIT')),
        "vert": S(lambda: selmode((True, False, False)), lambda: sel("v")),
        "dent": S(lambda: fake_op("TRANSFORM_OT_translate", constraint_axis=(False, False, False))),
        "edge": S(lambda: selmode((False, True, False)), lambda: sel("e")),
        "face": S(lambda: selmode((False, False, True)), lambda: sel_top()),
        "lift": S(lambda: fake_op("TRANSFORM_OT_translate", constraint_axis=(False, False, True), value=(0, 0, 1))),
        "all": S(lambda: sel("f", 6), lambda: (sel_none())),
        "xray-box": S(lambda: setattr(space().shading, "show_xray", True), lambda: sel("v", 4)),
        "tab-out": S(lambda: setattr(space().shading, "show_xray", False), lambda: mode('OBJECT')),
    },
    "lesson06": {
        "extrude": S(lambda: sel_top(), lambda: extrude_top(1.0)),
        "extrude-2": S(lambda: extrude_top(2.0)),
        "taper": S(lambda: fake_op("TRANSFORM_OT_resize", value=(0.5, 0.5, 0.5))),
        "inset": S(inset_top),
        "dig": S(lambda: extrude_top(-0.5)),
        "loopcut": S(loopcut),
        "bevel": S(bevel_edge),
        "merge": S(merge_two),
        "delete": S(delete_face),
        "tab-out": S(lambda: mode('OBJECT')),
    },
    "lesson07": {
        "array": S(lambda: cube().modifiers.new("Array", 'ARRAY')),
        "count": S(lambda: setattr(cube().modifiers["Array"], "count", 5)),
        "gap": S(lambda: cube().modifiers["Array"].relative_offset_displace.__setitem__(0, 1.5)),
        "grid": S(lambda: grid2()),
        "wire": S(lambda: cube().modifiers.new("Wireframe", 'WIREFRAME')),
        "edit-live": S(lambda: fake_op("TRANSFORM_OT_resize", value=(1.2, 1.2, 1.2))),
        "remove": S(lambda: cube().modifiers.remove(cube().modifiers["Wireframe"])),
        "apply": S(lambda: apply_first()),
    },
    "lesson08": {
        "preview": S(lambda: setattr(space().shading, "type", 'MATERIAL')),
        "new": S(lambda: cube().data.materials.append(bpy.data.materials.new("Material"))),
        "name": S(lambda: setattr(mat(), "name", "Clay")),
        "color": S(lambda: setattr(principled().inputs['Base Color'], "default_value", (0.9, 0.2, 0.1, 1))),
        "metal": S(lambda: setattr(principled().inputs['Metallic'], "default_value", 1.0)),
        "gloss": S(lambda: setattr(principled().inputs['Roughness'], "default_value", 0.1)),
        "slot": S(lambda: mode('EDIT'), lambda: second_slot()),
        "tab-out": S(lambda: mode('OBJECT')),
    },
    "lesson09": {
        "noise": S(lambda: add_node("ShaderNodeTexNoise")),
        "wire": S(lambda: nt().links.new(node('TEX_NOISE').outputs['Color'], principled().inputs['Base Color'])),
        "scale": S(lambda: setattr(node('TEX_NOISE').inputs['Scale'], "default_value", 20.0)),
        "ramp": S(splice_ramp),
        "ramp-color": S(lambda: setattr(node('VALTORGB').color_ramp.elements[0], "color", (0.1, 0.0, 0.3, 1))),
        "bump": S(bump),
    },
    "lesson10": {
        "rendered": S(lambda: setattr(space().shading, "type", 'RENDERED')),
        "area": S(new_area_light),
        "lift": S(lambda: setattr(first("Area", 'LIGHT').location, "z", 4.0)),
        "power": S(lambda: setattr(first("Area", 'LIGHT').data, "energy", 500.0)),
        "warm": S(lambda: setattr(first("Area", 'LIGHT').data, "color", (1.0, 0.6, 0.3))),
        "soft": S(lambda: setattr(first("Area", 'LIGHT').data, "size", 4.0)),
        "world": S(lambda: setattr(bpy.context.scene.world.node_tree.nodes['Background'].inputs['Strength'], "default_value", 0.2)),
    },
    "lesson11": {
        "look": S(lambda: setattr(rv3d(), "view_perspective", 'CAMERA')),
        "aim": S(lambda: setattr(cam().location, "x", cam().location.x + 0.5), lambda: bpy.context.view_layer.update()),
        "lens": S(lambda: setattr(cam().data, "lens", 85.0)),
        "lock": S(lambda: setattr(space(), "lock_camera", True)),
        "drive": S(lambda: setattr(cam().location, "y", cam().location.y + 0.5), lambda: bpy.context.view_layer.update(),
                   lambda: setattr(space(), "lock_camera", False)),
        "dof": S(lambda: setattr(cam().data.dof, "use_dof", True)),
    },
    "lesson12": {
        "engine": S(lambda: setattr(bpy.context.scene.render, "engine",
                                    'CYCLES' if bpy.context.scene.render.engine != 'CYCLES' else 'BLENDER_WORKBENCH')),
        "size": S(lambda: setattr(bpy.context.scene.render, "resolution_percentage", 50)),
        "f12": S(lambda: C._on_render_complete()),
    },
    "lesson13": {
        "key1": S(lambda: cube().keyframe_insert("location", frame=1)),
        "jump": S(lambda: bpy.context.scene.frame_set(40)),
        "key2": S(lambda: setattr(cube().location, "x", 3.0), lambda: cube().keyframe_insert("location", frame=40)),
        "play": S(lambda: play(True), lambda: play(False)),
        "scrub": S(lambda: bpy.context.scene.frame_set(12)),
        "spin": S(lambda: bpy.context.scene.frame_set(80), lambda: cube().keyframe_insert("rotation_euler", frame=80)),
    },
    "lesson14": {
        "save": S(lambda: C._on_save_post()),
    },
}


def sel_none():
    o, bm = bm_edit()
    for seq in (bm.verts, bm.edges, bm.faces):
        for x in seq:
            x.select = False
    bm_done(o)


def grid2():
    m = cube().modifiers.new("Array.001", 'ARRAY')
    m.relative_offset_displace = (0.0, 1.5, 0.0)


def apply_first():
    c = cube()
    with bpy.context.temp_override(**ov(active_object=c, object=c)):
        bpy.ops.object.modifier_apply(modifier=c.modifiers[0].name)


def second_slot():
    c = cube()
    c.data.materials.append(bpy.data.materials.new("Accent"))
    o, bm = bm_edit()
    bm.faces[0].material_index = 1
    bm_done(o)


def run_bite(lesson_id, i):
    R.goto(i)
    if R.pending:
        R._arm()
    b = R.bite
    if R.is_read():
        return (b["id"], "read")
    steps = SIMS.get(lesson_id, {}).get(b["id"])
    if steps is None:
        return (b["id"], "NO SIM")
    before = ck()
    res = False
    for step in steps:
        try:
            step()
        except Exception as e:
            return (b["id"], "SIM ERROR: %r" % e)
        res = ck()
    return (b["id"], "ok" if (not before and res) else ("PASSED EARLY" if before else "FAIL"))


def run_lesson(lesson_id, only=None):
    out = []
    for i, b in enumerate(R.lesson["bites"]):
        if only and b["id"] not in only:
            continue
        out.append(run_bite(lesson_id, i))
    return out
