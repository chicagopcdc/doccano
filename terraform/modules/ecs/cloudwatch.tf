resource "aws_cloudwatch_log_group" "doccano" {
  name = "/ecs/doccano-logs"
}

resource "aws_cloudwatch_log_group" "flower" {
  name = "/ecs/flower-logs"
}

resource "aws_cloudwatch_log_group" "celery" {
  name = "/ecs/celery-logs"
}

resource "aws_cloudwatch_log_group" "nginx" {
  name = "/ecs/nginx-logs"
}

resource "aws_cloudwatch_log_group" "rabbitmq" {
  name = "/ecs/rabbitmq-logs"
}