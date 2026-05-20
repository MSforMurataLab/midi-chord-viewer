//! winit スタンドアロン — Rust 単体デバッグ（オフスクリーン）

use midi_viz::midi::timeline::{MidiNote, MidiTimeline};
use midi_viz::VisualizerEngine;

fn main() {
    env_logger::init();
    let mut engine = VisualizerEngine::new(1280, 720).expect("engine");

    let mut notes = Vec::new();
    for i in 0..32 {
        notes.push(MidiNote {
            onset_ql: i as f64 * 0.5,
            duration_ql: 0.4,
            midi: 60 + (i % 12),
            velocity: 80 + (i % 40) as u8,
            channel: 0,
        });
    }
    engine.load_timeline(MidiTimeline {
        notes,
        duration_ql: 20.0,
    });
    engine.set_transport(0.0, 120.0, 8.0, 1.0);
    engine.set_style("waterfall");

    for frame in 0..120 {
        let t = (frame as f64 / 60.0) * 2.0;
        engine.set_transport(t, 120.0, 8.0, 1.0);
        engine.tick(1.0 / 60.0);
        let rgba = engine.frame_rgba();
        assert_eq!(rgba.len(), 1280 * 720 * 4);
    }
    println!("standalone: 120 frames OK");
}
