# Rust / wgpu ビジュアライザ

MIDI Chord Lab の GPU ビジュアライザを **Rust + wgpu + PyO3** で再実装するプロジェクトです。既存の Python 仕様（4 スタイル・鍵盤同期・サスティン・パーティクル）を維持しつつ、ネイティブ性能で描画します。

## フェーズ対応表

| フェーズ | 内容 | 状態 |
|---------|------|------|
| 0 | PyO3 cdylib、`midi_viz` クレート、依存選定 | 基盤済 |
| 1 | wgpu インスタンシング、コンピュートパーティクル、WGSL | 基盤済 |
| 2 | リングバッファ、バイナリヒープスケジューラ | 基盤済 |
| 3 | HWND → wgpu Surface、PyQt6 統合 | 基盤済 |
| 4 | オーディオレイテンシ補正 API | API のみ |
| 5 | 決定論クロック、FFmpeg パイプ | 骨格のみ |
| — | Spectrum / Cyber スタイル（Rust） | 実装済 |
| — | 再生 MIDI → `send_midi_event` | 実装済 |

## ビルド

```bat
scripts\build_rust.bat
```

または:

```bash
cd midi-chord-viewer
.venv\Scripts\activate
maturin develop --release --manifest-path rust/midi_viz/Cargo.toml
```

## スタンドアロン確認（winit）

```bash
cargo run --release --bin midi_viz_standalone --manifest-path rust/midi_viz/Cargo.toml
```

## Python API

```python
import midi_viz

eng = midi_viz.VisualizerEngine(hwnd, width, height)
eng.load_notes(onsets, durations, midis, velocities, channels)
eng.set_transport(t_ql, bpm, window_sec, speed)
eng.set_style("waterfall")
eng.tick(1.0 / 60.0)
eng.render_frame()
```

## アプリ統合

`midi_lab/visualizer/canvas_factory.py` は **Rust/wgpu のみ**（`RustVisualizerCanvas`）。オフスクリーン描画の RGBA を Qt `QImage` で表示します。ModernGL は使用しません。

動画・PNG 連番の書き出しも `midi_viz` オフスクリーン描画を使用します。

## ディレクトリ

```
rust/midi_viz/
  src/
    midi/          # midly, リングバッファ, スケジューラ
    render/        # wgpu, WGSL, レイアウト, シーン
    export.rs      # 決定論クロック, FFmpeg
    engine.rs      # 統合エンジン
    pybind.rs      # PyO3
    bin/standalone.rs
```
