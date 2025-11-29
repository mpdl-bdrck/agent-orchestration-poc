"""
Deal Classifier
================

Classifies line items as Deal vs Marketplace based on client-specific patterns.
"""

from .utils.config import load_client_config


class DealClassifier:
    """
    Classifies line items as Deal vs Marketplace based on client-specific patterns
    """
    
    def __init__(self, client_config=None):
        """
        Initialize with client config (loaded from config/clients/[client].json)
        
        Args:
            client_config (dict, optional): Client configuration dictionary
        """
        self.client_config = client_config or {}
        deal_classification = self.client_config.get('deal_classification', {})
        self.deal_patterns = deal_classification.get('patterns', {})
        self.case_sensitive = deal_classification.get('case_sensitive', False)
    
    @classmethod
    def from_client_name(cls, client_name):
        """
        Factory method to create classifier from client name
        
        Args:
            client_name (str): Name of the client (e.g., "Tricoast")
            
        Returns:
            DealClassifier: Configured classifier instance
        """
        client_config = load_client_config(client_name)
        return cls(client_config)
    
    def classify_inventory_type(self, line_item_name):
        """
        Check line item name for patterns from client config
        Returns: "Deals" or "Marketplace"
        
        Examples (Tricoast):
        - "Zepbound - :90s - Marketplace" → "Marketplace"
        - "OSA DSE - :30s - Deals - November" → "Deals"
        
        Args:
            line_item_name (str): Name of the line item
            
        Returns:
            str: "Deals" or "Marketplace"
        """
        if not line_item_name:
            return "Marketplace"  # Default fallback
        
        search_text = line_item_name if self.case_sensitive else line_item_name.upper()
        deals_patterns = [
            p.upper() if not self.case_sensitive else p 
            for p in self.deal_patterns.get('deals', [])
        ]
        marketplace_patterns = [
            p.upper() if not self.case_sensitive else p 
            for p in self.deal_patterns.get('marketplace', [])
        ]
        
        # Check for "Deals" patterns first (more specific)
        for pattern in deals_patterns:
            if pattern in search_text:
                return "Deals"
        
        # Check for "Marketplace" patterns
        for pattern in marketplace_patterns:
            if pattern in search_text:
                return "Marketplace"
        
        # Default fallback
        return "Marketplace"

