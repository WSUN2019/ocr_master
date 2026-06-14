; Inno Setup script for OCR Master
; Compile with: iscc build\installer.iss   or open in Inno Setup Compiler and press F9
;
; Prerequisites:
;   1. Run build\build_windows.ps1 first to produce dist\OCRMaster\
;   2. Install Inno Setup from https://jrsoftware.org/isinfo.php
;
; Output: build\Output\OCRMasterSetup.exe

#define AppName      "OCR Master"
#define AppVersion   "1.2.0"
#define AppPublisher "WSUN2019"
#define AppURL       "https://github.com/WSUN2019/ocr_master"
#define AppExeName   "OCRMaster.exe"
#define SourceDir    "..\dist\OCRMaster"
#define UserDataName "OCR Master"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
; Install app binaries to Program Files\OCR Master
DefaultDirName={autopf}\OCR Master
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=OCRMasterSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 64-bit Windows required (matches Tesseract w64 build)
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
; Installer runs as admin but intentionally writes config to user's AppData
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
; Create user data folders in AppData (writable without admin rights)
Name: "{userappdata}\{#UserDataName}"
Name: "{userappdata}\{#UserDataName}\templates"
Name: "{userappdata}\{#UserDataName}\input_files"
Name: "{userappdata}\{#UserDataName}\output"

[Files]
; Main application bundle (output from PyInstaller)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";   Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]

var
  TessPage: TInputOptionWizardPage;
  TessAlreadyInstalled: Boolean;

// ── Dependency checks ────────────────────────────────────────────────────────

function TesseractInstalled(): Boolean;
var
  Path: String;
begin
  Result :=
    RegQueryStringValue(HKLM,   'SOFTWARE\Tesseract-OCR', 'InstallDir', Path) or
    RegQueryStringValue(HKLM32, 'SOFTWARE\Tesseract-OCR', 'InstallDir', Path) or
    FileExists('C:\Program Files\Tesseract-OCR\tesseract.exe');
end;

function VCRedistInstalled(): Boolean;
var
  Ver: String;
begin
  Result :=
    RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Ver) or
    RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Ver);
end;

// ── Write config.json to user AppData ────────────────────────────────────────

procedure WriteConfig(TessPath: String);
var
  ConfigPath: String;
  Lines: TArrayOfString;
  EscapedPath: String;
begin
  ConfigPath := ExpandConstant('{userappdata}\{#UserDataName}\config.json');
  EscapedPath := TessPath;
  StringChange(EscapedPath, '\', '\\');
  SetArrayLength(Lines, 1);
  Lines[0] := '{"tesseract_path": "' + EscapedPath + '"}';
  SaveStringsToFile(ConfigPath, Lines, False);
end;

// ── Auto-install Tesseract via winget ────────────────────────────────────────

procedure InstallTesseractAuto();
var
  ResultCode: Integer;
  TessExe: String;
begin
  MsgBox(
    'Tesseract will now be installed automatically.' + #13#10 + #13#10 +
    'A progress window will appear. Please wait for it to complete before' + #13#10 +
    'clicking Finish on the next screen.',
    mbInformation, MB_OK);

  // Use PowerShell to invoke winget (handles PATH lookup reliably)
  Exec(
    'powershell.exe',
    '-ExecutionPolicy Bypass -WindowStyle Normal -Command ' +
    '"winget install --id UB-Mannheim.TesseractOCR --silent ' +
    '--accept-package-agreements --accept-source-agreements"',
    '', SW_SHOW, ewWaitUntilTerminated, ResultCode);

  TessExe := 'C:\Program Files\Tesseract-OCR\tesseract.exe';
  if FileExists(TessExe) then
  begin
    WriteConfig(TessExe);
    MsgBox('Tesseract installed successfully.', mbInformation, MB_OK);
  end else
  begin
    MsgBox(
      'Automatic installation did not complete.' + #13#10 + #13#10 +
      'This can happen if winget is not available on your Windows version.' + #13#10 + #13#10 +
      'The Tesseract download page will open in your browser.' + #13#10 +
      'Download: tesseract-ocr-w64-setup-*.exe' + #13#10 + #13#10 +
      'OCR Master will work once you install Tesseract.',
      mbError, MB_OK);
    ShellExec('open', 'https://github.com/UB-Mannheim/tesseract/wiki', '', '', SW_SHOW, ewNoWait, ResultCode);
  end;
end;

// ── Wizard setup ─────────────────────────────────────────────────────────────

procedure InitializeWizard();
begin
  TessAlreadyInstalled := TesseractInstalled();

  if not TessAlreadyInstalled then
  begin
    // Insert Tesseract page after directory selection
    TessPage := CreateInputOptionPage(
      wpSelectDir,
      'Tesseract OCR Engine',
      'OCR Master requires Tesseract to read bank statements.',
      'Tesseract is not installed on this machine. How would you like to install it?',
      True,   // exclusive (radio buttons, not checkboxes)
      False
    );
    TessPage.Add('Install Tesseract automatically  (recommended — needs internet)');
    TessPage.Add('I will install Tesseract manually after setup');
    TessPage.SelectedValueIndex := 0;
  end;
end;

// ── Post-install actions ─────────────────────────────────────────────────────

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
  TessExe: String;
begin
  if CurStep = ssPostInstall then
  begin
    if TessAlreadyInstalled then
    begin
      // Tesseract already present — write config pointing to it
      TessExe := 'C:\Program Files\Tesseract-OCR\tesseract.exe';
      if FileExists(TessExe) then
        WriteConfig(TessExe);
    end else if Assigned(TessPage) then
    begin
      if TessPage.SelectedValueIndex = 0 then
        InstallTesseractAuto()
      else
      begin
        // Manual: open download page and explain
        ShellExec('open', 'https://github.com/UB-Mannheim/tesseract/wiki', '', '', SW_SHOW, ewNoWait, ErrorCode);
        MsgBox(
          'The Tesseract download page has been opened in your browser.' + #13#10 + #13#10 +
          'Download and run:  tesseract-ocr-w64-setup-*.exe' + #13#10 + #13#10 +
          'OCR Master will detect Tesseract automatically once it is installed.',
          mbInformation, MB_OK);
      end;
    end;

    // Visual C++ Redistributable check (required by Python runtime DLLs)
    if not VCRedistInstalled() then
    begin
      if MsgBox(
        'OCR Master also requires the Microsoft Visual C++ Redistributable (2022, x64).' + #13#10 +
        'It is NOT currently installed on this machine.' + #13#10 + #13#10 +
        'Without it the application may fail to start.' + #13#10 + #13#10 +
        'Would you like to download it now?',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        ShellExec('open', 'https://aka.ms/vs/17/release/vc_redist.x64.exe', '', '', SW_SHOW, ewNoWait, ErrorCode);
      end;
    end;
  end;
end;

// ── Uninstall ─────────────────────────────────────────────────────────────────

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataDir := ExpandConstant('{userappdata}\{#UserDataName}');
    if DirExists(AppDataDir) then
    begin
      if MsgBox(
        'Would you like to delete your OCR Master data?' + #13#10 + #13#10 +
        'This includes saved templates, transaction history, and settings.' + #13#10 +
        'Location: ' + AppDataDir + #13#10 + #13#10 +
        'YES — delete all data permanently' + #13#10 +
        'NO  — keep data (safe for reinstalling later)',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(AppDataDir, True, True, True);
      end;
    end;
  end;
end;
