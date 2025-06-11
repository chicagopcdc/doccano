module "doccano_ecs" {
  source            = "../modules/ecs"
  app_name          = var.app_name
  subnet_ids        = var.private_subnet_ids
  lb_security_group = [module.doccano_alb.alb_security_group]
  load_balancer = {
    container_port = 8080
  }
  vpc_id           = var.vpc_id
  target_group_arn = module.doccano_alb.alb_target_group_arn
  container_name   = "nginx"
  # container_count = 2
  efs_volume                    = module.doccano_efs.efs_id
  efs_access_point_static_files = module.doccano_efs.access_point_ids["staticfiles"]
  efs_access_point_id_media     = module.doccano_efs.access_point_ids["media"]
  efs_access_point_id_tmp       = module.doccano_efs.access_point_ids["tmp"]
  database_url                  = aws_ssm_parameter.DATABASE_URL.arn
}

module "doccano_efs" {
  source          = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/efs?ref=0.5.0"
  vpc_id          = var.vpc_id
  efs_name        = var.app_name
  subnet_ids      = var.private_subnet_ids
  security_groups = [module.doccano_ecs.ecs_tasks_sg]
  access_points = [
    {
      name       = "media"
      posix_user = { uid = 1000, gid = 1000 }
      root_directory = {
        path = "/backend/media"
        creation_info = {
          owner_uid   = "1000"
          owner_gid   = "1000"
          permissions = "755"
        }
      }
    },
    {
      name       = "staticfiles"
      posix_user = { uid = 1000, gid = 1000 }
      root_directory = {
        path = "/backend/staticfiles"
        creation_info = {
          owner_uid   = "1000"
          owner_gid   = "1000"
          permissions = "755"
        }
      }
    },
    {
      name       = "tmp"
      posix_user = { uid = 1000, gid = 1000 }
      root_directory = {
        path = "/backend/filepond-temp-uploads"
        creation_info = {
          owner_uid   = "1000"
          owner_gid   = "1000"
          permissions = "755"
        }
      }
    }
  ]
}

module "doccano_alb" {
  source      = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/alb?ref=0.5.0"
  environment = var.environment
  app_name    = "doccano"
  vpc_id      = var.vpc_id
  subnet_ids  = var.private_subnet_ids
  acm_cert_arn =  "arn:aws:acm:us-east-1:471835990085:certificate/c1cebe37-738d-4766-a635-bc23d3e8caa7" # 
}

module "rds" {
  source              = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/rds?ref=0.5.0"
  rds_security_groups = module.doccano_ecs.ecs_tasks_sg
  vpc_id              = var.vpc_id
  subnet_ids          = var.private_subnet_ids
  db_name             = "doccano"
}

resource "aws_ssm_parameter" "DATABASE_URL" {
  name  = "/${var.environment}/${var.app_name}/DATABASE_URL"
  type  = "SecureString"
  value = "postgres://doccano:${module.rds.rds_random_password}@${module.rds.rds_enpoint}/doccano?sslmode=disable"
}