#!/usr/bin/env bash
# ============================================================================
# Validate AWS Parameter Store Configuration
# ============================================================================
# Purpose: Pre-deployment validation of Parameter Store parameters
#
# Usage:
#   ./scripts/validate-parameters.sh [environment]
#
# Example:
#   ./scripts/validate-parameters.sh production
#
# Exit Codes:
#   0 - All validations passed
#   1 - Critical parameters missing or invalid
#   2 - Warnings only (optional parameters missing)
# ============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${1:-production}

# Counters
CRITICAL_MISSING=0
OPTIONAL_MISSING=0
PLACEHOLDER_COUNT=0
DUPLICATE_COUNT=0

# ============================================================================
# Helper Functions
# ============================================================================

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# Validation
# ============================================================================

log_info "Validating Parameter Store configuration..."
log_info "Environment: $ENVIRONMENT"
log_info "AWS Region: $AWS_REGION"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured"
    exit 1
fi

# ============================================================================
# Fetch Parameters
# ============================================================================

log_info "Fetching parameters from Parameter Store..."

PARAMS_ENV=$(aws ssm get-parameters-by-path \
    --path "/gamepulse/$ENVIRONMENT/" \
    --recursive \
    --with-decryption \
    --region "$AWS_REGION" \
    --query 'Parameters[*].[Name,Value]' \
    --output text 2>/dev/null || echo "")

PARAMS_SHARED=$(aws ssm get-parameters-by-path \
    --path "/gamepulse/shared/" \
    --recursive \
    --with-decryption \
    --region "$AWS_REGION" \
    --query 'Parameters[*].[Name,Value]' \
    --output text 2>/dev/null || echo "")

TOTAL_PARAMS=$(echo "$PARAMS_ENV$PARAMS_SHARED" | grep -c "^/gamepulse/" || echo "0")

log_info "Found $TOTAL_PARAMS parameters"
echo ""

# ============================================================================
# Check Critical Parameters
# ============================================================================

log_info "Checking critical parameters..."

CRITICAL_PARAMS=(
    "/gamepulse/$ENVIRONMENT/app/secret_key"
    "/gamepulse/$ENVIRONMENT/app/first_superuser_password"
    "/gamepulse/$ENVIRONMENT/database/password"
    "/gamepulse/$ENVIRONMENT/database/name"
    "/gamepulse/$ENVIRONMENT/database/user"
    "/gamepulse/$ENVIRONMENT/docker/backend_image"
    "/gamepulse/$ENVIRONMENT/docker/frontend_image"
)

for param in "${CRITICAL_PARAMS[@]}"; do
    value=$(echo "$PARAMS_ENV" | grep "^$param" | cut -f2 || echo "")

    if [ -z "$value" ]; then
        log_error "Missing: $param"
        ((CRITICAL_MISSING++))
    elif [ "$value" = "PLACEHOLDER-UPDATE-VIA-AWS-CLI" ]; then
        log_error "Placeholder value: $param"
        ((PLACEHOLDER_COUNT++))
    else
        log_info "✅ $param"
    fi
done

echo ""

# ============================================================================
# Check Optional Parameters
# ============================================================================

log_info "Checking optional parameters..."

OPTIONAL_PARAMS=(
    "/gamepulse/$ENVIRONMENT/email/smtp_host"
    "/gamepulse/$ENVIRONMENT/email/smtp_password"
    "/gamepulse/$ENVIRONMENT/monitoring/sentry_dsn"
)

for param in "${OPTIONAL_PARAMS[@]}"; do
    value=$(echo "$PARAMS_ENV" | grep "^$param" | cut -f2 || echo "")

    if [ -z "$value" ]; then
        log_warn "Optional parameter not set: $param"
        ((OPTIONAL_MISSING++))
    fi
done

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "========================================="
log_info "Validation Summary"
echo "========================================="
echo ""
echo "Total parameters:     $TOTAL_PARAMS"
echo "Critical missing:     $CRITICAL_MISSING"
echo "Placeholder values:   $PLACEHOLDER_COUNT"
echo "Optional missing:     $OPTIONAL_MISSING"
echo ""

if [ $CRITICAL_MISSING -gt 0 ] || [ $PLACEHOLDER_COUNT -gt 0 ]; then
    log_error "❌ Validation FAILED"
    echo ""
    log_error "Action required:"
    echo "  Run: bash backend/scripts/populate-parameters-interactive.sh $ENVIRONMENT"
    echo ""
    exit 1
fi

if [ $OPTIONAL_MISSING -gt 0 ]; then
    log_warn "⚠️  Optional parameters missing (non-blocking)"
    echo ""
    log_info "✅ Validation PASSED (with warnings)"
    exit 2
fi

log_info "✅ All validations PASSED"
echo ""
exit 0
