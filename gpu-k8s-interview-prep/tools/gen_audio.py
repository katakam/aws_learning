#!/usr/bin/env python3
"""Generate narration MP3s for the diagrams with Kokoro (open-source TTS, runs on CPU).

Setup:  pip install kokoro-onnx soundfile ;  ffmpeg on PATH
Models: kokoro-v1.0.int8.onnx + voices-v1.0.bin from
        https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
Run:    python3 tools/gen_audio.py MODEL.onnx VOICES.bin [max_seconds]
Reads diagrams/audio/narration.json (written by build_diagrams.py); skips clips that already exist.
"""
import json, pathlib, re, subprocess, sys, tempfile, time
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'diagrams' / 'audio'
VOICE, SPEED, LANG = 'bf_emma', 0.95, 'en-gb'

SAY = {'NCCL': 'N C C L', 'EFA': 'E F A', 'DCGM': 'D C G M', 'CDI': 'C D I', 'GFD': 'G F D', 'NFD': 'N F D',
       'OOM': 'out of memory', 'DLQ': 'D L Q', 'JWT': 'J W T', 'SPA': 'S P A', 'TCP': 'T C P', 'RDMA': 'R D M A',
       'SSE': 'S S E', 'vLLM': 'v L L M', 'MPS': 'M P S', 'APIs': 'A P Is', 'API': 'A P I', 'CPU': 'C P U',
       'DB': 'D B', 'SLOs': 'S L Os', 'SLO': 'S L O', 'IAM': 'I A M', 'CVEs': 'C V Es', 'HPA': 'H P A',
       'DRA': 'D R A', 'NIC': 'N I C', 'AZ': 'A Z', 'CLI': 'C L I', 'GPUs': 'G P Us', 'GPU': 'G P U',
       'NVLink': 'N V Link', 'kubelet': 'kube-let', 'kubectl': 'kube control', 'etcd': 'et C D',
       'Kueue': 'Queue', 'containerd': 'container D', 'NVML': 'N V M L', 'MIG': 'mig', 'YAML': 'yaml',
       'KEDA': 'keda', 'OSS': 'O S S', 'BSS': 'B S S', 'SM': 'S M', 'SMs': 'S Ms'}


def clean(t):
    t = (t.replace('nvidia.com/gpu', 'nvidia dot com slash G P U').replace('→', ' to ').replace('≥', ' at least ')
          .replace('≈', ' about ').replace('×', ' times ').replace('&', ' and ').replace('%', ' percent')
          .replace('/', ' slash ').replace('·', ',').replace('…', '.').replace('✓', ''))
    t = re.sub(r'\b(' + '|'.join(sorted(map(re.escape, SAY), key=len, reverse=True)) + r')\b', lambda m: SAY[m.group(1)], t)
    return re.sub(r'\s+', ' ', t).strip()


def main():
    model, voices = sys.argv[1], sys.argv[2]
    cap = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9
    k = Kokoro(model, voices)
    data = json.loads((ROOT / 'narration.json').read_text())
    t0 = time.time(); made = 0; left = 0
    for slug, scenes in data.items():
        for si, steps in enumerate(scenes):
            for ti, parts in enumerate(steps):
                out = ROOT / f'{slug}-{si}-{ti}.mp3'
                if out.exists():
                    continue
                if time.time() - t0 > cap:
                    left += 1
                    continue
                chunks = []
                for p in parts:
                    s, sr = k.create(clean(p), voice=VOICE, speed=SPEED, lang=LANG)
                    chunks += [s, np.zeros(int(sr * 0.35), dtype=s.dtype)]
                with tempfile.NamedTemporaryFile(suffix='.wav') as tf:
                    sf.write(tf.name, np.concatenate(chunks), sr)
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', tf.name, '-ac', '1', '-b:a', '64k', str(out)], check=True)
                made += 1
                print('made', out.name, flush=True)
    print(f'made {made}, remaining {left}')


if __name__ == '__main__':
    main()
