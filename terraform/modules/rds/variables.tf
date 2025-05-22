variable "vpc_id" {
  
}
variable "app_name" {
  default = "doccano"
}

variable "environment" {
  default = "dev"
}

variable "rds_instance_name" {
  default = "doccano"
}

variable "rds_instance_skip_final_snapshot" {
  description = "rds instance skip final snapshot"
  default     = false
}

variable "rds_instance_backup_retention_period" {
  description = "The days to retain backups for. Must be between 0 and 35"
  default     = 0
}

variable "rds_instance_multi_az" {
  description = "Specifies if the RDS instance is multi-AZ"
  default     = false
}

variable "rds_instance_publicly_accessible" {
  description = "Control if instance is publicly accessible"
  default     = true
}

# variable "rds_instance_username" {
#   default = ""  #Defaulting to app name
# }

variable "rds_instance_allocated_storage" {
  description = "The allocated storage in GiB"
  default     = 10
}

variable "rds_instance_storage_type" {
  description = "gp2, io1, standard"
  default     = "gp2"
}

variable "rds_instance_class" {
  description = "The instance type of the RDS instance"
  default     = "db.t3.micro"
}

variable "rds_instance_engine" {
  default = "postgres"
}

variable "rds_instance_engine_version" {
  description = "The engine version to use. If auto_minor_version_upgrade is enabled, you can provide a prefix of the version such as 5.7 (for 5.7.10) and this attribute will ignore differences in the patch version automatically (e.g. 5.7.17)"
  default     = "13"
}

variable "rds_instance_max_allocated_storage" {
  description = "Specifies the value for Storage Autoscaling"
  default     = 0
}

variable "rds_instance_password" {
  description = "Password to use"
  default     = ""
}

# variable "rds_instance_identifier" {
#   description = "The name of the RDS instance, if omitted, Terraform will assign a random, unique identifier"
#   type        = string
# }

# variable "database_url" {
#   default = ""
# }
variable "rds_security_groups" {
  default = ""
}