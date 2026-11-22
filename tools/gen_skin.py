#!/usr/bin/env python3
"""Generate the VARIANT skin art + layout.conf (run: python3 tools/gen_skin.py). Needs Pillow, numpy, scipy, Inter fonts.
Panel look = the approved top-lit panel (page1/2/3 sketches). Writes skin/art/*.png and skin/layout.conf."""
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.join(HERE,"..")
sys.path.insert(0,HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from knob_render import render
import variant_spec as S
ART=os.path.join(ROOT,"skin","art"); os.makedirs(ART,exist_ok=True)
W,H=1280,628
BG=(36,34,30); RED=(224,58,46); LINE=(120,118,112); TXT=(236,234,228); OFF=(58,56,51)
FB='/usr/share/fonts/opentype/inter/Inter-Bold.otf'; FS='/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
f26=ImageFont.truetype(FB,26); f30=ImageFont.truetype(FB,30); f40=ImageFont.truetype(FB,40)

class Page:
    def __init__(s,n,title):
        s.n=n; s.alb=Image.new('RGB',(W,H),BG); s.da=ImageDraw.Draw(s.alb)
        s.hm=Image.new('F',(W,H),0.0); s.dh=ImageDraw.Draw(s.hm); s.texts=[]; s.ctl=[]; s.lines=[]
        s.da.rectangle([0,0,W,54],fill=(24,23,20)); s.dh.rectangle([0,0,W,54],fill=-4.0)
        s.T(20,27,"VARIANT",f40,TXT,'lm')
    def T(s,x,y,t,f,fill=TXT,a='mm'): s.texts.append((x,y,t,f,fill,a))
    def raised(s,b,fill,r=8,h=14.0): s.da.rounded_rectangle(b,r,fill=fill); s.dh.rounded_rectangle(b,r,fill=h)
    def recessed(s,b,r=8,h=-6.0): s.dh.rounded_rectangle(b,r,fill=h)
    def readout(s,x,y,w,h,t=None,r=8):
        if w<=0: return
        s.recessed([x,y,x+w,y+h],r,-8.0); s.da.rounded_rectangle([x,y,x+w,y+h],r,fill=(20,19,17))
        if t: s.T(x+w/2,y+h/2,t,f26)
    def block(s,y0,label):
        s.recessed([384,y0-4,1264,y0+160],8,-6.0); s.da.rounded_rectangle([384,y0-4,1264,y0+160],8,fill=(30,28,25))
        s.T(396,y0+22,label,f30,TXT,'lm')
    def add(s,kind,key,x,y,w,h,label,label_on=None,font=None,num=None,outline=None):
        s.ctl.append(dict(kind=kind,key=key,x=x,y=y,w=w,h=h,label=label,label_on=label_on or label,font=font or (f30 if len(label)<9 else f26)))
    def finish(s,on,segs=False):
        """draw the tiles (all off or all on) into the albedo/height maps, then light it; returns the image (no knobs)"""
        alb=s.alb.copy(); da=ImageDraw.Draw(alb); hm=s.hm.copy(); dh=ImageDraw.Draw(hm); tx=list(s.texts)
        for c in s.ctl:
            if c['kind']=='ro' or (c['kind']=='seg' and not segs): continue
            b=[c['x'],c['y'],c['x']+c['w'],c['y']+c['h']]
            da.rounded_rectangle(b,8,fill=RED if on else OFF); dh.rounded_rectangle(b,8,fill=14.0)
            tx.append((c['x']+c['w']/2,c['y']+c['h']/2,c['label_on'] if on else c['label'],c['font'],(255,255,255) if on else TXT,'mm'))
        a=np.asarray(alb).astype(float)/255
        red=np.all(np.asarray(alb)==np.array(RED),axis=2).astype(float)
        glow=ndi.gaussian_filter(red,9)[...,None]*np.array([.9,.12,.08])*0.55
        h=ndi.gaussian_filter(np.asarray(hm).astype(float),2.2)
        gy,gx=np.gradient(h); nx,ny=-gx*1.1,-gy*1.1; nl=np.sqrt(nx*nx+ny*ny+1); nx,ny,nz=nx/nl,ny/nl,1/nl
        L=np.array([0,-.5,.866]); L/=np.linalg.norm(L); Hh=L+np.array([0,0,1.]); Hh/=np.linalg.norm(Hh)
        ndl=np.clip(nx*L[0]+ny*L[1]+nz*L[2],0,1); ndh=np.clip(nx*Hh[0]+ny*Hh[1]+nz*Hh[2],0,1)
        flat=(.33+.10)+.52*L[2]; shade=((.33+.10*nz)+.52*ndl)/flat; spec=.10*ndh**38-.10*(Hh[2]**38)
        sh=ndi.shift(ndi.gaussian_filter(np.clip(h,0,None)/14,5),(5,0),order=1)
        out=a*shade[...,None]+spec[...,None]*.9
        out=out*(1-.45*np.clip(sh,0,1)[...,None]*(h<1)[...,None])+glow
        img=Image.fromarray((np.clip(out,0,1)*255+.5).astype(np.uint8)); d=ImageDraw.Draw(img)
        d.line([0,54,W,54],fill=LINE,width=2)
        for x,y,t,f,fill,an in tx: d.text((x,y),t,font=f,fill=fill,anchor=an)
        return img

# ---------------- page definitions: tiles + layout lines ----------------
KNOB_Y=58; KR=58   # 2r+10=126 px frames x128 = 16128 px: under MPC's 16384 px limit (r=59 sits exactly on it and drifts on screen)
def knob_lines(p,keys):
    cw=W/6
    for i,k in enumerate(keys):
        cx=int(cw*i+cw/2); name=[q["name"] for q in S.P if q["key"]==k][0]
        p.lines.append('knob cx=%d cy=%d r=%d label="%s" key=%s strip=art/knob.png frames=64 bw=212'%(cx,120,KR,name,k))
def header(p,boxes):
    """boxes: list of (x0,x1,text|None,key|None)"""
    for x0,x1,t,k in boxes:
        p.readout(x0,8,x1-x0,38,t,6)
        if k: p.add('ro',k,x0,8,x1-x0,38,"")
    p.readout(1140,8,126,38,"PAGE %d / 3"%p.n,6)
def left(p,items):
    tx,ty,tw,th=16,290,172,100; pos=0
    for it in items:   # (kind,key,label,label_on,span)
        kind,key,label,lon,span=it; r,c=divmod(pos,2)
        ww=tw*2+16 if span else tw; x=tx+c*(tw+16); y=ty+r*(th+12)
        if kind=='ro': p.readout(x,y,ww,th,None,8); p.add('ro',key,x,y,ww,th,"")
        else: p.add(kind,key,x,y,ww,th,label,lon,f30 if len(label)<9 else f26)
        pos+=2 if span else 1
def row2(p,y0,items):
    for j,(kind,key,label,lon) in enumerate(items):
        x=396+j*216; y=y0+82
        if kind=='ro': p.readout(x,y,204,66,None,8); p.add('ro',key,x,y,204,66,"")
        else: p.add(kind,key,x,y,204,66,label,lon,f30 if len(label)<9 else f26)
def segs(p,y0,key,labels,x=508):
    p.seg.append((key,x,y0+4,labels))
    for i,l in enumerate(labels): p.add('seg',key+"#%d"%i,x+i*188,y0+4,182,62,"",None,f26)

def build():
    pages=[]
    # ---- page 1 ----
    p=Page(1,"SEQUENCER"); p.seg=[]
    header(p,[(380,560,None,"tx_bpm"),(580,790,None,"tx_scale_full"),(810,960,None,"tx_root_full"),(980,1130,None,"tx_rate_full")])
    knob_lines(p,S.PAGES[0]["knobs"])
    left(p,[("toggle","run","RUN / STOP",None,0),("button","trigger","TRIGGER",None,0),("toggle","chain","CHAIN SEQ",None,0),
            ("toggle","buffer","BUFFER",None,0),("button","reset","RESET",None,0),("button","advance","ADVANCE",None,0)])
    for s in (1,2):
        y0=290+(s-1)*172; p.block(y0,"SEQ %d"%s)
        for i in range(8): p.add('toggle','bit%d_%d'%(s,i+1),488+i*96,y0+4,90,62,str(i+1),None,f30)
        row2(p,y0,[("popup","len%d"%s,"",None),("button","shift%d_l"%s,"SHIFT ◄",None),("button","shift%d_r"%s,"SHIFT ►",None),("button","flip%d"%s,"FLIP",None)])
        p.lines.append(('pos',s,488,y0+4))
    p.q=("SEQUENCER","tempo,corr1,corr2,range1,range2,egmix,run,chain,buffer,len1,len2,flip1,flip2"); pages.append(p)
    # ---- page 2 ----
    p=Page(2,""); p.seg=[]
    header(p,[(380,560,"RANDOMIZER",None),(580,790,None,"tx_seed_full"),(810,960,None,"tx_scope_full"),(980,1130,None,"tx_target_full")])
    knob_lines(p,S.PAGES[1]["knobs"])
    left(p,[("button","randomize","RANDOMIZE",None,1),("button","undo","UNDO",None,0),("button","redo","REDO",None,0),
            ("toggle","lock1","LOCK 1",None,0),("toggle","lock2","LOCK 2",None,0)])
    p.block(290,"WHAT"); segs(p,290,"scope",["BITS","NOTES","VELOC","ALL"])
    row2(p,290,[("button","seed_prev","SEED ◄",None),("ro","tx_seed","",None),("button","seed_next","SEED ►",None),("button","seed_new","NEW SEED",None)])
    p.block(462,"WHERE"); segs(p,462,"target",["SEQ 1","SEQ 2","BOTH"])
    p.add('toggle','seedlock',508+3*188,466,182,62,"SEED LOCK",None,f26)
    row2(p,462,[("toggle","evolve_on","EVOLVE OFF","EVOLVE ON"),("button","every_prev","EVERY ◄",None),("ro","tx_every","",None),("button","every_next","EVERY ►",None)])
    p.q=("RANDOMIZER","amount,density,spread,velvar,gatevar,evolve,scope,target,seedlock,evolve_on,every,lock1,lock2"); pages.append(p)
    # ---- page 3 ----
    p=Page(3,""); p.seg=[]
    header(p,[(380,560,"PLAY / MIDI",None),(580,790,None,"tx_scale_full"),(810,960,None,"tx_root_full"),(980,1130,None,"tx_outch")])
    knob_lines(p,S.PAGES[2]["knobs"])
    left(p,[("button","scale_prev","SCALE ◄",None,0),("button","scale_next","SCALE ►",None,0),("button","root_prev","ROOT ◄",None,0),
            ("button","root_next","ROOT ►",None,0),("ro","tx_scale","",None,0),("ro","tx_root","",None,0)])
    for s in (1,2):
        y0=290+(s-1)*172; p.block(y0,"SEQ %d"%s)
        for j,(kind,key,label) in enumerate([("button","ch%d_prev"%s,"CH ◄"),("ro","tx_ch%d"%s,""),("button","ch%d_next"%s,"CH ►"),("toggle","mute%d"%s,"MUTE")]):
            x=508+j*188
            if kind=='ro': p.readout(x,y0+4,182,62,None,8); p.add('ro',key,x,y0+4,182,62,"")
            else: p.add(kind,key,x,y0+4,182,62,label,None,f30)
        row2(p,y0,[("button","rate%d_prev"%s,"RATE ◄",None),("ro","tx_rate%d"%s,"",None),("button","rate%d_next"%s,"RATE ►",None),("toggle","ratelink","RATE LINK",None)])
    p.q=("PLAY / MIDI","prob1,prob2,ratchet,swing,human,gate,scale,root,rate1,rate2,mute1,mute2,ratelink"); pages.append(p)
    return pages

LENS=["LEN %d"%i for i in range(1,9)]
POPUPS={"tx_scale":("scale",[x[0] for x in S.SCALES]),"tx_root":("root",list(S.ROOTS)),
        "tx_rate1":("rate1",[x[0] for x in S.RATES]),"tx_rate2":("rate2",[x[0] for x in S.RATES]),"tx_every":("every",[x[0] for x in S.EVERY])}
def main():
    pages=build()
    # shared knob strip (frames cut from the approved knob render over the panel colour)
    fr=[render((225/255,225/255,233/255),-135+270*i/63).resize((116,116),Image.LANCZOS) for i in range(64)]
    bgc=Image.open(os.path.join(ART,"bg1.png")).convert('RGB').getpixel((20,120)) if os.path.exists(os.path.join(ART,"bg1.png")) else BG
    st=Image.new('RGB',(126,126*64),bgc)
    for i,f in enumerate(fr): st.paste(f,(5,126*i+5))
    st.save(os.path.join(ART,"knob.png"))
    conf=["label_scale=1.7","scale_names=1","art_css=art.css",""]
    for p in pages:
        off=p.finish(False); on=p.finish(True)
        off.save(os.path.join(ART,"bg%d.png"%p.n))
        conf.append("[tab %s]"%p.q[0]); conf.append("art file=art/bg%d.png fit=stretch"%p.n)
        for c in p.ctl:
            if c['kind'] in ('ro','seg','popup'): continue
            nm="p%d_%s"%(p.n,c['key']); box=(c['x'],c['y'],c['x']+c['w'],c['y']+c['h'])
            off.crop(box).save(os.path.join(ART,nm+".png")); on.crop(box).save(os.path.join(ART,nm+"_on.png"))
        for line in p.lines:
            if isinstance(line,str): conf.append(line)
        for c in p.ctl:
            cx=c['x']+c['w']//2; cy=c['y']+c['h']//2; nm="art/p%d_%s"%(p.n,c['key'])
            if c['kind']=='ro' and c['key'] in POPUPS:
                k,opts=POPUPS[c['key']]
                conf.append('popup cx=%d cy=%d w=%d h=%d label="" key=%s options="%s" tsize=%d tcolor=ece9e3'%(cx,cy,c['w']-8,c['h']-8,k,",".join(opts),28 if c['w']<180 else 34)); continue
            if c['kind']=='ro': conf.append('readout cx=%d cy=%d w=%d h=%d label="" key=%s tsize=%d tcolor=ece9e3'%(cx,cy,c['w']-8,c['h']-8,c['key'],30 if c['h']<60 else 34)); continue
            if c['kind']=='seg': continue
            if c['kind']=='popup':
                opts=",".join(["LEN %d"%i for i in range(1,9)])
                conf.append('popup cx=%d cy=%d w=%d h=%d label="" key=%s options="%s" tsize=30 tcolor=ece9e3'%(cx,cy,c['w'],c['h'],c['key'],opts)); continue
            conf.append('%s cx=%d cy=%d w=%d h=%d ns=0 label="" key=%s img=%s.png img_on=%s_on.png'%(c['kind'],cx,cy,c['w'],c['h'],c['key'],nm,nm))
        for key,x,y,labels in p.seg:
            n=len(labels); SW=185
            so=p.finish(False,True); sn=p.finish(True,True)
            for nm2,im in (("seg_off",so),("seg_on",sn)):
                a=Image.new('RGBA',(SW,62),(0,0,0,0)); a.paste(im.crop((x,y,x+182,y+62)).convert('RGBA'),(1,0)); a.save(os.path.join(ART,"p%d_%s_%s.png"%(p.n,key,nm2)))
            conf.append('enum_h cx=%d cy=%d key=%s label="" options="%s" sw=%d sh=62 img=art/p%d_%s_seg_off.png img_on=art/p%d_%s_seg_on.png'%(x+(n*SW+(n-1)*2)//2,y+31,key,",".join(labels),SW,p.n,key,p.n,key))
        for line in p.lines:
            if isinstance(line,tuple):
                _,s,x,y=line; key="pos%d"%s
                files=[]
                for i in range(9):
                    im=Image.new('RGBA',(8*96-6,62),(0,0,0,0))
                    if i<8: ImageDraw.Draw(im).rounded_rectangle([i*96,0,i*96+89,61],8,outline=(255,255,255),width=5)
                    fn="art/p%d_pos%d_%d.png"%(p.n,s,i); im.save(os.path.join(ROOT,"skin",fn)); files.append(fn)
                conf.append('picture x=%d y=%d w=%d h=62 key=%s files="%s"'%(x,y,8*96-6,key,",".join(files)))
        conf.append('qlinks "%s" = %s'%p.q); conf.append("")
    open(os.path.join(ROOT,'skin','art.css'),'w').write(':root { --seg-size: 26px; }\n.seg-tx { font-weight: 700; letter-spacing: 0; }\n')
    import re
    conf=[re.sub(r"\b(cy|y)=(\d+)",lambda m:"%s=%d"%(m.group(1),int(m.group(2))+86),l) for l in conf]   # plugin area starts 86 px down
    open(os.path.join(ROOT,"skin","layout.conf"),"w").write("\n".join(conf)+"\n")

    # ---- control map + numbered overlays (one place to read every control's position; layout.conf is the editable source) ----
    LM=os.path.join(ROOT,"skin","layout_map"); os.makedirs(LM,exist_ok=True)
    rows=["id,page,type,key,x,y,w,h,printed_label,label_px"]; n=0
    fnt=ImageFont.truetype(FB,18)
    for p in pages:
        ov=Image.open(os.path.join(ART,"bg%d.png"%p.n)).convert('RGB'); d=ImageDraw.Draw(ov)
        items=[]
        for i,k in enumerate(S.PAGES[p.n-1]["knobs"]):
            items.append(("knob",k,int(W/6*i+W/12)-58,120-58,116,116,"%s (live name 35.7 px, value 37.4 px)"%k,36))
        for c in p.ctl: items.append((c['kind'],c['key'],c['x'],c['y'],c['w'],c['h'],c['label'],26 if c['font']==f26 else 30))
        for kind,key,x,y,w,h,lab,px in items:
            n+=1; d.rectangle([x,y,x+w,y+h],outline=(0,255,255),width=2); d.text((x+4,y+2),str(n),font=fnt,fill=(255,255,0))
            rows.append('%d,%d,%s,%s,%d,%d,%d,%d,"%s",%d'%(n,p.n,kind,key,x,y,w,h,lab.replace('"',''),px))
        ov.save(os.path.join(LM,"overlay_page%d.png"%p.n))
    open(os.path.join(LM,"controls.csv"),"w").write("\n".join(rows)+"\n")
    print("pages",len(pages),"conf lines",len(conf))
if __name__=="__main__": main()
