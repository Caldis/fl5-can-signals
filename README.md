# Honda Civic Type R (FL5) — diagnostic signal reference

25 DIDs / 109 signals read over OBD-II with UDS service 22: offsets, decoding, units, confidence and evidence.

[简体中文](README.zh-CN.md)

This reference was assembled from eight on-car capture sessions on one Honda Civic Type R (FL5, K20C1 2.0T, 6-speed manual) between 2026-09-08 and 2026-09-16, plus all the offline analysis that followed. Everything here came from **read-only diagnostics**. Nothing came from flashing, security access or memory reads.

It states what was observed **on that one car**, and labels every line with a confidence level. **High confidence does not mean independently calibrated, and it does not mean it holds on a stock car** — the car carries a Hondata FlashPro (unlocked and tuned ECU) and its market version was never confirmed. Verify before you rely on any of this on another vehicle.

**Licence:** documentation and data CC BY-SA 4.0, code MIT · **Attribution:** Caldis

> This document is generated from one decode table plus one hand-maintained supplement; the tables are not written by hand. Generator and validator live in `tools/`.

## 1. Read this first: these are not broadcast CAN frames

**This car has a gateway behind the OBD-II connector, and no periodic broadcast frames reach it.** A 24.8-minute passive capture on the first session recorded 590,000 frames across 16 CAN IDs — every one of them a `18DAxxxx` diagnostic frame. Key-on, idle and driving all produced zero broadcast frames. So every number in this document was obtained by **asking and being answered**: the positive-response bytes of UDS service `22` (ReadDataByIdentifier).

That is why the primary key here is «**module address + DID + byte / bit position**», not a CAN ID. Four (decoded) ECUs share one physical channel and are told apart by the target address inside the 29-bit ID.

**A DBC file is the wrong primary format for this.** DBC describes the layout of periodically broadcast frames, and there are none to describe. For machine consumption use `data/signals.json` / `data/signals.csv`, or the OBDb-compatible `signalsets/v3/default.json`.

## 2. The car, and what the scope of this is

| Item | Detail |
|---|---|
| Vehicle | Honda Civic Type R **FL5**, K20C1 2.0T turbo, 6-speed manual |
| Model year / market | **Not confirmed** (privately imported). This document does not guess the model year and does not assume the software matches any one market's stock build. |
| ECU state | Fitted with a Hondata FlashPro: **the ECU is unlocked and tuned**. Known consequence: on this car the default session reads every tested DID with no handshake at all — **that cannot be extrapolated to a stock car**. |
| ECU software / calibration ID | Not compared. Part numbers for each module were read (see the module table); read yours with `22 F110` / `F112` / `F181` and compare. |
| Capture span | 2026-09-08 to 2026-09-16, eight on-car sessions; 105 logs entered the statistics, roughly 540,000 diagnostic transactions (277,000 positive responses). |

**The scope of every claim here is: this one car.** The public OBDb Honda-Civic signal set confirms that stock Civics answer `2610` / `2611`; the oil-temperature DID `268F` has **no external corroboration whatsoever** and is the highest-risk item in this document. The no-handshake behaviour was likewise only ever verified on this car.

Evidence in the other direction: several conclusions here agree with the public OBDb Civic entries (brake pressure, brake switch, fuel level, odometer, run time, knock, lambda), and two errors in that public archive were found in the process (see the refuted list).

## 3. Quick start

Read one DID and decode one signal. The example below reads engine oil temperature (`ECM 0x10`, DID `0x268F`, data byte 15, `raw − 40 °C`) with [python-can](https://python-can.readthedocs.io) and the ISO-TP helper of your choice. **It only ever sends service `22`.**

```python
# pip install can-isotp python-can
import isotp, can

bus = can.interface.Bus(channel="can0", interface="socketcan", bitrate=500000)
addr = isotp.Address(isotp.AddressingMode.Normal_29bits,
                     txid=0x18DA10F1, rxid=0x18DAF110)   # request -> ECM, response <- ECM
stack = isotp.CanStack(bus, address=addr, params={"tx_padding": 0x55, "blocksize": 0, "stmin": 0})

stack.send(bytes([0x22, 0x26, 0x8F]))                   # ReadDataByIdentifier 0x268F
payload = stack.recv(block=True, timeout=1.0)           # 62 26 8F <54 data bytes>
data = payload[3:]                                      # strip the 62 + DID echo: offset 0 == data[0]
print("oil temperature:", data[15] - 40, "degC")
```

Three things will bite you if you skip them:

- **Answer the flow control frame immediately.** Responses are 54–63 bytes, so they arrive as a first frame plus 8–9 consecutive frames. The tester must send `30 00 00` within a few milliseconds or this ECU gives up on the transfer.
- **Pad requests to 8 bytes** (this car's tester uses `0x55` for requests and `0xAA` for flow control).
- **Offsets in this document start after the `62 + DID` echo.** `[a:b]` excludes `b`, and `value = raw × scale + add`.

No session control and no security access is needed on the car this was captured from. That is a property of *that* car (unlocked ECU) and may not hold on yours; if a read is refused, do not go looking for a way around it — see the safety section.

## 4. How the data is read: addressing, services, timing and budget

| Layer | Fact |
|---|---|
| Physical | OBD-II connector: pin 6 CAN-H, pin 14 CAN-L, pin 4 GND, pin 16 permanent 12 V. **Count 6 / 14 from the orientation of the male plug going into the car** — counting from the wrong side yields zero frames. |
| Link | Classical CAN 2.0B, 500 kbit/s, ≤8 data bytes per frame, **no CAN FD** (12 logs, ~1.9 M frames, FD frame count 0). This only characterises the OBD side of the gateway. |
| Addressing | 29-bit ISO 15765 physical addressing: request `18DA<target>F1`, response `18DAF1<target>`; the tester address is fixed at `F1`. Functional broadcast `18DB33F1` enumerates the car. Mode 01 on 11-bit `7DF` / `7E0` draws no response at all. |
| Transport | ISO 15765-2: the request is a single frame `03 22 <DID hi> <DID lo>` padded to 8 bytes with `0x55`; the response is a 54–63 byte data area delivered as a first frame plus 8–9 consecutive frames. **Flow control `30 00 00` (padded with `0xAA`) must be sent within a few milliseconds or the ECU abandons the transfer.** |
| Application | UDS service `22` ReadDataByIdentifier. On this car the default session needs no handshake (no `10 03`, and certainly no `27`); `3E` tester-present was measured to be unnecessary (600 s of continuous sampling, zero errors). **Verified on this car only.** |
| Offset convention | Offsets in this document are into the data area **after stripping the `62 + DID` echo**; `[a:b]` excludes `b`; `value = raw × scale + add`. Big-endian unless the row says little. |

### 4.1 Time per transaction (tester-side observations, not ECU hard limits)

| Module / DID | request→complete p50 | p95 | consecutive-frame gap |
|---|---:|---:|---|
| ECM `10:2610` | 24.9 / 27.4 ms | 30.7 / 30.6 ms | ≈2 ms |
| ECM `10:2611` | 29.3 ms | 33.5 ms | ≈2 ms |
| ECM `10:268F` | 27.3 ms | 29.8 ms | ≈2 ms |
| VSA `28:4001/4004/4007/4073` | ≈100.1 ms | ≈100.6 ms | ≈10 ms |
| EPS `30:48BD/48C0/48C4` | ≈67.9 ms | ≈69 ms | ≈8 ms |

**These are tester-side observations, not ECU hard limits.** The often-quoted «VSA 80 ms» is the span from first frame to last frame, not an inter-frame gap, and it cannot be claimed as an STmin floor (the adapter used has no hardware timestamps).

**The serial model holds**: over 2,051 polling rounds the per-round identity `period = Σ(request→complete) + Σ(gaps)` has zero residual, with 1.48 ms of per-round overhead. That gives a **single-ECU serial ceiling of roughly 1 s / 30.5 ms ≈ 33 Hz (for the ECM)**. Cross-module concurrency is allowed by the protocol (one outstanding request per address) but was **never verified on this car**; summing per module and taking the maximum is only about 28% faster than strict serial, not the 10× some people expect.

For comparison: the tuning tool polls `22 2610` and `22 2611` at **18.13 Hz** each.

Two capture rules learned the hard way: ① a single timed-out request gets that address isolated, so put the most reliable DID first in a sampling group; ② **do not interleave a DID scan with continuous sampling on one serial chain while the car is moving** — a log that scanned while driving lost up to 7.891 s of continuous sampling in one gap, while a sampling-only log lost at most 1.244 s.

### 4.2 Negative responses seen

| NRC | Meaning | Observed on this car |
|---|---|---|
| `0x31` | requestOutOfRange (no such DID) | the dominant negative response while scanning; by far the most common in the archive |
| `0x11` | serviceNotSupported | service `21` (256 local identifiers across five modules) and service `24` both return it everywhere — unsupported on this car, not worth retrying |
| `0x22` | conditionsNotCorrect | handled; appears occasionally during scans |
| `0x78` | requestCorrectlyReceived-ResponsePending | handled (up to 5 × timeout). Not counted as a negative response in the archive statistics |
| `0x80` | manufacturer-specific / not in the standard table | seen once while scanning the ECM on session 2 |

## 5. Modules and scan coverage

| Address | Identity | Part number | UDS 22 scan coverage | DIDs answering | In this reference | Status |
|---|---|---|---|---|---|---|
| `0x10` | ECM/PCM engine control | 37805-66V-H020 | `0000–FFFF` complete | 77 (52 in 26xx, 5 in 30xx, 20 in the DC59–FFFF range) | 10 DIDs | done; three isolated points (6F2B / 6F8A / DC58) timed out during the scan and were not re-read |
| `0x28` | VSA stability control (ABS/ESC) | 57114-T60-AA20 | `0000–A082` | 31 (4000–400A, 4030–403B, 4070–4073, 0EEC, 4100, 48AF, 48F5) | 5 DIDs | A083–FFFF not scanned |
| `0x30` | EPS electric power steering | 39990-T60-J030 | `0000–7EEB` | 20 (all in 48xx) | 5 DIDs | a re-scan of 0000–2A30 found nothing new; 2A31–FFFF outstanding |
| `0x3A` | ADS adaptive damper system (part-number family 39390, inferred) | 39390-31M-A040 | `0000–FFFF` complete | 16 (48AF, 48F5, 52xx, 5280/5281, E600, E602, F1xx) | 0 DIDs | done; 9 of its 10 data DIDs are byte-for-byte constant, and the one live DID `520A` is undecoded |
| `0x53` | SRS airbags | 77959-T60-H830 | not scanned | — | 0 DIDs | **deliberately left alone** (restraint system) |
| `0x60` | Instrument cluster | 78108-T60-H020 | `7000–70FF` | 18 (6 of them carry data) | 5 DIDs | the rest of the DID space was not scanned |
| `0x70` | Unknown (part-number family 33137, possibly headlight control) | 33137T24Y112M1 | not scanned | — | 0 DIDs | answers the functional broadcast |
| `0xB0` | Multi-purpose camera (Honda Sensing) | 36161-T60-H050 | `0000–00C5` | 0 | 0 DIDs | largely uncooperative to service 22; both attempts hit a timeout inside 00xx and got the address isolated. Abandoned |
| `0xB3` | Honda Sensing sub-unit | 36162-T51-H010 | not scanned | — | 0 DIDs | answers the functional broadcast |
| `0xB7` | Parking sensor control unit | 39670T60E010M1 | not scanned | — | 0 DIDs | answers the functional broadcast |
| `0xED` | Body control / gateway, one of two (family 38898) | 38898-T60-H010 | not scanned | — | 0 DIDs | pairs with EF |
| `0xEF` | Gateway / body control, one of two (family 38897) | 38897-T60-H010 | not scanned | — | 0 DIDs | first to answer the functional broadcast; probably the gateway |

Part numbers were read with `22 F181` / `22 F110`. These are **part numbers shared by every car of the same build**, not per-vehicle serial numbers. This repository contains no VIN, no ECU serial number and no other per-vehicle identifier.

Addresses present in the public OBDb Civic table that produced **no answer** to the functional broadcast `18DB33F1` on this car: `0x2A`, `0x0E`, `0x11`, `0x1D`, `0x01`, `0x15`, `0x16`.

Scanning the cluster `0x60`, the gateway pair `ED`/`EF` and `0x70` at a 5 ms request interval was followed by the entire diagnostic link going quiet for 5–7 seconds, every module at once. **The correlation is strong; the mechanism is not established** — «one ECU is busy» is ruled out (the whole archive contains only NRC `0x31` and `0x11`; `0x21` and `0x78` never occur), while gateway rate-limiting, an ISO-TP fault, the capture tooling itself and a silently timing-out scan request holding the channel are all under-evidenced. If you want to scan those modules, do it separately at ≥50 ms intervals.

## 6. Data dictionary: files and fields

`data/signals.csv` and the `signals[]` array of `data/signals.json` carry one row per signal with these fields:

| Field | Meaning |

|---|---|

| `module_address` | Diagnostic target address, e.g. `0x10`. Request ID is `18DA<address>F1`, response `18DAF1<address>`. |
| `module` | Human name of that ECU. |
| `did` | The data identifier read with service `22`. |
| `response_length` | Length in bytes of the data area, i.e. the positive response minus the `62 + DID` echo. |
| `name` / `name_en` | Stable identifier for the signal, and its English display name. |
| `offset` | Byte offset into the data area (offset 0 = first byte after the `62 + DID` echo). |
| `size_bytes` | Width of the field in bytes before any mask is applied. |
| `bit_mask` | Present only for bit fields; the mask applies to the `size_bytes` integer assembled per `endian`, and is **not** shifted down. |
| `bit_length` | Width in bits (`size_bytes × 8` when there is no mask). |
| `endian` | `big` or `little` for multi-byte fields. |
| `signed` | Whether the raw integer is two's complement. |
| `scale` / `add` | `value = raw × scale + add`. |
| `unit` | Unit of the decoded value, as recorded by the research. `unresolved`, `?` and `raw` mean the physical unit is genuinely not established. |
| `value_min` / `value_max` | Theoretical range of the decoded value over the full raw range. **Not** a measured range and **not** an operating limit. |
| `observed_samples` / `observed_min` / `observed_max` | Sample count and extremes actually seen across the whole capture archive. Empty when the signal was never sampled. For masked bit fields these are the **masked raw values**, not 0/1. |
| `confidence` | `high` / `medium` / `low`, exactly as recorded in the decode table. See below. |
| `evidence` | One line saying what the confidence rests on. |
| `source_report` | Which capture session or analysis first established it. |
| `enum` | Value → meaning map, where one is known. |

Confidence means strength of evidence on this one car, nothing more:

- **`high`** — matched point by point against an independent display, or fitted column by column against the tuning tool's unrounded export to r≈1, or tied to a deliberate physical action with a clean before/after. Still **not** independently calibrated, and **not** verified on a stock car.
- **`medium`** — consistent and reproducible, but resting on a single observation, an assumed scale, an inferred ordering, or a public source that was not fully verified here.
- **`low`** — a candidate. The position and the shape of the data are real; the physical identity, the scale or both are not established. Do not build anything on these.

- `data/signals.json` — the complete export (everything structured in this document: modules, signals, candidates, not-identifiable items, refuted claims, limits, safety notes, data version).
- `data/signals.csv` — the signal table in tabular form; the fields are documented above.
- `signalsets/v3/default.json` — a signalset compatible with [OBDb](https://github.com/OBDb) `signalsets/v3`. **Only `high` and `medium` confidence signals are included**; low-confidence and candidate entries stay in this document and out of the signalset. Bit positions use OBDb's MSB0 convention (`byte = bix // 8`, `bit = 7 − (bix % 8)`), scale factors are expressed as `mul` / `div`, and units use OBDb's enumeration — where no enumeration value fits, the unit is recorded as `unknown` and the real unit is stated in `description`.

All three are produced from the same sources; `tools/validate.py` checks that they agree with each other, and CI runs it on every push.

## 7. Signal tables (by module → DID → offset)

4 modules, 25 DIDs, 109 signals: 52 high, 39 medium, 18 low / candidate.

**Confidence is reproduced verbatim from the decode table — never promoted, never demoted.**

`high` means the evidence on this car is strong: matched point by point against an independent display, fitted to r≈1 against the tuning tool's unrounded export, or tied to a deliberate action. It does **not** mean independently calibrated, and it does **not** mean it holds on a stock car.

«Observed range» is the minimum and maximum actually seen across the capture archive, with the sample count (no mean is kept). It says **what has been seen**, and defines neither an operating range nor a warning threshold. Empty means the signal was never sampled.

### 0x10 ECM/PCM engine control — `0x2610` (54-byte data area)

The ECM's main data packet; the tuning tool polls it at 18.13 Hz. Oil pressure and boost both come from this response.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ENGINE_RPM` | Engine RPM | 6 | 2 B | big | unsigned | raw × 0.25 | rpm | 0 … 5300 (53908) | high | r = 0.99999984 against the tuning tool's RPM column | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `MAP_ABS` | Manifold absolute pressure | 9 | 2 B | big | unsigned | raw × 0.0078125 | kPa | 22.2734375 … 282.3515625 (53908) | high | matches the tuning tool's MAP column; a 282 kPa absolute peak under full boost lines up with the in-car display reading 1.83 bar gauge | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `ECT` | Engine coolant temperature | 11 | 1 B | big | unsigned | raw − 40 | degC | 33 … 90 (53908) | high | agrees item by item with the in-car coolant temperature display | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `IAT` | Intake air temperature | 13 | 1 B | big | unsigned | raw − 40 | degC | 33 … 65 (53908) | high | matches the tuning tool's IAT column | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `MAP_RELATED_B14` | MAP-related byte 14 (candidate) | 14 | 1 B | big | unsigned | raw × 1.579 − 19.76 | kPa | 22.873 … 278.671 (53908) | low / candidate | not integer kPa and not linear over the full range; the fit coefficients change once positive boost is included, with up to ~31 kPa residual | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `MAP_ALT_INT` | Manifold pressure (8-bit) | 15 | 1 B | big | unsigned | raw | kPa | 23 … 255 (53908) | medium | a coarse MAP, r = 0.995 against the 16-bit one; saturates at 255 under high boost, so the 8-bit range is insufficient | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `BARO` | Barometric pressure | 17 | 1 B | big | unsigned | raw | kPa | 100 … 101 (53908) | medium | two integer points on two days (1006 hPa→100, 1009 hPa→101); VSA `4005[21]` carries the same value | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `VEHICLE_SPEED` | Vehicle speed | 18 | 1 B | big | unsigned | raw | km/h | 0 … 137 (53908) | high | verified 0–114 km/h; the 0.621 slope against the tool's mph column is exactly the unit conversion | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `LOAD_ALT` | Engine load (candidate) | 19 | 1 B | big | unsigned | raw × 0.7615 + 2.46 | flashpro_AIRC_unit | 2.46 … 187.5045 (53908) | low / candidate | r = 0.98 against air charge, nature undetermined. It is currently the single best gating proxy for `2610[39]`, but very likely derives from the same internal load quantity, so it is not independent evidence | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `IGN_ADVANCE` | Ignition advance | 21 | 1 B | big | unsigned | raw × 0.5 − 64 | deg | -42 … 43.5 (53908) | high | matches the tuning tool's ignition advance column | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `BATTERY_V` | Battery voltage | 22 | 1 B | big | unsigned | raw × 0.1 | V | 6 … 14.6 (53908) | high | 96% of samples agree point for point with the tuning tool | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `INJ_PULSE` | Injector pulse width | 24 | 2 B | big | unsigned | raw × 0.001 | ms | 0 … 39.251 (53908) | high | matches the tuning tool's injector pulse width column | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `FUEL_PUMP_DUTY` | Fuel pump duty | 26 | 2 B | big | unsigned | raw × 0.1111111111111111 | % | 4.444444444 … 111.111111111 (53908) | medium | stands in a 10/9 normalised relation to another channel, which looks more like a pump duty cycle than a low-side fuel pressure | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `AC_REQUEST` | A/C request | 32 | 2 bit (mask 0x3) | big | unsigned | raw & 0x3 | bool | 0 … 3 (53908) | medium | takes 0x00 / 0x01 / 0x03 in the archive: 0x01 with the key on and the engine off, 0x03 about 5 s after start. bit1 is exactly the bit the public signal set points at, **but nobody ever marked the A/C switch, so this stays a candidate** | cross-check against public signal sets (2026-09-14); bit-order correction (2026-09-20) |
| `AIRFLOW` | Mass air flow | 34 | 2 B | big | unsigned | raw × 0.01 | g/s | 0 … 212.91 (53908) | high | r = 0.99996 against the relation AFM.c = 30000·AFM/RPM | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `ECT2` | Slow-response temperature (candidate) | 38 | 1 B | big | unsigned | raw − 40 | degC | 28 … 87 (53908) | low / candidate | r = 1.000 against the tuning tool's ECT2 column, yet within one 292 s file it moves 34→39 °C while coolant goes 58→79 °C — a location with far more thermal inertia | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `BOOST_LOAD_STATE` | Boost load state | 39 | 1 B | big | unsigned | raw | enum | 0 … 2 (53908) | medium | re-checked over the whole archive (31 logs, 53,908 samples, 180 state changes): every non-zero state has MAP_ABS ≥ 100.25 kPa. **A single pressure threshold and a Schmitt hysteresis are both refuted**; state 2 has only 8 independent entries, so its threshold is not identifiable | candidate review (2026-09-18); full-archive re-check (2026-09-20) |
| ↳ enum | 0 = normal, 1 = boosted_load, 2 = high_boost | | | | | | | | | | |
| `AIR_CHARGE_ALT` | Air charge (8-bit) | 40 | 1 B | big | unsigned | raw × 0.3567 − 0.23 | flashpro_AIRC_unit | -0.23 … 90.7285 (53908) | medium | r = 0.99 against the tuning tool's air-charge column; an 8-bit version of it | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `IAT2` | Intake air temperature 2 | 42 | 1 B | big | unsigned | raw − 40 | degC | 28 … 71 (53908) | high | matches the tuning tool's IAT2 column; the physical location is not inferred from the name | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `OIL_PRESSURE_SENSOR_8BIT` | Engine oil pressure (8-bit) | 43 | 1 B | big | unsigned | raw × 3.921 − 148.5 | kPa | 0.498 … 623.937 (53908) | medium | r = 0.99995 against the 16-bit oil pressure, but **its zero is not zero** (raw = 38 at a true 0 kPa), so it cannot be used as a pressure directly | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `OIL_PRESSURE` | Engine oil pressure | 44 | 2 B | big | unsigned | raw | kPa | 0 … 626 (53908) | high | 2,021 samples at zero engine speed read exactly 0 while the same responses carry BARO = 101 and MAP = 100.3, which rules out a dead sensor; idle readings of 241 / 251 against an in-car 252 support a gauge-pressure reading | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `BATTERY_V_HIRES_CANDIDATE` | Battery voltage (high resolution candidate) | 46 | 2 B | big | unsigned | raw × 0.0025 | V | 6.08 … 14.64 (53908) | low / candidate | ≈ raw/400 resembles battery voltage, but r is only 0.87 and it moves over a span of just 1.1 V | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `MAP_MMHG` | Manifold pressure (mmHg scale) | 48 | 2 B | big | unsigned | raw × 0.1 | mmHg | 173.3 … 1920.1 (53908) | medium | r = 0.994 against MAP; the 0.1 mmHg/LSB unit is an **assumption** | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |

### 0x10 ECM/PCM engine control — `0x2611` (63-byte data area)

The ECM's second large packet (combustion / boost / torque), polled alternately with `2610`.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `LAMBDA_ALT` | Lambda (alternate) | 6 | 2 B | big | unsigned | raw × 3.0517578e-05 | lambda | 0.991058346 … 1.021087642 (42797) | medium | only ever moves within 0.997–1.016; possibly a second sensor or a filtered value | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `LAMBDA` | Lambda | 8 | 2 B | big | unsigned | raw × 3.0517578e-05 | lambda | 0.764526364 … 1.999969474 (42797) | high | AFR = λ × 14.7; the public signal set decodes the same bytes as ×29.4/65535 = AFR, which agrees | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `SHORT_TRIM` | Short term fuel trim | 10 | 1 B | big | unsigned | raw × 0.78125 − 100 | % | -10.15625 … 17.96875 (42797) | high | exact coefficient 0.78125·raw − 100 recovered from unrounded values | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `LONG_TRIM` | Long term fuel trim | 11 | 1 B | big | unsigned | raw × 0.78125 − 100 | % | -3.125 … 4.6875 (42797) | high | same encoding as short-term trim | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `LAMBDA_CMD` | Lambda target | 12 | 2 B | big | unsigned | raw × 3.0517578e-05 | lambda | 0.897705074 … 1.999969474 (42797) | high | its difference from measured lambda is the error the closed loop is chasing | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `FUEL_STATUS` | Fuel system status | 14 | 1 B | big | unsigned | raw | enum | 2 … 4 (42797) | high | only the values 2 and 4 have been observed | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `PERCENT_UNKNOWN_B15` | Unknown percentage byte 15 | 15 | 1 B | big | unsigned | raw × 0.39215686274509803 | % | 0 … 18.823529412 (42797) | low / candidate | equals an internal channel of the tuning tool that its CSV export does not expose; identity unknown. **It is definitely not purge** | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `CAM_CMD` | Intake cam phase target | 16 | 1 B | big | unsigned | raw × -0.5 + 53 | deg | -22 … 33 (42797) | high | corrected to 53 − 0.5·raw from unrounded values | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `CAM` | Intake cam phase | 17 | 1 B | big | unsigned | raw × -0.5 + 53 | deg | -22.5 … 34.5 (42797) | high | same encoding; its difference from the command shows the VTC response | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `VTS` | VTEC engaged | 18 | 1 bit (mask 0x1) | big | unsigned | raw & 0x1 | bool | 0 … 1 (42797) | high | 0/2 = off, 1/3 = on (bit0) | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `GEAR` | Gear | 19 | 1 B | big | unsigned | raw | gear | 0 … 6 (42797) | high | 96% agreement with the speed/rpm ratio while driving; 0 means neutral or clutch depressed. **The reverse value has never been seen** — selecting reverse still reads 0 | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `PEDAL` | Accelerator pedal | 20 | 2 B | big | unsigned | raw × 0.005 | % | 0 … 60.825 (42797) | high | accelerator **pedal** position, distinct from throttle | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `THROTTLE` | Throttle position | 22 | 2 B | big | unsigned | raw × 0.005 | % | 0.02 … 99.975 (42797) | high | actual electronic throttle position; it does not track the pedal one to one | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `BOOST_PRESSURE` | Boost pressure (absolute) | 24 | 2 B | big | unsigned | raw × 0.013157894736842105 | kPa_abs | 94.513157895 … 215.078947368 (42797) | high | pressure ahead of the throttle, different from MAP at idle; up to 202–215 kPa absolute while driving | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `BOOST_CMD` | Boost pressure target | 26 | 2 B | big | unsigned | raw × 0.013157894736842105 | kPa_abs | 24.618421053 … 233.684210526 (42797) | high | the target, same encoding | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `WASTEGATE` | Wastegate position | 28 | 2 B | big | signed | raw × 0.001 | mm? | -0.176 … 8.412 (42797) | high | **signed**: of 42,797 samples, 41,971 are ≤9000 and 826 are ≥65000, with nothing in between; 34 adjacent-sample transitions cross the sign boundary and read as >30000 jumps unsigned but as zero jumps signed | independent re-derivation from the tuning tool's export; re-classified as signed by the bit-level coverage map and confidence review (2026-09-19) |
| `WASTEGATE_CMD` | Wastegate position target | 30 | 2 B | big | unsigned | raw × 0.001 | mm? | 0 … 8 (42797) | high | never negative, so it is still read unsigned; the millimetre unit is unproven | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `AIRC` | Air charge | 32 | 2 B | big | unsigned | raw × 0.0234375 | % | 12.6796875 … 192.1171875 (42797) | high | the ECU's primary load quantity, reaching 218% under boost. **It must not be mapped onto OBD calculated load** | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `EXCAM` | Exhaust cam phase | 34 | 1 B | big | unsigned | raw × 0.2 − 23 | deg | -23 … 22.4 (42797) | high | coefficient 0.2·raw − 23 recovered from unrounded values | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `EXCAM_CMD` | Exhaust cam phase target | 35 | 1 B | big | unsigned | raw × 0.2 − 23 | deg | -23 … 21.8 (42797) | high | same encoding | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `CAT_TEMP` | Catalyst temperature | 36 | 2 B | big | unsigned | raw × 0.083333 | degC | 278.998884 … 766.163602 (42797) | high | an ECU model value; observed 303–766 °C | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `DI_FUEL_PRESSURE` | Direct injection fuel pressure | 38 | 2 B | big | unsigned | raw × 10 | kPa | 4290 … 20980 (42797) | high | actual direct-injection rail pressure, 43.5–200 bar; an earlier swap with the commanded value was corrected | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `OIL_PRESSURE_MIRROR` | Engine oil pressure (mirror) | 40 | 2 B | big | unsigned | raw | kPa | 58 … 621 (42797) | high | the same quantity as in `2610` sampled at a different instant (pairs agree exactly only 79.9% of the time) | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `PTANK` | Unresolved pressure quantity (PTANK) | 42 | 2 B | big | unsigned | raw × 0.0077089115016959605 | unresolved | 221.160962072 … 296.014492754 (42797) | medium | the numbers look like kPa (221–296) but are implausible for tank pressure, and they correlate strongly with the air-charge limits — a limit or model quantity. **Do not read it as fuel tank pressure** | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `DI_FUEL_PRESSURE_CMD` | Direct injection fuel pressure target | 44 | 2 B | big | unsigned | raw × 0.5 | kPa | 4355.5 … 20000 (42797) | high | r = 0.99997 against the actual value | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `TORQUE_REQ` | Requested torque | 46 | 1 B | big | unsigned | raw × 0.39215686274509803 | % | 0 … 70.980392157 (42797) | high | a normalised percentage; the reference torque is unknown, so it cannot be converted to N·m | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `TORQUE_ACT` | Actual torque | 47 | 1 B | big | unsigned | raw × 0.39215686274509803 | % | 0 … 64.705882353 (42797) | high | same as above | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `TORQUE_MAX` | Maximum torque (unit undetermined) | 48 | 1 B | big | unsigned | raw × 6.0024 | unresolved | 198.0792 … 276.1104 (42797) | medium | probably the torque ceiling for the current conditions; unit undetermined | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `AIRC_MAX` | Air charge limit | 49 | 1 B | big | unsigned | raw × 6.0024 | % | 150.06 … 270.108 (42797) | medium | `[49]` / `[57]` / `[58]` are equal at all times, so the three names are **indistinguishable** in this data | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `AIRC_PROT` | Air charge protection limit | 57 | 1 B | big | unsigned | raw × 6.0024 | % | 150.06 … 276.1104 (42797) | medium | same as above | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |
| `AIRC_COMP` | Air charge compensation limit | 58 | 1 B | big | unsigned | raw × 6.0024 | % | 150.06 … 276.1104 (42797) | medium | same as above | independent re-derivation from the tuning tool's unrounded datalog export; session 5 (2026-09-12) |

### 0x10 ECM/PCM engine control — `0x2660` (54-byte data area)

ECM odometer and run time.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ODOMETER` | Odometer | 43 | 3 B | big | unsigned | raw | km | withheld (365) | high | checked against the cluster reading | session 2 (2026-09-10), checked against the cluster odometer |
| `ENGINE_RUNTIME` | Engine run time | 46 | 2 B | big | unsigned | raw | s | 87 … 2232 (365) | medium | taken from the public signal set; not independently verified here | session 2 (2026-09-10), checked against the cluster odometer |

### 0x10 ECM/PCM engine control — `0x2662` (54-byte data area)

ECM knock and catalyst miscellany.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `KNOCK_CONTROL` | Knock control | 10 | 1 B | big | unsigned | raw × 0.00784313725490196 | scalar | 0 … 0 (365) | medium | taken from the public signal set; not independently verified here | cross-check against public signal sets (2026-09-14); session 2 (2026-09-10) |
| `CAT_TEMP_MIRROR` | Catalyst temperature (mirror) | 12 | 2 B | big | unsigned | raw × 0.083333 | degC | 303.582119 … 651.997392 (365) | high | r = 1.000 against the catalyst temperature in `2611` | cross-check against public signal sets (2026-09-14); session 2 (2026-09-10) |
| `VTC_DUTY` | VTC actuator duty | 28 | 1 B | big | unsigned | raw × 0.39215686274509803 | % | 5.882352941 … 55.294117647 (365) | medium | adopted from the public signal set; on this car the raw value moves over 15..123 with engine speed. It was once mis-read as a coolant temperature duplicate | adopted from public signal sets (2026-09-14); raw value tracks engine speed on this car |
| `UNKNOWN_B39` | Unknown byte 39 | 39 | 1 B | big | unsigned | raw | ? | 71 … 73 (365) | low / candidate | once mis-read as coolant temperature: it stayed at 73 while coolant went 73→80 °C, which rules that out. Nature unknown | cross-check against public signal sets (2026-09-14); session 2 (2026-09-10) |

### 0x10 ECM/PCM engine control — `0x2665` (54-byte data area)

Run-time duplicate, found while reviewing the ECM DIDs that were still unexplained.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ENGINE_RUNTIME_COPY` | Engine run time (copy) | 8 | 2 B | big | unsigned | raw | s | 95 … 2232 (1017) | medium | equal sample by sample to the run time in `2660` (250/278; the rest differ by 1 s across a second boundary) | offline review of the remaining ECM DIDs (2026-09-13) |

### 0x10 ECM/PCM engine control — `0x267E` (68-byte data area)

A long 68-byte response; only one 8-bit high-byte duplicate is identified.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `PTANK_HI8` | Unresolved pressure quantity (high byte) | 11 | 1 B | big | unsigned | raw × 1.973481344434166 | unresolved | 228.923835954 … 294.048720321 (1017) | low / candidate | equals the high byte of the 16-bit PTANK raw value (273/278) | offline review of the remaining ECM DIDs (2026-09-13) |

### 0x10 ECM/PCM engine control — `0x267F` (10-byte data area)

A short 10-byte response; one byte duplicates the air-charge limit from `2611`.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `AIRC_MAX_COPY` | Air charge limit (copy) | 5 | 1 B | big | unsigned | raw × 6.0024 | % | 156.0624 … 264.1056 (364) | low / candidate | raw byte equal to `2611[49]` sample by sample (264/278) | offline review of the remaining ECM DIDs (2026-09-13) |

### 0x10 ECM/PCM engine control — `0x2683` (54-byte data area)

Timer packet A. The start event and the overflow behaviour are both unknown; research use only.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `TIMER_A` | Timer A | 28 | 2 B | big | unsigned | raw × 0.1 | s | 237.5 … 6202.8 (1017) | low / candidate | monotonic, starting about 81 s later than engine run time; the start event is unknown | offline review of the remaining ECM DIDs (2026-09-13) |

### 0x10 ECM/PCM engine control — `0x2689` (54-byte data area)

Timer packet B, started by a different event than timer A.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `TIMER_B` | Timer B | 12 | 2 B | big | unsigned | raw × 0.1 | s | 121.6 … 3550.4 (363) | low / candidate | monotonic, starting about 197 s later than run time — a different event from timer A | offline review of the remaining ECM DIDs (2026-09-13) |
| `TIMER_B_DUP` | Timer B (duplicate position) | 16 | 2 B | big | unsigned | raw × 0.1 | s | 121.6 … 3550.4 (363) | low / candidate | byte-for-byte identical to `[12:14]` throughout; listed only to mark the position | offline review of the remaining ECM DIDs (2026-09-13) |

### 0x10 ECM/PCM engine control — `0x268F` (54-byte data area)

The oil-temperature packet. **This one has no precedent anywhere in public sources** and is the item most in need of verification on a stock car. Another 25 bytes in this response are live; their structure has been analysed but none of them is named — see the unmapped-bytes section.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `OIL_TEMP_MODEL` | Engine oil temperature (ECU model) | 15 | 1 B | big | unsigned | raw − 40 | degC | 32 … 82 (20684) | high | an ECU model value. Matches the cluster point for point over 54→67 °C; the in-car display showed 54 °C where the bus read 55 °C; warm-up is continuous over 32→81 °C. **No precedent in any public source**; the model algorithm, the sensor arrangement and the start-up display threshold are all unverified | session 2 (2026-09-10), cluster 54→67 °C point by point; session 5 (2026-09-12), in-car display 54 °C vs 55 °C on the bus |

### 0x28 VSA stability control (ABS/ESC) — `0x4001` (56-byte data area)

VSA longitudinal acceleration plus yaw and steering-angle duplicates.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `STEER_ANGLE_COPY` | Steering wheel angle (copy) | 20 | 2 B | big | unsigned | raw × 1.04 − 1170 | deg | -396.24 … 399.36 (3965) | low / candidate | r = 0.96 against the steering angle in `48BD` | session 7 (2026-09-15), event-outlier analysis re-run over session 4 data as well |
| `YAW_RATE_U8` | Yaw rate (8-bit copy) | 50 | 1 B | big | unsigned | raw × 1.17 − 146.25 | deg/s | -54.99 … 40.95 (3965) | low / candidate | an 8-bit copy of `48C0` (same source, so it cannot cross-validate it) | session 7 (2026-09-15), event-outlier analysis re-run over session 4 data as well |
| `LATERAL_G_VSA_CANDIDATE` | Lateral acceleration (VSA candidate) | 51 | 1 B | big | unsigned | raw × 0.02 − 2.5 | g? | -0.66 … 0.36 (3965) | low / candidate | best r = 0.873 against a speed × yaw-rate model. It is **an independent lateral channel**, not a sample-by-sample mirror of the EPS one; back-solving the yaw scale from each of the two gives results 35% apart, so at least one of the two scales is wrong | candidate review (2026-09-18); full-archive re-check of the G / yaw scales (2026-09-20) |
| `LONGITUDINAL_G` | Longitudinal acceleration | 52 | 1 B | big | unsigned | raw × 0.02 − 2.5 | g | -0.44 … 0.46 (3965) | medium | zero at raw = 125; r = 0.67–0.83 against acceleration differentiated from wheel speed, free slope 1.039, residual 0.030 g. **Only one trip sampled wheel speed fast enough to compute dv/dt** | session 7 (2026-09-15), event-outlier analysis; full-archive re-check of the G / yaw scales (2026-09-20) |

### 0x28 VSA stability control (ABS/ESC) — `0x4004` (56-byte data area)

VSA brake switch and the coarse (1.5 km/h) wheel speeds.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `WHEEL_SPEED_FL_VSA` | Wheel speed front left (VSA, coarse) | 8 | 1 B | big | unsigned | raw × 1.5 | km/h | 0 … 114 (3339) | medium | 1.5 km/h per LSB; **the wheel order is inferred from the EPS packet**, not independently confirmed | session 3 (2026-09-10); cross-check against public signal sets (2026-09-14) |
| `WHEEL_SPEED_FR_VSA` | Wheel speed front right (VSA, coarse) | 9 | 1 B | big | unsigned | raw × 1.5 | km/h | 0 … 114 (3339) | medium | same as above | session 3 (2026-09-10); cross-check against public signal sets (2026-09-14) |
| `WHEEL_SPEED_RL_VSA` | Wheel speed rear left (VSA, coarse) | 10 | 1 B | big | unsigned | raw × 1.5 | km/h | 0 … 114 (3339) | medium | same as above | session 3 (2026-09-10); cross-check against public signal sets (2026-09-14) |
| `WHEEL_SPEED_RR_VSA` | Wheel speed rear right (VSA, coarse) | 11 | 1 B | big | unsigned | raw × 1.5 | km/h | 0 … 114 (3339) | medium | same as above | session 3 (2026-09-10); cross-check against public signal sets (2026-09-14) |
| `BRAKE_SWITCH` | Brake switch | 15 | 1 bit (mask 0x1) | big | unsigned | raw & 0x1 | bool | 0 … 1 (3339) | medium | agrees with the public signal set once the MSB0 bit numbering is applied: bix 127 is byte 15 bit0 | session 3 (2026-09-10); cross-check against public signal sets (2026-09-14) |

### 0x28 VSA stability control (ABS/ESC) — `0x4005` (56-byte data area)

VSA brake pressure. Verified at two points against the in-car display.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `BRAKE_PRESSURE` | Brake master cylinder pressure | 7 | 2 B | big | unsigned | raw − 25 | bar | 0 … 106 (4840) | high | 0 at rest; the in-car display's 5 MPa and 10 MPa correspond to 50 bar and 106 bar here (about 6% apart, kept as-is) | session 2 (2026-09-10), two measured points against the in-car display |
| `BARO_MIRROR` | Barometric pressure (VSA mirror) | 21 | 1 B | big | unsigned | raw | kPa | 101 … 101 (4840) | medium | same value as `2610[17]` | session 2 (2026-09-10), two measured points against the in-car display |

### 0x28 VSA stability control (ABS/ESC) — `0x4007` (56-byte data area)

VSA clutch / reverse / Brake Hold / seatbelt packet. Most bit meanings come from stationary, guided, one-action-at-a-time segments.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `BRAKE_HOLD_HOLDING_CANDIDATE` | Brake Hold actively holding (candidate) | 9 | 1 bit (mask 0x8) | big | unsigned | raw & 0x8 | bool | 0 … 8 (3515) | low / candidate | all 26 set segments occur with Brake Hold enabled; two negative controls (Hold disabled, 559 samples; seatbelt unfastened, 317 samples) produce zero counter-examples. «Clears as soon as the pedal is released» is refuted by counter-example. **There is no independent «currently holding» reference, so it is not promoted** | candidate review (2026-09-18); full-archive re-check (2026-09-20) |
| `BRAKE_SWITCH_MIRROR` | Brake switch (VSA mirror) | 9 | 1 bit (mask 0x4) | big | unsigned | raw & 0x4 | bool | 0 … 4 (3515) | medium | **not a clean mirror of the brake switch**: `[9]` only ever takes 0 / 4 / 12 and never 8, and what holds is «bit2 = pedal OR bit3». While bit3 is set, bit2 does not fall back when the pedal is released — using it as a brake indicator will keep the indicator lit throughout a Brake Hold | candidate review (2026-09-18); full-archive re-check (2026-09-20) |
| `REVERSE_GEAR` | Reverse gear engaged | 11 | 1 bit (mask 0x2) | big | unsigned | raw & 0x2 | bool | 0 … 2 (3515) | high | four transitions across two reversing manoeuvres while driving, plus a 30 s stationary segment held in reverse | session 4, two reversing manoeuvres while driving; session 7, a 30 s stationary segment in reverse |
| `SEATBELT_DRIVER` | Driver seatbelt fastened | 17 | 1 bit (mask 0x20) | big | unsigned | raw & 0x20 | bool | 0 … 32 (3515) | high | two independent unfasten / fasten actions: cleared on unfasten, set on fasten | session 8 (2026-09-16), stationary segment 5; startup-sequence review (2026-09-18) |
| `BRAKE_HOLD_ACTIVE` | Brake Hold enabled | 21 | 1 bit (mask 0x2) | big | unsigned | raw & 0x2 | bool | 0 … 2 (3515) | medium | synchronous with the cluster bit `7021[7] bit7`; **verified by a single stationary press / cancel, needs repeating** | session 7 (2026-09-15), stationary guided action segments; session 8 (2026-09-16), stationary segments |
| `CLUTCH_PEDAL` | Clutch pedal travel | 24 | 1 B | big | unsigned | raw | % | 0 … 100 (3515) | high | fully separated (0 / 100) across five stationary press-and-release cycles; intermediate values such as 3–36 appear when shifting on the move, so it is **travel in percent**, not a switch | session 7 (2026-09-15), stationary segment 2; session 8 (2026-09-16), gear changes while driving |

### 0x28 VSA stability control (ABS/ESC) — `0x4009` (56-byte data area)

VSA vehicle speed.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `EPB_APPLIED` | Electric parking brake applied | 9 | 1 B | big | unsigned | raw | raw | 0 … 175 (2997) | medium | the byte becomes 0xAF when the electric parking brake is applied; **single observation** | session 8 (2026-09-16), stationary segment, single observation |
| `VEHICLE_SPEED_VSA` | Vehicle speed (VSA) | 32 | 1 B | big | unsigned | raw | km/h | 0 … 114 (2997) | high | integer speed, agrees with the ECM's | session 3 (2026-09-10) |

### 0x30 EPS electric power steering — `0x4818` (56-byte data area)

EPS vehicle speed and wheel speeds as 8-bit integers.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `VEHICLE_SPEED_COPY` | Vehicle speed (EPS copy) | 15 | 1 B | big | unsigned | raw | km/h | 0 … 114 (1142) | high | EPS-side vehicle speed duplicate (16-bit ×0.01 in `48BD`, 8-bit integer in `4818`) | session 3 (2026-09-10) |
| `WHEEL_SPEED_FL_8BIT` | Wheel speed front left (8-bit) | 25 | 1 B | big | unsigned | raw | km/h | 0 … 115 (1142) | medium | 1 km/h integer version; wheel order inferred from `48C4` | session 3 (2026-09-10) |
| `WHEEL_SPEED_FR_8BIT` | Wheel speed front right (8-bit) | 26 | 1 B | big | unsigned | raw | km/h | 0 … 115 (1142) | medium | same as above | session 3 (2026-09-10) |
| `WHEEL_SPEED_RL_8BIT` | Wheel speed rear left (8-bit) | 27 | 1 B | big | unsigned | raw | km/h | 0 … 115 (1142) | medium | same as above | session 3 (2026-09-10) |
| `WHEEL_SPEED_RR_8BIT` | Wheel speed rear right (8-bit) | 28 | 1 B | big | unsigned | raw | km/h | 0 … 115 (1142) | medium | same as above | session 3 (2026-09-10) |

### 0x30 EPS electric power steering — `0x48AC` (56-byte data area)

EPS steering assist mode. This is the **only** drive-mode bit that has been found: the mode is not one global flag, each module keeps its own.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `STEER_MODE` | Steering assist mode | 1 | 1 B | big | unsigned | raw | enum | 1 … 3 (2083) | high | 1 = comfort, 2 = sport, 3 = +R; a custom mode still reads 1. Consistent across three independent sessions, and the **only** confirmed drive-mode bit | session 7 (2026-09-15), per-segment analysis across a drive-mode sweep |
| ↳ enum | 1 = comfort, 2 = sport, 3 = plusR | | | | | | | | | | |
| `STEER_MODE_AUX` | Steering assist mode (aux byte) | 2 | 1 B | big | unsigned | raw | enum | 0 … 2 (2083) | low / candidate | a second byte that flips in step with the mode (comfort = 02, sport = 00, +R = 01); meaning unknown | session 7 (2026-09-15), per-segment analysis across a drive-mode sweep |
| ↳ enum | 0 = sport, 1 = plusR, 2 = comfort | | | | | | | | | | |

### 0x30 EPS electric power steering — `0x48BD` (56-byte data area)

EPS steering angle.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `STEER_ANGLE` | Steering wheel angle | 11 | 2 B | big | signed | raw × 0.1 | deg | -405.6 … 408.1 (5164) | medium | **0.1°/LSB is an assumption**: raw −4032 at full left lock, −26 at centre, and an eyeballed ~390° from centre to full lock gives 0.0974°/LSB. Full right lock was never captured and no instrument calibration was done | session 3 (2026-09-10); session 5 (2026-09-12) |
| `VEHICLE_SPEED_COPY` | Vehicle speed (EPS copy) | 15 | 2 B | big | unsigned | raw × 0.01 | km/h | 0 … 113.99 (5164) | medium | EPS-side vehicle speed duplicate (16-bit ×0.01 in `48BD`, 8-bit integer in `4818`) | session 3 (2026-09-10); session 5 (2026-09-12) |
| `YAW_RATE_8BIT` | Yaw rate (8-bit candidate) | 19 | 1 B | big | unsigned | raw × 1.13 − 144.6 | deg/s | -49.68 … 39.59 (5164) | low / candidate | r = 0.976 against a v·tanδ/L model | session 3 (2026-09-10); session 5 (2026-09-12) |

### 0x30 EPS electric power steering — `0x48C0` (56-byte data area)

EPS yaw rate.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `YAW_RATE` | Yaw rate | 0 | 2 B | big | signed | raw × 0.0045 | deg/s | -46.404 … 42.183 (2798) | medium | r = 0.982 against a model built on a 2.735 m wheelbase and a steering ratio of 13; positive is a right turn. **The scale is not calibrated**: a wheel-speed geometry method gives a pooled point estimate of 0.004214 with an error-budget interval of [0.00239, 0.00604], and the 43.4% systematic error dwarfs the 14.7% gap between the two candidate scales | session 3 (2026-09-10), model fit; error budget from the full-archive re-check (2026-09-20) |

### 0x30 EPS electric power steering — `0x48C4` (56-byte data area)

EPS four-wheel speeds at 0.01 km/h. The wheel order is inferred from «outer wheels faster in a turn» plus «front wheels faster under acceleration», not from documentation.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `STEER_ANGLE_COPY` | Steering wheel angle (copy) | 8 | 2 B | big | signed | raw × 0.1 | deg | -405.4 … 408 (3193) | medium | r = 0.96 against the steering angle in `48BD` | session 3 (2026-09-10) |
| `LATERAL_G_CANDIDATE` | Lateral acceleration (EPS candidate) | 18 | 1 B | big | signed | raw × 0.005 | g? | -0.35 … 0.435 (3193) | low / candidate | r = 0.85 against a v²δ/L model; hard to separate from yaw rate over the speed range available | session 3 (2026-09-10); full-archive re-check (2026-09-20) |
| `WHEEL_SPEED_FL` | Wheel speed front left | 23 | 2 B | big | unsigned | raw × 0.01 | km/h | 0 … 115.23 (3193) | high | r = 0.997 against ECM vehicle speed; the wheel order comes from outer wheels running faster in a turn and front wheels faster under acceleration | session 3 (2026-09-10) |
| `WHEEL_SPEED_FR` | Wheel speed front right | 25 | 2 B | big | unsigned | raw × 0.01 | km/h | 0 … 115.18 (3193) | high | same as above | session 3 (2026-09-10) |
| `WHEEL_SPEED_RL` | Wheel speed rear left | 27 | 2 B | big | unsigned | raw × 0.01 | km/h | 0 … 114.75 (3193) | high | same as above | session 3 (2026-09-10) |
| `WHEEL_SPEED_RR` | Wheel speed rear right | 29 | 2 B | big | unsigned | raw × 0.01 | km/h | 0 … 114.55 (3193) | high | same as above | session 3 (2026-09-10) |

### 0x60 Instrument cluster — `0x7020` (54-byte data area)

Cluster seatbelt and electric parking brake indicators.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `SEATBELT_WARN_CLUSTER` | Seatbelt warning (cluster) | 9 | 1 bit (mask 0x10) | big | unsigned | raw & 0x10 | bool | 0 … 16 (480) | medium | **inverted polarity** relative to the VSA bit (here 1 means not fastened) | session 8 (2026-09-16), stationary segment 5; startup-sequence review (2026-09-18) |
| `EPB_INDICATOR_CLUSTER` | Electric parking brake indicator (cluster) | 11 | 1 bit (mask 0x20) | big | unsigned | raw & 0x20 | bool | 0 … 32 (480) | medium | set when the electric parking brake is applied; **single observation** | session 8 (2026-09-16), stationary segment, single observation |

### 0x60 Instrument cluster — `0x7021` (54-byte data area)

Cluster Brake Hold indicator.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `BRAKE_HOLD_ACTIVE_CLUSTER` | Brake Hold enabled (cluster) | 7 | 1 bit (mask 0x80) | big | unsigned | raw & 0x80 | bool | 0 … 128 (480) | medium | synchronous with VSA `4007[21] bit1` (set at +77 s, cleared at +87 s) | session 7 (2026-09-15), stationary segment |

### 0x60 Instrument cluster — `0x7022` (54-byte data area)

Cluster odometer.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ODOMETER_CLUSTER` | Odometer (cluster) | 6 | 3 B | big | unsigned | raw | km | withheld (1394) | high | same value and same unit (km) as the ECM odometer — **the public archive's «miles» is wrong** | session 2 (2026-09-10), checked against the cluster odometer |

### 0x60 Instrument cluster — `0x7028` (54-byte data area)

Cluster ambient temperature.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `AMBIENT_TEMP` | Ambient temperature | 17 | 1 B | big | unsigned | raw | degC | 26 … 34 (2059) | high | raw = 28 corresponds to 28 °C on the in-car display, with **no −40 offset** (the public archive's −40 does not hold on this car); `[15]` carries the same value. Negative-temperature encoding could never be verified at the capture location | session 2 (2026-09-10), against the in-car ambient temperature display |

### 0x60 Instrument cluster — `0x7029` (54-byte data area)

Cluster fuel level.

| Signal | Name | Offset | Width | Endian | Sign | Decoding | Unit | Observed range (n) | Confidence | Evidence | First established by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `FUEL_LEVEL` | Fuel level | 12 | 2 B | big | unsigned | raw × 0.01 | L | 16.46 … 43.88 (1393) | high | a smooth 16.57→16.46 L over ten minutes of idling (≈0.66 L/h) | session 2 (2026-09-10) |

Where the same signal name appears under two DIDs (`VEHICLE_SPEED_COPY`, `STEER_ANGLE_COPY`), they are two independent fields at different positions; read the decoding and the confidence from the row you are looking at.

Rows marked `kPa_abs` are absolute pressure. For gauge boost pressure use `MAP_ABS − BARO` **from the same response**, not a fixed 101.325 constant.

For masked bit fields the «Observed range» column shows the **masked raw value** (a set bit under mask `0x8` shows as 8), not 0 / 1.

Observed ranges are withheld for per-vehicle cumulative counters such as the odometer, because an exact reading can identify one specific car. The sample count is still given.

## 8. Bytes that change but are not mapped

Across the 25 mapped DIDs there are still **206 unmapped bytes that change / 1,183 bits** (189 bytes / 1,124 bits change within a single capture), from a bit-level coverage analysis over the whole archive. Only the entries with a definite conclusion are listed here.

**Four of those bytes hold unmapped bits alongside already-mapped ones** — tooling that filters candidates a whole byte at a time cannot see them.

| DID | Position | Everything known about it |
|---|---|---|
| `10:2610` | [8] | identical to [27] (low byte of fuel pressure) |
| `10:2610` | [12] | strongly anti-correlated with intake air temperature (ADC-like); r ≈ 0.69 against gear / speed |
| `10:2610` | [16] | changes within a capture, low nibble only (mask 0x0F); 5 distinct values, r ≈ −0.77 against coolant temperature |
| `10:2610` | [37] | strongly anti-correlated with `ECT2` |
| `10:2610` | [41] | anti-correlated with `IAT2` |
| `10:2610` | [46:48] | drifts slowly over 5272–5704 (mapped as a low-confidence high-resolution voltage candidate) |
| `10:2610` | [49] | low byte of `MAP_MMHG` |
| `10:2610` | [50] | 0 / 1 flag |
| `10:2610` | [51] | 0–240 in steps of about 7.5 |
| `10:2611` | [7] | low byte of `LAMBDA_ALT` |
| `10:2611` | [18] bit1 | a second, unmapped bit in the same byte as the mapped `VTS` (bit0) |
| `10:2611` | [38] | 1–7, r = 0.93 against direct-injection pressure (possibly a high-pressure pump stage) |
| `10:2611` | [39] | low byte of `DI_FUEL_PRESSURE_CMD` |
| `10:2611` | [52] | 1 / 3 flag |
| `10:2611` | [53:55] / [55:57] | a short-lived negative internal correction, range −53…0. **The width is not identifiable** (s8 and s16LE are identical over that range); the two are in a one-way containment relation, not one 4-byte structure. «A one-off adaptation right after start-up» is **refuted** — one single capture holds at least two non-zero stretches, the second lasting 80.3 s over 893 samples. **It is not a clutch switch** |
| `10:268F` | [20:28] | four zero-mean signed 16-bit **big-endian** pairs (boundaries 20–27, not 28–31) |
| `10:268F` | [28:30] | family membership undecided |
| `10:268F` | [16:18] / [31:33] | sign-extension pairs; width not identifiable |
| `10:268F` | [40] / [42] and [44] / [46] | **two pairs of bit0 / bit2 flags, not four identical switches**: [40]≡[42] and [44]≡[46] with zero counter-examples, but [40]≡[44] has 184. The whole archive contains only 2 one-shot latching events (once set, never cleared before end of file); the gating condition is unsolved — coolant ≥80 °C, an oil-temperature threshold, elapsed time and peak load are each refuted by counter-example |
| `10:268F` | [12] / [13] / [14] | carry a 255 sentinel; `[12]` survives both a differenced and a matched test against engine speed (r = 0.21 / 0.256), the only one of 50 candidates that does — **left unnamed** |
| `10:268F` | [9] / [30] | continuous quantities, unsolved |
| `10:268F` | [11] / [35] | small enumerations |
| `28:4007` | [21] bit0 | all 118 set samples coincide with bit2 and bit3 of `[9]` both being set; **registered, not named** |
| `28:4007` | [17] bit3 | shares a byte with the mapped seatbelt bit; set in 1,567 positive responses with 323 rising edges; identity undetermined |
| `30:48BD` | [21] | takes 0x10 / 0x20 / 0x30 and is **a candidate for tracking the drive mode** (steering mode 1→0x10, 2→0x20, 3→0x30). The evidence is one capture with one round trip, and it sits in the same module as the confirmed mode byte, so it may be an internal duplicate |
| `3A:520A` | whole 64 B response | the only live ADS data packet, undecoded. Three multi-byte field candidates (10:12, 36:38, 38:40, all big-endian); `[4]` is a two-state collapse of `48BD[21]` (0 ↔ 0x10, ≥1 ↔ 0x20/0x30, holding for 586 of 595 pairs) |

## 9. Candidates, unsolved items and what cannot be told apart

### 9.1 Candidates (real structure, no independent ground truth)

| Item | Where it stands | What is missing |
|---|---|---|
| Drive-mode bits other than steering | The mode is **not one global flag**; each module keeps its own. Only EPS `48AC[1]` (steering assist) is confirmed. Candidate chain: `48AC[1]` ↔ `48BD[21]` ↔ ADS `520A[4]`, plus VSA `4004[52]` (1/2→4, 3→6) | every hop rests on a single capture, and the first hop may be an internal duplicate inside one module. No stable fingerprint was found in the sampled damper, engine or cluster DIDs; the diagnostic address of the exhaust / active-sound module is unknown |
| A/C clutch `2610[32] bit1` | values 0x00 / 0x01 / 0x03; bit0 is present with the engine off while bit1 only appears once running, matching a request / clutch-engaged split, and it is exactly the bit the public signal set names | **nobody ever marked the A/C switch**, so there is no ground truth. One on and one off with a marker would settle it |
| Brake Hold «actively holding» `4007[9] bit3` | all 26 set segments occur with Hold enabled; two negative controls give zero counter-examples | an indicator independent of what VSA reports about itself; only 12 stopped events carry pedal evidence at a matching rate (fewer than 20). The cluster bit and the VSA bit are the same source, so they cannot corroborate each other |
| `10:3000` / `3001` / `3004` / `3008` / `300C` | read once each during a scan. `3004` and `3008` share one record layout (header `df002f000000`, `3008` being an empty slot) | all four readings of `3004` (counter, date/time, mileage/service record, freeze frame) are **refuted**; it correlates strongly with quantities in the same response (up to \|r\| = 0.9997) but there is no independent ground truth, so it stays **unnamed** |
| The 20 new ECM DIDs in DC59–FFFF and VSA `0EEC` / `4100` | static across 60 s of stationary idle | another capture with the car actually doing something |
| Compass heading / GPS | not in the 18 known cluster DIDs (30 minutes of cruising with 476° of accumulated steering produced no byte that tracks heading) | the unscanned part of the cluster, the gateway pair and `0x70` were never scanned; it may also live only on the body network |
| «Constant» DIDs | 22 ECM DIDs do not change anywhere in the current coverage | **this must not be written as «confirmed calibration constants»**: 278 of the 280 samples per DID come from one ten-minute window in one ignition cycle, and there is exactly one cross-session re-read. Confirming true constancy needs one read per DID across several natural ignition cycles, or the same batch read on a stock car |

### 9.2 Not identifiable from the data at hand (which is not the same as «no effect»)

| Item | The competing readings | Why they cannot be separated |
|---|---|---|
| Yaw-rate scale | 0.0045 (steering-angle / wheelbase kinematic model) vs 0.003924 (rear-wheel differential geometry) | these are **not two independent calibrations**: the same geometric method yields 0.00347–0.00488 depending on the speed window and the track width used. The systematic error budget totals 43.4% (left/right asymmetry 34.1%, speed window 21.5%, trip-to-trip 16.0%), far larger than the 14.7% between the two candidates. Settling it needs an external yaw-rate reference (≥10 Hz, <3% error) or a measured track width and rolling circumference |
| The gating of `2610[39]` | absolute vs gauge pressure as the input; a single threshold vs hysteresis vs a speed/gear-dependent split | a single pressure threshold and a Schmitt hysteresis are both refuted (within one trip the state is entered at 7.1 kPa gauge and absent at 26.3 kPa, which would require the entry threshold to be below the exit threshold). Absolute vs gauge is not separable in this archive because barometric pressure only ever read 100 or 101. A speed/gear split improves held-out log-loss by 17–18%, short of the 20% bar but with a confidence interval crossing it → **undecided, not «no effect»** |
| The width of `2611[53:57]` | signed 8-bit vs signed 16-bit little-endian | over the observed range of −53…0 the two are identical, with zero counter-examples. One sample with magnitude above 127 would settle it |
| The width of `268F[16:18]` / `[31:33]` | 8-bit vs 16-bit sign-extended | they are sign-extension pairs, so both readings give the same value over the observed range |
| The lateral-acceleration scale | EPS `48C4[18]` ≈0.005 g vs VSA `4001[51]` ≈0.02 g | they are independent channels, not mirrors; back-solving the yaw scale from each gives results 35% apart, so **at least one is wrong**, and there is no independent reference to say which |
| The mechanism behind the link stalls during scans | gateway rate-limiting / an ISO-TP fault / the capture tooling / a silently timing-out scan request holding the serial channel | the correlation is strong (time slices containing a scan stall about 6× as often as sampling-only slices) and «one ECU is busy» is ruled out, but the remaining four are all under-evidenced; without adapter-side telemetry, «the tool is blocked» and «the bus or gateway went quiet» look identical |
| `AIRC_MAX` / `AIRC_PROT` / `AIRC_COMP` | three different names | bytes `[49]`, `[57]` and `[58]` are equal at all times, so the three cannot be told apart in this data |

## 10. Claims that were overturned

This section matters as much as the table above it. Every line below was written down at some point and later overturned by data. Publishing them saves the next person from repeating the mistake, and it shows how the surviving conclusions were filtered.

| The claim | Corrected to | What the mistake was | Overturned by |
|---|---|---|---|
| Service 22 requests go to `7E0` and responses come from `7E8` | this car uses 29-bit `18DA10F1` / `18DAF110`; Mode 01 on 11-bit `7DF` / `7E0` draws no response at all | a generic OBD-II prior applied to Honda's 29-bit diagnostic addressing | first session, passive capture |
| `22 2610` does not answer, so a stock ECU must need a `10 03` + `27` handshake | the tester's flow control was 120 ms late and the ECU abandoned the transfer; the default session needs no handshake | a rate limiter queued the flow control frame, and the resulting symptom was read as a protocol requirement | session 2, self-corrected |
| Oil temperature is not in the ECU / the head unit gets it elsewhere | it is in ECM `268F[15]` | only `2610` and `2611` had been searched before the negative conclusion was drawn | session 2 |
| 21 coefficients derived from the tuning tool (pedal 0.00457, cams, boost, air charge, an 8-bit wastegate, actual and commanded injection pressure swapped, torque in N·m …) | all replaced by exact constants (0.005; 53 − 0.5·raw; raw/76 absolute; raw×3/128; a 16-bit wastegate; torque as 100·raw/255 %) | regressing against an already rounded and truncated CSV export, which also mixed inHg and psi | re-derivation from the unrounded datalog stream |
| `2662[28] − 40` is a coolant temperature duplicate | it stayed at 73 while coolant went 73→80 °C, so it was first downgraded to unknown and later identified as VTC duty (medium confidence) | a coincidence inside a short window read as a correspondence | self-review plus cross-check against public sources |
| `2610[14]` is MAP in integer kPa | not integer kPa and not linear over the full range; use `[9:11]` | a single linear fit over a narrow range | review plus session 5 |
| `ECT2` is «coolant temperature 2» | a location with far more thermal inertia; confidence dropped to low | a handful of samples, plus the continuous trace being misread as a frozen start-up snapshot | session 5 |
| Air charge can be used as OBD calculated load | air charge is relative and reaches 218%; the semantics differ, and calculated load stays absent | conflating two different quantities because the units looked alike | external review |
| «The sum of ten transaction medians ≈ the cycle time, so the serial model holds» | the method is wrong (medians do not add); the correct proof is a per-round identity with zero residual | a statistical error | independent review |
| VSA has a fixed 80 ms consecutive-frame gap, and a 10/10/5 Hz schedule was built on it | 80 ms is the first-frame-to-last-frame span; real CF gaps are ≈10 ms (VSA), ≈2 ms (ECM), ≈8 ms (EPS). That schedule would need 1700 ms of bus time per second from one module | reading a total duration as an inter-frame gap, and never checking the schedule against an ECU time budget | independent review |
| «Everything on the in-car performance display except longitudinal G and clutch is readable» | the steering scale is an assumption and the yaw rate is a model fit; neither is calibrated | over-generalisation | external review |
| With the key on and the engine not running, oil temperature reads 32 while the display shows dashes, so the product must reproduce that threshold | that key-on capture never sampled `268F` at all, and by the time 32 was read the engine was turning at 1514 rpm | treating a verbal observation from a minute earlier and a current reading as the same instant | session 5 review |
| «The low-pressure warning threshold must be below 58 kPa» and «above 4500 rpm the regulator is limiting pressure» | 58 is merely the smallest value ever observed, and above 4500 rpm there are only 29 samples | an inference stated as a fact | session 5 review |
| 0.0967 °/LSB for steering, with the full two-sided range reproduced | the centre offset was not subtracted; it should be 0.0974, and that session never reached full right lock | a missing zero offset, plus a negative claim beyond the evidence | session 5 review |
| `2611[55:56]` is a strong clutch candidate | it is not the clutch, and it is not «a one-off adaptation right after start-up» either — one capture holds at least two non-zero stretches, the second lasting 80.3 s over 893 samples | first correlation mistaken for identification, then a «one-off» conclusion drawn from looking only at the start of the file | session 5 self-correction; full-archive re-check (2026-09-20) |
| The drive-mode bits are most likely concentrated in the damper module | they are not in any of its 10 data DIDs; the mode bits are **spread across modules, each keeping its own** | assuming a single global flag | session 6, plus the owner explaining that the custom mode is six per-subsystem settings |
| Scanning VSA `40xx` after parking returned zero responses, so the clutch is not in VSA | the engine was already off and the ECU unpowered, so that scan proves nothing; the clutch is in VSA `4007[24]` | not verifying that the ECU was online before scanning — zero responses after shutdown are not exclusion evidence | session 5 review; found in session 7 |
| Longitudinal G is not in these nine VSA packets | it is, at `4001[52]` | it had only been correlated against brake pressure, never against acceleration, and no event-outlier analysis was done | session 7, event-outlier analysis |
| Live monitoring reported a boost peak of +0.85 bar | computed over the full log it is +1.16 bar | polling misses instantaneous peaks; peak-type conclusions must always be computed from the complete log | session 5 |
| From the public archive: `7028` needs a −40 offset, `7022` is in miles, and the brake switch is bit7 of `4004[15]` | on this car they read directly in °C, in km, and at bit0 | a public table applied across model variants; the bit7 item was actually a bit-order conversion error (see the next row) | session 2 measurements plus a 2026-09-14 comparison |
| «The public signal set's `bix` modulo 8 is the bit number within the byte» | that project numbers bits **MSB0**: bit = 7 − (bix % 8). bix 262 is bit1 (not bit6) and bix 127 is bit0, so there was never a disagreement with this car | the original implementation was never opened; the convention was inferred backwards from one example that happened to fit | reading the upstream implementation at a fixed commit |
| Service `21` might be the entry point to Honda's dealer-tool data list | all 256 local identifiers on all five modules return `0x11` serviceNotSupported | extrapolating from older Honda platforms | session 7 |
| «`4007[9]` bit2 mirrors the brake switch; agreement rises to 100% as the time tolerance tightens, so the difference is sampling skew» | the 97.05% figure reproduces, but «rises to 100%» is an artefact of which logs contribute (54 of the 58 pairs in the tightest bin come from logs where Hold was never enabled). bit2 is **not** an instantaneous mirror; what holds is «bit2 = pedal OR bit3» | reading the trend of a tolerance sweep without breaking it down by log | full-archive re-check (2026-09-20) |
| «Scanning the cluster / gateway / 0x70 at 5 ms intervals causes the link to stall» (stated as causation) | the phenomenon is real and strongly correlated, but the **mechanism is not established**: «one ECU is busy» is ruled out and every other explanation is under-evidenced. Recorded as «strong correlation, mechanism unknown» | two reproductions written up as causation, with no graded evidence review | full-archive re-check (2026-09-20) |
| «`48BD[21]` is not a mode byte — it takes the same three values in a capture with no mode changes» | it **is** a candidate for tracking the drive mode: in one capture the confirmed mode byte runs 1→2→3→1 across four segments while `48BD[21]` runs 0x10→0x20→0x30→0x10 in step, with the boundaries aligned to within one polling interval; a separate capture with no mode changes holds 0x10 for all 176 samples | the «no-change control» never checked whether that control capture contained a mode change, and no per-segment alignment was done — the value sets merely looked alike | independent re-check (2026-09-20) |
| «`268F[39]` is a high-load flag» | that byte is 0 in all 20,684 samples in the archive; there is nothing to stand on. Probably a mix-up with `2610[39]` | two similar offsets in two different DIDs confused in a note, with no return to the raw samples | full-archive re-check (2026-09-20) |
| «`268F[40]/[42]/[44]/[46]` are four identical switches that set once coolant reaches 80 °C» | they are **two pairs** of bit fields (bit0 / bit2), not four copies; the value set {0,1,4} is all powers of two. The coolant threshold is refuted by counter-example (whole captures sit above 80 °C with the bytes at 0) | a value set of {0,1} assumed to mean a switch, without testing whether the four bytes are equal sample by sample | full-archive re-check (2026-09-20) |
| «`10:3004` looks like a date/time or a mileage-segmented record» | counter, BCD date, mileage/service structure and freeze frame are **all refuted** (all 70 width × endianness combinations show non-wrapping decreases; 20 of 70 produce illegal BCD and change in both directions within 1.4 s; subsets independently confirmed stationary by vehicle speed still show many distinct payloads) | a guess written from a few non-zero bytes in the first reading that happened to look like a date, with no width / endianness / BCD enumeration and no check of whether it is constant at rest | full-archive re-check (2026-09-20) |
| «The first 6 bytes of an ECM response are a general bitmap over the remaining 48» | the general model is **refuted**: 9 of the 58 DIDs that meet the length condition provide counter-examples. It holds on the 29 DIDs where the test has discriminating power, while 17 «zero counter-examples but no discriminating power» cases do not count as support. Among same-numbered pairs only 4 of 7 hold → «some members of a family share a header», not a family-wide bitmap | counting non-discriminating samples as positives | full-archive re-check (2026-09-20) |
| `WASTEGATE` decodes as unsigned 16-bit (giving a maximum of 65.532 in the statistics) | it is signed. Of 42,797 samples, 41,971 are ≤9000 and 826 are ≥65000 with nothing in between; the most negative value, −176, matches the tuning tool's over-travel | the note had said for a long time that the real range includes negatives, but the decode flag never followed, and nobody questioned a physically impossible maximum sitting in the statistics | bit-level coverage map and confidence review (2026-09-19) |
| An analysis script took wheel speed from `48C4[0:8]` | the mapping is at `[23:31]`. `[0:8]` is constant at `0000FFFFFFC00000` throughout the archive, which yields a fixed 327.52 km/h with zero derivative (a silent miss, never a false positive) | the offset of a reference quantity was hard-coded in an analysis script instead of being read from the decode table | per-log re-check over the whole archive (2026-09-19) |

## 11. Broadcast frames seen passively

**Essentially none.** There is a gateway behind this car's OBD-II connector, and no periodic vehicle CAN frames reach it with the key on, at idle or while driving. That is why everything in this document comes from active polling.

The only repeating frame in the archive that is not part of a request/response exchange appeared while passively recording a tuning tool session: **11-bit ID `0x784`, data `01 00 7E 6A 00 00 00 00`, roughly every 2.51 s**. Neither its sender nor its meaning is established — the tuning tool was on the bus at the time, so it cannot be ruled out as the source. No decoding is offered for it.

Two unusual diagnostic addresses were also seen: the functional broadcast `18DBEFF1` once, and `18DAF1EF` twice. Those are still request/response traffic, not vehicle broadcasts.

If what you want is chassis broadcast data (the kind covered by openpilot's `opendbc`), you have to tap the powertrain bus **inside** the gateway — the candidate points are the 12-pin front camera connector or the 32-pin cluster connector A. This project has **never** done that, so it offers no conclusions about that bus.

## 12. Method and evidence discipline

**Correlation is not identification.** Nothing enters the decode table without a sample-by-sample exact match (equal raw values, a fixed shift, or a fixed constant difference). Over ten minutes of idling every slow-moving quantity correlates with every other one; that kind of correlation counts for nothing.

**Peaks and counts are always computed over the complete log**, never while a log is still being written — doing that once turned 15,976 responses into 11,779 and a +1.16 bar peak into +0.85 bar.

**Spoken markers lag the event on the bus by 16–40 seconds**, repeatedly and consistently. So time alignment always uses an event visible on the bus (brake pressure, engine speed going to zero) as the anchor, with spoken markers only as a coarse index; fast-moving quantities are captured by holding a state for 30 seconds instead.

**Look for enumerated bits only while stationary** (driving quantities drown them out) and **for dynamic quantities only while driving**; then use a capture with no mode changes as a control to check that a candidate bit is not just a driving quantity.

**Negative conclusions must be qualified**: «not identified at the current sampling rate / encoding / set of DIDs», never «does not exist». This is the single most frequently overturned kind of conclusion here — both longitudinal G and the clutch were once wrongly declared absent.

**Graded evidence with stopping conditions**: before going to the data, write down what would count as supported, what would count as refuted, and what counts as too few samples; if the samples are too few, record `insufficient` rather than rounding it up into a conclusion. The «not identifiable» section of this document exists because of that rule.

**Keep the layers of evidence apart**: a format parsing is not a host accepting it, is not a display showing the right thing, is not the same car being a stock car; and numbers agreeing is not a calibration.

## 13. Known limits, and what data is still missing

- **One car** — every conclusion comes from the same FL5 with a Hondata FlashPro fitted. Whether a stock car's default session behaves the same, and whether `268F` answers at all, **has never been tested**.
- **No independent instruments** — the reference plane for oil pressure (gauge or absolute), the yaw and lateral-G scales, the °/LSB of the steering angle and the wastegate unit are all uncalibrated. The scale factors here are research fits, not calibrations.
- **Low sampling rate** — the research polled far more slowly than the tuning tool's 18 Hz (most extended quantities at 0.2–1.2 Hz). Sub-second transients and fast counters alias at that rate — which is exactly why the counter test on the damper module's live packet could only be recorded as «insufficient».
- **Incomplete scan coverage** — VSA `A083–FFFF`, EPS `2A31–FFFF`, everything outside `7000–70FF` on the cluster, the gateway pair `ED`/`EF`, `0x70` and the Honda Sensing sub-units were never scanned.
- **No data for cold or extreme conditions** — negative ambient temperatures can never be verified where this car is driven, and a single continuous cold-start-to-thermal-equilibrium recording is still missing.
- **What is still missing (no special driving required — ordinary commuting covers it)** — ① state 2 of `2610[39]` needs ≥10 independent high-boost events sampled at ≤0.1 s; ② separating absolute from gauge pressure needs a trip at a noticeably different barometric pressure; ③ the `268F` latch needs ≥10 set events; ④ the `2611` tail needs one sample with magnitude above 127 to fix its width; ⑤ Brake Hold needs ≥20 stops with pedal evidence at a matching rate; ⑥ the «constant» DIDs need one read each across several natural ignition cycles.
- **What needs an external reference** — an external yaw-rate reference (≥10 Hz, <3% error), a measured track width and rolling circumference, an independent lateral-G calibration, and independent ground truth for `3004` (service records, cluster readings or manufacturer documentation). Service `24` (read scaling data) returned `0x11` twice, so that route is closed.

## 14. Safety and legal notice

**This repository covers read-only diagnostics only.** Everything here was obtained with UDS service `22` (ReadDataByIdentifier), together with `3E` (tester present), `10 01/03` (session control) and ISO-TP flow control `30`. It **does not contain and will not provide** anything that bypasses security access.

**Services never used, and never to be used from this material**: `27` security access, `23` read memory by address, `2E` write data, `31` routine control, `11` ECU reset, `14` clear diagnostic information, `34–37` upload/download. Where a third-party tool's use of `27` / `23` is mentioned, it is only as something observed on the bus — no details are reproduced and no reimplementation is offered.

**A driver must never operate capture equipment while driving.** Anything that has to be recorded with the car in motion must be recorded by a capture that runs unattended from start to finish.

**Do not leave any other frame-sending device on the OBD connector while a tool is reflashing an ECU**; two testers using source address `F1` at the same time will collide.

**Writing to a vehicle bus carries real risk, and you do it at your own risk.** Nothing in this repository is a warranty of fitness for any purpose, and the authors accept no liability for any damage, injury, loss, failed inspection or voided warranty arising from its use. On a car you do not know, listen before you talk.

**Not affiliated with Honda.** This is an independent, non-commercial research record. «Honda», «Civic» and «Type R» are trademarks of Honda Motor Co., Ltd.; «Hondata» and «FlashPro» are trademarks of Hondata, Inc. They are used here only to identify the vehicle and the equipment involved, under nominative fair use. No endorsement, sponsorship or affiliation is claimed or implied, and no manufacturer documentation, firmware or proprietary protocol material is redistributed here.

The allow-list the capture tooling behind this data enforces on itself:

- Read-only services only: `22`, `21`, `24`, `3E`, `10 (01,03)` and ISO-TP flow control `30`; on 11-bit addresses, single-PID Mode 01 / 09 requests only.
- Only the agreed target addresses (`18DAxxF1` / `18DB33F1`); everything else is rejected.
- A minimum 2 ms gap between frames.
- Write, routine control, ECU reset, clear DTCs, security access, memory read, periodic and dynamic identifier definition, and DTC reads are all rejected outright.
- Sending requires three independent switches to be on at once (a process flag, an environment variable and an explicit confirmation in the UI); any one missing blocks the send.

## 15. Licence and attribution

**Documentation and data** — this README, `README.zh-CN.md`, `data/signals.json`, `data/signals.csv` and `signalsets/v3/default.json` — are licensed under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/). The full legal code is in [`LICENSE`](LICENSE).

**Code** — everything under `tools/` — is licensed under the [MIT licence](https://opensource.org/license/mit), see [`LICENSE-CODE`](LICENSE-CODE).

Attribute as: **Caldis, «Honda Civic Type R (FL5) — diagnostic signal reference»**, with a link back to this repository. Under ShareAlike, a derived data set has to carry the same licence.

**Attribution for material this work builds on**: several cross-checks in this reference are made against the [OBDb](https://github.com/OBDb) `Honda-Civic` signal set (fixed commit `8eb884dc5e9595b477f1fb5df0712d86736e3da9`), which is itself licensed CC BY-SA 4.0 — that is why this data set uses the same licence. The MSB0 bit-numbering convention used for `bix` follows the OBDb schema implementation at fixed commit `db6d0c5121c66a5c0b49f4edd79ea7a6f7c15c49`. Where this document contradicts those entries, the contradiction is stated explicitly in the refuted section; no OBDb file is redistributed here.

No manufacturer documentation, firmware, calibration file or proprietary protocol material is included or redistributed.

If you use this data set in published work, please cite it via [`CITATION.cff`](CITATION.cff) — GitHub renders a ready-made citation from it in the sidebar.

## 16. Data version and changelog

| Item | Value |
|---|---|
| `dataset_version` | `1.0.1` |
| `signals_csv_sha256` | `efee5056ec7338b4489e59071a4e3bd78fba9d0d9e7d84313eb593c031494041` |

`dataset_version` is the semantic version of this data set; `signals_csv_sha256` is the content hash of `data/signals.csv`, so you can check the copy in your hands against it.

Hashes are computed after normalising CRLF to LF, so they are identical on Windows, macOS and Linux.

### Changelog

| Version | Contents |
|---|---|
| 1.0.1 (2026-09-21) | Text-only correction release, no decoding changes: the Chinese descriptions of eight signals were aligned with the English evidence. `AC_REQUEST`, `BOOST_LOAD_STATE` and `YAW_RATE` now carry the conclusions of the 2026-09-20 full-archive re-check. `BRAKE_SWITCH_MIRROR` no longer reads «a mirror of the `4004` brake switch with 97.05% agreement» but «not a clean mirror: while bit3 is set, bit2 does not fall back when the pedal is released», and the agreement rate is now the 97.03% (2745/2829) measured at a 1.0 s tolerance. `WASTEGATE` mentions the change to signed decoding made on 2026-09-19. `STEER_MODE` was verified in three sessions, not two. `LATERAL_G_VSA_CANDIDATE` no longer claims «a ratio close to 1»: there are two independent lateral channels whose implied yaw scales differ by 35%. `BOOST_PRESSURE` has an observed ceiling of 215 kPa, not 202. |
| 1.0.0 (2026-09-21) | First public release. Covers every conclusion filed up to 2026-09-19, including the ten offline analyses completed on 2026-09-20. `WASTEGATE` is now signed. Seven claims were overturned and are recorded in the refuted section: the single threshold and hysteresis for `2610[39]`, «`268F[39]` is a high-load flag», the «four identical switches» in `268F`, all four readings of `10:3004`, «`48BD[21]` is not a mode byte», the strict-mirror reading of `4007[9] bit2`, and the general ECM header bitmap. Observed ranges are withheld for the two odometer signals: an exact odometer reading would identify one specific car. |
