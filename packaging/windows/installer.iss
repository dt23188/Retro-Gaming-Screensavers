#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef OutputDir
  #define OutputDir "..\..\releases"
#endif
#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

[Setup]
AppId={{E8393547-525C-4E32-9489-E806B4ACD478}
AppName=Retro Gaming Screensavers
AppVersion={#AppVersion}
AppPublisher=dt23188
AppPublisherURL=https://github.com/dt23188/Retro-Gaming-Screensavers
AppSupportURL=https://github.com/dt23188/Retro-Gaming-Screensavers/issues
DefaultDirName={autopf}\Retro Gaming Screensavers
DefaultGroupName=Retro Gaming Screensavers
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
OutputDir={#OutputDir}
OutputBaseFilename=Retro-Gaming-Screensavers-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\..\LICENSE
UninstallDisplayIcon={app}\runtime\RetroScreensaver.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Files]
Source: "{#PayloadDir}\RetroScreensaver\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\RetroScreensaver\Retro Asteroids.scr"; DestDir: "{sys}"; Flags: ignoreversion
Source: "{#PayloadDir}\RetroScreensaver\Retro Pong.scr"; DestDir: "{sys}"; Flags: ignoreversion
Source: "{#PayloadDir}\RetroScreensaver\Retro Snake.scr"; DestDir: "{sys}"; Flags: ignoreversion
Source: "{#PayloadDir}\NOTICES\*"; DestDir: "{app}\NOTICES"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\SHA256SUMS"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\windows\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKLM; Subkey: "Software\RetroGamingScreensavers"; ValueType: string; ValueName: "RuntimePath"; ValueData: "{app}\runtime"; Flags: uninsdeletevalue uninsdeletekeyifempty

[Icons]
Name: "{group}\Screensaver Settings"; Filename: "{sys}\control.exe"; Parameters: "desk.cpl,,@screensaver"
Name: "{group}\Preview Asteroids"; Filename: "{app}\runtime\RetroScreensaver.exe"; Parameters: "--game asteroids --preview"
Name: "{group}\Preview Pong"; Filename: "{app}\runtime\RetroScreensaver.exe"; Parameters: "--game pong --preview"
Name: "{group}\Preview Snake"; Filename: "{app}\runtime\RetroScreensaver.exe"; Parameters: "--game snake --preview"
Name: "{group}\Uninstall Retro Gaming Screensavers"; Filename: "{uninstallexe}"

[Run]
Filename: "{sys}\control.exe"; Parameters: "desk.cpl,,@screensaver"; Description: "Choose a screensaver in Windows Settings"; Flags: postinstall nowait skipifsilent runasoriginaluser
