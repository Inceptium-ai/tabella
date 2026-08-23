variable "region" {
  description = "AWS region for the reference stack"
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "tabella"
}

variable "lambda_image_uri" {
  description = "ECR image URI of the registrar Lambda (built from lambda.Dockerfile)"
  type        = string
}

variable "enable_glue" {
  description = "Apply the Glue governance backend on registration"
  type        = bool
  default     = true
}

variable "enable_openmetadata" {
  description = "Mirror registrations into OpenMetadata"
  type        = bool
  default     = false
}

variable "om_host" {
  description = "OpenMetadata base URL reachable from the Lambda (e.g. http://om.internal:8585)"
  type        = string
  default     = ""
}

variable "om_mode" {
  description = "OpenMetadata provisioning mode: direct | ingest"
  type        = string
  default     = "direct"

  validation {
    condition     = contains(["direct", "ingest"], var.om_mode)
    error_message = "om_mode must be direct or ingest."
  }
}

variable "om_token_secret_arn" {
  description = "Secrets Manager secret ARN holding the OpenMetadata bot JWT (required when enable_openmetadata)"
  type        = string
  default     = ""
}

variable "lambda_timeout" {
  description = "Registrar timeout in seconds (ingest mode polls OM, so allow headroom)"
  type        = number
  default     = 300
}

variable "lambda_memory_mb" {
  description = "Registrar memory (pyarrow-backed connectors like RAM)"
  type        = number
  default     = 1024
}

variable "vpc_subnet_ids" {
  description = "Subnets for the Lambda when OM/Postgres are only reachable in-VPC (empty = no VPC config)"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "Security groups for the Lambda when using vpc_subnet_ids"
  type        = list(string)
  default     = []
}
