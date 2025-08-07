#!/bin/bash

# Install AWS SAM CLI on macOS
echo "📦 Installing AWS SAM CLI..."

if command -v brew &> /dev/null; then
    echo "Using Homebrew to install SAM CLI..."
    brew tap aws/tap
    brew install aws-sam-cli
    echo "✅ SAM CLI installed via Homebrew"
else
    echo "Installing SAM CLI directly..."
    # Download the installer
    curl -L "https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-macos-x86_64.pkg" -o "/tmp/aws-sam-cli-macos.pkg"
    
    # Install the package
    sudo installer -pkg "/tmp/aws-sam-cli-macos.pkg" -target /
    
    echo "✅ SAM CLI installed"
    rm "/tmp/aws-sam-cli-macos.pkg"
fi

# Verify installation
sam --version
echo "🎉 SAM CLI ready!"