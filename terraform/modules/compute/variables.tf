variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where resources will be created"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EC2 instance"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "ami_id" {
  description = "AMI ID for EC2 instance. If not provided, uses latest Ubuntu 24.04 LTS"
  type        = string
  default     = null
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 20
}

variable "admin_ip_cidrs" {
  description = "List of CIDR blocks for admin SSH access"
  type        = list(string)
}

variable "tailscale_device_ips" {
  description = "List of specific Tailscale device IPs (in CIDR notation) allowed to SSH"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "environment" {
  description = "Environment name (production, staging, etc.)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region for Parameter Store access"
  type        = string
  default     = "us-east-1"
}

variable "secrets_kms_key_arn" {
  description = "KMS key ARN for secrets decryption"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
