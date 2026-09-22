<!--
  ═══════════════════════════════════════════════════════════════
  README for IoT Camera Analyzer
  ---------------------------------------------------------------
  HOW TO ADD YOUR IMAGES:
  Every image below points to a file in  docs/screenshots/ .
  1. Create a folder named  docs/screenshots/  in your repo.
  2. Drop your screenshots in with the exact file names shown
     (dashboard.png, multi-feed.png, etc.) — or change the paths.
  Until you add them, GitHub shows the alt-text in a grey box,
  so nothing looks broken.
  Anything marked  <!-- EDIT --> 
  ═════════════════════════════════════════════════════════════════════════
  

<div align="center">

<!-- Replace docs/screenshots/logo.png with your logo or banner (recommended width ~600px) -->
<img src="https://imgup.uk/i/brNnwUC4.png" alt="IoT Camera Analyzer logo" />

# IoT Camera Analyzer

**Discover, monitor and manage every IP camera on your network — from one desktop app.**

Real-time feeds · motion detection · smart alerts · automatic signed updates. No cloud account, no subscription, everything stays on your machine.

[![Latest release](https://img.shields.io/github/v/release/MrNinja1410/iot-camera-releases?style=flat-square&color=00c8e8)](https://github.com/MrNinja1410/iot-camera-releases/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/MrNinja1410/iot-camera-releases/total?style=flat-square&color=3dd68c)](https://github.com/MrNinja1410/iot-camera-releases/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue?style=flat-square)](#-system-requirements)
[![License](https://img.shields.io/github/license/MrNinja1410/iot-camera-releases?style=flat-square)](LICENSE)

### [⬇ Download the latest release](https://github.com/MrNinja1410/iot-camera-releases/releases/latest)

</div>

<br />

<!-- Replace docs/screenshots/dashboard.png with a screenshot of the main app window -->
<div align="center">
  <img src="https://imgup.uk/i/j05c5wzf.png" alt="IoT Camera Analyzer main dashboard showing multiple live camera feeds" width="850" />
</div>

<br />

## Contents

- [What is IoT Camera Analyzer?](#-what-is-iot-camera-analyzer)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Download & Install](#-download--install)
- [How automatic updates work](#-how-automatic-updates-work)
- [Full capability list](#-full-capability-list)
- [System requirements](#-system-requirements)
- [Quick start](#-quick-start)
- [FAQ & troubleshooting](#-faq--troubleshooting)
- [Changelog](#-changelog)
- [License](#-license)

---

## 🎯 What is IoT Camera Analyzer?

IoT Camera Analyzer is a Windows desktop application that scans your local network, automatically finds connected IP and IoT cameras, and gives you a single dashboard to watch live feeds, track motion, review alerts, record footage, and keep your devices' firmware in check.

It's built for **home-lab users, network engineers, and security teams** who want reliable, fully offline camera management — without handing their video streams to a third-party cloud.

> This repository is also the **official download and update host**. The app's built-in **Update** button pulls signed release binaries directly from here.

---

## ✨ Features

**🎬 Core Camera Features**

| | Feature | Tier | What it does |
|---|---|---|---|
| 🔍 | **Network Discovery** | FREE | Automatically scans your LAN for 25+ camera brands (Hikvision, Dahua, Axis, Reolink, Tapo, etc.) and detects brand, model, firmware and IP — no manual setup. |
| 📺 | **Live Multi-Feed View** | FREE | Watch up to **16 feeds at once** in a resizable grid. Supports H.264, H.265 and MJPEG with hardware-accelerated decoding. |
| 🎯 | **Motion Detection** | FREE | Draw per-camera detection zones with independent sensitivity, and trigger alerts or snapshots the moment motion is seen. |
| 📊 | **Analytics Dashboard** | FREE | Charts motion events over time, tracks per-device uptime, and logs connection quality. Export everything to CSV or JSON. |
| 🔔 | **Smart Alerts** | FREE | Alert rules by camera, time of day or event type. Desktop notifications plus optional **webhooks** for outside integrations. |
| 🔄 | **Automatic Updates** | FREE | The built-in updater checks this repo for a new **signed** release and installs it in the background — no manual reinstall. |
| 🔐 | **Credential Manager** | FREE | Stores camera logins in the OS keychain (never plaintext) and flags any camera still using factory-default passwords. |
| 📁 | **Recording & Playback** | FREE | Schedule recordings by time or motion trigger, saved locally as MP4 with a built-in playback timeline and snapshot export. |
| 🌐 | **Works Fully Offline** | FREE | No account, no cloud. Your feeds never leave your network — the internet is only touched to check for updates. |

**🔧 Advanced Protocol Toolkits (VIP)**

| | Protocol | What it does |
|---|---|---|
| 🐚 | **SSH Toolkit** | Test Login, Batch SSH Scan, SSH Brute Force. Find open SSH ports and test credentials across your network. |
| 📂 | **FTP Toolkit** | Test Login, Batch FTP Scan, FTP Brute Force. Discover open FTP servers and test for anonymous/credential access. |
| 📡 | **Telnet Toolkit** | Test Login, Batch Telnet Scan, Telnet Brute Force. Includes Mirai-era default passwords for IoT devices. |
| 🔗 | **SMB Toolkit** | Test Login, Batch SMB Scan, SMB Brute Force. Find open file shares and list accessible content. |
| 🎬 | **RTSP Toolkit** | Test Login, Batch RTSP Scan, RTSP Brute Force. Real Basic/Digest auth testing for streaming protocols. |
| 🖥️ | **RDP Toolkit** | Test Login, Batch RDP Scan, RDP Brute Force. Connect to Windows RDP hosts and detect NLA enforcement (BlueKeep detection). |
| 📨 | **MQTT Toolkit** | Test Login, Batch MQTT Scan, MQTT Brute Force. Scan IoT message brokers and test for anonymous access. |

**🔍 Vulnerability & Exploit Tools (VIP)**

| | Feature | What it does |
|---|---|---|
| 🎯 | **Live PSS Mode** | Real-time port scanner with service detection. Discovers open ports and running services on target hosts. |
| 🔬 | **CVE Lookup** | Scans discovered devices against known CVE databases and flags outdated firmware. |
| 💣 | **Metasploit Integration** | Direct integration with Metasploit framework for exploit verification and testing. |
| 🗺️ | **Masscan Integration** | High-speed network scanning using Masscan for large subnet sweeps (10,000+ IPs). |
| 🌍 | **IP Geolocation** | Right-click any IP to see location details (country, city, coordinates, ISP, timezone) on interactive map. |
| 🔐 | **Multi IoT Mode** | Scan for exposed services across your network with one click. Auto-detects: cameras, NVRs, smart-home hubs, industrial IoT, databases, APIs. |

**🌐 Public Internet Scanning (VIP)**

| | Feature | What it does |
|---|---|---|
| 📡 | **Databse Integration** | Search the database for publicly exposed devices matching your criteria. Find cameras, NVRs, and IoT devices worldwide. |
| 🎯 | **IP Range Scanning** | Scan arbitrary IP ranges (CIDR notation) for devices. Not limited to your LAN — scan any public internet range. |
| 🔍 | **LAN Discovery** | Auto-scan your local network with zero configuration. Find cameras on your subnet. |
| 📊 | **Bulk Export** | Export scan results with device details, credentials, CVEs, and metadata to CSV/JSON. |
| ⚡ | **Masscan for Scale** | Ultra-fast network scanning using Masscan for large sweeps (10,000+ IPs per minute). |

---

## 📸 Screenshots

<!--
  Drop your screenshots into docs/screenshots/ with these file names,
  or change the paths below. Descriptive alt text means the grey
  placeholder box still tells you what belongs there.
-->

### Live multi-camera view
<img src="docs/screenshots/multi-feed.png" alt="Grid of live camera feeds with per-camera status" width="850" />

### Network discovery
<img src="docs/screenshots/network-scan.png" alt="Network scan results listing discovered cameras with brand, model and firmware" width="850" />

### Motion detection zones
<img src="docs/screenshots/motion-zones.png" alt="Camera feed with drawn motion-detection zones and sensitivity sliders" width="850" />

### Analytics
<img src="docs/screenshots/analytics.png" alt="Analytics dashboard charting motion events and device uptime" width="850" />

---

## 📥 Download & Install

Grab the latest signed build from the [**Releases**](https://github.com/MrNinja1410/iot-camera-releases/releases/latest) page.

| Build | File | Size | Notes |
|---|---|---|---|
| **Portable** | `IoTCameraAnalyzer.exe` | ~246 MB | Runs from any folder or USB stick — no installation. |

> 🍎🐧 **macOS and Linux builds are in progress.** Click **Watch → Releases** on this repo to be notified.

### Install (portable)
1. Download and unzip `IoTCameraAnalyzer-Portable.zip`.
2. Run `IoTCameraAnalyzer.exe` from the extracted folder.

### Verify your download (optional but recommended)
Every release ships with a `SHA256SUMS.txt`. Confirm your file is intact:

```powershell
Get-FileHash .\IoTCameraAnalyzer-Setup.exe -Algorithm SHA256
# Compare the printed hash against the matching line in SHA256SUMS.txt
```

---

## 🔄 How automatic updates work

You don't need to visit this page to stay current. Inside the app:

**Settings → About → Check for Updates**

1. The app queries this repository's **latest release**.
2. It downloads the new signed binary to a temp folder.
3. It **verifies the signature / checksum** before doing anything.
4. It relaunches into the new version — your settings, camera list and recordings are all preserved.

<!-- Replace docs/screenshots/update-dialog.png with a screenshot of the in-app update dialog -->
<div align="center">
  <img src="docs/screenshots/update-dialog.png" alt="In-app update dialog showing a new version ready to install" width="620" />
</div>

A corrupt or unsigned binary is rejected automatically, so a failed download can never install a broken build.

---

## 🧰 Full capability list

### FREE TIER — Everything You Need for Camera Monitoring

- ✅ **Auto-discover cameras** across your subnet — 25+ brands (Hikvision, Dahua, Axis, Reolink, Tapo, Uniview, Foscam, etc.)
- ✅ **Live stream up to 16 feeds** with drag-to-reorder, full-screen, and PTZ controls
- ✅ **H.264 / H.265 / MJPEG** decoding with hardware acceleration (DXVA2)
- ✅ **Motion zones** — draw per-camera detection regions with independent sensitivity
- ✅ **Snapshot on motion** — auto-saves timestamped JPEG frames to a folder you choose
- ✅ **Scheduled recording** — record by timer or motion trigger, saved as MP4 with built-in playback
- ✅ **Searchable motion event log** with linked snapshots and timestamps
- ✅ **Per-camera uptime tracking** with connection-loss alerts
- ✅ **Firmware version check** — flags cameras running known-outdated firmware
- ✅ **Default-credential scanner** — finds your cameras still on factory passwords
- ✅ **Webhook alerts** — POST event data to any endpoint on motion, disconnect or alert
- ✅ **CSV / JSON export** of motion logs, device inventory, and scan results
- ✅ **OS keychain integration** — credentials stored securely in Windows Credential Manager, never in plaintext
- ✅ **Dark & light themes** — follows your Windows system theme or pin your choice
- ✅ **Auto-update from GitHub** — signed, verified binaries pulled automatically
- ✅ **Portable mode** — run from any folder or USB drive with zero installation

### VIP TIER — Advanced Scanning & Exploitation Tools

**Local Network Scanning:**
- ✅ **Live PSS Mode** — Real-time port scanner with service detection and version identification
- ✅ **Full Protocol Toolkits** — SSH, FTP, Telnet, SMB, RTSP, RDP, MQTT with Test/Batch/Brute-Force variants
- ✅ **Metasploit Integration** — Direct module execution for exploit verification and payload testing
- ✅ **Masscan Integration** — Ultrafast network scanning for large subnets (10,000+ IPs per minute)
- ✅ **Multi IoT Mode** — One-click scan for exposed cameras, NVRs, smart-home hubs, databases, APIs
- ✅ **LAN Discovery** — Auto-scan your local network with zero configuration

**Public Internet Scanning:**
- ✅ **Shodan Integration** — Search Shodan database for publicly exposed devices worldwide
- ✅ **IP Range Scanning** — Scan arbitrary IP ranges (CIDR notation) on the public internet
- ✅ **Bulk Results Export** — Export device details, credentials, CVEs, and metadata to CSV/JSON

**Advanced Features:**
- ✅ **CVE Lookup** — Scan for known vulnerabilities in discovered device firmware
- ✅ **IP Geolocation** — Interactive map showing country, city, ISP, timezone for any IP
- ✅ **Advanced URL Fuzzer** — Directory and endpoint discovery with custom wordlists
- ✅ **Batch Vulnerability Scan** — Cross-device CVE detection and firmware outdatedness checks
- ✅ **Session Management (PSS)** — Automatically reuse discovered credentials across services

---

## 💻 System requirements

| | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 (x64) | Windows 11 (x64) |
| **RAM** | 4 GB | 8 GB+ for 8 or more streams |
| **Disk** | 200 MB for the app | Plus room for recordings |
| **GPU** | Not required | DXVA2-capable for hardware decode |
| **Network** | Cameras on the same LAN / subnet | Wired connection for many feeds |
| **Internet** | Not required | Only used to check for updates |

---

## 🚀 Quick start

1. **Install** the app (see [Download & Install](#-download--install)).
2. On first launch, open **Discover** and let it scan your network.
3. Select the cameras you want and enter their credentials when prompted (or import them).
4. Arrange feeds in the grid, then open **Motion** to draw detection zones.
5. Set your **Alert** and **Recording** rules under **Settings**.

That's it — the app runs in the background and notifies you when something happens.

---

## ❓ FAQ & troubleshooting

<details>
<summary><strong>A camera isn't showing up in Discovery</strong></summary>

- Confirm the camera is on the **same subnet** as your PC.
- Some cameras disable ONVIF by default — enable it in the camera's own web UI.
- Add it manually via **Add Camera → RTSP URL** if auto-discovery misses it.
</details>

<details>
<summary><strong>The feed is black or won't connect</strong></summary>

- Double-check the username and password.
- Try the camera's **sub-stream** URL — some devices only allow one main-stream connection at a time.
- Make sure your firewall isn't blocking the RTSP port (commonly 554).
</details>

<details>
<summary><strong>Windows SmartScreen blocked the installer</strong></summary>

New releases haven't built up publisher reputation yet. Choose **More info → Run anyway**, or verify the SHA256 checksum first (see [Verify your download](#verify-your-download-optional-but-recommended)).
</details>

<details>
<summary><strong>Where are my recordings and settings stored?</strong></summary>

<!-- EDIT: update these paths to match your app -->
- Settings: `%APPDATA%\IoTCameraAnalyzer\`
- Recordings: the folder you set under **Settings → Recording** (defaults to `Videos\IoTCameraAnalyzer\`).
</details>

---

## 📝 Changelog

### [v1.31.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.31.0) — 2026-09-22
**Update Mechanism Validation**
- Confirmed end-to-end update flow working correctly
- All v1.30.0+ users receive automatic updates seamlessly

### [v1.30.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.30.0) — 2026-09-22 ⭐ Major Release
**IP Geolocation Feature**
- **New:** Right-click any IP in results table → select **Geolocate** to see:
  - Country, city, exact coordinates on interactive Leaflet map
  - ISP, timezone, connection type
  - Copy all details to clipboard
- Built with Nuitka for maximum performance and code obfuscation
- 100% self-contained (246 MB executable)
- ⚠️ **Note:** Users on v1.28.0 and earlier must manually download v1.30.0. Auto-update unavailable due to key rotation. Future updates will be automatic.

### [v1.29.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.29.0) — 2026-09-21
**IP Geolocation (Preview)**
- Early release of geolocation feature for testing

### [v1.28.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.28.0) — 2026-09-20
**Theme Fixes & RDP Brute Force**
- **Fixed:** FTP/Telnet/SMB/RDP/MQTT/RTSP toolbar buttons now correctly re-theme when switching between dark and light modes
- **New:** RDP Brute Force — genuine credential guessing using Windows' own RDP engine (CredSSP/NTLM)
- **Fixed:** Qt crash when closing RDP test widget during brute-force attempts

### [v1.27.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.27.0) — 2026-09-19
**RTSP Toolkit & Experimental RDP Login**
- **New:** RTSP Toolkit — Test Login, Batch RTSP Scan, RTSP Brute Force with real Basic/Digest auth
- **New (Experimental):** Test Login (real NLA) in RDP Quick Connect — genuine Windows RDP authentication
- Found logins auto-integrate with PSS Mode for credential reuse

### [v1.26.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.26.0) — 2026-09-18
**MQTT Toolkit & IoT Support**
- **New:** MQTT Toolkit — Test Login, Batch MQTT Scan, MQTT Brute Force
- **New:** Multi IoT Mode includes "MQTT (anonymous access)" detection
- Real CONNACK verdict from broker (not a guess)

### [v1.25.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.25.0) — 2026-09-17
**RDP Toolkit & Batch RDP Recon**
- **New:** RDP Connect (launches `mstsc.exe` with cached credentials)
- **New:** Batch RDP Scan — X.224/RDP Negotiation for NLA verification (BlueKeep detection)

### [v1.24.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.24.0) — 2026-09-16
**Full SMB Toolkit**
- **New:** SMB Connect, Batch SMB Scan, SMB Brute Force with real NTLM
- Found logins list accessible shares
- Multi IoT Mode: "SMB (guest/null session)" detection

### [v1.23.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.23.0) — 2026-09-15
**Full Telnet Toolkit**
- **New:** Telnet Connect, Batch Telnet Scan, Telnet Brute Force
- Includes real Mirai-era default passwords (xc3511, vizxv, 888888, etc.)
- Results saved with reverse-DNS hostname and login banner

### [v1.22.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.22.0) — 2026-09-14
**Smarter FTP Scanning**
- **Improved:** Nested credential sweep (admin:all-passwords, then next-user:all-passwords, etc.)
- **New:** Anonymous login toggle (separate from cracked-credential results)
- **Enhanced:** Results show hostname (reverse DNS) and server banner

### [v1.21.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.21.0) — 2026-09-13
**FTP/SSH Dual Checks & Live Counters**
- **Enhanced:** "Port 22 Open" now checks both TCP/21 (FTP) and TCP/22 (SSH)
- **New:** Live FTP and SSH counters in status bar

### [v1.20.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.20.0) — 2026-09-12
**Multi-IoT Protocol Fixes**
- **Fixed:** Multi IoT scans for FTP, MongoDB, Redis, RDP, VNC now show Good results
- **Enhanced:** FTP 'Open External' launches FileZilla if installed
- **New:** FTP Quick Connect shows directory listing

### [v1.19.0](https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1.19.0) — 2026-09-11
**Full FTP Toolkit**
- **New:** FTP Connect, Batch FTP Scan, FTP Brute Force
- Multi IoT Mode: "FTP (anonymous login)" detection

---

**See the full [Releases page](https://github.com/MrNinja1410/iot-camera-releases/releases) for complete history and download links.**

---

## 📄 License

<!-- EDIT: state your license, e.g. MIT, and make sure a LICENSE file exists in the repo. -->
Released under the [MIT License](LICENSE).

---

<div align="center">

**IoT Camera Analyzer** — made for people who'd rather keep their cameras off the cloud.

[Report a bug](https://github.com/MrNinja1410/iot-camera-releases/issues) · [Request a feature](https://github.com/MrNinja1410/iot-camera-releases/issues) · [Releases](https://github.com/MrNinja1410/iot-camera-releases/releases)

</div>
