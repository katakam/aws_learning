# SAP-C02 20-Day Prep Guide for Experienced Solution Architects

This guide assumes you already understand most AWS services at a working SA level. The goal is not to relearn AWS from zero. The goal is to become exam-sharp: recognize scenario signals, eliminate traps, and choose the AWS-native architecture the exam expects.

## Core exam mindset

SAP-C02 usually tests this pattern:

```text
Business constraint + technical constraint + operational constraint
→ best AWS architecture
→ avoid plausible but wrong alternatives
```

For an experienced architect, the biggest risk is overthinking with real-world flexibility. The exam often wants the managed AWS answer that best satisfies the stated constraints.

Use this mental model:

```text
If the question says governance at scale → Organizations / SCP / Control Tower / Config
If the question says human access → IAM Identity Center / roles / federation
If the question says app-to-app auth → IAM roles / resource policies / STS
If the question says hybrid network → TGW / DX / VPN / Route 53 Resolver
If the question says migration → MGN / DMS / SCT / DataSync / Snowball
If the question says DR → RTO/RPO decide pilot light, warm standby, active-active
If the question says cost → managed scaling, lifecycle, endpoints, Savings Plans
```

---

# 20-Day Plan

## Days 1–2: Organizations, IAM, governance foundation

Focus hard here. This is high-value and easy to confuse.

Study:

- AWS Organizations
- SCP evaluation
- IAM policy evaluation
- Permission boundaries
- Resource-based policies
- IAM Identity Center
- Control Tower
- Config conformance packs
- CloudTrail organization trail
- GuardDuty / Security Hub delegated admin

Use these patterns from the knowledge map:

- SCP Deny-List + Acquired Account Carve-Out
- SCP Evaluation Logic — Full Authorization Chain
- Merging Two AWS Organizations Post-Acquisition
- Human Access to Production
- Control Tower Landing Zone
- Organization-Wide Security Controls

Outcome:

You should be able to explain why IAM cannot override SCP, why root deny is dangerous, and when Identity Center is the correct answer.

---

## Days 3–4: Networking and hybrid architecture

Study:

- Transit Gateway
- Direct Connect Gateway
- Private VIF / Transit VIF
- Site-to-Site VPN
- Route 53 Resolver inbound/outbound endpoints
- AWS RAM sharing
- GWLB
- VPC endpoints / PrivateLink
- CloudFront vs Global Accelerator vs Route 53 ARC

Outcome:

You should quickly identify:

- hybrid DNS pattern
- centralized inspection pattern
- private connectivity pattern
- global latency/failover pattern

---

## Days 5–6: Data stores and global architecture

Study:

- Aurora Global Database
- DynamoDB Global Tables
- ElastiCache Global Datastore
- S3 replication and Object Lock
- RDS read replicas
- QLDB / Timestream / DocumentDB / Neptune basics

Outcome:

Know which service matches:

- relational global read latency
- active-active NoSQL
- immutable ledger
- time-series data
- document data
- graph relationships

---

## Days 7–8: Migration services

Study:

- AWS Application Migration Service / MGN
- DMS and CDC
- SCT
- DataSync
- Snowball / Snowmobile
- Storage Gateway
- Migration Hub
- Application Discovery Service

Simple memory:

```text
Server lift-and-shift → MGN
Database migration → DMS
Schema conversion → SCT
File transfer → DataSync
Offline huge data → Snowball
Hybrid file/block/tape access → Storage Gateway
```

Outcome:

You should eliminate wrong migration tools instantly.

---

## Days 9–10: Serverless, eventing, streaming

Study:

- Lambda concurrency, aliases, provisioned concurrency, SnapStart
- Step Functions Standard vs Express
- SQS / SNS / EventBridge
- Kinesis Data Streams / Firehose / Managed Flink
- MSK
- API Gateway REST / HTTP / WebSocket

Simple memory:

```text
Queue buffer → SQS
Pub/sub fanout → SNS
SaaS/event routing → EventBridge
Ordered high-throughput stream → Kinesis/MSK
Workflow orchestration → Step Functions
```

Outcome:

Know when async buffering beats direct synchronous scaling.

---

## Days 11–12: Reliability and DR

Study:

- RTO/RPO mapping
- Route 53 ARC
- AWS Elastic Disaster Recovery / DRS
- Backup
- Multi-AZ vs Multi-Region
- Active-active vs active-passive
- Health checks and false positives

Simple memory:

```text
Backup/restore → cheapest, slowest
Pilot light → core infra always on
Warm standby → scaled-down full stack
Active-active → fastest, most expensive
```

Outcome:

You should select DR architecture from RTO/RPO without hesitation.

---

## Days 13–14: Security and compliance

Study:

- KMS key policy vs IAM policy
- Secrets Manager vs Parameter Store
- Macie
- GuardDuty
- Security Hub
- Inspector
- Access Analyzer
- WAF / Shield / Firewall Manager
- ACM Private CA
- CloudHSM basics

Outcome:

Know what each security service actually does. Avoid choosing Security Hub when detection should be GuardDuty, or Macie when the issue is malware/threat detection.

---

## Days 15–16: Cost optimization

Study:

- Savings Plans vs Reserved Instances vs Spot
- S3 lifecycle vs Intelligent-Tiering
- NAT Gateway cost reduction with VPC endpoints
- CloudFront egress reduction
- Compute right-sizing
- Aurora Serverless v2
- Redshift pause/resume
- CloudWatch Logs retention/export

Outcome:

When the question says cost, choose architecture-level savings before micro-optimizations.

---

## Days 17–18: Practice exam + error mapping

Do one full practice test.

For each wrong answer, classify it:

```text
Knowledge gap?
Misread constraint?
Wrong service comparison?
Ignored RTO/RPO?
Ignored org/security boundary?
Chose real-world answer instead of exam answer?
```

Then map it back to the knowledge graph pattern.

Do not just read explanations. Convert every miss into an IF/WHEN → THEN → NEVER rule.

---

## Day 19: Trap drill and weak domains

Use the knowledge map:

- Trap Index
- Concept Index
- Domain filters

Focus on:

- services that look similar
- traps you repeatedly choose
- governance/IAM details
- migration services
- DR choices

---

## Day 20: Light review only

Do not cram new services.

Review:

- Organizations/IAM cheat sheet
- migration tool selector
- DR RTO/RPO table
- networking selector
- top traps

Sleep properly. SAP-C02 is a long reasoning exam.

---

# High-Value Focus Areas

If time becomes tight, prioritize:

1. Organizations + IAM + SCPs
2. Migration services
3. Hybrid networking
4. DR and global failover
5. Data service selection
6. Eventing/streaming selection
7. Cost optimization patterns

---

# Simple Organizations + IAM Memory Model

## The one-line model

```text
SCP says what an account is allowed to use.
IAM says what a principal is allowed to do.
Resource policy says who can access this resource.
Permission boundary says maximum permissions for a role/user.
Session policy says maximum permissions for this session.
```

## Authorization shortcut

For most exam questions:

```text
Explicit Deny anywhere = Deny
SCP must allow it
IAM or resource policy must allow it
Permission boundary/session policy must not limit it
```

## SCP memory

```text
SCPs do not grant permissions.
SCPs set the maximum available permissions for accounts.
IAM still has to allow the action.
```

Important:

- SCP affects member accounts, not the management account.
- SCP applies to principals in the account, including root user of member account.
- SCP cannot be bypassed by IAM admin permissions.
- Permission boundary cannot override SCP.
- Resource policy cannot override explicit deny.
- Deny beats allow.

## SCP carve-out memory

If a root or parent OU SCP denies something and one account needs temporary exception:

```text
Move account to different OU with appropriate SCP structure.
Do not try IAM permission boundary.
Do not try another child deny.
```

## IAM Identity Center memory

Use IAM Identity Center when the question says:

- workforce access
- multiple AWS accounts
- SSO
- external IdP like Okta/Azure AD
- permission sets
- centralized human access

Do not choose long-lived IAM users for human production access.

## Cross-account access memory

```text
Human cross-account access → IAM Identity Center or assume-role federation
AWS service access → IAM role
External account access to resource → resource policy and/or role trust
Organization-wide guardrail → SCP
```

## Permission boundary memory

Permission boundaries are useful when delegating role/user creation.

```text
Boundary = maximum permissions a created principal can ever get.
```

They are not for:

- overriding SCPs
- granting access by themselves
- organization-wide governance

## Resource policy memory

Resource policies live on resources like:

- S3 bucket
- KMS key
- SQS queue
- SNS topic
- Lambda function
- Secrets Manager secret
- ECR repository

They answer:

```text
Who can access this resource?
```

IAM identity policy answers:

```text
What can this principal do?
```

Both may be needed.

---

# Mini Service Selector

## Governance

```text
Multi-account setup best practice → Control Tower
Prevent actions across accounts → SCP
Detect config drift/noncompliance → AWS Config
Deploy compliance rules at scale → Config conformance packs
Central security findings → Security Hub
Threat detection → GuardDuty
Sensitive S3 data discovery → Macie
Central human access → IAM Identity Center
```

## Migration

```text
EC2/server migration → MGN
Database migration with CDC → DMS
Schema conversion → SCT
File/object transfer → DataSync
Offline bulk transfer → Snowball
Hybrid file/block/tape → Storage Gateway
```

## Global / edge

```text
Static/dynamic content cache → CloudFront
Anycast static IP, instant regional routing → Global Accelerator
Controlled app recovery/failover → Route 53 ARC
DNS-based routing → Route 53
Global relational read locality → Aurora Global Database
Global active-active NoSQL → DynamoDB Global Tables
```

## Messaging / streaming

```text
Queue and decouple → SQS
Fanout notification → SNS
Event bus/routing/SaaS events → EventBridge
Ordered high-throughput stream → Kinesis Data Streams
Managed Kafka compatibility → MSK
Stream analytics → Managed Service for Apache Flink
```

---

# Daily Study Loop

Use this loop every day:

1. Read 8–12 patterns from the knowledge map.
2. Hide the THEN mentally.
3. Predict the correct AWS design.
4. Read the NEVER section.
5. Write down one trap you might fall for.
6. Do 20–30 practice questions.
7. Convert wrong answers into new rules.

The goal is not memorizing all services. The goal is fast, accurate architectural selection.
