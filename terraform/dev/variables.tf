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
  default = ["subnet-02daaea0d231975df", "subnet-0c7f4570d0c82bdc3"]
}

variable "vpc_id" {
  default = "vpc-0e20603ab3c8dd65e"
}

variable "efs_sg_id" {
  default = ""
}

# variable "alb_sg_id" {
#   default = ""
# }