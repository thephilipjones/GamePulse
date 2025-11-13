# ============================================================================
# AWS Systems Manager Parameter Store - Secrets Module
# ============================================================================
# This module manages all application secrets using SSM Parameter Store
# with KMS encryption for sensitive values.

data "aws_caller_identity" "current" {}

# ============================================================================
# KMS Key for Parameter Store Encryption
# ============================================================================

resource "aws_kms_key" "secrets" {
  description             = "KMS key for ${var.project_name} Parameter Store encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-secrets-key"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# ============================================================================
# Parameter Store - Application Configuration (Non-Sensitive)
# ============================================================================
# These parameters store configuration values that don't require encryption.
# Sensitive values (passwords, keys) should be populated via AWS CLI outside
# of Terraform to keep them out of state files.

locals {
  # Non-sensitive configuration parameters managed by Terraform
  config_parameters = {
    "/gamepulse/${var.environment}/app/domain" = {
      value       = var.domain
      description = "Production domain"
    }
    "/gamepulse/${var.environment}/app/environment" = {
      value       = var.environment
      description = "Environment name (production/staging)"
    }
    "/gamepulse/${var.environment}/app/project_name" = {
      value       = var.project_name
      description = "Project name"
    }
    "/gamepulse/${var.environment}/app/stack_name" = {
      value       = "${var.project_name}-${var.environment}"
      description = "Docker stack name"
    }
    "/gamepulse/${var.environment}/app/frontend_host" = {
      value       = "https://${var.domain}"
      description = "Frontend host URL"
    }
    "/gamepulse/${var.environment}/app/backend_cors_origins" = {
      value       = "https://${var.domain},https://api.${var.domain}"
      description = "Allowed CORS origins"
    }
    "/gamepulse/${var.environment}/app/emails_from_email" = {
      value       = "noreply@${var.domain}"
      description = "Default sender email address"
    }
    "/gamepulse/${var.environment}/app/first_superuser" = {
      value       = var.first_superuser_email
      description = "Admin user email"
    }
    "/gamepulse/${var.environment}/database/server" = {
      value       = "db"
      description = "PostgreSQL server hostname (Docker service name)"
    }
    "/gamepulse/${var.environment}/database/port" = {
      value       = "5432"
      description = "PostgreSQL server port"
    }
    "/gamepulse/${var.environment}/database/name" = {
      value       = var.project_name
      description = "PostgreSQL database name"
    }
    "/gamepulse/${var.environment}/database/user" = {
      value       = var.project_name
      description = "PostgreSQL username"
    }
    "/gamepulse/${var.environment}/database/dagster_db" = {
      value       = "dagster"
      description = "Dagster database name"
    }
    "/gamepulse/${var.environment}/docker/backend_image" = {
      value       = var.ecr_backend_url
      description = "Backend Docker image URL"
    }
    "/gamepulse/${var.environment}/docker/frontend_image" = {
      value       = var.ecr_frontend_url
      description = "Frontend Docker image URL"
    }
    "/gamepulse/${var.environment}/docker/tag" = {
      value       = "latest"
      description = "Docker image tag"
    }
  }

  # Sensitive parameters that will be populated via AWS CLI (placeholders only)
  # These create the parameter with a placeholder value that must be updated
  sensitive_parameters = {
    "/gamepulse/${var.environment}/app/secret_key" = {
      description = "FastAPI JWT secret key (populate via AWS CLI)"
    }
    "/gamepulse/${var.environment}/app/first_superuser_password" = {
      description = "Admin user password (populate via AWS CLI)"
    }
    "/gamepulse/${var.environment}/database/password" = {
      description = "PostgreSQL password (populate via AWS CLI)"
    }
    "/gamepulse/shared/infrastructure/tailscale_authkey" = {
      description = "Tailscale auth key for EC2 auto-join (populate via AWS CLI)"
    }
  }
}

# Configuration parameters (String type, not encrypted)
resource "aws_ssm_parameter" "config" {
  for_each = local.config_parameters

  name        = each.key
  description = each.value.description
  type        = "String"
  value       = each.value.value

  tags = merge(
    var.tags,
    {
      Name        = each.key
      Environment = var.environment
      Category    = split("/", each.key)[3] # Extract category from path
      ManagedBy   = "terraform"
    }
  )
}

# Sensitive parameters (SecureString type, KMS encrypted, placeholder values)
# IMPORTANT: After Terraform apply, populate actual values via:
# aws ssm put-parameter --name <parameter-name> --value <actual-value> --type SecureString --key-id <kms-key-id> --overwrite
resource "aws_ssm_parameter" "sensitive" {
  for_each = local.sensitive_parameters

  name        = each.key
  description = each.value.description
  type        = "SecureString"
  value       = "PLACEHOLDER-UPDATE-VIA-AWS-CLI"
  key_id      = aws_kms_key.secrets.arn

  # Ignore changes to value after initial creation
  # This prevents Terraform from reverting manually-set values
  lifecycle {
    ignore_changes = [value]
  }

  tags = merge(
    var.tags,
    {
      Name        = each.key
      Environment = each.key == "/gamepulse/shared/infrastructure/tailscale_authkey" ? "shared" : var.environment
      Category    = split("/", each.key)[length(split("/", each.key)) - 2] # Extract category from path
      ManagedBy   = "terraform"
    }
  )
}
