#!/usr/bin/env bash
# ============================================================================
# Sync Terraform Outputs to AWS Parameter Store
# ============================================================================
# Purpose: Automatically copy infrastructure values from Terraform outputs
#          to AWS Parameter Store for application runtime configuration
#
# Usage:
#   ./scripts/sync-terraform-outputs.sh [environment]
#
# Example:
#   ./scripts/sync-terraform-outputs.sh production
#
# What it does:
#   - Reads Terraform outputs from terraform/
#   - Updates Parameter Store with infrastructure values
#   - Preserves SecureString parameters (never overwrites secrets)
#   - Idempotent (safe to run multiple times)
#
# Parameters Updated:
#   - /gamepulse/{env}/docker/backend_image
#   - /gamepulse/{env}/docker/frontend_image
#   - /gamepulse/{env}/docker/tag
#   - /gamepulse/{env}/infrastructure/instance_id
#   - /gamepulse/{env}/infrastructure/public_ip
#   - /gamepulse/{env}/infrastructure/vpc_id
#   - /gamepulse/{env}/infrastructure/security_group_id
# ============================================================================

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${1:-production}
TERRAFORM_DIR="terraform"

# Counters
UPDATED_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Update a Parameter Store parameter (String type only)
update_parameter() {
    local param_name=$1
    local param_value=$2

    if [ -z "$param_value" ] || [ "$param_value" = "null" ]; then
        log_warn "Skipping $param_name (value is empty or null)"
        ((SKIPPED_COUNT++)) || true
        return 0
    fi

    # Check if parameter exists and its type
    local existing_type=$(aws ssm describe-parameters \
        --filters "Key=Name,Values=$param_name" \
        --region "$AWS_REGION" \
        --query 'Parameters[0].Type' \
        --output text 2>/dev/null || echo "")

    if [ "$existing_type" = "SecureString" ]; then
        log_warn "Skipping $param_name (SecureString - preserving encrypted value)"
        ((SKIPPED_COUNT++)) || true
        return 0
    fi

    # Update or create parameter
    if aws ssm put-parameter \
        --name "$param_name" \
        --value "$param_value" \
        --type "String" \
        --overwrite \
        --region "$AWS_REGION" \
        --output text &>/dev/null; then

        log_info "✅ Updated: $param_name → $param_value"
        ((UPDATED_COUNT++)) || true
    else
        log_error "❌ Failed to update: $param_name"
        ((ERROR_COUNT++)) || true
    fi
}

# ============================================================================
# Validation
# ============================================================================

log_info "Syncing Terraform outputs to Parameter Store..."
log_info "Environment: $ENVIRONMENT"
log_info "AWS Region: $AWS_REGION"
echo ""

# Check if Terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    log_error "Terraform directory not found: $TERRAFORM_DIR"
    log_error "Run this script from the project root directory"
    exit 1
fi

# Check if Terraform state exists
if [ ! -f "$TERRAFORM_DIR/terraform.tfstate" ]; then
    log_error "Terraform state not found: $TERRAFORM_DIR/terraform.tfstate"
    log_error "Run 'terraform apply' first to create infrastructure"
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install it:"
    log_error "  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    log_error "Run: aws configure"
    exit 1
fi

log_info "✅ Validations passed"
echo ""

# ============================================================================
# Extract Terraform Outputs
# ============================================================================

log_info "Extracting Terraform outputs..."

cd "$TERRAFORM_DIR"

# Get all outputs as JSON
TF_OUTPUTS=$(terraform output -json 2>/dev/null)

if [ -z "$TF_OUTPUTS" ] || [ "$TF_OUTPUTS" = "{}" ]; then
    log_error "No Terraform outputs found"
    log_error "Ensure 'terraform apply' has been run successfully"
    exit 1
fi

# Extract specific outputs
ECR_BACKEND=$(echo "$TF_OUTPUTS" | jq -r '.ecr_backend_repository_url.value // empty')
ECR_FRONTEND=$(echo "$TF_OUTPUTS" | jq -r '.ecr_frontend_repository_url.value // empty')
INSTANCE_ID=$(echo "$TF_OUTPUTS" | jq -r '.instance_id.value // empty')
PUBLIC_IP=$(echo "$TF_OUTPUTS" | jq -r '.public_ip.value // empty')
VPC_ID=$(echo "$TF_OUTPUTS" | jq -r '.vpc_id.value // empty')
SECURITY_GROUP_ID=$(echo "$TF_OUTPUTS" | jq -r '.security_group_id.value // empty')

cd ..

log_info "✅ Terraform outputs extracted"
echo ""

# ============================================================================
# Update Parameter Store
# ============================================================================

log_info "Updating Parameter Store parameters..."
echo ""

# Docker configuration
update_parameter "/gamepulse/$ENVIRONMENT/docker/backend_image" "$ECR_BACKEND"
update_parameter "/gamepulse/$ENVIRONMENT/docker/frontend_image" "$ECR_FRONTEND"
update_parameter "/gamepulse/$ENVIRONMENT/docker/tag" "latest"

echo ""

# Infrastructure metadata
update_parameter "/gamepulse/$ENVIRONMENT/infrastructure/instance_id" "$INSTANCE_ID"
update_parameter "/gamepulse/$ENVIRONMENT/infrastructure/public_ip" "$PUBLIC_IP"
update_parameter "/gamepulse/$ENVIRONMENT/infrastructure/vpc_id" "$VPC_ID"
update_parameter "/gamepulse/$ENVIRONMENT/infrastructure/security_group_id" "$SECURITY_GROUP_ID"

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "========================================="
log_info "Sync Complete!"
echo "========================================="
echo ""
echo "Parameters updated:  $UPDATED_COUNT"
echo "Parameters skipped:  $SKIPPED_COUNT"
echo "Errors encountered:  $ERROR_COUNT"
echo ""

if [ $ERROR_COUNT -gt 0 ]; then
    log_error "Some parameters failed to update"
    log_error "Check the errors above and retry"
    exit 1
fi

if [ $UPDATED_COUNT -eq 0 ]; then
    log_warn "No parameters were updated"
    log_warn "This may be normal if values haven't changed"
fi

log_info "Next steps:"
echo "  1. Validate Parameter Store: bash scripts/validate-aws-parameters.sh $ENVIRONMENT"
echo "  2. Update secrets: bash scripts/update-aws-parameters.sh (interactive)"
echo "  3. Sync GitHub Secrets: bash scripts/sync-terraform-to-github-secrets.sh"
echo ""

exit 0
