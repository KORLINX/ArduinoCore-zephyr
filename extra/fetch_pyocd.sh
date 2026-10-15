#!/bin/bash
# Copyright (c) 2026 KORLINX
# SPDX-License-Identifier: Apache-2.0
#
# Usage: extra/fetch_pyocd.sh VERSION OUT_DIR
#
# Downloads the official pyOCD builds (github.com/pyocd/pyOCD releases) and
# repacks them unchanged as OUT_DIR/pyocd-VERSION-<host>.tar.bz2 for the
# Boards Manager. The official zips have no top folder, which the Arduino
# CLI cannot install, so the files are put under pyocd/.
# Intel Macs are left out: pyOCD publishes no x86_64 macOS build.

set -e

VERSION=$1
OUT=$2
[ -n "$VERSION" ] && [ -n "$OUT" ] || { echo "usage: $0 VERSION OUT_DIR" >&2; exit 1; }
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

for pair in linux:x86_64-linux-gnu linux-arm64:aarch64-linux-gnu macos:arm64-apple-darwin windows:x86_64-mingw32; do
	name=${pair%%:*}
	host=${pair#*:}
	curl -fsSL -o "$TMP/$name.zip" "https://github.com/pyocd/pyOCD/releases/download/v$VERSION/pyocd-$name-$VERSION.zip"
	mkdir -p "$TMP/$name/pyocd"
	unzip -q "$TMP/$name.zip" -d "$TMP/$name/pyocd"
	tar -C "$TMP/$name" --owner=0 --group=0 --numeric-owner --sort=name -cjf "$OUT/pyocd-$VERSION-$host.tar.bz2" pyocd
	echo "$OUT/pyocd-$VERSION-$host.tar.bz2"
done
