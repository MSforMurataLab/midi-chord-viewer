# MIDI Chord Lab

MIDI の和声（コード）を解析・編集するデスクトップアプリです。PyQt6 と music21 をベースに、タイムライン編集・理論アシスト・仮想鍵盤・再生を一体化しています。

## 機能

- MIDI 読み込み（ドラッグ＆ドロップ対応）
- 和声タイムライン（コード記号表示・セル編集）
- 再生（MIDI デバイス / ソフトウェア音源）
- 理論アシスト（コード・メロディ候補）
- MusicXML / MIDI 書き出し
- Windows 向け exe ビルド（PyInstaller）

## 必要環境

- Python 3.11 以降（推奨）
- Windows（配布 exe は Windows 向け）

## セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## ビルド（Windows）

```bash
build.bat
```

成果物: `dist/MIDIChordViewer/MIDIChordViewer.exe`

`image.png` から `app.ico` を生成してから PyInstaller を実行します（`app.ico` は `.gitignore` 対象）。

## プロジェクト構成

```
app.py                 # エントリポイント
midi_lab/              # アプリ本体
  main.py              # 起動・スプラッシュ
  core/                # 読み込み・和声・再生・スコア
  ui/                  # メインウィンドウ・テーマ・ウィジェット
midi_chord_viewer.spec # PyInstaller 設定
requirements.txt
```

## ライセンス

リポジトリ管理者に従ってください。
