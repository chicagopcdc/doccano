resource "aws_ssm_parameter" "ADMIN_PASSWORD" {
  name      = "/${var.environment}/${var.app_name}/ADMIN_PASSWORD"
  type      = "SecureString"
  value     = "change-password"
  lifecycle {
    ignore_changes = [ "value" ]
  }
}

resource "aws_ssm_parameter" "RABBITMQ_DEFAULT_PASS" {
  name      = "/${var.environment}/${var.app_name}/RABBITMQ_DEFAULT_PASS"
  type      = "SecureString"
  value     = "doccano"
  lifecycle {
    ignore_changes = [ "value" ]
  }
}

resource "aws_ssm_parameter" "FLOWER_BASIC_AUTH" {
  name      = "/${var.environment}/${var.app_name}/FLOWER_BASIC_AUTH"
  type      = "SecureString"
  value     = "change-password"
  lifecycle {
    ignore_changes = [ "value" ]
  }
}

resource "aws_ssm_parameter" "CELERY_BROKER_URL" {
  name      = "/${var.environment}/${var.app_name}/CELERY_BROKER_URL"
  type      = "SecureString"
  value     = "amqp://doccano:doccano@localhost"
  lifecycle {
    ignore_changes = [ "value" ]
  }
}