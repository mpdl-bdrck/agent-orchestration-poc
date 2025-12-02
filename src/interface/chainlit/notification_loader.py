"""
Notification Loader Module

Loads alerts from JSON files, simulates API responses, and supports multiple playback modes.
This module provides a JSON-driven mock system that can be easily replaced with real API calls.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Singleton instance
_loader_instance: Optional['NotificationLoader'] = None


def _create_default_json(json_path: Path) -> None:
    """Create a default JSON file if it doesn't exist."""
    default_json = {
        "metadata": {
            "source": "mock_api",
            "version": "1.0",
            "description": "Mock alerts simulating Guardian/Optimizer/Specialist/Pathfinder detection"
        },
        "alerts": [
            {
                "id": "alert_001",
                "agent": "guardian",
                "issue_type": "under_pacing",
                "severity": "warning",
                "message": "Campaign 'Summer_2025' is under-pacing by 40%.",
                "campaign_id": "Summer_2025",
                "deal_id": None,
                "details": "Current spend: $12K of $20K budget. Expected: $16K by now.",
                "timestamp": None,
                "delay_seconds": 5
            },
            {
                "id": "alert_002",
                "agent": "optimizer",
                "issue_type": "bid_too_low",
                "severity": "warning",
                "message": "Deal 12345 has low win rate (2.1%).",
                "campaign_id": None,
                "deal_id": "12345",
                "details": "Win rate below 3% threshold. Consider increasing bid cap.",
                "timestamp": None,
                "delay_seconds": 35
            },
            {
                "id": "alert_003",
                "agent": "specialist",
                "issue_type": "geo_conflict",
                "severity": "critical",
                "message": "Deal 67890: Geo targeting conflict detected.",
                "campaign_id": None,
                "deal_id": "67890",
                "details": "Both buyer and seller have geo-targeting. CTV deal with 68% delivery drop.",
                "timestamp": None,
                "delay_seconds": 65
            },
            {
                "id": "alert_004",
                "agent": "pathfinder",
                "issue_type": "qps_limit",
                "severity": "info",
                "message": "SSP 'PubMatic' approaching QPS limit.",
                "campaign_id": None,
                "deal_id": None,
                "details": "Current: 8.2K QPS of 10K limit. Consider traffic allocation.",
                "timestamp": None,
                "delay_seconds": 95
            }
        ],
        "settings": {
            "mode": "streaming",
            "loop": True,
            "interval_seconds": 30,
            "max_alerts": 10
        }
    }
    
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(default_json, f, indent=2)
        logger.info(f"✅ Created default JSON file at {json_path}")
    except Exception as e:
        logger.error(f"Failed to create default JSON file: {e}", exc_info=True)
        raise


class NotificationLoader:
    """
    Loads and manages notification alerts from JSON files.
    
    Supports three playback modes:
    - streaming: Alerts appear one at a time
    - static: All alerts appear at once
    - replay: Uses delay_seconds from each alert for precise timing
    """
    
    def __init__(self, json_path: Optional[str] = None):
        """
        Initialize the NotificationLoader.
        
        Args:
            json_path: Optional path to JSON file. Defaults to config/notifications/mock_alerts.json
        """
        if json_path is None:
            # Default path relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            json_path = project_root / "config" / "notifications" / "mock_alerts.json"
        
        self.json_path = Path(json_path)
        self._data: Optional[Dict] = None
        self._current_index = 0
        
        # Load JSON file (or create default if missing)
        self.reload()
    
    def reload(self) -> None:
        """Reload the JSON file from disk."""
        try:
            if not self.json_path.exists():
                logger.warning(f"JSON file not found at {self.json_path}, creating default")
                _create_default_json(self.json_path)
            
            with open(self.json_path, 'r') as f:
                self._data = json.load(f)
            
            # Validate structure
            self._validate_structure()
            
            # Reset index
            self._current_index = 0
            
            logger.debug(f"✅ Loaded {len(self._data.get('alerts', []))} alerts from {self.json_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.json_path}: {e}", exc_info=True)
            raise ValueError(f"Invalid JSON structure in {self.json_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load JSON from {self.json_path}: {e}", exc_info=True)
            raise
    
    def _validate_structure(self) -> None:
        """Validate JSON structure."""
        if not isinstance(self._data, dict):
            raise ValueError("JSON root must be a dictionary")
        
        if "metadata" not in self._data:
            raise ValueError("JSON must contain 'metadata' section")
        
        if "alerts" not in self._data:
            raise ValueError("JSON must contain 'alerts' array")
        
        if "settings" not in self._data:
            raise ValueError("JSON must contain 'settings' section")
        
        # Validate alerts structure
        for i, alert in enumerate(self._data.get("alerts", [])):
            required_fields = ["id", "agent", "issue_type", "severity", "message"]
            for field in required_fields:
                if field not in alert:
                    raise ValueError(f"Alert {i} missing required field: {field}")
    
    def get_settings(self) -> Dict:
        """
        Get settings from JSON.
        
        Returns:
            Dictionary with mode, loop, interval_seconds, max_alerts
        """
        if self._data is None:
            self.reload()
        
        return self._data.get("settings", {
            "mode": "streaming",
            "loop": True,
            "interval_seconds": 30,
            "max_alerts": 10
        })
    
    def get_next_alert(self) -> Optional[Dict]:
        """
        Get the next alert in sequence (streaming mode).
        
        Returns:
            Alert dictionary with dynamic fields added, or None if no more alerts
        """
        if self._data is None:
            self.reload()
        
        alerts = self._data.get("alerts", [])
        if not alerts:
            return None
        
        # Get current alert
        if self._current_index >= len(alerts):
            settings = self.get_settings()
            if settings.get("loop", True):
                # Loop back to start
                self._current_index = 0
            else:
                # No more alerts
                return None
        
        alert = alerts[self._current_index].copy()
        
        # Add dynamic fields
        alert["timestamp"] = datetime.now().strftime("%H:%M:%S")
        if not alert.get("id"):
            alert["id"] = f"alert_{datetime.now().timestamp()}"
        
        # Move to next alert
        self._current_index += 1
        
        return alert
    
    def get_all_alerts(self) -> List[Dict]:
        """
        Get all alerts at once (static mode).
        
        Returns:
            List of alert dictionaries with dynamic fields added
        """
        if self._data is None:
            self.reload()
        
        alerts = self._data.get("alerts", [])
        result = []
        
        for alert in alerts:
            alert_copy = alert.copy()
            # Add dynamic fields
            alert_copy["timestamp"] = datetime.now().strftime("%H:%M:%S")
            if not alert_copy.get("id"):
                alert_copy["id"] = f"alert_{datetime.now().timestamp()}"
            result.append(alert_copy)
        
        return result
    
    def reset(self) -> None:
        """Reset to the beginning of the alert sequence."""
        self._current_index = 0
        logger.debug("Reset notification loader to beginning")
    
    @staticmethod
    def get_instance(json_path: Optional[str] = None) -> 'NotificationLoader':
        """
        Get singleton instance of NotificationLoader.
        
        Args:
            json_path: Optional path to JSON file (only used on first call)
        
        Returns:
            NotificationLoader instance
        """
        global _loader_instance
        if _loader_instance is None:
            _loader_instance = NotificationLoader(json_path)
        return _loader_instance

