# Spring Boot — Interview Notes (with a GPU-gateway angle)

> Versions checked Nov 2026: Spring Boot **4.1.x** current (4.0 GA Nov 2025, 4.1.0 Jun 2026), Spring Framework 7, Jakarta EE 11, Java 17 minimum (works up to 25/26). Boot 3.5 reached OSS end-of-life on 30 Jun 2026.

**NOT:** Spring Boot is not a different framework from Spring.
**IS:** Spring + sensible defaults: starters (dependency bundles), auto-configuration (beans created when the classpath/config says so), an embedded server, and production endpoints (Actuator).

**Analogy — Maggi masala packet.** Plain Spring = buy every spice and decide quantities. Boot = the masala packet: just add water (your code), and a decent taste (default config) arrives. You can still add your own spice (override a bean).

---

## 1. How Boot actually starts

`SpringApplication.run(App.class, args)`:
1. Build `Environment` (properties, profiles).
2. Create `ApplicationContext` (servlet or reactive, decided by classpath).
3. **Refresh**: component scan → register bean definitions → auto-config → instantiate singletons → start embedded Tomcat.
4. Run `ApplicationRunner` / `CommandLineRunner`.
5. Publish `ApplicationReadyEvent`; readiness goes `ACCEPTING_TRAFFIC`.

`@SpringBootApplication` = `@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`.

### Auto-configuration
- Candidate classes are listed in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` inside each jar.
- Each is guarded by conditions: `@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnProperty`, …
- **`@ConditionalOnMissingBean` is why your own bean wins** — Boot backs off.
- Debug: run with `--debug` → **conditions evaluation report** (what matched, what didn't). Or `/actuator/conditions`.
- **Boot 4:** the one giant autoconfigure jar is split into many focused modules (70+ jars), so you pull only what you use; starters changed accordingly.

### Configuration precedence (high → low, simplified)
Command-line args → OS env vars (`SPRING_DATASOURCE_URL`) → `application-{profile}.yml` → `application.yml` → `@PropertySource` → defaults. Relaxed binding: `my.gpu-endpoint` = `MY_GPU_ENDPOINT`.
Use `@ConfigurationProperties` (typed, validated) over scattered `@Value`.

---

## 2. Beans and DI

- Constructor injection (immutable, testable). Field injection is discouraged.
- Scopes: singleton (default), prototype, request, session.
- Lifecycle: instantiate → inject → `@PostConstruct` / `InitializingBean` → ready → `@PreDestroy`.
- **Proxies**: `@Transactional`, `@Async`, `@Cacheable`, `@Retryable` work through proxies.
  - Pitfall 1: **self-invocation** (`this.method()`) bypasses the proxy → no transaction.
  - Pitfall 2: only `public` methods on proxied beans are advised in typical setups.
  - Pitfall 3: `@Transactional` rolls back on unchecked exceptions by default, **not** checked ones (`rollbackFor`).
- Circular dependencies: constructor cycles fail fast; fix design (extract a third bean), don't enable the allow-circular flag.

---

## 3. Web layer

### MVC vs WebFlux
- **MVC (servlet):** thread-per-request on Tomcat. Simple, blocking-friendly (JDBC, JPA).
- **WebFlux:** event loop (Netty), non-blocking, needs reactive drivers end to end. Wins for high-concurrency streaming I/O (e.g., proxying token streams).
- **Virtual threads** (`spring.threads.virtual.enabled=true`, Java 21+): MVC with blocking code scales like async without rewriting. Watch out for pinning (synchronized blocks around blocking I/O), connection-pool limits (DB pool becomes the bottleneck), and thread-local-heavy libs.

### Request lifecycle (MVC)
Client → Tomcat connector → **Filter chain** (Spring Security, logging) → **DispatcherServlet** → HandlerMapping → **Interceptors** (`preHandle`) → argument resolvers (`@RequestBody` via Jackson) → Controller → Service → Repository → return value handler → message converter → response.
Errors: `@RestControllerAdvice` + `@ExceptionHandler`, `ProblemDetail` (RFC 9457).

> Animated: `diagrams/05-springboot-request-lifecycle.html`

### Boot 4 / Framework 7 features worth naming
- **API versioning** built into request mapping (`version` attribute on `@GetMapping` etc.).
- **Declarative HTTP service clients** (`@HttpExchange` interfaces, easier registration).
- **Jackson 3** default (`tools.jackson` packages; Jackson 2 compat module for migration).
- **JSpecify null-safety** across the portfolio.
- **Resilience in core:** `@Retryable`, `@ConcurrencyLimit` now in Spring Framework (no Spring Retry dependency).
- Hibernate 7, Tomcat 11, Spring Security 7 (changed defaults — test your REST security on upgrade).
- **Starters renamed / split:** `spring-boot-starter-web` → `spring-boot-starter-webmvc`; `RestClient` and `WebClient` have their own starters (`-restclient`, `-webclient`); Flyway/Liquibase need their starters; each technology gets a matching `-test` starter. "Classic" starters exist as a deprecated stopgap.
- **Test change:** `@MockBean` / `@SpyBean` removed → use `@MockitoBean` / `@MockitoSpyBean` from Spring Test.
- Everything deprecated in 3.x is gone; Boot 3.5 is the last 3.x line (OSS support ended 30 Jun 2026).

---

## 4. Data access

- **Spring Data JPA**: repositories, derived queries, `@Query`, projections, pagination.
- **N+1 problem:** lazy collection loaded per row → use `join fetch`, `@EntityGraph`, batch size, or DTO projections.
- **Open-Session-In-View** (`spring.jpa.open-in-view`) is on by default — it keeps a DB connection through view rendering; most teams turn it **off**.
- **HikariCP** pool sizing: start with small (`cores*2 + spindles` style rule), measure; with virtual threads, *the pool* is the throttle.
- Transactions: propagation (`REQUIRED`, `REQUIRES_NEW`), isolation, read-only hint, keep them short, never call remote GPU/LLM APIs inside a DB transaction.
- Migrations: Flyway/Liquibase, not `ddl-auto=update` in prod.

---

## 5. Security (Spring Security 6/7)

- Everything is a **`SecurityFilterChain`** bean (no more `WebSecurityConfigurerAdapter`).
- Resource server: `spring-boot-starter-oauth2-resource-server`, validate JWT via issuer/JWKS; map scopes → authorities.
- Method security: `@PreAuthorize("hasAuthority('SCOPE_infer')")`.
- CSRF: needed for browser session apps; typically disabled for stateless token APIs.
- Secrets: never in `application.yml` in git → env/Secret/CSI driver/Vault.

---

## 6. Observability (Actuator + Micrometer)

- Endpoints: `/actuator/health`, `/info`, `/metrics`, `/prometheus` (with registry), `/env`, `/conditions`, `/loggers`, `/threaddump`.
- **Expose minimally** (`management.endpoints.web.exposure.include=health,prometheus`), put on a **separate management port**, secure the rest.
- Health groups for Kubernetes: `management.endpoint.health.probes.enabled=true` → `/actuator/health/liveness` and `/readiness` (auto-enabled when Boot detects Kubernetes).
- **Liveness = "restart me if false"** (internal deadlock). **Readiness = "don't send traffic"** (dependency down, warming up, overloaded). Don't put downstream checks (DB, GPU backend) in *liveness*, or an outage causes restart storms.
- Micrometer: `Timer`, `Counter`, `Gauge`; add tags carefully (cardinality!). For a GPU gateway: `inference.ttft`, `inference.tokens.out`, `inference.queue.wait`, `inference.rejected`.
- Tracing: Micrometer Tracing + OpenTelemetry; propagate `traceparent` to the model server.

---

## 7. Testing

- `@SpringBootTest` (full context, slow) vs **slices**: `@WebMvcTest` (controllers), `@DataJpaTest`, `@JsonTest`, `@RestClientTest`.
- **Testcontainers** with `@ServiceConnection` wires real Postgres/Kafka without manual properties.
- `MockMvc` / `RestTestClient` (new in Framework 7) for HTTP assertions; `WireMock`/`MockWebServer` for fake model servers.
- Test the failure paths: timeouts, 429s, slow streams.

---

## 8. Resilience patterns (critical in front of GPUs)

GPU backends are **expensive, slow, and finite**. The gateway must protect them and the callers.

- **Timeouts everywhere** (connect, read). LLM read timeouts are long; set per-endpoint.
- **Bulkhead / concurrency limit** — cap in-flight requests per replica to what the GPU can batch. (`@ConcurrencyLimit` in Framework 7, or Resilience4j `Bulkhead`, or a `Semaphore`.)
- **Retry only idempotent calls**, with exponential backoff + jitter; never retry a request that may have already consumed GPU time unless safe.
- **Circuit breaker** on backend pool health.
- **Load shedding:** return `429`/`503` + `Retry-After` instead of queueing forever.
- **Streaming:** Server-Sent Events (`SseEmitter` for MVC, `Flux<ServerSentEvent>` in WebFlux); cancel upstream when the client disconnects, otherwise the GPU keeps generating for nobody.
- **Idempotency keys** for expensive POSTs.

---

## 9. Running Spring Boot on Kubernetes

Config that matters:
- **Probes:** `startupProbe` (slow start), `readinessProbe` → `/actuator/health/readiness`, `livenessProbe` → `/actuator/health/liveness`.
- **Graceful shutdown:** `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase=30s`; Pod `terminationGracePeriodSeconds` > that; `preStop: sleep 5-10` so endpoints are removed before SIGTERM handling.
- **JVM in containers:** container-aware by default; set `-XX:MaxRAMPercentage=70..75` (leave room for metaspace, threads, direct buffers). Memory *limit* == *request* for predictable OOM behaviour. Be careful with tiny CPU limits (throttling hurts GC and startup).
- **Image:** `./mvnw spring-boot:build-image` (Buildpacks) or layered jar Dockerfile; run as non-root, read-only root FS.
- **Startup speed:** AOT + CDS (Class Data Sharing); **GraalVM native image** for very fast start / low memory (trade-offs: longer build, reflection config, fewer dynamic features).
- **Config:** ConfigMap/Secret as env or mounted files; optional `spring.config.import=configtree:/etc/secrets/`.
- **HPA:** CPU is a poor signal for an I/O-bound gateway — scale on in-flight requests / custom metrics (KEDA).

---

## 10. Gateway in front of GPU model servers

See `springboot-gpu-gateway/`. What it demonstrates:
- Typed config for backend URL, timeouts, max concurrency.
- `RestClient` call to an **OpenAI-compatible** endpoint (vLLM serves `/v1/chat/completions`).
- Bulkhead via `Semaphore` with timed acquire → `429` when saturated.
- Micrometer timer for end-to-end latency, counter for rejections.
- Health indicator that reports backend readiness (used in *readiness*, not *liveness*).

> Not compiled in this environment (no Maven here) — treat as a reference skeleton and build it locally with `./mvnw verify`.

Spring AI note: `ChatClient` + OpenAI-compatible `base-url` can also front vLLM; fine for prototypes, but a hand-rolled gateway gives you finer control over queueing, cancellation and token-level metrics.

---

## 11. Interview Q&A

**1. What does `@SpringBootApplication` do?**
Combines `@Configuration`, `@EnableAutoConfiguration`, `@ComponentScan`. Scans from the main class's package down.

**2. How does auto-configuration decide what to create?**
Reads the `AutoConfiguration.imports` list from jars; each class is gated by conditions (class present, bean missing, property set). Your bean overrides because of `@ConditionalOnMissingBean`.

**3. How do you find out why a bean was or wasn't created?**
`--debug` conditions report or `/actuator/conditions`.

**4. Starter vs auto-configuration?**
Starter = dependency bundle (POM). Auto-configuration = the code that wires beans when those dependencies are present. In Boot 4 these are more modular.

**5. `@Component` vs `@Bean`?**
`@Component` (and stereotypes) is class-level, found by scanning. `@Bean` is a factory method in a `@Configuration`, for third-party classes or conditional/complex construction.

**6. Why did my `@Transactional` not work?**
Self-invocation, non-public method, bean not Spring-managed (`new`), checked exception without `rollbackFor`, wrong `@Transactional` import, or async boundary (different thread).

**7. Explain the request flow in Spring MVC.**
Filter chain → DispatcherServlet → HandlerMapping → interceptors → controller → converters → response. (Draw it.)

**8. MVC vs WebFlux vs virtual threads — choose?**
Blocking stack (JPA/JDBC) → MVC + virtual threads. Streaming/many idle connections with reactive clients → WebFlux. Don't mix blocking calls into WebFlux event loops.

**9. Liveness vs readiness?**
Liveness = process healthy (restart if not). Readiness = can serve traffic now (remove from Service if not). Keep dependency checks out of liveness.

**10. How do you do zero-downtime deploys on Kubernetes?**
Readiness probe, rolling update (`maxUnavailable: 0`), `preStop` sleep, graceful shutdown in Boot, PodDisruptionBudget, enough grace period for in-flight (especially long streams).

**11. How do you externalise config and secrets?**
Env vars/ConfigMap for config, Secrets (or CSI/Vault) for credentials, profiles for environment differences, `@ConfigurationProperties` validated with `@Validated`.

**12. How do you handle high load on a downstream that is slow (GPU)?**
Timeouts, bulkhead, bounded queue, circuit breaker, load shedding with 429/Retry-After, cancel on client disconnect, autoscale on backlog. Never unbounded thread/queue growth.

**13. How would you stream LLM tokens to a client?**
SSE: MVC `SseEmitter` (with virtual threads) or WebFlux `Flux<ServerSentEvent>`. Propagate cancellation upstream; flush per token/chunk; set proxy buffering off at ingress.

**14. What is the N+1 problem and fix?**
One query for parents + N for children. Fix with fetch joins, entity graphs, batch fetching, or DTO projection.

**15. How do you secure a stateless REST API?**
OAuth2 resource server with JWT, `SecurityFilterChain`, method security, CSRF off for token APIs, CORS configured explicitly, rate limit at the edge.

**16. What changed in Spring Boot 4?**
Spring Framework 7 / Jakarta EE 11 baseline, modular codebase (smaller jars), Jackson 3 default, JSpecify null-safety, built-in API versioning, declarative HTTP clients, core retry/concurrency-limit annotations, Hibernate 7, Tomcat 11, Spring Security 7 default changes.

**17. How do you make startup faster in containers?**
Lazy init selectively, trim dependencies/auto-configs, AOT + CDS, layered image, or GraalVM native for extreme cases. Measure with startup actuator (`BufferingApplicationStartup`).

**18. JVM memory settings in Kubernetes?**
Use `MaxRAMPercentage` (≈70-75 %), request == limit, watch off-heap (direct buffers, metaspace, threads), enable GC logging/JFR when diagnosing OOMKilled.

**19. How do you test a controller vs the whole app?**
`@WebMvcTest` with mocked services for controller slice; `@SpringBootTest` + Testcontainers for integration; contract tests for downstream APIs.

**20. How would you design the gateway for an LLM serving cluster?**
AuthN/Z → tenant rate limit (tokens) → bulkhead/queue → route to model backend (by model/version) → stream response → metrics (TTFT, tokens/s, queue wait) → cancel propagation → retries only if safe → backend health feeds readiness.

---

## 12. Sound-bite cheat sheet

- Boot = Spring + starters + auto-config + embedded server + Actuator.
- Your bean beats auto-config (`@ConditionalOnMissingBean`).
- `@Transactional` = proxy → self-invocation breaks it.
- Liveness ≠ readiness; no downstream checks in liveness.
- Protect the GPU: timeout, bulkhead, shed, cancel.
- Virtual threads fix blocking scale, not pool limits.
