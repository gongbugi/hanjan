output "public_ip" {
  value = oci_core_instance.k3s.public_ip
}

output "ssh" {
  value = "ssh ubuntu@${oci_core_instance.k3s.public_ip}"
}

output "backup_bucket" {
  value = oci_objectstorage_bucket.backups.name
}

output "object_storage_namespace" {
  value = data.oci_objectstorage_namespace.this.namespace
}

output "s3_compat_endpoint" {
  description = "백업 CronJob과 Terraform 원격 상태가 쓰는 S3 호환 엔드포인트"
  value       = "https://${data.oci_objectstorage_namespace.this.namespace}.compat.objectstorage.${var.region}.oraclecloud.com"
}
