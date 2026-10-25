# Voice options

Offer these at the start of every project (`SKILL.md`, Step 0), with a recommendation. Then
**audition before recording**: put 2–3 candidates in `voice.candidates` and run
`tts_render.py COURSE_DIR --audition`. It records the same line in each voice and plays them.
Never start a long recording without the learner choosing a sample.

| Engine | Quality | Cost and setup | Offline | Status in this repo |
|---|---|---|---|---|
| `edge`: Microsoft neural voices via edge-tts | Very natural, many languages | Free, no key; needs internet while recording | No (playback is offline) | **Tested** (English, Korean) |
| `gemini`: Gemini TTS | Very natural, steerable style | API key (`GEMINI_API_KEY`), pay per use | No | Written from API docs, untested |
| `openai`: OpenAI speech | Natural, steerable with `instructions` | API key (`OPENAI_API_KEY`), pay per use | No | Written from API docs, untested |
| `elevenlabs` | Premium, very expressive | API key (`ELEVENLABS_API_KEY`), paid plans | No | Written from API docs, untested |
| `command`: any local TTS CLI | Varies (good to excellent) | Free; model download (hundreds of MB to several GB) | **Yes** | Generic wrapper |
| `say`: macOS voices | Robotic to decent ("Premium" voices are good) | Free, built in | **Yes** | **Tested** |
| `browser`: built-in voice at runtime | Robotic | Nothing to record; smallest file | **Yes** | **Tested** |

The audition step exists to catch a wrong key, model name or response format before a long
recording. For untested engines, expect to fix a field or two the first time. If an engine fails
twice the same way, stop and read its current docs rather than retrying.

## edge (recommended default)

```json
"voice": { "engine": "edge", "voice": "ko-KR-HyunsuMultilingualNeural", "label": "Hyunsu",
           "candidates": [ { "voice": "ko-KR-SunHiNeural" }, { "voice": "ko-KR-InJoonNeural" }, { "voice": "ko-KR-HyunsuMultilingualNeural" } ] }
```

Run every edge command through `uv run --with edge-tts python scripts/tts_render.py ...`.

- **Listing voices:** `uv run --with edge-tts python scripts/tts_render.py --list-voices edge ko`
  (any locale prefix: `en`, `ja`, `es-MX`, ...).
- **Good starting voices:**
  - Korean: `ko-KR-HyunsuMultilingualNeural` (male; chosen by the first learner), `ko-KR-SunHiNeural`
    (female), `ko-KR-InJoonNeural` (male).
  - English: `en-US-AndrewMultilingualNeural`, `en-US-AvaMultilingualNeural`, `en-US-EmmaMultilingualNeural`,
    `en-GB-SoniaNeural`.
  - Japanese: `ja-JP-NanamiNeural`, `ja-JP-KeitaNeural`. Chinese: `zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`.
  - Spanish: `es-ES-ElviraNeural`, `es-MX-DaliaNeural`. French: `fr-FR-DeniseNeural`.
    German: `de-DE-KatjaNeural`.
- **Optional fields:** `"rate": "+10%"`, `"pitch": "-2Hz"`.
- **If requests fail with HTTP 403:** upgrade edge-tts (`uv run --with "edge-tts@latest" ...`).
  The service changes its handshake from time to time.

## gemini

```json
"voice": { "engine": "gemini", "voice": "Kore", "model": "gemini-2.5-flash-preview-tts",
           "style": "Read calmly, like a patient tutor" }
```

- Prebuilt voices include Kore, Puck, Charon, Fenrir, Aoede and Zephyr.
- The model name changes as previews graduate. Check the current TTS model in Google's docs.
- Output is raw 24 kHz PCM; the script converts it to MP3.

## openai

```json
"voice": { "engine": "openai", "voice": "coral", "model": "gpt-4o-mini-tts",
           "instructions": "Warm, unhurried, clear articulation." }
```

Voices include alloy, ash, coral, echo, fable, nova, onyx, sage and shimmer. Speak the course
language in the input text; the model follows it.

## elevenlabs

```json
"voice": { "engine": "elevenlabs", "voice": "<voice_id>", "model": "eleven_multilingual_v2" }
```

Find a `voice_id` in the ElevenLabs voice library.

## command (local, open-source, offline)

The command gets the text on stdin, or as `{text}` if you include it, and must write a WAV file
to `{out}`.

```json
"voice": { "engine": "command", "voice": "piper-en-lessac", "command": "piper --model en_US-lessac-medium.onnx --output_file {out}" }
```

- **Piper:** very fast on CPU, many languages, slightly synthetic. Check that a voice exists for
  your language.
- **Kokoro-82M:** small and natural. English, Japanese, Chinese, Spanish, French, Hindi, Italian,
  Portuguese (no Korean).
- **MeloTTS:** English, Spanish, French, Chinese, Japanese, Korean. CPU real-time.
- **Qwen3-TTS (Alibaba):** high quality, multilingual including Korean. Runs on Apple Silicon via
  `mlx-audio`. Downloads are 1.2–4 GB, so ask before downloading. It is slow: expect roughly
  real-time or slower on an M-series laptop.
- `voice` is only a label here. It goes into the cache key, so change it when you change models.
- Check each tool's `--help` for its exact flags; they change between releases.

## say (macOS)

```json
"voice": { "engine": "say", "voice": "Yuna" }
```

- **Listing voices:** `say -v '?'`, or `python3 scripts/tts_render.py --list-voices say ko_KR`.
- **Better voices:** download "Premium" or "Enhanced" voices in System Settings → Accessibility →
  Spoken Content → System voice → Manage Voices.

## browser

```json
"voice": { "engine": "browser" }
```

Nothing is recorded. The app uses the browser's built-in voice for the course language at
runtime. Set `preferBrowserVoice` (a regex) to pick a specific installed voice. This is also
the automatic fallback whenever a recorded clip is missing or playback is blocked.

## Size and quality

Trimmed clips are 40 kbps mono MP3 (`tts_trim.py --bitrate`), about 0.3 MB per spoken minute, or
0.4 MB once embedded. A 60-minute course is a ~25 MB HTML file. That opens instantly from disk
but exceeds some hosting limits (e.g. 16 MB). For hosting, lower the bitrate to 24k, or host the
browser-voice build.
