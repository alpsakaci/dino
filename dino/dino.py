import sys
import logging
import yaml
import threading
import time
import hashlib
import json


class DinoObserver:
    def update_config(self):
        pass


class Dino:
    _instance = None
    _configs = {}
    _stop_event = threading.Event()
    _file_watchers = []
    _observers = []

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Dino, cls).__new__(cls)
        return cls._instance

    def _is_key_exists_in_configs(self, key):
        try:
            self._configs[key]
            return True
        except KeyError:
            return False

    def _validate_config_name(self, name):
        if self._is_key_exists_in_configs(name):
            logging.fatal(f"Dino: `{name}` is already registered.")
            sys.exit(1)
        logging.info(f"Dino: `{name}` validated.")

    def _read_yaml(self, file_path):
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except Exception as e:
            logging.fatal(f"Dino: File could not read. {e}")
            sys.exit(1)

    def _get_config(self, name):
        try:
            return self._configs[name]
        except KeyError:
            logging.fatal(f"Dino: Config `{name}` not found in registry.")
            sys.exit(1)

    @staticmethod
    def _get_dict_hash(dictionary):
        dict_string = json.dumps(dictionary, sort_keys=True).encode()
        return hashlib.md5(dict_string).hexdigest()

    def _set_config(self, name, file_path, hash_check=False):
        changed = False
        config_read = self._read_yaml(file_path)
        if not hash_check:
            self._configs[name] = config_read
            changed = True
        else:
            current_config_hash = Dino._get_dict_hash(self._configs[name])
            config_read_hash = Dino._get_dict_hash(config_read)

            if config_read_hash != current_config_hash:
                logging.info(f"Dino: Config `{name}` changed.")
                self._configs[name] = config_read
                changed = True

        return changed

    def _watch_file(self, name, file_path, sleep_seconds=60):
        logging.info(f"Dino: File watch started for `{name}`")
        while not self._stop_event.is_set():
            time.sleep(sleep_seconds)
            changed = self._set_config(name, file_path, True)
            if changed:
                logging.info(f"Dino: Config update successful for `{name}`")
                self.notify()

    def stop(self):
        logging.info("Dino: Stop invoked.")
        self._stop_event.set()
        for file_watcher in self._file_watchers:
            file_watcher.join()

    def register_config(self, name, file_path, file_watch_interval_seconds=0):
        self._validate_config_name(name)
        self._set_config(name, file_path)
        logging.info(f"Dino: `{name}` registered.")
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
            self._file_watchers.append(file_watcher)
            file_watcher.start()

    def get_config_value(self, config_name, key_path):
        keys_list = key_path.split(".")
        value = self._get_config(config_name)
        for key in keys_list:
            value = value.get(key)
            if value is None:
                return None
        return value

    def attach(self, observers):
        for observer in observers:
            if observer not in self._observers:
                self._observers.append(observer)

    def notify(self):
        for observer in self._observers:
            observer.update_config()
