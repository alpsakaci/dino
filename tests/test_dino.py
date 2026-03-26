import pytest
import yaml
import json
import threading
from dino import Dino, DinoObserver



class MockObserver(DinoObserver):
    def __init__(self):
        self.notified = False
        self.last_config = None

    def update_config(self, config_name: str):
        self.notified = True
        self.last_config = config_name

def test_observer_attach_and_notify():
    dino = Dino()
    obs1 = MockObserver()
    obs2 = MockObserver()
    
    dino.attach(obs1, obs2)
    
    # Check if they are added
    assert obs1 in dino._observers
    assert obs2 in dino._observers
    
    # Test notification
    dino.notify("test_config")
    assert obs1.notified is True
    assert obs1.last_config == "test_config"
    assert obs2.notified is True
    assert obs2.last_config == "test_config"

def test_register_config(tmp_path):
    # Create a temporary yaml config file
    config_file = tmp_path / "config.yaml"
    config_data = {"database": {"host": "localhost", "port": 5432}}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    dino = Dino()
    dino.register_config("main", str(config_file))
    
    assert dino._configs["main"] == config_data

def test_register_duplicate_config_raises(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"key": "value"}, f)
        
    dino = Dino()
    dino.register_config("main", str(config_file))
    
    # Second time should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        dino.register_config("main", str(config_file))
    
    assert "already registered" in str(excinfo.value)

def test_get_config_value(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {"db": {"host": "127.0.0.1", "credentials": {"user": "admin", "pass": "secret"}}}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    dino = Dino()
    dino.register_config("app", str(config_file))
    
    # Test valid keys
    assert dino.get_config_value("app", "db.host") == "127.0.0.1"
    assert dino.get_config_value("app", "db.credentials.user") == "admin"
    
    # Test non-existent keys
    assert dino.get_config_value("app", "db.nonexistent") is None
    assert dino.get_config_value("app", "invalid.path") is None

def test_stop_method():
    from unittest.mock import Mock
    dino = Dino()
    mock_watcher = Mock()
    dino._file_watchers.append(mock_watcher)
    
    dino.stop()
    
    assert dino._stop_event.is_set()
    mock_watcher.join.assert_called_once()

def test_missing_file_raises_error(tmp_path):
    dino = Dino()
    bad_path = str(tmp_path / "nonexistent.yaml")
    with pytest.raises(FileNotFoundError):
        dino.register_config("app", bad_path)

def test_duck_typing_default_value(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {
        "app": {
            "port": 8080,
            "features": ["a", "b"]
        }
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    dino = Dino()
    dino.register_config("main", str(config_file))
    
    # 1. Normal list access
    assert dino.get_config_value("main", "app.features.0") == "a"
    assert dino.get_config_value("main", "app.features.1") == "b"
    
    # 2. Out of bounds fallback
    assert dino.get_config_value("main", "app.features.99", default="NOT_FOUND") == "NOT_FOUND"
    
    # 3. Missing key completely fallback
    assert dino.get_config_value("main", "app.host", default="localhost") == "localhost"

def test_file_watcher_updates_config(tmp_path):
    import time
    config_file = tmp_path / "watch.yaml"
    with open(config_file, "w") as f:
        f.write("port: 80\n")
        
    dino = Dino()
    # Watch every 1 second
    dino.register_config("web", str(config_file), file_watch_interval_seconds=1)
    
    assert dino.get_config_value("web", "port") == 80
    
    time.sleep(1.1)
    with open(config_file, "w") as f:
        f.write("port: 90\n")
        
    time.sleep(2)
    assert dino.get_config_value("web", "port") == 90
    dino.stop()
