# SoundFont

再生に使う GM SoundFont（`.sf2`）をここに置きます。

## 同梱

`soundfonts` 以下の `.sf2` を再帰的に探索し、サイドバーの **音源 (SoundFont)** ドロップダウンに表示します。

例:

- `GeneralUser-GS/GeneralUser-GS.sf2`
- `Animal_Crossing_Wild_World.sf2`

`FluidR3_GM.sf2` など 100MB を超えるファイルは Git 管理外です。ローカルに置けばドロップダウンと配布ビルドに含まれます。

選択は設定に保存され、次回起動時も復元されます。

## 自動セットアップ（FluidSynth のみ）

FluidSynth バイナリだけ必要な場合:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_soundfont.ps1
```

SoundFont は GeneralUser-GS を手動で配置するか、下記 URL から取得してください。

## 手動

任意の `.sf2` を上記フォルダに置くか、アプリの「設定」でパスを指定してください。
