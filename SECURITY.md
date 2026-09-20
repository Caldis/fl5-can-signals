# Security and privacy

## Reporting a problem with this repository's contents

Open a **private security advisory** through GitHub: go to the Security tab of this repository and choose «Report a vulnerability». Please use that channel rather than a public issue if the report itself would expose the problem.

Please report it if you find:

- **personal or vehicle-identifying data** that should not be here — a VIN, an ECU serial number, a MAC address, a name, an email address, a location or anything that identifies an individual car or person;
- **content that could be misused** — anything that amounts to a way around security access, a write/flash procedure, or a route to disabling a safety system.

Both are treated as defects and will be removed. Because git keeps history, a removal may require a history rewrite; say so in your report if the content is sensitive enough to need that.

## What this repository deliberately does not contain

- No VIN, no ECU serial numbers, no per-vehicle identifiers, no device addresses, no personal data.
- No raw capture logs.
- Nothing about security access (`27`), memory reads (`23`), writes (`2E`), routine control (`31`), ECU reset (`11`) or clearing diagnostic information (`14`).

## Scope

This repository is documentation and data. It ships no service and no runtime component; `tools/validate.py` only reads files in this repository. Vulnerability reports about vehicles, ECUs or third-party tools belong with their vendors, not here.
