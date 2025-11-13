# ============================================================================
# Secrets Module Variables
# ============================================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (production, staging, etc.)"
  type        = string
}

variable "domain" {
  description = "Production domain name"
  type        = string
}

variable "first_superuser_email" {
  description = "Admin user email address"
  type        = string
}

variable "ecr_backend_url" {
  description = "ECR Public URL for backend Docker image"
  type        = string
}

variable "ecr_frontend_url" {
  description = "ECR Public URL for frontend Docker image"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
