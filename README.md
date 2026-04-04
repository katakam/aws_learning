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
