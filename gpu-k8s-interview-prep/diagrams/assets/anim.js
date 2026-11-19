/* Tiny step engine. Scenes = <section class="scene" data-title="...">.
   [data-s="k"]  -> visible once step >= k
   [data-a="k j"]-> gets class "hot" while step is k or j
   path.flow[data-s="k"] -> a dot travels along it when step k is reached
   <ol class="caps"><li>intro</li><li>step 1</li>...</ol>  (li[0] is step 0) */
(function(){
  const scenes=[...document.querySelectorAll('.scene')];
  const tabsEl=document.querySelector('.tabs');
  let si=0, step=0, timer=null, playing=false;
  const SVGNS='http://www.w3.org/2000/svg';
  const $=s=>document.querySelector(s);
  scenes.forEach((sc,i)=>{
    if(tabsEl && scenes.length>1){
      const b=document.createElement('button');b.className='tab';b.textContent=sc.dataset.title||('Scene '+(i+1));
      b.onclick=()=>{go(i)};tabsEl.appendChild(b);
    }
  });
  if(tabsEl && scenes.length<=1) tabsEl.remove();
  function cur(){return scenes[si]}
  function steps(){return cur().querySelectorAll('.caps li').length-1}
  function render(spawn){
    const sc=cur();
    sc.querySelectorAll('[data-s]').forEach(e=>{
      const k=+e.dataset.s; e.classList.toggle('on',step>=k);
    });
    sc.querySelectorAll('[data-a]').forEach(e=>{
      const list=e.dataset.a.split(' ').map(Number); e.classList.toggle('hot',list.includes(step));
    });
    sc.querySelectorAll('path.flow').forEach(p=>p.classList.toggle('hot',(+p.dataset.s)===step));
    sc.querySelectorAll('.caps li').forEach((li,i)=>li.classList.toggle('on',i===step));
    $('#pos').textContent=(step)+' / '+steps();
    const bar=$('.bar i'); if(bar) bar.style.width=(steps()?step/steps()*100:0)+'%';
    if(spawn) sc.querySelectorAll('path.flow[data-s="'+step+'"]').forEach(travel);
  }
  function travel(path){
    const svg=path.ownerSVGElement, len=path.getTotalLength();
    const c=document.createElementNS(SVGNS,'circle');c.setAttribute('r',6);c.setAttribute('class','dot');
    svg.appendChild(c);
    const t0=performance.now(), dur=1100;
    (function f(t){
      const k=Math.min(1,(t-t0)/dur), pt=path.getPointAtLength(len*k);
      c.setAttribute('cx',pt.x);c.setAttribute('cy',pt.y);
      if(k<1)requestAnimationFrame(f);else setTimeout(()=>c.remove(),150);
    })(t0);
  }
  function go(i){
    si=i;step=0;scenes.forEach((s,j)=>s.classList.toggle('on',j===si));
    document.querySelectorAll('.tab').forEach((b,j)=>b.classList.toggle('on',j===si));
    pause();render(false);
  }
  function next(){ if(step<steps()){step++;render(true)} else {pause()} }
  function prev(){ if(step>0){step--;render(false)} }
  function play(){
    if(step>=steps()){step=0;render(false)}
    playing=true;$('#play').textContent='❚❚ Pause';
    timer=setInterval(()=>{ if(step>=steps()){pause();return} next() },2600);
  }
  function pause(){playing=false;clearInterval(timer);const b=$('#play');if(b)b.textContent='▶ Play'}
  $('#play').onclick=()=>playing?pause():play();
  $('#next').onclick=()=>{pause();next()};
  $('#prev').onclick=()=>{pause();prev()};
  $('#reset').onclick=()=>{pause();step=0;render(false)};
  document.addEventListener('keydown',e=>{
    if(e.key==='ArrowRight'){pause();next()} else if(e.key==='ArrowLeft'){pause();prev()} else if(e.key===' '){e.preventDefault();playing?pause():play()}
  });
  // deep link / testing: #s=<scene index>&t=<step>  (no autoplay)
  const hp=new URLSearchParams(location.hash.slice(1));
  if(hp.has('s')||hp.has('t')){
    go(Math.min(scenes.length-1,+(hp.get('s')||0)));
    step=Math.min(steps(),+(hp.get('t')||0));render(false);
  } else {
    go(0);
    setTimeout(play,700);   // autoplay once on load
  }
})();
