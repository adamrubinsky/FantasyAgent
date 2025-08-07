# Using Root User to Set Up AgentCore Permissions

## 🔐 Method 1: AWS Console (Recommended)

### Step 1: Log in as Root User
1. Go to: https://aws.amazon.com/console/
2. Click **"Root user"** 
3. Enter your **root email address** (not the IAM user)
4. Enter your **root password**

### Step 2: Add Permissions via Console
1. Once logged in as root, go to **IAM Console**
2. Click **"Users"** in left sidebar
3. Click on **"rubinsky-website-deploy"** (your current user)
4. Click **"Permissions"** tab
5. Click **"Add permissions"** → **"Attach policies directly"**
6. Search for and attach these AWS managed policies:
   - ✅ **AmazonBedrockFullAccess**
   - ✅ **CloudWatchFullAccess** 
   - ✅ **AmazonDynamoDBFullAccess**
   - ✅ **AWSLambda_FullAccess**
7. Click **"Next"** → **"Add permissions"**

## 🖥️ Method 2: AWS CLI as Root

### Step 1: Configure Root User Credentials
```bash
# Create new AWS profile for root user
aws configure --profile root

# Enter your ROOT USER credentials:
# AWS Access Key ID: [Your root access key]
# AWS Secret Access Key: [Your root secret key] 
# Default region: us-east-1
# Default output format: json
```

**Note**: If you don't have root access keys, create them:
1. Log in as root user to AWS Console
2. Go to **"My Security Credentials"** 
3. Click **"Access keys"** → **"Create access key"**

### Step 2: Add Permissions via CLI
```bash
# Use root profile to add permissions
export AWS_PROFILE=root

# Attach managed policies to your user
aws iam attach-user-policy \
    --user-name rubinsky-website-deploy \
    --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-user-policy \
    --user-name rubinsky-website-deploy \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess

aws iam attach-user-policy \
    --user-name rubinsky-website-deploy \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-user-policy \
    --user-name rubinsky-website-deploy \
    --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

echo "✅ Permissions added to rubinsky-website-deploy"
```

### Step 3: Switch Back to Your User
```bash
# Switch back to your regular user
export AWS_PROFILE=default
# or 
unset AWS_PROFILE
```

## 🚀 Method 3: Quick Script (Run as Root)

Save this as `root_add_permissions.sh`:

```bash
#!/bin/bash
# Run this with root credentials configured

echo "🔐 Adding AgentCore permissions as root user"

USER_NAME="rubinsky-website-deploy"

# Attach AWS managed policies
aws iam attach-user-policy --user-name $USER_NAME --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-user-policy --user-name $USER_NAME --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess  
aws iam attach-user-policy --user-name $USER_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-user-policy --user-name $USER_NAME --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

echo "✅ All permissions added to $USER_NAME"
echo "🎉 AgentCore system ready for deployment!"
```

Then run:
```bash
# Configure root profile first
aws configure --profile root

# Run script
AWS_PROFILE=root ./root_add_permissions.sh
```

## ✅ Verify It Worked

After adding permissions, test with:
```bash
# Switch back to your regular user
unset AWS_PROFILE

# Run verification
python3 verify_agentcore.py
```

## 🎯 Recommended Approach

**I recommend Method 1 (AWS Console)** because:
- ✅ Most secure (no CLI credentials)
- ✅ Visual confirmation 
- ✅ Easy to verify

Choose the method you're most comfortable with!