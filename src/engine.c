/* VARIANT engine: dual generative 8-step MIDI sequencer for Force / MPC OS (mpc-vst-plugins wrapper).
 * MIDI only: render() writes silence. Notes leave on an ALSA sequencer port ("VARIANT" / "MIDI Out") because MPC OS ignores
 * a plugin's VST MIDI output (docs/MIDI_TIMING.md in the wrapper repo). libasound is opened at run time (dlopen).
 * Timing: steps are derived from the host song position (ppq) each block and sent at the block start (128 frames);
 * with the host stopped and RUN on, an internal clock at the TEMPO knob drives them. */
#include <alsa/asoundlib.h>
#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "engine.h"
#include "params_gen.h"

#define NEVT 512
#define NSNAP 32

typedef struct { double t; int ch, note, vel; } evt_t;      /* vel 0 = note off */
typedef struct { float bit[2][8], note[2][8], vel[2][8], gat[2][8]; int seed; } snap_t;

typedef struct {
    float v[NPAR];
    unsigned char dirty[NPAR];
    int scan;
    int rev;
    /* ALSA */
    void *lib; snd_seq_t *seq; int port;
    int (*f_open)(snd_seq_t **, const char *, int, int);
    int (*f_name)(snd_seq_t *, const char *);
    int (*f_port)(snd_seq_t *, const char *, unsigned, unsigned);
    int (*f_out)(snd_seq_t *, snd_seq_event_t *);
    int (*f_close)(snd_seq_t *);
    /* timing */
    double ppq_int, last_end, bpm;
    int have_end, was_active;
    long nextn[2];
    double nextsb[2];
    long base[2];
    int lastpos[2];
    long bar_done;
    int transpose;
    unsigned rng;
    evt_t ev[NEVT]; int nev;
    snap_t undo[NSNAP], redo[NSNAP]; int nundo, nredo;
    snap_t buf; int have_buf;
    int manual[2];
    long man;          /* ADVANCE while stopped: step counter */
    double idle_t;     /* ADVANCE while stopped: its own clock, so note-offs fall due */
} V;

static unsigned hash32(unsigned a, unsigned b, unsigned c, unsigned d) {
    unsigned h = a * 0x9E3779B1u ^ (b + 0x7F4A7C15u) * 0x85EBCA6Bu ^ (c + 0x165667B1u) * 0xC2B2AE35u ^ (d + 0x27D4EB2Fu) * 0x9E3779B9u;
    h ^= h >> 15; h *= 0x2C1B3C6Du; h ^= h >> 12; h *= 0x297A2D39u; h ^= h >> 15;
    return h;
}
static float hf(unsigned a, unsigned b, unsigned c, unsigned d) { return (hash32(a, b, c, d) & 0xFFFFFF) / 16777216.0f; }
static float rnd(V *x) { x->rng ^= x->rng << 13; x->rng ^= x->rng >> 17; x->rng ^= x->rng << 5; return (x->rng & 0xFFFFFF) / 16777216.0f; }

static int idx_of(const char *k) {
    for (int i = 0; i < NPAR; i++) if (!strcmp(VPD[i].key, k)) return i;
    return -1;
}
static void mark(V *x, int i) { x->dirty[i] = 1; }
static void setv(V *x, int i, float val) {
    if (val < VPD[i].min) val = VPD[i].min;
    if (val > VPD[i].max) val = VPD[i].max;
    if (x->v[i] != val) { x->v[i] = val; mark(x, i); }
}
static int B(V *x, int s, int i) { return P_bit1_1 + s * 8 + i; }
static int N(V *x, int s, int i) { (void)x; return P_note1_1 + s * 8 + i; }
static int VL(V *x, int s, int i) { (void)x; return P_vel1_1 + s * 8 + i; }
static int G(V *x, int s, int i) { (void)x; return P_gat1_1 + s * 8 + i; }
static int ilen(V *x, int s) { return 1 + (int)x->v[s ? P_len2 : P_len1]; }
static int chan(V *x, int s) { return (int)x->v[s ? P_ch2 : P_ch1] - 1; }
static int rate_of(V *x, int s) { int r = (int)x->v[(s && !(int)x->v[P_ratelink]) ? P_rate2 : P_rate1]; return r < 0 ? 0 : r > 7 ? 7 : r; }

/* ---- MIDI output ---- */
static void alsa_open(V *x) {
    x->lib = dlopen("libasound.so.2", RTLD_NOW);
    if (!x->lib) return;
    x->f_open = dlsym(x->lib, "snd_seq_open");
    x->f_name = dlsym(x->lib, "snd_seq_set_client_name");
    x->f_port = dlsym(x->lib, "snd_seq_create_simple_port");
    x->f_out = dlsym(x->lib, "snd_seq_event_output_direct");
    x->f_close = dlsym(x->lib, "snd_seq_close");
    if (!x->f_open || !x->f_name || !x->f_port || !x->f_out) return;
    if (x->f_open(&x->seq, "default", SND_SEQ_OPEN_OUTPUT, 0) < 0) { x->seq = NULL; return; }
    x->f_name(x->seq, "VARIANT");
    x->port = x->f_port(x->seq, "MIDI Out", SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ,
                        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
}
static void send_midi(V *x, int ch, int note, int vel) {
    if (!x->seq || x->port < 0) return;
    snd_seq_event_t e;
    snd_seq_ev_clear(&e);
    snd_seq_ev_set_source(&e, x->port);
    snd_seq_ev_set_subs(&e);
    snd_seq_ev_set_direct(&e);
    if (vel > 0) snd_seq_ev_set_noteon(&e, ch & 15, note & 127, vel);
    else snd_seq_ev_set_noteoff(&e, ch & 15, note & 127, 0);
    x->f_out(x->seq, &e);
}
static void push(V *x, double t, int ch, int note, int vel) {
    if (x->nev >= NEVT) return;
    x->ev[x->nev++] = (evt_t){ t, ch, note, vel };
}
static void flush_due(V *x, double upto, int all) {
    /* offs first, then ons, each in time order; simple selection passes */
    for (int pass = 0; pass < 2; pass++) {
        for (;;) {
            int best = -1;
            for (int i = 0; i < x->nev; i++) {
                int isoff = x->ev[i].vel == 0;
                if ((pass == 0) != isoff) continue;
                if (!all && x->ev[i].t >= upto) continue;
                if (best < 0 || x->ev[i].t < x->ev[best].t) best = i;
            }
            if (best < 0) break;
            if (pass == 1 || x->ev[best].vel == 0) send_midi(x, x->ev[best].ch, x->ev[best].note, x->ev[best].vel);
            if (pass == 1 && all) { /* discarding unsent note-ons when silencing */ }
            x->ev[best] = x->ev[--x->nev];
        }
    }
}
static void silence(V *x) {
    /* send every pending note-off, drop pending note-ons */
    int n = 0;
    for (int i = 0; i < x->nev; i++) if (x->ev[i].vel == 0) x->ev[n++] = x->ev[i];
    x->nev = n;
    flush_due(x, 0, 1);
}

/* ---- pattern helpers ---- */
static void snap_take(V *x, snap_t *s) {
    for (int q = 0; q < 2; q++) for (int i = 0; i < 8; i++) {
        s->bit[q][i] = x->v[B(x, q, i)]; s->note[q][i] = x->v[N(x, q, i)];
        s->vel[q][i] = x->v[VL(x, q, i)]; s->gat[q][i] = x->v[G(x, q, i)];
    }
    s->seed = (int)x->v[P_seed];
}
static void snap_put(V *x, const snap_t *s) {
    for (int q = 0; q < 2; q++) for (int i = 0; i < 8; i++) {
        setv(x, B(x, q, i), s->bit[q][i]); setv(x, N(x, q, i), s->note[q][i]);
        setv(x, VL(x, q, i), s->vel[q][i]); setv(x, G(x, q, i), s->gat[q][i]);
    }
    setv(x, P_seed, s->seed);
}
static void push_undo(V *x) {
    if (x->nundo == NSNAP) { memmove(x->undo, x->undo + 1, sizeof(snap_t) * (NSNAP - 1)); x->nundo--; }
    snap_take(x, &x->undo[x->nundo++]);
    x->nredo = 0;
}
static int pitch_of(V *x, int s, float nv) {
    int range = (int)x->v[s ? P_range2 : P_range1];
    int semis = (int)floorf(nv / 127.0f * range * 12 + 0.5f);
    int sc = (int)x->v[P_scale]; if (sc < 0 || sc >= 16) sc = 0;
    int oct = semis / 12, deg = semis % 12, best = 0;
    for (int k = 0; k < SCALE_N[sc]; k++) if (SCALE_IV[sc][k] <= deg) best = SCALE_IV[sc][k];
    int p = 48 + (int)x->v[P_root] + oct * 12 + best + x->transpose;
    return p < 0 ? 0 : p > 127 ? 127 : p;
}
static int scope_has(V *x, int what) { int sc = (int)x->v[P_scope]; return sc == 3 || sc == what; }
static void randomize_with(V *x, unsigned seed) {
    int tg = (int)x->v[P_target];
    float amount = x->v[P_amount] / 100.f, dens = x->v[P_density] / 100.f;
    float spread = x->v[P_spread], vv = x->v[P_velvar] / 100.f, gv = x->v[P_gatevar] / 100.f;
    for (int s = 0; s < 2; s++) {
        if (tg != 2 && tg != s) continue;
        if ((int)x->v[s ? P_lock2 : P_lock1]) continue;
        int range = (int)x->v[s ? P_range2 : P_range1];
        float half = 63.5f * fminf(1.f, spread / (float)range);
        for (int i = 0; i < 8; i++) {
            if (scope_has(x, 0) && hf(seed, s, i, 1) < amount) setv(x, B(x, s, i), hf(seed, s, i, 2) < dens ? 1 : 0);
            if (scope_has(x, 1) && hf(seed, s, i, 3) < amount) setv(x, N(x, s, i), floorf(63.5f + (hf(seed, s, i, 4) * 2 - 1) * half + 0.5f));
            if (scope_has(x, 2) && hf(seed, s, i, 5) < amount) {
                setv(x, VL(x, s, i), floorf(100 + (hf(seed, s, i, 6) * 2 - 1) * vv * 80 + 0.5f));
                setv(x, G(x, s, i), floorf(100 + (hf(seed, s, i, 7) * 2 - 1) * gv * 75 + 0.5f));
            }
        }
    }
}
static void apply_seed(V *x, int seed) {
    push_undo(x);
    if (seed < 1) seed = 99999;
    if (seed > 99999) seed = 1;
    setv(x, P_seed, seed);
    randomize_with(x, (unsigned)seed);
}
static void shift_seq(V *x, int s, int dir) {
    int n = ilen(x, s);
    float a[4][8];
    for (int i = 0; i < n; i++) { a[0][i] = x->v[B(x, s, i)]; a[1][i] = x->v[N(x, s, i)]; a[2][i] = x->v[VL(x, s, i)]; a[3][i] = x->v[G(x, s, i)]; }
    for (int i = 0; i < n; i++) {
        int j = (i + dir + n) % n;
        setv(x, B(x, s, j), a[0][i]); setv(x, N(x, s, j), a[1][i]); setv(x, VL(x, s, j), a[2][i]); setv(x, G(x, s, j), a[3][i]);
    }
}
static void flip_seq(V *x, int s) {
    int n = ilen(x, s);
    for (int i = 0; i < n / 2; i++) {
        int j = n - 1 - i;
        int ks[4] = { B(x, s, i), N(x, s, i), VL(x, s, i), G(x, s, i) }, kj[4] = { B(x, s, j), N(x, s, j), VL(x, s, j), G(x, s, j) };
        for (int q = 0; q < 4; q++) { float t = x->v[ks[q]]; setv(x, ks[q], x->v[kj[q]]); setv(x, kj[q], t); }
    }
}
static void corrupt_seq(V *x, int s, float amt) {
    int n = ilen(x, s);
    int i = (int)(rnd(x) * n) % n;
    setv(x, N(x, s, i), x->v[N(x, s, i)] + (rnd(x) - 0.5f) * 30.f * (amt < 0.5f ? 0.5f : 1.f));
    if (amt >= 0.5f) { int j = (int)(rnd(x) * n) % n; setv(x, B(x, s, j), 1 - x->v[B(x, s, j)]); }
}
static void evolve_now(V *x) {
    float p = x->v[P_evolve] / 100.f;
    int tg = (int)x->v[P_target];
    for (int s = 0; s < 2; s++) {
        if (tg != 2 && tg != s) continue;
        if ((int)x->v[s ? P_lock2 : P_lock1]) continue;
        int n = ilen(x, s);
        for (int i = 0; i < n; i++) {
            if (rnd(x) >= p * 0.5f) continue;
            if (scope_has(x, 0) && rnd(x) < 0.4f) setv(x, B(x, s, i), 1 - x->v[B(x, s, i)]);
            if (scope_has(x, 1)) setv(x, N(x, s, i), x->v[N(x, s, i)] + (rnd(x) - 0.5f) * 40.f);
            if (scope_has(x, 2)) setv(x, VL(x, s, i), x->v[VL(x, s, i)] + (rnd(x) - 0.5f) * 40.f * x->v[P_velvar] / 100.f);
        }
    }
}

/* ---- sequencing ---- */
static double step_beats(V *x, int s) { return RATE_BEATS[rate_of(x, s)]; }
static double step_time(V *x, long n, double sb) {
    double sw = (x->v[P_swing] / 100.0) * 2.0 - 1.0;
    return n * sb + ((n & 1) ? sw * sb : 0.0);
}
static void fire(V *x, int s, int pos, double t, double sb) {
    if (!(int)x->v[B(x, s, pos)]) return;
    if ((int)x->v[s ? P_mute2 : P_mute1]) return;
    float prob = x->v[s ? P_prob2 : P_prob1] / 100.f;
    if (prob < 1.f && rnd(x) >= prob) return;
    float hum = x->v[P_human] / 100.f;
    float egf = x->v[P_egmix] / 50.f;
    float vel = x->v[VL(x, s, pos)] * egf + (rnd(x) - 0.5f) * 2.f * hum * 30.f;
    int iv = (int)(vel + 0.5f); if (iv < 1) iv = 1; if (iv > 127) iv = 127;
    int note = pitch_of(x, s, x->v[N(x, s, pos)]);
    int ch = chan(x, s);
    double gl = sb * (x->v[P_gate] / 100.0) * (x->v[G(x, s, pos)] / 100.0) * (1.0 + (rnd(x) - 0.5) * hum * 0.5);
    if (gl < 0.01) gl = 0.01;
    int rat = x->v[P_ratchet] > 0 && rnd(x) < x->v[P_ratchet] / 100.f;
    if (rat) gl *= 0.5;
    push(x, t, ch, note, iv);
    push(x, t + gl, ch, note, 0);
    if (rat) {
        push(x, t + sb * 0.5, ch, note, (iv * 3 + 3) / 4);
        push(x, t + sb * 0.5 + gl, ch, note, 0);
    }
}
static void seq_pos(V *x, int s, int k, double t, double sb) { (void)t; (void)sb; x->lastpos[s] = k; (void)s; }
static void play_range(V *x, double t0, double t1) {
    int chain = (int)x->v[P_chain];
    int l1 = ilen(x, 0), l2 = ilen(x, 1);
    for (int s = 0; s < 2; s++) {
        double sb = step_beats(x, chain ? 0 : s);
        if (sb != x->nextsb[s]) { x->nextsb[s] = sb; x->nextn[s] = (long)ceil(t0 / sb - 1e-9); }
        if (chain && s == 1) { x->nextn[1] = x->nextn[0]; continue; }  /* chain: seq 1 drives both */
        int guard = 0;
        while (guard++ < 64) {
            double t = step_time(x, x->nextn[s], sb);
            if (t >= t1) break;
            long n = x->nextn[s] - x->base[s];
            if (t >= t0 - 0.5) {
                if (chain) {
                    int L = l1 + l2; int k = (int)(((n % L) + L) % L);
                    int sq = k < l1 ? 0 : 1, pos = k < l1 ? k : k - l1;
                    fire(x, sq, pos, t, sb);
                    x->lastpos[sq] = pos; x->lastpos[1 - sq] = -1;
                    if (k == L - 1) {
                        if (x->v[P_corr1] > 0 && rnd(x) < x->v[P_corr1] / 100.f) corrupt_seq(x, 0, x->v[P_corr1] / 100.f);
                        if (x->v[P_corr2] > 0 && rnd(x) < x->v[P_corr2] / 100.f) corrupt_seq(x, 1, x->v[P_corr2] / 100.f);
                    }
                } else {
                    int L = s ? l2 : l1; int pos = (int)(((n % L) + L) % L);
                    fire(x, s, pos, t, sb);
                    x->lastpos[s] = pos;
                    if (pos == L - 1) {
                        float c = x->v[s ? P_corr2 : P_corr1];
                        if (c > 0 && rnd(x) < c / 100.f) corrupt_seq(x, s, c / 100.f);
                    }
                }
            }
            x->nextn[s]++;
        }
    }
    (void)seq_pos;
}
static void show_pos(V *x) {
    for (int s = 0; s < 2; s++) {
        int p = x->lastpos[s] < 0 ? 8 : x->lastpos[s];
        if ((int)x->v[s ? P_pos2 : P_pos1] != p) { x->v[s ? P_pos2 : P_pos1] = (float)p; x->rev++; }
    }
}

static void reset_pos(V *x, double ppq) {
    for (int s = 0; s < 2; s++) {
        double sb = step_beats(x, s);
        x->nextsb[s] = sb;
        x->nextn[s] = (long)ceil(ppq / sb - 1e-9);
        x->base[s] = x->nextn[s];
    }
}

static void *create(const char *d) {
    (void)d;
    V *x = calloc(1, sizeof *x);
    for (int i = 0; i < NPAR; i++) x->v[i] = VPD[i].def;
    x->rng = 0x1234567u; x->port = -1; x->man = -1;
    x->v[P_pos1] = x->v[P_pos2] = 8;
    x->lastpos[0] = x->lastpos[1] = -1;
    for (int i = 0; i < NPAR; i++) x->dirty[i] = 0;
    alsa_open(x);
    return x;
}
static void destroy(void *i) {
    V *x = i;
    silence(x);
    if (x->seq && x->f_close) x->f_close(x->seq);
    if (x->lib) dlclose(x->lib);
    free(x);
}
static void midi(void *i, const uint8_t *m, int n) {
    V *x = i;
    if (n >= 3 && (m[0] & 0xf0) == 0x90 && m[2]) {
        int t = (int)m[1] - 60;
        x->transpose = t < -24 ? -24 : t > 24 ? 24 : t;
        x->rev++;
    }
}
static void action(V *x, int k) {
    switch (k) {
    case P_trigger: reset_pos(x, x->have_end ? x->last_end : 0.0); x->manual[0] = x->manual[1] = 0; x->man = -1; break;
    case P_reset: for (int s = 0; s < 2; s++) { x->base[s] = x->nextn[s]; x->lastpos[s] = -1; } x->man = -1; break;
    case P_advance:
        if (x->was_active) { for (int s = 0; s < 2; s++) x->base[s]--; break; }   /* running: skip one step ahead */
        x->man++;                                                                   /* stopped: play the next step now */
        if ((int)x->v[P_chain]) {
            int l1 = ilen(x, 0), l2 = ilen(x, 1), L = l1 + l2, k = (int)(x->man % L);
            int sq = k < l1 ? 0 : 1, pos = k < l1 ? k : k - l1;
            fire(x, sq, pos, x->idle_t, step_beats(x, 0));
            x->lastpos[sq] = pos; x->lastpos[1 - sq] = -1;
        } else for (int s = 0; s < 2; s++) {
            int pos = (int)(x->man % ilen(x, s));
            fire(x, s, pos, x->idle_t, step_beats(x, s));
            x->lastpos[s] = pos;
        }
        flush_due(x, x->idle_t + 1e-6, 0);
        show_pos(x);
        break;
    case P_shift1_l: shift_seq(x, 0, -1); break;
    case P_shift1_r: shift_seq(x, 0, 1); break;
    case P_shift2_l: shift_seq(x, 1, -1); break;
    case P_shift2_r: shift_seq(x, 1, 1); break;
    case P_flip1: flip_seq(x, 0); break;
    case P_flip2: flip_seq(x, 1); break;
    case P_randomize:
        if (!(int)x->v[P_seedlock]) { int ns = (int)(hash32((unsigned)x->v[P_seed], 7, 7, 7) % 99999) + 1; setv(x, P_seed, ns); }
        push_undo(x); randomize_with(x, (unsigned)x->v[P_seed]); break;
    case P_seed_new: { int ns = (int)(hash32((unsigned)x->v[P_seed], 11, (unsigned)x->rev, 3) % 99999) + 1; apply_seed(x, ns); break; }
    case P_seed_prev: apply_seed(x, (int)x->v[P_seed] - 1); break;
    case P_seed_next: apply_seed(x, (int)x->v[P_seed] + 1); break;
    case P_undo:
        if (x->nundo) {
            if (x->nredo < NSNAP) snap_take(x, &x->redo[x->nredo++]);
            snap_put(x, &x->undo[--x->nundo]);
        } break;
    case P_redo:
        if (x->nredo) {
            if (x->nundo < NSNAP) snap_take(x, &x->undo[x->nundo++]);
            snap_put(x, &x->redo[--x->nredo]);
        } break;
    default: break;
    }
    x->rev++;
}
static void set_param(void *i, const char *k, const char *val) {
    V *x = i;
    int p = idx_of(k);
    if (p < 0 || VPD[p].kind == 3) return;
    float f = (float)atof(val);
    if (VPD[p].kind == 2) { if (f >= 0.5f) action(x, p); return; }
    float old = x->v[p];
    if (f < VPD[p].min) f = VPD[p].min;
    if (f > VPD[p].max) f = VPD[p].max;
    x->v[p] = f;
    if (p == P_buffer && old != f) {
        if (f >= 0.5f) { snap_take(x, &x->buf); x->have_buf = 1; }
        else if (x->have_buf) snap_put(x, &x->buf);
    }
    if (p == P_mute1 || p == P_mute2) { if (f >= 0.5f) silence(x); }
    x->rev++;
}
static int get_param(void *i, const char *k, char *b, int n) {
    V *x = i;
    if (!strcmp(k, "display_rev")) return snprintf(b, n, "%d", x->rev);
    int sc = (int)x->v[P_scale], rt = (int)x->v[P_root];
    if (sc < 0 || sc > 15) sc = 0;
    if (rt < 0 || rt > 11) rt = 0;
    if (!strcmp(k, "tx_bpm")) return snprintf(b, n, "%d BPM", (int)(x->bpm > 0 && (int)x->was_active ? x->bpm + 0.5 : x->v[P_tempo] + 0.5));
    if (!strcmp(k, "tx_scale_full")) return snprintf(b, n, "%s", SCALE_NAME[sc]);
    if (!strcmp(k, "tx_scale")) return snprintf(b, n, "%s", SCALE_NAME[sc]);
    if (!strcmp(k, "tx_root_full")) return snprintf(b, n, "ROOT %s", ROOT_NAME[rt]);
    if (!strcmp(k, "tx_root")) return snprintf(b, n, "ROOT %s", ROOT_NAME[rt]);
    if (!strcmp(k, "tx_rate_full")) return snprintf(b, n, "%s", RATE_NAME[rate_of(x, 0)]);
    if (!strcmp(k, "tx_seed")) return snprintf(b, n, "%d", (int)x->v[P_seed]);
    if (!strcmp(k, "tx_seed_full")) return snprintf(b, n, "SEED %d", (int)x->v[P_seed]);
    if (!strcmp(k, "tx_scope_full")) { static const char *S[4] = { "BITS", "NOTES", "VELOC", "ALL" }; return snprintf(b, n, "%s", S[(int)x->v[P_scope] & 3]); }
    if (!strcmp(k, "tx_target_full")) { static const char *T[3] = { "SEQ 1", "SEQ 2", "BOTH" }; int t = (int)x->v[P_target]; return snprintf(b, n, "%s", T[t < 0 || t > 2 ? 2 : t]); }
    if (!strcmp(k, "tx_outch")) return snprintf(b, n, "CH %d / CH %d", (int)x->v[P_ch1], (int)x->v[P_ch2]);
    if (!strcmp(k, "tx_ch1")) return snprintf(b, n, "CH %d", (int)x->v[P_ch1]);
    if (!strcmp(k, "tx_ch2")) return snprintf(b, n, "CH %d", (int)x->v[P_ch2]);
    if (!strcmp(k, "tx_rate1")) return snprintf(b, n, "%s", RATE_NAME[rate_of(x, 0)]);
    if (!strcmp(k, "tx_rate2")) return snprintf(b, n, "%s", RATE_NAME[rate_of(x, 1)]);
    if (!strcmp(k, "tx_every")) { int e = (int)x->v[P_every]; static const char *E[5] = { "1 BAR", "2 BARS", "4 BARS", "8 BARS", "16 BARS" }; return snprintf(b, n, "%s", E[e < 0 || e > 4 ? 2 : e]); }
    int p = idx_of(k);
    if (p >= 0) return snprintf(b, n, "%g", x->v[p]);
    return 0;
}
int mpc_engine_changed(void *i, char *key, int len) {
    V *x = i;
    while (x->scan < NPAR) {
        int p = x->scan++;
        if (x->dirty[p]) { x->dirty[p] = 0; snprintf(key, len, "%s", VPD[p].key); return 1; }
    }
    x->scan = 0;
    return 0;
}
static void render(void *i, int16_t *o, int f) { (void)i; memset(o, 0, (size_t)f * 4); }

static void song_pos(void *i, double ppq, double bpm, int playing, int frames) {
    V *x = i;
    int host = playing && ppq >= 0 && bpm > 0;
    int run = (int)x->v[P_run];
    int active = host || run;
    double tempo = host ? bpm : x->v[P_tempo];
    double t0, t1;
    x->bpm = tempo;
    if (!active) {
        x->idle_t += frames * x->v[P_tempo] / 60.0 / 44100.0;   /* lets a manual ADVANCE note end */
        flush_due(x, x->idle_t, 0);
        if (x->was_active) { silence(x); x->was_active = 0; x->have_end = 0; x->lastpos[0] = x->lastpos[1] = -1; show_pos(x); }
        return;
    }
    if (host) t0 = ppq; else {
        if (!x->was_active || x->have_end == 0) x->ppq_int = 0;
        t0 = x->ppq_int;
    }
    t1 = t0 + frames * tempo / 60.0 / 44100.0;
    if (!x->was_active) { reset_pos(x, t0); x->was_active = 1; x->bar_done = (long)floor(t0 / 4.0); }
    else if (x->have_end && (t0 < x->last_end - 1.0 || t0 > x->last_end + 1.0)) { reset_pos(x, t0); x->bar_done = (long)floor(t0 / 4.0); }
    x->have_end = 1;
    /* evolve at bar boundaries */
    if ((int)x->v[P_evolve_on]) {
        static const int EV[5] = { 1, 2, 4, 8, 16 };
        int e = (int)x->v[P_every]; if (e < 0 || e > 4) e = 2;
        long bar = (long)floor(t0 / 4.0);
        if (bar > x->bar_done) { if (bar % EV[e] == 0) evolve_now(x); x->bar_done = bar; }
    }
    play_range(x, t0, t1);
    flush_due(x, t1, 0);
    show_pos(x);
    x->last_end = t1;
    if (!host) x->ppq_int = t1;
}

static const mpc_engine_t ENGINE = { create, destroy, midi, set_param, get_param, render, NULL, song_pos };
const mpc_engine_t *mpc_engine(void) { return &ENGINE; }
