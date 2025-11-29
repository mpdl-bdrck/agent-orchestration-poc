"""
JSON schema definitions and validation for Google Sheets configurations.

This module provides schema validation for formula configurations, formatting presets,
and other structured data used by the Google Sheets utilities.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validates JSON configurations against predefined schemas.
    """

    def __init__(self):
        """Initialize schema validator."""
        self.schemas = self._load_schemas()

    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined JSON schemas."""
        return {
            "formula_config": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["metadata", "formulas"],
                "properties": {
                    "metadata": {
                        "type": "object",
                        "required": ["name", "description", "version"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "version": {"type": "string"},
                            "extracted_from": {
                                "type": "object",
                                "properties": {
                                    "spreadsheet_id": {"type": "string"},
                                    "sheet_name": {"type": "string"},
                                    "range": {"type": "string"}
                                }
                            },
                            "extraction_date": {"type": "string"}
                        }
                    },
                    "formulas": {
                        "type": "object",
                        "patternProperties": {
                            "^[A-Z]+[0-9]+$": {
                                "type": "object",
                                "required": ["formula"],
                                "properties": {
                                    "formula": {"type": "string"},
                                    "description": {"type": "string"},
                                    "fallback_value": {},
                                    "dependencies": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "formatting_preset": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["metadata", "columns"],
                "properties": {
                    "metadata": {
                        "type": "object",
                        "required": ["name", "description", "version"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "version": {"type": "string"},
                            "created_at": {"type": "string"}
                        }
                    },
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer"},
                                "width": {"type": "number"},
                                "hidden": {"type": "boolean"},
                                "numberFormat": {"type": "object"},
                                "textFormat": {"type": "object"},
                                "backgroundColor": {"type": "object"}
                            }
                        }
                    },
                    "header_row": {
                        "type": "object",
                        "properties": {
                            "backgroundColor": {"type": "object"},
                            "textFormat": {"type": "object"},
                            "horizontalAlignment": {"type": "string"}
                        }
                    },
                    "conditional_formatting_rules": {"type": "array"},
                    "filters": {"type": "object"},
                    "frozen_rows": {"type": "integer"},
                    "frozen_columns": {"type": "integer"}
                }
            }
        }

    def validate_formula_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate a formula configuration against the schema.

        Args:
            config: Formula configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required top-level fields
        if "metadata" not in config:
            errors.append("Missing required field: metadata")
        if "formulas" not in config:
            errors.append("Missing required field: formulas")

        # Validate metadata
        if "metadata" in config:
            metadata = config["metadata"]
            required_meta_fields = ["name", "description", "version"]
            for field in required_meta_fields:
                if field not in metadata:
                    errors.append(f"Missing required metadata field: {field}")

        # Validate formulas structure
        if "formulas" in config:
            formulas = config["formulas"]
            if not isinstance(formulas, dict):
                errors.append("formulas must be an object")
            else:
                # Check cell reference format (e.g., A1, B2, AA10)
                import re
                cell_pattern = re.compile(r'^[A-Z]+[0-9]+$')
                for cell_ref, formula_config in formulas.items():
                    if not cell_pattern.match(cell_ref):
                        errors.append(f"Invalid cell reference format: {cell_ref}")

                    if not isinstance(formula_config, dict):
                        errors.append(f"Formula config for {cell_ref} must be an object")
                    elif "formula" not in formula_config:
                        errors.append(f"Missing formula for cell {cell_ref}")

        return errors

    def validate_formatting_preset(self, preset: Dict[str, Any]) -> List[str]:
        """
        Validate a formatting preset against the schema.

        Args:
            preset: Formatting preset dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required top-level fields
        if "metadata" not in preset:
            errors.append("Missing required field: metadata")
        if "columns" not in preset:
            errors.append("Missing required field: columns")

        # Validate metadata
        if "metadata" in preset:
            metadata = preset["metadata"]
            required_meta_fields = ["name", "description", "version"]
            for field in required_meta_fields:
                if field not in metadata:
                    errors.append(f"Missing required metadata field: {field}")

        # Validate columns
        if "columns" in preset:
            columns = preset["columns"]
            if not isinstance(columns, list):
                errors.append("columns must be an array")
            else:
                for i, col in enumerate(columns):
                    if not isinstance(col, dict):
                        errors.append(f"Column {i} must be an object")
                    elif "index" not in col:
                        errors.append(f"Column {i} missing required field: index")

        return errors

    def validate_config_file(self, filepath: str, config_type: str) -> List[str]:
        """
        Validate a configuration file.

        Args:
            filepath: Path to the configuration file
            config_type: Type of configuration ("formula_config" or "formatting_preset")

        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            with open(filepath, 'r') as f:
                config = json.load(f)

            if config_type == "formula_config":
                return self.validate_formula_config(config)
            elif config_type == "formatting_preset":
                return self.validate_formatting_preset(config)
            else:
                return [f"Unknown config type: {config_type}"]

        except FileNotFoundError:
            return [f"Configuration file not found: {filepath}"]
        except json.JSONDecodeError as e:
            return [f"Invalid JSON in configuration file: {e}"]
        except Exception as e:
            return [f"Error validating configuration: {e}"]

    def create_formula_config_template(self, name: str = "New Formula Config") -> Dict[str, Any]:
        """
        Create a template formula configuration.

        Args:
            name: Name for the configuration

        Returns:
            Template configuration dictionary
        """
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "metadata": {
                "name": name,
                "description": "Formula configuration template",
                "version": "1.0",
                "created_at": "2025-11-21"
            },
            "formulas": {
                "A1": {
                    "formula": "=SUM('Sheet1'!B:B)",
                    "description": "Example SUM formula",
                    "fallback_value": 0
                },
                "B1": {
                    "formula": "=AVERAGE('Sheet1'!C:C)",
                    "description": "Example AVERAGE formula",
                    "fallback_value": 0
                }
            }
        }

    def create_formatting_preset_template(self, name: str = "New Formatting Preset") -> Dict[str, Any]:
        """
        Create a template formatting preset.

        Args:
            name: Name for the preset

        Returns:
            Template preset dictionary
        """
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "metadata": {
                "name": name,
                "description": "Formatting preset template",
                "version": "1.0",
                "created_at": "2025-11-21"
            },
            "columns": [
                {
                    "index": 0,
                    "width": 120,
                    "numberFormat": {
                        "type": "DATE",
                        "pattern": "yyyy-mm-dd"
                    }
                },
                {
                    "index": 1,
                    "width": 100,
                    "numberFormat": {
                        "type": "CURRENCY",
                        "pattern": "$#,##0.00"
                    }
                }
            ],
            "header_row": {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                "textFormat": {"bold": True}
            },
            "conditional_formatting_rules": [],
            "filters": {"enabled": False},
            "frozen_rows": 1,
            "frozen_columns": 0
        }
