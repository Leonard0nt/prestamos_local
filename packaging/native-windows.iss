[Setup]
AppId={{7D68E6A8-AFCB-4AE1-87DF-69A23B8A5E30}
AppName=Préstamos Biblioteca CSF Nativo
AppVersion=0.2.0
DefaultDirName={localappdata}\Programs\PrestamosBibliotecaCSF-Nativo
PrivilegesRequired=lowest
UsePreviousAppDir=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer_output
OutputBaseFilename=prestamos-biblioteca-nativo-setup
Compression=lzma2
SolidCompression=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\PrestamosBibliotecaCSF-Nativo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "native.env.example"; DestDir: "{localappdata}\prestamos-biblioteca"; Flags: onlyifdoesntexist

[Icons]
Name: "{autoprograms}\Préstamos Biblioteca CSF Nativo"; Filename: "{app}\PrestamosBibliotecaCSF-Nativo.exe"
