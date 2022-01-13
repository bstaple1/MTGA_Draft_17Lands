; -- MtgaDraft.iss --
[Setup]
AppName=MTGA Draft Tool
AppVersion=2.57
WizardStyle=modern
DefaultDirName={sd}\MtgaDraftTool
DefaultGroupName=MtgaDraftTool
LicenseFile=LICENSE
UninstallDisplayIcon={app}\MtgaDraftTool.exe
Compression=lzma2
UsePreviousAppDir=yes
SolidCompression=yes
OutputDir={app}

[Files]
Source: "MTGA_Draft_Tool.exe"; DestDir: "{app}"
Source: "config.json"; DestDir: "{app}"
Source: "README.md"; DestDir: "{app}"
source: "geckodriver.exe"; DestDir: "{app}" 
[Icons]
Name: "{group}\MtgaDraftTool"; Filename: "{app}\MTGA_Draft_Tool.exe"

[Dirs]
Name: {app}\Logs