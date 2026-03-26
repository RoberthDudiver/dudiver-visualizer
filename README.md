<p align="center">
  <img src="icon.png" width="120" alt="Dudiver Visualizer Studio">
</p>

<h1 align="center">Dudiver Visualizer Studio</h1>

<p align="center">
  <strong>Turn any song into a professional lyric video in minutes — not hours.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0-e94560?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4?style=for-the-badge" alt="Windows">
  <img src="https://img.shields.io/badge/python-3.10+-3776ab?style=for-the-badge" alt="Python">
  <img src="https://img.shields.io/badge/license-Personal%20Use-ffd460?style=for-the-badge" alt="License">
</p>

<p align="center">
  <a href="../../releases"><strong>Download Installer</strong></a> ·
  <a href="#how-it-works"><strong>How It Works</strong></a> ·
  <a href="#features"><strong>Features</strong></a> ·
  <a href="#roadmap"><strong>Roadmap</strong></a>
</p>

---

<!-- TODO: Replace with actual screenshots/GIFs -->
<!--
<p align="center">
  <img src="docs/demo.gif" width="720" alt="Demo — Song to lyric video in 3 clicks">
</p>
-->

## The Problem

You made a song. Now you need a lyric video for YouTube, a vertical version for TikTok, and maybe an Instagram square — all synced perfectly to the vocals. Doing this manually in Premiere or After Effects takes **hours per video**. Paying someone costs **$50–200 per video**.

## The Solution

Dudiver Visualizer Studio uses **Whisper AI** to detect exactly when each word is sung, then renders a fully animated lyric video automatically. Three clicks: load audio, paste lyrics, generate.

| Input | Output |
|-------|--------|
| Audio file (MP3/WAV/FLAC) + lyrics | Synced lyric video (MP4/WebM) |
| 1 song | YouTube + TikTok + Instagram + Stories in one session |

---

## How It Works

```
Audio + Lyrics
      │
      ▼
┌─────────────┐
│  Whisper AI  │  ← Detects each word's exact timing
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Sync Editor     │  ← Review & adjust timestamps (manual or AI-assisted)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Render Engine   │  ← Karaoke mode (PIL) or Kinetic Typography (Manim)
└──────┬───────────┘
       │
       ▼
  Final Video (MP4/WebM/MOV with alpha)
```

**The entire pipeline runs locally on your machine.** No cloud, no subscriptions, no watermarks.

---

## Features

### Two Video Modes

| Mode | Description |
|------|-------------|
| **Karaoke** | Classic lyric video — lines highlight as they're sung. Particles, wave, vignette, glow, progress bar. |
| **Kinetic Typography** | Dynamic word-by-word animations powered by Manim. 8 animation styles. |

### Kinetic Typography Styles

| Style | Effect |
|-------|--------|
| Wave | Words rise from below with a wave motion |
| Typewriter | Letters appear one by one |
| Zoom Bounce | Words pop in with scale + bounce |
| Slide | Text slides from alternating sides |
| Fade & Float | Soft fade-in with upward drift |
| Glitch | Digital distortion flash |
| Bounce Drop | Words fall from above with physics |
| Cinematic | Dramatic word-by-word reveal |

### Social Format Presets

| Format | Resolution | Use Case |
|--------|-----------|----------|
| YouTube | 1920×1080 | Standard horizontal video |
| TikTok | 1080×1920 | Vertical short-form |
| Instagram | 1080×1080 | Square feed post |
| Stories | 720×1280 | IG/FB Stories |

### Advanced Sync Editor

After Whisper generates timestamps, open the **Sync Editor** to fine-tune:

- Edit each word's start/end time manually
- Shift all timestamps globally (+/- 50ms)
- Auto-fix overlapping words
- **Re-sync with AI**: Claude Code, Claude API, OpenAI API, or re-run Whisper

### More

- **5 color schemes**: Night, Fire, Ocean, Neon, Gold
- **Real-time preview** with auto-refresh on any config change
- **Custom backgrounds**: image or video
- **Transparent export** (WebM/MOV with alpha) for compositing in Premiere, DaVinci, etc.
- **Promo spot**: add a branded end screen (text, image, or video clip)
- **System font selector**: use any font installed on your machine (185+ detected)
- **GPU acceleration**: NVENC (NVIDIA), QSV (Intel), AMF (AMD)
- **Project save/load**: save your entire workspace and pick up later
- **Bilingual UI**: full Spanish and English interface

---

## Installation

### Option A: Installer (recommended)

1. Download `DudiverVisualizerSetup.exe` from [Releases](../../releases)
2. Run the installer
3. Launch from Start Menu or Desktop shortcut

### Option B: Run from source

```bash
git clone https://github.com/RoberthDudiver/dudiver-visualizer.git
cd dudiver-visualizer
pip install customtkinter pillow numpy moviepy librosa whisper
pip install manim          # only needed for Kinetic Typography mode
python visualizer_app.py
```

**Requirements:**
- Windows 10/11
- Python 3.10+
- FFmpeg in PATH ([download](https://ffmpeg.org/download.html))
- ~2GB disk for Whisper model (downloaded on first use)

---

## Technical Details

| Component | Technology |
|-----------|-----------|
| UI Framework | CustomTkinter (dark theme) |
| AI Sync | OpenAI Whisper (local, word-level timestamps) |
| Karaoke Render | PIL/Pillow + moviepy + ffmpeg |
| Kinetic Render | Manim (3Blue1Brown's animation engine) |
| Beat Detection | librosa |
| Audio Support | MP3, WAV, FLAC, OGG |
| Video Export | MP4 (H.264), WebM (VP9+alpha), MOV (ProRes 4444) |
| GPU Encode | NVENC, QSV, AMF via ffmpeg |
| i18n | ES/EN with persistent settings |

### Architecture

```
visualizer_app.py          ← Thin launcher
app/
├── main.py                ← Entry point + splash screen
├── config.py              ← Constants, color schemes, mode definitions
├── i18n.py                ← Internationalization (ES/EN)
├── core/
│   ├── audio.py           ← Beat analysis (librosa)
│   ├── renderer.py        ← Preview frame generation
│   ├── video.py           ← Full video generation pipeline
│   ├── timestamps.py      ← Whisper timestamp management
│   ├── project.py         ← Save/load project workspace
│   └── spot.py            ← Promo spot generation
├── ui/
│   ├── app.py             ← Main window orchestrator
│   ├── toolbar.py         ← Top bar with actions
│   ├── splash.py          ← Splash screen
│   ├── about.py           ← About window
│   ├── settings.py        ← GPU & language config
│   ├── help_window.py     ← Built-in help guide
│   ├── sync_editor.py     ← Advanced timestamp editor
│   ├── components.py      ← Reusable UI components
│   └── panels/
│       ├── files_panel.py
│       ├── config_panel.py
│       ├── spot_panel.py
│       └── preview_panel.py
└── utils/
    └── fonts.py           ← Font loading utilities
```

---

## Why Not Just Use CapCut / Premiere?

| | CapCut | Premiere | **Dudiver Visualizer** |
|---|---|---|---|
| Auto sync to vocals | Manual or basic | Manual | **Whisper AI word-level** |
| Batch formats | One at a time | One at a time | **All formats in one session** |
| Kinetic typography | Limited presets | After Effects needed | **8 styles built-in** |
| Transparent export | No | Yes (paid) | **Yes (free)** |
| Runs locally | Cloud-dependent | Yes | **Yes, fully offline** |
| Cost | Free (with limits) | $22/month | **Free** |

---

## Known Limitations

- **Windows only** (for now — the UI uses CustomTkinter which is cross-platform, but testing has only been done on Windows 10/11)
- **Whisper model download** takes ~1-2 minutes on first run (base model, ~150MB)
- **Kinetic Typography** requires Manim installed separately (`pip install manim`)
- **Long songs** (5+ min) may take 3-10 minutes to render depending on your hardware
- **GPU acceleration** requires compatible hardware + ffmpeg compiled with the right encoder

---

## Roadmap

- [x] Karaoke mode with effects (particles, glow, vignette)
- [x] Whisper AI word-level sync
- [x] Multiple export formats (YouTube, TikTok, Instagram, Stories)
- [x] Transparent background export (WebM/MOV)
- [x] Kinetic Typography with 8 animation styles (Manim)
- [x] Advanced Sync Editor with AI re-sync
- [x] Project save/load
- [x] Bilingual UI (ES/EN)
- [x] GPU acceleration support
- [ ] macOS / Linux support
- [ ] Batch processing (multiple songs at once)
- [ ] Custom animation presets (save & share your styles)
- [ ] Plugin system for community effects
- [ ] Audio waveform visualization mode
- [ ] Direct upload to YouTube/TikTok

---

## Contributing

Found a bug? Have a feature idea? [Open an issue](../../issues).

Want to contribute code? Fork the repo, create a branch, and submit a PR.

---

## Support the Project

If this tool saved you time, consider:

- Giving this repo a star — it helps others find it
- Following [@dudivermusic](https://instagram.com/dudivermusic) on Instagram or [TikTok](https://tiktok.com/@dudivermusic)
- Sharing a lyric video you made with it (tag me!)

<p align="center">
  <a href="https://instagram.com/dudivermusic"><img src="https://img.shields.io/badge/Instagram-@dudivermusic-E4405F?style=flat-square&logo=instagram&logoColor=white" alt="Instagram"></a>
  <a href="https://tiktok.com/@dudivermusic"><img src="https://img.shields.io/badge/TikTok-@dudivermusic-000000?style=flat-square&logo=tiktok&logoColor=white" alt="TikTok"></a>
  <a href="https://youtube.com/@Dudiver"><img src="https://img.shields.io/badge/YouTube-@Dudiver-FF0000?style=flat-square&logo=youtube&logoColor=white" alt="YouTube"></a>
  <a href="https://open.spotify.com/artist/dudiver"><img src="https://img.shields.io/badge/Spotify-Dudiver-1DB954?style=flat-square&logo=spotify&logoColor=white" alt="Spotify"></a>
</p>

---

<p align="center">
  Made with code and beats by <a href="https://github.com/RoberthDudiver">Dudiver</a> from Venezuela
</p>
