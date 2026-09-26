; OpenClass-Box 安装包脚本（Inno Setup 6）
; 源：dist_build/OpenClass-Box（pack.py 生成的绿色版）
; 生成：installer/OpenClass-Box_Setup.exe（被 .gitignore 忽略，不入库）

[Setup]
AppName=OpenClass-Box
AppVersion=0.1.3 Beta
AppPublisher=HMUG12
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
; 安装向导第一步展示的用户许可与免责协议（需勾选"我接受"才能继续）
LicenseFile=license.txt
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
; 签名信任证书（随包携带：装到其他机器时导入后不再提示「未知发布者」）
Source: "dist_build/OpenClass-Box/OpenClass-Box.cer"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; WebView2 运行时安装器（界面渲染依赖，随包携带，目标机缺失时自动安装）
Source: "installer\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
; A 端＝服务端（管理端，启动即拉起管理服务）；B 端＝本体（被管理端）
Name: "{group}\OpenClass-Box（A 端·服务端）"; Filename: "{app}\OpenClass-Box.exe"; Parameters: "--role=a"
Name: "{group}\OpenClass-Box（B 端·本体）"; Filename: "{app}\OpenClass-Box.exe"; Parameters: "--role=b"
Name: "{group}\OpenClass-Box（默认）"; Filename: "{app}\OpenClass-Box.exe"
Name: "{autodesktop}\OpenClass-Box（A 端）"; Filename: "{app}\OpenClass-Box.exe"; Parameters: "--role=a"; Tasks: desktopicon
Name: "{autodesktop}\OpenClass-Box（B 端）"; Filename: "{app}\OpenClass-Box.exe"; Parameters: "--role=b"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "额外任务:"
Name: "shellmenu"; Description: "把 OpenClass-Box 加入右键菜单与""打开方式""（文件将由工具箱内对应工具打开）"; GroupDescription: "系统集成:"
Name: "trustcert"; Description: "在本机信任 OpenClass-Box 签名证书（消除""未知发布者""安全提示）"; GroupDescription: "系统集成:"

[Registry]
; ── 右键菜单与「打开方式」集成 ──
; HKA 会按安装权限自动落到 HKCR 或 HKCU\Software\Classes，无需管理员
; 所有文件的右键菜单：用 OpenClass-Box 打开（由工具箱内对应工具处理该文件）
Root: HKA; Subkey: "*\shell\OpenClassBox"; ValueType: string; ValueName: ""; ValueData: "用 OpenClass-Box 打开"; Flags: uninsdeletekey; Tasks: shellmenu
Root: HKA; Subkey: "*\shell\OpenClassBox"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\openclass.ico"; Tasks: shellmenu
Root: HKA; Subkey: "*\shell\OpenClassBox\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OpenClass-Box.exe"" ""%1"""; Tasks: shellmenu

; 注册为「打开方式」列表中的可选程序
Root: HKA; Subkey: "Applications\OpenClass-Box.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OpenClass-Box.exe"" ""%1"""; Flags: uninsdeletekey; Tasks: shellmenu
Root: HKA; Subkey: "Applications\OpenClass-Box.exe\shell\open\command"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "OpenClass-Box"; Tasks: shellmenu
Root: HKA; Subkey: "*\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: "OpenClassBox.Document"; ValueType: string; ValueName: ""; ValueData: "OpenClass-Box 文档"; Flags: uninsdeletekey; Tasks: shellmenu
Root: HKA; Subkey: "OpenClassBox.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\openclass.ico"; Tasks: shellmenu
Root: HKA; Subkey: "OpenClassBox.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OpenClass-Box.exe"" ""%1"""; Tasks: shellmenu

; 常见类型也加入「打开方式」候选（实际由工具箱内对应工具打开）
Root: HKA; Subkey: ".zip\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".7z\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".rar\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".pdf\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".docx\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".xlsx\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".pptx\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".mp4\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".mkv\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu
Root: HKA; Subkey: ".mp3\OpenWithProgids"; ValueType: string; ValueName: "OpenClassBox.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: shellmenu

[Run]
; 目标机缺 WebView2 运行时（界面显示不出来的根因）时，自动静默安装
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "正在安装界面运行组件 WebView2…"; Check: NeedsWebView2
; 把签名证书导入当前用户的受信任根（仅勾选了该任务且证书存在时执行）
Filename: "{sys}\certutil.exe"; Parameters: "-user -addstore -f Root ""{app}\OpenClass-Box.cer"""; StatusMsg: "正在信任签名证书…"; Flags: runhidden; Check: TrustCertWanted
Filename: "{app}\OpenClass-Box.exe"; Description: "安装完成后启动 OpenClass-Box"; Flags: nowait postinstall

[Code]
function TrustCertWanted(): Boolean;
begin
  // 勾选了「信任签名证书」且证书文件确实随包携带时才执行
  Result :=
    WizardIsTaskSelected('trustcert') and
    FileExists(ExpandConstant('{app}\OpenClass-Box.cer'));
end;

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
