output "intake_bucket" {
  description = "Drop onboarding manifests at s3://<bucket>/manifests/; descriptors appear under catalog/"
  value       = aws_s3_bucket.intake.bucket
}

output "registrar_function" {
  description = "The registrar Lambda"
  value       = aws_lambda_function.registrar.function_name
}
