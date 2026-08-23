# The registrar: container-image Lambda running tabella_cli.lambda_handler.

resource "aws_cloudwatch_log_group" "registrar" {
  name              = "/aws/lambda/${var.name_prefix}-registrar"
  retention_in_days = 30
}

resource "aws_lambda_function" "registrar" {
  function_name = "${var.name_prefix}-registrar"
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  role          = aws_iam_role.registrar.arn
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_mb

  environment {
    variables = {
      TABELLA_CATALOG_BUCKET      = aws_s3_bucket.intake.bucket
      TABELLA_CATALOG_PREFIX      = "catalog/"
      TABELLA_ENABLE_GLUE         = var.enable_glue ? "true" : "false"
      TABELLA_ENABLE_OM           = var.enable_openmetadata ? "true" : "false"
      TABELLA_OM_HOST             = var.om_host
      TABELLA_OM_MODE             = var.om_mode
      TABELLA_OM_TOKEN_SECRET_ARN = var.om_token_secret_arn
    }
  }

  dynamic "vpc_config" {
    for_each = length(var.vpc_subnet_ids) > 0 ? [1] : []

    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  depends_on = [aws_cloudwatch_log_group.registrar]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.registrar.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.intake.arn
}
