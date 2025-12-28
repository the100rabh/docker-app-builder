
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".docker-app-builder"

def get_config_dir():
    """Returns the config directory path, creating it if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def save_config(config_data):
    """Saves a container configuration to a JSON file."""
    if 'container_name' not in config_data:
        raise ValueError("'container_name' is a required key in config_data")
    
    config_dir = get_config_dir()
    container_name = config_data['container_name']
    file_path = config_dir / f"{container_name}.json"
    
    with open(file_path, 'w') as f:
        json.dump(config_data, f, indent=4)
    return file_path

def load_config(config_name):
    """Loads a container configuration from a JSON file."""
    config_dir = get_config_dir()
    file_path = config_dir / f"{config_name}.json"
    
    if not file_path.exists():
        return None
        
    with open(file_path, 'r') as f:
        return json.load(f)

def get_saved_configs():
    """Returns a list of saved configuration file names."""
    config_dir = get_config_dir()
    if not config_dir.exists():
        return []
    
    return [p.stem for p in config_dir.glob("*.json")]
