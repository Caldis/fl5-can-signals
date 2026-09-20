#!/usr/bin/env python3
"""Validate this repository's published data. MIT licensed, see LICENSE-CODE.

Checks, all of them offline and read-only:
  1. every JSON file parses;
  2. the CSV and the JSON signal list agree row for row;
  3. the OBDb signalset only contains high/medium signals, and its bix/len round-trips
     back to the byte offset, size and bit mask of the matching CSV row;
  4. scale factors in the signalset reproduce the CSV values bit for bit;
  5. no VIN, MAC address, e-mail address, private IP or machine path appears anywhere.

Usage: python tools/validate.py
Exit code 0 when everything passes, 1 otherwise; a JSON summary is printed either way.
"""
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNITS = json.loads((ROOT / "tools" / "obdb-units.json").read_text(encoding="utf-8"))
PATH_ROOTS = set(UNITS["path_roots"])
UNIT_VALUES = set(UNITS["units"])

FORBIDDEN = [
    (r"\b(?=[A-HJ-NPR-Z0-9]{17}\b)(?=[A-HJ-NPR-Z0-9]{0,16}[A-HJ-NPR-Z])"
     r"(?=[A-HJ-NPR-Z0-9]{0,16}\d)[A-HJ-NPR-Z0-9]{17}\b", "looks like a VIN"),
    (r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "looks like a MAC address"),
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "looks like an e-mail address"),
    (r"(?i)\b[a-z]:[\\/](?:users|home)\b", "machine path"),
    (r"(?i)(?:^|[^\w])/(?:Users|home)/[A-Za-z0-9._-]+", "machine path"),
    (r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "private or loopback IP"),
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "private IP"),
    (r"[\w/\\.-]+\.log\b", "raw capture log file name"),
]
TEXT_SUFFIXES = {".md", ".json", ".csv", ".yml", ".yaml", ".cff", ".py", ".txt"}
# validate.py carries the redaction patterns themselves, so it cannot be scanned with them.
SKIP = {"LICENSE", "LICENSE-CODE", "validate.py"}


def problems():
    found = []
    signals = json.loads((ROOT / "data" / "signals.json").read_text(encoding="utf-8"))
    signalset = json.loads((ROOT / "signalsets" / "v3" / "default.json").read_text(encoding="utf-8"))
    with (ROOT / "data" / "signals.csv").open(encoding="utf-8", newline="") as handle:
        table = list(csv.DictReader(handle))

    if len(table) != len(signals["signals"]):
        found.append(f"signals.csv has {len(table)} rows, signals.json has {len(signals['signals'])}")
    for row, entry in zip(table, signals["signals"]):
        for field in ("name", "did", "module_address", "confidence", "unit", "endian"):
            if row[field] != str(entry[field]):
                found.append(f"{entry['name']}: {field} differs between CSV and JSON")
        if int(row["offset"]) != entry["offset"] or int(row["size_bytes"]) != entry["size_bytes"]:
            found.append(f"{entry['name']}: offset/size differ between CSV and JSON")

    by_position = {}
    for entry in signals["signals"]:
        offset, size = entry["offset"], entry["size_bytes"]
        mask = int(entry["bit_mask"], 16) if entry["bit_mask"] else 0
        if mask:
            low = (mask & -mask).bit_length() - 1
            high = mask.bit_length() - 1
            key = (offset * 8 + (size * 8 - 1 - high), high - low + 1)
        else:
            key = (offset * 8, size * 8)
        by_position[(entry["module_address"][2:], entry["did"][2:]) + key] = entry
    seen = set()
    for command in signalset["commands"]:
        if not re.fullmatch(r"[0-9A-F]{3,4}", command["hdr"]):
            found.append(f"{command['hdr']}: not a hexadecimal header")
        if list(command["cmd"]) != ["22"]:
            found.append(f"{command['hdr']}: only service 22 is expected in this signalset")
        for signal in command["signals"]:
            if signal["id"] in seen:
                found.append(f"{signal['id']}: duplicate signal id")
            seen.add(signal["id"])
            bix, length = signal["fmt"]["bix"], signal["fmt"]["len"]
            entry = by_position.get((command["rax"], command["cmd"]["22"], bix, length))
            if entry is None:
                found.append(f"{signal['id']}: bix/len does not match any row in signals.json")
                continue
            if entry["confidence"] not in ("high", "medium"):
                found.append(f"{signal['id']}: confidence {entry['confidence']} must not be in the signalset")
            if signal["fmt"].get("unit") not in UNIT_VALUES:
                found.append(f"{signal['id']}: unit {signal['fmt'].get('unit')!r} is not an OBDb unit")
            if signal["path"].split(".")[0] not in PATH_ROOTS:
                found.append(f"{signal['id']}: path root {signal['path']!r} is not an OBDb path root")
            offset, last = bix // 8, bix + length - 1
            size = last // 8 - offset + 1
            shift = size * 8 - 1 - (last - offset * 8)
            mask = ((1 << length) - 1) << shift
            if offset != entry["offset"] or size != entry["size_bytes"]:
                found.append(f"{signal['id']}: bix/len does not round-trip to offset {entry['offset']}")
            expected = int(entry["bit_mask"], 16) if entry["bit_mask"] else (1 << (size * 8)) - 1
            if mask != expected:
                found.append(f"{signal['id']}: bit mask does not round-trip")
            scale = signal["fmt"].get("mul", 1) / signal["fmt"].get("div", 1)
            if scale != float(entry["scale"]) or signal["fmt"].get("add", 0) != entry["add"]:
                found.append(f"{signal['id']}: mul/div/add does not reproduce scale {entry['scale']}")
            if signal["fmt"].get("unit") == "offon" and length != 1:
                found.append(f"{signal['id']}: a multi-bit field must not use the offon unit")

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.name in SKIP:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, why in FORBIDDEN:
            hit = re.search(pattern, text)
            if hit:
                found.append(f"{path.relative_to(ROOT).as_posix()}: {why} ({hit.group(0)!r})")
    return found


def main():
    found = problems()
    print(json.dumps({"ok": not found, "status": "passed" if not found else "failed",
                      "problems": found}, ensure_ascii=False, indent=2))
    return 0 if not found else 1


if __name__ == "__main__":
    sys.exit(main())
