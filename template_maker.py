#!/usr/bin/env python3
"""从截图快速制作麻将模板图（Windows/Linux/macOS）。

用法：
  python template_maker.py --image board.png --out templates

操作：
- 打开截图后，鼠标框选一张牌面（尽量只包含牌本体白色区域）。
- 输入牌名（如 1m / 9p / 5s / 1z）。
- 回车保存，继续下一张。
- 输入 q 结束。
"""

from __future__ import annotations

import argparse
from pathlib import Path

VALID = {
    *(f"{i}m" for i in range(1, 10)),
    *(f"{i}p" for i in range(1, 10)),
    *(f"{i}s" for i in range(1, 10)),
    *(f"{i}z" for i in range(1, 8)),
}


def load_cv2():
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("需要安装 opencv-python 才能运行模板制作工具") from exc
    return cv2


def main() -> None:
    parser = argparse.ArgumentParser(description="交互式模板制作工具")
    parser.add_argument("--image", required=True, help="整桌截图路径")
    parser.add_argument("--out", default="templates", help="输出目录")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖同名模板")
    args = parser.parse_args()

    cv2 = load_cv2()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(args.image)
    if img is None:
        raise FileNotFoundError(f"无法读取截图: {args.image}")

    print("\n已加载截图。按提示框选模板并输入牌名，输入 q 退出。")
    print("合法牌名示例：1m, 9p, 5s, 1z...7z")

    while True:
        roi = cv2.selectROI("template_maker", img, fromCenter=False, showCrosshair=True)
        x, y, w, h = map(int, roi)
        if w <= 0 or h <= 0:
            print("未选择区域，输入 q 退出，或直接回车继续。")
        tile = input("牌名（如 1m/9p/5s/1z，q=退出）：").strip().lower()
        if tile == "q":
            break
        if tile not in VALID:
            print("牌名不合法，跳过本次。")
            continue
        path = out / f"{tile}.png"
        if path.exists() and not args.overwrite:
            print(f"已存在 {path.name}，如需覆盖请加 --overwrite")
            continue
        if w <= 0 or h <= 0:
            print("没有有效框选，跳过。")
            continue
        crop = img[y : y + h, x : x + w]
        cv2.imwrite(str(path), crop)
        print(f"已保存：{path}")

    cv2.destroyAllWindows()
    print("模板制作结束。")


if __name__ == "__main__":
    main()
