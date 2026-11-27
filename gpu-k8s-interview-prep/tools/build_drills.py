#!/usr/bin/env python3
"""Build diagrams/drills.html (spoken mock interview) from docs/06.
Usage: python3 tools/build_drills.py            # page only
       python3 tools/build_drills.py MODEL VOICES  # page + question MP3s (Kokoro, voice bm_george)
"""
import json, re, sys, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
doc = (ROOT / 'docs/06-leadership-management-questions.md').read_text().splitlines()
CATS = [(1, 4, 'Opening'), (5, 14, 'Leading leads'), (15, 20, 'People'), (21, 26, 'Delivery'), (27, 30, 'Stakeholders'), (31, 34, 'Strategy')]
def cat(n):
    return next(c for a, b, c in CATS if a <= n <= b)
strip = lambda t: t.replace('**', '').replace('*', '').strip()
items = []
i = 0
while i < len(doc):
    m = re.match(r'^\*\*(\d+)\. (.*?)\*\* \*\(testing: (.*?)\)\*', doc[i])
    if m:
        n = int(m.group(1)); body = []
        i += 1
        while i < len(doc) and doc[i].strip():
            body.append(strip(doc[i])); i += 1
        items.append(dict(id=f'q{n}', cat=cat(n), q=strip(m.group(2)), testing=m.group(3), ans=body))
        continue
    i += 1
start = next(k for k, l in enumerate(doc) if l.startswith('## H.'))
for l in doc[start:]:
    m = re.match(r'^(\d)\. (.*)', l)
    if m:
        items.append(dict(id=f's{m.group(1)}', cat='Scenario', q=strip(m.group(2)), testing='C-P-A-C-L: clarify, prioritise, act, communicate, learn',
                          ans=['Frame: clarify one or two facts, put people and risk first, act in three steps, say who hears what and when, then say how you prevent a repeat.'], scenario=True))
print(len(items), 'drills')

if len(sys.argv) > 2:
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(sys.argv[1], sys.argv[2])
    for it in items:
        out = ROOT / f'diagrams/audio/drill-{it["id"]}.mp3'
        if out.exists(): continue
        text = ('Scenario. ' if it.get('scenario') else '') + it['q']
        text = text.replace('a.m.', 'A M').replace('/', ' slash ').replace('GPU', 'G P U').replace('AI', 'A I').replace('CEO', 'C E O').replace('VP', 'V P')
        s, sr = k.create(text, voice='bm_george', speed=0.95, lang='en-gb')
        with tempfile.NamedTemporaryFile(suffix='.wav') as tf:
            sf.write(tf.name, s, sr)
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', tf.name, '-ac', '1', '-b:a', '64k', str(out)], check=True)
        print('made', out.name, flush=True)

cats = ['All'] + [c for _, _, c in CATS] + ['Scenario']
html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mock interview: leadership</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono&display=swap" rel="stylesheet">
<style>
body{font-family:Roboto,sans-serif;background:#fff;color:#1B2A4A;max-width:820px;margin:0 auto;padding:20px}
a{color:#1A5CBF;text-decoration:none;font-size:14px}h1{margin:8px 0 4px}p.sub{color:#5a6477;margin:0 0 14px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}.chip{border:1px solid #c9d0dc;border-radius:20px;padding:6px 14px;background:#fff;cursor:pointer;font:inherit;font-size:14px}
.chip.on{background:#1B2A4A;color:#fff;border-color:#1B2A4A}
.card{border:1px solid #d5dbe6;border-radius:12px;padding:20px;background:#F7F8FB}
.cat{font-size:12px;color:#1A5CBF;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.q{font-size:22px;font-weight:500;margin:8px 0 16px;line-height:1.35}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
button.b{border:1px solid #1A5CBF;background:#1A5CBF;color:#fff;border-radius:8px;padding:10px 16px;font:inherit;font-size:15px;cursor:pointer}
button.b.alt{background:#fff;color:#1A5CBF}
.timer{font-family:'Roboto Mono',monospace;font-size:26px;margin-left:auto}.timer.low{color:#B42318}
.ans{display:none;margin-top:16px;border-left:4px solid #0E6E48;background:#E3F3EC;padding:12px 16px;border-radius:6px;font-size:15px;line-height:1.5}
.ans p{margin:6px 0}.cnt{color:#5a6477;font-size:13px;margin-top:12px}
</style></head><body>
<a href="index.html">&larr; All diagrams</a>
<h1>Mock interview: leadership</h1>
<p class="sub">Hear the question, answer out loud for two minutes, then check the answer shape.</p>
<div class="chips" id="chips"></div>
<div class="card"><div class="cat" id="cat"></div><div class="q" id="q"></div>
<div class="row"><button class="b" id="ask">&#9654; Ask me</button><button class="b alt" id="start">Start 2:00 timer</button><button class="b alt" id="show">Show answer frame</button><button class="b alt" id="next">Next random</button><span class="timer" id="t">2:00</span></div>
<div class="ans" id="ans"></div><div class="cnt" id="cnt"></div></div>
<script>
const ITEMS=__DATA__, CATS=__CATS__;
let pool=ITEMS, cur=null, tm=null, left=120; const $=id=>document.getElementById(id), audio=new Audio();
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function stop(){clearInterval(tm);tm=null;left=120;$('t').textContent='2:00';$('t').className='timer'}
function show(it){cur=it;stop();audio.pause();$('cat').textContent=it.cat;$('q').textContent=it.q;$('ans').style.display='none';
 $('ans').innerHTML='<b>Testing:</b> '+esc(it.testing)+it.ans.map(a=>'<p>'+esc(a)+'</p>').join('');$('cnt').textContent=pool.length+' in this set'}
function next(){let it;do{it=pool[Math.floor(Math.random()*pool.length)]}while(pool.length>1&&it===cur);show(it);ask()}
function ask(){audio.src='audio/drill-'+cur.id+'.mp3';audio.play().catch(()=>{})}
$('ask').onclick=ask;$('next').onclick=next;$('show').onclick=()=>{$('ans').style.display='block'};
$('start').onclick=()=>{if(tm){stop();return}tm=setInterval(()=>{left--;const m=Math.floor(left/60),s=left%60;$('t').textContent=m+':'+String(s).padStart(2,'0');if(left<=20)$('t').className='timer low';if(left<=0){stop();$('t').textContent='Time'}},1000)};
CATS.forEach((c,i)=>{const b=document.createElement('button');b.className='chip'+(i?'':' on');b.textContent=c;b.onclick=()=>{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));b.classList.add('on');pool=c=='All'?ITEMS:ITEMS.filter(x=>x.cat==c);show(pool[Math.floor(Math.random()*pool.length)])};$('chips').appendChild(b)});
show(ITEMS[0]);
</script></body></html>'''
html = html.replace('__DATA__', json.dumps(items)).replace('__CATS__', json.dumps(cats))
(ROOT / 'diagrams/drills.html').write_text(html)
print('wrote drills.html')
