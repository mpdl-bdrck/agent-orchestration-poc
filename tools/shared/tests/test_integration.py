"""
Integration tests for Google Sheets functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add the shared modules to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sheets.summary import SummaryManager
from sheets.schema import SchemaValidator


class TestIntegration(unittest.TestCase):
    """Integration tests for end-to-end functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.manager = SummaryManager(self.mock_service)
        self.validator = SchemaValidator()

    @patch('sheets.summary.SummaryManager._apply_formulas_to_sheet')
    @patch('sheets.summary.FormulaExtractor.get_sheet_id_by_name')
    def test_create_formula_dashboard_integration(self, mock_get_sheet_id, mock_apply_formulas):
        """Test end-to-end dashboard creation."""
        # Mock the sheet ID lookup
        mock_get_sheet_id.return_value = 123456

        # Mock successful formula application
        mock_apply_formulas.return_value = True

        # Test dashboard creation
        summary_config = self.validator.create_formula_config_template("Integration Test")
        rollup_sheets = ["Portfolio TOTAL", "Campaigns TOTAL", "Portfolio DAILY"]

        result = self.manager.create_formula_dashboard(
            spreadsheet_id="test_spreadsheet_id",
            summary_config=summary_config,
            rollup_sheets=rollup_sheets
        )

        self.assertTrue(result)
        mock_get_sheet_id.assert_called_with("test_spreadsheet_id", "Summary")
        mock_apply_formulas.assert_called_once()

    def test_formula_validation_and_generation_workflow(self):
        """Test the complete workflow from config validation to formula generation."""
        # Create a valid configuration
        config = self.validator.create_formula_config_template("Workflow Test")

        # Validate it
        is_valid = self.manager.validate_formula_config(config)
        self.assertTrue(is_valid)

        # Test formula generation from config
        formulas = {}
        for cell_ref, formula_config in config["formulas"].items():
            formulas[cell_ref] = formula_config["formula"]

        # Verify we have formulas
        self.assertGreater(len(formulas), 0)

        # Test that formulas are strings starting with =
        for formula in formulas.values():
            self.assertIsInstance(formula, str)
            self.assertTrue(formula.startswith('='))

    @patch('sheets.summary.SummaryManager._apply_single_formula')
    def test_error_handling_integration(self, mock_apply_single):
        """Test error handling in formula application."""
        # Mock some formulas failing, some succeeding
        mock_apply_single.side_effect = [True, False, True, False]

        formula_configs = {
            "A1": {"formula": "=SUM(B:B)", "fallback_value": "ERROR"},
            "A2": {"formula": "=INVALID()", "fallback_value": "N/A"},
            "A3": {"formula": "=AVERAGE(C:C)", "fallback_value": "0"},
            "A4": {"formula": "=BROKEN()", "fallback_value": "FAIL"}
        }

        results = self.manager.apply_formulas_with_fallbacks(
            "test_spreadsheet_id", 123, formula_configs
        )

        # Should have results for all formulas
        self.assertEqual(len(results), 4)

        # Check that some succeeded and some failed
        success_count = sum(1 for success in results.values() if success)
        self.assertGreater(success_count, 0)
        self.assertLess(success_count, 4)

    def test_sheet_config_inference(self):
        """Test automatic sheet configuration inference."""
        rollup_sheets = [
            "Line Items DAILY", "Line Items TOTAL",
            "Campaigns DAILY", "Campaigns TOTAL",
            "Portfolio DAILY", "Portfolio TOTAL",
            "Unknown Sheet", "Another Sheet"
        ]

        configs = self.manager._infer_sheet_configs(rollup_sheets)

        # Should correctly identify known sheet types
        self.assertEqual(configs["portfolio_total"], "Portfolio TOTAL")
        self.assertEqual(configs["campaigns_total"], "Campaigns TOTAL")
        self.assertEqual(configs["portfolio_daily"], "Portfolio DAILY")

        # Should not include line items (not implemented in inference logic)
        self.assertNotIn("line_items_total", configs)

        # Should not include unknown sheets
        self.assertNotIn("Unknown Sheet", configs)

    def test_cross_sheet_formula_generation(self):
        """Test generation of formulas that reference multiple sheets."""
        sheet_configs = {
            "portfolio_total": "Portfolio TOTAL",
            "campaigns_total": "Campaigns TOTAL",
            "portfolio_daily": "Portfolio DAILY"
        }

        formulas = self.manager.formula_generator.generate_portfolio_total_formulas(sheet_configs)

        # Check that formulas reference the correct sheets
        self.assertIn("'Portfolio TOTAL'", formulas["B2"])  # Total budget
        self.assertIn("'Portfolio TOTAL'", formulas["C2"])  # Total spend
        self.assertIn("'Campaigns TOTAL'", formulas["E2"])  # Avg campaign spend %
        self.assertIn("'Portfolio DAILY'", formulas["F2"])  # Latest daily ratio

        # Verify formula structure
        self.assertTrue(formulas["B2"].startswith("=SUM("))
        self.assertTrue(formulas["D2"].startswith("=IFERROR("))

    def test_config_file_workflow(self):
        """Test the complete config file workflow."""
        import tempfile

        # Create a temporary config file
        config = self.validator.create_formula_config_template("File Workflow Test")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_file = f.name

        try:
            # Test loading and validation
            loaded_config = self.manager.load_formula_config(config_file)
            self.assertIsNotNone(loaded_config)
            self.assertEqual(loaded_config["metadata"]["name"], "File Workflow Test")

            # Test file-based validation
            errors = self.validator.validate_config_file(config_file, "formula_config")
            self.assertEqual(len(errors), 0, f"File validation failed: {errors}")

        finally:
            os.unlink(config_file)


if __name__ == '__main__':
    unittest.main()
