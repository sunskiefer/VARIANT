# Changelog

## 0.1.2 (tested on a Force)
- Two builds: `-mpc-armv7.zip` (Force and Gen1, tested on a Force, MPC OS 3.9.1) and `-mpc-aarch64.zip` (Gen2, same code, not tested on a Gen2 device). Tested on the Force only.
- ADVANCE now plays the next step immediately when the project is stopped (step by hand); while running it still skips one step ahead.

## 0.1.1 (superseded by 0.1.2)
- Fix: knobs drifted up and down on screen. The knob strip is now 126 px frames x 128 = 16128 px (knob radius 58), under MPC's 16384 px image limit; 0.1.0 used radius 59, which sits exactly on the limit.

## 0.1.0 (knobs drift on screen: replaced by 0.1.1)
- First build: dual 8-step generative MIDI sequencer, three pages (SEQUENCER, RANDOMIZER, PLAY / MIDI).
- Randomizer with seeds, undo/redo, locks and evolve; 16 scales, chain, buffer, ratchet, swing, humanize.
- MIDI out on its own port, VARIANT / MIDI Out (MPC ignores plugin MIDI output).
- 128 factory presets. Layout file and numbered overlays shipped in the zip (`layout/`).
