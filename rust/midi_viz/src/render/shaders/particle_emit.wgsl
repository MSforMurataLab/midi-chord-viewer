// MIDI ベロシティ立ち上がり → パーティクル emit（note.wgsl と同じ鍵盤 X）

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
    frame_seed: f32,
    amount_scale: f32,
    _p0: f32,
    _p1: f32,
    _p2: f32,
    _p3: f32,
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

/// NDC（Y は aspect 適用前）→ ピクセル（particle_draw と整合）
fn ndc_pre_aspect_to_pixel(x_ndc: f32, y_ndc: f32) -> vec2<f32> {
    let y_clip = y_ndc * emit_u.aspect;
    let px = (x_ndc + 1.0) * 0.5 * emit_u.resolution.x;
    let py = (1.0 - (y_clip + 1.0) * 0.5) * emit_u.resolution.y;
    return vec2<f32>(px, py);
}

fn hash_u32(x: u32) -> f32 {
    var v = x * 747796405u + 2891336453u;
    v = ((v >> 16u) ^ v) * 2246822519u;
    v = ((v >> 13u) ^ v) * 3266489917u;
    return f32(v & 0xffffu) / 65535.0;
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
    let kb = emit_u.kb_ratio;
    let xr = build_key_x(midi, y_lo, y_hi);
    let cx = (xr.x + xr.y) * 0.5;
    let py_ndc = play_y(kb);
    let origin = ndc_pre_aspect_to_pixel(cx, py_ndc);
    let n = u32(6.0 * emit_u.amount_scale + 2.0);
    let base = u32(emit_u.frame_seed) * 7919u + i * 104729u;
    for (var k = 0u; k < n; k++) {
        let slot = atomicAdd(&spawn_head[0], 1u) % MAX_P;
        let h1 = hash_u32(base + k * 17u);
        let h2 = hash_u32(base + k * 97u + 1u);
        let spread = (h1 - 0.5) * 1.2;
        let spd = 120.0 + h2 * 300.0;
        let vel_f = v;
        let life = 0.35 + h1 * 0.55;
        var np: Particle;
        np.pos = origin;
        np.vel = vec2<f32>(spread * spd * 0.65, -spd * (0.75 + h2 * 0.4));
        np.life = life;
        np.max_life = life;
        np.size = 4.0 + h2 * 12.0 * vel_f;
        np.midi = f32(i);
        np.velocity = v * 127.0;
        np._pad = 0.0;
        particles[slot] = np;
    }
}
