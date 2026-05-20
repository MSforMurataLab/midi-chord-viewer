# -*- coding: utf-8 -*-
import numpy as np

from midi_lab.core.note_events import NoteEvent
from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.gl.geometry import build_geometry, build_scene_meshes
from midi_lab.visualizer.gl.particles import GPUParticleSystem
from midi_lab.visualizer.styles_builders.keyboard import build_key_map, key_geom_for_midi
from midi_lab.visualizer.timeline import MidiTimeline


def test_build_geometry_waterfall():
    ev = [NoteEvent(0.0, 1.0, 60, 100, 0), NoteEvent(2.0, 1.0, 64, 80, 1)]
    tl = MidiTimeline.from_note_events(ev)
    g = build_geometry(tl, t_ql=1.0, window_ql=8.0, style_id="waterfall", track_colors=True, sustain_extend=0.0)
    assert g.size >= 6
    scene = build_scene_meshes(
        tl, t_ql=1.0, window_ql=8.0, style_id="waterfall", track_colors=True, sustain_extend=0.0
    )
    assert scene.keyboard.size > 0
    assert hasattr(scene, "glow")


def test_circular_geometry_radial():
    ev = [NoteEvent(0.0, 1.0, 60, 100, 0), NoteEvent(0.0, 1.0, 84, 100, 0)]
    tl = MidiTimeline.from_note_events(ev)
    scene = build_scene_meshes(
        tl,
        t_ql=0.5,
        window_ql=4.0,
        style_id="circular",
        track_colors=True,
        sustain_extend=0.0,
        viewport_w=1920,
        viewport_h=1080,
    )
    assert scene.use_glow
    assert scene.notes.size >= 6
    xs = scene.notes["x"]
    ys = scene.notes["y"]
    assert xs.max() - xs.min() > 0.05


def test_spectrum_only_active():
    ev = [NoteEvent(0.0, 2.0, 60, 100, 0)]
    tl = MidiTimeline.from_note_events(ev)
    scene_on = build_scene_meshes(
        tl, t_ql=0.5, window_ql=4.0, style_id="spectrum", track_colors=True, sustain_extend=0.0
    )
    scene_off = build_scene_meshes(
        tl, t_ql=3.0, window_ql=4.0, style_id="spectrum", track_colors=True, sustain_extend=0.0
    )
    assert scene_on.notes.size >= scene_off.notes.size


def test_keyboard_aligns_note_width():
    keys = build_key_map(60, 72)
    kg = key_geom_for_midi(keys, 60, 60, 72)
    assert kg.x_right > kg.x_left
    assert abs((kg.x_right - kg.x_left) - (2.0 / max(1, len([m for m in range(60, 73) if m % 12 not in {1, 3, 6, 8, 10}])))) < 0.05


def test_gpu_particles():
    ps = GPUParticleSystem()
    ps.spawn_hit(100.0, 200.0, 100, r=0.5, g=0.7, b=1.0)
    assert len(ps) >= 1
    ps.update(0.016)
    arr = ps.active_array()
    assert arr["life"].max() <= arr["max_life"].max()
    assert arr["vy"].max() < 0


def test_engine_spawn_pixels():
    eng = VisualizerEngine()
    eng.load_events([NoteEvent(0.0, 0.5, 60, 127, 0)])
    eng.set_time_sec(0.0)
    eng.spawn_hits_pixels(800, 600)
    assert len(eng.particles) > 0
