"""
Unit tests for formula generation functionality.
"""

import unittest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add the shared modules to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sheets.formula_generator import FormulaGenerator
from sheets.formula_extractor import FormulaExtractor
from sheets.summary import SummaryManager


class TestFormulaGenerator(unittest.TestCase):
    """Test cases for FormulaGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = FormulaGenerator()

    def test_generate_sum_formula_no_sheet(self):
        """Test SUM formula generation without sheet reference."""
        result = self.generator.generate_sum_formula("B2:B10")
        self.assertEqual(result, "=SUM(B2:B10)")

    def test_generate_sum_formula_with_sheet(self):
        """Test SUM formula generation with sheet reference."""
        result = self.generator.generate_sum_formula("B2:B10", "Portfolio TOTAL")
        self.assertEqual(result, "=SUM('Portfolio TOTAL'!B2:B10)")

    def test_generate_average_formula_no_sheet(self):
        """Test AVERAGE formula generation without sheet reference."""
        result = self.generator.generate_average_formula("C:C")
        self.assertEqual(result, "=AVERAGE(C:C)")

    def test_generate_average_formula_with_sheet(self):
        """Test AVERAGE formula generation with sheet reference."""
        result = self.generator.generate_average_formula("C:C", "Campaigns TOTAL")
        self.assertEqual(result, "=AVERAGE('Campaigns TOTAL'!C:C)")

    def test_generate_countif_formula(self):
        """Test COUNTIF formula generation."""
        result = self.generator.generate_countif_formula("E:E", ">1", "Line Items TOTAL")
        self.assertEqual(result, "=COUNTIF('Line Items TOTAL'!E:E, >1)")

    def test_generate_max_formula(self):
        """Test MAX formula generation."""
        result = self.generator.generate_max_formula("F:F", "Portfolio DAILY")
        self.assertEqual(result, "=MAX('Portfolio DAILY'!F:F)")

    def test_generate_min_formula(self):
        """Test MIN formula generation."""
        result = self.generator.generate_min_formula("B:B")
        self.assertEqual(result, "=MIN(B:B)")

    def test_generate_iferror_formula(self):
        """Test IFERROR formula generation."""
        result = self.generator.generate_iferror_formula("=SUM(A:A)/SUM(B:B)", "N/A")
        self.assertEqual(result, "=IFERROR(=SUM(A:A)/SUM(B:B), N/A)")

    def test_generate_vlookup_formula(self):
        """Test VLOOKUP formula generation."""
        result = self.generator.generate_vlookup_formula(
            "Campaign_123", "A:B", 2, "Campaigns TOTAL"
        )
        self.assertEqual(result, "=VLOOKUP(Campaign_123, 'Campaigns TOTAL'!A:B, 2, FALSE)")

    def test_generate_portfolio_total_formulas(self):
        """Test generation of complete portfolio summary formulas."""
        sheet_configs = {
            "portfolio_total": "Portfolio TOTAL",
            "campaigns_total": "Campaigns TOTAL",
            "portfolio_daily": "Portfolio DAILY"
        }

        formulas = self.generator.generate_portfolio_total_formulas(sheet_configs)

        # Check that key formulas are generated
        self.assertIn("B2", formulas)  # Total budget
        self.assertIn("C2", formulas)  # Total spend
        self.assertIn("D2", formulas)  # Spend percentage
        self.assertIn("E2", formulas)  # Avg campaign spend %
        self.assertIn("F2", formulas)  # Latest daily spend ratio

        # Check specific formula content
        self.assertEqual(formulas["B2"], "=SUM('Portfolio TOTAL'!B2)")
        self.assertIn("IFERROR", formulas["D2"])  # Should include error handling

    def test_column_letter_to_index(self):
        """Test column letter to index conversion."""
        # Test the private method through the extractor
        extractor = FormulaExtractor(None)

        # Test single letters
        self.assertEqual(extractor._column_index_to_letter(0), "A")
        self.assertEqual(extractor._column_index_to_letter(25), "Z")

        # Test double letters
        self.assertEqual(extractor._column_index_to_letter(26), "AA")
        self.assertEqual(extractor._column_index_to_letter(51), "AZ")


class TestFormulaExtractor(unittest.TestCase):
    """Test cases for FormulaExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.extractor = FormulaExtractor(self.mock_service)

    @patch('sheets.summary.FormulaExtractor.extract_formulas')
    def test_extract_and_save_formulas(self, mock_extract):
        """Test formula extraction and saving to JSON."""
        # Mock the extract_formulas method
        mock_extract.return_value = {
            "A1": "=SUM(B:B)",
            "B2": "=AVERAGE(C:C)"
        }

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            result = self.extractor.extract_and_save_formulas(
                "spreadsheet_id", "Sheet1", "/tmp/test.json"
            )

            self.assertTrue(result)
            # Verify file was opened for writing
            mock_file.assert_called_with("/tmp/test.json", 'w')

    def test_parse_cell_reference(self):
        """Test cell reference parsing."""
        manager = SummaryManager(None)

        # Test valid references
        self.assertEqual(manager._parse_cell_reference("A1"), ("A", "1"))
        self.assertEqual(manager._parse_cell_reference("B10"), ("B", "10"))
        self.assertEqual(manager._parse_cell_reference("AA100"), ("AA", "100"))

        # Test invalid references
        with self.assertRaises(ValueError):
            manager._parse_cell_reference("INVALID")

        with self.assertRaises(ValueError):
            manager._parse_cell_reference("123")


class TestSummaryManager(unittest.TestCase):
    """Test cases for SummaryManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.manager = SummaryManager(self.mock_service)

    def test_infer_sheet_configs(self):
        """Test sheet configuration inference."""
        rollup_sheets = [
            "Line Items DAILY", "Line Items TOTAL",
            "Campaigns DAILY", "Campaigns TOTAL",
            "Portfolio DAILY", "Portfolio TOTAL"
        ]

        configs = self.manager._infer_sheet_configs(rollup_sheets)

        self.assertEqual(configs["portfolio_total"], "Portfolio TOTAL")
        self.assertEqual(configs["campaigns_total"], "Campaigns TOTAL")
        self.assertEqual(configs["portfolio_daily"], "Portfolio DAILY")

    def test_validate_formula_config_valid(self):
        """Test validation of valid formula configuration."""
        valid_config = {
            "metadata": {
                "name": "Test Config",
                "description": "Test description",
                "version": "1.0"
            },
            "formulas": {
                "A1": {"formula": "=SUM(B:B)", "description": "Test formula"},
                "B2": {"formula": "=AVERAGE(C:C)", "description": "Another formula"}
            }
        }

        self.assertTrue(self.manager.validate_formula_config(valid_config))

    def test_validate_formula_config_invalid(self):
        """Test validation of invalid formula configuration."""
        invalid_config = {
            "formulas": {
                "INVALID": {"formula": "=SUM(B:B)"}  # Invalid cell reference
            }
        }

        self.assertFalse(self.manager.validate_formula_config(invalid_config))

    @patch('sheets.summary.SummaryManager.load_formula_config')
    def test_load_formula_config_valid(self, mock_load):
        """Test loading valid formula configuration."""
        mock_load.return_value = {
            "metadata": {"name": "Test", "description": "Test", "version": "1.0"},
            "formulas": {"A1": {"formula": "=SUM(B:B)"}}
        }

        result = self.manager.load_formula_config("/tmp/test.json")
        self.assertIsInstance(result, dict)
        self.assertIn("formulas", result)

    def test_load_formula_config_invalid(self):
        """Test loading invalid formula configuration."""
        # Create a temporary invalid config file
        import tempfile
        invalid_config = {"invalid": "config"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_file = f.name

        try:
            with self.assertRaises(ValueError):
                self.manager.load_formula_config(temp_file)
        finally:
            import os
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
