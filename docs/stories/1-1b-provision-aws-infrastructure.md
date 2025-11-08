# Story 1.1b: Provision AWS Infrastructure with Terraform

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** ready-for-dev
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a DevOps engineer,
I want to provision AWS infrastructure using Terraform Infrastructure as Code,
So that I have a reproducible, version-controlled EC2 environment ready for deploying GamePulse.

---

## Acceptance Criteria

**Source:** [Tech Spec Epic 1 - AC-3: AWS Infrastructure Provisioning](../tech-spec-epic-1.md)

1. **Terraform Configuration Created**
   - [ ] Terraform modules created: ec2, iam, cloudwatch
   - [ ] Directory structure: terraform/ with main.tf, variables.tf, outputs.tf, providers.tf
   - [ ] terraform.tfvars.example provided (secrets excluded)
   - [ ] user_data.sh script for Docker installation

2. **Terraform Validation Passes**
   - [ ] `terraform init` executes without errors
   - [ ] `terraform validate` confirms configuration is syntactically valid
   - [ ] `terraform plan` executes without errors and shows expected resources

3. **AWS Infrastructure Provisioned**
   - [ ] `terraform apply` provisions EC2 t2.micro successfully
   - [ ] Elastic IP allocated and associated with EC2 instance
   - [ ] Security group configured: SSH (admin IP only), HTTP (80), HTTPS (443)
   - [ ] IAM role and instance profile attached to EC2 with CloudWatch permissions
   - [ ] CloudWatch log groups created: `/gamepulse/backend`, `/gamepulse/frontend`

4. **Infrastructure Accessible**
   - [ ] Can SSH to EC2 instance using provided key pair
   - [ ] EC2 instance has Docker and Docker Compose pre-installed (via user_data)
   - [ ] Elastic IP is static and reachable
   - [ ] terraform output returns instance_id, public_ip, instance_state

---

## Tasks / Subtasks

### Task 1.1b.1: Create Terraform Directory Structure (AC: #1)
- [ ] Create terraform/ directory in project root
- [ ] Create main.tf (main infrastructure definition)
- [ ] Create variables.tf (input variables: aws_region, instance_type, admin_ip_cidr)
- [ ] Create outputs.tf (output: instance_id, public_ip, instance_state)
- [ ] Create providers.tf (AWS provider configuration)
- [ ] Create terraform.tfvars.example (template without secrets)
- [ ] Update .gitignore to exclude terraform.tfvars and .terraform/ directory

### Task 1.1b.2: Define EC2 Instance Resource (AC: #1, #3)
- [ ] Define aws_instance resource in main.tf:
  - AMI: data source for Ubuntu 22.04 LTS (latest)
  - Instance type: t2.micro (free tier eligible)
  - Root block device: 20GB gp3 volume
  - IAM instance profile: reference to gamepulse_profile
  - Security group: reference to gamepulse_sg
  - User data: reference to user_data.sh script
  - Tags: Name=gamepulse-api, Environment=production, ManagedBy=terraform
- [ ] Create data source for Ubuntu 22.04 AMI (aws_ami)

### Task 1.1b.3: Configure Networking Resources (AC: #3)
- [ ] Define aws_eip resource for Elastic IP allocation
- [ ] Associate Elastic IP with EC2 instance
- [ ] Define aws_security_group resource:
  - Ingress rule: Port 22 (SSH) from var.admin_ip_cidr only
  - Ingress rule: Port 80 (HTTP) from 0.0.0.0/0
  - Ingress rule: Port 443 (HTTPS) from 0.0.0.0/0
  - Egress rule: All traffic to 0.0.0.0/0
  - Description tags for each rule

### Task 1.1b.4: Configure IAM Resources (AC: #3)
- [ ] Define aws_iam_role resource:
  - Name: gamepulse-ec2-role
  - Assume role policy: Allow ec2.amazonaws.com to assume role
- [ ] Define aws_iam_role_policy_attachment:
  - Attach CloudWatchAgentServerPolicy (arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy)
- [ ] Define aws_iam_instance_profile resource:
  - Name: gamepulse-instance-profile
  - Role reference: gamepulse_role

### Task 1.1b.5: Configure CloudWatch Log Groups (AC: #3)
- [ ] Define aws_cloudwatch_log_group resources:
  - Log group: /gamepulse/backend (retention: 7 days)
  - Log group: /gamepulse/frontend (retention: 7 days)

### Task 1.1b.6: Create User Data Script (AC: #3, #4)
- [ ] Create terraform/user_data.sh script:
  - Update apt package index
  - Install prerequisites (ca-certificates, curl, gnupg)
  - Add Docker GPG key
  - Add Docker repository
  - Install Docker CE and Docker Compose plugin
  - Add ubuntu user to docker group
  - Enable and start Docker service
- [ ] Reference user_data.sh in aws_instance resource via file()

### Task 1.1b.7: Define Variables and Outputs (AC: #1, #4)
- [ ] In variables.tf, define:
  - aws_region (default: "us-east-1")
  - instance_type (default: "t2.micro")
  - admin_ip_cidr (required, no default - user must provide their IP)
- [ ] In outputs.tf, export:
  - instance_id (EC2 instance ID)
  - public_ip (Elastic IP address)
  - instance_state (Current instance state: running/stopped)
- [ ] In terraform.tfvars.example, document variable values (without secrets)

### Task 1.1b.8: Validate and Apply Terraform Configuration (AC: #2, #3)
- [ ] Run `terraform init` to initialize working directory
- [ ] Run `terraform validate` to check syntax
- [ ] Run `terraform plan` to preview infrastructure changes
- [ ] Review plan output for expected resources (EC2, EIP, SG, IAM, CloudWatch)
- [ ] Run `terraform apply` to provision infrastructure
- [ ] Verify terraform apply completes without errors
- [ ] Run `terraform output` to capture instance_id and public_ip

### Task 1.1b.9: Verify Infrastructure Accessibility (AC: #4)
- [ ] Retrieve public IP: `terraform output -raw public_ip`
- [ ] Test SSH access: `ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<PUBLIC_IP>`
- [ ] Verify Docker installed: `docker --version` on EC2 instance
- [ ] Verify Docker Compose installed: `docker compose version` on EC2 instance
- [ ] Verify ubuntu user in docker group: `groups ubuntu | grep docker`
- [ ] Test Elastic IP persistence: Stop and start instance, verify IP unchanged

### Task 1.1b.10: Testing (AC: #1, #2, #3, #4)
- [ ] Test terraform plan with invalid admin_ip_cidr (should fail validation)
- [ ] Test SSH access restricted: Verify SSH from non-admin IP is blocked
- [ ] Test HTTP/HTTPS access open: Verify ports 80/443 accessible from any IP
- [ ] Test IAM permissions: Verify EC2 instance can write to CloudWatch logs
- [ ] Test cost estimation: Run `terraform plan` with cost estimation tools
- [ ] Document Terraform state management (local state file location)

---

## Dev Notes

### Architecture Patterns and Constraints

This story establishes the AWS infrastructure foundation using Terraform Infrastructure as Code (IaC), providing:

- **Terraform IaC**: Version-controlled infrastructure provisioning with plan/apply workflow
- **EC2 t2.micro**: Single instance within AWS free tier (1 vCPU, 1GB RAM, 20GB storage)
- **Elastic IP**: Static public IP address for consistent DNS mapping
- **Security Group**: Firewall rules restricting SSH to admin IP only, HTTP/HTTPS open
- **IAM Least Privilege**: EC2 role with only CloudWatch Logs write permissions
- **CloudWatch Logging**: Centralized log aggregation for /gamepulse/backend and /gamepulse/frontend
- **User Data Bootstrap**: Docker and Docker Compose pre-installed on instance launch

**Key Constraints:**
- AWS free tier limits: EC2 t2.micro only, 750 hours/month for 12 months
- SSH access restricted to admin IP for security (no 0.0.0.0/0 SSH access)
- Terraform state stored locally (not S3 backend) for MVP simplicity
- Single availability zone (no multi-AZ redundancy for MVP)
- No auto-scaling or load balancing (single instance deployment)
- Budget constraint: Infrastructure must stay under $10/month

### Testing Standards Summary

For this infrastructure provisioning story:
- **Terraform Validation**: `terraform validate` and `terraform plan` must pass
- **Integration Testing**: Verify `terraform apply` provisions all resources successfully
- **Security Testing**: Verify SSH restricted to admin IP, HTTP/HTTPS open to all
- **Accessibility Testing**: Verify SSH access works, Docker installed, Elastic IP persistent
- **Cost Testing**: Estimate monthly cost using AWS pricing calculator (target: <$10/month)
- **No Unit Tests Required**: Infrastructure as Code validation via Terraform commands
- **Manual Verification**: SSH login, docker --version, security group rules in AWS console

### Project Structure Notes

This story creates the Terraform infrastructure configuration:

```
gamepulse/
├── terraform/
│   ├── main.tf              # EC2, EIP, Security Group, IAM, CloudWatch
│   ├── variables.tf         # Input variables (region, instance_type, admin_ip)
│   ├── outputs.tf           # Exported values (public_ip, instance_id)
│   ├── providers.tf         # AWS provider configuration
│   ├── terraform.tfvars.example  # Variable template (no secrets)
│   └── user_data.sh         # Docker installation bootstrap script
└── .gitignore               # Exclude terraform.tfvars, .terraform/
```

**Alignment Notes:**
- Terraform structure matches tech spec lines 90-102
- Follows AWS best practices: IAM least privilege, security group restrictive ingress
- No conflicts with Story 1.1 (template initialization) - stories are independent
- Prepares infrastructure for Story 1.6 (deployment to AWS EC2)

### Learnings from Previous Story

**From Story 1-1-initialize-fastapi-template (Status: ready-for-dev)**

Story 1.1 has not been implemented yet (status: ready-for-dev), so no completion notes available. However, key context for this story:

- **Template Initialized**: Story 1.1 establishes the FastAPI template locally with Docker Compose
- **Local Development Ready**: Docker Compose orchestration configured for local dev environment
- **No Deployment Yet**: Story 1.1 does NOT deploy to cloud - that's handled by Story 1.6
- **AWS Provisioning Independent**: This story (1.1b) provisions AWS infrastructure in parallel, does not depend on Story 1.1 completion
- **Deployment Story Dependency**: Story 1.6 (Deploy to AWS EC2) will depend on BOTH Story 1.1 (template) and Story 1.1b (infrastructure) being completed

**Story Sequencing Note:**
Stories 1.1 and 1.1b can be worked in parallel. Story 1.6 (deployment) requires both to be complete.

[Source: docs/sprint-status.yaml - development_status section]
[Source: docs/stories/story-1.1-initialize-fastapi-template.md#Dev-Agent-Record]

### References

All technical details sourced from approved project documentation:

- [Source: docs/tech-spec-epic-1.md - AC-3: AWS Infrastructure Provisioning (lines 562-569)]
- [Source: docs/tech-spec-epic-1.md - AWS Infrastructure table (lines 79-88)]
- [Source: docs/tech-spec-epic-1.md - Terraform Module Structure (lines 90-102)]
- [Source: docs/tech-spec-epic-1.md - Dependencies table (line 523: Terraform 1.9+)]
- [Source: docs/architecture.md - Decision Summary (line 52: Docker Compose + AWS EC2)]
- [Source: docs/epics.md - Epic 1: Project Foundation & Infrastructure]
- [Source: docs/PRD.md - NFR-6.1: Budget constraints (<$10/month)]

---

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-1b-provision-aws-infrastructure.context.xml) - Generated 2025-11-07

### Agent Model Used

TBD (will be filled during implementation)

### Debug Log References

TBD

### Completion Notes

- [ ] TBD (Developer will add completion notes here)

### File List

TBD (Developer will list all files created/modified during implementation)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-07 | Philip | Initial story draft (from epic level) |
| 2025-11-07 | Bob (SM) | Regenerated with proper BMM structure, citations, and traceability |
