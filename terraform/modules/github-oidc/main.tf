# GitHub OIDC Provider and IAM Role for GitHub Actions
# Enables zero-secret deployments via temporary credentials

# ============================================================================
# Data Sources
# ============================================================================

# Get GitHub's OIDC thumbprint automatically
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# Get current AWS account ID for IAM role ARN construction
data "aws_caller_identity" "current" {}

# ============================================================================
# OIDC Identity Provider
# ============================================================================

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  thumbprint_list = [
    data.tls_certificate.github.certificates[0].sha1_fingerprint,
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-github-oidc-provider"
      Description = "OIDC provider for GitHub Actions authentication"
    }
  )
}

# ============================================================================
# IAM Role for GitHub Actions
# ============================================================================

resource "aws_iam_role" "github_actions" {
  name        = "${var.project_name}-github-actions-role"
  description = "IAM role for GitHub Actions OIDC authentication with SSM access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = [
              for pattern in var.allowed_branch_patterns :
              "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/${pattern}"
            ]
          }
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-github-actions-role"
      Description = "Role for GitHub Actions deployments via OIDC"
    }
  )
}

# ============================================================================
# IAM Policy for Least-Privilege Access
# ============================================================================

resource "aws_iam_policy" "github_actions_deployment" {
  name        = "${var.project_name}-github-actions-deployment-policy"
  description = "Least-privilege policy for GitHub Actions deployments via SSM"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # SSM Session Manager permissions for deployment
      {
        Effect = "Allow"
        Action = [
          "ssm:StartSession",
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:DescribeInstanceInformation"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:instance/*",
          "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
        ]
        Condition = {
          StringEquals = {
            "ssm:resourceTag/Project" = var.project_name
          }
        }
      },
      # EC2 describe permissions to find target instance
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus",
          "ec2:DescribeTags"
        ]
        Resource = "*"
      },
      # CloudWatch Logs permissions for session logging
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ssm/*"
        ]
      },
      # SSM Session Manager plugin requirements
      {
        Effect = "Allow"
        Action = [
          "ssm:TerminateSession",
          "ssm:ResumeSession",
          "ssm:DescribeSessions",
          "ssm:GetConnectionStatus"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-github-actions-policy"
      Description = "Deployment permissions for GitHub Actions"
    }
  )
}

# ============================================================================
# Attach Policy to Role
# ============================================================================

resource "aws_iam_role_policy_attachment" "github_actions_deployment" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_deployment.arn
}
