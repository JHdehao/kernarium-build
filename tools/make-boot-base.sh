#!/bin/sh
# 生成一个最小的 aarch64 引导基础 initramfs（静态 BusyBox + stub /init）。
# 官方的 starter 产物只在 arm64 Linux 上用 Buildroot 生成；这里先做一个功能
# 等价的替代，让 runtime 构建链路跑通，之后再替换为官方 starter release。
set -eu

OUT=${1:?用法: make-boot-base.sh OUT.cpio.gz}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cd "$WORK"
curl -sSL -o bb.apk \
  https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/busybox-static-1.36.1-r31.apk
gzip -dc bb.apk > bb.tar
tar xf bb.tar bin/busybox.static 2>/dev/null || tar xf bb.tar
BUSYBOX=$(find . -name busybox.static -type f | head -1)
[ -n "$BUSYBOX" ] || { echo "busybox.static 未找到" >&2; exit 1; }

mkdir -p root/bin root/dev root/proc root/sys root/tmp root/newroot root/payload
cp "$BUSYBOX" root/bin/busybox
chmod 755 root/bin/busybox
for c in sh mount umount switch_root mkdir cat echo sleep mdev ln ls cp mv rm \
         grep sed awk chmod chown mknod find; do
  ln -sf busybox "root/bin/$c"
done
printf '#!/bin/busybox sh\necho "UML_BOOT_BASE_ERROR:stub initramfs" >&2\nexec /bin/sh\n' \
  > root/init
chmod 755 root/init

( cd root && find . | cpio -o -H newc 2>/dev/null ) | gzip -9 > "$OUT"
echo "wrote $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
