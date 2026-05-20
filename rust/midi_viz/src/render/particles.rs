//! パーティクルプール（CPU スポーン + GPU シミュレーション）

use bytemuck::{Pod, Zeroable};

pub const MAX_PARTICLES: usize = 16384;

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
pub struct GpuParticle {
    pub pos: [f32; 2],
    pub vel: [f32; 2],
    pub life: f32,
    pub max_life: f32,
    pub size: f32,
    pub midi: f32,
    pub velocity: f32,
    pub _pad: f32,
}

pub struct ParticlePool {
    pub data: Vec<GpuParticle>,
    pub alive: usize,
    pub amount_scale: f32,
}

impl Default for ParticlePool {
    fn default() -> Self {
        Self {
            data: vec![GpuParticle::zeroed(); MAX_PARTICLES],
            alive: 0,
            amount_scale: 1.0,
        }
    }
}

impl ParticlePool {
    pub fn clear(&mut self) {
        self.alive = 0;
    }

    pub fn spawn_hit(&mut self, px: f32, py: f32, velocity: u8, midi: u8) {
        let n = (32.0 * self.amount_scale * (velocity as f32 / 127.0)).max(8.0) as usize;
        for _ in 0..n {
            if self.alive >= MAX_PARTICLES {
                self.alive = MAX_PARTICLES - 1;
            }
            let i = self.alive;
            self.alive += 1;
            let spread = (rand_simple() - 0.5) * 1.1;
            let spd = 120.0 + rand_simple() * 300.0;
            let vel_f = velocity as f32 / 127.0;
            let life = 0.4 + rand_simple() * 0.8;
            self.data[i] = GpuParticle {
                pos: [px, py],
                vel: [spread * spd * 0.65, -spd * (0.75 + rand_simple() * 0.4)],
                life,
                max_life: life,
                size: 4.0 + rand_simple() * 12.0 * vel_f,
                midi: midi as f32,
                velocity: velocity as f32,
                _pad: 0.0,
            };
        }
    }

    pub fn tick_cpu(&mut self, dt: f32) {
        let mut write = 0;
        for i in 0..self.alive {
            let mut p = self.data[i];
            p.life -= dt;
            if p.life <= 0.0 {
                continue;
            }
            p.vel[1] -= 220.0 * dt;
            p.vel[0] *= 1.0 - 1.8 * dt;
            p.pos[0] += p.vel[0] * dt;
            p.pos[1] += p.vel[1] * dt;
            self.data[write] = p;
            write += 1;
        }
        self.alive = write;
    }
}

fn rand_simple() -> f32 {
    use std::cell::Cell;
    thread_local! {
        static S: Cell<u32> = const { Cell::new(0x12345678) };
    }
    let mut x = S.get();
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    S.set(x);
    (x & 0x00ff_ffff) as f32 / 16777216.0
}
