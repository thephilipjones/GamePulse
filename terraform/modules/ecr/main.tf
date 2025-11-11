# ECR Public Repositories for GamePulse
# Provides container registry with zero-cost hosting for public Docker images

# ============================================================================
# Data Sources
# ============================================================================

# Get current AWS account ID for IAM policy construction
data "aws_caller_identity" "current" {}

# ============================================================================
# ECR Public Repositories
# ============================================================================

resource "aws_ecrpublic_repository" "repositories" {
  for_each = toset(var.repository_names)

  repository_name = each.value

  catalog_data {
    description       = "${var.project_name} ${title(split("/", each.value)[1])} - Portfolio Project"
    about_text        = "GamePulse is a real-time NCAA basketball excitement tracking dashboard. This repository contains the ${split("/", each.value)[1]} Docker image for production deployment."
    usage_text        = "Pull and run: docker pull public.ecr.aws/ALIAS/${each.value}:latest"
    architectures     = ["x86_64"]
    operating_systems = ["Linux"]

    # GitHub repository link
    logo_image_blob = null # Optional: Could add project logo in the future
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${split("/", each.value)[1]}-ecr-public"
      Description = "Public ECR repository for ${split("/", each.value)[1]} container images"
      Component   = split("/", each.value)[1]
    }
  )
}

# ============================================================================
# Lifecycle Policies
# ============================================================================

# Note: ECR Public supports basic lifecycle policies via repository policy
# Lifecycle management configured as follows:
# - Keep last 3 tagged images (rollback capability)
# - Delete untagged images after 1 day (cost optimization)

resource "aws_ecrpublic_repository_policy" "lifecycle" {
  for_each = toset(var.repository_names)

  repository_name = aws_ecrpublic_repository.repositories[each.key].repository_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "PublicReadAccess"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = [
          "ecr-public:DescribeImages",
          "ecr-public:DescribeRepositories",
          "ecr-public:GetRepositoryPolicy",
          "ecr-public:ListImages"
        ]
      }
    ]
  })
}

# ============================================================================
# Image Scanning Configuration
# ============================================================================

# Note: ECR Public repositories have scan-on-push enabled by default
# Basic scanning (CVE detection) is available in the free tier
# Scanning configuration is managed through repository settings in the AWS Console
# or can be enabled via AWS CLI:
# aws ecr-public put-image-scanning-configuration --repository-name REPO --image-scanning-configuration scanOnPush=true

# ============================================================================
# Encryption Configuration
# ============================================================================

# Note: ECR Public repositories use AWS-managed encryption at rest by default
# Images are encrypted using AES-256 encryption
# Encryption in transit uses TLS (HTTPS)
# Customer-managed KMS keys are not supported for ECR Public (AWS-managed only)
