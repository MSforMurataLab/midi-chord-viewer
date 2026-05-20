// GPU パーティクル物理（コンピュート）

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

struct SimParams {
    dt: f32,
    gravity: f32,
    drag: f32,
    amount: f32,
}

@group(0) @binding(0) var<storage, read_write> particles: array<Particle>;
@group(0) @binding(1) var<uniform> params: SimParams;

@compute @workgroup_size(256)
fn physics_main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x;
    if (i >= arrayLength(&particles)) {
        return;
    }
    var p = particles[i];
    if (p.life <= 0.0) {
        return;
    }
    p.life -= params.dt;
    if (p.life <= 0.0) {
        particles[i] = p;
        return;
    }
    p.vel.y -= params.gravity * params.dt;
    p.vel *= 1.0 - params.drag * params.dt;
    p.pos += p.vel * params.dt;
    particles[i] = p;
}
