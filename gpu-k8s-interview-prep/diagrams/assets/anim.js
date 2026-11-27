/* Step engine + spoken narration (Web Speech API, no audio files).
   Scenes = <section class="scene" data-title="...">.
   [data-s="k"] visible from step k;  [data-a="k j"] highlighted at step k/j;
   path.flow[data-s="k"] dot travels when step k is reached.
   Narration of step i = (step 0 only: "why this matters" card) + caption + analogy. */
(function(){
  const scenes=[...document.querySelectorAll('.scene')];
  const tabsEl=document.querySelector('.tabs');
  const synth=window.speechSynthesis;
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

  /* ---------- narration ---------- */
  const SPELL={NCCL:'N C C L',EFA:'E F A',DCGM:'D C G M',CDI:'C D I',GFD:'G F D',NFD:'N F D',OOM:'out of memory',
    DLQ:'D L Q',JWT:'J W T',SPA:'S P A',TCP:'T C P',RDMA:'R D M A',SSE:'S S E',vLLM:'v L L M',MIG:'mig',MPS:'M P S',
    API:'A P I',APIs:'A P Is',CPU:'C P U',DB:'D B',SLO:'S L O',SLOs:'S L Os',IAM:'I A M',CVEs:'C V Es',KEDA:'keda',
    HPA:'H P A',DRA:'D R A',NIC:'N I C',AZ:'A Z',CLI:'C L I',SM:'S M',SMs:'S Ms',GPUs:'G P Us',GPU:'G P U'};
  function clean(t){
    t=t.replace(/nvidia\.com\/gpu/g,'nvidia dot com slash gpu')
       .replace(/→/g,' to ').replace(/≥/g,' at least ').replace(/≈/g,' about ').replace(/×/g,' times ')
       .replace(/[·…✓🛺]/g,', ').replace(/&/g,' and ').replace(/%/g,' percent').replace(/\//g,' slash ')
       .replace(/\b(NCCL|EFA|DCGM|CDI|GFD|NFD|OOM|DLQ|JWT|SPA|TCP|RDMA|SSE|vLLM|MIG|MPS|APIs|API|CPU|DB|SLOs|SLO|IAM|CVEs|KEDA|HPA|DRA|NIC|AZ|CLI|SMs|SM|GPUs|GPU)\b/g,m=>SPELL[m]||m)
       .replace(/\s+/g,' ').trim();
    return t;
  }
  function parts(i){
    const sc=cur(), li=sc.querySelectorAll('.caps li')[i], out=[];
    if(i===0){const w=sc.querySelector('.why .wt'); if(w) out.push('Why this matters. '+w.textContent);}
    const c=li.cloneNode(true), an=c.querySelector('.an'); let analogy='';
    if(an){analogy=an.textContent; an.remove();}
    out.push(c.textContent);
    if(analogy) out.push('Think of it like this. '+analogy.replace('🛺',''));
    return out.map(clean).filter(Boolean);
  }
  let voices=[];
  function loadVoices(){
    if(!synth) return; voices=synth.getVoices().filter(v=>/^en/i.test(v.lang));
    const sel=$('#voice'); if(!sel) return; const keep=sel.value; sel.innerHTML='';
    voices.forEach((v,i)=>{const o=document.createElement('option');o.value=i;o.textContent=v.name+' ('+v.lang+')';sel.appendChild(o)});
    let pref=voices.findIndex(v=>/en[-_]IN/i.test(v.lang));
    if(pref<0)pref=voices.findIndex(v=>/en[-_](SG|GB)/i.test(v.lang));
    let saved=null;try{saved=localStorage.getItem('anim.voice')}catch(e){}
    const sv=voices.findIndex(v=>v.name===saved);
    sel.value= keep? keep : String(sv>=0?sv:(pref>=0?pref:0));
  }
  if(synth){loadVoices(); synth.onvoiceschanged=loadVoices;}
  const narrateOn=()=>!!synth && $('#nar') && $('#nar').checked;
  function stopSpeech(){token++; clearTimeout(tmr); if(synth) synth.cancel();}
  function speakSeq(arr,done){
    const my=++token; let k=0;
    (function next(){
      if(my!==token) return;
      if(k>=arr.length){done&&done();return;}
      const u=new SpeechSynthesisUtterance(arr[k++]);
      const v=voices[+($('#voice')||{}).value]; if(v){u.voice=v;u.lang=v.lang}
      const rate=+($('#spd')||{value:1}).value; u.rate=rate;
      let fin=false;const f=()=>{if(fin||my!==token)return;fin=true;clearTimeout(fb);setTimeout(next,250)};
      u.onend=f; u.onerror=f;
      const fb=setTimeout(f, Math.max(2500, u.text.length*85/rate+1500));   // safety net if onend never fires
      synth.speak(u);
    })();
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
      if(step>=steps()){ finish(); return; }
      tmr=setTimeout(()=>{ if(playing) present(step+1) }, 500); };
    if(narrateOn()) speakSeq(parts(i),after);
    else { const my=++token; tmr=setTimeout(()=>{ if(my===token) after() },2800); }
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
    nar.onchange=()=>{ try{localStorage.setItem('anim.nar',nar.checked?'1':'0')}catch(e){} if(!nar.checked) stopSpeech(); };
    if(!synth){ nar.checked=false; nar.disabled=true; nar.parentElement.title='Speech not supported in this browser'; }
  }
  const vs=$('#voice'); if(vs) vs.onchange=()=>{ try{localStorage.setItem('anim.voice',voices[+vs.value].name)}catch(e){} };
  document.addEventListener('keydown',e=>{
    if(['SELECT','INPUT'].includes(e.target.tagName)) return;
    if(e.key==='ArrowRight'){$('#next').click()} else if(e.key==='ArrowLeft'){$('#prev').click()}
    else if(e.key===' '){e.preventDefault();$('#play').click()}
  });
  window.addEventListener('beforeunload',()=>{ if(synth) synth.cancel() });

  /* deep link / testing: #s=<scene>&t=<step>  (no speech) */
  const hp=new URLSearchParams(location.hash.slice(1));
  go(Math.min(scenes.length-1,+(hp.get('s')||0)));
  if(hp.has('t')){ step=Math.min(steps(),+hp.get('t')); render(false); }
  setBtn();
})();
