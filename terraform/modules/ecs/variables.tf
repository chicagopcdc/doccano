variable "environment" {
  default = "dev"
}

variable "app_name" {
  default = "doccano"
}

variable "container_count" {
  default = 1
}

variable "container_name" {
}

variable "container_port" {
  default = 8080
}

variable "aws_efs_access_point_static_files" { 
}

variable "efs_access_point_id_media" {
}

variable "efs_access_point_id_tmp" {
}

variable "vpc_id" {
}

variable "target_group_arn" {}

variable "lb_security_group" {
  type = list(string)
}

variable "subnet_ids" {
  type    = list(string)
  default = [""]
}

variable "database_url" {
  default = ""
}

variable "load_balancer" {
}

variable "efs_volume" {
  type = string
}