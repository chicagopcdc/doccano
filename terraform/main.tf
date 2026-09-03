# VPC
module "vpc" {
  source = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/vpc?ref=1.0.8"
  
  cidr_block            = "172.32.16.0/20"
}

# ALB
module "doccano_alb" {
  source       = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/alb?ref=1.0.8"
  environment  = var.env_name
  app_name     = var.app_name
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnet_ids
  acm_cert_arn = module.acm_cert.acm_cert_arn
}
# ACM cert
module "acm_cert" {
  source = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/acm?ref=1.0.8"
  
  domain_url            =  local.domain_url
}

# EFS
module "doccano_efs" {
  source          = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/efs?ref=1.0.8"
  vpc_id          = module.vpc.vpc_id
  efs_name        = var.app_name
  subnet_ids      = module.vpc.private_subnet_ids
  security_groups = [aws_security_group.ecs_tasks.id]
  access_points = [
    {
      name       = "media"
      posix_user = { uid = 1000, gid = 1000 }
      root_directory = {
        path = "/backend/media"
        creation_info = { owner_uid = "1000", owner_gid = "1000", permissions = "755" }
      }
    },
    {
      name       = "staticfiles"
      posix_user = { uid = 1000, gid = 1000 }
      root_directory = {
        path = "/backend/staticfiles"
        creation_info = { owner_uid = "1000", owner_gid = "1000", permissions = "755" }
      }
    },
    {
      name       = "tmp"
      posix_user = { uid = 1000, gid = 1000 }
      root_directory = {
        path = "/backend/filepond-temp-uploads"
        creation_info = { owner_uid = "1000", owner_gid = "1000", permissions = "755" }
      }
    }
  ]
}

# RDS
module "rds" {
  source              = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/rds?ref=1.0.8"
  rds_security_groups = aws_security_group.ecs_tasks.id
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  db_name             = var.app_name
}

# ECS
module "doccano_ecs" {
  source = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/ecs?ref=1.0.8"

  app_name               = var.app_name
  app_port               = var.app_port
  app_image              = "quay.io/pcdc/doccano:${var.application_tag}"
  cpu                    = 512
  memory                 = 1024
  ecs_execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  security_group_id      = aws_security_group.ecs_tasks.id
  subnet_ids             = module.vpc.private_subnet_ids
  alb_target_group_arns  = [module.doccano_alb.alb_target_group_arn]
  include_service        = false
}
