# Follow-Me Print & Office Printer Troubleshooting

**Document ID:** KB-PRT-005  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Public  

## 1. Setting Up NovaPrint Follow-Me Printing
All NovaTech offices use **NovaPrint Secure Release** (`\\print.novatech-demo.internal\FollowMe-Color`).
1. On corporate Windows laptops, the `FollowMe-Color` queue installs automatically via Group Policy.
2. If missing, open **Settings > Bluetooth & devices > Printers & scanners > Add device** and select **FollowMe-Color on print.novatech-demo.internal**.
3. Send your print job as normal, walk to any multifunction printer (MFP) on your floor, and tap your **Employee RFID Badge** on the card reader to release the job.
4. Unreleased jobs expire automatically after **24 hours** for document confidentiality.

## 2. Print Job Stuck in Queue or Printer Shows "Offline"
1. Confirm you are connected to the corporate **NovaTech-Corp** Wi-Fi or wired Ethernet (guest Wi-Fi `NovaTech-Guest` cannot reach internal print servers).
2. Open **Printers & scanners > FollowMe-Color > Open print queue** and cancel any stalled documents.
3. If a job remains stuck on "Deleting", restart the **Print Spooler** service from **Terminal (Admin)** or ask IT Support to run:
   ```powershell
   Restart-Service -Name Spooler -Force
   ```
4. Check the physical printer touchscreen for paper jam alerts (`Tray 2 Jam`) or low toner warnings.

## 3. Paper Jams & Hardware Alerts
**Important:** Do not pull torn paper forcefully against roller direction or use sharp objects inside the fuser unit (which operates at high temperature).
1. Follow the numbered green-latch diagram displayed on the printer's LCD panel.
2. Close all trays firmly until they click.
3. If the error code persists (e.g., `Fuser Error 50.2`), place an "Out of Service" note on the unit and submit a **Workplace Hardware** ticket with the printer's asset tag (e.g., `PRT-BLDG2-FL4`).

