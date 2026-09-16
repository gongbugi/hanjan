locals {
  name = "hanjan"
  # OCI 링크 로컬 주소 — VCN DNS 리졸버와 NTP
  oci_link_local = "169.254.169.254/32"
}

data "oci_identity_availability_domains" "this" {
  compartment_id = var.tenancy_ocid
}

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# --- 네트워크 ---
resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "${local.name}-vcn"
  dns_label      = local.name
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.name}-igw"
  enabled        = true
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.name}-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.name}-public-sl"

  # --- 들어오는 트래픽: SSH는 내 IP만. 웹은 public_https 모드에서만 연다 ---
  ingress_security_rules {
    description = "SSH from admin only"
    protocol    = "6"
    source      = var.admin_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }

  dynamic "ingress_security_rules" {
    for_each = var.ingress_mode == "public_https" ? [80, 443] : []
    content {
      description = "Web (public_https mode)"
      protocol    = "6"
      source      = "0.0.0.0/0"
      tcp_options {
        min = ingress_security_rules.value
        max = ingress_security_rules.value
      }
    }
  }

  # --- 나가는 트래픽: 전체 허용 대신 필요한 포트만 (myWeb은 아웃바운드 전체 허용이었다) ---
  egress_security_rules {
    description = "HTTPS: Gemini/Groq API, GHCR, roaster sites, ACME"
    protocol    = "6"
    destination = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # DB를 VM 밖(Supabase)에 두면서 생긴 길. 직접 연결은 IPv6 전용이라 Shared Pooler(5432)를 쓴다
  egress_security_rules {
    description = "Postgres: Supabase shared pooler (session mode)"
    protocol    = "6"
    destination = "0.0.0.0/0"
    tcp_options {
      min = 5432
      max = 5432
    }
  }

  egress_security_rules {
    description = "HTTP: apt mirrors, robots.txt"
    protocol    = "6"
    destination = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  dynamic "egress_security_rules" {
    for_each = [53, 123]
    content {
      description = "DNS/NTP to OCI link-local"
      protocol    = "17"
      destination = local.oci_link_local
      udp_options {
        min = egress_security_rules.value
        max = egress_security_rules.value
      }
    }
  }

  dynamic "egress_security_rules" {
    for_each = var.ingress_mode == "tunnel" ? ["6", "17"] : []
    content {
      description = "Cloudflare Tunnel (7844 TCP/UDP)"
      protocol    = egress_security_rules.value
      destination = "0.0.0.0/0"

      dynamic "tcp_options" {
        for_each = egress_security_rules.value == "6" ? [1] : []
        content {
          min = 7844
          max = 7844
        }
      }

      dynamic "udp_options" {
        for_each = egress_security_rules.value == "17" ? [1] : []
        content {
          min = 7844
          max = 7844
        }
      }
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.this.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "${local.name}-public"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_security_list.public.id]
}

# --- 컴퓨트: 단일 노드 k3s ---
resource "oci_core_instance" "k3s" {
  availability_domain = data.oci_identity_availability_domains.this.availability_domains[var.availability_domain_index].name
  compartment_id      = var.compartment_ocid
  display_name        = "${local.name}-k3s"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_gb
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
      ingress_mode         = var.ingress_mode
      cert_manager_version = var.cert_manager_version
      deploy_repo_url      = var.deploy_repo_url
      sops_version         = var.sops_version
      age_version          = var.age_version
    }))
  }

  lifecycle {
    # 새 우분투 이미지가 나오거나 cloud-init을 고칠 때마다 VM(과 로컬 볼륨의 DB)을 다시 만들지 않게
    ignore_changes = [source_details[0].source_id, metadata["user_data"]]
  }
}

# --- 백업: Supabase 덤프를 여기에 올린다 (hanjan-deploy의 backup CronJob).
# 무료 플랜에는 자동 백업이 없어서 이 버킷이 유일한 백업이다 ---
resource "oci_objectstorage_bucket" "backups" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.this.namespace
  name           = "${local.name}-backups"
  access_type    = "NoPublicAccess"
}

# --- 0원 조건 감시: 실제 비용이 조금이라도 생기면 메일 ---
resource "oci_budget_budget" "zero_cost_guard" {
  compartment_id = var.tenancy_ocid
  amount         = 1
  reset_period   = "MONTHLY"
  target_type    = "COMPARTMENT"
  targets        = [var.compartment_ocid]
  display_name   = "${local.name}_zero_cost_guard"
  description    = "Always Free limits should keep this at zero."
}

resource "oci_budget_alert_rule" "any_actual_spend" {
  budget_id      = oci_budget_budget.zero_cost_guard.id
  threshold      = 1
  threshold_type = "PERCENTAGE"
  type           = "ACTUAL"
  recipients     = var.budget_alert_email
  display_name   = "any_actual_spend"
  message        = "hanjan: Always Free를 넘는 실제 비용이 발생했습니다. 콘솔의 Cost Analysis를 확인하세요."
}
