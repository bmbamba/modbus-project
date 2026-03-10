; client_installer.iss
; Modbus Client Installer — Inno Setup 6

[Setup]
AppId={{B2C3D4E5-F6A7-8901-BCDE-F12345678901}
AppName=Modbus Client
AppVersion=1.0.0
AppPublisher=Your Company Name
AppPublisherURL=https://yourwebsite.com
DefaultDirName={autopf}\Modbus Client
DefaultGroupName=Modbus Client
OutputDir=installer_output
OutputBaseFilename=ModbusClient_Setup_v1.0.0
SetupIconFile=client_icon.ico
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
LicenseFile=LICENSE.txt
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ModbusClient\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Modbus Client"; Filename: "{app}\ModbusClient.exe"
Name: "{group}\Uninstall Modbus Client"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Modbus Client"; Filename: "{app}\ModbusClient.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ModbusClient.exe"; Description: "Launch Modbus Client"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM ModbusClient.exe"; Flags: runhidden

[Code]
var
  AcceptPage: TWizardPage;
  AcceptCheck: TCheckBox;
  MemoText: TMemo;

procedure InitializeWizard();
begin
  AcceptPage := CreateCustomPage(wpLicense, 'Terms and Conditions', 'You must accept the terms to continue.');

  MemoText := TMemo.Create(AcceptPage);
  MemoText.Parent := AcceptPage.Surface;
  MemoText.Left := 0;
  MemoText.Top := 0;
  MemoText.Width := AcceptPage.SurfaceWidth;
  MemoText.Height := AcceptPage.SurfaceHeight - 30;
  MemoText.ScrollBars := ssVertical;
  MemoText.ReadOnly := True;
  MemoText.WordWrap := True;
  MemoText.Lines.Add('MODBUS CLIENT - END USER LICENSE AGREEMENT');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('By installing this software you agree to the following terms:');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('1. LICENSE GRANT');
  MemoText.Lines.Add('You are granted a non-exclusive license to install and use this software on devices you own or control.');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('2. RESTRICTIONS');
  MemoText.Lines.Add('You may not redistribute, sell, sublicense, or reverse-engineer this software without written permission.');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('3. NO WARRANTY');
  MemoText.Lines.Add('This software is provided "as is" without warranty of any kind. The authors are not liable for any damages.');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('4. NETWORK USE');
  MemoText.Lines.Add('This application connects to a Modbus TCP server. You are responsible for ensuring correct configuration.');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('5. DATA');
  MemoText.Lines.Add('This software stores setpoint configuration locally. No data is transmitted to any external server.');
  MemoText.Lines.Add('');
  MemoText.Lines.Add('6. TERMINATION');
  MemoText.Lines.Add('This license terminates automatically if you fail to comply with its terms.');

  AcceptCheck := TCheckBox.Create(AcceptPage);
  AcceptCheck.Parent := AcceptPage.Surface;
  AcceptCheck.Left := 0;
  AcceptCheck.Top := MemoText.Height + 8;
  AcceptCheck.Width := AcceptPage.SurfaceWidth;
  AcceptCheck.Caption := 'I accept the Terms and Conditions';
  AcceptCheck.Checked := False;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = AcceptPage.ID then
  begin
    if not AcceptCheck.Checked then
    begin
      MsgBox('You must accept the Terms and Conditions to continue.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
