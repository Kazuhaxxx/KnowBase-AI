# Account Unlock, Password Reset & MFA Enrollment

**Document ID:** KB-IAM-007  
**Organization:** NovaTech Global (Fictional Demo Knowledge Base)  
**Classification:** Public  

## 1. Self-Service Password Reset (SSPR)
Employees can reset forgotten passwords 24/7 via the **NovaTech Identity Portal** (`https://sspr.novatech-demo.internal`).
1. Click **Can't access your account?** on the Microsoft 365 or SSO login screen.
2. Enter your `@novatech-demo.internal` email and complete the verification challenge using **Microsoft Authenticator** or your registered secondary verification method.
3. Choose a new password meeting NovaTech complexity policy:
   - Minimum **14 characters**
   - Cannot reuse any of the last **12 passwords**
   - Must not contain your first name, last name, or the word `novatech`.
4. **Important:** After resetting your password remotely, connect to NovaPulse VPN (or on-campus Wi-Fi) and lock (`Win + L`) and unlock your Windows session so your local cached password updates.

## 2. Account Lockout Policy
- Accounts automatically lock for **15 minutes** after **5 consecutive failed login attempts**.
- Common causes of unexpected lockouts include outdated passwords cached on mobile mail apps, mapped network drives, or old browser sessions.
- Remove stale saved entries from **Windows Credential Manager** (`Control Panel > Credential Manager > Windows Credentials`) if lockouts repeat.

## 3. Re-enrolling MFA on a New Mobile Device
If you replaced or lost your smartphone and no longer have Microsoft Authenticator:
1. Do NOT factory-reset your old phone before transferring MFA if you still have access to it; add the new phone first at `https://mysignins.microsoft.com/security-info`.
2. If you already lost access to your old device, call the **IT Service Desk Verification Line** (`ext. 4357`) or visit the IT Walk-Up Desk with your **Employee Photo ID** so an IT Specialist can issue a temporary **Temporary Access Pass (TAP)** valid for 2 hours.
3. Once signed in with TAP, scan the new QR code in the **Microsoft Authenticator** app.

