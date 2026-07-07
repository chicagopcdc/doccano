provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      Name        = var.app_name
    }
  }
}

# terraform {
#   backend "s3" {
#     bucket         = "pcdc-doccano-dev-tfstate-bucket"
#     key            = "terraform.tfstate"
#     region         = var.aws_region
#     dynamodb_table = "pcdc-doccano-dynomodb-table-terraform-lock"
#     encrypt        = true
#   }
# }