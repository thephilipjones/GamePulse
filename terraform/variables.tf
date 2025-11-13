# ============================================================================
# Project Configuration
# ============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "gamepulse"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# ============================================================================
# AWS Configuration
# ============================================================================

variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Availability zone for resources"
  type        = string
  default     = "us-east-1a"
}

# ============================================================================
# VPC Configuration
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet (EC2 instances)"
  type        = string
  default     = "10.1.1.0/24"
}

variable "private_subnet_cidr" {
  description = "CIDR block for private subnet (RDS, internal services)"
  type        = string
  default     = "10.1.2.0/24"
}

# ============================================================================
# Compute Configuration
# ============================================================================

variable "instance_type" {
  description = "EC2 instance type (t2.micro for AWS free tier)"
  type        = string
  default     = "t2.micro"

  validation {
    condition     = var.instance_type == "t2.micro"
    error_message = "Only t2.micro is allowed to stay within AWS free tier budget constraints."
  }
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20

  validation {
    condition     = var.root_volume_size >= 8 && var.root_volume_size <= 30
    error_message = "Root volume size must be between 8 and 30 GB to stay within reasonable costs."
  }
}

# ============================================================================
# Security Configuration
# ============================================================================

variable "admin_ip_cidrs" {
  description = "List of admin public IP addresses in CIDR notation (e.g., [\"203.0.113.10/32\"])"
  type        = list(string)

  validation {
    condition = alltrue([
      for cidr in var.admin_ip_cidrs : can(cidrhost(cidr, 0))
    ])
    error_message = "All entries must be valid CIDR blocks (e.g., 203.0.113.10/32 for single IP)."
  }
}

variable "tailscale_device_ips" {
  description = "List of specific Tailscale device IPs allowed to SSH (in CIDR notation, e.g., [\"100.64.0.10/32\", \"100.64.0.20/32\"])"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.tailscale_device_ips : can(cidrhost(cidr, 0))
    ])
    error_message = "All Tailscale IPs must be valid CIDR blocks (e.g., 100.64.0.10/32)."
  }
}

# ============================================================================
# Monitoring Configuration
# ============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.log_retention_days)
    error_message = "Log retention must be one of: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365 days."
  }
}

# ============================================================================
# GitHub OIDC Configuration
# ============================================================================

variable "github_org" {
  description = "GitHub organization or username (for OIDC authentication)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (for OIDC trust policy)"
  type        = string
  default     = "gamepulse"
}

variable "allowed_branch_patterns" {
  description = "Branch patterns allowed to deploy via GitHub Actions OIDC (e.g., ['main', 'staging'])"
  type        = list(string)
  default     = ["main", "staging"]

  validation {
    condition     = length(var.allowed_branch_patterns) > 0
    error_message = "At least one branch pattern must be specified for OIDC authentication."
  }
}

# ============================================================================
# Application Configuration (for Parameter Store)
# ============================================================================

variable "domain" {
  description = "Production domain name (e.g., gamepulse.top)"
  type        = string
  default     = "gamepulse.top"
}

variable "first_superuser_email" {
  description = "Admin user email address"
  type        = string
  default     = "admin@gamepulse.top"
}
