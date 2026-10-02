"""Profile storage — JSON-file based persistence under .envforge/profiles/."""
import json
import os
import time
from pathlib import Path


STORE_DIR = ".envforge"
PROFILES_DIR = "profiles"
HISTORY_DIR = "history"
META_FILE = "meta.json"


class Store:
    """Manages profile storage on disk."""

    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or os.getcwd())
        self.root = self.base_dir / STORE_DIR
        self.profiles_dir = self.root / PROFILES_DIR
        self.history_dir = self.root / HISTORY_DIR

    def init(self):
        """Initialize the store directory structure."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.root / META_FILE
        if not meta_path.exists():
            meta = {
                "created_at": int(time.time()),
                "version": "1.0",
                "profiles": [],
            }
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return self.root

    def is_initialized(self):
        return self.root.exists() and self.profiles_dir.exists()

    def _profile_path(self, name):
        safe = name.replace("/", "_").replace("\\", "_")
        return self.profiles_dir / f"{safe}.json"

    def save(self, profile):
        """Save a profile. Returns the profile dict."""
        if not self.is_initialized():
            self.init()
        path = self._profile_path(profile["name"])
        path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
        self._update_meta(profile["name"])
        # Also save to history
        self._save_history(profile)
        return profile

    def _save_history(self, profile):
        """Save a historical snapshot of the profile."""
        name = profile["name"]
        hist_dir = self.history_dir / name
        hist_dir.mkdir(parents=True, exist_ok=True)
        ts = profile.get("captured_at", int(time.time()))
        hist_path = hist_dir / f"{ts}.json"
        hist_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    def _update_meta(self, name):
        meta_path = self.root / META_FILE
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            meta = {"created_at": int(time.time()), "version": "1.0", "profiles": []}
        if name not in meta["profiles"]:
            meta["profiles"].append(name)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def get(self, name):
        """Load a profile by name. Returns None if not found."""
        path = self._profile_path(name)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_profiles(self):
        """List all profile names."""
        if not self.profiles_dir.exists():
            return []
        names = []
        for f in sorted(self.profiles_dir.glob("*.json")):
            names.append(f.stem)
        return names

    def list_all(self):
        """List all profiles with their summary data."""
        from .capture import summarize_profile
        result = []
        for name in self.list_profiles():
            profile = self.get(name)
            if profile:
                result.append(summarize_profile(profile))
        return result

    def delete(self, name):
        """Delete a profile. Returns True if deleted."""
        path = self._profile_path(name)
        if path.exists():
            path.unlink()
            # Remove from meta
            meta_path = self.root / META_FILE
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if name in meta["profiles"]:
                    meta["profiles"].remove(name)
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            return True
        return False

    def history(self, name):
        """Get historical snapshots for a profile."""
        hist_dir = self.history_dir / name
        if not hist_dir.exists():
            return []
        snapshots = []
        for f in sorted(hist_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snapshots.append({
                    "timestamp": int(f.stem),
                    "iso": data.get("captured_at_iso", ""),
                    "tools": len(data.get("tools", {})),
                    "packages": sum(len(v) for v in data.get("packages", {}).values()),
                })
            except (json.JSONDecodeError, ValueError):
                continue
        return snapshots

    def stats(self):
        """Return store statistics."""
        profiles = self.list_profiles()
        total_history = 0
        for name in profiles:
            hist_dir = self.history_dir / name
            if hist_dir.exists():
                total_history += len(list(hist_dir.glob("*.json")))
        return {
            "profiles": len(profiles),
            "history_snapshots": total_history,
            "profile_names": profiles,
        }

    def export_profile(self, name, output_path):
        """Export a profile to a JSON file."""
        profile = self.get(name)
        if not profile:
            return False
        Path(output_path).write_text(
            json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True

    def import_profile(self, input_path):
        """Import a profile from a JSON file."""
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        if "name" not in data:
            raise ValueError("Profile file missing 'name' field")
        return self.save(data)
