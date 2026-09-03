resource "aws_ssm_parameter" "DATABASE_URL" {
  name  = "/${var.env_name}/${var.app_name}/DATABASE_URL"
  type  = "SecureString"
  value = "postgres://doccano:${module.rds.rds_random_password}@${module.rds.rds_enpoint}/doccano?sslmode=require"
}

resource "aws_ssm_parameter" "ADMIN_PASSWORD" {
  name  = "/${var.env_name}/${var.app_name}/ADMIN_PASSWORD"
  type  = "SecureString"
  value = "change-password"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "RABBITMQ_DEFAULT_PASS" {
  name  = "/${var.env_name}/${var.app_name}/RABBITMQ_DEFAULT_PASS"
  type  = "SecureString"
  value = "doccano"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "FLOWER_BASIC_AUTH" {
  name  = "/${var.env_name}/${var.app_name}/FLOWER_BASIC_AUTH"
  type  = "SecureString"
  value = "change-password"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "CELERY_BROKER_URL" {
  name  = "/${var.env_name}/${var.app_name}/CELERY_BROKER_URL"
  type  = "SecureString"
  value = "amqp://doccano:doccano@localhost"

  lifecycle {
    ignore_changes = [value]
  }
}
