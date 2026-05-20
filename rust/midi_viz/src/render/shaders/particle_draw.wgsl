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

struct DrawUniforms {
    resolution: vec2<f32>,
    aspect: f32,
    _pad: f32,
}

@group(0) @binding(0) var<storage, read> particles: array<Particle>;
@group(0) @binding(1) var<uniform> u: DrawUniforms;

struct VertexOutput {
    @builtin(position) pos: vec4<f32>,
    @location(0) color: vec4<f32>,
    @location(1) uv: vec2<f32>,
    @location(2) @interpolate(flat) alive: f32,
}

@vertex
fn vs_main(
    @builtin(vertex_index) vi: u32,
    @builtin(instance_index) ii: u32,
) -> VertexOutput {
    let p = particles[ii];
    let corner = vec2<f32>(
        f32((vi >> 1u) & 1u) * 2.0 - 1.0,
        f32(vi & 1u) * 2.0 - 1.0,
    );
    let t = p.life / max(p.max_life, 0.001);
    let size = p.size * (0.5 + 0.5 * t);
    var ndc = p.pos / u.resolution * 2.0 - 1.0;
    ndc.y = -ndc.y;
    ndc += corner * size / u.resolution * vec2<f32>(2.0, 2.0 * u.aspect);

    var out: VertexOutput;
    if (p.life <= 0.0) {
        out.pos = vec4<f32>(0.0, 0.0, 0.0, 0.001);
        out.color = vec4<f32>(0.0);
        out.uv = corner;
        out.alive = 0.0;
        return out;
    }
    out.pos = vec4<f32>(ndc, 0.0, 1.0);
    let vel = clamp(p.velocity / 127.0, 0.0, 1.0);
    let hue = fract(p.midi / 127.0);
    out.color = vec4<f32>(0.4 + hue * 0.6, 0.6, 1.0, t * vel);
    out.uv = corner;
    out.alive = 1.0;
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    if (in.alive < 0.5) { discard; }
    let d = length(in.uv);
    let core = smoothstep(0.6, 0.0, d);
    let halo = smoothstep(1.0, 0.2, d) * 0.5;
    let rgb_mul = 1.0 + core * 2.0;
    return vec4<f32>(in.color.rgb * rgb_mul, in.color.a * (core + halo));
}
