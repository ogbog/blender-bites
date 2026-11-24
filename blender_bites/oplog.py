# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator log: the grading oracle.

Blender keeps recently run, registered operators (with their final property
values) in WindowManager.operators. We poll it and record anything new since
the current bite started, with every simple property the operator has. That
includes redo edits from the Adjust Last Operation panel, which change the
values of the top operator in place.

Script-called operators never show up here; real keystrokes and clicks do.
"""
import bpy

SIMPLE = {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}


def _plain(v):
    if isinstance(v, (str, bool, int, float)) or v is None:
        return v
    if isinstance(v, (set, frozenset)):
        return tuple(sorted(v))
    try:
        return tuple(_plain(x) for x in v)
    except TypeError:
        return v


def _record(op):
    rec = {"id": op.bl_idname}
    props = op.properties
    for p in props.bl_rna.properties:
        k = p.identifier
        if k == "rna_type" or p.type not in SIMPLE:
            continue
        try:
            rec[k] = _plain(getattr(props, k))
        except Exception:
            pass
    return rec


def _signature(ops):
    if not len(ops):
        return None
    top = ops[-1]
    rec = _record(top)
    # Pointer alone can be reused after free, so fold in length and values.
    return (top.as_pointer(), len(ops), repr(sorted(rec.items())))


class OpLog:
    def __init__(self):
        self.records = []
        self._sig = None

    def reset(self):
        self.records = []
        self._sig = _signature(bpy.context.window_manager.operators)

    def poll(self):
        ops = bpy.context.window_manager.operators
        sig = _signature(ops)
        if sig is None or sig == self._sig:
            return
        self._sig = sig
        self.records.append(_record(ops[-1]))
