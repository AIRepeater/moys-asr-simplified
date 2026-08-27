from __future__ import annotations


def split_items_by_speaker(items: list[dict]) -> list[list[dict]]:
    """按 speaker 变化硬切分，避免两个说话人进入同一字幕段。

    缺少 speaker 的 item 跟随前一个已知 speaker，不主动制造切分。
    """
    runs: list[list[dict]] = []
    current: list[dict] = []
    current_speaker: str | None = None
    for item in items:
        speaker = item.get("speaker")
        if (
            current
            and speaker is not None
            and current_speaker is not None
            and speaker != current_speaker
        ):
            runs.append(current)
            current = []
            current_speaker = None
        current.append(item)
        if speaker is not None:
            current_speaker = speaker
    if current:
        runs.append(current)
    return runs
