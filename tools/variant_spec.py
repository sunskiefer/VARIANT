"""VARIANT: the single source of truth for parameters (VST index order, append only), scales, roots, rates and
the page/knob layout. Everything else (params.json, params_gen.h, layout.conf, presets.json, skin art) is generated from here."""
SCALES = [  # name, semitones inside one octave
 ("CHROMATIC",[0,1,2,3,4,5,6,7,8,9,10,11]), ("MAJOR",[0,2,4,5,7,9,11]), ("DORIAN",[0,2,3,5,7,9,10]),
 ("PENTATONIC",[0,2,4,7,9]), ("MEL MINOR",[0,2,3,5,7,9,11]), ("HARM MINOR",[0,2,3,5,7,8,11]),
 ("DIMINISHED",[0,2,3,5,6,8,9,11]), ("WHOLE TONE",[0,2,4,6,8,10]), ("HIRAJOSHI",[0,2,3,7,8]),
 ("7SUS4",[0,5,7,10]), ("MAJ7",[0,4,7,11]), ("MAJ13",[0,2,4,7,9,11]), ("MIN11",[0,2,3,5,7,10]),
 ("HANG DRUM",[0,2,3,5,7,8,10]), ("QUADS",[0,3,5,8,10]), ("BLUES",[0,3,5,6,7,10])]
ROOTS = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
RATES = [("1",4.0),("1/2",2.0),("1/4",1.0),("1/8",0.5),("1/8T",1/3),("1/16",0.25),("1/16T",1/6),("1/32",0.125)]
EVERY = [("1 BAR",1),("2 BARS",2),("4 BARS",4),("8 BARS",8),("16 BARS",16)]
SCOPES = ["BITS","NOTES","VELOC","ALL"]
TARGETS = ["SEQ 1","SEQ 2","BOTH"]
OFFON = ["off","on"]
P = []   # dicts: key,name,kind,min,max,def,opts,display,unit,momentary,step_of,step_delta,poll
def add(key,name,kind="val",mn=0,mx=1,df=0,opts=None,display=None,unit=None,**kw):
    d=dict(key=key,name=name,kind=kind,min=mn,max=mx,default=df,opts=opts,display=display,unit=unit); d.update(kw); P.append(d)
def knob(key,name,mn,mx,df,unit=None): add(key,name,"val",mn,mx,df,display="int",unit=unit)
def tog(key,name,df=0): add(key,name,"opt",opts=OFFON,df=df)
def mom(key,name,**kw): add(key,name,"mom",momentary=True,**kw)
def txt(key,name): add(key,name,"str",display="string",poll=True)
# ---- page 1 SEQUENCER ----
knob("tempo","TEMPO",30,300,120); knob("corr1","CORR 1",0,100,0,"%"); knob("corr2","CORR 2",0,100,0,"%")
knob("range1","RANGE 1",1,10,3); knob("range2","RANGE 2",1,10,3); knob("egmix","EG MIX",0,100,50,"%")
tog("run","RUN / STOP"); mom("trigger","TRIGGER"); tog("chain","CHAIN SEQ"); tog("buffer","BUFFER"); mom("reset","RESET"); mom("advance","ADVANCE")
add("len1","LEN 1","opt",opts=["LEN %d"%i for i in range(1,9)],df=7); add("len2","LEN 2","opt",opts=["LEN %d"%i for i in range(1,9)],df=7)
mom("shift1_l","SHIFT 1 LEFT"); mom("shift1_r","SHIFT 1 RIGHT"); mom("shift2_l","SHIFT 2 LEFT"); mom("shift2_r","SHIFT 2 RIGHT")
mom("flip1","FLIP 1"); mom("flip2","FLIP 2")
for s in (1,2):
    for i in range(1,9): tog("bit%d_%d"%(s,i),"SEQ %d STEP %d"%(s,i),df=int(i in ((1,3,5,6,8) if s==1 else (1,4,7))))
add("pos1","PLAYHEAD 1","opt",opts=[str(i) for i in range(1,9)]+["-"],df=8,poll=False)
add("pos2","PLAYHEAD 2","opt",opts=[str(i) for i in range(1,9)]+["-"],df=8,poll=False)
txt("tx_bpm","BPM TEXT"); txt("tx_scale_full","SCALE TEXT"); txt("tx_root_full","ROOT TEXT"); txt("tx_rate_full","RATE TEXT")
# ---- page 2 RANDOMIZER ----
knob("amount","AMOUNT",0,100,70,"%"); knob("density","DENSITY",0,100,50,"%"); knob("spread","SPREAD",1,10,3)
knob("velvar","VEL VAR",0,100,25,"%"); knob("gatevar","GATE VAR",0,100,40,"%"); knob("evolve","EVOLVE",0,100,20,"%")
mom("randomize","RANDOMIZE"); mom("undo","UNDO"); mom("redo","REDO"); tog("lock1","LOCK 1"); tog("lock2","LOCK 2")
add("scope","SCOPE","opt",opts=SCOPES,df=3); add("target","TARGET","opt",opts=TARGETS,df=2); tog("seedlock","SEED LOCK"); tog("evolve_on","EVOLVE ON")
add("seed","SEED","val",1,99999,48213,display="int")
mom("seed_prev","SEED PREV"); mom("seed_next","SEED NEXT"); mom("seed_new","NEW SEED")
add("every","EVERY","opt",opts=[e[0] for e in EVERY],df=2); mom("every_prev","EVERY PREV",step_of="every",step_delta=-1); mom("every_next","EVERY NEXT",step_of="every",step_delta=1)
txt("tx_seed","SEED TEXT"); txt("tx_seed_full","SEED TEXT FULL"); txt("tx_scope_full","SCOPE TEXT"); txt("tx_target_full","TARGET TEXT")
# ---- page 3 PLAY / MIDI ----
knob("prob1","PROB 1",0,100,100,"%"); knob("prob2","PROB 2",0,100,100,"%"); knob("ratchet","RATCHET",0,100,0,"%")
knob("swing","SWING",50,75,50,"%"); knob("human","HUMAN",0,100,0,"%"); knob("gate","GATE",10,100,60,"%")
add("scale","SCALE","opt",opts=[s[0] for s in SCALES],df=2); add("root","ROOT","opt",opts=ROOTS,df=0)
mom("scale_prev","SCALE PREV",step_of="scale",step_delta=-1); mom("scale_next","SCALE NEXT",step_of="scale",step_delta=1)
mom("root_prev","ROOT PREV",step_of="root",step_delta=-1); mom("root_next","ROOT NEXT",step_of="root",step_delta=1)
add("ch1","CH 1","val",1,16,1,display="int"); add("ch2","CH 2","val",1,16,2,display="int")
mom("ch1_prev","CH 1 PREV",step_of="ch1",step_delta=-1); mom("ch1_next","CH 1 NEXT",step_of="ch1",step_delta=1)
mom("ch2_prev","CH 2 PREV",step_of="ch2",step_delta=-1); mom("ch2_next","CH 2 NEXT",step_of="ch2",step_delta=1)
tog("mute1","MUTE 1"); tog("mute2","MUTE 2")
add("rate1","RATE 1","opt",opts=[r[0] for r in RATES],df=5); add("rate2","RATE 2","opt",opts=[r[0] for r in RATES],df=5)
mom("rate1_prev","RATE 1 PREV",step_of="rate1",step_delta=-1); mom("rate1_next","RATE 1 NEXT",step_of="rate1",step_delta=1)
mom("rate2_prev","RATE 2 PREV",step_of="rate2",step_delta=-1); mom("rate2_next","RATE 2 NEXT",step_of="rate2",step_delta=1)
tog("ratelink","RATE LINK",1)
txt("tx_scale","SCALE NAME"); txt("tx_root","ROOT NAME"); txt("tx_outch","OUT CHANNELS"); txt("tx_ch1","CH 1 NAME"); txt("tx_ch2","CH 2 NAME")
txt("tx_rate1","RATE 1 NAME"); txt("tx_rate2","RATE 2 NAME"); txt("tx_every","EVERY NAME")
# ---- per-step data (hidden, but real parameters so presets, automation and projects keep every note) ----
for s in (1,2):
    for i in range(1,9): add("note%d_%d"%(s,i),"SEQ %d NOTE %d"%(s,i),"val",0,127,(37*i+11*s)%128,display="int",poll=False)
for s in (1,2):
    for i in range(1,9): add("vel%d_%d"%(s,i),"SEQ %d VEL %d"%(s,i),"val",1,127,100,display="int",poll=False)
for s in (1,2):
    for i in range(1,9): add("gat%d_%d"%(s,i),"SEQ %d GATE %d"%(s,i),"val",25,200,100,display="int",poll=False)
KEYS=[p["key"] for p in P]
# ---- knob rows (key, label shown under the knob) per page ----
PAGES = [
 dict(n=1,title="SEQUENCER",knobs=["tempo","corr1","corr2","range1","range2","egmix"]),
 dict(n=2,title="RANDOMIZER",knobs=["amount","density","spread","velvar","gatevar","evolve"]),
 dict(n=3,title="PLAY / MIDI",knobs=["prob1","prob2","ratchet","swing","human","gate"]),
]
