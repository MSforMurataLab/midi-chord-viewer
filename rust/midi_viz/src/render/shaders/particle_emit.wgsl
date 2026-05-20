// MIDI ベロシティ立ち上がり → パーティクル emit（スタイル別のヒット位置）

struct Particle {
    pos: vec2<f32>,
    vel: vec2<f32>,
    life: f32,
    max_life: f32,
    size: f32,
    midi: f32,
    velocity: f32,
    _pad: f32,
}

struct EmitUniform {
    resolution: vec2<f32>,
    kb_ratio: f32,
    aspect: f32,
    y_lo: f32,
    y_hi: f32,
    x0: f32,
    x1: f32,
    t_ql: f32,
    style: f32,
    frame_seed: f32,
    amount_scale: f32,
}

const MAX_P: u32 = 16384u;

@group(0) @binding(0) var<storage, read_write> particles: array<Particle>;
@group(0) @binding(1) var<storage, read> vel_curr: array<f32>;
@group(0) @binding(2) var<storage, read> vel_prev: array<f32>;
@group(0) @binding(3) var<storage, read_write> spawn_head: array<atomic<u32>, 1>;
@group(0) @binding(4) var<uniform> emit_u: EmitUniform;

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

fn play_y(kb: f32) -> f32 {
    return -1.0 + kb * 2.0;
}

fn midi_to_theta(midi: u32, y_lo: u32, y_hi: u32) -> f32 {
    let span = max(f32(y_hi - y_lo), 1.0);
    let t = f32(midi - y_lo) / span;
    return t * 6.28318530718 - 1.57079632679;
}

fn midi_to_lane_y(midi: u32, y_lo: u32, y_hi: u32, kb: f32) -> f32 {
    let span = max(f32(y_hi - y_lo), 1.0);
    let t = f32(midi - y_lo) / span;
    let margin = 0.08;
    let bot = play_y(kb) + margin;
    let top = 1.0 - 0.05 - margin;
    return bot + t * (top - bot);
}

fn x_ndc_from_beat(beat_ql: f32, x0: f32, x1: f32) -> f32 {
    let span = max(x1 - x0, 0.001);
    return ((beat_ql - x0) / span) * 2.0 - 1.0;
}

fn ndc_pre_aspect_to_pixel(x_ndc: f32, y_ndc: f32) -> vec2<f32> {
    let y_clip = y_ndc * emit_u.aspect;
    let px = (x_ndc + 1.0) * 0.5 * emit_u.resolution.x;
    let py = (1.0 - (y_clip + 1.0) * 0.5) * emit_u.resolution.y;
    return vec2<f32>(px, py);
}

fn hit_ndc_for_note(midi: u32, y_lo: u32, y_hi: u32) -> vec2<f32> {
    let kb = emit_u.kb_ratio;
    let st = emit_u.style;
    let xr = build_key_x(midi, y_lo, y_hi);
    let cx = (xr.x + xr.y) * 0.5;

    if (st < 0.5) {
        return vec2<f32>(cx, play_y(kb));
    }
    if (st > 0.5 && st < 1.5) {
        let th = midi_to_theta(midi, y_lo, y_hi);
        let r_hub = 0.08;
        return vec2<f32>(cos(th) * r_hub, sin(th) * r_hub);
    }
    if (st > 1.5 && st < 2.5) {
        return vec2<f32>(cx, play_y(kb));
    }
    if (st > 2.5) {
        let y = midi_to_lane_y(midi, y_lo, y_hi, kb);
        let px = x_ndc_from_beat(emit_u.t_ql, emit_u.x0, emit_u.x1);
        return vec2<f32>(px, y);
    }
    return vec2<f32>(cx, play_y(kb));
}

fn hash_u32(x: u32) -> f32 {
    var v = x * 747796405u + 2891336453u;
    v = ((v >> 16u) ^ v) * 2246822519u;
    v = ((v >> 13u) ^ v) * 3266489917u;
    return f32(v & 0xffffu) / 65535.0;
}

/// スタイル別の初速度（ピクセル/秒）— ノートの進行方向に合わせる
fn particle_vel_pixel(midi: u32, y_lo: u32, y_hi: u32, h1: f32, h2: f32) -> vec2<f32> {
    let spread = (h1 - 0.5) * 1.2;
    let spd = 120.0 + h2 * 300.0;
    let st = emit_u.style;

    // Waterfall: 鍵盤上へ（上方向）
    if (st < 0.5) {
        return vec2<f32>(spread * spd * 0.65, -spd * (0.75 + h2 * 0.4));
    }

    // Circular: ハブから外側へ（ノートの半径拡大と同じ向き）
    if (st > 0.5 && st < 1.5) {
        let th = midi_to_theta(midi, y_lo, y_hi);
        var dir = vec2<f32>(
            cos(th) * emit_u.resolution.x,
            -sin(th) * emit_u.aspect * emit_u.resolution.y,
        );
        let len = length(dir);
        if (len > 0.001) {
            dir = dir / len;
        } else {
            dir = vec2<f32>(1.0, 0.0);
        }
        let tang = vec2<f32>(-sin(th), -cos(th) * emit_u.aspect);
        let tang_len = length(tang);
        var tang_n = vec2<f32>(0.0, 0.0);
        if (tang_len > 0.001) {
            tang_n = tang / tang_len;
        }
        return dir * spd + tang_n * spread * spd * 0.22;
    }

    // Cyber: タイムライン上でノートが進む向き（左 = 過去側）
    if (st > 2.5) {
        let lane_jitter = (h1 - 0.5) * spd * 0.35;
        return vec2<f32>(-spd * (0.85 + h2 * 0.25), lane_jitter);
    }

    // Spectrum 等: Waterfall に近い上向き
    return vec2<f32>(spread * spd * 0.65, -spd * (0.75 + h2 * 0.4));
}

@compute @workgroup_size(128)
fn emit_main(@builtin(local_invocation_id) lid: vec3<u32>) {
    let i = lid.x;
    if (i >= 128u) {
        return;
    }
    let v = vel_curr[i];
    let pv = vel_prev[i];
    if (v <= 0.12 || pv > 0.04) {
        return;
    }
    let midi = i;
    let y_lo = u32(emit_u.y_lo);
    let y_hi = u32(emit_u.y_hi);
    let hit = hit_ndc_for_note(midi, y_lo, y_hi);
    let origin = ndc_pre_aspect_to_pixel(hit.x, hit.y);
    let n = u32(6.0 * emit_u.amount_scale + 2.0);
    let base = u32(emit_u.frame_seed) * 7919u + i * 104729u;
    for (var k = 0u; k < n; k++) {
        let slot = atomicAdd(&spawn_head[0], 1u) % MAX_P;
        let h1 = hash_u32(base + k * 17u);
        let h2 = hash_u32(base + k * 97u + 1u);
        let vel_f = v;
        let life = 0.35 + h1 * 0.55;
        var np: Particle;
        np.pos = origin;
        np.vel = particle_vel_pixel(midi, y_lo, y_hi, h1, h2);
        np.life = life;
        np.max_life = life;
        np.size = 4.0 + h2 * 12.0 * vel_f;
        np.midi = f32(i);
        np.velocity = v * 127.0;
        np._pad = 0.0;
        particles[slot] = np;
    }
}
