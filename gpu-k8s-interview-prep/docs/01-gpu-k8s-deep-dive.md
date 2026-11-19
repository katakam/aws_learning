# GPU on Kubernetes — Deep Dive

> Format: **NOT → IS** first (Winston fence), then an everyday analogy, then the mechanics.
> Versions checked Nov 2026: Kubernetes 1.37 current, DRA core GA since 1.34, DRA extended-resource support GA in 1.37.

---

## 0. The 30-second picture

**NOT:** Kubernetes does not know what a GPU is. The scheduler only counts opaque integers.
**IS:** A GPU is an *extended resource* (`nvidia.com/gpu`) advertised by a **device plugin**, made visible inside containers by the **NVIDIA container toolkit**, and powered by the **host driver**. The **GPU Operator** installs and babysits all of that.

**Analogy — taxi stand.**
- GPU = a taxi.
- Driver = the taxi's engine and licence (must match the road rules, i.e. CUDA version).
- Device plugin = the dispatcher who tells the city control room (kubelet) "I have 4 taxis, here are their numbers".
- Scheduler = control room: "this passenger needs 1 taxi, which depot has a free one?"
- Container toolkit = the key handover: gives the passenger the key of *that one* taxi only.
- GPU Operator = the taxi-company manager who makes sure every depot has engine, dispatcher, keys and a mechanic.

---

## 1. The stack, bottom to top

| Layer | What it is | Who owns it |
|---|---|---|
| Hardware | GPU (A10G, L4, A100, H100, H200, B200…) + NVLink/NVSwitch + NIC (EFA/IB) | Cloud / you |
| Kernel driver | `nvidia.ko`, NVML, `libcuda.so` | Host (AMI) **or** driver container from the Operator |
| Container toolkit | Injects `/dev/nvidia*` + driver libs into containers; CDI spec generation | NVIDIA Container Toolkit |
| Runtime | containerd / CRI-O configured with the `nvidia` runtime or CDI | Node |
| Device plugin | gRPC server; registers `nvidia.com/gpu` with kubelet | DaemonSet |
| kubelet | Tracks allocatable GPUs; calls `Allocate()` | Kubernetes |
| Scheduler | Fits Pod's `limits` against node `allocatable` | Kubernetes |
| Your container | CUDA runtime + framework (PyTorch, vLLM, Triton) | You |

**Key rule of thumb:** *driver on the host, CUDA toolkit in the image.* The host driver must be **new enough** for the CUDA version inside your image.

---

## 2. Device plugin internals (interview favourite)

**Analogy:** hotel front desk. The desk (plugin) tells the hotel manager (kubelet) "I have rooms 1-4". When a guest (Pod) arrives, kubelet asks "give me one room", desk answers "room 2, here is the key card".

Mechanics:
1. Plugin starts a gRPC server on a unix socket in `/var/lib/kubelet/device-plugins/`.
2. It calls `Register` on `kubelet.sock`, giving its socket name and resource name (`nvidia.com/gpu`).
3. `ListAndWatch` — a **streaming** RPC. Plugin sends the device list and re-sends whenever health changes.
4. kubelet adds the count to Node `status.capacity` / `allocatable`.
5. When a Pod lands on the node, kubelet calls `Allocate(deviceIDs)`. Plugin returns env vars, device nodes, mounts, annotations (or CDI device names).
6. Optional: `GetPreferredAllocation` (pick GPUs that are NVLink-adjacent), `PreStartContainer`.

Extended-resource rules — memorise these:
- **Integers only.** No `0.5` GPU.
- **`requests` must equal `limits`** (if you set both). Setting only `limits` is fine; request defaults to limit.
- **No overcommit.** One GPU cannot be given to two Pods (unless you configure sharing).
- Unhealthy GPU → removed from allocatable, but **running Pods are not killed**.
- Plugin restart → kubelet re-registers; if the plugin is down, new GPU Pods cannot start but running ones keep running.

---

## 3. From Pod to GPU — the full path

1. `kubectl apply` a Pod with `resources.limits."nvidia.com/gpu": 1`.
2. Scheduler **Filter**: `NodeResourcesFit` rejects nodes without free `nvidia.com/gpu`. Taints/affinity also checked.
3. Scheduler **Score** + **Bind**.
4. kubelet on that node admits the Pod, asks the device plugin to `Allocate`.
5. Plugin picks GPU-2, returns `NVIDIA_VISIBLE_DEVICES=GPU-<uuid>` (or a CDI name like `nvidia.com/gpu=2`).
6. containerd + nvidia toolkit create the container, mount `/dev/nvidia2`, `/dev/nvidiactl`, `/dev/nvidia-uvm`, and bind-mount driver libs.
7. App calls CUDA → talks to the host driver → real GPU. `nvidia-smi` inside shows only GPU-2.

> Animated version: `diagrams/01-gpu-scheduling-flow.html`

**CDI (Container Device Interface)** is the modern replacement for the old `nvidia-container-runtime` hook: a JSON/YAML spec lists devices, and the runtime applies it natively. Less hook magic, easier for non-NVIDIA devices too. `RuntimeClass: nvidia` is the older/explicit way to pick the NVIDIA runtime.

---

## 4. NVIDIA GPU Operator

**Analogy:** the society maintenance office. You don't hire an electrician, plumber and guard per flat; the office does it for every flat via one contract (`ClusterPolicy` CRD).

Operands (all DaemonSets/Deployments):
- **NFD (Node Feature Discovery)** — detects NVIDIA PCI device (vendor `10de`) and labels the node so other operands know where to run.
- **Driver** — containerised driver (skip if the AMI already has it).
- **Container Toolkit** — configures containerd / CDI.
- **Device Plugin** — advertises `nvidia.com/gpu` (and MIG/shared variants). Also hosts the **MPS control daemon** when MPS is on.
- **GFD (GPU Feature Discovery)** — labels: `nvidia.com/gpu.product`, `.memory`, `.count`, `.family`, `nvidia.com/mig.capable`, CUDA driver/runtime versions.
- **DCGM + DCGM Exporter** — Prometheus metrics.
- **MIG Manager** — applies MIG layouts from the `nvidia.com/mig.config` node label.
- **Validator** — init checks that gate other operands (driver ok → toolkit ok → CUDA ok → plugin ok).
- Optional: vGPU manager, sandbox/KubeVirt device plugin, VFIO manager, GDS driver.

Install notes:
- Helm chart `nvidia/gpu-operator`, namespace `gpu-operator`.
- **EKS:** use the accelerated (NVIDIA) EKS-optimized AMI which ships the driver; typically set `driver.enabled=false` and let the Operator handle the rest. Check your AMI's toolkit status before also disabling `toolkit`.
- **Operator does not auto-watch your time-slicing ConfigMap** — after editing it, restart the device-plugin DaemonSet (a classic gotcha).
- Upgrades: drain GPU nodes; driver container upgrade is rolling via the driver upgrade controller.

---

## 5. Scheduling GPU workloads

### 5.1 Basics
- Request: `limits: nvidia.com/gpu: N`.
- **Taint GPU nodes** (`nvidia.com/gpu=present:NoSchedule`) so CPU-only Pods don't squat on expensive nodes; GPU Pods tolerate it. (EKS/Karpenter: set the taint on the NodePool.)
- **Pick the model by label**, not by guessing: `nodeSelector: nvidia.com/gpu.product: NVIDIA-A100-SXM4-80GB` (GFD label).
- **ResourceQuota:** `requests.nvidia.com/gpu: "8"` per namespace — quotas are how you do multi-tenant fairness.
- **Bin-packing vs spreading:** default scoring spreads. For GPU fleets you usually want *pack* (so whole nodes free up and autoscaler can remove them): use `NodeResourcesFit` with `MostAllocated` scoring.
- **Priority + preemption:** let inference preempt dev notebooks via `PriorityClass`.

### 5.2 Topology
- Intra-node: NVLink/NVSwitch domains. Two GPUs on the same NVLink island talk ~10× faster than over PCIe.
- Kubelet **Topology Manager** (`best-effort`/`restricted`/`single-numa-node`) aligns CPU, memory, GPU, NIC on the same NUMA node.
- Multi-GPU Pods should request **all GPUs of the node** (e.g., 8) for tensor parallelism, otherwise you may get a bad mix.

### 5.3 Gang scheduling
**Analogy:** wedding party booking. 8 people must sit together — if only 5 seats exist, don't seat anyone. Default Kubernetes seats whoever arrives first → half the job holds GPUs forever waiting for the rest (deadlock + waste).

Tools:
- **Kueue** (SIG-Scheduling): queues, quotas, borrowing/fair share, admits a *Workload* all-or-nothing. Works with Job, JobSet, RayJob, Kubeflow jobs. Concepts: `ResourceFlavor`, `ClusterQueue`, `LocalQueue`, `Workload`, `WorkloadPriorityClass`.
- **Volcano** — own scheduler, `PodGroup`, queues.
- **scheduler-plugins coscheduling** — `PodGroup` with minMember.
- **JobSet** — one object for a group of Jobs (e.g., driver + workers).
- **LeaderWorkerSet** — multi-node *inference* (one leader + N workers as a unit; restarts together).
- **Kubeflow Training Operator / MPI Operator**, **KubeRay** for Ray.

---

## 6. GPU sharing — pick the right wall

**Analogy — housing.**
| Technique | Housing analogy | Isolation |
|---|---|---|
| Exclusive | Whole bungalow, one family | Full |
| Time-slicing | One auto-rickshaw, passengers take turns | **None** (no memory limits, one OOM can hurt others) |
| MPS | One shared kitchen, several cooks at once | Weak (shared context; thread % and memory caps) |
| MIG | Separate flats in one building — own walls, own meter | **Hardware** (memory, cache, SMs) |
| vGPU | Rented rooms managed by building owner (hypervisor) | Strong, licensed |

### Time-slicing
- Config via device-plugin ConfigMap: `sharing.timeSlicing.resources[].replicas: 4` → node advertises `nvidia.com/gpu: 4` for 1 physical GPU.
- `renameByDefault: true` → advertises `nvidia.com/gpu.shared` so Pods opt in explicitly.
- Context switching has overhead; no QoS; **no memory isolation** → use for dev, notebooks, light inference.
- `failRequestsGreaterThanOne: true` stops a Pod asking for 2 replicas thinking it gets 2× speed.

### MIG (Multi-Instance GPU)
- Supported on A100, A30, H100, H200, B200 etc. (not T4/L4/A10G).
- A100/H100 80GB can split into up to **7** instances (e.g., `1g.10gb` × 7, `3g.40gb` + `4g.40gb`, …).
- Strategies: `none` (ignore MIG), `single` (all GPUs same profile; resource still `nvidia.com/gpu`), `mixed` (different profiles; resources like `nvidia.com/mig-1g.10gb`).
- Change layout by labelling the node `nvidia.com/mig.config=all-1g.10gb`; **MIG Manager** drains/reconfigures. Layout changes need **no running GPU workloads** on that GPU.
- Best for: many small, latency-sensitive inference services with strict isolation.
- Limitation: static partitions; stranded capacity if mix doesn't match demand. DRA is the answer to this.

### MPS
- A control daemon lets multiple processes share one CUDA context → real concurrent kernels (no time-slice switching).
- Good for many small kernels/small batch inference. Weaker fault isolation than MIG.

---

## 7. Dynamic Resource Allocation (DRA) — the future (and now present)

**NOT:** device plugin ("I want *a* GPU, count only, decided at node start").
**IS:** a claim system ("I want a GPU with ≥40 GB memory, Hopper, on the same NVLink as my other GPU, shared by these 2 containers").

**Analogy:** counting-taxi vs. Ola/Uber. Device plugin = "give me any 1 taxi". DRA = "give me an SUV, AC, within 2 km, shared with my colleague".

Objects (`resource.k8s.io/v1`):
- **DeviceClass** — category of device + selectors (installed by the driver: `gpu.nvidia.com`, `mig.nvidia.com`).
- **ResourceSlice** — published by the driver: "node X has these devices with these attributes (product, memory, PCI bus, MIG profile…)". Scheduler reads these.
- **ResourceClaim** — a request; **ResourceClaimTemplate** — a per-Pod claim generated from a template.
- Pod references claims under `spec.resourceClaims`, containers consume via `resources.claims`.
- Selection uses **CEL expressions** over device attributes.
- **Structured parameters** let the *scheduler* decide without calling the driver in the loop (this is what made it GA-able).

Status:
- Core DRA **GA in 1.34**, locked on in 1.35. **DRA extended-resource support GA in 1.37** — lets old `nvidia.com/gpu: 1` YAML be served by DRA drivers (smooth migration).
- NVIDIA DRA driver now lives in `kubernetes-sigs/dra-driver-nvidia-gpu`. GPU allocation via DRA is opt-in (node label `nvidia.com/dra-kubelet-plugin=true`).
- Wins: dynamic MIG carve-up on demand, sharing semantics, multi-device topology, **ComputeDomains** for multi-node NVLink (GB200 NVL72 class systems), fewer node labels/webhooks.
- Caveats: managed-service (EKS/GKE/AKS) and ecosystem maturity vary — check your version matrix before betting production on it.

---

## 8. Multi-node training networking

- **Intra-node:** NVLink/NVSwitch. **Inter-node:** InfiniBand, RoCE, or **AWS EFA** (`vpc.amazonaws.com/efa` resource, EFA device plugin, `aws-ofi-nccl` plugin).
- **NCCL** does collective ops (all-reduce, all-gather). `NCCL_DEBUG=INFO` is your first debugging step. Wrong interface → silent fallback to slow TCP.
- **GPUDirect RDMA** — NIC reads/writes GPU memory directly, bypassing CPU.
- Place nodes in a **cluster placement group / same AZ / same spine** for low latency.
- **Shared memory:** mount `emptyDir{medium: Memory}` on `/dev/shm` (PyTorch DataLoader dies with default 64 MB).
- Checkpoints to FSx for Lustre / S3 — **Spot** is fine only if you checkpoint frequently.
- Fault tolerance: one bad GPU kills a 512-GPU job → health checks, auto-cordon, elastic training (torchrun elastic), fast restart from checkpoint.

---

## 9. Inference on Kubernetes

Serving engines: **vLLM**, **Triton**, **TGI**, **TensorRT-LLM**; control layer: **KServe**, KubeRay Serve, LeaderWorkerSet for multi-node.

GPU memory budget (rule of thumb):
`weights ≈ params × bytes/param` (FP16 = 2 B, FP8/INT8 = 1 B, INT4 = 0.5 B) + **KV cache** (grows with batch × context) + activations + CUDA overhead. A 70B model in FP16 ≈ 140 GB → needs ≥2×80 GB with tensor parallel.

Operational patterns:
- **Slow start** (pull 10-30 GB image + load weights): use `startupProbe` with generous `failureThreshold`, readiness only after model loaded.
- **Cache weights:** PVC/EFS/FSx, S3 mountpoint, init-container download, or bake in image. Pre-pull images (DaemonSet / image caching) to cut cold start.
- **Autoscale on the right signal:** queue depth, in-flight requests, tokens/s, time-to-first-token — **not** raw GPU utilisation (a busy GPU at 100 % can still have free batch capacity). KEDA + Prometheus is the common route.
- **Scale-to-zero** on GPUs = painful cold starts; keep a warm floor for latency-sensitive paths.
- **Graceful shutdown:** `terminationGracePeriodSeconds` ≥ longest generation; `preStop` sleep so the Service stops routing first.
- **Gateway in front** (see Spring Boot gateway in this repo): auth, rate limit by tokens, queue/bulkhead, retries only if idempotent.

---

## 10. Autoscaling and cost

- **Cluster Autoscaler** vs **Karpenter** (EKS): Karpenter provisions the right GPU instance directly from pending Pod requests (`nvidia.com/gpu`), consolidates empty nodes. Use separate NodePools for inference vs training; taint them; set `capacity-type` (on-demand/spot); restrict families (g5/g6/g6e/p4d/p5…).
- **Capacity:** big training GPUs are scarce → On-Demand Capacity Reservations or **EC2 Capacity Blocks for ML**; Spot for fault-tolerant jobs only.
- **Cost levers:** MIG/time-slicing for small models, right-size GPU (L4/A10G for small inference, H100 for big), bin-pack, idle-GPU reaper (alert on util < X% for Y hours), quantisation (FP8/INT4), batch scheduling via Kueue with borrowing.
- **Showback:** label Pods by team, use DCGM + OpenCost/Kubecost to allocate GPU-hours.

---

## 11. Observability

- **DCGM Exporter → Prometheus → Grafana.** Key metrics:
  - `DCGM_FI_DEV_GPU_UTIL` — SM busy %
  - `DCGM_FI_DEV_FB_USED` / `FB_FREE` — framebuffer memory
  - `DCGM_FI_DEV_POWER_USAGE`, `DCGM_FI_DEV_GPU_TEMP`
  - `DCGM_FI_DEV_SM_CLOCK`
  - `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` — tensor-core use (needs profiling metrics enabled)
  - `DCGM_FI_DEV_XID_ERRORS` — last XID error
- **XID errors** (kernel log): `79` GPU fell off the bus (hardware; cordon+replace), `48` double-bit ECC (replace), `31` GPU memory page fault (usually app bug), `13` graphics engine exception (app/driver). Wire fatal XIDs to automatic cordon-and-drain.
- **GPU util ≠ efficiency.** 100 % util can still be memory-bound. Watch tensor activity, memory bandwidth, and app-level throughput.
- Node: `kubectl describe node` → `Capacity`/`Allocatable` for `nvidia.com/gpu`. Pods: events for `Insufficient nvidia.com/gpu`.

---

## 12. Security & multi-tenancy

- Never run GPU Pods `privileged` just to "make it work".
- Set the device plugin to **ignore** `NVIDIA_VISIBLE_DEVICES` from unprivileged containers (`accept-nvidia-visible-devices-envvar-when-unprivileged=false`) — otherwise any image could ask for GPUs it was not allocated. Use volume-mount or CDI based injection.
- Hard isolation between tenants → **MIG** or dedicated nodes (taints + namespaces + quotas). Time-slicing/MPS are *not* security boundaries.
- Pod Security Standards, NetworkPolicy, signed images, driver patch cadence (GPU drivers have regular CVEs).
- For regulated environments (e.g., GCC/IM8-style controls): data residency of model weights and prompts, audit logs of who ran what on which GPU, encrypted checkpoints.

---

## 13. Troubleshooting runbook

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Pod `Pending`, "Insufficient nvidia.com/gpu" | No free GPU, or plugin not registered | `kubectl describe node` → allocatable; plugin DaemonSet logs; taints/tolerations |
| Pod `Pending`, node has GPUs but not chosen | Taint, nodeSelector, quota | `describe pod` events; `ResourceQuota` |
| Plugin Pods stuck `Init` | Validator waiting on driver/toolkit | `kubectl logs -c driver-validation`; driver DaemonSet logs |
| `nvidia-smi: command not found` in Pod | Toolkit not injecting, wrong runtime | RuntimeClass/CDI, `/etc/containerd/config.toml`, restart containerd |
| `CUDA error: no kernel image` / driver too old | Image CUDA > host driver | Upgrade driver or use forward-compat; match CUDA to driver |
| `CUDA out of memory` | KV cache/batch too large; shared GPU | Lower batch/`gpu-memory-utilization`; MIG or exclusive |
| Works then GPU disappears in container after a while | Known cgroup (systemd) + device-access issue in older setups | Use CDI / current toolkit; ensure latest plugin |
| MIG layout won't apply | GPU busy | Drain node; check `nvidia.com/mig.config.state` label |
| Time-slicing change ignored | Operator doesn't watch ConfigMap | Restart device-plugin DaemonSet |
| Training hangs at start | NCCL can't reach peers / wrong NIC / partial gang | `NCCL_DEBUG=INFO`, check Kueue admitted all pods, security groups for EFA |
| DataLoader crash "bus error" | `/dev/shm` too small | `emptyDir` Memory mount |
| GPU node never scales down | System DaemonSets / PDBs / pods without owners | Karpenter consolidation settings; `do-not-disrupt` annotations |

---

## 14. Numbers and facts to keep in your head

- A100 80 GB: 7 MIG slices max. H100 80 GB: same. HBM bandwidth ≈ 2 TB/s (A100) / ≈ 3.35 TB/s (H100 SXM).
- NVLink (H100): 900 GB/s per GPU aggregate vs PCIe Gen5 x16 ≈ 64 GB/s each way.
- DRA GA: **1.34**. Extended-resource DRA GA: **1.37**.
- Extended resources: ints only, request == limit, no overcommit.
- FP16 = 2 bytes/param → 7B ≈ 14 GB, 70B ≈ 140 GB.
