; Inno Setup script para empaquetar la app desktop_app.exe
; Uso:
;   1) Genera el ejecutable:
;        pyinstaller --onefile --noconsole --name PrestamosBibliotecaCSF --icon assets\prestamos_csf.ico desktop_app.py
;   2) Compila este script desde Inno Setup Compiler.

#define MyAppName "PrestamosBibliotecaCSF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Prestamos Biblioteca"
#define MyAppExeName "PrestamosBibliotecaCSF.exe"
#define MyAppIcon "assets\prestamos_csfv2.ico"
#define MyAppId "{{8C2D95E7-90B2-4E29-86D4-C387C308C4A7}"

#ifnexist ".env"
  #error "Falta el archivo .env en la raíz del proyecto. Debes crearlo antes de compilar el instalador."
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=prestamos_biblioteca_installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear ícono en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
; Ejecutable principal generado por PyInstaller
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppIcon}"; DestDir: "{app}"; Flags: ignoreversion

; Archivos del proyecto Django requeridos por desktop_app.exe (busca manage.py en {app})
Source: "manage.py"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env"; DestDir: "{app}"; Flags: ignoreversion

; Código de apps y proyecto
Source: "prestamos_biblioteca\*"; DestDir: "{app}\prestamos_biblioteca"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "librosApp\*"; DestDir: "{app}\librosApp"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "prestamoApp\*"; DestDir: "{app}\prestamoApp"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "usuarioApp\*"; DestDir: "{app}\usuarioApp"; Flags: ignoreversion recursesubdirs createallsubdirs

; Templates y estáticos
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs

#ifexist "static\*"
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Dirs]
Name: "{app}\templates"
Name: "{app}\static"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\prestamos_csfv2.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\prestamos_csfv2.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent