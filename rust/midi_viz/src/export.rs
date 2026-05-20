//! 決定論的オフライン・レンダリング + FFmpeg パイプ

use std::io::Write;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::thread::{self, JoinHandle};

pub struct DeterministicClock {
    pub frame: u64,
    pub fps: u32,
    pub t_ql: f64,
    pub bpm: f64,
}

impl DeterministicClock {
    pub fn new(fps: u32, bpm: f64) -> Self {
        Self {
            frame: 0,
            fps: fps.max(1),
            t_ql: 0.0,
            bpm: bpm.max(20.0),
        }
    }

    pub fn advance(&mut self) -> f64 {
        let dt_sec = 1.0 / self.fps as f64;
        let dt_ql = dt_sec * self.bpm / 60.0;
        self.t_ql += dt_ql;
        self.frame += 1;
        self.t_ql
    }

    pub fn time_sec(&self) -> f64 {
        self.t_ql * 60.0 / self.bpm
    }
}

pub struct FfmpegPipe {
    child: Child,
    width: u32,
    height: u32,
}

impl FfmpegPipe {
    pub fn start(
        ffmpeg_exe: &str,
        path: &str,
        width: u32,
        height: u32,
        fps: u32,
    ) -> Result<Self, String> {
        let mut child = Command::new(ffmpeg_exe)
            .args([
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-s",
                &format!("{width}x{height}"),
                "-r",
                &fps.to_string(),
                "-i",
                "pipe:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "18",
                path,
            ])
            .stdin(Stdio::piped())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("ffmpeg spawn failed: {e}"))?;
        Ok(Self {
            child,
            width,
            height,
        })
    }

    pub fn write_frame(&mut self, rgba: &[u8]) -> Result<(), String> {
        let expected = (self.width * self.height * 4) as usize;
        if rgba.len() != expected {
            return Err(format!("frame size mismatch: {} vs {expected}", rgba.len()));
        }
        let stdin = self
            .child
            .stdin
            .as_mut()
            .ok_or("ffmpeg stdin closed")?;
        stdin.write_all(rgba).map_err(|e| e.to_string())
    }

    pub fn finish(mut self) -> Result<(), String> {
        if let Some(mut stdin) = self.child.stdin.take() {
            let _ = stdin.flush();
        }
        let status = self.child.wait().map_err(|e| e.to_string())?;
        if !status.success() {
            return Err(format!("ffmpeg exit: {status}"));
        }
        Ok(())
    }
}

/// 別スレッドで stdin へ書き込み（レンダースレッドは readback のみ待つ）
pub struct FfmpegWriterThread {
    tx: mpsc::Sender<Vec<u8>>,
    handle: Option<JoinHandle<Result<(), String>>>,
    err: Option<String>,
}

impl FfmpegWriterThread {
    pub fn start(
        ffmpeg_exe: &str,
        path: &str,
        width: u32,
        height: u32,
        fps: u32,
    ) -> Result<Self, String> {
        let (tx, rx) = mpsc::channel::<Vec<u8>>();
        let path = path.to_string();
        let ffmpeg_exe = ffmpeg_exe.to_string();
        let handle = thread::Builder::new()
            .name("midi_viz_ffmpeg".into())
            .spawn(move || {
                let mut pipe = FfmpegPipe::start(&ffmpeg_exe, &path, width, height, fps)?;
                while let Ok(frame) = rx.recv() {
                    pipe.write_frame(&frame)?;
                }
                pipe.finish()
            })
            .map_err(|e| format!("ffmpeg thread spawn: {e}"))?;
        Ok(Self {
            tx,
            handle: Some(handle),
            err: None,
        })
    }

    pub fn send_frame(&mut self, rgba: Vec<u8>) -> Result<(), String> {
        self.tx
            .send(rgba)
            .map_err(|_| "ffmpeg writer channel closed".to_string())
    }

    pub fn finish(mut self) -> Result<(), String> {
        drop(self.tx);
        if let Some(h) = self.handle.take() {
            match h.join() {
                Ok(Ok(())) => Ok(()),
                Ok(Err(e)) => Err(e),
                Err(_) => Err("ffmpeg writer thread panicked".to_string()),
            }
        } else {
            Ok(())
        }
    }
}
