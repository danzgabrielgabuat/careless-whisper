import os
import threading
import queue
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

SUPPORTED   = (".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".webm")
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL   = "http://localhost:11434"

BG      = "#FFFFFF"
BG2     = "#F8FAF8"
BG3     = "#F0F7F0"
BORDER  = "#D8E8D8"
BORDER2 = "#C0D8C0"
GREEN   = "#2D6A2D"
GREEN2  = "#3D7A3D"
GREEN_L = "#EEF6EE"
GREEN_T = "#5A8A5A"
MUTED   = "#8AAA8A"
MUTED2  = "#B0C8B0"
TEXT    = "#1A2E1A"
TS_CLR  = "#4A8A4A"
RED     = "#C0392B"
GOLD    = "#B8860B"
GOLD_L  = "#FFFBF0"
BLUE    = "#1E4A8A"
BLUE_L  = "#EEF3FF"

FONT_TITLE = ("Georgia", 16, "bold")
FONT_SUB   = ("Segoe UI", 8)
FONT_LBL   = ("Segoe UI", 8, "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_MONO  = ("Courier New", 9, "bold")
FONT_BTN   = ("Segoe UI", 10, "bold")
FONT_SM    = ("Segoe UI", 8)

MSG_STATUS  = "status"
MSG_SEGMENT = "segment"
MSG_DONE    = "done"
MSG_ERROR   = "error"
MSG_CLEANED = "cleaned"

MODE_LOCAL = "Local (Offline)"

Base = TkinterDnD.Tk if HAS_DND else tk.Tk


def _ollama_status():
    """Returns 'running', 'installed', or 'missing'."""
    try:
        import urllib.request
        urllib.request.urlopen(OLLAMA_URL, timeout=2)
        return "running"
    except Exception:
        pass
    # check if ollama binary exists
    try:
        subprocess.run(["ollama", "--version"],
                       capture_output=True, timeout=3)
        return "installed"
    except Exception:
        return "missing"


class CarelessWhisper(Base):
    def __init__(self):
        super().__init__()
        self.title("Careless Whisper")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(580, 760)

        self._full_path   = None
        self._running     = False
        self._cleaning    = False
        self._segments    = []
        self._queue       = queue.Queue()
        self._show_ts     = tk.BooleanVar(value=True)
        self._status_var  = tk.StringVar(value="Ready")
        self._file_var    = tk.StringVar(value="No file selected")
        self._model_var   = tk.StringVar(value="large-v2")
        self._lang_var    = tk.StringVar(value="Auto-detect")
        self._ollama_var  = tk.StringVar(value="Checking Ollama...")
        self._ph          = True
        self._job         = {}

        self._build()
        self._center()
        self._poll_queue()
        self.after(500, self._check_ollama_status)

    def _center(self):
        self.update_idletasks()
        w  = max(self.winfo_width(), 580)
        h  = max(self.winfo_height(), 760)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Queue poll ────────────────────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                msg_type, payload = self._queue.get_nowait()
                if msg_type == MSG_STATUS:
                    self._prog_lbl.config(text=payload[0])
                elif msg_type == MSG_SEGMENT:
                    self._add_segment(*payload)
                elif msg_type == MSG_DONE:
                    self._done(payload[0])
                elif msg_type == MSG_ERROR:
                    self._error(payload[0])
                elif msg_type == MSG_CLEANED:
                    self._apply_cleaned(payload[0])
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ── BUILD UI ──────────────────────────────────────────────────────────────
    def _build(self):

        # ── Scrollable canvas wrapper ────────────────────────────
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical",
                                  command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        c = tk.Frame(canvas, bg=BG, padx=24, pady=20)
        self._canvas_window = canvas.create_window(
            (0, 0), window=c, anchor="nw")

        def _on_frame_resize(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_resize(event):
            canvas.itemconfig(self._canvas_window, width=event.width)

        c.bind("<Configure>", _on_frame_resize)
        canvas.bind("<Configure>", _on_canvas_resize)

        # mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._brand(c)
        self._sep(c)
        self._audio_zone(c)
        self._controls(c)
        self._progress_bar(c)
        self._sep(c)
        self._transcript_area(c)
        self._ollama_area(c)
        self._footer(c)

    def _brand(self, p):
        row = tk.Frame(p, bg=BG)
        row.pack(fill="x", pady=(0, 4))
        left = tk.Frame(row, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="Careless Whisper",
                 bg=BG, fg=TEXT, font=FONT_TITLE).pack(anchor="w")
        tk.Label(left, text="Let Whisper do it. Carelessly.\nOffline. Accurate. Yours.",
                 bg=BG, fg=MUTED, font=FONT_SUB).pack(anchor="w")
        self._badge = tk.Label(row, textvariable=self._status_var,
                               bg=GREEN_L, fg=GREEN,
                               font=("Segoe UI", 9, "bold"),
                               padx=10, pady=4)
        self._badge.pack(side="right", anchor="e")

    def _sep(self, p):
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", pady=8)

    def _audio_zone(self, p):
        self._dz = tk.Frame(p, bg=BG3, highlightthickness=1,
                            highlightbackground=BORDER2, cursor="hand2")
        self._dz.pack(fill="x", ipady=14)
        tk.Label(self._dz, text="\U0001f3b5", bg=BG3,
                 font=("Segoe UI", 20)).pack()
        tk.Label(self._dz, text="Drag & drop audio file here",
                 bg=BG3, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack()
        tk.Label(self._dz,
                 text="or click to browse  \u00b7  MP3  WAV  M4A  MP4  OGG  FLAC  WEBM",
                 bg=BG3, fg=MUTED, font=FONT_SM).pack(pady=(2, 0))
        tk.Label(self._dz, textvariable=self._file_var,
                 bg=BG3, fg=GREEN,
                 font=("Segoe UI", 9, "bold")).pack(pady=(6, 0))
        for w in [self._dz] + list(self._dz.winfo_children()):
            w.bind("<Button-1>", lambda e: self._browse())
        if HAS_DND:
            self._dz.drop_target_register(DND_FILES)
            self._dz.dnd_bind("<<Drop>>", self._on_drop)

    def _controls(self, p):
        self._controls_row = tk.Frame(p, bg=BG)
        self._controls_row.pack(fill="x", pady=(10, 0))
        self._model_frame = tk.Frame(self._controls_row, bg=BG)
        self._model_frame.pack(side="left")
        tk.Label(self._model_frame, text="MODEL", bg=BG, fg=GREEN_T,
                 font=FONT_LBL).pack(anchor="w")
        ttk.Combobox(self._model_frame, textvariable=self._model_var,
                     values=["tiny", "base", "small", "medium", "large-v2"],
                     state="readonly", width=12,
                     font=FONT_BODY).pack(anchor="w", pady=(4, 0))
        ll = tk.Frame(self._controls_row, bg=BG)
        ll.pack(side="left", padx=(20, 0))
        tk.Label(ll, text="LANGUAGE", bg=BG, fg=GREEN_T,
                 font=FONT_LBL).pack(anchor="w")
        ttk.Combobox(ll, textvariable=self._lang_var,
                     values=["Auto-detect", "Filipino / Tagalog", "English",
                             "Mixed (auto-detect)"],
                     state="readonly", width=20,
                     font=FONT_BODY).pack(anchor="w", pady=(4, 0))
        self._btn = tk.Button(self._controls_row,
                              text="\U0001f3a4  Transcribe",
                              bg=GREEN, fg="white",
                              font=FONT_BTN, relief="flat",
                              padx=20, pady=8, cursor="hand2",
                              activebackground=GREEN2,
                              activeforeground="white",
                              command=self._start)
        self._btn.pack(side="right")
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=BG2, background=BG2,
                    foreground=TEXT, bordercolor=BORDER,
                    arrowcolor=GREEN, selectbackground=GREEN_L,
                    selectforeground=TEXT)
        # model accuracy note
        note_frame = tk.Frame(p, bg=GOLD_L, highlightthickness=1,
                              highlightbackground="#FFFFFF")
        note_frame.pack(fill="x", pady=(8, 0))
        tk.Label(note_frame, text="\u26a0\ufe0f  Model Note",
                 bg=GOLD_L, fg=GOLD, font=FONT_LBL).pack(
                 side="left", padx=(10, 6), pady=6)
        tk.Label(note_frame,
                 text="larger models = better accuracy but slower & more RAM. "
                      "\ntiny/base/small \u2248 1 \u2013 2 GB \u00b7 medium \u2248 5 GB \u00b7 large-v2 \u2248 10 GB",
                 bg=GOLD_L, fg=GOLD, font=FONT_SM,
                 wraplength=420, justify="left").pack(
                 side="left", pady=6, padx=(0, 10))

    def _progress_bar(self, p):
        pf = tk.Frame(p, bg=BG)
        pf.pack(fill="x", pady=(10, 0))
        self._prog_lbl = tk.Label(pf, text="", bg=BG, fg=MUTED, font=FONT_SM)
        self._prog_lbl.pack(anchor="w")
        self._track = tk.Frame(pf, bg=BORDER, height=5)
        self._track.pack(fill="x", pady=(4, 0))
        self._prog_fill = tk.Frame(self._track, bg=GREEN, height=5)
        self._prog_fill.place(x=0, y=0, relheight=1, width=0)

    def _transcript_area(self, p):
        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="LIVE TRANSCRIPT",
                 bg=BG, fg=GREEN_T, font=FONT_LBL).pack(side="left")
        tk.Checkbutton(hdr, text="\u23f1 Timestamps",
                       variable=self._show_ts,
                       bg=BG, fg=GREEN_T, font=FONT_SM,
                       activebackground=BG, selectcolor=BG,
                       command=self._refresh_transcript,
                       cursor="hand2").pack(side="right")
        tf = tk.Frame(p, bg=BORDER, padx=1, pady=1)
        tf.pack(fill="both", expand=True, pady=(6, 0))
        inner = tk.Frame(tf, bg=BG)
        inner.pack(fill="both", expand=True)
        self._txt = tk.Text(inner, bg=BG, fg=TEXT,
                            font=FONT_BODY, relief="flat",
                            wrap="word", padx=12, pady=10,
                            height=14, state="disabled",
                            cursor="arrow", spacing1=2, spacing2=4)
        sb = ttk.Scrollbar(inner, orient="vertical", command=self._txt.yview)
        self._txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._txt.pack(fill="both", expand=True)
        self._txt.tag_configure("ts",   foreground=TS_CLR, font=FONT_MONO)
        self._txt.tag_configure("body", foreground=TEXT,   font=FONT_BODY)
        bf = tk.Frame(p, bg=BG)
        bf.pack(fill="x", pady=(8, 0))
        self._word_lbl = tk.Label(bf, text="", bg=BG, fg=MUTED, font=FONT_SM)
        self._word_lbl.pack(side="left")
        tk.Button(bf, text="\U0001f4be  Save Transcript",
                  bg=BG, fg=GREEN,
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=5,
                  highlightthickness=1,
                  highlightbackground=BORDER2,
                  activebackground=GREEN_L,
                  command=self._save).pack(side="right")

    def _ollama_area(self, p):
        self._sep(p)
        # header row
        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="AI CLEANUP",
                 bg=BG, fg=GREEN_T, font=FONT_LBL).pack(side="left")
        self._ollama_status_lbl = tk.Label(
            hdr, textvariable=self._ollama_var,
            bg=BG, fg=MUTED, font=FONT_SM)
        self._ollama_status_lbl.pack(side="left", padx=(10, 0))
        self._clean_btn = tk.Button(
            hdr, text="\u2728  Clean with Qwen",
            bg=BLUE_L, fg=BLUE,
            font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=4,
            highlightthickness=1,
            highlightbackground="#A0B8E8",
            activebackground="#D8E4F8",
            state="disabled",
            command=self._start_clean)
        self._clean_btn.pack(side="right")

        # glossary box
        tk.Label(p, text="Glossary terms for Qwen to fix  \u2014  one per line  "
                         "(e.g. acronyms, names, slangs, ...)",
                 bg=BG, fg=MUTED, font=FONT_SM).pack(
                 anchor="w", pady=(6, 4))
        gf = tk.Frame(p, bg=BORDER, padx=1, pady=1)
        gf.pack(fill="x")
        inner = tk.Frame(gf, bg=BG)
        inner.pack(fill="both")
        self._glossary = tk.Text(inner, bg=BG, fg=TEXT,
                                 font=FONT_BODY, relief="flat",
                                 wrap="word", padx=12, pady=8,
                                 height=4, spacing1=2)
        self._glossary.pack(fill="both", expand=True)
        ph = "Sir Danz\nDOST\nYIP\nPCIEERD"
        self._glossary.insert("1.0", ph)
        self._glossary.config(fg=MUTED)
        self._ph = True

        def _fi(e):
            if self._ph:
                self._glossary.delete("1.0", "end")
                self._glossary.config(fg=TEXT)
                self._ph = False

        def _fo(e):
            if not self._glossary.get("1.0", "end").strip():
                self._glossary.insert("1.0", ph)
                self._glossary.config(fg=MUTED)
                self._ph = True

        self._glossary.bind("<FocusIn>",  _fi)
        self._glossary.bind("<FocusOut>", _fo)

        # clean progress label
        self._clean_lbl = tk.Label(p, text="", bg=BG, fg=BLUE,
                                   font=FONT_SM)
        self._clean_lbl.pack(anchor="w", pady=(4, 0))

    def _footer(self, p):
        self._sep(p)
        tk.Label(p, text="By Danz Gabriel S. Gabuat | Built with Claude | Powered by Whisper + Ollama Qwen 2.5:3b",
                 bg=BG, fg=MUTED2, font=FONT_SM).pack(
                 anchor="w", pady=(0, 4))

    # ── Ollama status check ───────────────────────────────────────────────────
    def _check_ollama_status(self):
        def _check():
            status = _ollama_status()
            self.after(0, self._update_ollama_ui, status)
        threading.Thread(target=_check, daemon=True).start()

    def _update_ollama_ui(self, status):
        if status == "running":
            self._ollama_var.set("\u25cf Ollama running")
            self._ollama_status_lbl.config(fg="#2D9A2D")
            if self._segments:
                self._clean_btn.config(state="normal")
        elif status == "installed":
            self._ollama_var.set("\u25cf Ollama installed but not running")
            self._ollama_status_lbl.config(fg=GOLD)
            self._clean_lbl.config(
                text="Start Ollama first: open a terminal and run 'ollama serve'")
        else:
            self._ollama_var.set("\u25cf Ollama not installed")
            self._ollama_status_lbl.config(fg=RED)
            self._clean_lbl.config(
                text="Install Ollama from https://ollama.com/download then restart the app")

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _browse(self):
        if self._running:
            return
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files",
                        "*.mp3 *.mp4 *.wav *.m4a *.ogg *.flac *.webm"),
                       ("All files", "*.*")])
        if path:
            self._set_file(path)

    def _on_drop(self, event):
        path = event.data.strip().strip("{}")
        if os.path.isfile(path) and path.lower().endswith(SUPPORTED):
            self._set_file(path)
        else:
            self._set_status("Unsupported file type", error=True)

    def _set_file(self, path):
        self._full_path = path
        self._file_var.set(f"\U0001f4c2  {os.path.basename(path)}")
        self._set_status("Ready")

    def _set_status(self, text, error=False):
        self._status_var.set(text)
        self._badge.config(bg="#FDECEA" if error else GREEN_L,
                           fg=RED      if error else GREEN)

    def _lang_code(self):
        return {
            "Auto-detect":         None,
            "Filipino / Tagalog":  "tl",
            "English":             "en",
            "Mixed (auto-detect)": None,
        }.get(self._lang_var.get(), None)

    def _start(self):
        if self._running:
            return
        if not self._full_path:
            messagebox.showwarning("No file",
                                   "Please select an audio file first.")
            return
        if not HAS_WHISPER:
            messagebox.showerror("Whisper not installed",
                                 "Run:  pip install openai-whisper")
            return

        # read glossary on main thread (safe)
        glossary_terms = (
            "" if self._ph
            else self._glossary.get("1.0", "end").strip()
        )

        self._job = {
            "path":     self._full_path,
            "model":    self._model_var.get(),
            "lang_lbl": self._lang_var.get(),
            "lang":     self._lang_code(),
            "mode":     MODE_LOCAL,
            "api_key":  "",
            "glossary": glossary_terms,
        }
        self._running  = True
        self._segments = []
        self._clean_btn.config(state="disabled")
        self._btn.config(state="disabled", bg=MUTED)
        self._set_status("Transcribing\u2026")
        self._txt.config(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.config(state="disabled")
        self._word_lbl.config(text="")
        self._clean_lbl.config(text="")
        self._prog_fill.place_configure(width=0)
        self._prog_lbl.config(text="Starting\u2026")
        threading.Thread(target=self._run, daemon=True).start()

    # ── Worker: transcription ─────────────────────────────────────────────────
    def _run(self):
        try:
            self._run_local()
        except Exception as e:
            self._queue.put((MSG_ERROR, (str(e),)))

    def _run_local(self):
        q        = self._queue
        job      = self._job
        path     = job["path"]
        mnm      = job["model"]
        lang     = job["lang"]
        lang_lbl = job["lang_lbl"]

        q.put((MSG_STATUS, (f"Loading {mnm} model\u2026",)))
        model    = whisper.load_model(mnm)
        duration = self._get_duration(path)
        outpath, outfile = self._open_outfile(path, mnm, lang_lbl)

        # ── Split audio into 30-second chunks and transcribe each one ─────────
        # This gives live feedback instead of waiting for the whole file.
        CHUNK_SEC = 30
        import numpy as np
        import whisper.audio as wa

        q.put((MSG_STATUS, ("Loading audio\u2026",)))
        # load full audio as float32 numpy array at 16kHz (whisper's native rate)
        audio = wa.load_audio(path)           # shape: (samples,)
        sr    = 16000                          # whisper always uses 16kHz
        total_samples = len(audio)
        chunk_samples = CHUNK_SEC * sr
        n_chunks      = max(1, int(np.ceil(total_samples / chunk_samples)))

        for i in range(n_chunks):
            start_sample = i * chunk_samples
            end_sample   = min(start_sample + chunk_samples, total_samples)
            chunk        = audio[start_sample:end_sample]
            offset_sec   = i * CHUNK_SEC      # seconds from start of file

            pct_start = (offset_sec / duration * 100) if duration else 0
            q.put((MSG_STATUS,
                   (f"Transcribing\u2026  {pct_start:.0f}%  "
                    f"[{self._fmt_time(offset_sec)} / "
                    f"{self._fmt_time(duration)}]",)))

            result = model.transcribe(
                chunk,
                language=lang,
                fp16=False,
                verbose=False,
                initial_prompt=job["glossary"] or None,
            )

            for seg in result.get("segments", []):
                start = seg["start"] + offset_sec   # adjust to global time
                text  = seg["text"].strip()
                if not text:
                    continue
                ts  = self._fmt_time(start)
                pct = min((start / duration * 100) if duration else 0, 99)
                outfile.write(f"[{ts}]  {text}\n")
                outfile.flush()
                q.put((MSG_SEGMENT, (ts, text, pct)))

        outfile.close()
        q.put((MSG_DONE, (outpath,)))

    # ── Worker: Ollama cleanup ────────────────────────────────────────────────
    def _start_clean(self):
        if self._cleaning or not self._segments:
            return
        if _ollama_status() != "running":
            messagebox.showwarning(
                "Ollama not running",
                "Please start Ollama first:\n\nOpen a terminal and run:  ollama serve")
            return

        # read glossary from job dict (already captured on main thread at transcription start)
        # fall back to live glossary box if job has no glossary
        glossary_terms = (
            self._job.get("glossary", "")
            or ("" if self._ph else self._glossary.get("1.0", "end").strip())
        )
        raw_transcript = "\n".join(
            f"[{s['ts']}]  {s['text']}" for s in self._segments)

        self._cleaning = True
        self._clean_btn.config(state="disabled", bg=MUTED2)
        self._clean_lbl.config(text="Checking Qwen model\u2026", fg=BLUE)

        threading.Thread(
            target=self._run_clean,
            args=(raw_transcript, glossary_terms),
            daemon=True).start()

    def _run_clean(self, raw_transcript, glossary_terms):
        import urllib.request, json
        q = self._queue

        # pull model if needed
        try:
            req  = urllib.request.Request(
                f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as r:
                tags = json.loads(r.read())
            model_names = [m["name"] for m in tags.get("models", [])]
            if not any(OLLAMA_MODEL in n for n in model_names):
                q.put((MSG_STATUS,
                       (f"Pulling {OLLAMA_MODEL} for first time...",)))
                self.after(0, self._clean_lbl.config,
                           {"text": f"Downloading {OLLAMA_MODEL}\u2026 "
                                    "this only happens once, may take a few minutes.",
                            "fg": GOLD})
                subprocess.run(["ollama", "pull", OLLAMA_MODEL],
                               check=True)
        except Exception as e:
            q.put((MSG_ERROR, (f"Ollama check failed: {e}",)))
            self.after(0, self._clean_done, False)
            return

        self.after(0, self._clean_lbl.config,
                   {"text": "Cleaning transcript with Qwen\u2026", "fg": BLUE})

        # build prompt
        glossary_block = (
            f"\n\nKnown terms and names to use:\n{glossary_terms}"
            if glossary_terms else "")

        prompt = (
            "You are a transcript line editor. Your ONLY job is to return a corrected version of the transcript lines below.\n\n"
            "STRICT OUTPUT RULES — violating any of these is a failure:\n"
            "- Output ONLY the corrected transcript lines. Nothing before them. Nothing after them.\n"
            "- Do NOT write any introduction, greeting, summary, explanation, note, or commentary.\n"
            "- Do NOT write phrases like 'Here is', 'Sure!', 'Cleaned transcript:', 'Key points:', or anything similar.\n"
            "- Do NOT add bullet points, headers, or markdown.\n"
            "- Your response must start directly with the first transcript line and end with the last transcript line.\n\n"
            "EDITING RULES:\n"
            "- Fix misheard or misspelled words based on context\n"
            "- Correct capitalization and punctuation\n"
            "- Keep ALL timestamps exactly as they appear (e.g. [00:14])\n"
            "- Keep the exact same number of lines — do not merge, split, or reorder lines\n"
            f"{glossary_block}\n\n"
            "Transcript to clean (output ONLY these lines, corrected):\n"
            f"{raw_transcript}"
        )

        try:
            payload = json.dumps({
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=300) as r:
                result   = json.loads(r.read())
                cleaned  = result.get("response", "").strip()

            q.put((MSG_CLEANED, (cleaned,)))
        except Exception as e:
            q.put((MSG_ERROR, (f"Qwen error: {e}",)))
            self.after(0, self._clean_done, False)

    def _apply_cleaned(self, cleaned_text):
        """Parse cleaned text back into segments and refresh transcript."""
        import re
        lines = [l for l in cleaned_text.splitlines() if l.strip()]
        new_segments = []
        for line in lines:
            m = re.match(r"\[(\d{2}:\d{2})\]\s+(.*)", line)
            if m:
                new_segments.append({"ts": m.group(1), "text": m.group(2).strip()})
            else:
                # no timestamp — append to last segment or create new
                if new_segments:
                    new_segments[-1]["text"] += " " + line.strip()
                else:
                    new_segments.append({"ts": "00:00", "text": line.strip()})

        if new_segments:
            self._segments = new_segments
        else:
            # fallback: no timestamps found, replace as single block
            self._segments = [{"ts": "00:00", "text": cleaned_text.strip()}]

        self._refresh_transcript()
        words = sum(len(s["text"].split()) for s in self._segments)
        self._word_lbl.config(
            text=f"{words} words  \u00b7  {len(self._segments)} segments  \u00b7  \u2728 cleaned")
        self._clean_lbl.config(
            text="\u2705  Transcript cleaned! Review and save.", fg=GREEN)
        self._clean_done(True)

        # auto-save cleaned version
        if self._full_path:
            base     = os.path.splitext(self._full_path)[0]
            outpath  = base + "_transcript_cleaned.txt"
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(f"File     : {os.path.basename(self._full_path)}\n")
                f.write(f"Model    : {self._job.get('model','')}\n")
                f.write(f"Language : {self._job.get('lang_lbl','')}\n")
                f.write(f"Date     : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"Cleaned  : Yes (Qwen {OLLAMA_MODEL})\n")
                f.write("-" * 60 + "\n\n")
                for seg in self._segments:
                    f.write(f"[{seg['ts']}]  {seg['text']}\n"
                            if self._show_ts.get()
                            else f"{seg['text']}\n")

    def _clean_done(self, success):
        self._cleaning = False
        self._clean_btn.config(
            state="normal",
            bg=BLUE_L if success else BLUE_L)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _open_outfile(self, audio_path, model_name, lang_lbl):
        base    = os.path.splitext(audio_path)[0]
        outpath = base + "_transcript.txt"
        f = open(outpath, "w", encoding="utf-8")
        f.write(f"File     : {os.path.basename(audio_path)}\n")
        f.write(f"Model    : {model_name}\n")
        f.write(f"Language : {lang_lbl}\n")
        f.write(f"Date     : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("-" * 60 + "\n\n")
        f.flush()
        return outpath, f

    def _get_duration(self, path):
        try:
            import json
            out = subprocess.check_output(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", path],
                stderr=subprocess.DEVNULL)
            return float(json.loads(out)["format"]["duration"])
        except Exception:
            return 0

    def _fmt_time(self, s):
        return f"{int(s)//60:02d}:{int(s)%60:02d}"

    def _add_segment(self, ts, text, pct):
        self._segments.append({"ts": ts, "text": text})
        self._txt.config(state="normal")
        if self._show_ts.get():
            self._txt.insert("end", f"[{ts}]  ", "ts")
        self._txt.insert("end", text + "\n", "body")
        self._txt.see("end")
        self._txt.config(state="disabled")
        self._track.update_idletasks()
        tw = self._track.winfo_width() or 1
        self._prog_fill.place_configure(width=max(1, int(tw * pct / 100)))
        self._prog_lbl.config(
            text=f"Transcribing\u2026  {pct:.0f}%  [{ts}]")

    def _done(self, outpath):
        self._track.update_idletasks()
        self._prog_fill.place_configure(width=self._track.winfo_width() or 1)
        self._prog_lbl.config(
            text=f"\u2705  Done!  Auto-saved to: {outpath}")
        words = sum(len(s["text"].split()) for s in self._segments)
        self._word_lbl.config(
            text=f"{words} words  \u00b7  {len(self._segments)} segments")
        self._set_status("Done \u2713")
        self._btn.config(state="normal", bg=GREEN)
        self._running = False
        # enable clean button if ollama is running
        if _ollama_status() == "running":
            self._clean_btn.config(state="normal")

    def _error(self, msg):
        self._prog_lbl.config(text=f"\u274c  Error: {msg}")
        self._set_status("Error", error=True)
        self._btn.config(state="normal", bg=GREEN)
        self._running  = False
        self._cleaning = False

    def _refresh_transcript(self):
        self._txt.config(state="normal")
        self._txt.delete("1.0", "end")
        for seg in self._segments:
            if self._show_ts.get():
                self._txt.insert("end", f"[{seg['ts']}]  ", "ts")
            self._txt.insert("end", seg["text"] + "\n", "body")
        self._txt.config(state="disabled")

    def _save(self):
        if not self._segments:
            messagebox.showinfo("Nothing to save", "Transcript is empty.")
            return
        default = (os.path.splitext(
            os.path.basename(self._full_path or "transcript"))[0]
            + "_transcript.txt")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile=default,
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"File     : {os.path.basename(self._full_path)}\n")
                f.write(f"Model    : {self._job.get('model', '')}\n")
                f.write(f"Language : {self._job.get('lang_lbl', '')}\n")
                f.write(f"Date     : "
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("-" * 60 + "\n\n")
                for seg in self._segments:
                    f.write(f"[{seg['ts']}]  {seg['text']}\n"
                            if self._show_ts.get()
                            else f"{seg['text']}\n")
            messagebox.showinfo("Saved", f"Saved to:\n{path}")


if __name__ == "__main__":
    app = CarelessWhisper()
    app.mainloop()