; OpenClass-Box 安装包脚本（Inno Setup 6）
; 源：dist_build/OpenClass-Box（pack.py 生成的绿色版）
; 生成：installer/OpenClass-Box_Setup.exe（被 .gitignore 忽略，不入库）

[Setup]
AppName=OpenClass-Box
AppVersion=0.1.2 Beta
AppPublisher=OpenClass-Box
AppComments=开源实用工具箱
DefaultDirName={autopf}\OpenClass-Box
DefaultGroupName=OpenClass-Box
OutputDir=installer
OutputBaseFilename=OpenClass-Box_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=openclass.ico
PrivilegesRequired=lowest
UninstallDisplayName=OpenClass-Box
CreateUninstallRegKey=yes
; 中文向导（Inno Setup 6 自带 Simplified Chinese 语言包）
LanguageDetectionMethod=uilanguage
ShowLanguageDialog=auto

[Languages]
Name: "chinese"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist_build/OpenClass-Box/*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OpenClass-Box"; Filename: "{app}\OpenClass-Box.exe"
Name: "{autodesktop}\OpenClass-Box"; Filename: "{app}\OpenClass-Box.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "额外任务:"

[Run]
Filename: "{app}\OpenClass-Box.exe"; Description: "安装完成后启动 OpenClass-Box"; Flags: nowait postinstall

; 其他设备「界面显示不出来」多因缺少 WebView2 运行时（pywebview 依赖它渲染），
; 这里做安装前检测并给出明确提示。
[Code]
function InitializeSetup(): Boolean;
var
  Found: Boolean;
begin
  Found :=
    DirExists(ExpandConstant('{localappdata}\Microsoft\EdgeWebView')) or
    DirExists(ExpandConstant('{pf32}\Microsoft\EdgeWebView\Application')) or
    DirExists(ExpandConstant('{pf64}\Microsoft\EdgeWebView\Application'));
  if not Found then
    MsgBox('未检测到 Microsoft Edge WebView2 运行时。' + #13#10 +
           '程序界面依赖它来渲染；若启动后界面空白/不显示，请先安装 WebView2 运行时。',
           mbInformation, MB_OK);
  Result := True;
end;
