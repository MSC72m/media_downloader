; Inno Setup Script for Media Downloader
; ========================================
;
; Prerequisites:
;   1. Build the app with PyInstaller first:
;      pyinstaller media_downloader.spec
;   2. Install Inno Setup: https://jrsoftware.org/isinfo.php
;   3. Open this file in Inno Setup Compiler and click Build
;
; This produces:
;   installers/MediaDownloaderSetup-{version}.exe
;
; The installer downloads ffmpeg during setup so it is NOT shipped
; inside the .exe — keeps licensing clean.

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
#define FfmpegUrl "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

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
; App bundle from PyInstaller (no ffmpeg bundled)
Source: "dist\MediaDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\bin\ffmpeg.exe"

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nThe application allows you to download media from YouTube, Instagram, SoundCloud, TikTok, Twitter, Pinterest, RadioJavan, and Spotify.%n%nIt is recommended that you close all other applications before continuing.

[Code]
// ── ffmpeg download during install ──────────────────────────────
var
  FfmpegDownloadPage: TDownloadWizardPage;

procedure OnFfmpegDownloadProgress(Sender: TObject; const URL, FileName: String;
  const Progress, ProgressMax: Int64);
begin
  if ProgressMax > 0 then
    WizardForm.StatusLabel.Caption :=
      Format('Downloading ffmpeg... %d%%', [MulDiv(Progress, 100, ProgressMax)]);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  BinDir: String;
  ZipFile: String;
  TmpDir: String;
  FindRec: TFindRec;
  ZipEntry: String;
begin
  Result := '';

  BinDir := ExpandConstant('{app}\bin');
  if not DirExists(BinDir) then
    CreateDir(BinDir);

  // Skip download if ffmpeg already exists
  if FileExists(BinDir + '\ffmpeg.exe') then
  begin
    WizardForm.StatusLabel.Caption := 'ffmpeg already installed, skipping download.';
    Exit;
  end;

  WizardForm.StatusLabel.Caption := 'Downloading ffmpeg for video processing...';

  FfmpegDownloadPage := CreateDownloadPage(
    'Downloading ffmpeg',
    'ffmpeg is required for video/audio processing.' + #13#10 +
    'This is a one-time download (~80 MB) from gyan.dev.',
    @OnFfmpegDownloadProgress
  );
  FfmpegDownloadPage.Clear;
  FfmpegDownloadPage.Add('{#FfmpegUrl}', 'ffmpeg.zip', '');
  FfmpegDownloadPage.Show;

  try
    try
      FfmpegDownloadPage.Download;
    except
      Result := 'Failed to download ffmpeg. The app will work but video merging may fail.';
      Exit;
    end;

    // Extract ffmpeg.exe from the downloaded zip
    TmpDir := ExpandConstant('{tmp}');
    ZipFile := TmpDir + '\ffmpeg.zip';

    if not FileExists(ZipFile) then
    begin
      Result := 'ffmpeg download completed but file not found.';
      Exit;
    end;

    WizardForm.StatusLabel.Caption := 'Extracting ffmpeg...';

    // Use PowerShell to extract only ffmpeg.exe from the zip
    Exec('powershell.exe',
      '-NoProfile -ExecutionPolicy Bypass -Command "' +
      'Add-Type -AssemblyName System.IO.Compression.FileSystem; ' +
      '$zip = [System.IO.Compression.ZipFile]::OpenRead(''' + ZipFile + '''); ' +
      'try { ' +
      '  foreach ($entry in $zip.Entries) { ' +
      '    if ($entry.FullName -like ''*/bin/ffmpeg.exe'') { ' +
      '      [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, ''' + BinDir + '\ffmpeg.exe'', $true); ' +
      '      break; ' +
      '    } ' +
      '  } ' +
      '} finally { $zip.Dispose() }"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    if ResultCode <> 0 then
    begin
      Result := 'Failed to extract ffmpeg. The app will work but video merging may fail.';
      Exit;
    end;

    if not FileExists(BinDir + '\ffmpeg.exe') then
    begin
      Result := 'ffmpeg extraction completed but ffmpeg.exe not found.';
      Exit;
    end;

    WizardForm.StatusLabel.Caption := 'ffmpeg installed successfully.';

  finally
    // Cleanup temp zip
    if FileExists(ZipFile) then
      DeleteFile(ZipFile);
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  chromiumPath: String;
begin
  if CurPageID = wpFinished then
  begin
    chromiumPath := ExpandConstant('{app}\chromium');

    if DirExists(chromiumPath) then
    begin
      WizardForm.FinishedLabel.Caption :=
        'Setup has finished installing {#MyAppName} on your computer.' + #13#10 + #13#10 +
        'What was installed:' + #13#10 +
        '  - Media Downloader application' + #13#10 +
        '  - ffmpeg for video processing' + #13#10 +
        '  - Chromium browser for cookie generation' + #13#10 + #13#10 +
        'The application is ready to use immediately. No additional downloads are required.';
    end
    else
    begin
      WizardForm.FinishedLabel.Caption :=
        'Setup has finished installing {#MyAppName} on your computer.' + #13#10 + #13#10 +
        'What was installed:' + #13#10 +
        '  - Media Downloader application' + #13#10 +
        '  - ffmpeg for video processing' + #13#10 + #13#10 +
        'IMPORTANT - First Launch:' + #13#10 +
        'On the first run, the application will download a browser ' +
        'component (~150 MB) required for cookie generation. This is ' +
        'needed to access age-restricted or login-protected content.' + #13#10 + #13#10 +
        'What to expect:' + #13#10 +
        '  - A progress dialog will appear showing the download status' + #13#10 +
        '  - This download only happens once' + #13#10 +
        '  - An internet connection is required' + #13#10 +
        '  - The download takes 1-3 minutes depending on your connection' + #13#10 + #13#10 +
        'The browser component is stored in your user profile and does ' +
        'not require reinstallation when updating the application.';
    end;
  end;
end;
