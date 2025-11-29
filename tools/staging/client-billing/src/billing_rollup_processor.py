"""
Billing Rollup Processor
=========================

Processes raw daily line item data into billing rollup format:
- Groups by Advertiser → Campaign
- Optionally splits by Deal/Marketplace inventory type
- Aggregates impressions and spend
"""

import pandas as pd
from .deal_classifier import DealClassifier
from .utils.logging import setup_logger


class BillingRollupProcessor:
    """
    Creates advertiser → campaign rollup with Deal/Marketplace split
    """
    
    def __init__(self, deal_classifier=None):
        """
        Initialize the billing rollup processor
        
        Args:
            deal_classifier (DealClassifier, optional): Classifier for Deal vs Marketplace
        """
        self.deal_classifier = deal_classifier
        self.logger = setup_logger('billing.rollup.processor')
    
    def create_billing_rollup(self, daily_line_items, split_by_inventory=True):
        """
        Groups by:
        - Advertiser
        - Campaign (within advertiser)
        - Deal vs Marketplace (if split_by_inventory=True)
        
        Args:
            daily_line_items: DataFrame with daily line item records
            split_by_inventory: Whether to split by Deal/Marketplace
        
        Returns:
            DataFrame with columns:
            - advertiser_name
            - campaign_name
            - inventory_type (Deals/Marketplace, if split_by_inventory)
            - impressions
            - spend
        """
        if daily_line_items.empty:
            self.logger.warning("Empty daily_line_items DataFrame provided")
            return pd.DataFrame(columns=[
                'advertiser_name', 'campaign_name', 'inventory_type', 'impressions', 'spend'
            ])
        
        # Ensure required columns exist
        required_cols = ['advertiser_name', 'campaign_name', 'line_item_name', 'total_spent', 'total_impressions']
        missing_cols = [col for col in required_cols if col not in daily_line_items.columns]
        if missing_cols:
            self.logger.error(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()
        
        # Add inventory_type column if splitting by inventory
        df = daily_line_items.copy()
        if split_by_inventory and self.deal_classifier:
            df['inventory_type'] = df['line_item_name'].apply(
                lambda name: self.deal_classifier.classify_inventory_type(name)
            )
            groupby_cols = ['advertiser_name', 'campaign_name', 'inventory_type']
        else:
            groupby_cols = ['advertiser_name', 'campaign_name']
        
        # Group and aggregate
        grouped = df.groupby(groupby_cols, as_index=False).agg({
            'total_impressions': 'sum',
            'total_spent': 'sum'
        })
        
        # Rename columns
        grouped = grouped.rename(columns={
            'total_impressions': 'impressions',
            'total_spent': 'spend'
        })
        
        # Round spend to 2 decimals
        grouped['spend'] = grouped['spend'].round(2)
        
        # Ensure impressions are integers
        grouped['impressions'] = grouped['impressions'].astype(int)
        
        # Sort by advertiser_name, then campaign_name
        sort_cols = ['advertiser_name', 'campaign_name']
        if 'inventory_type' in grouped.columns:
            sort_cols.append('inventory_type')
        grouped = grouped.sort_values(sort_cols).reset_index(drop=True)
        
        self.logger.info(f"Created billing rollup with {len(grouped)} rows")
        return grouped

