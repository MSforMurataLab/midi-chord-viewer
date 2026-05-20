//! スペクトラム・バーアニメーション（Python SpectrumAnimator 相当）

use std::collections::HashMap;

use crate::midi::timeline::MidiTimeline;

#[derive(Clone, Copy, Default)]
struct BarAnim {
    height: f32,
    velocity: f32,
    peak: f32,
}

#[derive(Default)]
pub struct SpectrumAnimator {
    bars: HashMap<u8, BarAnim>,
}

impl SpectrumAnimator {
    pub fn clear(&mut self) {
        self.bars.clear();
    }

    pub fn tick(&mut self, timeline: &MidiTimeline, t_ql: f64, y_lo: u8, y_hi: u8, dt: f32) {
        let mut active: HashMap<u8, f32> = HashMap::new();
        for n in &timeline.notes {
            let end = n.end_ql();
            if n.onset_ql <= t_ql && t_ql < end {
                let v = n.velocity as f32 / 127.0;
                active
                    .entry(n.midi)
                    .and_modify(|e| *e = e.max(v))
                    .or_insert(v);
            }
        }

        for midi in y_lo..=y_hi {
            let bar = self.bars.entry(midi).or_default();
            let target = *active.get(&midi).unwrap_or(&0.0);
            bar.velocity = (bar.velocity * 0.88).max(target);

            if bar.height < target {
                bar.height += (target - bar.height) * (14.0 * dt).min(1.0);
            } else {
                let gap = bar.height - target;
                let step = ease_out_cubic((5.5 * dt).min(1.0)) * gap;
                bar.height = (bar.height - step).max(target);
            }

            if bar.height > bar.peak {
                bar.peak = bar.height;
            } else if bar.peak > bar.height {
                let fall = ease_out_cubic((2.2 * dt).min(1.0)) * 0.14;
                bar.peak = (bar.peak - fall).max(bar.height);
            }

            if target <= 0.0 && bar.height < 0.008 {
                bar.height = 0.0;
            }
            if bar.peak < 0.01 {
                bar.peak = 0.0;
            }
        }
    }

    pub fn height(&self, midi: u8) -> f32 {
        self.bars.get(&midi).map(|b| b.height).unwrap_or(0.0)
    }

    pub fn peak(&self, midi: u8) -> f32 {
        self.bars.get(&midi).map(|b| b.peak).unwrap_or(0.0)
    }

    pub fn velocity(&self, midi: u8) -> f32 {
        self.bars.get(&midi).map(|b| b.velocity).unwrap_or(0.0)
    }
}

fn ease_out_cubic(t: f32) -> f32 {
    let u = 1.0 - t;
    1.0 - u * u * u
}
