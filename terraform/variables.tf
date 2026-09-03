variable "aws_region" {
  default = "us-east-1"
}

variable "env_name" {
  default = "dev"
}

variable "app_name" {
  default = "doccano"
}

variable "app_port" {
  default     = 8080
}

variable "base_domain_url" {
  default = "pedscommons.org"
}

variable "application_tag" {
  default     = "latest"
}

variable "rabbitmq_image" {
  default     = "rabbitmq"
}

# variable "alb_sg_id" {
#   default = ""
# }