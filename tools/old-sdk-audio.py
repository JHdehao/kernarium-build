#!/usr/bin/env python3
"""把音频设备代码里的 iOS 27 SDK 判断压成不可满足，让它走源码自带的
旧 SDK 路径（Xcode 26 的 SDK 没有 AVAudioEngine 的新 selector）。"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1]) / "darwin" / "device" / "audio"
files = sorted(root.glob("*.mm"))
print(f"扫描 {root}: {[f.name for f in files]}")
if not files:
    print("没有找到音频源文件", file=sys.stderr)
    raise SystemExit(2)

total = 0
for path in files:
    text = path.read_text()
    updated = text.replace(">= 270000", ">= 999999")
    changed = text.count(">= 270000")
    if changed:
        path.write_text(updated)
        print(f"{path.name}: 替换 {changed} 处")
        total += changed
print(f"合计替换 {total} 处")
raise SystemExit(0 if total else 1)
