variable "project_name" {
  description = "Project name for resource naming and tagging"
  type        = string
}

variable "repository_names" {
  description = "List of ECR Public repository names to create (e.g., ['gamepulse/backend', 'gamepulse/frontend'])"
  type        = list(string)

  validation {
    condition     = length(var.repository_names) > 0
    error_message = "At least one repository name must be specified."
  }

  validation {
    condition = alltrue([
      for name in var.repository_names :
      can(regex("^[a-z0-9][a-z0-9-_/]*$", name))
    ])
    error_message = "Repository names must start with a lowercase letter or number and can only contain lowercase letters, numbers, hyphens, underscores, and forward slashes."
  }
}

variable "tags" {
  description = "Common tags for all ECR resources"
  type        = map(string)
  default     = {}
}
