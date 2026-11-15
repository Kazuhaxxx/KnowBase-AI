# Windows 11 Enterprise Support & Recovery Procedures

**Document ID:** KB-WIN-004  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Employee  

## 1. Windows Update Stuck or Failing (Error 0x80070005 / 0x80240034)
Error `0x80070005` indicates an access denied permission fault or locked update component, while `0x80240034` indicates an interrupted download.
1. Ensure at least **15 GB of free disk space** is available on drive `C:`.
2. Connect the laptop to AC power and disconnect from NovaPulse VPN if large feature updates are timing out.
3. Open **Settings > System > Troubleshoot > Other troubleshooters** and run the **Windows Update** troubleshooter.
4. If system files may be corrupted, open **Terminal (Administrator)** and run System File Checker followed by DISM:
   ```cmd
   DISM /Online /Cleanup-Image /RestoreHealth
   sfc /scannow
   ```
5. Reboot the workstation and re-check **Settings > Windows Update**.

## 2. High CPU or Slow Performance Diagnostics
1. Press `Ctrl + Shift + Esc` to open **Task Manager** and inspect **CPU**, **Memory**, and **Disk** columns.
2. Check **Uptime** under **Performance > CPU**. If uptime exceeds **14 days**, perform a full **Restart** (do not use Shut Down, as Fast Startup preserves kernel state).
3. Close unused browser tabs or memory-heavy Electron applications.
4. **Important:** Never terminate `MsMpEng.exe` (Microsoft Defender) or `IntuneManagementExtension` services; if Defender scans cause sustained >80% CPU for more than 30 minutes, contact the IT Service Desk.

## 3. Blue Screen of Death (BSOD) Handling
1. Note the exact **Stop Code** shown on screen (e.g., `CRITICAL_PROCESS_DIED`, `DRIVER_IRQL_NOT_LESS_OR_EQUAL`).
2. After automatic reboot, disconnect newly attached third-party USB docks or adapters to test stability.
3. Open **Company Portal** or **Dell Command | Update / Lenovo Vantage** to install approved BIOS and chipset driver updates.
4. If two or more BSOD events occur within 24 hours, log a Priority-2 IT ticket and mention the stop code and timestamp so IT can inspect `C:\Windows\Minidump`.

