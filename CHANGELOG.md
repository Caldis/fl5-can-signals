# Changelog

This file tracks the data set version. The version is semantic: the major number
changes when a decoding changes in a way that breaks existing consumers, the minor
number when signals are added, the patch number for corrections to text or evidence.

## 1.0.1 (2026-09-21)

Text-only correction release, no decoding changes: the Chinese descriptions of eight signals were aligned with the English evidence. `AC_REQUEST`, `BOOST_LOAD_STATE` and `YAW_RATE` now carry the conclusions of the 2026-09-20 full-archive re-check. `BRAKE_SWITCH_MIRROR` no longer reads «a mirror of the `4004` brake switch with 97.05% agreement» but «not a clean mirror: while bit3 is set, bit2 does not fall back when the pedal is released», and the agreement rate is now the 97.03% (2745/2829) measured at a 1.0 s tolerance. `WASTEGATE` mentions the change to signed decoding made on 2026-09-19. `STEER_MODE` was verified in three sessions, not two. `LATERAL_G_VSA_CANDIDATE` no longer claims «a ratio close to 1»: there are two independent lateral channels whose implied yaw scales differ by 35%. `BOOST_PRESSURE` has an observed ceiling of 215 kPa, not 202.

## 1.0.0 (2026-09-21)

First public release. Covers every conclusion filed up to 2026-09-19, including the ten offline analyses completed on 2026-09-20. `WASTEGATE` is now signed. Seven claims were overturned and are recorded in the refuted section: the single threshold and hysteresis for `2610[39]`, «`268F[39]` is a high-load flag», the «four identical switches» in `268F`, all four readings of `10:3004`, «`48BD[21]` is not a mode byte», the strict-mirror reading of `4007[9] bit2`, and the general ECM header bitmap. Observed ranges are withheld for the two odometer signals: an exact odometer reading would identify one specific car.
