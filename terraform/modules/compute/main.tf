# Compute Module - EC2, Security, Monitoring
# Creates application server with Docker and Tailscale

# ============================================================================
# Data Sources
# ============================================================================

# Get latest Ubuntu 24.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical official

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================================
# IAM Resources
# ============================================================================

# IAM role for EC2 instance to access CloudWatch
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-ec2-role"
    }
  )
}

# Attach CloudWatch Agent Server Policy for log writing
resource "aws_iam_role_policy_attachment" "cloudwatch_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Attach SSM Managed Instance Core Policy for Session Manager access
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Inline policy for Parameter Store access (least privilege)
resource "aws_iam_role_policy" "parameter_store_access" {
  name = "${var.project_name}-parameter-store-access"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowParameterStoreRead"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/gamepulse/${var.environment}/*",
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/gamepulse/shared/*"
        ]
      },
      {
        Sid    = "AllowKMSDecryption"
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = var.secrets_kms_key_arn
      }
    ]
  })
}

# IAM instance profile to attach role to EC2 instance
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.ec2_role.name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-instance-profile"
    }
  )
}

# ============================================================================
# Security Group
# ============================================================================

resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-security-group"
  description = "Security group for ${var.project_name} EC2 instance"
  vpc_id      = var.vpc_id

  # SSH access - restricted to admin IPs and specific Tailscale devices
  ingress {
    description = "SSH from admin IPs and authorized Tailscale devices"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = concat(
      var.admin_ip_cidrs,
      var.tailscale_device_ips
    )
  }

  # HTTP access - open to all for public dashboard
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS access - open to all for public dashboard
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound traffic - allow all
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-sg"
    }
  )
}

# ============================================================================
# CloudWatch Log Groups
# ============================================================================

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/gamepulse/backend"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-backend-logs"
      Application = "backend"
    }
  )
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/gamepulse/frontend"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-frontend-logs"
      Application = "frontend"
    }
  )
}

# ============================================================================
# SSH Key Pair
# ============================================================================

resource "aws_key_pair" "deployer" {
  key_name   = "${var.project_name}-key"
  public_key = file(pathexpand("~/.ssh/gamepulse-key.pub"))

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-ssh-key"
    }
  )
}

# ============================================================================
# EC2 Instance
# ============================================================================

resource "aws_instance" "app" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id
  key_name      = aws_key_pair.deployer.key_name

  # IAM instance profile for CloudWatch access
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  # Security group
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  # Root volume configuration
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true

    tags = merge(
      var.tags,
      {
        Name = "${var.project_name}-root-volume"
      }
    )
  }

  # User data script for Docker and Tailscale installation
  user_data = file("${path.module}/user_data.sh")

  # Enable detailed monitoring (free for t2.micro)
  monitoring = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-api"
      Role = "application-server"
    }
  )

  # Lifecycle settings
  lifecycle {
    create_before_destroy = false
  }
}

# ============================================================================
# Elastic IP
# ============================================================================

resource "aws_eip" "app" {
  domain = "vpc"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-eip"
    }
  )
}

# Associate Elastic IP with EC2 instance
resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}

# ============================================================================
# CloudTrail for SSM Session Auditing
# ============================================================================

# S3 bucket for CloudTrail logs
resource "aws_s3_bucket" "cloudtrail" {
  bucket = "${var.project_name}-cloudtrail-logs-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-cloudtrail-logs"
      Description = "CloudTrail logs for SSM session auditing"
    }
  )
}

# Block public access to CloudTrail S3 bucket
resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for CloudTrail bucket
resource "aws_s3_bucket_versioning" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket policy for CloudTrail
resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail.arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# CloudTrail for SSM session logging
# Note: SSM StartSession, ResumeSession, TerminateSession events are logged as management events
resource "aws_cloudtrail" "main" {
  name                          = "${var.project_name}-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  # Management events include SSM session events (StartSession, etc.)
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-cloudtrail"
      Description = "CloudTrail for SSM session auditing"
    }
  )

  depends_on = [aws_s3_bucket_policy.cloudtrail]
}
