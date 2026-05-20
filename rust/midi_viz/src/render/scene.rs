//! GPU シーン — 絶対拍インスタンス（読み込み時に一度だけ GPU へ転送）

use crate::midi::timeline::{visible_beat_window, MidiTimeline};
use crate::render::spectrum_anim::SpectrumAnimator;

pub const KIND_NOTE: f32 = 0.0;
pub const KIND_PIANO_KEY: f32 = 1.0;
pub const KIND_PLAYLINE: f32 = 2.0;
pub const KIND_SPECTRUM_BAR: f32 = 3.0;
pub const KIND_SPECTRUM_PEAK: f32 = 4.0;
pub const KIND_CYBER_GRID_H: f32 = 5.0;
pub const KIND_CYBER_GRID_V: f32 = 6.0;
pub const KIND_CYBER_PLAYHEAD: f32 = 7.0;

/// 絶対拍（クォーター長）— 毎フレームの CPU 再パック不要
#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuNoteInstance {
    /// ノート開始拍（絶対 quarter length）
    pub start_ql: f32,
    /// ノート終了拍（絶対）
    pub end_ql: f32,
    pub midi: f32,
    pub velocity: f32,
    pub channel: f32,
    pub kind: f32,
    pub extra0: f32,
    pub extra1: f32,
}

/// `note.wgsl` の `Scene` と一致
#[repr(C)]
#[derive(Clone, Copy, Default, bytemuck::Pod, bytemuck::Zeroable)]
pub struct NoteSceneUniform {
    pub aspect: f32,
    /// 現在の絶対拍
    pub t_ql: f32,
    pub window_ql: f32,
    pub kb_ratio: f32,
    pub x0: f32,
    pub x1: f32,
    pub duration_ql: f32,
    pub sustain_extend: f32,
    pub y_lo: f32,
    pub y_hi: f32,
    pub style: f32,
    pub track_colors: f32,
    pub style_prev: f32,
    pub style_blend: f32,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum VisualStyle {
    Waterfall = 0,
    Circular = 1,
    Spectrum = 2,
    Cyber = 3,
}

impl VisualStyle {
    pub fn from_str(s: &str) -> Self {
        match s {
            "circular" => Self::Circular,
            "spectrum" => Self::Spectrum,
            "cyber" => Self::Cyber,
            _ => Self::Waterfall,
        }
    }

    pub fn as_f32(self) -> f32 {
        self as u8 as f32
    }
}

#[derive(Clone, Copy)]
pub struct SceneParams {
    pub t_ql: f64,
    pub window_ql: f64,
    pub bpm: f64,
    pub kb_ratio: f32,
    pub aspect: f32,
    pub track_colors: bool,
    pub sustain_extend: f64,
    pub style: VisualStyle,
}

/// 曲全体のノート（可視窓で CPU 側フィルタしない）
pub fn build_timeline_notes(timeline: &MidiTimeline, track_colors: bool) -> Vec<GpuNoteInstance> {
    let mut out = Vec::with_capacity(timeline.notes.len());
    for n in &timeline.notes {
        out.push(GpuNoteInstance {
            start_ql: n.onset_ql as f32,
            end_ql: n.end_ql() as f32,
            midi: if track_colors {
                n.midi as f32
            } else {
                60.0
            },
            velocity: n.velocity as f32,
            channel: n.channel as f32,
            kind: KIND_NOTE,
            extra0: 0.0,
            extra1: 0.0,
        });
    }
    out
}

pub fn build_overlays(style: VisualStyle, y_lo: u8, y_hi: u8) -> Vec<GpuNoteInstance> {
    let mut out = Vec::new();
    match style {
        VisualStyle::Waterfall => {
            out.push(GpuNoteInstance {
                start_ql: 0.0,
                end_ql: 0.0,
                midi: 60.0,
                velocity: 100.0,
                channel: 0.0,
                kind: KIND_PLAYLINE,
                extra0: 0.0,
                extra1: 0.0,
            });
            for m in y_lo..=y_hi {
                out.push(GpuNoteInstance {
                    start_ql: 0.0,
                    end_ql: 0.0,
                    midi: m as f32,
                    velocity: 80.0,
                    channel: 0.0,
                    kind: KIND_PIANO_KEY,
                    extra0: 0.0,
                    extra1: 0.0,
                });
            }
        }
        VisualStyle::Circular => {}
        VisualStyle::Spectrum => {
            for m in y_lo..=y_hi {
                out.push(GpuNoteInstance {
                    start_ql: 0.0,
                    end_ql: 0.0,
                    midi: m as f32,
                    velocity: 80.0,
                    channel: 0.0,
                    kind: KIND_SPECTRUM_BAR,
                    extra0: 0.0,
                    extra1: 0.0,
                });
                out.push(GpuNoteInstance {
                    start_ql: 0.0,
                    end_ql: 0.0,
                    midi: m as f32,
                    velocity: 80.0,
                    channel: 0.0,
                    kind: KIND_PIANO_KEY,
                    extra0: 0.0,
                    extra1: 0.0,
                });
            }
        }
        VisualStyle::Cyber => {
            for i in -10..=10 {
                out.push(GpuNoteInstance {
                    start_ql: 0.0,
                    end_ql: 0.0,
                    midi: 60.0,
                    velocity: 40.0,
                    channel: 0.0,
                    kind: KIND_CYBER_GRID_H,
                    extra0: i as f32,
                    extra1: 0.0,
                });
                out.push(GpuNoteInstance {
                    start_ql: 0.0,
                    end_ql: 0.0,
                    midi: 60.0,
                    velocity: 35.0,
                    channel: 0.0,
                    kind: KIND_CYBER_GRID_V,
                    extra0: i as f32 / 10.0,
                    extra1: 0.0,
                });
            }
            out.push(GpuNoteInstance {
                start_ql: 0.0,
                end_ql: 0.0,
                midi: 60.0,
                velocity: 90.0,
                channel: 0.0,
                kind: KIND_CYBER_PLAYHEAD,
                extra0: 0.0,
                extra1: 0.0,
            });
        }
    }
    out
}

/// タイムライン全ノート + スタイル用オーバーレイ（読み込み・スタイル変更時のみ）
pub fn compose_gpu_scene(
    timeline: &MidiTimeline,
    style: VisualStyle,
    track_colors: bool,
) -> Vec<GpuNoteInstance> {
    let (y_lo, y_hi) = timeline.y_range();
    let mut out = build_timeline_notes(timeline, track_colors);
    out.extend(build_overlays(style, y_lo, y_hi));
    out
}

pub fn build_scene_uniform(
    params: &SceneParams,
    duration_ql: f64,
    y_lo: f32,
    y_hi: f32,
    style_prev: VisualStyle,
    style_blend: f32,
) -> NoteSceneUniform {
    let (x0, x1) = visible_beat_window(params.t_ql, params.window_ql, duration_ql);
    NoteSceneUniform {
        aspect: params.aspect,
        t_ql: params.t_ql as f32,
        window_ql: params.window_ql as f32,
        kb_ratio: params.kb_ratio,
        x0: x0 as f32,
        x1: x1 as f32,
        duration_ql: duration_ql as f32,
        sustain_extend: params.sustain_extend as f32,
        y_lo,
        y_hi,
        style: params.style.as_f32(),
        track_colors: if params.track_colors { 1.0 } else { 0.0 },
        style_prev: style_prev.as_f32(),
        style_blend: style_blend.clamp(0.0, 1.0),
    }
}

pub fn pack_spectrum_gpu(spectrum: &SpectrumAnimator, y_lo: u8, y_hi: u8) -> [f32; 128 * 3] {
    let mut buf = [0.0f32; 128 * 3];
    for m in y_lo..=y_hi {
        let i = m as usize * 3;
        if i + 2 < buf.len() {
            buf[i] = spectrum.height(m);
            buf[i + 1] = spectrum.peak(m);
            buf[i + 2] = spectrum.velocity(m);
        }
    }
    buf
}
