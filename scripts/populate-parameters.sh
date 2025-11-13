#!/usr/bin/env bash
# ============================================================================
# Populate AWS Parameter Store with GamePulse Secrets
# ============================================================================
# This script populates sensitive parameters in AWS Parameter Store.
# Run this ONCE after terraform apply to set actual secret values.
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - Terraform applied (KMS key and placeholder parameters created)
#   - Permission to write to SSM Parameter Store
#
# Usage:
#   ./scripts/populate-parameters.sh [environment]
#
# Example:
#   ./scripts/populate-parameters.sh production
#   ./scripts/populate-parameters.sh staging

set -e  # Exit on any error

# ============================================================================
# Configuration
# ============================================================================

ENVIRONMENT=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

log_prompt() {
    echo -e "${BLUE}[INPUT]${NC} $1"
}

# ============================================================================
# Validate Prerequisites
# ============================================================================

log_info "GamePulse Parameter Store Setup"
log_info "Environment: $ENVIRONMENT"
log_info "AWS Region: $AWS_REGION"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install it first:"
    log_error "  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    log_error "Configure credentials: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_info "AWS Account ID: $ACCOUNT_ID"

# Check if KMS key exists
KMS_KEY_ALIAS="alias/gamepulse-secrets"
if ! aws kms describe-key --key-id "$KMS_KEY_ALIAS" --region "$AWS_REGION" &> /dev/null; then
    log_error "KMS key not found: $KMS_KEY_ALIAS"
    log_error "Please run 'terraform apply' first to create infrastructure"
    exit 1
fi

KMS_KEY_ID=$(aws kms describe-key --key-id "$KMS_KEY_ALIAS" --region "$AWS_REGION" --query 'KeyMetadata.KeyId' --output text)
log_info "KMS Key ID: $KMS_KEY_ID"
echo ""

# ============================================================================
# Helper: Put Parameter
# ============================================================================

put_parameter() {
    local name=$1
    local value=$2
    local description=$3

    if [ -z "$value" ]; then
        log_warn "Skipping $name (empty value)"
        return
    fi

    log_info "Setting parameter: $name"

    if aws ssm put-parameter \
        --name "$name" \
        --value "$value" \
        --type "SecureString" \
        --key-id "$KMS_KEY_ID" \
        --description "$description" \
        --region "$AWS_REGION" \
        --overwrite \
        --no-cli-pager &> /dev/null; then
        echo "  ✅ Success"
    else
        log_error "Failed to set parameter: $name"
        exit 1
    fi
}

# ============================================================================
# Generate Secure Random Values
# ============================================================================

log_info "Generating secure random values..."

# Generate SECRET_KEY (40 characters, URL-safe)
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))' 2>/dev/null || openssl rand -base64 32 | tr -d "=+/" | cut -c1-40)
log_info "  Generated SECRET_KEY: ${SECRET_KEY:0:10}... (40 chars)"

# Generate POSTGRES_PASSWORD (32 characters)
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
log_info "  Generated POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:0:10}... (32 chars)"

echo ""

# ============================================================================
# Prompt for User-Provided Values
# ============================================================================

log_info "Please provide the following values:"
echo ""

# First superuser password
log_prompt "Admin user password (FIRST_SUPERUSER_PASSWORD):"
echo -n "  > "
read -s FIRST_SUPERUSER_PASSWORD
echo ""
if [ -z "$FIRST_SUPERUSER_PASSWORD" ]; then
    log_error "Admin password cannot be empty"
    exit 1
fi

# Tailscale auth key
log_prompt "Tailscale auth key (leave empty to skip):"
echo -n "  > "
read -s TAILSCALE_AUTHKEY
echo ""

# SMTP password (optional)
log_prompt "SMTP password for email (leave empty to skip):"
echo -n "  > "
read -s SMTP_PASSWORD
echo ""

echo ""

# ============================================================================
# Confirm Before Writing
# ============================================================================

log_warn "⚠️  This will overwrite existing parameters in Parameter Store"
log_warn "Environment: $ENVIRONMENT"
log_warn "Region: $AWS_REGION"
echo ""
log_prompt "Continue? (yes/no)"
echo -n "  > "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Aborted by user"
    exit 0
fi

echo ""

# ============================================================================
# Write Parameters to Parameter Store
# ============================================================================

log_info "Writing parameters to Parameter Store..."
echo ""

# Application secrets
put_parameter \
    "/gamepulse/$ENVIRONMENT/app/secret_key" \
    "$SECRET_KEY" \
    "FastAPI JWT secret key"

put_parameter \
    "/gamepulse/$ENVIRONMENT/app/first_superuser_password" \
    "$FIRST_SUPERUSER_PASSWORD" \
    "Admin user password"

# Database secrets
put_parameter \
    "/gamepulse/$ENVIRONMENT/database/password" \
    "$POSTGRES_PASSWORD" \
    "PostgreSQL password"

# Infrastructure secrets (shared across environments)
if [ -n "$TAILSCALE_AUTHKEY" ]; then
    put_parameter \
        "/gamepulse/shared/infrastructure/tailscale_authkey" \
        "$TAILSCALE_AUTHKEY" \
        "Tailscale auth key for EC2 auto-join"
else
    log_warn "Skipping Tailscale auth key (not provided)"
fi

# Optional: SMTP password
if [ -n "$SMTP_PASSWORD" ]; then
    put_parameter \
        "/gamepulse/$ENVIRONMENT/email/smtp_password" \
        "$SMTP_PASSWORD" \
        "SMTP password for email service"
else
    log_warn "Skipping SMTP password (not provided)"
fi

echo ""

# ============================================================================
# Verification
# ============================================================================

log_info "Verifying parameters..."

PARAM_COUNT=$(aws ssm get-parameters-by-path \
    --path "/gamepulse/$ENVIRONMENT/" \
    --recursive \
    --region "$AWS_REGION" \
    --query 'length(Parameters)' \
    --output text)

log_info "Total parameters in /gamepulse/$ENVIRONMENT/: $PARAM_COUNT"

echo ""

# ============================================================================
# Summary
# ============================================================================

log_info "✅ Parameter Store setup complete!"
echo ""
log_info "Next steps:"
log_info "  1. Verify parameters:"
log_info "     aws ssm get-parameters-by-path --path '/gamepulse/$ENVIRONMENT/' --recursive --region $AWS_REGION"
log_info ""
log_info "  2. Test secret loading (on EC2 or locally with AWS credentials):"
log_info "     cd /opt/gamepulse"
log_info "     bash backend/scripts/load-secrets.sh $ENVIRONMENT .env"
log_info "     cat .env"
log_info ""
log_info "  3. Deploy application (triggers automatic secret loading):"
log_info "     git push origin main"
log_info ""

log_warn "Security reminders:"
log_warn "  - Store this output securely (contains generated passwords)"
log_warn "  - Never commit .env files to version control"
log_warn "  - Rotate secrets regularly via 'aws ssm put-parameter --overwrite'"
log_warn "  - Use 'aws ssm get-parameter-history' to track changes"

echo ""
log_info "Generated credentials (save these securely):"
echo "  POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
echo "  SECRET_KEY: $SECRET_KEY"
if [ -n "$FIRST_SUPERUSER_PASSWORD" ]; then
    echo "  FIRST_SUPERUSER_PASSWORD: [hidden - you provided this]"
fi

echo ""
log_info "Done!"
