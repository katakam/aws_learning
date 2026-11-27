/* Step engine + spoken narration (Web Speech API, no audio files).
   Scenes = <section class="scene" data-title="...">.
   [data-s="k"] visible from step k;  [data-a="k j"] highlighted at step k/j;
   path.flow[data-s="k"] dot travels when step k is reached.
   Narration of step i = (step 0 only: "why this matters" card) + caption + analogy. */
(function(){
  const scenes=[...document.querySelectorAll('.scene')];
  const tabsEl=document.querySelector('.tabs');
    const SVGNS='http://www.w3.org/2000/svg';
  const $=s=>document.querySelector(s);
  let si=0, step=0, playing=false, token=0, tmr=null;

  scenes.forEach((sc,i)=>{
    if(tabsEl && scenes.length>1){
      const b=document.createElement('button');b.className='tab';b.textContent=sc.dataset.title||('Scene '+(i+1));
      b.onclick=()=>go(i);tabsEl.appendChild(b);
    }
  });
  if(tabsEl && scenes.length<=1) tabsEl.remove();
  const cur=()=>scenes[si];
  const steps=()=>cur().querySelectorAll('.caps li').length-1;

  /* ---------- narration (pre-recorded MP3: audio/<page>-<scene>-<step>.mp3) ---------- */
  const slug=document.body.dataset.page;
  const audio=new Audio(); audio.preload='auto';
  const msg=t=>{const m=$('#amsg'); if(m) m.textContent=t||''};
  const narrateOn=()=>$('#nar') && $('#nar').checked;
  function stopSpeech(){ token++; clearTimeout(tmr); audio.onended=null; audio.onerror=null; try{audio.pause()}catch(e){} }
  function speakClip(sceneIdx,i,done,fallbackMs){
    const my=++token; clearTimeout(tmr);
    const fin=()=>{ if(my===token) done&&done(); };
    const fail=t=>{ if(my!==token) return; msg(t); tmr=setTimeout(fin,fallbackMs||3500); };
    audio.onended=()=>{ msg(''); setTimeout(fin,300); };
    audio.onerror=()=>fail('Could not load the audio file for this step. Check that the audio folder is next to the page.');
    audio.src='audio/'+slug+'-'+sceneIdx+'-'+i+'.mp3';
    audio.playbackRate=+($('#spd')||{value:1}).value;
    msg('🔊 Playing narration…');
    const pr=audio.play();
    if(pr&&pr.catch) pr.catch(()=>fail('Your browser blocked audio. Click Play or Next again, and check the device is not muted.'));
  }

  /* ---------- rendering ---------- */
  function render(spawn){
    const sc=cur();
    sc.querySelectorAll('[data-s]').forEach(e=>e.classList.toggle('on',step>=+e.dataset.s));
    sc.querySelectorAll('[data-a]').forEach(e=>{
      e.classList.toggle('hot',e.dataset.a.split(' ').map(Number).includes(step));
    });
    sc.querySelectorAll('path.flow').forEach(p=>p.classList.toggle('hot',(+p.dataset.s)===step));
    sc.querySelectorAll('.caps li').forEach((li,i)=>li.classList.toggle('on',i===step));
    $('#pos').textContent=step+' / '+steps();
    const bar=$('.bar i'); if(bar) bar.style.width=(steps()?step/steps()*100:0)+'%';
    if(spawn) sc.querySelectorAll('path.flow[data-s="'+step+'"]').forEach(travel);
  }
  function travel(path){
    const svg=path.ownerSVGElement, len=path.getTotalLength();
    const c=document.createElementNS(SVGNS,'circle');c.setAttribute('r',6);c.setAttribute('class','dot');svg.appendChild(c);
    const t0=performance.now(), dur=1100;
    (function f(t){const k=Math.min(1,(t-t0)/dur), pt=path.getPointAtLength(len*k);
      c.setAttribute('cx',pt.x);c.setAttribute('cy',pt.y);
      if(k<1)requestAnimationFrame(f);else setTimeout(()=>c.remove(),150);})(t0);
  }

  /* ---------- playback ---------- */
  function present(i){
    step=i; render(true); stopSpeech();
    const after=()=>{ if(!playing) return;
      if(step>=steps()){ msg(''); finish(); return; }
      tmr=setTimeout(()=>{ if(playing) present(step+1) }, 400); };
    if(narrateOn()) speakClip(si,i,after,3500);
    else { const my=++token; msg(''); tmr=setTimeout(()=>{ if(my===token) after() },2800); }
  }
  function finish(){ playing=false; setBtn(); }
  function setBtn(){ $('#play').textContent = playing ? '❚❚ Pause' : (step>=steps()&&step>0 ? '↻ Replay' : '▶ Play (with audio)'); }
  function play(){ playing=true; setBtn(); present(step>=steps()?0:step); }
  function pause(){ playing=false; stopSpeech(); setBtn(); }
  function go(i){
    si=i; step=0; scenes.forEach((s,j)=>s.classList.toggle('on',j===si));
    document.querySelectorAll('.tab').forEach((b,j)=>b.classList.toggle('on',j===si));
    pause(); render(false);
  }
  $('#play').onclick=()=>playing?pause():play();
  $('#next').onclick=()=>{ playing=false; setBtn(); if(step<steps()) present(step+1); };
  $('#prev').onclick=()=>{ playing=false; setBtn(); if(step>0) present(step-1); };
  $('#reset').onclick=()=>{ pause(); step=0; render(false); setBtn(); };
  const nar=$('#nar'); if(nar){
    try{ if(localStorage.getItem('anim.nar')==='0') nar.checked=false }catch(e){}
    nar.onchange=()=>{ try{localStorage.setItem('anim.nar',nar.checked?'1':'0')}catch(e){} if(!nar.checked){ stopSpeech(); msg('') } };
  }
  document.addEventListener('keydown',e=>{
    if(['SELECT','INPUT'].includes(e.target.tagName)) return;
    if(e.key==='ArrowRight'){$('#next').click()} else if(e.key==='ArrowLeft'){$('#prev').click()}
    else if(e.key===' '){e.preventDefault();$('#play').click()}
  });
  window.addEventListener('beforeunload',()=>stopSpeech());

  /* deep link / testing: #s=<scene>&t=<step>  (no speech) */
  const hp=new URLSearchParams(location.hash.slice(1));
  go(Math.min(scenes.length-1,+(hp.get('s')||0)));
  if(hp.has('t')){ step=Math.min(steps(),+hp.get('t')); render(false); }
  setBtn();
})();
