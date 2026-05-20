// 絶対拍インスタンス + scene.t_ql で座標算出（毎フレーム CPU 再パック不要）

struct Scene {
    aspect: f32,
    t_ql: f32,
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

fn y_at_beat(t_ql: f32, beat_ql: f32, window_ql: f32, kb: f32) -> f32 {
    let play = play_y(kb);
    let span = max(fall_span(kb), 0.2);
    let w = max(window_ql, 0.001);
    return play - (t_ql - beat_ql) / w * span;
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

fn x_ndc_from_beat(beat_ql: f32) -> f32 {
    let span = max(scene.x1 - scene.x0, 0.001);
    return ((beat_ql - scene.x0) / span) * 2.0 - 1.0;
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

fn spectrum_at(midi: u32) -> vec3<f32> {
    let i = midi * 3u;
    return vec3<f32>(spectrum[i], spectrum[i + 1u], spectrum[i + 2u]);
}

fn quad_from_rect(c: vec2<f32>, rect_min: vec2<f32>, rect_max: vec2<f32>) -> vec2<f32> {
    let t = c * 0.5 + 0.5;
    return mix(rect_min, rect_max, t);
}

fn note_end_vis(end_ql: f32, t_ql: f32) -> f32 {
    var end_v = end_ql;
    if (scene.sustain_extend > 0.0 && end_ql <= t_ql + 0.05) {
        end_v = max(end_v, t_ql + scene.sustain_extend);
    }
    return end_v;
}

/// Cyber / Circular — タイムライン窓（CPU と同じ x0/x1）
fn note_visible_timeline(start_ql: f32, end_ql: f32) -> bool {
    let end_v = note_end_vis(end_ql, scene.t_ql);
    return start_ql <= scene.x1 && end_v >= scene.x0;
}

/// Waterfall — 落下レーン用: 再生位置から最大 window_ql 拍先まで表示（x1≈t だと先読みが消える）
fn note_visible_waterfall(start_ql: f32, end_ql: f32) -> bool {
    let t = scene.t_ql;
    let w = max(scene.window_ql, 0.001);
    let end_v = note_end_vis(end_ql, t);
    let x0 = max(0.0, t - w);
    let x1_look = t + w;
    return start_ql <= x1_look && end_v >= x0;
}

/// kind==0 — style_f で配置（aspect 適用前）→ xyzw = xy, alpha, discard
fn note_kind0_at_style(
    style_f: f32,
    c: vec2<f32>,
    start_ql: f32,
    end_ql: f32,
    midi: f32,
    velocity: f32,
    extra0: f32,
    t_ql: f32,
    wql: f32,
    kb: f32,
    y_lo: u32,
    y_hi: u32,
) -> vec4<f32> {
    var discard_me = 0.0;
    var alpha = 0.7;
    var p = vec2<f32>(0.0, 0.0);

    let end_v = note_end_vis(end_ql, t_ql);

    if (style_f < 0.5) {
        if (!note_visible_waterfall(start_ql, end_ql)) {
            return vec4<f32>(0.0, 0.0, 0.0, 1.0);
        }
        let play = play_y(kb);
        let top = lane_top();
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let y_on = y_at_beat(t_ql, start_ql, wql, kb);
        let y_off = y_at_beat(t_ql, end_v, wql, kb);
        var y_bot = min(y_on, y_off);
        var y_top = max(y_on, y_off);
        y_bot = max(y_bot, play - 0.01);
        y_top = min(y_top, top);
        if (y_top - y_bot < 0.004) {
            discard_me = 1.0;
        } else {
            p = quad_from_rect(c, vec2<f32>(xr.x, y_bot), vec2<f32>(xr.y, y_top));
        }
        let vel = clamp(velocity / 127.0, 0.0, 1.0);
        alpha = 0.55 + 0.25 * vel;
        if (t_ql > end_v) {
            let fade = clamp((t_ql - end_v) / 0.25, 0.0, 1.0);
            alpha *= 1.0 - fade * 0.85;
        }
    } else if (style_f > 0.5 && style_f < 1.5) {
        if (!note_visible_timeline(start_ql, end_ql)) {
            return vec4<f32>(0.0, 0.0, 0.0, 1.0);
        }
        let r_hub = 0.08;
        let r_max = 0.92;
        let span_t = max(wql, 0.001);
        let theta = midi_to_theta(midi, scene.y_lo, scene.y_hi);
        let age_on = max(t_ql - start_ql, 0.0);
        let age_end = max(t_ql - end_v, 0.0);
        var r_in = r_hub + (age_on / span_t) * (r_max - r_hub);
        var r_out = r_hub + (age_end / span_t) * (r_max - r_hub);
        if (start_ql <= t_ql && t_ql < end_v) {
            r_out = max(r_out, r_in + 0.05);
        }
        let th0 = theta - 0.02;
        let th1 = theta + 0.02;
        let u = c.x * 0.5 + 0.5;
        let v = c.y * 0.5 + 0.5;
        let th = mix(th0, th1, u);
        let r = mix(r_in, r_out, v);
        p = polar_xy(th, r);
        alpha = 0.7;
    } else if (style_f > 1.5 && style_f < 2.5) {
        discard_me = 1.0;
    } else if (style_f > 2.5) {
        if (!note_visible_timeline(start_ql, end_ql)) {
            return vec4<f32>(0.0, 0.0, 0.0, 1.0);
        }
        let y = midi_to_ndc_y(midi, scene.y_lo, scene.y_hi, kb);
        let xs = x_ndc_from_beat(start_ql);
        let px = x_ndc_from_beat(t_ql);
        let vel = velocity / 127.0;
        let th = 0.0025 + 0.004 * vel;
        if (extra0 > 0.5) {
            p = quad_from_rect(
                c,
                vec2<f32>(px - 0.02, y - 0.025),
                vec2<f32>(px + 0.02, y + 0.025),
            );
            alpha = 0.75;
        } else {
            p = quad_from_rect(
                c,
                vec2<f32>(min(xs, px), y - th),
                vec2<f32>(max(xs, px), y + th),
            );
            alpha = 0.55 + 0.3 * vel;
        }
    } else {
        discard_me = 1.0;
    }
    return vec4<f32>(p.x, p.y, alpha, discard_me);
}

fn blend_note_geom(
    c: vec2<f32>,
    start_ql: f32,
    end_ql: f32,
    midi: f32,
    velocity: f32,
    extra0: f32,
    t_ql: f32,
    wql: f32,
    kb: f32,
    y_lo: u32,
    y_hi: u32,
) -> vec4<f32> {
    let st = scene.style;
    let st_prev = scene.style_prev;
    let b = scene.style_blend;
    let a = note_kind0_at_style(
        st_prev, c, start_ql, end_ql, midi, velocity, extra0, t_ql, wql, kb, y_lo, y_hi,
    );
    if (abs(st - st_prev) < 0.01 || b <= 0.001) {
        return note_kind0_at_style(
            st, c, start_ql, end_ql, midi, velocity, extra0, t_ql, wql, kb, y_lo, y_hi,
        );
    }
    if (b >= 0.999) {
        return note_kind0_at_style(
            st, c, start_ql, end_ql, midi, velocity, extra0, t_ql, wql, kb, y_lo, y_hi,
        );
    }
    let cur = note_kind0_at_style(
        st, c, start_ql, end_ql, midi, velocity, extra0, t_ql, wql, kb, y_lo, y_hi,
    );
    return vec4<f32>(
        mix(a.x, cur.x, b),
        mix(a.y, cur.y, b),
        mix(a.z, cur.z, b),
        max(a.w, cur.w),
    );
}

@vertex
fn vs_main(v: VertexInput, inst: InstanceInput) -> VertexOutput {
    let _bind = spec_dummy_read();
    let c = v.corner;
    let start_ql = inst.t0.x;
    let end_ql = inst.t0.y;
    var midi = inst.t0.z;
    let velocity = inst.t0.w;
    let channel = inst.t1.x;
    let kind = inst.t1.y;
    let extra0 = inst.t1.z;
    let extra1 = inst.t1.w;

    let kb = scene.kb_ratio;
    let asp = scene.aspect;
    let t_ql = scene.t_ql;
    let wql = scene.window_ql;
    let y_lo = u32(scene.y_lo);
    let y_hi = u32(scene.y_hi);

    var p = vec2<f32>(0.0, 0.0);
    var alpha = 0.7;
    var out_midi = midi;
    var out_vel = velocity;
    var out_ch = channel;
    var discard_me = 0.0;

    if (kind == 1.0) {
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        p = quad_from_rect(c, vec2<f32>(xr.x, kb_bottom()), vec2<f32>(xr.y, play_y(kb)));
        alpha = 0.95;
    } else if (kind == 2.0) {
        let py = play_y(kb);
        p = quad_from_rect(c, vec2<f32>(-1.0, py - 0.005), vec2<f32>(1.0, py + 0.005));
        alpha = 0.65;
        out_midi = 60.0;
    } else if (kind == 3.0) {
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let floor_y = play_y(kb);
        let max_h = fall_span(kb);
        let spec = spectrum_at(u32(midi));
        let h = spec.x * max_h;
        p = quad_from_rect(c, vec2<f32>(xr.x, floor_y), vec2<f32>(xr.y, floor_y + h));
        alpha = min(spec.z, 0.95);
    } else if (kind == 4.0) {
        let xr = build_key_x(u32(midi), y_lo, y_hi);
        let floor_y = play_y(kb);
        let max_h = fall_span(kb);
        let spec = spectrum_at(u32(midi));
        let peak = spec.y;
        let pk_y = floor_y + peak * max_h;
        let dot_h = max(max_h * 0.018, 0.008);
        let cx = (xr.x + xr.y) * 0.5;
        let hw = (xr.y - xr.x) * 0.22;
        p = quad_from_rect(
            c,
            vec2<f32>(cx - hw, pk_y - dot_h),
            vec2<f32>(cx + hw, pk_y + dot_h * 0.3),
        );
        alpha = min(spec.z, 0.95);
    } else if (kind == 5.0) {
        let y = extra0 / 10.0;
        p = quad_from_rect(c, vec2<f32>(-1.0, y - 0.001), vec2<f32>(1.0, y + 0.001));
        alpha = 0.28;
        out_midi = 60.0;
    } else if (kind == 6.0) {
        let x = extra0;
        p = quad_from_rect(c, vec2<f32>(x - 0.001, -1.0), vec2<f32>(x + 0.001, 1.0));
        alpha = 0.22;
        out_midi = 60.0;
    } else if (kind == 7.0) {
        let px = x_ndc_from_beat(t_ql);
        p = quad_from_rect(c, vec2<f32>(px - 0.002, -1.0), vec2<f32>(px + 0.002, 1.0));
        alpha = 0.45;
        out_midi = 60.0;
    } else if (kind == 0.0) {
        let r = blend_note_geom(
            c, start_ql, end_ql, midi, velocity, extra0, t_ql, wql, kb, y_lo, y_hi,
        );
        p = r.xy;
        alpha = r.z;
        discard_me = r.w;
    } else {
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
