import json
import boto3
import os
import requests
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

MAGNIFICENT_SEVEN_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']

def lambda_handler(event, context):
    try:
        logger.info("Lambda function invoked")
        all_options = []
        
        # Get Polygon API key from environment variable
        api_key = os.environ.get('POLYGON_API_KEY')
        if not api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        
        for ticker in MAGNIFICENT_SEVEN_TICKERS:
            logger.info("Fetching options data for ticker: %s", ticker)
            options_data = fetch_options_data(ticker, api_key)
            if options_data:
                logger.info("Options data fetched for ticker %s: %d options", ticker, len(options_data))
                all_options.extend(options_data)
            else:
                logger.warning("No options data found for ticker: %s", ticker)
            time.sleep(2.0)  # Rate limiting for Polygon API
        
        if all_options:
            store_to_s3(all_options)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {len(all_options)} options',
                'total_options': len(all_options),
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def fetch_options_data(ticker, api_key):
    try:
        # Get current stock price
        current_price = get_current_price(ticker, api_key)
        if not current_price:
            logger.error("Could not get current price for %s", ticker)
            return []
        
        # Fetch options contracts without specific expiration date
        options_url = f"https://api.polygon.io/v3/reference/options/contracts"
        params = {
            'underlying_ticker': ticker,
            'contract_type': 'call',
            'limit': 1000,
            'apikey': api_key
        }
        
        response = requests.get(options_url, params=params, timeout=30)
        logger.info("Options contracts API response status for %s: %d", ticker, response.status_code)
        
        if response.status_code != 200:
            logger.error("Failed to fetch options contracts for %s: %s", ticker, response.text)
            return []
        
        contracts_data = response.json()
        
        if 'results' not in contracts_data or not contracts_data['results']:
            logger.warning("No options contracts found for %s", ticker)
            return []
        
        # Find 1 call strike just above current price
        contracts = sorted(contracts_data['results'], key=lambda x: x['strike_price'])
        
        # Group by expiration date and take the nearest one with options above current price
        expiration_groups = {}
        for contract in contracts:
            exp_date = contract['expiration_date']
            if exp_date not in expiration_groups:
                expiration_groups[exp_date] = []
            expiration_groups[exp_date].append(contract)
        
        # Sort expiration dates and try the nearest one
        sorted_expirations = sorted(expiration_groups.keys())
        
        for exp_date in sorted_expirations:
            contracts_for_exp = sorted(expiration_groups[exp_date], key=lambda x: x['strike_price'])
            
            for contract in contracts_for_exp:
                if contract['strike_price'] > current_price:
                    # Get option pricing data
                    option_quotes = get_option_quotes(contract['ticker'], api_key)
                    
                    option_data = {
                        'underlying_ticker': ticker,
                        'current_price': current_price,
                        'strike': contract['strike_price'],
                        'expiration': contract['expiration_date'],
                        'contract_ticker': contract['ticker'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Add pricing data if available
                    option_data.update(option_quotes)
                    
                    logger.info("Added call option for %s: strike $%.2f, exp %s", ticker, contract['strike_price'], contract['expiration_date'])
                    
                    # Add longer delay to avoid rate limits
                    time.sleep(1.0)
                    
                    return [option_data]  # Return immediately after finding first option
            
            # If we found an option in this expiration, we're done
            break
        
        return []
        
    except Exception as e:
        logger.error("Error fetching options for %s: %s", ticker, str(e))
        return []

def get_current_price(ticker, api_key):
    try:
        # Get previous close price
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
        params = {'apikey': api_key}
        
        response = requests.get(url, params=params, timeout=10)
        logger.info("Price API response for %s: %d", ticker, response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("Price API data for %s: %s", ticker, json.dumps(data))
            if 'results' in data and data['results']:
                price = data['results'][0]['c']  # Close price
                logger.info("Current price for %s: $%.2f", ticker, price)
                return price
        
        # If prev endpoint fails, try current day
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{datetime.now().strftime('%Y-%m-%d')}/{datetime.now().strftime('%Y-%m-%d')}"
        response = requests.get(url, params=params, timeout=10)
        logger.info("Fallback price API response for %s: %d", ticker, response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                price = data['results'][0]['c']
                logger.info("Fallback current price for %s: $%.2f", ticker, price)
                return price
        
        logger.error("Failed to get price for %s, response: %s", ticker, response.text)
        return None
        
    except Exception as e:
        logger.error("Error getting price for %s: %s", ticker, str(e))
        return None

def get_option_quotes(option_ticker, api_key):
    try:
        # Use basic aggregates endpoint which should work with basic API tier
        url = f"https://api.polygon.io/v2/aggs/ticker/{option_ticker}/prev"
        params = {'apikey': api_key}
        
        response = requests.get(url, params=params, timeout=15)
        logger.info("Option quotes API response for %s: %d", option_ticker, response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'results' in data and data['results']:
                result = data['results'][0]
                return {
                    'open': result.get('o', 0),
                    'high': result.get('h', 0), 
                    'low': result.get('l', 0),
                    'close': result.get('c', 0),
                    'volume': result.get('v', 0),
                    'vwap': result.get('vw', 0)
                }
        
        # If that fails, just return basic calculated values
        return {
            'estimated_value': max(0, 1.0),
            'status': 'no_pricing_data'
        }
    except Exception as e:
        logger.error("Error getting option quotes for %s: %s", option_ticker, str(e))
        return {'status': 'error'}

def store_to_s3(results):
    try:
        bucket = 'faang-options'
        key = f"magnificent-seven-options/{datetime.now().strftime('%Y-%m-%d-%H-%M')}.json"
        logger.info("Storing results to S3. Bucket: %s, Key: %s", bucket, key)
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(results, default=str),
            ContentType='application/json'
        )
        logger.info("Successfully stored %d options to S3.", len(results))
    except Exception as e:
        logger.error("Error storing to S3: %s", str(e))
