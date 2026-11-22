#!/usr/bin/env python3
"""Generate vst/presets.json: 128 factory presets. Every non-momentary, non-text parameter is set (bits first, then notes)."""
import json, os, random
import variant_spec as S
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
MOODS=["Drift","Pulse","Bloom","Glide","Static","Tide","Ember","Orbit"]
TEMPO=[84,92,100,108,116,122,128,134,140,150]
def mk(n):
    r=random.Random(1000+n)
    sc=n%16; mood=MOODS[(n//16)%8]
    v={}
    kind=(n//16)%8   # character of the preset family
    dens=[.45,.6,.5,.7,.55,.4,.65,.5][kind]
    # bits first
    for s in (1,2):
        L=r.choice([4,5,6,7,8,8,8]) if kind in (1,4) else 8
        for i in range(8): v["bit%d_%d"%(s,i+1)]=1 if r.random()<(dens if s==1 else dens*.8) else 0
        v["bit%d_1"%s]=1 if s==1 else v["bit%d_1"%s]
        v["len%d"%s]=L-1
    for k in ("run","chain","buffer","lock1","lock2","seedlock","evolve_on","mute1","mute2"):
        v[k]=0
    v["chain"]=1 if kind==6 else 0
    v["ratelink"]=1 if kind in (0,3) else 0
    for s in (1,2):
        rg=r.choice([2,3,3,4]) if s==1 else r.choice([2,3,4,5])
        v["range%d"%s]=rg
        for i in range(8):
            v["note%d_%d"%(s,i+1)]=r.randrange(0,128)
            v["vel%d_%d"%(s,i+1)]=min(127,max(1,int(r.gauss(100,16))))
            v["gat%d_%d"%(s,i+1)]=min(200,max(25,int(r.gauss(100,30))))
    v["tempo"]=TEMPO[(n*3+kind)%len(TEMPO)]
    v["corr1"]=[0,10,25,40,0,15,30,5][kind]; v["corr2"]=[0,5,20,50,10,0,35,25][kind]
    v["egmix"]=r.choice([40,50,50,60,70])
    v["amount"]=r.choice([50,70,85,100]); v["density"]=int(dens*100); v["spread"]=r.choice([2,3,4,5])
    v["velvar"]=r.choice([15,25,40]); v["gatevar"]=r.choice([20,40,60]); v["evolve"]=r.choice([10,20,35,50])
    v["scope"]=3; v["target"]=2; v["seed"]=1000+n*313
    v["every"]=r.choice([1,2,2,3,4])
    v["prob1"]=r.choice([100,100,90,80]); v["prob2"]=r.choice([100,90,80,70])
    v["ratchet"]=[0,10,0,25,0,15,0,30][kind]
    v["swing"]=[50,54,50,58,60,50,56,62][kind]; v["human"]=r.choice([0,8,15,25]); v["gate"]=r.choice([40,55,60,75])
    v["scale"]=sc; v["root"]=r.randrange(12)
    v["ch1"]=1; v["ch2"]=2
    v["rate1"]=r.choice([3,5,5,5,6]); v["rate2"]=r.choice([3,3,5,5,6,2])
    if v["ratelink"]: v["rate2"]=v["rate1"]
    name="%s %s %02d"%(S.SCALES[sc][0].title(),mood,n+1)
    return {"name":name[:24],"values":v}
def main():
    pres=[mk(n) for n in range(128)]
    # make sure every non-momentary non-text param is set, in a stable order: bits, then everything else
    want=[p["key"] for p in S.P if p["kind"] not in ("mom","str") and p["key"] not in ("pos1","pos2")]
    out=[]
    for pr in pres:
        v=pr["values"]; miss=[k for k in want if k not in v]
        assert not miss,(pr["name"],miss)
        order=[k for k in want if k.startswith("bit")]+[k for k in want if not k.startswith("bit")]
        out.append({"name":pr["name"],"values":{k:v[k] for k in order}})
    json.dump({"presets":out},open(os.path.join(ROOT,"vst","presets.json"),"w"))
    print(len(out),"presets;",len(want),"params each")
if __name__=="__main__": main()
