# Auto-Sync Infrastructure Values via Parameter Store

## Problem

GitHub Actions deployment currently relies on manually-managed GitHub secrets for infrastructure values:
- `AWS_EC2_INSTANCE_ID` - Changes when instance is recreated
- `AWS_GITHUB_ACTIONS_ROLE_ARN` - Static but Terraform-managed
- `ECR_BACKEND_URL` - Static but Terraform-managed
- `ECR_FRONTEND_URL` - Static but Terraform-managed
- `DOMAIN_PRODUCTION` - Static constant
- `AWS_DEPLOYMENT_PATH` - Static constant

**Issue**: When Terraform recreates infrastructure (e.g., EC2 instance), GitHub secrets become stale and must be manually updated via `scripts/sync-terraform-to-github-secrets.sh`. This causes deployment failures if forgotten.

**Example**: The EC2 instance ID changed, causing `AccessDeniedException` errors until the GitHub secret was manually updated to match the new instance ID in the IAM policy.

## Proposed Solution

**Replace GitHub secrets with AWS Parameter Store lookups** - let Terraform manage infrastructure values as SSM parameters, and have GitHub Actions fetch them dynamically at runtime.

### Benefits

✅ **Zero manual sync** - Terraform automatically updates Parameter Store when infrastructure changes
✅ **Single source of truth** - Parameter Store is authoritative, no drift between Terraform and GitHub
✅ **Already authenticated** - OIDC role already has Parameter Store read access
✅ **Atomic updates** - Terraform ensures IAM policies and resource IDs stay in sync
✅ **Cost**: FREE (Parameter Store standard tier, < 10,000 parameters)
✅ **Audit trail** - Parameter history tracked in AWS

### Current State

Some values are already in Parameter Store (via `terraform/modules/secrets/main.tf`):
- `/gamepulse/production/docker/backend_image` (ECR backend URL)
- `/gamepulse/production/docker/frontend_image` (ECR frontend URL)
- `/gamepulse/production/app/domain` (production domain)

Missing from Parameter Store:
- `/gamepulse/shared/infrastructure/instance_id` (EC2 instance ID)
- `/gamepulse/shared/infrastructure/github_actions_role_arn` (IAM role ARN)

## Implementation Plan

### Phase 1: Add Infrastructure Parameters to Terraform

**File: `terraform/main.tf`** (add after module definitions):

```hcl
# ============================================================================
# Infrastructure Metadata - Shared Parameters for CI/CD
# ============================================================================
# These parameters are read by GitHub Actions during deployment to get
# current infrastructure state (instance ID, role ARN, etc.)

resource "aws_ssm_parameter" "instance_id" {
  name        = "/gamepulse/shared/infrastructure/instance_id"
  description = "Current EC2 instance ID for SSM deployments"
  type        = "String"
  value       = module.compute.instance_id

  tags = merge(
    local.common_tags,
    {
      Name        = "/gamepulse/shared/infrastructure/instance_id"
      Description = "Auto-updated by Terraform when instance changes"
    }
  )
}

resource "aws_ssm_parameter" "github_actions_role_arn" {
  name        = "/gamepulse/shared/infrastructure/github_actions_role_arn"
  description = "IAM role ARN for GitHub Actions OIDC authentication"
  type        = "String"
  value       = module.github_oidc.github_actions_role_arn

  tags = merge(
    local.common_tags,
    {
      Name        = "/gamepulse/shared/infrastructure/github_actions_role_arn"
      Description = "Auto-updated by Terraform if role is recreated"
    }
  )
}
```

**Apply changes**:
```bash
cd terraform
terraform apply
```

### Phase 2: Update GitHub Actions Workflow

**File: `.github/workflows/deploy.yml`**

Replace hardcoded secrets with Parameter Store lookups:

```yaml
deploy:
  name: Deploy to EC2
  runs-on: ubuntu-latest
  needs: [build-backend, build-frontend]
  steps:
    - name: Configure AWS credentials via OIDC
      uses: aws-actions/configure-aws-credentials@v5
      with:
        role-to-assume: ${{ secrets.AWS_GITHUB_ACTIONS_ROLE_ARN }}  # Keep this one for initial auth
        aws-region: us-east-1
        role-session-name: GitHubActionsDeployment

    - name: Get infrastructure values from Parameter Store
      run: |
        echo "Fetching infrastructure configuration from Parameter Store..."

        # Fetch all values in parallel (faster than sequential)
        INSTANCE_ID=$(aws ssm get-parameter \
          --name '/gamepulse/shared/infrastructure/instance_id' \
          --query 'Parameter.Value' \
          --output text)

        ECR_BACKEND=$(aws ssm get-parameter \
          --name '/gamepulse/production/docker/backend_image' \
          --query 'Parameter.Value' \
          --output text)

        ECR_FRONTEND=$(aws ssm get-parameter \
          --name '/gamepulse/production/docker/frontend_image' \
          --query 'Parameter.Value' \
          --output text)

        DOMAIN=$(aws ssm get-parameter \
          --name '/gamepulse/production/app/domain' \
          --query 'Parameter.Value' \
          --output text)

        # Export to workflow environment
        echo "INSTANCE_ID=$INSTANCE_ID" >> $GITHUB_ENV
        echo "ECR_BACKEND_URL=$ECR_BACKEND" >> $GITHUB_ENV
        echo "ECR_FRONTEND_URL=$ECR_FRONTEND" >> $GITHUB_ENV
        echo "DOMAIN_PRODUCTION=$DOMAIN" >> $GITHUB_ENV

        # Hardcoded constant (never changes, no need for Parameter Store)
        echo "AWS_DEPLOYMENT_PATH=/opt/gamepulse" >> $GITHUB_ENV

        echo "✅ Infrastructure configuration loaded"

    - name: Deploy via SSM Session Manager
      run: |
        echo "Deploying to EC2 instance: $INSTANCE_ID via SSM Session Manager"

        # Use INSTANCE_ID from environment (loaded from Parameter Store)
        aws ssm send-command \
          --instance-ids "$INSTANCE_ID" \
          --document-name "AWS-RunShellScript" \
          ...
```

**Update other jobs** (build-backend, build-frontend) similarly:

```yaml
build-backend:
  # ... existing steps ...

  - name: Get ECR backend URL from Parameter Store
    run: |
      ECR_BACKEND=$(aws ssm get-parameter \
        --name '/gamepulse/production/docker/backend_image' \
        --query 'Parameter.Value' \
        --output text)
      echo "ECR_BACKEND_URL=$ECR_BACKEND" >> $GITHUB_ENV

  - name: Build and push backend image
    uses: docker/build-push-action@v5
    with:
      context: ./backend
      push: true
      platforms: linux/arm64
      tags: |
        ${{ env.ECR_BACKEND_URL }}:${{ github.sha }}
        ${{ env.ECR_BACKEND_URL }}:latest
```

### Phase 3: Remove GitHub Secrets

**After verifying workflow works**:

```bash
# Delete obsolete secrets (keep only AWS_GITHUB_ACTIONS_ROLE_ARN for initial OIDC auth)
gh secret delete AWS_EC2_INSTANCE_ID
gh secret delete ECR_BACKEND_URL
gh secret delete ECR_FRONTEND_URL
gh secret delete DOMAIN_PRODUCTION
gh secret delete AWS_DEPLOYMENT_PATH
```

**Note**: Keep `AWS_GITHUB_ACTIONS_ROLE_ARN` as a GitHub secret because it's needed for the initial OIDC authentication step (chicken-and-egg problem - can't fetch from Parameter Store until authenticated).

### Phase 4: Cleanup & Documentation

1. **Delete obsolete script**: `scripts/sync-terraform-to-github-secrets.sh` (no longer needed)

2. **Update CLAUDE.md**:
   - Remove references to manual secret syncing
   - Document the Parameter Store approach
   - Add section: "How Infrastructure Values are Managed"

3. **Add verification step** to deployment workflow:
   ```yaml
   - name: Verify infrastructure values are current
     run: |
       echo "Instance ID from Parameter Store: $INSTANCE_ID"
       echo "Instance ID in IAM policy: (matches Terraform state)"
       # Could add a check here to verify they match
   ```

## Migration Path

**Zero-downtime migration**:

1. Apply Terraform changes (adds parameters, doesn't break existing workflow)
2. Update GitHub Actions workflow to use Parameter Store
3. Test deployment (values come from Parameter Store, but GitHub secrets still exist as backup)
4. After 1-2 successful deployments, delete GitHub secrets
5. Remove sync script from repository

## IAM Permissions

The GitHub Actions OIDC role already has Parameter Store read access via this policy (in `terraform/modules/compute/main.tf`):

```hcl
{
  "Sid": "AllowParameterStoreRead",
  "Effect": "Allow",
  "Action": [
    "ssm:GetParameter",
    "ssm:GetParameters",
    "ssm:GetParametersByPath"
  ],
  "Resource": [
    "arn:aws:ssm:${var.aws_region}:${account_id}:parameter/gamepulse/${var.environment}/*",
    "arn:aws:ssm:${var.aws_region}:${account_id}:parameter/gamepulse/shared/*"
  ]
}
```

✅ No IAM changes needed - access to `/gamepulse/shared/*` already granted.

## Testing Strategy

**Before deleting GitHub secrets**:

1. Add infrastructure parameters to Terraform
2. Run `terraform apply`
3. Update workflow to fetch from Parameter Store
4. Trigger deployment - verify it uses Parameter Store values
5. Check CloudWatch logs to confirm correct instance ID was used
6. Manually change a parameter value in AWS Console - verify next deployment uses the new value
7. If all tests pass, delete GitHub secrets

**Rollback plan** (if issues):
- Revert workflow changes
- Re-add GitHub secrets from Terraform outputs
- Keep Parameter Store parameters (harmless if not used)

## Cost Analysis

**Parameter Store Standard Tier**:
- FREE for up to 10,000 parameters
- FREE for standard throughput (40 TPS per account)
- Current usage: ~30 parameters total (production + shared)
- **Cost**: $0.00/month

## Related Issues

- Fixes the manual sync problem that caused deployment failures when EC2 instance ID changed
- Eliminates the `sync-terraform-to-github-secrets.sh` script
- Aligns with AWS best practices (single source of truth)
- Reduces GitHub secret sprawl (from 6 secrets to 1)

## Priority

**Medium** - Nice to have, but not urgent:
- Current workaround (manual sync script) works fine if you remember to run it
- Main benefit is automation and reducing human error
- Good cleanup task for future sprint

## Effort Estimate

**~1-2 hours**:
- 15 min: Add Terraform parameters
- 15 min: Apply and verify in AWS
- 30 min: Update GitHub Actions workflow
- 15 min: Test deployment
- 15 min: Delete secrets and cleanup
- 15 min: Update documentation

## References

- [AWS Parameter Store Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- Related to Epic 9 (Infrastructure Automation) in product roadmap
