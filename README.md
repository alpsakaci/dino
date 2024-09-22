# Dino 🦖
#### Dynamic config management.

## Example usage

```yaml
# config.yml

client:
  my_client:
    url: example.com
```

```python
# main.py
import logging
import signal
from dino import Dino, DinoObserver


logging.basicConfig(level=logging.INFO)


def signal_handler(sig, frame):
    logging.info("Shutdown signal received")
    Dino().stop()  # Stop Dino gracefully.


class MyClient(DinoObserver):

    def __init__(self, url):
        self.url = url
        logging.info(f"MyClient initialized. {self.url}")

    def update_config(
        self,
    ):  # implement update_config from DinoObserver to update your configs when Dino notifies.
        self.url = Dino().get_config_value("appconfig", "client.my_client.url")
        logging.info(f"MyClient config updated. {self.url}")


def main():

    # Register your config yaml file.
    Dino().register_config(
        "appconfig",  # Config name
        "./config.yml",  # Yaml file path
        10,  # File read interval in seconds.
    )

    my_client = MyClient(Dino().get_config_value("appconfig", "client.my_client.url"))
    logging.info(f"MyClient url. {my_client.url}")

    Dino().attach(
        [
            my_client,  # Attach your objects which you want to get config updates.
        ]
    )


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
```
