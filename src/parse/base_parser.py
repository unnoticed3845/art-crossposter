from typing import Generator
from pathlib import Path
import logging
from json import load, dump

from . import Post
from src.config import config_dir, data_dir

logger = logging.getLogger("BaseParser")

class BaseParser:
    def __init__(self, 
                 config_file: str, 
                 data_file: str,
                 default_data: dict = None) -> None:
        """Loads parser's data and configuration.

        Args:
            config_file (str): file name relative to config_dir
            data_file (str): file name relative to data_dir
            default_data (dict, optional): default data to write to file if not exists. Defaults to None.
        """            
        self.config_file_path = config_dir.joinpath(config_file)
        self.data_file_path = data_dir.joinpath(data_file)

        self.config = self.load_json(
            file=self.config_file_path
        )

        self.file_data = self.load_json(
            file=self.data_file_path,
            default_data=default_data
        )

    def load_json(self,
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
        class_name = type(self).__name__
        if not file.is_file():
            if default_data is None:
                raise FileNotFoundError(f"{class_name} file does not exist: {file}")
            logger.info(f"{class_name} file missing: {file}")
            self._write_json(file, default_data)
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
