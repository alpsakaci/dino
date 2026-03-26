# Dino 🦖
#### Dynamic config management.

[![PyPI version](https://badge.fury.io/py/dinocore.svg)](https://pypi.org/project/dinocore/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Dino is a high-performance, thread-safe configuration management library for Python. It parses YAML files, watches them for background changes using daemon threads, natively supports deep object queries via duck-typing, and alerts attached observers dynamically.

## Installation

```bash
pip install dinocore
```

## Features

- **Daemon Watchers:** Native background threads using OS file timestamps (`os.path.getmtime`) to reload configuration precisely when the YAML is edited.
- **Thread-Safety:** Atomic locking (`threading.Lock()`) protects the config state to entirely prevent read/write race conditions across environments.
- **Context Manager Support:** Graceful teardown out-of-the-box (`with dino: ...`).
- **Duck-Typing & Defaults:** Retrieve nested dictionaries, lists, or Python objects gracefully using dot-notation (`"foo.bar.0"`). Fallback to standard defaults avoiding `KeyError`s or `IndexError`s.
- **Dynamic Observer Payloads:** Listeners actively receive the specific `config_name` that updated, skipping guesswork.

## Example Usage

```yaml
# config.yml

client:
  my_client:
    url: example.com
    features:
      - logging
      - retries
```

```python
# main.py
import logging
import signal
import time
from dino.dino import dino, DinoObserver

logging.basicConfig(level=logging.INFO)

def signal_handler(sig, frame):
    logging.info("Shutdown signal received")
    dino.stop()  # Stop Dino watchers gracefully.


# Implement DinoObserver to update configs dynamically
class MyClient(DinoObserver):

    def __init__(self, url):
        self.url = url
        logging.info(f"MyClient initialized with url: {self.url}")

    def update_config(self, config_name: str):
        # Payload 'config_name' gives you explicit detail on which file triggered this
        if config_name == "appconfig":
            # Native fallback using 'default' parameter avoids breaking your app
            self.url = dino.get_config_value("appconfig", "client.my_client.url", default="localhost")
            logging.info(f"MyClient config updated. New url: {self.url}")


def main():
    # Register your config YAML file(s).
    dino.register_config(
        "appconfig",  # Config name
        "./config.yml",  # Yaml file path
        10,  # File read interval in seconds
    )

    # Use context managers optionally to auto-stop watchers on exit
    with dino:
        initial_url = dino.get_config_value("appconfig", "client.my_client.url", default="localhost")
        my_client = MyClient(initial_url)
        
        # Test duck-typing array retrieval (indexing lists via dot-notation)
        feature_0 = dino.get_config_value("appconfig", "client.my_client.features.0", default="n/a")
        logging.info(f"First feature enabled: {feature_0}")

        # Attach single or multiple listeners using *args
        dino.attach(my_client)

        # Keep main thread alive to watch daemon threads react
        while not dino._stop_event.is_set():
            time.sleep(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
```
