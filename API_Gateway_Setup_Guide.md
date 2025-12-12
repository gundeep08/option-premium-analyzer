# AWS API Gateway Setup Guide

This guide documents the steps to create an API Gateway that connects to a Lambda function for the Options Trading API.

## Prerequisites

- AWS Lambda function (`lambda_api_athena`) already created and deployed
- Lambda function has proper IAM permissions for S3 and Athena
- Lambda function returns proper HTTP response format

## Step 1: Create API Gateway

1. **Navigate to API Gateway Console**
   - Go to AWS Console → API Gateway
   - Click **Create API**

2. **Choose API Type**
   - Select **REST API** → **Build**
   - API name: `options-athena-api`
   - Description: `API for retrieving top 3 profitable options`
   - Endpoint Type: **Regional**
   - Click **Create API**

## Step 2: Create Resource

1. **Create Resource**
   - Click **Actions** → **Create Resource**
   - Resource Name: `options`
   - Resource Path: `/options`
   - Enable API Gateway CORS: ✅ (Check this box)
   - Click **Create Resource**

## Step 3: Create GET Method

1. **Add GET Method**
   - Select `/options` resource
   - Click **Actions** → **Create Method**
   - Choose **GET** from dropdown → Click checkmark ✓

2. **Configure Integration**
   - Integration type: **Lambda Function**
   - Use Lambda Proxy integration: ✅ **IMPORTANT: Check this box**
   - Lambda Region: Select your region (e.g., us-east-2)
   - Lambda Function: `lambda_api_athena`
   - Click **Save** → **OK** (to grant permissions)

## Step 4: Configure Method Settings

1. **Method Request Settings**
   - Authorization: **None**
   - API Key Required: **false**
   - Request Validator: **None**

2. **Integration Request**
   - Verify "Use Lambda Proxy integration" is checked ✅
   - This is crucial for proper request/response handling

## Step 5: Enable CORS (if not done in Step 2)

1. **Enable CORS**
   - Select **GET** method under `/options`
   - Click **Actions** → **Enable CORS**
   - Access-Control-Allow-Origin: `*`
   - Access-Control-Allow-Headers: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
   - Access-Control-Allow-Methods: `GET,OPTIONS`
   - Click **Enable CORS and replace existing CORS headers**

## Step 6: Deploy API

1. **Deploy to Stage**
   - Click **Actions** → **Deploy API**
   - Deployment stage: **New Stage**
   - Stage name: `prod`
   - Stage description: `Production stage`
   - Deployment description: `Initial deployment`
   - Click **Deploy**

2. **Get API URL**
   - Copy the **Invoke URL** from the stage editor
   - Format: `https://{api-id}.execute-api.{region}.amazonaws.com/prod`

## Step 7: Test the API

### Using cURL
```bash
curl --location 'https://1b6gkn1x2g.execute-api.us-east-2.amazonaws.com/prod/options'
```

### Using Postman
- **Method**: GET
- **URL**: `https://1b6gkn1x2g.execute-api.us-east-2.amazonaws.com/prod/options`
- **Headers**: None required
- **Body**: None (GET request)
- **Authorization**: None

### Expected Response
```json
{
  "success": true,
  "data": {
    "top_3_options": [
      {
        "underlying_ticker": "AAPL",
        "current_price": 278.85,
        "strike": 280.0,
        "option_price": 2.29,
        "volume": 22804,
        "contract_ticker": "O:AAPL251205C00280000",
        "profit_score": 2.45,
        "open": 1.84,
        "high": 2.44,
        "low": 1.3,
        "vwap": 1.7042
      }
    ],
    "query_execution_id": "abc123...",
    "data_source": "AWS Athena"
  },
  "message": "Top 3 most profitable options from Athena analysis"
}
```

## Troubleshooting

### Common Issues

1. **403 Forbidden - "Missing Authentication Token"**
   - **Cause**: Lambda Proxy integration not enabled
   - **Fix**: Enable "Use Lambda Proxy integration" in Integration Request

2. **403 Forbidden - Wrong URL**
   - **Cause**: Missing resource path in URL
   - **Fix**: Use full URL with `/options` path

3. **500 Internal Server Error**
   - **Cause**: Lambda function errors or permissions
   - **Fix**: Check CloudWatch logs for Lambda function

4. **CORS Errors (Browser)**
   - **Cause**: CORS not properly configured
   - **Fix**: Re-enable CORS and redeploy API

### Postman Issues

- Remove all custom headers for GET requests
- Don't add `Content-Type` header for GET
- Ensure URL is exactly correct with no extra spaces
- Use new request if previous attempts cached errors

## Security Considerations

- **Current Setup**: Open API (no authentication)
- **Production Recommendations**:
  - Add API Key authentication
  - Implement rate limiting
  - Use AWS WAF for additional protection
  - Consider VPC endpoints for internal access

## API Gateway Features Used

- **REST API**: Traditional REST API with resources and methods
- **Lambda Proxy Integration**: Passes entire request to Lambda
- **CORS**: Enables browser-based requests
- **Regional Endpoint**: Lower latency for regional access
- **Stage Management**: Separate environments (dev, prod)

## Next Steps

1. **Add Authentication**: Implement API keys or Cognito
2. **Rate Limiting**: Configure usage plans and throttling
3. **Monitoring**: Set up CloudWatch alarms
4. **Custom Domain**: Add custom domain name
5. **Documentation**: Generate API documentation