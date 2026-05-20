//! 生 MIDI イベント（リアルタイム用）

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MidiEventKind {
    NoteOn,
    NoteOff,
    ControlChange,
    Other,
}

#[derive(Debug, Clone, Copy)]
pub struct LiveMidiEvent {
    pub kind: MidiEventKind,
    pub channel: u8,
    pub data1: u8,
    pub data2: u8,
    /// マイクロ秒（オーディオ基準時刻）
    pub timestamp_us: u64,
}

impl LiveMidiEvent {
    pub fn from_status(status: u8, data1: u8, data2: u8, timestamp_us: u64) -> Self {
        let channel = status & 0x0f;
        let cmd = status & 0xf0;
        let kind = match cmd {
            0x90 if data2 > 0 => MidiEventKind::NoteOn,
            0x80 => MidiEventKind::NoteOff,
            0x90 => MidiEventKind::NoteOff,
            0xb0 => MidiEventKind::ControlChange,
            _ => MidiEventKind::Other,
        };
        Self {
            kind,
            channel,
            data1,
            data2,
            timestamp_us,
        }
    }
}
