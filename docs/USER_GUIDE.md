# VARIANT user guide (0.1.2)

VARIANT is a MIDI-only generative sequencer: it makes no sound. Put it on a track, send its MIDI to the tracks you want to play.

## 1. Get its MIDI to another track
MPC OS ignores a plugin's own MIDI output, so VARIANT creates a MIDI port named **VARIANT / MIDI Out**.
1. Open Preferences > MIDI and enable **Track** on the VARIANT port.
2. On the instrument track you want to play, set its MIDI input to that port.
3. Use channel 1 for SEQ 1 and channel 2 for SEQ 2 (change them on page 3).

## 2. Running it
- With the project playing, VARIANT follows the song position. With the project stopped, RUN/STOP starts its own clock at the TEMPO knob.
- Steps are sent at the start of each audio block (about 3 ms): timing is steady but not sample-accurate.
- MUTE (page 3) silences a sequence; it also stops notes that are held.

## 3. Page 1 SEQUENCER
Tap a step tile to switch it on or off; the white outline is the playhead. LEN sets the sequence length (1 to 8). SHIFT moves the pattern
left or right, FLIP reverses it. TRIGGER restarts both sequences, RESET returns the playhead to step 1, ADVANCE steps forward by hand: with the project stopped it plays the next step straight away (press it again for the next one), and while running it skips one step ahead.
CHAIN SEQ plays SEQ 1 then SEQ 2 as one line. BUFFER ON stores the current pattern; BUFFER OFF brings it back.
CORR 1/2 is the chance that a sequence mutates (a note moves, and above 50% a step flips) each time it wraps.
RANGE 1/2 is the note span in octaves; EG MIX scales velocity (50% = as stored).

## 4. Page 2 RANDOMIZER
RANDOMIZE builds new content from the SEED; each press picks a new seed unless SEED LOCK is on. SEED left/right use the neighbouring seed,
NEW SEED picks a fresh one. WHAT chooses BITS, NOTES, VELOC or ALL; WHERE chooses SEQ 1, SEQ 2 or BOTH. LOCK 1/2 protect a sequence.
AMOUNT is how much of the pattern is replaced, DENSITY how many steps are on, SPREAD the note spread in octaves, VEL VAR and GATE VAR the
velocity and gate variation. UNDO/REDO step through your last 32 changes. EVOLVE ON mutates the pattern every EVERY bars by the EVOLVE amount.

## 5. Page 3 PLAY / MIDI
PROB sets each step's chance of playing. RATCHET is the chance a step plays twice. SWING delays every second step. HUMAN adds small velocity and
length variation (not timing). GATE is the note length. SCALE and ROOT quantise the notes. CH, MUTE and RATE are per sequence; RATE LINK makes SEQ 2 follow SEQ 1.
A note played into the track transposes both sequences (middle C = no transposition).

## 6. Presets and Q-Links
128 factory presets are in MPC's PRESET menu; save your own the normal MPC way. Each page has its own Q-Link set for the controls shown on it.
The data wheel steps the selected option or value.

## Status
Works on the Akai Force (tested by the author). Please report anything odd on the Force or on an MPC.
