resource "aws_iam_role" "ecs_task_execution_role" {
  name = "EcsTaskExecutionRole-${var.app_name}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  for_each = toset([
    # "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    "arn:aws:iam::aws:policy/AmazonSSMFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
    "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
  ])
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = each.value
}

# resource "aws_iam_role_policy" "ecs_execution_inline" {
#   name = "task-inline-policy"

# }