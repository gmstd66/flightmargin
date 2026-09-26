; Prevent a raw file-write failure when the PyInstaller sidecar is still active.
; The user remains in control: this hook never terminates a process.
!macro NSIS_HOOK_PREINSTALL
  cqm_check_backend:
    !if "${INSTALLMODE}" == "currentUser"
      nsis_tauri_utils::FindProcessCurrentUser "codex-quota-backend.exe"
    !else
      nsis_tauri_utils::FindProcess "codex-quota-backend.exe"
    !endif
    Pop $R0
    ${If} $R0 = 0
      MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION \
        "Codex Quota Monitor is still running.$\n$\nFully Quit it from the system tray, then click Retry." \
        IDRETRY cqm_check_backend IDCANCEL cqm_cancel_install
    ${EndIf}
    Goto cqm_backend_stopped

  cqm_cancel_install:
    Quit

  cqm_backend_stopped:
!macroend
