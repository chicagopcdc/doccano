# # Terraform state storage resources
# module "s3_backend" {
#   source = "git::ssh://git@github.com/chicagopcdc/terraform_modules.git//aws/terraform_s3_state_storage_resources?ref=0.1.1"

#   s3_bucket_name      = local.state_bucket_name
#   dynamodb_table_name = local.dynamodb_table_name
#   policy_name         = local.access_s3_state_policy

#   tags = var.default_tags
# }