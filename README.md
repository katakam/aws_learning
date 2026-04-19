<style>
/* Pearson VUE Exam Authentic Styling */
body { background-color: #f2f2f2; font-family: Arial, Verdana, sans-serif; color: #000000; line-height: 1.5; font-size: 16px; }
.exam-container { background-color: #ffffff; margin: 30px auto; max-width: 900px; padding: 40px; border: 1px solid #cccccc; box-shadow: none; overflow-wrap: break-word; word-break: break-word; }
code { word-break: break-all; }
.vue-header { background-color: #003366; color: #ffffff; padding: 10px 20px; font-size: 14px; font-weight: bold; display: flex; justify-content: space-between; margin: -40px -40px 30px -40px; border-bottom: 2px solid #000000; }
h3 { font-size: 18px; font-weight: bold; color: #000000; border: none; margin-top: 0; margin-bottom: 20px; }
.question-prompt { font-weight: normal; background-color: transparent; padding: 0; border: none; margin: 20px 0; }
.question-prompt strong { font-weight: bold; }
ul, ol { list-style-type: none; padding: 0; margin: 20px 0; }
li { background-color: transparent; border: none; margin-bottom: 15px; padding: 0 0 0 28px; position: relative; }
input[type=checkbox] { position: absolute; left: 0; top: 3px; margin: 0; }
li p, li span { margin: 0; }
details { background-color: #f9f9f9; border: 1px solid #dddddd; padding: 15px; margin-top: 30px; font-size: 14px; }
summary { font-weight: bold; color: #333333; cursor: pointer; }
</style>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 1: Domain 1 – Design Solutions for Organizational Complexity

A financial services enterprise uses AWS Organizations with 40 accounts across 4 OUs: Prod, NonProd, Sandbox, and Security. The Security team mandates that no account outside the Security OU can disable AWS CloudTrail, modify S3 bucket policies on the central logging bucket, or create IAM users with console access. The Sandbox OU must additionally be prevented from launching any EC2 instances beyond t3.micro. The IAM Identity Center is deployed at the management account level. Individual account administrators currently hold AdministratorAccess via IAM Identity Center permission sets.

<div class="question-prompt">
**Question:** Which combination of controls satisfies ALL the stated requirements with the LEAST operational overhead?
</div>
- [ ] Create individual SCPs per OU denying CloudTrail modifications and S3 bucket policy changes, attach to Prod, NonProd, and Sandbox OUs; use a separate SCP on Sandbox denying `ec2:RunInstances` with a condition key `ec2:InstanceType` not equal to t3.micro; enforce via IAM Identity Center by removing AdministratorAccess from all accounts.
- [ ] Attach a deny-all-except-approved SCP to the Root; create allow SCPs at each OU level; use AWS Config rules to detect violations; use Lambda auto-remediation for any detected drift.
- [ ] Attach targeted Deny SCPs to the Root for CloudTrail and S3 logging bucket protections (with a condition excluding the Security OU's accounts); attach a separate SCP to the Sandbox OU denying `ec2:RunInstances` unless `ec2:InstanceType` equals t3.micro; leave IAM Identity Center permission sets unchanged.
- [ ] Use AWS Control Tower guardrails to enforce CloudTrail and S3 protections globally; create a custom Sandbox OU guardrail via Service Control Policies preventing large instance types; integrate with IAM Identity Center for permission set management.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Attach Root-level deny SCPs with a `StringNotEquals` condition on `aws:PrincipalAccount` to exclude Security OU accounts, plus a Sandbox-scoped SCP using `StringNotEquals` on `ec2:InstanceType`.

* **Why it succeeds:** SCPs use an intersection model — effective permissions = IAM permissions ∩ SCP allow scope. A Deny at any level in the hierarchy overrides any Allow. Placing the CloudTrail/S3 deny at Root ensures universal coverage across all OUs without per-OU duplication. The `aws:PrincipalAccount` condition in the `StringEquals` pattern for the Condition block with `ArnNotLike` or an explicit account list carves out the Security OU's accounts. The `ec2:InstanceType` `StringNotEquals` condition on the Sandbox SCP correctly enforces instance size restrictions. This requires no changes to IAM Identity Center permission sets, minimising administrative overhead per the Well-Architected Operational Excellence pillar.

* **Why alternatives fail:**
  - **A)** Attaching individual deny SCPs per OU (Prod, NonProd, Sandbox) creates redundancy and misses future OUs unless explicitly updated — high operational overhead and drift risk. Removing AdministratorAccess from IAM Identity Center is unnecessary and breaks legitimate admin workflows.
  - **B)** A deny-all-except-approved SCP at Root with per-OU allow SCPs is the "allowlist" model, which is extremely restrictive and requires enumerating every allowed action per OU — operationally unviable at scale and incompatible with IAM Identity Center's additive model.
  - **D)** AWS Control Tower guardrails wrap SCPs but add management plane complexity and require Control Tower enrollment of all accounts. Custom guardrails for instance type restrictions are not natively supported in Control Tower's proactive/detective guardrail library — this would still require a custom SCP, eliminating Control Tower's value-add here.


</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 2: Domain 1 – Design Solutions for Organizational Complexity

A global enterprise has 3 AWS accounts: Network Hub (owns Transit Gateway and Direct Connect Gateway), AppAccount A (us-east-1), and AppAccount B (ap-southeast-1). Both app accounts connect via TGW RAM share. On-premises routes are advertised via BGP over a Direct Connect hosted connection. The security team requires that all inter-VPC traffic and on-premises traffic flows through a centralised Network Firewall deployed in the Network Hub account. AppAccount B reports that traffic to on-premises is bypassing the firewall and routing directly via the TGW.

<div class="question-prompt">
**Question:** What is the root cause and the correct architectural fix?
</div>
- [ ] The TGW route table for AppAccount B's VPC attachment is missing a static route for the on-premises CIDR pointing to the Network Firewall VPC attachment; add the static route and enable appliance mode on the Firewall VPC attachment.
- [ ] Direct Connect Gateway is not propagating routes to the TGW; re-enable BGP propagation in the TGW route table for the DXGW attachment.
- [ ] The TGW uses a single shared route table. A segregated routing model with two TGW route tables is needed: one for spoke VPCs (propagating only to Firewall VPC) and one for the Firewall VPC (propagating to all spokes and DXGW); additionally, appliance mode must be enabled on the Firewall VPC attachment to prevent asymmetric routing across AZs.
- [ ] Enable VPC flow logs in AppAccount B and use Athena queries to trace the traffic path; once confirmed, add a blackhole route on the TGW for on-premises CIDRs from AppAccount B.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — The correct pattern is a two-route-table TGW architecture (Spoke RT + Firewall RT) with appliance mode enabled.

* **Why it succeeds:** In the AWS TGW inspection architecture, spoke VPC attachments are associated with a "Spoke Route Table" that has a default route (0.0.0.0/0) pointing to the Firewall VPC attachment, with no propagation to other spokes or DXGW. The Firewall VPC attachment is associated with a "Firewall Route Table" that propagates from all spoke attachments and the DXGW attachment. This forces all traffic (inter-VPC and on-premises) through the firewall. Appliance mode is critical: without it, TGW performs ECMP across AZs, causing asymmetric flows that bypass stateful firewall inspection. This directly aligns with the AWS "Centralized Inspection Architecture" whitepaper pattern.

* **Why alternatives fail:**
  - **A)** Adding a static route to a single shared route table partially fixes on-premises routing but doesn't enforce east-west inter-VPC inspection. Single-table designs cannot simultaneously route spoke-to-spoke through the firewall without hairpinning issues.
  - **B)** BGP propagation from DXGW is not the issue — the problem is TGW route table design. Re-enabling propagation without the two-table model would still bypass the firewall.
  - **D)** Flow logs are a diagnostic tool, not an architectural fix. Adding a blackhole route for on-premises CIDRs would block all on-premises connectivity, not redirect it through the firewall.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 3: Domain 2 – Design for New Solutions

A SaaS company is building a multi-tenant event-driven order processing platform on AWS. Requirements: 
1. Each tenant's events must be strictly isolated — one tenant's processing failure must not affect others. 
2. The platform must handle up to 500 tenant onboardings per day. 
3. Event ordering must be guaranteed per tenant. 
4. The solution must scale to millions of events/day without re-architecting. 
5. Cost must scale to near-zero for inactive tenants.

<div class="question-prompt">
**Question:** Which architecture best satisfies all five requirements?
</div>
- [ ] Provision a dedicated Amazon MSK cluster per tenant with a Lambda consumer; use EventBridge to route events by tenant ID; store tenant configurations in DynamoDB.
- [ ] Use a single Amazon Kinesis Data Stream with tenant ID as the partition key; deploy a single Lambda consumer with per-tenant processing logic; use SQS FIFO queues per tenant for ordering guarantees.
- [ ] Use Amazon SQS FIFO queues (one per tenant, created dynamically on onboarding); route events via EventBridge rules with tenant-specific targets; process with Lambda consumers; use DynamoDB for tenant state; leverage SQS FIFO's MessageGroupId = tenant ID for ordering.
- [ ] Use a single Amazon MSK (Kafka) cluster with one topic per tenant; deploy ECS Fargate consumer groups per topic; use Auto Scaling based on MSK consumer group lag.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — SQS FIFO per tenant + EventBridge routing + Lambda.

* **Why it succeeds:** SQS FIFO with `MessageGroupId` guarantees strict per-group (per-tenant) ordering and provides blast-radius isolation — a poison message in one tenant's queue does not affect others. Dynamic queue creation via SDK on tenant onboarding is trivial and supports 500/day with no infrastructure provisioning. Lambda scales to zero for inactive tenants, meeting cost requirement 5. EventBridge's content-based routing on tenant attributes cleanly decouples producers from consumer infrastructure. DynamoDB stores tenant metadata with sub-millisecond lookup. This aligns with the Well-Architected Framework's microservices isolation and event-driven decoupling patterns.

* **Why alternatives fail:**
  - **A)** A dedicated MSK cluster per tenant is massively cost-prohibitive (MSK minimum cost ~$0.21/hr per broker, 3 brokers minimum = ~$450/month per tenant at 500 tenants/day onboarding rate). Completely fails cost requirement 5.
  - **B)** A single Kinesis stream with Lambda: Kinesis ordering is per-shard, and a single stream cannot guarantee tenant isolation — a hot shard or Lambda concurrency issue affects all tenants. Bolting on per-tenant FIFO queues while maintaining a Kinesis stream creates an overly complex dual-ingestion path.
  - **D)** MSK with one topic per tenant has per-topic partition overhead; Kafka minimum practical deployment costs are high; ECS Fargate consumers don't scale to zero; MSK clusters don't support near-zero cost for inactive tenants. Fails requirement 5.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 4: Domain 2 – Design for New Solutions

A healthcare company is deploying a globally distributed patient records system. Requirements: 
1. RPO = 1 minute, RTO = 1 minute for database tier. 
2. The application must serve reads with < 100ms latency globally (users in US, EU, APAC). 
3. All writes must originate from the us-east-1 primary region only. 
4. Data must never leave a specific region for compliance — EU patient data stays in EU, APAC in APAC. 
5. Schema is relational with complex joins.

<div class="question-prompt">
**Question:** Which database architecture satisfies ALL constraints?
</div>
- [ ] Deploy Amazon Aurora Global Database with us-east-1 as primary writer; EU and APAC as read replicas; use Route 53 latency-based routing to direct reads to the nearest replica; promote replicas in DR scenarios; enforce data residency via application-layer filtering.
- [ ] Deploy DynamoDB Global Tables with write routing pinned to us-east-1 via application logic; leverage DynamoDB Streams for cross-region replication; use DAX for sub-100ms reads; enforce data residency via table-level conditional writes.
- [ ] Deploy Amazon Aurora Global Database with us-east-1 as the primary write region; secondary clusters in eu-west-1 and ap-southeast-1 as read replicas; use CloudFront with Lambda@Edge to route reads to the geographically closest Aurora secondary endpoint; enforce EU/APAC data residency by storing region-specific data only in regional secondary clusters and routing writes through an API Gateway layer that validates residency before forwarding to Aurora primary.
- [ ] Deploy RDS Multi-AZ in us-east-1 with cross-region read replicas in eu-west-1 and ap-southeast-1; use Route 53 latency routing for reads; RTO/RPO achieved via automated failover promotion scripted in Lambda.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — Aurora Global Database with Route 53 latency routing is the correct and exam-preferred answer, with an important nuance on data residency.

* **Why it succeeds:** Aurora Global Database replicates with typical lag < 1 second (meeting RPO = 1 min) and supports managed failover in < 1 minute via the managed planned/unplanned failover API (meeting RTO = 1 min). Secondary clusters in eu-west-1 and ap-southeast-1 serve low-latency reads (Aurora replicas typically serve reads in single-digit ms within region). Route 53 latency-based routing directs users to the nearest regional endpoint. For data residency, since writes go to us-east-1 and replicate globally, the application-layer enforcement of residency (writing EU records only when routed through EU endpoints, enforcing at the API layer) is the pragmatic and exam-correct approach — Aurora Global Database does not natively enforce per-row regional data residency, so option C's description of routing is overcomplicated but the core Aurora Global DB pattern in A is sound.

* **Why alternatives fail:**
  - **B)** DynamoDB Global Tables uses an active-active, multi-master model — you cannot restrict writes to a single region natively. The "application logic" approach for write pinning is unreliable and not a supported DynamoDB architecture. Additionally, DynamoDB does not support complex relational joins, violating requirement 5.
  - **C)** CloudFront + Lambda@Edge for database read routing is architecturally unsound — CloudFront caches HTTP responses, not database query results for live patient records. Lambda@Edge adds unnecessary latency and cost for database request routing; Route 53 latency routing is the correct and simpler mechanism.
  - **D)** RDS cross-region read replica promotion for RTO/RPO < 1 minute is not achievable — replica promotion to primary is a manual or scripted process taking 5–30 minutes, failing both RTO and RPO requirements. Lambda-scripted failover adds fragility.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 5: Domain 3 – Migration Planning

A large enterprise is migrating 200 on-premises virtual machines to AWS. The portfolio includes: 
1. 40 x Windows Server VMs running licensed SQL Server (bring-your-own-license). 
2. 80 x Linux VMs running Java microservices. 
3. 30 x VMs running legacy COBOL batch jobs (cannot be rehosted in containers). 
4. 50 x VMs running Oracle WebLogic with Java EE applications (refactoring budget available). 
The enterprise has a 24-month migration window and must minimize licensing costs.

<div class="question-prompt">
**Question:** Which migration strategy mapping is most cost-optimal and technically correct?
</div>
- [ ] All 200 VMs: AWS Application Migration Service (MGN) lift-and-shift to EC2; post-migration, convert SQL Server to RDS; COBOL to Lambda; WebLogic to ECS Fargate.
- [ ] SQL Server VMs → EC2 Dedicated Hosts with BYOL SQL Server; Linux Java VMs → replatform to ECS Fargate (containerize); COBOL VMs → EC2 with Dedicated Hosts (BYOL Windows if needed); WebLogic → refactor to Amazon EKS with Spring Boot microservices using AWS Schema Conversion Tool for any database dependencies.
- [ ] SQL Server VMs → RDS for SQL Server with License Included (LI) to eliminate BYOL complexity; Linux Java VMs → lift-and-shift to EC2 then containerize to ECS Fargate over 6 months; COBOL VMs → EC2 (rehost, no refactor); WebLogic → AWS Elastic Beanstalk with Tomcat platform.
- [ ] SQL Server VMs → EC2 with BYOL SQL Server on Dedicated Hosts (preserving existing licenses per Microsoft mobility rules); Linux Java VMs → replatform to ECS Fargate; COBOL VMs → rehost to EC2 (dedicated or shared per licensing need); WebLogic → refactor to EKS/Spring Boot using AWS Migration Hub Refactor Spaces for incremental strangler-fig migration; use AWS MGN for initial rehost of all VMs, then execute refactoring tracks in parallel.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — BYOL on Dedicated Hosts for SQL Server, ECS Fargate for Linux Java, EC2 rehost for COBOL, EKS refactor for WebLogic, with MGN as the migration engine.

* **Why it succeeds:** Microsoft's License Mobility program requires Dedicated Hosts (not Dedicated Instances) for BYOL SQL Server on AWS — this is a hard licensing constraint. EC2 Dedicated Hosts allow customers to bring existing SQL Server datacenter licenses, avoiding re-purchase. Linux Java microservices containerize cleanly to ECS Fargate (serverless containers, no cluster management). COBOL batch jobs cannot be containerized (requirement 3) — EC2 rehost is the only viable path. WebLogic-to-Spring Boot is a well-documented AWS migration pattern; Refactor Spaces provides the strangler-fig proxy pattern, allowing incremental traffic shifting from legacy WebLogic to new EKS microservices without a big-bang cutover. AWS MGN is the AWS-recommended rehost tool (replaces SMS) supporting all VM types.

* **Why alternatives fail:**
  - **A)** COBOL to Lambda is architecturally infeasible — Lambda has a 15-minute timeout and no support for legacy COBOL runtimes. Batch COBOL jobs require persistent, long-running compute.
  - **B)** Correct on SQL Server Dedicated Hosts, but misses AWS MGN as the migration engine and doesn't address the 24-month timeline with parallel tracks — purely sequential migration risks missing the window.
  - **C)** RDS for SQL Server License Included (LI) is significantly more expensive than BYOL for 40 servers over 24 months, directly contradicting the cost-minimization requirement. LI pricing bundles Microsoft license cost into the RDS hourly rate, which is wasteful when the enterprise already owns licenses.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 6: Domain 3 – Migration Planning

A company is migrating a 500TB on-premises data warehouse to Amazon S3 + Athena. The data is stored on a NAS (NFS protocol) in an on-premises data center. The connection to AWS is via a 1 Gbps Direct Connect link shared with production traffic (production traffic uses ~600 Mbps on average). The migration must complete in 30 days without impacting production. Post-migration, ongoing nightly incremental syncs of ~50GB must continue.

<div class="question-prompt">
**Question:** Which migration and ongoing sync architecture is optimal?
</div>
- [ ] Use AWS DataSync over Direct Connect with bandwidth throttling to 300 Mbps; schedule transfers during off-peak hours; for ongoing sync, continue DataSync nightly jobs.
- [ ] Order AWS Snowball Edge Storage Optimized (multiple devices) for the initial 500TB bulk migration; configure DataSync agent on-premises for ongoing nightly 50GB incremental sync over Direct Connect with a 200 Mbps throttle.
- [ ] Use AWS Storage Gateway File Gateway to mount S3 as NFS; migrate data by copying files from NAS to Storage Gateway (which uploads to S3); ongoing sync is handled automatically by Storage Gateway's cache invalidation.
- [ ] Use S3 Transfer Acceleration over the internet as a parallel path alongside Direct Connect; split the 500TB dataset across both paths; use S3 Multipart Upload for files > 100MB.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Snowball Edge for bulk + DataSync for ongoing incremental.

* **Why it succeeds:** At 300 Mbps usable bandwidth (1 Gbps - 600 Mbps production - overhead), transferring 500TB would take: `500TB × 8Tb/TB ÷ 0.3 Gbps = ~148 days` — far exceeding the 30-day window. AWS Snowball Edge Storage Optimized holds 80TB usable per device, so ~7 devices cover 500TB. Physical transfer eliminates network dependency for bulk migration. DataSync over DX for 50GB nightly = `50GB × 8 ÷ 200Mbps = ~33 minutes` — well within a nightly window at 200 Mbps throttle, leaving 400 Mbps for production. DataSync handles NFS source natively, preserves metadata, and supports scheduling.

* **Why alternatives fail:**
  - **A)** As calculated, 300 Mbps over DX for 500TB requires ~148 days — physically impossible in 30 days. DataSync throttling cannot overcome the fundamental bandwidth math.
  - **C)** Storage Gateway File Gateway is designed for hybrid access patterns, not bulk data migration. Copying 500TB through a gateway cache is extremely slow and operationally fragile; the gateway cache would overflow repeatedly, causing repeated S3 upload retries.
  - **D)** S3 Transfer Acceleration adds cost and internet latency. Combining it with DX for a split transfer requires custom orchestration. More importantly, this doesn't solve the core bandwidth constraint — the internet path would be limited by the on-premises uplink and would still take well over 30 days for 500TB.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 7: Domain 4 – Cost Control

A company runs a real-time analytics platform with the following components: 
1. 20 x r5.4xlarge EC2 instances (On-Demand) for Spark processing running 24/7. 
2. An Amazon Kinesis Data Stream with 100 shards. 
3. Amazon Redshift cluster (dc2.8xlarge × 4 nodes) running queries only 8 hours per day (business hours). 
4. S3 storage: 800TB total, with 600TB not accessed in > 180 days. 
5. NAT Gateway processing 50TB/month of data egress from private subnets.

<div class="question-prompt">
**Question:** Which cost optimization actions deliver the GREATEST savings with acceptable operational risk?
</div>
- [ ] Convert EC2 to Spot Instances; reduce Kinesis to 10 shards; migrate Redshift to Redshift Serverless; move 600TB S3 to Glacier Instant Retrieval; replace NAT Gateway with VPC endpoints for S3.
- [ ] Purchase 1-year Compute Savings Plans for EC2 (covering r5.4xlarge baseline); implement Kinesis shard-level auto-scaling via Application Auto Scaling; use Redshift pause/resume scheduling (pause after 8 hrs, resume before business hours); transition 600TB S3 to S3 Glacier Deep Archive via lifecycle policy; add S3 Gateway Endpoint to eliminate NAT Gateway S3 traffic charges.
- [ ] Convert EC2 to Reserved Instances (3-year, all-upfront); reduce Kinesis shards to 5; delete the Redshift cluster and migrate to Athena; move all 800TB S3 to Glacier Deep Archive; remove NAT Gateway and use internet gateway for all traffic.
- [ ] Purchase EC2 Savings Plans; migrate Redshift to Aurora Serverless; keep Kinesis shards at 100; apply S3 Intelligent-Tiering to all 800TB; use NAT Instance (t3.medium) instead of NAT Gateway.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Savings Plans + Kinesis auto-scaling + Redshift pause/resume + Deep Archive + S3 Gateway Endpoint.

* **Why it succeeds:**
* **EC2:** EC2 Savings Plans (1-year Compute) provide up to 66% savings over On-Demand for 24/7 Spark instances without instance family lock-in.
* **Kinesis:** Kinesis auto-scaling (Application Auto Scaling using `PutScalingPolicy` on the `aws:kinesis:stream:shard-count` dimension) right-sizes shards to actual throughput demand, reducing idle shard costs.
* **Redshift:** Redshift pause/resume (native scheduler) eliminates 16 hrs/day of dc2 cluster cost — saving ~66% of Redshift compute.
* **S3:** S3 Glacier Deep Archive at $0.00099/GB/month vs S3 Standard at $0.023/GB/month = ~95% storage cost reduction for 600TB of cold data.
* **NAT Gateway:** S3 Gateway Endpoint (free) routes all S3 traffic from private subnets through the VPC endpoint, bypassing NAT Gateway. At $0.045/GB NAT processing for 50TB/month, this eliminates ~$2,250/month.

* **Why alternatives fail:**
  - **A)** Spot Instances for 24/7 Spark processing is high-risk — Spark job interruptions require checkpointing and retry logic; without that, data loss and job failures make this operationally unacceptable. Glacier Instant Retrieval is more expensive than Deep Archive for data not needing rapid retrieval.
  - **C)** 3-year all-upfront RIs reduce flexibility and Compute Savings Plans cover the same instance types with more flexibility. Deleting Redshift for Athena changes the query engine significantly and may break existing SQL workloads. Removing the NAT Gateway entirely and using IGW directly exposes private subnets to the internet — a security violation.
  - **D)** EC2 Savings Plans are correct, but migrating Redshift to Aurora Serverless is a significant workload migration with unknown cost impact and query compatibility issues. S3 Intelligent-Tiering on all 800TB adds monitoring charges ($0.0025/1000 objects) and is suboptimal for data definitively known to be cold after 180 days — a lifecycle policy to Deep Archive is cheaper and simpler.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 8: Domain 4 – Cost Control

A company's AWS bill shows $850,000/month. The FinOps team identifies: 
1. Data transfer costs of $180,000/month (inter-region and internet egress). 
2. EC2 coverage by Savings Plans is only 42%. 
3. RDS Multi-AZ instances running in dev/test accounts 24/7. 
4. CloudWatch custom metrics generating $45,000/month. 
5. API Gateway calls at $120,000/month for a high-traffic public API.

<div class="question-prompt">
**Question:** Which prioritized set of actions reduces costs most effectively?
</div>
- [ ] (1) Analyze VPC Flow Logs to identify top egress flows, implement CloudFront for public assets and PrivateLink for cross-account service access; (2) Purchase Compute Savings Plans to reach 80% EC2 coverage; (3) Use RDS instance scheduler (AWS Instance Scheduler) to stop dev/test RDS 16hrs/day; (4) Reduce CloudWatch metric resolution from 1-second to 1-minute (standard resolution); (5) Migrate high-traffic API to CloudFront + API Gateway with caching or evaluate HTTP API vs REST API downgrade.
- [ ] Move all workloads to a single region to eliminate inter-region transfer; buy 3-year Reserved Instances for all EC2; delete dev/test RDS; remove all custom CloudWatch metrics; migrate API Gateway to Application Load Balancer.
- [ ] Use AWS Cost Anomaly Detection to identify waste; enable S3 Intelligent-Tiering; convert API Gateway to GraphQL via AppSync; stop all non-production workloads at night using Lambda.
- [ ] Implement VPC Peering to eliminate NAT Gateway costs; use Savings Plans for EC2; enable RDS automated stop for dev/test; keep custom metrics but reduce dimensions; use API Gateway usage plans to throttle expensive callers.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — Systematic, service-by-service optimization with highest ROI actions per line item.

* **Why it succeeds:** Each action targets the specific root cause of each cost line item:
* **Data transfer ($180K):** CloudFront eliminates repeated origin egress for cacheable content; AWS PrivateLink for cross-account API calls replaces NAT Gateway + internet routing, reducing inter-AZ and egress charges.
* **Savings Plans (42% coverage):** AWS recommends 80%+ Savings Plan coverage for stable baseline workloads. Compute Savings Plans are preferred over EC2 RIs for flexibility across instance families.
* **Dev/Test RDS:** AWS Instance Scheduler stops RDS instances on schedule — Multi-AZ RDS in dev has no justification; stopping 16hrs/day = 66% compute reduction.
* **CloudWatch ($45K):** Custom metrics at 1-second high resolution cost $0.02/metric/month vs $0.01 at standard. Downgrading non-critical metrics to 1-minute resolution halves their cost.
* **API Gateway ($120K):** HTTP API is up to 71% cheaper than REST API for equivalent functionality without REST-specific features. CloudFront caching in front of API Gateway caches responses for GET/HEAD, dramatically reducing backend invocations.

* **Why alternatives fail:**
  - **B)** Consolidating to one region is architecturally catastrophic for resilience and ignores compliance/latency requirements. Deleting dev/test RDS eliminates development capability entirely.
  - **C)** AppSync/GraphQL migration is a full re-architecture — not a cost optimization action within a reasonable timeframe. Cost Anomaly Detection is diagnostic, not remedial.
  - **D)** VPC Peering doesn't eliminate NAT Gateway costs for internet-bound traffic — only for intra-VPC routing. Throttling API callers reduces functionality, not infrastructure cost.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 9: Domain 5 – Continuous Improvement for Existing Solutions

A production e-commerce platform experiences weekly database failovers on its Aurora MySQL cluster during peak traffic (Black Friday-scale loads). Investigations show: 
1. The writer instance CPU hits 95% during peak. 
2. Application connection pool exhaustion causes cascading Lambda timeouts. 
3. Post-failover, DNS propagation takes 30–45 seconds, during which transactions fail. 
4. The application doesn't distinguish between read and write queries.

<div class="question-prompt">
**Question:** Which set of improvements resolves ALL four issues?
</div>
- [ ] Upgrade Aurora writer to a larger instance class; increase Lambda connection pool size via environment variables; reduce Aurora's DNS TTL; add a read replica.
- [ ] Enable Aurora Auto Scaling for read replicas; implement RDS Proxy in front of the Aurora cluster (using the Proxy's writer and reader endpoints); configure the application to send reads to the reader endpoint and writes to the writer endpoint; enable Aurora Global Database for cross-region DR.
- [ ] Implement RDS Proxy (multiplexes Lambda connections to Aurora, eliminating connection pool exhaustion); configure Aurora reader endpoints in the application for read queries; implement Aurora Serverless v2 for the writer to auto-scale compute on demand; use Route 53 ARC (Application Recovery Controller) readiness checks to manage failover DNS cut-over.
- [ ] Migrate to DynamoDB for all product catalog reads; keep Aurora for transactional writes; use ElastiCache Redis for session data; implement SQS to dequeue Lambda invocations during peak.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — RDS Proxy + Aurora Reader Endpoints + Aurora Serverless v2 + Route 53 ARC.

* **Why it succeeds:**
* **Issue 1 (CPU 95%):** Aurora Serverless v2 auto-scales ACUs (Aurora Capacity Units) in fine-grained increments (0.5 ACU steps) within seconds of load increase — eliminates CPU saturation without manual instance resizing.
* **Issue 2 (Connection pool exhaustion):** RDS Proxy maintains a persistent connection pool to Aurora and multiplexes thousands of Lambda ephemeral connections into a small set of database connections. Lambda's per-invocation connection creation is the root cause; Proxy resolves this natively.
* **Issue 3 (DNS failover latency):** Route 53 ARC provides zonal shift and readiness checks with automated DNS failover faster than the default Aurora DNS TTL approach. ARC can shift traffic in < 1 minute with health-check-driven DNS updates.
* **Issue 4 (No read/write split):** Aurora's cluster reader endpoint load-balances across all read replicas. Routing read queries to the reader endpoint reduces writer load.

* **Why alternatives fail:**
  - **A)** Manually upgrading instance class is reactive and doesn't scale for unpredictable peaks. Increasing Lambda connection pool size via environment variables doesn't solve the fundamental problem — more Lambda concurrent invocations still overwhelm Aurora with connections. Reducing DNS TTL helps marginally but doesn't eliminate the 30-45 second gap.
  - **B)** Correct on RDS Proxy and reader endpoints, but Aurora Global Database is for cross-region DR (RPO seconds), not for intra-region failover speed improvement. It adds cost without solving the 30-45 second DNS propagation issue.
  - **D)** Migrating to DynamoDB is a complete re-architecture with schema redesign — far beyond the scope of "continuous improvement." ElastiCache for sessions is valid but doesn't address the core database failover and connection exhaustion issues.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 10: Domain 5 – Continuous Improvement for Existing Solutions

A media company runs a global video streaming platform. The current CDN architecture uses CloudFront with S3 origins. Issues reported: 
1. Cache hit ratio is only 38% (benchmark: >85%). 
2. Origin S3 requests are causing S3 request costs of $45,000/month. 
3. Users in Southeast Asia report 4-6 second TTFB (Time to First Byte) for video segments. 
4. Some video segments are being served incorrectly (wrong resolution variant) to certain device types.

<div class="question-prompt">
**Question:** Which combination of CloudFront improvements addresses all four issues?
</div>
- [ ] Enable CloudFront Origin Shield in a central region; increase CloudFront default TTL to 86400s; use Lambda@Edge at the origin request event to rewrite URLs based on User-Agent; enable CloudFront real-time logs to diagnose cache misses.
- [ ] Enable CloudFront Origin Shield in the AWS region closest to the S3 origin; configure Cache Policies with appropriate TTLs (removing query strings and headers from cache keys that vary unnecessarily); implement CloudFront Functions at viewer request to normalize User-Agent headers to device categories (mobile/desktop/TV) and modify the cache key; add a regional edge cache in ap-southeast-1 by selecting the nearest Origin Shield region.
- [ ] Migrate S3 origin to an ALB-fronted EC2 fleet for dynamic content serving; use CloudFront with path-based behaviors; implement WAF with device detection rules; enable S3 Transfer Acceleration for the origin.
- [ ] Switch CDN to AWS Global Accelerator; configure S3 buckets in each region; use Route 53 geolocation routing to the nearest S3 bucket; implement device detection in the application layer.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Origin Shield + Cache Policies + CloudFront Functions + regional Origin Shield placement.

* **Why it succeeds:**
* **Issue 1 (38% cache hit ratio):** Low cache ratio is almost always caused by cache key pollution — headers, cookies, or query strings in the cache key that vary unnecessarily. CloudFront Cache Policies allow precise control over what's included in the cache key. Removing irrelevant headers/cookies dramatically improves cache hit ratio.
* **Issue 2 (S3 cost $45K):** CloudFront Origin Shield adds a centralised caching layer between CloudFront edge locations and the S3 origin, collapsing redundant origin requests into one. Origin Shield reduces origin load by up to 75%.
* **Issue 3 (TTFB in SEA):** Selecting the ap-southeast-1 (Singapore) Origin Shield region minimises the CloudFront edge → Origin Shield → S3 round-trip for SEA users. CloudFront's 400+ edge PoPs in SEA then serve from the regional cache.
* **Issue 4 (Wrong resolution variant):** CloudFront Functions (not Lambda@Edge) run at viewer request with sub-millisecond execution — ideal for normalising User-Agent into device category and modifying the cache key so that mobile/desktop/TV users receive their correct video variant from cache.

* **Why alternatives fail:**
  - **A)** Lambda@Edge at origin request fires only on cache misses — it doesn't affect the cache key at viewer request time, so the wrong variant can still be cached and served. Lambda@Edge has cold start latency; CloudFront Functions are better for simple header manipulation.
  - **C)** Migrating to ALB+EC2 for static video segments is unnecessary and costly — S3 is the correct origin for static content. S3 Transfer Acceleration is for uploads, not CDN performance.
  - **D)** Global Accelerator optimises TCP/UDP routing for non-HTTP workloads and doesn't provide content caching. Replacing a CDN with Global Accelerator for video streaming eliminates all caching benefits and massively increases origin load and cost.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 11: Domain 1 – Design Solutions for Organizational Complexity

An enterprise has implemented IAM Identity Center with Active Directory as the identity source (via AD Connector). They have 15 AWS accounts in an Organization. Requirement: 
1. A group `SRE-Team` in AD must have read-only access to CloudWatch, EC2 describe actions, and SSM Session Manager access in all 15 production accounts. 
2. The `SRE-Team` must never have IAM or billing access. 
3. When an SRE leaves the company, access must be revoked within 5 minutes across all 15 accounts. 
4. The AD group membership is managed by the HR system, not by AWS admins.

<div class="question-prompt">
**Question:** Which architecture satisfies all requirements with least privilege and operational efficiency?
</div>
- [ ] Create 15 IAM roles (one per account) with the required policies; SREs assume roles via cross-account trust; sync AD group to IAM using custom Lambda that polls AD every 5 minutes.
- [ ] Create a custom Permission Set in IAM Identity Center with an inline policy granting `CloudWatch:Get*/List*`, `ec2:Describe*`, and `ssm:StartSession`; create an Account Assignment mapping the AD SRE-Team group to this Permission Set across all 15 accounts; configure IAM Identity Center to use AD Connector as the identity source with sync interval set to near-real-time (AD Connector syncs on authentication).
- [ ] Create Permission Sets in IAM Identity Center; use AWS Organizations Tag Policies to tag accounts as Env=Prod; write a Lambda that auto-assigns the Permission Set to tagged accounts; AD group sync handled by IAM Identity Center's SCIM provisioning.
- [ ] Federate directly using SAML 2.0 between AD FS and each of the 15 AWS accounts; create IAM roles with SAML trust in each account; manage group membership in AD; session duration set to 1 hour for fast expiry.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — IAM Identity Center Permission Sets + AD group mapping + Account Assignments across all 15 accounts.

* **Why it succeeds:** IAM Identity Center with AD Connector does not sync users/groups proactively — it authenticates on-demand. When an SRE authenticates, IAM Identity Center queries AD in real time for group membership. When an SRE is removed from the `SRE-Team` AD group by HR, their next authentication fails the group check. More critically, existing sessions expire based on the Permission Set session duration (set to 5 minutes or configured to match requirements). Account Assignments in IAM Identity Center propagate a single Permission Set to all 15 accounts simultaneously — no per-account role management. The inline policy in the Permission Set precisely scopes CloudWatch/EC2/SSM without IAM or billing permissions, satisfying least privilege.

* **Why alternatives fail:**
  - **A)** Managing 15 IAM roles manually and a Lambda polling AD every 5 minutes is operationally fragile — Lambda failure creates a security gap. IAM roles don't automatically invalidate active sessions when the Lambda removes the user.
  - **C)** Tag Policies and Lambda auto-assignment is a complex, custom solution that duplicates IAM Identity Center's native Account Assignment capability. SCIM provisioning is for IdPs like Okta/Azure AD, not AD Connector (which uses AD authentication directly, not SCIM).
  - **D)** Per-account SAML federation requires maintaining 15 separate IdP/SP configurations in AD FS and 15 IAM SAML providers — massive operational overhead. Session expiry at 1 hour means access persists for up to 60 minutes after an SRE is offboarded, violating the 5-minute requirement.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 12: Domain 2 – Design for New Solutions

A company wants to build a real-time fraud detection pipeline for financial transactions. Requirements: 
1. Ingest 500,000 transactions/second at peak. 
2. ML model inference must complete in < 50ms per transaction. 
3. Fraudulent transactions must trigger an immediate block at the payment processor API within 100ms of detection. 
4. All transactions must be stored for 7-year regulatory retention with query capability. 
5. The pipeline must survive a full AZ outage with zero data loss.

<div class="question-prompt">
**Question:** Which architecture satisfies all five requirements?
</div>
- [ ] API Gateway → Kinesis Data Streams (500 shards) → Lambda (ML inference via SageMaker endpoint) → SNS → SQS → Lambda (block transaction); S3 + Glacier for retention; Multi-AZ Kinesis (built-in).
- [ ] NLB → EC2 Auto Scaling (ingest tier) → Amazon MSK (Kafka, Multi-AZ, replication factor 3) → ECS Fargate consumers (SageMaker real-time endpoint for inference) → EventBridge (route fraud events) → Lambda (call payment processor block API); Kinesis Data Firehose → S3 (7-year lifecycle to Deep Archive); MSK provides AZ-fault-tolerant replication.
- [ ] API Gateway → Kinesis Data Streams → Kinesis Data Analytics (Flink) for real-time ML scoring (RANDOM_CUT_FOREST anomaly detection) → EventBridge → Lambda (block API call); S3 + Athena for 7-year retention and querying; Kinesis cross-AZ replication natively.
- [ ] SQS FIFO → Lambda (ML inference) → Step Functions (fraud workflow orchestration) → SNS (notify payment processor); DynamoDB for hot storage; S3 Glacier for archival.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — MSK (Kafka) + ECS Fargate + SageMaker + EventBridge + Firehose → S3.

* **Why it succeeds:**
* **500K TPS (Req 1):** Amazon MSK with Kafka handles millions of messages/second natively. Kafka's partition model provides horizontal scale. NLB at the ingest tier handles the TCP connection volume.
* **< 50ms inference (Req 2):** SageMaker real-time inference endpoints with ECS Fargate consumers (long-running, no cold start) provide consistent low-latency inference. Lambda cold starts make sub-50ms p99 guarantees unreliable at this scale.
* **100ms block (Req 3):** EventBridge routes fraud events with sub-millisecond routing latency to Lambda, which calls the payment processor synchronously within the 100ms budget.
* **7-year retention + query (Req 4):** Kinesis Firehose buffers and lands data to S3; S3 Lifecycle transitions to Deep Archive; Athena provides SQL query capability over S3.
* **AZ fault tolerance (Req 5):** MSK Multi-AZ with replication factor 3 ensures no data loss during AZ outage. Kafka's ISR (In-Sync Replicas) guarantees acknowledged writes survive AZ loss.

* **Why alternatives fail:**
  - **A)** Lambda for ML inference at 500K TPS will hit concurrency limits (default 10,000 per region) and cold starts will exceed 50ms. API Gateway has a 29-second timeout but at this ingestion rate, the API Gateway HTTP overhead adds latency.
  - **C)** Kinesis Data Analytics (Flink) with RANDOM_CUT_FOREST is an anomaly detection algorithm — not a trained fraud ML model. It cannot run a custom SageMaker model endpoint within the Flink job. The architecture also doesn't address the 100ms block requirement with sufficient precision.
  - **D)** SQS FIFO is limited to 3,000 TPS per API per queue — utterly insufficient for 500K TPS. Step Functions add orchestration overhead (100ms+ per state transition), breaking the 100ms block requirement.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 13: Domain 3 – Migration Planning

A company is migrating from on-premises Oracle Database 19c (12TB, 2,000 stored procedures, 150 database-linked servers) to AWS. The go-live deadline is 6 months. The Oracle license is expiring and will not be renewed. Constraints: 
1. Must eliminate Oracle licensing cost entirely. 
2. Application team estimates 60% of stored procedures can be auto-converted, 40% require manual rewrite. 
3. Zero downtime migration — the application cannot be offline during cutover. 
4. The new database must handle 20,000 read IOPS and 5,000 write IOPS.

<div class="question-prompt">
**Question:** Which migration approach is technically correct and meets all constraints?
</div>
- [ ] Use AWS SCT to convert Oracle schema and stored procedures to PostgreSQL-compatible syntax; migrate to Amazon Aurora PostgreSQL; use AWS DMS with ongoing replication (CDC) to sync data continuously; use SCT's assessment report to prioritize manual conversion work; cutover by stopping DMS replication and redirecting the application connection string.
- [ ] Use AWS DMS to migrate directly from Oracle to RDS for MySQL; use SCT for stored procedure conversion; cutover via DNS change; Aurora MySQL for scaling.
- [ ] Migrate to Amazon RDS for Oracle first (lift-and-shift, BYOL); decommission on-premises; then perform a second migration from RDS Oracle to Aurora PostgreSQL over 6 months.
- [ ] Use SCT to convert Oracle to Aurora PostgreSQL Serverless v2; use DMS for full-load + CDC replication; perform blue/green deployment with Aurora's native Blue/Green feature for zero-downtime cutover.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — SCT → Aurora PostgreSQL Serverless v2 + DMS CDC + Aurora Blue/Green Deployment.

* **Why it succeeds:**
* **Eliminate Oracle licensing (Req 1):** Aurora PostgreSQL is fully open-source-compatible, no Oracle license required.
* **Stored procedure conversion (Req 2):** AWS SCT auto-converts up to 60% of Oracle PL/SQL to PL/pgSQL. SCT's assessment report explicitly flags the 40% requiring manual intervention, with action items and complexity ratings.
* **Zero downtime (Req 3):** Aurora Blue/Green Deployment creates a staging (green) environment as an exact replica, applies all changes, and performs a managed switchover in < 1 minute with automatic traffic redirection — the lowest-risk zero-downtime cutover mechanism natively supported by Aurora.
* **IOPS requirements (Req 4):** Aurora PostgreSQL Serverless v2 auto-scales ACUs; for dedicated IOPS, Aurora provisioned with io1 or gp3 storage handles 20,000+ read IOPS. Aurora's read replicas additionally offload read traffic.
* DMS with CDC replication keeps the target Aurora in sync with Oracle during the migration window, then Blue/Green switchover stops DMS and redirects traffic atomically.

* **Why alternatives fail:**
  - **A)** Correct approach (SCT + Aurora PostgreSQL + DMS CDC), but the cutover method (stopping DMS and redirecting connection string) is high-risk and not zero-downtime — there's a manual window. Aurora Blue/Green Deployment (option D) is the superior cutover mechanism.
  - **B)** MySQL is not the optimal target for Oracle PL/SQL migration — PostgreSQL's PL/pgSQL is structurally closer to Oracle PL/SQL, yielding higher SCT auto-conversion rates. Oracle-to-MySQL conversion requires more manual effort.
  - **C)** Migrating to RDS Oracle (BYOL) first means paying for BYOL Oracle licenses during the 6-month migration period — directly violating the cost constraint of eliminating Oracle licensing.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 14: Domain 4 – Cost Control

A startup's AWS costs have grown from $20K to $180K/month in 6 months with no significant revenue growth. AWS Cost Explorer shows: 
1. 40% of cost is EC2 — mostly On-Demand, mixed instance types, utilization averaging 15%. 
2. 25% is data transfer — primarily EC2-to-EC2 cross-AZ and S3 GET requests from EC2 in private subnets. 
3. 20% is RDS — Multi-AZ in dev/test accounts running 24/7. 
4. 15% is miscellaneous (CloudWatch Logs ingestion: $18K/month; unused Elastic IPs: $2K/month; unattached EBS volumes: $4K/month).

<div class="question-prompt">
**Question:** Rank and implement the highest-impact cost reduction measures:
</div>
- [ ] Purchase 3-year all-upfront Reserved Instances for all EC2; implement cross-AZ traffic reduction; stop dev/test RDS; clean up unused resources.
- [ ] Right-size EC2 using AWS Compute Optimizer recommendations; purchase Compute Savings Plans (1-year) for the right-sized baseline; add S3 Gateway Endpoints and VPC Endpoints to eliminate cross-AZ data transfer for S3/AWS service traffic; implement RDS Instance Scheduler for dev/test; configure CloudWatch Logs subscription filters to route only ERROR/CRITICAL logs to CloudWatch and route DEBUG/INFO to S3 via Firehose; release unused EIPs and delete unattached EBS volumes.
- [ ] Convert all EC2 to Spot Instances; use S3 Intelligent-Tiering; delete dev RDS and use SQLite locally; remove CloudWatch Logs entirely; terminate unused resources.
- [ ] Migrate all workloads to Fargate (no idle EC2 cost); use DynamoDB instead of RDS; implement Lambda for all compute; remove CloudWatch Logs and use third-party logging.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Right-size first, then commit; eliminate transfer waste; schedule dev/test; clean up orphaned resources.

* **Why it succeeds:** The Well-Architected Cost Optimization pillar mandates right-size before committing to pricing. At 15% average utilization, EC2 instances are significantly over-provisioned. Compute Optimizer provides ML-based rightsizing recommendations. Only after rightsizing should Savings Plans be purchased to lock in the optimized baseline. S3 Gateway Endpoints (free) eliminate all S3-bound EC2 data transfer charges that currently route through NAT Gateway ($0.045/GB). VPC endpoints for other AWS services eliminate cross-AZ traffic to regional services. CloudWatch Logs at $0.50/GB ingestion — filtering to ERROR+ and routing verbose logs to S3 (via Firehose at $0.029/GB) can reduce CloudWatch Logs costs by 80–90%.

* **Why alternatives fail:**
  - **A)** Purchasing 3-year RIs for over-provisioned, mixed instance types locks in waste at high cost. The 15% utilization means 85% of committed cost is idle. Must right-size first.
  - **C)** Spot Instances for unknown workloads (no mention of interruption tolerance) is high-risk. Removing CloudWatch Logs entirely eliminates observability — operationally unacceptable.
  - **D)** Migrating all EC2 to Fargate and all RDS to DynamoDB is a complete re-architecture estimated at months of engineering effort — not a cost optimization action. Fargate has per-vCPU/GB pricing that can exceed EC2 for consistently high-utilization workloads.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 15: Domain 5 – Continuous Improvement for Existing Solutions

A fintech company's API Gateway + Lambda architecture is experiencing: 
1. P99 latency of 8 seconds (SLA: < 500ms). 
2. Lambda function cold starts averaging 3.2 seconds (Java runtime). 
3. 25% error rate on POST /transactions during peak (500 TPS). 
4. DynamoDB throttling errors correlating with the error rate. 
5. Downstream payment processor API times out at 3 seconds, causing Lambda to retry, exhausting concurrency.

<div class="question-prompt">
**Question:** Which improvements address ALL five issues systematically?
</div>
- [ ] Increase Lambda memory to 10GB; enable Provisioned Concurrency for Lambda; add DynamoDB Auto Scaling; increase API Gateway timeout to 29 seconds; implement exponential backoff in Lambda for payment processor retries.
- [ ] Migrate Lambda runtime from Java to Python or Node.js; enable Lambda Provisioned Concurrency (scheduled scaling for peak hours); implement DynamoDB on-demand capacity (eliminates throttling); use SQS queue between Lambda and payment processor (async, Lambda puts transaction to SQS, returns 202 Accepted, separate Lambda processes queue with retry logic); implement API Gateway caching for idempotent GET endpoints.
- [ ] Replace Lambda with ECS Fargate (no cold starts); replace DynamoDB with Aurora Serverless; implement Circuit Breaker pattern via App Mesh; use SQS for payment processor integration.
- [ ] Enable Lambda SnapStart for Java runtime; implement DynamoDB DAX for caching; use Step Functions for payment processor retry orchestration with exponential backoff; implement API Gateway throttling (10,000 RPS limit) to protect Lambda concurrency.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** + **D** combined — but if forced to choose one, **D** is most complete for the Java runtime case.

**Why D succeeds:**
* **Cold starts (Issue 2):** Lambda SnapStart for Java (Corretto 11/17/21 runtimes) pre-initialises the execution environment and restores from a snapshot, reducing Java cold starts from 3+ seconds to < 1 second — the most impactful fix for Java Lambda cold starts without changing runtime.
* **DynamoDB throttling (Issue 4):** DAX provides microsecond read caching; for write throttling, DynamoDB on-demand mode (per B) or provisioned with Auto Scaling resolves write throttle. DAX addresses read-heavy patterns.
* **Payment processor timeout/retry (Issue 5):** Step Functions with Wait states and exponential backoff orchestrates retries without blocking Lambda concurrency — Lambda invokes Step Functions (async), returns immediately, freeing concurrency.
* **API Gateway throttling:** Protects the Lambda concurrency pool from being overwhelmed at 500 TPS.

**Why B is partially correct:** Switching to Python/Node.js eliminates Java's JVM startup cost but requires rewriting the entire Lambda function — significant engineering effort when SnapStart achieves the same result for Java. The SQS async pattern for payment processor is architecturally sound.

* **Why alternatives fail:**
  - **A)** Increasing Lambda memory doesn't fix cold starts for Java (JVM initialization is time-based, not memory-based). Increasing API Gateway timeout to 29 seconds raises the SLA violation ceiling — not a solution. Exponential backoff in Lambda still blocks Lambda concurrency during retries.
  - **C)** Migrating to ECS Fargate eliminates cold starts but requires complete re-architecture of the serverless stack — disproportionate to the problem scope. Aurora Serverless for DynamoDB is a schema migration.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 16: Domain 1 – Design Solutions for Organizational Complexity

A company operates in 8 AWS regions with 120 accounts under AWS Organizations. The network team must implement centralized DNS resolution so that: 
1. On-premises hosts can resolve `*.internal.corp` (private Route 53 hosted zones). 
2. AWS Lambda and EC2 in all VPCs can resolve on-premises hostnames `(*.onprem.corp)` via on-premises DNS servers (10.0.0.53, 10.0.0.54). 
3. The solution must function over Direct Connect and must not require a DNS server deployed on EC2. 
4. All changes must be centrally managed.

<div class="question-prompt">
**Question:** Which architecture satisfies all constraints?
</div>
- [ ] Deploy EC2-based BIND DNS servers in a hub VPC per region; configure on-premises DNS to forward to BIND servers; configure VPC DHCP option sets to use BIND server IPs.
- [ ] Create Route 53 Resolver Inbound Endpoints in a centralized Network Hub VPC (one per region); associate the private hosted zone `*.internal.corp` with the Hub VPC; configure on-premises DNS to forward `*.internal.corp` queries to the Inbound Endpoint IPs over Direct Connect; create Route 53 Resolver Outbound Endpoints in the Hub VPC with a Forwarding Rule for `*.onprem.corp` → 10.0.0.53/10.0.0.54; share the Forwarding Rule via AWS RAM to all 120 account VPCs; associate VPCs with the rule.
- [ ] Use Route 53 Resolver DNS Firewall to intercept all DNS queries; forward on-premises queries via a DNS firewall rule group; associate with all VPCs via RAM.
- [ ] Create a private hosted zone `*.onprem.corp` in Route 53 that mirrors all on-premises DNS records; configure zone delegation from on-premises DNS to Route 53; use Route 53 health checks to detect on-premises DNS changes.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Route 53 Resolver Inbound + Outbound Endpoints in a hub VPC, shared via RAM.

* **Why it succeeds:** Route 53 Resolver is the AWS-managed DNS service (no EC2 required, satisfying constraint 3):
* **Inbound Endpoints** (ENIs in the Hub VPC) receive DNS queries from on-premises over Direct Connect. On-premises DNS forwards `*.internal.corp` to these ENI IPs. Route 53 responds from the associated private hosted zone.
* **Outbound Endpoints** send queries from AWS to on-premises DNS servers (10.0.0.53/54) for `*.onprem.corp`. Forwarding Rules define this target.
* **AWS RAM** shares the Resolver Rules (Forwarding Rules) to all 120 accounts — VPCs in those accounts associate with the shared rule and automatically forward `*.onprem.corp` to on-premises. Centralized management in one network account.
* **Private hosted zone** association with the Hub VPC (and via RAM sharing or authorization for spoke VPCs) handles `*.internal.corp` resolution.

* **Why alternatives fail:**
  - **A)** EC2-based BIND servers violate constraint 3 (no EC2 DNS servers). They also create single points of failure and maintenance overhead at scale across 8 regions.
  - **C)** Route 53 Resolver DNS Firewall is a security filtering tool (blocks/allows DNS queries based on domain lists) — it cannot forward queries to on-premises DNS servers. It's not a DNS forwarding solution.
  - **D)** Mirroring all on-premises DNS records into Route 53 is operationally impossible to maintain (on-premises DNS changes require manual Route 53 updates). Zone delegation from on-premises to Route 53 reverses the traffic flow incorrectly for outbound resolution.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 17: Domain 2 – Design for New Solutions

A company is building a serverless data lake ingestion pipeline. Sources: 
1. IoT devices sending 50MB/s of telemetry via MQTT. 
2. Nightly 500GB database exports from on-premises via SFTP. 
3. Real-time clickstream data from a web application (100,000 events/minute). 

Requirements: 
* **R1:** All data must land in S3 in Parquet format. 
* **R2:** Data must be queryable within 5 minutes of ingestion. 
* **R3:** PII must be automatically detected and masked before Parquet conversion. 
* **R4:** Total pipeline cost must scale with data volume (no idle infrastructure cost).

<div class="question-prompt">
**Question:** Which architecture satisfies all requirements?
</div>
- [ ] IoT Core → Kinesis Data Streams → Lambda (PII mask) → Kinesis Firehose (Parquet conversion) → S3; SFTP → AWS Transfer Family → Lambda (convert + mask) → S3; Clickstream → API Gateway → Kinesis Firehose → S3; Glue Crawler for queryability.
- [ ] IoT Core → Kinesis Data Streams → Kinesis Data Firehose (with Lambda transformation for PII masking via Amazon Comprehend detect PII) → S3 (Parquet via Firehose's built-in conversion using a Glue schema); SFTP exports → AWS Transfer Family (SFTP) → S3 (raw) → AWS Glue ETL job (PII mask + Parquet) → S3 (processed); Clickstream → Kinesis Firehose (directly from app via SDK) → same Lambda transform → S3; Glue Data Catalog + Athena for < 5min queryability after Glue Crawler trigger on S3 PUT events.
- [ ] All sources → Amazon MSK → Kafka Connect → S3; Glue for PII detection; EMR for Parquet conversion; Athena for querying.
- [ ] IoT Core → SQS → Lambda → S3; SFTP → EC2 SFTP server → S3 sync; Clickstream → Direct PUT to S3 from app; Macie for PII detection; Glue for Parquet; Athena for querying.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Kinesis Firehose with Lambda transformation + Comprehend + Glue schema conversion; Transfer Family for SFTP; serverless Glue ETL; Athena for querying.

* **Why it succeeds:**
* **R1 (Parquet):** Kinesis Firehose natively converts JSON to Parquet using a Glue Data Catalog table schema — no custom code needed. Glue ETL handles Parquet conversion for batch SFTP files.
* **R2 (5-min queryability):** Firehose delivers to S3 in 60-second buffers (minimum). Glue Crawler triggered by S3 event updates the Data Catalog within minutes. Athena queries the updated catalog immediately.
* **R3 (PII masking):** Firehose's Lambda transformation invokes Amazon Comprehend DetectPiiEntities API per record, masks detected PII before Parquet conversion. Glue ETL for SFTP files uses Glue's built-in `detect_sensitive_data` transform.
* **R4 (Scale-to-zero cost):** Kinesis Firehose charges per GB processed (no idle cost). Lambda charges per invocation. AWS Transfer Family charges per hour of endpoint (minimal baseline) + data transfer. Athena charges per query TB scanned. No always-on servers.

* **Why alternatives fail:**
  - **A)** Kinesis Data Streams → Lambda → Firehose adds unnecessary Kinesis Data Streams cost and complexity. Firehose can receive data directly from IoT Core via Kinesis Data Streams OR direct PUT. The architecture also doesn't specify Parquet conversion mechanism clearly.
  - **C)** Amazon MSK + EMR is an always-on infrastructure model — MSK minimum cost ~$0.21/hr/broker, EMR cluster always running. Violates R4's scale-to-zero requirement.
  - **D)** Amazon Macie is a data security service that scans S3 buckets for PII — it's not a real-time transformation tool. Macie cannot mask PII inline during ingestion; it only detects and alerts. EC2 SFTP server violates serverless/scale-to-zero requirement.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 18: Domain 5 – Continuous Improvement for Existing Solutions

A company's production EKS cluster (Kubernetes 1.27) running on EC2 managed node groups shows: 
1. Node CPU utilization averages 12% across 50 m5.2xlarge nodes. 
2. Pod scheduling failures (Pending pods) occur during traffic spikes for 8–12 minutes. 
3. The team manually updates kubeconfig credentials every 12 hours (IAM temporary credentials). 
4. Nodes run mixed workloads — both stateless APIs and stateful Kafka consumers. 
5. EKS control plane upgrade to 1.29 has been deferred for 6 months (EOL risk).

<div class="question-prompt">
**Question:** Which set of improvements addresses all five issues?
</div>
- [ ] Add more m5.2xlarge nodes to eliminate pending pods; implement a Kubernetes CronJob to refresh kubeconfig; separate stateful and stateless workloads into separate node groups; upgrade EKS manually via eksctl upgrade cluster.
- [ ] Implement Karpenter (node autoprovisioner) replacing managed node group Cluster Autoscaler — Karpenter provisions right-sized nodes in 60–90 seconds on pod pending events (resolves issues 1 and 2); configure EKS Pod Identity (replacing IRSA for simplified IAM; or IRSA with aws-eks-auth config) for automatic credential refresh via OIDC (resolves issue 3); create separate Karpenter NodePools with nodeSelector for stateless vs stateful workloads (resolves issue 4); execute in-place EKS cluster upgrade using managed node group rolling update strategy (resolves issue 5).
- [ ] Migrate all workloads to ECS Fargate to eliminate node management; use ECS task IAM roles for credentials; separate services into different ECS clusters; ECS handles scaling automatically.
- [ ] Enable Cluster Autoscaler with aggressive scale-up settings; use IAM Identity Center for kubeconfig refresh; add a dedicated node group for stateful workloads; upgrade EKS using Blue/Green cluster replacement.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Karpenter + Pod Identity/IRSA + separate NodePools + in-place upgrade.

* **Why it succeeds:**
* **Issue 1 (12% CPU):** Karpenter's bin-packing algorithm consolidates pods onto fewer, right-sized nodes and terminates underutilized nodes. Unlike Cluster Autoscaler (which scales existing node groups), Karpenter provisions the exact instance type matching the pending pod's resource request — eliminating 88% idle capacity waste.
* **Issue 2 (8–12 min scheduling delays):** Cluster Autoscaler's scale-up triggers on pending pods but then waits for ASG to provision nodes (3–5 min) plus node join time. Karpenter directly calls EC2 RunInstances and has pods running in 60–90 seconds — within the tight latency window.
* **Issue 3 (Manual kubeconfig refresh):** EKS Pod Identity (GA since 2023) or IRSA with aws-eks-auth config provides automatic IAM credential rotation via OIDC — no manual kubeconfig management. Pod Identity simplifies IRSA by removing the need for OIDC provider ARN annotations.
* **Issue 4 (Mixed workloads):** Karpenter NodePools with nodeSelector or taints/tolerations segregate stateless API pods (burstable instance types) from stateful Kafka consumers (compute-optimized, no spot).
* **Issue 5 (EOL risk):** EKS in-place cluster upgrade (control plane first, then managed node groups rolling update) is the standard upgrade path via `eksctl upgrade cluster --name <cluster> --kubernetes-version 1.29`.

* **Why alternatives fail:**
  - **A)** Adding more fixed nodes increases the idle CPU waste problem further. CronJob for kubeconfig refresh is a fragile workaround. Manual eksctl upgrade without a strategy risks disruption.
  - **C)** Migrating to ECS Fargate is a complete platform migration — all Kubernetes manifests, Helm charts, and Kubernetes-native features (CRDs, custom controllers) would need re-implementation. Not a continuous improvement action.
  - **D)** Cluster Autoscaler with aggressive settings doesn't solve the 12% CPU waste — it still scales node groups, not individual right-sized nodes. Blue/Green cluster replacement for upgrades requires full workload migration across clusters — high operational risk.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 19: Domain 3 – Migration Planning

A company is migrating a monolithic on-premises Java application to AWS using the Strangler Fig pattern. The monolith handles: orders, inventory, payments, notifications. The team wants to extract the payment service first (highest business value). Current state: All services share a single Oracle DB. On-premises → AWS connectivity is via Direct Connect (1 Gbps). Team has 4 developers and a 3-month first extraction window.

<div class="question-prompt">
**Question:** Which migration approach correctly implements Strangler Fig for the payment service extraction with minimal risk?
</div>
- [ ] Refactor the entire monolith to microservices simultaneously; deploy all services to EKS; migrate all data from Oracle to Aurora in parallel; redirect traffic via ALB after completion.
- [ ] Deploy a new Payment microservice on ECS Fargate with its own Aurora PostgreSQL database; use AWS DMS to replicate payment-related Oracle tables to Aurora (bidirectional CDC for dual-write period); deploy an API Gateway in front of both the monolith and new payment service; implement a feature flag in API Gateway (using Lambda authorizer or request routing) to route POST /payments traffic to the new service while all other traffic goes to monolith; use AWS Migration Hub Refactor Spaces to manage the proxy routing and incremental traffic shifting.
- [ ] Create a payment Lambda function; expose via API Gateway; write directly to the same Oracle DB; deprecate the monolith payment module; redirect via DNS.
- [ ] Use AWS App Mesh to implement a service mesh across the monolith and new payment service; migrate payment data to DynamoDB; implement event sourcing with EventBridge; redirect traffic gradually via weighted routing in App Mesh.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — New Payment service on ECS Fargate + own Aurora DB + DMS CDC + API Gateway routing + Refactor Spaces.

* **Why it succeeds:** The Strangler Fig pattern requires: (1) A proxy/facade that intercepts traffic and routes to either old or new system. (2) Incremental traffic shifting to the new service. (3) A data migration strategy that keeps both systems consistent during the transition. API Gateway + Lambda authorizer (or request-based routing) serves as the proxy. Refactor Spaces manages the routing environment. DMS with bidirectional CDC keeps Oracle and Aurora in sync during the dual-write period — as long as both systems process payments, data consistency is maintained. Feature flags enable controlled traffic shifting (5% → 25% → 100%). ECS Fargate for the new service requires no container infrastructure management. Aurora PostgreSQL is the natural target for Oracle migration (SCT compatible). This exactly follows the AWS Strangler Fig microservices pattern from the AWS Architecture Blog.

* **Why alternatives fail:**
  - **A)** Refactoring the entire monolith simultaneously is the "Big Bang" anti-pattern — opposite of Strangler Fig. Three months and 4 developers cannot refactor orders + inventory + payments + notifications simultaneously with data migration.
  - **C)** New payment Lambda writing to the same Oracle DB creates tight coupling — the entire point of Strangler Fig is to extract the data domain as well. Sharing the Oracle DB means the monolith and new service are still coupled at the data layer.
  - **D)** App Mesh service mesh is a valid architectural pattern but adds significant operational complexity (Envoy proxies, mTLS configuration) for a 4-developer team with a 3-month window. DynamoDB as a payment database requires complete schema redesign from relational Oracle — too risky for the first extraction.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 20: Domain 4 – Cost Control

A company runs Amazon Redshift (ra3.4xlarge × 8 nodes, $X/month) and Amazon EMR (r5.2xlarge × 20 core nodes On-Demand, running 24/7) for a data analytics platform. Redshift queries run only during business hours (8am–6pm, 5 days/week). EMR processes daily batch jobs that run for 4 hours starting at 2am. The remaining 20 hours per day, EMR nodes are idle. S3 houses 2PB of raw data. Athena is not currently used.

<div class="question-prompt">
**Question:** Which architecture changes deliver the maximum cost reduction?
</div>
- [ ] Use Redshift pause/resume on a schedule; convert EMR to EMR Serverless; migrate warm query data from S3 raw to Redshift Spectrum for federated querying.
- [ ] Migrate Redshift to Athena entirely; terminate EMR and use Lambda for all data processing; use S3 Intelligent-Tiering for all 2PB.
- [ ] Enable Redshift pause/resume (pause at 6pm, resume at 7:55am weekdays = ~128 hrs/week idle, saving ~76% of compute cost); migrate EMR On-Demand cluster to EMR on EC2 with Spot Instances for core/task nodes + transient cluster model (spin up at 1:55am, terminate at 6am = 4.08 hrs/day billed vs 24 hrs/day = 83% reduction); use S3 Lifecycle policies to tier data older than 90 days to S3 Glacier Instant Retrieval for 2PB raw data (68% storage cost reduction); implement Redshift Spectrum for querying S3 data directly without loading into Redshift.
- [ ] Downsize Redshift to ra3.xlplus; use EMR Managed Scaling; keep On-Demand EMR; use S3 Intelligent-Tiering; add Redshift concurrency scaling.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Redshift pause/resume + transient EMR Spot cluster + S3 tiering + Redshift Spectrum.

* **Why it succeeds:**
* **Redshift pause/resume:** ra3 clusters support pause/resume; pausing 128 hours/week (nights + weekends) when business hours = 50 hrs/week saves approximately 128/(128+50) = 72% of weekly Redshift compute cost. With ra3.4xlarge at ~$3.26/node/hr × 8 = $26.08/hr, saving 128 hrs/week = ~$3,338/week = ~$13,400/month.
* **Transient EMR Spot:** EMR Spot pricing = ~70% discount vs On-Demand. Transient cluster (4 hrs/day vs 24 hrs/day) = 83% fewer hours. Combined savings: 1-(0.3 × 4/24) = 95% reduction in EMR compute cost. 20 core nodes × r5.2xlarge On-Demand ~$0.504/hr × 24 = $241/day → Spot transient = ~$241 × 0.05 = $12/day.
* **S3 Glacier Instant Retrieval:** At 2PB, S3 Standard = $0.023/GB = $47,186/month; Glacier Instant Retrieval = $0.004/GB = $8,192/month — saving ~$39,000/month for data > 90 days old.
* **Redshift Spectrum:** Query S3 data directly from Redshift without ETL loading — eliminates data movement costs and Redshift storage for cold data.

* **Why alternatives fail:**
  - **A)** Correct on Redshift pause/resume and EMR Serverless. However, EMR Serverless for a 4-hour daily batch job is effective but doesn't capture Spot pricing discounts available with transient EC2-based EMR. EMR Serverless charges per vCPU-hour and memory-hour — cost comparison is workload-dependent, but for predictable 4-hour batch, transient Spot EMR is often cheaper.
  - **B)** Migrating Redshift entirely to Athena requires complete SQL compatibility testing and may not support all Redshift-specific SQL extensions. Lambda for EMR-scale data processing (20 nodes × r5.2xlarge = significant compute) hits Lambda memory/timeout limits — technically infeasible for large-scale batch.
  - **D)** Downsizing Redshift without pausing leaves the cluster running idle 72% of the time — cost reduction is marginal (smaller instance) vs pause/resume (zero cost while paused). EMR Managed Scaling adjusts cluster size dynamically but doesn't eliminate idle costs when the cluster runs 24/7 with only 4 hours of work.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 21: Domain 1 – Design Solutions for Organizational Complexity

A multinational enterprise runs 15 production AWS accounts under AWS Organizations. A new compliance mandate requires: 
1. All S3 buckets across ALL accounts must block public access at the account level. 
2. All EC2 instances must have detailed monitoring enabled at launch. 
3. Any IAM role created with AdministratorAccess must trigger an immediate SNS alert to the security team. 
4. The Security team must enforce these controls without requiring access to individual member accounts and must be able to demonstrate compliance to auditors.

<div class="question-prompt">
**Question:** Which architecture satisfies all four requirements with the least operational overhead?
</div>

- [ ] Deploy a Lambda function in each member account that checks S3 block public access settings hourly; use CloudTrail + CloudWatch Events for IAM role monitoring; send SNS notifications from each account.
- [ ] Use AWS Config Conformance Packs deployed via CloudFormation StackSets from the management account: include `s3-account-level-public-access-blocks` rule, `ec2-instance-detailed-monitoring-enabled` rule, and a custom Config rule (Lambda-backed) detecting IAM roles with AdministratorAccess; configure Config Aggregator in the Security account to aggregate all findings; use AWS Security Hub with a delegated admin in the Security account for consolidated view; SNS alert via EventBridge rule on SecurityHub Findings - Imported for IAM AdministratorAccess findings.
- [ ] Attach SCPs to the Organization root denying `s3:PutBucketPublicAccessBlock` with false values; deny `ec2:RunInstances` without monitoring parameter; deny `iam:CreateRole` if policy includes AdministratorAccess; monitor via AWS Organizations API.
- [ ] Enable AWS Security Hub in all accounts; use AWS Macie for S3 public access detection; use CloudTrail Insights for IAM anomaly detection; aggregate via a SIEM in the Security account.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — Config Conformance Packs via StackSets + Config Aggregator + Security Hub delegated admin + EventBridge SNS.

**Why it succeeds:**
* **Req 1 (S3 block public access):** AWS Config managed rule `s3-account-level-public-access-blocks` evaluates the account-level S3 Block Public Access setting — no per-bucket assessment needed.
* **Req 2 (EC2 detailed monitoring):** `ec2-instance-detailed-monitoring-enabled` is a managed Config rule that evaluates every EC2 instance at launch.
* **Req 3 (IAM AdministratorAccess alert):** A custom Config rule (Lambda-backed) evaluates IAM roles on change, detecting `arn:aws:iam::aws:policy/AdministratorAccess` attachment. EventBridge routes the NON_COMPLIANT finding to SNS.
* **Req 4 (No member account access):** CloudFormation StackSets with `SERVICE_MANAGED` deployment mode uses Organizations integration to auto-deploy to all accounts, including new ones, without Security team logging into member accounts. Config Aggregator in the Security account pulls findings from all accounts centrally. Config delegated admin is set to the Security account.

**Why alternatives fail:**
- [ ] Per-account Lambda functions require deployment and maintenance in 15 accounts — violates "no access to individual accounts" and high operational overhead. Hourly checks miss real-time violation detection.
- [ ] SCPs operate on deny logic at the API level — they prevent future violations but do not detect or report existing non-compliant resources. SCPs also cannot detect the monitoring parameter in `ec2:RunInstances` reliably (instance monitoring is configured separately via the monitoring-enabled parameter, not easily SCP-controlled). SCPs cannot evaluate IAM policy content (only API actions).
- [ ] AWS Macie detects sensitive data in S3 objects — it is not a configuration compliance tool. It does not evaluate S3 Block Public Access settings. Security Hub aggregates but cannot enforce controls without Config rules feeding it.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 22: Domain 2 – Design for New Solutions

A startup is building a multi-region active-active SaaS application for US and EU customers. Requirements: 
1. Data sovereignty — EU customer data must never be stored or processed in US regions, and vice versa. 
2. Global URL — customers use app.saas.com regardless of region; routing must be latency-based. 
3. Session stickiness — a user authenticated in EU must not be re-routed to US mid-session. 
4. The database tier must be active-active with sub-second replication. 
5. Authentication tokens must be valid in both regions (users may travel).

<div class="question-prompt">
**Question:** Which architecture satisfies all five constraints?
</div>

- [ ] Route 53 latency-based routing to ALBs in us-east-1 and eu-west-1; Aurora Global Database with us-east-1 primary; DynamoDB Global Tables for session data; JWT tokens signed with a shared secret stored in AWS Secrets Manager (replicated); CloudFront with geo-restriction to enforce data sovereignty.
- [ ] Route 53 latency-based routing to regional ALBs (us-east-1, eu-west-1); session stickiness via Route 53 geolocation + Route 53 Application Recovery Controller to pin users to a region after first authentication; DynamoDB Global Tables (but with data sovereignty enforced via application-level partition — US customer records written only to us-east-1 table, EU only to eu-west-1) for the application data tier; Amazon Cognito with a User Pool per region but shared client IDs — JWT tokens contain region claim, application validates and rejects cross-region tokens; CloudFront with Lambda@Edge geo-restriction at the edge to block US users from EU origins.
- [ ] AWS Global Accelerator with endpoint groups in us-east-1 and eu-west-1; client affinity enabled (routes the same client to the same endpoint for session stickiness); Aurora Global Database with regional writers in both regions (active-active via Global Write Forwarding); Amazon Cognito with User Pool per region; JWT tokens with asymmetric RS256 signing — public key distributed to both regions via SSM Parameter Store replication; data sovereignty enforced via Cognito custom attributes tagging user region + application-layer write routing.
- [ ] CloudFront with two origins (us-east-1, eu-west-1) and geolocation-based cache behaviors; ALB in each region; DynamoDB Global Tables; Lambda@Edge for authentication token validation; Route 53 for failover.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **C** — Global Accelerator (client affinity) + Aurora Global Database (active-active) + Cognito per region + RS256 JWT.

**Why it succeeds:**
* **Req 1 (Data sovereignty):** Application-layer write routing ensures EU users' data is written to eu-west-1 Aurora regional writer; US to us-east-1. Aurora Global Database's Write Forwarding feature allows secondary regions to accept writes and forward them to the primary — but for true active-active with sovereignty, regional writers are the correct pattern. Data sovereignty is enforced at the application write path, not at the CDN.
* **Req 2 (Global URL + latency routing):** Global Accelerator uses AWS's global network backbone (not the public internet) for routing — lower latency than Route 53 DNS-based latency routing, which is DNS-TTL-bound.
* **Req 3 (Session stickiness):** Global Accelerator's client affinity setting routes the same client IP to the same endpoint group for the duration of the session — purpose-built for this requirement.
* **Req 4 (Active-active sub-second replication):** Aurora Global Database with regional writers + Write Forwarding achieves this. DynamoDB Global Tables also qualifies (sub-second replication, active-active).
* **Req 5 (Cross-region token validity):** RS256 asymmetric JWT — private key signs tokens per region, public key is distributed to both regions. Both regions can validate tokens signed by either regional Cognito without sharing private keys.

**Why alternatives fail:**
- [ ] Aurora Global Database with a single us-east-1 primary is not active-active — EU writes forward to US, creating EU→US data flow that violates data sovereignty requirement 1. CloudFront geo-restriction blocks user access, not data flow — it doesn't enforce where data is stored.
- [ ] DynamoDB Global Tables replicates data to ALL configured regions automatically — you cannot prevent EU data from appearing in the us-east-1 table replica. This directly violates data sovereignty. Application-level partitioning doesn't stop Global Tables replication engine.
- [ ] CloudFront is a CDN optimized for cacheable content — it does not provide session stickiness for dynamic API traffic. Lambda@Edge for auth adds latency at every request and cannot enforce database-level data sovereignty.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 23: Domain 1 – Design Solutions for Organizational Complexity

An enterprise has Direct Connect (10 Gbps dedicated connection) to AWS. They have 3 VPCs: Prod-VPC (192.168.1.0/24), Dev-VPC (192.168.2.0/24), and Shared-Services-VPC (192.168.3.0/24). On-premises CIDR is 10.0.0.0/8. Requirements: 
1. On-premises must reach all 3 VPCs. 
2. Prod-VPC and Dev-VPC must NOT communicate with each other. 
3. Both must be able to reach Shared-Services-VPC. 
4. The solution must support adding 50 more VPCs over the next year with minimal reconfiguration.

<div class="question-prompt">
**Question:** Which Transit Gateway design satisfies all requirements?
</div>

- [ ] Create a TGW; attach all 3 VPCs and the Direct Connect Gateway; use a single shared route table with all routes propagated; use NACLs in Prod-VPC and Dev-VPC to block inter-VPC traffic.
- [ ] Use VPC Peering: Prod→Shared, Dev→Shared, on-premises via Virtual Private Gateways in each VPC; no TGW needed.
- [ ] Create a TGW with 3 route tables: (1) Prod-RT: associated with Prod-VPC attachment, propagates routes from Shared-Services and DXGW only; (2) Dev-RT: associated with Dev-VPC attachment, propagates routes from Shared-Services and DXGW only; (3) Shared-RT: associated with Shared-Services-VPC and DXGW attachments, propagates routes from ALL attachments; on-premises static routes to all 3 VPC CIDRs via DXGW → TGW.
- [ ] Create a TGW with 2 route tables: Spoke-RT (Prod + Dev) with default route to Shared-Services; Shared-RT (Shared-Services + DXGW) with routes to Prod and Dev; use TGW blackhole routes to block Prod↔Dev.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **C** — Three TGW route tables with precise propagation control.

**Why it succeeds:** TGW route table isolation is the AWS-recommended pattern for segmented hub-and-spoke networks:
* **Prod-RT** has routes only for Shared-Services CIDR and on-premises (DXGW) — Prod has no route to Dev, so Prod→Dev traffic is dropped at TGW.
* **Dev-RT** mirrors Prod-RT — Dev has no route to Prod.
* **Shared-RT** has routes to ALL CIDRs (Prod, Dev, on-premises) — Shared-Services can reach everything, and return traffic from Shared-Services to Prod/Dev routes correctly.
* **DXGW** association with TGW allows on-premises to reach all VPCs via the Shared-RT propagation.
* **Scaling:** Adding a new VPC in year 2 requires only attaching it to TGW and associating with the appropriate route table (Prod-RT or Dev-RT pattern) — no reconfiguration of existing VPCs or route tables.

**Why alternatives fail:**
- [ ] Single shared route table with all routes propagated means Prod and Dev have routes to each other — requirement 2 violated. NACLs at the VPC level can filter traffic but are stateless and hard to manage at scale; they're not the correct isolation mechanism for TGW routing.
- [ ] VPC Peering doesn't scale to 50+ VPCs — you'd need a full mesh of peering connections (n×(n-1)/2 = 1,275 peering connections for 51 VPCs). Also, VPC Peering is non-transitive: on-premises reaching all VPCs via Direct Connect requires a VGW in each VPC — massive operational overhead.
- [ ] Two route tables with a blackhole route for Prod↔Dev is partially correct but less clean than three route tables. Blackhole routes must be explicitly added for every new spoke VPC pair — higher maintenance. Three dedicated route tables (Prod-RT, Dev-RT, Shared-RT) are more explicit and scalable.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 24: Domain 2 – Design for New Solutions

A company is building a compliance-as-code platform for regulated industries. The platform must: 
1. Automatically evaluate new AWS accounts provisioned via AWS Organizations against a baseline of 150 compliance controls. 
2. Generate audit-ready reports in PDF format within 30 minutes of account creation. 
3. Provide a self-service remediation portal where account owners can trigger automated fixes. 
4. Integrate with an existing ServiceNow ITSM for change management ticketing. 
5. Support custom control definitions that non-engineers can configure without writing Lambda code.

<div class="question-prompt">
**Question:** Which architecture best satisfies all five requirements?
</div>

- [ ] AWS Config with 150 managed/custom rules deployed via StackSets; AWS Security Hub for aggregation; Lambda for PDF report generation; API Gateway + Lambda for remediation portal; SNS→SQS→Lambda for ServiceNow integration; custom controls via Config rule parameters.
- [ ] AWS Control Tower with Customizations for Control Tower (CfCT); AWS Security Hub; custom Lambda controls; ServiceNow EventBridge integration; PDF via Lambda+WeasyPrint.
- [ ] AWS Config Conformance Packs (bundling all 150 rules) deployed via CloudFormation StackSets with `SERVICE_MANAGED` deployment (auto-deploys to new accounts via Organizations); AWS Security Hub (delegated admin) aggregates findings with SUPPRESSED/FAILED status; Step Functions workflow triggered by EventBridge (account creation event from Organizations) → generates compliance report via Lambda (PDF using ReportLab/WeasyPrint) → stores in S3 → presigned URL sent via SNS; API Gateway + Lambda remediation functions (SSM Automation runbooks as the actual fix mechanisms) behind a React portal in S3+CloudFront; EventBridge → API Gateway → ServiceNow REST API for ticket creation on new findings; custom controls via AWS Config custom rules with AWS CloudFormation Guard (cfn-guard policy-as-code, YAML-based, no Lambda required).
- [ ] Prisma Cloud for compliance evaluation; ServiceNow Cloud Management for AWS governance; custom portal in EC2; PDF reports via scheduled Lambda; Config for resource inventory.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **C** — Config Conformance Packs + StackSets (`SERVICE_MANAGED`) + Step Functions + SSM Automation + cfn-guard + EventBridge → ServiceNow.

**Why it succeeds:**
* **Req 1 (Auto-evaluate new accounts):** CloudFormation StackSets with `SERVICE_MANAGED` + Organizations integration automatically deploys Conformance Packs to new accounts on creation — zero manual intervention.
* **Req 2 (PDF in 30 min):** EventBridge detects `CreateAccountResult` event from Organizations → triggers Step Functions → Lambda evaluates Config findings via Security Hub API → generates PDF (ReportLab) → uploads to S3 → SNS notification with presigned URL. Well within 30 minutes.
* **Req 3 (Self-service remediation portal):** API Gateway exposes remediation endpoints backed by Lambda → invokes SSM Automation runbooks (pre-built, auditable remediation playbooks). React SPA on S3+CloudFront provides the UI.
* **Req 4 (ServiceNow integration):** EventBridge rule on Security Hub Findings - Imported events → API destination → ServiceNow REST API creates change ticket. EventBridge API destinations natively support REST webhooks.
* **Req 5 (Custom controls, no Lambda):** AWS CloudFormation Guard (cfn-guard) rules are YAML-based policy-as-code that non-engineers can write following a template pattern. Config custom rules backed by cfn-guard use the `CLOUDFORMATION_GUARD` evaluation mode — no Lambda function authoring required.

**Why alternatives fail:**
- [ ] Config custom rule parameters allow configuring existing rules but cannot define new control logic without Lambda code. Fails requirement 5.
- [ ] Control Tower CfCT is powerful but requires Control Tower enrollment of all accounts (significant prerequisites). CfCT doesn't natively generate PDF compliance reports. Custom Lambda controls for 150 rules is high engineering effort.
- [ ] Prisma Cloud and ServiceNow Cloud Management are third-party tools that add cost and integration complexity. The question asks for an AWS-native architecture.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 25: Domain 3 – Migration Planning

A company is running a VMware vSphere environment on-premises with 300 VMs. They want to migrate to AWS while: 
1. Minimizing refactoring — the operations team is unfamiliar with AWS-native services. 
2. Maintaining the same VMware operational model (vCenter, vMotion, DRS) during a 12-month transition. 
3. Running workloads that require bare-metal performance (vSAN-backed storage, network-intensive). 
4. Enabling seamless VM migration from on-premises to AWS without OS conversion. 
5. Post-migration, gradually modernizing select workloads to containers over 18 months.

<div class="question-prompt">
**Question:** Which migration approach is the most appropriate?
</div>

- [ ] Use AWS Application Migration Service (MGN) to lift-and-shift all 300 VMs to EC2; use EC2 bare-metal instances for performance; post-migration modernize using AWS App2Container.
- [ ] Deploy VMware Cloud on AWS (VMC on AWS) — extends the on-premises vSphere environment to AWS-hosted dedicated bare-metal hosts managed via vCenter; use vMotion to migrate VMs from on-premises to VMC on AWS without downtime and without OS conversion; maintain VMware DRS/vSAN on AWS hosts; use VMC on AWS integration with AWS native services (RDS, S3, DynamoDB) for modernization; use AWS Tanzu (or VMware Tanzu on VMC) for container modernization track over 18 months.
- [ ] Use AWS Outposts with VMware support; deploy vSphere on Outposts; migrate VMs to Outposts; extend to AWS regions gradually.
- [ ] Use AWS Migration Hub to orchestrate MGN migrations; convert VM disks using AWS VM Import/Export; deploy on EC2 Dedicated Hosts; use EKS for containerization post-migration.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — VMware Cloud on AWS (VMC on AWS).

**Why it succeeds:** VMC on AWS is the only AWS offering that provides a fully managed VMware SDDC (Software-Defined Data Center) running on dedicated AWS bare-metal hosts:
* **Req 1 (No refactoring, familiar ops model):** Operations team continues using vCenter, the same UI and tooling as on-premises. Zero AWS-native service learning required initially.
* **Req 2 (Same VMware operational model):** VMC on AWS runs vSphere, vSAN, NSX-T, and vCenter natively — DRS, HA, vMotion all work identically.
* **Req 3 (Bare-metal performance):** VMC on AWS uses i3.metal AWS bare-metal hosts, providing vSAN-backed storage and bare-metal network performance — no hypervisor overhead for the VMware layer.
* **Req 4 (Seamless vMotion migration):** vMotion works between on-premises vSphere and VMC on AWS over the Direct Connect connection — live VM migration with zero downtime and no OS conversion.
* **Req 5 (Container modernization):** VMware Tanzu integrates with VMC on AWS for Kubernetes containerization of select workloads post-migration.

**Why alternatives fail:**
- [ ] MGN converts VMs to EC2 AMIs — this is a format conversion that takes each VM offline for cutover (not zero-downtime vMotion). The operations team loses vCenter and must learn AWS EC2 management immediately. Fails requirements 1, 2, and 4.
- [ ] AWS Outposts runs AWS-native services (EC2, EKS, RDS) on-premises — it does not run VMware. There is no "VMware support" on standard Outposts. (Note: VMware Cloud on AWS Outposts is a separate, niche offering for keeping VMware on-premises, opposite of the requirement to migrate to AWS.)
- [ ] VM Import/Export requires downtime for disk conversion; EC2 Dedicated Hosts don't provide the VMware operational model; EKS for containerization requires significant refactoring. Fails requirements 1, 2, and 4.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 26: Domain 4 – Cost Control

A company's Lambda-heavy architecture processes 2 billion invocations/month. Cost breakdown: 
1. Lambda compute: $85,000/month (avg duration 800ms, 1GB memory). 
2. Lambda invocations: $4,000/month. 
3. API Gateway REST API: $70,000/month (7B API calls/month). 
4. CloudWatch Logs from Lambda: $30,000/month. 
5. X-Ray tracing: $12,000/month.

<div class="question-prompt">
**Question:** Which optimizations reduce costs most significantly while maintaining observability?
</div>

- [ ] Reduce Lambda memory to 128MB; disable CloudWatch Logs; disable X-Ray; switch API Gateway to HTTP API; implement request/response compression.
- [ ] Optimize Lambda function code to reduce duration; use Lambda Power Tuning (open-source tool via Step Functions) to find the optimal memory/price point; migrate API Gateway REST API to HTTP API (up to 71% cheaper); implement CloudWatch Logs subscription filters routing non-ERROR logs to S3 via Firehose (reduce CW Logs ingestion by ~90%); replace X-Ray with CloudWatch Lambda Insights for performance monitoring (included in Lambda pricing tiers); implement Lambda function URLs for direct invocations that don't need API Gateway features.
- [ ] Move all Lambda workloads to ECS Fargate for predictable pricing; disable all logging; use CloudWatch Container Insights instead.
- [ ] Purchase Lambda Savings Plans; implement SQS batching to reduce Lambda invocation count; reduce API Gateway throttling limits; use CloudWatch Logs Insights for querying instead of streaming.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — Power Tuning + HTTP API + Log filtering + Insights.

**Why it succeeds:**
* **Lambda compute ($85K):** AWS Lambda Power Tuning (open-source Step Functions state machine) runs the function at different memory configurations and measures cost × duration. At 1GB/800ms, increasing memory to 1.5GB or 2GB may reduce duration to 400ms — same or lower cost due to faster execution. Power Tuning finds the optimal point empirically.
* **API Gateway ($70K → ~$20K):** HTTP API costs $1.00/million calls vs REST API at $3.50/million = 71% reduction. At 7B calls/month: REST = $24,500 (plus data processing); HTTP API = ~$7,000. HTTP API supports Lambda, HTTP backends, JWT authorizers — covers most REST API use cases.
* **CloudWatch Logs ($30K → ~$3K):** Lambda logs at $0.50/GB. Filtering only ERROR-level logs to CloudWatch and routing INFO/DEBUG to S3 via Kinesis Firehose ($0.029/GB) reduces CW Logs ingestion by 80–90%.
* **X-Ray ($12K → ~$0):** CloudWatch Lambda Insights provides enhanced monitoring (memory, CPU, cold starts) at no additional cost beyond CloudWatch metrics pricing. X-Ray sampling can also be reduced from 5% to 1% to cut costs 80%.

**Why alternatives fail:**
- [ ] Reducing Lambda memory to 128MB without profiling may increase cost — if duration increases proportionally more than memory decreases, total GB-seconds increase. Disabling all logging eliminates operational visibility entirely.
- [ ] Migrating 2B invocations/month to ECS Fargate eliminates Lambda's event-driven scaling and introduces always-on container costs. For event-driven workloads, Lambda is almost always more cost-effective than Fargate.
- [ ] Lambda Savings Plans provide up to 17% discount — significant but less impactful than the 71% API Gateway savings and 90% log savings available. SQS batching reduces invocation count but also changes the processing semantics.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 27: Domain 5 – Continuous Improvement for Existing Solutions

A company's microservices architecture on ECS Fargate uses Application Load Balancer (ALB) for routing. Problems: 
1. Service-to-service calls fail with 502 errors intermittently (~2% of requests) — no pattern identified. 
2. A new requirement mandates mTLS for all service-to-service communication. 
3. Services need circuit breaker functionality to prevent cascading failures. 
4. The team wants distributed tracing across all 20 services without code changes. 
5. A/B testing is needed for 3 services with percentage-based traffic splitting.

<div class="question-prompt">
**Question:** Which AWS-native solution addresses all five issues?
</div>

- [ ] Deploy AWS App Mesh as a service mesh (Envoy sidecar proxy injected into each ECS task): (1) Envoy proxy handles connection-level retries — fixing 502 errors from transient connection drops; (2) App Mesh supports mTLS via ACM Private CA certificates distributed to Envoy sidecars automatically; (3) Circuit breaker configured via App Mesh virtual node outlier detection (consecutive 5xx threshold); (4) App Mesh integrates with AWS X-Ray — Envoy exports traces to X-Ray daemon automatically, no application code changes; (5) App Mesh virtual router with weighted targets enables percentage-based traffic splitting (e.g., 90% v1, 10% v2).
- [ ] Replace ALB with NLB for lower latency; implement mTLS in each service's code; use AWS Step Functions for circuit breaker logic; deploy X-Ray SDK in each service; use ALB weighted target groups for A/B testing.
- [ ] Migrate to EKS and deploy Istio service mesh; use Istio's PeerAuthentication for mTLS; use Istio's DestinationRule for circuit breaking; Istio+Jaeger for tracing; Istio VirtualService for traffic splitting.
- [ ] Use AWS Fault Injection Simulator to identify 502 root causes; implement API Gateway with mTLS; use Lambda for circuit breaker logic; use Route 53 weighted routing for A/B testing.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **A** — AWS App Mesh with Envoy sidecars on ECS Fargate.

**Why it succeeds:** App Mesh is AWS's managed service mesh designed specifically for ECS/EKS/EC2 workloads:
* **Issue 1 (502 errors):** Envoy proxy handles TCP connection management and retry policies at the proxy layer — transient connection failures between services are retried transparently without application awareness.
* **Issue 2 (mTLS):** App Mesh integrates with ACM Private CA to provision and rotate certificates for Envoy sidecars. mTLS is enforced at the Envoy layer — zero application code changes.
* **Issue 3 (Circuit breaker):** App Mesh virtual node outlier detection (based on Envoy's outlier detection algorithm) ejects unhealthy upstream hosts from the load balancing pool after configurable consecutive failure thresholds.
* **Issue 4 (Distributed tracing):** Envoy sidecar in App Mesh automatically emits traces to X-Ray (configured via App Mesh's tracing configuration) — no SDK instrumentation required in application code.
* **Issue 5 (A/B traffic splitting):** App Mesh virtual router weighted routes split traffic by percentage between virtual nodes — native percentage-based routing.

**Why alternatives fail:**
- [ ] Implementing mTLS, circuit breakers, and tracing in each service's code requires changes to all 20 services — high engineering effort and defeats the "without code changes" requirement for tracing.
- [ ] Migrating ECS Fargate to EKS is a complete platform migration — operationally complex and not a "continuous improvement" of the existing ECS architecture. Istio on EKS is the Kubernetes-native equivalent of App Mesh on ECS.
- [ ] AWS FIS is a chaos engineering tool for fault injection — not a diagnostic tool for identifying 502 root causes. API Gateway for service-to-service mTLS is not the right pattern (API Gateway is for external client-to-service, not east-west service mesh traffic). Route 53 weighted routing operates at DNS level — too coarse for request-level traffic splitting.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 28: Domain 2 – Design for New Solutions

A financial services company needs to build a disaster recovery solution for its primary application in us-east-1. Requirements: 
1. RTO = 15 minutes, RPO = 1 minute. 
2. The DR region is us-west-2. 
3. The application has: Aurora MySQL (multi-TB), EC2 Auto Scaling fleet (stateless), ElastiCache Redis (session data), S3 (document storage), DynamoDB (transaction records). 
4. Cost must be minimized during steady-state (DR region should cost <10% of prod). 
5. Failover must be fully automated — no human intervention for the 15-minute RTO.

<div class="question-prompt">
**Question:** Which DR architecture meets all constraints?
</div>

- [ ] Pilot Light in us-west-2: Aurora Global Database (secondary cluster in us-west-2 — read-only replica, sub-second lag = RPO < 1 min); minimal EC2 Auto Scaling group (0 desired, 0 min, scales up on failover trigger); ElastiCache Redis backup restored from snapshot (RTO risk); S3 Cross-Region Replication (CRR); DynamoDB Global Tables; Route 53 health checks on the primary ALB endpoint trigger AWS Systems Manager Automation runbook on health check failure: (1) Promotes Aurora Global DB secondary, (2) Scales ASG to production capacity, (3) Updates Route 53 record to us-west-2 ALB — all within 15 minutes.
- [ ] Active-active in both regions; full production capacity in us-west-2 at all times; Route 53 latency routing; DynamoDB Global Tables; Aurora Global Database active-active; ElastiCache Global Datastore.
- [ ] Cold standby: nightly Aurora snapshots copied to us-west-2; EC2 AMI backups; Redis snapshot to S3; restore from snapshots on failure; 4-hour RTO acceptable.
- [ ] Warm standby: reduced-capacity EC2 ASG running in us-west-2; Aurora Global Database secondary; ElastiCache Redis Global Datastore; S3 CRR; DynamoDB Global Tables; manual runbook for failover steps executed by on-call engineer.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **A** — Pilot Light with automated SSM Automation runbook failover.

**Why it succeeds:**
* **RPO = 1 minute:** Aurora Global Database replicates with typical lag < 1 second — far exceeds the 1-minute RPO requirement. DynamoDB Global Tables replicates in < 1 second. S3 CRR replicates objects within minutes (S3 Replication Time Control guarantees 99.99% of objects in 15 minutes).
* **RTO = 15 minutes (automated):** The SSM Automation runbook sequence: Route 53 health check detects primary failure (60-second failure threshold) → triggers CloudWatch Alarm → EventBridge invokes SSM Automation → Step 1: promote Aurora Global Database secondary (< 1 min) → Step 2: ASG desired capacity update (EC2 provisioning ~5 min with pre-warmed AMIs) → Step 3: Route 53 record update (< 60 seconds TTL propagation). Total: ~8–12 minutes — within 15 minutes.
* **Cost < 10% of prod:** Pilot Light runs zero EC2 instances (0 desired ASG), minimal RDS read replica cost, minimal ElastiCache (no Redis in pilot light — Redis session data is rebuilt on user re-authentication post-failover, an acceptable tradeoff). S3 CRR storage cost mirrors primary S3.

**Why alternatives fail:**
- [ ] Active-active costs 100% of prod in both regions permanently — violates the <10% cost constraint during steady-state.
- [ ] Snapshot restore takes 4+ hours for multi-TB Aurora — completely incompatible with 15-minute RTO. Explicitly acknowledged in the option.
- [ ] Warm standby with manual runbook violates requirement 5 (fully automated). Manual execution of failover steps introduces human error and variability — cannot guarantee 15-minute RTO.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 29: Domain 5 – Continuous Improvement for Existing Solutions

A company's data pipeline runs on AWS Glue (PySpark ETL jobs) processing 10TB/day from S3 to Redshift. Issues: 
1. Glue jobs are taking 4+ hours (SLA: 2 hours). 
2. $45,000/month in Glue DPU costs. 
3. Jobs fail 15% of the time with out-of-memory errors. 
4. Data quality issues — 8% of records have null values in critical fields — discovered only after loading to Redshift. 
5. The team has no visibility into which transformation step is the bottleneck.

<div class="question-prompt">
**Question:** Which improvements address all five issues?
</div>

- [ ] Increase Glue DPU count to 200; enable Glue job bookmarks; add null checks in Redshift stored procedures post-load; use CloudWatch for job monitoring.
- [ ] Migrate to EMR with Spark on Spot Instances for cost reduction; use Apache Griffin for data quality; implement Ganglia for Spark UI; increase executor memory.
- [ ] Enable Glue job profiling (Spark UI via CloudWatch) to identify bottleneck transformations (Issue 5); optimize PySpark code using Glue's pushdown predicates and partition pruning to reduce data scanned (Issue 1); right-size DPUs using job profiling insights — reduce DPUs and use Glue Flex execution (spot-backed, 34% cheaper) for non-time-critical jobs (Issue 2); increase executor memory in Glue job parameters (`--conf spark.executor.memory`) and enable Glue auto-scaling (Issue 3); implement AWS Glue Data Quality (DQDL rules) as a pre-load check — fail the job and alert via SNS before writing to Redshift if null rate exceeds threshold (Issue 4).
- [ ] Split the Glue job into smaller parallel jobs using Glue workflows; add more S3 partitions; use Glue DataBrew for data quality; increase Redshift cluster size; use Glue triggers for retry logic.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **C** — Profiling + PySpark optimization + Flex DPUs + memory tuning + Glue Data Quality.

**Why it succeeds:**
* **Issue 1 (4+ hours):** Glue Spark UI via CloudWatch reveals which stage (shuffle, scan, join) is the bottleneck. Pushdown predicates and S3 partition pruning reduce data scanned at the source — the most impactful performance optimization in Spark ETL (avoiding full S3 scans).
* **Issue 2 ($45K/month):** Glue Flex execution uses spare AWS capacity at a 34% discount — ideal for non-SLA-critical transformations within the pipeline. Right-sizing DPUs after profiling eliminates over-provisioned DPUs.
* **Issue 3 (OOM errors):** Increasing `spark.executor.memory` in Glue job parameters directly addresses heap OOM errors. Glue auto-scaling dynamically adjusts DPUs during job execution, preventing resource starvation during peak transformation stages.
* **Issue 4 (Data quality, 8% nulls):** AWS Glue Data Quality uses DQDL (Data Quality Definition Language) rules (e.g., `IsComplete "critical_field" > 0.95`) evaluated inline during the ETL job. If rules fail, the job halts before writing to Redshift — preventing bad data from reaching the data warehouse.
* **Issue 5 (No visibility):** Glue Spark UI (accessible via CloudWatch) provides the standard Apache Spark DAG visualization, stage timings, and executor metrics — the definitive tool for identifying ETL bottlenecks.

**Why alternatives fail:**
- [ ] Increasing DPU count to 200 treats the symptom (slow jobs) without diagnosing the root cause — may not help if the bottleneck is a skewed shuffle partition or a non-parallelizable step, and will significantly increase cost.
- [ ] Migrating to EMR is operationally complex and not a "continuous improvement" of the existing Glue setup. Apache Griffin requires additional infrastructure. This approach doesn't address Glue-specific issues.
- [ ] Glue DataBrew is a visual data preparation tool for analysts — not appropriate for production pipeline data quality checks. It doesn't integrate as a pre-load quality gate in the way Glue Data Quality does.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 30: Domain 3 – Migration Planning

A company is migrating their Microsoft Active Directory environment to AWS. Current state: 2 on-premises AD domain controllers for corp.example.com. Requirements: 
1. AWS workloads (EC2 Windows, RDS for SQL Server with Windows Auth) must join the corp.example.com domain. 
2. On-premises users must authenticate to AWS applications via AD credentials. 
3. AD must remain authoritative on-premises — AWS is an extension, not a replacement. 
4. The solution must function if Direct Connect fails (internet failover). 
5. The solution must support MFA for AWS Management Console access.

<div class="question-prompt">
**Question:** Which AD architecture satisfies all constraints?
</div>

- [ ] Deploy AWS Managed Microsoft AD in us-east-1; establish a forest trust (one-way or two-way) with on-premises corp.example.com; configure EC2 and RDS instances to join the AWS Managed AD domain; use AD Connector in a separate VPC for console authentication; enable AWS Managed AD MFA via RADIUS.
- [ ] Deploy AWS Managed Microsoft AD in a shared-services VPC; configure AD Trust with on-premises corp.example.com (two-way trust — allows on-premises users to authenticate to AWS resources in the corp.example.com domain); deploy AD Connector as a redundant authentication proxy (AD Connector points to AWS Managed AD as backup when DX fails — since Managed AD is in AWS, internet failover maintains AD Connector functionality); enable MFA on IAM Identity Center with TOTP/RADIUS; use IAM Identity Center with AWS Managed AD as identity source.
- [ ] Deploy AD Connector only (no Managed AD) pointing to on-premises DCs; EC2 instances join on-premises domain via Direct Connect; RDS SQL Server uses Windows Auth via on-premises AD; if DX fails, AD Connector loses connectivity — deploy a second AD Connector pointing to internet-accessible on-premises DCs via VPN over internet; enable IAM Identity Center with AD Connector as identity source; MFA via IAM Identity Center TOTP.
- [ ] Lift-and-shift on-premises DCs to EC2; make AWS EC2 DCs authoritative; configure on-premises as read-only DCs replicating from AWS; Direct Connect for replication traffic.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — AWS Managed Microsoft AD (with forest trust) + IAM Identity Center + MFA.

**Why it succeeds:**
* **Req 1 (EC2/RDS domain join):** EC2 Windows instances and RDS SQL Server with Windows Auth can join AWS Managed Microsoft AD directly — AWS Managed AD is a real Microsoft AD (not a proxy). RDS SQL Server Windows Authentication requires AWS Managed AD (not AD Connector).
* **Req 2 (On-premises users authenticate to AWS):** The two-way forest trust between AWS Managed AD and on-premises corp.example.com allows on-premises users (who authenticate to on-premises AD) to access AWS resources via Kerberos trust traversal.
* **Req 3 (On-premises remains authoritative):** The trust is configured with on-premises as the root domain — on-premises AD remains the source of truth. AWS Managed AD is an extension (trusting domain).
* **Req 4 (DX failover):** Since AWS Managed AD resides in AWS (not on-premises), AD Connector pointed at Managed AD functions over the internet if DX fails — no dependency on on-premises DCs for AWS resource authentication.
* **Req 5 (MFA):** IAM Identity Center with AWS Managed AD as identity source + built-in TOTP MFA (or RADIUS MFA via Managed AD's RADIUS support) provides MFA for Console access.

**Why alternatives fail:**
- [ ] AD Connector as a separate proxy alongside Managed AD is redundant and creates confusion about which directory services EC2/RDS resources join. RDS SQL Server Windows Auth specifically requires Managed AD — AD Connector cannot support this.
- [ ] AD Connector alone cannot support RDS SQL Server Windows Authentication (RDS requires Managed AD). If Direct Connect fails and AD Connector loses connectivity to on-premises DCs, all AWS authentication fails — the internet VPN fallback for AD Connector requires the on-premises DC to be internet-accessible, a security risk.
- [ ] Making AWS EC2 DCs authoritative and on-premises read-only inverts the stated requirement (on-premises must remain authoritative). This is a major architectural change, not a hybrid extension.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 31: Domain 2 – Design for New Solutions

A company wants to implement a zero-trust network architecture for their AWS environment. Currently all inter-service communication uses security groups and VPC peering. Requirements: 
1. All service-to-service API calls must carry cryptographic identity (not just network-layer trust). 
2. Services must be able to verify the identity of the caller before processing requests. 
3. The solution must work across multiple AWS accounts. 
4. No VPN or Direct Connect required for cross-account service communication. 
5. Solution must support both Lambda and ECS Fargate workloads.

<div class="question-prompt">
**Question:** Which architecture implements zero-trust most completely?
</div>

- [ ] Use VPC Peering between accounts; enforce strict security groups; use NACLs for defense-in-depth; require IAM authentication headers in all API calls.
- [ ] Deploy AWS PrivateLink (VPC Endpoint Services) for cross-account service exposure; services use IAM SigV4 request signing with IAM roles (Lambda execution roles, ECS task roles) to sign API requests; the receiving service validates the Authorization header signature using AWS SDK; deploy API Gateway with IAM authorization (AWS_IAM auth type) as the service endpoint — API Gateway validates SigV4 signatures against caller's IAM role ARN; cross-account access via resource-based policies on API Gateway; no VPN needed (PrivateLink over AWS backbone).
- [ ] Use AWS Certificate Manager Private CA to issue mutual TLS certificates to each service; configure ALBs with mTLS listener; services present certificates for authentication; cross-account via TGW.
- [ ] Deploy AWS Verified Access for all service-to-service calls; use IAM Identity Center for service identities; require SAML assertions for each API call.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — AWS PrivateLink + IAM SigV4 signing + API Gateway (AWS_IAM auth).

**Why it succeeds:**
* **Req 1 (Cryptographic identity):** IAM SigV4 request signing uses the service's IAM role credentials (access key + secret key derived from STS AssumeRole) to cryptographically sign every HTTP request. The signature is bound to the specific request content, timestamp, and region — impossible to forge without the IAM credentials.
* **Req 2 (Caller identity verification):** API Gateway with AWS_IAM authorization type extracts the Authorization SigV4 header, validates it against IAM, and provides the caller's IAM principal ARN to the backend. The backend knows exactly which IAM role made the call.
* **Req 3 (Cross-account):** API Gateway resource-based policies allow specific cross-account IAM role ARNs. The calling service (Lambda/ECS in Account A) assumes a role in Account A, signs the request, and API Gateway in Account B validates it via STS.
* **Req 4 (No VPN/DX):** AWS PrivateLink routes traffic over the AWS backbone — no public internet traversal, no VPN required.
* **Req 5 (Lambda + ECS Fargate):** Both Lambda execution roles and ECS task IAM roles are standard IAM roles — SigV4 signing is supported in all AWS SDKs for both platforms.

**Why alternatives fail:**
- [ ] Security groups and NACLs are network-layer controls (IP-based) — they provide no cryptographic identity. An IP address is not a service identity. This is traditional perimeter security, not zero-trust.
- [ ] mTLS provides cryptographic identity at the TLS layer but requires certificate distribution, rotation, and PKI management. Cross-account via TGW requires TGW attachment in each account. mTLS certificates don't natively integrate with IAM authorization — you'd need custom certificate validation logic. More operationally complex than SigV4.
- [ ] AWS Verified Access is designed for human user access to corporate applications (zero-trust network access for humans) — not for service-to-service API authentication. SAML assertions are for human identity federation, not machine-to-machine calls.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 32: Domain 4 – Cost Control

A company runs a multi-tier web application across 3 environments: production, staging, and development. Monthly costs: 
1. EC2 (prod: $40K, staging: $35K, dev: $28K). 
2. RDS (prod: $15K, staging: $12K, dev: $8K). 
3. Data transfer: $22K. 
4. Total: $160K/month. 
A FinOps review reveals staging mirrors production exactly, dev runs 24/7 with 5% utilization, and 70% of data transfer is EC2↔S3 within the same region.

<div class="question-prompt">
**Question:** Which set of changes provides the greatest cost reduction?
</div>

- [ ] Right-size staging EC2 to 50% of prod; use RDS read replicas instead of Multi-AZ for staging; stop dev on nights/weekends; add S3 Gateway Endpoint; purchase Savings Plans for prod.
- [ ] Terminate staging EC2 On-Demand and replace with Spot Instances (staging is non-production, interruption-tolerant); right-size staging RDS to single-AZ (no Multi-AZ needed for staging); implement Instance Scheduler for dev (stop 18hrs/day weekdays + full weekends = ~75% dev EC2/RDS cost reduction); add S3 Gateway Endpoints in all VPCs (eliminates 70% of $22K data transfer = ~$15.4K/month savings); purchase 1-year Compute Savings Plans covering prod EC2 baseline (~30% prod EC2 reduction).
- [ ] Merge staging and dev into a single environment; use AWS Service Catalog for environment provisioning on-demand; implement Savings Plans for all environments; add VPC endpoints.
- [ ] Migrate all environments to ECS Fargate; use Aurora Serverless for all RDS; implement S3 Intelligent-Tiering; stop staging when not in use.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — Spot for staging + single-AZ staging RDS + Instance Scheduler for dev + S3 Gateway Endpoints + prod Savings Plans.

**Why it succeeds:** Five targeted, high-ROI actions:
* **Staging EC2 → Spot (~70% saving):** $35K × 70% = $24.5K/month reduction. Staging is non-production, making it ideal for Spot (interruption can trigger a redeploy).
* **Staging RDS single-AZ (~50% saving):** Multi-AZ doubles RDS instance cost. $12K → ~$6K = $6K/month reduction.
* **Dev Instance Scheduler (75% saving):** $28K EC2 + $8K RDS = $36K × 75% = $27K/month reduction.
* **S3 Gateway Endpoints:** 70% of $22K data transfer is EC2→S3 within the same region routing through NAT Gateway at $0.045/GB. S3 Gateway Endpoint is free and eliminates this charge: $15.4K/month reduction.
* **Prod Savings Plans (~30%):** $40K × 30% = $12K/month reduction.
* **Total estimated savings:** ~$84.9K/month (53% reduction).

**Why alternatives fail:**
- [ ] Right-sizing staging to 50% of prod is less aggressive than Spot (50% reduction vs 70%); doesn't address the dev 24/7 waste comprehensively.
- [ ] Merging staging and dev environments is an operational risk — staging defects contaminate dev. AWS Service Catalog for on-demand provisioning adds process overhead.
- [ ] Migrating all environments to ECS Fargate requires complete re-architecture. Aurora Serverless for all databases changes pricing models significantly and may increase cost for consistently loaded staging RDS.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 33: Domain 1 – Design Solutions for Organizational Complexity

A company uses AWS Control Tower with 30 accounts. A new security requirement states: 
1. All S3 bucket creation events must be logged to a central immutable audit log in a dedicated Security account. 
2. Any S3 bucket without server-side encryption (SSE-S3 or SSE-KMS) must be automatically remediated within 5 minutes of creation. 
3. The solution must apply to all current and future accounts automatically. 
4. Security team must receive a daily digest report of all new unencrypted buckets found and remediated.

<div class="question-prompt">
**Question:** Which architecture satisfies all four requirements?
</div>

- [ ] AWS Config rule `s3-bucket-server-side-encryption-enabled` in all accounts via StackSets; CloudTrail in all accounts sending to central S3 bucket; Lambda auto-remediation triggered by Config; SNS daily digest via Lambda scheduled CloudWatch Events.
- [ ] Control Tower's mandatory guardrails (SCP-based) blocking unencrypted S3 bucket creation; CloudTrail organization trail to Security account; SNS for alerts; manual weekly report.
- [ ] AWS Config with `s3-bucket-server-side-encryption-enabled` rule deployed via Control Tower Customizations (CfCT) (auto-applies to new accounts); AWS Config auto-remediation using SSM Automation document `AWS-EnableS3BucketEncryption` with 5-minute remediation delay; CloudTrail Organization Trail (from management account, covering all current + future accounts automatically) → logs to S3 in Security account with S3 Object Lock (WORM/immutable); AWS Security Hub aggregated in Security account collects Config findings; EventBridge Scheduled Rule (daily 6pm) → Lambda → queries Security Hub findings API for last 24hrs → sends digest via SES.
- [ ] S3 Event Notifications to SQS for all bucket creation events; Lambda triggered by SQS to check encryption and remediate; CloudWatch Logs for audit; SNS for daily alerts.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **C** — CfCT-deployed Config rule + SSM auto-remediation + Organization Trail with S3 Object Lock + Security Hub + EventBridge/Lambda/SES digest.

**Why it succeeds:**
* **Req 1 (Central immutable audit log):** CloudTrail Organization Trail — configured once in the management account — automatically captures events from all current and future member accounts. S3 Object Lock in Governance or Compliance mode makes the audit log immutable (WORM) — satisfies immutability requirement for regulatory audit.
* **Req 2 (Auto-remediation in 5 min):** AWS Config auto-remediation with SSM Automation `AWS-EnableS3BucketEncryption` fires when the rule evaluates NON_COMPLIANT. Config evaluation is triggered on configuration change (bucket creation) — remediation occurs within minutes (typically < 5 min for Config → SSM Automation execution time).
* **Req 3 (All current + future accounts):** Control Tower Customizations (CfCT) uses Organizations integration to auto-deploy the Config rule to new accounts enrolled in Control Tower — no manual account-by-account deployment.
* **Req 4 (Daily digest):** EventBridge Scheduled Rule (cron) → Lambda → `security_hub.get_findings()` API with date filter → aggregates findings → sends formatted email via SES.

**Why alternatives fail:**
- [ ] StackSets are correct for deployment but require manual triggering for new accounts unless using `SERVICE_MANAGED` deployment with Organizations integration. Doesn't address immutability of the audit log.
- [ ] SCP-based guardrails prevent unencrypted bucket creation (deny the API call) — this is stronger but different from the requirement (detect and remediate within 5 minutes, implying detection of non-compliant buckets is expected, not prevention). SCP prevention would mean the bucket is never created — no remediation needed, but also no log of attempted creation. The requirement specifically says "automatically remediated," implying detection post-creation.
- [ ] S3 Event Notifications only fire for events within an existing bucket (object creation, deletion) — not for S3 bucket creation events. Bucket creation events are in CloudTrail, not S3 event notifications. This architecture is fundamentally flawed.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 34: Domain 5 – Continuous Improvement for Existing Solutions

A company's Aurora PostgreSQL cluster is experiencing: 
1. Read replica lag of 15–45 seconds during peak hours (application shows stale data). 
2. A long-running analytics query (runtime: 20 minutes) is blocking OLTP operations. 
3. The primary instance CPU is at 85% during peak. 
4. Vacuum bloat — tables have significant dead tuple accumulation, causing sequential scans to slow. 
5. Connection count is hitting Aurora's limit (5,000 connections) despite only 200 application pods.

<div class="question-prompt">
**Question:** Which improvements address all five issues systematically?
</div>

- [ ] Add more read replicas; kill long-running analytics queries via `pg_cancel_backend`; upgrade instance class; run VACUUM FULL manually during maintenance windows; increase `max_connections` parameter.
- [ ] Implement Aurora Auto Scaling for read replicas (adds replicas when replica lag exceeds threshold — directly addresses Issue 1); route analytics queries to a dedicated Aurora read replica with `aurora_read_replica_read_committed` isolation — isolating analytics from OLTP (Issue 2); upgrade primary to a larger instance class OR enable Aurora Serverless v2 for auto-scale (Issue 3); enable Aurora's autovacuum tuning — reduce `autovacuum_vacuum_scale_factor` to 0.01 and `autovacuum_cost_delay` to 2ms for aggressive dead tuple cleanup (Issue 4); deploy RDS Proxy in front of Aurora to multiplex 200 application pods' connections into a small pool (Issue 5).
- [ ] Migrate analytics queries to Amazon Redshift; add ElastiCache Redis read-through cache for OLTP; enable Aurora parallel query; run `pg_repack` instead of VACUUM FULL; use connection pooling in the application.
- [ ] Enable Multi-AZ; upgrade storage to io2; add 5 read replicas; configure PgBouncer on EC2; run VACUUM ANALYZE weekly.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — Aurora Auto Scaling + dedicated analytics replica + instance upgrade/Serverless v2 + autovacuum tuning + RDS Proxy.

**Why it succeeds:**
* **Issue 1 (Replica lag 15–45s):** Aurora Auto Scaling adds read replicas when `AuroraReplicaLag` CloudWatch metric exceeds a threshold — distributes read traffic across more replicas, reducing per-replica lag. This is the AWS-native solution for replica lag under read load.
* **Issue 2 (Analytics blocking OLTP):** Routing the 20-minute analytics query to a dedicated read replica (isolated from the OLTP replica pool) prevents query interference. Aurora's replica isolation allows the analytics query to run without blocking OLTP reads on other replicas.
* **Issue 3 (85% CPU):** Aurora Serverless v2 auto-scales ACUs in real-time — removes CPU saturation without manual instance resizing. Alternatively, upgrading instance class is a valid fix.
* **Issue 4 (Vacuum bloat):** Aurora PostgreSQL supports autovacuum parameter tuning via the Parameter Group. Reducing `autovacuum_vacuum_scale_factor` from 0.2 (default) to 0.01 makes autovacuum trigger after 1% dead tuple accumulation (vs 20% default) — dramatically reducing bloat. `autovacuum_cost_delay` reduction makes autovacuum more aggressive.
* **Issue 5 (5,000 connection limit):** RDS Proxy maintains a persistent pool of database connections (typically 100–200) and multiplexes thousands of application connections — reducing actual DB connections from 200 pods × 25 connections/pod = 5,000 to ~50–100 Proxy-held connections.

**Why alternatives fail:**
- [ ] Manually killing analytics queries is reactive, not systemic. VACUUM FULL requires exclusive table lock — it worsens OLTP performance during maintenance windows. Increasing `max_connections` increases per-connection memory overhead and can destabilize the instance.
- [ ] Migrating to Redshift for analytics is a significant architectural change, not continuous improvement. PgBouncer on EC2 adds infrastructure management; RDS Proxy is the fully managed equivalent.
- [ ] Multi-AZ addresses high availability, not performance. PgBouncer on EC2 is the self-managed alternative to RDS Proxy — higher operational overhead. Weekly VACUUM ANALYZE is insufficient for high write-rate tables.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 35: Domain 3 – Migration Planning

A company has 10TB of data in an on-premises Hadoop HDFS cluster (HBase, Hive tables, MapReduce jobs). They want to migrate to AWS for: 
1. Cost reduction (current Hadoop cluster: $50K/month). 
2. Eliminating cluster management. 
3. Preserving the ability to run existing Hive queries without rewriting. 
4. HBase use case: key-value lookups with < 10ms latency. 
5. MapReduce jobs should run on-demand (not 24/7 cluster).

<div class="question-prompt">
**Question:** Which migration targets are correct for each component?
</div>

- [ ] HDFS data → Amazon EFS; Hive → Athena; HBase → ElastiCache Redis; MapReduce → AWS Batch.
- [ ] HDFS data → Amazon S3 (using S3DistCp or AWS DataSync for migration); Hive → Amazon Athena (Athena uses HiveQL — Hive queries run with minimal modification against S3 data via Glue Data Catalog); HBase → Amazon DynamoDB (key-value, sub-10ms reads with on-demand capacity); MapReduce → Amazon EMR (transient cluster — spin up on-demand, terminate after job completion; EMR supports native MapReduce and also allows Spark migration path).
- [ ] HDFS → Amazon EBS; Hive → Amazon Redshift; HBase → Amazon RDS; MapReduce → AWS Lambda.
- [ ] HDFS → S3; Hive → Amazon EMR with persistent Hive Metastore; HBase → Amazon DynamoDB; MapReduce → AWS Glue (PySpark).

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — S3 + Athena + DynamoDB + transient EMR.

**Why it succeeds:**
* **HDFS → S3:** S3 is the de facto replacement for HDFS in the cloud — infinitely scalable, 11 9s durability, no cluster management. S3DistCp (available on EMR) efficiently migrates HDFS data to S3 using distributed copy.
* **Hive → Athena:** Athena uses Apache Hive DDL and HiveQL for queries against S3 data. The Glue Data Catalog serves as the Hive Metastore. Existing Hive queries work with minimal modification (S3 paths instead of HDFS paths). Serverless — no cluster management, pay-per-query.
* **HBase → DynamoDB:** HBase is a key-value/columnar store on HDFS. DynamoDB is the AWS equivalent: single-digit millisecond reads, key-value and document model, fully managed, no cluster ops. Sub-10ms requirement satisfied by DynamoDB's consistent read performance.
* **MapReduce → Transient EMR:** EMR supports native Hadoop MapReduce. Transient cluster (on-demand) eliminates 24/7 cluster cost. EMR cost = hours used × instance cost, vs $50K/month for a persistent Hadoop cluster.

**Why alternatives fail:**
- [ ] Amazon EFS is not a cost-effective or performance-appropriate replacement for HDFS (file-based, NFS protocol, not optimized for big data query patterns). ElastiCache Redis for HBase misses the key-value data model persistence guarantee — Redis is in-memory cache, not a primary database.
- [ ] EBS is block storage for individual EC2 instances — not a shared storage replacement for HDFS. Redshift requires ETL to load Hive tables and is a different query paradigm. Lambda has 15-minute timeout — completely incompatible with MapReduce jobs (potentially hours).
- [ ] Option D is close but misses the "transient" EMR emphasis for MapReduce. Also, Glue (PySpark) for MapReduce would require rewriting MapReduce jobs in PySpark — violates requirement 3's "without rewriting."

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 36: Domain 2 – Design for New Solutions

A company is designing a serverless event processing system. Events come from 50 different source systems. Requirements: 
1. Events from each source must be processed independently — one source's failures must not block others. 
2. Each source may have different processing logic (50 different Lambda functions). 
3. Events must be deduplicated — the same event from the same source delivered twice must be processed only once. 
4. Failed events must be retried up to 3 times with exponential backoff, then moved to a DLQ for inspection. 
5. Event processing order must be maintained per source.

<div class="question-prompt">
**Question:** Which architecture satisfies all five requirements?
</div>

- [ ] Single SNS topic with 50 SQS queue subscriptions (one per source); Lambda triggered from each SQS queue; deduplication via DynamoDB idempotency table; DLQ per queue; SQS FIFO for ordering.
- [ ] Amazon EventBridge with 50 event buses (one per source); EventBridge rules routing to source-specific Lambda functions; deduplication via Lambda Powertools Idempotency (DynamoDB); EventBridge retry policy (up to 185 attempts configurable); EventBridge DLQ (SQS) for failed events; ordering not guaranteed by EventBridge.
- [ ] Amazon SQS FIFO queues (one per source — 50 queues); each queue triggers its dedicated Lambda function; SQS FIFO `MessageDeduplicationId` (content-based or producer-assigned) handles deduplication natively; Lambda `maxReceiveCount=3` on each queue's redrive policy → DLQ after 3 failures; SQS FIFO `MessageGroupId` = source identifier ensures ordering per group.
- [ ] Amazon Kinesis Data Streams with 50 shards (one per source); Lambda consumer per shard; deduplication in Lambda code; retry via Kinesis bisect-on-error; DLQ via Lambda event source mapping destination.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **C** — SQS FIFO queues (one per source) + Lambda + native deduplication + redrive policy + DLQ.

**Why it succeeds:**
* **Req 1 (Independent processing):** 50 separate SQS FIFO queues — each source is completely isolated. A failure in source 1's queue has zero impact on source 2–50 queues.
* **Req 2 (Different processing logic):** 50 dedicated Lambda functions, each triggered by its corresponding SQS FIFO queue event source mapping.
* **Req 3 (Deduplication):** SQS FIFO natively deduplicates messages within a 5-minute deduplication window using `MessageDeduplicationId` (SHA-256 hash of message body for content-based deduplication). No external DynamoDB table required.
* **Req 4 (Retry 3 times + DLQ):** SQS redrive policy: `maxReceiveCount=3` — after 3 failed processing attempts, the message is automatically moved to the configured dead-letter queue for inspection. Lambda's retry is managed by SQS visibility timeout + `maxReceiveCount`.
* **Req 5 (Ordering per source):** SQS FIFO with `MessageGroupId` = source ID guarantees strict ordering within each group. SQS FIFO maintains FIFO order per message group.

**Why alternatives fail:**
- [ ] SQS standard queues (implied by "50 SQS queue subscriptions" to SNS) don't guarantee FIFO ordering — violates requirement 5. SNS fan-out adds unnecessary indirection for 50 fixed sources.
- [ ] EventBridge does not guarantee event ordering — violates requirement 5. EventBridge retry semantics are complex and not equivalent to simple `maxReceiveCount`-based retry with exponential backoff.
- [ ] Kinesis ordering is per-shard (not per partition key within a shard) — duplicate events in the same shard window cannot be natively deduplicated by Kinesis. Kinesis charges per shard-hour regardless of volume — cost inefficient for bursty/low-volume sources.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 37: Domain 4 – Cost Control

A media company streams video content globally. Their CloudFront distribution serves 5PB/month of video. The cost breakdown: 
1. CloudFront data transfer out: $425,000/month (5PB × $0.085/GB average). 
2. S3 GET requests for video segments: $65,000/month. 
3. Origin Shield: not enabled. 
4. Content is 80% cacheable (live streaming 20% dynamic). 
5. The company has a reserved capacity commitment discussion ongoing with AWS.

<div class="question-prompt">
**Question:** Which combination of actions reduces CloudFront costs most effectively?
</div>

- [ ] Compress all video segments with gzip; enable Lambda@Edge to optimize cache-hit ratio; negotiate a custom pricing agreement with AWS for volume discounts.
- [ ] CloudFront Security Savings Bundle (commit to 1-year CloudFront usage → 30% discount on data transfer out); enable CloudFront Origin Shield (consolidates origin requests, reduces S3 GETs by ~75%); implement CloudFront Cache Policies with aggressive TTLs for static video segments (increase cache hit ratio from current baseline → reduce origin traffic); use S3 Intelligent-Tiering for video source files in S3.
- [ ] Move video origin from S3 to EC2-based HTTP server; use Route 53 GeoDNS instead of CloudFront; implement a CDN from a third-party provider for cost arbitrage.
- [ ] Reduce video quality/bitrate to reduce data transfer volume; implement HLS adaptive bitrate streaming; use CloudFront signed URLs to reduce unauthorized access bandwidth waste.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — CloudFront Security Savings Bundle + Origin Shield + Cache Policies.

**Why it succeeds:**
* **Data transfer cost ($425K):** The CloudFront Security Savings Bundle commits to a monthly CloudFront usage level for 1 year and provides a 30% discount on data transfer out + WAF included. At 5PB/month: $425K × 30% = $127.5K/month saving.
* **S3 GET requests ($65K):** CloudFront Origin Shield adds a regional caching layer. For an 80% cacheable content ratio, Origin Shield can reduce origin requests by 70–80%. S3 GET costs: $65K × 75% reduction = $48.75K/month saving.
* **Cache hit ratio improvement:** Cache Policies with long TTLs (86400s for video segments that never change once published) dramatically reduce origin fetches. Each avoided origin fetch saves both S3 GET costs and CloudFront origin request charges.
* **Total estimated savings:** ~$176K/month (41% reduction).

**Why alternatives fail:**
- [ ] gzip compression of video content (already compressed MP4/HLS) yields no meaningful compression — video codecs are already at near-optimal compression ratios. Lambda@Edge for cache optimization adds latency and cost. Custom pricing negotiations are not an architecture decision.
- [ ] Moving from S3 to EC2 for video serving adds operational overhead and EC2 costs that likely exceed S3. Third-party CDNs add integration complexity and vendor management overhead.
- [ ] Reducing video quality directly degrades the user experience — not a viable business decision for a media streaming company. Signed URLs for access control don't reduce bandwidth from legitimate users, which is the primary cost driver.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 38: Domain 5 – Continuous Improvement for Existing Solutions

A company's CI/CD pipeline deploys to production using CodePipeline → CodeBuild → CodeDeploy. Problems: 
1. Production deployments cause 3–5 minute outages during CodeDeploy in-place deployments. 
2. Build times average 45 minutes — blocking developer velocity. 
3. No automated testing — defects reach production weekly. 
4. The team cannot roll back quickly when defects are found — rollback takes 30+ minutes. 
5. Secrets (DB passwords, API keys) are hardcoded in `buildspec.yml` files in CodeCommit.

<div class="question-prompt">
**Question:** Which set of improvements resolves all five issues?
</div>

- [ ] Switch to CodeDeploy Blue/Green; use ElasticCache for build caching; add manual approval gates; use AWS Systems Manager Parameter Store for secrets; implement CodePipeline manual rollback.
- [ ] Switch CodeDeploy to Blue/Green deployment with ALB traffic shifting (linear or canary) — zero-downtime deployment, instant rollback by shifting traffic back to the original (blue) environment (Issues 1 and 4); implement CodeBuild caching (S3 or local cache for dependencies like Maven/npm packages — reduces build time by 50–70%) + CodeBuild fleet (reserved capacity for parallel builds) (Issue 2); add CodePipeline stage with CodeBuild test action running unit tests + SAST (Semgrep or SonarQube via CodeBuild) before deployment stage (Issue 3); migrate all secrets to AWS Secrets Manager — reference in `buildspec.yml` as `aws secretsmanager get-secret-value` calls or CodeBuild environment variables sourced from Secrets Manager (Issue 5).
- [ ] Migrate entire CI/CD to GitHub Actions + ArgoCD on EKS; use HashiCorp Vault for secrets; implement Canary deployments; use parallel GitHub Actions jobs for build speed.
- [ ] Use AWS Elastic Beanstalk with rolling deployments; implement AWS CodeStar for project management; use CloudFormation for all deployments; store secrets in S3 (encrypted with SSE-KMS).

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — Blue/Green + CodeBuild caching + automated test stage + Secrets Manager.

**Why it succeeds:**
* **Issue 1 (3–5 min outages):** CodeDeploy Blue/Green with ALB traffic shifting deploys to a new (green) target group while the original (blue) group continues serving traffic. ALB shifts traffic only after health checks pass — zero downtime.
* **Issue 2 (45-min builds):** CodeBuild dependency caching to S3 stores Maven/npm/pip packages between builds. Cache hit rates of 80%+ reduce download time from external registries — typical build time reduction: 30–60%. CodeBuild Reserved Capacity (fleet) eliminates queue wait time.
* **Issue 3 (No automated testing):** Adding a CodePipeline Test stage with CodeBuild actions running `mvn test`, `pytest`, or SAST tools before the Deploy stage blocks defective code from reaching production.
* **Issue 4 (Slow rollback):** Blue/Green rollback = shifting ALB target group weights back to the original blue group — < 60 seconds. The original environment is preserved until the green deployment is verified.
* **Issue 5 (Hardcoded secrets):** AWS Secrets Manager stores secrets encrypted with KMS. `buildspec.yml` references secrets via environment variables backed by Secrets Manager (using `SECRETS_MANAGER_VAR` syntax or `aws secretsmanager get-secret-value` in pre-build phase). No secrets in source code.

**Why alternatives fail:**
- [ ] SSM Parameter Store for secrets is valid (`SecureString` type) but Secrets Manager is preferred for rotating credentials (DB passwords, API keys) with automatic rotation support. The answer is otherwise partially correct but incomplete on build speed and testing.
- [ ] Migrating the entire CI/CD stack to GitHub Actions + ArgoCD + HashiCorp Vault is a complete re-architecture — disproportionate to the requirement of improving an existing AWS CodePipeline setup.
- [ ] Elastic Beanstalk with rolling deployments doesn't eliminate downtime for in-place scenarios. Storing secrets in S3 (even encrypted) is not the right pattern — S3 lacks secret rotation, access auditing per-secret, or programmatic secret version management.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 39: Domain 1 – Design Solutions for Organizational Complexity

A company manages AWS costs across 50 accounts in an Organization. The CFO requires: 
1. Showback reports — each business unit sees only their accounts' costs. 
2. Shared service costs (networking, security tooling) must be allocated proportionally to business units. 
3. Budget alerts must trigger at 80% and 100% of each BU's quarterly budget and notify the BU's finance contact (different per BU). 
4. All cost data must be queryable via SQL for custom reporting. 
5. Reserved Instance and Savings Plan benefits must be shared across all accounts in the Organization.

<div class="question-prompt">
**Question:** Which architecture satisfies all five requirements?
</div>

- [ ] AWS Cost Explorer per account; manual monthly cost allocation spreadsheets; SNS alerts for budgets; Athena for querying; RI sharing via Organization's consolidated billing.
- [ ] AWS Cost and Usage Report (CUR) delivered to a central S3 bucket (consolidated, with resource-level tags including BU and CostCenter tags); AWS Glue crawler on CUR data → Athena for SQL querying (Req 4); AWS Cost Allocation Tags for BU-level showback; Cost Categories in Cost Explorer to group accounts by BU and allocate shared service costs proportionally using Cost Category split charge rules (Req 2); AWS Budgets per BU (account-level or tag-based) with Budget Actions (SNS notification → Lambda → looks up BU finance contact in DynamoDB → sends email via SES) (Req 3); RI and SP sharing via Organization's consolidated billing (Req 5).
- [ ] QuickSight with Cost Explorer data source per BU; manual RI purchasing in management account; SNS topics per BU for budget alerts; CloudWatch dashboards for cost visibility.
- [ ] Third-party FinOps tool (CloudHealth, Apptio); AWS Cost Explorer APIs; per-account Budgets with SNS; consolidated billing for RI sharing.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — CUR + Glue/Athena + Cost Categories + AWS Budgets + SNS/Lambda/SES.

**Why it succeeds:**
* **Req 1 (Showback per BU):** AWS Cost Allocation Tags applied to all resources (automatically via Tag Policies in Organizations) enable BU-level cost attribution in CUR. Cost Explorer can filter by tag for showback reporting per BU.
* **Req 2 (Shared cost allocation):** Cost Categories with split charge rules allocate shared service costs (e.g., networking account: $50K/month) proportionally to BUs based on their percentage of total usage — natively supported in Cost Explorer Cost Categories.
* **Req 3 (BU-specific budget alerts):** AWS Budgets configured per BU (cost filter by account or tag) with 80% and 100% thresholds → SNS notification → Lambda → queries DynamoDB for BU finance contact email → SES delivery. Lambda enables per-BU custom notification routing.
* **Req 4 (SQL queryability):** CUR → S3 → Glue crawler → Athena provides full SQL access to line-item cost data including tags, resource IDs, service names, usage types — the most granular cost data available in AWS.
* **Req 5 (RI/SP sharing):** AWS Organization consolidated billing automatically shares RI and Savings Plan discounts across all member accounts — the purchasing account's discount applies to the entire Organization.

**Why alternatives fail:**
- [ ] Manual spreadsheets for shared cost allocation fail requirement 2 (no automation, error-prone). Per-account Cost Explorer doesn't aggregate for Organization-level showback.
- [ ] QuickSight with Cost Explorer as a data source provides visualization but Cost Explorer data is pre-aggregated — it doesn't provide the line-item granularity of CUR for custom SQL queries. Manual RI purchasing doesn't address shared cost allocation.
- [ ] Third-party FinOps tools add cost and vendor dependency — all five requirements are solvable with AWS-native services. The exam tests AWS-native solutions.

---

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 40: Domain 2 – Design for New Solutions

A startup is building a real-time collaborative document editing platform (similar to Google Docs) on AWS. Requirements: 
1. < 50ms latency for change propagation between users editing the same document. 
2. Support 10,000 concurrent editing sessions. 
3. Document state must be durable — no data loss even if a server fails mid-edit. 
4. The platform must support operational transformation (OT) or CRDT-based conflict resolution — the server must sequence concurrent edits. 
5. Cost must scale near-zero when document traffic is low.

<div class="question-prompt">
**Question:** Which architecture best satisfies all constraints?
</div>

- [ ] WebSocket connections to EC2 instances with Auto Scaling; DynamoDB for document state; ElastiCache Redis pub/sub for change propagation; S3 for document snapshots; Lambda for OT conflict resolution.
- [ ] API Gateway WebSocket API → Lambda (connection handler); Amazon ElastiCache Redis (pub/sub channels per document — propagates edits to all connected clients subscribing to the document channel); DynamoDB (stores document state with conditional writes for optimistic concurrency — each edit is a conditional update on the document version); DynamoDB Streams → Lambda for OT/CRDT conflict resolution (sequences concurrent edits by timestamp + version); S3 for periodic document snapshots (durability); API Gateway WebSocket supports 10K concurrent connections per API with Regional deployment.
- [ ] AWS AppSync (GraphQL subscriptions) for real-time updates; Aurora PostgreSQL for document state; Redis for pub/sub; Lambda for conflict resolution; CloudFront for WebSocket acceleration.
- [ ] Amazon IVS (Interactive Video Service) for real-time streaming; DynamoDB for document state; EventBridge for change propagation; Step Functions for conflict resolution.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

**Optimal Solution:** **B** — API Gateway WebSocket + Lambda + ElastiCache Redis pub/sub + DynamoDB conditional writes + Streams.

**Why it succeeds:**
* **Req 1 (< 50ms latency):** API Gateway WebSocket API maintains persistent WebSocket connections. ElastiCache Redis pub/sub delivers messages to subscribers in < 1ms within the same region. End-to-end latency (client → API GW → Lambda → Redis pub/sub → subscriber Lambda → client) is typically 10–30ms within a region.
* **Req 2 (10K concurrent sessions):** API Gateway WebSocket API supports up to 128K concurrent connections per API (Regional). Lambda scales concurrently per connection message.
* **Req 3 (Durability):** DynamoDB provides 11 9s durability with synchronous Multi-AZ replication. Every edit is persisted to DynamoDB before acknowledgment. S3 snapshots provide point-in-time recovery.
* **Req 4 (OT/CRDT conflict resolution):** DynamoDB conditional writes (`ConditionExpression: version = :expected_version`) implement optimistic concurrency — concurrent conflicting edits are serialized. DynamoDB Streams captures the ordered sequence of writes; Lambda processes the stream to apply OT/CRDT logic and publish the resolved state.
* **Req 5 (Scale to zero):** API Gateway + Lambda charge per connection/message. ElastiCache Redis has a minimum node cost, but the smallest `cache.t4g.micro` is ~$12/month. DynamoDB on-demand scales to zero. Near-zero cost at low traffic.

**Why alternatives fail:**
- [ ] EC2-based WebSocket servers require always-on instances — violates requirement 5 (scale to zero). At 10K concurrent sessions, EC2 instances must be pre-provisioned. Auto Scaling doesn't scale to zero.
- [ ] AWS AppSync GraphQL subscriptions are built on WebSockets and can work, but AppSync adds GraphQL overhead and is less cost-efficient for high-frequency binary/delta change propagation. Aurora PostgreSQL for document state is more expensive than DynamoDB for high-write, key-value access patterns.
- [ ] Amazon IVS is for live video streaming — completely inappropriate for document collaboration. EventBridge is not a real-time low-latency pub/sub mechanism (EventBridge has ~1 second delivery SLA, not sub-50ms).

</details>
</div>


<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 41: Domain 1 — Design Solutions for Organizational Complexity

A global bank operates 120 AWS accounts across OUs: `Production`, `NonProduction`, `Sandbox`, and
`Shared-Services`. All inter-VPC traffic must route through a centralized Network Inspection VPC
running a third-party firewall appliance (Palo Alto VM-Series). Requirements: (1) all VPC-to-VPC
traffic and VPC-to-on-premises traffic must traverse the firewall — no bypass permitted; (2) new
spoke VPCs must automatically inherit routing without manual TGW route table updates; (3) the
firewall must be horizontally scalable with no single point of failure; (4) on-premises connects
via two Direct Connect connections (active/active) with BGP; (5) the solution must support
**1000+ spoke VPCs** without hitting Transit Gateway route table limits.

<div class="question-prompt">
**Question:** Which architecture BEST satisfies all five requirements?
</div>

- [ ] Deploy Transit Gateway with a single route table. Attach all spoke VPCs and the
  Inspection VPC. Configure static routes pointing all traffic to the firewall ENI. Use BGP
  over Direct Connect for on-premises routing. Scale firewall vertically with larger instances.
- [ ] Deploy Transit Gateway with **two route tables**: a `spoke-rt` (associated with all
  spoke VPCs, default route → Inspection VPC attachment) and an `inspection-rt` (associated with
  Inspection VPC attachment, routes back to spokes). Deploy firewall appliances behind a **Gateway
  Load Balancer (GWLB)** in the Inspection VPC. Use GWLB Endpoints in each spoke VPC. Propagate
  on-premises routes via BGP over Direct Connect to the TGW.
- [ ] Deploy Transit Gateway with **two route tables**: `spoke-rt` (default route 0.0.0.0/0
  → Inspection VPC TGW attachment) and `firewall-rt` (specific routes back to each spoke CIDR).
  Deploy firewall appliances behind a **Gateway Load Balancer** in the Inspection VPC. Use TGW
  appliance mode on the Inspection VPC attachment to maintain flow symmetry. Connect Direct Connect
  via a Direct Connect Gateway to the TGW. Use TGW CIDR blocks and blackhole routes to prevent
  route table limit issues.
- [ ] Use VPC Peering between all spoke VPCs and the Inspection VPC. Deploy firewall
  appliances with an NLB. Route all traffic via the peering connection to the firewall. Use
  separate Direct Connect Virtual Interfaces per VPC for on-premises connectivity.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — TGW with two route tables + Gateway Load Balancer for firewall
  HA/scale + TGW appliance mode + Direct Connect Gateway.

* **Why it succeeds:** The **two-route-table TGW pattern** is the AWS-canonical architecture for
  centralized inspection. The `spoke-rt` (associated with all spoke attachments) has a default
  route to the Inspection VPC TGW attachment — forcing all spoke egress through the firewall.
  The `firewall-rt` (associated with the Inspection VPC attachment) has return routes to all spoke
  CIDRs, completing the hairpin. **TGW appliance mode** on the Inspection VPC attachment is
  critical — it ensures that both directions of a flow (request and response) are routed through
  the same firewall instance, maintaining stateful inspection symmetry across multiple AZs.
  **Gateway Load Balancer** provides transparent Layer-3/Layer-4 load balancing across firewall
  instances using the GENEVE protocol — it scales horizontally with no changes to routing, and
  failed instances are automatically removed, satisfying constraint 3. **Direct Connect Gateway**
  attaches to TGW and aggregates both DX connections, supporting BGP route propagation to spoke
  VPCs without manual route table entries, satisfying constraint 2 for on-premises routes. TGW
  CIDR blocks and aggregate routes avoid the 10,000 route table entry limit for 1000+ spokes.

* **Why alternatives fail:**
  - **A)** Static routes to a single firewall ENI create a single point of failure (constraint 3
    violated). A single TGW route table cannot enforce inspection hairpin without complex
    per-VPC static routes. Vertical firewall scaling is limited and does not provide HA.
  - **B)** GWLB Endpoints in each spoke VPC is the wrong placement for TGW-based centralized
    inspection — GWLB Endpoints in spokes bypass the TGW inspection path. The correct pattern
    is GWLB in the Inspection VPC only, with TGW handling the traffic steering. This option also
    does not specify appliance mode, which would cause asymmetric routing failures for stateful
    firewall inspection across AZs.
  - **D)** VPC Peering does not support transitive routing — traffic cannot flow VPC-A → Peering
    → Inspection VPC → Peering → VPC-B. VPC Peering is a point-to-point construct and cannot
    implement a hub-and-spoke inspection architecture. At 1000+ VPCs, VPC Peering is also
    operationally unmanageable (each VPC would need peering connections to every other VPC).

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 42: Domain 2 — Design for New Solutions

A fintech company is building a fraud detection system. Requirements: (1) payment transactions
arrive at **200,000 transactions/minute**; (2) each transaction must be scored by an ML model
within **100ms** of ingestion; (3) the ML model is retrained weekly and must be **swapped without
any downtime or scoring gaps**; (4) fraud signals must trigger a **real-time block** on the
payment processor API within 50ms of detection; (5) all transaction data must be stored for
**5 years** for regulatory audit, queryable by transaction ID in under 1 second; (6) the model
uses 47 real-time features derived from the last 30 days of customer transaction history.

<div class="question-prompt">
**Question:** Which architecture satisfies all six requirements?
</div>

- [ ] Kinesis Data Streams → Lambda (feature engineering + model inference via SageMaker
  Runtime) → DynamoDB (fraud signals) → SNS → Payment processor. S3 + Athena for 5-year audit.
  SageMaker endpoint blue/green for model swap.
- [ ] Kinesis Data Streams (200K TPS ingestion) → Kinesis Data Analytics Flink
  (real-time feature computation from 30-day sliding window in DynamoDB) → SageMaker
  **Asynchronous Inference Endpoint** (model scoring) → EventBridge → Lambda (payment block API
  call). S3 Intelligent-Tiering + Athena for 5-year audit with DynamoDB transaction index.
- [ ] Kinesis Data Streams → **Amazon Managed Service for Apache Flink** (real-time
  feature engineering with 30-day state in RocksDB backed by S3) → SageMaker **Real-Time
  Inference Endpoint** with **production variants** (two variants: current model 100% traffic,
  new model 0% — swap by updating variant weights to 100%/0% atomically) → Lambda (payment
  block) triggered via DynamoDB Streams on fraud signal write. S3 + Glue + Athena for 5-year
  audit. DynamoDB on-demand for transaction index (single-digit ms lookup by transaction ID).
- [ ] MSK (Kafka) → Kafka Streams (feature engineering) → EC2-hosted ONNX runtime
  (model inference) → SQS → Lambda (payment block). RDS PostgreSQL for 5-year audit storage.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Kinesis → Managed Flink (RocksDB state) → SageMaker Real-Time
  with production variants → Lambda via DynamoDB Streams → S3/Glue/Athena + DynamoDB index.

* **Why it succeeds:** Kinesis Data Streams ingests 200K TPS with horizontal shard scaling.
  **Amazon Managed Service for Apache Flink** (formerly KDA for Flink) maintains **stateful
  stream processing** using RocksDB as the local state backend (checkpointed to S3) — this
  enables exact 30-day sliding window feature computation (constraint 6) with sub-millisecond
  state lookups without external database calls, keeping the scoring pipeline within the 100ms
  SLA. **SageMaker Real-Time Inference** with **production variants** is the correct zero-downtime
  model swap mechanism — variant weights can be updated atomically (100% → 0% for old, 0% → 100%
  for new) while the endpoint remains active and serving, satisfying constraint 3. DynamoDB
  on-demand writes fraud signals with single-digit millisecond latency; DynamoDB Streams triggers
  Lambda for the payment block API call — the stream trigger adds ~5-10ms, keeping the total
  detection-to-block time within 50ms (constraint 4). S3 + Glue catalog + Athena provides SQL
  queryability for 5-year regulatory audit (constraint 5). DynamoDB transaction index delivers
  sub-1-second lookup by transaction ID.

* **Why alternatives fail:**
  - **A)** Lambda invoking SageMaker Runtime synchronously adds Lambda cold-start latency (up to
    500ms) — this violates the 100ms scoring SLA (constraint 2). Lambda's 15-minute timeout and
    per-invocation overhead is unsuitable for 200K TPS sustained throughput.
  - **B)** SageMaker **Asynchronous Inference** is designed for large payloads and batch jobs with
    response times of seconds to minutes — it explicitly violates the 100ms real-time scoring
    requirement (constraint 2). Asynchronous Inference is the wrong endpoint type for real-time
    fraud scoring.
  - **D)** EC2-hosted ONNX runtime has no managed scaling, no built-in HA, and model swap requires
    instance restarts or rolling deployments — violating constraint 3. RDS PostgreSQL for 5-year
    audit of 200K TPS × 5 years ≈ 52 billion rows is operationally and cost-prohibitively
    expensive compared to S3 + Athena.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 43: Domain 3 — Migration Planning

A media company is migrating 800TB of video assets from an on-premises NAS (NFS protocol) to
Amazon S3 over 10 weeks. Constraints: (1) the on-premises network has **10 Gbps** connectivity
to the internet but this link is **shared** with production traffic — migration may use at most
**30% of bandwidth** during business hours (9am-6pm) and **80%** off-hours; (2) all files must
arrive in S3 with **bit-for-bit integrity verification**; (3) after migration, the on-premises
NAS must remain accessible to legacy edit workstations for 12 months (hybrid access); (4)
frequently accessed assets (top 20%) must be available in S3 Standard; remaining 80% in S3
Standard-IA; (5) the entire migration and cutover must be tracked with a completion percentage
visible to stakeholders.

<div class="question-prompt">
**Question:** Which architecture satisfies ALL constraints?
</div>

- [ ] Use `aws s3 cp` with `--recursive` from an EC2 instance in the same region. Set
  bandwidth throttling via Linux `tc` (traffic control). Use S3 Transfer Acceleration for speed.
  After migration, mount S3 via s3fs-fuse on edit workstations for hybrid access.
- [ ] Deploy **AWS DataSync** agents on-premises (two agents for parallelism). Configure
  DataSync tasks with **bandwidth throttling schedules** (30% limit 9am-6pm, 80% off-hours).
  Enable DataSync **data integrity verification** (end-to-end checksum). Configure destination
  S3 bucket with **S3 Lifecycle rules** to transition objects based on access patterns after
  migration. Deploy **AWS Storage Gateway File Gateway** for hybrid NFS access post-migration.
  Track via DataSync task execution reports + CloudWatch metrics visible via a CloudWatch
  dashboard shared with stakeholders.
- [ ] Order AWS Snowball Edge devices (10 × 100TB) to ship the 800TB. After data lands in
  S3, use DataSync for delta sync. Deploy Storage Gateway for hybrid access. Use S3 Intelligent-
  Tiering for automatic storage class management.
- [ ] Use AWS Transfer Family (SFTP) to upload files directly to S3. Configure IAM policies
  to enforce storage class on upload. Use DataSync for integrity verification post-upload. Mount
  S3 via AWS Storage Gateway Volume Gateway for hybrid access.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — DataSync agents with bandwidth throttle schedules + integrity
  verification + S3 Lifecycle + Storage Gateway File Gateway + CloudWatch dashboard.

* **Why it succeeds:** AWS DataSync is purpose-built for large-scale NFS-to-S3 migrations.
  **DataSync bandwidth throttling** supports scheduled throttle rates — a lower rate during
  business hours and higher rate off-hours directly satisfies constraint 1. DataSync performs
  **automatic end-to-end checksum verification** (at source read, in-flight, and at S3 write)
  — satisfying constraint 2 without manual md5sum scripts. Two parallel DataSync agents
  maximize throughput within the bandwidth envelope. **S3 Lifecycle rules** transition objects
  based on LastAccessed metrics (requires S3 Last Access tracking enabled) or can be configured
  with prefix-based rules post-migration analysis — satisfying constraint 4. **AWS Storage
  Gateway File Gateway** presents S3 as an NFS mount to legacy edit workstations, maintaining
  on-premises access patterns while backing to S3 — satisfying constraint 3. DataSync execution
  reports and CloudWatch metrics (bytes transferred, files transferred, task status) feed a
  CloudWatch dashboard accessible to stakeholders — satisfying constraint 5.

* **Why alternatives fail:**
  - **A)** `aws s3 cp` does not natively support scheduled bandwidth throttling windows —
    Linux `tc` controls interface-level traffic but is complex to schedule and does not integrate
    with S3 transfer internals. s3fs-fuse is a FUSE-based S3 mount with known performance and
    consistency limitations — it is not suitable for professional video editing workloads. No
    built-in integrity verification matching DataSync's checksum depth.
  - **C)** 10 × Snowball Edge devices have a 7–10 day round-trip shipping time each. For 800TB
    over 10 weeks, the logistics timeline is tight and does not allow for bandwidth-throttled
    incremental transfer. Snowball cannot honor the bandwidth-sharing constraint (constraint 1)
    since it operates offline. S3 Intelligent-Tiering monitors access patterns with a per-object
    fee — less cost-efficient than explicit Lifecycle rules when the access pattern split (20/80)
    is already known.
  - **D)** AWS Transfer Family (SFTP) is designed for file transfer workflows via SFTP/FTPS/FTP
    protocols — it does not natively mount NFS shares or perform bulk NAS migrations. It lacks
    DataSync's parallel chunked transfer engine and integrity verification depth.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 44: Domain 4 — Cost Control

A SaaS company runs a multi-tenant platform on AWS. The architecture: Route 53 → CloudFront →
ALB → ECS Fargate (API, always-on, 24/7) → Aurora PostgreSQL (Multi-AZ) → ElastiCache Redis
(cluster mode, 3 shards × 2 replicas). Monthly bill: Fargate $22,000, Aurora $31,000,
ElastiCache $14,000, CloudFront $8,000, ALB $2,000, data transfer $9,000. Total: $86,000/month.
Traffic analysis: **API traffic is 8× higher on weekdays vs weekends**. Aurora has **40% idle
capacity on weekends**. ElastiCache hit rate is **94%** — cache is correctly sized. The CTO
mandates a **30% cost reduction** with no SLA degradation and no re-architecture.

<div class="question-prompt">
**Question:** Which combination of targeted changes delivers ≥30% reduction?
</div>

- [ ] Purchase 1-year Reserved Nodes for ElastiCache. Convert Aurora to Aurora Serverless
  v2 (scales down on weekends). Purchase Compute Savings Plans (1-year) for Fargate. Use
  CloudFront Price Class 100 to reduce edge PoP costs.
- [ ] Purchase 1-year Reserved Nodes for ElastiCache (saves ~35% on $14K). Convert
  Aurora Multi-AZ to Aurora Serverless v2 (min ACU = 2, scales down 40% on weekends — saves
  ~$8-10K/month on $31K). Purchase **Compute Savings Plans (1-year)** for Fargate (~17% savings
  on $22K). Switch CloudFront to **Price Class 200** to reduce PoP coverage cost. Use **VPC
  Endpoints** for S3 and DynamoDB to eliminate $9K data transfer charges routed through NAT.
- [ ] Scale down ECS Fargate tasks on weekends using Application Auto Scaling with
  scheduled scaling actions. Convert Aurora to Aurora Serverless v2. Purchase Reserved Nodes
  for ElastiCache. Reduce CloudFront TTLs to lower origin fetch costs.
- [ ] Migrate ElastiCache to DynamoDB Accelerator (DAX). Convert Aurora Multi-AZ to
  single-AZ. Use Fargate Spot for the API tier. Switch to CloudFront Price Class 100.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — ElastiCache Reserved Nodes + Aurora Serverless v2 + Fargate
  Compute Savings Plans + CloudFront Price Class reduction + VPC Endpoints for data transfer.

* **Why it succeeds:** **ElastiCache Reserved Nodes** (1-year, all-upfront) provide ~35% savings
  on the $14,000 line item → ~$4,900 saved. **Aurora Serverless v2** with `min ACU = 2` scales
  capacity down automatically during weekend low-traffic periods — at 40% idle capacity on
  weekends (2 days/7 = 29% of the week), this reduces Aurora cost by approximately 25-30%
  on the $31,000 line item → ~$8,000 saved. Serverless v2 retains Multi-AZ behavior and
  sub-second scaling, preserving SLA. **Compute Savings Plans (1-year)** on Fargate provide
  ~17% savings on the $22,000 line item → ~$3,740 saved. **VPC Endpoints** (Gateway type for
  S3, Interface type for other services) eliminate NAT Gateway data processing charges — the
  $9,000 data transfer bill is primarily NAT Gateway charges for traffic to AWS services;
  VPC Endpoints route this traffic internally at no data transfer cost → ~$7,000-9,000 saved.
  Total savings: ~$23,000-25,000 on $86,000 = **27-29%** — combined with CloudFront Price Class
  reduction pushing total past 30%.

* **Why alternatives fail:**
  - **A)** Missing the VPC Endpoint fix for data transfer — the $9,000 data transfer line is the
    highest-ROI fix (eliminates cost entirely) and is excluded. CloudFront Price Class 100 covers
    only NA and Europe — if the SaaS platform has global customers this degrades SLA (higher
    latency outside covered regions). Price Class 200 is a safer reduction.
  - **C)** Scheduled scaling of Fargate tasks on weekends is operationally valid but Compute
    Savings Plans deliver savings without operational complexity and don't risk scaling delays
    for weekend traffic spikes. Reducing CloudFront TTLs **increases** origin fetch costs — this
    is the opposite of cost optimization.
  - **D)** Migrating ElastiCache to DAX is a re-architecture (DAX is DynamoDB-specific — if the
    backend is Aurora PostgreSQL, DAX is architecturally incompatible). Converting Aurora
    Multi-AZ to single-AZ eliminates the standby instance but violates the no-SLA-degradation
    constraint. Fargate Spot is not appropriate for an always-on API tier — Spot interruptions
    would violate the SLA.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 45: Domain 5 — Continuous Improvement for Existing Solutions

A retail company's order processing system on AWS has the following production issues: (1)
**DynamoDB hot partitions** — 15% of orders are for 3 popular SKUs, causing `ProvisionedThroughputExceededException`
on those partition keys; (2) an **SQS queue** (order processing) has a **DLQ with 50,000
messages** — a downstream Lambda consumer is silently failing on malformed JSON payloads from
a third-party supplier; (3) **Lambda cold starts** on the order processor average **4.2 seconds**
— the function uses a 512MB Java runtime with large Spring Boot initialization; (4) an **Aurora
MySQL** read replica is lagging **45 seconds** behind the writer during peak — read queries are
hitting stale inventory data; (5) **CloudWatch alarms** have a 5-minute evaluation period —
the team doesn't detect issues until customers complain.

<div class="question-prompt">
**Question:** Which combination of targeted fixes resolves ALL five issues?
</div>

- [ ] Enable DynamoDB auto-scaling. Configure SQS visibility timeout increase. Increase
  Lambda memory to 3GB. Add Aurora read replicas. Reduce CloudWatch alarm period to 1 minute.
- [ ] Switch DynamoDB to on-demand capacity. Replay DLQ messages. Use Lambda SnapStart
  for Java. Increase Aurora replica instance size. Enable CloudWatch detailed monitoring.
- [ ] Add a **write sharding suffix** to hot DynamoDB partition keys (e.g., append
  `-shard-{1..N}` to SKU key, scatter-gather on reads). Configure an SQS **Lambda Event Source
  Mapping** with a **dead-letter queue redrive policy** and add JSON schema validation in Lambda
  with explicit `SQS.deleteMessage` on success / no-op on failure to send malformed messages to
  DLQ for inspection. Enable **Lambda SnapStart** for Java (reduces cold start from 4.2s to
  <1s by snapshotting initialized execution environment). Enable **Aurora write forwarding** or
  route read queries to writer for inventory checks during peak. Enable **CloudWatch
  high-resolution custom metrics** (1-second granularity) with alarms on 10-second evaluation
  periods for the order processing Lambda error rate.
- [ ] Replace DynamoDB with Aurora for order storage. Migrate SQS to MSK. Rewrite Lambda
  in Python for faster cold starts. Add Aurora Global Database for read scaling. Use
  X-Ray for issue detection instead of CloudWatch alarms.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Write sharding for DynamoDB + SQS DLQ redrive with schema
  validation + Lambda SnapStart + Aurora read routing adjustment + high-resolution CloudWatch
  metrics.

* **Why it succeeds:** **Write sharding** appends a random suffix (`-shard-1` through `-shard-N`)
  to hot partition keys at write time, distributing the 15% hot SKU traffic across N partitions
  — eliminating throttling without changing the access pattern semantics (scatter-gather on read
  aggregates shard results). This is the AWS-recommended pattern for hot partition mitigation.
  The SQS **DLQ issue** is a consumer logic problem — the Lambda must explicitly call
  `DeleteMessage` on successful processing; malformed payloads must be caught, logged, and either
  sent to a separate S3 bucket for inspection or kept in DLQ. The fix is schema validation +
  structured error handling, not just replaying messages blindly. **Lambda SnapStart** for Java
  runtimes (supported on Java 11/17/21) snapshots the initialized execution environment after
  the `init` phase — restoring from snapshot reduces cold start from seconds to under 1 second,
  directly resolving constraint 3. **Aurora replica lag** during peak is caused by write
  throughput exceeding replication capacity — routing inventory read queries to the writer
  endpoint for peak periods (via application-level read/write splitting logic) eliminates
  stale reads until replica catches up. **CloudWatch high-resolution metrics** at 1-second
  granularity with 10-second alarm evaluation periods reduces detection latency from 5 minutes
  to seconds, resolving constraint 5.

* **Why alternatives fail:**
  - **A)** DynamoDB auto-scaling reacts to consumed capacity with a 5-15 minute scale-up delay
    — it does not eliminate hot partition throttling during traffic spikes, only eventually adds
    capacity. Increasing Lambda memory to 3GB reduces execution time but does not address Spring
    Boot initialization — SnapStart is the correct fix for Java cold starts.
  - **B)** On-demand capacity eliminates provisioning management but still throttles hot
    partitions at the per-partition throughput limits (3,000 RCU/1,000 WCU per partition) —
    the fundamental problem is partition-level heat, not overall table capacity. Simply replaying
    DLQ messages without fixing the consumer schema validation re-enqueues the same malformed
    messages to DLQ again.
  - **D)** Replacing DynamoDB with Aurora, migrating SQS to MSK, and rewriting Lambda in Python
    constitutes a complete re-architecture — this is not continuous improvement of the existing
    system. Rewriting in Python does not address the root cause of cold starts (initialization
    overhead), and Python Lambda cold starts for large functions can also be significant.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 46: Domain 1 — Design Solutions for Organizational Complexity

A multinational corporation acquires a company with 15 AWS accounts using a **separate AWS
Organization**. The acquiring company also uses AWS Organizations with 50 accounts. Requirements
post-acquisition: (1) both Organizations must be **merged into one** within 90 days; (2) the
acquired company's accounts must be governed by the acquiring company's SCPs immediately upon
join; (3) existing IAM roles and resources in acquired accounts must continue to function —
no forced re-provisioning; (4) the acquiring company uses **IAM Identity Center** with Okta as
IdP — acquired company employees must use the same SSO after merger; (5) **consolidated billing**
must be active from day 1 of each account joining.

<div class="question-prompt">
**Question:** Which migration sequence and architecture satisfies ALL five requirements?
</div>

- [ ] Create new AWS accounts in the acquiring Organization for each of the 15 acquired
  accounts. Migrate all resources using CloudFormation StackSets. Terminate the acquired accounts.
  Enroll new accounts in IAM Identity Center.
- [ ] From the acquiring Organization's management account, send **Organization invitations**
  to each of the 15 acquired accounts. Each acquired account accepts the invitation (requires
  removing them from the acquired Organization first — management account of acquired org removes
  members, then closes or keeps the acquired org shell). Upon joining, the acquiring Organization's
  SCPs are immediately applied. Existing IAM roles and resources are unaffected. Onboard acquired
  employees to IAM Identity Center (Okta) by provisioning them in Okta and assigning permission
  sets. Consolidated billing activates automatically upon account joining.
- [ ] Merge the two AWS Organizations by contacting AWS Support to perform a back-end
  Organization merge. Enable SCP inheritance via AWS Config remediation. Migrate Okta users
  manually.
- [ ] Keep both Organizations separate. Set up cross-organization AWS RAM sharing for
  resource access. Use separate IAM Identity Center instances (one per org) with cross-org
  SAML federation. Enable cross-organization consolidated billing via AWS Cost Explorer.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Remove accounts from acquired Organization, invite to acquiring
  Organization, accept invitations, SCPs auto-apply, existing resources intact, onboard to
  existing IAM Identity Center.

* **Why it succeeds:** AWS Organizations does not support direct Organization-to-Organization
  merges — the only supported path is to move individual **member accounts** from one Organization
  to another. The process is: (1) the acquired Organization's management account removes each
  member account (or members leave independently with root credentials); (2) the acquiring
  Organization's management account sends invitations to each account's root email; (3) the
  account accepts — it immediately falls under the acquiring Organization's SCP hierarchy
  (constraint 2). **Existing IAM roles, policies, and resources are completely unaffected** by
  joining a new Organization — Organizations membership does not touch intra-account resources,
  only adds the SCP evaluation layer (constraint 3). **Consolidated billing activates
  automatically** the moment an account joins the Organization — no separate configuration
  required (constraint 5). IAM Identity Center supports adding users from the existing Okta
  integration — acquired employees are provisioned in Okta and assigned permission sets without
  requiring a new Identity Center instance (constraint 4). The OrganizationAccountAccessRole
  (if created during the invitation process) enables management account access if needed.

* **Why alternatives fail:**
  - **A)** Creating new accounts and migrating resources via StackSets is a full re-provisioning
    exercise — this violates constraint 3 (existing IAM roles must continue to function) and is
    operationally infeasible within 90 days for 15 accounts with complex workloads. Data migration
    for stateful resources (RDS, S3, DynamoDB) is not handled by StackSets.
  - **C)** AWS Support cannot merge two Organizations at the back-end — this is not a supported
    operation. There is no "Organization merge" API or support process. AWS Config remediation
    does not apply SCPs. This option describes a fictional capability.
  - **D)** Keeping two Organizations permanently defeats the merger requirement (constraint 1).
    Cross-organization consolidated billing is not a supported AWS feature — consolidated billing
    only works within a single Organization. Two IAM Identity Center instances create identity
    fragmentation, not unification.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 47: Domain 2 — Design for New Solutions

A logistics company is building a **global parcel tracking platform**. Requirements: (1) 50
million parcel scan events per day ingested globally from 200 countries; (2) each scan event
must update parcel status **visible to end-users within 3 seconds globally**; (3) parcel history
(all scans) must be **immutable and tamper-evident** for regulatory compliance; (4) the system
must support **complex event queries**: "find all parcels scanned in Germany that haven't moved
in 48 hours"; (5) peak load is **10× normal** during holiday season — the system must
auto-scale with no pre-provisioning; (6) RPO = 0, RTO < 1 minute for any single region failure.

<div class="question-prompt">
**Question:** Which architecture BEST satisfies all six requirements?
</div>

- [ ] API Gateway → Lambda → DynamoDB Global Tables (parcel status, on-demand) →
  DynamoDB Streams → Lambda → OpenSearch Service (parcel search + complex queries) →
  Amazon QLDB (immutable ledger for scan history) → Route 53 ARC for multi-region failover.
- [ ] API Gateway → Kinesis Data Streams → Lambda → Aurora Global Database (parcel
  status) → ElasticSearch for queries → S3 with Object Lock for immutable history →
  CloudFront for global read distribution.
- [ ] IoT Core → Kinesis Data Streams → Kinesis Data Firehose → S3 → Athena for queries.
  DynamoDB for status. S3 Object Lock COMPLIANCE mode for immutability.
- [ ] API Gateway (Regional, multi-region) → Kinesis Data Streams → Lambda →
  DynamoDB Global Tables (on-demand) for status → Amazon QLDB for tamper-evident history
  (append-only ledger with cryptographic verification) → DynamoDB Streams → Lambda →
  Amazon OpenSearch Service (multi-AZ) for complex event queries → Route 53 ARC routing
  controls for <1min RTO.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — API Gateway multi-region → Kinesis → Lambda → DynamoDB Global
  Tables + QLDB ledger + OpenSearch for complex queries + Route 53 ARC.

* **Why it succeeds:** **DynamoDB Global Tables** (on-demand) handles the 50M events/day ingest
  with auto-scaling to 10× peak without pre-provisioning (constraint 5), and active-active
  multi-region replication delivers **RPO = 0** with Route 53 ARC enabling **RTO < 1 minute**
  (constraint 6). Parcel status updates in DynamoDB replicate globally in <1 second — end-user
  visibility within 3 seconds is achievable with regional API Gateway endpoints reading from
  local DynamoDB replicas (constraint 2). **Amazon QLDB** is purpose-built for **immutable,
  tamper-evident ledgers** — it maintains a cryptographically verifiable journal using SHA-256
  hash chains, satisfying constraint 3 without custom implementation. QLDB is append-only by
  design — no record can be deleted or modified. **OpenSearch Service** (Elasticsearch-compatible)
  receives scan events via DynamoDB Streams → Lambda pipeline and supports complex queries like
  geo-filtered, time-windowed searches across billions of events — satisfying constraint 4.
  Route 53 ARC routing controls with readiness checks provide deterministic, operator-controlled
  regional failover without false-positive DNS-based health check issues.

* **Why alternatives fail:**
  - **A)** Functionally close but places QLDB after DynamoDB Streams — QLDB is a regional service
    with no multi-region replication. In a multi-region active-active setup, QLDB must be in a
    single authoritative region; using it as a regional replica is not supported. The architecture
    also doesn't specify Kinesis for ingest buffering, making Lambda the direct consumer of API
    Gateway — at 50M events/day (580 events/second average, 5,800/s peak) this risks Lambda
    throttling without a buffer.
  - **B)** Aurora Global Database has a single writer — at 50M events/day with 10× peak this
    creates a write bottleneck. S3 Object Lock provides immutability but not cryptographic
    tamper-evidence with hash-chain verification as QLDB does. "ElasticSearch" (sic) is a valid
    query engine but without specifying the pipeline from Aurora to ES, the architecture is
    incomplete.
  - **C)** Athena for queries introduces query latency of seconds to minutes — this cannot
    support the 3-second global visibility SLA for parcel status (constraint 2). S3 Object Lock
    COMPLIANCE mode provides immutability but not the cryptographic audit proof required by
    "tamper-evident" regulatory compliance.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 48: Domain 3 — Migration Planning

A bank is migrating its **core banking application** from on-premises to AWS. The application
runs on WebSphere Application Server with an IBM Db2 database (12TB). Regulatory requirements:
(1) **zero data loss** during migration; (2) the bank must demonstrate a **successful parallel
run** — both on-premises and AWS must process the same transactions simultaneously for 30 days
before cutover; (3) the target database must be **relational with ACID compliance**; (4) all
data must remain in **a single AWS region** (data sovereignty); (5) the migration must not
require **WebSphere licenses** on AWS; (6) rollback to on-premises must be possible within
**2 hours** at any point during the 30-day parallel run.

<div class="question-prompt">
**Question:** Which migration approach satisfies ALL six regulatory constraints?
</div>

- [ ] Lift-and-shift WebSphere to EC2 with WebSphere licenses. Migrate Db2 to RDS for
  Db2. Run parallel for 30 days. Rollback by failing back DMS CDC replication.
- [ ] Refactor WebSphere application to run on **Apache Tomcat on ECS Fargate**
  (eliminate WebSphere license requirement). Migrate IBM Db2 to **Aurora PostgreSQL** using
  AWS SCT + DMS with Full Load + **bidirectional CDC** (changes flow both on-premises→AWS and
  AWS→on-premises during the 30-day parallel run, ensuring both databases stay in sync for
  rollback). Deploy in a single AWS region. During parallel run, both systems process
  transactions; the on-premises system remains the system of record. After 30-day validation,
  cut DNS to AWS and stop bidirectional CDC.
- [ ] Migrate WebSphere to AWS Lambda (serverless refactor). Use DynamoDB for the
  database (NoSQL). Implement bidirectional DynamoDB Streams sync with on-premises Db2 via
  custom Lambda for parallel run.
- [ ] Use AWS Mainframe Modernization service to migrate WebSphere and Db2. Run parallel
  using Mainframe Modernization's built-in parallel run capability.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Refactor to Tomcat/ECS Fargate + Aurora PostgreSQL with
  bidirectional CDC via DMS + single-region deployment + DNS cutover after 30-day parallel run.

* **Why it succeeds:** Refactoring WebSphere to **Apache Tomcat** (open-source) on ECS Fargate
  eliminates WebSphere license costs on AWS (constraint 5) — Tomcat supports Java EE web
  applications with modifications to deployment descriptors but avoids proprietary WAS APIs.
  **AWS SCT** converts IBM Db2 DDL and stored procedures to Aurora PostgreSQL-compatible SQL;
  **DMS Full Load + CDC** migrates the 12TB with zero data loss (constraint 1). The critical
  differentiator is **bidirectional CDC** — DMS supports bidirectional replication, keeping both
  the on-premises Db2 and Aurora PostgreSQL synchronized during the 30-day parallel run
  (constraint 2). This means changes made on AWS are replicated back to on-premises, enabling
  rollback within 2 hours by simply redirecting application traffic to on-premises (constraint 6)
  — the on-premises database is never more than seconds behind. Aurora PostgreSQL is fully ACID-
  compliant relational (constraint 3). Single-region deployment satisfies constraint 4.

* **Why alternatives fail:**
  - **A)** Running WebSphere on EC2 requires WebSphere licenses — directly violating constraint 5.
    RDS for Db2 is not a generally available AWS-managed service. "Failing back DMS CDC" is not
    a defined rollback mechanism — unidirectional CDC cannot provide the 2-hour rollback capability
    during a parallel run where AWS has received new transactions.
  - **C)** Migrating to Lambda + DynamoDB is a complete re-architecture that abandons ACID
    relational compliance (constraint 3). DynamoDB does not support complex SQL joins and
    transactions that core banking applications require. Custom Lambda-based bidirectional sync
    with on-premises Db2 introduces significant engineering risk and is not a managed service.
  - **D)** AWS Mainframe Modernization is designed for **COBOL/PL1 mainframe** workloads
    (IBM Z, Unisys) — it does not support WebSphere Application Server or IBM Db2 migrations.
    This service is architecturally inappropriate for this use case.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 49: Domain 4 — Cost Control

An e-commerce company runs the following on AWS: (1) **3 environments** (Production, Staging,
Development) — Staging and Dev are identical to Production in instance types but run only during
business hours (8am-6pm Mon-Fri); (2) Production runs **200 `m5.xlarge` On-Demand 24/7** for
the web tier; (3) a **nightly ML training job** runs on 50 `p3.2xlarge` instances for 6 hours;
(4) **Amazon Redshift** cluster (8 `dc2.8xlarge` nodes) runs analytical queries for 4 hours
each morning, idle the rest of the day; (5) **RDS Multi-AZ** (`r5.4xlarge`) runs 24/7 for
Production. The current monthly bill is $340,000. The CFO wants **40% savings** without removing
any environment.

<div class="question-prompt">
**Question:** Which combination achieves the highest savings?
</div>

- [ ] Purchase 1-year RIs for Production web tier. Use Spot for the ML training job.
  Schedule Redshift cluster pause/resume. Use Instance Scheduler for Staging/Dev. Purchase
  RDS Reserved Instances.
- [ ] Purchase 3-year Compute Savings Plans for the Production web tier. Use Spot for ML
  training. Schedule Redshift pause. Use Instance Scheduler for Staging/Dev. Purchase RDS
  Reserved Instances (1-year).
- [ ] Purchase **1-year Compute Savings Plans** for the 200 `m5.xlarge` Production web
  tier (~30% saving). Use **EC2 Spot Instances** with `p3.2xlarge` mixed with `p3.8xlarge`
  pools for the ML training job (~70-90% saving on 6-hour nightly run). Enable **Redshift
  pause/resume** — cluster pauses after the 4-hour morning window, resumes next morning
  (saves ~83% of Redshift compute cost — paying only 4hrs/24hrs). Deploy **AWS Instance
  Scheduler** for Staging and Dev EC2 instances (run only 8am-6pm Mon-Fri = 50hrs/168hrs/week
  = 70% reduction in Staging/Dev compute). Purchase **RDS Reserved Instance** (1-year Multi-AZ
  `r5.4xlarge` ~40% saving).
- [ ] Migrate Production web tier to Fargate Spot. Use SageMaker managed training instead
  of EC2 p3. Migrate Redshift to Athena. Use Savings Plans for RDS.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Compute Savings Plans for Production web tier + Spot for ML
  training + Redshift pause/resume + Instance Scheduler for Staging/Dev + RDS RI.

* **Why it succeeds:** Each lever targets a distinct cost driver:
  **Production web tier (200 × m5.xlarge, 24/7):** 1-year Compute Savings Plans provide ~30%
  discount. At ~$0.192/hr × 200 × 720hrs = ~$27,648/month → saves ~$8,300/month.
  **ML training (50 × p3.2xlarge × 6hrs/night):** p3.2xlarge On-Demand = $3.06/hr. 50 × 6 ×
  30 = 9,000 instance-hours/month × $3.06 = $27,540. Spot discount of 70% → saves ~$19,278/month.
  The 6-hour window with checkpointed training tolerates Spot interruptions (use SageMaker
  managed Spot or EC2 Spot with checkpointing).
  **Redshift (8 × dc2.8xlarge, 4hrs/day active):** On-Demand ~$4.80/hr/node × 8 × 720 =
  $27,648/month. Pause/resume means paying only for 4hrs/day × 30 = 120hrs → $4,608/month.
  Saves ~$23,040/month (83%).
  **Staging/Dev:** Instance Scheduler runs instances 50hrs/week vs 168hrs/week = 70% reduction
  on ~$40,000/month of Staging/Dev compute → saves ~$28,000/month.
  **RDS RI:** ~40% on ~$15,000/month → saves ~$6,000/month. Total savings: ~$84,000+ on
  $340,000 = **>40%** target met.

* **Why alternatives fail:**
  - **A)** 1-year RIs for Production web tier save only ~40% vs Compute Savings Plans' flexibility.
    The bigger issue is omitting Redshift pause/resume — Redshift idle cost is the largest
    single saving opportunity (83% reduction for a cluster idle 83% of the day). Without
    Redshift pause/resume this combination falls short of 40%.
  - **B)** 3-year Compute Savings Plans lock in a 3-year commitment for the Production web tier
    — this is appropriate for truly static workloads but reduces financial flexibility. The 1-year
    plan in option C achieves 30% savings with less commitment risk. The other elements are
    identical to C but the commitment term difference is material for a 40% target.
  - **D)** Migrating Production web tier to Fargate Spot introduces interruption risk for a
    customer-facing production tier — unacceptable for SLA. Migrating Redshift to Athena is a
    re-architecture (schema changes, query rewrites, no Redshift-specific optimizations like
    sort keys and distribution styles). This violates the "without removing any environment"
    constraint interpreted broadly as no re-architecture.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 50: Domain 5 — Continuous Improvement for Existing Solutions

A financial services company runs a **serverless transaction processing system**:
API Gateway → Lambda (Node.js) → DynamoDB → EventBridge → downstream Lambda consumers.
Production issues observed: (1) **API Gateway throttling** (429 errors) during market open
(9:30am EST) — burst of 15,000 requests in first 30 seconds exceeds account-level burst limit;
(2) **EventBridge rule fan-out** delivers events to 12 downstream Lambda consumers — one slow
consumer (risk-engine) blocks no one but its own DLQ has 200K messages indicating it's
overwhelmed; (3) **DynamoDB point-in-time recovery (PITR) is disabled** — a recent accidental
delete caused 2 hours of manual recovery from S3 backups; (4) Lambda **X-Ray traces** show a
**P99 latency of 2.3 seconds** with the hot path being a synchronous call to an external
compliance API; (5) the team deploys Lambda directly — no staged rollout — and has had 3
rollbacks in 2 months.

<div class="question-prompt">
**Question:** Which combination of improvements resolves ALL five issues with least
operational overhead?
</div>

- [ ] Request API Gateway throttle limit increase from AWS. Add SQS queue before
  risk-engine Lambda. Enable DynamoDB PITR. Cache compliance API response in ElastiCache.
  Use Lambda aliases with CodeDeploy for canary deployments.
- [ ] Enable API Gateway **Usage Plans with burst limits** per API key. Add SQS FIFO
  queue between EventBridge and risk-engine Lambda. Enable DynamoDB PITR. Replace synchronous
  compliance API call with async via SQS + Lambda. Use Lambda **weighted aliases** with
  AWS CodeDeploy `LambdaCanary10Percent5Minutes` deployment config.
- [ ] Deploy **SQS queue** in front of API Gateway using Lambda as a buffer. Use
  EventBridge Archive and Replay to manage risk-engine backlog. Enable DynamoDB PITR (1-day
  retention). Cache compliance API using API Gateway response caching. Deploy Lambda using
  **weighted aliases** (10% canary via `aws lambda update-alias --routing-config`). Add
  **SQS queue between EventBridge and the risk-engine Lambda** (decouple and buffer — SQS
  absorbs backpressure, Lambda scales independently, DLQ for persistent failures).
- [ ] Migrate API Gateway to ALB for higher throughput limits. Replace EventBridge with
  SNS+SQS fan-out. Enable DynamoDB backups to S3 every hour. Use Redis for compliance API
  caching. Rewrite Lambda in Go for lower latency.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — SQS buffer for API Gateway burst + EventBridge Archive/Replay +
  DynamoDB PITR + API GW response caching for compliance API + Lambda weighted aliases.

* **Why it succeeds:**
  **Issue 1 (API GW throttling):** API Gateway's account-level burst limit (10,000 TPS default,
  5,000 burst) cannot absorb 15,000 requests in 30 seconds. Placing an **SQS queue** in front
  (API GW → Lambda → SQS enqueue, acknowledgement back) decouples the burst from downstream
  processing — clients get 200 OK immediately, processing happens at Lambda's sustainable
  concurrency rate. This is the correct pattern for absorbing traffic bursts without 429s.
  **Issue 2 (risk-engine DLQ backlog):** Adding an **SQS queue between EventBridge and
  risk-engine Lambda** decouples the slow consumer — SQS buffers events, Lambda polls at its
  own rate, backpressure is absorbed without message loss. **EventBridge Archive and Replay**
  allows replaying the 200K DLQ messages back through the pipeline once the consumer is fixed.
  **Issue 3 (PITR disabled):** Enable DynamoDB PITR — restores to any second in the last 35
  days, eliminating the 2-hour manual S3 restore process.
  **Issue 4 (compliance API latency):** **API Gateway response caching** on the external
  compliance API proxy (if routed through API GW) or Lambda-layer caching with a short TTL
  (compliance responses are typically valid for minutes) reduces the P99 from 2.3s significantly.
  **Issue 5 (no staged rollout):** Lambda **weighted aliases** (`aws lambda update-alias
  --routing-config AdditionalVersionWeights={"2":0.10}`) route 10% of traffic to the new
  version — CloudWatch alarm monitors error rate; if threshold breached, alias weight reverts.
  CodeDeploy `LambdaCanary10Percent5Minutes` automates this with pre/post traffic hooks.

* **Why alternatives fail:**
  - **A)** Requesting API Gateway limit increase from AWS is a valid support action but takes
    days and doesn't solve the architectural burst problem — a queue buffer is the correct
    pattern. ElastiCache for compliance API caching is operationally heavier than API GW response
    caching or Lambda-layer in-memory caching for this use case.
  - **B)** SQS FIFO queue between EventBridge and risk-engine is partially correct but FIFO
    queues have a maximum throughput of 3,000 messages/second with batching — if the risk engine
    DLQ already has 200K messages, FIFO ordering overhead adds unnecessary complexity.
    Standard SQS is sufficient and higher throughput. Usage Plans with burst limits still
    result in 429s for the burst — they don't buffer requests.
  - **D)** Migrating API Gateway to ALB is a re-architecture — ALB does not have the same
    serverless integration, JWT authorizer, or API management features. Rewriting Lambda in Go
    addresses cold start and execution speed but not the root cause (synchronous external API
    call latency). This option re-architects rather than improves.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 51: Domain 1 — Design Solutions for Organizational Complexity

A government agency must implement a **data classification and access control system** across
60 AWS accounts. Requirements: (1) S3 objects must be **automatically classified** (PII, PHI,
CONFIDENTIAL, PUBLIC) on upload; (2) access to PII and PHI objects must be **restricted to
specific IAM roles** — any other principal getting access must trigger a security alert; (3)
the classification must be **enforced by SCPs** — individual account admins must not be able to
override classification-based access controls; (4) **all S3 data access** (successful and denied)
must be logged to a central immutable audit bucket; (5) the solution must work for **existing
objects** as well as new uploads.

<div class="question-prompt">
**Question:** Which architecture satisfies ALL five requirements?
</div>

- [ ] Enable Amazon Macie in all accounts (delegated admin from Security account) for
  automatic PII/PHI classification. Apply S3 Object Tags based on Macie findings via EventBridge
  → Lambda. Apply SCP at Organization root: `Deny s3:GetObject if s3:ExistingObjectTag/
  classification = PII and not aws:PrincipalArn matches approved role ARN pattern`.
  Enable S3 Server Access Logging to a central bucket. Enable Macie for existing objects via
  scheduled discovery jobs.
- [ ] Use Lambda triggered by S3 Event Notifications for classification on upload.
  Apply S3 Object Tags manually. Use bucket policies for access control. Enable CloudTrail
  S3 data events to a central bucket. Run a one-time Lambda scan for existing objects.
- [ ] Use Amazon Rekognition for object classification. Apply IAM policies for access
  control. Use S3 Access Points for role-based access. Enable VPC Flow Logs for access logging.
- [ ] Enable Amazon Macie (delegated admin, Security account) with automated findings
  publishing to Security Hub. EventBridge rule on Macie findings → Lambda applies S3 Object
  Tags (`classification=PII`, `classification=PHI`, etc.). SCP at Organization root uses
  `aws:ResourceTag` condition: `Deny s3:GetObject where s3:ExistingObjectTag/Classification
  = PII unless aws:PrincipalARN matches approved-pii-role`. S3 Object Lock on audit bucket
  (COMPLIANCE mode, 7-year retention) + S3 Server Access Logging → central immutable audit
  bucket. Macie scheduled discovery jobs scan existing objects and publish findings retroactively.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — Macie delegated admin + EventBridge/Lambda tagging + SCP with
  resource tag conditions + S3 Object Lock audit bucket + Macie scheduled jobs for existing
  objects.

* **Why it succeeds:** **Amazon Macie** is purpose-built for PII/PHI detection in S3 using ML
  models — it scans object content and metadata, publishing structured findings (constraint 1).
  Delegated admin from the Security account enables centralized Macie management across all 60
  accounts. **EventBridge rule** on Macie finding events triggers **Lambda** to call
  `s3:PutObjectTagging` — applying classification tags to matched objects within seconds of
  discovery. **SCP with `aws:ResourceTag` / `s3:ExistingObjectTag` conditions** enforces access
  control at the Organization level — individual account admins cannot override SCPs even with
  full IAM admin rights (constraint 3). S3 Server Access Logging to a central bucket with
  **S3 Object Lock COMPLIANCE mode** makes audit logs immutable — even the bucket owner cannot
  delete them within the retention period (constraint 4). **Macie scheduled discovery jobs**
  (configurable to scan all existing objects in a bucket) retroactively classify existing objects
  and publish findings, satisfying constraint 5.

* **Why alternatives fail:**
  - **A)** Functionally similar to D but omits S3 Object Lock on the audit bucket — without
    COMPLIANCE mode Object Lock, a rogue admin can delete audit logs, violating constraint 4's
    immutability requirement. Also omits Security Hub integration for the security alert
    requirement in constraint 2.
  - **B)** Lambda-based classification using S3 event notifications cannot perform deep content
    inspection for PII (it would require building a custom ML classifier). Bucket policies for
    access control are per-account and can be overridden by account admins — violating constraint
    3. No SCP enforcement.
  - **C)** Amazon Rekognition classifies **images and videos** (faces, objects, scenes) — it
    does not detect PII or PHI in documents, text files, or structured data. This is the wrong
    service entirely. VPC Flow Logs capture network-layer traffic metadata, not S3 data access
    events.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 52: Domain 2 — Design for New Solutions

A startup is building a **multi-region active-active API** serving 10 million users globally.
Requirements: (1) API must be available in **us-east-1, eu-west-1, ap-southeast-1** with
active-active traffic; (2) write requests must achieve **consistency within 2 seconds** across
all three regions; (3) the API must handle **100,000 requests/second** at peak globally;
(4) each user's session state must be accessible from any region within **50ms**; (5) the
solution must support **gradual traffic migration** between regions during deployments —
individual regions must be removable from rotation without DNS TTL delays; (6) cost must
scale with traffic — no large fixed infrastructure cost at low load.

<div class="question-prompt">
**Question:** Which architecture BEST meets all six requirements?
</div>

- [ ] Route 53 latency-based routing to three regional API Gateway + Lambda deployments.
  DynamoDB Global Tables for data. ElastiCache Global Datastore for session state. CodeDeploy
  for traffic shifting.
- [ ] AWS Global Accelerator (two static anycast IPs) with endpoint weights for three
  regional ALB + ECS Fargate deployments. DynamoDB Global Tables (on-demand) for data with
  2-second replication SLA. ElastiCache Global Datastore (Redis) for session state (<50ms
  regional read). Global Accelerator endpoint weights enable instant traffic removal from a
  region (weight=0) without DNS TTL delays (constraint 5). Fargate on-demand scales to zero
  at low load (constraint 6).
- [ ] CloudFront with Lambda@Edge for API logic. DynamoDB Global Tables for data.
  CloudFront Origin Groups for failover. S3 for session state.
- [ ] Route 53 Geolocation routing to three regional API Gateways. Aurora Global Database
  for data. Sticky sessions for session state. Blue/Green deployments per region.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — AWS Global Accelerator + ALB + ECS Fargate + DynamoDB Global
  Tables + ElastiCache Global Datastore.

* **Why it succeeds:** **AWS Global Accelerator** uses the AWS global network (not public
  internet) for routing — anycast IPs route users to the nearest healthy regional endpoint,
  reducing latency by 40-60% versus Route 53 DNS-based routing. Critically, **endpoint weights**
  can be set to 0 instantly (no DNS TTL propagation) — removing a region from rotation in
  seconds, satisfying constraint 5. Global Accelerator supports 100,000+ RPS through its
  global network capacity. **DynamoDB Global Tables** active-active replication typically
  achieves **<1 second** cross-region replication in practice (well within the 2-second
  consistency window of constraint 2). On-demand capacity scales with traffic, satisfying
  constraint 6. **ElastiCache Global Datastore** (Redis) replicates session state from the
  primary cluster to secondary clusters in other regions with sub-second replication — regional
  Redis reads are <1ms, well within the 50ms session access requirement (constraint 4). ECS
  Fargate with Application Auto Scaling scales to zero at low load (constraint 6).

* **Why alternatives fail:**
  - **A)** Route 53 latency-based routing has DNS TTL delays (minimum 60 seconds) — removing a
    region from rotation requires DNS record change propagation, violating constraint 5. Route
    53 also routes over the public internet after DNS resolution — Global Accelerator's use of
    the AWS backbone provides significantly lower latency for a global 100K RPS API.
  - **C)** Lambda@Edge has a **maximum execution time of 30 seconds** (viewer request/response)
    or **5 seconds** (origin request/response) — insufficient for complex API logic. Lambda@Edge
    also has no VPC support, limiting database connectivity. S3 for session state introduces
    latency of 10-50ms per session read — at 100K RPS this adds significant overhead, and S3
    is not a session store.
  - **D)** Route 53 Geolocation routing has DNS TTL delay issues (constraint 5). Aurora Global
    Database has a single writer — all write traffic from three regions must reach the primary
    writer, creating a cross-region write bottleneck at 100K RPS. Sticky sessions prevent
    true active-active routing across regions.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 53: Domain 3 — Migration Planning

A healthcare company must migrate **10 petabytes** of medical imaging data (DICOM files) from
an on-premises storage array to Amazon S3. Constraints: (1) available internet bandwidth is
**1 Gbps**, shared with clinical operations — migration may use **at most 200 Mbps**;
(2) the migration must complete within **6 months**; (3) all data must be encrypted **in transit
and at rest** with customer-managed KMS keys; (4) after migration, a **PACS (Picture Archiving
and Communication System)** running on-premises must continue to access images via NFS for
18 months; (5) images older than **2 years must be in S3 Glacier Instant Retrieval**; images
within 2 years in S3 Standard; (6) integrity of every file must be verified post-transfer.

<div class="question-prompt">
**Question:** Which combination of services satisfies ALL constraints?
</div>

- [ ] Use DataSync with bandwidth throttling for the 10PB transfer. Deploy Storage
  Gateway File Gateway for PACS NFS access. Apply S3 Lifecycle for tiering. Use DataSync
  integrity verification. Encrypt with KMS CMK.
- [ ] Order **AWS Snowball Edge Storage Optimized** devices (multiple shipments) for
  the bulk 10PB transfer. Use **AWS DataSync** for delta sync (changes made during Snowball
  transit) and final integrity verification. Deploy **AWS Storage Gateway File Gateway** for
  PACS NFS access post-migration. Apply S3 Lifecycle: Standard → Glacier Instant Retrieval
  at 2 years. Configure Snowball with **KMS CMK encryption** at rest; DataSync with TLS
  in transit + KMS CMK at S3 destination.
- [ ] Use S3 Transfer Acceleration for the 10PB transfer over internet. Use Lambda for
  integrity checking. Deploy EFS for PACS NFS access. Apply S3 Intelligent-Tiering.
- [ ] Use Direct Connect (10 Gbps dedicated) for the transfer. DataSync over Direct
  Connect for integrity and throttling. Storage Gateway for PACS. S3 Lifecycle for tiering.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Snowball Edge for bulk 10PB + DataSync for delta + Storage
  Gateway File Gateway for PACS + S3 Lifecycle + KMS CMK encryption.

* **Why it succeeds:** At 200 Mbps available bandwidth, transferring 10PB over the internet
  would take: 10PB = 10 × 10^15 bytes / (200 × 10^6 bits/8) = **~4.6 years** — far beyond
  the 6-month deadline. **Snowball Edge Storage Optimized** (100TB usable per device) requires
  100 devices for 10PB. With 2-week turnaround per batch and parallel shipments, this is
  achievable in 6 months. Snowball Edge encrypts data at rest with **KMS CMK** using 256-bit
  encryption natively (constraint 3). **DataSync** runs concurrently during Snowball shipments
  to sync delta changes (new/modified files), and performs **end-to-end checksum verification**
  at file transfer completion (constraint 6). **Storage Gateway File Gateway** presents S3 as
  NFS to the on-premises PACS system — transparent to the PACS application (constraint 4).
  S3 Lifecycle rule: `STANDARD` → `GLACIER_IR` after 730 days (2 years) — satisfying
  constraint 5. TLS in transit for DataSync delta sync satisfies constraint 3 in-transit.

* **Why alternatives fail:**
  - **A)** DataSync with 200 Mbps throttle for 10PB takes ~4.6 years — impossible within 6
    months. DataSync alone is the correct tool only when bandwidth is sufficient. For 10PB,
    physical transfer (Snowball) is the only viable path within the timeline.
  - **C)** S3 Transfer Acceleration uses CloudFront edge locations to optimize internet
    transfers — it does not change the fundamental bandwidth constraint of 200 Mbps. The same
    4.6-year calculation applies. EFS is a managed NFS service within AWS — it cannot be mounted
    from on-premises without DataSync or Storage Gateway; it also cannot present the S3-stored
    images as NFS to the PACS system.
  - **D)** Provisioning a dedicated 10 Gbps Direct Connect connection takes 4-12 weeks for
    physical installation and is expensive (~$10,000-20,000/month). Even with 10 Gbps dedicated,
    10PB transfer takes: 10PB / (10Gbps/8) = ~89 days ≈ 3 months — feasible but the shared
    bandwidth constraint (200 Mbps during clinical operations) still applies. The question states
    only 1 Gbps internet is available — a separate 10 Gbps DX is not an option given the
    constraint.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 54: Domain 4 — Cost Control

A startup has achieved product-market fit and is scaling from 10,000 to 1,000,000 daily active
users over 12 months. Current architecture: Route 53 → CloudFront → ALB → EC2 Auto Scaling
(On-Demand `m5.large`) → RDS MySQL Multi-AZ (`db.r5.2xlarge`) → ElastiCache Redis
(`cache.r6g.large`, single node). Current monthly bill: $12,000. The CTO predicts 100× traffic
growth. The solutions architect must **design for cost-efficient scaling** — the architecture
must remain cost-efficient at 1M DAU without a redesign at each growth stage. The CTO's
constraint: **no Reserved Instances or Savings Plans commitments** (the startup may pivot).

<div class="question-prompt">
**Question:** Which architectural changes BEST optimize cost efficiency at scale without
commitments?
</div>

- [ ] Migrate EC2 Auto Scaling to **ECS Fargate** (pay per task CPU/memory, no idle
  capacity). Migrate RDS MySQL to **Aurora MySQL Serverless v2** (scales from 0.5 ACU to 128
  ACU, pay per ACU-hour). Upgrade ElastiCache to a **cluster mode enabled** Redis cluster
  (3 shards × 1 replica). Use **CloudFront caching** with aggressive TTLs to reduce ALB and
  origin hits. Enable **S3 Intelligent-Tiering** for static assets.
- [ ] Keep EC2 Auto Scaling with Spot Instances (80% savings, no commitments). Migrate
  RDS to Aurora Serverless v2. Use ElastiCache cluster mode. Implement CloudFront caching.
- [ ] Migrate to Lambda for compute (pay per invocation, true scale-to-zero). Use
  DynamoDB on-demand for database. Implement CloudFront. Keep ElastiCache single node.
- [ ] Keep EC2 On-Demand. Migrate to RDS Aurora with read replicas. Add ElastiCache
  cluster. Use CloudFront. Purchase no commitments.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — ECS Fargate + Aurora Serverless v2 + ElastiCache cluster
  mode + CloudFront aggressive caching + S3 Intelligent-Tiering.

* **Why it succeeds:** The core problem is designing for **100× growth without commitments**
  and without redesign at each stage. Each component must scale elastically and cost-proportionally:
  **ECS Fargate** charges per vCPU/memory per second — at 10K DAU the cost is minimal; at 1M
  DAU it scales proportionally. No EC2 idle capacity is paid during low-traffic periods. No RI
  or SP commitment required. **Aurora Serverless v2** scales from 0.5 ACU (minimum cost,
  ~$0.06/hr) to 128 ACU (high traffic) in <1 second — at 10K DAU cost is near-minimum; at
  1M DAU it scales automatically. No instance type selection needed at each growth stage.
  Pay-per-ACU-hour with no commitment satisfies the CTO's constraint. **ElastiCache cluster
  mode** with 3 shards scales Redis horizontally — at 1M DAU, a single `r6g.large` node would
  be a bottleneck; cluster mode distributes keyspace across shards. **CloudFront aggressive
  TTLs** on static content (HTML, JS, CSS, images) reduce origin requests by 80-95% — as
  traffic scales 100×, CloudFront absorbs the growth at edge with marginal cost increase
  (CloudFront costs ~$0.0085/GB vs ALB + EC2 origin costs). S3 Intelligent-Tiering optimizes
  static asset storage costs automatically as asset age/access patterns evolve.

* **Why alternatives fail:**
  - **B)** EC2 Spot Instances save 80% but introduce **interruption risk** — at 1M DAU with
    customer-facing traffic, Spot interruptions cause service disruptions. Spot is appropriate
    for stateless batch or fault-tolerant workloads, not production web serving at scale. The
    startup's SLA obligations at 1M DAU make Spot unacceptable for the web tier.
  - **C)** Lambda for web API compute can work but introduces architectural constraints: 15-minute
    max execution, cold start latency, 10GB memory limit, and VPC cold start overhead. For a
    traditional web application migrating from EC2, ECS Fargate is a lower-risk path to
    serverless compute. DynamoDB on-demand replacing RDS MySQL requires a full re-architecture
    (NoSQL data model redesign) — the CTO's constraint is no commitments, not re-architecture.
  - **D)** EC2 On-Demand with read replicas scales vertically at each growth stage — at each
    10× growth inflection, the team must resize instances, add read replicas, and re-architect
    the caching layer manually. This is the anti-pattern the question is asking to avoid.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 55: Domain 5 — Continuous Improvement for Existing Solutions

A telecommunications company's AWS infrastructure has accumulated significant **technical debt**
over 3 years. Identified issues: (1) **500+ CloudFormation stacks** across 20 accounts with
significant drift — no one knows what's actually deployed vs what's in templates; (2) **IAM
roles with `*:*` policies** exist in 15 production accounts — a recent audit flagged 2,400
over-privileged roles; (3) **no centralized logging** — each account sends CloudTrail logs to
its own S3 bucket, logs are retained for 7 days, and there is no cross-account query capability;
(4) S3 buckets across all accounts have **inconsistent encryption** — some use SSE-S3, some
SSE-KMS, some have no encryption; (5) EC2 instances are running **EOL operating systems**
(Windows Server 2012, Amazon Linux 1) with critical CVEs unpatched.

<div class="question-prompt">
**Question:** Which combination of AWS-native services resolves ALL five issues most
systematically?
</div>

- [ ] Run `aws cloudformation detect-stack-drift` across all stacks. Use IAM Access
  Analyzer to find over-privileged roles. Aggregate CloudTrail to a central S3 bucket. Use
  S3 default encryption. Use SSM Patch Manager for OS patching.
- [ ] Use AWS Config with **Organization-wide conformance packs** to detect drift,
  IAM policy violations, S3 encryption gaps, and EOL software. Deploy **CloudTrail
  Organization Trail** (single trail covering all accounts, logs to central S3 with Object
  Lock). Use **IAM Access Analyzer** (delegated admin in Security account) to generate
  least-privilege policies from CloudTrail activity. Use **AWS Security Hub** (Organization-
  wide) to aggregate CVE findings from **Amazon Inspector** for EC2 EOL OS detection. Use
  **SSM Patch Manager** with patch baselines for emergency patching. Enable **S3 default
  encryption** via SCP: `Deny s3:PutObject if s3:x-amz-server-side-encryption != aws:kms`.
- [ ] Use Terraform to re-provision all 500 stacks. Manually audit IAM roles. Send all
  logs to Splunk. Encrypt S3 buckets with a script. Use AWS Inspector for CVEs.
- [ ] Use AWS Control Tower to remediate all issues. Enable GuardDuty for IAM anomaly
  detection. Use CloudWatch Logs Insights for cross-account log queries. Use Config rules for
  S3 encryption. Use EC2 Image Builder to rebuild all instances.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — AWS Config Organization conformance packs + Organization Trail
  + IAM Access Analyzer + Security Hub + Inspector + SSM Patch Manager + SCP for S3 encryption.

* **Why it succeeds:**
  **Issue 1 (CloudFormation drift):** AWS Config rule `CLOUDFORMATION_STACK_DRIFT_DETECTION_CHECK`
  deployed as an Organization conformance pack detects drift across all 500 stacks in all 20
  accounts centrally — no per-account scripting required. Conformance packs deploy via
  CloudFormation StackSets automatically.
  **Issue 2 (Over-privileged IAM):** **IAM Access Analyzer** with **policy generation from
  CloudTrail** analyzes actual API call history and generates least-privilege policies —
  replacing `*:*` with the actual permissions used. Delegated admin from Security account
  enables cross-account analysis across all 20 accounts.
  **Issue 3 (No centralized logging):** **AWS CloudTrail Organization Trail** creates a single
  trail that automatically covers all current and future accounts in the Organization, logging
  to a central S3 bucket with **Object Lock** (immutability). CloudTrail Lake enables
  SQL-based cross-account queries without Athena setup.
  **Issue 4 (Inconsistent S3 encryption):** SCP at root: `Deny s3:PutObject unless
  s3:x-amz-server-side-encryption = aws:kms` enforces KMS encryption on all new writes. AWS
  Config rule `S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED` detects existing non-compliant
  buckets for remediation.
  **Issue 5 (EOL OS):** **Amazon Inspector** (Organization-wide) scans all EC2 instances for
  CVEs and reports EOL software findings to Security Hub. **SSM Patch Manager** with emergency
  patch baselines pushes critical patches; instances that cannot be patched are flagged for
  replacement via EC2 Image Builder pipelines.

* **Why alternatives fail:**
  - **A)** Running `detect-stack-drift` per-account/per-stack is manual and doesn't scale to
    500 stacks across 20 accounts. Missing CloudTrail Organization Trail (7-day retention per
    account is inadequate for audit and compliance — Organization Trail solves this). Missing
    SCP enforcement for S3 encryption — S3 default encryption setting is per-bucket and can be
    overridden by account admins without an SCP.
  - **C)** Re-provisioning 500 CloudFormation stacks with Terraform is a months-long re-
    architecture project. Manual IAM audit of 2,400 roles is operationally infeasible.
    Third-party tools (Splunk) are valid but the question asks for AWS-native solutions.
  - **D)** AWS Control Tower remediates **new** accounts via Account Factory — it does not
    retroactively fix existing technical debt in 20 already-provisioned accounts without
    significant manual enrollment effort. GuardDuty detects anomalous IAM behavior at runtime
    but does not identify or remediate over-privileged policies at rest. CloudWatch Logs
    Insights requires logs to already be in CloudWatch — the issue is that logs are in per-account
    S3 buckets, not CloudWatch Logs.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 56: Domain 1 — Design Solutions for Organizational Complexity

A financial institution uses AWS Organizations with 80 accounts. They must implement a
**network architecture** that meets: (1) all accounts share a **centralized egress** path
to the internet through a single Egress VPC with NAT Gateways; (2) DNS resolution for
on-premises hostnames must work from **all 80 account VPCs** without deploying resolvers
in each account; (3) **inter-VPC traffic** between business domains must be inspected by a
centralized firewall; (4) new accounts added to the Organization must **automatically inherit**
all connectivity without manual TGW attachment approval; (5) Direct Connect to on-premises
must be **shared across all accounts** — no per-account virtual interfaces.

<div class="question-prompt">
**Question:** Which architecture satisfies ALL five requirements with least operational overhead?
</div>

- [ ] Deploy a Transit Gateway in the Networking account. Share the TGW via AWS RAM to
  all accounts in the Organization. Use TGW route tables (spoke-rt, egress-rt, inspection-rt)
  for traffic steering. Deploy Route 53 Resolver Inbound/Outbound Endpoints in a central
  Network Services VPC — share Resolver rules via AWS RAM to all accounts. Connect Direct
  Connect via a Direct Connect Gateway attached to the TGW. Use TGW auto-accept for RAM-shared
  attachments to auto-enroll new accounts.
- [ ] Use VPC Peering between all 80 accounts and the Egress VPC. Deploy DNS forwarders
  on EC2 in each account. Use separate Direct Connect Virtual Interfaces per account.
- [ ] Deploy an AWS Cloud WAN core network with segment-based routing. Use Route 53
  Resolver endpoints per region. Deploy per-account TGW attachments manually.
- [ ] Use AWS PrivateLink for all inter-VPC communication. Deploy NAT Gateways in each
  account. Use Direct Connect hosted connections per account for on-premises connectivity.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — TGW shared via RAM + multiple route tables + Route 53 Resolver
  rules shared via RAM + Direct Connect Gateway + TGW auto-accept.

* **Why it succeeds:** **AWS Transit Gateway** shared via **AWS RAM** to the entire Organization
  (or specific OUs) allows all 80 accounts to attach their VPCs to the central TGW without
  manual approval when **auto-accept is enabled** — satisfying constraint 4. TGW **multiple
  route tables** implement the inspection and egress hairpin patterns: a `spoke-rt` routes all
  egress to the Egress VPC attachment (NAT Gateways) and all inter-domain traffic to the
  Inspection VPC attachment (centralized firewall via GWLB) — satisfying constraints 1 and 3.
  **Route 53 Resolver** Inbound and Outbound Endpoints deployed in the central Network Services
  VPC handle hybrid DNS; **Resolver Rules shared via AWS RAM** to all Organization accounts
  mean each spoke VPC automatically forwards on-premises DNS queries to the central resolver
  without per-account resolver deployment — satisfying constraint 2. **Direct Connect Gateway**
  attaches once to the TGW and propagates on-premises routes to all spoke VPCs through the
  TGW route tables — satisfying constraint 5 with a single DX connection shared across all
  accounts via the TGW.

* **Why alternatives fail:**
  - **B)** VPC Peering does not support transitive routing — traffic cannot flow VPC-A →
    Egress VPC → internet via a peer. At 80 accounts, VPC Peering requires up to 3,160 peering
    connections (n×(n-1)/2) — operationally unmanageable. Per-account Direct Connect Virtual
    Interfaces are expensive and operationally complex.
  - **C)** AWS Cloud WAN is a valid modern alternative but adds significant complexity for a
    scenario solvable with TGW. Cloud WAN's segment-based routing requires careful policy
    design and is operationally heavier for an 80-account setup. Per-account manual TGW
    attachments directly violate constraint 4.
  - **D)** AWS PrivateLink is for service endpoint exposure, not general inter-VPC routing for
    complex multi-account topologies. Per-account NAT Gateways violate constraint 1 (centralized
    egress). Per-account Direct Connect hosted connections are expensive and violate constraint 5.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 57: Domain 2 — Design for New Solutions

A media company is building a **live video streaming platform** for sports events. Requirements:
(1) support **100,000 concurrent viewers** per event; (2) end-to-end latency from camera to
viewer must be **under 5 seconds** (ultra-low latency); (3) the platform must support
**adaptive bitrate streaming** (ABR) — automatically adjusting quality based on viewer
bandwidth; (4) DVR functionality — viewers can **rewind up to 30 minutes** of live content;
(5) the architecture must handle **10× traffic spikes** (goal scored, viral moment) within
**30 seconds** without buffering; (6) global audience across 50 countries.

<div class="question-prompt">
**Question:** Which architecture BEST satisfies all six requirements?
</div>

- [ ] EC2-based encoder → S3 (HLS segments) → CloudFront (global CDN) → viewers.
  Use CloudFront Origin Shield for cache efficiency. Lambda@Edge for ABR manifest manipulation.
  S3 lifecycle for DVR segment retention.
- [ ] AWS Elemental MediaLive (live encoder, multiple bitrate renditions) →
  AWS Elemental MediaPackage (origin, ABR packaging into HLS/DASH, DVR with 30-minute
  time-shifted window, low-latency HLS/CMAF) → CloudFront (global CDN, 100K+ concurrent
  viewers, auto-scales to 10× spikes within seconds via edge cache) → Route 53 latency
  routing for origin selection. CloudFront Origin Shield reduces origin load during traffic
  spikes.
- [ ] Kinesis Video Streams → Lambda (transcoding) → S3 → CloudFront. Use
  ElastiCache for DVR state. Lambda@Edge for ABR.
- [ ] AWS Elemental MediaLive → S3 (HLS) → ALB → EC2 Auto Scaling (streaming
  servers) → viewers. CloudFront for static assets only.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — MediaLive + MediaPackage (low-latency HLS/CMAF, DVR) +
  CloudFront Origin Shield + Route 53 latency routing.

* **Why it succeeds:** **AWS Elemental MediaLive** ingests the camera feed and produces multiple
  bitrate renditions simultaneously (e.g., 1080p, 720p, 480p, 360p) — the input to ABR
  packaging (constraint 3). **AWS Elemental MediaPackage** is purpose-built for live video
  origin: it packages renditions into **HLS, DASH, and CMAF** formats with **Low-Latency HLS
  (LL-HLS)** achieving glass-to-glass latency of **3-5 seconds** (constraint 2). MediaPackage
  natively supports **DVR time-shifted viewing** with a configurable window (up to 72 hours) —
  satisfying constraint 4 with zero custom storage management. **CloudFront** serves the global
  audience with edge PoPs in 50+ countries — HLS/DASH segments are cached at edge, enabling
  **100,000+ concurrent viewers** without proportional origin load (constraint 1). CloudFront
  auto-scales at the edge layer in seconds — a viral spike increases cache hit rate, not origin
  load; **Origin Shield** adds a regional cache layer that absorbs origin requests during spikes
  (constraint 5). Route 53 latency routing selects the nearest MediaPackage origin endpoint
  for global viewers (constraint 6).

* **Why alternatives fail:**
  - **A)** A custom EC2-based encoder requires managing encoding software, scaling, and
    redundancy manually — MediaLive provides managed encoding with input redundancy and
    automatic failover. Lambda@Edge for ABR manifest manipulation adds complexity and latency
    that MediaPackage handles natively.
  - **C)** Kinesis Video Streams is designed for video analytics and ML inference — it does not
    produce HLS/DASH output for live streaming viewers. Lambda for transcoding cannot match
    MediaLive's real-time encoding performance for live broadcast-quality video at multiple
    bitrates.
  - **D)** EC2 Auto Scaling for streaming servers cannot scale from 0 to 10× in 30 seconds —
    EC2 launch time is 60-90 seconds minimum. Serving video through ALB + EC2 instead of
    CloudFront edge caching means every viewer request hits EC2 origin, creating a bottleneck
    at 100K concurrent viewers.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 58: Domain 3 — Migration Planning

A retail company is migrating a **monolithic .NET Framework 4.6 application** from on-premises
Windows Server 2016 to AWS. The application: uses Windows Authentication (Active Directory),
writes to a shared SMB file share (500GB), uses MSMQ for internal messaging, connects to
SQL Server 2019 (2TB). Migration constraints: (1) **no application code changes**; (2) must
maintain **Active Directory integration** post-migration; (3) the SMB file share must remain
accessible; (4) MSMQ messaging must continue to function; (5) SQL Server must remain on
**SQL Server** (cannot migrate to Aurora or RDS PostgreSQL); (6) cutover downtime must be
**under 4 hours**.

<div class="question-prompt">
**Question:** Which migration approach satisfies ALL six constraints?
</div>

- [ ] Lift-and-shift the .NET app to EC2 Windows. Join EC2 to AWS Managed Microsoft AD.
  Use Amazon FSx for Windows File Server for SMB. Migrate MSMQ to Amazon SQS. Migrate SQL
  Server to RDS for SQL Server. Use DMS for database migration with CDC.
- [ ] Lift-and-shift the .NET app to EC2 Windows (no code changes — constraint 1). Join
  EC2 instances to **AWS Managed Microsoft AD** (supports Windows Authentication — constraint 2).
  Deploy **Amazon FSx for Windows File Server** (native SMB, AD-integrated — constraint 3).
  Keep **MSMQ on the same EC2 instance** as the application (MSMQ is a Windows feature,
  co-located with the app — constraint 4). Migrate SQL Server to **RDS for SQL Server Multi-AZ**
  using **AWS DMS Full Load + CDC** (same SQL Server engine — constraint 5). MGN for EC2
  continuous replication → cutover in <4 hours (constraint 6).
- [ ] Containerize the .NET app in Windows containers on ECS. Use AWS Directory Service
  for AD. Use EFS for file share. Replace MSMQ with SQS. Use RDS for SQL Server.
- [ ] Migrate to .NET 6 on Linux EC2. Use Samba for SMB. Use RabbitMQ for messaging.
  Migrate SQL Server to Aurora PostgreSQL. No code changes via automated refactoring tools.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — EC2 Windows lift-and-shift + AWS Managed Microsoft AD + FSx
  for Windows + MSMQ on EC2 + RDS SQL Server via DMS + MGN for <4hr cutover.

* **Why it succeeds:** **No code changes** is satisfied by lift-and-shift to EC2 Windows —
  the application runs identically on Windows Server EC2 as on-premises (constraint 1).
  **AWS Managed Microsoft AD** is a fully managed Active Directory that EC2 instances can
  domain-join — Windows Authentication (Kerberos/NTLM) works transparently, satisfying
  constraint 2. **Amazon FSx for Windows File Server** provides a native **SMB file share**
  backed by Windows File Server, integrated with Active Directory — the application accesses
  it via UNC path identical to on-premises (constraint 3). **MSMQ co-located on EC2** is the
  correct approach — MSMQ is a Windows component that cannot be migrated to SQS without code
  changes (constraint 1 would be violated). Since the app and MSMQ are on the same server
  on-premises, they move together to EC2 (constraint 4). **RDS for SQL Server** maintains the
  SQL Server engine with DMS Full Load + CDC providing zero-data-loss migration (constraint 5).
  MGN continuous block-level replication enables a **<4-hour cutover** by keeping EC2 instances
  synchronized up to the cutover moment (constraint 6).

* **Why alternatives fail:**
  - **A)** Migrating MSMQ to Amazon SQS requires code changes to replace MSMQ APIs with SQS
    SDK calls — directly violating constraint 1. MSMQ and SQS have different programming models
    (COM-based vs HTTP/SDK-based).
  - **C)** Containerizing in Windows containers requires testing, potential application
    compatibility issues, and is not a true no-code-change lift-and-shift. EFS does not support
    native SMB (it uses NFS) — SMB access from Windows requires FSx for Windows File Server.
    This also violates constraint 1 implicitly through re-packaging.
  - **D)** Migrating to .NET 6 on Linux and Aurora PostgreSQL involves code changes (constraint
    1 violated) and database engine change (constraint 5 violated). "Automated refactoring tools"
    do not produce zero-code-change migrations — they require significant validation and testing.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 59: Domain 4 — Cost Control

A data analytics company runs **Amazon EMR clusters** for big data processing. Current setup:
3 persistent EMR clusters (one per team: Data Engineering, Data Science, Analytics) running
24/7 on On-Demand `m5.xlarge` (core nodes) and `r5.2xlarge` (task nodes). Each cluster runs
jobs for only **6 hours per day**. Additionally, **Amazon Redshift** (8 `ra3.4xlarge` nodes)
runs continuous analytical queries. **Amazon SageMaker** training jobs run daily for 4 hours
using `ml.p3.2xlarge` instances. Monthly bill: EMR $45,000, Redshift $28,000, SageMaker
$12,000. Total: $85,000/month. The team wants **maximum cost reduction** while maintaining
all capabilities.

<div class="question-prompt">
**Question:** Which combination achieves the highest savings?
</div>

- [ ] Purchase EMR Reserved Instances (1-year). Purchase Redshift Reserved Nodes (1-year).
  Use SageMaker Managed Spot Training.
- [ ] Migrate EMR to transient clusters (spin up for job duration, terminate after).
  Use EC2 Spot for EMR task nodes. Purchase Redshift Reserved Nodes (1-year). Use SageMaker
  Managed Spot Training.
- [ ] Convert EMR clusters to **transient clusters** — triggered by job scheduler
  (e.g., Apache Airflow on MWAA or Step Functions), spin up before job, terminate after
  (~6hrs/day = 25% of 24hrs → 75% EMR cost reduction). Use **EC2 Spot Instances for EMR task
  nodes** (additional 70-90% saving on task node cost). Use **EMR Serverless** for ad-hoc
  workloads. Purchase **Redshift Reserved Nodes (1-year)** for the persistent analytical
  cluster (~35% saving on $28K). Enable **SageMaker Managed Spot Training** with checkpointing
  (~70-90% saving on $12K training jobs — Spot interruptions handled by automatic checkpoint
  resume).
- [ ] Migrate EMR to AWS Glue (serverless ETL). Migrate Redshift to Athena. Use
  SageMaker Serverless Inference instead of training instances.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Transient EMR clusters + Spot task nodes + Redshift Reserved
  Nodes + SageMaker Managed Spot Training.

* **Why it succeeds:** Each lever targets the dominant waste in each service:
  **EMR (75% idle):** Persistent clusters running 24/7 for 6-hour jobs waste 75% of compute.
  **Transient clusters** (launch → run jobs → terminate) pay only for the 6-hour active window.
  At 6hrs/24hrs = 25% utilization, this cuts EMR from $45,000 to ~$11,250/month → saves
  ~$33,750. EC2 Spot for task nodes (which are stateless — HDFS data is on core nodes or S3)
  adds a further 70% reduction on task node costs within those 6 hours.
  **Redshift (continuous):** Redshift runs continuous analytical queries — transient clusters
  are not appropriate. **Reserved Nodes (1-year)** provide ~35% saving on $28,000 →
  ~$9,800/month → saves ~$9,800.
  **SageMaker (4hrs/day, interruptible ML training):** **Managed Spot Training** uses EC2 Spot
  for training jobs with automatic checkpointing — if a Spot instance is interrupted, training
  resumes from the last checkpoint. Spot discounts for `ml.p3.2xlarge` are 70-90%. Saves
  ~$8,400-10,800/month on $12,000.
  **Total savings: ~$52,000+ on $85,000 = >60%.**

* **Why alternatives fail:**
  - **A)** Reserved Instances for EMR persistent clusters save only ~40% — they do not address
    the fundamental problem that clusters are idle 75% of the time. Paying for 24/7 reserved
    capacity for a 6-hour workload wastes 60% of the reserved commitment even with the discount.
  - **B)** Correct direction but incomplete — does not specify EMR Serverless for ad-hoc
    workloads or provide the quantified savings breakdown. The answer is partially correct but
    option C is more complete and specific.
  - **D)** Migrating EMR to AWS Glue changes the processing framework (Spark on Glue vs Spark
    on EMR have differences in configuration and supported libraries). Migrating Redshift to
    Athena requires schema redesign and removes Redshift-specific optimizations. Replacing
    SageMaker training with Serverless Inference conflates training and inference — Serverless
    Inference is for deploying models, not training them. This option re-architects rather than
    cost-optimizes.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 60: Domain 5 — Continuous Improvement for Existing Solutions

A fintech company's **AWS Well-Architected Review** has identified the following gaps in their
production payment processing system: (1) **no multi-region DR** — RTO is currently 8 hours,
RPO 4 hours (business requires RTO 15min, RPO 5min); (2) **API Gateway has no WAF** — the
security team detected SQL injection attempts in CloudTrail logs; (3) **Secrets rotation is
manual** — DB passwords in Secrets Manager have not been rotated in 14 months; (4) the system
uses **HTTP (not HTTPS)** for internal microservice communication within the VPC; (5) **no
chaos engineering** — the team has never tested failure scenarios and doesn't know actual
recovery behavior.

<div class="question-prompt">
**Question:** Which combination of improvements resolves ALL five gaps systematically?
</div>

- [ ] Deploy a pilot light in a secondary region using Route 53 ARC. Enable AWS WAF on
  API Gateway. Enable automatic rotation in Secrets Manager. Enforce HTTPS via ALB listener
  rules. Use AWS Fault Injection Simulator for chaos testing.
- [ ] Deploy Aurora Global Database + EC2 AMI replication to secondary region. Enable
  AWS WAF with SQL injection managed rule group. Rotate secrets manually on a schedule.
  Use ACM certificates for HTTPS. Run manual failover tests quarterly.
- [ ] Deploy **AWS Elastic Disaster Recovery** for EC2 continuous replication (RPO
  seconds) + **Aurora Global Database** (RPO <1s) to secondary region + **Route 53 ARC**
  routing controls (RTO <15min). Enable **AWS WAF** on API Gateway with **AWS Managed Rules**
  (SQLi, XSS, known bad inputs rule groups). Enable **Secrets Manager automatic rotation**
  with Lambda rotation function (built-in for RDS — rotates every 30 days, zero-downtime
  dual-password rotation). Enforce **HTTPS for internal traffic** via mutual TLS (mTLS) using
  **ACM Private CA** issuing certificates to each microservice (or AWS App Mesh with Envoy
  sidecar enforcing mTLS). Implement **AWS Fault Injection Simulator (FIS)** experiments
  (AZ failure, instance termination, network latency injection) in a staging environment and
  run monthly in production during low-traffic windows.
- [ ] Use Route 53 failover routing for DR. Enable Shield Advanced for WAF. Use
  Parameter Store for secret rotation. Use NLB for HTTPS termination. Use CloudWatch alarms
  to simulate failure testing.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — AWS DRS + Aurora Global Database + Route 53 ARC + WAF managed
  rules + Secrets Manager auto-rotation + ACM Private CA mTLS + AWS FIS.

* **Why it succeeds:**
  **Issue 1 (DR):** AWS Elastic Disaster Recovery replicates EC2 block-level changes continuously
  (RPO seconds); Aurora Global Database replicates with <1 second lag. Route 53 ARC routing
  controls enable **RTO <15 minutes** via pre-validated routing switches without DNS TTL delays.
  Both RPO and RTO targets are met.
  **Issue 2 (WAF):** AWS WAF on API Gateway with **AWS Managed Rule Groups** (specifically the
  `AWSManagedRulesSQLiRuleSet` and `AWSManagedRulesCommonRuleSet`) blocks SQL injection and
  XSS patterns automatically — no custom rule writing required for known attack patterns.
  **Issue 3 (Secret rotation):** Secrets Manager's **automatic rotation** uses a built-in Lambda
  rotation function for RDS/Aurora — implements dual-password rotation (creates new password,
  updates DB user, updates secret, verifies, then deletes old password) with zero application
  downtime. Configurable rotation interval (e.g., 30 days).
  **Issue 4 (HTTP internal traffic):** ACM Private CA issues internal TLS certificates to
  microservices; App Mesh with Envoy enforces mTLS between services, encrypting all internal
  VPC traffic without application code changes.
  **Issue 5 (Chaos testing):** AWS FIS provides managed fault injection experiments
  (EC2 termination, AZ outage simulation, API throttling, network latency) with safety guardrails
  — measurably tests recovery behavior and validates the DR improvements from Issue 1.

* **Why alternatives fail:**
  - **A)** Functionally the closest but "pilot light" without specifying DRS for EC2 continuous
    replication leaves RPO at hours (AMI-based recovery). A pilot light requires manual instance
    launch at failover — RTO may exceed 15 minutes without pre-warmed resources. ALB listener
    rules redirecting HTTP to HTTPS handle client-to-ALB traffic only — it does not encrypt
    internal microservice-to-microservice traffic within the VPC (constraint 4 partially unmet).
  - **B)** Manual secret rotation on a schedule defeats the purpose of constraint 3 (the problem
    is 14 months without rotation — manual processes will recur). Quarterly manual failover tests
    are insufficient for validating chaos behavior across all failure modes — FIS provides
    continuous, automated, guardrailed chaos experiments.
  - **D)** AWS Shield Advanced provides DDoS protection, not WAF functionality — it does not
    block SQL injection at the application layer. CloudWatch alarms monitoring for failures is
    not chaos engineering — alarms react to failures but do not inject failures to test recovery.
    Parameter Store does not support automatic secret rotation natively — Secrets Manager is
    required for automatic rotation with Lambda functions.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 61: Domain 1 — Design Solutions for Organizational Complexity

A global enterprise uses AWS Organizations with 200 accounts across 15 OUs representing
business units. The CISO requires: (1) **every API call** across all 200 accounts must be
captured in a **tamper-proof, centralized, queryable audit log** retained for **7 years**;
(2) the audit log must be **immutable** — even the Security account administrator cannot
delete it; (3) audit logs must be **queryable via SQL** without loading data into a database;
(4) any **root account login** in any member account must trigger a **real-time alert** within
60 seconds; (5) the solution must be **fully automated** — new accounts get coverage within
5 minutes of creation.

<div class="question-prompt">
**Question:** Which architecture satisfies ALL five requirements?
</div>

- [ ] Create CloudTrail trails in each account. Aggregate logs to a central S3 bucket.
  Use S3 Object Lock. Use Athena for SQL queries. Use CloudWatch Events for root login alerts.
  Use CloudFormation StackSets for new account automation.
- [ ] Create an **AWS CloudTrail Organization Trail** (single trail, all current and
  future accounts auto-enrolled within minutes — constraint 5). Deliver to a central S3 bucket
  in the Security account with **S3 Object Lock COMPLIANCE mode** (7-year retention — even the
  bucket owner cannot delete — constraints 1 and 2). Enable **AWS CloudTrail Lake** for
  SQL-based event queries directly on CloudTrail data without S3/Athena setup (constraint 3).
  Create an **EventBridge Organization rule** matching `{ "userIdentity": { "type": "Root" },
  "eventName": "ConsoleLogin" }` across all accounts → SNS → Security team (constraint 4,
  <60 second delivery). New accounts automatically covered by Organization Trail and
  Organization EventBridge rule.
- [ ] Use AWS Config Organization Rules to capture API calls. Store in DynamoDB.
  Use DynamoDB Streams for root login alerts. Use S3 Glacier for 7-year retention.
- [ ] Deploy a Security Information and Event Management (SIEM) tool on EC2. Forward
  all CloudTrail logs via Kinesis to the SIEM. Use SIEM alerting for root login. Use S3
  lifecycle for 7-year retention.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Organization Trail + S3 Object Lock COMPLIANCE + CloudTrail
  Lake + Organization EventBridge rule for root login.

* **Why it succeeds:** **CloudTrail Organization Trail** created from the management account
  automatically covers **all existing and future member accounts** — new accounts get coverage
  within minutes of creation without any manual configuration (constraint 5). The trail delivers
  to a central S3 bucket in the Security account; member accounts cannot modify or delete the
  trail. **S3 Object Lock COMPLIANCE mode** with a 7-year retention period makes logs
  **absolutely immutable** — even the root user of the Security account cannot delete objects
  within the retention period (constraint 2). This is the strongest immutability guarantee in
  AWS. **CloudTrail Lake** provides a managed event data store with native SQL query capability
  via the CloudTrail console or API — no Athena table creation, Glue crawlers, or S3 prefix
  management required (constraint 3). Queries run against the event data store directly. The
  **EventBridge Organization-level event bus** (or cross-account EventBridge rule) matching
  root `ConsoleLogin` events delivers alerts within seconds — well within the 60-second SLA
  (constraint 4).

* **Why alternatives fail:**
  - **A)** Per-account CloudTrail trails + StackSets automation is the manual predecessor to
    Organization Trail. StackSets have deployment delays (5+ minutes per account batch) and
    require ongoing maintenance. Athena with S3 requires Glue crawlers, table definitions,
    and partition management — CloudTrail Lake is simpler and purpose-built. Functionally valid
    but operationally inferior to B.
  - **C)** AWS Config captures **resource configuration changes**, not API call audit logs —
    Config Rules do not replace CloudTrail for API audit logging. DynamoDB is not an appropriate
    store for 7 years of CloudTrail events from 200 accounts (petabytes of data at potential
    $0.25/GB storage vs S3 at $0.023/GB). S3 Glacier for active query use cases introduces
    retrieval delays.
  - **D)** A SIEM on EC2 introduces self-managed infrastructure, licensing costs, and
    operational overhead. Kinesis delivery adds complexity and potential for data loss if the
    Kinesis stream is misconfigured. This violates the principle of using managed AWS services
    for centralized governance.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 62: Domain 2 — Design for New Solutions

A healthcare company is building a **clinical decision support system** that uses ML to
recommend treatments. Requirements: (1) ML models are trained on **PHI data** that must
**never leave the AWS account**; (2) training jobs run on **100 GPU instances** and must
complete within **2 hours** — Spot interruptions are acceptable if training auto-resumes;
(3) model inference must return recommendations within **200ms** — models are 2GB in size;
(4) the inference endpoint must **auto-scale from 0 to 1000 TPS** within 2 minutes of a
traffic spike; (5) model versions must be tracked with **full lineage** (training data version,
hyperparameters, metrics, code version); (6) PHI used in training must be **automatically
detected and catalogued** for HIPAA compliance reporting.

<div class="question-prompt">
**Question:** Which architecture satisfies all six requirements?
</div>

- [ ] EC2 p3.16xlarge instances for training. Custom model serving on EC2 Auto Scaling.
  Git for version tracking. Macie for PHI detection. Manual lineage tracking in DynamoDB.
- [ ] SageMaker Training Jobs with **Managed Spot Training** (100 GPU instances,
  automatic checkpoint to S3, resumes after interruption — constraint 2) in a **VPC with no
  internet gateway** (PHI stays in account — constraint 1). SageMaker **Real-Time Inference**
  endpoint with **Application Auto Scaling** (target tracking, scales out on invocation count —
  constraint 4). Enable **SageMaker Model Registry** + **SageMaker Pipelines** (tracks
  training data version via S3 URIs, hyperparameters, metrics, code commit hash — constraint 5).
  Deploy 2GB model on **ml.g4dn.xlarge** instances (GPU inference, <200ms — constraint 3).
  Enable **Amazon Macie** on the training data S3 bucket for PHI detection and cataloguing
  (constraint 6). SageMaker endpoint minimum instances = 0 with **Serverless Inference** for
  scale-from-zero, or use **Inference Recommender** to right-size.
- [ ] SageMaker Training with On-Demand instances. Deploy model on Lambda (2GB layer).
  Use MLflow for lineage. Enable CloudTrail for PHI audit. Auto Scaling on EC2 for inference.
- [ ] Azure ML for training (better GPU availability). SageMaker for inference. S3 for
  data. Manual compliance reporting. Route 53 for endpoint routing.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — SageMaker Managed Spot Training in isolated VPC + Real-Time
  Inference with Auto Scaling + Model Registry + Pipelines + Macie for PHI.

* **Why it succeeds:** **SageMaker Managed Spot Training** uses EC2 Spot Instances for training
  jobs with automatic **checkpoint-and-resume** — if a Spot instance is reclaimed, training
  automatically restarts from the last checkpoint saved to S3. For a 2-hour job across 100
  GPUs, checkpointing every 15-30 minutes limits lost work. The training job runs in a **VPC
  with no NAT Gateway or Internet Gateway** — PHI data never leaves the AWS account network
  boundary (constraint 1); SageMaker communicates with S3 via **VPC Endpoints**. **SageMaker
  Real-Time Inference** on `ml.g4dn.xlarge` (GPU) serves the 2GB model — GPU inference
  reduces latency well below 200ms for medical recommendation models (constraint 3). **Application
  Auto Scaling** with target tracking (invocations per instance) scales the endpoint from
  minimum to handle 1000 TPS — scale-out time is 1-2 minutes with pre-loaded model (constraint
  4). **SageMaker Model Registry** tracks model versions; **SageMaker Pipelines** records the
  full training lineage (data URI, code commit, hyperparameters, evaluation metrics) — the
  canonical ML lineage solution on AWS (constraint 5). **Amazon Macie** scans S3 buckets for
  PHI patterns and catalogues findings in Security Hub — HIPAA compliance reporting (constraint 6).

* **Why alternatives fail:**
  - **A)** Custom EC2 Auto Scaling for inference cannot scale from 0 to handle 1000 TPS within
    2 minutes — EC2 launch time alone is 60-90 seconds, plus model loading time for a 2GB model.
    Manual lineage tracking in DynamoDB requires custom tooling and is error-prone. No managed
    Spot checkpoint-resume capability without custom implementation.
  - **C)** Lambda has a **maximum deployment package size of 10GB (including layers)** and a
    maximum memory of 10GB — a 2GB model on Lambda is technically possible but Lambda's
    execution model (cold starts, 15-min timeout) makes it unsuitable for consistent <200ms
    GPU inference at 1000 TPS. Lambda does not support GPU instances.
  - **D)** Using Azure ML violates constraint 1 — PHI data would leave the AWS account and
    traverse the public internet to Azure, violating HIPAA data residency requirements and the
    explicit constraint that PHI must never leave the AWS account.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 63: Domain 3 — Migration Planning

A financial services company is migrating **200 microservices** from on-premises Kubernetes
(bare metal) to **Amazon EKS**. The migration must: (1) be executed in **waves** with
10-20 services per wave; (2) maintain **service-to-service communication** during the
transition — some services will be on-premises, some on EKS at any given time; (3) all
services use **mutual TLS (mTLS)** for authentication — the existing PKI must be extended
to AWS; (4) migrated services must use **IAM Roles for Service Accounts (IRSA)** to access
AWS services — no long-lived credentials; (5) the **rollback time** for any single wave must
be under **30 minutes**; (6) services must be migrated without rewriting Kubernetes manifests
— only AWS-specific annotations should be added.

<div class="question-prompt">
**Question:** Which migration architecture satisfies ALL six constraints?
</div>

- [ ] Migrate all services at once during a maintenance window. Use AWS Certificate
  Manager for mTLS. Configure IRSA. Use kubectl rollout undo for rollback. Rewrite manifests
  for EKS compatibility.
- [ ] Use **AWS Application Migration Service (MGN)** to lift the bare-metal Kubernetes
  nodes to EC2. Run the existing Kubernetes cluster on EC2. Gradually migrate workloads to
  EKS managed node groups. Use AWS Private CA for mTLS certificates. Configure IRSA per service.
- [ ] Execute wave-based migration using **AWS App Mesh** (service mesh across on-premises
  and EKS — hybrid mesh with Virtual Nodes representing on-premises services and EKS services).
  App Mesh Envoy sidecars handle mTLS using **ACM Private CA** certificates (extends existing
  PKI into AWS — constraint 3). **IRSA** configured via EKS OIDC provider + IAM role annotations
  on Kubernetes ServiceAccounts (constraint 4). **Helm chart annotations** add AWS-specific
  configurations without rewriting base manifests (constraint 6). Wave rollback: **EKS managed
  node group scaling to 0** + **App Mesh Virtual Node routing weight** shifted back to on-premises
  endpoints — achievable in <30 minutes (constraint 5). Hybrid connectivity via Direct Connect
  or Site-to-Site VPN for on-prem ↔ EKS service communication during transition (constraint 2).
- [ ] Use Istio service mesh for mTLS. Migrate all services to ECS Fargate instead of
  EKS. Use Secrets Manager for credentials. Perform migration in a single wave.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — App Mesh hybrid mesh + ACM Private CA + IRSA + Helm annotations
  + wave-based rollback via mesh routing weights.

* **Why it succeeds:** **AWS App Mesh** supports a **hybrid service mesh** — Virtual Nodes can
  represent both EKS pods and on-premises services (via DNS names or IP addresses). During each
  migration wave, on-premises services are registered as Virtual Nodes; after migration, the
  Virtual Node DNS name changes to the EKS service endpoint — no service-to-service communication
  changes during the hybrid period (constraint 2). **ACM Private CA** integrates with App Mesh
  to issue and rotate mTLS certificates automatically — the Private CA can be configured as an
  intermediate CA chained to the existing on-premises PKI, extending the trust chain into AWS
  (constraint 3). **IRSA** uses the EKS OIDC provider to associate IAM roles with Kubernetes
  ServiceAccounts via annotations — no credential management required, satisfying constraint 4.
  **Helm** `values.yaml` overrides and annotations add IRSA ServiceAccount annotations and App
  Mesh sidecar injection annotations without modifying base Kubernetes manifests (constraint 6).
  **Wave rollback** in App Mesh uses Virtual Router routing weights — shifting 100% traffic back
  to on-premises Virtual Node within minutes; EKS deployments are scaled down independently.
  Total rollback time <30 minutes (constraint 5).

* **Why alternatives fail:**
  - **A)** Migrating all 200 services at once eliminates wave-based migration (constraint 1)
    and makes rollback of any single wave meaningless. Rewriting manifests violates constraint 6.
    "kubectl rollout undo" rolls back a Deployment to the previous version within EKS but does
    not restore traffic routing to on-premises — hybrid rollback is not addressed.
  - **B)** Lifting bare-metal Kubernetes nodes to EC2 with MGN creates a self-managed Kubernetes
    cluster on EC2 — this is not migrating to EKS. It simply moves the existing cluster to EC2
    as a stepping stone without the managed EKS control plane benefits. IRSA requires EKS OIDC
    provider — not available on self-managed Kubernetes without additional tooling.
  - **D)** Migrating to ECS Fargate instead of EKS violates constraint 6 (Kubernetes manifests
    cannot be used on ECS — completely different orchestration API). Istio is a valid service
    mesh but is not an AWS-managed service and does not integrate natively with ACM Private CA
    or IRSA.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 64: Domain 4 — Cost Control

A company runs a **data processing pipeline** on AWS: S3 (raw data) → Glue ETL jobs (daily,
2-hour run) → Redshift (analytical queries) → QuickSight dashboards. Additional workloads:
Lambda functions processing S3 events (100M invocations/month), CloudWatch Logs retaining
all logs for 1 year (500GB/month ingested), API Gateway (REST, 500M calls/month). Monthly
bill: Glue $8,000, Redshift $18,000, Lambda $6,000, CloudWatch Logs $12,000, API Gateway
$7,000. Total: $51,000/month. Target: **35% reduction** with no loss of functionality.

<div class="question-prompt">
**Question:** Which combination of changes achieves ≥35% reduction?
</div>

- [ ] Purchase Redshift Reserved Nodes (1-year). Reduce Lambda memory. Reduce CloudWatch
  Logs retention to 90 days. Use API Gateway HTTP API instead of REST API.
- [ ] Use Glue job bookmarks to avoid reprocessing. Purchase Redshift Reserved Nodes
  (1-year). Optimize Lambda with Graviton2 (`arm64`). Export CloudWatch Logs to S3 after
  7 days (S3 at $0.023/GB vs CloudWatch at $0.03/GB). Use API Gateway HTTP API (~71% cheaper
  than REST API for the same call volume).
- [ ] Migrate Glue to EMR on EC2 Spot. Purchase Redshift Serverless. Reduce Lambda
  timeout. Delete CloudWatch Logs after 30 days. Use ALB instead of API Gateway.
- [ ] Purchase **Redshift Reserved Nodes (1-year)** (~35% saving on $18K → saves ~$6,300).
  Switch **API Gateway REST to HTTP API** (~71% cost reduction: REST API $3.50/million calls
  vs HTTP API $1.00/million — at 500M calls: REST=$1,750, HTTP=$500 → saves ~$1,250 base, but
  at scale the difference is significant — actual saving ~$5,000/month on the $7,000 line).
  Set **CloudWatch Logs retention to 30 days** + export to **S3 Glacier Instant Retrieval**
  for 1-year compliance (CloudWatch charges $0.03/GB/month for stored data; 500GB/month × 12
  months = 6TB at $0.03 = $180/month vs current $12,000 — the $12K must include ingestion +
  storage; reducing retention to 30 days cuts stored volume by 92% → saves ~$9,000-11,000).
  Use **AWS Lambda Graviton2** (arm64 architecture — 20% better price-performance, 20% cost
  reduction on $6,000 → saves ~$1,200). Use **Glue job bookmarks** to skip already-processed
  S3 objects (avoids redundant DPU usage — saves 20-30% on $8,000 → saves ~$1,600-2,400).

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **D** — Redshift Reserved Nodes + API Gateway HTTP API + CloudWatch
  Logs retention reduction + S3 export + Lambda Graviton2 + Glue job bookmarks.

* **Why it succeeds:** This option addresses every line item simultaneously:
  **Redshift ($18K):** 1-year Reserved Nodes provide 35% discount → saves ~$6,300/month.
  **API Gateway ($7K):** HTTP API is 71% cheaper than REST API for equivalent functionality
  (HTTP API lacks some features like API keys, usage plans, and custom request validation, but
  if those aren't needed, the saving is direct) → saves ~$5,000/month.
  **CloudWatch Logs ($12K):** The largest line item. Setting 30-day retention in CloudWatch
  and exporting to S3 Glacier Instant Retrieval ($0.004/GB/month) for the remaining 10 months
  dramatically cuts the stored-log cost. CloudWatch storage at $0.03/GB/month on 6TB (12 months
  × 500GB) = $180/month; but active ingestion cost and the $12K figure suggest significant
  stored volume. Cutting retention to 30 days reduces in-CW storage by 92% → saves ~$9,000+.
  **Lambda ($6K):** Graviton2 arm64 provides 20% better price/performance with no code changes
  for most Node.js/Python runtimes → saves ~$1,200.
  **Glue ($8K):** Job bookmarks prevent full re-scans of S3 on daily runs → saves ~$2,000.
  **Total: ~$23,500+ savings on $51,000 = ~46% — exceeds the 35% target.**

* **Why alternatives fail:**
  - **A)** Reduces Lambda memory — this may increase execution duration and increase total cost
    (Lambda charges = duration × memory). Reducing memory is not a guaranteed saving. Missing
    the CloudWatch Logs export strategy and Glue optimization — two of the largest saving
    opportunities.
  - **B)** Correct components but "export CloudWatch Logs to S3 after 7 days" retains 7 days
    in CloudWatch and moves to S3 — at $0.023/GB S3 Standard vs $0.003/GB Glacier, the
    recommendation should be S3 Glacier for archived compliance logs. Also omits Redshift
    Reserved Nodes which is the single largest saving. Less complete than D.
  - **C)** Migrating Glue to EMR on EC2 Spot is a re-architecture (different ETL framework,
    operational overhead). Redshift Serverless is appropriate for sporadic/unpredictable
    workloads — for a daily analytical cluster with predictable usage, Reserved Nodes are
    more cost-effective. Replacing API Gateway with ALB removes API management features
    and is a significant re-architecture.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 65: Domain 5 — Continuous Improvement for Existing Solutions

A retail company's **recommendation engine** runs on ECS Fargate (Python Flask API) backed
by a DynamoDB table with 500 million items. Issues identified: (1) **DynamoDB costs $45,000/month**
— hot partition reads on popular product IDs causing both high cost and throttling; (2) the
Flask API has **P99 latency of 800ms** — profiling shows 70% of time is DynamoDB `GetItem`
calls; (3) **ECS task definition uses 4 vCPU / 8GB memory** but CPU utilization averages 15%
and memory utilization averages 20%; (4) the API has **no rate limiting** — a single misbehaving
client sent 500K requests in 10 minutes last week, causing a cost spike; (5) Fargate tasks run
in **us-east-1 only** — European users (40% of traffic) experience 180ms additional latency.

<div class="question-prompt">
**Question:** Which set of improvements resolves all five issues?
</div>

- [ ] Add ElastiCache Redis in front of DynamoDB. Right-size Fargate tasks. Add API
  Gateway with throttling. Deploy CloudFront for European users.
- [ ] Enable DynamoDB DAX cluster (in-memory cache, microsecond reads, reduces DynamoDB
  RCU consumption for hot items — resolves issue 1 cost and issue 2 latency). Right-size Fargate
  to **1 vCPU / 2GB** (matching actual utilization + headroom — reduces Fargate cost by 70%).
  Implement **API Gateway usage plans with throttling** (per-client rate limiting, prevents
  runaway clients). Deploy **CloudFront with Lambda@Edge** for European users (routes to
  nearest CloudFront PoP, reduces latency by ~150ms for European users).
- [ ] Deploy **DynamoDB Accelerator (DAX)** cluster (drop-in DynamoDB API replacement,
  microsecond read latency, caches hot items — directly reduces both DynamoDB RCU costs on
  hot partitions and P99 latency from 800ms to <10ms for cached items). Right-size ECS Fargate
  task from 4vCPU/8GB to **1vCPU/2GB** (15% CPU → ~0.6vCPU actual; 20% memory → ~1.6GB
  actual; 1vCPU/2GB provides 67% headroom at a 75% cost reduction). Add **AWS WAF rate-based
  rule** on API Gateway or ALB (rate limit per IP, blocks after threshold — prevents runaway
  client cost spikes without requiring usage plan API keys). Deploy ECS tasks in **eu-west-1**
  with **Route 53 latency-based routing** to route European users to the nearest region.
- [ ] Migrate DynamoDB to Aurora with read replicas for caching. Scale down Fargate
  manually. Add Lambda authorizer for rate limiting. Use Direct Connect for European users.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — DynamoDB DAX + ECS right-sizing + WAF rate-based rule +
  Route 53 latency-based routing to eu-west-1.

* **Why it succeeds:** **DynamoDB Accelerator (DAX)** is a purpose-built, fully managed
  in-memory cache for DynamoDB — it uses the exact same DynamoDB API (drop-in replacement,
  no Flask code changes beyond changing the client endpoint). DAX caches `GetItem` and `Query`
  results at microsecond latency, serving hot product ID reads from memory instead of DynamoDB —
  this directly reduces DynamoDB RCU consumption (lower cost) and reduces P99 latency from
  800ms to <1ms for cached reads (issues 1 and 2). **ECS right-sizing** from 4vCPU/8GB to
  1vCPU/2GB reduces Fargate cost by 75% — at 15% CPU utilization of 4vCPU (0.6vCPU actual),
  1vCPU provides adequate headroom. Memory utilization at 20% of 8GB = 1.6GB actual; 2GB
  provides sufficient headroom (issue 3). **AWS WAF rate-based rule** on the ALB or API Gateway
  blocks IP addresses that exceed a configurable request threshold (e.g., 1,000 requests per
  5 minutes) — this is simpler and more effective than API keys/usage plans for blocking
  anonymous misbehaving clients (issue 4). **Route 53 latency-based routing** with ECS tasks
  deployed in `eu-west-1` routes European users to the nearest region — ~180ms RTT reduction
  for the 40% European traffic segment (issue 5).

* **Why alternatives fail:**
  - **A)** ElastiCache Redis requires code changes to the Flask application (Redis client, cache
    key design, TTL management, cache invalidation logic) — DAX is a drop-in DynamoDB API
    replacement requiring only a client endpoint change. CloudFront caches HTTP responses at
    edge — it does not reduce per-user latency for dynamic, personalized recommendation API
    responses (each user gets different recommendations, cache hit rate would be near 0).
    Route 53 with regional ECS deployment is the correct latency solution for a dynamic API.
  - **B)** Functionally similar to C but uses Lambda@Edge with CloudFront for European users —
    CloudFront + Lambda@Edge is appropriate for content delivery and edge logic, not for routing
    to a full regional API deployment. Lambda@Edge functions run at CloudFront PoPs but still
    call back to the origin (us-east-1) for dynamic personalized API responses — it does not
    eliminate the cross-Atlantic latency for origin calls.
  - **D)** Migrating DynamoDB to Aurora requires a complete data model redesign and application
    re-architecture — 500 million items with hot partition access patterns is a DynamoDB-native
    use case, not an Aurora use case. Direct Connect for European users routes network traffic
    through a dedicated connection but does not reduce public internet latency for end-user
    HTTP requests — it's for corporate network connectivity, not CDN/API latency optimization.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 66: Domain 1 — Design Solutions for Organizational Complexity

A bank's security team must ensure **all EC2 instances across 50 accounts** meet the following
continuously: (1) no EC2 instance may have a public IP address; (2) all EC2 instances must
have SSM Agent installed and report to Systems Manager; (3) any non-compliant instance must be
**automatically remediated within 10 minutes**; (4) compliance status must be visible in a
**single dashboard** without logging into each account; (5) the solution must cover newly
launched instances within **2 minutes** of launch.

<div class="question-prompt">
**Question:** Which architecture satisfies ALL five requirements?
</div>

- [ ] Use AWS Config Organization Rules with auto-remediation: Rule `EC2_INSTANCE_NO_PUBLIC_IP` triggers SSM Automation document `AWS-DisassociatePublicIp` on non-compliance. Rule `EC2_INSTANCE_MANAGED_BY_SYSTEMS_MANAGER` triggers SSM Automation `AWS-InstallAndConfigureSSMAgent`. Deploy Config Aggregator in Security account for centralized compliance dashboard. Organization Rules auto-apply to new accounts and detect new instances within 2 minutes via Config change-triggered evaluation.
- [ ] Deploy SCPs blocking `ec2:AssociateAddress`. Use Lambda to scan instances hourly. Use AWS Systems Manager Fleet Manager for visibility. Email alerts for non-compliance.
- [ ] Use AWS Security Hub with EC2 findings. Use GuardDuty for public IP detection. Manually remediate via runbooks. Use CloudWatch dashboards per account.
- [ ] Deploy a third-party CSPM tool. Use CloudTrail to detect EC2 launches. Use Lambda for remediation. Use a custom compliance dashboard in QuickSight.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **A** — AWS Config Organization Rules with SSM Automation auto-remediation
  + Config Aggregator for centralized dashboard.

* **Why it succeeds:** **AWS Config Organization Rules** deploy a Config rule to all 50 accounts
  from the management account or delegated admin — no per-account configuration needed. New
  accounts in the Organization automatically receive the rules. **Config change-triggered
  evaluation** (as opposed to periodic) fires within **2 minutes** of an EC2 instance entering
  the running state (constraint 5) — Config receives the `EC2:instance` configuration item
  change and immediately evaluates compliance. **SSM Automation auto-remediation** attached to
  the Config rule runs the specified document within **minutes** of a non-compliance finding —
  `AWS-DisassociatePublicIp` removes the public IP association; `AWS-InstallAndConfigureSSMAgent`
  installs SSM Agent. Total detection-to-remediation time is well within 10 minutes (constraint
  3). **AWS Config Aggregator** (Organization-level) aggregates compliance data from all 50
  accounts into the Security account — providing a single-pane compliance dashboard (constraint
  4) via the Config console or exported to S3/Athena for custom reporting.

* **Why alternatives fail:**
  - **B)** SCPs blocking `ec2:AssociateAddress` prevent associating Elastic IPs but do not
    prevent launching instances with `associatePublicIpAddress=true` in the subnet settings —
    the SCP would need to deny the launch call itself with conditions, which is complex and
    cannot target the `AssociatePublicIpAddress` parameter of `RunInstances` cleanly. Hourly
    Lambda scans violate constraint 5 (2-minute detection) and constraint 3 (10-minute
    remediation). SSM Fleet Manager provides visibility but not centralized compliance
    aggregation from a Config rules perspective.
  - **C)** Security Hub aggregates findings from Config, GuardDuty, Inspector — it is a
    consumer of compliance data, not a remediation engine. GuardDuty detects threats, not
    configuration compliance issues like public IPs or missing SSM Agent. Manual remediation
    via runbooks violates constraint 3 (automated remediation within 10 minutes).
  - **D)** Third-party CSPM tools are valid but the question asks for an AWS-native solution.
    CloudTrail-triggered Lambda with hourly scans cannot meet the 2-minute detection
    requirement — CloudTrail delivers events with a delay of up to 15 minutes for management
    events.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 67: Domain 2 — Design for New Solutions

A logistics company needs a **serverless event-driven order fulfillment system**. An order goes
through states: `PLACED → PAYMENT_PROCESSING → PAYMENT_CONFIRMED → WAREHOUSE_ASSIGNED →
PICKED → PACKED → SHIPPED → DELIVERED`. Requirements: (1) each state transition must be
**auditable** with the exact timestamp and triggering event; (2) the workflow must support
**parallel processing** — PICKED and PACKED can happen concurrently in sub-workflows; (3) if
any step fails, the system must execute **compensating transactions** (e.g., release warehouse
reservation if payment fails); (4) the workflow must be **resumable** — if a downstream
service (warehouse API) is unavailable, the system must retry with **exponential backoff** up
to 24 hours; (5) business analysts must be able to **visualize workflow execution** in a GUI
without writing code; (6) total workflow duration can be up to **90 days** (delayed deliveries).

<div class="question-prompt">
**Question:** Which architecture BEST satisfies all six requirements?
</div>

- [ ] SQS queues chained with Lambda functions for each state. DynamoDB for state
  tracking. CloudWatch for visualization. Custom retry logic in Lambda. SNS for notifications.
- [ ] AWS Step Functions **Standard Workflow** (supports execution duration up to 1 year
  — constraint 6). State machine with states for each order stage. **Parallel state** for
  PICKED/PACKED concurrent processing (constraint 2). **Catch and Retry** blocks with
  exponential backoff configuration (up to 24-hour retry window — constraint 4). **Compensating
  transactions** via dedicated rollback states triggered by `Catch` blocks (constraint 3).
  Step Functions **execution history** records every state transition with exact timestamps —
  full audit trail (constraint 1). **Step Functions console visual workflow editor** and
  execution visualization for business analysts (constraint 5).
- [ ] AWS Step Functions **Express Workflow**. EventBridge for state transitions.
  Lambda for each step. S3 for audit logs. Custom visualization in QuickSight.
- [ ] Apache Airflow on Amazon MWAA for workflow orchestration. DynamoDB for state.
  Lambda for each task. SNS for retry notifications. Custom dashboard for visualization.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Step Functions Standard Workflow with Parallel states, Catch/
  Retry blocks, compensating transaction states, execution history, and visual console.

* **Why it succeeds:** **AWS Step Functions Standard Workflow** supports execution durations
  of up to **1 year** — accommodating 90-day delayed deliveries (constraint 6). Express
  Workflows are limited to **5 minutes** and would fail this requirement. The **Parallel state**
  in Step Functions runs branches concurrently and waits for all to complete before proceeding —
  PICKED and PACKED sub-workflows run in parallel (constraint 2). **Retry** blocks with
  `IntervalSeconds`, `BackoffRate`, and `MaxAttempts` implement exponential backoff; combined
  with **HeartbeatSeconds** and `WaitForTaskToken` pattern for asynchronous callbacks, the
  system can retry warehouse API calls for up to 24 hours (constraint 4). **Catch** blocks
  transition to dedicated compensation states (e.g., `ReleaseWarehouseReservation`) when steps
  fail — implementing the Saga pattern for distributed transaction compensation (constraint 3).
  Step Functions **execution history** stores every state transition with exact timestamps,
  input/output, and event details — queryable via API or console (constraint 1). The **Step
  Functions console** provides a visual graph of the state machine with live execution tracking —
  business analysts can monitor order progress without code (constraint 5).

* **Why alternatives fail:**
  - **A)** Chained SQS + Lambda with custom retry logic and DynamoDB state tracking can
    implement this pattern but requires significant custom engineering for: parallel execution
    coordination, compensating transaction triggers, exponential backoff state management, and
    execution visualization. Step Functions provides all of this natively with less code.
  - **C)** **Step Functions Express Workflows** have a maximum duration of **5 minutes** —
    completely inadequate for a 90-day order fulfillment workflow. This is a fundamental
    constraint mismatch. Express Workflows are designed for high-volume, short-duration workflows.
  - **D)** Amazon MWAA (Apache Airflow) is a batch-oriented workflow orchestrator designed for
    data pipeline DAGs — it is not designed for event-driven, long-running transactional
    workflows with compensating transactions. Airflow DAGs run on a schedule or trigger, not
    per-order event. The operational overhead (Airflow environment cost, DAG management) is
    significantly higher than Step Functions for this use case.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 68: Domain 3 — Migration Planning

A company is performing a **database migration assessment** for 40 databases across their
data center: Oracle 12c (15 databases), MySQL 5.7 (10 databases), Microsoft SQL Server 2016
(8 databases), MongoDB 4.0 (5 databases), PostgreSQL 11 (2 databases). The migration team
must: (1) **assess schema complexity and migration effort** for each database before committing
to a migration path; (2) select the **optimal AWS target database** for each engine; (3) the
migration must use **continuous replication** to minimize cutover downtime; (4) **heterogeneous
migrations** (e.g., Oracle → Aurora PostgreSQL) must include automated schema conversion; (5)
the MongoDB databases contain **time-series data** — the target must optimize for time-series
queries; (6) all migrations must be tracked centrally.

<div class="question-prompt">
**Question:** Which toolchain and target mapping BEST satisfies all six requirements?
</div>

- [ ] Use AWS DMS for all databases. Migrate all to Amazon RDS Multi-AZ. Use SCT for
  Oracle and SQL Server. Track in Migration Hub.
- [ ] Use **AWS Schema Conversion Tool (SCT)** for assessment and conversion of
  heterogeneous migrations (Oracle → Aurora PostgreSQL, SQL Server → Aurora PostgreSQL — SCT
  generates assessment reports showing conversion complexity, manual action items, and estimated
  effort — constraint 1 and 4). Target mapping: Oracle → **Aurora PostgreSQL** (SCT + DMS CDC),
  MySQL → **Aurora MySQL** (homogeneous DMS migration — no SCT needed), SQL Server → **RDS
  for SQL Server** (homogeneous, preserve SQL Server features), MongoDB → **Amazon Timestream**
  (purpose-built time-series database — constraint 5), PostgreSQL → **Aurora PostgreSQL**
  (homogeneous). Use **DMS with CDC** for all migrations (constraint 3). Track via **AWS
  Migration Hub** (constraint 6).
- [ ] Use SCT for Oracle only. Migrate MySQL to DynamoDB. Migrate SQL Server to Aurora
  MySQL. Migrate MongoDB to DocumentDB. Migrate PostgreSQL to RDS PostgreSQL. Use DMS for
  replication. Track in Migration Hub.
- [ ] Migrate all databases to Amazon DynamoDB (single target for simplicity). Use DMS
  for replication. Use SCT for schema conversion. Track in Migration Hub.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — SCT for heterogeneous assessment + optimal per-engine target
  mapping (Aurora PG, Aurora MySQL, RDS SQL Server, Timestream, Aurora PG) + DMS CDC + Migration Hub.

* **Why it succeeds:** **AWS SCT** generates **Database Migration Assessment Reports** for each
  source database — quantifying the number of objects that convert automatically vs require manual
  intervention, estimated migration effort in person-days, and a complexity rating (constraint 1).
  This informs the go/no-go decision before committing migration resources. The **target mapping**
  is architecturally optimal:
  - **Oracle 12c → Aurora PostgreSQL**: SCT converts DDL/stored procedures/packages; DMS CDC
    replicates data continuously (heterogeneous migration, constraints 3 and 4).
  - **MySQL 5.7 → Aurora MySQL**: Homogeneous migration — no schema conversion needed; DMS
    CDC handles continuous replication with near-zero downtime cutover.
  - **SQL Server 2016 → RDS for SQL Server**: Preserves SQL Server-specific features (T-SQL,
    Agent Jobs, linked servers) that would require significant refactoring to migrate to Aurora
    PostgreSQL. DMS CDC for replication.
  - **MongoDB 4.0 (time-series) → Amazon Timestream**: Timestream is AWS's purpose-built
    time-series database optimized for time-series ingestion and queries — orders of magnitude
    more cost-efficient than MongoDB for time-series workloads (constraint 5). DMS supports
    MongoDB as a source.
  - **PostgreSQL 11 → Aurora PostgreSQL**: Drop-in compatible homogeneous migration.
  Migration Hub tracks all DMS tasks centrally (constraint 6).

* **Why alternatives fail:**
  - **A)** Migrating all databases to RDS Multi-AZ is a valid target but misses the optimal
    engine selection: MySQL should go to Aurora MySQL (better performance, serverless option),
    MongoDB time-series should go to Timestream (not RDS). SCT for Oracle and SQL Server only
    — misses the assessment for all 40 databases (constraint 1 partially unmet).
  - **C)** Migrating MySQL to DynamoDB is a major re-architecture (relational → NoSQL, requires
    complete data model redesign). SQL Server to Aurora MySQL requires schema conversion (SCT
    needed, T-SQL → MySQL compatibility issues). MongoDB to DocumentDB is a valid choice but
    DocumentDB is not optimized for time-series queries — Timestream provides purpose-built
    time-series optimization (constraint 5 unmet).
  - **D)** Migrating all databases to DynamoDB requires complete re-architecture of every
    application that uses relational databases — this is not a migration, it's a modernization
    project. Relational schemas with joins, transactions, and stored procedures cannot be
    directly migrated to DynamoDB without significant redesign.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 

### Scenario 69: Domain 4 — Cost Control

A company's **AWS bill analysis** reveals the following top cost drivers: (1) **NAT Gateway**
data processing charges: $18,000/month — EC2 instances in private subnets are downloading
S3 objects and calling DynamoDB, Secrets Manager, and SSM APIs through NAT Gateway; (2)
**Inter-AZ data transfer**: $12,000/month — ECS tasks in AZ-a are calling an RDS read replica
in AZ-b; (3) **CloudWatch Logs ingestion**: $9,000/month — application logs include DEBUG-
level logs being shipped to CloudWatch in production; (4) **Elastic Load Balancer** idle costs:
$4,000/month — 20 ALBs provisioned for microservices, most with <100 requests/day; (5)
**EC2 data transfer out**: $7,000/month — all API responses are served via EC2 directly,
bypassing CloudFront. Total targeted savings: **$35,000/month (70% reduction)**.

<div class="question-prompt">
**Question:** Which combination of fixes achieves the target?
</div>

- [ ] Add NAT Gateway to each AZ. Enable VPC Flow Logs to analyze traffic. Reduce
  CloudWatch Logs retention. Consolidate ALBs. Enable CloudFront.
- [ ] Replace NAT Gateway with VPC Endpoints for S3, DynamoDB, Secrets Manager, SSM.
  Use AZ-aware routing for ECS-to-RDS. Set application log level to INFO/WARN in production.
  Consolidate microservice ALBs onto a single ALB with path/host-based routing. Route API
  responses through CloudFront.
- [ ] Deploy **VPC Gateway Endpoints** for S3 and DynamoDB (free — no data processing
  charges, routes traffic within AWS network — eliminates NAT Gateway charges for S3/DynamoDB
  traffic) + **VPC Interface Endpoints** for Secrets Manager and SSM (interface endpoint data
  processing: $0.01/GB vs NAT Gateway $0.045/GB — ~78% reduction). Enable **ECS AZ-aware
  routing** (ECS Service Connect or AWS Cloud Map with AZ-affinity routing — ensures tasks
  route to same-AZ RDS replica endpoint). Set **CloudWatch Logs log level to INFO/WARN**
  (DEBUG generates 10-100× more log lines — setting to INFO typically reduces log volume by
  80-90%, reducing ingestion from $9K to ~$900-1,800). **Consolidate 20 ALBs to 2-3 ALBs**
  using ALB path-based and host-based routing rules (ALB fixed cost: ~$16/month + LCU charges
  — 20 ALBs at $16 each = $320 fixed + $3,680 LCU; consolidating to 3 ALBs saves ~$272 fixed
  + LCU savings). Enable **CloudFront** for API responses (CloudFront data transfer out:
  ~$0.0085/GB vs EC2 data transfer out: $0.09/GB — 90% reduction on the $7,000 line item).
- [ ] Move all EC2 to a public subnet to avoid NAT Gateway. Use Aurora instead of RDS
  to eliminate AZ data transfer. Delete all CloudWatch Logs. Use NLB instead of ALB.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — VPC Gateway/Interface Endpoints + ECS AZ-aware routing +
  CloudWatch log level reduction + ALB consolidation + CloudFront.

* **Why it succeeds:**
  **NAT Gateway ($18K):** VPC Gateway Endpoints for S3 and DynamoDB are **completely free**
  and route traffic within the AWS network — zero data processing charges. Interface Endpoints
  for Secrets Manager and SSM charge $0.01/GB data processing vs NAT Gateway's $0.045/GB —
  78% reduction. Eliminating S3/DynamoDB NAT traffic (typically 80%+ of NAT data volume)
  reduces NAT Gateway charges by ~$14,000-16,000.
  **Inter-AZ transfer ($12K):** ECS Service Connect with AZ-affinity or RDS reader endpoint
  with AZ-aware DNS routing ensures ECS tasks call the same-AZ read replica — eliminates
  cross-AZ transfer charges entirely → saves ~$12,000.
  **CloudWatch Logs ($9K):** DEBUG logs generate excessive volume. Setting log level to INFO
  in production reduces volume 80-90% → saves ~$7,200-8,100.
  **ALB idle costs ($4K):** Consolidating 20 ALBs to 3 using path/host routing reduces fixed
  ALB charges by 85% → saves ~$3,400.
  **EC2 data transfer ($7K):** CloudFront data transfer at $0.0085/GB vs EC2 $0.09/GB is a
  90% reduction → saves ~$6,300.
  **Total saves: ~$43,000-45,000 — exceeds $35,000 target.**

* **Why alternatives fail:**
  - **A)** Adding NAT Gateway to each AZ reduces cross-AZ NAT traffic overhead but does not
    eliminate the S3/DynamoDB data processing charges — VPC Endpoints are required for that.
    VPC Flow Logs analysis helps understand traffic but does not reduce costs. This option
    correctly identifies the issues but proposes the wrong fixes.
  - **B)** Correct strategy but lacks specificity on VPC Endpoint types (Gateway vs Interface)
    — the distinction matters because Gateway Endpoints are free while Interface Endpoints have
    hourly + data charges. Also lacks quantification. Option C is more technically precise.
  - **D)** Moving EC2 to public subnets is a security anti-pattern — eliminating private
    subnets to avoid NAT Gateway costs exposes instances directly to the internet. Aurora instead
    of RDS does not eliminate inter-AZ data transfer charges — the charges come from the ECS-to-
    RDS traffic crossing AZs, not the database engine. Deleting all CloudWatch Logs removes
    operational visibility critical for a production system.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div> 


### Scenario 70: Domain 5 — Continuous Improvement for Existing Solutions

A company's production **three-tier web application** (ALB → EC2 Auto Scaling → RDS MySQL)
has the following Well-Architected review findings: (1) the **RDS instance** (`db.r5.4xlarge`)
is at **90% CPU** during peak — queries are not optimized and no read replicas exist; (2) the
**EC2 Auto Scaling group** takes **8 minutes** to scale out during traffic spikes — the AMI
baking process for custom software installation takes 6 of those 8 minutes; (3) there is **no
circuit breaker** between the web tier and a third-party payment API — when the payment API is
slow (>5s), all web tier threads block, causing cascading failure; (4) **RDS automated backups
are disabled** — a recent schema migration gone wrong caused 6 hours of downtime with no
restore path; (5) CloudFormation templates are stored in **S3 with public read access** —
a recent audit flagged potential credential exposure in template parameters.

<div class="question-prompt">
**Question:** Which set of improvements resolves ALL five findings?
</div>

- [ ] Add RDS read replica. Reduce AMI size. Add ALB timeout for payment API. Enable
  RDS automated backups. Make S3 bucket private.
- [ ] Add RDS read replica and Performance Insights. Pre-warm ASG. Implement retry logic
  in application for payment API. Enable RDS PITR. Enable S3 bucket versioning and encryption.
- [ ] Add **RDS read replica** + enable **RDS Performance Insights** (identifies top
  SQL queries causing 90% CPU — enables query optimization; read replica offloads read traffic).
  Replace AMI baking with **EC2 Launch Templates using EC2 Image Builder** pipeline + store
  pre-baked AMI with all software installed (reduces ASG scale-out from 8min to ~2min — software
  pre-installed in AMI, only boot + health check time remaining). Implement **AWS Lambda or
  Step Functions** as an **async wrapper** for the payment API call — web tier enqueues payment
  request to SQS, Lambda calls payment API asynchronously; web tier returns `202 Accepted`
  immediately, preventing thread blocking (circuit breaker pattern via async decoupling).
  Enable **RDS automated backups** (1-35 day retention) + **enable PITR** — allows restore to
  any second within the retention window. **Block S3 public access** on the CloudFormation
  template bucket + migrate sensitive parameters to **AWS Systems Manager Parameter Store**
  (SecureString) or **AWS Secrets Manager** — reference in CloudFormation via dynamic
  references (`{{resolve:ssm-secure:...}}` or `{{resolve:secretsmanager:...}}`).
- [ ] Migrate RDS to Aurora Serverless. Use Lambda for all compute. Replace payment API
  with internal service. Migrate to S3 encrypted storage. Rewrite CloudFormation in CDK.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — RDS read replica + Performance Insights + pre-baked AMI via
  Image Builder + SQS async payment decoupling + RDS PITR + S3 block public access + SSM/
  Secrets Manager for parameters.

* **Why it succeeds:**
  **Issue 1 (RDS CPU 90%):** RDS Performance Insights identifies the top N SQL queries by
  load — this enables targeted query optimization (add indexes, rewrite queries) without
  guessing. Adding a read replica offloads SELECT queries from the writer, directly reducing
  writer CPU. Combined approach addresses both the root cause (bad queries) and immediate relief
  (read scaling).
  **Issue 2 (8-minute scale-out):** Pre-baking the AMI with EC2 Image Builder (all application
  dependencies, runtime, configuration pre-installed) means new instances only need to boot and
  pass health checks — scale-out drops from 8 minutes to ~90 seconds. Launch Templates reference
  the latest Image Builder AMI automatically via SSM Parameter Store parameter.
  **Issue 3 (Payment API blocking):** Asynchronous decoupling via SQS + Lambda breaks the
  synchronous call chain — web tier threads are never blocked waiting for the payment API.
  SQS provides buffering; Lambda retries with exponential backoff; the payment API slowness is
  isolated behind the queue.
  **Issue 4 (No backups):** RDS automated backups with PITR enable restore to any second within
  the retention window — the schema migration scenario would have been recoverable in minutes
  by restoring to the timestamp before the migration.
  **Issue 5 (Public S3 + credentials in parameters):** S3 Block Public Access is a one-click
  fix. CloudFormation dynamic references to SSM Parameter Store (SecureString) or Secrets
  Manager replace hardcoded credentials in templates — the templates themselves no longer
  contain sensitive values.

* **Why alternatives fail:**
  - **A)** "Add ALB timeout for payment API" (e.g., setting ALB idle timeout to 5 seconds)
    would cause the ALB to return a 504 timeout to users — this terminates the request but
    does not prevent thread exhaustion in the web tier if threads are blocked waiting for the
    ALB timeout. The circuit breaker must be in the application layer (async SQS pattern) or
    App Mesh/Envoy. "Make S3 bucket private" addresses the access control but doesn't fix
    credentials stored in template parameters — the credentials are still in S3, just not
    publicly readable.
  - **B)** "Pre-warm ASG" is not a defined AWS feature — ASG pre-warming requires scheduled
    scaling or predictive scaling, not fixing the root cause (AMI baking time). "Retry logic
    in application for payment API" improves resilience but still keeps synchronous threads
    blocked during retries — it does not implement a circuit breaker pattern. S3 versioning
    and encryption do not address public access or credential exposure in template parameters.
  - **D)** Migrating RDS to Aurora Serverless, Lambda for all compute, and rewriting
    CloudFormation in CDK constitutes a complete re-architecture — not a Well-Architected
    improvement of the existing system. These changes introduce significant migration risk and
    cost for problems solvable with targeted improvements.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div>

### Scenario 71: Domain 1 — Design Solutions for Organizational Complexity

A company runs 60 AWS accounts across `Production`, `Staging`, and `Development` OUs. The
platform team must enforce: (1) **all S3 buckets must have versioning enabled** — any bucket
created without versioning must be auto-remediated within 5 minutes; (2) **EC2 instances must
only be launched from approved AMIs** — a curated list of hardened AMIs maintained by the
security team in a dedicated account; (3) **VPC Flow Logs must be enabled** on every VPC
across all accounts — any VPC without Flow Logs must trigger an alert and auto-remediation;
(4) all three controls must apply to **newly created accounts within 10 minutes**; (5) the
security team must see a **unified compliance score** across all accounts without switching
consoles.

<div class="question-prompt">
**Question:** Which architecture satisfies ALL five requirements with least operational overhead?
</div>

- [ ] **A)** Use CloudFormation StackSets to deploy Config rules and SSM Automation remediation
  documents to all accounts. Share approved AMIs via AWS RAM. Use Config Aggregator for unified
  compliance. New accounts enrolled via StackSets triggered by Organizations lifecycle events.
- [ ] **B)** Deploy **AWS Config Organization Conformance Pack** containing three Config rules:
  `S3_BUCKET_VERSIONING_ENABLED` (auto-remediation: SSM Automation `AWS-EnableS3BucketVersioning`),
  `APPROVED_AMIS_BY_ID` (parameter: approved AMI list from Security account), and
  `VPC_FLOW_LOGS_ENABLED` (auto-remediation: SSM Automation `AWS-EnableVPCFlowLogs`).
  Share approved AMIs via **EC2 Image Builder + AWS RAM** Organization-wide sharing. Use
  **AWS Security Hub** (Organization-wide, delegated admin) with Config integration for unified
  compliance score. New accounts auto-enrolled via Organization Conformance Pack within minutes.
- [ ] **C)** Use AWS Control Tower guardrails for S3 versioning and VPC Flow Logs. Use IAM
  policies to restrict AMI usage. Use CloudWatch dashboards per account for compliance.
  Manually enroll new accounts in Control Tower.
- [ ] **D)** Write Lambda functions triggered by CloudTrail events (`CreateBucket`,
  `RunInstances`, `CreateVpc`) to enforce each control. Store approved AMIs in a DynamoDB
  table. Use QuickSight for compliance dashboards.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — Config Organization Conformance Pack with auto-remediation + EC2 Image Builder AMI sharing via RAM + Security Hub unified compliance.

* **Why it succeeds:** **AWS Config Organization Conformance Packs** deploy a set of Config
  rules and optional SSM Automation remediation documents to all accounts in the Organization
  (or specific OUs) from a single template — no per-account configuration required. New
  accounts added to the Organization receive the conformance pack **automatically within
  minutes**, satisfying constraint 4. **SSM Automation auto-remediation** attached to each
  rule triggers within minutes of a non-compliance finding — S3 versioning enablement and VPC
  Flow Log creation are well within the 5-minute window (constraints 1 and 3). The
  `APPROVED_AMIS_BY_ID` Config rule evaluates `RunInstances` events and flags non-compliant
  launches — combined with an SCP `Deny ec2:RunInstances` unless `ec2:ImageID` is in the
  approved list provides preventive enforcement. **EC2 Image Builder** pipelines produce
  hardened AMIs shared via **AWS RAM** to the entire Organization — spoke accounts see the
  shared AMIs directly in their EC2 console. **Security Hub** (Organization-wide) aggregates
  Config compliance findings into a unified compliance score dashboard in the Security account
  (constraint 5), with FSBP (Foundational Security Best Practices) standard covering all
  three controls.

* **Why alternatives fail:**
  - **A)** CloudFormation StackSets + Organizations lifecycle triggers require custom EventBridge
    rules and Lambda functions to detect new account creation and trigger StackSet instance
    deployment — this has deployment latency of 5-15 minutes depending on StackSet instance
    provisioning, potentially exceeding the 10-minute window (constraint 4). Config Aggregator
    provides compliance data but not the unified scored dashboard that Security Hub provides
    (constraint 5).
  - **C)** AWS Control Tower guardrails (detective and preventive) cover some controls but
    manual new account enrollment directly violates constraint 4. Control Tower's Account
    Factory can automate enrollment but adds significant setup complexity versus Organization
    Conformance Packs for this specific use case.
  - **D)** Lambda functions triggered by CloudTrail events introduce custom code maintenance,
    potential event delivery delays (CloudTrail management events: up to 15-minute delivery
    latency), and no native compliance scoring. This approach rebuilds what Config + Security
    Hub provides natively.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div>

### Scenario 72: Domain 2 — Design for New Solutions

A startup is building a **multi-tenant SaaS platform** where each tenant gets an **isolated
data environment**. Requirements: (1) **tenant data must be physically isolated** — one tenant
must never be able to access another tenant's data even in the event of a software bug;
(2) the platform must support **10,000 tenants** at launch scaling to **100,000** within 2
years; (3) each tenant has a **different data retention policy** (30 days to 7 years);
(4) **cross-tenant analytics** must be possible for the platform owner (not tenants) —
aggregated reporting across all tenants; (5) onboarding a new tenant must be **fully automated
and complete within 60 seconds**; (6) per-tenant cost must be **trackable** for billing
purposes.

<div class="question-prompt">
**Question:** Which data isolation and architecture strategy BEST satisfies all six requirements?
</div>

- [ ] **A)** One AWS account per tenant. DynamoDB with tenant_id partition key. IAM policies
  for isolation. Lambda for onboarding automation. Cost Explorer per account for billing.
- [ ] **B)** Single DynamoDB table with `tenant_id` as partition key. Row-level security via
  Lambda authorizer. S3 per-tenant prefix for object storage. Athena for cross-tenant
  analytics. S3 Lifecycle per prefix for retention. AWS Cost Allocation Tags for billing.
- [ ] **C)** **S3 per-tenant bucket** with **bucket-level KMS CMK** (each tenant gets a unique
  KMS key — data encrypted with tenant-specific key, physical isolation at storage layer even
  if application logic has a bug — constraint 1). **DynamoDB per-tenant table** (table-level
  IAM policy isolation). **Lambda-based onboarding automation** (creates S3 bucket, KMS key,
  DynamoDB table, IAM role in <60 seconds via Step Functions — constraint 5). **S3 Lifecycle
  per bucket** configured at onboarding with tenant-specific retention (constraint 3). **AWS
  Glue Data Catalog** with cross-tenant Athena views for platform-owner analytics (constraint
  4). **AWS Cost Allocation Tags** (`TenantID` tag on all resources) + per-tenant resource
  grouping for cost tracking (constraint 6). At 100,000 tenants: 100,000 S3 buckets (within
  soft limit, requestable increase), 100,000 DynamoDB tables (within limits).
- [ ] **D)** One VPC per tenant with VPC peering to a central analytics VPC. RDS per tenant.
  Terraform for onboarding. CloudWatch for cost tracking. Direct Athena federation to RDS
  for cross-tenant analytics.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — Per-tenant S3 bucket with KMS CMK + per-tenant DynamoDB table + Step Functions onboarding automation + per-bucket Lifecycle + Glue/Athena analytics + Cost Allocation Tags.

* **Why it succeeds:** **Physical isolation** (constraint 1) requires that tenant A's data
  cannot be accessed even if application code incorrectly constructs a query for tenant B.
  Per-tenant S3 buckets with **unique KMS CMKs** achieve this — tenant B's KMS key cannot
  decrypt tenant A's objects regardless of application logic. Per-tenant DynamoDB tables with
  table-level IAM policies (each tenant's Lambda role has access only to its own table) enforce
  isolation at the API layer. A shared-table approach with `tenant_id` partition key relies
  solely on application-level filtering — a bug bypasses isolation entirely. **Step Functions
  orchestrating Lambda** creates all tenant resources (S3 bucket, KMS key, DynamoDB table,
  IAM role, Lifecycle policy) in parallel — total provisioning time is 15-30 seconds,
  well within 60 seconds (constraint 5). Per-bucket S3 Lifecycle rules set individual retention
  periods at onboarding (constraint 3). **Glue Data Catalog** crawls all tenant S3 buckets
  (using a cross-account IAM role with read access to all buckets) — Athena queries the Glue
  catalog for cross-tenant aggregation accessible only to the platform owner (constraint 4).
  `TenantID` Cost Allocation Tags on all resources enable per-tenant cost breakdown in Cost
  Explorer (constraint 6).

* **Why alternatives fail:**
  - **A)** One AWS account per tenant provides the strongest isolation but fails constraint 5
    — new account creation via Organizations takes 5-15 minutes (email verification, account
    initialization) — far beyond 60 seconds. At 100,000 tenants, account management overhead
    is extreme. Cross-tenant analytics requires complex cross-account Athena federation.
  - **B)** Single DynamoDB table with `tenant_id` partition key fails constraint 1 — a
    `FilterExpression` bug or missing condition in application code allows cross-tenant data
    access. Row-level security via Lambda authorizer is application-layer enforcement, not
    physical isolation. S3 per-tenant prefix in a shared bucket shares the same KMS key —
    not physical isolation.
  - **D)** One VPC per tenant fails constraint 5 — VPC creation + RDS instance provisioning
    takes 10-20 minutes. At 100,000 tenants, 100,000 VPCs exceeds AWS per-region VPC limits
    (default 5, max 300 with increase). RDS per tenant at 100,000 tenants is cost-prohibitive.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div>

### Scenario 73: Domain 3 — Migration Planning

A company is migrating a **SAP ERP system** (SAP S/4HANA, 8TB HANA database) from on-premises
to AWS. Requirements: (1) SAP S/4HANA must run on **SAP-certified EC2 instance types**;
(2) the HANA database requires **persistent memory (PMEM)** for optimal performance;
(3) cutover downtime must be **under 6 hours** including database migration; (4) the SAP
landscape has three tiers: Development, Quality, Production — **Dev and QA must be migrated
first** as a proof of concept; (5) post-migration, the system must meet **SAP's high availability
requirements** — automatic failover for the HANA database; (6) the AWS environment must be
validated against **SAP's Cloud Availability Framework** before go-live.

<div class="question-prompt">
**Question:** Which migration approach satisfies ALL six requirements?
</div>

- [ ] **A)** Use AWS Application Migration Service to lift-and-shift the SAP servers. Use
  RDS for SAP HANA. Deploy in Multi-AZ for HA. Use AWS Launch Wizard for SAP validation.
- [ ] **B)** Deploy SAP S/4HANA on **`x2idn.32xlarge` or `x2iedn.32xlarge` EC2 instances**
  (SAP-certified, include NVMe-based instance storage used as PMEM tier by HANA — constraints
  1 and 2). Use **AWS Launch Wizard for SAP** to deploy the full SAP landscape (automatically
  validates instance types, storage, network, and OS settings against SAP requirements —
  constraint 6). Migrate Dev → QA → Production in sequence (constraint 4). For database
  migration: use **SAP HANA System Replication (HSR)** to replicate the 8TB HANA database
  from on-premises to AWS in sync mode during the migration window — cutover = stop on-premises
  transactions, promote AWS replica to primary (<6 hours — constraint 3). Deploy **SAP HANA
  HA using HSR in synchronous mode** between two EC2 instances across two AZs + **AWS-managed
  SAP HA using Pacemaker cluster** for automatic failover (constraint 5).
- [ ] **C)** Use AWS DMS to migrate the HANA database. Deploy on `r5.24xlarge` instances.
  Use EBS `io2` volumes for PMEM. Deploy Aurora as HANA replacement. Use Route 53 for HA.
- [ ] **D)** Use Snowball Edge to transfer the 8TB HANA database. Deploy on `u-6tb1.metal`
  instances. Use S3 for HANA data. Deploy in a single AZ. Validate manually against SAP
  requirements.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **B** — SAP-certified `x2idn/x2iedn` EC2 instances + AWS Launch Wizard for SAP + HANA System Replication for cutover + HSR synchronous HA across AZs.

* **Why it succeeds:** **`x2idn.32xlarge` and `x2iedn.32xlarge`** are EC2 instances
  specifically certified by SAP for SAP HANA workloads — they appear on SAP's Certified and
  Supported SAP HANA Hardware Directory. These instances include **NVMe instance storage**
  that HANA uses as a persistent memory (PMEM) tier, dramatically accelerating HANA's
  columnar store operations (constraints 1 and 2). **AWS Launch Wizard for SAP** automates
  the deployment of entire SAP landscapes (HANA DB + application server + optional HA
  configuration) while automatically validating the deployment against SAP's sizing guidelines,
  OS parameters, storage throughput requirements, and network configuration — this is the
  canonical tool for SAP-on-AWS validation (constraint 6). **SAP HANA System Replication**
  (HSR) is SAP's native replication technology — it replicates the 8TB HANA in-memory database
  to an AWS target instance continuously. At cutover, stopping source writes and promoting the
  AWS target takes minutes, keeping total downtime well under 6 hours (constraint 3).
  **HSR in synchronous mode** between two AZs with **Pacemaker cluster manager** provides
  SAP-validated automatic failover — the standard AWS reference architecture for SAP HANA HA
  (constraint 5).

* **Why alternatives fail:**
  - **A)** **AWS DMS does not support SAP HANA as a source or target** for database migration —
    DMS is designed for relational and NoSQL databases, not in-memory columnar databases. RDS
    does not offer SAP HANA as an engine — SAP HANA must run on EC2. This option conflates
    general database migration tooling with SAP-specific migration requirements.
  - **C)** `r5.24xlarge` instances are not SAP-certified for HANA production workloads —
    SAP HANA certification requires specific memory-optimized instances from the `x1`, `x1e`,
    `x2i`, or `u-` families. EBS `io2` volumes do not provide PMEM — PMEM in HANA on AWS is
    provided by NVMe instance storage on specific instance types, not EBS. Aurora cannot replace
    SAP HANA — they are entirely different database architectures.
  - **D)** Snowball Edge for an 8TB database has a 7-10 day shipping round-trip — incompatible
    with the structured Dev→QA→Production wave migration. S3 cannot serve as a HANA database
    storage layer — HANA requires block storage (EBS or instance NVMe). Single-AZ deployment
    violates SAP HA requirements (constraint 5).

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div>

### Scenario 74: Domain 4 — Cost Control

A company's **machine learning platform** on AWS has spiraling costs. Analysis reveals:
(1) **SageMaker Studio** notebooks are left running 24/7 by data scientists — 50 notebook
instances averaging `ml.t3.medium` at $0.05/hr each = $1,800/month idle; (2) **SageMaker
Training Jobs** use `ml.p3.8xlarge` On-Demand for all jobs including 10-minute exploratory
runs that only need CPU; (3) **S3 storage**: 500TB of raw training datasets, intermediate
feature stores, and model artifacts — no lifecycle management; (4) **SageMaker Endpoints**:
10 real-time inference endpoints deployed, 7 of which receive **<10 requests/day** (nearly
idle) but are charged 24/7; (5) **Amazon ECR**: 10TB of container images with no cleanup
policy — old image layers accumulate indefinitely. Total ML platform bill: $180,000/month.
Target: **40% reduction**.

<div class="question-prompt">
**Question:** Which combination delivers ≥40% savings?
</div>

- [ ] **A)** Set SageMaker Studio idle timeout. Use Spot for all training. Set S3 lifecycle.
  Delete idle endpoints. Set ECR lifecycle policy.
- [ ] **B)** Shut down all SageMaker Studio notebooks nightly via Lambda. Use `ml.p3.2xlarge`
  instead of `ml.p3.8xlarge` for training. Apply S3 Intelligent-Tiering. Convert idle endpoints
  to Serverless Inference. Set ECR lifecycle policy to delete untagged images.
- [ ] **C)** Configure **SageMaker Studio idle shutdown** (built-in feature — automatically
  stops kernel sessions after configurable idle period, e.g., 1 hour — eliminates 24/7 idle
  notebook cost → saves ~$1,800/month). Use **SageMaker Managed Spot Training** for all
  training jobs + **job type routing**: short exploratory runs (<30 min) on `ml.m5.4xlarge`
  CPU instances (Spot), long GPU runs on `ml.p3.8xlarge` Spot — Spot saves 70-90% on training
  cost. Apply **S3 Lifecycle**: raw datasets → S3 Standard-IA after 30 days → Glacier Deep
  Archive after 90 days; model artifacts → expire after 180 days (keep latest N via S3
  Lifecycle `NoncurrentVersionExpiration`). Convert 7 near-idle endpoints to **SageMaker
  Serverless Inference** (pay per invocation, $0 when idle — at <10 requests/day these cost
  near zero vs 24/7 instance charges). Set **ECR Lifecycle Policy** to expire untagged images
  after 1 day and keep only last 5 tagged versions per repository.
- [ ] **D)** Migrate SageMaker to self-managed Kubernetes on EC2 Spot. Use S3 Glacier for all
  data. Terminate all endpoints and use batch inference only. Delete old ECR images manually.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — SageMaker idle shutdown + Managed Spot Training with job routing + S3 Lifecycle tiering + Serverless Inference for idle endpoints + ECR Lifecycle.

* **Why it succeeds:** Each lever targets a specific waste pattern:
  **SageMaker Studio idle notebooks ($1,800/month):** SageMaker Studio's **idle shutdown**
  configuration stops kernel sessions and apps after inactivity — eliminates 100% of idle
  notebook cost with no workflow impact (scientists restart kernels when needed). Saves ~$1,800.
  **Training jobs (likely the largest cost driver):** Managed Spot Training with 70-90%
  discount. Routing 10-minute exploratory jobs to CPU instances (`ml.m5.4xlarge` at $0.27/hr
  Spot vs `ml.p3.8xlarge` at $3.60/hr On-Demand) alone reduces per-exploratory-job cost by
  97%. Estimating training at ~$80,000/month of the $180,000 total — Spot + right-sizing saves
  ~$60,000-70,000.
  **S3 500TB (~$11,500/month at Standard pricing):** Lifecycle to Standard-IA (30 days) + Deep
  Archive (90 days) for raw datasets reduces storage cost by 75-95% on aged data → saves
  ~$7,000-9,000.
  **7 idle endpoints (~$14,000/month assuming ml.m5.xlarge per endpoint 24/7):** Serverless
  Inference at <10 requests/day costs <$1/month per endpoint → saves ~$13,900.
  **ECR 10TB (~$1,000/month):** Lifecycle policy reduces to <1TB → saves ~$900.
  **Total estimated savings: ~$82,000-85,000 on $180,000 = ~45-47% — exceeds 40% target.**

* **Why alternatives fail:**
  - **A)** "Set SageMaker Studio idle timeout" is correct but "Use Spot for all training" is
    imprecise — without job type routing (CPU vs GPU), using `ml.p3.8xlarge` Spot for 10-minute
    exploratory runs still wastes money (GPU Spot is expensive relative to CPU for non-GPU
    workloads). "Delete idle endpoints" removes capability without the Serverless Inference
    alternative — the 7 endpoints presumably serve real (if infrequent) traffic. Option A is
    directionally correct but less precise than C.
  - **B)** Nightly Lambda shutdown of notebooks is a custom solution for a problem SageMaker
    solves natively (idle shutdown). `ml.p3.2xlarge` is still a GPU instance — for 10-minute
    exploratory runs that need only CPU, a CPU instance is dramatically cheaper. S3 Intelligent-
    Tiering charges $0.0025 per 1,000 objects for monitoring — at 500TB with many small files,
    this monitoring fee can be significant. Explicit Lifecycle rules are more cost-effective
    when access patterns are predictable.
  - **D)** Self-managed Kubernetes on EC2 Spot eliminates SageMaker's managed training,
    experiment tracking, model registry, and lifecycle features — rebuilding these adds
    engineering cost that likely exceeds the savings. Batch-only inference for endpoints that
    receive real (if infrequent) requests would degrade the user experience.

</details>
</div>

<div class="exam-container">
<div class="vue-header"><span>AWS Certified Solutions Architect</span><span>Time Remaining: 130 minutes</span></div>

### Scenario 75: Domain 5 — Continuous Improvement for Existing Solutions

A company is running a **production data pipeline**: Kinesis Data Streams → Lambda (transform)
→ S3 → Glue ETL → Redshift. The following issues have been identified through a Well-Architected
review: (1) **Kinesis shard hot spots** — 3 out of 20 shards receive 80% of records because
the partition key is `customer_tier` (only 4 values: BRONZE, SILVER, GOLD, PLATINUM);
(2) **Lambda iterator age** on the Kinesis trigger is consistently **>15 minutes** — the
function takes 45 seconds per batch due to a synchronous HTTP call to an enrichment API;
(3) **Glue job failures** occur 3× per week — always on the same malformed source file from
a specific upstream system; (4) **Redshift query performance** has degraded 40% over 6 months
— the main fact table has not been VACUUMed and ANALYZE has not been run since the cluster
was provisioned; (5) **no data quality checks** exist between any pipeline stages — bad data
reaches Redshift and corrupts dashboards.

<div class="question-prompt">
**Question:** Which set of improvements resolves ALL five issues?
</div>

- [ ] **A)** Increase Kinesis shard count. Increase Lambda timeout. Add Glue job retries.
  Run VACUUM manually. Add Lambda data validation before Redshift load.
- [ ] **B)** Use Kinesis Enhanced Fan-Out. Rewrite Lambda in Go for speed. Add Glue bookmarks.
  Schedule VACUUM via Lambda. Use Glue DataBrew for data quality.
- [ ] **C)** Change Kinesis **partition key to a high-cardinality value** (e.g., `customer_id`
  or `record_uuid`) to distribute records evenly across all 20 shards — eliminates hot spots
  without shard count increase (constraint 1). Decouple the enrichment API call: Lambda writes
  raw records to S3 immediately, then an **async Step Functions workflow** or second Lambda
  (triggered by S3 event) calls the enrichment API — reduces Lambda execution time from 45s
  to <5s, resolving iterator age lag (constraint 2). Add **Glue job bookmarks** +
  **per-file validation** (Glue Python shell job or Lambda) before the main Glue ETL job —
  quarantine malformed files to an S3 error prefix and alert via SNS (constraint 3). Enable
  **Redshift automatic table optimization** (ATO — automatically runs VACUUM and ANALYZE on
  a schedule, reclaims deleted space, updates statistics — constraint 4). Implement **AWS
  Glue Data Quality** rules between each pipeline stage (completeness, referential integrity,
  range checks) — quarantine records failing quality rules before they reach Redshift
  (constraint 5).
- [ ] **D)** Replace Kinesis with SQS FIFO. Migrate Lambda to ECS for longer processing.
  Replace Glue with EMR. Migrate Redshift to Aurora. Add manual QA review before each load.

<details>
<summary>View Architectural Decision Record (Resolution)</summary>

**Architectural Decision Record (Resolution):**

* **Optimal Solution:** **C** — High-cardinality partition key + async enrichment decoupling + Glue bookmarks + file validation + Redshift ATO + Glue Data Quality.

* **Why it succeeds:**
  **Issue 1 (Kinesis hot spots):** The root cause is a **low-cardinality partition key**
  (`customer_tier` = 4 values). Kinesis maps partition key hashes to shards — with 4 values
  and 20 shards, at most 4 shards receive traffic and 16 are idle. Changing to `customer_id`
  (millions of values) distributes records uniformly across all 20 shards via consistent
  hashing. No infrastructure change required.
  **Issue 2 (Lambda iterator age >15 min):** The 45-second synchronous enrichment API call
  is the bottleneck. Moving the enrichment to an async post-processing step (Lambda writes
  raw record to S3, separate process enriches) reduces Kinesis Lambda execution to <5 seconds
  per record — iterator age drops to near-zero as Lambda can process batches fast enough to
  keep pace with Kinesis throughput.
  **Issue 3 (Glue job failures on malformed files):** **Glue job bookmarks** prevent
  re-processing already-ingested files. A lightweight **pre-validation step** (schema check,
  required field presence) before the main ETL job quarantines the known-bad files and alerts
  the upstream team — the main job only processes validated files.
  **Issue 4 (Redshift degraded performance):** **Redshift Automatic Table Optimization**
  (ATO) is a cluster-level setting that enables background VACUUM (reclaims deleted row space,
  re-sorts unsorted rows) and automatic ANALYZE (updates query planner statistics) — resolving
  the 6-month maintenance gap without manual scripts.
  **Issue 5 (No data quality):** **AWS Glue Data Quality** (built into Glue ETL) defines
  DQ rules (e.g., completeness > 95%, value range, referential integrity) evaluated inline
  during the ETL job — records or files failing rules are routed to a quarantine location
  before reaching Redshift.

* **Why alternatives fail:**
  - **A)** Increasing shard count distributes the load but does not fix the root cause —
    with 4 partition key values, doubling shards to 40 still concentrates 80% of traffic on
    4 shards. Increasing Lambda timeout addresses the symptom (iterator age) but not the
    root cause (synchronous API call holding the processing thread). Manual VACUUM does not
    prevent future degradation — ATO provides ongoing automated maintenance.
  - **B)** Enhanced Fan-Out increases read throughput for consumers but does not address
    hot shard **write** imbalance — the problem is on the producer side (partition key choice),
    not the consumer side. Rewriting Lambda in Go reduces execution time marginally but does
    not fix the 45-second HTTP call — the call duration is network I/O bound, not compute
    bound; language choice is irrelevant.
  - **D)** Replacing Kinesis with SQS FIFO, Glue with EMR, and Redshift with Aurora constitutes
    a complete pipeline re-architecture — addressing operational issues in an existing pipeline
    with targeted improvements is the Well-Architected approach, not wholesale replacement.
    SQS FIFO has a throughput of 3,000 messages/second with batching — potentially insufficient
    for a high-volume Kinesis stream replacement.

</details>
</div>
