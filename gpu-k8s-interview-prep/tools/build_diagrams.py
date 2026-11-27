#!/usr/bin/env python3
"""Generates the animated HTML diagrams in ../diagrams.

Run:  python3 tools/build_diagrams.py
Each page = shared assets/anim.css + assets/anim.js + inline SVG scenes.
Step engine rules (see assets/anim.js):
  data-s="k"  element appears at step >= k
  data-a="k"  element is highlighted at step k
  path.flow[data-s=k]  a dot travels along the path when step k is reached
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "diagrams"

DEFS = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
        '<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker></defs></svg>')



WHY = {
 'Pod → GPU': "What are we trying to understand? When you write one line in a YAML file asking for a GPU, what really happens behind the scenes? Kubernetes does not know what a GPU is. It only counts a number. So several small components cooperate: one announces the GPUs, one picks the machine, and one hands over the key. This is the most common question on any GPU platform interview. If you can walk through it calmly, it shows you understand the whole stack, not just one tool.",
 'Exclusive': "Why does this matter? Exclusive is the default mode, and it is simple and safe, but expensive. A GPU costs a lot of money, and if one job uses only a fifth of it, the rest sits idle. Interviewers love asking how you would raise GPU utilisation, and this is the starting point of that answer. First understand what is wasted, then look at the sharing options.",
 'Time-slicing': "Why does this matter? Time-slicing is the cheapest way to share a GPU, so teams reach for it first. But it has a hidden danger: there is no wall between the jobs. In an interview, the right answer is not 'it shares the GPU', the right answer is: good for dev and notebooks, never for tenants who do not trust each other.",
 'MIG': "Why does this matter? When you run a platform for external customers, you must promise that one customer cannot slow down or crash another. MIG gives hardware walls inside one GPU, so it is the answer for strong isolation. Be ready to also explain the cost: the slices are fixed, so some capacity can be stranded.",
 'MPS': "Why does this matter? MPS is the middle path: jobs really run at the same time, so throughput is better than time-slicing, but the isolation is weaker than MIG. Knowing all four options, and when to use each, is what separates a platform owner from someone who only used GPUs.",
 'Operator stack': "What are we trying to do here? A GPU node needs many things installed in the right order: driver, toolkit, plugin, labels, monitoring. Doing that by hand on hundreds of nodes, after every kernel upgrade, is a nightmare. The GPU Operator automates it. In an interview this shows you think about operating at scale, not just installing once.",
 'Without gang': "Why does this matter? Training jobs are not like web servers. All the workers must run together, or none can make progress. If the scheduler places only some of them, they hold expensive GPUs and wait forever. This is a classic way platforms waste money, and a very common interview scenario.",
 'With Kueue (gang)': "The fix is all or nothing admission. Kueue keeps the job in a queue until every worker can start together, and it also gives each team a fair share of GPUs. For a director level interview, this is your fairness and utilisation story: how many teams share a scarce fleet without fighting.",
 'All-reduce': "Why does this matter? In multi-node training, the network is as important as the GPUs. If the fast fabric is misconfigured, the job silently falls back to slow networking, and you pay for GPUs that wait. When you can explain this simply, you show you understand why GPU platforms are really network and scheduling problems.",
 'Request': "What are we trying to do? Follow one request through a Spring Boot service, step by step, so you can explain where security, validation, limits and timeouts belong. At the end the call goes to a GPU model server, which is slow and expensive, so the service must protect it. Interviewers use this to check whether you can review a design, not just write code.",
 'Startup': "Why does this matter? Many Spring Boot problems come from not knowing what the framework does at startup. Knowing the sequence, and that your own bean always wins over the default, lets you debug surprises quickly and review other people's code with confidence.",
 'Gateway to GPU': "What are we trying to do? Put a protective front desk in front of the expensive GPU kitchen. It limits how many orders go in, says come back later when it is full, and the platform adds more kitchens when the queue grows. This single picture answers many questions: resilience, autoscaling, cost, and how Spring Boot, Kubernetes and GPUs fit together.",
 'Platform layers': "What are we trying to do? This is the picture to draw on the whiteboard when they say, describe the platform you would lead. Each layer has an owner, a service level, and a failure mode. As a director, your value is in how these layers, and the teams behind them, work together, along with security, operations and cost.",
 'Kafka': "Why does this matter? The role mentions Kafka for event driven integration. Interviewers want to hear that you understand ordering, duplicates, lag and failure handling, not just that Kafka is a message queue. Explain these four ideas simply, and you will sound like someone who has run it in production.",
}

import re, json, html as _html
_PENDING = []   # scenes of the page being built
NARR = {}       # page slug -> scenes -> step texts (written to diagrams/audio/narration.json)


def _plain(t):
    return _html.unescape(re.sub(r'<[^>]+>', '', t)).strip()


# ---------- helpers ----------
def _attrs(s=None, a=None):
    return (f' data-s="{s}"' if s is not None else ''), (f' data-a="{a}"' if a is not None else '')


def box(x, y, w, h, cls, title, sub=None, s=None, a=None, tcls=''):
    ds, da = _attrs(s, a)
    fs = max(10, min(14, (w - 12) / (0.6 * max(1, len(title)))))
    cx = x + w / 2
    ty = y + h / 2 + (-3 if sub else 5)
    out = f'<g{ds}><rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"{da}/>'
    out += f'<text x="{cx}" y="{ty}" text-anchor="middle" class="h {tcls}" style="font-size:{fs:.1f}px">{title}</text>'
    if sub:
        sfs = max(8.5, min(11.5, (w - 10) / (0.62 * len(sub))))
        out += (f'<text x="{cx}" y="{ty + 17}" text-anchor="middle" class="m {tcls if tcls else "sm"}" '
                f'style="font-size:{sfs:.1f}px;{"" if tcls else "fill:#5A6782"}">{sub}</text>')
    return out + '</g>'


def frame(x, y, w, h, label, s=None):
    ds, _ = _attrs(s)
    return (f'<g{ds}><rect class="frame" x="{x}" y="{y}" width="{w}" height="{h}"/>'
            f'<text x="{x + 14}" y="{y + 22}" class="t" style="font-weight:700;fill:#5A6782">{label}</text></g>')


def flow(d, s, cls=''):
    return f'<path class="flow {cls}" data-s="{s}" d="{d}"/>'


def label(x, y, text, cls='sm', anchor='middle', s=None, color=None):
    ds, _ = _attrs(s)
    st = f' style="fill:{color};font-weight:700"' if color else ''
    return f'<text{ds} x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}"{st}>{text}</text>'


def scene(title, h, body, caps):
    lis = ''.join(
        f'<li>{c[0]}' + (f'<span class="an">🛺 {c[1]}</span>' if len(c) > 1 and c[1] else '') + '</li>' for c in caps)
    w = WHY.get(title, '')
    texts = []
    for i, c in enumerate(caps):
        parts = []
        if i == 0 and w:
            parts.append('Why this matters. ' + w)
        parts.append(_plain(c[0]))
        if len(c) > 1 and c[1]:
            parts.append('Think of it like this. ' + c[1])
        texts.append(parts)
    _PENDING.append(texts)
    whyhtml = (f'<div class="why"><b class="wl">Why this matters</b><span class="wt">{w}</span></div>' if w else '')
    return (f'<section class="scene" data-title="{title}">{whyhtml}<div class="stage">'
            f'<svg viewBox="0 0 960 {h}" role="img" aria-label="{title}">{body}</svg></div>'
            f'<ol class="caps">{lis}</ol></section>')


def page(fname, title, sub, no, is_, scenes):
    slug = fname[:-5]
    NARR[slug] = list(_PENDING)
    _PENDING.clear()
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="assets/anim.css">
</head><body data-page="{slug}"><div class="wrap">
<div class="nav"><a href="index.html">← All diagrams</a></div>
<h1>{title}</h1><p class="sub">{sub}</p>
<p class="fence"><b class="no">NOT:</b> {no}<br><b class="is">IS:</b> {is_}</p>
{DEFS}
<div class="tabs"></div>
{''.join(scenes)}
<div class="opts"><label><input type="checkbox" id="nar" checked> 🔊 Narration</label>
<label>Speed <select id="spd"><option value="0.85">Slow</option><option value="0.95" selected>Normal</option><option value="1.1">Fast</option></select></label>
</div>
<p class="hintline" id="amsg" style="color:#B85C00;min-height:1.2em"></p>
<p class="hintline">Press <b>Play (with audio)</b> for a narrated walkthrough. Audio is a recorded voice and plays in any browser after a click.</p>
<div class="ctrl"><button class="btn" id="prev">◀ Prev</button><button class="btn pri" id="play">▶ Play (with audio)</button>
<button class="btn" id="next">Next ▶</button><button class="btn" id="reset">↺ Reset</button><span id="pos"></span></div>
<div class="bar"><i></i></div>
<p class="sub" style="margin-top:14px">Keys: ← → step (speaks that step) · Space play/pause.</p>
</div><script src="assets/anim.js"></script></body></html>'''
    (OUT / fname).write_text(html, encoding='utf-8')
    print('wrote', fname)


# ======================================================================
# 01  GPU scheduling flow
# ======================================================================
def d01():
    b = ''
    b += frame(420, 30, 520, 430, 'GPU node (e.g. g6e / p5)')
    b += box(20, 200, 130, 56, 'n', 'kubectl apply', 'gpu: 1', a=2)
    b += box(210, 200, 130, 56, 'b', 'API Server', 'etcd', a='1 2 4')
    b += box(210, 70, 130, 56, 'p', 'Scheduler', 'filter·score·bind', a=3)
    b += box(450, 70, 150, 56, 'b', 'kubelet', 'allocatable gpu=4', a='1 5')
    b += box(700, 70, 210, 56, 'g', 'Device Plugin', 'DaemonSet · gRPC', a='1 5')
    b += box(450, 180, 200, 60, 'n', 'containerd + toolkit', 'CDI / runtime hook', a=6)
    b += box(710, 180, 200, 60, 'a', 'Host driver + NVML', 'nvidia.ko · libcuda', a=6)
    b += box(450, 290, 200, 70, 'g', 'Your Pod', 'limits: nvidia.com/gpu: 1', s=4, a=7)
    b += box(450, 390, 85, 46, 'a', 'GPU 0', 'busy')
    b += box(545, 390, 85, 46, 'a', 'GPU 1', 'busy')
    b += box(640, 390, 85, 46, 'b', 'GPU 2', 'free', a='5 7')
    b += box(735, 390, 85, 46, 'b', 'GPU 3', 'free')
    b += label(650, 60, 'Register + ListAndWatch', s=1)
    b += label(650, 140, 'Allocate() → GPU 2', s=5, color='#0E6E48')
    b += label(700, 270, 'nvidia-smi sees only GPU 2', s=7, color='#0E6E48', anchor='start')
    b += flow('M700,98 L600,98', 1, 'g')
    b += flow('M450,90 L395,90 L395,222 L340,222', 1, 'b')
    b += flow('M150,228 L210,228', 2)
    b += flow('M250,200 L250,126', 3, 'p')
    b += flow('M300,126 L300,200', 4, 'p')
    b += flow('M340,244 L408,244 L408,112 L450,112', 4, 'b')
    b += flow('M600,84 L700,84', 5, 'g')
    b += flow('M700,112 L600,112', 5, 'g')
    b += flow('M525,126 L525,180', 6, 'b')
    b += flow('M650,210 L710,210', 6, 'a')
    b += flow('M550,240 L550,290', 7, 'g')
    b += flow('M620,360 L620,375 L682,375 L682,390', 7, 'g')
    caps = [
        ('A Pod asks for a GPU by <b>count</b>. Follow it from YAML to silicon.',
         'Booking "1 taxi", not "taxi number 7".'),
        ('<b>Node boot:</b> the device plugin registers <code>nvidia.com/gpu</code> with kubelet and streams 4 healthy GPUs (ListAndWatch). kubelet reports capacity to the API server.',
         'Dispatcher tells the control room: "4 taxis at this depot".'),
        ('You submit a Pod with <code>limits: nvidia.com/gpu: 1</code>.', 'Passenger asks for one taxi.'),
        ('<b>Scheduler filter:</b> NodeResourcesFit needs allocatable GPU ≥ 1. Taints, nodeSelector and quota are checked too.',
         'Control room looks for a depot with a free taxi.'),
        ('<b>Bind:</b> the Pod is assigned to this node and kubelet receives it.', ''),
        ('kubelet calls <b>Allocate()</b>. The plugin picks GPU 2 and returns its UUID (or a CDI device name).',
         'Dispatcher hands over the key of one specific taxi.'),
        ('kubelet asks containerd to start the container. The <b>NVIDIA toolkit</b> mounts <code>/dev/nvidia2</code>, <code>/dev/nvidiactl</code> and the host driver libraries.', ''),
        ('Container runs. <code>nvidia-smi</code> shows only GPU 2; CUDA calls go to the <b>host</b> driver. Driver on host, CUDA toolkit in the image.',
         'Passenger sees only their taxi, not the whole depot.'),
    ]
    page('01-gpu-scheduling-flow.html', 'From Pod YAML to GPU',
         'Device plugin → kubelet → scheduler → runtime → driver',
         'Kubernetes does not understand GPUs. The scheduler just counts an opaque integer.',
         'A device plugin advertises <code>nvidia.com/gpu</code>; the toolkit exposes the chosen device; the host driver does the work.',
         [scene('Pod → GPU', 470, b, caps)])


# ======================================================================
# 02  GPU sharing
# ======================================================================
def gpu_frame(x=330, y=50, w=300, h=230, title='GPU · 80 GB'):
    return frame(x, y, w, h, title)


def d02():
    scenes = []
    # --- Exclusive
    b = gpu_frame()
    b += box(30, 70, 200, 50, 'g', 'Pod A', 'gpu: 1', a=1)
    b += box(30, 140, 200, 50, 'r', 'Pod B', 'gpu: 1', s=2)
    b += box(30, 210, 200, 50, 'r', 'Pod C', 'gpu: 1', s=2)
    b += box(350, 90, 260, 170, 'g', 'Pod A owns the whole GPU', '100 % of memory + SMs', s=1)
    b += box(350, 215, 260, 30, 'a', 'actually used ≈ 20 %', None, s=3)
    b += label(280, 170, 'Pending', s=2, color='#B81A1A')
    b += label(280, 240, 'Pending', s=2, color='#B81A1A')
    b += flow('M230,95 L350,150', 1, 'g')
    caps = [('Default mode: <b>one GPU = one Pod</b>. Whole bungalow, one family.',),
            ('Pod A gets the full GPU. Safe, full isolation, best for training and big models.',),
            ('Pods B and C stay <b>Pending</b> (<code>Insufficient nvidia.com/gpu</code>): extended resources are integers and never overcommitted.',),
            ('If A only uses ~20 %, the rest is wasted. That is why sharing exists.',)]
    scenes.append(scene('Exclusive', 310, b, caps))

    # --- Time slicing
    b = gpu_frame()
    b += box(30, 70, 200, 46, 'b', 'Pod A', 'replica 1', s=2, a=3)
    b += box(30, 130, 200, 46, 'p', 'Pod B', 'replica 2', s=2, a=4)
    b += box(30, 190, 200, 46, 'g', 'Pod C', 'replica 3', s=2, a=5)
    b += box(350, 90, 260, 40, 'n', 'Advertised: nvidia.com/gpu: 4', 'for 1 physical GPU', s=1)
    b += '<rect class="b" x="350" y="150" width="80" height="34" data-a="3" data-s="3"/>'
    b += '<rect class="p" x="435" y="150" width="80" height="34" data-a="4" data-s="3"/>'
    b += '<rect class="g" x="520" y="150" width="80" height="34" data-a="5" data-s="3"/>'
    b += label(390, 172, 'A', 't', s=3) + label(475, 172, 'B', 't', s=3) + label(560, 172, 'C', 't', s=3)
    b += label(480, 205, 'GPU time: A → B → C → A …', 'sm', s=3)
    b += box(350, 222, 250, 36, 'r', 'C allocates too much → OOM hits A and B', None, s=6)
    b += flow('M230,93 L346,156', 3, 'b')
    b += flow('M230,153 L346,167', 4, 'p')
    b += flow('M230,213 L346,178', 5, 'g')
    caps = [('<b>Time-slicing</b>: the GPU is shared by turns.',
             'One auto-rickshaw, passengers take turns.'),
            ('Config says replicas: 4, so the plugin advertises 4 "GPUs" for 1 physical device.',),
            ('Three Pods each get a replica. Replicas are scheduling slots, not extra capacity.',),
            ('The GPU runs <b>Pod A</b> for a slice…',),
            ('…then <b>Pod B</b>…',),
            ('…then <b>Pod C</b>. Context-switch overhead each time.',),
            ('<b>No memory or fault isolation.</b> One greedy Pod can hurt the others. Use for dev, notebooks, light inference, never for untrusted tenants.',)]
    scenes.append(scene('Time-slicing', 310, b, caps))

    # --- MIG
    b = gpu_frame(title='A100/H100 80 GB (illustrative layout)')
    b += box(30, 90, 200, 44, 'n', 'node label', 'mig.config=all-balanced', s=1)
    b += box(30, 160, 200, 44, 'p', 'MIG Manager', 'drains + reconfigures', s=2, a=2)
    b += box(30, 230, 200, 44, 'g', 'Device Plugin', 'advertises mig-* resources', s=3, a=3)
    b += box(345, 90, 130, 180, 'b', '3g.40gb', 'Pod A', s=2, a=4)
    b += box(480, 90, 70, 85, 'b', '2g', '20gb', s=2, a=4)
    b += box(480, 185, 70, 85, 'b', '1g', '10gb', s=2, a=4)
    b += box(555, 90, 65, 85, 'b', '1g', '10gb', s=2, a=4)
    b += box(555, 185, 65, 85, 'r', '1g', 'OOM', s=5)
    b += label(480, 292, 'own memory · own cache · own SMs', 'sm', s=2)
    b += flow('M230,182 L345,182', 2, 'p')
    b += flow('M230,252 L300,252 L300,140 L345,140', 3, 'g')
    caps = [('<b>MIG</b> cuts one GPU into hardware-isolated instances (A100/A30/H100/H200/B200 families).',
             'Separate flats in one building: own walls, own meter.'),
            ('Ask for a layout by labelling the node. The GPU must be idle.',),
            ('<b>MIG Manager</b> carves the GPU. Each slice gets dedicated memory, cache and SMs.',),
            ('The device plugin advertises per-profile resources such as <code>nvidia.com/mig-1g.10gb</code> (mixed strategy).',),
            ('Pods request a slice and land on it. Predictable latency, strong isolation.',),
            ('A Pod that overruns its slice OOMs <b>only inside its own slice</b>. Neighbours are untouched. Downside: static geometry, stranded capacity.',)]
    scenes.append(scene('MIG', 310, b, caps))

    # --- MPS
    b = gpu_frame(title='GPU · one shared CUDA context')
    b += box(30, 70, 200, 44, 'b', 'Process A', 'CUDA client', s=2, a=3)
    b += box(30, 130, 200, 44, 'p', 'Process B', 'CUDA client', s=2, a=3)
    b += box(30, 190, 200, 44, 'g', 'Process C', 'CUDA client', s=2, a=3)
    b += box(350, 85, 260, 40, 'n', 'MPS control daemon + server', None, s=1, a=1)
    b += '<rect class="b" x="350" y="145" width="200" height="22" data-s="3"/>'
    b += '<rect class="p" x="370" y="172" width="220" height="22" data-s="3"/>'
    b += '<rect class="g" x="390" y="199" width="180" height="22" data-s="3"/>'
    b += label(480, 242, 'kernels from A, B, C run at the same time', 'sm', s=3)
    b += box(350, 255, 260, 28, 'a', 'caps: thread % + pinned memory per client', None, s=4)
    b += flow('M230,92 L350,105', 2, 'b')
    b += flow('M230,152 L350,115', 2, 'p')
    b += flow('M230,212 L350,125', 2, 'g')
    caps = [('<b>MPS</b> lets several processes share the GPU <i>concurrently</i>.',
             'One shared kitchen: several cooks work at once.'),
            ('The MPS control daemon starts a server that owns the GPU context.',),
            ('Client processes connect to the server instead of the GPU directly.',),
            ('Kernels from different processes overlap in time: better throughput for many small kernels than time-slicing.',),
            ('Limits: active-thread percentage and pinned-memory caps per client. Isolation is weaker than MIG (a fault can affect other clients).',)]
    scenes.append(scene('MPS', 310, b, caps))

    page('02-gpu-sharing.html', 'Sharing a GPU: exclusive, time-slicing, MIG, MPS',
         'Pick the right wall between tenants',
         'Fractional GPUs do not exist in the scheduler. <code>nvidia.com/gpu: 0.5</code> is invalid.',
         'Sharing is a node-level feature (time-slicing, MPS, MIG) that changes what the device plugin advertises, or DRA claims that describe it.',
         scenes)


# ======================================================================
# 03  GPU Operator stack
# ======================================================================
def d03():
    b = frame(260, 20, 680, 440, 'GPU node')
    b += box(20, 195, 180, 70, 'p', 'GPU Operator', 'ClusterPolicy CRD', a='1 2 3 4 6')
    # rows (top to bottom)
    b += box(290, 60, 620, 44, 'b', 'NFD · Node Feature Discovery', 'labels node: PCI vendor 10de = NVIDIA', s=1, a=1)
    b += box(290, 120, 300, 44, 'n', 'DCGM Exporter', 'metrics → Prometheus', s=6, a=6)
    b += box(610, 120, 300, 44, 'p', 'MIG Manager (optional)', 'reads nvidia.com/mig.config', s=7, a=7)
    b += box(290, 180, 300, 44, 'g', 'Device Plugin', 'nvidia.com/gpu · MPS daemon', s=4, a=4)
    b += box(610, 180, 300, 44, 'g', 'GPU Feature Discovery', 'labels: product · memory · count', s=5, a=5)
    b += box(290, 240, 620, 44, 'n', 'Container Toolkit', 'containerd config + CDI spec', s=3, a=3)
    b += box(290, 300, 620, 44, 'a', 'NVIDIA driver', 'host AMI or driver container', s=2, a=2)
    b += box(290, 360, 620, 44, 'n', 'GPUs · NVLink · NIC (EFA / IB)', None)
    for yy, xx, st in ((322, 895, 3), (262, 895, 4), (202, 575, 5)):
        b += label(xx, yy + 4, '✓', 't', anchor='end', s=st, color='#0E6E48')
    b += label(290, 432, '✓ = Operator Validator gate passed (each layer waits for the one below)', 'sm', anchor='start')
    b += flow('M200,230 C245,230 245,82 290,82', 1, 'b')
    b += flow('M200,230 C245,230 245,322 290,322', 2, 'a')
    b += flow('M200,230 C245,230 245,262 290,262', 3)
    b += flow('M200,230 C245,230 245,202 290,202', 4, 'g')
    b += flow('M200,230 C245,230 245,142 290,142', 6, 'p')
    caps = [('One Helm install, one <code>ClusterPolicy</code>. The Operator then runs everything a GPU node needs.',
             'Society maintenance office: one contract covers electrician, plumber and guard for every flat.'),
            ('<b>NFD</b> detects the NVIDIA PCI device and labels the node, so GPU operands only run where GPUs exist.',),
            ('<b>Driver</b> (skip it if the AMI already ships one, e.g. EKS accelerated AMI).',),
            ('<b>Container toolkit</b> configures containerd and CDI so containers can be given device files.',),
            ('<b>Device plugin</b> registers <code>nvidia.com/gpu</code> with kubelet. The validator gates it until driver and toolkit pass.',),
            ('<b>GFD</b> publishes labels such as <code>nvidia.com/gpu.product</code> for scheduling by model.',),
            ('<b>DCGM Exporter</b> exposes utilisation, memory, power and XID errors to Prometheus.',),
            ('<b>MIG Manager</b> (optional) applies MIG layouts when you label the node. Gotcha: editing the time-slicing ConfigMap needs a device-plugin restart.',)]
    page('03-gpu-operator-stack.html', 'NVIDIA GPU Operator: what runs on a GPU node',
         'Bring-up order and what each operand does',
         'A pile of scripts you run by hand on every node after every kernel upgrade.',
         'A Kubernetes operator that deploys, orders and health-gates the whole GPU software stack declaratively.',
         [scene('Operator stack', 470, b, caps)])


# ======================================================================
# 04  Multi-node training
# ======================================================================
def slot_grid(prefix_busy=3):
    """8 GPU slots in 2 rows of 4 on the right; first `prefix_busy` are busy."""
    out = ''
    pos = []
    for i in range(8):
        x = 520 + (i % 4) * 102
        y = 90 + (i // 4) * 80
        pos.append((x, y))
        out += f'<rect class="b" x="{x}" y="{y}" width="92" height="62"/>'
        out += f'<text x="{x + 46}" y="{y + 36}" text-anchor="middle" class="t">GPU {i}</text>'
    return out, pos


def workers_col():
    out = ''
    pos = []
    for i in range(8):
        x = 30 + (i % 4) * 110
        y = 90 + (i // 4) * 80
        pos.append((x, y))
        out += f'<rect class="n" x="{x}" y="{y}" width="100" height="62"/>'
        out += f'<text x="{x + 50}" y="{y + 36}" text-anchor="middle" class="t">worker {i}</text>'
    return out, pos


def d04():
    scenes = []
    # --- no gang
    b = frame(500, 40, 440, 230, 'Cluster · 8 GPUs, 3 busy')
    b += frame(15, 40, 460, 230, 'Job: 8 workers (1 GPU each)')
    wcol, wpos = workers_col()
    sg, spos = slot_grid()
    b += wcol + sg
    for i in range(3):
        x, y = spos[i]
        b += f'<rect class="a" x="{x}" y="{y}" width="92" height="62"/><text x="{x + 46}" y="{y + 36}" text-anchor="middle" class="t">busy</text>'
    for k, i in enumerate(range(3, 8)):
        x, y = spos[i]
        b += (f'<g data-s="2"><rect class="g" x="{x}" y="{y}" width="92" height="62" data-a="2"/>'
              f'<text x="{x + 46}" y="{y + 36}" text-anchor="middle" class="t">worker {k}</text></g>')
    for i in range(5, 8):
        x, y = wpos[i]
        b += (f'<g data-s="3"><rect class="r" x="{x}" y="{y}" width="100" height="62"/>'
              f'<text x="{x + 50}" y="{y + 36}" text-anchor="middle" class="t">Pending</text></g>')
    b += box(180, 280, 600, 40, 'r', 'Deadlock: 5 GPUs held, all-reduce waits for 3 missing workers', None, s=4)
    caps = [('<b>Without gang scheduling</b> the default scheduler places Pods one by one.',
             'Wedding party: some guests are seated, the rest have no chairs.'),
            ('Cluster state: 8 GPUs, 3 busy, only 5 free. The job needs 8.',),
            ('Five workers get placed immediately and start holding GPUs.',),
            ('Three workers stay <b>Pending</b>.',),
            ('The job cannot start (collectives need every rank) yet 5 GPUs are locked. Waste and starvation for others.',)]
    scenes.append(scene('Without gang', 340, b, caps))

    # --- Kueue gang
    b = frame(500, 40, 440, 230, 'Cluster · 8 GPUs')
    b += frame(15, 40, 460, 230, 'Workload (Kueue): needs 8 GPUs')
    wcol, wpos = workers_col()
    sg, spos = slot_grid()
    b += wcol + sg
    for i in range(3):
        x, y = spos[i]
        b += f'<rect class="a" x="{x}" y="{y}" width="92" height="62"/><text x="{x + 46}" y="{y + 36}" text-anchor="middle" class="t">busy</text>'
    for i in range(3):   # cover: they become free at step 3
        x, y = spos[i]
        b += (f'<g data-s="3"><rect class="b" x="{x}" y="{y}" width="92" height="62"/>'
              f'<text x="{x + 46}" y="{y + 36}" text-anchor="middle" class="t">free</text></g>')
    for i in range(8):
        x, y = spos[i]
        b += (f'<g data-s="4"><rect class="g" x="{x}" y="{y}" width="92" height="62" data-a="4"/>'
              f'<text x="{x + 46}" y="{y + 36}" text-anchor="middle" class="t">worker {i}</text></g>')
    b += box(180, 280, 600, 40, 'n', 'Kueue: admit all 8 or none. Pods are not even created until admitted.', None, s=2)
    b += box(180, 330, 600, 40, 'g', 'Training starts with every rank present', None, s=4)
    caps = [('<b>With Kueue</b> the whole job is one Workload, admitted all-or-nothing.',
             'Book the whole wedding hall or none of it.'),
            ('Same cluster: 3 busy, 5 free. Job needs 8.',),
            ('Not enough quota or capacity → the Workload <b>stays queued</b>. No Pods hold GPUs; other teams can use the 5 free ones.',),
            ('Three busy GPUs finish and free up. Now 8 are available.',),
            ('Kueue admits the Workload; all 8 Pods start together. No partial placement, no deadlock.',)]
    scenes.append(scene('With Kueue (gang)', 390, b, caps))

    # --- all-reduce ring
    b = frame(40, 30, 330, 330, 'Node A')
    b += frame(590, 30, 330, 330, 'Node B')
    b += box(120, 90, 130, 60, 'b', 'GPU 0', None, a='1 2')
    b += box(120, 230, 130, 60, 'b', 'GPU 1', None, a='1 2')
    b += box(710, 230, 130, 60, 'b', 'GPU 2', None, a='1 3')
    b += box(710, 90, 130, 60, 'b', 'GPU 3', None, a='1 3')
    b += label(150, 200, 'NVLink', 's' if False else 'sm', s=2, color='#1A5CBF')
    b += label(780, 200, 'NVLink', 'sm', s=2, color='#1A5CBF')
    b += label(480, 250, 'EFA / InfiniBand', 'sm', s=3, color='#B85C00')
    b += label(480, 110, 'EFA / InfiniBand', 'sm', s=3, color='#B85C00')
    b += flow('M185,150 L185,230', 2, 'b')
    b += flow('M775,230 L775,150', 2, 'b')
    b += flow('M250,262 L710,262', 3, 'a')
    b += flow('M710,122 L250,122', 3, 'a')
    for (x, y) in ((120, 90), (120, 230), (710, 230), (710, 90)):
        b += label(x + 118, y + 20, '✓', 't', s=4, color='#0E6E48')
    b += box(250, 305, 460, 40, 'r', 'NCCL falls back to TCP → everything waits on the slowest link', None, s=5)
    caps = [('<b>Data-parallel training</b>: every GPU computes gradients, then NCCL averages them (all-reduce).',
             'Four friends each add a column of a bill, then pass the partial sums around until all know the total.'),
            ('Forward + backward: each GPU has its own local gradients.',),
            ('Reduce inside a node first over <b>NVLink</b> (fast, 100s of GB/s).',),
            ('Then across nodes over <b>EFA / InfiniBand</b> with GPUDirect RDMA (NIC reads GPU memory directly).',),
            ('Every GPU now holds the same averaged gradients; next step begins.',),
            ('If the fabric is misconfigured (wrong NIC, no EFA, cross-AZ) NCCL silently drops to TCP. Debug with <code>NCCL_DEBUG=INFO</code>.',)]
    scenes.append(scene('All-reduce', 390, b, caps))

    page('04-multinode-training.html', 'Multi-node training: gang scheduling and all-reduce',
         'Why jobs need all-or-nothing placement, and what the network does',
         'Training jobs are not independent Pods you can place one at a time.',
         'A tightly coupled group of ranks that must all run, on a fast fabric, or none should.',
         scenes)


# ======================================================================
# 05  Spring Boot lifecycle
# ======================================================================
def d05():
    scenes = []
    # --- request
    b = ''
    b += box(20, 70, 120, 56, 'n', 'Client', 'POST /v1/chat', a='1 8')
    b += box(170, 70, 120, 56, 'b', 'Tomcat', 'thread / vthread', a='1 2')
    b += box(320, 70, 120, 56, 'p', 'Filter chain', 'Security · logging', a=3)
    b += box(470, 70, 120, 56, 'b', 'DispatcherServlet', 'front controller', a=4)
    b += box(620, 70, 120, 56, 'p', 'Interceptors', 'HandlerMapping', a='4 5')
    b += box(770, 70, 150, 56, 'g', 'Controller', '@RestController', a=5)
    b += box(770, 250, 150, 70, 'a', 'Bulkhead + Service', 'semaphore · metrics', a=6)
    b += box(620, 250, 120, 70, 'b', 'RestClient', 'timeouts set', a=7)
    b += box(470, 250, 120, 70, 'g', 'vLLM on GPU', '/v1/chat/completions', a=7)
    b += flow('M140,98 L170,98', 1)
    b += flow('M290,98 L320,98', 3, 'p')
    b += flow('M440,98 L470,98', 4, 'p')
    b += flow('M590,98 L620,98', 4, 'b')
    b += flow('M740,98 L770,98', 5, 'g')
    b += flow('M845,126 L845,250', 6, 'a')
    b += flow('M770,285 L740,285', 7, 'b')
    b += flow('M620,285 L590,285', 7, 'g')
    b += flow('M530,320 L530,375 L80,375 L80,126', 8, 'g')
    b += label(305, 394, 'response: Jackson → JSON · slot released · timer recorded', 'sm', s=8, color='#0E6E48')
    b += label(858, 215, 'full? → 429', 'sm', s=6, color='#B81A1A', anchor='start')
    caps = [('Request lifecycle in Spring MVC, with a GPU backend at the end.',
             'Courier path: gate → security desk → reception → right department → warehouse → back.'),
            ('Client sends <code>POST /v1/chat/completions</code>.',),
            ('<b>Tomcat</b> parses HTTP and assigns a thread (a virtual thread when <code>spring.threads.virtual.enabled=true</code>).',),
            ('<b>Filter chain</b> (servlet level): Spring Security validates the JWT, logging and tracing add context.',),
            ('<b>DispatcherServlet</b> finds the handler; <b>interceptors</b> run <code>preHandle</code>.',),
            ('Controller: Jackson binds JSON to the argument; validation runs.',),
            ('<b>Bulkhead</b> takes a slot. No slot within 200 ms → <code>429 + Retry-After</code> instead of piling onto the GPU.',),
            ('<b>RestClient</b> calls the model server with explicit connect/read timeouts.',),
            ('Response flows back: message converter writes JSON, the slot is released in <code>finally</code>, latency is recorded.',)]
    scenes.append(scene('Request', 400, b, caps))

    # --- startup
    b = ''
    xs = [20, 260, 500, 740]
    items = [
        ('SpringApplication.run', 'main() entry', 'n'),
        ('Prepare Environment', 'props · profiles · env', 'b'),
        ('Create context', 'servlet vs reactive', 'b'),
        ('Scan + auto-config', 'AutoConfiguration.imports', 'p'),
        ('Evaluate conditions', '@ConditionalOnMissingBean', 'p'),
        ('Instantiate beans', 'DI · @PostConstruct', 'g'),
        ('Start Tomcat', 'port 8080 (+8081 mgmt)', 'b'),
        ('Ready', 'readiness: ACCEPTING_TRAFFIC', 'g'),
    ]
    for i, (t, sub, c) in enumerate(items):
        x = xs[i % 4]
        y = 70 if i < 4 else 250
        b += box(x, y, 190, 70, c, t, sub, s=i + 1, a=i + 1)
    for i in range(1, 8):
        if i == 4:
            b += flow('M835,140 L835,195 L115,195 L115,250', 5)
        else:
            x = xs[i % 4]
            y = 105 if i < 4 else 285
            b += flow(f'M{x - 50},{y} L{x},{y}', i + 1)
    b += label(480, 360, 'Debug any surprise with  --debug  (conditions report) or  /actuator/conditions', 'sm', s=5)
    caps = [('What happens between <code>java -jar</code> and "ready".',
             'Maggi masala packet: the framework adds the default spices unless you brought your own.'),
            ('<code>SpringApplication.run()</code> begins.',),
            ('Environment is built: application.yml, env vars, command line, profiles.',),
            ('An ApplicationContext is created (servlet or reactive, decided by the classpath).',),
            ('Component scan finds your beans; <b>auto-configuration</b> classes listed in <code>AutoConfiguration.imports</code> are considered.',),
            ('Each auto-config is guarded by conditions. <b>Your own bean wins</b> because of <code>@ConditionalOnMissingBean</code>.',),
            ('Singletons are created, dependencies injected, <code>@PostConstruct</code> runs.',),
            ('Embedded Tomcat starts and binds the port(s).',),
            ('Runners execute, <code>ApplicationReadyEvent</code> fires, readiness turns <b>ACCEPTING_TRAFFIC</b>.',)]
    scenes.append(scene('Startup', 400, b, caps))

    page('05-springboot-request-lifecycle.html', 'Spring Boot: startup and request lifecycle',
         'From java -jar to ready, and from HTTP request to GPU and back',
         'Spring Boot is not magic. Every default is a conditional bean you can override.',
         'Spring + starters + auto-configuration + embedded server + Actuator, with a predictable filter → servlet → controller path.',
         scenes)


# ======================================================================
# 06  Spring Boot gateway → GPU autoscaling
# ======================================================================
def d06():
    b = ''
    b += box(15, 190, 100, 50, 'n', 'Clients', None, a='1 7')
    b += box(140, 190, 100, 50, 'b', 'Ingress', 'ALB / NGINX', a=1)
    b += frame(270, 90, 190, 230, 'Spring Boot gateway')
    for i, y in enumerate((125, 185, 245)):
        b += box(285, y, 160, 44, 'g', f'gateway-{i + 1}', 'bulkhead 8 · RestClient', a='2 3')
    b += frame(560, 30, 390, 200, 'GPU node A')
    b += box(580, 70, 150, 48, 'g', 'vllm-1', '1× GPU', a='3 7')
    b += box(580, 140, 150, 48, 'g', 'vllm-2', '1× GPU', a='3 7')
    b += label(850, 62, 'queue: waiting', 'sm', s=4)
    b += '<rect class="n" x="830" y="75" width="40" height="120"/>'
    b += '<rect class="solida" x="830" y="95" width="40" height="100" data-s="4" data-a="4 5"/>'
    b += '<rect class="n" x="831" y="76" width="38" height="75" data-s="7" style="fill:#fff;stroke:none"/>'
    b += frame(560, 255, 390, 200, 'GPU node B (Karpenter)', s=6)
    b += box(580, 295, 150, 48, 'g', 'vllm-3', 'new replica', s=6, a='6 7')
    b += box(580, 365, 150, 48, 'g', 'vllm-4', 'new replica', s=6, a='6 7')
    b += box(270, 345, 190, 48, 'p', 'Prometheus + KEDA', 'vllm:num_requests_waiting', s=5, a=5)
    b += box(270, 405, 190, 48, 'a', 'Karpenter', 'pending GPU Pods → node', s=6, a=6)
    b += label(200, 318, '429 Retry-After', 'sm', s=2, color='#B81A1A')
    b += flow('M115,215 L140,215', 1)
    b += flow('M240,215 L270,215', 1)
    b += flow('M460,150 C510,150 510,94 580,94', 3, 'g')
    b += flow('M460,215 C520,215 520,164 580,164', 3, 'g')
    b += flow('M270,300 L190,300 L190,242', 2, 'r')
    b += flow('M460,369 L520,369 L520,319 L580,319', 5, 'p')
    b += flow('M460,429 L540,429 L540,389 L580,389', 6, 'a')
    caps = [('Spring Boot gateway in front of vLLM, and how the platform scales under load.',
             'Reception desk (gateway) in front of a busy kitchen (GPU): limit the orders in, grow the kitchen when the queue builds.'),
            ('Clients reach the gateway through the ingress.',),
            ('Each gateway replica caps in-flight calls (<b>bulkhead</b>). Over the cap → <code>429 + Retry-After</code> instead of overloading the GPU.',),
            ('Admitted requests are forwarded to the vLLM Service on GPU nodes.',),
            ('Demand rises: vLLM\'s waiting queue grows. This is the right scaling signal, not raw GPU utilisation.',),
            ('<b>KEDA</b> reads the queue from Prometheus and raises vLLM replicas 2 → 4.',),
            ('New Pods are Pending (no free GPUs) so <b>Karpenter</b> launches a GPU node. Image pull and model load take minutes, so keep a warm floor.',),
            ('New replicas pass their <code>startupProbe</code> and <code>readinessProbe</code>, the queue drains, and the 429s stop.',)]
    page('06-springboot-gpu-gateway.html', 'Spring Boot gateway in front of GPU inference',
         'Protect the GPU, scale on the queue, add nodes on demand',
         'Autoscaling on CPU or GPU utilisation alone. A busy GPU may still have batch headroom, and CPU says nothing about the queue.',
         'Bulkhead and timeouts at the gateway, queue-depth scaling with KEDA, node scaling with Karpenter.',
         [scene('Gateway to GPU', 470, b, caps)])



# ======================================================================
# 07  AI platform on private cloud (layers + tenant request)
# ======================================================================
def d07():
    b = ''
    layers = [
        (60,  'b', 'Experience', 'SPA portal · APIs · CLI · self-service', 1),
        (120, 'g', 'Platform services (Java / Spring Boot)', 'tenant · quota · catalogue · orchestrator · metering · inference gateway', 2),
        (180, 'p', 'Event backbone (Kafka)', 'lifecycle events · usage metering · audit', 3),
        (240, 'n', 'Kubernetes + GPU layer', 'Operator · MIG/DRA · Kueue · DCGM · vLLM/Triton', 4),
        (300, 'a', 'Cloud foundation', 'bare-metal provisioning · identity · network · storage · secrets', 5),
        (360, 'n', 'Infrastructure', 'GPU servers · RoCE / InfiniBand · storage · DC power & cooling', 6),
    ]
    for y, c, t, sub, st in layers:
        b += box(200, y, 560, 48, c, t, sub, s=st, a=st)
    b += box(20, 60, 140, 48, 'n', 'Tenant', 'enterprise user', a=1)
    b += box(800, 120, 140, 48, 'r', 'Security', 'IAM · audit · CVEs', s=7, a=7)
    b += box(800, 240, 140, 48, 'g', 'SRE / Ops', 'SLOs · on-call', s=7, a=7)
    b += box(800, 360, 140, 48, 'a', 'FinOps', 'cost per tenant', s=7, a=7)
    b += flow('M160,84 L200,84', 1, 'b')
    b += flow('M480,108 L480,120', 2, 'g')
    b += flow('M480,168 L480,180', 3, 'p')
    b += flow('M480,228 L480,240', 4)
    b += flow('M480,288 L480,300', 5, 'a')
    b += flow('M480,348 L480,360', 6)
    b += flow('M800,144 L760,144', 7, 'r')
    b += flow('M800,264 L760,264', 7, 'g')
    b += flow('M800,384 L760,384', 7, 'a')
    caps = [('A private-cloud GPU/AI platform, top to bottom. Each layer has an owner and an SLO.',
             'Shopping mall: shopfront (portal), management office (services), intercom (Kafka), plumbing (K8s/GPU), foundations, land.'),
            ('<b>Experience:</b> tenants self-serve through a portal, APIs and CLI (SPA frontend, contract-first APIs).',),
            ('<b>Platform services</b> (Java/Spring Boot): tenants, quotas, catalogue, provisioning orchestration, metering, inference gateway. This is where your teams build.',),
            ('<b>Kafka</b> carries lifecycle, usage and audit events so services stay decoupled and billing can replay.',),
            ('<b>Kubernetes + GPU layer:</b> Operator, MIG or DRA, Kueue for fair share, DCGM for health and cost, model servers.',),
            ('<b>Cloud foundation:</b> bare-metal provisioning, identity, networking, storage, secrets.',),
            ('<b>Infrastructure:</b> GPU servers on a fast fabric. Capacity is scarce and has long lead times.',),
            ('<b>Cross-cutting:</b> security (isolation, audit, CVEs), SRE (SLOs, incidents), FinOps (cost per tenant). A director owns how these three meet delivery.',)]
    page('07-ai-platform-private-cloud.html', 'Private-cloud GPU/AI platform: the layers',
         'What you would lead, and where the risks sit',
         'A pile of GPU servers with a Kubernetes cluster on top.',
         'A product: self-service experience, platform services, event backbone, GPU layer and foundation, run to SLOs and billed per tenant.',
         [scene('Platform layers', 470, b, caps)])


# ======================================================================
# 08  Kafka event flow
# ======================================================================
def d08():
    b = ''
    b += box(20, 150, 130, 56, 'g', 'Producer', 'key = tenantId', a='1 2')
    b += frame(190, 60, 330, 250, 'Topic: gpu.usage (3 partitions)')
    for i, y in enumerate((100, 170, 240)):
        b += box(210, y, 290, 50, 'b', f'Partition {i}', 'offset 0 … N', a=f'2 {4 if i == 2 else 99}')
    b += frame(580, 60, 360, 250, 'Consumer group: billing')
    b += box(600, 100, 150, 50, 'p', 'Consumer 1', 'P0', s=3, a=3)
    b += box(600, 170, 150, 50, 'p', 'Consumer 2', 'P1', s=3, a=3)
    b += box(600, 240, 150, 50, 'p', 'Consumer 3', 'P2', s=3, a=3)
    b += box(770, 100, 150, 50, 'g', 'Idempotent', 'dedupe by event id', s=5, a=5)
    b += box(770, 240, 150, 50, 'r', 'Dead-letter topic', 'after N retries', s=6, a=6)
    b += box(190, 340, 330, 44, 'a', 'Consumer lag = latest offset - committed', None, s=4, a=4)
    b += box(580, 340, 360, 44, 'n', 'Outbox: DB row + event in one transaction', 'relay publishes to Kafka', s=7, a=7)
    b += flow('M150,170 L190,125', 2, 'g')
    b += flow('M150,180 L190,195', 2, 'g')
    b += flow('M150,190 L190,265', 2, 'g')
    b += flow('M500,125 L600,125', 3, 'p')
    b += flow('M500,195 L600,195', 3, 'p')
    b += flow('M500,265 L600,265', 3, 'p')
    b += flow('M750,125 L770,125', 5, 'g')
    b += flow('M750,265 L770,265', 6, 'r')
    caps = [('Kafka in one picture: a topic split into partitions, read by a consumer group.',
             'Railway: line = topic, track = partition, porters = consumers, offset = how far each porter has unloaded.'),
            ('The producer chooses the partition from the <b>key</b> (here the tenant). Same key, same partition, same order.',),
            ('Events are appended to partitions. <b>Order is guaranteed only inside a partition.</b>',),
            ('Each partition is read by exactly one consumer in the group. More consumers than partitions sit idle.',),
            ('If consumers fall behind, <b>lag</b> grows. Check slow handlers, hot partitions, downstream timeouts.',),
            ('Delivery is at-least-once in practice, so handlers must be <b>idempotent</b> (dedupe by event id).',),
            ('Poison messages go to a <b>dead-letter topic</b> after bounded retries, with an alert and a replay tool.',),
            ('To avoid "DB saved, Kafka failed", write the event to an <b>outbox</b> table in the same transaction and let a relay publish it.',)]
    page('08-kafka-event-flow.html', 'Kafka: partitions, consumer groups, lag, DLQ, outbox',
         'The ideas a director must be able to explain simply',
         'A faster message queue where ordering and delivery are automatic.',
         'A partitioned, replicated log: ordering per partition, consumers track offsets, and you design for duplicates and failures.',
         [scene('Kafka', 420, b, caps)])

# ======================================================================
def index():
    cards = [
        ('01-gpu-scheduling-flow.html', 'From Pod YAML to GPU', 'Device plugin, scheduler, kubelet, toolkit, driver'),
        ('02-gpu-sharing.html', 'GPU sharing', 'Exclusive vs time-slicing vs MIG vs MPS'),
        ('03-gpu-operator-stack.html', 'GPU Operator stack', 'What runs on a GPU node and in what order'),
        ('04-multinode-training.html', 'Multi-node training', 'Gang scheduling (Kueue) and NCCL all-reduce'),
        ('05-springboot-request-lifecycle.html', 'Spring Boot lifecycle', 'Startup sequence and request path'),
        ('06-springboot-gpu-gateway.html', 'Gateway + GPU autoscaling', 'Bulkhead, KEDA on queue depth, Karpenter'),
        ('07-ai-platform-private-cloud.html', 'AI platform layers', 'Private-cloud GPU/AI platform, top to bottom'),
        ('08-kafka-event-flow.html', 'Kafka event flow', 'Partitions, consumer groups, lag, DLQ, outbox'),
    ]
    items = ''.join(
        f'<a class="card" href="{h}"><h3>{t}</h3><p>{d}</p></a>' for h, t, d in cards)
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>GPU on Kubernetes: animated diagrams</title>
<link rel="stylesheet" href="assets/anim.css">
<style>.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin-top:16px}}
.card{{display:block;border:1px solid var(--line);border-radius:10px;padding:16px;text-decoration:none;color:var(--ink);background:#fff}}
.card:hover{{border-color:var(--blue);box-shadow:0 2px 10px rgba(26,92,191,.15)}}
.card h3{{margin:0 0 6px;color:var(--blue)}}.card p{{margin:0;color:var(--muted);font-size:14px}}</style></head>
<body><div class="wrap"><h1>GPU on Kubernetes: animated diagrams</h1>
<p class="sub">Open any page, press Play (or use ← → keys). Each step has an everyday analogy.</p>
<div class="grid">{items}</div></div></body></html>'''
    (OUT / 'index.html').write_text(html, encoding='utf-8')
    print('wrote index.html')


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    d01(); d02(); d03(); d04(); d05(); d06(); d07(); d08(); index()
    (OUT / 'audio').mkdir(exist_ok=True)
    (OUT / 'audio' / 'narration.json').write_text(json.dumps(NARR, indent=1, ensure_ascii=False), encoding='utf-8')
