import os
import sys
import logging
import yaml  # type: ignore
from typing import Dict, List, Any, Optional
import threading
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DinoObserver(ABC):
    """Abstract base class for Dino Observers."""

    @abstractmethod
    def update_config(self, config_name: str) -> None:
        """Called when a configuration changes."""
        pass


class Dino:
    """Class managing YAML configurations and watching them for changes."""

    def __init__(self) -> None:
        """Initializes the Dino instance."""
        self._configs: Dict[str, Any] = {}
        self._stop_event = threading.Event()
        self._file_watchers: List[threading.Thread] = []
        self._observers: List[DinoObserver] = []
        self._lock = threading.Lock()

    def __enter__(self) -> "Dino":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def _is_key_exists_in_configs(self, key: str) -> bool:
        """Check if a key exists in configs."""
        with self._lock:
            try:
                self._configs[key]
                return True
            except KeyError:
                return False

    def _validate_config_name(self, name: str) -> None:
        """Validates if a configuration name is unique."""
        if self._is_key_exists_in_configs(name):
            logger.error(f"Dino: `{name}` is already registered.")
            raise ValueError(f"Dino: `{name}` is already registered.")
        logger.info(f"Dino: `{name}` validated.")

    def _read_yaml(self, file_path: str) -> Dict[str, Any]:
        """Reads and parses a YAML file."""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            logger.error(f"Dino: File could not read. {e}")
            raise FileNotFoundError(f"Dino: File could not read. {e}")

    def _get_config(self, name: str) -> Dict[str, Any]:
        """Returns the configuration map by name."""
        with self._lock:
            try:
                return self._configs[name]
            except KeyError:
                logger.error(f"Dino: Config `{name}` not found in registry.")
                raise KeyError(f"Dino: Config `{name}` not found in registry.")

    def _set_config(self, name: str, file_path: str, hash_check: bool = False) -> bool:
        """Sets configuration values and checks for changes if required."""
        changed = False
        config_read = self._read_yaml(file_path)

        with self._lock:
            if not hash_check:
                self._configs[name] = config_read
                changed = True
            else:
                if config_read != self._configs.get(name):
                    logger.info(f"Dino: Config `{name}` changed.")
                    self._configs[name] = config_read
                    changed = True

        return changed

    def _watch_file(self, name: str, file_path: str, sleep_seconds: int = 60) -> None:
        """Watches a configuration file for background updates."""
        logger.info(f"Dino: File watch started for `{name}`")
        last_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
        while not self._stop_event.is_set():
            time.sleep(sleep_seconds)
            try:
                current_mtime = os.path.getmtime(file_path)
            except OSError:
                continue

            if current_mtime != last_mtime:
                last_mtime = current_mtime
                changed = self._set_config(name, file_path, True)
                if changed:
                    logger.info(f"Dino: Config update successful for `{name}`")
                    self.notify(name)

    def stop(self) -> None:
        """Stops all background file watchers."""
        logger.info("Dino: Stop invoked.")
        self._stop_event.set()
        for file_watcher in self._file_watchers:
            file_watcher.join()

    def register_config(
        self, name: str, file_path: str, file_watch_interval_seconds: int = 0
    ) -> None:
        """Registers a new configuration to be managed."""
        self._validate_config_name(name)
        self._set_config(name, file_path)
        logger.info(f"Dino: `{name}` registered.")
        if file_watch_interval_seconds > 0:
            self._configs[name] = self._read_yaml(file_path)
            file_watcher = threading.Thread(
                target=self._watch_file,
                args=(
                    name,
                    file_path,
                    file_watch_interval_seconds,
                ),
            )
            file_watcher.daemon = True
            self._file_watchers.append(file_watcher)
            file_watcher.start()

    def get_config_value(
        self, config_name: str, key_path: str, default: Any = None
    ) -> Any:
        """Gets a configuration value using dot-notation (e.g. 'db.host')."""
        keys_list = key_path.split(".")
        value: Any = self._get_config(config_name)
        for key in keys_list:
            try:
                if isinstance(value, dict):
                    value = value.get(key)
                elif isinstance(value, (list, tuple)) and key.isdigit():
                    value = value[int(key)]
                else:
                    value = getattr(value, key)
            except Exception:
                return default

            if value is None:
                return default
        return value

    def attach(self, *observers: DinoObserver) -> None:
        """Attaches observers to be notified upon configuration changes."""
        for observer in observers:
            if observer not in self._observers:
                self._observers.append(observer)

    def notify(self, config_name: str) -> None:
        """Notifies all attached observers."""
        for observer in self._observers:
            observer.update_config(config_name)


# Global module-level instance
dino = Dino()
