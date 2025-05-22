variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "dev"
}

variable "app_name" {
  default = "doccano"
}

variable "private_subnet_ids" {
  default = ["subnet-013e8d4a439201a84", "subnet-0025d9b857876f8a5"]
}

variable "vpc_id" {
  default = "vpc-0ab59a594548de1b9" #doccano dev vpc
}

variable "efs_sg_id" {
  default = ""
}

# variable "alb_sg_id" {
#   default = ""
# }