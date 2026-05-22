# MIDI Chord Lab

MIDI の和声（コード）を解析・編集する Windows 向けデスクトップアプリです。PyQt6 と music21 をベースに、**和声タイムライン**・**分析スタジオ**・**GPU ビジュアライザ**・**理論アシスト**・**SoundFont 再生**を一体化しています。

**現在のバージョン:** 2.14.9（`midi_lab.__version__` と同期）

## 主な機能

| 機能 | 説明 |
|------|------|
| MIDI 読み込み | ファイル選択・ドラッグ＆ドロップ・最近使ったファイル・関連付け起動 |
| 和声タイムライン | コード／音名・**長さ（拍）**を編集。拍・開始位置は表示専用 |
| 行操作 | 右クリックで行の追加・複製・削除 |
| Undo / Redo | タイムライン編集の取り消し（`Ctrl+Z` / `Ctrl+Y`） |
| 分析スタジオ | ピアノロール・パフォーマンス統計・声部進行（非同期描画） |
| MIDI ビジュアライザ | Rust/wgpu または ModernGL。4 スタイル・Transport 同期・動画書き出し |
| コード記号推定 | 構成音から `Cmaj7` / `Am7` などを自動表示 |
| 理論アシスト | メジャー／マイナーキー向けルールベース置換候補 |
| **SoundFont 再生** | 同梱 **FluidSynth** でレンダリング。読み込み時に事前生成で初回再生を高速化 |
| **音量表現** | ノートの **ベロシティ**、**CC#7（Volume）**、**CC#11（Expression）** を再生に反映 |
| **音源切替** | `assets/soundfonts/` 以下の `.sf2` を自動列挙し、サイドバーから切替 |
| 保存 | `Ctrl+S` で上書き保存。未保存時はタイトルに `*` 表示 |
| 書き出し | MusicXML / MIDI / HTML 分析レポート / ビジュアライザ動画 |
| 配布 | PyInstaller exe、Inno Setup インストーラー（約 300MB、複数 SoundFont 同梱時） |

## SoundFont（再生音源）

再生は **FluidSynth + SoundFont（.sf2）** のみです（旧来の簡易合成・外部 MIDI デバイス出力はありません）。

### 配置場所

```
assets/
  fluidsynth/bin/     # fluidsynth.exe と DLL（同梱または setup スクリプト）
  soundfonts/         # ここに .sf2 を置く（サブフォルダ可）
    GeneralUser-GS/GeneralUser-GS.sf2
    Animal_Crossing_Wild_World.sf2
    ...
```

- `soundfonts` 以下の **すべての `.sf2`** が起動時・表示時に再スキャンされ、サイドバー **音源 (SoundFont)** に並びます。
- 選択は設定に保存され、次回起動時も復元されます。
- 100MB を超える SoundFont（例: `FluidR3_GM.sf2`、`chiptune_soundfont_4.0.sf2`）は **Git 管理外**です。ローカルに置けば開発・`build_release.ps1` の配布物に含まれます。

### FluidSynth のみセットアップ

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_soundfont.ps1
```

詳細は [assets/soundfonts/README.md](assets/soundfonts/README.md) を参照してください。

## 必要環境

| 用途 | 要件 |
|------|------|
| 開発 | **Python 3.11 以降**、Windows 推奨 |
| 配布 exe | **Windows 10/11**（64bit） |
| ビジュアライザ（任意） | Rust toolchain + maturin（`scripts/build_rust.bat`） |
| インストーラー作成 | [Inno Setup 6](https://jrsoftware.org/isdl.php) |

## セットアップ（開発）

```bash
cd midi-chord-viewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # テスト用（任意）
python app.py
```

引数で MIDI を開く例:

```bash
python app.py "曲.mid"
```

## ビルド（Windows）

### ポータブル exe のみ

```bat
build.bat
```

**成果物:** `dist\MIDIChordViewer\MIDIChordViewer.exe`

### リリース一式（推奨）

`assets` の配置修正・Qt ICU 対策・インストーラーまで含むフルビルド:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_release.ps1
```

**成果物:**

- `dist\MIDIChordViewer\` — 配布用フォルダ（`assets` は exe 横）
- `dist\installer\MIDIChordLab_Setup_2.14.9.exe` — インストーラー

### インストーラーのみ（exe 済みの場合）

```bat
build_installer.bat
```

## MIDI ファイルの関連付け

1. 配布 exe を起動 → **ファイル** → **MIDI ファイルの関連付けを登録…**
2. または `MIDIChordViewer.exe --register-midi-association`
3. 解除: `--unregister-midi-association`

## 使い方（概要）

1. MIDI を開くかウィンドウへドロップする。
2. 読み込み中に SoundFont で再生用オーディオを事前生成（ステータスバーに表示）。
3. **和声タイムライン**でコード・長さを編集。右クリックで行を追加／削除。
4. サイドバーで **テンポ**・**音源 (SoundFont)** を変更（変更後は再プリロード）。
5. **Space** または **再生** で聴く（タイムライン行とビジュアライザが同期）。
6. **理論アシスト**で候補をダブルクリックして反映。
7. 分析タブ（ピアノロール・パフォーマンス・声部進行・ビジュアライザ）を確認。
8. `Ctrl+S` で保存。必要に応じて MusicXML / MIDI / HTML レポート / 動画を書き出し。

### ショートカット

| 操作 | キー |
|------|------|
| MIDI を開く | `Ctrl+O` |
| 保存 | `Ctrl+S` |
| 元に戻す / やり直し | `Ctrl+Z` / `Ctrl+Y` |
| 再生 / 停止 | `Space` · `Ctrl+Enter` / `Ctrl+.` |
| 全画面 | `F11` / `Esc` |
| 理論アシスト | `Ctrl+\` |
| MusicXML | `Ctrl+Shift+S` |
| MIDI 書き出し | `Ctrl+Shift+M` |
| 分析レポート | `Ctrl+Shift+R` |
| ビジュアライザ動画 | `Ctrl+Shift+V` |

## 理論アシスト

`midi_lab/core/chord_rules.py` のルールベース置換。マイナーキーは相対長調のルールで候補を生成します。

## プロジェクト構成

```
app.py                      # エントリ（PyInstaller 向け）
midi_chord_viewer.spec      # PyInstaller 定義
midi_lab/
  core/                     # 解析・再生・SoundFont・MIDI 制御
    note_events.py          # スコアからのノート抽出
    midi_controls.py        # CC#7 / #11・mido 再生用ノート
    soundfont_player.py     # FluidSynth レンダ・音源一覧
    soundfont_midi.py       # 再生用一時 MIDI 生成
    playback.py             # 再生スレッド
  ui/                       # メインウィンドウ・テーマ・ウィジェット
  visualizer/               # MIDI ビジュアライザ（ModernGL / Rust）
rust/midi_viz/              # wgpu ビジュアライザ（オプション）
assets/
  fluidsynth/               # FluidSynth バイナリ
  soundfonts/               # .sf2 音源
installer/                  # Inno Setup（midi_chord_lab.iss）
scripts/
  build_release.ps1         # リリースビルド
  setup_soundfont.ps1       # FluidSynth セットアップ
tests/                      # pytest
```

## テスト

```bash
.venv\Scripts\activate
pytest
```

SoundFont / 再生まわり:

```bash
pytest tests/test_soundfont.py tests/test_midi_controls.py tests/test_playback_schedule.py
```

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。

同梱 SoundFont（GeneralUser GS 等）は各パッケージのライセンスに従ってください。
