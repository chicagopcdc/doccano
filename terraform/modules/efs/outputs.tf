output "aws_efs_file_system" {
    value = aws_efs_file_system.this.id
}

output "access_point_id_static_files" {
  value = aws_efs_access_point.static_files.id
}

output "access_point_id_media" {
  value = aws_efs_access_point.media.id
}

output "access_point_id_tmp" {
  value = aws_efs_access_point.tmp.id
}