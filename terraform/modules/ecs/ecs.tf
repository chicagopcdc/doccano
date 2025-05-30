resource "aws_ecs_service" "doccano_service" {
  name                   = var.app_name
  cluster                = aws_ecs_cluster.cluster.id
  task_definition        = aws_ecs_task_definition.doccano.arn
  desired_count          = var.container_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = var.subnet_ids
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = var.container_name
    container_port   = var.container_port
  }

}


resource "aws_ecs_task_definition" "doccano" {
  family                   = "doccano"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn

  volume {
    name = "static-volume"
    efs_volume_configuration {
      file_system_id = var.efs_volume
      root_directory = "/"
      authorization_config {
        access_point_id = var.efs_access_point_static_files
        iam             = "ENABLED"
      }
      transit_encryption = "ENABLED"
    }
  }
  volume {
    name = "media-volume"
    efs_volume_configuration {
      file_system_id = var.efs_volume
      root_directory = "/"
      authorization_config {
        access_point_id = var.efs_access_point_id_media
        iam             = "ENABLED"
      }
      transit_encryption = "ENABLED"
    }
  }
  volume {
    name = "tmp-volume"
    efs_volume_configuration {
      file_system_id = var.efs_volume
      root_directory = "/"
      authorization_config {
        access_point_id = var.efs_access_point_id_tmp
        iam             = "ENABLED"
      }
      transit_encryption = "ENABLED"
    }
  }
  container_definitions = jsonencode([
    {
      name      = "doccano"
      image     = "quay.io/pcdc/doccano:be_20240813"
      essential = true
      mountPoints = [
        {
          sourceVolume  = "static-volume"
          containerPath = "/backend/staticfiles"
        },
        {
          sourceVolume  = "media-volume"
          containerPath = "/backend/media"
        },
        {
          sourceVolume  = "tmp-volume"
          containerPath = "/backend/filepond-temp-uploads"
        }
      ]
      environment = [{
        name  = "ADMIN_USERNAME"
        value = "admin"
        }, {
        name  = "ADMIN_EMAIL"
        value = "pcdc_root@lists.uchicago.edu"
        }, {
        name  = "ALLOW_SIGNUP"
        value = "False"
        }, {
        name  = "DEBUG"
        value = "False"
        }, {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
        }, {
        name  = "CELERY_BROKER_URL"
        value = aws_ssm_parameter.CELERY_BROKER_URL.value
        }
      ]
      "logConfiguration" : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : "/ecs/doccano-logs",
          "awslogs-region" : "us-east-1",
          "awslogs-stream-prefix" : "ecs"
        }
      }
      secrets = [{
        name      = "ADMIN_PASSWORD"
        valueFrom = aws_ssm_parameter.ADMIN_PASSWORD.arn
        }, {
        name      = "DATABASE_URL"
        valueFrom = var.database_url
        }
      ]
    },
    {
      name       = "celery"
      image      = "quay.io/pcdc/doccano:be_20240813"
      essential  = true
      entryPoint = ["/opt/bin/prod-celery.sh"]
      mountPoints = [
        {
          sourceVolume  = "media-volume"
          containerPath = "/backend/media"
        },
        {
          sourceVolume  = "tmp-volume"
          containerPath = "/backend/filepond-temp-uploads"
        }
      ]
      depends_on = [
        {
          containerName = "rabbitmq"
          condition     = "START"
        }
      ]
      environment = [{
        name  = "PYTHONUNBUFFERED"
        value = "1"
        }, {
        name  = "ADMIN_EMAIL"
        value = "pcdc_root@lists.uchicago.edu"
        }, {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
        }
      ]
      "logConfiguration" : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : "/ecs/celery-logs",
          "awslogs-region" : "us-east-1",
          "awslogs-stream-prefix" : "ecs"
        }
      }
      secrets = [{
        name      = "CELERY_BROKER_URL"
        valueFrom = aws_ssm_parameter.CELERY_BROKER_URL.arn
        }, {
        name      = "DATABASE_URL"
        valueFrom = var.database_url
        }
      ]
    },
    {
      name       = "flower"
      image      = "quay.io/pcdc/doccano:be_20240813"
      essential  = true
      entryPoint = ["/opt/bin/prod-flower.sh"]
      portMappings = [
        {
          containerPort = 5555
          hostPort      = 5555
        }
      ]
      depends_on = [
        {
          containerName = "celery"
          condition     = "START"
        }
      ]
      "logConfiguration" : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : "/ecs/flower-logs",
          "awslogs-region" : "us-east-1",
          "awslogs-stream-prefix" : "ecs"
        }
      }
      environment = [{
        name  = "PYTHONUNBUFFERED"
        value = "1"
        }, {
        name  = "ADMIN_EMAIL"
        value = "pcdc_root@lists.uchicago.edu"
        }, {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
        }
      ]
      secrets = [{
        name      = "CELERY_BROKER_URL"
        valueFrom = aws_ssm_parameter.CELERY_BROKER_URL.arn
        }, {
        name      = "DATABASE_URL"
        valueFrom = var.database_url
        },
        {
          name      = "FLOWER_BASIC_AUTH"
          valueFrom = aws_ssm_parameter.FLOWER_BASIC_AUTH.arn
        }
      ]
    },
    {
      name      = "rabbitmq"
      image     = "rabbitmq:3.10.7-alpine"
      essential = true
      portMappings = [
        {
          containerPort = 5672
          hostPort      = 5672
        }
      ]
      "logConfiguration" : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : "/ecs/rabbitmq-logs",
          "awslogs-region" : "us-east-1",
          "awslogs-stream-prefix" : "ecs"
        }
      }
      environment = [{
        name  = "RABBITMQ_DEFAULT_USER"
        value = "doccano"
      }]
      secrets = [{
        name      = "RABBITMQ_DEFAULT_PASS"
        valueFrom = aws_ssm_parameter.RABBITMQ_DEFAULT_PASS.arn
        }
      ]
    },
    {
      name       = "nginx"
      image      = "954006452010.dkr.ecr.us-east-1.amazonaws.com/doccano-nginx:latest" #"quay.io/pcdc/doccano:fe_20240813"
      essential  = true
      entryPoint = ["/bin/sh", "-c"]
      command    = ["envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
        }
      ]
      mountPoints = [
        {
          sourceVolume  = "static-volume"
          containerPath = "/static"
        },
        {
          sourceVolume  = "media-volume"
          containerPath = "/media"
        }
      ]
      depends_on = [
        {
          containerName = "doccano"
          condition     = "COMPLETE"
        }
      ]
      "logConfiguration" : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : "/ecs/nginx-logs",
          "awslogs-region" : "us-east-1",
          "awslogs-stream-prefix" : "ecs"
        }
      }
      environment = [{
        name  = "API_URL"
        value = "http://localhost:8000"
        }, {
        name  = "GOOGLE_TRACKING_ID"
        value = ""
        }, {
        name  = "WORKER_PROCESSES"
        value = "auto"
      }]
      secrets = []
    }
  ])
}


