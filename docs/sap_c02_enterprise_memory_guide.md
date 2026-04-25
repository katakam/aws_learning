# SAP-C02 Enterprise Memory Guide: Organizations, IAM, Governance

This is for the common memory problem: enterprise-grade AWS services sound similar because they solve adjacent problems. Use the short hooks below.

## 1. The five permission layers

```text
SCP                = what the account is allowed to use at maximum
IAM policy         = what the principal is allowed to do
Resource policy    = who can access this resource
Permission boundary= maximum permissions for this user/role
Session policy     = maximum permissions for this temporary session
```

Exam shortcut:

```text
Explicit Deny anywhere = Deny
SCP must allow
IAM or resource policy must allow
Boundary/session must not cap
```

## 2. SCP memory

```text
SCP does not grant. SCP only limits.
```

Remember:

- SCP applies to member accounts.
- SCP does not apply to the management account.
- SCP affects the root user of member accounts.
- IAM administrator permissions cannot bypass SCP.
- Permission boundaries cannot bypass SCP.
- Deny in SCP wins.

Common trap:

```text
Question: root/parent SCP blocks action, account needs exception.
Wrong: IAM permission boundary or admin policy.
Right: change OU/SCP structure, often temporary OU carve-out.
```

## 3. IAM Identity Center memory

Choose IAM Identity Center for:

- workforce users
- SSO
- external IdP: Okta, Azure AD, Google Workspace
- multiple AWS accounts
- permission sets
- central human access

Avoid:

- long-lived IAM users for humans
- creating users in every account

Memory hook:

```text
Humans use Identity Center. Workloads use roles.
```

## 4. Cross-account access

```text
Human cross-account access  → Identity Center / federation / assume role
AWS service cross-account   → IAM role + trust policy
Resource exposed cross-acct → resource policy, sometimes plus IAM/KMS policy
Org-wide restriction        → SCP
```

Do not forget KMS:

```text
Encrypted cross-account access often needs both resource access and KMS key policy access.
```

## 5. Permission boundary

Use permission boundaries when delegating IAM administration.

Example:

```text
Developers can create roles, but no role they create can exceed this boundary.
```

Boundary does not:

- grant permissions by itself
- override SCP
- replace Organizations governance

Memory hook:

```text
Boundary is a safety fence for delegated IAM creation.
```

## 6. Organizations vs Control Tower

```text
Organizations = accounts, OUs, SCPs, consolidated billing.
Control Tower = opinionated landing zone on top of Organizations.
```

Choose Control Tower for:

- new multi-account landing zone
- account factory
- guardrails
- standardized account vending

Choose Organizations/SCP for:

- account hierarchy
- policy guardrails
- billing consolidation
- OU-based exceptions

## 7. Config vs Security Hub vs GuardDuty

```text
Config       = is the resource configured correctly?
GuardDuty   = is there suspicious/threat activity?
Security Hub= collect/security-posture dashboard and standards.
```

Examples:

- S3 bucket public? → Config rule / Security Hub control
- Crypto-mining behavior? → GuardDuty
- Aggregate findings across accounts? → Security Hub
- Deploy compliance checks at scale? → Config conformance packs

## 8. CloudTrail vs CloudWatch vs EventBridge

```text
CloudTrail  = who did what API call?
CloudWatch  = metrics/logs/alarms from systems/apps
EventBridge = event routing and reactions
```

Examples:

- Audit API activity across accounts → CloudTrail organization trail
- Alarm on CPU or Lambda errors → CloudWatch
- Trigger remediation on resource change/finding → EventBridge

## 9. RAM vs Resource Policy vs PrivateLink

```text
RAM             = share supported AWS resources with accounts/OUs/org
Resource policy = grant access to a specific resource
PrivateLink     = private network access to a service over interface endpoint
```

Examples:

- Share Transit Gateway/subnets/Resolver rules → RAM
- Allow another account to read S3 bucket → bucket policy
- Expose internal service privately to consumers → PrivateLink

## 10. Simple exam elimination rules

If answer says IAM user for workforce access:

```text
Usually wrong. Prefer Identity Center/federation.
```

If answer says permission boundary to bypass SCP:

```text
Wrong.
```

If answer says Security Hub detects threats:

```text
Wrong wording. GuardDuty detects; Security Hub aggregates.
```

If answer says SCP grants access:

```text
Wrong. SCP only limits maximum permissions.
```

If answer says resource policy overrides explicit deny:

```text
Wrong. Explicit deny wins.
```

## 11. Active recall prompts

Use these daily:

1. What does SCP do that IAM cannot?
2. What does IAM do that SCP cannot?
3. When do I choose Identity Center?
4. When do I choose Control Tower?
5. What is the difference between GuardDuty and Security Hub?
6. What does Config check?
7. Why cannot a permission boundary fix an SCP deny?
8. What policies are needed for cross-account encrypted S3 access?
9. When do I use RAM instead of a resource policy?
10. What is the first rule in AWS authorization evaluation?

Answers should be short. If you need long explanations, review again.
