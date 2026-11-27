# GPU on Kubernetes + Spring Boot: interview prep

Everyday-analogy explanations, interview Q&A, runnable-style manifests, a Spring Boot gateway sample, and **animated diagrams**.

## Start here
| What | Where |
|---|---|
| Deep dive (stack, device plugin, Operator, sharing, DRA, scheduling, training, inference, cost, troubleshooting) | [docs/01-gpu-k8s-deep-dive.md](docs/01-gpu-k8s-deep-dive.md) |
| 38 Q&A + 3 system-design walkthroughs + questions to ask them | [docs/02-interview-qa.md](docs/02-interview-qa.md) |
| Spring Boot (Boot 4 era) notes + 20 Q&A + GPU-gateway patterns | [docs/03-spring-boot.md](docs/03-spring-boot.md) |
| One-page revision sheet | [docs/04-cheatsheet.md](docs/04-cheatsheet.md) |
| Director / Associate Director (platform engineering) interview: leadership, delivery, architecture, Kafka, SPA, ops, scenarios, 90 days | [docs/05-director-platform-engineering-interview.md](docs/05-director-platform-engineering-interview.md) |
| Animated diagrams (open `diagrams/index.html` in a browser) | [diagrams/](diagrams/index.html) |
| YAML you can adapt (pod, time-slicing, MIG, Kueue, DRA, vLLM, KEDA, Karpenter, Spring gateway) | [manifests/](manifests/) |
| Spring Boot gateway sample (bulkhead, timeouts, SSE, Micrometer) | [springboot-gpu-gateway/](springboot-gpu-gateway/) |

## Animated diagrams
Open `diagrams/index.html` locally, or enable GitHub Pages (Settings → Pages → branch `main`, folder `/`) and visit `/diagrams/`.
Each page opens with a "Why this matters" card and **recorded narration** (MP3 files in `diagrams/audio/`, plays in any browser; press Play with audio, choose speed). Controls: Play/Pause, Prev/Next (speaks that step), or ← → and Space. Deep link: `page.html#s=<scene>&t=<step>`.

1. From Pod YAML to GPU
2. Sharing: exclusive / time-slicing / MIG / MPS
3. GPU Operator stack
4. Multi-node training: gang scheduling + all-reduce
5. Spring Boot startup + request lifecycle
6. Spring Boot gateway + GPU autoscaling (bulkhead, KEDA, Karpenter)
7. Private-cloud GPU/AI platform layers
8. Kafka: partitions, consumer groups, lag, DLQ, outbox

Regenerate pages: `python3 tools/build_diagrams.py`. Regenerate audio: `python3 tools/gen_audio.py MODEL.onnx VOICES.bin` (Kokoro open-source TTS, see script header).

## Status and caveats
- Facts checked Nov 2026: Kubernetes 1.37 current; DRA core GA in 1.34, DRA extended-resource GA in 1.37; Spring Boot 4.1.x current (Boot 3.5 OSS EOL 30 Jun 2026).
- The Spring Boot sample and the YAML were **not compiled/applied** in the authoring environment (no Maven Central or cluster access). Treat as reference skeletons; pin versions and test.
- Hardware numbers (bandwidths, MIG geometries) are rules of thumb: confirm against the vendor datasheet for your GPU.
