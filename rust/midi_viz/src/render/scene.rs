//! タイムライン → GPU インスタンス（座標はシェーダー側で計算）
//!
//! CPU は可視ノートのメタデータ（開始・終了・MIDI・ベロシティ）のみ転送し、
//! レイアウト・落下・極座標は `note.wgsl` の頂点シェーダーで行う。

use crate::midi::timeline::{visible_beat_window, MidiTimeline};
use crate::render::spectrum_anim::SpectrumAnimator;

/// タイムライン由来のノート（頂点シェーダーがスタイルに応じて配置）
pub const KIND_NOTE: f32 = 0.0;
/// 鍵盤（白鍵幅はシェーダーで算出）
pub const KIND_PIANO_KEY: f32 = 1.0;
/// 再生ライン（ウォーターフォール）
pub const KIND_PLAYLINE: f32 = 2.0;
/// スペクトラム棒（`spectrum` ストレージ参照）
pub const KIND_SPECTRUM_BAR: f32 = 3.0;
/// スペクトラムピークドット
pub const KIND_SPECTRUM_PEAK: f32 = 4.0;
/// サイバーグリッド横線（`extra0` = -10..10 の行インデックス）
pub const KIND_CYBER_GRID_H: f32 = 5.0;
/// サイバーグリッド縦線
pub const KIND_CYBER_GRID_V: f32 = 6.0;
/// サイバー再生ヘッド（縦一線）
pub const KIND_CYBER_PLAYHEAD: f32 = 7.0;

/// 1 インスタンス = 32 byte（頂点 2×vec4）
#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuNoteInstance {
    /// 可視ウィンドウ左端 `x0` からの相対拍（数値安定のため）
    pub onset_rel: f32,
    pub end_rel: f32,
    pub midi: f32,
    pub velocity: f32,
    pub channel: f32,
    pub kind: f32,
    pub extra0: f32,
    pub extra1: f32,
}

/// `note.wgsl` の `Scene` とバイト一致させる
#[repr(C)]
#[derive(Clone, Copy, Default, bytemuck::Pod, bytemuck::Zeroable)]
pub struct NoteSceneUniform {
    pub aspect: f32,
    /// `t_ql - x0`（相対拍）
    pub t_rel: f32,
    pub window_ql: f32,
    pub kb_ratio: f32,
    pub x0: f32,
    pub x1: f32,
    pub duration_ql: f32,
    pub sustain_extend: f32,
    pub y_lo: f32,
    pub y_hi: f32,
    /// 0=Waterfall, 1=Circular, 2=Spectrum, 3=Cyber
    pub style: f32,
    pub track_colors: f32,
    /// 0=Waterfall … 3=Cyber（遷移元）
    pub style_prev: f32,
    /// スタイル間ブレンド 0..1
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

/// シーン uniform（`note.wgsl` の `Scene` と一致）
pub fn build_scene_uniform_full(
    params: &SceneParams,
    duration_ql: f64,
    y_lo: f32,
    y_hi: f32,
    x0: f64,
    x1: f64,
    style_prev: VisualStyle,
    style_blend: f32,
) -> NoteSceneUniform {
    NoteSceneUniform {
        aspect: params.aspect,
        t_rel: (params.t_ql - x0) as f32,
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

/// スペクトラム用 `[midi][0]=height, [1]=peak, [2]=vel` を 128×3 要素で詰める
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

pub fn pack_gpu_instances(
    timeline: &MidiTimeline,
    p: &SceneParams,
    spectrum: Option<&SpectrumAnimator>,
    x0: f64,
    x1: f64,
) -> Vec<GpuNoteInstance> {
    let (y_lo, y_hi) = timeline.y_range();
    let t = p.t_ql;
    let mut out = Vec::new();

    match p.style {
        VisualStyle::Waterfall => {
            for n in &timeline.notes {
                let mut end = n.end_ql();
                if p.sustain_extend > 0.0 && n.onset_ql <= t && t < end + 0.05 {
                    end = end.max(t + p.sustain_extend);
                }
                if end < x0 || n.onset_ql > x1 {
                    continue;
                }
                out.push(GpuNoteInstance {
                    onset_rel: (n.onset_ql - x0) as f32,
                    end_rel: (end - x0) as f32,
                    midi: if p.track_colors {
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
            out.push(GpuNoteInstance {
                onset_rel: 0.0,
                end_rel: 0.0,
                midi: 60.0,
                velocity: 100.0,
                channel: 0.0,
                kind: KIND_PLAYLINE,
                extra0: 0.0,
                extra1: 0.0,
            });
            for m in y_lo..=y_hi {
                out.push(GpuNoteInstance {
                    onset_rel: 0.0,
                    end_rel: 0.0,
                    midi: m as f32,
                    velocity: 80.0,
                    channel: 0.0,
                    kind: KIND_PIANO_KEY,
                    extra0: 0.0,
                    extra1: 0.0,
                });
            }
        }
        VisualStyle::Circular => {
            for n in &timeline.notes {
                let mut end = n.end_ql();
                if p.sustain_extend > 0.0 && n.onset_ql <= t && t < end + 0.05 {
                    end = end.max(t + p.sustain_extend);
                }
                if end < x0 || n.onset_ql > x1 {
                    continue;
                }
                out.push(GpuNoteInstance {
                    onset_rel: (n.onset_ql - x0) as f32,
                    end_rel: (end - x0) as f32,
                    midi: n.midi as f32,
                    velocity: n.velocity as f32,
                    channel: n.channel as f32,
                    kind: KIND_NOTE,
                    extra0: 0.0,
                    extra1: 0.0,
                });
            }
        }
        VisualStyle::Spectrum => {
            let spec = spectrum;
            for m in y_lo..=y_hi {
                let h = spec.map(|s| s.height(m)).unwrap_or(0.0);
                let peak = spec.map(|s| s.peak(m)).unwrap_or(0.0);
                let vel = spec.map(|s| s.velocity(m)).unwrap_or(0.0);
                let alpha_hint = 0.55 + 0.35 * vel;
                if h >= 0.02 {
                    out.push(GpuNoteInstance {
                        onset_rel: 0.0,
                        end_rel: 0.0,
                        midi: m as f32,
                        velocity: vel * 127.0,
                        channel: 0.0,
                        kind: KIND_SPECTRUM_BAR,
                        extra0: h,
                        extra1: alpha_hint,
                    });
                }
                if peak > h + 0.02 {
                    out.push(GpuNoteInstance {
                        onset_rel: 0.0,
                        end_rel: 0.0,
                        midi: m as f32,
                        velocity: 110.0,
                        channel: 0.0,
                        kind: KIND_SPECTRUM_PEAK,
                        extra0: peak,
                        extra1: alpha_hint + 0.15,
                    });
                }
            }
            for m in y_lo..=y_hi {
                out.push(GpuNoteInstance {
                    onset_rel: 0.0,
                    end_rel: 0.0,
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
                    onset_rel: 0.0,
                    end_rel: 0.0,
                    midi: 60.0,
                    velocity: 40.0,
                    channel: 0.0,
                    kind: KIND_CYBER_GRID_H,
                    extra0: i as f32,
                    extra1: 0.0,
                });
                let x = i as f32;
                out.push(GpuNoteInstance {
                    onset_rel: 0.0,
                    end_rel: 0.0,
                    midi: 60.0,
                    velocity: 35.0,
                    channel: 0.0,
                    kind: KIND_CYBER_GRID_V,
                    extra0: x,
                    extra1: 0.0,
                });
            }
            out.push(GpuNoteInstance {
                onset_rel: 0.0,
                end_rel: 0.0,
                midi: 60.0,
                velocity: 90.0,
                channel: 0.0,
                kind: KIND_CYBER_PLAYHEAD,
                extra0: 0.0,
                extra1: 0.0,
            });
            for n in &timeline.notes {
                let mut end = n.end_ql();
                if p.sustain_extend > 0.0 && n.onset_ql <= t && t < end + 0.05 {
                    end = end.max(t + p.sustain_extend);
                }
                if end < x0 || n.onset_ql > x1 {
                    continue;
                }
                out.push(GpuNoteInstance {
                    onset_rel: (n.onset_ql - x0) as f32,
                    end_rel: (end - x0) as f32,
                    midi: if p.track_colors {
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
                if n.onset_ql <= t && t < end {
                    out.push(GpuNoteInstance {
                        onset_rel: (n.onset_ql - x0) as f32,
                        end_rel: (end - x0) as f32,
                        midi: n.midi as f32,
                        velocity: n.velocity as f32,
                        channel: n.channel as f32,
                        kind: KIND_NOTE,
                        extra0: 1.0,
                        extra1: 0.0,
                    });
                }
            }
        }
    }

    out
}

/// 可視拍ウィンドウとインスタンス列をまとめて構築
pub fn pack_frame(
    timeline: &MidiTimeline,
    p: &SceneParams,
    spectrum: Option<&SpectrumAnimator>,
    style_prev: VisualStyle,
    style_blend: f32,
) -> (NoteSceneUniform, Vec<GpuNoteInstance>, [f32; 128 * 3]) {
    let (x0, x1) = visible_beat_window(p.t_ql, p.window_ql, timeline.duration_ql);
    let (y_lo, y_hi) = timeline.y_range();
    let scene = build_scene_uniform_full(
        p,
        timeline.duration_ql,
        y_lo as f32,
        y_hi as f32,
        x0,
        x1,
        style_prev,
        style_blend,
    );
    let instances = pack_gpu_instances(timeline, p, spectrum, x0, x1);
    let spec_buf = if let Some(s) = spectrum {
        pack_spectrum_gpu(s, y_lo, y_hi)
    } else {
        [0.0f32; 128 * 3]
    };
    (scene, instances, spec_buf)
}
