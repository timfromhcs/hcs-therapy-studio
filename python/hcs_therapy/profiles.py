"""Compute-profile selection.

Profiles are chosen from *measured* facts plus a declared model geometry, never
from a hard-coded GPU name. Every decision returns the numbers and reasons that
produced it so the UI can explain itself instead of hiding a guess.

Design intent from the build contract:

* ``SAFE_CPU`` always available, never a crash-recovery afterthought;
* ``VULKAN_BALANCED`` full offload only when the measured headroom allows it;
* ``VULKAN_LOW_MEMORY`` partial offload with a smaller context;
* context length is a capability claim, so it is derived from a KV-cache
  estimate and only grows after repeated successful loads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .hardware import GIB, HardwareReport

#: Reserved headroom for the UI, the OS, the Python process and the llama.cpp
#: compute buffers. Absolute values, not percentages, because small machines
#: need the floor and large machines do not need the percentage.
MIN_FREE_RESERVE_BYTES = int(1.6 * GIB)

#: Share of available system memory we are willing to commit to a model run.
RAM_COMMIT_FRACTION = 0.62

#: Never touch more than this share of reported device-local memory.
VRAM_COMMIT_FRACTION = 0.75

DEFAULT_CONTEXTS = (2048, 4096, 8192, 16384)


class ProfileName(StrEnum):
    SAFE_CPU = "SAFE_CPU"
    VULKAN_BALANCED = "VULKAN_BALANCED"
    VULKAN_LOW_MEMORY = "VULKAN_LOW_MEMORY"
    BROWSER_WEBGPU = "BROWSER_WEBGPU"
    BROWSER_WASM = "BROWSER_WASM"


@dataclass(frozen=True)
class ModelGeometry:
    """Minimal transformer geometry needed to size a KV cache honestly."""

    n_layers: int
    n_kv_heads: int
    head_dim: int
    n_params: int | None = None

    def kv_bytes_per_token(self, kv_bytes: int = 2) -> int:
        return 2 * self.n_layers * self.n_kv_heads * self.head_dim * kv_bytes

    def kv_cache_bytes(self, context: int, kv_bytes: int = 2) -> int:
        return self.kv_bytes_per_token(kv_bytes) * context


# Qwen3-1.7B: 28 layers, 8 KV heads (GQA), head_dim 128, ~1.72B params.
QWEN3_1_7B = ModelGeometry(n_layers=28, n_kv_heads=8, head_dim=128, n_params=1_720_000_000)
QWEN3_0_6B = ModelGeometry(n_layers=28, n_kv_heads=8, head_dim=128, n_params=596_000_000)


@dataclass
class Assessment:
    profile: ProfileName
    backend: str
    n_gpu_layers: int
    context: int
    #: bytes we expect the runtime to need, excluding the OS and the UI
    estimated_runtime_bytes: int
    #: bytes we measured as safely usable
    budget_bytes: int
    kv_bytes_per_token: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    device_name: str | None = None

    @property
    def estimated_runtime_gib(self) -> float:
        return round(self.estimated_runtime_bytes / GIB, 2)

    @property
    def budget_gib(self) -> float:
        return round(self.budget_bytes / GIB, 2)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.value,
            "backend": self.backend,
            "n_gpu_layers": self.n_gpu_layers,
            "context": self.context,
            "estimated_runtime_gib": self.estimated_runtime_gib,
            "budget_gib": self.budget_gib,
            "kv_bytes_per_token": self.kv_bytes_per_token,
            "device_name": self.device_name,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
        }


def ram_budget(hw: HardwareReport) -> int:
    available = hw.ram_available_bytes or hw.ram_total_bytes
    usable = int(available * RAM_COMMIT_FRACTION) - MIN_FREE_RESERVE_BYTES
    return max(0, usable)


def vram_budget(hw: HardwareReport) -> int:
    if not hw.vulkan.usable:
        return 0
    # Prefer the largest device-local heap: that is what an offload can use.
    device = max(hw.vulkan.devices, key=lambda d: d.device_local_memory_bytes)
    heap_budget = int(device.device_local_memory_bytes * VRAM_COMMIT_FRACTION)
    if device.device_type == "integrated-gpu":
        # An iGPU heap *is* system RAM. Promising the heap size without the RAM
        # constraint is how a tool over-commits a machine and OOMs the desktop.
        return max(0, min(heap_budget, ram_budget(hw)))
    # Even a discrete GPU needs host memory for buffers and the process itself.
    return max(0, min(heap_budget, ram_budget(hw) * 2))


def select_context(
    geometry: ModelGeometry,
    model_bytes: int,
    budget: int,
    *,
    preferred: int | None = None,
    kv_bytes: int = 2,
) -> int:
    """Largest default context whose model+KV fits the budget."""
    candidates = [preferred] if preferred else list(DEFAULT_CONTEXTS)
    chosen = 0
    for ctx in candidates:
        if model_bytes + geometry.kv_cache_bytes(ctx, kv_bytes) <= budget:
            chosen = ctx
    if chosen == 0 and candidates:
        # Fall back to the smallest context even if it is tight; the caller
        # decides whether to warn or refuse.
        chosen = candidates[0]
    return chosen


def assess(
    hw: HardwareReport,
    geometry: ModelGeometry = QWEN3_1_7B,
    model_bytes: int = int(1.05 * GIB),
    *,
    preferred_context: int | None = None,
    kv_bytes: int = 2,
) -> Assessment:
    """Choose the safest profile that can host ``model_bytes`` + KV cache."""
    reasons: list[str] = []
    warnings: list[str] = []
    kv_per_token = geometry.kv_bytes_per_token(kv_bytes)

    cpu_budget = ram_budget(hw)
    reasons.append(
        f"available RAM {hw.ram_available_gib} GiB of {hw.ram_total_gib} GiB; "
        f"CPU commit budget {round(cpu_budget / GIB, 2)} GiB "
        f"({int(RAM_COMMIT_FRACTION * 100)}% minus {round(MIN_FREE_RESERVE_BYTES / GIB, 1)} GiB reserve)"
    )

    if hw.ram_available_bytes and hw.ram_available_bytes < MIN_FREE_RESERVE_BYTES + model_bytes // 2:
        warnings.append(
            "free RAM is low right now; close other applications before loading a model"
        )

    if not hw.vulkan.usable:
        ctx = select_context(
            geometry, model_bytes, cpu_budget, preferred=preferred_context, kv_bytes=kv_bytes
        )
        reasons.append(
            hw.vulkan.error
            if hw.vulkan.loader_present
            else "no Vulkan loader found; the CPU backend is the only supported route"
        )
        return Assessment(
            profile=ProfileName.SAFE_CPU,
            backend="cpu",
            n_gpu_layers=0,
            context=ctx,
            estimated_runtime_bytes=model_bytes + geometry.kv_cache_bytes(ctx, kv_bytes),
            budget_bytes=cpu_budget,
            kv_bytes_per_token=kv_per_token,
            reasons=reasons,
            warnings=warnings,
        )

    device = max(hw.vulkan.devices, key=lambda d: d.device_local_memory_bytes)
    gpu_budget = vram_budget(hw)
    reasons.append(
        f"Vulkan device '{device.name}' ({device.device_type}, Vulkan {device.api_version}) "
        f"with {round(device.device_local_memory_bytes / GIB, 2)} GiB device-local memory; "
        f"offload budget {round(gpu_budget / GIB, 2)} GiB"
    )
    if device.device_type == "integrated-gpu":
        reasons.append(
            "integrated GPU: device memory is shared with system RAM, so the budget is "
            "the lower of the GPU heap share and the safe RAM commit"
        )

    ctx_full = select_context(
        geometry, model_bytes, gpu_budget, preferred=preferred_context, kv_bytes=kv_bytes
    )
    full_need = model_bytes + geometry.kv_cache_bytes(ctx_full, kv_bytes)

    if full_need <= gpu_budget:
        reasons.append(
            f"full offload fits: {round(full_need / GIB, 2)} GiB needed at {ctx_full} tokens "
            f"within a {round(gpu_budget / GIB, 2)} GiB budget"
        )
        if device.device_type == "integrated-gpu":
            warnings.append(
                "integrated GPU memory is shared with system RAM; llama.cpp may report "
                "lower real free memory than the heap size suggests"
            )
        return Assessment(
            profile=ProfileName.VULKAN_BALANCED,
            backend="vulkan",
            n_gpu_layers=-1,
            context=ctx_full,
            estimated_runtime_bytes=full_need,
            budget_bytes=gpu_budget,
            kv_bytes_per_token=kv_per_token,
            reasons=reasons,
            warnings=warnings,
            device_name=device.name,
        )

    # Partial offload on the GPU, remainder in system RAM.
    low_ctx = min(preferred_context or 2048, 2048)
    partial_need = model_bytes * 0.7 + geometry.kv_cache_bytes(low_ctx, kv_bytes)
    if partial_need <= cpu_budget:
        reasons.append(
            f"full offload does not fit ({round(full_need / GIB, 2)} GiB > "
            f"{round(gpu_budget / GIB, 2)} GiB); using partial offload with a "
            f"{low_ctx}-token context"
        )
        return Assessment(
            profile=ProfileName.VULKAN_LOW_MEMORY,
            backend="vulkan",
            n_gpu_layers=max(1, geometry.n_layers // 2),
            context=low_ctx,
            estimated_runtime_bytes=partial_need,
            budget_bytes=min(cpu_budget, gpu_budget),
            kv_bytes_per_token=kv_per_token,
            reasons=reasons,
            warnings=warnings,
            device_name=device.name,
        )

    reasons.append(
        "neither full nor partial GPU offload fits the measured budget; falling back to CPU"
    )
    ctx = select_context(
        geometry, model_bytes, cpu_budget, preferred=preferred_context, kv_bytes=kv_bytes
    )
    return Assessment(
        profile=ProfileName.SAFE_CPU,
        backend="cpu",
        n_gpu_layers=0,
        context=ctx,
        estimated_runtime_bytes=model_bytes + geometry.kv_cache_bytes(ctx, kv_bytes),
        budget_bytes=cpu_budget,
        kv_bytes_per_token=kv_per_token,
        reasons=reasons,
        warnings=warnings,
    )


def browser_profile(webgpu_adapter: str | None, wasm_only: bool = False) -> ProfileName:
    if wasm_only or not webgpu_adapter:
        return ProfileName.BROWSER_WASM
    return ProfileName.BROWSER_WEBGPU
