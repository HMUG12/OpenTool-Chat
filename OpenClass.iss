; OpenClass-Box 安装包脚本（Inno Setup 6）
; 源：dist_build/OpenClass-Box（pack.py 生成的绿色版）
; 生成：installer/OpenClass-Box_Setup.exe（被 .gitignore 忽略，不入库）

[Setup]
AppName=OpenClass-Box
AppVersion=0.1.2
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
