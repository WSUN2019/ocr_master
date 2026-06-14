; Inno Setup script for OCR Master
; Download Inno Setup free from: https://jrsoftware.org/isinfo.php
;
; Before running this script:
;   1. Build the PyInstaller bundle:  pyinstaller build\OCRMaster.spec
;   2. Open this file in the Inno Setup Compiler and click Build > Compile
;
; Output: build\Output\OCRMasterSetup.exe

#define AppName      "OCR Master"
#define AppVersion   "1.2.0"
#define AppPublisher "WSUN2019"
#define AppURL       "https://github.com/WSUN2019/ocr_master"
#define AppExeName   "OCRMaster.exe"
#define SourceDir    "..\dist\OCRMaster"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\OCRMaster
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=OCRMasterSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Require 64-bit Windows
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application bundle (output from PyInstaller)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function TesseractInstalled(): Boolean;
var
  Path: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Tesseract-OCR', 'InstallDir', Path) or
            RegQueryStringValue(HKLM32, 'SOFTWARE\Tesseract-OCR', 'InstallDir', Path);
end;

// Visual C++ 2015-2022 x64 Redistributable (required by python3XX.dll)
function VCRedistInstalled(): Boolean;
var
  Ver: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Ver) or
            RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Ver);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
begin
  if CurStep = ssDone then
  begin
    if not VCRedistInstalled() then
    begin
      if MsgBox(
        'OCR Master requires the Microsoft Visual C++ Redistributable (2022, x64).' + #13#10 + #13#10 +
        'It is NOT currently installed on this machine.' + #13#10 + #13#10 +
        'Without it the application will fail to start.' + #13#10 + #13#10 +
        'Would you like to open the Microsoft download page now?',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        ShellExec('open', 'https://aka.ms/vs/17/release/vc_redist.x64.exe', '', '', SW_SHOW, ewNoWait, ErrorCode);
      end;
    end;

    if not TesseractInstalled() then
    begin
      if MsgBox(
        'OCR Master requires Tesseract OCR to read bank statements.' + #13#10 + #13#10 +
        'Tesseract is NOT currently installed on this machine.' + #13#10 + #13#10 +
        'Would you like to open the Tesseract download page now?' + #13#10 +
        '(Download the "tesseract-ocr-w64-setup-*.exe" installer)',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        ShellExec('open', 'https://github.com/UB-Mannheim/tesseract/wiki', '', '', SW_SHOW, ewNoWait, ErrorCode);
      end;
    end;
  end;
end;
