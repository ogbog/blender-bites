# Changelog

## 0.3.0 (2026-11-24)

First public release.

- 15 lessons, 148 bites: Viewport, Seeing, Making, Organizing, Properties, Edit Mode, Modeling, Modifiers, Materials, Shader Nodes, Light, Camera, Render, Animation, Graduation.
- 112 EXPLAIN entries: hover anything and press F1, or right-click a button and choose EXPLAIN.
- Learn mode runs in its own temporary "Blender Bites" workspace and deletes it on exit. Each lesson shows exactly the editors it needs (Outliner, Properties, Shader Editor, Timeline), split in as they're earned.
- Help > Blender Bites menu: Continue, any lesson, Exit. Local progress with check marks.
- 32 data-driven check types, including generic property paths, mesh counts, modifiers, shader nodes, keyframes, render and save events.
- Lesson-level locked shortcuts (Shift+A in Lesson 01, Tab in Lessons 03 and 04).
- Dev tools: `tools/build_lessons.py` (lessons 03 to 14 source of truth), `tools/harness.py` (fail-before, pass-after checker), `tools/package.py`, `tools/store_art.py`.

## 0.2.x (unreleased)

- Lessons 01 and 02, lesson chaining, the lesson menu, generic checks, key locks.
- 0.2.1 dropped focus mode, which left Blender's top bar and status bar hidden after a lesson.

## 0.1.0 (unreleased)

- Vertical slice: Lesson 00, the lesson card overlay, F1 / right-click EXPLAIN.
