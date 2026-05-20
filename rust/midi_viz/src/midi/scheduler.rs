//! 優先度キューによるノートオン/オフスケジューリング

use std::cmp::Ordering;
use std::collections::BinaryHeap;

#[derive(Debug, Clone, Copy)]
pub struct ScheduledEvent {
    pub time_us: u64,
    pub midi: u8,
    pub velocity: u8,
    pub channel: u8,
    pub is_note_on: bool,
}

impl PartialEq for ScheduledEvent {
    fn eq(&self, other: &Self) -> bool {
        self.time_us == other.time_us
    }
}

impl Eq for ScheduledEvent {}

impl PartialOrd for ScheduledEvent {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for ScheduledEvent {
    fn cmp(&self, other: &Self) -> Ordering {
        other.time_us.cmp(&self.time_us)
    }
}

pub struct MidiScheduler {
    heap: BinaryHeap<ScheduledEvent>,
    sustain: bool,
}

impl Default for MidiScheduler {
    fn default() -> Self {
        Self {
            heap: BinaryHeap::new(),
            sustain: false,
        }
    }
}

impl MidiScheduler {
    pub fn schedule_note_on(&mut self, time_us: u64, midi: u8, velocity: u8, channel: u8) {
        self.heap.push(ScheduledEvent {
            time_us,
            midi,
            velocity,
            channel,
            is_note_on: true,
        });
    }

    pub fn schedule_note_off(&mut self, time_us: u64, midi: u8, channel: u8) {
        self.heap.push(ScheduledEvent {
            time_us,
            midi,
            velocity: 0,
            channel,
            is_note_on: false,
        });
    }

    pub fn set_sustain(&mut self, down: bool) {
        self.sustain = down;
    }

    pub fn sustain(&self) -> bool {
        self.sustain
    }

    pub fn pop_due(&mut self, now_us: u64, out: &mut Vec<ScheduledEvent>) {
        while let Some(ev) = self.heap.peek() {
            if ev.time_us > now_us {
                break;
            }
            out.push(self.heap.pop().unwrap());
        }
    }
}
