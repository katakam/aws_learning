# One-page revision sheet

## GPU on K8s in 10 lines
1. GPU = extended resource `nvidia.com/gpu`: **integers, request == limit, no overcommit**.
2. Device plugin: `Register` → `ListAndWatch` → `Allocate`. Unhealthy GPU leaves allocatable; running Pods survive.
3. Stack: hardware → **host driver** → container toolkit/CDI → runtime → plugin → kubelet → scheduler.
4. Driver on host, CUDA toolkit in image. Host driver must support the image's CUDA.
5. GPU Operator = NFD + driver + toolkit + plugin + GFD + DCGM + MIG manager + validator via `ClusterPolicy`.
6. Taint GPU nodes; select model with GFD labels; quota with `requests.nvidia.com/gpu`.
7. Sharing: **time-slicing** (no isolation) · **MPS** (concurrent, weak isolation) · **MIG** (hardware isolation, static) · exclusive.
8. **DRA** (GA 1.34): claim by attributes (`DeviceClass`, `ResourceSlice`, `ResourceClaim`, CEL). Extended-resource DRA GA 1.37.
9. Training: **gang scheduling** (Kueue/Volcano/JobSet), NCCL, EFA/IB, `/dev/shm`, checkpoints.
10. Inference: vLLM/Triton, startupProbe, cached weights, **scale on queue depth**, keep warm floor.

## Analogies
| Concept | Everyday picture |
|---|---|
| Device plugin | Taxi dispatcher registering cabs with the control room |
| Time-slicing | Auto-rickshaw, passengers take turns |
| MIG | Separate flats with own walls and meter |
| MPS | Shared kitchen, several cooks at once |
| Gang scheduling | Wedding party: seat everyone or nobody |
| DRA | "SUV with AC within 2 km" instead of "any 1 taxi" |
| GPU Operator | Society maintenance office |
| Bulkhead | Lift with a weight limit |
| Spring auto-config | Maggi masala packet: defaults unless you bring your own |

## Debug order for a Pending GPU Pod
`describe pod` → node allocatable → taints/tolerations → nodeSelector/affinity → quota → plugin Pod healthy → driver validator → autoscaler logs.

## Numbers
- 7 MIG slices max (A100/H100 80 GB). FP16 = 2 B/param (70B ≈ 140 GB).
- XID: 79 off the bus, 48 double-bit ECC (replace); 31 page fault (app); 13 engine exception.
- DCGM: `GPU_UTIL`, `FB_USED`, `POWER_USAGE`, `PROF_PIPE_TENSOR_ACTIVE`, `XID_ERRORS`.

## Spring Boot in 10 lines
1. Boot = Spring + starters + auto-config + embedded server + Actuator.
2. `@SpringBootApplication` = Configuration + EnableAutoConfiguration + ComponentScan.
3. Auto-config via `AutoConfiguration.imports` + conditions; your bean wins (`@ConditionalOnMissingBean`). Debug: `--debug`.
4. `@Transactional` is a proxy: self-invocation and non-public methods bypass it.
5. MVC + virtual threads for blocking stacks; WebFlux for streaming I/O.
6. Liveness (restart me) ≠ readiness (send traffic). No downstream checks in liveness.
7. K8s: graceful shutdown, preStop sleep, `MaxRAMPercentage≈70`, memory request == limit.
8. In front of GPUs: timeouts, **bulkhead**, shed with 429 + Retry-After, cancel on disconnect.
9. Boot 4: Framework 7, Jackson 3, modular starters (`webmvc`), API versioning, `@Retryable`/`@ConcurrencyLimit` in core, `@MockitoBean`.
10. Observe: Micrometer metrics (TTFT, queue wait, tokens), tracing, separate management port.
