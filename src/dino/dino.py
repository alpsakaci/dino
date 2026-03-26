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
        self._watch_registry: Dict[str, Dict[str, Any]] = {}
        self._watcher_thread: Optional[threading.Thread] = None
        self._observers: List[DinoObserver] = []
        self._lock = threading.Lock()

    def __enter__(self) -> "Dino":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def _is_key_exists_in_configs(self, key: str) -> bool:
        """Check if a key exists in configs."""
        with self._lock:
            return key in self._configs

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

    def _watcher_loop(self) -> None:
        """A single thread that watches all registered files."""
        logger.info("Dino: Central file watcher started.")
        while not self._stop_event.is_set():
            time.sleep(1)

            current_time = time.time()
            with self._lock:
                registry_items = list(self._watch_registry.items())

            for name, data in registry_items:
                if current_time - data["last_check"] >= data["interval"]:
                    data["last_check"] = current_time
                    file_path = data["file_path"]

                    try:
                        current_mtime = os.path.getmtime(file_path)
                    except OSError:
                        continue

                    if current_mtime != data["last_mtime"]:
                        data["last_mtime"] = current_mtime
                        changed = self._set_config(name, file_path, True)
                        if changed:
                            logger.info(f"Dino: Config update successful for `{name}`")
                            self.notify(name)

    def stop(self) -> None:
        """Stops the background file watcher."""
        logger.info("Dino: Stop invoked.")
        self._stop_event.set()
        t = self._watcher_thread
        if t is not None and t.is_alive():
            t.join()

    def register_config(
        self, name: str, file_path: str, file_watch_interval_seconds: int = 0
    ) -> None:
        """Registers a new configuration to be managed."""
        self._validate_config_name(name)
        self._set_config(name, file_path)
        logger.info(f"Dino: `{name}` registered.")
        if file_watch_interval_seconds > 0:
            self._configs[name] = self._read_yaml(file_path)
            last_mtime = (
                os.path.getmtime(file_path) if os.path.exists(file_path) else 0.0
            )

            with self._lock:
                self._watch_registry[name] = {
                    "file_path": file_path,
                    "interval": file_watch_interval_seconds,
                    "last_check": time.time(),
                    "last_mtime": last_mtime,
                }

                t = self._watcher_thread
                if t is None or not t.is_alive():
                    self._watcher_thread = threading.Thread(target=self._watcher_loop)
                    self._watcher_thread.daemon = True
                    self._watcher_thread.start()

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
