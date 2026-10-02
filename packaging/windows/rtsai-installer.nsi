; RTS AI - per-user Windows installer (no administrator rights).
;
; Built by packaging/windows/build-release.ps1, which passes:
;   VERSION      release version, e.g. 0.2.0-alpha.1
;   VIVERSION    numeric file version, e.g. 0.2.0.1
;   PAYLOAD      the staged portable build (game, mods, companion\)
;   OUTFILE      the setup .exe to write
;   ICON         the RTS AI .ico
;   LICENSE      COPYING (GPLv3)
;   VOICEPACK    file name of the optional offline voice pack placed next to setup.exe
;   UNINSTALLLIST an .nsh with the Delete/RMDir lines for exactly the files in PAYLOAD
;   UNINSTALLSIGNER (optional) a command that signs the generated uninstaller
;
; AI options (page, or /AI=hosted|local|none for silent installs):
;   hosted  Hosted AI + local voice (default): downloads and SHA-verifies the ~270 MB voice pack.
;   local   Full local AI: downloads and SHA-verifies the ~1.8 GB local model pack.
;   none    No AI: the co-commander stays off until it is turned on in Settings > AI.
; The choice is written to $INSTDIR\rtsai-install.json and applied by the game on first launch.

Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"
!include "FileFunc.nsh"

!ifndef VERSION
  !error "VERSION must be supplied"
!endif
!ifndef PAYLOAD
  !error "PAYLOAD must be supplied"
!endif

!define PRODUCT_NAME "RTS AI"
!define PUBLISHER "The RTS AI authors"
!define REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\RTSAI"
!define LAUNCHER "RTSAI.exe"
!define UNINSTALLER "Uninstall RTS AI.exe"
!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING

Name "${PRODUCT_NAME} ${VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\RTS AI"
InstallDirRegKey HKCU "${REGKEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show
BrandingText "RTS AI ${VERSION}"
ManifestDPIAware true

VIProductVersion "${VIVERSION}"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "${PUBLISHER}"
VIAddVersionKey "FileDescription" "${PRODUCT_NAME} installer"
VIAddVersionKey "LegalCopyright" "GPLv3. Red Alert 2 content is not included."

!ifdef UNINSTALLSIGNER
  !uninstfinalize '${UNINSTALLSIGNER} "%1"' = 0
!endif

Var AIMode
Var AIPage
Var RadioHosted
Var RadioLocal
Var RadioNone

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${LICENSE}"
!insertmacro MUI_PAGE_DIRECTORY
Page custom AIOptionsCreate AIOptionsLeave
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${LAUNCHER}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch RTS AI"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Function .onInit
  StrCpy $AIMode "hosted"
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/AI=" $1
  ${IfNot} ${Errors}
    ${If} $1 == "local"
      StrCpy $AIMode "local"
    ${ElseIf} $1 == "none"
      StrCpy $AIMode "none"
    ${EndIf}
  ${EndIf}
FunctionEnd

Function AIOptionsCreate
  !insertmacro MUI_HEADER_TEXT "AI co-commander" "Choose how the co-commander thinks and speaks. You can change this later in Settings > AI."
  nsDialogs::Create 1018
  Pop $AIPage
  ${If} $AIPage == error
    Abort
  ${EndIf}

  ${NSD_CreateRadioButton} 0 0 100% 12u "Hosted AI + local voice (recommended)"
  Pop $RadioHosted
  ${NSD_CreateLabel} 12u 13u 95% 26u "Thinking runs on rtsai.net (free daily allowance, no account or key). Speech recognition and the voice stay on this PC: downloads about 270 MB now."
  Pop $0

  ${NSD_CreateRadioButton} 0 44u 100% 12u "Full local AI (about 1.8 GB)"
  Pop $RadioLocal
  ${NSD_CreateLabel} 12u 57u 95% 26u "Everything runs on this PC, offline. Downloads about 1.8 GB now; needs 8 GB RAM (16 GB recommended) and a 4-core CPU with AVX2."
  Pop $0

  ${NSD_CreateRadioButton} 0 88u 100% 12u "No AI"
  Pop $RadioNone
  ${NSD_CreateLabel} 12u 101u 95% 18u "Play without the co-commander. Nothing is downloaded; turn it on later in Settings > AI."
  Pop $0

  ${NSD_CreateLabel} 0 124u 100% 26u "Red Alert 2 is not included. On first launch the game imports the copy you own (Steam, EA app/Origin or disc)."
  Pop $0

  ${If} $AIMode == "local"
    ${NSD_Check} $RadioLocal
  ${ElseIf} $AIMode == "none"
    ${NSD_Check} $RadioNone
  ${Else}
    ${NSD_Check} $RadioHosted
  ${EndIf}
  nsDialogs::Show
FunctionEnd

Function AIOptionsLeave
  ${NSD_GetState} $RadioLocal $0
  ${NSD_GetState} $RadioNone $1
  ${If} $0 == ${BST_CHECKED}
    StrCpy $AIMode "local"
  ${ElseIf} $1 == ${BST_CHECKED}
    StrCpy $AIMode "none"
  ${Else}
    StrCpy $AIMode "hosted"
  ${EndIf}
FunctionEnd

Section "RTS AI" SEC_GAME
  SectionIn RO
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*.*"

  ; The game applies this choice once on first launch (OpenRA.Mods.RTSAI CompanionHost).
  ${GetTime} "" "L" $0 $1 $2 $3 $4 $5 $6
  FileOpen $9 "$INSTDIR\rtsai-install.json" w
  FileWrite $9 '{"ai_mode": "$AIMode", "version": "${VERSION}", "stamp": "$2-$1-$0T$4:$5:$6"}$\r$\n'
  FileClose $9

  ${If} $AIMode == "hosted"
    DetailPrint "Downloading and verifying the local voice pack (about 270 MB)..."
    nsExec::ExecToLog '"$INSTDIR\companion\rtsai-companion.exe" pack install --profile voice-only --root "$INSTDIR\companion" --archive "$EXEDIR\${VOICEPACK}"'
    Pop $0
    ${If} $0 != 0
      DetailPrint "The voice pack could not be downloaded now (code $0). The game finishes it on first launch."
      IfSilent +2
      MessageBox MB_ICONINFORMATION "The local voice pack could not be downloaded now. RTS AI will finish the download on first launch; hosted advice and on-screen alerts work meanwhile."
    ${EndIf}
  ${ElseIf} $AIMode == "local"
    DetailPrint "Downloading and verifying the full local AI pack (about 1.8 GB)..."
    nsExec::ExecToLog '"$INSTDIR\companion\rtsai-companion.exe" pack install --profile recommended --root "$INSTDIR\companion"'
    Pop $0
    ${If} $0 != 0
      DetailPrint "The local AI pack could not be downloaded now (code $0). Retry under Settings > AI > Models."
      IfSilent +2
      MessageBox MB_ICONINFORMATION "The local AI pack could not be downloaded now. Retry later under Settings > AI > Models; nothing unverified was installed."
    ${EndIf}
  ${EndIf}

  WriteUninstaller "$INSTDIR\${UNINSTALLER}"
  CreateDirectory "$SMPROGRAMS\RTS AI"
  CreateShortcut "$SMPROGRAMS\RTS AI\RTS AI.lnk" "$INSTDIR\${LAUNCHER}" "" "$INSTDIR\rtsai.ico" 0 SW_SHOWNORMAL "" "Play RTS AI"
  CreateShortcut "$SMPROGRAMS\RTS AI\Uninstall RTS AI.lnk" "$INSTDIR\${UNINSTALLER}" "" "$INSTDIR\rtsai.ico" 0

  ; openra-rtsai-<version>:// join links, per user.
  WriteRegStr HKCU "Software\Classes\openra-rtsai-${VERSION}" "" "URL:Join RTS AI server"
  WriteRegStr HKCU "Software\Classes\openra-rtsai-${VERSION}" "URL Protocol" ""
  WriteRegStr HKCU "Software\Classes\openra-rtsai-${VERSION}\DefaultIcon" "" "$INSTDIR\rtsai.ico,0"
  WriteRegStr HKCU "Software\Classes\openra-rtsai-${VERSION}\Shell\Open\Command" "" '"$INSTDIR\${LAUNCHER}" "Launch.URI=%1"'

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegStr HKCU "${REGKEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "${REGKEY}" "URLInfoAbout" "https://rtsai.net"
  WriteRegStr HKCU "${REGKEY}" "DisplayIcon" "$INSTDIR\rtsai.ico"
  WriteRegStr HKCU "${REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "UninstallString" '"$INSTDIR\${UNINSTALLER}"'
  WriteRegStr HKCU "${REGKEY}" "QuietUninstallString" '"$INSTDIR\${UNINSTALLER}" /S'
  WriteRegDWORD HKCU "${REGKEY}" "EstimatedSize" "$0"
  WriteRegDWORD HKCU "${REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${REGKEY}" "NoRepair" 1
SectionEnd

Section "Desktop shortcut" SEC_DESKTOP
  SetShellVarContext current
  CreateShortcut "$DESKTOP\RTS AI.lnk" "$INSTDIR\${LAUNCHER}" "" "$INSTDIR\rtsai.ico" 0 SW_SHOWNORMAL "" "Play RTS AI"
SectionEnd

LangString DESC_GAME ${LANG_ENGLISH} "The RTS AI mod, the OpenRA engine and the AI co-commander."
LangString DESC_DESKTOP ${LANG_ENGLISH} "Place an RTS AI shortcut on the desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_GAME} $(DESC_GAME)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} $(DESC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetShellVarContext current
  ; Only what setup installed (or the game downloaded into the companion folder) is removed, so a
  ; custom install folder that holds other files is never wiped. Player data lives in the OpenRA
  ; support folder (%APPDATA%\OpenRA by default) and is kept: imported RA2 content, settings,
  ; replays, maps, logs and the co-commander's settings and install token (ai-companion).
  ; Generated by build-release.ps1: one Delete per top-level payload file, one recursive RMDir per
  ; payload folder (companion\ also holds the downloaded voice or local AI pack).
  !include "${UNINSTALLLIST}"
  Delete "$INSTDIR\rtsai-install.json"
  Delete "$INSTDIR\${UNINSTALLER}"
  RMDir "$INSTDIR"

  Delete "$DESKTOP\RTS AI.lnk"
  Delete "$SMPROGRAMS\RTS AI\RTS AI.lnk"
  Delete "$SMPROGRAMS\RTS AI\Uninstall RTS AI.lnk"
  RMDir "$SMPROGRAMS\RTS AI"
  DeleteRegKey HKCU "Software\Classes\openra-rtsai-${VERSION}"
  DeleteRegKey HKCU "${REGKEY}"
SectionEnd

Function un.onUninstSuccess
  ; NSIS runs the uninstaller from a copy in %TEMP%\~nsuN.tmp, which cannot delete itself and,
  ; without administrator rights, cannot be scheduled for deletion at reboot. Remove that folder
  ; a few seconds after this process exits. Only ever the temporary copy's own folder.
  ${If} ${FileExists} "$EXEDIR\Un.exe"
  ${AndIf} "$EXEDIR" != "$INSTDIR"
    ExecShell "open" "$SYSDIR\cmd.exe" '/c ping -n 4 127.0.0.1 >nul & rd /s /q "$EXEDIR"' SW_HIDE
  ${EndIf}
FunctionEnd
