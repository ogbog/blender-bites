# SPDX-License-Identifier: GPL-3.0-or-later
"""The lesson loop: card -> challenge -> check -> celebrate -> next bite -> next lesson."""
import json
import math
import time
from pathlib import Path

import bpy
from mathutils import Euler, Vector

from . import checks, learnmode, oplog

CONTENT = Path(__file__).parent / "content"
PASS_HOLD = 1.1   # seconds of "Nailed it!" before auto-advance
TICK = 0.15


# ---- lesson index + progress -----------------------------------------
def lesson_index():
    try:
        return json.loads((CONTENT / "index.json").read_text("utf-8"))["lessons"]
    except Exception:
        return [{"id": "lesson00", "title": "Lesson 00: The Viewport"}]


def _progress_file():
    return Path(bpy.utils.extension_path_user(__package__, create=True)) / "progress.json"


def load_progress():
    try:
        f = _progress_file()
        return json.loads(f.read_text("utf-8")) if f.exists() else {}
    except Exception:
        return {}


def _save_progress(lesson_id):
    try:
        f = _progress_file()
        data = load_progress()
        data.setdefault("completed", [])
        if lesson_id not in data["completed"]:
            data["completed"].append(lesson_id)
        f.write_text(json.dumps(data, indent=2), "utf-8")
    except Exception as e:
        print("[Bites] could not save progress", e)


def resume_id():
    done = set(load_progress().get("completed", []))
    index = lesson_index()
    for entry in index:
        if entry["id"] not in done and (CONTENT / f"{entry['id']}.json").exists():
            return entry["id"]
    return index[-1]["id"]


def _read_lesson(lesson_id):
    return json.loads((CONTENT / f"{lesson_id}.json").read_text(encoding="utf-8"))


# ---- runner ----------------------------------------------------------
class Runner:
    def __init__(self):
        self.active = False
        self.lesson = None
        self.lesson_id = None
        self.idx = 0
        self.passed_at = None
        self.started_at = 0.0
        self.snap = {"objs": {}}
        self.log = oplog.OpLog()
        self.nudge_until = 0.0
        self.toast_text = ""
        self.toast_until = 0.0
        self.pending = False      # bite setup waits until the layout settles
        self._was_busy = False

    # ---- state -------------------------------------------------------
    @property
    def bite(self):
        return self.lesson["bites"][self.idx]

    @property
    def count(self):
        return len(self.lesson["bites"]) if self.lesson else 0

    def is_read(self):
        return self.bite.get("check", {}).get("type", "read") == "read"

    def show_hint(self):
        return (
            self.passed_at is None
            and not self.pending
            and not self.is_read()
            and time.monotonic() - self.started_at > self.bite.get("hint_after", 15)
        )

    def toast(self, text, secs=2.2):
        self.toast_text = text
        self.toast_until = time.monotonic() + secs
        redraw()

    # ---- lifecycle ---------------------------------------------------
    def start(self, lesson_id=""):
        lesson_id = lesson_id or resume_id()
        lesson = _read_lesson(lesson_id)
        if not self.active:
            learnmode.enter(lesson.get("unlocked", []))
            self.active = True
            if not bpy.app.timers.is_registered(_tick):
                bpy.app.timers.register(_tick, first_interval=TICK, persistent=True)
            learnmode.start_card_modal()
        self._load(lesson_id, lesson)
        self.goto(0)

    def _load(self, lesson_id, lesson):
        self.lesson = lesson
        self.lesson_id = lesson_id
        learnmode.apply_lesson(lesson.get("unlocked", []))

    def stop(self):
        if not self.active:
            return
        self.active = False
        try:
            learnmode.exit()
        finally:
            redraw()

    def finish(self):
        _save_progress(self.lesson_id or self.lesson.get("id", "lesson"))
        nxt = self.lesson.get("next")
        if nxt and (CONTENT / f"{nxt}.json").exists():
            self._load(nxt, _read_lesson(nxt))
            self.goto(0)
        else:
            self.stop()

    # ---- navigation --------------------------------------------------
    def goto(self, i):
        self.idx = max(0, min(i, self.count - 1))
        self.passed_at = None
        self.started_at = time.monotonic()
        self.pending = True
        if not learnmode.busy():
            self._arm()
        redraw()

    def _arm(self):
        """Run the bite's setup and take the 'before' snapshot."""
        self.pending = False
        for action in self.bite.get("setup", []):
            try:
                _setup(action)
            except Exception as e:
                print("[Bites] setup failed", action, e)
        for what in self.bite.get("unlock", []):
            learnmode.unlock(what)
        self.snap = checks.snapshot()
        self.log.reset()
        self.started_at = time.monotonic()

    def next(self):
        if self.idx >= self.count - 1:
            self.finish()
        else:
            self.goto(self.idx + 1)

    def scroll_next(self):
        if self.is_read() or self.passed_at is not None:
            self.next()
        else:
            self.nudge_until = time.monotonic() + 0.6
            redraw()

    def scroll_prev(self):
        if self.idx > 0:
            self.goto(self.idx - 1)

    # ---- heartbeat ---------------------------------------------------
    def tick(self):
        learnmode.relayout_if_needed()
        if learnmode.busy():
            self._was_busy = True
            return
        if self.pending:
            self._arm()
            redraw()
            return
        if self._was_busy:
            # The layout just changed under us: re-take the view snapshot.
            self._was_busy = False
            self.snap = checks.snapshot()
        self.log.poll()
        if self.passed_at is None:
            if not self.is_read() and checks.run(self.bite["check"], self.snap, self.log):
                self.passed_at = time.monotonic()
                redraw()
        elif time.monotonic() - self.passed_at > PASS_HOLD:
            self.next()
            return
        if self.bite.get("pulse") or self.show_hint() or time.monotonic() < self.toast_until + 0.3:
            redraw()


_runner = Runner()


def get():
    return _runner


def _tick():
    r = _runner
    if not r.active:
        return None
    try:
        r.tick()
    except Exception as e:
        print("[Bites] tick error", e)
    return TICK


def redraw():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# ---- bite setup actions ----------------------------------------------
def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    obj["bites_generated"] = True
    return obj


def _ensure_cube():
    cube = bpy.data.objects.get("Cube")
    if cube is None or cube.name not in bpy.context.scene.objects:
        import bmesh
        mesh = bpy.data.meshes.new("Cube")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        bm.to_mesh(mesh)
        bm.free()
        cube = _link(bpy.data.objects.new("Cube", mesh))
    return cube


def _ensure_suzanne():
    for o in bpy.context.scene.objects:
        if o.name.startswith("Suzanne"):
            return o
    import bmesh
    mesh = bpy.data.meshes.new("Suzanne")
    bm = bmesh.new()
    bmesh.ops.create_monkey(bm)
    bm.to_mesh(mesh)
    bm.free()
    suz = _link(bpy.data.objects.new("Suzanne", mesh))
    suz.location = (3.0, 0.0, 0.0)
    return suz


def _select_only(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _setup(action):
    name = action if isinstance(action, str) else action.get("do")
    v = learnmode.find_view3d()
    if name == "reset_cube":
        c = _ensure_cube()
        c.location = (0, 0, 0)
        c.rotation_euler = (0, 0, 0)
        c.scale = (1, 1, 1)
    elif name == "deselect_all":
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
    elif name == "select_cube":
        _select_only(_ensure_cube())
    elif name == "select":
        prefix = action.get("prefix", "Cube")
        for o in bpy.context.scene.objects:
            if o.name.startswith(prefix):
                _select_only(o)
                break
    elif name == "ensure_suzanne":
        _ensure_suzanne()
    elif name == "offset_view" and v:
        v[4].view_location += Vector(action.get("by", (4, 2, 0)))
    elif name == "reset_view" and v:
        rv = v[4]
        rv.view_perspective = 'PERSP'
        rv.view_location = (0, 0, 0)
        rv.view_distance = action.get("distance", 12.0) if isinstance(action, dict) else 12.0
        # Front-left three-quarter view. The classic (63, 0, 46) angle looks
        # straight down the default camera's line of sight, so the camera
        # blocks the cube.
        rv.view_rotation = Euler((math.radians(62), 0, math.radians(-40))).to_quaternion()
    elif name == "shading" and v:
        v[3].shading.type = action.get("value", 'SOLID')
    elif name == "xray_off" and v:
        v[3].shading.show_xray = False
    elif name == "cursor_reset":
        cur = bpy.context.scene.cursor
        cur.location = (0, 0, 0)
        cur.rotation_euler = (0, 0, 0)
    elif name == "object_mode":
        _mode("OBJECT")
    elif name == "edit_mode":
        _select_only(_ensure_cube())
        _mode("EDIT")
    elif name == "fresh_cube":
        # Back to a pristine default cube: object mode, 8 verts, no modifiers,
        # no materials, no animation, flat shading, at the origin.
        _mode("OBJECT")
        c = _ensure_cube()
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        bm.to_mesh(c.data)
        bm.free()
        c.data.update()
        c.modifiers.clear()
        c.data.materials.clear()
        c.animation_data_clear()
        for poly in c.data.polygons:
            poly.use_smooth = False
        c.location, c.rotation_euler, c.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
        c.hide_set(False)
        _select_only(c)
    elif name == "select_mode":
        bpy.context.scene.tool_settings.mesh_select_mode = action.get("value", (True, False, False))
    elif name == "mesh_deselect":
        o = bpy.context.view_layer.objects.active
        if o and o.mode == 'EDIT':
            import bmesh
            bm = bmesh.from_edit_mesh(o.data)
            for seq in (bm.verts, bm.edges, bm.faces):
                for e in seq:
                    e.select = False
            bmesh.update_edit_mesh(o.data)
    elif name == "frame":
        bpy.context.scene.frame_set(int(action.get("value", 1)))
    elif name == "stop_playback":
        win = bpy.context.window_manager.windows[0]
        if win.screen.is_animation_playing:
            with bpy.context.temp_override(window=win, screen=win.screen):
                bpy.ops.screen.animation_cancel(restore_frame=False)
    elif name == "perspective" and v:
        if v[4].view_perspective == 'CAMERA':
            v[4].view_perspective = 'PERSP'
    elif name == "unhide_all":
        for o in bpy.context.scene.objects:
            if o.hide_get():
                o.hide_set(False)
    elif name == "clear_parent":
        prefix = action.get("prefix", "Suzanne")
        for o in bpy.context.scene.objects:
            if o.name.startswith(prefix) and o.parent is not None:
                mw = o.matrix_world.copy()
                o.parent = None
                o.matrix_world = mw
    elif name == "set":
        # {"do": "set", "object": "Cube", "path": "scale", "value": [1, 1, 2]}
        o = bpy.data.objects.get(action.get("object", "Cube"))
        path = action["path"]
        if o is not None:
            head, _, attr = path.rpartition(".")
            target = checks._resolve(o, head) if head else o
            if target is not checks._MISSING:
                setattr(target, attr, action["value"])
    elif name == "hide":
        for o in bpy.context.scene.objects:
            if (o.type == action.get("object_type", o.type)
                    and o.name.startswith(action.get("prefix", ""))):
                o.hide_set(True)
    elif name == "ensure_light":
        if not any(o.type == 'LIGHT' for o in bpy.context.scene.objects):
            ld = bpy.data.lights.new("Light", 'POINT')
            ld.energy = 1000
            _link(bpy.data.objects.new("Light", ld)).location = (4.08, 1.0, 5.9)
    elif name == "ensure_camera":
        if not any(o.type == 'CAMERA' for o in bpy.context.scene.objects):
            cam = _link(bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera")))
            cam.location = (7.36, -6.93, 4.96)
            cam.rotation_euler = Euler((math.radians(63.6), 0, math.radians(46.7)))
        if bpy.context.scene.camera is None:
            bpy.context.scene.camera = next(o for o in bpy.context.scene.objects if o.type == 'CAMERA')
    elif name == "ensure_material":
        c = _ensure_cube()
        if c.active_material is None:
            mat = bpy.data.materials.get("Bites Clay") or bpy.data.materials.new("Bites Clay")
            if getattr(mat, "node_tree", None) is None and hasattr(mat, "use_nodes"):
                mat.use_nodes = True
            c.data.materials.append(mat)
    elif name == "place":
        # Walk every prefix match to a known spot (unparented), side by side,
        # so a challenge can't pass on leftovers from an earlier run.
        x, y, z = action.get("location", (3, 0, 0))
        i = 0
        for o in bpy.context.scene.objects:
            if o.name.startswith(action.get("prefix", "Suzanne")):
                o.parent = None
                o.location = (x + 2.5 * i, y, z)
                i += 1
    elif name == "bites_workspace":
        win = bpy.context.window_manager.windows[0]
        ws = bpy.data.workspaces.get(learnmode.WS_NAME)
        if ws is not None and win.workspace != ws:
            win.workspace = ws


def _mode(mode):
    """mode_set needs a real 3D View context, even from a timer."""
    o = bpy.context.view_layer.objects.active
    if o is None or o.mode == mode:
        return
    v = learnmode.find_view3d()
    if v is None:
        return
    win, area, region, _, _ = v
    with bpy.context.temp_override(window=win, screen=win.screen, area=area, region=region,
                                   active_object=o, object=o):
        bpy.ops.object.mode_set(mode=mode)
