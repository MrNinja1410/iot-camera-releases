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

Release notes
Download IoT Camera Analyzer:
https://github.com/MrNinja1410/iot-camera-releases/releases/tag/v1....
v1.31.0:
Testing: Update mechanism validation - no user-facing changes.
v1.29.0:
New: IP Geolocation feature - right-click any IP in results table and select 'Geolocate' to see location details (country, city, coordinates, ISP, timezone) with an interactive Leaflet map pinned to the exact location. Copy details to clipboard.
v1.28.0:
Fixed: the FTP/Telnet/SMB/RDP/MQTT/RTSP toolbar buttons stayed frozen on their creation-time look after a theme switch - they copied SSH's button style once at startup but weren't in the list re-themed on every switch, unlike SSH itself. All now switch cleanly between the dark and default themes.
New: RDP Brute Force (real NLA) - genuine credential guessing for RDP, using the same Windows RDP client engine as 'Test Login (real NLA)' for every attempt. Unlike this app's other brute-force tools, attempts run one at a time rather than in parallel threads, since the ActiveX control has to stay on the GUI thread - slower, but each attempt is a real CredSSP/NTLM verdict, not a guess.
Fixed a real bug found while building it: Qt's default 'quit on last window closed' meant closing the RDP test widget between brute-force attempts could tear down the whole app the moment it was the only visible window - now suspended for exactly that widget's lifetime and restored after.
v1.27.0:
New: RTSP toolkit - Test Login, Batch RTSP Scan, and RTSP Brute Force, plus a right-click 'RTSP Test Login' action on any result. RTSP is the actual streaming protocol behind this app's camera targets, so this is directly on-theme - a raw DESCRIBE request with real Basic/Digest auth (MD5 via the standard library, no hand-rolled cipher), same genuine login test as FTP/Telnet/SMB/MQTT. A found login is also registered with PSS Mode's session store, so switching that device to View > PSS Mode picks the credentials up automatically.
New (experimental): 'Test Login (real NLA)' in RDP Quick Connect - an actual RDP login test via Windows' own RDP client engine (mstscax.dll, the same one mstsc.exe uses), hosted through PyQt6's QAxWidget. Real CredSSP/NTLM authentication, not a guess - this is the piece Batch RDP Scan still can't do on its own. Marked experimental because this dev environment has no real Windows Pro/Server RDP host to verify the success case against - the rejection case is verified (a non-RDP service and a genuinely unreachable host both correctly report failure, matching the real control's own ~16s internal timeout, with no crash either way).
v1.26.0:
New: MQTT toolkit - Test Login, Batch MQTT Scan, and MQTT Brute Force, plus a right-click 'MQTT Test Login' action on any result. MQTT's CONNACK reason code gives a real accept/reject verdict straight from the broker, the same genuine login test FTP/Telnet/SMB use - no crypto handshake to work around like RDP's NLA. Anonymous access (no username/password at all) is checked first, since it's the single most common finding on exposed brokers.
Multi IoT Mode gained an 'MQTT (anonymous access)' Exposed Services entry - genuinely on-theme for an IoT scanner, since MQTT is the actual messaging bus behind smart-home hubs and sensor networks, not just a legacy protocol that happens to land on IoT gear.
Renamed the 'FTP/SSH' tab to 'Protocol' and widened its open-port check to cover SMB, RDP, and MQTT alongside FTP/SSH - the Found column now spells out every protocol confirmed open on a host, not just the original two. Added live SMB/RDP/MQTT counters next to the existing FTP/SSH ones in the summary bar.
v1.25.0:
New: RDP toolkit - RDP Connect and Batch RDP Scan, plus a right-click 'RDP to' action on any result. Connect launches Windows' own mstsc.exe, caching credentials via 'cmdkey' first (then cleaning them back up once the session closes) so it connects without an extra prompt.
No RDP Brute Force this round: real RDP authentication happens inside CredSSP/NLA, a full NTLM/Kerberos-over-TLS handshake, and the one pure-Python library with that support needs a Rust toolchain to build with no prebuilt wheel available - there's no lightweight way to actually test a login the way FTP/Telnet/SMB could.
Batch RDP Scan does real, verifiable recon instead: a genuine X.224/RDP Negotiation handshake against each host reporting whether NLA is actually enforced - turning the existing BlueKeep advisory into a concrete per-host fact rather than a generic warning.
v1.24.0:
New: full SMB toolkit, mirroring FTP/Telnet - SMB Connect, Batch SMB Scan, and SMB Brute Force, plus a right-click 'SMB to' action on any result. Built on pysmb since SMB's NTLM handshake needs a real client library, unlike FTP/Telnet's raw-socket approach.
A found login also lists the server's shares, and Multi IoT Mode gained an 'SMB (guest/null session)' Exposed Services entry that flags servers with guest access or null sessions left enabled - the SMB equivalent of FTP's anonymous-login check.
'Open External' authenticates the session via Windows' own 'net use' then hands off to Explorer's native UNC-path browsing - no 3rd-party SMB client needed, unlike FTP's FileZilla integration.
v1.23.0:
New: full Telnet toolkit, mirroring FTP/SSH - Telnet Connect, Batch Telnet Scan, and Telnet Brute Force, plus a right-click 'Telnet to' action on any result. Built without telnetlib (removed from Python 3.13+) via a small raw-socket client.
Telnet's credential cycle uses the same admin-first nested sweep as FTP, with real Mirai-botnet default passwords (xc3511, vizxv, 888888, etc.) since that's genuinely what's found on exposed telnet - this is the exact credential set the original Mirai malware used to compromise IoT devices at internet scale.
Found Telnet credentials also show the host's reverse-DNS hostname and the login banner, and are saved to Results/telnet_batch_scan_logins.txt as they're found.
v1.22.0:
New: Batch FTP Scan is smarter now: usernames and passwords are separate lists cycled as a proper nested sweep - admin:admin first, then every other password against admin, then the next username and the full password cycle again - instead of a flat list of pre-paired guesses.
Anonymous logins are now a separate 'Include Anonymous Logins' toggle in the FTP menu (off by default) instead of always being mixed into the credential cycle, so genuine cracked-credential hits aren't diluted by trivially-open anonymous servers.
Found FTP credentials now also show the server's hostname (reverse DNS) and/or its welcome banner, which often embeds the real hostname even when there's no PTR record.
Batch FTP Scan hits are now saved to Results/ftp_batch_scan_logins.txt as they're found, matching FTP Brute Force's own results file.
v1.21.0:
Renamed 'Port 22 Open' to 'FTP/SSH' - it now checks tcp/21 (FTP) alongside tcp/22 (SSH) on every Good result, with a new 'Found' column showing exactly which protocol(s) were confirmed open on each host.
New: live FTP and SSH counters in the status bar next to Good/Bad, so you can see at a glance how many of each are open during a scan.
New: the Batch FTP Scan's credential list is now its own curated FTP-specific set (anonymous variants, common FTP/device defaults) instead of being reused from the SSH/camera-brand list.
v1.20.0:
Fixed: Multi IoT scans of FTP, MongoDB, Redis, RDP and VNC never showed any Good results - these aren't HTTP services, so the old HTTP-based check just errored out on every match. Each now gets a real protocol-aware check (FTP: anonymous login; the rest: the same no-auth checks the vulnerability scanner already used).
FTP's 'Open External' now launches FileZilla if it's installed, instead of just handing off to Windows Explorer's read-only ftp:// view.
New: FTP Quick Connect shows a read-only directory listing after a successful login, so you can see what's exposed without leaving the dialog.
New: a List Files button on every Batch FTP Scan hit, same directory-listing preview without re-entering credentials.
v1.19.0:
New: full FTP toolkit, mirroring the SSH tools - FTP Connect (login test + hand off to Windows Explorer's ftp:// support), Batch FTP Scan (live results across your Good tab), and FTP Brute Force (dictionary attack against a single host). Also on any result's right-click menu.
Multi IoT Mode: added FTP (anonymous login) to Exposed Services, with a Shodan query verified against live results.
New: right-click a country in the 9-5 Time Zones tab to set it as the Country in Quick Search.

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
