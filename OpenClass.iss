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
; 内嵌 WebView2 运行时后包体较大（~700MB），normal 级别平衡体积与编译时间
Compression=lzma2/normal
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
; WebView2 运行时安装器（界面渲染依赖，随包携带，目标机缺失时自动安装）
Source: "installer\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\OpenClass-Box"; Filename: "{app}\OpenClass-Box.exe"
Name: "{autodesktop}\OpenClass-Box"; Filename: "{app}\OpenClass-Box.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "额外任务:"

[Run]
; 目标机缺 WebView2 运行时（界面显示不出来的根因）时，自动静默安装
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "正在安装界面运行组件 WebView2…"; Check: NeedsWebView2
Filename: "{app}\OpenClass-Box.exe"; Description: "安装完成后启动 OpenClass-Box"; Flags: nowait postinstall

[Code]
function NeedsWebView2(): Boolean;
begin
  // 已随包携带固定版本运行时（{app}\WebView2Runtime）时无需再装系统运行时的
  Result := not (
    FileExists(ExpandConstant('{app}\WebView2Runtime\msedgewebview2.exe')) or
    DirExists(ExpandConstant('{localappdata}\Microsoft\EdgeWebView\Application')) or
    DirExists(ExpandConstant('{pf32}\Microsoft\EdgeWebView\Application')) or
    DirExists(ExpandConstant('{pf64}\Microsoft\EdgeWebView\Application'))
  );
end;
