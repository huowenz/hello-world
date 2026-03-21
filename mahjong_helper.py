#!/usr/bin/env python3
"""本地麻将辅助算法（离线可运行）。

功能：
1. 解析手牌（支持万 m、筒 p、索 s、字 z）。
2. 判断是否和牌（标准 4 面子 + 1 雀头，支持七对子）。
3. 计算向听数（标准型 + 七对子，取最小）。
4. 给出 14 张手牌的弃牌建议：枚举每种可弃牌后，统计可进张数（ukeire）。

示例输入：
- "123m456p789s11z22z"（紧凑表示）
- "1m 2m 3m 4p 5p ..."（空格分隔）
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Sequence, Tuple

SUITS = "mpsz"
TILE_NAMES = [
    *(f"{i}m" for i in range(1, 10)),
    *(f"{i}p" for i in range(1, 10)),
    *(f"{i}s" for i in range(1, 10)),
    *(f"{i}z" for i in range(1, 8)),
]


def tile_to_index(tile: str) -> int:
    n, suit = int(tile[0]), tile[1]
    if suit not in SUITS:
        raise ValueError(f"不支持的花色: {tile}")
    if suit == "z":
        if not (1 <= n <= 7):
            raise ValueError(f"字牌范围应为 1-7z: {tile}")
        return 27 + (n - 1)
    if not (1 <= n <= 9):
        raise ValueError(f"数牌范围应为 1-9: {tile}")
    base = {"m": 0, "p": 9, "s": 18}[suit]
    return base + (n - 1)


def index_to_tile(i: int) -> str:
    return TILE_NAMES[i]


def parse_tiles(text: str) -> List[int]:
    """解析两种格式：紧凑串 or 空格分隔。"""
    text = text.strip().lower()
    if not text:
        return []

    if " " in text:
        tiles = text.split()
        return [tile_to_index(t) for t in tiles]

    out: List[int] = []
    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif ch in SUITS:
            if not digits:
                raise ValueError(f"花色 {ch} 前没有数字")
            for d in digits:
                out.append(tile_to_index(f"{d}{ch}"))
            digits = ""
        else:
            raise ValueError(f"无法解析字符: {ch}")
    if digits:
        raise ValueError("尾部数字缺少花色")
    return out


def to_counts(tiles: Sequence[int]) -> Tuple[int, ...]:
    c = [0] * 34
    for t in tiles:
        c[t] += 1
        if c[t] > 4:
            raise ValueError(f"同一张牌超过 4 枚: {index_to_tile(t)}")
    return tuple(c)


def can_form_all_melds(counts: Tuple[int, ...]) -> bool:
    """只检查是否可完全拆为面子（3n 张）。"""
    c = list(counts)

    # 字牌只能刻子
    for i in range(27, 34):
        if c[i] % 3 != 0:
            return False

    # 数牌花色分别处理
    for base in (0, 9, 18):
        arr = c[base : base + 9]
        for i in range(9):
            while arr[i] > 0:
                if arr[i] >= 3:
                    arr[i] -= 3
                    continue
                if i + 2 >= 9 or arr[i + 1] <= 0 or arr[i + 2] <= 0:
                    return False
                arr[i] -= 1
                arr[i + 1] -= 1
                arr[i + 2] -= 1
    return True


def is_standard_win(counts: Tuple[int, ...]) -> bool:
    if sum(counts) % 3 != 2:
        return False
    for i in range(34):
        if counts[i] >= 2:
            c = list(counts)
            c[i] -= 2
            if can_form_all_melds(tuple(c)):
                return True
    return False


def is_chiitoitsu_win(counts: Tuple[int, ...]) -> bool:
    if sum(counts) != 14:
        return False
    pairs = sum(1 for x in counts if x == 2)
    return pairs == 7


def is_win(counts: Tuple[int, ...]) -> bool:
    return is_standard_win(counts) or is_chiitoitsu_win(counts)


@lru_cache(maxsize=None)
def _mentsu_taatsu_for_suit(arr: Tuple[int, ...]) -> Tuple[int, int]:
    """对 9 张数牌返回可取到的最大 (面子数, 搭子数)。"""
    best = (0, 0)

    def better(a: Tuple[int, int], b: Tuple[int, int]) -> Tuple[int, int]:
        return a if (a[0], a[1]) >= (b[0], b[1]) else b

    def dfs(state: List[int], m: int, t: int) -> None:
        nonlocal best
        i = next((k for k, v in enumerate(state) if v), -1)
        if i == -1:
            best = better(best, (m, t))
            return

        # 跳过该牌（孤张）
        state[i] -= 1
        dfs(state, m, t)
        state[i] += 1

        # 刻子
        if state[i] >= 3:
            state[i] -= 3
            dfs(state, m + 1, t)
            state[i] += 3

        # 顺子
        if i <= 6 and state[i + 1] > 0 and state[i + 2] > 0:
            state[i] -= 1
            state[i + 1] -= 1
            state[i + 2] -= 1
            dfs(state, m + 1, t)
            state[i] += 1
            state[i + 1] += 1
            state[i + 2] += 1

        # 搭子
        if state[i] >= 2:
            state[i] -= 2
            dfs(state, m, t + 1)
            state[i] += 2
        if i <= 7 and state[i + 1] > 0:
            state[i] -= 1
            state[i + 1] -= 1
            dfs(state, m, t + 1)
            state[i] += 1
            state[i + 1] += 1
        if i <= 6 and state[i + 2] > 0:
            state[i] -= 1
            state[i + 2] -= 1
            dfs(state, m, t + 1)
            state[i] += 1
            state[i + 2] += 1

    dfs(list(arr), 0, 0)
    return best


def shanten_standard(counts: Tuple[int, ...]) -> int:
    """标准型向听数。"""
    total = sum(counts)
    if total % 3 not in (1, 2):
        raise ValueError("手牌张数必须为 3n+1 或 3n+2")

    best = 8
    for head in range(-1, 34):
        c = list(counts)
        has_head = 0
        if head != -1:
            if c[head] < 2:
                continue
            c[head] -= 2
            has_head = 1

        m = 0
        t = 0

        # 字牌：刻子/对子
        for i in range(27, 34):
            m += c[i] // 3
            if c[i] % 3 == 2:
                t += 1

        # 三门数牌
        for base in (0, 9, 18):
            mm, tt = _mentsu_taatsu_for_suit(tuple(c[base : base + 9]))
            m += mm
            t += tt

        if m > 4:
            m = 4
        if t > 4 - m:
            t = 4 - m

        cur = 8 - 2 * m - t - has_head
        best = min(best, cur)
    return best


def shanten_chiitoitsu(counts: Tuple[int, ...]) -> int:
    pairs = sum(1 for x in counts if x >= 2)
    unique = sum(1 for x in counts if x > 0)
    need_pairs = 7 - pairs
    need_unique = max(0, 7 - unique)
    return need_pairs + need_unique


def shanten(counts: Tuple[int, ...]) -> int:
    if is_win(counts):
        return -1
    return min(shanten_standard(counts), shanten_chiitoitsu(counts))


@dataclass
class DiscardAdvice:
    discard: str
    shanten_after_discard: int
    ukeire: int
    improving_tiles: Dict[str, int]


def suggest_discards(tiles: Sequence[int]) -> List[DiscardAdvice]:
    if len(tiles) != 14:
        raise ValueError("弃牌建议需要 14 张手牌")

    original = Counter(tiles)
    results: List[DiscardAdvice] = []

    for discard_idx in sorted(original.keys()):
        hand_after = list(tiles)
        hand_after.remove(discard_idx)
        counts_after = to_counts(hand_after)
        base_shanten = shanten(counts_after)

        improve: Dict[str, int] = {}
        total_ukeire = 0

        for draw in range(34):
            if counts_after[draw] >= 4:
                continue
            c = list(counts_after)
            c[draw] += 1
            new_s = shanten(tuple(c))
            if new_s < base_shanten:
                remain = 4 - counts_after[draw]
                improve[index_to_tile(draw)] = remain
                total_ukeire += remain

        results.append(
            DiscardAdvice(
                discard=index_to_tile(discard_idx),
                shanten_after_discard=base_shanten,
                ukeire=total_ukeire,
                improving_tiles=dict(sorted(improve.items())),
            )
        )

    results.sort(key=lambda x: (x.shanten_after_discard, -x.ukeire, x.discard))
    return results


def pretty_hand(tiles: Iterable[int]) -> str:
    groups = {"m": [], "p": [], "s": [], "z": []}
    for t in sorted(tiles):
        name = index_to_tile(t)
        groups[name[1]].append(name[0])
    return " ".join(f"{''.join(v)}{k}" for k, v in groups.items() if v)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="本地麻将辅助算法")
    parser.add_argument("hand", help="手牌字符串，如 123m456p789s11z22z")
    args = parser.parse_args()

    tiles = parse_tiles(args.hand)
    counts = to_counts(tiles)

    print("手牌:", pretty_hand(tiles), f"({len(tiles)} 张)")
    print("和牌:", "是" if is_win(counts) else "否")
    print("向听:", shanten(counts))

    if len(tiles) == 14:
        print("\n弃牌建议（按向听优先、再按进张数排序）:")
        for r in suggest_discards(tiles)[:10]:
            print(
                f"- 弃 {r.discard}: 向听 {r.shanten_after_discard}, "
                f"进张 {r.ukeire}, 有效牌 {','.join(r.improving_tiles.keys()) or '无'}"
            )


if __name__ == "__main__":
    main()
