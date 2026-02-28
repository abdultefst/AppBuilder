# 📱 Mobile Build Tool

> **A professional macOS GUI** for building React Native & Flutter projects to `.ipa` and `.apk` — with automatic widget linking, smart error parsing, and a modern dark UI.

---

## ✨ Features at a Glance

| Feature | Details |
|---|---|
| 🍎 **iOS Build → IPA** | Builds release/debug `.ipa` with clean, versioned filenames |
| 🤖 **Android Build → APK** | Runs Gradle `assembleRelease` / `assembleDebug` automatically |
| 📦 **Both Targets** | Build iOS + Android in a single click |
| 🔍 **Auto-Detection** | Scans your folder — detects Flutter vs React Native instantly |
| 🔗 **Widget Linking** | Links iOS Widget Extensions via **xcodeproj gem** or pbxproj edit |
| ✅ **Widget Verifier** | Full health-check: WidgetKit, App Groups, bundle ID nesting |
| 📋 **Smart Logs** | Colour-coded output, error location extraction, copy buttons |
| 🏷️ **Proper Naming** | `AppName_1.2.0_release_20250601.ipa` — no random hashes |
| 🔄 **Replace-Safe** | Second build overwrites the previous file, never accumulates junk |

---

## 🖥️ Screenshots

```
╔══════════════════════════════════════════════════════════════════════╗
║  📱  Mobile Build Tool         React Native & Flutter › IPA + APK  ║
╠══════════╦═══════════════════════════════════════════════════════════╣
║  ⚙️ Settings  ║  📋 Build Output                                     ║
║  ─────────  ║  ──────────────────────────────────────────────────  ║
║  📁 Path    ║  🔍 Scanning project…                                 ║
║  🔍 Detect  ║     /Users/you/Projects/MyApp                         ║
║  📊 Info    ║  ✅ Flutter project detected!                          ║
║  🎯 Target  ║  📋 App: MyApp v2.1.0                                 ║
║  🔧 Options ║                                                        ║
║  📤 Output  ║  🚀 BUILD STARTED                                     ║
║  🔗 Widget  ║  📦 [1/3] Cleaning…                                   ║
║  ─────────  ║  🍎 [2/3] Building iOS…                               ║
║  🚀 Build   ║    $ flutter build ipa --release --no-codesign        ║
║  ⏹ Stop    ║  ✅ IPA saved:                                         ║
║  📂 Open    ║     📁 /builds/MyApp_2.1.0_release_20250601.ipa       ║
╚══════════╩═══════════════════════════════════════════════════════════╝
```

---

## 🚀 Quick Start

### 1 — Prerequisites

Make sure the following tools are available on your Mac:

```bash
# Flutter
brew install --cask flutter
flutter doctor

# Xcode (iOS builds)
xcode-select --install

# CocoaPods
sudo gem install cocoapods

# xcodeproj gem (for widget linking)
gem install xcodeproj

# Android: ensure JAVA_HOME and Android SDK are in PATH
# React Native: Node.js + npm or yarn
brew install node
```

> 💡 The tool also searches `/opt/homebrew/bin`, `/usr/local/bin`, and `~/flutter/bin` automatically.

---

### 2 — Run the Tool

```bash
# Clone or download the script
git clone https://github.com/you/mobile-build-tool
cd mobile-build-tool

# Run directly (auto-installs customtkinter if missing)
python3 build_tool.py
```

That's it — the window opens at a comfortable 1280×820 and is fully resizable.

---

## 📖 How to Use

### Step 1 — Load your project

1. Click **Browse** next to the path field and select your project root.
2. Or paste the path manually, then press **🔍 Auto-Detect Project**.
3. The tool reads `pubspec.yaml` (Flutter) or `package.json` (React Native) and fills in app name + version.

---

### Step 2 — Configure the build

| Setting | What it does |
|---|---|
| 🎯 **Target** | iOS only, Android only, or Both |
| 🔧 **Clean** | Runs `flutter clean` / `rm -rf node_modules` before building |
| 🔧 **Release mode** | Toggle Release vs Debug build |
| 🔧 **Verbose** | Pass `--verbose` to the build command |
| 📤 **Output dir** | Where `.ipa` / `.apk` land (defaults to `<project>/builds/`) |

---

### Step 3 — Start the build

Click **🚀 Start Build**.

The log panel on the right streams live output:

- 🔴 **Errors** — highlighted in red, with exact file + line extracted
- 🟡 **Warnings** — yellow
- 🟢 **Success** lines — green
- 💜 **File paths** — purple, easy to spot

Use the toolbar buttons:

| Button | Action |
|---|---|
| **All** | Show full log |
| **Errors** | Show only error lines |
| **Summary** | Totals, elapsed time, output files |
| **📋 Copy All** | Copy entire log to clipboard |
| **🔴 Copy Errors** | Copy only error lines |
| **🗑 Clear** | Wipe the log panel |

---

### Step 4 — Widget linking (iOS only)

1. Set the **Widget Extension Folder** path (the tool auto-detects it if the folder contains "widget" or "extension" in its name).
2. Click **🔗 Link Widget to Xcode Project**.
3. The tool tries to use the `xcodeproj` Ruby gem first, then falls back to manual `project.pbxproj` editing.
4. Click **✅ Verify Widget Link Status** afterwards for a full health report:

```
📊  Widget Health Check:
  ✅  Widget name referenced
  ✅  Embed Foundation Extensions
  ✅  WidgetKit framework
  ✅  SwiftUI framework
  ❌  App Groups entitlement   ← you need to fix this in Xcode
  ✅  Widget bundle identifier
  ✅  Bundle ID nesting  ( com.company.app  ›  com.company.app.widget )
```

---

## 📁 Output File Naming

Files are always named in a predictable, human-readable format:

```
AppName_version_mode_date.ext
```

Examples:
```
MyAwesomeApp_2.1.0_release_20250601.ipa
MyAwesomeApp_2.1.0_release_20250601.apk
```

- **Rebuilding** replaces the existing file — no duplicate accumulation.
- All output lands in `<project>/builds/` by default (configurable).

---

## 🏗️ How Builds Work Internally

### Flutter

```
flutter clean
flutter pub get
flutter build ipa --release --no-codesign   (iOS)
flutter build apk --release                  (Android)
→ copies + renames output to builds/
```

### React Native

```
npm ci  (or  yarn install --frozen-lockfile)
pod install --repo-update                    (iOS)
xcodebuild -workspace … archive             (iOS)
xcodebuild -exportArchive …                 (iOS export)
./gradlew assembleRelease                    (Android)
→ copies + renames output to builds/
```

---

## 🔗 Widget Linking Deep Dive

The tool performs the link in this priority order:

| Method | When used |
|---|---|
| **xcodeproj gem** (Ruby) | Available or successfully auto-installed |
| **Manual pbxproj** | Gem unavailable — modifies `project.pbxproj` directly after making a timestamped backup |

What gets linked:
- Widget extension target added to the Xcode project
- Swift source files registered
- Asset catalogs registered
- `Embed Foundation Extensions` build phase created
- `WidgetKit.framework` and `SwiftUI.framework` linked
- Product embedded into main app target with `RemoveHeadersOnCopy`

> ⚠️ After manual linking, open Xcode once to confirm bundle IDs and add App Groups capability — the tool tells you exactly what to verify.

---

## ⚠️ Troubleshooting

### `flutter` not found
```bash
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.zshrc
source ~/.zshrc
```

### `pod install` fails
```bash
sudo gem install cocoapods
pod repo update
```

### Android build fails — SDK not found
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/emulator:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

### Signing error on iOS
The tool builds with `CODE_SIGN_IDENTITY=-` and `CODE_SIGNING_REQUIRED=NO` — this is intentional for CI-style unsigned builds. For App Store distribution, sign in Xcode Organizer after the archive is created.

### customtkinter not installed
The script installs it automatically on first run. If that fails:
```bash
pip3 install customtkinter --break-system-packages
```

---

## 📦 Dependencies

| Package | Purpose | Auto-installed? |
|---|---|---|
| `customtkinter` | Modern dark UI framework for Python/Tkinter | ✅ Yes |
| `tkinter` | Bundled with Python 3 on macOS | — Built-in |
| `xcodeproj` gem | Widget linking via Xcode project API | Attempted at runtime |
| `cocoapods` | iOS dependency management | Manual |

---

## 🛠️ Architecture

```
build_tool.py
│
├── MobileBuildTool (ctk.CTk)
│   ├── _build_header()         — top bar
│   ├── _build_left_panel()     — settings scroll panel
│   ├── _build_right_panel()    — log output + toolbar
│   └── _build_statusbar()      — bottom status bar
│
├── Project Detection
│   ├── _detect_type()
│   ├── _load_flutter_meta()
│   ├── _load_rn_meta()
│   └── _detect_widget()
│
├── Build Engine  (background threads)
│   ├── _build_flutter()
│   ├── _build_rn()
│   ├── _build_rn_ios()
│   ├── _build_rn_android()
│   ├── _collect_ipa()
│   └── _collect_apk()
│
├── Widget Linking
│   ├── _do_widget_link()
│   ├── _write_ruby_script()
│   ├── _run_ruby()
│   ├── _manual_link()
│   └── _check_widget_health()
│
└── Logging
    ├── _queue()     — thread-safe enqueue
    ├── _log()       — main-thread direct insert
    ├── _classify_line()
    ├── _filter_logs()
    └── _write_summary()
```

---

## 🎨 UI Design

- **Colour scheme** — deep navy dark theme with cyan/purple accents
- **Fonts** — SF Pro Display for UI, Menlo for code/logs
- **Left panel** — scrollable settings, never clips content
- **Right panel** — resizable log viewer with horizontal + vertical scroll
- **Responsive** — uses grid weights; resizes cleanly from 900 px to full-screen
- **Progress bar** — tracks each build stage with descriptive labels
- **Elapsed timer** — live seconds counter in the status bar during builds

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">

**Made with 🖤 for mobile developers who want fast, clean builds.**

</div>
