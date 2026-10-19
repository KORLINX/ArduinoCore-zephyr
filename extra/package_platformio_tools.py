#!/usr/bin/env python3
# Copyright (c) 2026 KORLINX
# SPDX-License-Identifier: Apache-2.0

"""Repack the core's build tools as PlatformIO packages.

Usage: extra/package_platformio_tools.py OUT_DIR

PlatformIO only installs archives that carry a package.json, so the tools the
Arduino IDE downloads cannot be used as they are. For every tool below, at the
version pinned in extra/artifacts/_common.json, this downloads Arduino's
archive for each host, checks it against the SHA-256 in Arduino's package
index, and writes OUT_DIR/<package>-<version>-<systype>.tar.xz with a
package.json next to the files. KORLINX-PlatformIO picks the file for the
user's host by its PlatformIO systype.
"""

import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

INDEX_URL = "https://downloads.arduino.cc/packages/package_index.json"

# Arduino tool -> PlatformIO package, and where its source is
TOOLS = {
    "arm-zephyr-eabi": ("toolchain-gccarmzephyreabi",
                        "https://github.com/zephyrproject-rtos/sdk-ng"),
    "zephyr-sketch-tool": ("tool-zephyr-sketch-tool",
                           "https://github.com/arduino/ArduinoCore-zephyr"),
    "gen-rodata-ld": ("tool-gen-rodata-ld",
                      "https://github.com/arduino/ArduinoCore-zephyr"),
    "zephyr-check-size": ("tool-zephyr-check-size",
                          "https://github.com/arduino/ArduinoCore-zephyr"),
}

# Arduino host -> PlatformIO systype. Arduino's i686-mingw32 toolchain is a
# 64-bit Windows build.
HOSTS = {
    "x86_64-linux-gnu": "linux_x86_64",
    "aarch64-linux-gnu": "linux_aarch64",
    "x86_64-apple-darwin": "darwin_x86_64",
    "arm64-apple-darwin": "darwin_arm64",
    "i686-mingw32": "windows_amd64",
}


def members(path):
    """(TarInfo, data or None) for every entry of a tar or zip file."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for zi in zf.infolist():
                ti = tarfile.TarInfo(zi.filename.rstrip("/"))
                if zi.is_dir():
                    ti.type, ti.mode = tarfile.DIRTYPE, 0o755
                    yield ti, None
                else:
                    data = zf.read(zi)
                    ti.size, ti.mode = len(data), 0o755
                    yield ti, data
        return
    with tarfile.open(path) as tf:
        for ti in tf:
            yield ti, (tf.extractfile(ti).read() if ti.isfile() else None)


def repack(src, dst, manifest):
    """Copy src into dst.tar.xz under a top folder named after the package,
    replacing the archive's own top folder if it has exactly one."""
    names = [ti.name.lstrip("./") for ti, _ in members(src)]
    tops = {n.split("/", 1)[0] for n in names if n}
    strip = tops.pop() + "/" if len(tops) == 1 and any("/" in n for n in names) else ""
    root = manifest["name"] + "/"

    def rename(name):
        name = name.lstrip("./")
        return root + name[len(strip):] if name.startswith(strip) else None

    with tarfile.open(dst, "w:xz", format=tarfile.PAX_FORMAT) as out:
        data = (json.dumps(manifest, indent=2) + "\n").encode()
        ti = tarfile.TarInfo(root + "package.json")
        ti.size, ti.mode = len(data), 0o644
        out.addfile(ti, io.BytesIO(data))
        for ti, data in members(src):
            name = rename(ti.name)
            if not name or name == root:
                continue
            ti.name = name
            if ti.islnk():  # hard links name another member of the archive
                ti.linkname = rename(ti.linkname)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            out.addfile(ti, io.BytesIO(data) if data is not None else None)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)

    here = os.path.dirname(os.path.abspath(__file__))
    pinned = {d["name"]: (d["packager"], d["version"]) for d in json.load(
        open(os.path.join(here, "artifacts", "_common.json")))["toolsDependencies"]}
    index = json.load(urllib.request.urlopen(INDEX_URL))
    available = {(p["name"], t["name"], t["version"]): t
                 for p in index["packages"] for t in p.get("tools", [])}

    for tool, (package, homepage) in TOOLS.items():
        packager, version = pinned[tool]
        for system in available[(packager, tool, version)]["systems"]:
            systype = HOSTS.get(system["host"])
            if not systype:
                continue
            dst = os.path.join(out_dir, "%s-%s-%s.tar.xz" % (package, version, systype))
            print("%s <- %s" % (os.path.basename(dst), system["url"]), flush=True)
            with tempfile.NamedTemporaryFile() as tmp:
                algo, want = system["checksum"].split(":", 1)
                h = hashlib.new(algo.lower().replace("-", ""))
                with urllib.request.urlopen(system["url"]) as r:
                    while chunk := r.read(1 << 20):
                        tmp.write(chunk)
                        h.update(chunk)
                tmp.flush()
                if h.hexdigest() != want.lower():
                    sys.exit("checksum mismatch for %s" % system["url"])
                repack(tmp.name, dst, {
                    "name": package,
                    "version": version,
                    "description": "%s %s as the KORLINX Arduino core uses it, "
                                   "repacked for PlatformIO" % (tool, version),
                    "homepage": homepage,
                    "system": [systype],
                })


if __name__ == "__main__":
    main()
