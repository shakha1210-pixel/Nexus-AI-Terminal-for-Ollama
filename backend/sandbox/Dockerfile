FROM python:3.11-alpine

# Minimal runtime: no package installation, no shell entrypoint, no application code.
RUN addgroup -S -g 65532 sandbox && adduser -S -D -H -u 65532 -G sandbox sandbox
USER 65532:65532
WORKDIR /input
ENTRYPOINT ["python"]
