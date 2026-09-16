variable "tenancy_ocid" {
  type = string
}

variable "user_ocid" {
  type = string
}

variable "fingerprint" {
  type = string
}

variable "private_key_path" {
  type = string
}

variable "compartment_ocid" {
  type        = string
  description = "리소스를 만들 컴파트먼트. 루트 대신 hanjan 전용 컴파트먼트를 권장한다."
}

variable "region" {
  type        = string
  description = "홈 리전. Always Free 컴퓨트는 홈 리전에서만 만들 수 있고, 홈 리전은 가입 뒤 사실상 바꿀 수 없다."

  validation {
    # Oracle 공식 문서(Always Free Resources)에 A1 생성 예외로 명시된 리전 — 2026-09 확인
    condition     = var.region != "ap-chuncheon-1"
    error_message = "South Korea North (ap-chuncheon-1) is excluded from Always Free Ampere A1 instances."
  }
}

variable "availability_domain_index" {
  type        = number
  default     = 0
  description = "'out of host capacity'가 나면 다른 가용 도메인 번호로 다시 시도한다."
}

variable "ocpus" {
  type    = number
  default = 2

  validation {
    # 2026-06-15에 4 OCPU → 2 OCPU로 줄었다. 넘으면 과금되거나 인스턴스가 종료된다
    condition     = var.ocpus >= 1 && var.ocpus <= 2
    error_message = "Always Free Ampere A1 allows at most 2 OCPUs per tenancy."
  }
}

variable "memory_gb" {
  type    = number
  default = 12

  validation {
    condition     = var.memory_gb >= 1 && var.memory_gb <= 12
    error_message = "Always Free Ampere A1 allows at most 12 GB of memory per tenancy."
  }
}

variable "boot_volume_gb" {
  type    = number
  default = 100

  validation {
    condition     = var.boot_volume_gb >= 50 && var.boot_volume_gb <= 200
    error_message = "Boot volume must be 50-200 GB. Always Free block storage is 200 GB in total."
  }
}

variable "ssh_public_key" {
  type = string
}

variable "admin_cidr" {
  type        = string
  description = "SSH를 허용할 내 IP 대역 (예: 203.0.113.7/32). 전체 공개 금지."

  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && var.admin_cidr != "0.0.0.0/0"
    error_message = "The admin_cidr value must be a valid CIDR and must not be 0.0.0.0/0."
  }
}

variable "ingress_mode" {
  type        = string
  default     = "public_https"
  description = "public_https(기본): 80·443 개방 + 무료 DDNS 호스트명 + Let's Encrypt — 도메인을 사지 않기로 한 결과(2026-09-16) / tunnel: Cloudflare Tunnel, 인바운드 0개지만 Cloudflare에 영역(도메인)이 있어야 한다."

  validation {
    condition     = contains(["tunnel", "public_https"], var.ingress_mode)
    error_message = "The ingress_mode value must be tunnel or public_https."
  }
}

variable "deploy_repo_url" {
  description = "Manifest repo the node pulls every few minutes (replaces ArgoCD)."
  type        = string
  default     = "https://github.com/gongbugi/hanjan-deploy.git"
}

variable "cert_manager_version" {
  description = "cert-manager release the sync script installs in public_https mode (no leading v)."
  type        = string
  default     = "1.21.2"
}

variable "sops_version" {
  description = "getsops/sops release to install on the node (no leading v)."
  type        = string
  default     = "3.13.3"
}

variable "age_version" {
  description = "FiloSottile/age release to install on the node (no leading v)."
  type        = string
  default     = "1.3.2"
}

variable "budget_alert_email" {
  type        = string
  description = "Always Free를 넘는 실제 비용이 1이라도 생기면 알림을 받을 메일."
}
