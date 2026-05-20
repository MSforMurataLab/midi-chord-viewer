//! ロックフリーリングバッファ（MIDI 受信 → 描画スレッド）

use std::sync::atomic::{AtomicUsize, Ordering};

use super::event::LiveMidiEvent;

const CAPACITY: usize = 4096;

pub struct MidiRingBuffer {
    buffer: Box<[LiveMidiEvent; CAPACITY]>,
    write: AtomicUsize,
    read: AtomicUsize,
}

impl Default for MidiRingBuffer {
    fn default() -> Self {
        Self {
            buffer: Box::new([LiveMidiEvent {
                kind: super::event::MidiEventKind::Other,
                channel: 0,
                data1: 0,
                data2: 0,
                timestamp_us: 0,
            }; CAPACITY]),
            write: AtomicUsize::new(0),
            read: AtomicUsize::new(0),
        }
    }
}

impl MidiRingBuffer {
    pub fn push(&self, event: LiveMidiEvent) -> bool {
        let w = self.write.load(Ordering::Acquire);
        let r = self.read.load(Ordering::Acquire);
        let next = (w + 1) % CAPACITY;
        if next == r {
            return false;
        }
        unsafe {
            let ptr = self.buffer.as_ptr() as *mut LiveMidiEvent;
            ptr.add(w).write(event);
        }
        self.write.store(next, Ordering::Release);
        true
    }

    pub fn drain(&self, out: &mut Vec<LiveMidiEvent>) {
        loop {
            let r = self.read.load(Ordering::Acquire);
            let w = self.write.load(Ordering::Acquire);
            if r == w {
                break;
            }
            let event = unsafe {
                let ptr = self.buffer.as_ptr();
                ptr.add(r).read()
            };
            out.push(event);
            self.read.store((r + 1) % CAPACITY, Ordering::Release);
        }
    }
}
