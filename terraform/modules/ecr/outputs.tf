output "repository_urls" {
  description = "Map of repository names to their public URLs"
  value = {
    for name, repo in aws_ecrpublic_repository.repositories :
    name => repo.repository_uri
  }
}

output "backend_repository_url" {
  description = "Public URL for backend repository (format: public.ecr.aws/ALIAS/gamepulse/backend)"
  value       = try(aws_ecrpublic_repository.repositories["gamepulse/backend"].repository_uri, "")
}

output "frontend_repository_url" {
  description = "Public URL for frontend repository (format: public.ecr.aws/ALIAS/gamepulse/frontend)"
  value       = try(aws_ecrpublic_repository.repositories["gamepulse/frontend"].repository_uri, "")
}

output "registry_id" {
  description = "ECR Public registry ID (account-specific registry identifier)"
  value       = try(aws_ecrpublic_repository.repositories[var.repository_names[0]].registry_id, "")
}

output "repository_arns" {
  description = "Map of repository names to their ARNs"
  value = {
    for name, repo in aws_ecrpublic_repository.repositories :
    name => repo.arn
  }
}
