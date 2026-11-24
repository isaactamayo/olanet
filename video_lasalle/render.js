// Uso: node render.js <dir_build> video          -> <dir_build>/video_mudo.mp4 + events.json
//      node render.js <dir_build> snap t1 t2 ... -> capturas PNG en esos segundos
const {chromium}=require('playwright');const {spawn}=require('child_process');const fs=require('fs');const path=require('path');
const [OUT,MODE,...TIMES]=process.argv.slice(2);
(async()=>{
 const b=await chromium.launch();
 const p=await b.newPage({viewport:{width:1080,height:1920}});
 const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
 await p.goto('file://'+path.join(__dirname,'escenas.html'));
 await p.evaluate(async()=>{await Promise.all(['400 40px Baloo','700 40px Baloo','800 40px Baloo','40px Chalk','40px "Noto Color Emoji"'].map(f=>document.fonts.load(f,'Aá🌍')));await document.fonts.ready});
 if(errs.length){console.error(errs);process.exit(1)}
 const {EVENTS,TOTAL,FPS}=await p.evaluate(()=>({EVENTS:window.EVENTS,TOTAL:window.TOTAL,FPS:window.TL.fps}));
 fs.writeFileSync(path.join(OUT,'events.json'),JSON.stringify({EVENTS,TOTAL}));
 if(MODE==='snap'){
  for(const t of TIMES){await p.evaluate(t=>render(t),+t);await p.screenshot({path:path.join(OUT,`snap_${t}.png`)});}
 }else{
  const N=Math.round(TOTAL*FPS);
  const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',''+FPS,'-c:v','mjpeg','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','19','-preset','medium',path.join(OUT,'video_mudo.mp4')],{stdio:['pipe','inherit','inherit']});
  for(let i=0;i<N;i++){await p.evaluate(t=>render(t),i/FPS);const buf=await p.screenshot({type:'jpeg',quality:92});
   if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
   if(i%240===0)console.log(`frame ${i}/${N}`);}
  ff.stdin.end();await new Promise(r=>ff.on('close',r));
 }
 if(errs.length)console.error(errs);
 await b.close();
})();
