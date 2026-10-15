# Copyright (c) 2026 KORLINX
# SPDX-License-Identifier: Apache-2.0

import json
import shutil
import subprocess
import sys
import threading

POLL_SECONDS = 3

lock = threading.Lock()
ports = []
stop = None
worker = None


def send(msg):
    with lock:
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


def probe_ports(boards):
    """Turn the "boards" list of `pyocd json --probes` into ports."""
    result = []
    for b in boards:
        uid = b.get("unique_id")
        if not uid:
            continue
        product = " ".join(p for p in (b.get("vendor_name"), b.get("product_name")) if p) or b.get("info") or "Debug probe"
        props = {"serialNumber": uid, "product": product}
        # a CMSIS-DAP board such as a DAPLink can name its target; J-Link only reports "cortex_m"
        if b.get("target") and b.get("target") != "cortex_m":
            props["target"] = b["target"]
        if b.get("board_name") and b.get("board_name") != "Generic":
            props["board"] = b["board_name"]
        result.append({
            "address": uid,
            "label": product + " " + uid,
            "protocol": "pyocd",
            "protocolLabel": "Debug probes (pyOCD)",
            "properties": props,
            "hardwareId": uid,
        })
    return sorted(result, key=lambda p: p["address"])


def scan():
    pyocd = shutil.which("pyocd")
    if not pyocd:
        return []
    try:
        out = subprocess.run([pyocd, "json", "--probes"], capture_output=True, text=True, timeout=20).stdout
        # pyOCD may print log lines after the JSON object
        return probe_ports(json.loads(out[:out.rfind("}") + 1]).get("boards", []))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def poll(events, halted):
    global ports
    known = {}
    while not halted.is_set():
        current = scan()
        if halted.is_set():
            return
        with lock:
            ports = current
        if events:
            now = {p["address"]: p for p in current}
            for addr, p in known.items():
                if addr not in now:
                    send({"eventType": "remove", "port": {"address": addr, "protocol": p["protocol"]}})
            for addr, p in now.items():
                if addr not in known:
                    send({"eventType": "add", "port": p})
            known = now
        halted.wait(POLL_SECONDS)


def start(events):
    global stop, worker
    stop = threading.Event()
    worker = threading.Thread(target=poll, args=(events, stop), daemon=True)
    worker.start()


def halt():
    """Stop scanning and wait for it, so no event follows the reply."""
    global stop, worker, ports
    if stop:
        stop.set()
        worker.join()
        stop = worker = None
        with lock:
            ports = []


def main():
    global ports
    helloed = False
    for line in sys.stdin:
        fields = line.split()
        if not fields:
            continue
        cmd = fields[0].upper()
        event = cmd.lower()
        if not helloed and cmd not in ("HELLO", "QUIT"):
            send({"eventType": event, "error": True, "message": "HELLO must be sent first"})
        elif cmd == "HELLO":
            if helloed:
                send({"eventType": event, "error": True, "message": "HELLO already received"})
            elif len(fields) < 2 or not fields[1].isdigit() or int(fields[1]) < 1:
                send({"eventType": event, "error": True, "message": "invalid protocol version"})
            else:
                helloed = True
                send({"eventType": event, "protocolVersion": 1, "message": "OK"})
        elif cmd in ("START", "START_SYNC"):
            if stop:
                send({"eventType": event, "error": True, "message": "already started"})
                continue
            events = cmd == "START_SYNC"
            if not events:
                with lock:
                    ports = scan()  # so LIST right after START isn't empty
            send({"eventType": event, "message": "OK"})  # must precede the first add
            start(events)
        elif cmd == "LIST":
            if not stop:
                send({"eventType": event, "error": True, "message": "START must be sent before LIST"})
                continue
            with lock:
                current = list(ports)
            send({"eventType": event, "ports": current})
        elif cmd == "STOP":
            if not stop:
                send({"eventType": event, "error": True, "message": "already stopped"})
                continue
            halt()
            send({"eventType": event, "message": "OK"})
        elif cmd == "QUIT":
            halt()
            send({"eventType": event, "message": "OK"})
            return
        else:
            send({"eventType": "command_error", "error": True, "message": "command " + fields[0] + " not supported"})
    halt()


if __name__ == "__main__":
    main()
