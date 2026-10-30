"""[patch] 世界书：从插件数据目录的 worldbook.md 读取设定，给日程、场景、梦、日记补背景。

文件格式见 worldbook.md 顶部说明。文件不存在时所有函数返回空串，原流程不受影响。
"""
from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

FILE_NAME = "worldbook.md"
SCHEDULE_LIMIT = 3500
MATCHED_LIMIT = 1600
INTEREST_PICKS = 3

_HEADER = re.compile(r"^##\s+(.+?)\s*$")
_ENTRY = re.compile(r"^(常驻|条目)\s*[·・.]\s*(.+?)(?:\s*[｜|]\s*关键词[:：]\s*(.+))?$")
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _parse(text: str) -> dict[str, Any]:
    book: dict[str, Any] = {"always": [], "entries": [], "interests": [], "threads": [], "taboos": []}
    lists = {"兴趣池": "interests", "长期线": "threads", "禁区": "taboos"}
    current: dict[str, Any] | None = None
    target: str = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith(">") or line.startswith("# "):
            continue
        header = _HEADER.match(line)
        if header:
            title = header.group(1); current = None; target = lists.get(title, "")
            entry = _ENTRY.match(title)
            if entry:
                keywords = [k.strip() for k in re.split(r"[、,，\s]+", entry.group(3) or "") if k.strip()]
                current = {"title": entry.group(2).strip(), "keywords": keywords, "body": []}
                book["always" if entry.group(1) == "常驻" else "entries"].append(current)
            continue
        if target and line.lstrip().startswith("- "):
            book[target].append(line.lstrip()[2:].strip())
        elif current is not None and line.strip():
            current["body"].append(line.strip())
    for key in ("always", "entries"):
        book[key] = [dict(item, body="\n".join(item["body"])) for item in book[key] if item["body"]]
    return book


def load(data_dir: Any) -> dict[str, Any]:
    """按文件修改时间缓存；读不到返回空字典。"""
    path = Path(str(data_dir)) / FILE_NAME
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    cached = _cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        book = _parse(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    _cache[str(path)] = (mtime, book)
    return book


def _section(title: str, body: str) -> str:
    return f"【{title}】{body}"


def _taboos(book: dict[str, Any]) -> str:
    items = book.get("taboos") or []
    return ("世界书禁区：" + "；".join(items)) if items else ""


def schedule_block(data_dir: Any) -> str:
    """日程生成用：常驻 + 全部条目 + 随机兴趣 + 长期线 + 禁区。"""
    book = load(data_dir)
    if not book:
        return ""
    parts = [_section(item["title"], item["body"]) for item in book["always"] + book["entries"]]
    interests = book.get("interests") or []
    if interests:
        picked = random.sample(interests, min(INTEREST_PICKS, len(interests)))
        parts.append("今天可以优先考虑的兴趣（挑一两项安排进休闲段，不必全用）：" + "、".join(picked))
    if book.get("threads"):
        parts.append("长期在做的事（可以安排其中一件今天推进一点，写清推进到哪一步）：" + "；".join(book["threads"]))
    taboos = _taboos(book)
    if taboos:
        parts.append(taboos)
    return "\n".join(parts)[:SCHEDULE_LIMIT]


def matched_block(data_dir: Any, text: str, *, with_always: bool = False) -> str:
    """场景/梦/日记用：关键词命中的条目和禁区（with_always 时先带常驻设定），控制长度。"""
    book = load(data_dir)
    if not book:
        return ""
    source = str(text or "")
    hits = [item for item in book["entries"] if any(k in source for k in item["keywords"])]
    parts = [_section(item["title"], item["body"]) for item in (book["always"] if with_always else []) + hits]
    taboos = _taboos(book)
    if taboos:
        parts.append(taboos)
    return "\n".join(parts)[:MATCHED_LIMIT]


def has_book(data_dir: Any) -> bool:
    return bool(load(data_dir))
