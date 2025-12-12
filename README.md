# Polygon API Lambda Function

This Lambda function fetches real options data using Polygon API for the Magnificent Seven stocks.

## Key Changes from Previous Version

1. **Real Options Data**: Uses Polygon API to fetch actual options contracts and pricing
2. **No Ranking Logic**: Simply fetches 21 options (3 per ticker) and stores them in S3
3. **Better Rate Limiting**: Includes proper delays for Polygon API limits

## Setup Requirements

1. **Polygon API Key**: Sign up at https://polygon.io and get a free API key
2. **Environment Variable**: Set `POLYGON_API_KEY` in Lambda environment variables
3. **S3 Bucket**: Ensure `magnificent-seven-options` bucket exists
4. **IAM Permissions**: Lambda needs S3 PutObject permissions

## Deployment

1. Upload `lambda_deployment_polygon.zip` to AWS Lambda
2. Set environment variable `POLYGON_API_KEY` with your API key
3. Configure timeout to 5 minutes (Polygon API can be slow)
4. Set memory to 256MB

## API Endpoints Used

- **Stock Prices**: `/v2/aggs/ticker/{ticker}/prev` - Gets previous close price
- **Options Contracts**: `/v3/reference/options/contracts` - Lists available options
- **Option Quotes**: `/v2/last/nbbo/{option_ticker}` - Gets bid/ask prices
- **Option Trades**: `/v2/last/trade/{option_ticker}` - Gets last trade data

## Output Format

Each option includes:
- `underlying_ticker`: Stock symbol (AAPL, MSFT, etc.)
- `current_price`: Current stock price
- `strike`: Option strike price
- `expiration`: Option expiration date
- `contract_ticker`: Full option contract symbol
- `bid/ask`: Current bid/ask prices
- `last_price`: Last trade price
- `volume`: Trading volume

## Rate Limits

- Free tier: 5 requests per minute
- Function includes 0.5 second delays between requests
- Total execution time: ~4-5 minutes for all 7 stocks