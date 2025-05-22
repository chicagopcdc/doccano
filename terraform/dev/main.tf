module "doccano_ecs" {
  source = "../modules/ecs"
  app_name =  var.app_name
  subnet_ids = var.private_subnet_ids
  lb_security_group = [module.doccano_alb.lb_security_group]
  load_balancer = {
    container_port = 8080
  }
  vpc_id = var.vpc_id
  target_group_arn = module.doccano_alb.doccano_target_group.arn
  container_name = "nginx"
  container_count = 2
  efs_volume = module.doccano_efs.aws_efs_file_system
  aws_efs_access_point_static_files = module.doccano_efs.access_point_id_static_files
  efs_access_point_id_media = module.doccano_efs.access_point_id_media
  efs_access_point_id_tmp = module.doccano_efs.access_point_id_tmp
  database_url = module.rds.database_url
}

module "doccano_efs" {
  source = "../modules/efs"
  efs_name = var.app_name
  vpc_id = var.vpc_id
  subnet_ids = var.private_subnet_ids
  security_groups = [module.doccano_ecs.ecs_tasks_sg]
}

module "doccano_alb" {
  source = "../modules/alb"
  environment = var.environment
  vpc_id = var.vpc_id
  subnet_ids = var.private_subnet_ids
}

module "rds" {
  source = "../modules/rds"
  rds_security_groups = module.doccano_ecs.ecs_tasks_sg
  vpc_id = var.vpc_id
}