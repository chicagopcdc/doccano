resource "aws_db_instance" "this" {
  identifier              = var.app_name #var.rds_instance_identifier
  engine                  = var.rds_instance_engine
  engine_version          = var.rds_instance_engine_version
  instance_class          = var.rds_instance_class
  allocated_storage       = var.rds_instance_allocated_storage
  max_allocated_storage   = var.rds_instance_max_allocated_storage
  db_name                 = var.app_name #var.rds_instance_name
  username                = var.app_name
  password                = var.rds_instance_password == "" ? random_string.randompostgres.result : var.rds_instance_password
  port                    = 5432
  publicly_accessible     = var.rds_instance_publicly_accessible
  multi_az                = var.rds_instance_multi_az
  storage_encrypted       = true
  backup_retention_period = var.rds_instance_backup_retention_period
  skip_final_snapshot     = var.rds_instance_skip_final_snapshot
  vpc_security_group_ids  = [aws_security_group.rds.id]
  db_subnet_group_name    = aws_db_subnet_group.this.name

  tags = {
    Name        = var.rds_instance_name
    environment = var.environment
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.rds_instance_name}-${var.environment}"
  subnet_ids = ["subnet-02daaea0d231975df", "subnet-0c7f4570d0c82bdc3"]

  tags = {
    Name = var.rds_instance_name
  }
}

resource "random_string" "randompostgres" {
  length  = 16
  special = false
}

resource "aws_ssm_parameter" "POSTGRES_PASSWORD" {
  name      = "/${var.environment}/${var.app_name}/POSTGRES_PASSWORD"
  type      = "SecureString"
  value     = random_string.randompostgres.result
}

resource "aws_ssm_parameter" "DATABASE_URL" {
  name      = "/${var.environment}/${var.app_name}/DATABASE_URL"
  type      = "SecureString"
  value     = "postgres://doccano:${random_string.randompostgres.result}@${aws_db_instance.this.endpoint}/doccano?sslmode=disable"
}


#RDS DB Security Group
resource "aws_security_group" "rds" {
  name        = "doccano-rds-security-group"
  description = "controls access to the RDS"
  vpc_id      = var.vpc_id

  ingress {
    protocol  = "tcp"
    from_port = 5432
    to_port   = 5432
    # cidr_blocks = ["0.0.0.0/0"]
    security_groups = [var.rds_security_groups]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}