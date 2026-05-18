# -*- coding: utf-8 -*-
"""
ルールベースのコード置換候補（メジャーキー中心）。

内部表現: ピッチクラス 0–11、キー（root + mode）、コード（root + type）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from music21 import pitch as m21_pitch

# メジャースケール上のダイアトニック度数（キー根音からの半音）
DIATONIC_MAJOR_DEGREES = frozenset({0, 2, 4, 5, 7, 9, 11})

PITCH_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


@dataclass(frozen=True)
class KeySpec:
    root_pc: int  # 0–11
    mode: str  # "major" | "minor"


@dataclass(frozen=True)
class ChordSpec:
    root_pc: int
    chord_type: str  # maj, maj7, m, m7, 7, m7b5, dim7, note, ...


@dataclass(frozen=True)
class RuleOutput:
    degree_pc: int
    chord_type: str
    rule_name: str


@dataclass(frozen=True)
class MatchRule:
    """キー根音からの半音差 + タイプファミリ → 候補度数群。"""
    degree_pc: int
    type_families: tuple[str, ...]
    outputs: tuple[RuleOutput, ...]


# メジャーキー置換マトリクス（仕様 3章）
MAJOR_REPLACEMENT_RULES: tuple[MatchRule, ...] = (
    MatchRule(
        0,
        ("maj", "maj7"),
        (
            RuleOutput(9, "m", "機能置換（トニック）→ vi"),
            RuleOutput(9, "m7", "機能置換（トニック）→ vi7"),
            RuleOutput(4, "m", "機能置換（トニック）→ iii"),
            RuleOutput(4, "m7", "機能置換（トニック）→ iii7"),
        ),
    ),
    MatchRule(
        5,
        ("maj", "maj7"),
        (
            RuleOutput(2, "m", "機能置換（サブドミ）→ ii"),
            RuleOutput(2, "m7", "機能置換（サブドミ）→ ii7"),
            RuleOutput(5, "maj", "機能置換（サブドミ）→ IV"),
            RuleOutput(5, "maj7", "機能置換（サブドミ）→ IVmaj7"),
        ),
    ),
    MatchRule(
        2,
        ("m", "m7"),
        (
            RuleOutput(5, "maj", "機能置換（サブドミ）→ IV"),
            RuleOutput(5, "maj7", "機能置換（サブドミ）→ IVmaj7"),
            RuleOutput(2, "m7", "機能置換（サブドミ）→ ii7"),
        ),
    ),
    MatchRule(
        7,
        ("7",),
        (
            RuleOutput(7, "7", "ドミナント → V7"),
            RuleOutput(1, "7", "裏コード → ♭II7"),
            RuleOutput(5, "maj7", "機能置換（ドミナント）→ IVmaj7"),
            RuleOutput(5, "maj", "機能置換（ドミナント）→ IV"),
        ),
    ),
    MatchRule(
        11,
        ("m7b5",),
        (
            RuleOutput(11, "m7b5", "viiø7"),
            RuleOutput(5, "maj7", "モーダル・インターチェンジ → IVmaj7"),
            RuleOutput(5, "maj", "モーダル・インターチェンジ → IV"),
        ),
    ),
    MatchRule(
        5,
        ("m", "m7"),
        (
            RuleOutput(5, "m", "モーダル → iv"),
            RuleOutput(5, "m7", "モーダル → iv7"),
            RuleOutput(8, "maj7", "モーダル → ♭VImaj7"),
            RuleOutput(10, "7", "モーダル → ♭VII7"),
            RuleOutput(3, "maj7", "モーダル → ♭IIImaj7"),
        ),
    ),
    # マイナートニック（相対メジャー表と同じ半音差でよく出現）
    MatchRule(
        0,
        ("m", "m7"),
        (
            RuleOutput(9, "maj", "相対メジャー → VI"),
            RuleOutput(9, "maj7", "相対メジャー → VImaj7"),
            RuleOutput(4, "maj", "相対メジャー → III"),
            RuleOutput(5, "maj", "相対メジャー → iv → IV"),
        ),
    ),
    MatchRule(
        9,
        ("m", "m7"),
        (
            RuleOutput(0, "maj", "機能置換 → i"),
            RuleOutput(0, "maj7", "機能置換 → Imaj7"),
            RuleOutput(5, "maj", "機能置換 → IV"),
        ),
    ),
)


def pc_to_name(pc: int) -> str:
    return m21_pitch.Pitch(pc % 12).name


def normalize_chord_type(figure: str) -> str:
    """コード記号文字列 → 内部タイプ。"""
    if not figure:
        return "maj"
    base = figure.split("/")[0].strip()
    fl = base.lower()
    if "m7b5" in fl or "m7(b5)" in fl or "ø" in base or "dim7" in fl:
        return "m7b5"
    if "maj7" in fl or "ma7" in fl or "mmaj7" in fl:
        return "maj7"
    if re.search(r"(^|[^a-z])maj([^a-z]|$)", fl):
        return "maj"
    if "m7" in fl or "min7" in fl:
        return "m7"
    if re.search(r"7", fl):
        return "7"
    if re.search(r"(^|[^a-z])m([^a-z]|$)|min", fl):
        return "m"
    if "dim" in fl:
        return "dim7"
    if "5" in fl and "maj" not in fl and "m" not in fl:
        return "maj"
    return "maj"


def type_matches(actual: str, family: str) -> bool:
    if family == "maj":
        return actual in ("maj", "maj7")
    if family == "m":
        return actual in ("m", "m7")
    if family == "7":
        return actual == "7"
    if family == "m7b5":
        return actual in ("m7b5", "dim7", "dim")
    return actual == family


def figure_from_spec(key: KeySpec, degree_pc: int, chord_type: str) -> str:
    root_pc = (key.root_pc + degree_pc) % 12
    name = pc_to_name(root_pc)
    suffix = {
        "maj": "",
        "maj7": "maj7",
        "m": "m",
        "m7": "m7",
        "7": "7",
        "m7b5": "m7b5",
        "dim7": "dim7",
    }.get(chord_type, "")
    return name + suffix


def chord_degree(key: KeySpec, chord: ChordSpec) -> int:
    return (chord.root_pc - key.root_pc) % 12


def key_from_music21(ky) -> KeySpec | None:
    if ky is None:
        return None
    try:
        tonic = ky.tonic
        root_pc = tonic.pitchClass
        mode = "minor" if str(getattr(ky, "mode", "major")).lower() == "minor" else "major"
        return KeySpec(root_pc, mode)
    except Exception:
        return None


def chord_spec_from_figure(figure: str, root_pc: int | None = None) -> ChordSpec:
    ctype = normalize_chord_type(figure)
    if root_pc is None:
        m = re.match(r"^([A-G](?:#|b)?)", figure.strip())
        if m:
            root_pc = m21_pitch.Pitch(m.group(1)).pitchClass
        else:
            root_pc = 0
    return ChordSpec(root_pc % 12, ctype)


def chord_spec_from_element(el, figure: str) -> ChordSpec:
    if hasattr(el, "pitch"):  # Note
        return ChordSpec(el.pitch.pitchClass, "note")
    try:
        root_pc = el.root().pitchClass
    except Exception:
        root_pc = el.pitches[0].pitchClass if el.pitches else 0
    return ChordSpec(root_pc, normalize_chord_type(figure))


def _chord_pitch_classes(key: KeySpec, degree_pc: int, chord_type: str) -> set[int]:
    root = (key.root_pc + degree_pc) % 12
    intervals = {
        "maj": {4, 7},
        "maj7": {4, 7, 11},
        "m": {3, 7},
        "m7": {3, 7, 10},
        "7": {4, 7, 10},
        "m7b5": {3, 6, 10},
        "dim7": {3, 6, 9},
    }.get(chord_type, {4, 7})
    return {root} | {(root + i) % 12 for i in intervals}


def melody_conflicts(chord_pcs: set[int], melody_midi: int | None) -> bool:
    """メロディ音がコード構成音と短2度で衝突。"""
    if melody_midi is None:
        return False
    mpc = melody_midi % 12
    for pc in chord_pcs:
        diff = (mpc - pc) % 12
        if diff in (1, 11):
            return True
    return False


def _same_chord(a: ChordSpec, key: KeySpec, degree_pc: int, chord_type: str) -> bool:
    return a.root_pc == (key.root_pc + degree_pc) % 12 and a.chord_type == chord_type


def _apply_major_rules(
    key: KeySpec,
    target: ChordSpec,
    melody_midi: int | None = None,
) -> list[tuple[str, str, bool]]:
    """(figure, rule_name, melody_conflict)"""
    deg = chord_degree(key, target)
    results: list[tuple[str, str, bool]] = []

    for rule in MAJOR_REPLACEMENT_RULES:
        if rule.degree_pc != deg:
            continue
        if not any(type_matches(target.chord_type, fam) for fam in rule.type_families):
            continue
        for out in rule.outputs:
            if _same_chord(target, key, out.degree_pc, out.chord_type):
                continue
            fig = figure_from_spec(key, out.degree_pc, out.chord_type)
            pcs = _chord_pitch_classes(key, out.degree_pc, out.chord_type)
            conflict = melody_conflicts(pcs, melody_midi)
            results.append((fig, out.rule_name, conflict))

    return results


def _secondary_dominant_candidates(
    key: KeySpec,
    target: ChordSpec,
    next_chord: ChordSpec | None,
    melody_midi: int | None,
) -> list[tuple[str, str, bool]]:
    if next_chord is None or next_chord.chord_type == "note":
        return []
    next_deg = chord_degree(key, next_chord)
    if next_deg not in DIATONIC_MAJOR_DEGREES:
        return []
    sd_root = (next_chord.root_pc + 7) % 12
    sd_type = "7"
    if _same_chord(target, key, (sd_root - key.root_pc) % 12, sd_type):
        return []
    fig = figure_from_spec(key, (sd_root - key.root_pc) % 12, sd_type)
    pcs = _chord_pitch_classes(key, (sd_root - key.root_pc) % 12, sd_type)
    name = f"セカンダリードミナント（次: {pc_to_name(next_chord.root_pc)}{next_chord.chord_type} の V7）"
    return [(fig, name, melody_conflicts(pcs, melody_midi))]


def _note_row_candidates(key: KeySpec, target: ChordSpec, melody_midi: int | None) -> list[tuple[str, str, bool]]:
    """単音行 — その音を含むダイアトニックコード候補。"""
    pc = target.root_pc
    out: list[tuple[str, str, bool]] = []
    templates = (
        (0, "maj", "トニック（I）"),
        (0, "maj7", "トニック Imaj7"),
        (5, "maj", "サブドミ IV"),
        (5, "maj7", "IVmaj7"),
        (7, "7", "ドミナント V7"),
        (9, "m", "vi"),
        (9, "m7", "vi7"),
        (2, "m7", "ii7"),
        (4, "m", "iii"),
    )
    for deg, ctype, label in templates:
        pcs = _chord_pitch_classes(key, deg, ctype)
        if pc not in pcs:
            continue
        fig = figure_from_spec(key, deg, ctype)
        out.append((fig, label, melody_conflicts(pcs, melody_midi)))
    return out


def _default_diatonic_candidates(
    key: KeySpec,
    target: ChordSpec,
    melody_midi: int | None,
) -> list[tuple[str, str, bool]]:
    """ルール未一致時のフォールバック。"""
    out: list[tuple[str, str, bool]] = []
    for deg, ctype, label in (
        (0, "maj", "ダイアトニック I"),
        (5, "maj", "ダイアトニック IV"),
        (7, "7", "ダイアトニック V7"),
        (9, "m7", "ダイアトニック vi7"),
        (2, "m7", "ダイアトニック ii7"),
        (4, "m", "ダイアトニック iii"),
    ):
        if _same_chord(target, key, deg, ctype):
            continue
        fig = figure_from_spec(key, deg, ctype)
        pcs = _chord_pitch_classes(key, deg, ctype)
        out.append((fig, label, melody_conflicts(pcs, melody_midi)))
    return out


def _key_for_rules(key: KeySpec) -> tuple[KeySpec, str]:
    """マイナーキーは相対長調のルール表で解析（表示用プレフィックス付き）。"""
    if key.mode == "minor":
        rel = KeySpec(root_pc=(key.root_pc + 3) % 12, mode="major")
        return rel, "相対長調 · "
    return key, ""


def rule_based_chord_suggestions(
    key: KeySpec,
    target: ChordSpec,
    *,
    next_chord: ChordSpec | None = None,
    melody_midi: int | None = None,
    current_figure: str = "",
) -> list[str]:
    """
    ルール適用 → 実コード復元 → フィルタ。
    表示形式: 「Am7  —  機能置換（トニック）→ vi7」
    """
    rules_key, prefix = _key_for_rules(key)
    raw: list[tuple[str, str, bool, int]] = []

    if target.chord_type == "note":
        for fig, name, conflict in _note_row_candidates(rules_key, target, melody_midi):
            raw.append((fig, prefix + name, conflict, 0))
    else:
        for fig, name, conflict in _apply_major_rules(rules_key, target, melody_midi):
            raw.append((fig, prefix + name, conflict, 1))
        for fig, name, conflict in _secondary_dominant_candidates(
            rules_key, target, next_chord, melody_midi
        ):
            raw.append((fig, prefix + name, conflict, 2))
        if not any(r[3] == 1 for r in raw):
            for fig, name, conflict in _default_diatonic_candidates(
                rules_key, target, melody_midi
            ):
                raw.append((fig, prefix + name, conflict, 0))

    seen: set[str] = set()
    ordered: list[tuple[str, str, bool]] = []
    # 非衝突を優先、次にルール由来優先度
    for fig, name, conflict, pri in sorted(raw, key=lambda x: (x[2], -x[3], x[0])):
        if fig in seen:
            continue
        if current_figure and fig == current_figure.strip():
            continue
        seen.add(fig)
        ordered.append((fig, name, conflict))

    lines: list[str] = []
    for fig, name, conflict in ordered[:20]:
        suffix = " ※メロディと短2度" if conflict else ""
        lines.append(f"{fig}  —  {name}{suffix}")

    return lines if lines else ["（候補を生成できません）"]
