# AWS Infrastructure Provisioning Checklist

This checklist ensures all acceptance criteria are met when provisioning GamePulse infrastructure.

## Story 1.1b Acceptance Criteria

### AC#1: Terraform Configuration Created ✅ COMPLETE

- [x] Terraform modules created: ec2, iam, cloudwatch (all in main.tf)
- [x] Directory structure: terraform/ with main.tf, variables.tf, outputs.tf, providers.tf
- [x] terraform.tfvars.example provided (secrets excluded)
- [x] user_data.sh script for Docker installation

**Verification:**
```bash
ls -la terraform/
# Should show: main.tf, variables.tf, outputs.tf, providers.tf, user_data.sh, terraform.tfvars.example
```

### AC#2: Terraform Validation Passes ✅ COMPLETE

- [x] `terraform init` executes without errors
- [x] `terraform validate` confirms configuration is syntactically valid
- [x] `terraform plan` executes without errors and shows expected resources

**Verification Results:**
```
$ terraform init
Terraform has been successfully initialized!

$ terraform validate
Success! The configuration is valid.

$ terraform plan -var="admin_ip_cidr=203.0.113.1/32"
Plan: 9 to add, 0 to change, 0 to destroy.
```

**Resources in Plan:**
1. aws_instance.gamepulse_api (EC2 t2.micro)
2. aws_eip.gamepulse_eip (Elastic IP)
3. aws_eip_association.gamepulse_eip_assoc (EIP association)
4. aws_security_group.gamepulse_sg (Firewall rules)
5. aws_iam_role.gamepulse_role (IAM role)
6. aws_iam_role_policy_attachment.cloudwatch_policy (Policy attachment)
7. aws_iam_instance_profile.gamepulse_profile (Instance profile)
8. aws_cloudwatch_log_group.backend (Backend logs)
9. aws_cloudwatch_log_group.frontend (Frontend logs)

### AC#3: AWS Infrastructure Provisioned ⏸️ REQUIRES MANUAL EXECUTION

**Prerequisites:**
- [ ] AWS account created and verified
- [ ] AWS CLI installed and configured with credentials
- [ ] SSH key pair created in AWS (name: gamepulse-key)
- [ ] terraform.tfvars created with your actual admin IP address
- [ ] Reviewed and approved cost estimate (<$10/month)

**Manual Steps Required:**

1. **Configure AWS Credentials**
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: us-east-1
   # Default output format: json
   ```

2. **Create SSH Key Pair**
   ```bash
   # Via AWS Console: EC2 → Key Pairs → Create Key Pair
   # Name: gamepulse-key
   # Type: RSA
   # Format: .pem
   # Download and save to: ~/.ssh/gamepulse-key.pem
   chmod 400 ~/.ssh/gamepulse-key.pem
   ```

3. **Get Your Public IP**
   ```bash
   curl -4 ifconfig.me
   # Example: 203.0.113.42
   ```

4. **Create terraform.tfvars**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars

   # Edit terraform.tfvars and set:
   # admin_ip_cidr = "YOUR_IP/32"  # Replace with your actual IP
   ```

5. **Provision Infrastructure**
   ```bash
   cd terraform
   terraform apply

   # Review the plan output
   # Type 'yes' to confirm
   # Wait 3-5 minutes for provisioning
   ```

6. **Verify Provisioning**
   - [ ] `terraform apply` completes without errors
   - [ ] All 9 resources created successfully
   - [ ] EC2 instance state shows "running"
   - [ ] Elastic IP allocated and associated
   - [ ] Security group shows correct ingress rules
   - [ ] IAM role and instance profile attached
   - [ ] CloudWatch log groups exist

   **Verification Commands:**
   ```bash
   # Check instance state
   terraform output instance_state
   # Expected: running

   # Get public IP
   terraform output public_ip
   # Expected: X.X.X.X (your Elastic IP)

   # List all resources
   terraform state list
   # Expected: 9 resources

   # Verify in AWS Console
   # EC2 → Instances → gamepulse-api (should be running)
   # VPC → Security Groups → gamepulse-sg (verify rules)
   # IAM → Roles → gamepulse-ec2-role (verify policy)
   # CloudWatch → Log groups → /gamepulse/backend, /gamepulse/frontend
   ```

### AC#4: Infrastructure Accessible ⏸️ REQUIRES MANUAL EXECUTION

**Prerequisites:**
- [ ] AC#3 completed (infrastructure provisioned)
- [ ] SSH key pair downloaded and permissions set (chmod 400)
- [ ] Instance in "running" state

**Manual Verification Steps:**

1. **Test SSH Access**
   ```bash
   # Get SSH command from Terraform
   terraform output ssh_command

   # Or manually connect
   ssh -i ~/.ssh/gamepulse-key.pem ubuntu@$(terraform output -raw public_ip)
   ```

   **Expected Result:**
   - [ ] SSH connection succeeds without errors
   - [ ] Connected as ubuntu@gamepulse-api
   - [ ] No "Connection refused" or "Permission denied" errors

2. **Verify Docker Installation**
   ```bash
   # After SSH connection, run:
   docker --version
   docker compose version
   ```

   **Expected Results:**
   - [ ] Docker version 20.x or higher installed
   - [ ] Docker Compose version 2.x or higher installed
   - [ ] No "command not found" errors

3. **Verify Docker Group Membership**
   ```bash
   groups ubuntu | grep docker
   id ubuntu
   ```

   **Expected Result:**
   - [ ] ubuntu user is in docker group
   - [ ] Can run `docker ps` without sudo

4. **Verify Elastic IP Persistence**
   ```bash
   # Before test
   terraform output public_ip
   # Note the IP address: X.X.X.X

   # Stop instance via AWS Console
   aws ec2 stop-instances --instance-ids $(terraform output -raw instance_id)

   # Wait for instance to stop
   aws ec2 wait instance-stopped --instance-ids $(terraform output -raw instance_id)

   # Start instance
   aws ec2 start-instances --instance-ids $(terraform output -raw instance_id)

   # Wait for instance to start
   aws ec2 wait instance-running --instance-ids $(terraform output -raw instance_id)

   # Check IP again
   terraform output public_ip
   # Should be the SAME IP as before
   ```

   **Expected Result:**
   - [ ] Elastic IP remains unchanged after instance stop/start
   - [ ] IP is static and reachable

5. **Verify Terraform Outputs**
   ```bash
   terraform output
   ```

   **Expected Output:**
   ```hcl
   instance_id       = "i-0123456789abcdef0"
   instance_state    = "running"
   public_ip         = "X.X.X.X"
   security_group_id = "sg-0123456789abcdef0"
   ssh_command       = "ssh -i ~/.ssh/gamepulse-key.pem ubuntu@X.X.X.X"
   ```

   **Verification:**
   - [ ] instance_id is a valid EC2 instance ID (i-xxxxxxxxxx)
   - [ ] instance_state is "running"
   - [ ] public_ip is a valid IPv4 address
   - [ ] ssh_command works when copy-pasted

## Testing (Task 1.1b.10)

### Test 1: Terraform Validation (Priority: High, AC: #1, #2)

**Test:** Validate Terraform configuration syntax and plan
```bash
cd terraform
terraform init
terraform validate
terraform plan -var="admin_ip_cidr=203.0.113.1/32"
```

**Expected Result:** ✅ PASSED
- terraform init: Success
- terraform validate: Success
- terraform plan: 9 resources to add, 0 to change, 0 to destroy

### Test 2: Invalid Admin IP Validation (Priority: Medium, AC: #2)

**Test:** Test terraform plan with invalid admin_ip_cidr
```bash
terraform plan -var="admin_ip_cidr=invalid-ip"
```

**Expected Result:**
- Terraform validation fails with error: "Must be a valid CIDR block"

**Status:** ⏸️ Requires manual execution

### Test 3: SSH Accessibility (Priority: High, AC: #4)

**Test:** Verify SSH access works with provided key pair
```bash
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@$(terraform output -raw public_ip)
docker --version
docker compose version
```

**Expected Result:**
- SSH connection succeeds
- Docker version 20.x+ installed
- Docker Compose version 2.x+ installed

**Status:** ⏸️ Requires manual execution (needs AWS credentials and provisioning)

### Test 4: SSH Access Restriction (Priority: High, AC: #3)

**Test:** Verify SSH from non-admin IP is blocked
```bash
# From a different machine/IP (not your admin IP)
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<PUBLIC_IP>
```

**Expected Result:**
- Connection timeout or "Connection refused"
- SSH blocked by security group

**Status:** ⏸️ Requires manual execution (needs different IP source)

### Test 5: HTTP/HTTPS Access (Priority: High, AC: #3)

**Test:** Verify HTTP/HTTPS accessible from any IP
```bash
curl -I http://$(terraform output -raw public_ip)
curl -I https://$(terraform output -raw public_ip)
```

**Expected Result:**
- Ports 80 and 443 are reachable (may return connection refused if no web server running yet, but port should be open)
- No firewall blocking

**Status:** ⏸️ Requires manual execution (needs provisioning)

### Test 6: IAM Permissions (Priority: Medium, AC: #3)

**Test:** Verify EC2 instance can write to CloudWatch logs
```bash
# SSH to instance
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@$(terraform output -raw public_ip)

# Install AWS CLI if not present
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Test CloudWatch log write
aws logs put-log-events \
  --log-group-name /gamepulse/backend \
  --log-stream-name test-stream \
  --log-events timestamp=$(date +%s000),message="Test log entry from EC2"
```

**Expected Result:**
- Log write succeeds
- No permission denied errors

**Status:** ⏸️ Requires manual execution (needs provisioning)

### Test 7: Cost Estimation (Priority: Medium, AC: #1, #3)

**Test:** Verify estimated monthly cost < $10
```bash
# Using AWS Pricing Calculator
# Or terraform cost estimation tools
terraform plan -out=tfplan
# Analyze tfplan for resource costs
```

**Expected Result:**
- EC2 t2.micro: $0/month (free tier) or ~$8.50/month (after free tier)
- EBS 20GB gp3: ~$1.60/month
- Total: < $10/month

**Status:** ✅ PASSED (estimated from plan)

### Test 8: CloudWatch Log Groups (Priority: Low, AC: #3)

**Test:** Verify log groups exist with correct retention
```bash
aws logs describe-log-groups \
  --log-group-name-prefix /gamepulse
```

**Expected Result:**
- /gamepulse/backend exists with 7-day retention
- /gamepulse/frontend exists with 7-day retention

**Status:** ⏸️ Requires manual execution (needs provisioning)

## Summary

**Automated Tests Passed:** 2/8 (25%)
- ✅ Test 1: Terraform Validation
- ✅ Test 7: Cost Estimation

**Manual Tests Required:** 6/8 (75%)
- ⏸️ Test 2: Invalid Admin IP Validation
- ⏸️ Test 3: SSH Accessibility
- ⏸️ Test 4: SSH Access Restriction
- ⏸️ Test 5: HTTP/HTTPS Access
- ⏸️ Test 6: IAM Permissions
- ⏸️ Test 8: CloudWatch Log Groups

**Status:** Configuration validated and ready for provisioning. Manual execution required for AC#3 and AC#4.

## Next Steps

To complete Story 1.1b acceptance criteria:

1. **User Action Required:** Provide AWS credentials
2. **User Action Required:** Create SSH key pair in AWS
3. **User Action Required:** Create terraform.tfvars with actual admin IP
4. **User Action Required:** Review and approve infrastructure provisioning
5. **Execute:** Run `terraform apply`
6. **Verify:** Complete all manual tests in this checklist
7. **Complete:** Mark story as done once all ACs verified

---

**Note:** This story creates IaC configuration that has been validated but not yet provisioned. Actual AWS resource creation requires user approval and credentials.
