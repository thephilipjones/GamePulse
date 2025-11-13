# GamePulse AWS Infrastructure - Root Module
# Orchestrates VPC and Compute modules for production deployment

# ============================================================================
# Local Variables
# ============================================================================

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "gamepulse"
  }
}

# ============================================================================
# VPC Module - Networking Foundation
# ============================================================================

module "vpc" {
  source = "./modules/vpc"

  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidr  = var.public_subnet_cidr
  private_subnet_cidr = var.private_subnet_cidr
  availability_zone   = var.availability_zone
  tags                = local.common_tags
}

# ============================================================================
# Secrets Module - Parameter Store for Application Secrets
# ============================================================================

module "secrets" {
  source = "./modules/secrets"

  project_name           = var.project_name
  environment            = var.environment
  domain                 = var.domain
  first_superuser_email  = var.first_superuser_email
  ecr_backend_url        = module.ecr.backend_repository_url
  ecr_frontend_url       = module.ecr.frontend_repository_url
  tags                   = local.common_tags
}

# ============================================================================
# Compute Module - Application Server
# ============================================================================

module "compute" {
  source = "./modules/compute"

  project_name         = var.project_name
  environment          = var.environment
  aws_region           = var.aws_region
  vpc_id               = module.vpc.vpc_id
  subnet_id            = module.vpc.public_subnet_id
  instance_type        = var.instance_type
  root_volume_size     = var.root_volume_size
  admin_ip_cidrs       = var.admin_ip_cidrs
  tailscale_device_ips = var.tailscale_device_ips
  log_retention_days   = var.log_retention_days
  secrets_kms_key_arn  = module.secrets.kms_key_arn
  tags                 = local.common_tags
}

# ============================================================================
# GitHub OIDC Module - Zero-Secret CI/CD Authentication
# ============================================================================

module "github_oidc" {
  source = "./modules/github-oidc"

  project_name            = var.project_name
  github_org              = var.github_org
  github_repo             = var.github_repo
  allowed_branch_patterns = var.allowed_branch_patterns
  aws_region              = var.aws_region
  tags                    = local.common_tags
}

# ============================================================================
# ECR Public Module - Container Registry
# ============================================================================

module "ecr" {
  source = "./modules/ecr"

  project_name     = var.project_name
  repository_names = ["gamepulse/backend", "gamepulse/frontend"]
  tags             = local.common_tags
}
