# Database Management

## Overview

This comprehensive guide covers database management procedures for all Bedrock Platform database systems, including Aerospike, PostgreSQL, and Amazon Redshift. It provides operational procedures for maintenance, optimization, backup, recovery, and troubleshooting across the platform's data infrastructure.

## Database Architecture Overview

### Platform Database Systems
```yaml
Database Infrastructure:
Aerospike (NoSQL Cache):
  - Purpose: High-performance real-time data storage
  - Use Cases: Campaign configuration, user data, curation data
  - Deployment: 3-node cluster (staging + production)
  - Characteristics: Distributed, horizontally scalable, sub-millisecond latency

PostgreSQL (Relational):
  - Purpose: Transactional data and configuration management
  - Use Cases: Terminal UI data, campaign management, user accounts
  - Deployment: AWS RDS instances (stage + production)
  - Characteristics: ACID compliance, complex queries, referential integrity

Amazon Redshift (Analytics):
  - Purpose: Data warehousing and analytics
  - Use Cases: Reporting, performance analytics, historical data
  - Deployment: AWS Redshift cluster
  - Characteristics: Columnar storage, massive parallel processing
```

### Data Flow Architecture
```yaml
Data Flow Patterns:
Real-Time Data Path:
  - Bid Requests → Aerospike (user lookup, campaign config)
  - Campaign Updates → PostgreSQL → Aerospike (sync)
  - Event Tracking → Redshift (analytics)

Batch Data Processing:
  - ETL Jobs → Aerospike (segment data, audience updates)
  - Log Aggregation → Redshift (reporting data)
  - Configuration Sync → PostgreSQL ↔ Aerospike

Cross-Database Dependencies:
  - Terminal (PostgreSQL) ↔ Bidder (Aerospike) synchronization
  - Event logs → Redshift aggregation
  - User sync data → Aerospike storage
```

## Aerospike Database Management

### Aerospike Architecture and Configuration

#### Cluster Configuration
```yaml
Aerospike Cluster Setup:
Production Cluster:
  - Nodes: 3 instances for high availability
  - Deployment: Kubernetes-based on AWS/GCP
  - Access: aerodb-aerospike.production.svc.cluster.local
  - Port: 3000 (default), 31000 (external)
  - Replication Factor: 2 (data replicated across 2 nodes)

Regional Deployment:
EU (AWS):
  - Primary cluster: aero.eu-west1.bedrockplatform.bid:31000
  - Use Case: European traffic and data processing
  
APAC (GCP):
  - Secondary cluster: aero.apac-tokyo.bedrockplatform.bid:31000
  - Use Case: Asia-Pacific traffic with lower latency
```

#### Namespace and Set Structure
```yaml
Aerospike Data Organization:
Namespaces (Database-level):
bidder.*:
  - Purpose: Campaign configuration and bidding data
  - Sets: lineitems, creatives, orders, videos, lumen
  - TTL: Varies by data type (campaign duration-based)
  - Storage: Memory + SSD persistence

dmp.*:
  - Purpose: Data management platform and curation data
  - Sets: mapping, segments
  - TTL: Based on segment expiry (7-90 days typical)
  - Storage: Memory-optimized for fast lookup

spend.*:
  - Purpose: Budget tracking and pacing control
  - Sets: spend (budget consumption tracking)
  - TTL: Campaign duration + 30 days
  - Storage: Persistent with frequent updates
```

### Aerospike Operations and Maintenance

#### Accessing Aerospike
```bash
# Method 1: Direct kubectl access
kubectl run -ti aerospike-tools-YOUR_PREFIX \
  --image=aerospike/aerospike-tools --rm -- \
  aql -h aerodb-aerospike.production.svc.cluster.local

# Method 2: Regional access
kubectl run -ti aerospike-tools-YOUR_PREFIX \
  --image=aerospike/aerospike-tools --rm -- \
  aql -h aero.eu-west1.bedrockplatform.bid -p 31000

# Method 3: Automated script (add to ~/.zshrc)
aerospike() {
  local cluster=""
  local namespace="production"
  local aerospike_host="aerodb-aerospike.production.svc.cluster.local"
  
  while [[ $# -gt 0 ]]; do
    case $1 in
      --aws)
        cluster="aws"
        shift
        ;;
      --gcp)
        cluster="gcp"
        shift
        ;;
      *)
        echo "Usage: aerospike [--aws|--gcp]"
        return 1
        ;;
    esac
  done
  
  if [[ -z "$cluster" ]]; then
    echo "Usage: aerospike [--aws|--gcp]"
    return 1
  fi
  
  echo "Connecting to $cluster Aerospike..."
  local existing_pod=$(kubectl get pods -n "$namespace" \
    --field-selector=status.phase=Running 2>/dev/null | \
    grep aerospike-tools | head -1 | awk '{print $1}')
  
  if [[ -n "$existing_pod" ]]; then
    echo "Found existing pod: $existing_pod"
    kubectl exec -ti "$existing_pod" -n "$namespace" -- \
      aql -h "$aerospike_host"
  else
    echo "Creating new pod..."
    kubectl run -ti "aerospike-tools-$(whoami)" \
      --image=aerospike/aerospike-tools --rm -- \
      aql -h "$aerospike_host"
  fi
}
```

#### Common Aerospike Queries
```sql
-- List all namespaces and sets
SHOW SETS

-- View set statistics
SELECT * FROM bidder.lineitems LIMIT 10

-- Check specific campaign configuration
SELECT * FROM bidder.orders WHERE ID = 'campaign-uuid'

-- Monitor segment data
SELECT * FROM dmp.segments LIMIT 50

-- Check spend tracking
SELECT * FROM bidder.spend WHERE lineitem_id = 'lineitem-uuid'

-- View user segments for targeting
SELECT * FROM dmp.mapping WHERE user_id = 'user-identifier'
```

#### Performance Monitoring
```yaml
Aerospike Performance Metrics:
Key Performance Indicators:
  - Query Response Time: Target <1ms for 95th percentile
  - Throughput: Monitor QPS per namespace
  - Memory Usage: Track memory consumption per namespace
  - Disk Usage: Monitor SSD storage utilization
  - Replication Lag: Ensure data consistency across nodes

Monitoring Commands:
# Cluster status
asadm -e "show statistics"

# Namespace statistics
asadm -e "show statistics namespace"

# Set-level statistics
asadm -e "show statistics sets"

# Node health check
asadm -e "show statistics service"
```

#### Backup and Recovery
```yaml
Aerospike Backup Strategy:
Backup Methods:
Snapshot Backups:
  - Frequency: Daily automated backups
  - Retention: 30 days for production, 7 days for staging
  - Storage: AWS S3 with cross-region replication
  - Tool: asbackup utility with compression

Incremental Backups:
  - Frequency: Every 6 hours during business hours
  - Purpose: Minimize data loss window
  - Storage: S3 with lifecycle policies

Backup Commands:
# Full namespace backup
asbackup --host aerodb-aerospike.production.svc.cluster.local \
  --namespace bidder \
  --output-file /backup/bidder-$(date +%Y%m%d).asb \
  --compress gzip

# Restore from backup
asrestore --host aerodb-aerospike.production.svc.cluster.local \
  --input-file /backup/bidder-20250914.asb \
  --namespace bidder
```

### Aerospike Troubleshooting

#### Common Issues and Solutions
```yaml
Troubleshooting Guide:
High Memory Usage:
Symptoms:
  - Memory usage >80% of allocated
  - Eviction warnings in logs
  - Performance degradation

Diagnosis:
  - Check namespace memory usage: asadm -e "show statistics namespace"
  - Identify large sets: asadm -e "show statistics sets"
  - Review TTL configurations

Solutions:
  - Adjust TTL values for temporary data
  - Increase memory allocation if needed
  - Implement data archival for old segments
  - Optimize data structures and reduce payload sizes

Connection Issues:
Symptoms:
  - Connection timeouts from bidder
  - "Unable to connect" errors
  - Intermittent data access failures

Diagnosis:
  - Check cluster health: asadm -e "show statistics service"
  - Verify network connectivity: kubectl get pods
  - Review Kubernetes service status

Solutions:
  - Restart failed nodes: kubectl delete pod <aerospike-pod>
  - Check network policies and firewall rules
  - Verify DNS resolution for service endpoints
  - Review resource limits and scaling policies

Data Inconsistency:
Symptoms:
  - Different data on different nodes
  - Replication factor warnings
  - Data not found errors

Diagnosis:
  - Check replication status: asadm -e "show statistics replication"
  - Verify partition distribution
  - Review conflict resolution logs

Solutions:
  - Force data migration: asadm -e "asinfo -v 'recluster:'"
  - Check and repair partition tables
  - Verify clock synchronization across nodes
  - Review and adjust conflict resolution policies
```

## PostgreSQL Database Management

### PostgreSQL Architecture

#### Database Configuration
```yaml
PostgreSQL Setup:
Production Database:
  - Instance: exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com
  - Engine: PostgreSQL 14+
  - Deployment: AWS RDS with Multi-AZ
  - Storage: GP3 SSD with automated scaling
  - Backup: Daily automated backups with 7-day retention

Staging Database:
  - Instance: Same RDS instance, separate database
  - Database: exchange-stage
  - User: exchange-stage
  - Purpose: Development and testing environment

Connection Details:
Production:
  - Host: exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com
  - Port: 5432
  - Database: exchange
  - User: exchange
  - Password: AWS Secrets Manager (bedrock/eu-west-1/postgres-exchange/exchange)

Staging:
  - Host: Same as production
  - Database: exchange-stage
  - User: exchange-stage
  - Password: Located in stage.toml file in terminal repo
```

#### Schema Management
```yaml
Database Schema Organization:
Core Tables:
  - accounts: User account management
  - campaigns: Campaign configuration
  - line_items: Line item settings and targeting
  - creatives: Creative assets and metadata
  - targeting_rules: Targeting configuration
  - spend_tracking: Budget and pacing data

Audit Tables:
  - audit_log: Change tracking with pgAudit
  - user_sessions: Session management
  - api_access_log: API usage tracking

Migration Management:
  - Tool: Goose migration framework
  - Location: SQL scripts in terminal repository
  - Versioning: Incremental migration files
  - Rollback: Supported for schema changes
```

### PostgreSQL Operations

#### Database Access
```bash
# Production database access
psql -h exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com \
     -p 5432 \
     -U exchange \
     -d exchange

# Staging database access
psql -h exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com \
     -p 5432 \
     -U exchange-stage \
     -d exchange-stage

# Using pgAdmin (GUI alternative)
# Use same connection parameters with pgAdmin client
```

#### Common Database Operations
```sql
-- Check database size and usage
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor active connections
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    query
FROM pg_stat_activity 
WHERE state = 'active';

-- Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Analyze table statistics
ANALYZE;

-- Update table statistics for query optimization
VACUUM ANALYZE;
```

#### Performance Optimization
```yaml
PostgreSQL Performance Tuning:
Query Optimization:
  - Regular ANALYZE to update statistics
  - Index optimization for frequent queries
  - Query plan analysis with EXPLAIN
  - Connection pooling configuration

Configuration Tuning:
  - shared_buffers: 25% of available RAM
  - effective_cache_size: 75% of available RAM
  - work_mem: Optimized for concurrent connections
  - maintenance_work_mem: Increased for maintenance operations

Monitoring Queries:
-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;

-- Monitor table bloat
SELECT 
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup::numeric / (n_live_tup + n_dead_tup) * 100, 2) as bloat_ratio
FROM pg_stat_user_tables 
WHERE n_live_tup > 0
ORDER BY bloat_ratio DESC;
```

### PostgreSQL Backup and Recovery

#### Backup Strategy
```yaml
PostgreSQL Backup Configuration:
Automated Backups:
  - Frequency: Daily between 01:00-02:00 UTC+2
  - Retention: 7 days automatic retention
  - Type: Full database snapshots
  - Storage: AWS RDS automated backup system
  - Access: AWS Console → RDS → exchange-v2 → Maintenance and backups

Manual Backup Commands:
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier exchange-v2 \
  --db-snapshot-identifier exchange-manual-$(date +%Y%m%d-%H%M)

# Export specific tables
pg_dump -h exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com \
        -U exchange \
        -d exchange \
        -t campaigns \
        -t line_items \
        --data-only \
        > campaigns_backup_$(date +%Y%m%d).sql
```

#### Recovery Procedures
```yaml
PostgreSQL Recovery Process:
Point-in-Time Recovery:
Prerequisites:
  - Stop writes to current database if possible
  - Cannot rollback existing database - must create new instance
  - Requires Terraform configuration update

Recovery Steps:
1. Create New Instance from Snapshot:
   # Update terraform configuration
   restore_to_point_in_time {
     use_latest_restorable_time = true
     source_db_instance_identifier = "exchange"
   }

2. Verify Data Integrity:
   # Connect to new instance and verify data
   psql -h new-instance-endpoint -U exchange -d exchange
   
   # Run data validation queries
   SELECT COUNT(*) FROM campaigns;
   SELECT MAX(created_at) FROM line_items;

3. Update DNS Routing:
   # Update Route53 record in terraform
   resource "aws_route53_record" "postgres_exchange" {
     zone_id = data.terraform_remote_state.eks.outputs.zone_id
     name    = "exchange.production.eu-west-1.db.bedrockplatform.bid"
     type    = "CNAME"
     ttl     = "5"
     records = [aws_db_instance.postgres_exchange_v3.address]
   }

4. Application Restart:
   # Restart applications to pick up new database connection
   kubectl rollout restart deployment/terminal
   kubectl rollout restart deployment/syncer
```

## Amazon Redshift Management

### Redshift Architecture and Configuration

#### Cluster Configuration
```yaml
Redshift Data Warehouse:
Production Cluster:
  - Cluster: bedrock (EU-Ireland region)
  - Node Type: dc2.large or ra3.xlplus
  - Nodes: 2-4 nodes (auto-scaling enabled)
  - Storage: Managed storage with automatic backup
  - Access: Query Editor v2 via AWS Console

Data Retention:
  - Raw Logs: Last 30 days (EU region only)
  - Aggregated Data: 12 months retention
  - Historical Reports: 24 months with compression
  - Archive: S3 storage for long-term retention

Authentication:
  - Primary: IAM authentication via AWS SSO
  - Service Accounts: Looker readonly user
  - Access URL: https://d-93674cdf6a.awsapps.com/start#/
```

#### Database Schema
```yaml
Redshift Table Structure:
Raw Event Tables:
bidstream_v2:
  - Purpose: Bid requests to bidder
  - Source: Bidder service logs
  - Retention: 30 days
  - Partitioning: By date for query optimization

impressions:
  - Purpose: Bid requests from BidSwitch
  - Source: Exchange service logs
  - Retention: 30 days
  - Partitioning: By date and campaign

wins:
  - Purpose: Won impression tracking
  - Source: Tracker service
  - Retention: 90 days
  - Partitioning: By date for reporting

clicks:
  - Purpose: Click event tracking
  - Source: Tracker service
  - Retention: 90 days
  - Partitioning: By date and campaign

users:
  - Purpose: User sync tracking
  - Source: User sync service
  - Retention: 30 days
  - Partitioning: By date

Aggregated Tables:
  - daily_campaign_stats: Daily campaign performance
  - hourly_line_item_stats: Hourly line item metrics
  - creative_performance: Creative-level analytics
  - audience_insights: Segment performance data
```

### Redshift Operations

#### Accessing Redshift
```yaml
Redshift Access Methods:
AWS Console Access:
1. Login to AWS using Bedrock IAM Identity Center
   - URL: https://d-93674cdf6a.awsapps.com/start#/
   - Use IAM username (not BP email address)

2. Select EU-Ireland region

3. Navigate to AWS Redshift service

4. Enter Query Editor v2

5. Configure Connection:
   - Right-click "bedrock" namespace
   - Choose "Edit connection"
   - Select "IAM authentication"

Service Account Access:
  - User: looker_readonly
  - Password: AWS Secrets Manager (bedrock/eu-west-1/redshift-password/looker-readonly)
  - Purpose: Looker integration and automated reporting
```

#### Common Redshift Queries
```sql
-- Campaign performance analysis
SELECT 
    order_id,
    line_item_id,
    DATE(timestamp) as date,
    COUNT(*) as impressions,
    SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) as clicks,
    SUM(bid_price) as total_spend
FROM impressions 
WHERE DATE(timestamp) >= '2025-09-01'
    AND order_id = 'ecc1e1ef-6cdc-4638-aa76-c39c7abe231b'
GROUP BY order_id, line_item_id, DATE(timestamp)
ORDER BY date DESC;

-- Debug specific campaign issues
SELECT * 
FROM impressions 
WHERE DATE(timestamp) > '2025-09-10' 
    AND order_id = 'campaign-uuid'
LIMIT 100;

-- Performance troubleshooting
SELECT 
    line_item_id,
    COUNT(*) as bid_requests,
    COUNT(CASE WHEN win_price > 0 THEN 1 END) as wins,
    AVG(bid_price) as avg_bid,
    AVG(win_price) as avg_win_price
FROM bidstream_v2 
WHERE DATE(timestamp) = CURRENT_DATE - 1
GROUP BY line_item_id
ORDER BY bid_requests DESC;

-- User segment analysis
SELECT 
    segment_id,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_events
FROM dmp_events 
WHERE DATE(timestamp) >= CURRENT_DATE - 7
GROUP BY segment_id
ORDER BY unique_users DESC;
```

#### Performance Optimization
```yaml
Redshift Performance Tuning:
Query Optimization:
  - Use EXPLAIN to analyze query plans
  - Implement proper WHERE clause filtering
  - Utilize date partitioning for time-based queries
  - Avoid SELECT * in production queries

Table Design:
  - Choose appropriate distribution keys
  - Implement sort keys for frequently filtered columns
  - Use compression encoding for storage efficiency
  - Regular VACUUM and ANALYZE operations

Monitoring Queries:
-- Check query performance
SELECT 
    query,
    starttime,
    endtime,
    DATEDIFF(seconds, starttime, endtime) as duration,
    aborted
FROM stl_query 
WHERE starttime >= CURRENT_DATE - 1
ORDER BY duration DESC
LIMIT 10;

-- Monitor table statistics
SELECT 
    "table",
    size,
    tbl_rows,
    skew_sortkey1,
    skew_rows
FROM svv_table_info 
ORDER BY size DESC;

-- Check cluster utilization
SELECT 
    service_class,
    num_query_tasks,
    query_working_mem,
    query_cpu_time
FROM stl_wlm_query 
WHERE service_class > 4
ORDER BY query_cpu_time DESC;
```

### Redshift Maintenance

#### Regular Maintenance Tasks
```yaml
Redshift Maintenance Schedule:
Daily Tasks:
  - Monitor query performance and identify slow queries
  - Check cluster utilization and scaling needs
  - Review error logs for failed queries
  - Validate data loading and ETL processes

Weekly Tasks:
  - Run VACUUM on heavily updated tables
  - Update table statistics with ANALYZE
  - Review and optimize query patterns
  - Check storage utilization and growth trends

Monthly Tasks:
  - Review and update table distribution keys
  - Optimize sort keys based on query patterns
  - Archive old data to S3 for cost optimization
  - Review and update user access permissions

Maintenance Commands:
-- Vacuum tables to reclaim space
VACUUM REINDEX table_name;

-- Update statistics for query optimization
ANALYZE table_name;

-- Check table maintenance needs
SELECT 
    "table",
    unsorted,
    vacuum_sort_benefit
FROM svv_table_info 
WHERE vacuum_sort_benefit > 5
ORDER BY vacuum_sort_benefit DESC;
```

## Cross-Database Operations

### Data Synchronization

#### PostgreSQL to Aerospike Sync
```yaml
Sync Process Architecture:
Campaign Configuration Sync:
  - Trigger: PostgreSQL changes via triggers or polling
  - Process: Syncer service reads PostgreSQL and updates Aerospike
  - Frequency: Real-time for critical changes, batch for bulk updates
  - Validation: Data consistency checks and error handling

Sync Monitoring:
-- Check sync status in PostgreSQL
SELECT 
    table_name,
    last_sync_time,
    sync_status,
    error_count
FROM sync_status 
ORDER BY last_sync_time DESC;

-- Verify data consistency
SELECT COUNT(*) FROM campaigns; -- PostgreSQL
SELECT COUNT(*) FROM bidder.orders; -- Aerospike equivalent
```

#### ETL to Redshift
```yaml
ETL Pipeline Management:
Data Loading Process:
  - Source: Application logs, event streams, database exports
  - Processing: AWS Glue jobs for transformation
  - Loading: COPY commands for bulk data loading
  - Scheduling: AWS EventBridge for automated execution

ETL Monitoring:
-- Check recent data loads
SELECT 
    filename,
    curtime as load_time,
    rows_loaded,
    errors
FROM stl_load_commits 
WHERE curtime >= CURRENT_DATE - 1
ORDER BY curtime DESC;

-- Monitor ETL job status
SELECT 
    job_name,
    job_run_state,
    started_on,
    completed_on,
    error_message
FROM glue_job_runs 
WHERE started_on >= CURRENT_DATE - 7
ORDER BY started_on DESC;
```

### Disaster Recovery

#### Cross-Database Recovery Strategy
```yaml
Disaster Recovery Plan:
Recovery Time Objectives (RTO):
  - Aerospike: 15 minutes (cluster restart)
  - PostgreSQL: 30 minutes (RDS failover)
  - Redshift: 60 minutes (cluster restore)
  - Full Platform: 2 hours (complete recovery)

Recovery Point Objectives (RPO):
  - Aerospike: 6 hours (incremental backup)
  - PostgreSQL: 5 minutes (continuous backup)
  - Redshift: 24 hours (daily ETL)
  - Configuration Data: 1 hour (sync frequency)

Recovery Procedures:
1. Assess Impact and Scope:
   - Identify affected database systems
   - Determine data loss window
   - Prioritize recovery order

2. Execute Recovery Plan:
   - PostgreSQL: RDS automated failover or point-in-time recovery
   - Aerospike: Cluster restart or backup restoration
   - Redshift: Cluster restore from snapshot
   - Data Sync: Re-sync between systems

3. Validation and Testing:
   - Verify data integrity across all systems
   - Test application connectivity
   - Validate reporting and analytics
   - Confirm real-time bidding functionality

4. Post-Recovery Actions:
   - Update DNS and load balancer configurations
   - Restart dependent services
   - Monitor system performance
   - Document lessons learned
```

## Monitoring and Alerting

### Database Health Monitoring

#### Key Performance Indicators
```yaml
Database Monitoring Framework:
Aerospike Metrics:
  - Response Time: <1ms for 95th percentile
  - Throughput: QPS per namespace
  - Memory Usage: <80% of allocated memory
  - Disk Usage: <70% of SSD capacity
  - Replication Lag: <100ms between nodes

PostgreSQL Metrics:
  - Connection Count: <80% of max_connections
  - Query Response Time: <100ms for 95th percentile
  - Database Size: Monitor growth trends
  - Lock Contention: Minimal blocking queries
  - Replication Lag: <1 second for read replicas

Redshift Metrics:
  - Query Performance: <30 seconds for analytical queries
  - Cluster Utilization: <80% CPU and memory
  - Storage Usage: Monitor with auto-scaling
  - Concurrent Queries: Within workload management limits
  - ETL Success Rate: >99% for scheduled jobs
```

#### Alerting Configuration
```yaml
Database Alert Thresholds:
Critical Alerts (Immediate Response):
  - Database unavailable or connection failures
  - Memory usage >90% (Aerospike)
  - Disk space >85% (all systems)
  - Query response time >5 seconds
  - Replication failure or significant lag

Warning Alerts (Monitor and Plan):
  - Memory usage >75% (Aerospike)
  - Connection count >70% of maximum
  - Query response time >1 second (PostgreSQL)
  - ETL job failures or delays
  - Unusual query patterns or performance degradation

Alert Channels:
  - Slack: #alerts channel for immediate notifications
  - PagerDuty: Critical alerts for on-call rotation
  - Email: Summary reports and non-critical alerts
  - Grafana: Visual dashboards and trend analysis
```

## Best Practices and Guidelines

### Database Management Best Practices

#### Operational Excellence
```yaml
Best Practices Framework:
Change Management:
  - All schema changes through migration scripts
  - Test changes in staging environment first
  - Backup before major changes
  - Document all changes and rollback procedures

Performance Management:
  - Regular performance monitoring and optimization
  - Proactive capacity planning and scaling
  - Query optimization and index management
  - Regular maintenance tasks scheduling

Security Management:
  - Principle of least privilege for database access
  - Regular security updates and patches
  - Audit logging for sensitive operations
  - Encryption at rest and in transit

Data Management:
  - Regular backup testing and validation
  - Data retention policies and archival
  - Data quality monitoring and validation
  - Cross-system consistency checks
```

#### Troubleshooting Guidelines
```yaml
Troubleshooting Methodology:
1. Problem Identification:
   - Gather symptoms and error messages
   - Check monitoring dashboards and alerts
   - Identify affected systems and users
   - Determine timeline and impact scope

2. Root Cause Analysis:
   - Review recent changes and deployments
   - Analyze performance metrics and logs
   - Check system resources and dependencies
   - Validate data consistency and integrity

3. Resolution and Recovery:
   - Implement immediate fixes for critical issues
   - Plan and execute comprehensive solutions
   - Test fixes in staging environment when possible
   - Document resolution steps and lessons learned

4. Prevention and Improvement:
   - Update monitoring and alerting as needed
   - Improve documentation and procedures
   - Implement additional safeguards
   - Share knowledge with team members
```

## Conclusion

Effective database management is critical for Bedrock Platform's performance, reliability, and scalability. This comprehensive guide provides the operational procedures, best practices, and troubleshooting guidance necessary to maintain optimal database performance across all platform systems.

Regular monitoring, proactive maintenance, and adherence to established procedures ensure that the platform's data infrastructure can support high-performance real-time bidding while maintaining data integrity and availability. Continuous improvement of database operations contributes to overall platform success and client satisfaction.

## Related Topics
- [System Monitoring](../06-operations/system-monitoring.md) - Platform monitoring and alerting procedures
- [Performance Optimization](../06-operations/performance-optimization.md) - System and campaign performance tuning
- [Data Management](../03-technical-features/data-management.md) - Data architecture and processing
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Overall system architecture
- [Campaign Troubleshooting](../06-operations/campaign-troubleshooting.md) - Campaign-specific issue resolution
