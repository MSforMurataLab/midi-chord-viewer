# MIDI Chord Lab

MIDI の和声（コード）を解析・編集する Windows 向けデスクトップアプリです。PyQt6 と music21 をベースに、**和声タイムライン**・**分析スタジオ**・**ルールベース理論アシスト**・**仮想鍵盤**・**再生**を一体化しています。

**現在のバージョン:** 2.10.0

## 主な機能

| 機能 | 説明 |
|------|------|
| MIDI 読み込み | ファイル選択・ドラッグ＆ドロップ・最近使ったファイル・関連付け起動 |
| 和声タイムライン | コード／音名・**長さ（拍）**を編集。拍・開始位置は表示専用 |
| 行操作 | 右クリックで行の追加・複製・削除 |
| Undo / Redo | タイムライン編集の取り消し（`Ctrl+Z` / `Ctrl+Y`） |
| 分析スタジオ | ピアノロール・パフォーマンス統計・声部進行（非同期描画） |
| MIDI ビジュアライザ | ModernGL (GPU)・ブルーム・16k パーティクル・4 スタイル・Transport 同期 |
| コード記号推定 | 構成音から `Cmaj7` / `Am7` などを自動表示 |
| 理論アシスト | メジャー／マイナーキー向けルールベース置換候補 |
| 再生 | MIDI デバイスまたはソフトウェア音源。ファイルの BPM を反映 |
| 保存 | `Ctrl+S` で上書き保存。未保存時はタイトルに `*` 表示 |
| 書き出し | MusicXML / MIDI / HTML 分析レポート |
| 配布 | PyInstaller exe、Inno Setup インストーラー |

## 必要環境

- **Python 3.11 以降**（開発時）
- **Windows 10/11**（配布 exe）

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

**成果物:** `dist/MIDIChordViewer/MIDIChordViewer.exe`

## インストーラー（Windows）

1. `build.bat` で exe をビルド
2. [Inno Setup 6](https://jrsoftware.org/isdl.php) をインストール
3. `build_installer.bat` を実行

**成果物:** `dist/installer/MIDIChordLab_Setup_2.8.0.exe`

インストーラーではデスクトップショートカットと `.mid` / `.midi` の関連付け（任意）を設定できます。

## MIDI ファイルの関連付け

1. 配布 exe を起動 → **ファイル** → **MIDI ファイルの関連付けを登録…**
2. または `MIDIChordViewer.exe --register-midi-association`
3. エクスプローラーで `.mid` を **MIDI Chord Lab** に関連付け

開発時: `python app.py "曲.mid"`

## 使い方（概要）

1. MIDI を開くかドロップする。
2. **和声タイムライン**でコード・長さを編集。右クリックで行を追加／削除。
3. **Space** または **再生** で聴く（行がハイライト）。
4. **理論アシスト**で候補をダブルクリックして反映。
5. **ピアノロール**・**パフォーマンス**・**声部進行**タブで分析。
6. `Ctrl+S` で保存、必要に応じて MusicXML / レポートを書き出し。

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
app.py
midi_lab/
  core/          # 解析・再生・ルール・分析ワーカー
  ui/            # メインウィンドウ・テーマ・ウィジェット
installer/       # Inno Setup スクリプト
tests/           # pytest
build.bat
build_installer.bat
```

## テスト

```bash
pip install -r requirements-dev.txt
pytest
```

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。
