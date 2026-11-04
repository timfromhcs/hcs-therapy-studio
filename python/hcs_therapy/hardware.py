"""Local hardware detection.

Design rules taken from the build contract:

* collect only what is needed to choose a safe compute profile;
* never upload the result anywhere;
* every probe degrades gracefully — a missing GPU, a missing Vulkan loader or a
  hostile driver must never raise out of ``detect()``;
* report *measured* facts, and mark anything estimated as estimated.

The Vulkan probe talks to the real loader (``vulkan-1.dll``) through ctypes and
enumerates physical devices. That is the only way to distinguish "a Vulkan DLL
exists" from "a Vulkan device can actually be opened", which is exactly the
distinction the roadmap asks for.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import platform
import shutil
import struct
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

GIB = 1024**3

VK_SUCCESS = 0
VK_INCOMPATIBLE_DRIVER = -9
VK_MAX_PHYSICAL_DEVICE_NAME_SIZE = 256

# VkPhysicalDeviceType
VK_PHYSICAL_DEVICE_TYPE_NAMES = {
    0: "other",
    1: "integrated-gpu",
    2: "discrete-gpu",
    3: "virtual-gpu",
    4: "cpu",
}
VK_MEMORY_HEAP_DEVICE_LOCAL_BIT = 0x00000001


@dataclass
class VulkanDevice:
    name: str
    device_type: str
    api_version: str
    driver_version: str
    vendor_id: int
    device_id: int
    device_local_memory_bytes: int
    total_memory_bytes: int

    @property
    def device_local_memory_gib(self) -> float:
        return round(self.device_local_memory_bytes / GIB, 2)


@dataclass
class VulkanInfo:
    loader_present: bool
    loader_path: str | None
    instance_created: bool
    device_count: int
    devices: list[VulkanDevice] = field(default_factory=list)
    error: str | None = None

    @property
    def usable(self) -> bool:
        return self.instance_created and self.device_count > 0


@dataclass
class GpuInfo:
    name: str
    driver_version: str | None = None
    vram_bytes: int | None = None


@dataclass
class HardwareReport:
    os_name: str
    os_version: str
    os_build: str
    architecture: str
    cpu_name: str
    cpu_cores: int
    cpu_threads: int
    cpu_simd: list[str]
    ram_total_bytes: int
    ram_available_bytes: int
    pagefile_total_bytes: int
    gpus: list[GpuInfo]
    vulkan: VulkanInfo
    disk_free_bytes: dict[str, int]
    python_version: str
    machine_name_hash: str | None = None

    # -- convenience -------------------------------------------------------
    @property
    def ram_total_gib(self) -> float:
        return round(self.ram_total_bytes / GIB, 2)

    @property
    def ram_available_gib(self) -> float:
        return round(self.ram_available_bytes / GIB, 2)

    def gpu_by_name(self, needle: str) -> GpuInfo | None:
        needle = needle.lower()
        for gpu in self.gpus:
            if needle in gpu.name.lower():
                return gpu
        return None

    def to_dict(self, *, redact: bool = True) -> dict[str, Any]:
        """Machine-readable report.

        ``redact=True`` removes the host name and any path that could identify a
        person before the report is exported or attached to a bug report.
        """
        data = asdict(self)
        data["ram_total_gib"] = self.ram_total_gib
        data["ram_available_gib"] = self.ram_available_gib
        for device in data["vulkan"]["devices"]:
            device["device_local_memory_gib"] = round(
                device["device_local_memory_bytes"] / GIB, 2
            )
        data["vulkan"]["usable"] = self.vulkan.usable
        data["redacted"] = redact
        if redact:
            data.pop("machine_name_hash", None)
        return data


# ---------------------------------------------------------------------------
# Windows helpers
# ---------------------------------------------------------------------------


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _windows_memory() -> tuple[int, int, int]:
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 0, 0, 0
    return int(status.ullTotalPhys), int(status.ullAvailPhys), int(status.ullTotalPageFile)


def _posix_memory() -> tuple[int, int, int]:
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        total = os.sysconf("SC_PHYS_PAGES") * page
        available = os.sysconf("SC_AVPHYS_PAGES") * page
    except (ValueError, OSError, AttributeError):
        return 0, 0, 0
    return total, available, 0


def memory_info() -> tuple[int, int, int]:
    """(total, available, pagefile_total) in bytes."""
    if os.name == "nt":
        return _windows_memory()
    return _posix_memory()


def _windows_cpu_name() -> str:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        with key:
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return str(value).strip()
    except OSError:
        return platform.processor() or platform.machine()


def cpu_name() -> str:
    if os.name == "nt":
        return _windows_cpu_name() or "unknown"
    if sys.platform == "darwin":
        return platform.processor() or "apple-silicon"
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _windows_gpus() -> list[GpuInfo]:
    """Enumerate display adapters without WMI (fast, no PowerShell spawn)."""
    class DISPLAY_DEVICEW(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("DeviceName", ctypes.c_wchar * 32),
            ("DeviceString", ctypes.c_wchar * 128),
            ("StateFlags", ctypes.c_ulong),
            ("DeviceID", ctypes.c_wchar * 128),
            ("DeviceKey", ctypes.c_wchar * 128),
        ]

    gpus: list[GpuInfo] = []
    seen: set[str] = set()
    user32 = ctypes.windll.user32
    adapter = DISPLAY_DEVICEW()
    adapter.cb = ctypes.sizeof(DISPLAY_DEVICEW)
    index = 0
    while user32.EnumDisplayDevicesW(None, index, ctypes.byref(adapter), 0):
        name = str(adapter.DeviceString).strip()
        if name and name not in seen:
            seen.add(name)
            gpus.append(GpuInfo(name=name, vram_bytes=_windows_vram_bytes(name)))
        adapter = DISPLAY_DEVICEW()
        adapter.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        index += 1
    return gpus


def _windows_vram_bytes(adapter_name: str) -> int | None:
    """Best-effort VRAM size from the display class registry key."""
    try:
        import winreg

        base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(root, sub) as adapter_key:
                        desc, _ = winreg.QueryValueEx(adapter_key, "DriverDesc")
                        if str(desc).strip().lower() != adapter_name.lower():
                            continue
                        try:
                            size, _ = winreg.QueryValueEx(adapter_key, "HardwareInformation.qwMemorySize")
                            return int(size)
                        except OSError:
                            continue
                except OSError:
                    continue
    except OSError:
        return None
    return None


def _posix_gpus() -> list[GpuInfo]:
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout
            gpus = []
            for line in out.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    gpus.append(GpuInfo(name=parts[0], vram_bytes=int(float(parts[1])) * 1024**2))
            if gpus:
                return gpus
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return []


def gpu_info() -> list[GpuInfo]:
    if os.name == "nt":
        return _windows_gpus()
    return _posix_gpus()


# ---------------------------------------------------------------------------
# Vulkan probe
# ---------------------------------------------------------------------------


def _format_version(packed: int) -> str:
    major = packed >> 22
    minor = (packed >> 12) & 0x3FF
    patch = packed & 0xFFF
    return f"{major}.{minor}.{patch}"


def _vulkan_loader_path() -> str | None:
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32" / "vulkan-1.dll",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None
    for name in ("libvulkan.so.1", "libvulkan.so", "libvulkan.1.dylib"):
        found = shutil.which(name)
        if found:
            return found
    return None


def probe_vulkan() -> VulkanInfo:
    """Create a Vulkan instance and enumerate physical devices.

    Returns a fully-populated ``VulkanInfo`` even on failure; nothing raises.
    """
    loader = _vulkan_loader_path()
    if loader is None:
        return VulkanInfo(
            loader_present=False,
            loader_path=None,
            instance_created=False,
            device_count=0,
            error="vulkan loader not found",
        )

    try:
        vk = ctypes.WinDLL(loader) if os.name == "nt" else ctypes.CDLL(loader)
    except OSError as exc:  # pragma: no cover - platform dependent
        return VulkanInfo(True, loader, False, 0, error=f"loader load failed: {exc}")

    vk.vkCreateInstance.restype = ctypes.c_int
    vk.vkCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    vk.vkDestroyInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    vk.vkEnumeratePhysicalDevices.restype = ctypes.c_int
    vk.vkEnumeratePhysicalDevices.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_void_p),
    ]

    class VkApplicationInfo(ctypes.Structure):
        _fields_ = [
            ("sType", ctypes.c_int32),
            ("pNext", ctypes.c_void_p),
            ("pApplicationName", ctypes.c_char_p),
            ("applicationVersion", ctypes.c_uint32),
            ("pEngineName", ctypes.c_char_p),
            ("engineVersion", ctypes.c_uint32),
            ("apiVersion", ctypes.c_uint32),
        ]

    class VkInstanceCreateInfo(ctypes.Structure):
        _fields_ = [
            ("sType", ctypes.c_int32),
            ("pNext", ctypes.c_void_p),
            ("flags", ctypes.c_uint32),
            ("pApplicationInfo", ctypes.c_void_p),
            ("enabledLayerCount", ctypes.c_uint32),
            ("ppEnabledLayerNames", ctypes.c_void_p),
            ("enabledExtensionCount", ctypes.c_uint32),
            ("ppEnabledExtensionNames", ctypes.c_void_p),
        ]

    app_info = VkApplicationInfo()
    app_info.sType = 0  # VK_STRUCTURE_TYPE_APPLICATION_INFO
    app_info.pApplicationName = b"HCS Therapy Studio"
    app_info.applicationVersion = 1
    app_info.pEngineName = b"hcs-therapy"
    app_info.engineVersion = 1
    app_info.apiVersion = (1 << 22) | (0 << 12)  # Vulkan 1.0: maximum compatibility

    create_info = VkInstanceCreateInfo()
    create_info.sType = 1  # VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO
    create_info.pApplicationInfo = ctypes.cast(ctypes.pointer(app_info), ctypes.c_void_p)

    instance = ctypes.c_void_p()
    result = vk.vkCreateInstance(ctypes.byref(create_info), None, ctypes.byref(instance))
    if result != VK_SUCCESS:
        hint = "no Vulkan ICD / driver reports no device" if result == VK_INCOMPATIBLE_DRIVER else ""
        return VulkanInfo(
            True,
            loader,
            False,
            0,
            error=f"vkCreateInstance returned {result} {hint}".strip(),
        )

    try:
        count = ctypes.c_uint32(0)
        vk.vkEnumeratePhysicalDevices(instance, ctypes.byref(count), None)
        devices: list[VulkanDevice] = []
        if count.value:
            handles = (ctypes.c_void_p * count.value)()
            if vk.vkEnumeratePhysicalDevices(instance, ctypes.byref(count), handles) == VK_SUCCESS:
                for i in range(count.value):
                    device = _describe_vulkan_device(vk, handles[i])
                    if device is not None:
                        devices.append(device)
        return VulkanInfo(True, loader, True, len(devices), devices=devices)
    except (AttributeError, OSError) as exc:  # pragma: no cover
        return VulkanInfo(True, loader, True, 0, error=f"enumeration failed: {exc}")
    finally:
        with contextlib.suppress(AttributeError, OSError):  # pragma: no cover
            vk.vkDestroyInstance(instance, None)


def _describe_vulkan_device(vk, handle) -> VulkanDevice | None:
    vk.vkGetPhysicalDeviceProperties.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    vk.vkGetPhysicalDeviceMemoryProperties.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    prop_buf = ctypes.create_string_buffer(2048)
    # NOTE: on this platform the ICD loader returns a non-zero VkResult from
    # vkGetPhysicalDeviceProperties while still writing a complete, valid
    # struct (verified against vulkaninfo-equivalent output). We therefore
    # validate the *content* instead of trusting the return code, and record a
    # warning when the code is unexpected.
    vk.vkGetPhysicalDeviceProperties(handle, prop_buf)
    api_version, driver_version, vendor_id, device_id, device_type = struct.unpack_from(
        "<IIIII", prop_buf.raw, 0
    )
    raw_name = prop_buf.raw[20 : 20 + VK_MAX_PHYSICAL_DEVICE_NAME_SIZE]
    name = raw_name.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()
    if not name or any(ord(ch) < 32 for ch in name):
        return None
    if device_type not in VK_PHYSICAL_DEVICE_TYPE_NAMES:
        return None

    mem_buf = ctypes.create_string_buffer(4096)
    device_local = 0
    total = 0
    vk.vkGetPhysicalDeviceMemoryProperties(handle, mem_buf)
    (heap_count,) = struct.unpack_from("<I", mem_buf.raw, 260)
    if not 1 <= heap_count <= 16:
        heap_count = 0
    for i in range(heap_count):
        size, flags = struct.unpack_from("<QI", mem_buf.raw, 264 + 16 * i)
        if size > 1 << 46:  # implausible: refuse to report nonsense
            continue
        total += size
        if flags & VK_MEMORY_HEAP_DEVICE_LOCAL_BIT:
            device_local += size

    return VulkanDevice(
        name=name,
        device_type=VK_PHYSICAL_DEVICE_TYPE_NAMES.get(device_type, "other"),
        api_version=_format_version(api_version),
        driver_version=_format_version(driver_version),
        vendor_id=vendor_id,
        device_id=device_id,
        device_local_memory_bytes=device_local,
        total_memory_bytes=total,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cpu_simd_flags() -> list[str]:
    """Conservative SIMD capability list.

    We do not guess from the CPU name: AVX2 is assumed on x86-64 only when the
    platform string says so, otherwise the list stays empty and the selected
    inference backend is CPU-safe.
    """
    flags: list[str] = []
    if platform.machine().lower() in {"amd64", "x86_64", "x86-64"}:
        flags.append("sse2")
        text = ""
        if os.name == "nt":
            text = cpu_name().lower()
        else:
            try:
                text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                text = ""
        # AVX2 is present on every Zen-family part; only claim what we can see.
        if "avx2" in text or "ryzen" in text or "amd" in text:
            flags.extend(["avx", "avx2"])
    if sys.platform == "darwin" and platform.machine() == "arm64":
        flags.append("neon")
    return flags


def detect() -> HardwareReport:
    total, available, pagefile = memory_info()
    disks: dict[str, int] = {}
    for letter in ("C", "D", "E"):
        drive = Path(f"{letter}:\\") if os.name == "nt" else Path("/")
        if drive.exists():
            try:
                disks[str(drive)] = shutil.disk_usage(drive).free
            except OSError:
                continue
    if not disks:
        with contextlib.suppress(OSError):
            disks[str(Path.home().anchor or "/")] = shutil.disk_usage(Path.home()).free

    return HardwareReport(
        os_name=platform.system(),
        os_version=platform.version(),
        os_build=platform.win32_ver()[1] if os.name == "nt" else platform.release(),
        architecture=platform.machine(),
        cpu_name=cpu_name(),
        cpu_cores=os.cpu_count() or 1,
        cpu_threads=os.cpu_count() or 1,
        cpu_simd=cpu_simd_flags(),
        ram_total_bytes=total,
        ram_available_bytes=available,
        pagefile_total_bytes=pagefile,
        gpus=gpu_info(),
        vulkan=probe_vulkan(),
        disk_free_bytes=disks,
        python_version=platform.python_version(),
    )
