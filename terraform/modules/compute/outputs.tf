output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "instance_state" {
  description = "Current state of the EC2 instance"
  value       = aws_instance.app.instance_state
}

output "public_ip" {
  description = "Elastic IP address for EC2 instance"
  value       = aws_eip.app.public_ip
}

output "private_ip" {
  description = "Private IP address of EC2 instance"
  value       = aws_instance.app.private_ip
}

output "security_group_id" {
  description = "Security group ID for the EC2 instance"
  value       = aws_security_group.ec2_sg.id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/gamepulse-key -p 22 ubuntu@${aws_eip.app.public_ip}"
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    backend  = aws_cloudwatch_log_group.backend.name
    frontend = aws_cloudwatch_log_group.frontend.name
  }
}
