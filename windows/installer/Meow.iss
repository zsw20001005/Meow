#ifndef PayloadDir
  #error PayloadDir must point to a clean publish folder
#endif
#ifndef OutputDir
  #define OutputDir "..\..\build\installers"
#endif
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{163D833B-4C53-440A-A130-4D1362F7531F}
AppName=Meow · 张噜噜
AppVersion={#AppVersion}
AppVerName=Meow · 张噜噜 {#AppVersion}
DefaultDirName={localappdata}\Programs\Meow
DefaultGroupName=Meow · 张噜噜
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#OutputDir}
OutputBaseFilename=Meow-{#AppVersion}-Windows-x64-Setup
SetupIconFile={#PayloadDir}\Meow.ico
UninstallDisplayIcon={app}\Meow.ico
WizardStyle=modern
Compression=lzma2/fast
SolidCompression=yes
AppMutex=Local\Meow.Windows
CloseApplications=no
RestartApplications=no
SetupLogging=yes
InfoBeforeFile=安装说明.txt

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "完整安装（包含轻量本地模型）"
Name: "compact"; Description: "精简安装（使用云端 API，不安装本地模型）"
Name: "custom"; Description: "自定义安装"; Flags: iscustom

[Components]
Name: "core"; Description: "桌面角色、全部动画、聊天与信箱"; Types: full compact custom; Flags: fixed
#if DirExists(PayloadDir + "\local-engine")
Name: "localmodel"; Description: "轻量本地模型（Qwen2.5 0.5B，约 520 MB）"; Types: full
#endif

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Excludes: "local-engine\*"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
#if DirExists(PayloadDir + "\local-engine")
Source: "{#PayloadDir}\local-engine\*"; DestDir: "{app}\local-engine"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: localmodel
#endif
Source: "{#VCRedist}"; Flags: dontcopy

[Icons]
Name: "{group}\Meow · 张噜噜"; Filename: "{app}\Meow.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Meow.ico"
Name: "{autodesktop}\Meow · 张噜噜"; Filename: "{app}\Meow.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Meow.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Meow.exe"; Description: "启动张噜噜"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsVCRuntime: Boolean;
var
  Installed, Major, Minor: Cardinal;
begin
  Result := not (RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) and
                 RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Major', Major) and
                 RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Minor', Minor) and
                 (Installed = 1) and ((Major > 14) or ((Major = 14) and (Minor >= 50))));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
begin
  Result := '';
  if NeedsVCRuntime then
  begin
    ExtractTemporaryFile('vc_redist.x64.exe');
    if not ShellExec('runas', ExpandConstant('{tmp}\vc_redist.x64.exe'), '/install /passive /norestart', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ExitCode) then
      Result := '安装 Microsoft Visual C++ 运行库未完成，请允许系统权限提示后重试。'
    else if ExitCode = 3010 then NeedsRestart := True
    else if (ExitCode <> 0) and (ExitCode <> 1638) then
      Result := 'Microsoft Visual C++ 运行库安装失败，退出代码：' + IntToStr(ExitCode);
  end;
end;

// User data lives outside {app}. No UninstallDelete rule touches it.
