# ============================================================================
# VPC Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = module.vpc.public_subnet_id
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = module.vpc.private_subnet_id
}

# ============================================================================
# Compute Outputs
# ============================================================================

output "instance_id" {
  description = "EC2 instance ID"
  value       = module.compute.instance_id
}

output "instance_state" {
  description = "Current state of the EC2 instance"
  value       = module.compute.instance_state
}

output "public_ip" {
  description = "Elastic IP address for EC2 instance"
  value       = module.compute.public_ip
}

output "private_ip" {
  description = "Private IP address of EC2 instance"
  value       = module.compute.private_ip
}

output "security_group_id" {
  description = "Security group ID for the EC2 instance"
  value       = module.compute.security_group_id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = module.compute.ssh_command
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value       = module.compute.cloudwatch_log_groups
}

# ============================================================================
# GitHub OIDC Outputs
# ============================================================================

output "github_actions_role_arn" {
  description = "ARN of the IAM role for GitHub Actions (use this in workflow with role-to-assume)"
  value       = module.github_oidc.github_actions_role_arn
}

output "github_actions_role_name" {
  description = "Name of the IAM role for GitHub Actions"
  value       = module.github_oidc.github_actions_role_name
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = module.github_oidc.oidc_provider_arn
}

# ============================================================================
# ECR Public Outputs
# ============================================================================

output "ecr_backend_repository_url" {
  description = "ECR Public URL for backend repository (use in docker-compose.yml)"
  value       = module.ecr.backend_repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR Public URL for frontend repository (use in docker-compose.yml)"
  value       = module.ecr.frontend_repository_url
}

output "ecr_registry_id" {
  description = "ECR Public registry ID"
  value       = module.ecr.registry_id
}

# ============================================================================
# Connection Information
# ============================================================================

output "connection_info" {
  description = "All connection information"
  value = {
    public_ip                   = module.compute.public_ip
    private_ip                  = module.compute.private_ip
    ssh_command                 = module.compute.ssh_command
    instance_id                 = module.compute.instance_id
    vpc_id                      = module.vpc.vpc_id
    github_actions_role_arn     = module.github_oidc.github_actions_role_arn
    ecr_backend_repository_url  = module.ecr.backend_repository_url
    ecr_frontend_repository_url = module.ecr.frontend_repository_url
  }
}
