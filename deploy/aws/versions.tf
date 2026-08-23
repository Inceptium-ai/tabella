terraform {
  required_version = ">= 1.5" # OpenTofu >= 1.6 works identically

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}
