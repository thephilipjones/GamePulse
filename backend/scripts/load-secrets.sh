#!/usr/bin/env bash
# ============================================================================
# Load Secrets from AWS Parameter Store
# ============================================================================
# Fetches secrets from Parameter Store and generates .env file
# Usage: ./scripts/load-secrets.sh [environment] [output_file]
#
# Example:
#   ./scripts/load-secrets.sh production .env
#   ./scripts/load-secrets.sh staging ../staging.env

set -e  # Exit on any error

# ============================================================================
# Configuration
# ============================================================================

AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${1:-production}
OUTPUT_FILE=${2:-.env}

# Color output for terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
# Validate AWS CLI
# ============================================================================

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

log_info "AWS credentials validated (Region: $AWS_REGION)"

# ============================================================================
# Fetch Parameters from Parameter Store
# ============================================================================

log_info "Fetching secrets from Parameter Store (Environment: $ENVIRONMENT)..."

# Fetch all parameters under /gamepulse/{environment}/ and /gamepulse/shared/
# Combines both paths to get all required parameters
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

# Combine parameters
ALL_PARAMS=$(printf "%s\n%s" "$PARAMS_ENV" "$PARAMS_SHARED")

if [ -z "$ALL_PARAMS" ]; then
    log_error "No parameters found in Parameter Store for environment: $ENVIRONMENT"
    log_error "Expected parameter path: /gamepulse/$ENVIRONMENT/"
    log_error ""
    log_error "Please run the populate-parameters.sh script first to initialize secrets."
    exit 1
fi

# ============================================================================
# Parameter Name Mapping
# ============================================================================
# Maps Parameter Store paths to .env variable names
# Example: /gamepulse/production/database/password → POSTGRES_PASSWORD

map_parameter_name() {
    local param_path=$1

    # Remove prefix: /gamepulse/production/ or /gamepulse/shared/
    # Using bash parameter expansion (safer than sed - no delimiter issues with special characters)
    local key="$param_path"
    key="${key#/gamepulse/production/}"
    key="${key#/gamepulse/staging/}"
    key="${key#/gamepulse/shared/}"

    # Convert path separators to underscores: database/password → database_password
    key=$(echo "$key" | tr '/' '_')

    # Convert to uppercase: database_password → DATABASE_PASSWORD
    key=$(echo "$key" | tr '[:lower:]' '[:upper:]')

    # Map to .env naming conventions
    case "$key" in
        # Database mappings
        DATABASE_PASSWORD)         echo "POSTGRES_PASSWORD" ;;
        DATABASE_NAME)             echo "POSTGRES_DB" ;;
        DATABASE_USER)             echo "POSTGRES_USER" ;;
        DATABASE_SERVER)           echo "POSTGRES_SERVER" ;;
        DATABASE_PORT)             echo "POSTGRES_PORT" ;;
        DATABASE_DAGSTER_DB)       echo "DAGSTER_POSTGRES_DB" ;;

        # App mappings
        APP_SECRET_KEY)            echo "SECRET_KEY" ;;
        APP_FIRST_SUPERUSER)       echo "FIRST_SUPERUSER" ;;
        APP_FIRST_SUPERUSER_PASSWORD) echo "FIRST_SUPERUSER_PASSWORD" ;;
        APP_DOMAIN)                echo "DOMAIN" ;;
        APP_ENVIRONMENT)           echo "ENVIRONMENT" ;;
        APP_PROJECT_NAME)          echo "PROJECT_NAME" ;;
        APP_STACK_NAME)            echo "STACK_NAME" ;;
        APP_FRONTEND_HOST)         echo "FRONTEND_HOST" ;;
        APP_BACKEND_CORS_ORIGINS)  echo "BACKEND_CORS_ORIGINS" ;;
        APP_EMAILS_FROM_EMAIL)     echo "EMAILS_FROM_EMAIL" ;;

        # Docker mappings
        DOCKER_BACKEND_IMAGE)      echo "DOCKER_IMAGE_BACKEND" ;;
        DOCKER_FRONTEND_IMAGE)     echo "DOCKER_IMAGE_FRONTEND" ;;
        DOCKER_TAG)                echo "TAG" ;;

        # Email mappings (optional)
        EMAIL_SMTP_HOST)           echo "SMTP_HOST" ;;
        EMAIL_SMTP_USER)           echo "SMTP_USER" ;;
        EMAIL_SMTP_PASSWORD)       echo "SMTP_PASSWORD" ;;
        EMAIL_SMTP_PORT)           echo "SMTP_PORT" ;;

        # Monitoring (optional)
        MONITORING_SENTRY_DSN)     echo "SENTRY_DSN" ;;

        # Infrastructure (not needed in .env, skip)
        INFRASTRUCTURE_TAILSCALE_AUTHKEY) echo "" ;;

        # Default: keep the transformed name
        *) echo "$key" ;;
    esac
}

# ============================================================================
# Generate .env File
# ============================================================================

log_info "Generating $OUTPUT_FILE..."

# Create temporary file
TEMP_FILE=$(mktemp)

# Header
cat > "$TEMP_FILE" <<'EOF'
# ============================================================================
# GamePulse Environment Variables
# ============================================================================
# Auto-generated from AWS Parameter Store
# DO NOT EDIT MANUALLY - Changes will be overwritten on next deployment
#
# To update values:
#   1. Update in Parameter Store: aws ssm put-parameter --name <name> --value <value> --overwrite
#   2. Re-run this script: ./scripts/load-secrets.sh
#
# Generated at: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# ============================================================================

EOF

# Process parameters
param_count=0
while IFS=$'\t' read -r name value; do
    [ -z "$name" ] && continue  # Skip empty lines

    env_var=$(map_parameter_name "$name")

    # Skip if mapping returns empty (like Tailscale key not needed in .env)
    if [ -z "$env_var" ]; then
        continue
    fi

    # Check for placeholder values
    if [ "$value" = "PLACEHOLDER-UPDATE-VIA-AWS-CLI" ]; then
        log_warn "Parameter $name has placeholder value, skipping"
        continue
    fi

    # Write to .env file
    echo "$env_var=$value" >> "$TEMP_FILE"
    ((param_count++)) || true
done <<< "$ALL_PARAMS"

# ============================================================================
# Validation
# ============================================================================

if [ $param_count -eq 0 ]; then
    log_error "No valid parameters found (all may be placeholders)"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Move temporary file to output file
mv "$TEMP_FILE" "$OUTPUT_FILE"
chmod 600 "$OUTPUT_FILE"  # Restrict permissions (owner read/write only)

log_info "✅ Successfully generated $OUTPUT_FILE with $param_count parameters"
log_info "File permissions set to 600 (owner read/write only)"

# ============================================================================
# Verification
# ============================================================================

# Check for critical parameters
CRITICAL_PARAMS=("SECRET_KEY" "POSTGRES_PASSWORD" "FIRST_SUPERUSER_PASSWORD")
MISSING_PARAMS=()

for param in "${CRITICAL_PARAMS[@]}"; do
    if ! grep -q "^$param=" "$OUTPUT_FILE"; then
        MISSING_PARAMS+=("$param")
    fi
done

if [ ${#MISSING_PARAMS[@]} -gt 0 ]; then
    log_warn "Missing critical parameters: ${MISSING_PARAMS[*]}"
    log_warn "Application may not start correctly"
fi

# ============================================================================
# Add Optional Parameters (if not present)
# ============================================================================

# List of optional parameters that should have empty defaults
OPTIONAL_PARAMS=("SMTP_HOST" "SMTP_USER" "SMTP_PASSWORD" "SMTP_PORT" "SENTRY_DSN")

for param in "${OPTIONAL_PARAMS[@]}"; do
    if ! grep -q "^$param=" "$OUTPUT_FILE"; then
        echo "$param=" >> "$OUTPUT_FILE"
    fi
done

# ============================================================================
# Security Reminder
# ============================================================================

log_info ""
log_info "Security reminders:"
log_info "  - Never commit .env files to version control"
log_info "  - Delete .env files after deployment if no longer needed"
log_info "  - Rotate secrets regularly via Parameter Store"

exit 0
