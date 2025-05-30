resource "aws_cloudwatch_log_group" "doccano" {
  name              = "/ecs/doccano-logs"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "flower" {
  name              = "/ecs/flower-logs"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "celery" {
  name              = "/ecs/celery-logs"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "nginx" {
  name              = "/ecs/nginx-logs"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "rabbitmq" {
  name              = "/ecs/rabbitmq-logs"
  retention_in_days = 7
}