//! PyO3 バインディング

use pyo3::prelude::*;
use pyo3::types::PyModule;

use crate::engine::VisualizerEngine;
use crate::midi::parse::parse_smf_file;
use crate::midi::timeline::MidiTimeline;

#[pyclass(name = "VisualizerEngine")]
struct PyVisualizerEngine {
    inner: Option<VisualizerEngine>,
}

#[pymethods]
impl PyVisualizerEngine {
    #[new]
    #[pyo3(signature = (width, height))]
    fn new(width: u32, height: u32) -> PyResult<Self> {
        let inner = VisualizerEngine::new(width, height)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;
        Ok(Self { inner: Some(inner) })
    }

    fn resize(&mut self, width: u32, height: u32) -> PyResult<()> {
        self.engine_mut()?.resize(width, height);
        Ok(())
    }

    fn render_frame(&mut self) -> PyResult<()> {
        self.engine_mut()?.render_frame();
        Ok(())
    }

    fn render_frame_rgba(&mut self) -> PyResult<Vec<u8>> {
        self.engine_mut()?.render_frame();
        Ok(self.engine_mut()?.frame_rgba().to_vec())
    }

    fn load_notes(
        &mut self,
        onsets: Vec<f64>,
        durations: Vec<f64>,
        midis: Vec<u8>,
        velocities: Vec<u8>,
        channels: Vec<u8>,
    ) -> PyResult<()> {
        let tl = MidiTimeline::from_slices(&onsets, &durations, &midis, &velocities, &channels);
        self.engine_mut()?.load_timeline(tl);
        Ok(())
    }

    fn set_transport(&mut self, t_ql: f64, bpm: f64, window_sec: f64, speed: f64) -> PyResult<()> {
        self.engine_mut()?.set_transport(t_ql, bpm, window_sec, speed);
        Ok(())
    }

    fn set_style(&mut self, style_id: &str) -> PyResult<()> {
        self.engine_mut()?.set_style(style_id);
        Ok(())
    }

    fn set_track_colors(&mut self, on: bool) -> PyResult<()> {
        self.engine_mut()?.set_track_colors(on);
        Ok(())
    }

    fn set_particle_amount(&mut self, amount: f32) -> PyResult<()> {
        self.engine_mut()?.set_particle_amount(amount);
        Ok(())
    }

    fn set_sustain_pedal(&mut self, down: bool) -> PyResult<()> {
        self.engine_mut()?.set_sustain_pedal(down);
        Ok(())
    }

    fn set_audio_latency_ms(&mut self, ms: f64) -> PyResult<()> {
        self.engine_mut()?.set_audio_latency_ms(ms);
        Ok(())
    }

    fn send_midi_event(
        &mut self,
        status: u8,
        data1: u8,
        data2: u8,
        timestamp_us: u64,
    ) -> PyResult<()> {
        self.engine_mut()?
            .send_midi_event(status, data1, data2, timestamp_us);
        Ok(())
    }

    fn tick(&mut self, dt_sec: f32) -> PyResult<()> {
        self.engine_mut()?.tick(dt_sec);
        Ok(())
    }

    fn begin_export(&mut self, fps: u32) -> PyResult<()> {
        self.engine_mut()?.begin_export(fps);
        Ok(())
    }

    fn end_export(&mut self) -> PyResult<()> {
        self.engine_mut()?.end_export();
        Ok(())
    }

    #[pyo3(signature = (path, fps=30, width=1280, height=720))]
    fn export_video_ffmpeg(
        &mut self,
        path: &str,
        fps: u32,
        width: u32,
        height: u32,
    ) -> PyResult<u32> {
        let n = self
            .engine_mut()?
            .export_video_ffmpeg(path, fps, width, height)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;
        Ok(n)
    }
}

impl PyVisualizerEngine {
    fn engine_mut(&mut self) -> PyResult<&mut VisualizerEngine> {
        self.inner
            .as_mut()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("engine closed"))
    }
}

#[pyfunction]
fn parse_midi_file(path: &str, bpm: f64) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let tl = parse_smf_file(std::path::Path::new(path), bpm)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;
        let onsets: Vec<f64> = tl.notes.iter().map(|n| n.onset_ql).collect();
        let durations: Vec<f64> = tl.notes.iter().map(|n| n.duration_ql).collect();
        let midis: Vec<u8> = tl.notes.iter().map(|n| n.midi).collect();
        let velocities: Vec<u8> = tl.notes.iter().map(|n| n.velocity).collect();
        let channels: Vec<u8> = tl.notes.iter().map(|n| n.channel).collect();
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("onsets", onsets)?;
        dict.set_item("durations", durations)?;
        dict.set_item("midis", midis)?;
        dict.set_item("velocities", velocities)?;
        dict.set_item("channels", channels)?;
        dict.set_item("duration_ql", tl.duration_ql)?;
        Ok(dict.into())
    })
}

#[pyfunction]
fn is_available() -> bool {
    true
}

pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyVisualizerEngine>()?;
    m.add_function(wrap_pyfunction!(parse_midi_file, m)?)?;
    m.add_function(wrap_pyfunction!(is_available, m)?)?;
    m.add("__version__", "0.1.0")?;
    Ok(())
}
