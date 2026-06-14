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
; App binaries go to Program Files\OCR Master
DefaultDirName={autopf}\OCR Master
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=OCRMasterSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
; Installer runs as admin but intentionally writes config to user's AppData
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
; AppData dirs (db, templates, config)
Name: "{userappdata}\{#UserDataName}"
Name: "{userappdata}\{#UserDataName}\templates"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; SaiminBank example template — copy to user AppData templates folder (skip if user already has it)
Source: "..\templates\saiminbank.json"; DestDir: "{userappdata}\{#UserDataName}\templates"; Flags: ignoreversion onlyifdoesntexist
; SaiminBank example image — stage in app folder so Pascal can copy it to the user-chosen data dir
Source: "..\input_files\Examples\SaiminBank.png"; DestDir: "{app}\_examples"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";   Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]

var
  TessPage:    TInputOptionWizardPage;
  DataDirPage: TInputDirWizardPage;
  TessAlreadyInstalled: Boolean;

// ── Existing install detection ────────────────────────────────────────────────

function InitializeSetup(): Boolean;
var
  UninstStr: String;
  ResultCode: Integer;
  Choice: Integer;
begin
  Result := True;

  // Check for existing installation via Inno Setup registry key
  if RegQueryStringValue(HKLM,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1',
      'UninstallString', UninstStr) or
     RegQueryStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1',
      'UninstallString', UninstStr) then
  begin
    Choice := MsgBox(
      'OCR Master is already installed on this machine.' + #13#10 + #13#10 +
      'What would you like to do?' + #13#10 + #13#10 +
      '  YES  — Uninstall the existing version first, then exit' + #13#10 +
      '  NO   — Upgrade / reinstall over the existing version',
      mbConfirmation, MB_YESNO);

    if Choice = IDYES then
    begin
      MsgBox(
        'The uninstaller will now run.' + #13#10 +
        'After it finishes, re-run this installer to install a fresh copy.',
        mbInformation, MB_OK);
      Exec(RemoveQuotes(UninstStr), '/NORESTART', '', SW_SHOW,
           ewWaitUntilTerminated, ResultCode);
      Result := False; // exit setup after uninstall
    end;
    // IDNO: fall through and let the installer upgrade in place
  end;
end;

// ── Dependency checks ─────────────────────────────────────────────────────────

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

// ── Write config.json with all paths ─────────────────────────────────────────

procedure WriteFullConfig(TessExe: String; DataDir: String);
var
  ConfigPath, AppDataOCR: String;
  EscTess, EscData, EscApp: String;
  Lines: TArrayOfString;
begin
  AppDataOCR := ExpandConstant('{userappdata}\{#UserDataName}');

  EscApp  := AppDataOCR; StringChange(EscApp,  '\', '\\');
  EscTess := TessExe;    StringChange(EscTess, '\', '\\');
  EscData := DataDir;    StringChange(EscData, '\', '\\');

  ConfigPath := AppDataOCR + '\config.json';

  SetArrayLength(Lines, 1);
  Lines[0] :=
    '{' + #13#10 +
    '  "tesseract_path":    "' + EscTess + '",' + #13#10 +
    '  "db_path":           "' + EscApp + '\\ocr_master.db",' + #13#10 +
    '  "templates_dir":     "' + EscApp + '\\templates",' + #13#10 +
    '  "input_dir":         "' + EscData + '\\input_files",' + #13#10 +
    '  "output_dir":        "' + EscData + '\\output",' + #13#10 +
    '  "batch_import_dir":  "' + EscData + '\\batch_import",' + #13#10 +
    '  "batch_complete_dir":"' + EscData + '\\batch_complete"' + #13#10 +
    '}';

  SaveStringsToFile(ConfigPath, Lines, False);
end;

// ── Tesseract auto-install ────────────────────────────────────────────────────

procedure InstallTesseractAuto();
var
  ResultCode: Integer;
begin
  MsgBox(
    'Tesseract will now be installed automatically.' + #13#10 + #13#10 +
    'A progress window will appear. Please wait for it to finish.',
    mbInformation, MB_OK);

  Exec(
    'powershell.exe',
    '-ExecutionPolicy Bypass -WindowStyle Normal -Command ' +
    '"winget install --id UB-Mannheim.TesseractOCR --silent ' +
    '--accept-package-agreements --accept-source-agreements"',
    '', SW_SHOW, ewWaitUntilTerminated, ResultCode);

  if not FileExists('C:\Program Files\Tesseract-OCR\tesseract.exe') then
  begin
    MsgBox(
      'Automatic installation did not complete.' + #13#10 +
      'The Tesseract download page will open in your browser.' + #13#10 + #13#10 +
      'Download: tesseract-ocr-w64-setup-*.exe' + #13#10 +
      'OCR Master will work once Tesseract is installed.',
      mbError, MB_OK);
    ShellExec('open', 'https://github.com/UB-Mannheim/tesseract/wiki',
              '', '', SW_SHOW, ewNoWait, ResultCode);
  end;
end;

// ── Wizard setup ──────────────────────────────────────────────────────────────

procedure InitializeWizard();
var
  AfterID: Integer;
begin
  TessAlreadyInstalled := TesseractInstalled();

  AfterID := wpSelectDir;

  // Tesseract page (only when not installed)
  if not TessAlreadyInstalled then
  begin
    TessPage := CreateInputOptionPage(
      AfterID,
      'Tesseract OCR Engine',
      'OCR Master requires Tesseract to read bank statements.',
      'Tesseract is not installed on this machine. How would you like to install it?',
      True, False
    );
    TessPage.Add('Install Tesseract automatically  (recommended — needs internet)');
    TessPage.Add('I will install Tesseract manually after setup');
    TessPage.SelectedValueIndex := 0;
    AfterID := TessPage.ID;
  end;

  // Data folder page (always shown)
  DataDirPage := CreateInputDirPage(
    AfterID,
    'User Data Location',
    'Where should OCR Master store your files?',
    'Statement imports, batch jobs, and CSV exports will be saved here.' + #13#10 +
    'The database and templates are always stored in AppData (not changed here).' + #13#10 + #13#10 +
    'You can change any path later in the app under Settings.',
    False, ''
  );
  DataDirPage.Add('Data folder (input, batch, output):');
  DataDirPage.Values[0] := ExpandConstant('{userdocs}\OCR Master');
end;

// ── Post-install ──────────────────────────────────────────────────────────────

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
  TessExe, DataDir: String;
begin
  if CurStep <> ssPostInstall then Exit;

  TessExe := 'C:\Program Files\Tesseract-OCR\tesseract.exe';
  DataDir  := DataDirPage.Values[0];

  // ── Tesseract ──
  if not TessAlreadyInstalled then
  begin
    if Assigned(TessPage) and (TessPage.SelectedValueIndex = 0) then
      InstallTesseractAuto()
    else
    begin
      ShellExec('open', 'https://github.com/UB-Mannheim/tesseract/wiki',
                '', '', SW_SHOW, ewNoWait, ErrorCode);
      MsgBox(
        'The Tesseract download page has been opened in your browser.' + #13#10 + #13#10 +
        'Download and run:  tesseract-ocr-w64-setup-*.exe' + #13#10 + #13#10 +
        'OCR Master will detect Tesseract automatically once it is installed.',
        mbInformation, MB_OK);
    end;
  end;

  // ── Create data directories ──
  ForceDirectories(DataDir + '\input_files');
  ForceDirectories(DataDir + '\output');
  ForceDirectories(DataDir + '\batch_import');
  ForceDirectories(DataDir + '\batch_complete');

  // ── Copy SaiminBank example image to input folder (skip if already there) ──
  if not FileExists(DataDir + '\input_files\SaiminBank.png') then
    FileCopy(
      ExpandConstant('{app}') + '\_examples\SaiminBank.png',
      DataDir + '\input_files\SaiminBank.png',
      False);

  // ── Write config.json ──
  WriteFullConfig(TessExe, DataDir);

  // ── Visual C++ Redistributable ──
  if not VCRedistInstalled() then
  begin
    if MsgBox(
      'OCR Master also requires the Microsoft Visual C++ Redistributable (2022, x64).' + #13#10 +
      'It is NOT currently installed on this machine.' + #13#10 + #13#10 +
      'Without it the application may fail to start.' + #13#10 + #13#10 +
      'Would you like to download it now?',
      mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://aka.ms/vs/17/release/vc_redist.x64.exe',
                '', '', SW_SHOW, ewNoWait, ErrorCode);
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
