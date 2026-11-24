"""Build dist/blender_bites-<version>.zip from blender_bites/.

    python tools/package.py

The zip has the extension's files at its root, the layout Blender's
Install from Disk expects. To double-check with Blender itself:

    blender --command extension validate dist/blender_bites-<version>.zip
"""
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "blender_bites"


def version():
    m = re.search(r'^version\s*=\s*"([^"]+)"', (SRC / "blender_manifest.toml").read_text("utf-8"), re.M)
    return m.group(1)


def build():
    out = ROOT / "dist" / f"blender_bites-{version()}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SRC.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                z.write(f, f.relative_to(SRC).as_posix())
    print(out)
    return out


if __name__ == "__main__":
    build()
