//! SMF パース（midly）

use std::path::Path;

use midly::{Smf, Timing};

use super::timeline::{MidiNote, MidiTimeline};

pub fn parse_smf_file(path: &Path, default_bpm: f64) -> Result<MidiTimeline, String> {
    let data = std::fs::read(path).map_err(|e| e.to_string())?;
    let smf = Smf::parse(&data).map_err(|e| format!("{e:?}"))?;
    let mut notes = Vec::new();
    let mut us_per_quarter = (60_000_000.0 / default_bpm.max(20.0)) as u32;

    for track in smf.tracks {
        let mut tick = 0u32;
        let mut vel = [0u8; 128];
        for event in track {
            tick += event.delta.as_int();
            match event.kind {
                midly::TrackEventKind::Meta(midly::MetaMessage::Tempo(t)) => {
                    us_per_quarter = t.as_int();
                }
                midly::TrackEventKind::Midi { message, .. } => match message {
                    midly::MidiMessage::NoteOn { key, vel: v } if v > 0 => {
                        vel[key.as_int() as usize] = v.as_int();
                    }
                    midly::MidiMessage::NoteOff { key, .. }
                    | midly::MidiMessage::NoteOn { key, .. } => {
                        let v = vel[key.as_int() as usize];
                        if v > 0 {
                            let onset_tick = tick; // simplified — production uses note stack
                            let ql = tick_to_ql(onset_tick, &smf.header, us_per_quarter);
                            let dur_ql = 0.25;
                            notes.push(MidiNote {
                                onset_ql: ql,
                                duration_ql: dur_ql,
                                midi: key.as_int(),
                                velocity: v,
                                channel: 0,
                            });
                        }
                    }
                    _ => {}
                },
                _ => {}
            }
        }
    }

    let duration_ql = notes.iter().map(|n| n.end_ql()).fold(4.0, f64::max);
    Ok(MidiTimeline { notes, duration_ql })
}

fn tick_to_ql(tick: u32, header: &midly::Header, us_per_quarter: u32) -> f64 {
    let us = match header.timing {
        Timing::Metrical(tpq) => {
            let tpq = tpq.as_int().max(1) as f64;
            tick as f64 / tpq * us_per_quarter as f64
        }
        Timing::Timecode(fps, res) => {
            let fps = fps.as_f32() as f64;
            let res = (res as f64).max(1.0);
            tick as f64 / fps / res * 1_000_000.0
        }
    };
    us / us_per_quarter as f64
}
