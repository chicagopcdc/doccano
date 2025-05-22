output "doccano_target_group" {
  value = aws_lb_target_group.doccano_target_group
}

output "lb_security_group" {
  value = aws_security_group.lb.id
}