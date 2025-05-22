resource "aws_efs_file_system" "this" {
  creation_token = var.efs_name
}

resource "aws_efs_mount_target" "this" {
  for_each        = toset(var.subnet_ids)
  file_system_id  = aws_efs_file_system.this.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs_sg.id]
}


resource "aws_efs_access_point" "static_files" {
  file_system_id = aws_efs_file_system.this.id

  root_directory {
    path = "/backend/staticfiles"
    creation_info {
      owner_uid = 1000
      owner_gid = 1000
      permissions = "755"
    }
  }
  posix_user {
    uid = 1000
    gid = 1000
  }
}

resource "aws_efs_access_point" "media" {
  file_system_id = aws_efs_file_system.this.id

  root_directory {
    path = "/backend/media"
    creation_info {
      owner_uid = 1000
      owner_gid = 1000
      permissions = "755"
    }
  }
    posix_user {
    uid = 1000
    gid = 1000
  }
}

resource "aws_efs_access_point" "tmp" {
  file_system_id = aws_efs_file_system.this.id

  root_directory {
    path = "/backend/filepond-temp-uploads"
    creation_info {
      owner_uid = 1000
      owner_gid = 1000
      permissions = "755"
    }
  }
    posix_user {
    uid = 1000
    gid = 1000
  }
}


resource "aws_security_group" "efs_sg" {
  name   = "${var.efs_name}-efs-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = var.security_groups #[aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}