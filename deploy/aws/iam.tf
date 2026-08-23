data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "registrar" {
  name               = "${var.name_prefix}-registrar"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "registrar" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.registrar.arn}:*"]
  }

  statement {
    sid       = "IntakeBucket"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.intake.arn}/*"]
  }

  dynamic "statement" {
    for_each = var.enable_glue ? [1] : []

    content {
      sid = "Glue"
      actions = [
        "glue:CreateDatabase",
        "glue:GetDatabase",
        "glue:CreateTable",
        "glue:GetTable",
        "glue:UpdateTable",
      ]
      # Glue requires catalog + database + table ARNs for these calls.
      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = var.om_token_secret_arn != "" ? [1] : []

    content {
      sid       = "OmToken"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [var.om_token_secret_arn]
    }
  }
}

resource "aws_iam_role_policy" "registrar" {
  name   = "${var.name_prefix}-registrar"
  role   = aws_iam_role.registrar.id
  policy = data.aws_iam_policy_document.registrar.json
}

# VPC-attached Lambdas need ENI management.
resource "aws_iam_role_policy_attachment" "vpc_access" {
  count      = length(var.vpc_subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.registrar.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
