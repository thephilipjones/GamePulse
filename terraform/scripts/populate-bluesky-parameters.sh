#!/usr/bin/env bash
# ============================================================================
# Populate Bluesky Parameters in AWS Parameter Store
# ============================================================================
# This script populates Bluesky credentials in AWS Parameter Store.
# Run AFTER terraform apply to set actual credential values.
#
# Usage: ./terraform/scripts/populate-bluesky-parameters.sh [environment]
#
# Example:
#   ./terraform/scripts/populate-bluesky-parameters.sh production

set -e

# ============================================================================
# Configuration
# ============================================================================

ENVIRONMENT=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# ============================================================================
# Validate Prerequisites
# ============================================================================

if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install it first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

log_info "AWS credentials validated (Region: $AWS_REGION)"

# ============================================================================
# Get KMS Key ARN
# ============================================================================

log_info "Retrieving KMS key ARN..."
KMS_KEY_ARN=$(aws kms describe-key \
    --key-id "alias/gamepulse-secrets" \
    --region "$AWS_REGION" \
    --query 'KeyMetadata.Arn' \
    --output text 2>/dev/null || echo "")

if [ -z "$KMS_KEY_ARN" ]; then
    log_error "KMS key not found. Run 'terraform apply' first to create infrastructure."
    exit 1
fi

log_info "Using KMS key: $KMS_KEY_ARN"

# ============================================================================
# Prompt for Bluesky Credentials
# ============================================================================

echo ""
log_info "=== Bluesky Data Pipeline Setup ==="
echo ""
echo "To get your Bluesky app password:"
echo "  1. Go to https://bsky.app/settings"
echo "  2. Navigate to: Settings → Privacy and Security → App Passwords"
echo "  3. Click 'Add App Password'"
echo "  4. Name it 'GamePulse Production' (or similar)"
echo "  5. Copy the generated password (format: xxxx-xxxx-xxxx-xxxx)"
echo ""

read -p "Enter your Bluesky handle (e.g., user.bsky.social): " BLUESKY_HANDLE
read -sp "Enter your Bluesky app password: " BLUESKY_APP_PASSWORD
echo ""

# Validate inputs
if [ -z "$BLUESKY_HANDLE" ] || [ -z "$BLUESKY_APP_PASSWORD" ]; then
    log_error "Bluesky handle and app password are required"
    exit 1
fi

# ============================================================================
# Populate Parameters
# ============================================================================

log_info "Populating Bluesky parameters in Parameter Store..."

# Non-sensitive: Bluesky handle
aws ssm put-parameter \
    --name "/gamepulse/$ENVIRONMENT/app/bluesky_handle" \
    --value "$BLUESKY_HANDLE" \
    --type String \
    --overwrite \
    --region "$AWS_REGION" \
    > /dev/null

log_info "✓ Updated: /gamepulse/$ENVIRONMENT/app/bluesky_handle"

# Sensitive: Bluesky app password (encrypted with KMS)
aws ssm put-parameter \
    --name "/gamepulse/$ENVIRONMENT/app/bluesky_app_password" \
    --value "$BLUESKY_APP_PASSWORD" \
    --type SecureString \
    --key-id "$KMS_KEY_ARN" \
    --overwrite \
    --region "$AWS_REGION" \
    > /dev/null

log_info "✓ Updated: /gamepulse/$ENVIRONMENT/app/bluesky_app_password (encrypted)"

# ============================================================================
# Verify Parameters
# ============================================================================

log_info "Verifying parameters..."

HANDLE_CHECK=$(aws ssm get-parameter \
    --name "/gamepulse/$ENVIRONMENT/app/bluesky_handle" \
    --region "$AWS_REGION" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || echo "")

PASSWORD_CHECK=$(aws ssm get-parameter \
    --name "/gamepulse/$ENVIRONMENT/app/bluesky_app_password" \
    --with-decryption \
    --region "$AWS_REGION" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || echo "")

if [ "$HANDLE_CHECK" = "$BLUESKY_HANDLE" ] && [ -n "$PASSWORD_CHECK" ]; then
    log_info "✅ All Bluesky parameters successfully populated!"
else
    log_error "Parameter verification failed"
    exit 1
fi

# ============================================================================
# Display Summary
# ============================================================================

echo ""
log_info "=== Summary ==="
echo "  Environment:     $ENVIRONMENT"
echo "  Bluesky Handle:  $BLUESKY_HANDLE"
echo "  App Password:    ****-****-****-**** (encrypted with KMS)"
echo "  Region:          $AWS_REGION"
echo ""
log_info "Next steps:"
echo "  1. Deploy to EC2: Push to main branch (GitHub Actions will handle deployment)"
echo "  2. Or manually update .env: cd /opt/gamepulse && bash backend/scripts/create-env-from-aws-parameters.sh production .env"
echo "  3. Verify in Dagster UI: Check that extract_bluesky_posts asset runs successfully"
echo ""
log_info "Optional: Update hashtags or rate limit via Parameter Store if needed:"
echo "  aws ssm put-parameter --name '/gamepulse/$ENVIRONMENT/app/bluesky_hashtags' --value 'CollegeBasketball,MarchMadness,NCAAM' --overwrite"
echo "  aws ssm put-parameter --name '/gamepulse/$ENVIRONMENT/app/bluesky_rate_limit_points_per_hour' --value '5000' --overwrite"
echo ""

exit 0
