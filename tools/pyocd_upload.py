# Copyright (c) 2026 KORLINX
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

BANNER = re.compile(rb"Booting Arduino loader \S+ on")


def hex_bytes(path):
    """Return {address: byte} for the data records of an Intel HEX file."""
    data, base = {}, 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line.startswith(":"):
                continue
            n, addr, kind = int(line[1:3], 16), int(line[3:7], 16), int(line[7:9], 16)
            payload = bytes.fromhex(line[9:9 + 2 * n])
            if kind == 0:
                for i, b in enumerate(payload):
                    data[base + addr + i] = b
            elif kind == 2:
                base = int.from_bytes(payload, "big") << 4
            elif kind == 4:
                base = int.from_bytes(payload, "big") << 16
    return data


def banner_in_hex(path):
    """Return (address, bytes) of the loader banner in the image, or None."""
    data = hex_bytes(path)
    if not data:
        return None
    start = min(data)
    image = bytes(data.get(a, 0xFF) for a in range(start, max(data) + 1))
    m = BANNER.search(image)
    return (start + m.start(), m.group()) if m else None


def same_loader(pyocd, conn, path):
    """True when the chip holds the loader version found in path."""
    found = banner_in_hex(path)
    if not found:
        return False
    addr, want = found
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        cmd = [pyocd, "commander"] + conn + ["-c", "savemem 0x%x %d %s" % (addr, len(want), tmp)]
        if subprocess.call(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
            return False
        with open(tmp, "rb") as f:
            return f.read() == want
    finally:
        os.remove(tmp)


def main():
    pyocd = shutil.which("pyocd")
    if not pyocd:
        sys.exit("pyOCD not found. Install it with 'pip install pyocd pylink-square', then restart the IDE.")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-u")
    parser.add_argument("-f")
    parser.add_argument("--target")
    parser.add_argument("--if-changed")
    opts, files = parser.parse_known_args()
    conn = []
    for name, flag in (("u", "-u"), ("f", "-f"), ("target", "--target")):
        if getattr(opts, name):
            conn += [flag, getattr(opts, name)]

    if opts.if_changed:
        if same_loader(pyocd, conn, opts.if_changed):
            print("The Arduino firmware on the board is up to date; uploading the sketch only.", flush=True)
        else:
            print("Uploading the Arduino firmware and the sketch.", flush=True)
            files = [opts.if_changed] + files

    # no stdin: with several probes pyOCD asks which one, and the IDE cannot answer
    code = subprocess.call([pyocd, "load"] + conn + files, stdin=subprocess.DEVNULL)
    if code != 0:
        sys.exit("Upload failed. If several debug probes are connected, choose one in Tools > Port.")
    print("Upload finished.")


if __name__ == "__main__":
    main()
