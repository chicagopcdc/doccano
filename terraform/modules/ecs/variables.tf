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

variable "doccano_image" {
  default = "quay.io/pcdc/doccano"
}

variable "application_tag" {
  default = "latest"
}

variable "rabbitmq_image" {
  default = "rabbitmq"
}

variable "cpu" {
  description = "Default cpu amount for task"
  default     = "512"
}

variable "memory" {
  description = "Default memory amount for task"
  default     = "1024"
}


variable "efs_access_point_static_files" {
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