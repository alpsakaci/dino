import pytest
import yaml
import json
import threading
from dino import Dino, DinoObserver

@pytest.fixture(autouse=True)
def reset_dino():
    """Reset the Dino singleton before each test."""
    Dino._instance = None
    Dino._configs = {}
    Dino._stop_event = threading.Event()
    Dino._file_watchers = []
    Dino._observers = []

def test_dino_is_singleton():
    d1 = Dino()
    d2 = Dino()
    assert d1 is d2

class MockObserver(DinoObserver):
    def __init__(self):
        self.notified = False

    def update_config(self):
        self.notified = True

def test_observer_attach_and_notify():
    dino = Dino()
    obs1 = MockObserver()
    obs2 = MockObserver()
    
    dino.attach([obs1, obs2])
    
    # Check if they are added
    assert obs1 in dino._observers
    assert obs2 in dino._observers
    
    # Test notification
    dino.notify()
    assert obs1.notified is True
    assert obs2.notified is True

def test_register_config(tmp_path):
    # Create a temporary yaml config file
    config_file = tmp_path / "config.yaml"
    config_data = {"database": {"host": "localhost", "port": 5432}}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    dino = Dino()
    dino.register_config("main", str(config_file))
    
    assert dino._configs["main"] == config_data

def test_register_duplicate_config_exits(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"key": "value"}, f)
        
    dino = Dino()
    dino.register_config("main", str(config_file))
    
    # Second time should sys.exit(1)
    with pytest.raises(SystemExit) as excinfo:
        dino.register_config("main", str(config_file))
    
    assert excinfo.value.code == 1

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

def test_dict_hash():
    dino = Dino()
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}
    
    hash1 = dino._get_dict_hash(d1)
    hash2 = dino._get_dict_hash(d2)
    
    assert hash1 == hash2

def test_stop_method(mocker):
    dino = Dino()
    mock_watcher = mocker.Mock()
    dino._file_watchers.append(mock_watcher)
    
    dino.stop()
    
    assert dino._stop_event.is_set()
    mock_watcher.join.assert_called_once()
