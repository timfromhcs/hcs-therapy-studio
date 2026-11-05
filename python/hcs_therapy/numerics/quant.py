"""Memory and size arithmetic for quantised weights, KV cache and LoRA.

Sources
-------

* GGUF block layouts — ``ggml-quants.h`` in ggml/llama.cpp. Each block type is a
  fixed struct, so the bytes-per-weight figure is arithmetic, not an estimate.
  Q4_0: block of 32 → 2-byte scale + 16 bytes of 4-bit quants = 18 B = 4.5 bpw.
  Q8_0: block of 32 → 2-byte scale + 32 int8 = 34 B = 8.5 bpw.
  Q4_K: super-block of 256 → 2+2+12+128 = 144 B = 4.5 bpw.
  Q5_K: 2+2+12+32+128 = 176 B = 5.5 bpw.
  Q6_K: 128+64+16+2 = 210 B = 6.5625 bpw.
  Q2_K: 16+64+2+2 = 84 B = 2.625 bpw.
* KV cache — ``2 · n_layers · n_kv_heads · head_dim · bytes_per_element`` per
  token (NVIDIA, *Mastering LLM Techniques: Inference Optimization*). The ``2``
  is key plus value; using ``n_kv_heads`` rather than ``n_heads`` is what makes
  grouped-query attention cheap.
* LoRA — Hu et al. (2021). A rank-``r`` adapter on a ``d_in × d_out`` matrix
  adds ``r·(d_in + d_out)`` parameters.
* DoRA — Liu et al., ICML 2024. ``W = m · (W₀ + BA) / ‖W₀ + BA‖_c``, i.e. LoRA
  plus a per-column magnitude vector.

What this module refuses to do: present a single number as if it were certain.
Every function returns the arithmetic and, where reality diverges (unquantised
norms and embeddings, allocator overhead, page alignment), says so explicitly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = [
    "BLOCK_LAYOUTS",
    "KvCacheBudget",
    "QuantInfo",
    "bytes_per_weight",
    "estimate_gguf_bytes",
    "kv_cache_bytes",
    "lora_parameters",
    "quant_info",
]

# quant name -> (weights per block, bytes per block)
BLOCK_LAYOUTS: dict[str, tuple[int, int]] = {
    "Q2_K": (256, 84),
    "Q3_K": (256, 110),
    "Q4_0": (32, 18),
    "Q4_1": (32, 20),
    "Q4_K": (256, 144),
    "Q5_0": (32, 22),
    "Q5_1": (32, 24),
    "Q5_K": (256, 176),
    "Q6_K": (256, 210),
    "Q8_0": (32, 34),
    "Q8_K": (256, 292),
    "F16": (1, 2),
    "BF16": (1, 2),
    "F32": (1, 4),
}


@dataclass(frozen=True)
class QuantInfo:
    name: str
    block_weights: int
    block_bytes: int

    @property
    def bytes_per_weight(self) -> float:
        return self.block_bytes / self.block_weights

    @property
    def bits_per_weight(self) -> float:
        return 8.0 * self.bytes_per_weight

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "block_weights": self.block_weights,
            "block_bytes": self.block_bytes,
            "bits_per_weight": round(self.bits_per_weight, 4),
        }


def quant_info(name: str) -> QuantInfo:
    key = name.upper()
    if key not in BLOCK_LAYOUTS:
        known = ", ".join(sorted(BLOCK_LAYOUTS))
        raise ValueError(f"unknown quantisation {name!r}; known: {known}")
    weights, size = BLOCK_LAYOUTS[key]
    return QuantInfo(key, weights, size)


def bytes_per_weight(name: str) -> float:
    return quant_info(name).bytes_per_weight


def estimate_gguf_bytes(
    n_params: int,
    quantisation: str,
    *,
    quantised_fraction: float = 0.94,
    overhead_bytes: int = 8 * 1024 * 1024,
) -> int:
    """Estimate a GGUF file size.

    ``quantised_fraction`` defaults to 0.94 because a real GGUF keeps token
    embeddings, output head and every norm at higher precision — the llama.cpp
    default recipe quantises roughly that share of the parameters. Pretending
    100 % would under-estimate a 1.7B Q4_K_M file by ~150 MB, which is exactly
    the error that makes a fit check wrong.
    """
    if n_params <= 0:
        raise ValueError("n_params must be positive")
    if not 0.0 < quantised_fraction <= 1.0:
        raise ValueError("quantised_fraction must be within (0, 1]")
    info = quant_info(quantisation)
    quantised = int(n_params * quantised_fraction)
    remaining = n_params - quantised
    total = quantised * info.bytes_per_weight + remaining * 2.0
    return int(math.ceil(total)) + overhead_bytes


@dataclass
class KvCacheBudget:
    per_token_bytes: int
    context: int
    batch: int
    total_bytes: int
    breakdown: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "per_token_bytes": self.per_token_bytes,
            "context": self.context,
            "batch": self.batch,
            "total_mib": round(self.total_bytes / 1024**2, 2),
            **self.breakdown,
        }


def kv_cache_bytes(
    *,
    n_layers: int,
    n_kv_heads: int,
    head_dim: int,
    context: int,
    batch: int = 1,
    bytes_per_element: float = 2.0,
) -> KvCacheBudget:
    """Exact KV-cache footprint for a dense transformer.

    ``bytes_per_element`` of 2 is fp16/bf16; 1.0625 is Q8_0 at 8.5 bpw and
    0.5625 is Q4_0 at 4.5 bpw, which is what cache quantisation buys.
    """
    for label, value in (
        ("n_layers", n_layers),
        ("n_kv_heads", n_kv_heads),
        ("head_dim", head_dim),
        ("context", context),
        ("batch", batch),
    ):
        if value <= 0:
            raise ValueError(f"{label} must be positive")
    if bytes_per_element <= 0:
        raise ValueError("bytes_per_element must be positive")
    per_token = 2 * n_layers * n_kv_heads * head_dim * bytes_per_element
    per_token_bytes = int(math.ceil(per_token))
    total = per_token_bytes * context * batch
    return KvCacheBudget(
        per_token_bytes=per_token_bytes,
        context=context,
        batch=batch,
        total_bytes=total,
        breakdown={
            "n_layers": n_layers,
            "n_kv_heads": n_kv_heads,
            "head_dim": head_dim,
            "bytes_per_element": bytes_per_element,
            "fp16_per_token_bytes": int(math.ceil(2 * n_layers * n_kv_heads * head_dim * 2)),
        },
    )


def lora_parameters(
    modules: dict[str, tuple[int, int]], rank: int, *, magnitude: bool = False
) -> dict[str, object]:
    """Parameter count for a LoRA (or DoRA) adapter.

    ``modules`` maps a module name to ``(d_in, d_out)``. ``magnitude=True`` adds
    the DoRA magnitude vector (``d_out`` per adapted matrix).
    """
    if rank <= 0:
        raise ValueError("rank must be positive")
    per_module: dict[str, int] = {}
    total = 0
    for name, (d_in, d_out) in modules.items():
        if d_in <= 0 or d_out <= 0:
            raise ValueError(f"module {name!r} has a non-positive dimension")
        count = rank * (d_in + d_out)
        if magnitude:
            count += d_out
        per_module[name] = count
        total += count
    return {
        "rank": rank,
        "per_module": per_module,
        "total": total,
        "magnitude": magnitude,
    }


def transformer_lora_parameters(
    *,
    n_layers: int,
    hidden: int,
    intermediate: int,
    rank: int,
    targets: tuple[str, ...] = (
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ),
    magnitude: bool = False,
) -> dict[str, object]:
    """LoRA parameters for a Llama/Qwen-style transformer.

    Square attention projections are ``hidden × hidden``; the MLP has two
    ``hidden → intermediate`` expansions and one contraction back.
    """
    shapes: dict[str, tuple[int, int]] = {
        "q_proj": (hidden, hidden),
        "k_proj": (hidden, hidden),
        "v_proj": (hidden, hidden),
        "o_proj": (hidden, hidden),
        "gate_proj": (hidden, intermediate),
        "up_proj": (hidden, intermediate),
        "down_proj": (intermediate, hidden),
    }
    modules: dict[str, tuple[int, int]] = {}
    for layer in range(n_layers):
        for target in targets:
            if target not in shapes:
                raise ValueError(f"unknown target module {target!r}")
            modules[f"layers.{layer}.{target}"] = shapes[target]
    result = lora_parameters(modules, rank, magnitude=magnitude)
    result["n_layers"] = n_layers
    result["average_per_layer"] = result["total"] // max(n_layers, 1)
    return result
