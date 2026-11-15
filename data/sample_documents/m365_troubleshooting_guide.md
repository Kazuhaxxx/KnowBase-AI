# Microsoft 365 & Teams Troubleshooting Guide

**Document ID:** KB-M365-001  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Employee  

## 1. Microsoft Teams Audio, Microphone, or Camera Not Working
If Microsoft Teams fails to detect your headset microphone or webcam during a meeting:
1. Click the three-dot menu (**...**) next to your profile picture in Teams and select **Settings > Devices**.
2. Verify that **Audio devices** is set to your physical headset (e.g., *Jabra Evolve2 65*) rather than *Communications - Virtual Audio*.
3. Click **Make a test call** to verify microphone input levels and speaker playback.
4. On Windows 11, open **Settings > Privacy & security > Microphone** and confirm **Let desktop apps access your microphone** is enabled.
5. If the issue persists after a Windows update, sign out of Teams completely, right-click the Teams icon in the system tray, select **Quit**, and relaunch Teams.

## 2. OneDrive Sync Stuck on "Processing Changes" (Error 0x8004de40)
Error `0x8004de40` indicates OneDrive cannot reach Microsoft 365 cloud endpoints or has a stale authentication token.
1. Confirm your internet connection is active and disconnect briefly from NovaPulse VPN if split-tunneling is congested.
2. Check whether the system clock and time zone are set to **Set time automatically** under Windows **Date & time**.
3. Right-click the **OneDrive cloud icon** in the taskbar and select **Pause syncing > 2 hours**, wait 10 seconds, then click **Resume syncing**.
4. If syncing remains stuck, press `Win + R`, run:
   ```cmd
   %localappdata%\Microsoft\OneDrive\onedrive.exe /reset
   ```
   **Important:** Do not manually delete local OneDrive folders before running `/reset`, as unsynced edits could be lost.
5. Wait up to 3 minutes for the OneDrive icon to reappear; if it does not, launch **OneDrive** from the Start Menu and sign back in with your `@novatech-demo.internal` credentials.

## 3. SharePoint & Teams "Access Denied" on Shared Channels
1. Verify you are signed into Edge or Chrome with your primary corporate profile (`@novatech-demo.internal`), not a personal Microsoft account.
2. Clear cached Microsoft identity cookies for `login.microsoftonline.com` and `novatech.sharepoint.com`.
3. Request access directly from the channel owner via the **Request Access** button, or submit an **M365 Group Membership** ticket in the NovaTech Service Portal.

