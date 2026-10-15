#!/usr/bin/env python3
# Copyright (c) 2026 KORLINX
# SPDX-License-Identifier: Apache-2.0

"""Build package_korlinx_index.json for the Arduino Boards Manager.

Usage: extra/gen_korlinx_index.py BASE_URL CORE_ARCHIVE > package_korlinx_index.json

BASE_URL is where the archive is published (e.g. a GitHub release download URL).
The platform entry comes from extra/gen_package_index_json.sh.
"""

import hashlib
import json
import os
import re
import subprocess
import sys


def archive_info(path, base_url):
    data = open(path, "rb").read()
    name = os.path.basename(path)
    return {
        "url": f"{base_url}/{name}",
        "archiveFileName": name,
        "checksum": "SHA-256:" + hashlib.sha256(data).hexdigest(),
        "size": str(len(data)),
    }


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base_url = sys.argv[1].rstrip("/")
    core_archive = sys.argv[2]

    out = subprocess.run(["extra/gen_package_index_json.sh", "korlinx", core_archive],
                         check=True, capture_output=True, text=True).stdout
    platform = json.loads(out)["packages"][0]["platforms"][0]
    platform.update(archive_info(core_archive, base_url))
    # package_core.sh names the archive <artifact>-<version>.tar.bz2; keep the index in step with it
    m = re.fullmatch(r"korlinx-(.+)\.tar\.bz2", os.path.basename(core_archive))
    if not m:
        sys.exit(f"unexpected core archive name: {core_archive}")
    platform["version"] = m.group(1)
    platform["help"] = {"online": "https://github.com/KORLINX"}

    index = {"packages": [{
        "name": "korlinx",
        "maintainer": "KORLINX",
        "websiteUrl": "https://github.com/KORLINX",
        "email": "",
        "help": {"online": "https://github.com/KORLINX"},
        "platforms": [platform],
        "tools": [],
    }]}
    json.dump(index, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
