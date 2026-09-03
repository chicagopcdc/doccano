# Get the AWS account ID
data "aws_caller_identity" "current" {}

locals {
  # S3 variables
  state_bucket_name      = "${var.app_name}-${var.env_name}-state-bucket"
  access_s3_state_policy = "${var.app_name}-${var.env_name}-state-bucket-policy"

  # Dynamo DB
  dynamodb_table_name = "${var.app_name}-${var.env_name}-dynamodb-table-terraform-state"

  # ACM, ALB
  domain_url = "${var.app_name}${var.env_name != "prod" ? "-${var.env_name}" : ""}.${var.base_domain_url}"

}