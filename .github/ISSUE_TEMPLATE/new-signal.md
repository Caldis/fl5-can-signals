---
name: New signal
about: Propose a signal to add to the reference
title: "[signal] <module>:<DID>[<offset>] — what it is"
labels: ["new signal"]
---

<!-- Before you post: remove the VIN and any ECU serial numbers from anything you attach. -->

## Where

- Module address (e.g. `0x10`):
- DID (e.g. `0x2610`):
- Byte offset into the data area (after the `62 + DID` echo):
- Width in bytes / bit mask:
- Endianness, signed or unsigned:

## Decoding

- `value = raw × <scale> + <add>`, unit:
- How the scale and offset were derived:

## Evidence

- Proposed confidence (`high` / `medium` / `low`):
- What it was compared against, and how closely it agreed:
- What would have disproved it, and what you found when you looked:

## Your car

- Model year / market / transmission:
- ECU stock or tuned:
