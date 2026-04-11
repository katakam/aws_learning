# aws_learning
### Scenario 1: Domain 1 — Design Solutions for Organizational Complexity

A financial services enterprise operates 40 AWS accounts under AWS Organizations. The root has a
**deny-list SCP** blocking `ec2:RunInstances` for instance types larger than `c5.xlarge` across
all OUs. A newly acquired subsidiary's account is onboarded directly under the root. The subsidiary
runs a legacy risk-modelling workload on `c5.4xlarge` instances and cannot be refactored for 6
months. The CISO requires that the root SCP remains unchanged, the subsidiary account must rejoin
the Production OU after the transition, and no IAM policy changes in the management account are
permitted.

**Question:** Which approach satisfies ALL constraints — preserving the root SCP, meeting the
subsidiary's instance-size requirement, and requiring the least ongoing operational overhead?

- [ ] **A)** Move the subsidiary account under the root temporarily. Create an inline IAM
  permission boundary on the subsidiary's EC2 roles allowing `c5.4xlarge`. Remove the permission
  boundary after 6 months.
- [ ] **B)** Create a temporary OU named `Onboarding`. Attach an SCP to `Onboarding` that
  explicitly **allows** `ec2:RunInstances` for `c5.4xlarge`. Move the subsidiary account into
  `Onboarding`. After 6 months, move it to Production OU.
- [ ] **C)** Create a temporary OU named `Onboarding`. Attach an SCP to `Onboarding` that
  **denies** `ec2:RunInstances` for all instance types **except** `c5.4xlarge` and below. Move
  the subsidiary into `Onboarding`.
- [ ] **D)** Modify the root SCP to add a condition key `aws:RequestedRegion` scoped to the
  subsidiary's account ID, permitting `c5.4xlarge` only in `us-east-1`.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Create a temporary `Onboarding` OU with an explicit Allow SCP
  for the required instance type, place the subsidiary account there, then migrate to Production
  OU after the freeze period.

* **Why it succeeds:** SCPs follow an **implicit deny by default** model. When an account inherits
  a deny-list SCP at the root, an explicit Allow SCP attached to a child OU does not override the
  root deny unless the deny is structured as a conditional deny. The correct architectural move is
  to place the account in a separate OU whose attached SCP carves out the exception. The AWS
  Organizations SCP evaluation logic is: effective permissions = intersection of all SCPs in the
  OU hierarchy. By placing the account in `Onboarding` directly under root, the `Onboarding` SCP
  must explicitly Allow the carve-out instance type. This satisfies the Well-Architected Security
  Pillar's principle of least privilege with time-bound scope. Moving the account to Production OU
  after 6 months automatically re-applies the Production deny, requiring zero cleanup effort.

* **Why alternatives fail:**
  - **A)** IAM permission boundaries constrain maximum permissions for IAM entities within an
    account but **cannot override an SCP**. SCPs are evaluated before IAM policies in the
    authorization chain. A permission boundary on an EC2 role does nothing if the SCP already
    denies `ec2:RunInstances` at the org level.
  - **C)** Adding a second deny SCP to `Onboarding` compounds the restriction rather than
    relaxing it. SCPs with deny lists are additive across the hierarchy — both the root deny and
    the `Onboarding` deny would apply simultaneously, making the situation worse.
  - **D)** SCPs do not support `aws:PrincipalAccount` as a condition key in a way that
    selectively allows one account while keeping a broader deny for others at the same level.
    Per-account carve-outs must be done via OU structure, not SCP condition keys on the root.

---

### Scenario 2: Domain 2 — Design for New Solutions

A SaaS provider is building a new multi-tenant real-time analytics pipeline on AWS. Requirements:
(1) ingest 500,000 events/second from tenant applications globally; (2) each tenant's data must
be processed in strict isolation with no cross-tenant data leakage; (3) the enrichment logic
changes per tenant and must be updatable without pipeline downtime; (4) analytical results must
be available for tenant dashboards within **200ms end-to-end**; (5) the architecture must support
**exactly-once processing** semantics. The engineering team has rejected managed Kafka as too
operationally complex.

**Question:** Which architecture BEST meets all five requirements?

- [ ] **A)** Amazon Kinesis Data Streams (one stream per tenant, Enhanced Fan-Out consumers) →
  AWS Lambda (per-tenant function with enrichment logic in environment variables) → Amazon
  DynamoDB Global Tables → CloudFront for dashboard reads.
- [ ] **B)** Amazon MSK Serverless (one topic per tenant) → ECS Fargate consumers (per-tenant
  task definition) → Aurora Serverless v2 → API Gateway HTTP API for dashboard reads.
- [ ] **C)** Amazon Kinesis Data Streams (partitioned by `tenant_id`) → Amazon Kinesis Data
  Analytics for Apache Flink (per-tenant application with tenant-aware processing graphs) →
  Amazon DynamoDB (per-tenant table with on-demand capacity) → API Gateway with Lambda
  authorizer for dashboard reads.
- [ ] **D)** Amazon EventBridge (custom event bus per tenant) → Lambda (enrichment) → Amazon
  Kinesis Firehose → S3 → Athena for dashboard queries.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Kinesis Data Streams with `tenant_id` partitioning → Kinesis
  Data Analytics for Apache Flink → per-tenant DynamoDB tables → API Gateway with Lambda
  authorizer.

* **Why it succeeds:** Kinesis Data Streams supports up to 1 MB/s per shard with Enhanced
  Fan-Out providing up to 2 MB/s per consumer per shard, achieving 500K events/second ingestion
  at scale. Apache Flink on Kinesis Data Analytics natively supports **exactly-once processing**
  via its checkpointing mechanism backed by S3, satisfying constraint 5. Per-tenant processing
  graphs within a single Flink application enforce tenant isolation without requiring separate
  infrastructure per tenant. Flink application updates via application snapshots and blue/green
  upgrades can be done without dropping the stream, satisfying the no-downtime enrichment update
  requirement. DynamoDB with on-demand capacity delivers single-digit millisecond reads, keeping
  the 200ms SLA achievable. API Gateway with Lambda authorizer enforces tenant-scoped JWT claims,
  preventing cross-tenant data access at the read layer.

* **Why alternatives fail:**
  - **A)** One Kinesis stream per tenant means provisioning and managing thousands of streams —
    this does not scale operationally. Lambda cold-start latency risks breaching the 200ms SLA.
    Lambda environment variables for enrichment logic require function updates per tenant, violating
    the no-downtime update requirement.
  - **B)** The team explicitly rejected MSK. MSK Serverless does not provide exactly-once
    semantics by default without Kafka's Transactions API, which requires complex configuration —
    the exact reason MSK was rejected.
  - **D)** EventBridge has a throughput limit of ~10,000 events/second per event bus by default,
    far below the 500K requirement. Athena is a batch query engine with multi-second latency,
    violating the 200ms SLA. Firehose buffering (minimum 60 seconds) adds further incompatible
    latency.

---

### Scenario 3: Domain 3 — Migration Planning

A telecommunications company is migrating a 200TB Oracle RAC database (active-active, 2-node
cluster) running on-premises to AWS. Constraints: (1) the business requires **less than 1 hour
of total downtime** during the cutover window; (2) the source database has 14 custom Oracle-specific
PL/SQL packages and 3 materialized views with Oracle-proprietary syntax; (3) post-migration, the
target must eliminate Oracle licensing costs entirely; (4) the on-premises datacenter has a
**1 Gbps Direct Connect** connection to AWS; (5) the migration must be completed within **8 weeks**.
The data change rate is approximately **50 GB/day**.

**Question:** Which migration strategy MOST efficiently meets all constraints within the 8-week
window?

- [ ] **A)** Use AWS Schema Conversion Tool (SCT) to convert the Oracle schema to PostgreSQL. Use
  AWS DMS with Full Load + CDC to migrate to Aurora PostgreSQL. Manually refactor all 14 PL/SQL
  packages and 3 materialized views. Redirect traffic after CDC lag drops below 30 seconds.
- [ ] **B)** Provision AWS Snowball Edge devices to bulk-transfer the 200TB. Once data arrives in
  S3, use DMS to load into Aurora PostgreSQL. Run SCT for schema conversion in parallel. Perform
  a final DMS CDC sync during the cutover window.
- [ ] **C)** Use AWS DMS full load only (no CDC) to migrate the 200TB over Direct Connect.
  Schedule a full maintenance window of 48 hours for the transfer and cutover. Convert the schema
  using SCT targeting Amazon RDS for Oracle to eliminate refactoring.
- [ ] **D)** Use SCT to assess and convert the schema to Amazon Aurora PostgreSQL. Launch DMS
  Replication Instance in the same VPC. Run Full Load + CDC over Direct Connect. Address SCT
  action items for PL/SQL using AWS Lambda functions for any stored procedure logic that cannot
  be auto-converted. Perform cutover when CDC replication lag is under 60 seconds.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — SCT for schema assessment and conversion targeting Aurora
  PostgreSQL, DMS Full Load + CDC over Direct Connect, Lambda replacements for unconvertible
  PL/SQL, cutover at <60s CDC lag.

* **Why it succeeds:** At 1 Gbps Direct Connect, transfer of 200TB is achievable well within the
  8-week timeline. CDC with a 50 GB/day change rate means DMS lag will shrink to near-zero after
  the full load phase, enabling a **sub-1-hour cutover window** by redirecting application
  connections after lag drops under 60 seconds — satisfying constraint 1. SCT automatically
  converts a significant portion of Oracle PL/SQL; unconvertible constructs can be replaced with
  Lambda functions called via the `aws_lambda` extension in Aurora PostgreSQL, satisfying
  constraint 3 (zero Oracle licensing) while avoiding a full rewrite of all 14 packages.
  Aurora PostgreSQL fully eliminates Oracle licensing (constraint 3). This approach follows the
  Well-Architected Migration pillar methodology: assess → convert → replicate → validate →
  cutover.

* **Why alternatives fail:**
  - **A)** Directionally correct but incomplete — it does not specify how unconvertible PL/SQL
    packages will be handled, which is common with Oracle RAC-specific constructs. Simply saying
    "manually refactor" ignores the 8-week constraint without the Lambda accelerator pattern.
  - **B)** Snowball Edge is optimal when network bandwidth is insufficient. With 1 Gbps Direct
    Connect and 200TB, DMS over Direct Connect is faster — no Snowball shipping time of 2–3 weeks
    round-trip. Using Snowball eliminates real-time CDC during bulk transfer, risking the cutover
    SLA.
  - **C)** RDS for Oracle retains Oracle licensing costs — directly violating constraint 3.
    Full-load-only DMS with a 48-hour maintenance window violates the <1 hour downtime constraint.

---

### Scenario 4: Domain 4 — Cost Control

A media streaming company runs a globally distributed video transcoding workload on AWS. Workload
characteristics: (1) **burst processing** of user-uploaded videos runs 4–6 hours per day during
business hours across `us-east-1` and `eu-west-1`; (2) jobs are stateless and can be interrupted —
the average job runs 8 minutes; (3) currently using On-Demand `c5.4xlarge` instances with ASG
(min: 50, max: 500); (4) cold-start tolerance is under 3 minutes for new instances; (5) S3 stores
raw uploads (average object age 7 days before processing, then archived); (6) CloudFront delivers
processed video globally. The current monthly bill is $180,000 — 70% EC2, 20% S3, 10%
CloudFront/data transfer. The CFO requires a **40% cost reduction without degrading end-user QoE**.

**Question:** Which combination of changes delivers the HIGHEST cost reduction while respecting
ALL operational constraints?

- [ ] **A)** Replace On-Demand instances with **Reserved Instances** (1-year, standard). Enable
  S3 Intelligent-Tiering on the raw uploads bucket. Implement CloudFront cache policies with
  longer TTLs.
- [ ] **B)** Replace On-Demand with **Spot Instances** using a mixed instance policy across
  `c5.4xlarge`, `c5a.4xlarge`, `m5.4xlarge` pools. Enable S3 Lifecycle rules to transition
  objects to **S3 Glacier Instant Retrieval** after 7 days and **S3 Glacier Deep Archive**
  after 90 days. Purchase **CloudFront Security Savings Bundle**.
- [ ] **C)** Migrate transcoding to **AWS Elemental MediaConvert** (on-demand pricing per GB
  transcoded). Enable S3 Intelligent-Tiering. Retain On-Demand Auto Scaling for burst headroom.
- [ ] **D)** Replace On-Demand with **Savings Plans** (Compute Savings Plan, 3-year). Keep S3
  Standard for raw uploads. Purchase additional CloudFront Reserved Capacity for `us-east-1`
  and `eu-west-1`.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Spot Instances with mixed instance pools + S3 Lifecycle to
  Glacier Instant Retrieval / Deep Archive + CloudFront Security Savings Bundle.

* **Why it succeeds:** The workload is stateless, interruptible, and jobs average 8 minutes —
  the **canonical Spot Instance use case**. Spot Instances provide up to **90% discount** over
  On-Demand. A mixed instance policy across `c5.4xlarge`, `c5a.4xlarge`, and `m5.4xlarge` pools
  ensures Spot availability pools are diverse enough to absorb interruptions (2-minute warning —
  well within the 3-minute cold-start tolerance). EC2 Auto Scaling's **capacity-optimized**
  allocation strategy selects from the pool with the lowest interruption rate. The 70% EC2 share
  means a 70–90% discount on that portion alone exceeds the 40% total bill reduction target. S3
  Lifecycle to Glacier Instant Retrieval after 7 days reduces S3 storage cost by ~68% versus S3
  Standard. Deep Archive at 90 days reduces cost by ~95% for long-term retention. The CloudFront
  Security Savings Bundle provides up to 30% savings on CloudFront charges.

* **Why alternatives fail:**
  - **A)** Reserved Instances require 1-year commitment and are cost-effective only for steady-state
    24/7 workloads. This workload runs 4–6 hours/day — ~20–25% utilization. Paying for 24/7 RI
    capacity for a burst workload wastes 75% of the reserved commitment. RI savings (~40%) applied
    to 25% utilization yields a net bill reduction far below 40%.
  - **C)** MediaConvert is priced per minute of output video. For high-volume transcoding at scale,
    per-output-minute pricing often **exceeds** the cost of self-managed Spot transcoding by 3–5x.
    This option would likely increase costs.
  - **D)** Compute Savings Plans on a 3-year term have the same fundamental flaw as RIs for burst
    workloads — you pay for sustained compute you don't consume. "CloudFront Reserved Capacity" is
    not a standard CloudFront pricing construct.

---

### Scenario 5: Domain 5 — Continuous Improvement for Existing Solutions

A global e-commerce company runs a microservices platform on Amazon EKS (Fargate) across
`us-east-1` and `ap-southeast-1`. The platform uses Aurora Global Database (primary in
`us-east-1`, read replica in `ap-southeast-1`) and serves 50 million daily active users.
The ops team observes: (1) during `us-east-1` regional events, **RTO is 45 minutes** due to
manual Aurora failover procedures; (2) **API latency p99 is 850ms** for `ap-southeast-1` users
hitting the primary Aurora writer; (3) Route 53 health-check failover is triggering false
positives; (4) DynamoDB Global Tables are used for session state and functioning correctly.
The business target is **RTO < 5 minutes** and **p99 latency < 200ms** for all regions.

**Question:** Which combination of improvements MOST effectively achieves BOTH targets?

- [ ] **A)** Enable Aurora Global Database **write forwarding** on the `ap-southeast-1` secondary.
  Implement Route 53 Application Recovery Controller (ARC) with readiness checks. Automate Aurora
  managed planned failover via EventBridge + Lambda triggered by ARC routing control state changes.
- [ ] **B)** Replace Aurora Global Database with **DynamoDB Global Tables** for all transactional
  data. Deploy API Gateway regional endpoints in both regions. Use Route 53 latency-based routing
  with health checks.
- [ ] **C)** Deploy an Aurora read replica in `ap-southeast-1` (separate from Global Database).
  Configure the EKS application to route all reads to the local replica using a custom JDBC driver.
  Use Route 53 failover routing with a 10-second health check interval.
- [ ] **D)** Enable **Aurora Global Database managed failover** (RTO target <1 minute). Configure
  Route 53 ARC with routing controls. Implement read-local routing in the `ap-southeast-1` EKS
  application tier to direct all read queries to the Global Database secondary endpoint. Replace
  flawed health checks with ARC routing control health checks in Route 53.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — Aurora Global Database managed failover + Route 53 ARC routing
  controls + read-local routing via the `ap-southeast-1` Global Database secondary endpoint.

* **Why it succeeds:** Aurora Global Database **managed failover** achieves **RTO under 1 minute**
  by using Aurora's storage-level cross-region replication (lag typically <1 second) — eliminating
  the 45-minute manual procedure. Route 53 **Application Recovery Controller (ARC)** replaces
  standard health checks with **routing controls** — binary, operator-controlled switches not
  susceptible to transient health-check failures, eliminating false positives. ARC readiness
  checks continuously validate that the `ap-southeast-1` cell has sufficient capacity before a
  routing control change is allowed. **Read-local routing** directing `ap-southeast-1` application
  pods to the Aurora Global Database secondary endpoint eliminates cross-region database reads,
  reducing p99 latency from 850ms to sub-50ms for read operations.

* **Why alternatives fail:**
  - **A)** Write forwarding routes writes from the secondary back to the primary over the Global
    Database network link, adding 60–90ms of round-trip latency per write — does not address read
    latency. EventBridge + Lambda failover automation introduces additional latency and failure
    points versus the native managed failover API.
  - **B)** Replacing Aurora Global Database with DynamoDB Global Tables requires complete
    application re-architecture — not a continuous improvement. DynamoDB is not a relational
    substitute for ACID transactional workloads common in e-commerce.
  - **C)** A standalone Aurora read replica outside Global Database introduces higher binlog-based
    replication lag. Route 53 health checks with 10-second intervals still introduce false-positive
    risk — ARC was designed specifically to solve this problem.

---

### Scenario 6: Domain 1 — Design Solutions for Organizational Complexity

A regulated financial institution operates 60 AWS accounts across three OUs: `Production`,
`NonProduction`, and `Sandbox`. IAM Identity Center is configured with an external IdP (Okta)
via SAML 2.0. The security team mandates: (1) all human access to Production accounts must use
**MFA enforced at the IdP layer**; (2) developers must never have persistent IAM credentials in
Production; (3) a third-party auditing firm needs **read-only cross-account access** to all 60
accounts for 90 days — the firm uses its own AWS account (external); (4) SCPs must prevent any
IAM user creation in Production accounts; (5) the solution must be auditable via CloudTrail with
the principal identity visible.

**Question:** Which architecture satisfies ALL five constraints with the least operational overhead?

- [ ] **A)** Configure IAM Identity Center permission sets for developers with session duration of
  1 hour. Enforce MFA in Okta before the SAML assertion is issued. Deploy an SCP on the Production
  OU denying `iam:CreateUser`. For the auditing firm, create IAM users in each Production account
  with read-only policies and share credentials securely.
- [ ] **B)** Configure IAM Identity Center permission sets scoped to Production with read-only and
  developer roles. Enforce MFA in Okta. Deploy an SCP on Production OU denying `iam:CreateUser`.
  For the auditing firm, create a cross-account IAM role in each account with a trust policy to
  the auditing firm's AWS account, scoped to `ReadOnlyAccess`, with an `aws:MultiFactorAuthPresent`
  condition and tag-based automation for 90-day lifecycle.
- [ ] **C)** Create federated IAM roles in each Production account using Okta SAML directly
  (bypassing IAM Identity Center). Enforce MFA at Okta. For auditing, deploy AWS Organizations
  delegated admin for AWS Audit Manager and grant the firm access via Audit Manager APIs.
- [ ] **D)** Use IAM Identity Center with Okta SAML. Enforce MFA at Okta. Apply SCP on Production
  OU: `Deny iam:CreateUser`. For the auditing firm, create a single cross-account role in the
  management account with `organizations:*` and allow the firm to assume it for read access across
  all accounts.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — IAM Identity Center + Okta MFA enforcement + Production SCP
  denying `iam:CreateUser` + time-bound cross-account IAM role for the auditing firm with
  `ReadOnlyAccess` and lifecycle automation.

* **Why it succeeds:** IAM Identity Center uses **temporary credentials vended per session** —
  developers never receive persistent IAM credentials, satisfying constraint 2. MFA enforced in
  Okta before the SAML assertion ensures humans cannot reach Identity Center without MFA,
  satisfying constraint 1. The SCP `Deny iam:CreateUser` on the Production OU prevents any IAM
  user creation even by account administrators, satisfying constraint 4. For the auditing firm,
  a cross-account IAM role with a trust policy to the firm's account ID requires no IAM users in
  Production (constraints 2 and 4 satisfied), uses AWS STS AssumeRole which is fully logged in
  CloudTrail with the caller's ARN (constraint 5 satisfied), and can be lifecycle-managed via
  EventBridge + Lambda to auto-delete after 90 days (constraint 3 satisfied).

* **Why alternatives fail:**
  - **A)** Creating IAM users for the auditing firm directly violates constraint 2 (no persistent
    IAM credentials in Production) and constraint 4 (SCP blocks `iam:CreateUser` anyway — making
    this architecturally impossible once the SCP is in place).
  - **C)** Bypassing IAM Identity Center with direct SAML federation creates per-account federated
    roles that must be managed individually across 60 accounts — high operational overhead. Audit
    Manager does not grant the firm raw AWS API read access across accounts.
  - **D)** Granting `organizations:*` on the management account to an external party is a critical
    security anti-pattern. Full Organizations API access could allow the firm to detach accounts,
    modify SCPs, or alter billing — violating the principle of least privilege fundamentally.

---

### Scenario 7: Domain 2 — Design for New Solutions

A healthcare company is building a HIPAA-compliant real-time patient vitals monitoring system.
Requirements: (1) IoT devices in 500 hospitals stream vitals at 10 readings/second per device —
peak 2 million concurrent devices; (2) anomaly detection must trigger a clinical alert within
**500ms of ingestion**; (3) all data at rest and in transit must be encrypted with **customer-managed
KMS keys**; (4) the system must survive an **entire AWS region failure** with RPO = 0 and
RTO < 1 minute; (5) data must be queryable historically for 7 years for compliance; (6) HIPAA
Business Associate Agreement (BAA) must be coverable by all services used.

**Question:** Which architecture BEST satisfies all six constraints?

- [ ] **A)** IoT Core → Kinesis Data Streams (KMS-encrypted, two regions, `TRIM_HORIZON`) →
  Kinesis Data Analytics for Apache Flink (anomaly detection, 500ms window) → DynamoDB Global
  Tables (KMS CMK) for real-time state → S3 with S3 Glacier Deep Archive lifecycle (KMS CMK)
  for 7-year retention → Route 53 ARC for regional failover.
- [ ] **B)** IoT Core → Amazon MSK (KMS-encrypted) → Lambda (anomaly detection) → Aurora Global
  Database (KMS CMK) → S3 Intelligent-Tiering for 7-year retention → Route 53 latency-based
  routing.
- [ ] **C)** IoT Core → Kinesis Data Streams (single region) → Kinesis Data Analytics for Flink
  → ElastiCache Redis (anomaly state) → Redshift for 7-year historical queries → CloudFront for
  API delivery.
- [ ] **D)** IoT Core → EventBridge → Lambda (anomaly detection) → DynamoDB Global Tables →
  S3 for 7-year retention → CloudWatch alerts for clinical notifications.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — IoT Core → dual-region Kinesis Data Streams with KMS CMK →
  Kinesis Data Analytics Flink → DynamoDB Global Tables → S3/Glacier Deep Archive → Route 53 ARC.

* **Why it succeeds:** AWS IoT Core supports HIPAA BAA and scales to millions of concurrent device
  connections. Kinesis Data Streams deployed in **two regions simultaneously** with producers
  writing to both achieves **RPO = 0** — no data is lost on regional failure. Route 53 ARC
  routing controls enable **sub-1-minute RTO** by switching consumer applications to the secondary
  region's Kinesis stream without DNS propagation delays. Kinesis Data Analytics for Apache Flink
  processes the stream with a **tumbling window of ≤500ms**, meeting the anomaly detection SLA.
  DynamoDB Global Tables (KMS CMK) maintain real-time patient state with active-active multi-region
  replication. S3 with lifecycle to Glacier Deep Archive after 90 days provides cost-effective
  7-year HIPAA retention. All services listed have published HIPAA BAA coverage. KMS CMK satisfies
  constraint 3 end-to-end.

* **Why alternatives fail:**
  - **B)** MSK does not replicate cross-region natively — MSK Mirror Maker 2 introduces replication
    lag that violates RPO = 0. Lambda's cold-start latency can breach the 500ms anomaly detection
    SLA under burst conditions. Aurora Global Database has typical replication lag <1 second —
    technically violating RPO = 0.
  - **C)** Single-region Kinesis violates the RPO = 0 and RTO < 1 minute regional failure
    requirement. ElastiCache Redis is not a HIPAA BAA-eligible service.
  - **D)** EventBridge has a default throughput of ~10,000 events/second per bus — 20 million
    events/second (2M devices × 10 readings) is orders of magnitude beyond its limits. Lambda
    cannot guarantee 500ms latency at this throughput.

---

### Scenario 8: Domain 3 — Migration Planning

A retail company operates a monolithic Java EE application on 40 on-premises VMware VMs. The
migration plan calls for lift-and-shift to EC2 first, followed by containerisation into ECS
Fargate in phase 2. Constraints: (1) total cutover downtime must be **under 2 hours**; (2) the
on-premises environment has **500 Mbps internet bandwidth** only — no Direct Connect; (3) the
application uses a **shared NFS mount** (8TB) across all 40 VMs; (4) the Oracle database (3TB)
must be migrated to Amazon RDS for PostgreSQL with **zero data loss**; (5) a rollback to
on-premises must be executable within 4 hours if the cutover fails; (6) the migration must be
tracked centrally.

**Question:** Which combination of services and sequencing BEST satisfies all six constraints?

- [ ] **A)** Use AWS Application Migration Service (MGN) to replicate all 40 VMs continuously
  over the internet. Use AWS DataSync to replicate the 8TB NFS to Amazon EFS. Use DMS with Full
  Load + CDC to migrate Oracle to RDS PostgreSQL. Cutover: stop writes, wait for CDC lag < 60
  seconds, flip DNS, switch NFS clients to EFS endpoint. Track via AWS Migration Hub. Rollback:
  MGN provides on-premises agent still running — repoint DNS.
- [ ] **B)** Use AWS Server Migration Service (SMS) to replicate VMs. Use Storage Gateway File
  Gateway for the NFS share. Use DMS Full Load only for Oracle. Schedule a 6-hour maintenance
  window. Track via Migration Hub.
- [ ] **C)** Use AWS MGN to replicate VMs. Use AWS DataSync to sync the 8TB NFS share to S3.
  Mount S3 via S3 File Gateway on EC2 instances post-migration. Use DMS Full Load + CDC for
  Oracle to RDS PostgreSQL. Track via Migration Hub. Rollback: reverse DataSync job writes back
  to on-premises NFS.
- [ ] **D)** Ship 8TB NFS data via AWS Snowball Edge. Use MGN for VM replication. Use DMS Full
  Load + CDC for Oracle. Track via Migration Hub. Cutover after Snowball data lands in EFS.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — MGN continuous replication + DataSync NFS-to-EFS + DMS Full
  Load + CDC + Migration Hub tracking + DNS-flip cutover with MGN rollback capability.

* **Why it succeeds:** AWS Application Migration Service (MGN) performs **continuous block-level
  replication** over the internet using a lightweight agent, keeping EC2 cutover instances
  perpetually in sync. At 500 Mbps, initial sync completes in the background; by cutover day,
  delta replication lag is seconds — enabling a **sub-2-hour cutover**. AWS DataSync efficiently
  transfers the 8TB NFS share to Amazon EFS over the internet using parallel multi-threaded
  transfers with built-in integrity verification — EFS provides a drop-in NFS replacement
  mountable by all 40 EC2 instances simultaneously. DMS Full Load + CDC on the 3TB Oracle
  database achieves **zero data loss** by applying ongoing changes during the full load and
  reducing CDC lag to near-zero before cutover. AWS Migration Hub provides centralised tracking
  across MGN and DMS. Rollback within 4 hours is achievable because MGN agents remain installed
  on-premises — DNS repointing restores on-premises traffic.

* **Why alternatives fail:**
  - **B)** AWS SMS is deprecated — AWS recommends MGN for all VM migrations. DMS Full Load only
    means the database stops accepting writes during 3TB transfer — at 500 Mbps this takes 13+
    hours, violating the 2-hour downtime constraint and the zero data loss requirement.
  - **C)** Mounting the 8TB NFS via S3 File Gateway on EC2 introduces caching latency unsuitable
    for a high-concurrency NFS workload used by a Java EE monolith. EFS is the correct target for
    a lift-and-shift NFS replacement.
  - **D)** Snowball Edge has a 7–10 day shipping round-trip time. Snowball does not support ongoing
    delta sync — any changes to NFS after the Snowball copy require a separate DataSync catch-up
    job, adding risk to the cutover window.

---

### Scenario 9: Domain 4 — Cost Control

A media company runs a data lake on S3 with 4PB of data. Access pattern analysis: 20% of objects
accessed within 30 days of creation, 10% between 30–90 days, 70% never accessed after 90 days
but must be retained for 7 years for legal hold. The company also runs 200 `m5.2xlarge` On-Demand
instances 24/7 for video processing (steady-state, predictable), 50 `c5.4xlarge` instances for
batch transcoding (runs 8 hours/day on weekdays only), and spends $45,000/month on data transfer
out to end users via direct S3 URLs. 300 S3 buckets have no lifecycle policies. The CFO wants a
**50% reduction in total cloud spend** within 60 days.

**Question:** Which combination of actions delivers the HIGHEST savings while maintaining all
access SLAs?

- [ ] **A)** Apply S3 Intelligent-Tiering to all 4PB. Purchase 1-year Standard Reserved Instances
  for all 200 `m5.2xlarge`. Use Spot Instances for the 50 batch `c5.4xlarge`. Serve S3 content
  via CloudFront with Origin Access Control (OAC) to eliminate direct S3 data transfer charges.
- [ ] **B)** Apply S3 Lifecycle: S3 Standard (0–30 days) → S3 Standard-IA (30–90 days) → S3
  Glacier Deep Archive (90 days+). Purchase 3-year Compute Savings Plans for `m5.2xlarge`. Use
  Spot for batch transcoding. Serve content via CloudFront with OAC.
- [ ] **C)** Apply S3 Intelligent-Tiering to all 4PB. Purchase 3-year Standard Reserved Instances
  for all 200 `m5.2xlarge` and 50 `c5.4xlarge`. Serve content via CloudFront with OAC.
- [ ] **D)** Apply S3 Lifecycle: S3 Standard (0–30 days) → S3 Standard-IA (30–90 days) → S3
  Glacier Instant Retrieval (90 days+). Purchase 1-year Compute Savings Plans for `m5.2xlarge`.
  Use Spot for batch transcoding. Serve content via CloudFront with OAC.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Explicit S3 Lifecycle to Deep Archive + 3-year Compute Savings
  Plans for steady-state + Spot for batch + CloudFront OAC.

* **Why it succeeds:** With 70% of 4PB (2.8PB) never accessed after 90 days, S3 Glacier Deep
  Archive at **$0.00099/GB/month** versus S3 Standard at **$0.023/GB/month** yields a ~96%
  storage cost reduction on that tier. Explicit Lifecycle rules avoid Intelligent-Tiering's
  per-object monitoring fee ($0.0025 per 1,000 objects) — at 4PB scale with billions of small
  objects, this monitoring fee can exceed the storage savings. The 200 `m5.2xlarge` instances
  run 24/7 in steady state — **3-year Compute Savings Plans** provide up to **66% discount**
  over On-Demand versus 40% for 1-year. Spot Instances for the 8-hours/weekday batch transcoding
  (stateless, interruptible) delivers up to 90% savings. CloudFront with OAC eliminates the
  $45,000/month in S3 data transfer egress charges.

* **Why alternatives fail:**
  - **A)** S3 Intelligent-Tiering is suboptimal for objects with **known, predictable access
    patterns**. Explicit Lifecycle policies deliver higher savings with zero monitoring fees at
    4PB scale. 1-year RI savings (~40%) on steady-state compute leave significant savings on the
    table versus a 3-year Savings Plan.
  - **C)** Purchasing 3-year Reserved Instances for the 50 batch `c5.4xlarge` instances (running
    only 8 hours/weekday — ~24% utilization) wastes 76% of the reserved commitment. Spot Instances
    are the correct vehicle for this workload pattern.
  - **D)** S3 Glacier Instant Retrieval costs ~$0.004/GB/month — 4x more expensive than Deep
    Archive. For data that is **never accessed** after 90 days (legal hold only), Deep Archive is
    the correct tier. Paying for Instant Retrieval's millisecond access capability is wasteful.

---

### Scenario 10: Domain 5 — Continuous Improvement for Existing Solutions

A global logistics company runs a microservices platform on EKS across `us-east-1` and
`eu-central-1`. Services communicate via REST over API Gateway (Regional endpoints). The
observability team reports: (1) they cannot trace a single request across 12 microservices —
logs exist per service but correlation is manual; (2) a downstream service (shipment-tracker)
intermittently causes cascading failures that bring down unrelated services due to thread pool
exhaustion; (3) canary deployments for new service versions are done manually by editing
Kubernetes deployment YAMLs — this takes 4 hours per service; (4) the team has no automated
mechanism to detect and roll back a bad deployment before it affects more than 5% of traffic.

**Question:** Which combination of AWS-native improvements MOST comprehensively addresses all
four gaps?

- [ ] **A)** Deploy AWS X-Ray with the X-Ray daemon as a DaemonSet on EKS. Implement circuit
  breakers using AWS App Mesh with Envoy proxies (`outlierDetection` on virtual nodes). Migrate
  canary deployments to AWS CodeDeploy with `LINEAR_10PERCENT_EVERY_1MINUTE` strategy integrated
  with EKS via CodePipeline. Use CloudWatch Alarms on X-Ray error rate metrics to trigger
  automated CodeDeploy rollback.
- [ ] **B)** Deploy AWS CloudWatch Container Insights with EKS add-on. Use AWS Fault Injection
  Simulator to test cascading failures. Migrate canary deployments to Helm chart versioning with
  manual percentage splits. Use CloudWatch Synthetics for canary traffic simulation.
- [ ] **C)** Deploy AWS Distro for OpenTelemetry (ADOT) Collector as a DaemonSet for distributed
  tracing to X-Ray and metrics to CloudWatch. Implement AWS App Mesh with `outlierDetection`
  circuit breaker on the shipment-tracker virtual service. Use Argo Rollouts with an Analysis
  Template backed by CloudWatch metrics for automated canary promotion/rollback at 5% traffic
  threshold. Integrate Argo Rollouts with API Gateway weighted target groups for traffic splitting.
- [ ] **D)** Deploy Jaeger on EKS for distributed tracing. Use Kubernetes liveness probes with
  aggressive timeouts to restart failing pods. Use Flux CD with Helm releases for canary
  deployments. Set PodDisruptionBudgets to protect critical services during deployments.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — ADOT Collector + X-Ray + App Mesh circuit breaker + Argo Rollouts
  with CloudWatch Analysis Template + API Gateway weighted routing.

* **Why it succeeds:** AWS Distro for OpenTelemetry (ADOT) is the AWS-supported distribution of
  the OpenTelemetry Collector, enabling **vendor-neutral instrumentation** that sends traces to
  X-Ray and metrics to CloudWatch simultaneously. ADOT's auto-instrumentation provides
  **cross-service trace correlation via `X-Amzn-Trace-Id` propagation headers** — a single trace
  ID flows through all 12 microservices, resolving gap 1. AWS App Mesh's Envoy `outlierDetection`
  implements a **passive circuit breaker** — it ejects the shipment-tracker upstream from the
  load-balancing pool when consecutive 5xx errors exceed a configurable threshold, preventing
  thread pool exhaustion in callers without application code changes, resolving gap 2. Argo
  Rollouts natively supports **automated canary analysis** at any traffic percentage with an
  Analysis Template backed by CloudWatch metrics — automatically pausing or rolling back the
  canary if thresholds are breached, resolving gaps 3 and 4.

* **Why alternatives fail:**
  - **A)** CodeDeploy's EKS integration is primarily for EC2 node-based deployments or Lambda —
    it does not natively integrate with Kubernetes `Deployment` objects for pod-level canary
    traffic splitting on EKS Fargate. This conflates CodeDeploy's Lambda/EC2 canary capabilities
    with Kubernetes deployment patterns incorrectly.
  - **B)** CloudWatch Container Insights provides infrastructure metrics but not distributed
    traces — it does not solve the cross-service request correlation problem. Fault Injection
    Simulator tests chaos but does not implement a runtime circuit breaker. Manual Helm percentage
    splits do not provide automated rollback.
  - **D)** Jaeger requires self-managed infrastructure on EKS — increasing operational burden.
    Kubernetes liveness probes restart pods after failure — they do not prevent cascading failures
    caused by slow upstream responses. Flux CD with Helm does not provide automated metric-based
    canary rollback out of the box.

---

### Scenario 11: Domain 1 — Design Solutions for Organizational Complexity

A multinational bank operates 80 AWS accounts across OUs: `Production`, `Development`, `Sandbox`.
AWS Control Tower manages the landing zone. The CISO mandates: (1) no AWS account may disable
AWS CloudTrail in any region; (2) Amazon GuardDuty must be active in all accounts in all regions;
(3) Security Hub findings must aggregate to a **single designated Security account**; (4) newly
vended accounts must inherit all controls automatically within **5 minutes** of creation; (5)
member accounts must not be able to opt out of GuardDuty or leave the organization.

**Question:** Which architecture satisfies ALL five mandates with the least custom code?

- [ ] **A)** Use AWS Config Rules deployed via CloudFormation StackSets to detect CloudTrail
  disablement. Enable GuardDuty via StackSets. Use Security Hub with a delegated admin account.
  Apply an SCP denying `guardduty:DeleteDetector` and `cloudtrail:StopLogging`.
- [ ] **B)** Enable AWS Control Tower detective controls for CloudTrail. Use GuardDuty delegated
  admin in the Security account — enable auto-enable for new accounts. Set Security Hub delegated
  admin to the Security account with auto-enable. Apply SCPs denying `guardduty:DeleteDetector`,
  `cloudtrail:StopLogging`, and `organizations:LeaveOrganization`. Use Control Tower Account
  Factory to auto-enroll new accounts.
- [ ] **C)** Write a Lambda function triggered by `CreateAccount` CloudTrail event via EventBridge.
  Lambda enables GuardDuty, Security Hub, and CloudTrail in each new account via cross-account
  role assumption. Apply SCPs at root for restriction.
- [ ] **D)** Use AWS Config Aggregator in the Security account to collect findings from all
  accounts. Enable GuardDuty manually per account. Use CloudWatch Events to detect CloudTrail
  disablement and trigger SNS alerts.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Control Tower detective controls + GuardDuty/Security Hub
  delegated admin with auto-enable + SCPs blocking opt-out + Account Factory enrollment.

* **Why it succeeds:** AWS Control Tower's **mandatory guardrails** include a detective control
  that detects CloudTrail disablement — paired with an SCP preventive control (`Deny
  cloudtrail:StopLogging`), this satisfies constraint 1 without custom code. GuardDuty's
  **delegated administrator** model with `AutoEnable: ALL` ensures every new account and every
  region automatically gets GuardDuty within minutes of account creation — satisfying constraints
  2 and 4. Security Hub's delegated admin with auto-enable aggregates all findings to the Security
  account, satisfying constraint 3. The SCP `Deny organizations:LeaveOrganization` prevents member
  account escape, satisfying constraint 5. Control Tower Account Factory handles new account
  vending with all controls pre-applied — the 5-minute window is met because delegated admin
  auto-enable is event-driven at the Organizations API level, not polling-based.

* **Why alternatives fail:**
  - **A)** StackSets-based deployment of Config Rules is **detective, not preventive** — CloudTrail
    can still be disabled and the rule fires after the fact. StackSets also have deployment delays
    for new accounts that can exceed 5 minutes depending on stack instance propagation time.
  - **C)** Lambda with EventBridge is a custom-code solution that introduces operational risk —
    Lambda failures or event delivery delays can leave new accounts unprotected beyond the 5-minute
    window. This is the anti-pattern Control Tower's delegated admin model was designed to replace.
  - **D)** Config Aggregator collects resource configuration data, not GuardDuty findings — this
    conflates two different services. Manual per-account GuardDuty enablement does not satisfy the
    auto-enrollment requirement for new accounts.

---

### Scenario 12: Domain 2 — Design for New Solutions

A gaming company is launching a real-time global leaderboard supporting 10 million concurrent
players across 5 regions. Requirements: (1) leaderboard reads must return in **<10ms p99
globally**; (2) leaderboard writes (score updates) must be **conflict-free** — last-write-wins
is acceptable; (3) the system must tolerate a full region failure with **RPO = 0, RTO < 30
seconds**; (4) historical score events must be retained for **90 days** for anti-cheat auditing;
(5) the solution must scale to **500,000 writes/second** globally with no pre-provisioning.

**Question:** Which architecture BEST satisfies all five requirements?

- [ ] **A)** DynamoDB Global Tables (on-demand capacity) with a GSI on `score` for leaderboard
  ranking → DynamoDB Streams → Kinesis Data Firehose → S3 (90-day lifecycle) for audit.
  CloudFront with Lambda@Edge for leaderboard read caching.
- [ ] **B)** ElastiCache for Redis (ZADD/ZRANGE for sorted set leaderboard) with Global Datastore
  across 5 regions → Kinesis Data Streams → Lambda → S3 for audit retention.
- [ ] **C)** Amazon Aurora Global Database (writer in `us-east-1`) with read replicas in all 5
  regions → Aurora Streams to Kinesis for audit. Route 53 latency routing for reads.
- [ ] **D)** DynamoDB Global Tables (on-demand) for score storage → ElastiCache for Redis Global
  Datastore (sorted set `ZADD`/`ZRANGE`) in each region for leaderboard serving → DynamoDB
  Streams → EventBridge Pipes → Kinesis Data Firehose → S3 (90-day retention).

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — DynamoDB Global Tables for durable score storage + ElastiCache
  Redis Global Datastore sorted sets for sub-10ms leaderboard reads + Streams → Firehose → S3
  for 90-day audit.

* **Why it succeeds:** DynamoDB Global Tables with on-demand capacity handles **500,000
  writes/second** globally with no pre-provisioning, auto-scaling transparently across all 5
  regions — satisfying constraint 5. Last-write-wins conflict resolution is DynamoDB Global
  Tables' native behavior — satisfying constraint 2. Active-active replication across 5 regions
  with sub-second propagation delivers **RPO = 0** and **RTO < 30 seconds** on regional failure —
  satisfying constraint 3. ElastiCache Redis Global Datastore uses **sorted sets (ZADD/ZRANGE)**
  — the canonical data structure for leaderboards — delivering **<1ms read latency** locally in
  each region, well within the 10ms p99 SLA. DynamoDB Streams capture every score write;
  EventBridge Pipes deliver to Kinesis Firehose which buffers to S3 with a 90-day lifecycle
  policy — satisfying constraint 4.

* **Why alternatives fail:**
  - **A)** DynamoDB GSI on `score` for ranking requires scanning across all partition keys — at
    10 million concurrent players this is infeasible for sub-10ms reads. GSIs are not globally
    sorted across all partition keys. Lambda@Edge caching is inappropriate for real-time
    leaderboards updating at 500K writes/sec.
  - **B)** ElastiCache Redis Global Datastore does not provide **RPO = 0** — its cross-region
    replication is asynchronous and can lose seconds of data on primary region failure. There is
    no durable backing store for score data — a Redis cluster restart would lose all data not
    persisted to RDB/AOF snapshots.
  - **C)** Aurora Global Database has a **single writer** in `us-east-1` — all 500,000
    writes/second must traverse the network to the primary writer, creating a single-region write
    bottleneck far below the 500K writes/second requirement.

---

### Scenario 13: Domain 3 — Migration Planning

A government agency is migrating 500 applications from two on-premises datacenters to AWS over
24 months. The migration team must: (1) **classify each application** by migration strategy
(6 Rs) before moving; (2) track migration progress centrally across all AWS accounts; (3) perform
**portfolio assessment** to identify server dependencies automatically before planning; (4) large
file shares (200TB total) must move with **bandwidth throttling** to avoid impacting live
operations; (5) all migration activity must appear in a **single pane of glass** that
non-technical stakeholders can view.

**Question:** Which toolchain BEST addresses all five requirements in the correct sequence?

- [ ] **A)** AWS Application Discovery Service (ADS) with Discovery Connector (agentless) for
  dependency mapping → AWS Migration Hub for classification and central tracking → AWS DataSync
  with bandwidth throttling for file shares → Migration Hub console as stakeholder dashboard.
- [ ] **B)** AWS Server Migration Service (SMS) for dependency mapping → Migration Hub for
  tracking → AWS Snowball for file transfer → QuickSight dashboard over Migration Hub data.
- [ ] **C)** AWS Application Discovery Service with Discovery Agent (agent-based) for deep
  dependency mapping → Migration Hub for 6R classification and central tracking → AWS DataSync
  with `--bandwidth-limit` for throttled file share transfer → Migration Evaluator for portfolio
  business case → Migration Hub as stakeholder dashboard.
- [ ] **D)** AWS Systems Manager Inventory for server discovery → Migration Hub for tracking →
  AWS Transfer Family for file shares → Cost Explorer for stakeholder reporting.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — ADS Agent-based discovery + Migration Evaluator for portfolio
  assessment + Migration Hub for 6R tracking + DataSync with bandwidth throttling + Migration Hub
  dashboard.

* **Why it succeeds:** ADS **Discovery Agents** (installed on each server) collect process-level
  network connection data — enabling **automatic dependency mapping** between applications and
  servers, satisfying constraint 3. The agentless Discovery Connector (VMware-only) cannot map
  process-level dependencies. **Migration Evaluator** provides automated portfolio analysis and
  right-sizing recommendations, generating a business case report suitable for stakeholders —
  satisfying constraints 1 and 5. AWS Migration Hub provides the **central tracking plane**
  across all AWS migration tools (MGN, DMS, SMS) and all accounts, satisfying constraint 2.
  DataSync supports `--bandwidth-limit` parameter (MB/s) to throttle transfer speed, protecting
  live datacenter operations during the 200TB file share migration — satisfying constraint 4.

* **Why alternatives fail:**
  - **A)** Discovery Connector (agentless) only works with VMware vCenter and collects VM-level
    metadata — it **cannot map process-level network dependencies** between applications, making
    it insufficient for constraint 3 in a mixed on-premises environment.
  - **B)** AWS SMS is deprecated and should not be used for new migrations. Snowball cannot
    throttle transfer dynamically and is not suitable for 200TB where network transfer via DataSync
    is feasible and controllable.
  - **D)** SSM Inventory discovers installed software and instance metadata but does **not map
    network dependencies** between servers — insufficient for constraint 3. AWS Transfer Family
    is for SFTP/FTP file transfers to S3, not bulk datacenter file share migrations.

---

### Scenario 14: Domain 4 — Cost Control

A startup runs a multi-tier web application: ALB → ECS Fargate (API layer, always-on) → Aurora
PostgreSQL Serverless v2 → S3. Monthly bill: Fargate $12,000, Aurora $18,000, S3 $2,000, Data
Transfer $8,000, ALB $1,500. Total: $41,500/month. Traffic analysis shows: **70% of Aurora
capacity is consumed during business hours (9am–6pm UTC) only**. The Fargate API layer runs at
**15% average CPU utilization** 24/7. S3 stores application logs that are **never accessed after
30 days**. Data transfer costs come from **cross-AZ traffic** between Fargate tasks and Aurora.
The CTO wants to cut the bill by **35% without architectural redesign**.

**Question:** Which combination of targeted changes achieves the 35% reduction?

- [ ] **A)** Purchase Compute Savings Plans (1-year) for Fargate. Configure Aurora Serverless v2
  minimum ACUs to 0.5 (near-zero during off-hours). Apply S3 Lifecycle: expire logs after 30
  days. Place Fargate tasks and Aurora in the **same AZ** using AZ-aware service configuration.
- [ ] **B)** Migrate Fargate to EC2 Spot Instances. Convert Aurora Serverless v2 to Aurora
  Provisioned with Reserved Instances. Apply S3 Intelligent-Tiering. Use VPC endpoints for S3
  to reduce data transfer.
- [ ] **C)** Purchase Compute Savings Plans (1-year) for Fargate. Configure Aurora Serverless v2
  minimum ACUs to 0.5. Apply S3 Lifecycle: transition to S3 Glacier after 30 days. Pin ECS
  tasks to a single AZ matching Aurora's writer AZ using task placement constraints.
- [ ] **D)** Right-size Fargate task CPU/memory to match 15% utilization. Configure Aurora
  Serverless v2 `min ACU = 0.5`. Apply S3 Lifecycle: expire logs after 30 days. Use ECS Service
  Connect with AZ-local routing to eliminate cross-AZ data transfer to Aurora.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — Fargate right-sizing + Aurora min ACU reduction + S3 log expiry
  + AZ-local routing to eliminate cross-AZ charges.

* **Why it succeeds:** At 15% average CPU utilization, Fargate tasks are significantly
  **over-provisioned** — halving task CPU/memory definitions cuts Fargate costs by ~40–50% on the
  $12,000 line item without any Savings Plans commitment. Aurora Serverless v2 with `min ACU = 0.5`
  scales to near-zero during off-hours — at 70% of capacity consumed only during business hours,
  this reduces Aurora costs by ~30–40% on the $18,000 line item. S3 log expiry after 30 days
  eliminates 100% of post-30-day storage — expiry (delete) is more cost-effective than Glacier
  transition (which still incurs storage cost). Cross-AZ data transfer at **$0.01/GB** each way
  is the source of the $8,000 data transfer bill — ECS Service Connect with AZ-aware routing
  ensures Fargate tasks preferentially connect to Aurora endpoints in the same AZ, eliminating
  cross-AZ charges. Combined savings exceed 35% without redesign.

* **Why alternatives fail:**
  - **A)** Savings Plans on Fargate provide ~17–20% discount — meaningful but less impactful than
    right-sizing for a workload at 15% utilization. "Same AZ" placement without AZ-aware service
    discovery is not reliable — Fargate tasks can still be placed cross-AZ by the scheduler unless
    properly constrained. Aurora in a single AZ loses Multi-AZ resilience.
  - **B)** Migrating Fargate to EC2 Spot constitutes **architectural redesign**, violating the
    CTO's constraint. Aurora Serverless v2 to Provisioned is also a significant architectural
    change.
  - **C)** S3 Glacier transition after 30 days still incurs Glacier storage costs ($0.004/GB/month)
    plus a minimum 90-day storage charge on objects transitioned — for logs with zero value after
    30 days, **expiry is cheaper than Glacier**.

---

### Scenario 15: Domain 5 — Continuous Improvement for Existing Solutions

A financial trading platform runs on EC2 Auto Scaling behind an ALB in `us-east-1`. The platform
has: (1) **RTO of 4 hours** (too slow — business requires <15 minutes); (2) backups via nightly
AMI snapshots only — **RPO is 24 hours** (business requires <1 minute); (3) a single Aurora MySQL
cluster with no read replicas; (4) a legacy batch job running on a single `r5.8xlarge` EC2
instance every night — if it fails, manual restart takes 2 hours; (5) the team uses CloudFormation
for infrastructure but has **no drift detection** and configuration changes are applied manually
causing stack drift.

**Question:** Which combination of improvements MOST comprehensively resolves all five gaps?

- [ ] **A)** Enable Aurora MySQL **binary log replication** to a secondary region for RPO. Create
  an EC2 Image Builder pipeline for automated AMIs. Use AWS Elastic Disaster Recovery (DRS) for
  EC2 continuous replication. Migrate the batch job to AWS Batch with retry policies. Enable
  CloudFormation drift detection on a schedule via EventBridge.
- [ ] **B)** Convert Aurora MySQL to **Aurora Global Database** (cross-region, RPO <1 second).
  Replace nightly AMIs with AWS Elastic Disaster Recovery (DRS) for continuous EC2 block-level
  replication (RPO seconds). Deploy a pilot light environment in `us-west-2` with Route 53 ARC
  for <15-minute RTO. Migrate batch to AWS Batch with `MANAGED` compute environment and job retry
  count ≥ 1. Enable CloudFormation drift detection via EventBridge scheduled rule + SNS alert.
- [ ] **C)** Add Aurora read replicas in `us-east-1`. Enable automated Aurora backups with
  1-minute backup window. Use EC2 Auto Scaling across 3 AZs for HA. Keep batch job on EC2 but
  add a CloudWatch alarm to page on-call. Enable CloudFormation StackSets for drift remediation.
- [ ] **D)** Enable Aurora Global Database. Use AWS Backup with 1-minute continuous backup for
  EC2. Add Route 53 failover routing. Migrate batch to Step Functions with retry. Use AWS Config
  to detect CloudFormation drift.

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Aurora Global Database + AWS Elastic Disaster Recovery for EC2
  + pilot light in `us-west-2` + Route 53 ARC + AWS Batch with retry + CloudFormation drift
  detection via EventBridge.

* **Why it succeeds:** Aurora Global Database provides **storage-level cross-region replication
  with typical lag <1 second** — directly achieving the RPO <1 minute requirement for the database
  tier (constraint 2). AWS Elastic Disaster Recovery (DRS) performs **continuous block-level
  replication** of EC2 instances to a staging area in the recovery region — RPO is measured in
  **seconds** (not 24 hours), resolving constraint 2 for the compute tier. A pilot light
  environment in `us-west-2` with pre-provisioned minimal infrastructure can be activated in
  **<15 minutes** via Route 53 ARC routing control switches — resolving constraint 1. AWS Batch
  with a `MANAGED` compute environment handles job scheduling, retries, and infrastructure
  provisioning automatically — if the batch job fails, Batch retries per the job definition's
  `retryStrategy` without manual intervention, resolving constraint 4. CloudFormation drift
  detection triggered by an EventBridge scheduled rule with SNS notification gives visibility
  into manual configuration changes, resolving constraint 5.

* **Why alternatives fail:**
  - **A)** Aurora binary log replication to a secondary region is an older pattern superseded by
    Aurora Global Database — it has higher replication lag and requires more operational management.
    EC2 Image Builder creates AMIs on a schedule — this does not reduce RPO below the snapshot
    interval (still hours, not seconds). DRS is correct but the overall architecture lacks a clear
    RTO mechanism.
  - **C)** Aurora read replicas within `us-east-1` provide HA within the region but **do not
    address RTO for a regional failure** — the business requires DR, not just HA. A CloudWatch
    alarm on the batch job pages a human — this does not reduce the 2-hour manual restart time.
    StackSets do not perform drift remediation; they deploy stacks across accounts.
  - **D)** AWS Config detects resource configuration drift (EC2 security groups, S3 bucket
    policies, etc.) — it does **not detect CloudFormation stack drift** specifically. CloudFormation
    drift detection is a separate API (`detect-stack-drift`) that must be explicitly invoked. AWS
    Backup for EC2 takes EBS snapshots — point-in-time, not continuous replication, and does not
    achieve RPO <1 minute.

    ## Scenario 1: Domain 1 – Design Solutions for Organizational Complexity

A financial services enterprise uses AWS Organizations with 40 accounts across 4 OUs: Prod, NonProd, Sandbox, and Security. The Security team mandates that no account outside the Security OU can disable AWS CloudTrail, modify S3 bucket policies on the central logging bucket, or create IAM users with console access. The Sandbox OU must additionally be prevented from launching any EC2 instances beyond t3.micro. The IAM Identity Center is deployed at the management account level. Individual account administrators currently hold AdministratorAccess via IAM Identity Center permission sets.

**Question:** Which combination of controls satisfies ALL the stated requirements with the LEAST operational overhead?

* **A)** Create individual SCPs per OU denying CloudTrail modifications and S3 bucket policy changes, attach to Prod, NonProd, and Sandbox OUs; use a separate SCP on Sandbox denying `ec2:RunInstances` with a condition key `ec2:InstanceType` not equal to t3.micro; enforce via IAM Identity Center by removing AdministratorAccess from all accounts.
* **B)** Attach a deny-all-except-approved SCP to the Root; create allow SCPs at each OU level; use AWS Config rules to detect violations; use Lambda auto-remediation for any detected drift.
* **C)** Attach targeted Deny SCPs to the Root for CloudTrail and S3 logging bucket protections (with a condition excluding the Security OU's accounts); attach a separate SCP to the Sandbox OU denying `ec2:RunInstances` unless `ec2:InstanceType` equals t3.micro; leave IAM Identity Center permission sets unchanged.
* **D)** Use AWS Control Tower guardrails to enforce CloudTrail and S3 protections globally; create a custom Sandbox OU guardrail via Service Control Policies preventing large instance types; integrate with IAM Identity Center for permission set management.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **C** — Attach Root-level deny SCPs with a `StringNotEquals` condition on `aws:PrincipalAccount` to exclude Security OU accounts, plus a Sandbox-scoped SCP using `StringNotEquals` on `ec2:InstanceType`.

**Why it succeeds:** SCPs use an intersection model — effective permissions = IAM permissions ∩ SCP allow scope. A Deny at any level in the hierarchy overrides any Allow. Placing the CloudTrail/S3 deny at Root ensures universal coverage across all OUs without per-OU duplication. The `aws:PrincipalAccount` condition in the `StringEquals` pattern for the Condition block with `ArnNotLike` or an explicit account list carves out the Security OU's accounts. The `ec2:InstanceType` `StringNotEquals` condition on the Sandbox SCP correctly enforces instance size restrictions. This requires no changes to IAM Identity Center permission sets, minimising administrative overhead per the Well-Architected Operational Excellence pillar.

**Why alternatives fail:**
* **A)** Attaching individual deny SCPs per OU (Prod, NonProd, Sandbox) creates redundancy and misses future OUs unless explicitly updated — high operational overhead and drift risk. Removing AdministratorAccess from IAM Identity Center is unnecessary and breaks legitimate admin workflows.
* **B)** A deny-all-except-approved SCP at Root with per-OU allow SCPs is the "allowlist" model, which is extremely restrictive and requires enumerating every allowed action per OU — operationally unviable at scale and incompatible with IAM Identity Center's additive model.
* **D)** AWS Control Tower guardrails wrap SCPs but add management plane complexity and require Control Tower enrollment of all accounts. Custom guardrails for instance type restrictions are not natively supported in Control Tower's proactive/detective guardrail library — this would still require a custom SCP, eliminating Control Tower's value-add here.

---

## Scenario 2: Domain 1 – Design Solutions for Organizational Complexity

A global enterprise has 3 AWS accounts: Network Hub (owns Transit Gateway and Direct Connect Gateway), AppAccount A (us-east-1), and AppAccount B (ap-southeast-1). Both app accounts connect via TGW RAM share. On-premises routes are advertised via BGP over a Direct Connect hosted connection. The security team requires that all inter-VPC traffic and on-premises traffic flows through a centralised Network Firewall deployed in the Network Hub account. AppAccount B reports that traffic to on-premises is bypassing the firewall and routing directly via the TGW.

**Question:** What is the root cause and the correct architectural fix?

* **A)** The TGW route table for AppAccount B's VPC attachment is missing a static route for the on-premises CIDR pointing to the Network Firewall VPC attachment; add the static route and enable appliance mode on the Firewall VPC attachment.
* **B)** Direct Connect Gateway is not propagating routes to the TGW; re-enable BGP propagation in the TGW route table for the DXGW attachment.
* **C)** The TGW uses a single shared route table. A segregated routing model with two TGW route tables is needed: one for spoke VPCs (propagating only to Firewall VPC) and one for the Firewall VPC (propagating to all spokes and DXGW); additionally, appliance mode must be enabled on the Firewall VPC attachment to prevent asymmetric routing across AZs.
* **D)** Enable VPC flow logs in AppAccount B and use Athena queries to trace the traffic path; once confirmed, add a blackhole route on the TGW for on-premises CIDRs from AppAccount B.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **C** — The correct pattern is a two-route-table TGW architecture (Spoke RT + Firewall RT) with appliance mode enabled.

**Why it succeeds:** In the AWS TGW inspection architecture, spoke VPC attachments are associated with a "Spoke Route Table" that has a default route (0.0.0.0/0) pointing to the Firewall VPC attachment, with no propagation to other spokes or DXGW. The Firewall VPC attachment is associated with a "Firewall Route Table" that propagates from all spoke attachments and the DXGW attachment. This forces all traffic (inter-VPC and on-premises) through the firewall. Appliance mode is critical: without it, TGW performs ECMP across AZs, causing asymmetric flows that bypass stateful firewall inspection. This directly aligns with the AWS "Centralized Inspection Architecture" whitepaper pattern.

**Why alternatives fail:**
* **A)** Adding a static route to a single shared route table partially fixes on-premises routing but doesn't enforce east-west inter-VPC inspection. Single-table designs cannot simultaneously route spoke-to-spoke through the firewall without hairpinning issues.
* **B)** BGP propagation from DXGW is not the issue — the problem is TGW route table design. Re-enabling propagation without the two-table model would still bypass the firewall.
* **D)** Flow logs are a diagnostic tool, not an architectural fix. Adding a blackhole route for on-premises CIDRs would block all on-premises connectivity, not redirect it through the firewall.

---

## Scenario 3: Domain 2 – Design for New Solutions

A SaaS company is building a multi-tenant event-driven order processing platform on AWS. Requirements: 
1. Each tenant's events must be strictly isolated — one tenant's processing failure must not affect others. 
2. The platform must handle up to 500 tenant onboardings per day. 
3. Event ordering must be guaranteed per tenant. 
4. The solution must scale to millions of events/day without re-architecting. 
5. Cost must scale to near-zero for inactive tenants.

**Question:** Which architecture best satisfies all five requirements?

* **A)** Provision a dedicated Amazon MSK cluster per tenant with a Lambda consumer; use EventBridge to route events by tenant ID; store tenant configurations in DynamoDB.
* **B)** Use a single Amazon Kinesis Data Stream with tenant ID as the partition key; deploy a single Lambda consumer with per-tenant processing logic; use SQS FIFO queues per tenant for ordering guarantees.
* **C)** Use Amazon SQS FIFO queues (one per tenant, created dynamically on onboarding); route events via EventBridge rules with tenant-specific targets; process with Lambda consumers; use DynamoDB for tenant state; leverage SQS FIFO's MessageGroupId = tenant ID for ordering.
* **D)** Use a single Amazon MSK (Kafka) cluster with one topic per tenant; deploy ECS Fargate consumer groups per topic; use Auto Scaling based on MSK consumer group lag.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **C** — SQS FIFO per tenant + EventBridge routing + Lambda.

**Why it succeeds:** SQS FIFO with `MessageGroupId` guarantees strict per-group (per-tenant) ordering and provides blast-radius isolation — a poison message in one tenant's queue does not affect others. Dynamic queue creation via SDK on tenant onboarding is trivial and supports 500/day with no infrastructure provisioning. Lambda scales to zero for inactive tenants, meeting cost requirement 5. EventBridge's content-based routing on tenant attributes cleanly decouples producers from consumer infrastructure. DynamoDB stores tenant metadata with sub-millisecond lookup. This aligns with the Well-Architected Framework's microservices isolation and event-driven decoupling patterns.

**Why alternatives fail:**
* **A)** A dedicated MSK cluster per tenant is massively cost-prohibitive (MSK minimum cost ~$0.21/hr per broker, 3 brokers minimum = ~$450/month per tenant at 500 tenants/day onboarding rate). Completely fails cost requirement 5.
* **B)** A single Kinesis stream with Lambda: Kinesis ordering is per-shard, and a single stream cannot guarantee tenant isolation — a hot shard or Lambda concurrency issue affects all tenants. Bolting on per-tenant FIFO queues while maintaining a Kinesis stream creates an overly complex dual-ingestion path.
* **D)** MSK with one topic per tenant has per-topic partition overhead; Kafka minimum practical deployment costs are high; ECS Fargate consumers don't scale to zero; MSK clusters don't support near-zero cost for inactive tenants. Fails requirement 5.

---

## Scenario 4: Domain 2 – Design for New Solutions

A healthcare company is deploying a globally distributed patient records system. Requirements: 
1. RPO = 1 minute, RTO = 1 minute for database tier. 
2. The application must serve reads with < 100ms latency globally (users in US, EU, APAC). 
3. All writes must originate from the us-east-1 primary region only. 
4. Data must never leave a specific region for compliance — EU patient data stays in EU, APAC in APAC. 
5. Schema is relational with complex joins.

**Question:** Which database architecture satisfies ALL constraints?

* **A)** Deploy Amazon Aurora Global Database with us-east-1 as primary writer; EU and APAC as read replicas; use Route 53 latency-based routing to direct reads to the nearest replica; promote replicas in DR scenarios; enforce data residency via application-layer filtering.
* **B)** Deploy DynamoDB Global Tables with write routing pinned to us-east-1 via application logic; leverage DynamoDB Streams for cross-region replication; use DAX for sub-100ms reads; enforce data residency via table-level conditional writes.
* **C)** Deploy Amazon Aurora Global Database with us-east-1 as the primary write region; secondary clusters in eu-west-1 and ap-southeast-1 as read replicas; use CloudFront with Lambda@Edge to route reads to the geographically closest Aurora secondary endpoint; enforce EU/APAC data residency by storing region-specific data only in regional secondary clusters and routing writes through an API Gateway layer that validates residency before forwarding to Aurora primary.
* **D)** Deploy RDS Multi-AZ in us-east-1 with cross-region read replicas in eu-west-1 and ap-southeast-1; use Route 53 latency routing for reads; RTO/RPO achieved via automated failover promotion scripted in Lambda.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **A** — Aurora Global Database with Route 53 latency routing is the correct and exam-preferred answer, with an important nuance on data residency.

**Why it succeeds:** Aurora Global Database replicates with typical lag < 1 second (meeting RPO = 1 min) and supports managed failover in < 1 minute via the managed planned/unplanned failover API (meeting RTO = 1 min). Secondary clusters in eu-west-1 and ap-southeast-1 serve low-latency reads (Aurora replicas typically serve reads in single-digit ms within region). Route 53 latency-based routing directs users to the nearest regional endpoint. For data residency, since writes go to us-east-1 and replicate globally, the application-layer enforcement of residency (writing EU records only when routed through EU endpoints, enforcing at the API layer) is the pragmatic and exam-correct approach — Aurora Global Database does not natively enforce per-row regional data residency, so option C's description of routing is overcomplicated but the core Aurora Global DB pattern in A is sound.

**Why alternatives fail:**
* **B)** DynamoDB Global Tables uses an active-active, multi-master model — you cannot restrict writes to a single region natively. The "application logic" approach for write pinning is unreliable and not a supported DynamoDB architecture. Additionally, DynamoDB does not support complex relational joins, violating requirement 5.
* **C)** CloudFront + Lambda@Edge for database read routing is architecturally unsound — CloudFront caches HTTP responses, not database query results for live patient records. Lambda@Edge adds unnecessary latency and cost for database request routing; Route 53 latency routing is the correct and simpler mechanism.
* **D)** RDS cross-region read replica promotion for RTO/RPO < 1 minute is not achievable — replica promotion to primary is a manual or scripted process taking 5–30 minutes, failing both RTO and RPO requirements. Lambda-scripted failover adds fragility.

---

## Scenario 5: Domain 3 – Migration Planning

A large enterprise is migrating 200 on-premises virtual machines to AWS. The portfolio includes: 
1. 40 x Windows Server VMs running licensed SQL Server (bring-your-own-license). 
2. 80 x Linux VMs running Java microservices. 
3. 30 x VMs running legacy COBOL batch jobs (cannot be rehosted in containers). 
4. 50 x VMs running Oracle WebLogic with Java EE applications (refactoring budget available). 
The enterprise has a 24-month migration window and must minimize licensing costs.

**Question:** Which migration strategy mapping is most cost-optimal and technically correct?

* **A)** All 200 VMs: AWS Application Migration Service (MGN) lift-and-shift to EC2; post-migration, convert SQL Server to RDS; COBOL to Lambda; WebLogic to ECS Fargate.
* **B)** SQL Server VMs → EC2 Dedicated Hosts with BYOL SQL Server; Linux Java VMs → replatform to ECS Fargate (containerize); COBOL VMs → EC2 with Dedicated Hosts (BYOL Windows if needed); WebLogic → refactor to Amazon EKS with Spring Boot microservices using AWS Schema Conversion Tool for any database dependencies.
* **C)** SQL Server VMs → RDS for SQL Server with License Included (LI) to eliminate BYOL complexity; Linux Java VMs → lift-and-shift to EC2 then containerize to ECS Fargate over 6 months; COBOL VMs → EC2 (rehost, no refactor); WebLogic → AWS Elastic Beanstalk with Tomcat platform.
* **D)** SQL Server VMs → EC2 with BYOL SQL Server on Dedicated Hosts (preserving existing licenses per Microsoft mobility rules); Linux Java VMs → replatform to ECS Fargate; COBOL VMs → rehost to EC2 (dedicated or shared per licensing need); WebLogic → refactor to EKS/Spring Boot using AWS Migration Hub Refactor Spaces for incremental strangler-fig migration; use AWS MGN for initial rehost of all VMs, then execute refactoring tracks in parallel.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **D** — BYOL on Dedicated Hosts for SQL Server, ECS Fargate for Linux Java, EC2 rehost for COBOL, EKS refactor for WebLogic, with MGN as the migration engine.

**Why it succeeds:** Microsoft's License Mobility program requires Dedicated Hosts (not Dedicated Instances) for BYOL SQL Server on AWS — this is a hard licensing constraint. EC2 Dedicated Hosts allow customers to bring existing SQL Server datacenter licenses, avoiding re-purchase. Linux Java microservices containerize cleanly to ECS Fargate (serverless containers, no cluster management). COBOL batch jobs cannot be containerized (requirement 3) — EC2 rehost is the only viable path. WebLogic-to-Spring Boot is a well-documented AWS migration pattern; Refactor Spaces provides the strangler-fig proxy pattern, allowing incremental traffic shifting from legacy WebLogic to new EKS microservices without a big-bang cutover. AWS MGN is the AWS-recommended rehost tool (replaces SMS) supporting all VM types.

**Why alternatives fail:**
* **A)** COBOL to Lambda is architecturally infeasible — Lambda has a 15-minute timeout and no support for legacy COBOL runtimes. Batch COBOL jobs require persistent, long-running compute.
* **B)** Correct on SQL Server Dedicated Hosts, but misses AWS MGN as the migration engine and doesn't address the 24-month timeline with parallel tracks — purely sequential migration risks missing the window.
* **C)** RDS for SQL Server License Included (LI) is significantly more expensive than BYOL for 40 servers over 24 months, directly contradicting the cost-minimization requirement. LI pricing bundles Microsoft license cost into the RDS hourly rate, which is wasteful when the enterprise already owns licenses.

---

## Scenario 6: Domain 3 – Migration Planning

A company is migrating a 500TB on-premises data warehouse to Amazon S3 + Athena. The data is stored on a NAS (NFS protocol) in an on-premises data center. The connection to AWS is via a 1 Gbps Direct Connect link shared with production traffic (production traffic uses ~600 Mbps on average). The migration must complete in 30 days without impacting production. Post-migration, ongoing nightly incremental syncs of ~50GB must continue.

**Question:** Which migration and ongoing sync architecture is optimal?

* **A)** Use AWS DataSync over Direct Connect with bandwidth throttling to 300 Mbps; schedule transfers during off-peak hours; for ongoing sync, continue DataSync nightly jobs.
* **B)** Order AWS Snowball Edge Storage Optimized (multiple devices) for the initial 500TB bulk migration; configure DataSync agent on-premises for ongoing nightly 50GB incremental sync over Direct Connect with a 200 Mbps throttle.
* **C)** Use AWS Storage Gateway File Gateway to mount S3 as NFS; migrate data by copying files from NAS to Storage Gateway (which uploads to S3); ongoing sync is handled automatically by Storage Gateway's cache invalidation.
* **D)** Use S3 Transfer Acceleration over the internet as a parallel path alongside Direct Connect; split the 500TB dataset across both paths; use S3 Multipart Upload for files > 100MB.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Snowball Edge for bulk + DataSync for ongoing incremental.

**Why it succeeds:** At 300 Mbps usable bandwidth (1 Gbps - 600 Mbps production - overhead), transferring 500TB would take: `500TB × 8Tb/TB ÷ 0.3 Gbps = ~148 days` — far exceeding the 30-day window. AWS Snowball Edge Storage Optimized holds 80TB usable per device, so ~7 devices cover 500TB. Physical transfer eliminates network dependency for bulk migration. DataSync over DX for 50GB nightly = `50GB × 8 ÷ 200Mbps = ~33 minutes` — well within a nightly window at 200 Mbps throttle, leaving 400 Mbps for production. DataSync handles NFS source natively, preserves metadata, and supports scheduling.

**Why alternatives fail:**
* **A)** As calculated, 300 Mbps over DX for 500TB requires ~148 days — physically impossible in 30 days. DataSync throttling cannot overcome the fundamental bandwidth math.
* **C)** Storage Gateway File Gateway is designed for hybrid access patterns, not bulk data migration. Copying 500TB through a gateway cache is extremely slow and operationally fragile; the gateway cache would overflow repeatedly, causing repeated S3 upload retries.
* **D)** S3 Transfer Acceleration adds cost and internet latency. Combining it with DX for a split transfer requires custom orchestration. More importantly, this doesn't solve the core bandwidth constraint — the internet path would be limited by the on-premises uplink and would still take well over 30 days for 500TB.

---

## Scenario 7: Domain 4 – Cost Control

A company runs a real-time analytics platform with the following components: 
1. 20 x r5.4xlarge EC2 instances (On-Demand) for Spark processing running 24/7. 
2. An Amazon Kinesis Data Stream with 100 shards. 
3. Amazon Redshift cluster (dc2.8xlarge × 4 nodes) running queries only 8 hours per day (business hours). 
4. S3 storage: 800TB total, with 600TB not accessed in > 180 days. 
5. NAT Gateway processing 50TB/month of data egress from private subnets.

**Question:** Which cost optimization actions deliver the GREATEST savings with acceptable operational risk?

* **A)** Convert EC2 to Spot Instances; reduce Kinesis to 10 shards; migrate Redshift to Redshift Serverless; move 600TB S3 to Glacier Instant Retrieval; replace NAT Gateway with VPC endpoints for S3.
* **B)** Purchase 1-year Compute Savings Plans for EC2 (covering r5.4xlarge baseline); implement Kinesis shard-level auto-scaling via Application Auto Scaling; use Redshift pause/resume scheduling (pause after 8 hrs, resume before business hours); transition 600TB S3 to S3 Glacier Deep Archive via lifecycle policy; add S3 Gateway Endpoint to eliminate NAT Gateway S3 traffic charges.
* **C)** Convert EC2 to Reserved Instances (3-year, all-upfront); reduce Kinesis shards to 5; delete the Redshift cluster and migrate to Athena; move all 800TB S3 to Glacier Deep Archive; remove NAT Gateway and use internet gateway for all traffic.
* **D)** Purchase EC2 Savings Plans; migrate Redshift to Aurora Serverless; keep Kinesis shards at 100; apply S3 Intelligent-Tiering to all 800TB; use NAT Instance (t3.medium) instead of NAT Gateway.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Savings Plans + Kinesis auto-scaling + Redshift pause/resume + Deep Archive + S3 Gateway Endpoint.

**Why it succeeds:**
* **EC2:** EC2 Savings Plans (1-year Compute) provide up to 66% savings over On-Demand for 24/7 Spark instances without instance family lock-in.
* **Kinesis:** Kinesis auto-scaling (Application Auto Scaling using `PutScalingPolicy` on the `aws:kinesis:stream:shard-count` dimension) right-sizes shards to actual throughput demand, reducing idle shard costs.
* **Redshift:** Redshift pause/resume (native scheduler) eliminates 16 hrs/day of dc2 cluster cost — saving ~66% of Redshift compute.
* **S3:** S3 Glacier Deep Archive at $0.00099/GB/month vs S3 Standard at $0.023/GB/month = ~95% storage cost reduction for 600TB of cold data.
* **NAT Gateway:** S3 Gateway Endpoint (free) routes all S3 traffic from private subnets through the VPC endpoint, bypassing NAT Gateway. At $0.045/GB NAT processing for 50TB/month, this eliminates ~$2,250/month.

**Why alternatives fail:**
* **A)** Spot Instances for 24/7 Spark processing is high-risk — Spark job interruptions require checkpointing and retry logic; without that, data loss and job failures make this operationally unacceptable. Glacier Instant Retrieval is more expensive than Deep Archive for data not needing rapid retrieval.
* **C)** 3-year all-upfront RIs reduce flexibility and Compute Savings Plans cover the same instance types with more flexibility. Deleting Redshift for Athena changes the query engine significantly and may break existing SQL workloads. Removing the NAT Gateway entirely and using IGW directly exposes private subnets to the internet — a security violation.
* **D)** EC2 Savings Plans are correct, but migrating Redshift to Aurora Serverless is a significant workload migration with unknown cost impact and query compatibility issues. S3 Intelligent-Tiering on all 800TB adds monitoring charges ($0.0025/1000 objects) and is suboptimal for data definitively known to be cold after 180 days — a lifecycle policy to Deep Archive is cheaper and simpler.

---

## Scenario 8: Domain 4 – Cost Control

A company's AWS bill shows $850,000/month. The FinOps team identifies: 
1. Data transfer costs of $180,000/month (inter-region and internet egress). 
2. EC2 coverage by Savings Plans is only 42%. 
3. RDS Multi-AZ instances running in dev/test accounts 24/7. 
4. CloudWatch custom metrics generating $45,000/month. 
5. API Gateway calls at $120,000/month for a high-traffic public API.

**Question:** Which prioritized set of actions reduces costs most effectively?

* **A)** (1) Analyze VPC Flow Logs to identify top egress flows, implement CloudFront for public assets and PrivateLink for cross-account service access; (2) Purchase Compute Savings Plans to reach 80% EC2 coverage; (3) Use RDS instance scheduler (AWS Instance Scheduler) to stop dev/test RDS 16hrs/day; (4) Reduce CloudWatch metric resolution from 1-second to 1-minute (standard resolution); (5) Migrate high-traffic API to CloudFront + API Gateway with caching or evaluate HTTP API vs REST API downgrade.
* **B)** Move all workloads to a single region to eliminate inter-region transfer; buy 3-year Reserved Instances for all EC2; delete dev/test RDS; remove all custom CloudWatch metrics; migrate API Gateway to Application Load Balancer.
* **C)** Use AWS Cost Anomaly Detection to identify waste; enable S3 Intelligent-Tiering; convert API Gateway to GraphQL via AppSync; stop all non-production workloads at night using Lambda.
* **D)** Implement VPC Peering to eliminate NAT Gateway costs; use Savings Plans for EC2; enable RDS automated stop for dev/test; keep custom metrics but reduce dimensions; use API Gateway usage plans to throttle expensive callers.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **A** — Systematic, service-by-service optimization with highest ROI actions per line item.

**Why it succeeds:** Each action targets the specific root cause of each cost line item:
* **Data transfer ($180K):** CloudFront eliminates repeated origin egress for cacheable content; AWS PrivateLink for cross-account API calls replaces NAT Gateway + internet routing, reducing inter-AZ and egress charges.
* **Savings Plans (42% coverage):** AWS recommends 80%+ Savings Plan coverage for stable baseline workloads. Compute Savings Plans are preferred over EC2 RIs for flexibility across instance families.
* **Dev/Test RDS:** AWS Instance Scheduler stops RDS instances on schedule — Multi-AZ RDS in dev has no justification; stopping 16hrs/day = 66% compute reduction.
* **CloudWatch ($45K):** Custom metrics at 1-second high resolution cost $0.02/metric/month vs $0.01 at standard. Downgrading non-critical metrics to 1-minute resolution halves their cost.
* **API Gateway ($120K):** HTTP API is up to 71% cheaper than REST API for equivalent functionality without REST-specific features. CloudFront caching in front of API Gateway caches responses for GET/HEAD, dramatically reducing backend invocations.

**Why alternatives fail:**
* **B)** Consolidating to one region is architecturally catastrophic for resilience and ignores compliance/latency requirements. Deleting dev/test RDS eliminates development capability entirely.
* **C)** AppSync/GraphQL migration is a full re-architecture — not a cost optimization action within a reasonable timeframe. Cost Anomaly Detection is diagnostic, not remedial.
* **D)** VPC Peering doesn't eliminate NAT Gateway costs for internet-bound traffic — only for intra-VPC routing. Throttling API callers reduces functionality, not infrastructure cost.

---

## Scenario 9: Domain 5 – Continuous Improvement for Existing Solutions

A production e-commerce platform experiences weekly database failovers on its Aurora MySQL cluster during peak traffic (Black Friday-scale loads). Investigations show: 
1. The writer instance CPU hits 95% during peak. 
2. Application connection pool exhaustion causes cascading Lambda timeouts. 
3. Post-failover, DNS propagation takes 30–45 seconds, during which transactions fail. 
4. The application doesn't distinguish between read and write queries.

**Question:** Which set of improvements resolves ALL four issues?

* **A)** Upgrade Aurora writer to a larger instance class; increase Lambda connection pool size via environment variables; reduce Aurora's DNS TTL; add a read replica.
* **B)** Enable Aurora Auto Scaling for read replicas; implement RDS Proxy in front of the Aurora cluster (using the Proxy's writer and reader endpoints); configure the application to send reads to the reader endpoint and writes to the writer endpoint; enable Aurora Global Database for cross-region DR.
* **C)** Implement RDS Proxy (multiplexes Lambda connections to Aurora, eliminating connection pool exhaustion); configure Aurora reader endpoints in the application for read queries; implement Aurora Serverless v2 for the writer to auto-scale compute on demand; use Route 53 ARC (Application Recovery Controller) readiness checks to manage failover DNS cut-over.
* **D)** Migrate to DynamoDB for all product catalog reads; keep Aurora for transactional writes; use ElastiCache Redis for session data; implement SQS to dequeue Lambda invocations during peak.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **C** — RDS Proxy + Aurora Reader Endpoints + Aurora Serverless v2 + Route 53 ARC.

**Why it succeeds:**
* **Issue 1 (CPU 95%):** Aurora Serverless v2 auto-scales ACUs (Aurora Capacity Units) in fine-grained increments (0.5 ACU steps) within seconds of load increase — eliminates CPU saturation without manual instance resizing.
* **Issue 2 (Connection pool exhaustion):** RDS Proxy maintains a persistent connection pool to Aurora and multiplexes thousands of Lambda ephemeral connections into a small set of database connections. Lambda's per-invocation connection creation is the root cause; Proxy resolves this natively.
* **Issue 3 (DNS failover latency):** Route 53 ARC provides zonal shift and readiness checks with automated DNS failover faster than the default Aurora DNS TTL approach. ARC can shift traffic in < 1 minute with health-check-driven DNS updates.
* **Issue 4 (No read/write split):** Aurora's cluster reader endpoint load-balances across all read replicas. Routing read queries to the reader endpoint reduces writer load.

**Why alternatives fail:**
* **A)** Manually upgrading instance class is reactive and doesn't scale for unpredictable peaks. Increasing Lambda connection pool size via environment variables doesn't solve the fundamental problem — more Lambda concurrent invocations still overwhelm Aurora with connections. Reducing DNS TTL helps marginally but doesn't eliminate the 30-45 second gap.
* **B)** Correct on RDS Proxy and reader endpoints, but Aurora Global Database is for cross-region DR (RPO seconds), not for intra-region failover speed improvement. It adds cost without solving the 30-45 second DNS propagation issue.
* **D)** Migrating to DynamoDB is a complete re-architecture with schema redesign — far beyond the scope of "continuous improvement." ElastiCache for sessions is valid but doesn't address the core database failover and connection exhaustion issues.

---

## Scenario 10: Domain 5 – Continuous Improvement for Existing Solutions

A media company runs a global video streaming platform. The current CDN architecture uses CloudFront with S3 origins. Issues reported: 
1. Cache hit ratio is only 38% (benchmark: >85%). 
2. Origin S3 requests are causing S3 request costs of $45,000/month. 
3. Users in Southeast Asia report 4-6 second TTFB (Time to First Byte) for video segments. 
4. Some video segments are being served incorrectly (wrong resolution variant) to certain device types.

**Question:** Which combination of CloudFront improvements addresses all four issues?

* **A)** Enable CloudFront Origin Shield in a central region; increase CloudFront default TTL to 86400s; use Lambda@Edge at the origin request event to rewrite URLs based on User-Agent; enable CloudFront real-time logs to diagnose cache misses.
* **B)** Enable CloudFront Origin Shield in the AWS region closest to the S3 origin; configure Cache Policies with appropriate TTLs (removing query strings and headers from cache keys that vary unnecessarily); implement CloudFront Functions at viewer request to normalize User-Agent headers to device categories (mobile/desktop/TV) and modify the cache key; add a regional edge cache in ap-southeast-1 by selecting the nearest Origin Shield region.
* **C)** Migrate S3 origin to an ALB-fronted EC2 fleet for dynamic content serving; use CloudFront with path-based behaviors; implement WAF with device detection rules; enable S3 Transfer Acceleration for the origin.
* **D)** Switch CDN to AWS Global Accelerator; configure S3 buckets in each region; use Route 53 geolocation routing to the nearest S3 bucket; implement device detection in the application layer.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Origin Shield + Cache Policies + CloudFront Functions + regional Origin Shield placement.

**Why it succeeds:**
* **Issue 1 (38% cache hit ratio):** Low cache ratio is almost always caused by cache key pollution — headers, cookies, or query strings in the cache key that vary unnecessarily. CloudFront Cache Policies allow precise control over what's included in the cache key. Removing irrelevant headers/cookies dramatically improves cache hit ratio.
* **Issue 2 (S3 cost $45K):** CloudFront Origin Shield adds a centralised caching layer between CloudFront edge locations and the S3 origin, collapsing redundant origin requests into one. Origin Shield reduces origin load by up to 75%.
* **Issue 3 (TTFB in SEA):** Selecting the ap-southeast-1 (Singapore) Origin Shield region minimises the CloudFront edge → Origin Shield → S3 round-trip for SEA users. CloudFront's 400+ edge PoPs in SEA then serve from the regional cache.
* **Issue 4 (Wrong resolution variant):** CloudFront Functions (not Lambda@Edge) run at viewer request with sub-millisecond execution — ideal for normalising User-Agent into device category and modifying the cache key so that mobile/desktop/TV users receive their correct video variant from cache.

**Why alternatives fail:**
* **A)** Lambda@Edge at origin request fires only on cache misses — it doesn't affect the cache key at viewer request time, so the wrong variant can still be cached and served. Lambda@Edge has cold start latency; CloudFront Functions are better for simple header manipulation.
* **C)** Migrating to ALB+EC2 for static video segments is unnecessary and costly — S3 is the correct origin for static content. S3 Transfer Acceleration is for uploads, not CDN performance.
* **D)** Global Accelerator optimises TCP/UDP routing for non-HTTP workloads and doesn't provide content caching. Replacing a CDN with Global Accelerator for video streaming eliminates all caching benefits and massively increases origin load and cost.

---

## Scenario 11: Domain 1 – Design Solutions for Organizational Complexity

An enterprise has implemented IAM Identity Center with Active Directory as the identity source (via AD Connector). They have 15 AWS accounts in an Organization. Requirement: 
1. A group `SRE-Team` in AD must have read-only access to CloudWatch, EC2 describe actions, and SSM Session Manager access in all 15 production accounts. 
2. The `SRE-Team` must never have IAM or billing access. 
3. When an SRE leaves the company, access must be revoked within 5 minutes across all 15 accounts. 
4. The AD group membership is managed by the HR system, not by AWS admins.

**Question:** Which architecture satisfies all requirements with least privilege and operational efficiency?

* **A)** Create 15 IAM roles (one per account) with the required policies; SREs assume roles via cross-account trust; sync AD group to IAM using custom Lambda that polls AD every 5 minutes.
* **B)** Create a custom Permission Set in IAM Identity Center with an inline policy granting `CloudWatch:Get*/List*`, `ec2:Describe*`, and `ssm:StartSession`; create an Account Assignment mapping the AD SRE-Team group to this Permission Set across all 15 accounts; configure IAM Identity Center to use AD Connector as the identity source with sync interval set to near-real-time (AD Connector syncs on authentication).
* **C)** Create Permission Sets in IAM Identity Center; use AWS Organizations Tag Policies to tag accounts as Env=Prod; write a Lambda that auto-assigns the Permission Set to tagged accounts; AD group sync handled by IAM Identity Center's SCIM provisioning.
* **D)** Federate directly using SAML 2.0 between AD FS and each of the 15 AWS accounts; create IAM roles with SAML trust in each account; manage group membership in AD; session duration set to 1 hour for fast expiry.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — IAM Identity Center Permission Sets + AD group mapping + Account Assignments across all 15 accounts.

**Why it succeeds:** IAM Identity Center with AD Connector does not sync users/groups proactively — it authenticates on-demand. When an SRE authenticates, IAM Identity Center queries AD in real time for group membership. When an SRE is removed from the `SRE-Team` AD group by HR, their next authentication fails the group check. More critically, existing sessions expire based on the Permission Set session duration (set to 5 minutes or configured to match requirements). Account Assignments in IAM Identity Center propagate a single Permission Set to all 15 accounts simultaneously — no per-account role management. The inline policy in the Permission Set precisely scopes CloudWatch/EC2/SSM without IAM or billing permissions, satisfying least privilege.

**Why alternatives fail:**
* **A)** Managing 15 IAM roles manually and a Lambda polling AD every 5 minutes is operationally fragile — Lambda failure creates a security gap. IAM roles don't automatically invalidate active sessions when the Lambda removes the user.
* **C)** Tag Policies and Lambda auto-assignment is a complex, custom solution that duplicates IAM Identity Center's native Account Assignment capability. SCIM provisioning is for IdPs like Okta/Azure AD, not AD Connector (which uses AD authentication directly, not SCIM).
* **D)** Per-account SAML federation requires maintaining 15 separate IdP/SP configurations in AD FS and 15 IAM SAML providers — massive operational overhead. Session expiry at 1 hour means access persists for up to 60 minutes after an SRE is offboarded, violating the 5-minute requirement.

---

## Scenario 12: Domain 2 – Design for New Solutions

A company wants to build a real-time fraud detection pipeline for financial transactions. Requirements: 
1. Ingest 500,000 transactions/second at peak. 
2. ML model inference must complete in < 50ms per transaction. 
3. Fraudulent transactions must trigger an immediate block at the payment processor API within 100ms of detection. 
4. All transactions must be stored for 7-year regulatory retention with query capability. 
5. The pipeline must survive a full AZ outage with zero data loss.

**Question:** Which architecture satisfies all five requirements?

* **A)** API Gateway → Kinesis Data Streams (500 shards) → Lambda (ML inference via SageMaker endpoint) → SNS → SQS → Lambda (block transaction); S3 + Glacier for retention; Multi-AZ Kinesis (built-in).
* **B)** NLB → EC2 Auto Scaling (ingest tier) → Amazon MSK (Kafka, Multi-AZ, replication factor 3) → ECS Fargate consumers (SageMaker real-time endpoint for inference) → EventBridge (route fraud events) → Lambda (call payment processor block API); Kinesis Data Firehose → S3 (7-year lifecycle to Deep Archive); MSK provides AZ-fault-tolerant replication.
* **C)** API Gateway → Kinesis Data Streams → Kinesis Data Analytics (Flink) for real-time ML scoring (RANDOM_CUT_FOREST anomaly detection) → EventBridge → Lambda (block API call); S3 + Athena for 7-year retention and querying; Kinesis cross-AZ replication natively.
* **D)** SQS FIFO → Lambda (ML inference) → Step Functions (fraud workflow orchestration) → SNS (notify payment processor); DynamoDB for hot storage; S3 Glacier for archival.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — MSK (Kafka) + ECS Fargate + SageMaker + EventBridge + Firehose → S3.

**Why it succeeds:**
* **500K TPS (Req 1):** Amazon MSK with Kafka handles millions of messages/second natively. Kafka's partition model provides horizontal scale. NLB at the ingest tier handles the TCP connection volume.
* **< 50ms inference (Req 2):** SageMaker real-time inference endpoints with ECS Fargate consumers (long-running, no cold start) provide consistent low-latency inference. Lambda cold starts make sub-50ms p99 guarantees unreliable at this scale.
* **100ms block (Req 3):** EventBridge routes fraud events with sub-millisecond routing latency to Lambda, which calls the payment processor synchronously within the 100ms budget.
* **7-year retention + query (Req 4):** Kinesis Firehose buffers and lands data to S3; S3 Lifecycle transitions to Deep Archive; Athena provides SQL query capability over S3.
* **AZ fault tolerance (Req 5):** MSK Multi-AZ with replication factor 3 ensures no data loss during AZ outage. Kafka's ISR (In-Sync Replicas) guarantees acknowledged writes survive AZ loss.

**Why alternatives fail:**
* **A)** Lambda for ML inference at 500K TPS will hit concurrency limits (default 10,000 per region) and cold starts will exceed 50ms. API Gateway has a 29-second timeout but at this ingestion rate, the API Gateway HTTP overhead adds latency.
* **C)** Kinesis Data Analytics (Flink) with RANDOM_CUT_FOREST is an anomaly detection algorithm — not a trained fraud ML model. It cannot run a custom SageMaker model endpoint within the Flink job. The architecture also doesn't address the 100ms block requirement with sufficient precision.
* **D)** SQS FIFO is limited to 3,000 TPS per API per queue — utterly insufficient for 500K TPS. Step Functions add orchestration overhead (100ms+ per state transition), breaking the 100ms block requirement.

---

## Scenario 13: Domain 3 – Migration Planning

A company is migrating from on-premises Oracle Database 19c (12TB, 2,000 stored procedures, 150 database-linked servers) to AWS. The go-live deadline is 6 months. The Oracle license is expiring and will not be renewed. Constraints: 
1. Must eliminate Oracle licensing cost entirely. 
2. Application team estimates 60% of stored procedures can be auto-converted, 40% require manual rewrite. 
3. Zero downtime migration — the application cannot be offline during cutover. 
4. The new database must handle 20,000 read IOPS and 5,000 write IOPS.

**Question:** Which migration approach is technically correct and meets all constraints?

* **A)** Use AWS SCT to convert Oracle schema and stored procedures to PostgreSQL-compatible syntax; migrate to Amazon Aurora PostgreSQL; use AWS DMS with ongoing replication (CDC) to sync data continuously; use SCT's assessment report to prioritize manual conversion work; cutover by stopping DMS replication and redirecting the application connection string.
* **B)** Use AWS DMS to migrate directly from Oracle to RDS for MySQL; use SCT for stored procedure conversion; cutover via DNS change; Aurora MySQL for scaling.
* **C)** Migrate to Amazon RDS for Oracle first (lift-and-shift, BYOL); decommission on-premises; then perform a second migration from RDS Oracle to Aurora PostgreSQL over 6 months.
* **D)** Use SCT to convert Oracle to Aurora PostgreSQL Serverless v2; use DMS for full-load + CDC replication; perform blue/green deployment with Aurora's native Blue/Green feature for zero-downtime cutover.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **D** — SCT → Aurora PostgreSQL Serverless v2 + DMS CDC + Aurora Blue/Green Deployment.

**Why it succeeds:**
* **Eliminate Oracle licensing (Req 1):** Aurora PostgreSQL is fully open-source-compatible, no Oracle license required.
* **Stored procedure conversion (Req 2):** AWS SCT auto-converts up to 60% of Oracle PL/SQL to PL/pgSQL. SCT's assessment report explicitly flags the 40% requiring manual intervention, with action items and complexity ratings.
* **Zero downtime (Req 3):** Aurora Blue/Green Deployment creates a staging (green) environment as an exact replica, applies all changes, and performs a managed switchover in < 1 minute with automatic traffic redirection — the lowest-risk zero-downtime cutover mechanism natively supported by Aurora.
* **IOPS requirements (Req 4):** Aurora PostgreSQL Serverless v2 auto-scales ACUs; for dedicated IOPS, Aurora provisioned with io1 or gp3 storage handles 20,000+ read IOPS. Aurora's read replicas additionally offload read traffic.
* DMS with CDC replication keeps the target Aurora in sync with Oracle during the migration window, then Blue/Green switchover stops DMS and redirects traffic atomically.

**Why alternatives fail:**
* **A)** Correct approach (SCT + Aurora PostgreSQL + DMS CDC), but the cutover method (stopping DMS and redirecting connection string) is high-risk and not zero-downtime — there's a manual window. Aurora Blue/Green Deployment (option D) is the superior cutover mechanism.
* **B)** MySQL is not the optimal target for Oracle PL/SQL migration — PostgreSQL's PL/pgSQL is structurally closer to Oracle PL/SQL, yielding higher SCT auto-conversion rates. Oracle-to-MySQL conversion requires more manual effort.
* **C)** Migrating to RDS Oracle (BYOL) first means paying for BYOL Oracle licenses during the 6-month migration period — directly violating the cost constraint of eliminating Oracle licensing.

---

## Scenario 14: Domain 4 – Cost Control

A startup's AWS costs have grown from $20K to $180K/month in 6 months with no significant revenue growth. AWS Cost Explorer shows: 
1. 40% of cost is EC2 — mostly On-Demand, mixed instance types, utilization averaging 15%. 
2. 25% is data transfer — primarily EC2-to-EC2 cross-AZ and S3 GET requests from EC2 in private subnets. 
3. 20% is RDS — Multi-AZ in dev/test accounts running 24/7. 
4. 15% is miscellaneous (CloudWatch Logs ingestion: $18K/month; unused Elastic IPs: $2K/month; unattached EBS volumes: $4K/month).

**Question:** Rank and implement the highest-impact cost reduction measures:

* **A)** Purchase 3-year all-upfront Reserved Instances for all EC2; implement cross-AZ traffic reduction; stop dev/test RDS; clean up unused resources.
* **B)** Right-size EC2 using AWS Compute Optimizer recommendations; purchase Compute Savings Plans (1-year) for the right-sized baseline; add S3 Gateway Endpoints and VPC Endpoints to eliminate cross-AZ data transfer for S3/AWS service traffic; implement RDS Instance Scheduler for dev/test; configure CloudWatch Logs subscription filters to route only ERROR/CRITICAL logs to CloudWatch and route DEBUG/INFO to S3 via Firehose; release unused EIPs and delete unattached EBS volumes.
* **C)** Convert all EC2 to Spot Instances; use S3 Intelligent-Tiering; delete dev RDS and use SQLite locally; remove CloudWatch Logs entirely; terminate unused resources.
* **D)** Migrate all workloads to Fargate (no idle EC2 cost); use DynamoDB instead of RDS; implement Lambda for all compute; remove CloudWatch Logs and use third-party logging.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Right-size first, then commit; eliminate transfer waste; schedule dev/test; clean up orphaned resources.

**Why it succeeds:** The Well-Architected Cost Optimization pillar mandates right-size before committing to pricing. At 15% average utilization, EC2 instances are significantly over-provisioned. Compute Optimizer provides ML-based rightsizing recommendations. Only after rightsizing should Savings Plans be purchased to lock in the optimized baseline. S3 Gateway Endpoints (free) eliminate all S3-bound EC2 data transfer charges that currently route through NAT Gateway ($0.045/GB). VPC endpoints for other AWS services eliminate cross-AZ traffic to regional services. CloudWatch Logs at $0.50/GB ingestion — filtering to ERROR+ and routing verbose logs to S3 (via Firehose at $0.029/GB) can reduce CloudWatch Logs costs by 80–90%.

**Why alternatives fail:**
* **A)** Purchasing 3-year RIs for over-provisioned, mixed instance types locks in waste at high cost. The 15% utilization means 85% of committed cost is idle. Must right-size first.
* **C)** Spot Instances for unknown workloads (no mention of interruption tolerance) is high-risk. Removing CloudWatch Logs entirely eliminates observability — operationally unacceptable.
* **D)** Migrating all EC2 to Fargate and all RDS to DynamoDB is a complete re-architecture estimated at months of engineering effort — not a cost optimization action. Fargate has per-vCPU/GB pricing that can exceed EC2 for consistently high-utilization workloads.

---

## Scenario 15: Domain 5 – Continuous Improvement for Existing Solutions

A fintech company's API Gateway + Lambda architecture is experiencing: 
1. P99 latency of 8 seconds (SLA: < 500ms). 
2. Lambda function cold starts averaging 3.2 seconds (Java runtime). 
3. 25% error rate on POST /transactions during peak (500 TPS). 
4. DynamoDB throttling errors correlating with the error rate. 
5. Downstream payment processor API times out at 3 seconds, causing Lambda to retry, exhausting concurrency.

**Question:** Which improvements address ALL five issues systematically?

* **A)** Increase Lambda memory to 10GB; enable Provisioned Concurrency for Lambda; add DynamoDB Auto Scaling; increase API Gateway timeout to 29 seconds; implement exponential backoff in Lambda for payment processor retries.
* **B)** Migrate Lambda runtime from Java to Python or Node.js; enable Lambda Provisioned Concurrency (scheduled scaling for peak hours); implement DynamoDB on-demand capacity (eliminates throttling); use SQS queue between Lambda and payment processor (async, Lambda puts transaction to SQS, returns 202 Accepted, separate Lambda processes queue with retry logic); implement API Gateway caching for idempotent GET endpoints.
* **C)** Replace Lambda with ECS Fargate (no cold starts); replace DynamoDB with Aurora Serverless; implement Circuit Breaker pattern via App Mesh; use SQS for payment processor integration.
* **D)** Enable Lambda SnapStart for Java runtime; implement DynamoDB DAX for caching; use Step Functions for payment processor retry orchestration with exponential backoff; implement API Gateway throttling (10,000 RPS limit) to protect Lambda concurrency.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** + **D** combined — but if forced to choose one, **D** is most complete for the Java runtime case.

**Why D succeeds:**
* **Cold starts (Issue 2):** Lambda SnapStart for Java (Corretto 11/17/21 runtimes) pre-initialises the execution environment and restores from a snapshot, reducing Java cold starts from 3+ seconds to < 1 second — the most impactful fix for Java Lambda cold starts without changing runtime.
* **DynamoDB throttling (Issue 4):** DAX provides microsecond read caching; for write throttling, DynamoDB on-demand mode (per B) or provisioned with Auto Scaling resolves write throttle. DAX addresses read-heavy patterns.
* **Payment processor timeout/retry (Issue 5):** Step Functions with Wait states and exponential backoff orchestrates retries without blocking Lambda concurrency — Lambda invokes Step Functions (async), returns immediately, freeing concurrency.
* **API Gateway throttling:** Protects the Lambda concurrency pool from being overwhelmed at 500 TPS.

**Why B is partially correct:** Switching to Python/Node.js eliminates Java's JVM startup cost but requires rewriting the entire Lambda function — significant engineering effort when SnapStart achieves the same result for Java. The SQS async pattern for payment processor is architecturally sound.

**Why alternatives fail:**
* **A)** Increasing Lambda memory doesn't fix cold starts for Java (JVM initialization is time-based, not memory-based). Increasing API Gateway timeout to 29 seconds raises the SLA violation ceiling — not a solution. Exponential backoff in Lambda still blocks Lambda concurrency during retries.
* **C)** Migrating to ECS Fargate eliminates cold starts but requires complete re-architecture of the serverless stack — disproportionate to the problem scope. Aurora Serverless for DynamoDB is a schema migration.

---

## Scenario 16: Domain 1 – Design Solutions for Organizational Complexity

A company operates in 8 AWS regions with 120 accounts under AWS Organizations. The network team must implement centralized DNS resolution so that: 
1. On-premises hosts can resolve `*.internal.corp` (private Route 53 hosted zones). 
2. AWS Lambda and EC2 in all VPCs can resolve on-premises hostnames `(*.onprem.corp)` via on-premises DNS servers (10.0.0.53, 10.0.0.54). 
3. The solution must function over Direct Connect and must not require a DNS server deployed on EC2. 
4. All changes must be centrally managed.

**Question:** Which architecture satisfies all constraints?

* **A)** Deploy EC2-based BIND DNS servers in a hub VPC per region; configure on-premises DNS to forward to BIND servers; configure VPC DHCP option sets to use BIND server IPs.
* **B)** Create Route 53 Resolver Inbound Endpoints in a centralized Network Hub VPC (one per region); associate the private hosted zone `*.internal.corp` with the Hub VPC; configure on-premises DNS to forward `*.internal.corp` queries to the Inbound Endpoint IPs over Direct Connect; create Route 53 Resolver Outbound Endpoints in the Hub VPC with a Forwarding Rule for `*.onprem.corp` → 10.0.0.53/10.0.0.54; share the Forwarding Rule via AWS RAM to all 120 account VPCs; associate VPCs with the rule.
* **C)** Use Route 53 Resolver DNS Firewall to intercept all DNS queries; forward on-premises queries via a DNS firewall rule group; associate with all VPCs via RAM.
* **D)** Create a private hosted zone `*.onprem.corp` in Route 53 that mirrors all on-premises DNS records; configure zone delegation from on-premises DNS to Route 53; use Route 53 health checks to detect on-premises DNS changes.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Route 53 Resolver Inbound + Outbound Endpoints in a hub VPC, shared via RAM.

**Why it succeeds:** Route 53 Resolver is the AWS-managed DNS service (no EC2 required, satisfying constraint 3):
* **Inbound Endpoints** (ENIs in the Hub VPC) receive DNS queries from on-premises over Direct Connect. On-premises DNS forwards `*.internal.corp` to these ENI IPs. Route 53 responds from the associated private hosted zone.
* **Outbound Endpoints** send queries from AWS to on-premises DNS servers (10.0.0.53/54) for `*.onprem.corp`. Forwarding Rules define this target.
* **AWS RAM** shares the Resolver Rules (Forwarding Rules) to all 120 accounts — VPCs in those accounts associate with the shared rule and automatically forward `*.onprem.corp` to on-premises. Centralized management in one network account.
* **Private hosted zone** association with the Hub VPC (and via RAM sharing or authorization for spoke VPCs) handles `*.internal.corp` resolution.

**Why alternatives fail:**
* **A)** EC2-based BIND servers violate constraint 3 (no EC2 DNS servers). They also create single points of failure and maintenance overhead at scale across 8 regions.
* **C)** Route 53 Resolver DNS Firewall is a security filtering tool (blocks/allows DNS queries based on domain lists) — it cannot forward queries to on-premises DNS servers. It's not a DNS forwarding solution.
* **D)** Mirroring all on-premises DNS records into Route 53 is operationally impossible to maintain (on-premises DNS changes require manual Route 53 updates). Zone delegation from on-premises to Route 53 reverses the traffic flow incorrectly for outbound resolution.

---

## Scenario 17: Domain 2 – Design for New Solutions

A company is building a serverless data lake ingestion pipeline. Sources: 
1. IoT devices sending 50MB/s of telemetry via MQTT. 
2. Nightly 500GB database exports from on-premises via SFTP. 
3. Real-time clickstream data from a web application (100,000 events/minute). 

Requirements: 
* **R1:** All data must land in S3 in Parquet format. 
* **R2:** Data must be queryable within 5 minutes of ingestion. 
* **R3:** PII must be automatically detected and masked before Parquet conversion. 
* **R4:** Total pipeline cost must scale with data volume (no idle infrastructure cost).

**Question:** Which architecture satisfies all requirements?

* **A)** IoT Core → Kinesis Data Streams → Lambda (PII mask) → Kinesis Firehose (Parquet conversion) → S3; SFTP → AWS Transfer Family → Lambda (convert + mask) → S3; Clickstream → API Gateway → Kinesis Firehose → S3; Glue Crawler for queryability.
* **B)** IoT Core → Kinesis Data Streams → Kinesis Data Firehose (with Lambda transformation for PII masking via Amazon Comprehend detect PII) → S3 (Parquet via Firehose's built-in conversion using a Glue schema); SFTP exports → AWS Transfer Family (SFTP) → S3 (raw) → AWS Glue ETL job (PII mask + Parquet) → S3 (processed); Clickstream → Kinesis Firehose (directly from app via SDK) → same Lambda transform → S3; Glue Data Catalog + Athena for < 5min queryability after Glue Crawler trigger on S3 PUT events.
* **C)** All sources → Amazon MSK → Kafka Connect → S3; Glue for PII detection; EMR for Parquet conversion; Athena for querying.
* **D)** IoT Core → SQS → Lambda → S3; SFTP → EC2 SFTP server → S3 sync; Clickstream → Direct PUT to S3 from app; Macie for PII detection; Glue for Parquet; Athena for querying.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Kinesis Firehose with Lambda transformation + Comprehend + Glue schema conversion; Transfer Family for SFTP; serverless Glue ETL; Athena for querying.

**Why it succeeds:**
* **R1 (Parquet):** Kinesis Firehose natively converts JSON to Parquet using a Glue Data Catalog table schema — no custom code needed. Glue ETL handles Parquet conversion for batch SFTP files.
* **R2 (5-min queryability):** Firehose delivers to S3 in 60-second buffers (minimum). Glue Crawler triggered by S3 event updates the Data Catalog within minutes. Athena queries the updated catalog immediately.
* **R3 (PII masking):** Firehose's Lambda transformation invokes Amazon Comprehend DetectPiiEntities API per record, masks detected PII before Parquet conversion. Glue ETL for SFTP files uses Glue's built-in `detect_sensitive_data` transform.
* **R4 (Scale-to-zero cost):** Kinesis Firehose charges per GB processed (no idle cost). Lambda charges per invocation. AWS Transfer Family charges per hour of endpoint (minimal baseline) + data transfer. Athena charges per query TB scanned. No always-on servers.

**Why alternatives fail:**
* **A)** Kinesis Data Streams → Lambda → Firehose adds unnecessary Kinesis Data Streams cost and complexity. Firehose can receive data directly from IoT Core via Kinesis Data Streams OR direct PUT. The architecture also doesn't specify Parquet conversion mechanism clearly.
* **C)** Amazon MSK + EMR is an always-on infrastructure model — MSK minimum cost ~$0.21/hr/broker, EMR cluster always running. Violates R4's scale-to-zero requirement.
* **D)** Amazon Macie is a data security service that scans S3 buckets for PII — it's not a real-time transformation tool. Macie cannot mask PII inline during ingestion; it only detects and alerts. EC2 SFTP server violates serverless/scale-to-zero requirement.

---

## Scenario 18: Domain 5 – Continuous Improvement for Existing Solutions

A company's production EKS cluster (Kubernetes 1.27) running on EC2 managed node groups shows: 
1. Node CPU utilization averages 12% across 50 m5.2xlarge nodes. 
2. Pod scheduling failures (Pending pods) occur during traffic spikes for 8–12 minutes. 
3. The team manually updates kubeconfig credentials every 12 hours (IAM temporary credentials). 
4. Nodes run mixed workloads — both stateless APIs and stateful Kafka consumers. 
5. EKS control plane upgrade to 1.29 has been deferred for 6 months (EOL risk).

**Question:** Which set of improvements addresses all five issues?

* **A)** Add more m5.2xlarge nodes to eliminate pending pods; implement a Kubernetes CronJob to refresh kubeconfig; separate stateful and stateless workloads into separate node groups; upgrade EKS manually via eksctl upgrade cluster.
* **B)** Implement Karpenter (node autoprovisioner) replacing managed node group Cluster Autoscaler — Karpenter provisions right-sized nodes in 60–90 seconds on pod pending events (resolves issues 1 and 2); configure EKS Pod Identity (replacing IRSA for simplified IAM; or IRSA with aws-eks-auth config) for automatic credential refresh via OIDC (resolves issue 3); create separate Karpenter NodePools with nodeSelector for stateless vs stateful workloads (resolves issue 4); execute in-place EKS cluster upgrade using managed node group rolling update strategy (resolves issue 5).
* **C)** Migrate all workloads to ECS Fargate to eliminate node management; use ECS task IAM roles for credentials; separate services into different ECS clusters; ECS handles scaling automatically.
* **D)** Enable Cluster Autoscaler with aggressive scale-up settings; use IAM Identity Center for kubeconfig refresh; add a dedicated node group for stateful workloads; upgrade EKS using Blue/Green cluster replacement.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — Karpenter + Pod Identity/IRSA + separate NodePools + in-place upgrade.

**Why it succeeds:**
* **Issue 1 (12% CPU):** Karpenter's bin-packing algorithm consolidates pods onto fewer, right-sized nodes and terminates underutilized nodes. Unlike Cluster Autoscaler (which scales existing node groups), Karpenter provisions the exact instance type matching the pending pod's resource request — eliminating 88% idle capacity waste.
* **Issue 2 (8–12 min scheduling delays):** Cluster Autoscaler's scale-up triggers on pending pods but then waits for ASG to provision nodes (3–5 min) plus node join time. Karpenter directly calls EC2 RunInstances and has pods running in 60–90 seconds — within the tight latency window.
* **Issue 3 (Manual kubeconfig refresh):** EKS Pod Identity (GA since 2023) or IRSA with aws-eks-auth config provides automatic IAM credential rotation via OIDC — no manual kubeconfig management. Pod Identity simplifies IRSA by removing the need for OIDC provider ARN annotations.
* **Issue 4 (Mixed workloads):** Karpenter NodePools with nodeSelector or taints/tolerations segregate stateless API pods (burstable instance types) from stateful Kafka consumers (compute-optimized, no spot).
* **Issue 5 (EOL risk):** EKS in-place cluster upgrade (control plane first, then managed node groups rolling update) is the standard upgrade path via `eksctl upgrade cluster --name <cluster> --kubernetes-version 1.29`.

**Why alternatives fail:**
* **A)** Adding more fixed nodes increases the idle CPU waste problem further. CronJob for kubeconfig refresh is a fragile workaround. Manual eksctl upgrade without a strategy risks disruption.
* **C)** Migrating to ECS Fargate is a complete platform migration — all Kubernetes manifests, Helm charts, and Kubernetes-native features (CRDs, custom controllers) would need re-implementation. Not a continuous improvement action.
* **D)** Cluster Autoscaler with aggressive settings doesn't solve the 12% CPU waste — it still scales node groups, not individual right-sized nodes. Blue/Green cluster replacement for upgrades requires full workload migration across clusters — high operational risk.

---

## Scenario 19: Domain 3 – Migration Planning

A company is migrating a monolithic on-premises Java application to AWS using the Strangler Fig pattern. The monolith handles: orders, inventory, payments, notifications. The team wants to extract the payment service first (highest business value). Current state: All services share a single Oracle DB. On-premises → AWS connectivity is via Direct Connect (1 Gbps). Team has 4 developers and a 3-month first extraction window.

**Question:** Which migration approach correctly implements Strangler Fig for the payment service extraction with minimal risk?

* **A)** Refactor the entire monolith to microservices simultaneously; deploy all services to EKS; migrate all data from Oracle to Aurora in parallel; redirect traffic via ALB after completion.
* **B)** Deploy a new Payment microservice on ECS Fargate with its own Aurora PostgreSQL database; use AWS DMS to replicate payment-related Oracle tables to Aurora (bidirectional CDC for dual-write period); deploy an API Gateway in front of both the monolith and new payment service; implement a feature flag in API Gateway (using Lambda authorizer or request routing) to route POST /payments traffic to the new service while all other traffic goes to monolith; use AWS Migration Hub Refactor Spaces to manage the proxy routing and incremental traffic shifting.
* **C)** Create a payment Lambda function; expose via API Gateway; write directly to the same Oracle DB; deprecate the monolith payment module; redirect via DNS.
* **D)** Use AWS App Mesh to implement a service mesh across the monolith and new payment service; migrate payment data to DynamoDB; implement event sourcing with EventBridge; redirect traffic gradually via weighted routing in App Mesh.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **B** — New Payment service on ECS Fargate + own Aurora DB + DMS CDC + API Gateway routing + Refactor Spaces.

**Why it succeeds:** The Strangler Fig pattern requires: (1) A proxy/facade that intercepts traffic and routes to either old or new system. (2) Incremental traffic shifting to the new service. (3) A data migration strategy that keeps both systems consistent during the transition. API Gateway + Lambda authorizer (or request-based routing) serves as the proxy. Refactor Spaces manages the routing environment. DMS with bidirectional CDC keeps Oracle and Aurora in sync during the dual-write period — as long as both systems process payments, data consistency is maintained. Feature flags enable controlled traffic shifting (5% → 25% → 100%). ECS Fargate for the new service requires no container infrastructure management. Aurora PostgreSQL is the natural target for Oracle migration (SCT compatible). This exactly follows the AWS Strangler Fig microservices pattern from the AWS Architecture Blog.

**Why alternatives fail:**
* **A)** Refactoring the entire monolith simultaneously is the "Big Bang" anti-pattern — opposite of Strangler Fig. Three months and 4 developers cannot refactor orders + inventory + payments + notifications simultaneously with data migration.
* **C)** New payment Lambda writing to the same Oracle DB creates tight coupling — the entire point of Strangler Fig is to extract the data domain as well. Sharing the Oracle DB means the monolith and new service are still coupled at the data layer.
* **D)** App Mesh service mesh is a valid architectural pattern but adds significant operational complexity (Envoy proxies, mTLS configuration) for a 4-developer team with a 3-month window. DynamoDB as a payment database requires complete schema redesign from relational Oracle — too risky for the first extraction.

---

## Scenario 20: Domain 4 – Cost Control

A company runs Amazon Redshift (ra3.4xlarge × 8 nodes, $X/month) and Amazon EMR (r5.2xlarge × 20 core nodes On-Demand, running 24/7) for a data analytics platform. Redshift queries run only during business hours (8am–6pm, 5 days/week). EMR processes daily batch jobs that run for 4 hours starting at 2am. The remaining 20 hours per day, EMR nodes are idle. S3 houses 2PB of raw data. Athena is not currently used.

**Question:** Which architecture changes deliver the maximum cost reduction?

* **A)** Use Redshift pause/resume on a schedule; convert EMR to EMR Serverless; migrate warm query data from S3 raw to Redshift Spectrum for federated querying.
* **B)** Migrate Redshift to Athena entirely; terminate EMR and use Lambda for all data processing; use S3 Intelligent-Tiering for all 2PB.
* **C)** Enable Redshift pause/resume (pause at 6pm, resume at 7:55am weekdays = ~128 hrs/week idle, saving ~76% of compute cost); migrate EMR On-Demand cluster to EMR on EC2 with Spot Instances for core/task nodes + transient cluster model (spin up at 1:55am, terminate at 6am = 4.08 hrs/day billed vs 24 hrs/day = 83% reduction); use S3 Lifecycle policies to tier data older than 90 days to S3 Glacier Instant Retrieval for 2PB raw data (68% storage cost reduction); implement Redshift Spectrum for querying S3 data directly without loading into Redshift.
* **D)** Downsize Redshift to ra3.xlplus; use EMR Managed Scaling; keep On-Demand EMR; use S3 Intelligent-Tiering; add Redshift concurrency scaling.

### Architectural Decision Record (Resolution)

**Optimal Solution:** **C** — Redshift pause/resume + transient EMR Spot cluster + S3 tiering + Redshift Spectrum.

**Why it succeeds:**
* **Redshift pause/resume:** ra3 clusters support pause/resume; pausing 128 hours/week (nights + weekends) when business hours = 50 hrs/week saves approximately 128/(128+50) = 72% of weekly Redshift compute cost. With ra3.4xlarge at ~$3.26/node/hr × 8 = $26.08/hr, saving 128 hrs/week = ~$3,338/week = ~$13,400/month.
* **Transient EMR Spot:** EMR Spot pricing = ~70% discount vs On-Demand. Transient cluster (4 hrs/day vs 24 hrs/day) = 83% fewer hours. Combined savings: 1-(0.3 × 4/24) = 95% reduction in EMR compute cost. 20 core nodes × r5.2xlarge On-Demand ~$0.504/hr × 24 = $241/day → Spot transient = ~$241 × 0.05 = $12/day.
* **S3 Glacier Instant Retrieval:** At 2PB, S3 Standard = $0.023/GB = $47,186/month; Glacier Instant Retrieval = $0.004/GB = $8,192/month — saving ~$39,000/month for data > 90 days old.
* **Redshift Spectrum:** Query S3 data directly from Redshift without ETL loading — eliminates data movement costs and Redshift storage for cold data.

**Why alternatives fail:**
* **A)** Correct on Redshift pause/resume and EMR Serverless. However, EMR Serverless for a 4-hour daily batch job is effective but doesn't capture Spot pricing discounts available with transient EC2-based EMR. EMR Serverless charges per vCPU-hour and memory-hour — cost comparison is workload-dependent, but for predictable 4-hour batch, transient Spot EMR is often cheaper.
* **B)** Migrating Redshift entirely to Athena requires complete SQL compatibility testing and may not support all Redshift-specific SQL extensions. Lambda for EMR-scale data processing (20 nodes × r5.2xlarge = significant compute) hits Lambda memory/timeout limits — technically infeasible for large-scale batch.
* **D)** Downsizing Redshift without pausing leaves the cluster running idle 72% of the time — cost reduction is marginal (smaller instance) vs pause/resume (zero cost while paused). EMR Managed Scaling adjusts cluster size dynamically but doesn't eliminate idle costs when the cluster runs 24/7 with only 4 hours of work.
