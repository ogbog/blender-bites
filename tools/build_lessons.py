"""Source of truth for Blender Bites lessons 03 to 14.

Run from the repo root:  python tools/build_lessons.py
Writes blender_bites/content/lessonNN.json and index.json. Lessons 00 to 02 are
hand-written JSON already in blender_bites/content/.
"""
import json
from pathlib import Path

CONTENT = Path(__file__).resolve().parent.parent / "blender_bites" / "content"
READ = {"type": "read"}
F, T = False, True


def B(id, title, body, check=READ, hint=None, setup=None, praise=None, unlock=None, hint_after=None):
    b = {"id": id, "title": title, "body": body}
    if setup:
        b["setup"] = setup
    if unlock:
        b["unlock"] = unlock
    b["check"] = check
    if hint:
        b["hint"] = hint
    if hint_after:
        b["hint_after"] = hint_after
    if praise:
        b["praise"] = praise
    return b


def obj(path, value=None, op="eq", **kw):
    d = {"type": "object", "path": path, "op": op}
    if value is not None:
        d["value"] = value
    d.update(kw)
    return d


def prop(root, path, value=None, op="eq", **kw):
    d = {"type": "prop", "root": root, "path": path, "op": op}
    if value is not None:
        d["value"] = value
    d.update(kw)
    return d


def mesh(what, op="ge", value=1, rel=False, obj_name="Cube"):
    d = {"type": "mesh", "object": obj_name, "what": what, "op": op, "value": value}
    if rel:
        d["rel"] = True
    return d


def mod(mod_type, **props):
    d = {"type": "modifier", "object": "Cube", "mod_type": mod_type}
    if props:
        d["props"] = props
    return d


def seq(*checks):
    return {"type": "seq", "checks": list(checks)}


def all_(*checks):
    return {"type": "all", "checks": list(checks)}


def not_(check):
    return {"type": "not", "check": check}


def ge(v):
    return {"op": "ge", "value": v}


def le(v):
    return {"op": "le", "value": v}


PBSDF = "active_material.node_tree.nodes['Principled BSDF'].inputs"
BASE = ["header", "toolbar"]
LOCK_TAB = [{"type": "TAB", "say": "Tab (Edit Mode) unlocks in Lesson 05. Hold that thought."}]

LESSONS = []

# ---------------------------------------------------------------- 03
LESSONS.append({
    "id": "lesson03", "title": "Lesson 03: Organizing",
    "unlocked": BASE + ["outliner"], "locked": LOCK_TAB,
    "bites": [
        B("welcome", "The table of contents",
          "That panel on the right is the Outliner. It lists every object in your scene, even the ones you can't see. Think of it as the cast list.",
          setup=["object_mode", "unhide_all", "ensure_light", "ensure_camera", "ensure_suzanne",
                 {"do": "clear_parent", "prefix": "Suzanne"}, "select_cube", "reset_view"]),
        B("pick", "Point at a name",
          "Click Suzanne's name in the Outliner. She lights up in the viewport too. Two views, one selection.",
          {"type": "selected", "prefix": "Suzanne"},
          hint="Find the row with a little triangle icon named Suzanne and click the name.",
          setup=["select_cube"], praise="Same monkey, two windows."),
        B("rename", "Name things",
          "Double-click the Light's name in the Outliner, type Sun, press Enter. Good names are a gift to future you.",
          {"type": "added", "any": True, "object_type": "LIGHT"},
          hint="Double-click the name text itself, not the icon. Or select it and press F2 over the viewport.",
          praise="Future you says thanks."),
        B("eye", "Now you see it",
          "Click the eye icon on the Camera's row. It vanishes from the viewport but it's still in the scene, just napping.",
          obj("hide_get()", True, any=True, object_type="CAMERA"),
          hint="Right edge of the Camera row: the little eye.", setup=["unhide_all"]),
        B("alt-h", "Bring them all back",
          "Hover the viewport and press Alt+H. Everything hidden comes back at once. (H alone hides whatever is selected.)",
          not_(obj("hide_get()", True, any=True, object_type="CAMERA")),
          setup=[{"do": "hide", "object_type": "CAMERA"}], praise="Welcome back, camera."),
        B("parent", "Family tree",
          "Click Suzanne, then Shift+click the cube so the cube is selected last. Press Ctrl+P and choose Object. The last one you click becomes the parent.",
          obj("parent.name", "Cube", prefix="Suzanne"),
          hint="Order matters: Suzanne first, cube last (it gets the brighter outline). Then Ctrl+P, Object.",
          setup=[{"do": "clear_parent", "prefix": "Suzanne"}, {"do": "select", "prefix": "Suzanne"}],
          hint_after=20, praise="It's a family now."),
        B("ride", "Along for the ride",
          "Select just the cube and grab it with G. Suzanne rides along, because children follow their parents.",
          all_({"type": "moved", "object": "Cube", "distance": 0.5},
               {"type": "moved", "prefix": "Suzanne", "distance": 0.5}),
          setup=["select_cube"], praise="Piggyback ride."),
        B("tree", "Read the tree",
          "Look at the Outliner: Suzanne now lives indented under Cube. Click the little arrow beside Cube to fold and unfold the family."),
        B("collection", "Boxes for things",
          "Select Suzanne, hover the viewport, press M, choose + New Collection, call it Props, click OK. Collections are folders for objects.",
          obj("users_collection[0].name", op="changed", prefix="Suzanne"),
          hint="M opens Move to Collection. The + New Collection item is at the bottom.",
          setup=[{"do": "select", "prefix": "Suzanne"}], hint_after=20, praise="Filed under Props."),
        B("cleared", "Lesson 03: cleared",
          "You can find, rename, hide, parent, and file things. Big scenes won't scare you now.\n\nReward: the Properties editor just slid in under the Outliner. Every setting in Blender lives in there. Scroll on for Lesson 04.",
          unlock=["properties"]),
    ]})

# ---------------------------------------------------------------- 04
LESSONS.append({
    "id": "lesson04", "title": "Lesson 04: Properties",
    "unlocked": BASE + ["outliner", "properties"], "locked": LOCK_TAB,
    "bites": [
        B("welcome", "The control room",
          "The Properties editor is a filing cabinet. Each icon down its left edge opens a drawer: render, output, scene, world, object, modifiers, materials and more. Hover any icon and press F1.",
          setup=["fresh_cube", "reset_view", {"do": "shading", "value": "SOLID"}]),
        B("object-tab", "The object drawer",
          "Click the orange square tab (Object). Under Transform, set Scale Z to 2. Same numbers as the N sidebar, bigger cabinet.",
          obj("scale.z", 2, op="approx", tol=0.001, object="Cube"),
          hint="Properties editor, orange square icon, Transform, Scale, the Z field. Double-click and type 2.",
          setup=["select_cube"], praise="A tall cube. A box with ambition."),
        B("reset", "Undo one field",
          "Right-click the Scale Z field and choose Reset to Default Value. Right-click menus on fields are full of gems like this.",
          obj("scale.z", 1, op="approx", tol=0.001, object="Cube"),
          setup=[{"do": "set", "object": "Cube", "path": "scale", "value": [1, 1, 2]}],
          hint="Right-click directly on the Z number, then Reset to Default Value."),
        B("wrench", "The wrench",
          "Click the blue wrench tab: Modifiers. Modifiers change a shape without touching its real geometry. Recipes, not edits.",
          prop("area:PROPERTIES", "spaces.active.context", "MODIFIER"),
          hint="Blue wrench icon, a little below the orange square."),
        B("subsurf", "Make it smooth",
          "Click Add Modifier, then Generate, then Subdivision Surface. The cube puffs into a soft blob.",
          mod("SUBSURF"), praise="Cube, meet pillow."),
        B("levels", "Smoother",
          "In the Subdivision panel, set Levels Viewport to 3. More levels, smoother surface, heavier mesh.",
          mod("SUBSURF", levels=ge(3)), hint="Levels Viewport is the first number in the modifier panel."),
        B("shade-smooth", "Shade smooth",
          "Right-click the cube in the viewport and choose Shade Smooth. The faceted look melts away.",
          obj("data.polygons[0].use_smooth", True, object="Cube"),
          hint="Right-click over the cube itself. Shade Smooth is near the top of the menu.",
          praise="Buttery."),
        B("bevel", "Stack another",
          "Add Modifier, Generate, Bevel. Modifiers stack like pancakes: the top one runs first, then the next.",
          mod("BEVEL")),
        B("reorder", "Change the order",
          "Drag the Bevel panel above Subdivision by its handle (the dotted grip at the top-right of the panel), or use its dropdown arrow and pick Move to First. See how the edges tighten?",
          obj("modifiers[0].type", "BEVEL", object="Cube"),
          hint="Each modifier header has a small dropdown arrow. Move to First lives there.",
          praise="Order matters. Now you know."),
        B("toggle", "Peek without it",
          "Click the little monitor icon in the Subdivision header to switch it off in the viewport. Click again to switch it back on.",
          seq(mod("SUBSURF", show_viewport=False), mod("SUBSURF", show_viewport=True)),
          hint="Each modifier header has toggle icons. The monitor is Show in Viewport."),
        B("cleared", "Lesson 04: cleared",
          "Properties, Object transforms, field resets, modifiers, the stack, and Shade Smooth. You've seen inside the machine.\n\nReward: Tab is unlocked. Next lesson you climb inside the mesh itself."),
    ]})

# ---------------------------------------------------------------- 05
LESSONS.append({
    "id": "lesson05", "title": "Lesson 05: Edit Mode",
    "unlocked": BASE + ["outliner", "properties"],
    "bites": [
        B("welcome", "Inside the mesh",
          "Object Mode moves whole things. Edit Mode moves the points, edges, and faces they're made of. Same cube, new superpower.",
          setup=["fresh_cube", "reset_view", "xray_off", {"do": "shading", "value": "SOLID"}]),
        B("tab", "Press Tab",
          "Hover the viewport and press Tab. The cube shows its skeleton: dots at the corners, lines between them.",
          {"type": "mode", "value": "EDIT_MESH"}, setup=["object_mode", "select_cube"],
          praise="You're in."),
        B("vert", "Pick a point",
          "Press 1 for vertex select, then click one corner dot.",
          all_(prop("tool_settings", "mesh_select_mode", [T, F, F]), mesh("sel_verts", "ge", 1)),
          setup=["edit_mode", "mesh_deselect"], hint="1 on the main keyboard row, not the numpad."),
        B("dent", "Dent it",
          "With that corner selected, press G, move the mouse, and click. You just reshaped the cube.",
          {"type": "operator", "idname": "TRANSFORM_OT_translate"}, praise="Sculptor energy."),
        B("edge", "Edges",
          "Press 2 for edge select and click one edge.",
          all_(prop("tool_settings", "mesh_select_mode", [F, T, F]), mesh("sel_edges", "ge", 1)),
          setup=["edit_mode", "mesh_deselect"]),
        B("face", "Faces",
          "Press 3 for face select and click the top face. It fills with orange.",
          all_(prop("tool_settings", "mesh_select_mode", [F, F, T]), mesh("sel_faces", "ge", 1)),
          setup=["edit_mode", "mesh_deselect"]),
        B("lift", "Raise the roof",
          "G, then Z, then type 1 and press Enter. The top face rises exactly one meter.",
          {"type": "operator", "idname": "TRANSFORM_OT_translate", "props": {"constraint_axis": [F, F, T]}},
          hint="Make sure the top face is still selected (orange). G, Z, 1, Enter.", praise="Taller house."),
        B("all", "Everything, then nothing",
          "Press A to select everything, then Alt+A to select nothing.",
          seq(mesh("sel_faces", "ge", 6), mesh("sel_verts", "eq", 0)), hint="A, then Alt+A."),
        B("xray-box", "See through, select through",
          "Press 1 for vertices, Alt+Z for X-ray, then drag a box around the bottom half of the cube. X-ray lets the box grab the hidden back corners too.",
          all_(prop("space", "shading.show_xray", True), mesh("sel_verts", "ge", 4)),
          setup=["edit_mode", "mesh_deselect", {"do": "select_mode", "value": [T, F, F]}, "xray_off"],
          hint="Left-drag on empty space to draw the box. X-ray first, or the back corners hide.",
          praise="Four corners, one swipe."),
        B("tab-out", "Back out",
          "Press Alt+Z to turn X-ray off, then Tab back to Object Mode. The cube keeps every change you made.",
          {"type": "mode", "value": "OBJECT"}),
        B("cleared", "Lesson 05: cleared",
          "Tab, the 1 2 3 select modes, grabbing points, A and Alt+A, X-ray selection. You can touch geometry now.\n\nScroll on for Lesson 06: the real modeling tools."),
    ]})

# ---------------------------------------------------------------- 06
EDIT_FACES = ["fresh_cube", "edit_mode", {"do": "select_mode", "value": [F, F, T]}, "mesh_deselect"]
LESSONS.append({
    "id": "lesson06", "title": "Lesson 06: Modeling",
    "unlocked": BASE + ["outliner", "properties"],
    "bites": [
        B("welcome", "The big six",
          "Six tools build most of the 3D models you've ever seen: extrude, inset, loop cut, bevel, merge, delete. Let's grow a tower.",
          setup=EDIT_FACES + ["reset_view", "xray_off"]),
        B("extrude", "Extrude",
          "Face mode (3). Click the top face, press E, pull the mouse up, click. Brand new geometry grows out of the face.",
          mesh("faces", "ge", 4, rel=True), hint="Top face selected, then E. Move the mouse up, click to confirm.",
          praise="It grows!"),
        B("extrude-2", "Again, exactly",
          "E again, then type 2 and press Enter. Two more meters of tower.",
          mesh("faces", "ge", 4, rel=True)),
        B("taper", "Taper",
          "With the top face still selected, press S, type 0.5, press Enter. Pointy.",
          {"type": "operator", "idname": "TRANSFORM_OT_resize"}),
        B("inset", "Inset",
          "Press I and slide the mouse to inset the top face: a frame inside a frame. Click to confirm.",
          mesh("faces", "ge", 4, rel=True), hint="I, move the mouse toward the face center, click."),
        B("dig", "Dig in",
          "E, then push the mouse down into the tower and click. Extrude works inward too. Instant pool.",
          mesh("faces", "ge", 4, rel=True), praise="Rooftop pool, very fancy."),
        B("loopcut", "Loop cut",
          "Hover a side of the tower, press Ctrl+R. A yellow ring previews the cut. Click once, then right-click to drop it dead center.",
          mesh("faces", "ge", 4, rel=True), hint="Ctrl+R with the mouse over a side face edge. Click, then right-click.",
          setup=["edit_mode"], hint_after=20),
        B("bevel", "Bevel",
          "Press 2 for edges, click one sharp edge, press Ctrl+B and drag. Sharp corners become smooth chamfers. Scroll the wheel while dragging for more segments.",
          mesh("faces", "ge", 1, rel=True),
          setup=["edit_mode", {"do": "select_mode", "value": [F, T, F]}, "mesh_deselect"]),
        B("merge", "Merge",
          "Press 1 for vertices. Click one corner, Shift+click a neighbor, press M and choose At Center. Two points become one.",
          mesh("verts", "le", -1, rel=True),
          setup=["edit_mode", {"do": "select_mode", "value": [T, F, F]}, "mesh_deselect"],
          hint="M opens the Merge menu. At Center is first."),
        B("delete", "Delete",
          "Press 3 for faces, click any face, press X and choose Faces. A hole! Meshes don't have to be closed.",
          mesh("faces", "le", -1, rel=True),
          setup=["edit_mode", {"do": "select_mode", "value": [F, F, T]}, "mesh_deselect"],
          praise="Ventilation."),
        B("tab-out", "Step back",
          "Tab back to Object Mode and orbit around your creation.",
          {"type": "mode", "value": "OBJECT"}),
        B("cleared", "Lesson 06: cleared",
          "Extrude, inset, loop cut, bevel, merge, delete. Honestly, that's most of modeling. Everything else is practice and taste.\n\nScroll on for Lesson 07: modifiers that work while you sleep."),
    ]})

# ---------------------------------------------------------------- 07
LESSONS.append({
    "id": "lesson07", "title": "Lesson 07: Modifiers",
    "unlocked": BASE + ["outliner", "properties"],
    "bites": [
        B("welcome", "Recipes",
          "A modifier is a recipe Blender reruns every time anything changes. Edit the cube, and every copy, bevel, and wobble updates with it.",
          setup=["fresh_cube", "reset_view", {"do": "shading", "value": "SOLID"}]),
        B("array", "Array",
          "Properties, wrench tab, Add Modifier, Generate, Array. Two cubes in a row.",
          mod("ARRAY"), hint="The wrench tab in the Properties editor. Add Modifier is the big button."),
        B("count", "More!",
          "Set the Array's Count to 5.",
          mod("ARRAY", count=ge(5)), praise="A train of cubes."),
        B("gap", "Mind the gap",
          "Under Relative Offset, set Factor X to 1.5. Now there's space between them.",
          mod("ARRAY", **{"relative_offset_displace[0]": ge(1.4)}),
          hint="Expand Relative Offset if it's folded. Factor X is the first field."),
        B("grid", "Into a grid",
          "Add a second Array. In its Relative Offset, set Factor X to 0 and Factor Y to 1.5. A train becomes a parking lot.",
          {"type": "modifier", "object": "Cube", "mod_type": "ARRAY", "props": {"relative_offset_displace[1]": ge(1.0)}},
          hint="A second Array modifier goes below the first. X to 0, Y to 1.5.", hint_after=20,
          praise="Twenty-five cubes, one real one."),
        B("wire", "Jungle gym",
          "Add Modifier, Generate, Wireframe. Every edge turns into a beam.",
          mod("WIREFRAME"), praise="Climbable."),
        B("edit-live", "Change the source",
          "Scale the cube with S. Watch the whole grid update. That's the power: one edit, everything follows.",
          {"type": "operator", "idname": "TRANSFORM_OT_resize"}, setup=["select_cube"]),
        B("remove", "Remove one",
          "Delete the Wireframe modifier: hover its panel and press Ctrl+X, or use its dropdown and pick Delete.",
          not_(mod("WIREFRAME"))),
        B("apply", "Make it real",
          "Hover the first Array and press Ctrl+A to apply it (or dropdown, Apply). The recipe gets cooked into real geometry, for better or worse.",
          mesh("verts", "ge", 40), hint="Apply the top Array. The mesh jumps from 8 vertices to 40.",
          praise="Baked."),
        B("cleared", "Lesson 07: cleared",
          "Array, Wireframe, stacking, live updates, deleting, applying. Non-destructive is a mindset: keep the recipe as long as you can.\n\nScroll on for Lesson 08: color and shine."),
    ]})

# ---------------------------------------------------------------- 08
LESSONS.append({
    "id": "lesson08", "title": "Lesson 08: Materials",
    "unlocked": BASE + ["outliner", "properties"],
    "bites": [
        B("welcome", "Paint and polish",
          "A material decides how a surface handles light: its color, whether it's metal, how rough or glossy it is.",
          setup=["fresh_cube", "reset_view", {"do": "shading", "value": "SOLID"}]),
        B("preview", "Look properly",
          "Z, then Material Preview, so you can actually see materials.",
          prop("space", "shading.type", "MATERIAL")),
        B("new", "A new material",
          "In Properties, click the red checkered ball tab (Material), then click New.",
          obj("active_material", op="present", object="Cube"),
          hint="The material tab is near the bottom of the Properties tab column.", setup=["select_cube"],
          praise="Blank canvas acquired."),
        B("name", "Name it",
          "Double-click the material's name at the top of the tab and call it Clay. Materials get reused, so names matter.",
          obj("active_material.name", op="changed", object="Cube")),
        B("color", "Pick a color",
          "Click the Base Color swatch and pick anything bold.",
          obj(PBSDF + "['Base Color'].default_value", op="changed", object="Cube"),
          hint="The Base Color bar is near the top of the Surface panel. Click it for the color wheel.",
          praise="Gorgeous."),
        B("metal", "Make it metal",
          "Drag Metallic all the way to 1.",
          obj(PBSDF + "['Metallic'].default_value", 0.9, op="ge", object="Cube")),
        B("gloss", "Polish it",
          "Set Roughness down to 0.1. Rough is matte, smooth is a mirror.",
          obj(PBSDF + "['Roughness'].default_value", 0.15, op="le", object="Cube"), praise="Chrome dome."),
        B("slot", "Two materials, one object",
          "Tab into Edit Mode, press 3, click one face. In the Material tab press the + beside the slot list, click New, then click Assign.",
          mesh("max_mat", "ge", 1),
          hint="Three steps: + adds a slot, New fills it, Assign paints the selected faces with it.",
          hint_after=25, praise="Two-tone."),
        B("tab-out", "Back out",
          "Tab back to Object Mode.", {"type": "mode", "value": "OBJECT"}),
        B("cleared", "Lesson 08: cleared",
          "New materials, base color, metal, roughness, and multiple materials on one mesh.\n\nReward: the Shader Editor just slid in at the bottom. It's the same material, drawn as a node graph. Scroll on for Lesson 09.",
          unlock=["shader"]),
    ]})

# ---------------------------------------------------------------- 09
LESSONS.append({
    "id": "lesson09", "title": "Lesson 09: Shader Nodes",
    "unlocked": BASE + ["outliner", "properties", "shader"],
    "bites": [
        B("welcome", "Under the hood",
          "Every material is secretly a little machine of nodes. Boxes do jobs, wires carry data from left to right, and the Material Output on the far right is the finish line.",
          setup=["object_mode", "select_cube", "ensure_material", {"do": "shading", "value": "MATERIAL"}]),
        B("navigate", "Find your way",
          "Hover the Shader Editor at the bottom. Scroll to zoom, middle-drag to pan, Home to fit everything on screen. Same moves as the viewport."),
        B("noise", "Add a texture",
          "Hover the Shader Editor, press Shift+A, then Texture, then Noise Texture. Click to drop it.",
          {"type": "node", "object": "Cube", "node_type": "TEX_NOISE"},
          hint="Shift+A must be pressed with the mouse over the Shader Editor, not the viewport."),
        B("wire", "Plug it in",
          "Drag from the Noise node's yellow Color dot to the Base Color dot on Principled BSDF. Your cube turns cloudy.",
          {"type": "node", "object": "Cube", "node_type": "TEX_NOISE", "linked_to": "Base Color"},
          hint="Yellow dots carry color. Drag dot to dot.", praise="Clouds!"),
        B("scale", "Zoom the pattern",
          "On the Noise node, set Scale to 20. Finer grain.",
          obj("active_material.node_tree.nodes['Noise Texture'].inputs['Scale'].default_value", 15, op="ge",
              object="Cube")),
        B("ramp", "Splice in color",
          "Shift+A, Converter, Color Ramp. Drop it right ON the wire between Noise and Principled. Blender splices it in for you.",
          {"type": "node", "object": "Cube", "node_type": "VALTORGB", "linked_to": "Base Color"},
          hint="Drag the new node over the wire until the wire highlights, then click.", hint_after=20),
        B("ramp-color", "Choose the palette",
          "Click the black stop on the Color Ramp, then click the color bar below it and pick a color. Do the white one too.",
          obj("active_material.node_tree.nodes['Color Ramp'].color_ramp.elements[0].color", op="changed",
              object="Cube"), praise="Custom marble."),
        B("bump", "Make it bumpy",
          "Shift+A, Vector, Bump. Wire Noise's Fac into Bump's Height, and Bump's Normal into Principled's Normal.",
          {"type": "node", "object": "Cube", "node_type": "BUMP", "linked_to": "Normal"},
          hint="Two wires: Noise Fac to Bump Height, Bump Normal to Principled Normal (purple dots).",
          hint_after=25, praise="You can feel it."),
        B("cleared", "Lesson 09: cleared",
          "Adding nodes, wiring them, splicing, color ramps, and bump. That's the grammar of every procedural material.\n\nScroll on for Lesson 10: light."),
    ]})

# ---------------------------------------------------------------- 10
LESSONS.append({
    "id": "lesson10", "title": "Lesson 10: Light",
    "unlocked": BASE + ["outliner", "properties", "shader"],
    "bites": [
        B("welcome", "Light is everything",
          "Same object, different light, totally different mood. Painters have known this forever.",
          setup=["object_mode", "select_cube", "ensure_light", "reset_view"]),
        B("rendered", "See real light",
          "Z, then Rendered.", prop("space", "shading.type", "RENDERED")),
        B("area", "Add a softbox",
          "Shift+A, Light, Area. A flat, glowing panel, like a photographer's softbox.",
          {"type": "added", "prefix": "Area", "object_type": "LIGHT"}, praise="Lights, then..."),
        B("lift", "Hang it up",
          "G, Z, and lift the Area light to at least 3 meters up. It points down by default.",
          obj("location.z", 3, op="ge", prefix="Area", object_type="LIGHT"),
          setup=[{"do": "select", "prefix": "Area"}]),
        B("power", "Turn it up",
          "Properties, green lightbulb tab (Object Data). Set Power to 500 W.",
          obj("data.energy", 500, op="ge", prefix="Area", object_type="LIGHT"),
          hint="The green lightbulb tab only shows while the light is selected."),
        B("warm", "Warm it up",
          "Click the light's Color and pick a warm orange.",
          obj("data.color", op="changed", prefix="Area", object_type="LIGHT"), praise="Golden hour."),
        B("soft", "Soften the shadows",
          "Set the Area light's Size to 4. Bigger light, softer shadows. That's the whole secret of portrait lighting.",
          obj("data.size", 3.5, op="ge", prefix="Area", object_type="LIGHT")),
        B("world", "Dim the sky",
          "Click the red globe tab (World). Set Strength to 0.2. The ambient fill drops and your Area light takes over.",
          prop("scene", "world.node_tree.nodes['Background'].inputs['Strength'].default_value", 0.3, op="le"),
          hint="Red globe tab, Surface, Strength."),
        B("cleared", "Lesson 10: cleared",
          "Rendered view, Area lights, power, color, size, and the World. You're lighting like a photographer.\n\nScroll on for Lesson 11: the camera."),
    ]})

# ---------------------------------------------------------------- 11
LESSONS.append({
    "id": "lesson11", "title": "Lesson 11: Camera",
    "unlocked": BASE + ["outliner", "properties"],
    "bites": [
        B("welcome", "Choose the shot",
          "The camera decides what the final picture shows. Framing is half of every image.",
          setup=["object_mode", "ensure_camera", "perspective", {"do": "shading", "value": "SOLID"}, "reset_view"]),
        B("look", "Look through it",
          "Hover the viewport and press 0 on the number pad. You're looking through the camera now.",
          prop("rv3d", "view_perspective", "CAMERA"),
          hint="No numpad? View menu, Cameras, Active Camera."),
        B("aim", "Camera to view",
          "Middle-drag to orbit out of the camera, find an angle you love, then press Ctrl+Alt+Numpad 0. The camera jumps to exactly what you see.",
          {"type": "transformed", "any": True, "object_type": "CAMERA"},
          hint="No numpad? View menu, Align View, Align Active Camera to View.", setup=["perspective"],
          praise="Shot composed."),
        B("lens", "Change the lens",
          "Click the camera in the Outliner, open the green camera tab (Object Data), set Focal Length to 85. Long lenses flatten and flatter.",
          obj("data.lens", 80, op="ge", any=True, object_type="CAMERA")),
        B("lock", "Drive the camera",
          "Press N, open the View tab, and tick Lock Camera to View. Now orbiting in camera view moves the camera itself.",
          prop("space", "lock_camera", True), hint="Sidebar (N), View tab, look for Lock Camera to View."),
        B("drive", "Frame it, then unlock",
          "In camera view (numpad 0), orbit and pan until the cube sits nicely in the frame. Then untick Lock Camera to View.",
          seq({"type": "transformed", "any": True, "object_type": "CAMERA"}, prop("space", "lock_camera", False)),
          hint_after=25),
        B("dof", "Blur the background",
          "Back in the camera's Object Data tab, tick Depth of Field, set Focus on Object to the Cube, and F-Stop to 1.4.",
          obj("data.dof.use_dof", True, any=True, object_type="CAMERA"), praise="Cinematic."),
        B("cleared", "Lesson 11: cleared",
          "Camera view, camera to view, focal length, Lock Camera to View, and depth of field.\n\nScroll on for Lesson 12: take the picture."),
    ]})

# ---------------------------------------------------------------- 12
LESSONS.append({
    "id": "lesson12", "title": "Lesson 12: Render",
    "unlocked": BASE + ["outliner", "properties"],
    "bites": [
        B("welcome", "Take the picture",
          "Rendering turns your scene into a finished image, seen through the camera.",
          setup=["object_mode", "ensure_camera", "perspective", {"do": "shading", "value": "SOLID"}]),
        B("engine", "Pick an engine",
          "Properties, the camera-back tab (Render). Change Render Engine to something else, then back if you like. EEVEE is fast, Cycles is physically accurate, Workbench is a quick preview.",
          prop("render", "engine", op="changed"), praise="Engines warm."),
        B("size", "Smaller for speed",
          "Open the printer tab (Output). Set the % under Resolution to 50. Half size renders four times faster while you experiment.",
          prop("render", "resolution_percentage", 50, op="le"), hint="Output tab, Format, Resolution, the % field."),
        B("f12", "F12",
          "Hover the viewport and press F12. A render window opens and your picture appears.",
          {"type": "rendered"}, hint="No F12? Render menu at the top, Render Image.", hint_after=20,
          praise="Your first render!"),
        B("save", "Keep it",
          "In the render window, use Image, Save As to keep your picture. Then close the render window to come back here."),
        B("cleared", "Lesson 12: cleared",
          "Engines, resolution, F12, and saving the image. You can make pictures now.\n\nReward: the Timeline is about to slide in. Scroll on for Lesson 13: time."),
    ]})

# ---------------------------------------------------------------- 13
LESSONS.append({
    "id": "lesson13", "title": "Lesson 13: Animation",
    "unlocked": BASE + ["outliner", "properties", "timeline"],
    "bites": [
        B("welcome", "Things that move",
          "The strip at the bottom is the Timeline. Animation is just keyframes: you say where something is at certain frames, and Blender fills in between.",
          setup=["stop_playback", {"do": "frame", "value": 1}, "fresh_cube", "perspective", "reset_view"]),
        B("key1", "First keyframe",
          "Hover the viewport and press I, then pick Location. A diamond appears on frame 1 in the Timeline.",
          {"type": "keyframes", "object": "Cube", "path_prefix": "location", "value": 1},
          hint="I is for Insert keyframe. The cube must be selected.", setup=["select_cube"]),
        B("jump", "Jump ahead",
          "Click frame 40 in the Timeline (or type 40 in the current frame box at the right).",
          prop("scene", "frame_current", 30, op="ge")),
        B("key2", "Second keyframe",
          "G, X, move the cube, click. Then I, Location again.",
          {"type": "keyframes", "object": "Cube", "path_prefix": "location", "value": 2},
          praise="Two diamonds. That's an animation."),
        B("play", "Roll film",
          "Hover the viewport and press Space to play. Press Space again to stop.",
          seq(prop("screen", "is_animation_playing", True), prop("screen", "is_animation_playing", False)),
          hint="Space toggles playback. Esc stops and jumps back."),
        B("scrub", "Scrub",
          "Drag the blue playhead back and forth along the Timeline. That's scrubbing: you control time by hand.",
          prop("scene", "frame_current", op="changed"), setup=["stop_playback"]),
        B("spin", "Add a spin",
          "Go to frame 80. Press R, Z, 180, Enter, then I and pick Rotation.",
          {"type": "keyframes", "object": "Cube", "path_prefix": "rotation", "value": 1},
          hint="Frame 80 first, then rotate, then I, Rotation."),
        B("watch", "Watch your film",
          "Press Home over the Timeline to see the whole range, set End to 80, and press Space. Slide, spin, done."),
        B("cleared", "Lesson 13: cleared",
          "Keyframes, the Timeline, playback, scrubbing, and animating rotation. Things move when you say so.\n\nScroll on for the last lesson."),
    ]})

# ---------------------------------------------------------------- 14
LESSONS.append({
    "id": "lesson14", "title": "Lesson 14: Graduation",
    "unlocked": BASE + ["outliner", "properties", "timeline"],
    "bites": [
        B("welcome", "The tabs up top",
          "See the tabs along the very top of the window (Layout, Modeling, Sculpting, Shading...)? Each is a workspace: the same scene, arranged for a different job. You're in one called Blender Bites right now.",
          setup=["stop_playback", "bites_workspace"]),
        B("shading", "Visit Shading",
          "Click the Shading tab. Material preview, a node editor, an image browser, all laid out for painting with light.",
          prop("window", "workspace.name", "Shading"), hint="Top bar of the window, the tab named Shading."),
        B("modeling", "Visit Modeling",
          "Now click the Modeling tab. A big viewport, tools on the left, ready for edit mode.",
          prop("window", "workspace.name", "Modeling")),
        B("home", "Come home",
          "Click the Blender Bites tab to come back here.",
          prop("window", "workspace.name", "Blender Bites"),
          hint="The Blender Bites tab is with the others along the top. Scroll the tab row if it's hidden."),
        B("save", "Save your work",
          "Press Ctrl+S. If this file has never been saved, Blender asks where. Call it my_first_scene.blend.",
          {"type": "saved"}, hint="Ctrl+S, pick a folder, type a name, click Save.", hint_after=25,
          praise="Safe and sound."),
        B("f1-forever", "F1, forever",
          "F1 keeps working after you graduate. Hover anything strange and ask. Right-click any button for EXPLAIN, too."),
        B("cleared", "You graduated",
          "Viewport, seeing, making, organizing, properties, edit mode, modeling, modifiers, materials, nodes, light, camera, render, animation, workspaces. That's Blender.\n\nScroll down and the whole program is yours. Go make something weird."),
    ]})

# chain them
order = ["lesson02"] + [L["id"] for L in LESSONS]
for L in LESSONS:
    i = order.index(L["id"])
    if i + 1 < len(order):
        L["next"] = order[i + 1]

TITLES = [("lesson00", "Lesson 00: The Viewport"), ("lesson01", "Lesson 01: Seeing"),
          ("lesson02", "Lesson 02: Making")] + [(L["id"], L["title"]) for L in LESSONS]


def build():
    for L in LESSONS:
        ordered = {k: L[k] for k in ("id", "title", "next", "unlocked", "locked", "bites") if k in L}
        (CONTENT / f"{L['id']}.json").write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", "utf-8")
    (CONTENT / "index.json").write_text(
        json.dumps({"lessons": [{"id": i, "title": t} for i, t in TITLES]}, indent=2) + "\n", "utf-8")
    l02 = json.loads((CONTENT / "lesson02.json").read_text("utf-8"))
    l02["next"] = "lesson03"
    l02["bites"][-1]["body"] = (
        "You can place the cursor, add, tweak, delete, duplicate, and stack. You build things now.\n\n"
        "Reward: the Outliner just slid in on the right. It lists every object in your scene. "
        "Scroll on for Lesson 03: Organizing.")
    (CONTENT / "lesson02.json").write_text(json.dumps(l02, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print("bites:", {L["id"]: len(L["bites"]) for L in LESSONS})


if __name__ == "__main__":
    build()
