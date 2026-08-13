import hashlib
import json
import logging
import os
import socket
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Dict, Iterator
from core.character_consistency import (
    apply_character_to_prompt,
    build_character_prompt,
    consistency_report,
    normalize_character,
)
from core.branding import DEFAULT_ARTIST
from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags


LOGGER = logging.getLogger(__name__)
PROJECT_LOCK_TIMEOUT_SECONDS = 5.0
PROJECT_LOCK_STALE_SECONDS = 60.0
PROJECT_LOAD_ATTEMPTS = 3
PROJECT_LOAD_RETRY_SECONDS = 0.05
EPHEMERAL_PROJECT_KEYS = {"runtime", "preview_diagnostics"}


class ProjectLockTimeout(TimeoutError):
    pass


class ProjectLockPermissionError(PermissionError):
    pass


def _process_is_alive(pid: Any, hostname: str) -> bool | None:
    """Return owner liveness on this host; None means it cannot be proven."""
    if str(hostname or "") != socket.gethostname():
        return None
    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return False
    if process_id <= 0:
        return False
    if process_id == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(process_query_limited_information, False, process_id)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return None
                return exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return None
    try:
        os.kill(process_id, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _read_lock_owner(lock_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(lock_path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except PermissionError:
        raise
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _lock_identity(owner: dict[str, Any]) -> str:
    return str(owner.get("lock_id") or owner.get("token") or "")


def _read_lock_snapshot(lock_path: Path) -> dict[str, Any] | None:
    try:
        before = lock_path.stat()
        owner = _read_lock_owner(lock_path)
        after = lock_path.stat()
    except FileNotFoundError:
        return None
    before_signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_signature = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_signature != after_signature:
        return None
    return {
        "owner": owner,
        "lock_id": _lock_identity(owner),
        "signature": after_signature,
        "mtime": after.st_mtime,
    }


def _release_owned_lock(lock_path: Path, token: str) -> bool:
    if not lock_path.is_file():
        return False
    try:
        with _stale_recovery_guard(
            lock_path,
            deadline=time.monotonic() + PROJECT_LOCK_TIMEOUT_SECONDS,
            poll_interval=0.01,
        ):
            current = _read_lock_owner(lock_path) if lock_path.is_file() else {}
            if _lock_identity(current) != token:
                return False
            lock_path.unlink()
            return True
    except (OSError, ProjectLockTimeout):
        return False


def safe_name(name: str) -> str:
    keep = [ch for ch in (name or "").strip() if ch.isalnum() or ch in (" ", "-", "_")]
    return ("".join(keep).strip().replace(" ", "_") or "untitled_project")


def _project_lock_path(folder: Path, project_file: Path | None = None) -> Path:
    if project_file is not None and project_file.name != "project.json":
        return folder / f".{project_file.stem}.save.lock"
    return folder / ".project_save.lock"


def _create_lock_file(lock_path: Path, payload: bytes) -> None:
    descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _lock_directory_is_writable(lock_path: Path) -> bool:
    descriptor: int | None = None
    probe_path: Path | None = None
    try:
        descriptor, probe_name = tempfile.mkstemp(prefix=".lock_write_probe.", dir=str(lock_path.parent))
        probe_path = Path(probe_name)
        return True
    except (OSError, PermissionError):
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if probe_path is not None:
            try:
                probe_path.unlink(missing_ok=True)
            except OSError:
                pass


def _is_transient_windows_lock_permission_error(lock_path: Path, error: PermissionError) -> bool:
    if os.name != "nt":
        return False
    winerror = getattr(error, "winerror", None)
    if winerror in {32, 33}:
        return _lock_directory_is_writable(lock_path)
    if winerror not in {None, 5}:
        return False
    # Windows can report access denied while a just-released name remains in
    # delete-pending state. A still-present denied path may have a real ACL
    # problem and must not be silently converted into contention.
    return not lock_path.exists() and _lock_directory_is_writable(lock_path)


def _retry_transient_lock_permission(
    lock_path: Path,
    error: PermissionError,
    *,
    deadline: float,
    attempt: int,
    poll_interval: float,
) -> int:
    if not _is_transient_windows_lock_permission_error(lock_path, error):
        raise ProjectLockPermissionError(f"Project lock path is not writable: {lock_path}") from error
    if time.monotonic() >= deadline:
        raise ProjectLockTimeout(f"Timed out waiting for project lock: {lock_path}") from None
    delay = min(0.025, max(0.01, poll_interval) * (1.25 ** min(attempt, 4)))
    time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
    return attempt + 1


def _try_lock_recovery_handle(handle: Any) -> bool:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock_recovery_handle(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _stale_recovery_guard(lock_path: Path, *, deadline: float, poll_interval: float) -> Iterator[None]:
    """Serialize stale recovery with an OS lock that is released on process exit."""
    guard_path = lock_path.with_name(f"{lock_path.name}.recovery.guard")
    permission_attempt = 0
    while True:
        try:
            handle = guard_path.open("a+b")
            break
        except PermissionError as exc:
            permission_attempt = _retry_transient_lock_permission(
                guard_path,
                exc,
                deadline=deadline,
                attempt=permission_attempt,
                poll_interval=poll_interval,
            )
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        acquired = False
        while not acquired:
            acquired = _try_lock_recovery_handle(handle)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise ProjectLockTimeout(f"Timed out waiting for stale lock recovery: {lock_path}")
            time.sleep(max(0.005, poll_interval))
        try:
            yield
        finally:
            _unlock_recovery_handle(handle)
    finally:
        handle.close()


def _remove_lock_if_unchanged(lock_path: Path, observed: dict[str, Any]) -> bool:
    current = _read_lock_snapshot(lock_path)
    if current is None:
        return False
    if current["lock_id"] != observed["lock_id"] or current["signature"] != observed["signature"]:
        return False
    try:
        lock_path.unlink()
        return True
    except FileNotFoundError:
        return False


def _recover_stale_lock(
    lock_path: Path,
    payload: bytes,
    *,
    deadline: float,
    stale_after: float,
    poll_interval: float,
) -> bool:
    if stale_after <= 0:
        return False
    try:
        if time.time() - lock_path.stat().st_mtime <= stale_after:
            return False
    except FileNotFoundError:
        return False

    with _stale_recovery_guard(lock_path, deadline=deadline, poll_interval=poll_interval):
        observed = _read_lock_snapshot(lock_path)
        if observed is None or time.time() - float(observed["mtime"]) <= stale_after:
            return False
        owner = observed["owner"]
        owner_alive = _process_is_alive(owner.get("pid"), str(owner.get("hostname") or socket.gethostname()))
        if owner_alive is not False:
            return False
        if not _remove_lock_if_unchanged(lock_path, observed):
            return False
        try:
            _create_lock_file(lock_path, payload)
            return True
        except FileExistsError:
            # Another normal contender won the creation window. Its lock is
            # authoritative and must never be removed from this observation.
            return False


@contextmanager
def project_file_lock(
    folder: str | Path,
    *,
    project_file: str | Path | None = None,
    timeout: float = PROJECT_LOCK_TIMEOUT_SECONDS,
    stale_after: float = PROJECT_LOCK_STALE_SECONDS,
    poll_interval: float = 0.025,
) -> Iterator[Path]:
    """Cross-platform, per-project lock with bounded wait and stale recovery."""
    project_folder = Path(folder)
    project_folder.mkdir(parents=True, exist_ok=True)
    source = Path(project_file) if project_file is not None else None
    lock_path = _project_lock_path(project_folder, source)
    token = uuid.uuid4().hex
    deadline = time.monotonic() + max(0.0, timeout)
    payload = json.dumps({"lock_id": token, "token": token, "pid": os.getpid(), "hostname": socket.gethostname(), "acquired_at": time.time()}).encode("utf-8")
    permission_attempt = 0
    while True:
        try:
            _create_lock_file(lock_path, payload)
            break
        except PermissionError as exc:
            permission_attempt = _retry_transient_lock_permission(
                lock_path,
                exc,
                deadline=deadline,
                attempt=permission_attempt,
                poll_interval=poll_interval,
            )
        except FileExistsError:
            try:
                if _recover_stale_lock(
                    lock_path,
                    payload,
                    deadline=deadline,
                    stale_after=stale_after,
                    poll_interval=poll_interval,
                ):
                    break
            except ProjectLockPermissionError:
                raise
            except PermissionError as exc:
                permission_attempt = _retry_transient_lock_permission(
                    lock_path,
                    exc,
                    deadline=deadline,
                    attempt=permission_attempt,
                    poll_interval=poll_interval,
                )
                continue
            if not lock_path.exists():
                continue
            if time.monotonic() >= deadline:
                LOGGER.warning("project_lock_timeout path=%s", lock_path)
                raise ProjectLockTimeout(f"Timed out waiting for project lock: {lock_path}")
            time.sleep(max(0.005, poll_interval))
    try:
        yield lock_path
    finally:
        _release_owned_lock(lock_path, token)


def _fsync_directory(folder: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(str(folder), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass


def atomic_write_bytes(path: str | Path, payload: bytes, *, replace_func: Callable[[str, str], Any] = os.replace) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{target.name}.tmp.", dir=str(target.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        replace_func(str(temp_path), str(target))
        _fsync_directory(target.parent)
        return target
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: str | Path, text: str, *, encoding: str = "utf-8", replace_func: Callable[[str, str], Any] = os.replace) -> Path:
    return atomic_write_bytes(path, text.encode(encoding), replace_func=replace_func)


def atomic_write_json(path: str | Path, payload: Any) -> Path:
    return atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _persistent_project_state(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _persistent_project_state(item)
            for key, item in value.items()
            if str(key) not in EPHEMERAL_PROJECT_KEYS and not str(key).startswith("_session_")
        }
    if isinstance(value, list):
        return [_persistent_project_state(item) for item in value]
    if isinstance(value, tuple):
        return [_persistent_project_state(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def project_state_fingerprint(project: Dict[str, Any]) -> str:
    serialized = json.dumps(_persistent_project_state(project), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _backup_if_exists(path: Path) -> None:
    if not path.exists():
        return
    backup_dir = path.parent / "_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"{path.stem}_{stamp}{path.suffix}"
    atomic_write_bytes(backup_path, path.read_bytes())


def new_project(title: str, artist: str = DEFAULT_ARTIST, workflow_type: str = "music_pipeline") -> Dict[str, Any]:
    return {
        "version": "VelaFlow Beta 0.1.0",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "artist": artist,
        "workflow_type": workflow_type,
        "project_type": workflow_type,
        "song": {},
        "mv": {},
        "scene_edits": [],
        "character": normalize_character({}),
        "settings": {},
        "assets": {
            "audio_path": "",
            "images": {},
            "image_versions": {},
            "approved_images": {},
            "rejected_images": {},
            "locked_images": {},
            "hero_shot": "",
            "character_references": {},
            "videos": {},
            "video_versions": {},
            "video_metadata": {},
            "locked_videos": {},
        },
        "exports": [],
    }


def save_project(project: Dict[str, Any], base_dir: str = "outputs/projects") -> Path:
    folder = Path(base_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe_name(project.get('title','project'))}_v6_project.json"
    LOGGER.info("project_save_started path=%s", path)
    with project_file_lock(folder, project_file=path):
        _backup_if_exists(path)
        atomic_write_json(path, project)
    LOGGER.info("project_save_completed path=%s", path)
    return path


def save_project_folder(project: Dict[str, Any], base_dir: str = "project_data/music") -> Path:
    folder = Path(base_dir) / safe_name(project.get("title", "project"))
    folder.mkdir(parents=True, exist_ok=True)
    song = project.get("song", {}) or {}
    mv = project.get("mv", {}) or {}
    settings = project.get("settings", {}) or {}
    character = normalize_character(project.get("character") or mv.get("character_lock", {}) or {})
    assets = project.get("assets", {}) or {}
    storyboard = mv.get("storyboard", []) or []
    prompts = {
        "image_prompts": [item.get("image_prompt_with_character") or apply_character_to_prompt(item.get("expanded_prompt") or item.get("image_prompt", ""), character) for item in storyboard],
        "video_prompts": [item.get("video_prompt", "") for item in storyboard],
        "negative_prompts": [item.get("negative_prompt", "") for item in storyboard],
    }
    character_consistency = [
        {
            "scene": item.get("scene", index + 1),
            **consistency_report(item.get("image_prompt_with_character") or apply_character_to_prompt(item.get("expanded_prompt") or item.get("image_prompt", ""), character), character),
        }
        for index, item in enumerate(storyboard)
    ]
    image_review = {
        "images": assets.get("images", {}),
        "image_versions": assets.get("image_versions", {}),
        "approved_images": assets.get("approved_images", {}),
        "rejected_images": assets.get("rejected_images", {}),
        "locked_images": assets.get("locked_images", {}),
        "hero_shot": assets.get("hero_shot", ""),
        "character_references": assets.get("character_references", {}),
    }
    video_pipeline = {
        "videos": assets.get("videos", {}),
        "video_versions": assets.get("video_versions", {}),
        "video_metadata": assets.get("video_metadata", {}),
        "locked_videos": assets.get("locked_videos", {}),
    }
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    normalized_lyrics = song.get("normalized_song_output") or normalize_lyrics_tags(song.get("complete_lyrics", "") or project.get("manual_lyrics", ""), preset)
    normalized_song = {
        **song,
        "normalized_song_output": normalized_lyrics,
        "instrument_tag_validation": validate_english_only_tags(normalized_lyrics),
    }
    LOGGER.info("project_save_started project=%s", safe_name(project.get("title", "project")))
    with project_file_lock(folder):
        _backup_if_exists(folder / "project.json")
        atomic_write_json(folder / "song.json", normalized_song)
        atomic_write_json(folder / "storyboard.json", storyboard)
        atomic_write_json(folder / "prompts.json", prompts)
        atomic_write_json(folder / "settings.json", settings)
        atomic_write_json(folder / "character.json", character)
        atomic_write_text(folder / "character_prompt.txt", build_character_prompt(character))
        atomic_write_json(folder / "character_consistency.json", character_consistency)
        atomic_write_json(folder / "image_review.json", image_review)
        atomic_write_json(folder / "video_pipeline.json", video_pipeline)
        atomic_write_text(folder / "lyrics.txt", normalized_lyrics)
        atomic_write_json(folder / "artist_preset.json", song.get("artist_preset_data") or preset)
        # Commit the canonical project document last so readers see a coherent save.
        atomic_write_json(folder / "project.json", project)
    LOGGER.info("project_save_completed project=%s", safe_name(project.get("title", "project")))
    return folder


def save_project_if_dirty(
    project: Dict[str, Any],
    base_dir: str | Path,
    *,
    last_saved_fingerprint: str = "",
) -> Dict[str, Any]:
    fingerprint = project_state_fingerprint(project)
    folder = Path(base_dir) / safe_name(project.get("title", "project"))
    persisted_fingerprint = last_saved_fingerprint
    try:
        if not persisted_fingerprint and (folder / "project.json").is_file():
            with project_file_lock(folder):
                loaded = read_project_json(folder / "project.json", quarantine=False)
            if loaded.get("ok"):
                persisted_fingerprint = project_state_fingerprint(loaded["project"])
        if fingerprint == persisted_fingerprint:
            return {"ok": True, "saved": False, "dirty": False, "fingerprint": fingerprint, "path": str(folder)}
        saved_folder = save_project_folder(project, base_dir)
        return {"ok": True, "saved": True, "dirty": False, "fingerprint": fingerprint, "path": str(saved_folder)}
    except Exception as exc:
        LOGGER.exception("project_save_failed project=%s error=%s", safe_name(project.get("title", "project")), type(exc).__name__)
        return {"ok": False, "saved": False, "dirty": True, "fingerprint": persisted_fingerprint, "path": str(folder), "error": str(exc)}


def read_project_json(
    path: str | Path,
    *,
    attempts: int = PROJECT_LOAD_ATTEMPTS,
    retry_delay: float = PROJECT_LOAD_RETRY_SECONDS,
    reader: Callable[[Path], str] | None = None,
    quarantine: bool = True,
) -> Dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        return {"ok": False, "status": "missing", "project": None, "error": "missing_project"}
    read_text = reader or (lambda item: item.read_text(encoding="utf-8"))
    errors: list[Exception] = []
    malformed_payloads: list[str] = []
    for attempt in range(max(1, attempts)):
        try:
            raw = read_text(source)
            project = json.loads(raw)
            if not isinstance(project, dict):
                raise json.JSONDecodeError("Project root must be an object", raw, 0)
            return {"ok": True, "status": "loaded", "project": project, "error": ""}
        except json.JSONDecodeError as exc:
            errors.append(exc)
            malformed_payloads.append(hashlib.sha256(str(raw).encode("utf-8", errors="replace")).hexdigest())
        except (OSError, PermissionError) as exc:
            errors.append(exc)
        if attempt + 1 < max(1, attempts):
            LOGGER.info("project_load_retry path=%s attempt=%s", source, attempt + 1)
            time.sleep(max(0.0, retry_delay))
    confirmed_corruption = bool(malformed_payloads) and len(malformed_payloads) == len(errors) and len(set(malformed_payloads)) == 1
    broken_path = ""
    if confirmed_corruption and quarantine and source.is_file():
        broken = source.with_suffix(f".broken_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json")
        os.replace(source, broken)
        broken_path = str(broken)
        LOGGER.warning("confirmed_project_corruption path=%s backup=%s", source, broken)
    status = "confirmed_corruption" if confirmed_corruption else "temporary_read_failure"
    return {"ok": False, "status": status, "project": None, "broken_path": broken_path, "error": str(errors[-1]) if errors else "project_load_failed"}


def load_project(path: str) -> Dict[str, Any]:
    source = Path(path)
    try:
        with project_file_lock(source.parent, project_file=source):
            result = read_project_json(source)
    except ProjectLockTimeout as exc:
        LOGGER.warning("project_load_retry path=%s reason=lock_timeout", source)
        result = {"ok": False, "status": "temporary_read_failure", "project": None, "error": str(exc)}
    if result.get("ok"):
        return result["project"]
    return new_project(source.stem.replace("_v6_project", ""))
