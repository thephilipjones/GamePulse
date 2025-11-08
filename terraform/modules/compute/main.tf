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
# EC2 Instance
# ============================================================================

resource "aws_instance" "app" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id

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
