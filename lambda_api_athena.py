import json
import boto3
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

athena = boto3.client('athena')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    try:
        logger.info("API Lambda function invoked - using Athena")
        # Athena configuration
        database = 'options_analytics'
        table = 'magnificent_seven_options'
        output_location = 's3://faang-options/athena-results/'
        
        # Query to get records from most recent file (assumes files are processed in chronological order)
        query = """
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
        """
        
        # Execute Athena query
        response = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': output_location}
        )
        
        query_execution_id = response['QueryExecutionId']
        logger.info("Started Athena query: %s", query_execution_id)
        
        # Wait for query to complete
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            result = athena.get_query_execution(QueryExecutionId=query_execution_id)
            status = result['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'CANCELLED']:
                error_msg = result['QueryExecution']['Status'].get('StateChangeReason', 'Query failed')
                logger.error("Athena query failed: %s", error_msg)
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'Query failed: {error_msg}'})
                }
            
            time.sleep(2)
            attempt += 1
        
        if attempt >= max_attempts:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Query timeout'})
            }
        
        # Get query results
        results = athena.get_query_results(QueryExecutionId=query_execution_id)
        
        # Parse results
        rows = results['ResultSet']['Rows']
        if len(rows) <= 1:  # Only header row
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No options data found'})
            }
        
        # Convert to JSON format and calculate profit scores
        columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
        all_options = []
        
        logger.info(f"Found {len(rows)-1} rows to process")
        
        for row in rows[1:]:  # Skip header row
            raw_data = row['Data'][0].get('VarCharValue', '')
            
            # Parse the JSON array from underlying_ticker field
            try:
                options_data = json.loads(raw_data)
                for opt in options_data:
                    option = {
                        'underlying_ticker': opt.get('underlying_ticker'),
                        'current_price': float(opt.get('current_price', 0)),
                        'strike': float(opt.get('strike', 0)),
                        'option_price': float(opt.get('close', 0)),
                        'volume': int(opt.get('volume', 0)),
                        'contract_ticker': opt.get('contract_ticker'),
                        'open': float(opt.get('open', 0)),
                        'high': float(opt.get('high', 0)),
                        'low': float(opt.get('low', 0)),
                        'vwap': float(opt.get('vwap', 0))
                    }
                    
                    # Calculate profit score: (strike + low) - current_price
                    option['profit_score'] = (option['strike'] + option['low']) - option['current_price']
                    all_options.append(option)
            except:
                continue
        
        logger.info(f"Processed {len(all_options)} valid options")
        
        # Remove duplicates based on contract_ticker
        unique_options = {}
        for option in all_options:
            ticker = option['contract_ticker']
            if ticker not in unique_options:
                unique_options[ticker] = option
        
        # Convert back to list and sort by profit score (lowest = best)
        unique_list = list(unique_options.values())
        unique_list.sort(key=lambda x: x['profit_score'])
        top_3_options = unique_list[:3]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': True,
                'data': {
                    'top_3_options': top_3_options,
                    'query_execution_id': query_execution_id,
                    'data_source': 'AWS Athena'
                },
                'message': 'Top 3 most profitable options from Athena analysis'
            })
        }
        
    except Exception as e:
        logger.error("Error processing request: %s", str(e), exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }