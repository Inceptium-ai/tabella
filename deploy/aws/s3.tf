# Intake + catalog bucket: manifests land under manifests/, generated Asset
# Descriptors are written back under catalog/.

resource "aws_s3_bucket" "intake" {
  bucket_prefix = "${var.name_prefix}-intake-"
}

resource "aws_s3_bucket_public_access_block" "intake" {
  bucket                  = aws_s3_bucket.intake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "intake" {
  bucket = aws_s3_bucket.intake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_notification" "manifests" {
  bucket = aws_s3_bucket.intake.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.registrar.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "manifests/"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
