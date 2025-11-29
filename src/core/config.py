"""Agent configuration classes."""

from pathlib import Path
from typing import Any, Dict, List
import yaml
import logging

logger = logging.getLogger(__name__)


class AgentConfig:
    """Agent configuration loaded from YAML."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Agent configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file {config_path}: {e}")

        # Validate required fields
        required_fields = ["agent_id", "agent_name", "agent_type", "version", "llm", "prompts"]
        missing_fields = [field for field in required_fields if field not in self.config]
        if missing_fields:
            raise ValueError(f"Missing required fields in {config_path}: {missing_fields}")

        # Initialize LLM lazily
        self._llm = None
        self._llm_error = None

    @property
    def agent_id(self) -> str:
        return self.config["agent_id"]

    @property
    def agent_name(self) -> str:
        return self.config["agent_name"]

    @property
    def agent_type(self) -> str:
        return self.config["agent_type"]

    @property
    def version(self) -> str:
        return self.config["version"]

    @property
    def llm_config(self) -> Dict[str, Any]:
        return self.config["llm"]

    @property
    def prompts(self) -> Dict[str, str]:
        """Load prompt templates from files."""
        prompts = {}
        config_dir = self.config_path.parent

        for key, path in self.config["prompts"].items():
            # Handle both absolute and relative paths
            if Path(path).is_absolute():
                prompt_path = Path(path)
            else:
                prompt_path = config_dir / path

            try:
                with open(prompt_path) as f:
                    content = f.read()
                    prompts[key] = content
            except FileNotFoundError:
                raise FileNotFoundError(f"Prompt template file not found: {prompt_path}")
            except IOError as e:
                raise IOError(f"Error reading prompt template file {prompt_path}: {e}")
        return prompts

    @property
    def input_fields(self) -> List[str]:
        return self.config.get("input_fields", [])

    @property
    def output_fields(self) -> List[str]:
        return self.config.get("output_fields", [])

    @property
    def tools(self) -> List[str]:
        return self.config.get("tools", [])

    @property
    def validation(self) -> Dict[str, Any]:
        return self.config.get("validation", {})

    @property
    def retry(self) -> Dict[str, Any]:
        return self.config.get("retry", {})

    @property
    def performance(self) -> Dict[str, Any]:
        return self.config.get("performance", {})

