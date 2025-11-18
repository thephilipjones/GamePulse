#!/usr/bin/env bash
# ============================================================================
# Update Bluesky Parameters in AWS Parameter Store
# ============================================================================
# This script updates Bluesky credentials in AWS Parameter Store.
# Run AFTER terraform apply to set or update credential values.
#
# Features:
#   - Interactive: Shows existing values with partial masking
#   - Idempotent: Safe to run multiple times without data loss
#   - Selective: Only updates parameters you choose to change
#
# Usage: ./scripts/update-bluesky-parameters.sh [environment]
#
# Example:
#   ./scripts/update-bluesky-parameters.sh production

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
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track changes for summary
CHANGES_MADE=()
UNCHANGED=()

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

# Partially mask a value showing first N and last N characters
# Args: $1 = value, $2 = show_first (default 3), $3 = show_last (default 3)
mask_partial() {
    local value=$1
    local show_first=${2:-3}
    local show_last=${3:-3}
    local len=${#value}

    if [ $len -le $((show_first + show_last)) ]; then
        # Value too short to mask meaningfully
        echo "***"
    else
        local first="${value:0:$show_first}"
        local last="${value: -$show_last}"
        echo "${first}****${last}"
    fi
}

# Fetch existing parameter value from Parameter Store
# Args: $1 = parameter name
get_existing_parameter() {
    local param_name=$1
    aws ssm get-parameter \
        --name "$param_name" \
        --with-decryption \
        --region "$AWS_REGION" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo ""
}

# Prompt user to keep existing or enter new value
# Args: $1 = display_name, $2 = existing_value, $3 = is_secret (true/false)
prompt_parameter_update() {
    local display_name=$1
    local existing_value=$2
    local is_secret=${3:-false}
    local new_value=""
    local choice=""

    while true; do
        # Redirect prompts to stderr so they display even when output is captured
        log_prompt "$display_name:" >&2

        if [ -n "$existing_value" ]; then
            # Show existing value with partial masking
            # Do masking inline to avoid issues with command substitution in redirected context
            local len=${#existing_value}
            local show_first=3
            local show_last=3

            if [ "$is_secret" = "true" ]; then
                show_first=4
                show_last=4
            fi

            if [ $len -le $((show_first + show_last)) ]; then
                # Value too short to mask meaningfully
                echo "  Current: ***" >&2
            else
                local first="${existing_value:0:$show_first}"
                local last="${existing_value: -$show_last}"
                if [ "$is_secret" = "true" ]; then
                    echo "  Current: ${first}****${last} (encrypted)" >&2
                else
                    echo "  Current: ${first}****${last}" >&2
                fi
            fi
            echo "  [1] Keep existing value" >&2
            echo "  [2] Enter new value" >&2
        else
            echo "  No existing value found" >&2
            echo "  [1] Skip (leave empty)" >&2
            echo "  [2] Enter new value" >&2
        fi

        echo -n "  Choice (1 or 2): " >&2
        read -r choice </dev/tty

        # Validate choice
        if [ "$choice" != "1" ] && [ "$choice" != "2" ]; then
            log_error "  Invalid choice. Please enter 1 or 2." >&2
            echo "" >&2
            continue
        fi

        # Process valid choice
        if [ "$choice" = "1" ]; then
            # Keep existing (or skip if empty)
            echo "$existing_value"
            return
        elif [ "$choice" = "2" ]; then
            # Prompt for new value
            if [ "$is_secret" = "true" ]; then
                echo -n "  Enter new value: " >&2
                read -s new_value </dev/tty
                echo "" >&2
            else
                echo -n "  Enter new value: " >&2
                read -r new_value </dev/tty
            fi

            if [ -z "$new_value" ]; then
                log_warn "  Empty value provided - try again or choose option 1 to skip" >&2
                echo "" >&2
                continue
            else
                echo "$new_value"
                return
            fi
        fi
    done
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
# Fetch Existing Values
# ============================================================================

echo ""
log_info "Fetching existing Bluesky credentials from Parameter Store..."

EXISTING_HANDLE=$(get_existing_parameter "/gamepulse/$ENVIRONMENT/app/bluesky_handle")
EXISTING_PASSWORD=$(get_existing_parameter "/gamepulse/$ENVIRONMENT/app/bluesky_app_password")

# ============================================================================
# Display Setup Instructions
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

# ============================================================================
# Prompt for Credentials (Interactive Idempotency)
# ============================================================================

BLUESKY_HANDLE=$(prompt_parameter_update "Bluesky handle (e.g., user.bsky.social)" "$EXISTING_HANDLE" "false")
echo ""

BLUESKY_APP_PASSWORD=$(prompt_parameter_update "Bluesky app password" "$EXISTING_PASSWORD" "true")
echo ""

# ============================================================================
# Update Parameters (Only if Changed)
# ============================================================================

log_info "Updating Parameter Store..."

# Update Bluesky handle
if [ "$BLUESKY_HANDLE" != "$EXISTING_HANDLE" ] && [ -n "$BLUESKY_HANDLE" ]; then
    aws ssm put-parameter \
        --name "/gamepulse/$ENVIRONMENT/app/bluesky_handle" \
        --value "$BLUESKY_HANDLE" \
        --type String \
        --overwrite \
        --region "$AWS_REGION" \
        > /dev/null

    log_info "✓ Updated: bluesky_handle"
    CHANGES_MADE+=("bluesky_handle")
else
    if [ -n "$EXISTING_HANDLE" ]; then
        log_info "✓ Kept: bluesky_handle (no change)"
        UNCHANGED+=("bluesky_handle")
    else
        log_warn "⊘ Skipped: bluesky_handle (empty)"
    fi
fi

# Update Bluesky app password
if [ "$BLUESKY_APP_PASSWORD" != "$EXISTING_PASSWORD" ] && [ -n "$BLUESKY_APP_PASSWORD" ]; then
    aws ssm put-parameter \
        --name "/gamepulse/$ENVIRONMENT/app/bluesky_app_password" \
        --value "$BLUESKY_APP_PASSWORD" \
        --type SecureString \
        --key-id "$KMS_KEY_ARN" \
        --overwrite \
        --region "$AWS_REGION" \
        > /dev/null

    log_info "✓ Updated: bluesky_app_password (encrypted)"
    CHANGES_MADE+=("bluesky_app_password")
else
    if [ -n "$EXISTING_PASSWORD" ]; then
        log_info "✓ Kept: bluesky_app_password (no change)"
        UNCHANGED+=("bluesky_app_password")
    else
        log_warn "⊘ Skipped: bluesky_app_password (empty)"
    fi
fi

# ============================================================================
# Verify Parameters
# ============================================================================

echo ""
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

if [ -n "$HANDLE_CHECK" ] && [ -n "$PASSWORD_CHECK" ]; then
    log_info "✅ Bluesky parameters verified in Parameter Store"
else
    log_error "Parameter verification failed - some values are missing"
    exit 1
fi

# ============================================================================
# Display Summary
# ============================================================================

echo ""
log_info "=== Summary ==="
echo "  Environment:     $ENVIRONMENT"
echo "  AWS Region:      $AWS_REGION"
echo ""

if [ ${#CHANGES_MADE[@]} -gt 0 ]; then
    log_info "Parameters UPDATED (${#CHANGES_MADE[@]}):"
    for param in "${CHANGES_MADE[@]}"; do
        echo "  ✅ $param"
    done
    echo ""
fi

if [ ${#UNCHANGED[@]} -gt 0 ]; then
    log_info "Parameters UNCHANGED (${#UNCHANGED[@]}):"
    for param in "${UNCHANGED[@]}"; do
        echo "  ⊙ $param"
    done
    echo ""
fi

# ============================================================================
# Next Steps
# ============================================================================

if [ ${#CHANGES_MADE[@]} -gt 0 ]; then
    log_info "Next steps:"
    echo "  1. Deploy to EC2: Push to main branch (GitHub Actions will handle deployment)"
    echo "  2. Or manually update .env: cd /opt/gamepulse && bash backend/scripts/create-env-from-aws-parameters.sh production .env"
    echo "  3. Verify in Dagster UI: Check that extract_bluesky_posts asset runs successfully"
    echo ""
else
    log_info "No changes made. Credentials are already up to date."
    echo ""
fi

log_info "Optional: Update hashtags or rate limit via Parameter Store if needed:"
echo "  aws ssm put-parameter --name '/gamepulse/$ENVIRONMENT/app/bluesky_hashtags' --value 'CollegeBasketball,MarchMadness,NCAAM' --overwrite"
echo "  aws ssm put-parameter --name '/gamepulse/$ENVIRONMENT/app/bluesky_rate_limit_points_per_hour' --value '5000' --overwrite"
echo ""

exit 0
