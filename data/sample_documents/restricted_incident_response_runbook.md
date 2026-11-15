# RESTRICTED: Privileged AD & Security Incident Runbook

**Document ID:** KB-SEC-999  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Restricted (Administrators Only)  

## 1. Break-Glass Domain Administrator Vault Procedure
**RESTRICTED PROCEDURE — DO NOT SHARE WITH STANDARD EMPLOYEES OR EXTERNAL PARTIES.**
1. Break-glass accounts (`bg-ad-01`, `bg-ad-02`) are stored in Hardware Security Module (HSM) Vault **SecOps-Tier0-Alpha**.
2. Retrieval requires dual-custody approval from the CISO On-Call and Principal Identity Architect via hardware FIDO2 token quorum.
3. Every break-glass checkout automatically triggers a **Tier-0 SIEM Critical Alert** (`ALERT-IAM-901`) and expires credentials after **4 hours**.

## 2. Compromised Endpoint Immediate Containment Protocol
1. In Microsoft Defender for Endpoint, select the host and invoke **Isolate Device** (maintains telemetry channel `10.250.99.0/24` while blocking lateral SMB/RDP).
2. Revoke all Entra ID refresh tokens using the SecOps containment script (`Revoke-AllUserRefreshTokens -UPN <user>`).
3. Rotate any local LAPS administrator passwords immediately and preserve volatile memory dump before re-imaging.

