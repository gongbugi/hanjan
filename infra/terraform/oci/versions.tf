terraform {
  required_version = ">= 1.9"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 9.1"
    }
  }

  # 원격 상태는 OCI Object Storage의 S3 호환 엔드포인트에 둔다 (Always Free 20GB 안).
  # 값은 backend.hcl로 넣는다: terraform init -backend-config=backend.hcl
  backend "s3" {}
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}
