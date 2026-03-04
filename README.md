# TestVideoEditor

A lightweight Windows desktop application for basic MP4 video editing, built with **Python**, **PyQt6**, and **MoviePy**.

## Features

- **Merge Videos** — Combine two or more video files end-to-end into a single MP4.
- **Cut / Trim** — Extract a specific time range from a video by setting a start and end time (in seconds).
- **Audio Editing** — Either mute a video entirely (remove its audio track) or replace the audio with a new file (MP3, WAV, AAC, OGG, M4A).
- **Export** — Save the result as a new MP4 file via a standard file-save dialog.

All processing runs on a background thread so the UI stays responsive, with a progress bar and status messages during export.

## Requirements

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your system PATH

## Installation

```bash
pip install PyQt6 moviepy
```

### Install FFmpeg (Windows)

```bash
winget install Gyan.FFmpeg
```

Or download manually from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your PATH.

## Usage

```bash
python video_editor.py
```

The app opens with three tabs:

| Tab | Description |
|---|---|
| **Merge** | Select 2 or more video files and combine them in order. Click "+ Add another video" to add more clips. |
| **Cut / Trim** | Select a source video, set a start and end time in seconds, and export the trimmed clip. |
| **Audio** | Select a source video, then either check "Mute" to remove audio, or browse for a replacement audio file. |

## Packaging as a Standalone .exe

To distribute the app without requiring Python to be installed:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "VideoEditor" video_editor.py
```

The executable will appear in the `dist/` folder. Note that FFmpeg must still be present on the target machine.

## Tech Stack

- **UI:** PyQt6
- **Video processing:** MoviePy
- **Encoding engine:** FFmpeg
