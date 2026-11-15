# IT Staff Playbook: Intune Autopilot & BitLocker Recovery

**Document ID:** KB-IT-101  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** IT Staff Only (`it_only`)  

## 1. Retrieving a BitLocker 48-Digit Recovery Key
When an employee's laptop displays the blue BitLocker Recovery screen after a BIOS update or TPM reset:
1. Verify the caller's identity via Employee ID + manager confirmation or live video check.
2. Open **Microsoft Intune Admin Center > Devices > All Devices**, search the hostname or serial number.
3. Click **Recovery Keys** and verify the **Key ID** (first 8 characters) matches the screen shown to the user before reading the 48-digit recovery key.
4. Log the recovery key disclosure in the Service Desk ticket for audit compliance.

## 2. Windows Autopilot Re-Provisioning (White-Glove / Pre-Provisioning)
1. Boot a freshly wiped Windows 11 laptop to the OOBE region selection screen.
2. Press the **Windows key 5 times** rapidly to enter **Autopilot Technician Flow**.
3. Select **Provision with Windows Autopilot**, confirm the assigned NovaTech profile (`NT-Win11-Corp-Standard`), and wait for device ESP apps (`NovaPulse VPN`, `Defender`, `Office 365`) to turn green.
4. Click **Reseal** before shipping the workstation to the employee.

