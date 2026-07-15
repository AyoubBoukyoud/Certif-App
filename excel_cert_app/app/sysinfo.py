"""Best-effort system diagnostics: installed Office apps, Office language and
activation, and Windows version and activation.

Everything here is read-only and defensive — every probe is wrapped so a
missing registry key, a missing script, or a WMI hiccup degrades to an
"indéterminé" result rather than raising. Nothing here launches a visible
Office window; app detection reads the installed .exe's file-version resource
instead of starting the app.

Not applicable on non-Windows dev machines: :func:`is_windows` gates every
probe, and callers should treat a ``False`` result as "skip, dev stub".
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

# (key, display name, unversioned ProgID used to resolve the install path,
#  exe filename used only as a fallback label)
_OFFICE_APPS = [
    ("word", "Microsoft Word", "Word.Application"),
    ("excel", "Microsoft Excel", "Excel.Application"),
    ("powerpoint", "Microsoft PowerPoint", "PowerPoint.Application"),
    ("outlook", "Microsoft Outlook", "Outlook.Application"),
]

# (key, display name) pairs, for UIs that just need to know what to list.
OFFICE_APPS = [(key, name) for key, name, _ in _OFFICE_APPS]

# Excel's internal version stays "16.0" across 2016, 2019, 2021 and Microsoft
# 365 — there is no finer-grained way to tell them apart via file version.
MIN_SUPPORTED_OFFICE_VERSION = 16.0

_LICENSE_STATUS_LABELS = {
    0: "Non concédé", 1: "Activé", 2: "En période de grâce",
    3: "Grâce OOB dépassée", 4: "Grâce non authentique dépassée",
    5: "Notification", 6: "Grâce étendue",
}


@dataclass
class OfficeAppStatus:
    key: str
    display_name: str
    found: bool
    version: str | None = None        # "16.0"
    build: str | None = None          # "17029.20146"
    full_version: str | None = None   # "16.0.17029.20146"
    path: str | None = None
    note: str | None = None


@dataclass
class OfficeSuiteStatus:
    apps: list[OfficeAppStatus] = field(default_factory=list)
    language: str | None = None
    activated: bool | None = None     # None = could not be determined
    activation_detail: str = ""


@dataclass
class WindowsStatus:
    product_name: str | None = None
    display_version: str | None = None
    build: str | None = None
    activated: bool | None = None
    activation_detail: str = ""


def is_windows() -> bool:
    """False on dev machines, where app.excel falls back to a stub controller
    and none of these Windows-only probes apply."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False
    return True


# -- Office apps --------------------------------------------------------------

def _open_key_any_view(hive, subkey: str):
    """Office is commonly installed 32-bit even on 64-bit Windows, in which
    case its COM registration (CLSID\\LocalServer32) only exists in the
    32-bit registry view (WOW6432Node) — invisible to a 64-bit Python
    process using a plain OpenKey. Try the native view first, then the
    32-bit view, so detection works regardless of Office's or Python's
    bitness."""
    import winreg

    for flag in (0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            return winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | flag)
        except OSError:
            continue
    return None


def _exe_path_from_progid(progid: str) -> str | None:
    """COM Application ProgIDs (e.g. "Excel.Application") register their
    server under CLSID\\LocalServer32, not shell\\open\\command — the latter
    only exists for file-type ProgIDs like "Excel.Sheet.12"."""
    import winreg

    key = _open_key_any_view(winreg.HKEY_CLASSES_ROOT, f"{progid}\\CLSID")
    if key is None:
        return None
    with key:
        clsid, _ = winreg.QueryValueEx(key, None)
    key = _open_key_any_view(winreg.HKEY_CLASSES_ROOT, f"CLSID\\{clsid}\\LocalServer32")
    if key is None:
        return None
    with key:
        command, _ = winreg.QueryValueEx(key, None)
    match = re.match(r'\s*"([^"]+)"', command)
    if match:
        return match.group(1)
    # Unquoted paths can contain spaces (e.g. "...Microsoft Office\Root\...
    # \EXCEL.EXE /automation"), so a naive split on the first space would
    # truncate mid-path — anchor on the ".exe" extension instead.
    match = re.search(r"^(.*?\.exe)\b", command, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    first = command.strip().split(" ")[0]
    return first or None


def _file_version(path: str) -> tuple[str, str, str] | None:
    try:
        import win32api

        info = win32api.GetFileVersionInfo(path, "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        major, minor = ms >> 16, ms & 0xFFFF
        build, revision = ls >> 16, ls & 0xFFFF
    except Exception:
        return None
    return f"{major}.{minor}", f"{build}.{revision}", f"{major}.{minor}.{build}.{revision}"


def _check_office_app(key: str, display_name: str, progid: str) -> OfficeAppStatus:
    path = _exe_path_from_progid(progid)
    if not path or not os.path.isfile(path):
        return OfficeAppStatus(key, display_name, found=False,
                               note="Non installé (introuvable dans le registre).")
    fv = _file_version(path)
    if not fv:
        return OfficeAppStatus(key, display_name, found=True, path=path,
                               note="Trouvé, mais la version n'a pas pu être lue.")
    version, build, full = fv
    return OfficeAppStatus(key, display_name, found=True, version=version,
                           build=build, full_version=full, path=path)


def list_office_apps() -> list[OfficeAppStatus]:
    return [_check_office_app(k, name, progid) for k, name, progid in _OFFICE_APPS]


def office_language() -> str | None:
    import locale
    import winreg

    for ver in ("16.0", "15.0"):
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Microsoft\Office\{ver}\Common\LanguageResources",
            ) as key:
                lcid, _ = winreg.QueryValueEx(key, "UILanguage")
        except OSError:
            continue
        return locale.windows_locale.get(lcid, f"LCID {lcid}")
    return None


def office_activation(sample_app_path: str | None) -> tuple[bool | None, str]:
    """Runs OSPP.VBS /dstatus next to a detected Office app. Best-effort:
    covers the common Click-to-Run and MSI layouts, times out quickly, and
    never raises — an unreadable result just means "indéterminé"."""
    if not sample_app_path:
        return None, "Aucune application Office trouvée pour localiser OSPP.VBS."
    office_dir = os.path.dirname(sample_app_path)
    # Click-to-Run keeps OSPP.VBS in the shared "Office16" folder, one level
    # above the versioned "Root\Office16" folder that holds the actual EXEs
    # — so it is never actually next to the detected app on a C2R install.
    candidates = [office_dir, office_dir.replace(f"{os.sep}Root{os.sep}", os.sep)]
    ospp = next((os.path.join(d, "OSPP.VBS") for d in candidates
                if os.path.isfile(os.path.join(d, "OSPP.VBS"))), None)
    if not ospp:
        return None, "OSPP.VBS introuvable à côté de l'installation détectée."
    try:
        proc = subprocess.run(
            ["cscript", "//nologo", ospp, "/dstatus"],
            capture_output=True, text=True, timeout=15,
        )
        out = proc.stdout
    except Exception as exc:
        return None, f"Échec de l'exécution d'OSPP.VBS : {exc}"

    if "---LICENSED---" in out:
        return True, "Activé (licence valide)."
    for line in out.splitlines():
        if "LICENSE STATUS" in line.upper():
            return False, line.strip()
    return None, "Statut d'activation indéterminé (sortie OSPP.VBS inattendue)."


def office_suite_status() -> OfficeSuiteStatus:
    apps = list_office_apps()
    sample = next((a.path for a in apps if a.found and a.path), None)
    activated, detail = office_activation(sample)
    return OfficeSuiteStatus(
        apps=apps, language=office_language(),
        activated=activated, activation_detail=detail,
    )


# -- Windows -------------------------------------------------------------------

def windows_version() -> WindowsStatus:
    import winreg

    st = WindowsStatus()
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        ) as key:
            try:
                st.product_name = winreg.QueryValueEx(key, "ProductName")[0]
            except OSError:
                pass
            for value_name in ("DisplayVersion", "ReleaseId"):
                try:
                    st.display_version = winreg.QueryValueEx(key, value_name)[0]
                    break
                except OSError:
                    continue
            try:
                build = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
                try:
                    ubr = winreg.QueryValueEx(key, "UBR")[0]
                    st.build = f"{build}.{ubr}"
                except OSError:
                    st.build = str(build)
            except OSError:
                pass
    except OSError:
        pass
    return st


def windows_activation() -> tuple[bool | None, str]:
    """Queries the Software Licensing WMI provider — the same data source
    behind ``slmgr /dli`` — without spawning a script host."""
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return None, "pywin32 indisponible."

    pythoncom.CoInitialize()
    result: tuple[bool | None, str] = (None, "Aucune licence Windows trouvée.")
    try:
        wmi = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")
        products = wmi.ExecQuery(
            "SELECT LicenseStatus FROM SoftwareLicensingProduct "
            "WHERE PartialProductKey IS NOT NULL AND "
            "ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f'"
        )
        # Collect into plain ints and drop the COM proxies before returning —
        # holding one past CoUninitialize() logs spurious "Win32 exception"
        # warnings when it's eventually garbage-collected.
        statuses = [int(p.LicenseStatus) for p in products]
        del products, wmi
        if statuses:
            status = statuses[0]
            label = _LICENSE_STATUS_LABELS.get(status, f"Statut {status}")
            result = (status == 1, label)
    except Exception as exc:
        result = (None, f"Vérification impossible : {exc}")
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    return result


def windows_status() -> WindowsStatus:
    st = windows_version()
    st.activated, st.activation_detail = windows_activation()
    return st


# -- combined entry point -------------------------------------------------

def version_supported(version: str, minimum: float = MIN_SUPPORTED_OFFICE_VERSION) -> bool:
    try:
        return float(version) >= minimum
    except ValueError:
        return False


@dataclass
class FullCheck:
    office: OfficeSuiteStatus
    windows: WindowsStatus
    excel_supported: bool
    dev_stub: bool = False


def run_full_check() -> FullCheck:
    """Runs every probe. On a non-Windows dev machine (where app.excel falls
    back to the stub controller) this is a fast no-op that always passes, so
    it never blocks the existing dev workflow."""
    if not is_windows():
        return FullCheck(
            office=OfficeSuiteStatus(apps=[], language=None, activated=None,
                                     activation_detail="Environnement de développement "
                                     "(non Windows) : vérification ignorée."),
            windows=WindowsStatus(activation_detail="Environnement de développement."),
            excel_supported=True, dev_stub=True,
        )

    office = office_suite_status()
    windows = windows_status()
    excel = next((a for a in office.apps if a.key == "excel"), None)
    excel_supported = bool(excel and excel.found and excel.version
                           and version_supported(excel.version))
    return FullCheck(office=office, windows=windows, excel_supported=excel_supported)
