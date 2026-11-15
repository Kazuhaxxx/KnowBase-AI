# Corporate Wi-Fi, Ethernet & DNS Connectivity Guide

**Document ID:** KB-NET-006  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Employee  

## 1. Corporate Wireless Networks
NovaTech campuses broadcast two SSIDs:
- **`NovaTech-Corp`** (802.1X certificate authentication): For company-managed laptops. Provides access to internal servers, printers, and intranet.
- **`NovaTech-Guest`** (Captive portal): For visitor devices and personal smartphones. Internet-only access; isolated from internal resources.

## 2. "Connected, No Internet" or Self-Assigned IP (`169.254.x.x`)
An IP address starting with `169.254.` (APIPA) means the workstation could not obtain a DHCP lease.
1. Toggle Airplane Mode ON for 10 seconds, then OFF.
2. Verify you are connected to `NovaTech-Corp` rather than `NovaTech-Guest`.
3. Release and renew your DHCP lease and flush DNS:
   ```cmd
   ipconfig /release
   ipconfig /renew
   ipconfig /flushdns
   ```
4. If using a wired Ethernet dock and the link light does not illuminate, test an alternate wall jack or reseat the USB-C cable.

## 3. Browser "DNS_PROBE_FINISHED_NXDOMAIN" or Slow Name Resolution
1. Confirm no static custom DNS server (like `8.8.8.8`) was manually hardcoded on your Wi-Fi adapter, because internal domains (`*.novatech-demo.internal`) require automatic DHCP DNS (`10.240.0.10` / `10.240.0.11`).
2. Check **Settings > Network & internet > Wi-Fi > Hardware properties** and ensure **DNS server assignment** is set to **Automatic (DHCP)**.
3. Restart your browser completely or test in an InPrivate window to rule out proxy extensions.

## 4. Certificate Errors on `NovaTech-Corp` Wi-Fi
If Windows prompts to trust a radius certificate (`radius.novatech-demo.internal`) and fails to connect:
- Ensure your corporate machine certificate has not expired by opening **Company Portal** and clicking **Sync**.
- If completely offline, plug into an Ethernet port to sync policy, or visit the on-site IT Walk-Up Bar.

