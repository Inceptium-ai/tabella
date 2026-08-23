# Registrar Lambda image. Build from the REPO ROOT so the workspace packages
# are in the build context:
#
#   docker build -f deploy/aws/lambda.Dockerfile -t tabella-registrar .
#
FROM public.ecr.aws/lambda/python:3.12

COPY packages /opt/tabella/packages

RUN pip install --no-cache-dir \
    /opt/tabella/packages/tabella-core \
    /opt/tabella/packages/tabella-connectors \
    /opt/tabella/packages/tabella-catalog-om \
    /opt/tabella/packages/tabella-governance-aws \
    /opt/tabella/packages/tabella-enable \
    /opt/tabella/packages/tabella-cli

CMD ["tabella_cli.lambda_handler.handler"]
