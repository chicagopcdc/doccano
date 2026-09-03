output "acm_certificate_dns_validation" {
  description = "ACM certificate domain validation options (CNAME records for DNS validation)"
  value       = module.acm_cert.acm_certificate_dns_validation
}

output "acm_certificate_domain_name" {
  description = "Domain name the ACM certificate was issued for"
  value       = module.acm_cert.certificate_domain_name
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.doccano_alb.alb_dns_name
}

output "app_url" {
  description = "Application URL"
  value       = "https://${local.domain_url}"
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.doccano.name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.rds_enpoint
}

output "efs_id" {
  description = "EFS file system ID"
  value       = module.doccano_efs.efs_id
}
