//! NDC レイアウト — Python `layout.py` と同一仕様（Y: 下=-1, 上=+1）

pub fn kb_bottom_ndc(kb_ratio: f32) -> f32 {
    -1.0
}

pub fn kb_top_ndc(kb_ratio: f32) -> f32 {
    -1.0 + kb_ratio * 2.0
}

pub fn play_line_ndc(kb_ratio: f32) -> f32 {
    kb_top_ndc(kb_ratio)
}

pub fn lane_top_ndc(_kb_ratio: f32) -> f32 {
    1.0 - 0.05
}

pub fn fall_span_ndc(kb_ratio: f32) -> f32 {
    lane_top_ndc(kb_ratio) - play_line_ndc(kb_ratio)
}

pub fn y_at_beat(t_ql: f64, beat: f64, window_ql: f64, kb_ratio: f32) -> f32 {
    let play = play_line_ndc(kb_ratio) as f64;
    let span = fall_span_ndc(kb_ratio).max(0.2) as f64;
    let w = window_ql.max(0.001);
    (play - (t_ql - beat) / w * span) as f32
}

pub fn midi_to_theta(midi: u8, y_lo: u8, y_hi: u8) -> f32 {
    let span = (y_hi - y_lo).max(1) as f32;
    let t = (midi - y_lo) as f32 / span;
    t * std::f32::consts::TAU - std::f32::consts::FRAC_PI_2
}

pub fn polar_xy(aspect: f32, angle: f32, radius: f32) -> (f32, f32) {
    (
        angle.cos() * radius,
        angle.sin() * radius * aspect,
    )
}

pub fn x_ndc(beat: f64, x0: f64, x1: f64) -> f32 {
    let span = (x1 - x0).max(0.001);
    ((beat - x0) / span * 2.0 - 1.0) as f32
}

pub fn midi_to_ndc_y(midi: u8, y_lo: u8, y_hi: u8, kb_ratio: f32) -> f32 {
    let span = (y_hi - y_lo).max(1) as f32;
    let t = (midi - y_lo) as f32 / span;
    let margin = 0.08f32;
    let bot = play_line_ndc(kb_ratio) + margin;
    let top = lane_top_ndc(kb_ratio) - margin;
    bot + t * (top - bot)
}

pub fn build_key_x(midi: u8, y_lo: u8, y_hi: u8) -> (f32, f32) {
    let blacks = [1u8, 3, 6, 8, 10];
    let whites: Vec<u8> = (y_lo..=y_hi)
        .filter(|m| !blacks.contains(&(m % 12)))
        .collect();
    if whites.is_empty() {
        let span = (y_hi - y_lo).max(1) as f32;
        let t = (midi - y_lo) as f32 / span;
        let xc = -1.0 + t * 2.0;
        return (xc - 0.012, xc + 0.012);
    }
    if !blacks.contains(&(midi % 12)) {
        if let Some(i) = whites.iter().position(|&w| w == midi) {
            let n = whites.len() as f32;
            let xl = -1.0 + (i as f32 / n) * 2.0;
            let xr = -1.0 + ((i + 1) as f32 / n) * 2.0;
            return (xl, xr);
        }
    }
    let span = (y_hi - y_lo).max(1) as f32;
    let t = (midi - y_lo) as f32 / span;
    let xc = -1.0 + t * 2.0;
    (xc - 0.012, xc + 0.012)
}
