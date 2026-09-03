resource "aws_ecs_task_definition" "doccano" {
  family                   = var.app_name
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn

  volume {
    name = "static-volume"
    efs_volume_configuration {
      file_system_id = module.doccano_efs.efs_id
      root_directory = "/"
      authorization_config {
        access_point_id = module.doccano_efs.access_point_ids["staticfiles"]
        iam             = "ENABLED"
      }
      transit_encryption = "ENABLED"
    }
  }

  volume {
    name = "media-volume"
    efs_volume_configuration {
      file_system_id = module.doccano_efs.efs_id
      root_directory = "/"
      authorization_config {
        access_point_id = module.doccano_efs.access_point_ids["media"]
        iam             = "ENABLED"
      }
      transit_encryption = "ENABLED"
    }
  }

  volume {
    name = "tmp-volume"
    efs_volume_configuration {
      file_system_id = module.doccano_efs.efs_id
      root_directory = "/"
      authorization_config {
        access_point_id = module.doccano_efs.access_point_ids["tmp"]
        iam             = "ENABLED"
      }
      transit_encryption = "ENABLED"
    }
  }

  container_definitions = jsonencode([
    {
      name      = "doccano"
      image     = "quay.io/pcdc/doccano:${var.application_tag}"
      essential = true
      mountPoints = [
        { sourceVolume = "static-volume", containerPath = "/backend/staticfiles" },
        { sourceVolume = "media-volume",  containerPath = "/backend/media" },
        { sourceVolume = "tmp-volume",    containerPath = "/backend/filepond-temp-uploads" }
      ]
      environment = [
        { name = "ADMIN_USERNAME",         value = "admin" },
        { name = "ADMIN_EMAIL",            value = "pcdc_root@lists.uchicago.edu" },
        { name = "ALLOW_SIGNUP",           value = "False" },
        { name = "DEBUG",                  value = "False" },
        { name = "DJANGO_SETTINGS_MODULE", value = "config.settings.production" }
      ]
      secrets = [
        { name = "ADMIN_PASSWORD",    valueFrom = aws_ssm_parameter.ADMIN_PASSWORD.arn },
        { name = "DATABASE_URL",      valueFrom = aws_ssm_parameter.DATABASE_URL.arn },
        { name = "CELERY_BROKER_URL", valueFrom = aws_ssm_parameter.CELERY_BROKER_URL.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/doccano-logs"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name       = "celery"
      image      = "quay.io/pcdc/doccano:${var.application_tag}"
      essential  = true
      entryPoint = ["/opt/bin/prod-celery.sh"]
      mountPoints = [
        { sourceVolume = "media-volume", containerPath = "/backend/media" },
        { sourceVolume = "tmp-volume",   containerPath = "/backend/filepond-temp-uploads" }
      ]
      dependsOn = [
        { containerName = "rabbitmq", condition = "START" }
      ]
      environment = [
        { name = "PYTHONUNBUFFERED",       value = "1" },
        { name = "ADMIN_EMAIL",            value = "pcdc_root@lists.uchicago.edu" },
        { name = "DJANGO_SETTINGS_MODULE", value = "config.settings.production" }
      ]
      secrets = [
        { name = "CELERY_BROKER_URL", valueFrom = aws_ssm_parameter.CELERY_BROKER_URL.arn },
        { name = "DATABASE_URL",      valueFrom = aws_ssm_parameter.DATABASE_URL.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.celery.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name       = "flower"
      image      = "quay.io/pcdc/doccano:${var.application_tag}"
      essential  = true
      entryPoint = ["/opt/bin/prod-flower.sh"]
      portMappings = [
        { containerPort = 5555, hostPort = 5555 }
      ]
      dependsOn = [
        { containerName = "celery", condition = "START" }
      ]
      environment = [
        { name = "PYTHONUNBUFFERED",       value = "1" },
        { name = "ADMIN_EMAIL",            value = "pcdc_root@lists.uchicago.edu" },
        { name = "DJANGO_SETTINGS_MODULE", value = "config.settings.production" }
      ]
      secrets = [
        { name = "CELERY_BROKER_URL", valueFrom = aws_ssm_parameter.CELERY_BROKER_URL.arn },
        { name = "DATABASE_URL",      valueFrom = aws_ssm_parameter.DATABASE_URL.arn },
        { name = "FLOWER_BASIC_AUTH", valueFrom = aws_ssm_parameter.FLOWER_BASIC_AUTH.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.flower.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name      = "rabbitmq"
      image     = "${var.rabbitmq_image}:${var.application_tag}"
      essential = true
      portMappings = [
        { containerPort = 5672, hostPort = 5672 }
      ]
      environment = [
        { name = "RABBITMQ_DEFAULT_USER", value = "doccano" }
      ]
      secrets = [
        { name = "RABBITMQ_DEFAULT_PASS", valueFrom = aws_ssm_parameter.RABBITMQ_DEFAULT_PASS.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.rabbitmq.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name       = "nginx"
      image      = "quay.io/pcdc/doccano:${var.application_tag}"
      essential  = true
      entryPoint = ["/bin/sh", "-c"]
      command    = ["envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
      portMappings = [
        { containerPort = 8080, hostPort = 8080 }
      ]
      mountPoints = [
        { sourceVolume = "static-volume", containerPath = "/static" },
        { sourceVolume = "media-volume",  containerPath = "/media" }
      ]
      dependsOn = [
        { containerName = "doccano", condition = "COMPLETE" }
      ]
      environment = [
        { name = "API_URL",            value = "http://localhost:8000" },
        { name = "GOOGLE_TRACKING_ID", value = "" },
        { name = "WORKER_PROCESSES",   value = "auto" }
      ]
      secrets = []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.nginx.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "doccano" {
  name                   = var.app_name
  cluster                = module.doccano_ecs.cluster_arn
  task_definition        = aws_ecs_task_definition.doccano.arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = module.vpc.private_subnet_ids
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = module.doccano_alb.alb_target_group_arn
    container_name   = "nginx"
    container_port   = var.app_port
  }
}
