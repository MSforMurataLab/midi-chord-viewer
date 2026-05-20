# -*- coding: utf-8 -*-
import matplotlib

matplotlib.use("Agg")

from midi_lab.core.midi_visualizer import (
    VisualStyle,
    VisualizerData,
    build_preview_figure,
    render_frame,
    score_duration_ql,
    visible_beat_window,
)
from midi_lab.core.note_events import NoteEvent


def _sample_events() -> list[NoteEvent]:
    return [
        NoteEvent(0.0, 1.0, 60, 90, 0),
        NoteEvent(0.0, 1.0, 64, 80, 0),
        NoteEvent(1.0, 1.0, 62, 85, 0),
        NoteEvent(2.0, 2.0, 67, 100, 0),
    ]


def test_visualizer_data_duration():
    ev = _sample_events()
    assert score_duration_ql(ev) == 4.0
    vd = VisualizerData.from_events(ev)
    assert vd.duration_ql == 4.0


def test_render_all_styles():
    ev = _sample_events()
    for style in VisualStyle:
        fig = render_frame(style, ev, t_sec=0.5, bpm=120.0)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)


def test_visible_window_at_start():
    x0, x1 = visible_beat_window(0.0, 20.0, 100.0)
    assert x0 == 0.0
    assert x1 >= 10.0


def test_build_preview_figure():
    fig = build_preview_figure(VisualStyle.WATERFALL, _sample_events(), bpm=120.0)
    assert fig is not None
    import matplotlib.pyplot as plt

    plt.close(fig)
