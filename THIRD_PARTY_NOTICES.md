# Third-party notices

Generated 2026-11-04 from `licenses/manifest.yaml`.
Every component below is audited before it may be bundled. Entries with
`approved: false` are shortlisted but **not** shipped.

| id | name | publisher | licence | revision | source |
|---|---|---|---|---|---|
| `qwen3-1.7b-base` | Qwen3-1.7B-Base | Qwen | Apache-2.0 | `ea980cb0a6c2` | https://huggingface.co/Qwen/Qwen3-1.7B-Base |
| `qwen3-1.7b-instruct` | Qwen3-1.7B | Qwen | Apache-2.0 | `70d244cc86cc` | https://huggingface.co/Qwen/Qwen3-1.7B |
| `qwen3-1.7b-gguf` | Qwen3-1.7B-GGUF (official Q8_0) | Qwen | Apache-2.0 | `90862c4b9d27` | https://huggingface.co/Qwen/Qwen3-1.7B-GGUF |
| `smollm3-3b` | SmolLM3-3B | HuggingFaceTB | Apache-2.0 | `a07cc9a04f16` | https://huggingface.co/HuggingFaceTB/SmolLM3-3B |
| `granite-3.3-2b-instruct` | Granite 3.3 2B Instruct | IBM | Apache-2.0 | `707f574c6205` | https://huggingface.co/ibm-granite/granite-3.3-2b-instruct |
| `qwen3-vl-2b-instruct` | Qwen3-VL-2B-Instruct | Qwen | Apache-2.0 | `89644892e4d8` | https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct |
| `smolvlm2-2.2b-instruct` | SmolVLM2-2.2B-Instruct | HuggingFaceTB | Apache-2.0 | `482adb537c02` | https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct |
| `sana-sprint-1.6b` | Sana Sprint 1.6B | Efficient-Large-Model | Apache-2.0 | `unpinned` | https://huggingface.co/Efficient-Large-Model/Sana_Sprint_1.6B_1024px | *(not approved — not shipped)*
| `pixart-sigma` | PixArt-Sigma | PixArt-alpha | OpenRAIL++-M | `unpinned` | https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS | *(not approved — not shipped)*
| `cbt-bench` | CBT-Bench | Psychotherapy-LLM | CC-BY-NC-4.0 | `unpinned` | https://huggingface.co/datasets/Psychotherapy-LLM/CBT-Bench | *(not approved — not shipped)*
| `esconv` | ESConv | thu-coai | CC-BY-NC-4.0 | `unpinned` | https://github.com/thu-coai/Emotional-Support-Conversation | *(not approved — not shipped)*
| `llama-cpp-runtime` | llama.cpp (llama-server) | ggml-org | MIT | `unpinned` | https://github.com/ggml-org/llama.cpp | *(not approved — not shipped)*

## Deliberately not used

| id | reason |
|---|---|
| `esconv` | upstream is academic-research-only and CC BY-NC 4.0 |
| `cbt-bench` | CC BY-NC 4.0: evaluation only where permitted, never bundled |
| `pixart-sigma` | OpenRAIL++-M does not pass the strict permissive filter |
| `janus-pro` | DeepSeek Model Licence has use-based conditions |
| `sana-*` | depends on Gemma-2 text encoder with separate terms |
| `qwen-image-edit` | 20B parameters, exceeds the target device budget |
