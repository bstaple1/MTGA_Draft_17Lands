; -- Example1.iss --
; Demonstrates copying 3 files and creating an icon.

; SEE THE DOCUMENTATION FOR DETAILS ON CREATING .ISS SCRIPT FILES!

[Setup]
AppName=MTGA Draft Tool
AppVersion=2.55
WizardStyle=modern
DefaultDirName={autopf}\MtgaDraftTool
DefaultGroupName=MtgaDraftTool
LicenseFile=LICENSE
UninstallDisplayIcon={app}\MtgaDraftTool.exe
Compression=lzma2
SolidCompression=yes
OutputDir={app}

[Files]
Source: "MTGA_Draft_Tool_V0255.exe"; DestDir: "{app}"
Source: "MTGA_Draft_Tool_V0255.exe.manifest"; DestDir: "{app}"
Source: "config.json"; DestDir: "{app}"
Source: "README.md"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\MtgaDraftTool"; Filename: "{app}\MTGA_Draft_Tool_V0254.exe"

[Dirs]
Name: {app}\Logs