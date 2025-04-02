from pathlib import Path

config_dir = Path("config")
data_dir = Path("data")
log_dir = Path("log")

if not config_dir.is_dir():
    raise FileNotFoundError(f'Config dir is missing: {config_dir}')
if not data_dir.is_dir():
    data_dir.mkdir()
if not log_dir.is_dir():
    log_dir.mkdir()
