; MIDI Chord Lab — Windows インストーラー (Inno Setup 6)
; 事前にプロジェクト直下で build.bat を実行し dist\MIDIChordViewer を生成してください。

#ifnexist "..\dist\MIDIChordViewer\MIDIChordViewer.exe"
  #error "dist\MIDIChordViewer\MIDIChordViewer.exe がありません。先に build.bat を実行してください。"
#endif

#define MyAppName "MIDI Chord Lab"
#define MyAppVersion "2.14.9"
#define MyAppPublisher "MSforMurataLab"
#define MyAppURL "https://github.com/MSforMurataLab/midi-chord-viewer"
#define MyAppExeName "MIDIChordViewer.exe"

[Setup]
AppId={{8F4E2A91-6C3D-4B1E-9F2A-1D7E5B4C9A60}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=MIDIChordLab_Setup_{#MyAppVersion}
; 2.14.0 からの DLL 配置変更を確実に反映するため AppId は維持しファイルは全上書き
SetupIconFile=..\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=no
LicenseFile=
InfoBeforeFile=
InfoAfterFile=

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加のショートカット:"
Name: "midiassoc"; Description: ".mid / .midi を MIDI Chord Lab で開く（現在のユーザー）"; GroupDescription: "ファイル関連付け:"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\assets"

[Files]
Source: "..\dist\MIDIChordViewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "MIDI 和声解析・編集"
Name: "{group}\MIDI 関連付けを登録"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-midi-association"; Comment: "現在のユーザー向け"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-midi-association"; StatusMsg: "MIDI ファイルの関連付けを登録しています…"; Tasks: midiassoc; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister-midi-association"; Flags: runhidden skipifdoesntexist

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
