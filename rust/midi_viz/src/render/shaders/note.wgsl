// シェーダー駆動ノート: 相対拍 + MIDI メタのみをインスタンスで受け取り、NDC は VS で算出

struct Scene {
    aspect: f32,
    t_rel: f32,
    window_ql: f32,
    kb_ratio: f32,
    x0: f32,
    x1: f32,
    duration_ql: f32,
    sustain_extend: f32,
    y_lo: f32,
    y_hi: f32,
    style: f32,
    track_colors: f32,
    style_prev: f32,
    style_blend: f32,
}

@group(0) @binding(0) var<uniform> scene: Scene;
@group(0) @binding(1) var<storage, read> spectrum: array<f32>;

struct VertexInput {
    @location(0) corner: vec2<f32>,
}

struct InstanceInput {
    @location(1) t0: vec4<f32>,
    @location(2) t1: vec4<f32>,
}

struct VertexOutput {
    @builtin(position) pos: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) midi_c: f32,
    @location(2) vel_c: f32,
    @location(3) chan_c: f32,
    @location(4) alpha_c: f32,
    @location(5) discard_me: f32,
}

fn kb_bottom() -> f32 { return -1.0; }
fn kb_top(kb: f32) -> f32 { return -1.0 + kb * 2.0; }
fn play_y(kb: f32) -> f32 { return kb_top(kb); }
fn lane_top() -> f32 { return 1.0 - 0.05; }
fn fall_span(kb: f32) -> f32 { return lane_top() - play_y(kb); }

fn y_at_beat(t_rel: f32, beat_rel: f32, window_ql: f32, kb: f32) -> f32 {
    let play = play_y(kb);
    let span = max(fall_span(kb), 0.2);
    let w = max(window_ql, 0.001);
    return play - (t_rel - beat_rel) / w * span;
}

fn is_black_key(m: u32) -> bool {
    let mm = m % 12u;
    return mm == 1u || mm == 3u || mm == 6u || mm == 8u || mm == 10u;
}

fn build_key_x(midi: u32, y_lo: u32, y_hi: u32) -> vec2<f32> {
    var white_count = 0u;
    var mm = y_lo;
    loop {
        if (mm > y_hi) { break; }
        if (!is_black_key(mm)) { white_count = white_count + 1u; }
        mm = mm + 1u;
    }
    let span_keys = max(y_hi - y_lo, 1u);
    if (white_count == 0u) {
        let t = f32(midi - y_lo) / f32(span_keys);
        let xc = -1.0 + t * 2.0;
        return vec2<f32>(xc - 0.012, xc + 0.012);
    }
    if (!is_black_key(midi)) {
        var idx = 0u;
        var m2 = y_lo;
        loop {
            if (m2 > y_hi) { break; }
            if (!is_black_key(m2)) {
                if (m2 == midi) {
                    let n = f32(white_count);
                    let xl = -1.0 + (f32(idx) / n) * 2.0;
                    let xr = -1.0 + (f32(idx + 1u) / n) * 2.0;
                    return vec2<f32>(xl, xr);
                }
                idx = idx + 1u;
            }
            m2 = m2 + 1u;
        }
    }
    let t = f32(midi - y_lo) / f32(span_keys);
    let xc = -1.0 + t * 2.0;
    return vec2<f32>(xc - 0.012, xc + 0.012);
}

fn x_ndc_from_rel(onset_rel: f32) -> f32 {
    let x0 = scene.x0;
    let x1 = scene.x1;
    let span = max(x1 - x0, 0.001);
    let beat = onset_rel + x0;
    return ((beat - x0) / span) * 2.0 - 1.0;
}

fn midi_to_theta(midi: f32, y_lo: f32, y_hi: f32) -> f32 {
    let span = max(y_hi - y_lo, 1.0);
    let t = (midi - y_lo) / span;
    return t * 6.28318530718 - 1.57079632679;
}

fn polar_xy(angle: f32, radius: f32) -> vec2<f32> {
    return vec2<f32>(cos(angle) * radius, sin(angle) * radius);
}

fn midi_to_ndc_y(midi: f32, y_lo: f32, y_hi: f32, kb: f32) -> f32 {
    let span = max(y_hi - y_lo, 1.0);
    let t = (midi - y_lo) / span;
    let margin = 0.08;
    let bot = play_y(kb) + margin;
    let top = lane_top() - margin;
    return bot + t * (top - bot);
}

fn spec_dummy_read() -> f32 {
    return spectrum[0] * 0.0;
}

/// kind==0 ノート矩形のコーナー位置（未 aspect 補正）+ alpha + discard
fn note_kind0_at_style(
    style_f: f32,
    c: vec2<f32>,
    onset_rel: f32,
    end_rel: f32,
    midi: f32,
    velocity: f32,
    extra0: f32,
    t_rel: f32,
    wql: f32,
    kb: f32,
    asp: f32,
    y_lo: u32,
    y_hi: u32,
) -> vec4<f32> {
    var discard_me = 0.0;
    var alpha = 0.7;
    var p = vec2<f32>(0.0, 0.0);

    if (style_f < 0.5) {
        let play = play_y(kb);
        let top = lane_top();
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let y_on = y_at_beat(t_rel, onset_rel, wql, kb);
        let y_off = y_at_beat(t_rel, end_rel, wql, kb);
        var y_lo_n = min(y_on, y_off);
        var y_hi_n = max(y_on, y_off);
        y_lo_n = max(y_lo_n, play);
        y_hi_n = min(y_hi_n, top);
        if (y_hi_n - y_lo_n < 0.004) {
            discard_me = 1.0;
        } else {
            p = mix(vec2<f32>(xr.x, y_lo_n), vec2<f32>(xr.y, y_hi_n), c * 0.5 + 0.5);
        }
        let vel = clamp(velocity / 127.0, 0.0, 1.0);
        alpha = 0.55 + 0.25 * vel;
    } else if (style_f > 0.5 && style_f < 1.5) {
        let r_hub = 0.08;
        let r_max = 0.92;
        let span_t = max(wql, 0.001);
        let theta = midi_to_theta(midi, scene.y_lo, scene.y_hi);
        let age_on = max(t_rel - onset_rel, 0.0);
        let age_end = max(t_rel - end_rel, 0.0);
        var r_in = r_hub + (age_on / span_t) * (r_max - r_hub);
        var r_out = r_hub + (age_end / span_t) * (r_max - r_hub);
        if (onset_rel <= t_rel && t_rel < end_rel) {
            r_out = max(r_out, r_in + 0.05);
        }
        let th0 = theta - 0.02;
        let th1 = theta + 0.02;
        let p0 = polar_xy(th0, r_in);
        let p1 = polar_xy(th1, r_out);
        let mn = min(p0, p1);
        let mx = max(p0, p1);
        p = mix(mn, mx, c * 0.5 + 0.5);
        alpha = 0.7;
    } else if (style_f > 2.5) {
        let y = midi_to_ndc_y(midi, scene.y_lo, scene.y_hi, kb);
        let xs = x_ndc_from_rel(onset_rel);
        let px = x_ndc_from_rel(t_rel);
        let vel = velocity / 127.0;
        let th = 0.0025 + 0.004 * vel;
        if (extra0 > 0.5) {
            p = mix(vec2<f32>(px - 0.02, y - 0.025), vec2<f32>(px + 0.02, y + 0.025), c * 0.5 + 0.5);
            alpha = 0.75;
        } else {
            p = mix(vec2<f32>(min(xs, px), y - th), vec2<f32>(max(xs, px), y + th), c * 0.5 + 0.5);
            alpha = 0.55 + 0.3 * vel;
        }
    } else {
        discard_me = 1.0;
    }
    return vec4<f32>(p.x, p.y, alpha, discard_me);
}

@vertex
fn vs_main(v: VertexInput, inst: InstanceInput) -> VertexOutput {
    let _bind = spec_dummy_read();
    let c = v.corner;
    let onset_rel = inst.t0.x;
    let end_rel = inst.t0.y;
    var midi = inst.t0.z;
    let velocity = inst.t0.w;
    let channel = inst.t1.x;
    let kind = inst.t1.y;
    let extra0 = inst.t1.z;
    let extra1 = inst.t1.w;

    let kb = scene.kb_ratio;
    let asp = scene.aspect;
    let t_rel = scene.t_rel;
    let wql = scene.window_ql;
    let y_lo = u32(scene.y_lo);
    let y_hi = u32(scene.y_hi);
    let st = scene.style;

    var p = vec2<f32>(0.0, 0.0);
    var alpha = 0.7;
    var out_midi = midi;
    var out_vel = velocity;
    var out_ch = channel;

    var discard_me = 0.0;

    if (kind == 1.0) {
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let y0 = kb_bottom();
        let y1 = play_y(kb);
        p = mix(vec2<f32>(xr.x, y0), vec2<f32>(xr.y, y1), c * 0.5 + 0.5);
        alpha = 0.95;
    } else if (kind == 2.0) {
        let py = play_y(kb);
        p = mix(vec2<f32>(-1.0, py - 0.005), vec2<f32>(1.0, py + 0.005), c * 0.5 + 0.5);
        alpha = 0.65;
        out_midi = 60.0;
    } else if (kind == 3.0) {
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let floor_y = play_y(kb);
        let max_h = fall_span(kb);
        let h = extra0 * max_h;
        p = mix(vec2<f32>(xr.x, floor_y), vec2<f32>(xr.y, floor_y + h), c * 0.5 + 0.5);
        alpha = min(extra1, 0.95);
    } else if (kind == 4.0) {
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let floor_y = play_y(kb);
        let max_h = fall_span(kb);
        let peak = extra0;
        let pk_y = floor_y + peak * max_h;
        let dot_h = max(max_h * 0.018, 0.008);
        let cx = (xr.x + xr.y) * 0.5;
        let hw = (xr.y - xr.x) * 0.22;
        p = mix(vec2<f32>(cx - hw, pk_y - dot_h), vec2<f32>(cx + hw, pk_y + dot_h * 0.3), c * 0.5 + 0.5);
        alpha = min(extra1, 0.95);
    } else if (kind == 5.0) {
        let y = extra0 / 10.0;
        p = mix(vec2<f32>(-1.0, y - 0.001), vec2<f32>(1.0, y + 0.001), c * 0.5 + 0.5);
        alpha = 0.28;
        out_midi = 60.0;
    } else if (kind == 6.0) {
        let x = extra0;
        p = mix(vec2<f32>(x - 0.001, -1.0), vec2<f32>(x + 0.001, 1.0), c * 0.5 + 0.5);
        alpha = 0.22;
        out_midi = 60.0;
    } else if (kind == 7.0) {
        let px = x_ndc_from_rel(t_rel);
        p = mix(vec2<f32>(px - 0.002, -1.0), vec2<f32>(px + 0.002, 1.0), c * 0.5 + 0.5);
        alpha = 0.45;
        out_midi = 60.0;
    } else if (kind == 0.0) {
        let blend = scene.style_blend;
        let st_prev = scene.style_prev;
        if (blend > 0.001 && abs(st - st_prev) > 0.01) {
            let a = note_kind0_at_style(
                st_prev, c, onset_rel, end_rel, midi, velocity, extra0, t_rel, wql, kb, asp, y_lo, y_hi,
            );
            let b = note_kind0_at_style(
                st, c, onset_rel, end_rel, midi, velocity, extra0, t_rel, wql, kb, asp, y_lo, y_hi,
            );
            p = mix(a.xy, b.xy, blend);
            alpha = mix(a.z, b.z, blend);
            discard_me = max(a.w, b.w);
        } else {
            let r = note_kind0_at_style(
                st, c, onset_rel, end_rel, midi, velocity, extra0, t_rel, wql, kb, asp, y_lo, y_hi,
            );
            p = r.xy;
            alpha = r.z;
            discard_me = r.w;
        }
    } else {
        p = vec2<f32>(0.0, 0.0);
        discard_me = 1.0;
    }

    if (scene.track_colors < 0.5) {
        out_midi = 60.0;
    }

    p.y *= asp;

    var out: VertexOutput;
    out.pos = vec4<f32>(p.x, p.y, 0.0, 1.0);
    out.uv = c;
    out.midi_c = out_midi;
    out.vel_c = out_vel;
    out.chan_c = out_ch;
    out.alpha_c = alpha;
    out.discard_me = discard_me;
    return out;
}

fn midi_to_hsv(midi: f32, vel: f32, ch: f32) -> vec3<f32> {
    let h = fract(midi / 127.0 * 0.85 + 0.05 + ch * 0.03);
    let s = 0.75;
    let v = (0.45 + 0.55 * clamp(vel / 127.0, 0.0, 1.0)) * 0.95;
    return vec3<f32>(h, s, v);
}

fn hsv_to_rgb(c: vec3<f32>) -> vec3<f32> {
    let h = c.x * 6.0;
    let x = 1.0 - abs(fract(h * 0.5) * 2.0 - 1.0);
    var rgb = vec3<f32>(0.0);
    if (h < 1.0) { rgb = vec3<f32>(1.0, x, 0.0); }
    else if (h < 2.0) { rgb = vec3<f32>(x, 1.0, 0.0); }
    else if (h < 3.0) { rgb = vec3<f32>(0.0, 1.0, x); }
    else if (h < 4.0) { rgb = vec3<f32>(0.0, x, 1.0); }
    else if (h < 5.0) { rgb = vec3<f32>(x, 0.0, 1.0); }
    else { rgb = vec3<f32>(1.0, 0.0, x); }
    return rgb * c.z;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    if (in.discard_me > 0.5) { discard; }
    let hsv = midi_to_hsv(in.midi_c, in.vel_c, in.chan_c);
    let rgb = hsv_to_rgb(hsv);
    let veln = clamp(in.vel_c / 127.0, 0.0, 1.0);
    let hdr = rgb + vec3<f32>(0.15, 0.12, 0.08) * veln * veln;
    let edge = 1.0 - abs(in.uv.x) * abs(in.uv.y);
    let glow = pow(edge, 0.35);
    let rgb_mul = 0.7 + 0.5 * glow;
    let a_mul = 0.85 + 0.15 * glow;
    let a = clamp(in.alpha_c, 0.0, 0.92);
    return vec4<f32>(hdr * rgb_mul, a * a_mul);
}
