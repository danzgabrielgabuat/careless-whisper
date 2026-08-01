# Careless Whisper 🎙️

A desktop audio transcription app built with Python and Tkinter, powered by 
OpenAI Whisper for transcription and Ollama/Qwen for AI-assisted cleanup.

Built during my internship at DOST-CLSU to solve a real problem — staff 
had to manually transcribe recorded interviews, which took hours. This app 
automates the process.

## Features
- Transcribe audio files (MP3, WAV, M4A, MP4, OGG, FLAC, WEBM)
- Multiple Whisper model sizes (tiny, base, small, medium, large-v2)
- Auto-detect language or set manually
- Live transcript display with timestamps
- AI-powered cleanup via Ollama/Qwen 2.5:3b
- Glossary support for domain-specific terms
- Auto-saves transcript to .txt file

## Requirements
- Python 3.8+
- OpenAI Whisper
- Ollama (for AI cleanup) with qwen2.5:3b pulled

## Installation
```bash
pip install openai-whisper tkinter
```

For AI cleanup, install Ollama from ollama.com then:
```bash
ollama pull qwen2.5:3b
```

## Usage
```bash
python desktop/careless_whisper.py
```

## Built With
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Ollama](https://ollama.com)
- Python Tkinter

## Author
Danz Gabriel S. Gabuat — BS Mathematics, Computer Applications
