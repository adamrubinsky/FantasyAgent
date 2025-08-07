#!/usr/bin/env python3
"""
Create IAM Service Role for Bedrock AgentCore Agents
"""

import boto3
import json
from botocore.exceptions import ClientError

def create_agentcore_service_role():
    """Create the service role that AgentCore agents need"""
    
    iam_client = boto3.client('iam')
    
    role_name = "fantasy-draft-agentcore-role"
    
    # Trust policy - allows Bedrock to assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permission policy for AgentCore agents
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow", 
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/*"
            }
        ]
    }
    
    try:
        print(f"🔐 Creating AgentCore service role: {role_name}")
        
        # Create the role (without tags due to permission issues)
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Service role for Bedrock AgentCore fantasy draft agents"
        )
        
        role_arn = response['Role']['Arn']
        print(f"✅ Role created: {role_arn}")
        
        # Attach the permissions policy
        policy_name = "fantasy-draft-agentcore-permissions"
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy)
        )
        
        print(f"✅ Permissions policy attached: {policy_name}")
        
        # Wait a moment for role to propagate
        import time
        print("⏳ Waiting for role to propagate...")
        time.sleep(10)
        
        print(f"🎉 AgentCore service role ready!")
        print(f"📋 Role ARN: {role_arn}")
        
        return role_arn
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'EntityAlreadyExists':
            print(f"✅ Role {role_name} already exists")
            
            # Get the existing role ARN
            response = iam_client.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
            print(f"📋 Existing Role ARN: {role_arn}")
            
            return role_arn
        else:
            print(f"❌ Error creating role: {e}")
            return None

def main():
    print("🔐 CREATING AGENTCORE SERVICE ROLE")
    print("=" * 40)
    
    role_arn = create_agentcore_service_role()
    
    if role_arn:
        print(f"\n✅ SUCCESS!")
        print(f"🔑 Service Role ARN: {role_arn}")
        print(f"📋 Next: Use this role ARN when creating AgentCore agents")
        
        # Save role ARN for deployment script
        role_info = {
            'role_arn': role_arn,
            'role_name': 'fantasy-draft-agentcore-role'
        }
        
        with open('agentcore_role.json', 'w') as f:
            json.dump(role_info, f, indent=2)
        
        print(f"💾 Role info saved to: agentcore_role.json")
    else:
        print(f"\n❌ Failed to create service role")

if __name__ == "__main__":
    main()