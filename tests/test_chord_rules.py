# -*- coding: utf-8 -*-
from midi_lab.core.chord_rules import (
    ChordSpec,
    KeySpec,
    chord_spec_from_figure,
    figure_from_spec,
    rule_based_chord_suggestions,
)


def test_figure_roundtrip_c_major():
    key = KeySpec(0, "major")
    spec = ChordSpec(0, "maj7")
    fig = figure_from_spec(key, spec.root_pc, spec.chord_type)
    assert "maj7" in fig or fig.endswith("7")
    back = chord_spec_from_figure(fig)
    assert back.root_pc == 0


def test_major_tonic_suggestions():
    key = KeySpec(0, "major")
    target = ChordSpec(0, "maj7")
    lines = rule_based_chord_suggestions(key, target, current_figure="Cmaj7")
    assert lines
    assert lines[0] != "（候補を生成できません）"


def test_minor_uses_relative_rules():
    key = KeySpec(9, "minor")
    target = ChordSpec(9, "m")
    lines = rule_based_chord_suggestions(key, target, current_figure="Am")
    assert any("相対長調" in line for line in lines)
