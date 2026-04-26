; Glu2k-Image-Resizer Inno Setup Script

[Setup]
AppName=Glu2k-Image-Resizer
AppVersion=1.0.0
AppPublisher=Glu2k
AppPublisherURL=https://github.com/glu2k/Glu2k-Image-Resizer
DefaultDirName={autopf}\Glu2k-Image-Resizer
DefaultGroupName=Glu2k-Image-Resizer
UninstallDisplayIcon={app}\Glu2k-Image-Resizer.exe
OutputDir=installer_output
OutputBaseFilename=Glu2k-Image-Resizer-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Glu2k-Image-Resizer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Glu2k-Image-Resizer"; Filename: "{app}\Glu2k-Image-Resizer.exe"
Name: "{group}\Disinstalla Glu2k-Image-Resizer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Glu2k-Image-Resizer"; Filename: "{app}\Glu2k-Image-Resizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Glu2k-Image-Resizer.exe"; Description: "Avvia Glu2k-Image-Resizer"; Flags: nowait postinstall skipifsilent
