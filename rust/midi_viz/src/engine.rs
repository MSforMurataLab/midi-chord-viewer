//! ビジュアライザエンジン — MIDI + 描画 + 同期 + FFmpeg 書き出し

use crate::export::{DeterministicClock, FfmpegWriterThread};
use crate::midi::event::{LiveMidiEvent, MidiEventKind};
use crate::midi::ring::MidiRingBuffer;
use crate::midi::scheduler::MidiScheduler;
use crate::midi::timeline::{sec_to_ql, MidiTimeline};
use crate::render::scene::{pack_frame, SceneParams, VisualStyle};
use crate::render::spectrum_anim::SpectrumAnimator;
use crate::render::WgpuRenderer;

const STYLE_BLEND_SPEED: f32 = 2.5;

pub struct VisualizerEngine {
    renderer: WgpuRenderer,
    timeline: MidiTimeline,
    ring: MidiRingBuffer,
    scheduler: MidiScheduler,
    spectrum: SpectrumAnimator,
    t_ql: f64,
    bpm: f64,
    window_sec: f64,
    speed: f64,
    style: VisualStyle,
    style_prev: VisualStyle,
    style_blend_t: f32,
    track_colors: bool,
    particle_amount: f32,
    sustain_extend: f64,
    sustain_pedal: bool,
    audio_latency_ms: f64,
    export_clock: Option<DeterministicClock>,
    width: u32,
    height: u32,
    last_frame: Vec<u8>,
    note_vel_last: [f32; 128],
    /// ライブ MIDI 演奏中の鍵ベロシティ 0..127
    live_vel: [u8; 128],
    vel_edge_warmup: u8,
    render_frame_idx: u32,
}

impl VisualizerEngine {
    pub fn new(width: u32, height: u32) -> Result<Self, String> {
        let renderer = WgpuRenderer::new(width, height)?;
        Ok(Self {
            renderer,
            timeline: MidiTimeline::default(),
            ring: MidiRingBuffer::default(),
            scheduler: MidiScheduler::default(),
            spectrum: SpectrumAnimator::default(),
            t_ql: 0.0,
            bpm: 120.0,
            window_sec: 8.0,
            speed: 1.0,
            style: VisualStyle::Waterfall,
            style_prev: VisualStyle::Waterfall,
            style_blend_t: 1.0,
            track_colors: true,
            particle_amount: 1.0,
            sustain_extend: 0.0,
            sustain_pedal: false,
            audio_latency_ms: 0.0,
            export_clock: None,
            width,
            height,
            last_frame: Vec::new(),
            note_vel_last: [0.0; 128],
            live_vel: [0; 128],
            vel_edge_warmup: 3,
            render_frame_idx: 0,
        })
    }

    pub fn frame_rgba(&self) -> &[u8] {
        &self.last_frame
    }

    pub fn resize(&mut self, width: u32, height: u32) {
        self.width = width.max(1);
        self.height = height.max(1);
        self.renderer.resize(self.width, self.height);
    }

    pub fn load_timeline(&mut self, timeline: MidiTimeline) {
        self.timeline = timeline;
        self.t_ql = 0.0;
        self.spectrum.clear();
        self.note_vel_last = [0.0; 128];
        self.live_vel = [0; 128];
        self.vel_edge_warmup = 3;
    }

    pub fn set_transport(&mut self, t_ql: f64, bpm: f64, window_sec: f64, speed: f64) {
        self.t_ql = t_ql.max(0.0);
        self.bpm = bpm.max(20.0);
        self.window_sec = window_sec.max(0.25);
        self.speed = speed.max(0.25);
    }

    pub fn set_style(&mut self, style: &str) {
        let new = VisualStyle::from_str(style);
        if new != self.style {
            self.style_prev = self.style;
            self.style = new;
            self.style_blend_t = 0.0;
        }
    }

    pub fn set_track_colors(&mut self, on: bool) {
        self.track_colors = on;
    }

    pub fn set_particle_amount(&mut self, amount: f32) {
        self.particle_amount = amount.clamp(0.0, 2.0);
    }

    pub fn set_sustain_pedal(&mut self, down: bool) {
        self.sustain_pedal = down;
        self.scheduler.set_sustain(down);
    }

    pub fn set_audio_latency_ms(&mut self, ms: f64) {
        self.audio_latency_ms = ms.max(0.0);
    }

    pub fn begin_export(&mut self, fps: u32) {
        self.export_clock = Some(DeterministicClock::new(fps, self.bpm));
    }

    pub fn end_export(&mut self) {
        self.export_clock = None;
    }

    pub fn send_midi_event(&mut self, status: u8, data1: u8, data2: u8, timestamp_us: u64) {
        let ev = LiveMidiEvent::from_status(status, data1, data2, timestamp_us);
        let _ = self.ring.push(ev);
    }

    pub fn tick(&mut self, dt_sec: f32) {
        if self.sustain_pedal {
            self.sustain_extend = (self.sustain_extend + dt_sec as f64 * 1.2).min(2.5);
        } else {
            self.sustain_extend = (self.sustain_extend - dt_sec as f64 * 1.5).max(0.0);
        }
        self.advance_style_blend(dt_sec);
        if self.style == VisualStyle::Spectrum {
            let (y_lo, y_hi) = self.timeline.y_range();
            self.spectrum
                .tick(&self.timeline, self.t_ql, y_lo, y_hi, dt_sec);
        }
        self.drain_live_midi();
    }

    fn advance_style_blend(&mut self, dt_sec: f32) {
        if self.style_blend_t < 1.0 && self.style_prev != self.style {
            self.style_blend_t =
                (self.style_blend_t + dt_sec * STYLE_BLEND_SPEED).min(1.0);
        } else {
            self.style_prev = self.style;
            self.style_blend_t = 1.0;
        }
    }

    fn drain_live_midi(&mut self) {
        let mut batch = Vec::new();
        self.ring.drain(&mut batch);
        for ev in batch {
            match ev.kind {
                MidiEventKind::NoteOn => {
                    let midi = ev.data1 as usize;
                    if midi < 128 {
                        if ev.data2 > 0 {
                            self.live_vel[midi] = ev.data2;
                        } else {
                            self.live_vel[midi] = 0;
                        }
                    }
                    self.scheduler.schedule_note_on(
                        ev.timestamp_us,
                        ev.data1,
                        ev.data2,
                        ev.channel,
                    );
                }
                MidiEventKind::NoteOff => {
                    let midi = ev.data1 as usize;
                    if midi < 128 {
                        self.live_vel[midi] = 0;
                    }
                    self.scheduler
                        .schedule_note_off(ev.timestamp_us, ev.data1, ev.channel);
                }
                MidiEventKind::ControlChange if ev.data1 == 64 => {
                    self.set_sustain_pedal(ev.data2 >= 64);
                }
                _ => {}
            }
        }
    }

    fn window_ql(&self) -> f64 {
        sec_to_ql(self.window_sec / self.speed, self.bpm)
    }

    fn render_t_ql(&self) -> f64 {
        if let Some(clk) = &self.export_clock {
            clk.t_ql
        } else {
            self.t_ql
        }
    }

    fn fill_note_velocities(&self, out: &mut [f32; 128]) {
        out.fill(0.0);
        let t = self.render_t_ql();
        for n in &self.timeline.notes {
            let end = n.end_ql();
            if n.onset_ql <= t && t < end {
                let m = n.midi as usize;
                if m < 128 {
                    let v = n.velocity as f32 / 127.0;
                    out[m] = out[m].max(v);
                }
            }
        }
        for m in 0..128 {
            if self.live_vel[m] > 0 {
                let v = self.live_vel[m] as f32 / 127.0;
                out[m] = out[m].max(v);
            }
        }
    }

    pub fn render_frame(&mut self) {
        if let Some(clk) = &mut self.export_clock {
            clk.advance();
            self.t_ql = clk.t_ql;
        }

        let aspect = self.width as f32 / self.height as f32;
        let params = SceneParams {
            t_ql: self.render_t_ql(),
            window_ql: self.window_ql(),
            bpm: self.bpm,
            kb_ratio: 0.14,
            aspect,
            track_colors: self.track_colors,
            sustain_extend: self.sustain_extend,
            style: self.style,
        };

        let spec_ref = if self.style == VisualStyle::Spectrum {
            Some(&self.spectrum)
        } else {
            None
        };

        let style_prev = if self.style_blend_t < 1.0 {
            self.style_prev
        } else {
            self.style
        };
        let (scene, instances, spec_buf) = pack_frame(
            &self.timeline,
            &params,
            spec_ref,
            style_prev,
            self.style_blend_t,
        );

        let mut curr_vel = [0.0f32; 128];
        self.fill_note_velocities(&mut curr_vel);

        let prev_snapshot = self.note_vel_last;
        let prev_for_emit: &[f32; 128] = if self.vel_edge_warmup > 0 {
            self.vel_edge_warmup -= 1;
            &curr_vel
        } else {
            &prev_snapshot
        };

        self.render_frame_idx = self.render_frame_idx.wrapping_add(1);
        match self.renderer.render(
            &instances,
            &scene,
            &spec_buf,
            &curr_vel,
            prev_for_emit,
            self.render_frame_idx as f32,
            self.particle_amount,
        ) {
            Ok(frame) => self.last_frame = frame,
            Err(e) => log::warn!("render failed: {e}"),
        }
        self.note_vel_last = curr_vel;
    }

    /// タイムラインを決定論的にレンダリングし、FFmpeg へ RGBA をパイプ（書き込みは別スレッド）
    pub fn export_video_ffmpeg(
        &mut self,
        path: &str,
        fps: u32,
        width: u32,
        height: u32,
    ) -> Result<u32, String> {
        let fps = fps.clamp(12, 60);
        let w = width.max(64);
        let h = height.max(64);
        self.resize(w, h);

        let dur_sec = self.timeline.duration_ql * 60.0 / self.bpm.max(20.0);
        let n_frames = (dur_sec * fps as f64).ceil() as u32;
        let n_frames = n_frames.max(1);

        let mut writer = FfmpegWriterThread::start(path, w, h, fps)?;
        self.begin_export(fps);
        let dt = 1.0 / fps as f32;

        for _ in 0..n_frames {
            self.tick(dt);
            self.render_frame();
            let frame = self.last_frame.clone();
            writer.send_frame(frame)?;
        }

        self.end_export();
        writer.finish()?;
        Ok(n_frames)
    }
}
