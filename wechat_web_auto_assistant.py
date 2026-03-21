#!/usr/bin/env python3
"""微信 Web 版麻将全自动识别+牌理分析（本地运行）。"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from mahjong_helper import pretty_hand, shanten, suggest_discards, to_counts

TILE_NAMES = [
    *(f"{i}m" for i in range(1, 10)),
    *(f"{i}p" for i in range(1, 10)),
    *(f"{i}s" for i in range(1, 10)),
    *(f"{i}z" for i in range(1, 8)),
]


@dataclass
class Region:
    x: float
    y: float
    w: float
    h: float

    def to_pixels(self, width: int, height: int) -> Tuple[int, int, int, int]:
        x1 = int(self.x * width)
        y1 = int(self.y * height)
        x2 = int((self.x + self.w) * width)
        y2 = int((self.y + self.h) * height)
        return max(0, x1), max(0, y1), min(width, x2), min(height, y2)


def load_runtime_deps() -> Tuple[Any, Any]:
    """延迟加载重依赖：保证 `--help` 在缺少图像依赖时也可用。"""
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("需要安装 opencv-python 才能运行自动识别") from exc

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("需要安装 playwright 并执行 playwright install") from exc

    return cv2, sync_playwright


def load_templates(template_dir: Path, cv2: Any) -> Dict[str, Any]:
    templates: Dict[str, Any] = {}
    for t in TILE_NAMES:
        img_path = template_dir / f"{t}.png"
        if not img_path.exists():
            continue
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            templates[t] = img
    if not templates:
        raise ValueError(f"未在 {template_dir} 找到模板图（如 1m.png）")
    return templates


def detect_tiles_by_slots(
    gray: Any,
    region: Tuple[int, int, int, int],
    templates: Dict[str, Any],
    slots: int,
    threshold: float,
    cv2: Any,
) -> List[str]:
    x1, y1, x2, y2 = region
    crop = gray[y1:y2, x1:x2]
    if crop.size == 0 or slots <= 0:
        return []

    tile_w = crop.shape[1] / slots
    out: List[str] = []

    for i in range(slots):
        sx1 = int(i * tile_w)
        sx2 = int((i + 1) * tile_w)
        slot = crop[:, max(0, sx1) : min(crop.shape[1], sx2)]
        if slot.size == 0:
            continue

        best_name = None
        best_score = -1.0
        for name, tpl in templates.items():
            if slot.shape[0] < tpl.shape[0] or slot.shape[1] < tpl.shape[1]:
                resized_tpl = cv2.resize(tpl, (max(8, slot.shape[1] // 2), max(8, slot.shape[0] // 2)))
                if slot.shape[0] < resized_tpl.shape[0] or slot.shape[1] < resized_tpl.shape[1]:
                    continue
                use_tpl = resized_tpl
            else:
                use_tpl = tpl
            res = cv2.matchTemplate(slot, use_tpl, cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            if score > best_score:
                best_score = score
                best_name = name

        if best_name is not None and best_score >= threshold:
            out.append(best_name)

    return out


def parse_regions(config_path: Path) -> Tuple[Region, List[Region]]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    hand = Region(**data["hand_region"])
    rivers = [Region(**x) for x in data.get("river_regions", [])]
    return hand, rivers


def tile_name_to_index(name: str) -> int:
    suit = name[1]
    n = int(name[0])
    if suit == "m":
        return n - 1
    if suit == "p":
        return 9 + n - 1
    if suit == "s":
        return 18 + n - 1
    if suit == "z":
        return 27 + n - 1
    raise ValueError(name)


def run_loop(
    url: str,
    templates: Dict[str, Any],
    hand_region: Region,
    river_regions: List[Region],
    interval: float,
    threshold: float,
    headless: bool,
    cv2: Any,
    sync_playwright: Any,
) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto(url, wait_until="domcontentloaded")
        print("已打开页面，请先登录并进入牌局。")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            while True:
                page.screenshot(path=tmp.name, full_page=False)
                img = cv2.imread(tmp.name, cv2.IMREAD_COLOR)
                if img is None:
                    print("截图读取失败，跳过本轮。")
                    time.sleep(interval)
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape

                hand_px = hand_region.to_pixels(w, h)
                hand_tiles = detect_tiles_by_slots(gray, hand_px, templates, slots=14, threshold=threshold, cv2=cv2)

                river_text = []
                for idx, rr in enumerate(river_regions, start=1):
                    rr_px = rr.to_pixels(w, h)
                    tiles = detect_tiles_by_slots(gray, rr_px, templates, slots=24, threshold=threshold, cv2=cv2)
                    river_text.append(f"P{idx}:{','.join(tiles) if tiles else '-'}")

                print("\n=== 识别结果 ===")
                print("手牌:", " ".join(hand_tiles) if hand_tiles else "-")
                print("牌河:", " | ".join(river_text) if river_text else "-")

                if len(hand_tiles) in (13, 14):
                    try:
                        hand_idx = [tile_name_to_index(x) for x in hand_tiles]
                        cnt = to_counts(hand_idx)
                        print("向听:", shanten(cnt), "| 手牌整理:", pretty_hand(hand_idx))
                        if len(hand_idx) == 14:
                            rec = suggest_discards(hand_idx)[:5]
                            for r in rec:
                                print(f"建议弃 {r.discard} -> 向听 {r.shanten_after_discard}, 进张 {r.ukeire}")
                    except Exception as e:
                        print("牌理计算失败:", e)
                else:
                    print("当前未识别到 13/14 张完整手牌，跳过牌理计算。")

                time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="微信 Web 麻将全自动识别与建议")
    parser.add_argument("--url", required=True, help="微信网页地址")
    parser.add_argument("--templates", default="templates", help="模板目录")
    parser.add_argument("--config", default="wechat_regions.json", help="区域配置 json")
    parser.add_argument("--interval", type=float, default=1.5, help="轮询秒数")
    parser.add_argument("--threshold", type=float, default=0.7, help="模板匹配阈值")
    parser.add_argument("--headless", action="store_true", help="无头浏览器")
    args = parser.parse_args()

    cv2, sync_playwright = load_runtime_deps()
    templates = load_templates(Path(args.templates), cv2=cv2)
    hand_region, river_regions = parse_regions(Path(args.config))
    run_loop(
        url=args.url,
        templates=templates,
        hand_region=hand_region,
        river_regions=river_regions,
        interval=args.interval,
        threshold=args.threshold,
        headless=args.headless,
        cv2=cv2,
        sync_playwright=sync_playwright,
    )


if __name__ == "__main__":
    main()
