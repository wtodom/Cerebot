"""Cerebot configuration data."""

from beem.config import Config

class CerebotConfig(Config):
    """Holds the LomLobot configuration data."""

    def __init__(self, path):
        super().__init__(path)

    def check_discord(self):
        if not self.get("discord"):
            self.error("The discord table is undefined")

        self.require_table_fields("discord", self.discord,
                ["username", "token"])

    def load(self):
        """Read the main TOML configuration data from self.path and check
        that the configuration is valid.

        """

        super().load()
        self.check_dcss()
        self.check_discord()

    def error(self, msg):
        raise Exception("Config file {}: {}".format(self.path, msg))
