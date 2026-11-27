# Associate Director, Product Engineering: private-cloud GPU/AI platform

High-level interview prep. Stack in the role: **Java, Spring Boot, Kubernetes, Kafka, SPA frontend, GPU/AI workloads, private cloud**. You lead through team leads, so expect 60 % leadership/delivery, 40 % architecture.

**NOT:** a senior engineer interview where you out-code the panel.
**IS:** a test of whether you can set direction, protect delivery and stability, grow leads, and still smell a bad design in 2 minutes.

**Analogy:** you are the head chef of a restaurant chain's central kitchen. You don't cook every dish; you set the menu standard, keep the kitchen running at 8 pm on Saturday, grow the sous-chefs, and taste anything before it leaves.

---

## 1. Positioning (30-second opener)

Structure: *scope → how you lead → what you deliver → why this platform.*
- Scope: platforms/APIs at scale (numbers you can defend), Kubernetes and cloud-native, regulated environments.
- Leadership: set standards, review designs, grow leads, run delivery and incidents.
- Outcome: reliability, delivery predictability, security/compliance baked in.
- Why here: a multi-tenant GPU/AI platform is where platform engineering, scarce hardware economics and enterprise delivery meet.

**Be honest about the gap.** The JD says "managed multiple engineering teams". If your experience is technical leadership and influence across teams rather than line management, say exactly that, then show leadership evidence: standards you set, leads you mentored, cross-team delivery you drove, decisions you owned. Do not inflate headcount. Interviewers probe this with "who reported to you, who did their reviews?"

---

## 2. Leadership and people (most likely, high weight)

**Q1. How do you lead through team leads?**
Set clear outcomes and guardrails, let leads own the how. Weekly 1:1s with leads, monthly skip-levels, shared dashboards (delivery, quality, incidents). I coach leads to make decisions and escalate early, not to ask permission. *Analogy:* head chef sets quality and timing; sous-chefs run their stations.

**Q2. A team lead is underperforming. What do you do?**
Get facts (outcomes, not impressions) → private feedback with specific examples → agree a short plan (30-60 days) with support → check progress → decide (role change, move on) fairly. Protect the team's delivery meanwhile.

**Q3. How do you grow engineers and leads?**
Individual growth plans, stretch assignments, design-review mentoring, rotating tech-lead roles, promotion criteria written down, sponsor visible work. Measure by who can run without me.

**Q4. How do you build engineering culture/standards?**
Few, clear, automated standards: definition of done, code review rules, CI gates, ADRs for big decisions, blameless post-incident reviews. Lead by doing: attend reviews, follow the rules myself.

**Q5. Two leads disagree on a technical direction.**
Get both to write the trade-offs against agreed criteria (risk, cost, time, operability), time-box a decision, I decide if no consensus ("disagree and commit"), record in an ADR, revisit with data if wrong.

**Q6. How do you handle low morale / attrition?**
Listen first (skip-levels, anonymous pulse), find root causes (on-call load, unclear priorities, tech debt), fix what I can, be transparent about what I can't. Retention is mostly manager quality, workload and growth.

**Q7. How do you hire?**
Define the role outcomes, structured interviews with a rubric, include a practical design discussion, hire for learning ability and ownership, diversify the loop, close fast.

**Q8. What does "technical credibility" mean for you at director level?**
I can review a design, ask the question that exposes the risk, and judge trade-offs. I delegate depth but never lose touch: I read design docs, join incident reviews, and occasionally pair on a hard problem.

---

## 3. Delivery and execution

**Q9. How do you keep multiple teams delivering on time?**
Quarterly roadmap tied to business outcomes, milestones with owners, weekly risk/dependency review, visible dependency board, limit work in progress, cut scope not quality. Escalate slips early with options.

**Q10. A milestone will slip. What do you do?**
Quantify the slip and cause → options (descope, add capacity, move date, parallelise) with trade-offs → agree with product/stakeholders early → adjust plan → protect quality gates. Never hide it.

**Q11. How do you balance feature work vs tech debt vs reliability?**
Reserve a fixed capacity (e.g., 20 %) for debt/reliability; use error budgets: when SLOs are burning, reliability work wins. Make debt visible with business impact.

**Q12. How do you run release management?**
Trunk-based or short-lived branches, automated CI gates (tests, security scans), progressive delivery (canary / blue-green), feature flags, change calendar for risky changes, rollback plan, post-release verification. Release governance should be light but auditable.

**Q13. Which metrics do you track?**
- Delivery: DORA (deployment frequency, lead time, change failure rate, time to restore).
- Quality: escaped defects, test coverage trend, review turnaround.
- Reliability: SLO attainment, incident count/MTTR.
- People: attrition, engagement pulse, on-call load.
- Platform: tenant onboarding time, adoption, GPU utilisation. Avoid vanity metrics (lines of code, story points as performance).

**Q14. Agile at scale in a matrixed org?**
Shared roadmap, team-level Scrum/Kanban, joint planning per quarter, clear ownership of components (who is on call for what), working agreements with ops/security/product.

---

## 4. Architecture and platform (high level)

**Q15. Sketch a private-cloud GPU/AI platform.**
Layers (see diagram `07-ai-platform-private-cloud.html`):
1. Infrastructure: GPU servers, high-speed network (RoCE/InfiniBand), storage, DC power/cooling.
2. Cloud foundation: bare-metal provisioning, Kubernetes clusters, identity, networking, secrets.
3. GPU layer: drivers/Operator, device plugin or DRA, MIG/time-slicing, scheduling (Kueue), observability (DCGM).
4. Platform services (Java/Spring Boot microservices): tenant & identity, quota, catalogue, provisioning orchestrator, billing/metering, job and notebook service, model serving/inference gateway.
5. Event backbone: Kafka for lifecycle events, metering, audit.
6. Experience: SPA portal + APIs/CLI for self-service.
7. Cross-cutting: security, observability, FinOps, SRE.

**Q16. How do you design multi-tenancy?**
Tenant = identity + namespace/cluster + quota + network policy + data boundary. Soft isolation (namespaces, quotas, RBAC) for trusted teams; hard isolation (MIG, dedicated nodes/clusters, separate VLANs/VRFs, encrypted storage) for external customers. Noisy-neighbour control via quotas and priority.

**Q17. Build vs buy vs open source?**
Buy/adopt commodity (Kubernetes, Kafka, GPU Operator, Kueue, vLLM/Triton). Build the differentiator: tenant experience, provisioning/orchestration, metering/billing, integration with the company's own network and OSS/BSS. Criteria: differentiation, time to market, run cost, vendor lock-in, skills.

**Q18. How do you design for scalability and reliability?**
Stateless services behind gateways, horizontal scaling, backpressure and bulkheads, async via Kafka, multi-AZ/DC where available, graceful degradation, SLOs per service, capacity planning for GPUs (scarce, long lead time).

**Q19. How do you handle architecture governance without slowing teams?**
Lightweight design review for significant changes, ADRs, reference architectures and golden paths, guardrails in CI (policy as code), architecture office hours. Say yes to speed by making the right way the easy way.

**Q20. How would you meter and bill GPU usage?**
Emit usage events (allocation start/stop, GPU-seconds, tokens for inference) from the platform to Kafka; aggregate with idempotent consumers; reconcile with DCGM data; expose to billing; keep an audit trail. Design for late/duplicate events.

---

## 5. Java and Spring Boot (leader-level)

Know it well enough to challenge a design; deep notes in `03-spring-boot.md`.
- **Q21. What do you check in a Spring Boot design review?** Timeouts and retries on every outbound call, transaction boundaries (no remote calls inside DB transactions), pagination, N+1, idempotency, config externalised, health probes, metrics, graceful shutdown, security (JWT, method security), thread/connection pool sizing.
- **Q22. Why Spring Boot for platform services?** Mature ecosystem, strong hiring pool, Actuator/Micrometer, Kubernetes friendly, easy testing. Trade-off: memory/startup vs Go/Rust; mitigate with virtual threads, AOT/CDS, right-sized pods.
- **Q23. Upgrade strategy (e.g., Boot 3 → 4)?** Stay on supported lines, upgrade in small steps, automate with OpenRewrite, strong test suite, canary rollout. Boot 3.5 OSS support ended 30 Jun 2026, so older lines carry security risk.
- **Q24. Common production failures?** Pool exhaustion, missing timeouts, unbounded queues, blocking calls on event loops, memory off-heap OOM in containers, chatty services.

---

## 6. Kafka (event-driven integration)

**Analogy:** a railway network. Topic = a line, partition = a track on that line, producer = station sending trains, consumer group = a set of porters sharing the tracks, offset = how far a porter has unloaded.

Essentials:
- **Topic → partitions.** Order is guaranteed **only within a partition**. Key decides the partition (same key, same order).
- **Consumer group:** each partition is read by one consumer in the group; more consumers than partitions = idle consumers. Rebalances pause consumption.
- **Offsets** committed by consumers; **lag** = latest offset minus committed.
- **Delivery semantics:** at-most-once, at-least-once (default practical choice), exactly-once (idempotent producer + transactions, within Kafka). Design **consumers to be idempotent**.
- **Durability:** replication factor 3, `min.insync.replicas=2`, producer `acks=all`.
- **Retention vs compaction:** time/size-based deletion, or keep latest value per key (compacted topics for state).
- **KRaft** replaces ZooKeeper in modern Kafka.

Likely questions:
- **Q25. How do you avoid losing or duplicating messages?** `acks=all`, idempotent producer, retries, consumer commits after processing, idempotent handlers (dedupe key), **outbox pattern** for DB + Kafka consistency.
- **Q26. A consumer falls behind. What do you do?** Check lag per partition → slow handler? downstream timeout? hot partition (skewed key)? Scale consumers up to partition count, fix the handler, batch/parallelise, increase partitions (re-keying implications), alert on lag growth.
- **Q27. Message that always fails?** Bounded retries with backoff, then **dead-letter topic** with context, alert, replay tool. Never block the partition forever.
- **Q28. Schema evolution?** Schema Registry (Avro/Protobuf/JSON Schema), backward/forward compatibility rules, additive changes, versioned topics for breaking changes.
- **Q29. Ordering across entities?** Key by the entity ID so all its events land on one partition; accept no global order.
- **Q30. Kafka vs REST between services?** REST/gRPC for request-response needing an immediate answer; Kafka for decoupling, fan-out, audit, spikes, and replay. Avoid turning everything into events: harder debugging and eventual consistency.
- **Q31. Spring and Kafka?** Spring for Apache Kafka (`@KafkaListener`, error handlers, `DefaultErrorHandler` + DLT), tune `max.poll.interval.ms`, concurrency, manual ack when needed.

---

## 7. Kubernetes and GPU (high level)

Details in `01` and `02`. Directors get asked the *why* and the *risks*:
- **Q32. Why Kubernetes for AI workloads?** Declarative operations, multi-tenancy primitives (namespaces, quotas), ecosystem (Operator, Kueue, KServe, Ray), portability, autoscaling. Cost: complexity, GPU-specific tuning, need for platform skills.
- **Q33. What are the top GPU platform risks?** Capacity/lead time, utilisation (idle GPUs are expensive), noisy neighbours, driver/firmware drift, hardware failures at scale, network fabric misconfig, security isolation, cost visibility.
- **Q34. How do you improve GPU utilisation?** Measure (DCGM), right-size, MIG/time-slicing for small jobs, queueing with fair share and borrowing (Kueue), preemption for low priority, idle reclaim, right instance/GPU per workload, batch inference.
- **Q35. How do you keep the GPU fleet healthy?** Burn-in, health checks (DCGM diag), XID alerting, auto-cordon/drain, spares, firmware/driver upgrade rings, runbooks.
- **Q36. Training vs inference platform needs?** Training: gang scheduling, high-bandwidth fabric, checkpoints, long jobs. Inference: latency SLOs, autoscaling on queue depth, warm capacity, model caching, gateway with rate limits.

---

## 8. Frontend (SPA) at director level

You are not expected to write React/Angular; you are expected to govern it.
- **Q37. SPA architecture considerations?** Component library/design system, state management discipline, API contract first (OpenAPI), auth via OIDC (authorization code + PKCE), lazy-loaded routes, bundle budget, accessibility, i18n, telemetry (errors, web vitals).
- **Q38. Frontend security?** CSP, no tokens in localStorage if avoidable (prefer secure cookies/BFF), XSS hygiene, dependency scanning, CORS configured explicitly.
- **Q39. Monolith SPA vs micro-frontends?** Start with one app and modular boundaries; micro-frontends only when many teams ship independently and the cost of integration is justified.
- **Q40. How do frontend and backend teams collaborate?** Contract-first APIs, mock servers, consumer-driven contract tests, shared definition of done, BFF layer when UI needs differ from domain APIs.

---

## 9. Operations, incidents, security

**Q41. Walk me through a major incident you led.**
Use STAR with this shape: detect → declare severity → assign roles (incident commander, comms, scribe, SMEs) → mitigate first (rollback/failover) → communicate every 30 min → recover → **blameless RCA** within days → actions with owners and dates → verify they land.

**Q42. How do you set SLOs?**
Choose user-facing SLIs (availability, latency, successful job start), set targets with the business, error budget policy (freeze risky releases when budget is gone), review quarterly.

**Q43. What does operational readiness mean before go-live?**
Runbooks, dashboards and alerts tested, on-call rota trained, capacity and load tested, DR/backup restore tested, security review, rollback rehearsed, support model agreed.

**Q44. Observability stack?** Metrics (Prometheus/Micrometer), logs (central, structured), traces (OpenTelemetry), DCGM for GPUs, SLO dashboards, alert on symptoms not causes.

**Q45. Security and compliance in a telco/sovereign context?** Data residency, tenant isolation, encryption in transit/at rest, key management, least-privilege RBAC, audit logging, vulnerability management (images, dependencies, drivers), supply-chain controls (signed images, SBOM), regulatory alignment (PDPA, sector rules), pen-tests, security-by-design in the pipeline.

**Q46. DevOps/CI-CD standard?** Pipeline as code, mandatory tests and scans, artifact signing, environment promotion with approvals only where needed, GitOps (Argo CD/Flux) for cluster config, drift detection.

---

## 10. Stakeholders and the matrix

**Q47. How do you manage product, ops, security and architecture when priorities clash?**
Shared goals first, one prioritised backlog, explicit trade-off conversations with data, clear decision rights (RACI), regular forums, and no surprises: share bad news early.

**Q48. Shared platform ownership: who is on call?**
Ownership by service with named teams; clear escalation matrix; platform team owns the platform SLO, tenant teams own their workloads; joint incident reviews.

**Q49. How do you say no to a senior stakeholder?**
Acknowledge the goal, show the cost and the risk with numbers, offer alternatives (phase, descope, different date), escalate with a recommendation if needed. Keep the relationship intact.

**Q50. Vendor management (NVIDIA, OEMs, cloud/software vendors)?**
Clear SLAs, roadmaps and escalation paths, avoid single-vendor lock-in where practical, pilot before commit, regular business reviews, own the integration risk yourself.

---

## 11. Scenario questions (think aloud)

1. **A production outage hits a flagship customer's GPU jobs.** Mitigate, communicate, RCA, compensate if SLA breached, prevent recurrence.
2. **Demand doubles in two quarters but GPUs arrive in six months.** Prioritise by value, quotas/fair share, improve utilisation, burst via partner cloud, set expectations.
3. **Two teams both want to own the scheduler/queueing layer.** Define by product outcome and operating model, not by ego; one owner, clear interfaces.
4. **Security finds a critical CVE in the GPU driver stack.** Risk assess, rolling patch ring (dev → pilot → prod), drain nodes by tenant windows, communicate, verify.
5. **Your best tech lead resigns mid-programme.** Interim lead, knowledge transfer, retention conversations with the team, backfill plan, adjust milestones.
6. **The CEO wants a demo of an AI feature in 4 weeks.** Scope a thin vertical slice, protect production, label risks, no shortcuts that create security debt.

---

## 12. Short on time? Top 15 + 3-day plan

**Most likely questions (in this order):**
1. Tell me about yourself and why this role. (Q in section 1)
2. How have you led teams, and through whom? (Q1, plus the honest-gap note)
3. An underperforming lead or a conflict between leads. (Q2, Q5)
4. A milestone is slipping. (Q10)
5. A major incident you led and the RCA. (Q41)
6. Sketch the GPU/AI platform. (Q15, diagram 07)
7. Multi-tenancy and isolation. (Q16)
8. GPU utilisation, capacity and cost. (Q34, scenario 2)
9. Kafka: duplicates, lag, dead letters, outbox. (Q25-27, diagram 08)
10. Spring Boot design-review checklist. (Q21)
11. Release management, quality, CI/CD. (Q12, Q46)
12. Pushback from product, ops or security. (Q47, Q49)
13. Security and compliance in a sovereign/regulated platform. (Q45)
14. Build vs buy. (Q17)
15. What would you do first in this role? (answer: listen, baseline metrics, fix the worst operational pain, agree priorities with leads)

**3-day plan (about 2 hours a day):**
- **Day 1: your stories.** Write the opener (60 seconds). Prepare 4 STAR stories: leading across teams, an incident with RCA, a standard you got adopted, a hard people or stakeholder moment. Practise Q1-Q5 aloud.
- **Day 2: the platform.** Draw the layers (diagram 07) from memory in 2 minutes. Rehearse Q15-Q20 (design, multi-tenancy, GPU utilisation, metering), then Kafka and the Spring Boot checklist.
- **Day 3: mock and polish.** Do a full 30-minute mock aloud (record it). Tighten answers to 90 seconds each. Prepare 4 questions to ask them. Read the one-page cheatsheet and sleep.

## 13. Your story bank (prepare 6 STAR stories)

Pick real examples; keep numbers honest.
1. Delivered a platform/API at scale under an availability target (what you owned, how it was measured).
2. Led a cross-team technical initiative without direct authority.
3. Handled a production incident and drove RCA to completion.
4. Set or changed an engineering standard and got adoption.
5. Mentored someone who grew; or handled a hard people situation.
6. Made a build-vs-buy or architecture trade-off and lived with the outcome (including something that went wrong and what you changed).

---

## 14. Questions to ask them

- What does success look like in 6 and 12 months?
- How many teams and leads, and where are the biggest delivery or reliability gaps today?
- What is the GPU fleet mix and the utilisation target? Where does capacity planning sit?
- Which parts of the platform are strategic builds vs adopted open source?
- How is the platform split between product, engineering, DevOps/SRE, and security? Who owns on-call?
- What are the biggest customer pain points today (onboarding time, reliability, cost transparency)?

---

## 15. Quick rules for the room

- Lead with outcomes and numbers, then how.
- Say "my team" and "we", but be clear on *your* decisions.
- When unsure of a technical detail, say how you'd find out; never bluff.
- Always close with the people angle: who grew, who owned.
