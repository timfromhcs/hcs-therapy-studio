# Installing the local inference runtime

The product does not bundle `llama.cpp` in git. It supervises an official
release binary that you install once into the per-user data directory.

## One command

```powershell
pwsh -File scripts/bootstrap/fetch_llama_server.ps1
```

The script downloads the **pinned** release (`b12102`,
commit `bbb02c93…f9a7`), verifies the SHA-256
(`b322f7d6…de08`) and unpacks it to:

```
%LOCALAPPDATA%\HCS\TherapyStudio\runtime\llama-server.exe
```

If the hash does not match, it deletes the download and refuses to install. There
is no "continue anyway" flag, on purpose.

Manual alternative: set `HCS_LLAMA_SERVER` to the full path of any
`llama-server.exe` you trust. `hcs-therapy doctor` reports which binary it found.

## Why the Vulkan build also gives you CPU

The Vulkan build ships the CPU backend as well. `--backend cpu` in this project
means "zero GPU layers on the same binary", not "a second download". Switching
backends therefore never requires reinstalling anything.

```powershell
hcs-therapy doctor --json      # Vulkan device + selected profile
hcs-therapy runtime status     # which binary, which profile
```

## Installing a model

```powershell
hcs-therapy models list
hcs-therapy models install qwen3-1.7b-gguf-q8-0 --accept-license
hcs-therapy models verify qwen3-1.7b-gguf-q8-0
```

The download is resumable, is verified against the SHA-256 pinned in
`models/manifests/*.yaml`, and is only promoted to its final name after the hash
matches. An interrupted download leaves a `.part` file, never a usable-looking
truncated model.

## Smoke test

```powershell
hcs-therapy runtime smoke --backend cpu --json
hcs-therapy runtime smoke --backend vulkan --json
```

`runtime smoke` starts the sidecar, waits for `/health`, sends one short
completion, reports load time, completion tokens, tokens/second and the sample
text, then stops the process. It exits non-zero when generation produces nothing.

Add `--model <id>` to choose a model explicitly, `--max-tokens` to shorten the
generation, and `--timeout` when the first load is slow on a cold cache.

## What can go wrong

| Symptom | Cause | Fix |
|---|---|---|
| `llama-server binary not found` | runtime not installed | run the bootstrap script |
| `exited early with code …` | bad model path, unsupported quant, OOM | read the log path that the error prints |
| `did not become ready within …s` | model too large for the current free RAM, or a slow disk | close applications, or use a smaller quantisation |
| Vulkan run fails but CPU works | driver/ICD issue | `--backend cpu`; report the driver version |

## Memory honesty

`runtime smoke` uses the profile the app computed from *measured* free RAM. On
this development machine the integrated Radeon's 9.35 GiB heap is **shared** with
system RAM, so the budget is the lower of the heap share and the safe RAM commit.
A machine with a browser and an IDE open gets a smaller context than the same
machine at rest. That is intentional: the alternative is promising VRAM that does
not exist and taking the desktop down with it.
