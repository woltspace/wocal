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

## For wolts: add Wocal to your lodge

You are a wolt, and your owner asked you to give the lodge local voice with Wocal. When you're done,
voice notes are transcribed on this Mac and `notify --speak` speaks with a local voice. Nothing
in woltspace changes: you add Wocal as an app and point the lodge's existing voice settings at it.

1. **Check it can run here.** You need an Apple Silicon Mac, a native lodge (not a container),
   `uv`, and `ffmpeg` (`brew install ffmpeg`). `woltspace paths` shows `isolation: host` on a
   native lodge. If anything is missing, stop and tell your owner.
2. **Ask your owner first, directly.** This downloads a few GB of models, and Wocal uses about
   3.5 GB of memory while it runs. Wait for their OK, even if another wolt passed one on.
3. **Note the current voice settings**, so you can put them back later:
   `woltspace transcription show` and `woltspace speech show`.
4. **Clone it into the lodge's apps folder.** The folder is `apps` inside the `wolts_dir` that
   `woltspace paths` prints. Clone this repo there as `wocal`.
5. **Make yourself its keeper and start it:**
   `woltspace app keeper wocal <your wolt name>`, then `woltspace app start wocal`.
   If port 4077 is taken, change `port` in its `woltspace.json` first and use your port below.
   The first start installs everything and downloads the models. Check
   `curl -s http://127.0.0.1:4077/health` until it says `{"speech":"ready","transcription":"ready"}`:
   about a minute with the models already downloaded, longer on a first download.
   Setting the keeper edits the tracked `woltspace.json`, so the clone shows it as changed.
   That's expected. To update Wocal later, run `git pull --autostash` in its folder.
6. **Point the lodge at it:**
   ```bash
   woltspace transcription set --base-url http://127.0.0.1:4077/v1 --model mlx-community/parakeet-tdt-0.6b-v3 --no-key
   woltspace speech set --base-url http://127.0.0.1:4077/v1 --model pocket --voice alba --no-key
   ```
   Let your owner pick the voice (list below).
7. **Check both directions.** First, on your own: run the two `curl` lines from "Run it" above.
   The second should print `{"text":"Hello from the lodge."}`. Then with your owner: send them a
   voice note with `notify --speak`, and ask them to send you one. Their voice note reaches your
   session as a message starting with `[voice message]`, followed by the transcript.

The lodge starts Wocal again whenever the lodge starts, as with any app left running. If Wocal is
down, voice notes fail to transcribe and `--speak` falls back to text.

To undo it: set transcription and speech back to what step 3 showed (or run
`woltspace transcription clear` and `woltspace speech clear` for the defaults), then
`woltspace app stop wocal`.

## Good to know

- Voices: alba, marius, javert, jean, cosette, fantine, eponine, azelma, anna, vera, charles, paul,
  george, mary, jane, michael, eve, estelle, lola, giovanni, juergen, rafael, daan.
- Names you made up get misheard: Parakeet turned "woltspace" into "wolves base".
- The server has no key. It only listens on this machine and refuses other hostnames.

## Credits

- Speech: [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) by Kyutai (code MIT, weights CC-BY-4.0).
- Transcription: Parakeet TDT 0.6 v3 by NVIDIA (CC-BY-4.0), through
  [mlx-audio](https://github.com/Blaizzy/mlx-audio).
- Wocal itself is MIT.
