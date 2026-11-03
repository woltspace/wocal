# Wocal

Local vocal wolts: speech and transcription on your own Mac, behind one server.

> **Heads-up: Apple Silicon Macs only, for now.** The transcription model runs on mlx,
> so this version won't run on Linux, Windows or Intel Macs. In a lodge, it needs a native
> lodge: a container lodge can't reach a server on its host's `127.0.0.1`.

## Run it

You need [uv](https://docs.astral.sh/uv/) and ffmpeg (`brew install ffmpeg`).

```bash
uvx --from git+https://github.com/woltspace/wocal wocal serve
```

It listens on `http://127.0.0.1:4077`, on this machine only, and works with anything that speaks
the OpenAI audio API:

```bash
curl http://127.0.0.1:4077/v1/audio/speech -H 'content-type: application/json' \
  -d '{"input":"Hello from the lodge.","voice":"alba","response_format":"mp3"}' -o hello.mp3
curl http://127.0.0.1:4077/v1/audio/transcriptions -F file=@hello.mp3
```

The first run downloads both models, a few GB. Open `http://127.0.0.1:4077/` to see when they
are ready; a request made before then waits.

## Add it to your lodge

Tell a wolt: "Add Wocal to the lodge, from https://github.com/woltspace/wocal". Or run this from a
wolt's session:

```bash
LODGE="$(woltspace paths | sed -n 's/^endpoint: //p')"
APPS="$(woltspace paths | sed -n 's/^wolts_dir: //p')/apps"
git clone https://github.com/woltspace/wocal "$APPS/wocal"
cd "$APPS/wocal" && uv sync
curl -X PUT "$LODGE/apps/wocal" -H 'content-type: application/json' -d "{\"keeper\":\"$WOLT_NAME\"}"
curl -X POST "$LODGE/apps/wocal/start"
uv run wocal connect
```

Then send your wolt a voice note and ask it to answer with `notify --speak`. If port 4077 is taken,
change `port` in `woltspace.json`, then use `wocal connect --port <port>`.

The lodge starts Wocal again whenever the lodge itself starts, as with any app you left running.
If Wocal is down, voice notes fail to transcribe and `--speak` falls back to text.

To undo it: `uv run wocal disconnect` puts the lodge back on its default speech and transcription
service, then stop the app from the lodge.

## Good to know

- Voices: alba, marius, javert, jean, cosette, fantine, eponine, azelma, anna, vera, charles, paul,
  george, mary, jane, michael, eve, estelle, lola, giovanni, juergen, rafael, daan.
  Pick one with `wocal connect --voice marius`.
- Names you made up get misheard: Parakeet turned "woltspace" into "wolves base".
- The server has no key. It only listens on this machine and refuses other hostnames.

## Credits

- Speech: [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) by Kyutai (code MIT, weights CC-BY-4.0).
- Transcription: Parakeet TDT 0.6 v3 by NVIDIA (CC-BY-4.0), through
  [mlx-audio](https://github.com/Blaizzy/mlx-audio).
- Wocal itself is MIT.
