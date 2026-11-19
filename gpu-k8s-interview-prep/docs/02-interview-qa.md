# GPU + Kubernetes — Interview Q&A

Short answers first (what you say in 30 seconds). Go deeper only if they push.

---

## A. Fundamentals

**1. How does a Pod get a GPU in Kubernetes?**
Pod asks `nvidia.com/gpu: 1`. The device plugin has registered that resource with kubelet, so the scheduler sees a countable resource and places the Pod on a node with a free one. kubelet calls the plugin's `Allocate`, the plugin returns the device ID, and the container toolkit mounts that GPU's device files and driver libs into the container.
*Analogy:* control room finds a depot with a free taxi; dispatcher hands over the key of one specific taxi.

**2. What is the device plugin framework?**
A gRPC contract between kubelet and a vendor plugin: `Register`, `ListAndWatch` (stream of device list + health), `Allocate`, optional `GetPreferredAllocation`. It lets vendors add hardware without changing Kubernetes core.

**3. Why can't I request 0.5 GPU?**
Extended resources are integers, and the scheduler does not know about GPU internals. Fractions need sharing tech: time-slicing (fake replicas), MPS, MIG (real partitions), or DRA.

**4. Why must GPU `requests` equal `limits`?**
Extended resources can't be overcommitted, so the API requires request == limit (setting only the limit is enough).

**5. What is the NVIDIA GPU Operator and why use it?**
Helm-installed operator that deploys and manages driver, container toolkit, device plugin, GFD, DCGM exporter, MIG manager and a validator through one `ClusterPolicy`. Without it you hand-maintain 6+ DaemonSets across kernel and driver upgrades.

**6. Driver on host or in a container?**
Host (baked into the AMI) is simpler and faster to boot; driver container makes upgrades declarative and survives kernel changes. On EKS, accelerated AMI with host driver + Operator for the rest is the common pattern.

**7. How do I keep CPU Pods off GPU nodes?**
Taint the GPU nodes (`NoSchedule`) and add tolerations only to GPU workloads.

**8. How do I target a specific GPU model?**
GFD labels (`nvidia.com/gpu.product`, `.memory`) with `nodeSelector`/affinity. With DRA: CEL selectors on device attributes.

**9. What is CDI?**
Container Device Interface: a standard spec file describing devices; runtimes (containerd, CRI-O) apply it natively. It replaces the older runtime-hook approach.

**10. What goes wrong with CUDA versions?**
Host driver must support the CUDA version in the image. Newer driver runs older CUDA fine; older driver breaks newer CUDA (error: driver version insufficient). Datacenter GPUs can use forward-compatibility packages.

---

## B. Sharing and utilisation

**11. Time-slicing vs MIG vs MPS — when each?**
- Time-slicing: dev/notebooks/light inference; zero isolation.
- MIG: many small inference services needing hard isolation and predictable latency (A100/H100 class).
- MPS: many small kernels from trusted processes, wants real concurrency.
- Exclusive: training, large models.
*Analogy:* rickshaw turns / separate flats / shared kitchen / whole bungalow.

**12. Downsides of MIG?**
Static geometry (stranded capacity), reconfig needs idle GPU, only on specific GPU families, profile memory is a hard cap (a model that doesn't fit the slice won't run).

**13. How do you change MIG layout?**
Label the node `nvidia.com/mig.config=<profile>`; MIG Manager evicts GPU Pods, reconfigures, relabels state. Plan it as a maintenance operation.

**14. A user complains "my 4 time-sliced replicas run slower than 1 GPU." Why?**
Replicas are scheduling slots, not capacity. They time-share one GPU, plus context-switch overhead and no memory isolation.

**15. How would you raise GPU utilisation on a cluster at 25 %?**
Measure first (DCGM util, memory, tensor activity). Then: right-size GPU type per workload, MIG/time-slicing for small models, continuous batching (vLLM), bin-packing scheduler, Kueue with borrowing for batch fill, kill idle notebooks automatically, queue-based autoscaling.

**16. Why is "GPU util 100 %" not proof of efficiency?**
It only means *a* kernel was running during the sample window. It can be memory-bound or tiny kernels. Look at SM occupancy, tensor-core activity, memory bandwidth, and application throughput.

---

## C. Scheduling and batch

**17. What is gang scheduling and why does training need it?**
All-or-nothing placement of a group of Pods. Without it, a 8-worker job may get 5 GPUs and hold them while waiting forever → deadlock and waste. Use Kueue (admission-level), Volcano or coscheduling.
*Analogy:* wedding party — seat everyone or nobody.

**18. Kueue vs Volcano?**
Kueue = queueing/quota/admission on top of the default scheduler (lighter, upstream SIG, integrates with Job/JobSet/Ray/Kubeflow). Volcano = replacement batch scheduler with its own plugins and PodGroups. Prefer Kueue unless you need Volcano-specific scheduling policies.

**19. How do you share a GPU fleet fairly between teams?**
Namespaces + ResourceQuota (`requests.nvidia.com/gpu`), Kueue ClusterQueues with nominal quota + borrowing/cohorts, priority classes + preemption, showback via labels.

**20. Pending Pod: how do you debug in order?**
`describe pod` events → node allocatable vs requested → taints/tolerations → nodeSelector/affinity → quota → device plugin Pod healthy → driver validator passed → autoscaler decision logs.

**21. How do you make the scheduler pack GPU nodes?**
`NodeResourcesFit` scoring strategy `MostAllocated` (or `RequestedToCapacityRatio`), so Karpenter/Cluster Autoscaler can remove emptied nodes.

---

## D. DRA

**22. What problem does DRA solve that device plugins can't?**
Plugins only advertise counts at node start. DRA lets Pods claim devices by *attributes* (memory, model, topology), supports sharing a claim, dynamic partitioning, and multi-device placement decided by the scheduler.

**23. Name the DRA objects.**
`DeviceClass`, `ResourceSlice` (driver publishes inventory), `ResourceClaim`, `ResourceClaimTemplate`, plus `spec.resourceClaims` on the Pod. Selection via CEL.

**24. What's the DRA status?**
Core is GA since Kubernetes 1.34 (`resource.k8s.io/v1`); extended-resource support (old `nvidia.com/gpu` syntax served by DRA) GA in 1.37. NVIDIA's DRA driver is in kubernetes-sigs. Check managed-cluster version support before adopting.

**25. How would you migrate from device plugin to DRA?**
Run both on separate node pools, enable DRA driver on a canary pool, use extended-resource-over-DRA so manifests don't change, move workloads pool by pool, then retire the plugin.

---

## E. Training at scale

**26. Why does multi-node training slow down or hang?**
Network (NCCL falling back to TCP), bad placement across AZs/spines, stragglers, partial gang, `/dev/shm` too small, one flaky GPU. First step: `NCCL_DEBUG=INFO`, check EFA/IB device visibility, and per-rank step times.

**27. What is NCCL and GPUDirect RDMA?**
NCCL = NVIDIA's collective communication library (all-reduce etc.). GPUDirect RDMA lets the NIC DMA straight into GPU memory, skipping CPU copies.

**28. How do you make training resilient?**
Frequent async checkpoints to FSx/S3, elastic launchers (torchrun), auto-cordon on XID errors, spare nodes, Kueue requeue on failure, idempotent job config.

**29. On EKS, how does EFA fit in?**
EFA-enabled instances (p4d/p5…), `vpc.amazonaws.com/efa` device plugin, `aws-ofi-nccl` for NCCL, security group allowing all traffic within the group, cluster placement group for latency.

---

## F. Inference

**30. How do you serve an LLM on Kubernetes?**
vLLM or Triton in a Deployment/LeaderWorkerSet, one model replica per GPU group, weights from cached volume, `startupProbe` for long load, readiness after warm-up, Service/Gateway in front, autoscale on queue depth or concurrency via KEDA, Karpenter for nodes.

**31. How do you size GPU memory for a model?**
Weights (params × bytes) + KV cache (∝ batch × context × layers × heads) + overhead. 70B FP16 ≈ 140 GB weights → needs ≥ 2×80 GB with tensor parallelism, or quantise to FP8/INT4 to fit fewer GPUs.

**32. Why not autoscale on GPU utilisation?**
It's a lagging, saturating signal and doesn't tell you queue pressure. Use in-flight requests, queue time, time-to-first-token, tokens/s.

**33. How do you cut cold-start time?**
Pre-pulled/cached images, weights on fast shared storage or baked in, warm floor of replicas, smaller quantised models, snapshot/lazy-load techniques, avoid scale-to-zero on user-facing paths.

**34. How do you protect GPUs from overload at the API layer?**
Gateway with bulkhead/concurrency limit, request queue with timeout, token-based rate limits, circuit breaker, load shedding (429/503 with Retry-After). (Spring Boot gateway sample in this repo.)

---

## G. Reliability, security, cost

**35. How do you detect a bad GPU?**
DCGM health + XID events (79, 48 fatal), node problem detector, failing validator, dcgmi diag; automation cordons+drains and opens a replace ticket.

**36. Is time-slicing safe for multi-tenant?**
No. No memory or fault isolation. Use MIG or dedicated nodes for tenants who don't trust each other.

**37. What's the security risk with `NVIDIA_VISIBLE_DEVICES`?**
If the runtime honours it from unprivileged containers, a malicious image can request any GPU on the node. Configure the plugin/toolkit to ignore it and rely on device-plugin/CDI allocation.

**38. How do you control GPU cost?**
Right-size family, MIG/time-slice small workloads, Spot for checkpointed training, Capacity Blocks/reservations for big runs, Karpenter consolidation, idle reaper, quotas, showback by team, quantisation.

---

## H. System-design prompts

### H1. "Design a multi-tenant GPU platform on EKS for training and inference."
Walk the board in this order (draw it):
1. **Requirements:** tenants, models, SLOs (TTFT, p99), batch vs online, compliance.
2. **Cluster layout:** separate NodePools — inference (g6e/p5 small slices, on-demand), training (p5/p4d + EFA, capacity blocks), dev (time-sliced, spot). Taints per pool.
3. **Node stack:** accelerated AMI → GPU Operator (driver off, toolkit/plugin/GFD/DCGM on) → MIG on inference H100s if tenants need isolation.
4. **Scheduling:** Kueue ClusterQueues per team with cohorts and borrowing; PriorityClasses (inference > training > dev); gang via Kueue/JobSet.
5. **Networking:** EFA + placement group for training; private endpoints; NetworkPolicy per tenant.
6. **Storage:** FSx for Lustre (datasets, checkpoints), S3 for artifacts, model cache PVC.
7. **Serving:** vLLM/Triton behind a gateway (auth, rate limit, bulkhead) → KServe or plain Deployments; KEDA on queue depth.
8. **Observability:** DCGM → Prometheus → Grafana; XID alerts; cost per team (OpenCost).
9. **Security/governance:** quotas, PSS, signed images, audit, key management, data residency.
10. **Failure modes:** bad GPU, spot interruption, capacity unavailable → fallback instance families / queue.

### H2. "Design an LLM inference service for 1000 RPS."
- Clarify tokens in/out, model, latency target.
- Throughput per GPU (continuous batching) → replicas needed → GPUs → instance count.
- Multi-GPU tensor parallel if model > one GPU; LeaderWorkerSet.
- Gateway: concurrency caps, priority queues, streaming (SSE), idempotency/retries, tenant limits.
- Autoscale on queue depth; warm pool; node provisioning time budget.
- Rollouts: canary by model version, shadow traffic, rollback on TTFT regression.

### H3. "Your training job is 40 % slower than last week. Go."
Compare job configs → check node placement and NIC (EFA visible?) → per-rank step time for stragglers → GPU clocks/thermal throttling (DCGM) → dataloader/storage throughput → NCCL logs → driver/CUDA/NCCL version changes → noisy neighbour on shared node.

---

## I. Tie to your own background (tailor as you like)

Use *what you actually did*; don't oversell.
- **EKS platform governance** → how you'd enforce quotas, PSS, tenancy, and golden node pools for GPU.
- **Equinix Metal provisioning (Tinkerbell, Cluster API, Crossplane)** → bare-metal GPU fleets: provisioning, lifecycle, firmware/driver drift, declarative cluster creation.
- **Customer-facing APIs at scale (millions of requests/day)** → gateway design in front of GPU inference: versioning, deprecation, SLOs, backpressure.
- **GCC/IM8 compliance architecture** → how GPU platforms satisfy audit, isolation, data-residency controls.
- **Principal-level framing:** talk trade-offs (cost vs latency vs isolation), what you'd measure, and what you'd *not* build (buy vs build for scheduler/serving layers).

---

## J. Questions to ask them

- What GPU generations and instance mix do you run, and how do you get capacity?
- Device plugin or DRA today? What blocks migration?
- How do you measure GPU efficiency (not just utilisation)?
- Who owns the platform vs the model teams? How are quotas negotiated?
- What's your worst GPU incident, and what changed afterwards?
