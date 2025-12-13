# AWS Glue and Athena Setup for Options Data Analysis

## Overview
This document outlines the steps to set up AWS Glue and Athena to analyze options data stored in S3 and find the most profitable trading opportunities.

## Prerequisites
- S3 bucket: `faang-options` with data in `magnificent-seven-options/` folder
- JSON data format: Array of 7 options objects per file

## Step 1: Create Glue Database

1. Go to **AWS Glue Console**
2. Click **Databases** → **Add database**
3. Database name: `options_analytics`
4. Click **Create**

## Step 2: Create Glue Crawler

1. In Glue Console → **Crawlers** → **Create crawler**
2. Crawler name: `options-crawler`
3. **Data sources** → **Add a data source**
   - **S3 path**: `s3://faang-options/magnificent-seven-options/`
   - Click **Add an S3 data source**
4. **IAM role** → **Create new role** → Name: `GlueServiceRole`
5. **Target database**: Select `options_analytics`
6. **Crawler schedule**: Schedule → `cron(30 19 * * ? *)` (runs 30 minutes after Lambda data fetch)
7. Click **Create crawler**

## Step 3: Fix IAM Permissions

1. Go to **IAM Console** → **Roles**
2. Find role `GlueServiceRole`
3. Click **Add permissions** → **Attach policies**
4. Search and attach: `AmazonS3FullAccess`
5. Click **Add permissions**

## Step 4: Scheduled Crawler Execution

**Note**: Crawler now runs automatically on schedule (30 minutes after Lambda execution)

**Manual run (if needed)**:
1. Go back to **Glue Console** → **Crawlers**
2. Select `options-crawler` → **Run crawler**
3. Wait for completion (should show "READY" status)

**Schedule Details**:
- Lambda runs at 7:00 PM UTC (`cron(0 19 * * ? *)`)
- Crawler runs at 7:30 PM UTC (`cron(30 19 * * ? *)`)
- 30-minute delay ensures Lambda completes data upload to S3

## Step 5: Setup Athena

1. Go to **Amazon Athena Console**
2. **Settings** → **Manage**
3. **Query result location**: `s3://faang-options/athena-results/`
4. Click **Save**

## Step 6: Create Proper Table Structure

Since the crawler creates incorrect structure for JSON arrays, manually create the table:

```sql
DROP TABLE IF EXISTS magnificent_seven_options;

CREATE EXTERNAL TABLE magnificent_seven_options (
  records array<struct<
    underlying_ticker: string,
    current_price: double,
    strike: double,
    expiration: string,
    contract_ticker: string,
    timestamp: string,
    open: double,
    high: double,
    low: double,
    close: double,
    volume: int,
    vwap: double
  >>
)
STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://faang-options/magnificent-seven-options/'
TBLPROPERTIES ('has_encrypted_data'='false');
```

## Step 7: Query Most recent Options from each of the Magnificent Seven Tickers

```sql
SELECT 
          option.underlying_ticker,
          option.current_price,
          option.strike,
          option.close as option_price,
          option.volume,
          option.contract_ticker,
          option.open,
          option.high,
          option.low,
          option.vwap,
          option.timestamp
        FROM magnificent_seven_options
        CROSS JOIN UNNEST(records) AS t(option)
        ORDER BY option.timestamp DESC
        LIMIT 7
```

## Troubleshooting

- **No tables appear**: Check IAM permissions and re-run crawler
- **JSON parsing errors**: Verify S3 data format matches expected JSON array structure
- **Empty results**: Ensure S3 files contain data and table location is correct

## Next Steps

Ready to create REST API Lambda function to serve the top 3 options data via API Gateway.