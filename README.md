# MIDI Chord Lab

MIDI の和声（コード）を解析・編集する Windows 向けデスクトップアプリです。PyQt6 と music21 をベースに、**和声タイムライン**・**ルールベース理論アシスト**・**仮想鍵盤**・**再生**を一体化しています。

**現在のバージョン:** 2.4.5

## 主な機能

| 機能 | 説明 |
|------|------|
| MIDI 読み込み | ファイル選択・ドラッグ＆ドロップ・最近使ったファイル |
| 和声タイムライン | 拍・開始位置・長さ・コード記号・構成音を表形式で表示・編集 |
| コード記号推定 | 構成音から `Cmaj7` / `Am7` などを自動表示（music21 + 補完ルール） |
| 再生 | MIDI デバイス、またはソフトウェア音源（重なり和音をミックス再生） |
| 理論アシスト | メジャーキー向け置換ルールに基づくコード候補（次の和音からセカンダリードミナントも提示） |
| 仮想鍵盤 | 選択行・再生中の音高をハイライト |
| 書き出し | MusicXML / MIDI |
| 配布 | PyInstaller による `MIDIChordViewer.exe` |

## 必要環境

- **Python 3.11 以降**（開発時）
- **Windows 10/11**（配布 exe・ソフトウェア音源・`winsound` フォールバック）

## セットアップ（開発）

```bash
cd midi-chord-viewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## ビルド（Windows exe）

```bash
build.bat
```

または:

```bash
.venv\Scripts\activate
pip install pyinstaller
pyinstaller midi_chord_viewer.spec --noconfirm
```

**成果物:** `dist/MIDIChordViewer/MIDIChordViewer.exe`

`build.bat` は `image.png` から `app.ico` を生成してから PyInstaller を実行します（`app.ico` は `.gitignore` 対象）。

## 使い方（概要）

1. MIDI（`.mid` / `.midi`）を開くかドロップする。
2. 左サイドバーで **キー**・**BPM** を確認し、中央の **和声タイムライン** でコードを確認・ダブルクリック編集する。
3. **再生** / **停止** で聴きながら、行がハイライトされる。
4. 右 **理論アシスト** で候補をダブルクリックすると、コード列に反映される。
5. 必要に応じて MusicXML / MIDI を書き出す。

### ショートカット

| 操作 | キー |
|------|------|
| MIDI を開く | `Ctrl+O` |
| 再生 | `Ctrl+Enter` |
| 停止 | `Ctrl+.` |
| 全画面 | `F11` / `Esc`（終了） |
| 理論アシストパネル | `Ctrl+\` |
| MusicXML 保存 | `Ctrl+Shift+S` |
| MIDI 書き出し | `Ctrl+Shift+M` |

## 理論アシスト（ルールベース）

キーが検出されているとき、選択中のコードに対して **置換候補** を表示します。実装は `midi_lab/core/chord_rules.py` です。

- 入力コードをキー根音からの **半音度数** と **タイプ**（`maj` / `maj7` / `m` / `m7` / `7` / `m7b5` など）に抽象化
- メジャーキー向け **If-Then ルール表** で候補度数を導出し、実コード記号に復元
- **次の行**の和音がダイアトニックな場合、**セカンダリードミナント**（対象の V7）を追加
- 置換前後で同じコードは除外。メロディ音と短2度で衝突する候補は優先度を下げて表示

候補の例: `Am7  —  機能置換（トニック）→ vi7`

## 再生について

- **MIDI 出力デバイス**（Microsoft GS など）があればそちらを優先します。
- 未接続時は **ソフトウェア音源**（`sounddevice`）でタイムライン全体を1本の波形にミックスして再生します。
- 停止ボタンで `sounddevice` / `winsound` を中断します。

音が出ない場合は、Windows の音量・出力デバイスを確認してください。

## プロジェクト構成

```
app.py                      # エントリポイント
midi_lab/
  __init__.py               # バージョン
  main.py                   # 起動・スプラッシュ
  core/
    score.py                # MIDI 読み込み・タイムラインイベント
    harmony.py              # コード記号・候補 API
    chord_rules.py          # ルールベース理論アシスト
    playback.py             # 再生スレッド
    load_worker.py          # 非同期読み込み
  ui/
    main_window.py          # メイン UI
    theme.py                # Midnight Studio テーマ
    widgets/                # タイムライン・サイドバー・鍵盤など
midi_chord_viewer.spec      # PyInstaller
requirements.txt
build.bat
image.png                   # アイコン元画像
```

## 依存パッケージ

- PyQt6, music21, matplotlib, mido, numpy, sounddevice（`requirements.txt` 参照）

## ライセンス

リポジトリ管理者に従ってください。
