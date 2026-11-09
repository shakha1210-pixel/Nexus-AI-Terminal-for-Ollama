FROM python:3.11-alpine

# Minimal runtime: no application dependencies or shell entrypoint.
RUN addgroup -S -g 65532 sandbox && adduser -S -D -H -u 65532 -G sandbox sandbox
USER 65532:65532
WORKDIR /input
ENTRYPOINT ["python"]
