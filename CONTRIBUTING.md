# Contributing

Thanks for wanting to add to this. The value of this repository is not the number of signals in it — it is that **every line can be traced to evidence, and the weak ones say so**. Please keep it that way.

## Before anything else: scrub your logs

**Never attach a raw capture without redacting it first.** A diagnostic log from your own car very likely contains:

- the **VIN** (the response to `22 F190`, 17 ASCII characters — Honda VINs start with `JH`),
- **ECU serial numbers** (responses to `22 F18C` and some `F1xx` identifiers),
- anything else unique to your individual car.

Part numbers (`22 F181` / `F110`, e.g. `37805-66V-H020`) are shared by every car of the same build and are fine to post. Per-vehicle identifiers are not. If you are unsure, post the decoded values and the byte offsets rather than the raw log.

Pull requests and issues that contain a VIN or a serial number will be closed and the content removed.

## Adding a signal

Open a «New signal» issue, or a pull request against `data/signals.csv`, with:

1. **Where**: module address, DID, byte offset, width, endianness, signedness, and the mask if it is a bit field. Offsets are into the data area, after the `62 + DID` echo.
2. **Decoding**: `scale` and `add`, and how you arrived at them.
3. **Evidence**, which decides the confidence level:
   - `high` — a sample-by-sample match against an independent reference (a gauge, a display, a datalogger export), or a deliberate action with a clean before/after and a control.
   - `medium` — reproducible, but resting on one observation, an assumed scale, an inferred ordering, or an unverified public source.
   - `low` — a candidate: the position and the shape are real, the identity or the scale is not.
   Correlation on its own is never enough. Over ten minutes of idling every slow quantity correlates with every other one.
4. **Your car**: model year, market, transmission, and whether the ECU is stock or tuned. A signal that only holds on a tuned ECU is still worth having — it just has to say so.
5. **A counter-example search**: say what you looked for that would have disproved it, and what you found. «I did not find a counter-example» is a result; «I did not look» is not.

## Disproving something

Counter-evidence is as welcome as new signals, and easier to act on. Open a «Counter-evidence» issue with the claim you are disproving, the data that contradicts it, and — if you can — what the correct reading is. Refuted claims are not deleted from this repository; they move to the refuted section together with what went wrong, because that is useful to the next reader.

## What will not be accepted

- Anything relying on security access (`27`), memory reads (`23`), writes (`2E`), routines (`31`), ECU reset (`11`) or DTC clearing (`14`), or on defeating any of them.
- Redistributed manufacturer documentation, firmware, calibration files or proprietary protocol material.
- Procedures that require a driver to operate equipment while the car is moving.
- Confidence upgrades without new evidence.

## Note on the files

`README.md`, `README.zh-CN.md`, `data/signals.json`, `data/signals.csv` and `signalsets/v3/default.json` are **generated together** from one decode table, so a change has to be consistent across all of them — `tools/validate.py` checks that, and CI runs it on every push. If editing them by hand gets awkward, just open an issue with the evidence and the maintainer will regenerate.

By contributing you agree that your documentation and data contributions are licensed under CC BY-SA 4.0 and your code contributions under the MIT licence.
