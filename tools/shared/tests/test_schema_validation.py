"""
Unit tests for schema validation functionality.
"""

import unittest
import json
import sys
import os

# Add the shared modules to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sheets.schema import SchemaValidator


class TestSchemaValidator(unittest.TestCase):
    """Test cases for SchemaValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()

    def test_validate_formula_config_valid(self):
        """Test validation of valid formula configuration."""
        valid_config = {
            "metadata": {
                "name": "Test Campaign Dashboard",
                "description": "Test formula configuration",
                "version": "1.0",
                "created_at": "2025-11-21"
            },
            "formulas": {
                "A1": {
                    "formula": "=SUM('Portfolio TOTAL'!B2)",
                    "description": "Total budget formula",
                    "fallback_value": 0
                },
                "B2": {
                    "formula": "=AVERAGE('Campaigns TOTAL'!E:E)",
                    "description": "Average campaign spend %",
                    "fallback_value": 0
                }
            }
        }

        errors = self.validator.validate_formula_config(valid_config)
        self.assertEqual(len(errors), 0, f"Unexpected validation errors: {errors}")

    def test_validate_formula_config_missing_metadata(self):
        """Test validation fails when metadata is missing."""
        invalid_config = {
            "formulas": {
                "A1": {"formula": "=SUM(B:B)"}
            }
        }

        errors = self.validator.validate_formula_config(invalid_config)
        self.assertIn("Missing required field: metadata", errors)

    def test_validate_formula_config_missing_formulas(self):
        """Test validation fails when formulas field is missing."""
        invalid_config = {
            "metadata": {
                "name": "Test",
                "description": "Test",
                "version": "1.0"
            }
        }

        errors = self.validator.validate_formula_config(invalid_config)
        self.assertIn("Missing required field: formulas", errors)

    def test_validate_formula_config_invalid_cell_reference(self):
        """Test validation fails for invalid cell references."""
        invalid_config = {
            "metadata": {
                "name": "Test",
                "description": "Test",
                "version": "1.0"
            },
            "formulas": {
                "INVALID_REFERENCE": {
                    "formula": "=SUM(B:B)"
                }
            }
        }

        errors = self.validator.validate_formula_config(invalid_config)
        self.assertTrue(any("Invalid cell reference format" in error for error in errors))

    def test_validate_formula_config_missing_formula(self):
        """Test validation fails when formula is missing from config."""
        invalid_config = {
            "metadata": {
                "name": "Test",
                "description": "Test",
                "version": "1.0"
            },
            "formulas": {
                "A1": {
                    "description": "Missing formula"
                }
            }
        }

        errors = self.validator.validate_formula_config(invalid_config)
        self.assertIn("Missing formula for cell A1", errors)

    def test_validate_formatting_preset_valid(self):
        """Test validation of valid formatting preset."""
        valid_preset = {
            "metadata": {
                "name": "Test Formatting",
                "description": "Test formatting preset",
                "version": "1.0",
                "created_at": "2025-11-21"
            },
            "columns": [
                {
                    "index": 0,
                    "width": 120,
                    "numberFormat": {"type": "CURRENCY"}
                },
                {
                    "index": 1,
                    "width": 100,
                    "hidden": False
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

        errors = self.validator.validate_formatting_preset(valid_preset)
        self.assertEqual(len(errors), 0, f"Unexpected validation errors: {errors}")

    def test_validate_formatting_preset_missing_metadata(self):
        """Test formatting preset validation fails without metadata."""
        invalid_preset = {
            "columns": []
        }

        errors = self.validator.validate_formatting_preset(invalid_preset)
        self.assertIn("Missing required field: metadata", errors)

    def test_validate_formatting_preset_invalid_columns(self):
        """Test formatting preset validation fails with invalid columns."""
        invalid_preset = {
            "metadata": {
                "name": "Test",
                "description": "Test",
                "version": "1.0"
            },
            "columns": "not_an_array"
        }

        errors = self.validator.validate_formatting_preset(invalid_preset)
        self.assertIn("columns must be an array", errors)

    def test_create_formula_config_template(self):
        """Test creation of formula configuration template."""
        template = self.validator.create_formula_config_template("Test Template")

        # Validate the generated template
        errors = self.validator.validate_formula_config(template)
        self.assertEqual(len(errors), 0, f"Template validation failed: {errors}")

        # Check template structure
        self.assertIn("metadata", template)
        self.assertIn("formulas", template)
        self.assertEqual(template["metadata"]["name"], "Test Template")

    def test_create_formatting_preset_template(self):
        """Test creation of formatting preset template."""
        template = self.validator.create_formatting_preset_template("Test Preset")

        # Validate the generated template
        errors = self.validator.validate_formatting_preset(template)
        self.assertEqual(len(errors), 0, f"Template validation failed: {errors}")

        # Check template structure
        self.assertIn("metadata", template)
        self.assertIn("columns", template)
        self.assertEqual(template["metadata"]["name"], "Test Preset")

    def test_validate_config_file_formula_config(self):
        """Test file-based validation for formula config."""
        # Create a temporary valid config file
        import tempfile
        valid_config = self.validator.create_formula_config_template()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_config, f)
            temp_file = f.name

        try:
            errors = self.validator.validate_config_file(temp_file, "formula_config")
            self.assertEqual(len(errors), 0, f"File validation failed: {errors}")
        finally:
            os.unlink(temp_file)

    def test_validate_config_file_formatting_preset(self):
        """Test file-based validation for formatting preset."""
        # Create a temporary valid preset file
        import tempfile
        valid_preset = self.validator.create_formatting_preset_template()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_preset, f)
            temp_file = f.name

        try:
            errors = self.validator.validate_config_file(temp_file, "formatting_preset")
            self.assertEqual(len(errors), 0, f"File validation failed: {errors}")
        finally:
            os.unlink(temp_file)

    def test_validate_config_file_not_found(self):
        """Test validation of non-existent file."""
        errors = self.validator.validate_config_file("/nonexistent/file.json", "formula_config")
        self.assertEqual(len(errors), 1)
        self.assertIn("Configuration file not found", errors[0])

    def test_validate_config_file_invalid_json(self):
        """Test validation of file with invalid JSON."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_file = f.name

        try:
            errors = self.validator.validate_config_file(temp_file, "formula_config")
            self.assertEqual(len(errors), 1)
            self.assertIn("Invalid JSON", errors[0])
        finally:
            os.unlink(temp_file)

    def test_validate_config_file_unknown_type(self):
        """Test validation with unknown config type."""
        import tempfile
        valid_config = {"test": "data"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_config, f)
            temp_file = f.name

        try:
            errors = self.validator.validate_config_file(temp_file, "unknown_type")
            self.assertEqual(len(errors), 1)
            self.assertIn("Unknown config type", errors[0])
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
