from typing import Generator
from pathlib import Path
import logging
from json import load, dump

from . import Post

logger = logging.getLogger("BaseParser")

class BaseParser:
    _config_dir = Path(__file__).parent.joinpath("config")
    _data_dir = Path(__file__).parent.joinpath("data")

    def __init__(self, 
                 config_file: Path | str = None, 
                 data_file: Path | str = None,
                 default_config: dict = None,
                 default_data: dict = None) -> None:
        """Loads parser's data and configuration.

        - `self.file_data` will contain `data_file`'s contents
        - `self.config` will contain `config_file`'s contents

        Args:
            config_file (Path | str): file name relative to BaseParser._config_dir
            data_file (Path | str): file name relative to BaseParser._data_dir
            default_config (dict, optional): default config to write to file if not exists. Defaults to None.
            default_data (dict, optional): default data to write to file if not exists. Defaults to None.
        """
        self.config_file_path = self._config_dir.joinpath(config_file)
        self.data_file_path = self._data_dir.joinpath(data_file)

        self.config = self.load_json(
            file=self.config_file_path,
            default_data=default_config
        )

        self.file_data = self.load_json(
            file=self.data_file_path,
            default_data=default_data
        )

    @classmethod
    def load_json(cls,
                  file: Path,
                  default_data: dict = None) -> dict | list:
        """Loads json file.

        Args:
            file (Path): file name
            default_data (dict): defalt data if file doesn't exist

        Raises:
            FileNotFoundError: if resulting file does not exist AND default data not provided

        Returns:
            dict | list: loaded json data
        """
        # checking if file exists
        class_name = type(cls).__name__
        if not file.is_file():
            logger.info(f"{class_name} file missing: {file}")
            if default_data is None:
                raise FileNotFoundError(f"File {file} does not exist.")
            cls._write_json(file, default_data)
            logger.info(f"{class_name} created default: {file}")

        with open(file, 'r', encoding='utf-8') as f:
            json_data = load(f)
        logger.info(f"{class_name} file loaded: {file}")
        return json_data
    
    @staticmethod
    def _write_json(file: Path, data: dict):
        """Writes dict into json file

        Args:
            file (Path): file path
            data (dict): data dict
        """
        with open(file, 'w', encoding='utf-8') as f:
            dump(data, f, ensure_ascii=False, indent=2)

    def save_config(self):
        """Saves current config file at self.config_file_path"""
        self._write_json(self.config_file_path, self.config)

    def save_data(self):
        """Saves data file at self.data_file_path"""
        self._write_json(self.data_file_path, self.file_data)

    def scrape_posts(
        self,
        max_pages: int = 3
    ) -> Generator[Post, None, None]:
        raise NotImplementedError()
