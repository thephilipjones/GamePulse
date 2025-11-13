# ============================================================================
# Secrets Module Outputs
# ============================================================================

output "kms_key_id" {
  description = "KMS key ID for secrets encryption"
  value       = aws_kms_key.secrets.id
}

output "kms_key_arn" {
  description = "KMS key ARN for secrets encryption"
  value       = aws_kms_key.secrets.arn
}

output "kms_key_alias" {
  description = "KMS key alias for secrets encryption"
  value       = aws_kms_alias.secrets.name
}

output "parameter_paths" {
  description = "Map of parameter paths organized by category"
  value = {
    config_parameters    = keys(local.config_parameters)
    sensitive_parameters = keys(local.sensitive_parameters)
  }
}

output "parameter_base_path" {
  description = "Base path for all parameters in this environment"
  value       = "/gamepulse/${var.environment}/"
}
