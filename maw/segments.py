"""Segment timing repair helpers shared by the online ASR -> SRT pipeline."""

from __future__ import annotations

from typing import TypeAlias

JsonScalar = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

MIN_SEGMENT_DURATION_MS = 100


def repair_segment_durations(
    segments: list[JsonValue],
    min_ms: int = MIN_SEGMENT_DURATION_MS,
) -> int:
    """Widen zero/negative segment and item ranges to at least ``min_ms`` in place.

    ASR providers occasionally emit a word whose ``end`` equals its ``start``;
    once isolated by sentence splitting it becomes a zero-length subtitle that
    is invisible on playback. Only invalid (non-positive or inverted) ranges
    are widened, and the sweep keeps every range monotonic and non-overlapping;
    genuine short timings are left untouched. Returns the number of repaired
    boundaries.
    """
    floor = max(1, int(min_ms))
    fixed = 0
    previous_segment_end = 0
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = segment.get("start")
        end = segment.get("end")
        start = start if type(start) is int else 0
        end = end if type(end) is int else start
        if start < previous_segment_end:
            start = previous_segment_end
            fixed += 1
        items = segment.get("items")
        previous_item_end = start
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_start = item.get("start")
                item_end = item.get("end")
                item_start = item_start if type(item_start) is int else previous_item_end
                item_end = item_end if type(item_end) is int else item_start
                if item_start < previous_item_end:
                    item_start = previous_item_end
                    fixed += 1
                if item_end <= item_start:
                    item_end = item_start + floor
                    fixed += 1
                item["start"] = item_start
                item["end"] = item_end
                previous_item_end = item_end
            last_item = items[-1] if items else None
            if isinstance(last_item, dict):
                last_end = last_item.get("end")
                if type(last_end) is int and end < last_end:
                    end = last_end
                    fixed += 1
        if end <= start:
            end = start + floor
            fixed += 1
        segment["start"] = start
        segment["end"] = end
        previous_segment_end = end
    return fixed
