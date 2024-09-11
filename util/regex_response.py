import random
import re
import datetime
from pathlib import Path
from re import RegexFlag

import yaml

from shared import debug_stream


class RegexResponse:

	def __init__(self, response_config_path: Path):
		self.name = ""
		self.raw_pattern_string = ""
		self.responses = None
		self.cooldown = None
		self.cooldown_file = None
		self.regex = None
		self._load_config(response_config_path)

	def _load_config(self, config_path: Path):
		with open(config_path, "r") as config_file:
			response_config = yaml.safe_load(config_file)
		self.name = response_config["name"]
		self.raw_pattern_string = response_config["pattern"]
		self.responses = response_config["responses"]
		self.cooldown = datetime.timedelta(minutes=response_config["cooldown"])
		self.cooldown_file = config_path.with_suffix(".cooldown")
		regex_flags = RegexFlag.IGNORECASE
		if "case_insensitive" in response_config and not response_config["case_insensitive"]:
				regex_flags = 0
		self.regex = re.compile(self.raw_pattern_string, regex_flags)
		print(f"Created RegEx response with pattern {self.regex}", file=debug_stream, flush=True)
	def is_on_cooldown(self):
		if self.cooldown_file.exists():
			last_modified = datetime.datetime.fromtimestamp(self.cooldown_file.stat().st_mtime)
			return datetime.datetime.now() - last_modified < self.cooldown
		else:
			return False



	def check_response(self, message: str):
		if not self.is_on_cooldown():
			if self.regex.search(message):
				self.cooldown_file.touch()
				return random.choice(self.responses)

	def reset_cooldown(self):
		self.cooldown_file.unlink(missing_ok=True)
