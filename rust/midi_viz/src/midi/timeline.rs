//! タイムライン — Python `MidiTimeline` と同等の仕様

pub const PIANO_LO: u8 = 21;
pub const PIANO_HI: u8 = 108;

#[derive(Debug, Clone)]
pub struct MidiNote {
    pub onset_ql: f64,
    pub duration_ql: f64,
    pub midi: u8,
    pub velocity: u8,
    pub channel: u8,
}

impl MidiNote {
    pub fn end_ql(&self) -> f64 {
        self.onset_ql + self.duration_ql.max(0.04)
    }
}

#[derive(Debug, Clone, Default)]
pub struct MidiTimeline {
    pub notes: Vec<MidiNote>,
    pub duration_ql: f64,
}

impl MidiTimeline {
    pub fn from_slices(
        onsets: &[f64],
        durations: &[f64],
        midis: &[u8],
        velocities: &[u8],
        channels: &[u8],
    ) -> Self {
        let n = onsets.len();
        let mut notes = Vec::with_capacity(n);
        for i in 0..n {
            notes.push(MidiNote {
                onset_ql: onsets[i],
                duration_ql: durations[i].max(0.04),
                midi: midis[i],
                velocity: velocities[i],
                channel: channels.get(i).copied().unwrap_or(0),
            });
        }
        let duration_ql = notes.iter().map(|n| n.end_ql()).fold(4.0_f64, f64::max);
        Self { notes, duration_ql }
    }

    pub fn y_range(&self) -> (u8, u8) {
        if self.notes.is_empty() {
            return (PIANO_LO, PIANO_HI);
        }
        let mut lo = self.notes.iter().map(|n| n.midi).min().unwrap_or(PIANO_LO);
        let mut hi = self.notes.iter().map(|n| n.midi).max().unwrap_or(PIANO_HI);
        lo = lo.saturating_sub(2).max(PIANO_LO);
        hi = hi.saturating_add(2).min(PIANO_HI);
        let min_span = 24u8;
        if hi.saturating_sub(lo) < min_span {
            let mid = (lo as u16 + hi as u16) / 2;
            lo = mid.saturating_sub(min_span as u16 / 2).max(PIANO_LO as u16) as u8;
            hi = (mid + min_span as u16 / 2).min(PIANO_HI as u16) as u8;
        }
        (lo, hi)
    }
}

pub fn visible_beat_window(t_ql: f64, window_ql: f64, duration_ql: f64) -> (f64, f64) {
    let duration_ql = duration_ql.max(0.01);
    let window_ql = window_ql.max(0.25);
    let t_ql = t_ql.clamp(0.0, duration_ql);
    if t_ql < window_ql * 0.05 {
        return (0.0, window_ql.min(duration_ql));
    }
    let x0 = (t_ql - window_ql).max(0.0);
    let x1 = (t_ql + 0.02).max(x0 + 0.5).min(duration_ql + 0.02);
    (x0, x1)
}

pub fn sec_to_ql(sec: f64, bpm: f64) -> f64 {
    sec * bpm.max(20.0) / 60.0
}

pub fn ql_to_sec(ql: f64, bpm: f64) -> f64 {
    ql * 60.0 / bpm.max(20.0)
}
