resource "aws_ecs_cluster" "cluster" {
  name = "${var.environment}-cluster"
}