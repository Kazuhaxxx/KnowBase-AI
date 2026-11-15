# NovaPulse Enterprise VPN Connection Guide

**Document ID:** KB-VPN-003  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Employee  

## 1. Connecting to NovaPulse VPN
NovaTech uses **NovaPulse Secure Client** for encrypted remote access to internal engineering, ERP, and file servers.
1. Ensure your laptop has an active Wi-Fi or Ethernet connection.
2. Open **NovaPulse Secure Client** from the system tray.
3. Confirm the gateway profile is set to `vpn-gw.novatech-demo.internal` (Auto-Select Region).
4. Click **Connect**, enter your corporate SSO email and password, and approve the **Microsoft Authenticator** push notification within 45 seconds.

## 2. Error Code Reference & Troubleshooting

### Error VPN-403: Authentication or Device Compliance Denied
`VPN-403` means either your MFA prompt expired, your password was recently changed, or Intune flagged your device as non-compliant.
1. Wait 60 seconds and retry the connection, ensuring you approve the MFA prompt immediately.
2. Verify your Windows Defender Antivirus definitions and BitLocker disk encryption are active in **Company Portal**.
3. If you changed your corporate password within the last 15 minutes, restart your workstation so Windows cached credentials synchronize.

### Error ERR_TUNNEL_CONNECTION_FAILED or Frequent Drops
1. Switch from a guest hotel/airport Wi-Fi captive portal by opening a browser first to accept the Wi-Fi terms of service before starting NovaPulse VPN.
2. Disable any personal consumer VPNs (e.g., NordVPN, Mullvad) or custom DNS-over-HTTPS browser overrides that conflict with split-tunnel corporate DNS (`10.240.0.10`).
3. Flush your local DNS resolver cache from an elevated Command Prompt:
   ```cmd
   ipconfig /flushdns
   ```
4. In NovaPulse Client settings, toggle **Protocol** from `UDP/DTLS` to `TCP-443 Fallback` when on restrictive corporate or hotel firewalls.

## 3. Slow File Transfers Over VPN
- Large datasets (>2 GB) should be accessed via approved cloud storage rather than SMB shares over VPN.
- Confirm **Split Tunneling** is enabled (only `10.0.0.0/8` internal traffic routes through the tunnel; video calls stay on local ISP).
- If internal DNS names fail to resolve while connected, run `nslookup intranet.novatech-demo.internal` and include the output when escalating to the Network Operations Desk.

