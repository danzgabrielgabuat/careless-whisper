# Careless Whisper 🎙️

A desktop audio transcription app powered by OpenAI Whisper and Ollama/Qwen,
built as a personal automation initiative during my internship at SERDAC-Luzon.

## Background

During my internship at the **Socio-Economic Research and Data Analytics Center 
(SERDAC-Luzon)** — based inside Central Luzon State University (CLSU) — one of 
my recurring responsibilities was transcribing confidential interviews involving 
mentors and grantees under the **Youth Innovation Program (YIP)**. Recordings 
were often lengthy, and manual transcription required repeatedly listening to 
audio and typing every spoken word. After several days of doing this, it became 
clear the process consumed a significant amount of time and mental effort.

This was not an assigned project. It was a personal automation initiative I 
started after asking myself: *"Can this be automated?"*

I began conceptualizing the idea during my third week of internship, then 
continued developing and testing it during Week 5 when most assigned 
responsibilities had already been completed.

## What it does

- Transcribes audio files locally using OpenAI Whisper — no internet required
- Supports **58 languages** including Filipino/Tagalog with auto-detection
- Live transcript display with timestamps as transcription progresses
- AI-powered cleanup via **Ollama + Qwen 2.5:3b** to fix misheard words,
  correct punctuation, and improve readability
- Glossary input for domain-specific terms, acronyms, and proper nouns
  that Whisper might mishear
- Auto-saves transcript to `.txt` file
- Designed for non-technical users — no command line required

## Supported formats

MP3, WAV, M4A, MP4, OGG, FLAC, WEBM

## Models

| Model | Speed | Accuracy | RAM Required |
|-------|-------|----------|--------------|
| tiny | Fastest | Basic | ~1 GB |
| base | Fast | Good | ~1 GB |
| small | Moderate | Better | ~2 GB |
| medium | Slow | Very good | ~5 GB |
| large-v2 | Slowest | Best | ~10 GB |

## Requirements

- Python 3.8+
- ffmpeg

## Installation

```bash
pip install openai-whisper
```

For AI cleanup (optional), install Ollama from [ollama.com](https://ollama.com) then:

```bash
ollama pull qwen2.5:3b
```

## Usage

```bash
python desktop/careless_whisper.py
```

## Project structure

```
careless-whisper/
├── desktop/
│   └── careless_whisper.py    # Tkinter desktop version (current)
└── README.md
```

> A Streamlit web version is currently in development.

## Tech stack

- [OpenAI Whisper](https://github.com/openai/whisper) — speech recognition
- [Ollama](https://ollama.com) + Qwen 2.5:3b — local AI cleanup
- Python Tkinter — desktop GUI

## Author

**Danz Gabriel S. Gabuat**  
BS Mathematics with Specialization in Computer Applications
Central Luzon State University  
