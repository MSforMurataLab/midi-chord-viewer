# -*- coding: utf-8 -*-
"""分析レポートの HTML 書き出し。"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from midi_lab import __version__
from midi_lab.core.performance_analytics import PerformanceReport, report_summary_text
from midi_lab.core.voice_leading import VoiceLeadingStep, format_motions


def build_analysis_html(
    title: str,
    key_text: str,
    performance: PerformanceReport,
    voice_steps: list[VoiceLeadingStep],
    chord_labels: list[str],
    roman_labels: list[str],
) -> str:
    rows_vl = ""
    for s in voice_steps[:200]:
        rows_vl += (
            f"<tr><td>{s.index}</td><td>{html.escape(s.from_label)}</td>"
            f"<td>{html.escape(s.to_label)}</td><td>{html.escape(format_motions(s.motions))}</td>"
            f"<td>{html.escape(s.motion_kind)}</td><td>{s.total_motion}</td></tr>\n"
        )
    rows_ch = ""
    for i, (lab, rom) in enumerate(zip(chord_labels, roman_labels)):
        rows_ch += (
            f"<tr><td>{i + 1}</td><td>{html.escape(lab)}</td>"
            f"<td>{html.escape(rom)}</td></tr>\n"
        )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<title>{html.escape(title)} — 分析レポート</title>
<style>
body {{ font-family: "Segoe UI", "Yu Gothic UI", sans-serif; background: #141416; color: #ececef; margin: 2rem; }}
h1, h2 {{ color: #5b9cf5; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #3a3a42; padding: 8px 12px; text-align: left; }}
th {{ background: #222226; }}
tr:nth-child(even) {{ background: #1a1a1d; }}
.meta {{ color: #7a7a85; font-size: 0.9rem; }}
.summary {{ background: #222226; padding: 1rem 1.25rem; border-radius: 8px; border: 1px solid #3a3a42; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">MIDI Chord Lab v{__version__} · {ts} · キー: {html.escape(key_text)}</p>
<h2>パフォーマンス概要</h2>
<p class="summary">{html.escape(report_summary_text(performance))}</p>
<h2>和声タイムライン（機能記号）</h2>
<table>
<thead><tr><th>#</th><th>コード</th><th>機能</th></tr></thead>
<tbody>{rows_ch}</tbody>
</table>
<h2>声部進行</h2>
<table>
<thead><tr><th>#</th><th>前</th><th>後</th><th>移動</th><th>種別</th><th>総移動</th></tr></thead>
<tbody>{rows_vl}</tbody>
</table>
</body>
</html>"""
