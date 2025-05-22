output "random_string" {
  value = random_string.randompostgres.result
}

output "rds_enpoint" {
  value = aws_db_instance.this.endpoint
}

output "database_url" {
  value = aws_ssm_parameter.DATABASE_URL.arn
}