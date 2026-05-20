//! midi_viz — wgpu MIDI ビジュアライザ（PyO3 / スタンドアロン）

mod engine;
mod export;
mod midi;
mod render;

#[cfg(feature = "python")]
mod pybind;

pub use engine::VisualizerEngine;
pub use midi::timeline::MidiTimeline;

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn midi_viz(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pybind::register_module(m)
}
