#!/usr/bin/env python3
"""Check if Nov 26 UTC 08:00-09:59 data exists (should map to Nov 26 PST 00:00-01:59)"""

import sys
import os

env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from database_connector import DatabaseConnector

db = DatabaseConnector()

# Get a campaign UUID
campaign_query = '''
    SELECT DISTINCT c."campaignUuid"
    FROM "lineItems" li
    JOIN "campaigns" c ON li."campaignId" = c."campaignId"
    LEFT JOIN "advertisers" adv ON c."advertiserId" = adv."advertiserId"
    LEFT JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
    WHERE cp."accountId" = %s
        AND c."statusId" IN (1, 2, 3)
        AND adv."name" ILIKE %s
    LIMIT 1
'''
campaigns = db.execute_postgres_query(campaign_query, (17, '%Lilly%'))
if not campaigns:
    print('No campaigns found')
    sys.exit(1)

campaign_uuid = str(campaigns[0][0])
print(f'Testing with campaign: {campaign_uuid[:8]}...')

# Query specifically for Nov 26 UTC 08:00-09:59 (should map to Nov 26 PST 00:00-01:59)
redshift_query = '''
    SELECT 
        year, month, day, hour,
        DATE(CONVERT_TIMEZONE('UTC', 'America/Los_Angeles', 
             (TO_DATE(year::VARCHAR || '-' || LPAD(month::VARCHAR, 2, '0') || '-' || LPAD(day::VARCHAR, 2, '0'), 'YYYY-MM-DD')::VARCHAR || ' ' || LPAD(hour::VARCHAR, 2, '0') || ':00:00')::TIMESTAMP)) as date_local,
        SUM(media_spend) as total_spent
    FROM public.overview
    WHERE campaign_id = %s
      AND year = 2025
      AND month = 11
      AND day = 26
      AND hour >= 8
      AND hour <= 9
      AND media_spend > 0
    GROUP BY year, month, day, hour, date_local
    ORDER BY year, month, day, hour
'''

results = db.execute_redshift_query(redshift_query, (campaign_uuid,))
print(f'\nQuery results for Nov 26 UTC 08:00-09:59:')
print('UTC Time          PST Date      Spend')
print('-' * 50)
for row in results:
    utc_time = f'{row[0]}-{row[1]:02d}-{row[2]:02d} {row[3]:02d}:00'
    pst_date = row[4]
    spend = row[5]
    print(f'{utc_time}    {pst_date}    ${spend:.2f}')

if not results:
    print('❌ No data found for Nov 26 UTC 08:00-09:59')
    print('   This explains why there\'s no Nov 26 PST data!')
    print('   The data simply hasn\'t been loaded into Redshift yet for those hours.')
else:
    print(f'\n✅ Found {len(results)} hours of data')
    print('   This data SHOULD map to Nov 26 PST and appear in the report!')

