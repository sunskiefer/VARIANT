# VARIANT

Dual generative 8-step MIDI sequencer for the Akai Force / MPC OS (VST2, ARMv7), by L'Cronx. It plays no sound of its own:
it sends notes to other tracks over MIDI. Two sequences, a bit pattern per step, a randomizer with undo/redo and seeds,
16 scales, chain mode and a pattern buffer. Built from a Max for Live device (Labyrinth) as the model; the panel is our own drawing.

**Status: 0.1.2, tested on a Force.** It is built for MPC OS 3.x (first-generation ARMv7 devices, like the Force).
The catalog check passes; the sequencer timing, the MIDI port and the touch screen have not been run on real hardware yet.

## What it does
- **Page 1 SEQUENCER**: TEMPO, CORR 1/2 (corrupt: mutates a sequence each time it wraps), RANGE 1/2 (octaves), EG MIX (velocity scale);
  RUN/STOP, TRIGGER, CHAIN SEQ (SEQ 1 then SEQ 2 as one 16-step line), BUFFER (ON saves the pattern, OFF recalls it), RESET, ADVANCE (plays the next step by hand, also when stopped);
  per sequence 8 step tiles with a playhead, LEN, SHIFT left/right, FLIP.
- **Page 2 RANDOMIZER**: AMOUNT, DENSITY, SPREAD, VEL VAR, GATE VAR, EVOLVE; RANDOMIZE, UNDO, REDO, LOCK 1/2; WHAT (BITS, NOTES, VELOC, ALL),
  SEED with previous/next/new, WHERE (SEQ 1, SEQ 2, BOTH), SEED LOCK, EVOLVE ON/OFF and EVERY (1 to 16 bars).
- **Page 3 PLAY / MIDI**: PROB 1/2, RATCHET, SWING, HUMAN, GATE; 16 SCALES and 12 ROOTS; per sequence MIDI channel, MUTE and RATE (1 to 1/32, triplets), RATE LINK.
- 128 factory presets; your own presets use MPC's normal preset saving (no slot limit).
- A MIDI note played into the track transposes the sequences (note minus middle C).

## MIDI output
MPC OS ignores MIDI that a plugin sends out, so VARIANT opens its own MIDI port, **VARIANT / MIDI Out**. In MPC, open Preferences > MIDI and
enable **Track** on that port, then choose it as the input of the tracks you want to play. See the [user guide](docs/USER_GUIDE.md).

## Install
Download `VARIANT-0.1.2-mpc-armv7.zip` from the releases, unzip, and follow `INSTALL.md` inside (needs root shell access).

## Build
`tools/gen_params.py`, `tools/gen_skin.py`, `tools/gen_presets.py` generate the parameters, skin and presets; `build.sh` compiles the engine
(zig cc, armhf, glibc 2.31) and the wrapper from [mpc-vst-plugins](https://github.com/sd88me/mpc-vst-plugins) links it. The panel layout is
`skin/layout.conf` with a numbered overlay and control table in `skin/layout_map/`.

## Pictures
![Page 1](docs/img/page1_sequencer.png)
![Page 2](docs/img/page2_randomizer.png)
![Page 3](docs/img/page3_play_midi.png)

(Skin previews: the live values and names are drawn by MPC on the device.)

## Licence
PolyForm Noncommercial 1.0.0 (see `LICENSE`): free to use, not for sale. The plugin wrapper belongs to its authors under their own licence.
