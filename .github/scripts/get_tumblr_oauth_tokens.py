#!/usr/bin/env python3

import os
import requests
import urllib.parse
import hmac
import hashlib
import base64
import secrets
import time
from urllib.parse import parse_qs

class TumblrOAuthHelper:
    def __init__(self, consumer_key, consumer_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.request_token_url = "https://www.tumblr.com/oauth/request_token"
        self.authorize_url = "https://www.tumblr.com/oauth/authorize"
        self.access_token_url = "https://www.tumblr.com/oauth/access_token"
        
    def create_oauth_signature(self, method, url, params, token_secret=""):
        """Create OAuth signature"""
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = "&".join([f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params])
        
        # Create signature base string
        signature_base = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
        
        # Create signing key
        signing_key = f"{urllib.parse.quote(self.consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
        
        # Generate signature
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), signature_base.encode(), hashlib.sha1).digest()
        ).decode()
        
        return signature
    
    def get_request_token(self):
        """Step 1: Get request token"""
        oauth_params = {
            'oauth_callback': 'oob',  # Out of band
            'oauth_consumer_key': self.consumer_key,
            'oauth_nonce': secrets.token_hex(16),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0'
        }
        
        # Create signature
        oauth_params['oauth_signature'] = self.create_oauth_signature(
            'POST', self.request_token_url, oauth_params
        )
        
        # Create authorization header
        auth_header = 'OAuth ' + ', '.join([f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in oauth_params.items()])
        
        headers = {'Authorization': auth_header}
        
        response = requests.post(self.request_token_url, headers=headers)
        
        if response.status_code == 200:
            token_data = parse_qs(response.text)
            return {
                'oauth_token': token_data['oauth_token'][0],
                'oauth_token_secret': token_data['oauth_token_secret'][0]
            }
        else:
            raise Exception(f"Failed to get request token: {response.status_code} - {response.text}")
    
    def get_access_token(self, request_token, request_token_secret, verifier):
        """Step 3: Exchange request token for access token"""
        oauth_params = {
            'oauth_consumer_key': self.consumer_key,
            'oauth_nonce': secrets.token_hex(16),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': request_token,
            'oauth_verifier': verifier,
            'oauth_version': '1.0'
        }
        
        # Create signature
        oauth_params['oauth_signature'] = self.create_oauth_signature(
            'POST', self.access_token_url, oauth_params, request_token_secret
        )
        
        # Create authorization header
        auth_header = 'OAuth ' + ', '.join([f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in oauth_params.items()])
        
        headers = {'Authorization': auth_header}
        
        response = requests.post(self.access_token_url, headers=headers)
        
        if response.status_code == 200:
            token_data = parse_qs(response.text)
            return {
                'oauth_token': token_data['oauth_token'][0],
                'oauth_token_secret': token_data['oauth_token_secret'][0]
            }
        else:
            raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")

def main():
    print("=== Tumblr OAuth Token Generator ===\n")
    
    # Get consumer credentials
    consumer_key = input("Enter your Tumblr Consumer Key (API Key): ").strip()
    consumer_secret = input("Enter your Tumblr Consumer Secret: ").strip()
    
    if not consumer_key or not consumer_secret:
        print("Error: Consumer key and secret are required!")
        return
    
    oauth_helper = TumblrOAuthHelper(consumer_key, consumer_secret)
    
    try:
        # Step 1: Get request token
        print("\n🔄 Step 1: Getting request token...")
        request_tokens = oauth_helper.get_request_token()
        print("✅ Request token obtained successfully!")
        
        # Step 2: Get user authorization
        print("\n🔄 Step 2: User authorization required")
        print(f"Please visit this URL to authorize the application:")
        print(f"{oauth_helper.authorize_url}?oauth_token={request_tokens['oauth_token']}")
        print("\nAfter authorizing, you'll see a PIN/verifier code.")
        
        verifier = input("\nEnter the PIN/verifier code: ").strip()
        
        if not verifier:
            print("Error: Verifier code is required!")
            return
        
        # Step 3: Get access token
        print("\n🔄 Step 3: Getting access token...")
        access_tokens = oauth_helper.get_access_token(
            request_tokens['oauth_token'],
            request_tokens['oauth_token_secret'], 
            verifier
        )
        print("✅ Access token obtained successfully!")
        
        # Display results
        print("\n" + "="*60)
        print("🎉 SUCCESS! Your Tumblr OAuth tokens:")
        print("="*60)
        print(f"TUMBLR_CONSUMER_KEY: {consumer_key}")
        print(f"TUMBLR_CONSUMER_SECRET: {consumer_secret}")
        print(f"TUMBLR_OAUTH_TOKEN: {access_tokens['oauth_token']}")
        print(f"TUMBLR_OAUTH_TOKEN_SECRET: {access_tokens['oauth_token_secret']}")
        print("="*60)
        
        print("\n📝 Next steps:")
        print("1. Copy these values to your GitHub repository secrets")
        print("2. Also add your TUMBLR_BLOG_NAME (e.g., 'yourblogname' from yourblogname.tumblr.com)")
        print("3. Test the setup with your automation scripts")
        
        # Save to file option
        save_file = input("\nSave tokens to file? (y/n): ").strip().lower()
        if save_file == 'y':
            filename = "tumblr_tokens.txt"
            with open(filename, 'w') as f:
                f.write("# Tumblr OAuth Tokens\n")
                f.write("# Add these to your GitHub repository secrets\n\n")
                f.write(f"TUMBLR_CONSUMER_KEY={consumer_key}\n")
                f.write(f"TUMBLR_CONSUMER_SECRET={consumer_secret}\n")
                f.write(f"TUMBLR_OAUTH_TOKEN={access_tokens['oauth_token']}\n")
                f.write(f"TUMBLR_OAUTH_TOKEN_SECRET={access_tokens['oauth_token_secret']}\n")
                f.write(f"TUMBLR_BLOG_NAME=your-blog-name-here\n")
            print(f"✅ Tokens saved to {filename}")
            print("⚠️  IMPORTANT: Keep this file secure and don't commit it to version control!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Verify your consumer key and secret are correct")
        print("2. Make sure you completed the authorization step")
        print("3. Check that the PIN/verifier code was entered correctly")
        print("4. Ensure your Tumblr app is properly configured")

if __name__ == "__main__":
    main()