import json,sys,wave,numpy as np
d=json.load(open(sys.argv[1]));E=d['EVENTS'];T=d['TOTAL']
SR=44100;N=int(T*SR);mix=np.zeros(N);rng=np.random.default_rng(7)
def add(sig,t,g=1.0):
    i=int(t*SR); 
    if i>=N:return
    sig=sig[:N-i]; mix[i:i+len(sig)]+=sig*g
def env(n,a=0.005,r=None):
    t=np.arange(n)/SR; e=np.minimum(1,t/a); 
    return e*np.exp(-t/(r or (n/SR/4)))
def tone(f,dur,kind='sine',r=None):
    n=int(dur*SR);t=np.arange(n)/SR;ph=2*np.pi*np.cumsum(np.broadcast_to(f,(n,)))/SR if np.ndim(f) else 2*np.pi*f*t
    s={'sine':np.sin(ph),'sq':np.sign(np.sin(ph))*0.5,'tri':2/np.pi*np.arcsin(np.sin(ph))}[kind]
    return s*env(n,r=r)
# ---- música: 112 bpm, C Am F G
bpm=112;beat=60/bpm;prog=[(130.81,[261.63,329.63,392.0]),(110.0,[220.0,261.63,329.63]),(87.31,[174.61,220.0,261.63]),(98.0,[196.0,246.94,293.66])]
mel=[523.25,0,659.25,587.33,523.25,0,392.0,440.0, 523.25,0,440.0,392.0,329.63,0,392.0,0, 349.23,0,440.0,523.25,587.33,0,523.25,440.0, 392.0,0,493.88,587.33,523.25,0,0,0]
t=0;bar=0
while t<T:
    root,ch=prog[bar%4]
    for b in range(4):
        tb=t+b*beat
        add(tone(root if b%2==0 else root*1.5,beat*0.9,'tri',r=0.18),tb,0.22)
        for f in ch: add(tone(f*2,beat*0.35,'sq',r=0.05),tb+beat/2,0.025)
        add(rng.normal(0,1,int(0.03*SR))*env(int(0.03*SR),r=0.008),tb+beat/2,0.03)  # hi-hat
    if (bar//4)%2==1:
        for k in range(8):
            f=mel[(bar%4)*8+k]
            if f: add(tone(f,beat*0.45,'sine',r=0.12),t+k*beat/2,0.05)
    t+=4*beat;bar+=1
mfade=np.ones(N);fo=int(2*SR);mfade[-fo:]=np.linspace(1,0,fo)
mix*=mfade
# ---- efectos
for e in E:
    k=e['k'];t0=e['t']
    if k=='pop':
        n=int(0.12*SR);f=np.linspace(500,1100,n);add(tone(f,0.12,'sine',r=0.04),t0,0.25)
    elif k=='stamp':
        n=int(0.35*SR);add(tone(np.linspace(140,50,n),0.35,'sine',r=0.12),t0+0.1,0.8);add(rng.normal(0,1,n)*env(n,r=0.05),t0+0.1,0.3)
    elif k=='whoosh':
        n=int(0.5*SR);w=rng.normal(0,1,n);w=np.convolve(w,np.ones(30)/30,'same');add(w*np.hanning(n),max(0,t0-0.25),0.35)
    elif k=='strike':
        n=int(0.09*SR);add(rng.normal(0,1,n)*env(n,r=0.03)*np.sin(np.linspace(0,60,n)),t0,0.25)
    elif k=='swap':
        add(tone(np.linspace(300,120,int(0.25*SR)),0.25,'sq',r=0.1),t0,0.18)
    elif k=='ring':
        n=int((e['t1']-t0)*SR);tt=np.arange(n)/SR;s=np.sin(2*np.pi*(np.where((tt*20)%2<1,880,1100))*tt)*((tt%0.8)<0.6)
        add(s*0.5,t0,0.25)
    elif k=='shake':
        add(tone(np.linspace(600,300,int(0.4*SR)),0.4,'tri',r=0.2),t0,0.2)
    elif k=='type':
        base={'pm':170,'cl':330,'none':240}.get(e.get('who'),240)
        kind={'pm':'sq','cl':'sine','none':'tri'}.get(e.get('who'),'tri')
        tt=t0
        while tt<e['t1']:
            dur=rng.uniform(0.06,0.1);f=base*rng.choice([1,1.12,1.25,1.33,1.5])
            add(tone(f,dur,kind,r=0.03),tt,0.12 if kind=='sq' else 0.2)
            tt+=dur+0.02
mix/=max(1e-9,np.abs(mix).max())/0.85
w=wave.open(sys.argv[2],'wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((mix*32767).astype(np.int16).tobytes());w.close()
