#!/bin/bash

# Create deployment package for Lambda
echo "Creating Lambda deployment package..."

# Create temp directory
mkdir -p lambda_package
cd lambda_package

# Install dependencies
pip3 install -r ../requirements.txt -t .

# Copy Polygon API Lambda function
cp ../lambda_function.py lambda_function.py

# Create zip file
zip -r ../lambda_deployment.zip .

# Cleanup
cd ..
rm -rf lambda_package

echo "Lambda deployment package created: lambda_deployment.zip"