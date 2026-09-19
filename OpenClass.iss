; OpenClass 安装包脚本（Inno Setup 6）
; 源：dist_build/OpenClass（pack.py 生成的绿色版）
; 生成：installer/OpenClass_Setup.exe（被 .gitignore 忽略，不入库）

[Setup]
AppName=OpenClass
AppVersion=0.1.0
AppPublisher=OpenClass
AppComments=开源实用工具箱
DefaultDirName={autopf}\OpenClass
DefaultGroupName=OpenClass
OutputDir=installer
OutputBaseFilename=OpenClass_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=openclass.ico
PrivilegesRequired=lowest
UninstallDisplayName=OpenClass
CreateUninstallRegKey=yes
; 中文向导（Inno Setup 6 自带 Simplified Chinese 语言包）
LanguageDetectionMethod=uilanguage
ShowLanguageDialog=auto

[Languages]
Name: "chinese"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist_build/OpenClass/*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OpenClass"; Filename: "{app}\OpenClass.exe"
Name: "{autodesktop}\OpenClass"; Filename: "{app}\OpenClass.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "额外任务:"

[Run]
Filename: "{app}\OpenClass.exe"; Description: "安装完成后启动 OpenClass"; Flags: nowait postinstall
