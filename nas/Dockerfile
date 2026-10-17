# PocketBase chính thức cho NAS Synology DS224+ (Intel, linux/amd64)
FROM alpine:3.20

ARG PB_VERSION=0.40.5

RUN apk add --no-cache ca-certificates tzdata unzip wget \
 && cd /tmp \
 && wget -q "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip" \
 && wget -q "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/checksums.txt" \
 && grep " pocketbase_${PB_VERSION}_linux_amd64.zip$" checksums.txt | sha256sum -c - \
 && mkdir -p /pb \
 && unzip -q "pocketbase_${PB_VERSION}_linux_amd64.zip" pocketbase -d /pb \
 && rm -f /tmp/*.zip /tmp/checksums.txt

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8090/api/health >/dev/null || exit 1

# automigrate=false: cấu trúc bảng chỉ thay đổi qua file trong pb_migrations (quản lý trên GitHub),
# không tự sinh khi bấm sửa trong trang quản trị.
CMD ["/pb/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data", \
     "--migrationsDir=/pb/pb_migrations", "--hooksDir=/pb/pb_hooks", "--automigrate=false"]
