output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "github_actions_role_arn" {
  description = "ARN of the IAM role for GitHub Actions (use in workflow with role-to-assume)"
  value       = aws_iam_role.github_actions.arn
}

output "github_actions_role_name" {
  description = "Name of the IAM role for GitHub Actions"
  value       = aws_iam_role.github_actions.name
}

output "deployment_policy_arn" {
  description = "ARN of the deployment policy attached to the GitHub Actions role"
  value       = aws_iam_policy.github_actions_deployment.arn
}
