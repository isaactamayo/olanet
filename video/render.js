const {chromium}=require('playwright');const {spawn}=require('child_process');const fs=require('fs');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:720}});
await p.goto('file:///home/user/olanet/video/escenas.html');
const {EVENTS,TOTAL}=await p.evaluate(()=>({EVENTS:window.EVENTS,TOTAL:window.TOTAL}));
fs.writeFileSync(process.argv[2]+'/events.json',JSON.stringify({EVENTS,TOTAL}));
const FPS=24,N=Math.round(TOTAL*FPS);
const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',''+FPS,'-c:v','mjpeg','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-preset','medium',process.argv[2]+'/video_mudo.mp4'],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await p.evaluate(t=>render(t),i/FPS);const buf=await p.screenshot({type:'jpeg',quality:92});
 if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('frames',N);})();
