#ifndef PayloadDir
  #error PayloadDir is required
#endif
#if PackId == "core"
  #define Identity "{{163D833B-4C53-440A-A130-4D1362F7531F}"
#else
  #define Identity "Meow.Extension." + PackId
#endif

[Setup]
AppId={#Identity}
AppName=Meow · 张噜噜 — {#PackName}
AppVersion={#AppVersion}
DefaultDirName={code:DefaultDirectory}
DefaultGroupName=Meow · 张噜噜
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#OutputDir}
OutputBaseFilename=Meow-{#AppVersion}-{#PackId}-Setup
SetupIconFile={#IconFile}
WizardStyle=modern
#ifdef TestMode
Compression=none
#else
Compression=lzma2/normal
#endif
SolidCompression=yes
CloseApplications=no
RestartApplications=no
SetupLogging=yes
#ifdef TestMode
CreateUninstallRegKey=no
AppMutex=Local\Meow.ModularValidation
#else
AppMutex=Local\Meow.Windows
#endif
UninstallFilesDir={app}\uninstall-{#PackId}
UninstallDisplayIcon={app}\Meow.exe

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

#if PackId == "core"
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
#endif

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#if PackId == "core"
Source: "{#VCRedist}"; Flags: dontcopy
#ifndef TestMode
[Icons]
Name: "{group}\Meow · 张噜噜"; Filename: "{app}\Meow.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Lulu-{#AppVersion}.ico"
Name: "{autodesktop}\Meow · 张噜噜"; Filename: "{app}\Meow.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Lulu-{#AppVersion}.ico"; Tasks: desktopicon
[Run]
Filename: "{app}\Meow.exe"; Description: "启动张噜噜"; Flags: nowait postinstall skipifsilent
#endif
#endif

[Code]
function DefaultDirectory(Param: String): String;
begin
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{163D833B-4C53-440A-A130-4D1362F7531F}_is1', 'InstallLocation', Result) then
    Result := ExpandConstant('{localappdata}\Programs\Meow');
end;

function PackageError: String;
begin
  Result := '';
#if PackId != "core"
  if not FileExists(ExpandConstant('{app}\Meow.exe')) then
    Result := '请先安装基础主包，再选择 Meow.exe 所在的目录。'
  else if GetIniString('Package', 'ContentId', '', ExpandConstant('{app}\package.ini')) <> '{#ContentId}' then
    Result := '此目录的主程序与扩展包不匹配。请先安装配套的基础主包，再安装扩展包。';
#endif
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var Error: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    Error := PackageError;
    if Error <> '' then
    begin
      if not WizardSilent then MsgBox(Error, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
#if PackId == "core"
var Installed, Major, Minor: Cardinal; ExitCode: Integer; Ready: Boolean;
#endif
begin
  Result := PackageError;
  if Result <> '' then Exit;
#if PackId == "core"
  Ready := RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) and
           RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Major', Major) and
           RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Minor', Minor) and
           (Installed = 1) and ((Major > 14) or ((Major = 14) and (Minor >= 50)));
  if not Ready then
  begin
    ExtractTemporaryFile('vc_redist.x64.exe');
    if not ShellExec('runas', ExpandConstant('{tmp}\vc_redist.x64.exe'), '/install /passive /norestart', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ExitCode) then
      Result := '安装 Microsoft Visual C++ 运行库未完成，请允许系统权限提示后重试。'
    else if ExitCode = 3010 then NeedsRestart := True
    else if (ExitCode <> 0) and (ExitCode <> 1638) then Result := 'Microsoft Visual C++ 运行库安装失败：' + IntToStr(ExitCode);
  end;
#endif
end;

// Each pack owns disjoint payload files and its own uninstaller. User data is
// outside {app}; no deletion rule touches profiles, mail, notes or cache.
