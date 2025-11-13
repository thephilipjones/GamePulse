#!/usr/bin/env bash
# ============================================================================
# Sync Terraform Outputs to GitHub Secrets
# ============================================================================
# Purpose: Automatically copy infrastructure values from Terraform outputs
#          to GitHub repository secrets for CI/CD workflows
#
# Usage:
#   ./scripts/sync-github-secrets.sh [repository]
#
# Example:
#   ./scripts/sync-github-secrets.sh thephilipjones/GamePulse
#
# What it does:
#   - Reads Terraform outputs from terraform/
#   - Updates GitHub Secrets with infrastructure values
#   - Requires gh CLI authenticated with repo permissions
#   - Idempotent (safe to run multiple times)
#
# Secrets Updated:
#   - AWS_GITHUB_ACTIONS_ROLE_ARN
#   - AWS_EC2_INSTANCE_ID
#   - AWS_DEPLOYMENT_PATH
#   - ECR_BACKEND_URL
#   - ECR_FRONTEND_URL
#   - DOMAIN_PRODUCTION
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
TERRAFORM_DIR="terraform"
DEPLOYMENT_PATH="/opt/gamepulse"
DOMAIN_PRODUCTION="gamepulse.top"

# Repository (auto-detect from git remote or use argument)
if [ -n "$1" ]; then
    REPO="$1"
else
    # Auto-detect from git remote
    REPO=$(git remote get-url origin 2>/dev/null | sed -E 's#^https://github.com/##; s#^git@github.com:##; s#\.git$##' || echo "")
fi

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

# Update a GitHub Secret
update_secret() {
    local secret_name=$1
    local secret_value=$2

    if [ -z "$secret_value" ] || [ "$secret_value" = "null" ]; then
        log_warn "Skipping $secret_name (value is empty or null)"
        ((SKIPPED_COUNT++))
        return 0
    fi

    # Update secret using gh CLI
    if echo "$secret_value" | gh secret set "$secret_name" -R "$REPO" &>/dev/null; then
        log_info "✅ Updated: $secret_name"
        ((UPDATED_COUNT++))
    else
        log_error "❌ Failed to update: $secret_name"
        ((ERROR_COUNT++))
    fi
}

# ============================================================================
# Validation
# ============================================================================

log_info "Syncing Terraform outputs to GitHub Secrets..."
log_info "Repository: $REPO"
echo ""

# Check repository is set
if [ -z "$REPO" ]; then
    log_error "Repository not specified and could not be auto-detected"
    log_error "Usage: $0 <owner/repo>"
    log_error "Example: $0 thephilipjones/GamePulse"
    exit 1
fi

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

# Check gh CLI
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) not found. Please install it:"
    log_error "  macOS: brew install gh"
    log_error "  Linux: https://cli.github.com/manual/installation"
    exit 1
fi

# Verify gh authentication
if ! gh auth status &> /dev/null; then
    log_error "GitHub CLI not authenticated"
    log_error "Run: gh auth login"
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
GITHUB_ACTIONS_ROLE_ARN=$(echo "$TF_OUTPUTS" | jq -r '.github_actions_role_arn.value // empty')
INSTANCE_ID=$(echo "$TF_OUTPUTS" | jq -r '.instance_id.value // empty')
ECR_BACKEND=$(echo "$TF_OUTPUTS" | jq -r '.ecr_backend_repository_url.value // empty')
ECR_FRONTEND=$(echo "$TF_OUTPUTS" | jq -r '.ecr_frontend_repository_url.value // empty')

cd ..

log_info "✅ Terraform outputs extracted"
echo ""

# ============================================================================
# Update GitHub Secrets
# ============================================================================

log_info "Updating GitHub Secrets..."
echo ""

# AWS Infrastructure Secrets
update_secret "AWS_GITHUB_ACTIONS_ROLE_ARN" "$GITHUB_ACTIONS_ROLE_ARN"
update_secret "AWS_EC2_INSTANCE_ID" "$INSTANCE_ID"
update_secret "AWS_DEPLOYMENT_PATH" "$DEPLOYMENT_PATH"

echo ""

# ECR Repository URLs
update_secret "ECR_BACKEND_URL" "$ECR_BACKEND"
update_secret "ECR_FRONTEND_URL" "$ECR_FRONTEND"

echo ""

# Application Configuration
update_secret "DOMAIN_PRODUCTION" "$DOMAIN_PRODUCTION"

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "========================================="
log_info "Sync Complete!"
echo "========================================="
echo ""
echo "Secrets updated:     $UPDATED_COUNT"
echo "Secrets skipped:     $SKIPPED_COUNT"
echo "Errors encountered:  $ERROR_COUNT"
echo ""

if [ $ERROR_COUNT -gt 0 ]; then
    log_error "Some secrets failed to update"
    log_error "Check the errors above and retry"
    exit 1
fi

if [ $UPDATED_COUNT -eq 0 ]; then
    log_warn "No secrets were updated"
    log_warn "This may indicate an issue with Terraform outputs"
fi

log_info "Next steps:"
echo "  1. Verify secrets in GitHub: https://github.com/$REPO/settings/secrets/actions"
echo "  2. Manually add sensitive secrets via GitHub UI:"
echo "     - SECRET_KEY (generate: python -c \"import secrets; print(secrets.token_urlsafe(32))\")"
echo "     - POSTGRES_PASSWORD"
echo "     - FIRST_SUPERUSER_PASSWORD"
echo "  3. Test CI/CD workflow: git push origin main"
echo ""

exit 0
