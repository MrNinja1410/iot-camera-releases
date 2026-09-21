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
  Anything marked  <!-- EDIT -->  is a placeholder value you
  should swap for your real details (repo URL, version, etc.).
  ═══════════════════════════════════════════════════════════════
-->

<div align="center">

<!-- Replace docs/screenshots/logo.png with your logo or banner (recommended width ~600px) -->
<img src="docs/screenshots/logo.png" alt="IoT Camera Analyzer logo" width="140" />

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
  <img src="docs/screenshots/dashboard.png" alt="IoT Camera Analyzer main dashboard showing multiple live camera feeds" width="850" />
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

| | Feature | What it does |
|---|---|---|
| 🔍 | **Network Discovery** | Automatically scans your LAN for RTSP, ONVIF and HTTP cameras, and detects each device's brand, model and firmware version — no manual setup. |
| 📺 | **Live Multi-Feed View** | Watch up to **16 feeds at once** in a resizable grid. Supports H.264, H.265 and MJPEG with hardware-accelerated decoding. |
| 🎯 | **Motion Detection** | Draw per-camera detection zones with independent sensitivity, and trigger alerts or snapshots the moment motion is seen. |
| 📊 | **Analytics Dashboard** | Charts motion events over time, tracks per-device uptime, and logs connection quality. Export everything to CSV or JSON. |
| 🔔 | **Smart Alerts** | Alert rules by camera, time of day or event type. Desktop notifications plus optional **webhooks** for outside integrations. |
| 🔄 | **Automatic Updates** | The built-in updater checks this repo for a new **signed** release and installs it in the background — no manual reinstall. |
| 🔐 | **Credential Manager** | Stores camera logins in the OS keychain (never plaintext) and flags any camera still using factory-default passwords. |
| 📁 | **Recording & Playback** | Schedule recordings by time or motion trigger, saved locally as MP4 with a built-in playback timeline and snapshot export. |
| 🌐 | **Works Fully Offline** | No account, no cloud. Your feeds never leave your network — the internet is only touched to check for updates. |

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
| **Windows Installer** | `IoTCameraAnalyzer-Setup.exe` | ~48 MB | Standard install for Windows 10 / 11 (x64). |
| **Portable** | `IoTCameraAnalyzer-Portable.zip` | ~46 MB | Runs from any folder or USB stick — no installation. |

> 🍎🐧 **macOS and Linux builds are in progress.** Click **Watch → Releases** on this repo to be notified.

### Install (installer)
1. Download `IoTCameraAnalyzer-Setup.exe` from the latest release.
2. Run it. Windows SmartScreen may warn about a new publisher — choose **More info → Run anyway**.
3. Launch **IoT Camera Analyzer** from the Start menu.

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

Everything the app can do, at a glance:

- ✅ **Auto-discover cameras** across your subnet — RTSP, ONVIF, Axis, Hikvision, Dahua, Reolink and more
- ✅ **Live stream up to 16 feeds** with drag-to-reorder, full-screen, and PTZ controls
- ✅ **H.264 / H.265 / MJPEG** decoding, hardware-accelerated where supported
- ✅ **Motion zones** — draw detection regions per camera with per-region sensitivity
- ✅ **Snapshot on motion** — auto-saves timestamped frames to a folder you choose
- ✅ **Scheduled recording** — record any feed on a timer or when motion triggers
- ✅ **Searchable motion event log** with linked snapshots
- ✅ **Per-camera uptime tracking** with connection-loss alerts
- ✅ **Firmware version check** — flags cameras running known-outdated firmware
- ✅ **Default-credential scanner** — finds your cameras still on factory passwords
- ✅ **Webhook alerts** — POST event data to any endpoint on motion, disconnect or alert
- ✅ **CSV / JSON export** of motion logs and device inventory
- ✅ **OS keychain integration** — credentials stored securely, never in plaintext
- ✅ **Dark & light themes** — follows your system or pin your choice
- ✅ **Auto-update from GitHub** — signed binaries pulled from this repo in one click
- ✅ **Portable mode** — run from a USB drive with zero install

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

<!-- EDIT: replace these with your real release notes. Keep newest at the top. -->

### v2.4.1 — _latest_
- _Add your changes here (one bullet per change)._

### v2.3.0
- _Add your changes here._

### v2.2.0
- _Add your changes here._

### v2.0.0
- _Add your changes here._

See the [Releases page](https://github.com/MrNinja1410/iot-camera-releases/releases) for full notes and downloads.

---

## 📄 License

<!-- EDIT: state your license, e.g. MIT, and make sure a LICENSE file exists in the repo. -->
Released under the [MIT License](LICENSE).

---

<div align="center">

**IoT Camera Analyzer** — made for people who'd rather keep their cameras off the cloud.

[Report a bug](https://github.com/MrNinja1410/iot-camera-releases/issues) · [Request a feature](https://github.com/MrNinja1410/iot-camera-releases/issues) · [Releases](https://github.com/MrNinja1410/iot-camera-releases/releases)

</div>
