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
; Compile-time defines (passed via ISCC.exe command line):
;   /DBUNDLE_CHROMIUM - Indicates Chromium is bundled in the installer

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
; Allow user to choose install dir
AllowNoIcons=yes
; Output installer to installers/ directory
OutputDir=installers
OutputBaseFilename=MediaDownloaderSetup-{#MyAppVersion}-{#MyAppArchLabel}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Require admin for Program Files install
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Visual settings
WizardStyle=modern
; Uncomment when you have an icon:
SetupIconFile=assets\media_downloader.ico
; Uninstaller
UninstallDisplayName={#MyAppName}
; Minimum Windows version (Windows 10)
MinVersion=10.0
; Show "Setup will install..." on the ready page
DisableReadyPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Include everything from the PyInstaller dist output
Source: "dist\MediaDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Option to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up user data directory on uninstall (optional)
; Uncomment the next line if you want to remove user data on uninstall:
; Type: filesandirs; Name: "{userappdata}\.media_downloader"

[Messages]
; Customize the welcome page text
WelcomeLabel2=This will install [name/ver] on your computer.%n%nThe application allows you to download media from YouTube, Instagram, SoundCloud, TikTok, Twitter, Pinterest, RadioJavan, and Spotify.%n%nIt is recommended that you close all other applications before continuing.

[Code]
// Display information about what's included and what to expect
procedure CurPageChanged(CurPageID: Integer);
var
  chromiumBundled: Boolean;
  chromiumPath: String;
begin
  if CurPageID = wpFinished then
  begin
    // Only check for Chromium after install directory is set
    chromiumPath := ExpandConstant('{app}\chromium');
    chromiumBundled := DirExists(chromiumPath);

    if chromiumBundled then
    begin
      // Chromium is bundled - app is ready immediately
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
      // Chromium will be downloaded on first launch
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
