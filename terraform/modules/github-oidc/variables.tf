variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "allowed_branch_patterns" {
  description = "List of branch patterns allowed to assume the role (e.g., ['main', 'staging', 'feature/*'])"
  type        = list(string)
  default     = ["main"]

  validation {
    condition     = length(var.allowed_branch_patterns) > 0
    error_message = "At least one branch pattern must be specified."
  }
}

variable "aws_region" {
  description = "AWS region for resource creation"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
