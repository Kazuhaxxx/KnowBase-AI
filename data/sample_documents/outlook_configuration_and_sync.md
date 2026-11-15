# Outlook Profile Configuration & OST Sync Repair

**Document ID:** KB-MSG-002  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Employee  

## 1. Initial Outlook Desktop Configuration (Microsoft 365 Exchange Online)
1. Open **Microsoft Outlook** on your corporate Windows 11 or macOS workstation.
2. Enter your corporate email address (`firstname.lastname@novatech-demo.internal`) and click **Connect**.
3. Complete the **Microsoft Authenticator** MFA prompt on your registered mobile device.
4. Uncheck **Set up Outlook Mobile on my phone** unless needed, then click **Done**.
5. Allow 5–15 minutes for the initial **Cached Exchange Mode** mailbox synchronization (default window: 12 months of email).

## 2. Fixing Outlook Stuck on "Updating Inbox" or "Trying to Connect"
1. Check the bottom-right status bar in Outlook. If it displays **Working Offline**, open the **Send / Receive** tab and click **Work Offline** to toggle back online.
2. Test network connectivity to Exchange Online by confirming **Outlook Web Access** (`https://outlook.office.com`) loads in Microsoft Edge.
3. Run Outlook in Safe Mode to rule out broken COM add-ins:
   ```cmd
   outlook.exe /safe
   ```
4. If Outlook loads normally in Safe Mode, disable third-party add-ins under **File > Options > Add-ins > Manage: COM Add-ins > Go**.

## 3. Rebuilding a Corrupted OST Cache File
When search results are incomplete or Outlook throws `0x8004010F` (Outlook data file cannot be accessed):
**Important:** Never delete an `.ost` file without first closing Outlook completely and verifying your recent emails appear in Outlook on the Web (`outlook.office.com`), because unsent items in the Outbox only exist locally.
1. Close Microsoft Outlook and verify `OUTLOOK.EXE` is not running in **Task Manager**.
2. Press `Win + R` and open `%localappdata%\Microsoft\Outlook`.
3. Rename the affected `.ost` file from `user@novatech-demo.internal.ost` to `user@novatech-demo.internal.ost.bak`.
4. Relaunch Outlook. A fresh `.ost` cache will automatically re-download from Exchange Online.
5. Once synchronization completes and all folders are verified, you may delete the `.ost.bak` file to reclaim disk space.

## 4. Shared Mailbox Not Appearing Automatically
1. Wait up to 60 minutes after IT grants **Full Access** permission for AutoMapping to take effect.
2. Restart Outlook completely (close from system tray as well).
3. If it still does not appear, go to **File > Account Settings > Account Settings > Change > More Settings > Advanced > Add** and enter the shared mailbox email address.

