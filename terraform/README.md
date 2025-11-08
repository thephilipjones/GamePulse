# GamePulse AWS Infrastructure - Terraform

Production-grade Infrastructure as Code (IaC) using Terraform modules for VPC networking and compute resources.

## Overview

- **Architecture**: Custom VPC with public/private subnets
- **Modules**: Separate VPC and Compute modules for reusability
- **Cloud Provider**: AWS (us-east-1 by default)
- **Instance Type**: EC2 t2.micro (free tier eligible)
- **OS**: Ubuntu 24.04 LTS
- **Pre-installed**: Docker CE, Docker Compose, Tailscale
- **Budget**: <$10/month (within AWS free tier for 12 months)
- **Security**: Defense-in-depth with specific IP and device-level SSH access

## Architecture

```
VPC (10.1.0.0/16)
├── Public Subnet (10.1.1.0/24)
│   ├── EC2 Instance (Ubuntu 24.04 + Docker + Tailscale)
│   ├── Elastic IP (static public IP)
│   └── Internet Gateway (outbound connectivity)
└── Private Subnet (10.1.2.0/24)
    └── Reserved for future RDS database

Security:
├── SSH: Your home IP + specific Tailscale devices ONLY
├── HTTP (80): Open to all (public dashboard)
└── HTTPS (443): Open to all (public dashboard)
```

## Module Structure

```
terraform/
├── main.tf                          # Root orchestration
├── variables.tf                     # Root variables
├── outputs.tf                       # Root outputs
├── providers.tf                     # AWS provider config
├── terraform.tfvars.example         # Configuration template
├── README.md                        # This file
├── PROVISIONING_CHECKLIST.md        # Deployment checklist
└── modules/
    ├── vpc/                         # VPC, subnets, routing
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── compute/                     # EC2, security, monitoring
        ├── main.tf
        ├── variables.tf
        ├── outputs.tf
        └── user_data.sh             # Bootstrap script
```

## Prerequisites

### Required Tools

1. **Terraform** >= 1.9.0
   ```bash
   # Install with tfenv (recommended)
   brew install tfenv
   tfenv install 1.9.8
   tfenv use 1.9.8
   ```

2. **AWS CLI** >= 2.x
   ```bash
   brew install awscli
   aws --version
   ```

### AWS Account Setup

1. **Create AWS Account** (if needed)
   - Sign up at https://aws.amazon.com/free/
   - Verify email and set up billing

2. **Create IAM User for Terraform**
   ```bash
   # Via AWS Console:
   # IAM → Users → Create User
   # User name: terraform-admin
   # Attach policies: AdministratorAccess
   # Create access key (CLI type)
   # Download credentials
   ```

3. **Configure AWS CLI**
   ```bash
   aws configure
   # AWS Access Key ID: [your key]
   # AWS Secret Access Key: [your secret]
   # Default region: us-east-1
   # Default output format: json
   ```

4. **Create SSH Key Pair** (local generation - more secure)
   ```bash
   # Generate ED25519 key pair locally
   ssh-keygen -t ed25519 -f ~/.ssh/gamepulse-key -C "gamepulse-ec2-access" -N ""

   # Verify keys created
   ls -lh ~/.ssh/gamepulse-key*
   # Should see: gamepulse-key (private, 600) and gamepulse-key.pub (public, 644)
   ```

   > **Why local?** Private key never leaves your machine, Terraform-friendly (can destroy/apply without losing access), and industry standard for IaC.

### Get Your IPs

```bash
# 1. Get your public home IP
curl -4 ifconfig.me
# Example: 203.0.113.10

# 2. Get your Tailscale device IPs
tailscale status
# Look for your machines
# Example: 100.64.0.10 and 100.64.0.20
```

### Configuration

1. **Create terraform.tfvars**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars** with your actual values:
   ```hcl
   # Your public home/office IPs
   admin_ip_cidrs = ["203.0.113.10/32"]

   # Your specific Tailscale device IPs (defense-in-depth)
   tailscale_device_ips = [
     "100.64.0.10/32",  # your-laptop
     "100.64.0.20/32",  # your-desktop
   ]
   ```

## Deployment Steps

### Step 1: Initialize & Validate

```bash
cd terraform

# Initialize (downloads modules and providers)
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt -recursive
```

### Step 2: Review Plan

```bash
# Generate execution plan
terraform plan

# Review output - should show:
# - 17 resources to create
# - VPC with public/private subnets
# - EC2 t2.micro instance
# - Security group with YOUR IPs only for SSH
```

Expected plan summary:
```
Plan: 17 to add, 0 to change, 0 to destroy.

VPC Module (8 resources):
  - VPC (10.0.0.0/16)
  - Internet Gateway
  - Public subnet (10.0.1.0/24)
  - Private subnet (10.0.2.0/24)
  - 2 route tables
  - 2 route table associations

Compute Module (9 resources):
  - EC2 instance (t2.micro, Ubuntu 24.04)
  - Elastic IP + association
  - Security group
  - IAM role + instance profile + policy attachment
  - 2 CloudWatch log groups
```

### Step 3: Apply Infrastructure

```bash
# Provision infrastructure
terraform apply

# Type 'yes' when prompted
# Wait 3-5 minutes for completion
```

### Step 4: Verify Deployment

```bash
# Get instance details
terraform output

# Test SSH connection
terraform output -raw ssh_command
# Then paste the command to connect

# Once connected:
docker --version
docker compose version
tailscale version
```

### Step 5: Connect Tailscale (Optional but Recommended)

```bash
# After SSH to instance:
# 1. Get Tailscale auth key from https://login.tailscale.com/admin/settings/keys
# 2. Connect:
sudo tailscale up --authkey=tskey-auth-xxxxx

# 3. Verify:
tailscale status

# Now you can SSH via Tailscale:
ssh ubuntu@gamepulse-api  # Using MagicDNS
```

## Security Configuration

### SSH Access Strategy (Defense-in-Depth)

```hcl
# Layer 1: Public IP restriction
admin_ip_cidrs = ["203.0.113.10/32"]  # Your home/office

# Layer 2: Device-level Tailscale restriction
tailscale_device_ips = [
  "100.64.0.10/32",  # Specific laptop
  "100.64.0.20/32",  # Specific desktop
]
```

**Why this approach?**
- **Public IP**: Direct access from home/office
- **Tailscale IPs**: Specific devices only (not entire Tailscale network)
- **Defense-in-depth**: Even if Tailscale account compromised, only YOUR 2 devices can SSH

**What this PREVENTS:**
- ❌ Random bot SSH attempts blocked by security group
- ❌ If Tailscale account compromised, attacker can't SSH from new device
- ❌ If home IP changes, still have Tailscale access
- ✅ You can SSH from home OR via Tailscale from anywhere

### Public Access

```
HTTP (80):  Open to 0.0.0.0/0 (public dashboard)
HTTPS (443): Open to 0.0.0.0/0 (public dashboard)
```

## Cost Breakdown

### AWS Free Tier (First 12 Months)
```
EC2 t2.micro:        $0/month (750 hours free)
Elastic IP:          $0/month (free when attached)
EBS gp3 20GB:        $0/month (30GB free)
CloudWatch Logs:     $0/month (5GB ingestion + storage free)
VPC:                 $0/month (VPC itself is free)
Data Transfer:       $0/month (15GB outbound free)
────────────────────────────────
Monthly Total:       $0.00 ✅
```

### After Free Tier Expires (Month 13+)
```
EC2 t2.micro:        ~$8.47/month
EBS gp3 20GB:        ~$1.60/month
CloudWatch Logs:     ~$0.50/month (light usage)
Data Transfer:       ~$0.50/month (light traffic)
────────────────────────────────
Monthly Total:       ~$11.07 ⚠️ (slightly over budget)
```

### Cost Optimization

**Reduce to <$10/month:**
1. Stop instance when not demoing: `aws ec2 stop-instances --instance-ids $(terraform output -raw instance_id)`
2. Reduce EBS to 10GB: saves $0.80/month
3. Set log retention to 3 days: reduces storage costs

## Management Commands

### View Infrastructure

```bash
# List all resources
terraform state list

# Show specific resource
terraform state show module.vpc.aws_vpc.main
terraform state show module.compute.aws_instance.app

# Show outputs
terraform output
terraform output -json
```

### Update Infrastructure

```bash
# Modify .tf files or variables
# Preview changes
terraform plan

# Apply changes
terraform apply
```

### Module-Specific Operations

```bash
# Target specific module
terraform plan -target=module.vpc
terraform apply -target=module.compute

# Refresh module
terraform init -upgrade
```

### Destroy Infrastructure

```bash
# DANGER: Deletes all resources
terraform destroy

# Type 'yes' to confirm
```

## Troubleshooting

### SSH Connection Issues

**Problem:** Connection refused
```bash
# Check instance state
terraform output instance_state

# Check security group
aws ec2 describe-security-groups --group-ids $(terraform output -raw security_group_id)

# Verify your IP hasn't changed
curl -4 ifconfig.me
# If changed, update terraform.tfvars and run terraform apply
```

**Problem:** Tailscale SSH not working
```bash
# SSH to instance via public IP first
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@$(terraform output -raw public_ip)

# Check Tailscale status
sudo tailscale status

# If not connected:
sudo tailscale up --authkey=YOUR_KEY
```

### Module Errors

**Problem:** Module not found
```bash
# Reinitialize
terraform init -upgrade

# Clean and reinit
rm -rf .terraform .terraform.lock.hcl
terraform init
```

**Problem:** Variables not passed correctly
```bash
# Check module variables in main.tf
# Verify outputs from vpc module match inputs to compute module
terraform console
> module.vpc.vpc_id
> module.compute.instance_id
```

## VPC Details

### Network Architecture

```
VPC: 10.1.0.0/16 (65,536 IPs)
├── Public Subnet: 10.1.1.0/24 (256 IPs)
│   ├── EC2 instances
│   ├── Future load balancers
│   └── Bastion hosts
└── Private Subnet: 10.1.2.0/24 (256 IPs)
    ├── Future RDS databases
    ├── Internal services
    └── No internet access (secure)
```

### Why This Design?

✅ **Production-ready**: Follows AWS best practices
✅ **Secure**: Private subnet has no internet access
✅ **Scalable**: Can add more subnets, multi-AZ later
✅ **Cost-effective**: No NAT Gateway ($32/month) for MVP
✅ **Future-proof**: Ready for RDS, load balancers, etc.

⚠️ **MVP Trade-off:** Private subnet has no internet. When you add RDS later, it won't need internet anyway.

## Module Benefits

**Why modules instead of flat structure?**

1. **Reusability**: VPC module can be used for dev/staging/prod
2. **Separation of concerns**: Networking separate from compute
3. **Testing**: Can test modules independently
4. **Maintainability**: Changes to VPC don't affect compute config
5. **Learning**: Industry-standard Terraform pattern

**Minimal but meaningful:**
- Only 2 modules (VPC, Compute)
- Not over-engineered
- Teaches module patterns
- Production-ready architecture

## Next Steps

After infrastructure is provisioned:

1. **Story 1.6**: Deploy GamePulse application to EC2
2. **Configure DNS**: Point domain to Elastic IP
3. **Setup HTTPS**: Install SSL certificate (Let's Encrypt)
4. **Enable monitoring**: CloudWatch alarms for CPU, disk, etc.
5. **Add RDS**: PostgreSQL in private subnet
6. **Multi-AZ**: Add second availability zone for HA

## References

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-best-practices.html)
- [Terraform Modules](https://www.terraform.io/language/modules)
- [GamePulse Architecture](../docs/architecture.md)
- [Tailscale Documentation](https://tailscale.com/kb/)

## Security Notes

**SSH Access Control:**
- Only YOUR specific IPs can SSH (defense-in-depth)
- Tailscale device-level restriction (not just network-level)
- Even with Tailscale access, only 2 specific devices allowed
- SSH key required (no password auth)

**Data Protection:**
- EBS volumes encrypted at rest
- CloudWatch logs retained for 7 days
- IAM least-privilege (EC2 can only write logs)

**Network Security:**
- Custom VPC (not default VPC)
- Public subnet for internet-facing resources only
- Private subnet for databases (future)
- Security group deny-by-default

**Compliance:**
- All resources tagged (Project, Environment, ManagedBy)
- Infrastructure as Code (audit trail via git)
- No hardcoded secrets (all in terraform.tfvars)
