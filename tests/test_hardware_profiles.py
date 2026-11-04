"""Hardware detection and compute-profile honesty."""

from __future__ import annotations

import pytest

from hcs_therapy.hardware import (
    GIB,
    GpuInfo,
    HardwareReport,
    VulkanDevice,
    VulkanInfo,
    detect,
)
from hcs_therapy.profiles import (
    QWEN3_0_6B,
    QWEN3_1_7B,
    ProfileName,
    assess,
    select_context,
)


def _report(ram_total=16 * GIB, ram_available=12 * GIB, vulkan=None) -> HardwareReport:
    return HardwareReport(
        os_name="Windows",
        os_version="10.0",
        os_build="10.0",
        architecture="AMD64",
        cpu_name="Test CPU",
        cpu_cores=8,
        cpu_threads=16,
        cpu_simd=["avx2"],
        ram_total_bytes=ram_total,
        ram_available_bytes=ram_available,
        pagefile_total_bytes=0,
        gpus=[GpuInfo("Test GPU")],
        vulkan=vulkan or VulkanInfo(False, None, False, 0, error="no loader"),
        disk_free_bytes={"C:\\": 100 * GIB},
        python_version="3.12.0",
    )


def _vulkan(device_type: str = "discrete-gpu", memory: int = 8 * GIB) -> VulkanInfo:
    device = VulkanDevice(
        name="Test Vulkan",
        device_type=device_type,
        api_version="1.3.0",
        driver_version="1.0.0",
        vendor_id=0x1002,
        device_id=0x1681,
        device_local_memory_bytes=memory,
        total_memory_bytes=memory * 2,
    )
    return VulkanInfo(True, "vulkan-1.dll", True, 1, devices=[device])


def test_detect_runs_and_reports_reality() -> None:
    report = detect()
    assert report.os_name
    assert report.cpu_name
    assert report.ram_total_bytes > 0
    assert report.cpu_cores >= 1
    payload = report.to_dict()
    assert payload["ram_total_gib"] > 0
    assert "vulkan" in payload
    assert payload["redacted"] is True


def test_detect_is_side_effect_free_and_repeatable() -> None:
    first = detect().to_dict()
    second = detect().to_dict()
    assert first["cpu_name"] == second["cpu_name"]
    assert first["ram_total_gib"] == second["ram_total_gib"]


def test_no_vulkan_means_safe_cpu() -> None:
    result = assess(_report(), QWEN3_1_7B, int(1.05 * GIB))
    assert result.profile is ProfileName.SAFE_CPU
    assert result.backend == "cpu"
    assert result.n_gpu_layers == 0


def test_discrete_gpu_gets_full_offload_when_it_fits() -> None:
    result = assess(
        _report(vulkan=_vulkan()), QWEN3_1_7B, int(1.05 * GIB), preferred_context=2048
    )
    assert result.profile is ProfileName.VULKAN_BALANCED
    assert result.n_gpu_layers == -1
    assert result.context >= 2048


def test_integrated_gpu_budget_is_limited_by_system_ram() -> None:
    """Shared memory must never be promised as if it were dedicated VRAM."""
    report = _report(ram_available=4 * GIB, vulkan=_vulkan("integrated-gpu", 12 * GIB))
    result = assess(report, QWEN3_1_7B, int(1.05 * GIB))
    assert result.profile is not ProfileName.VULKAN_BALANCED
    assert result.budget_bytes <= 4 * GIB


def test_integrated_gpu_with_plenty_of_ram_can_use_balanced() -> None:
    report = _report(ram_available=14 * GIB, vulkan=_vulkan("integrated-gpu", 12 * GIB))
    result = assess(report, QWEN3_1_7B, int(1.05 * GIB), preferred_context=2048)
    assert result.profile is ProfileName.VULKAN_BALANCED
    assert any("integrated" in reason for reason in result.reasons)


def test_low_memory_partial_offload_path() -> None:
    # 1.4 GiB heap -> 1.05 GiB offload budget: too small for full offload at
    # 2048 tokens, big enough for a partial offload with the CPU taking the rest.
    report = _report(ram_available=10 * GIB, vulkan=_vulkan("discrete-gpu", int(1.4 * GIB)))
    result = assess(report, QWEN3_1_7B, int(1.05 * GIB))
    assert result.profile is ProfileName.VULKAN_LOW_MEMORY
    assert 0 < result.n_gpu_layers < QWEN3_1_7B.n_layers
    assert result.context <= 2048


def test_context_shrinks_before_the_model_does_not_fit() -> None:
    geometry = QWEN3_1_7B
    model_bytes = int(1.05 * GIB)
    budget = model_bytes + geometry.kv_cache_bytes(4096) + 1
    assert select_context(geometry, model_bytes, budget) == 4096
    assert select_context(geometry, model_bytes, budget // 2) < 4096


def test_kv_cache_estimate_matches_qwen3_geometry() -> None:
    # 2 (K and V) * 28 layers * 8 kv heads * 128 head_dim * 2 bytes = 114,688 B
    assert QWEN3_1_7B.kv_bytes_per_token(2) == 114_688
    assert QWEN3_0_6B.kv_bytes_per_token(2) == 114_688


def test_assessment_is_serialisable_and_explains_itself() -> None:
    payload = assess(_report(vulkan=_vulkan()), QWEN3_1_7B, int(1.05 * GIB)).to_dict()
    assert payload["reasons"], "a profile decision without reasons is a guess"
    assert payload["budget_gib"] > 0
    assert payload["profile"] in {p.value for p in ProfileName}


def test_low_free_ram_produces_a_warning() -> None:
    report = _report(ram_available=2 * GIB, vulkan=_vulkan())
    result = assess(report, QWEN3_1_7B, int(1.05 * GIB))
    assert result.warnings, "low RAM must produce a visible warning"


@pytest.mark.skipif(False, reason="kept for symmetry")
def test_vulkan_probe_never_raises() -> None:
    from hcs_therapy.hardware import probe_vulkan

    info = probe_vulkan()
    assert isinstance(info, VulkanInfo)
    assert info.device_count == len(info.devices)
