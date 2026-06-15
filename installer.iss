; Inno Setup Script for Media Downloader
; ========================================
;
; ffmpeg is downloaded during install so the app is ready on first launch.
; Uses curl.exe (built into Windows 10+) to download from BtbN FFmpeg-Builds.
; If ffmpeg download fails, installation continues silently — app handles
; missing ffmpeg gracefully with single-stream fallback.

#define MyAppName "Media Downloader"
#define MyAppVersion "1.1.1"
#ifndef MyAppArchLabel
#define MyAppArchLabel "x64"
#endif
#ifndef MyAppArchitecturesAllowed
#define MyAppArchitecturesAllowed "x64compatible"
#endif
#define MyAppPublisher "Media Downloader"
#define MyAppExeName "MediaDownloader.exe"
#define MyAppURL "https://github.com/MSC72m/media_downloader"
#define MyAppDescription "Download media from YouTube, Spotify, TikTok, Instagram, Twitter/X, Pinterest, SoundCloud, RadioJavan, and more"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
ArchitecturesAllowed={#MyAppArchitecturesAllowed}
ArchitecturesInstallIn64BitMode={#MyAppArchitecturesAllowed}
AppPublisher={#MyAppPublisher}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
AppComments={#MyAppDescription}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installers
OutputBaseFilename=MediaDownloaderSetup-{#MyAppVersion}-{#MyAppArchLabel}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
SetupIconFile=assets\media_downloader.ico
UninstallDisplayName={#MyAppName}
MinVersion=10.0
DisableReadyPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\MediaDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nThe application allows you to download media from YouTube, Instagram, SoundCloud, TikTok, Twitter, Pinterest, RadioJavan, and Spotify.%n%nIt is recommended that you close all other applications before continuing.

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  BinDir: String;
  FfmpegExe: String;
  TmpDir: String;
  ZipFile: String;
begin
  { Never block installation — return empty string to always continue }
  Result := '';
  BinDir := ExpandConstant('{app}\bin');
  FfmpegExe := BinDir + '\ffmpeg.exe';
  TmpDir := ExpandConstant('{tmp}');
  ZipFile := TmpDir + '\ffmpeg.zip';

  if FileExists(FfmpegExe) then
    Exit;

  CreateDir(BinDir);
  WizardForm.StatusLabel.Caption := 'Downloading ffmpeg...';

  { curl.exe is built into Windows 10+; -sS = silent but show errors }
  Exec('curl.exe',
    '-sS -L -o "' + ZipFile + '"' +
    ' "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if (ResultCode <> 0) or not FileExists(ZipFile) then
    Exit;

  WizardForm.StatusLabel.Caption := 'Extracting ffmpeg...';

  { Extract only ffmpeg.exe by matching entry Name (not FullName — BtbN zips
    have a subdirectory prefix like "ffmpeg-master-latest-win64-gpl/bin/") }
  Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -Command ' +
    '"Add-Type -AssemblyName System.IO.Compression.FileSystem;' +
    '$z=[System.IO.Compression.ZipFile]::OpenRead(''' + ZipFile + ''');' +
    'try{foreach($e in $z.Entries){if($e.Name -eq ''ffmpeg.exe''){' +
    '[System.IO.Compression.ZipFileExtensions]::ExtractToFile($e,''' + FfmpegExe + ''',$true);break}}}finally{$z.Dispose()}"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if FileExists(ZipFile) then
    DeleteFile(ZipFile);

  if FileExists(FfmpegExe) then
    WizardForm.StatusLabel.Caption := 'ffmpeg installed successfully.'
  else
    WizardForm.StatusLabel.Caption := 'ffmpeg installation skipped (will use app fallback).';
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    if DirExists(ExpandConstant('{app}\chromium')) then
    begin
      WizardForm.FinishedLabel.Caption :=
        'Setup has finished installing {#MyAppName} on your computer.' + #13#10 + #13#10 +
        'What was installed:' + #13#10 +
        '  - Media Downloader application' + #13#10 +
        '  - ffmpeg for video processing' + #13#10 +
        '  - Chromium browser for cookie generation' + #13#10 + #13#10 +
        'The application is ready to use immediately.';
    end
    else
    begin
      WizardForm.FinishedLabel.Caption :=
        'Setup has finished installing {#MyAppName} on your computer.' + #13#10 + #13#10 +
        'IMPORTANT - First Launch:' + #13#10 +
        'On the first run, the app will download a browser ' +
        'component (~150 MB) required for cookie generation.' + #13#10 + #13#10 +
        '  - A progress dialog will appear' + #13#10 +
        '  - This download only happens once' + #13#10 +
        '  - An internet connection is required' + #13#10 + #13#10 +
        'The browser component is stored in your user profile.';
    end;
  end;
end;
