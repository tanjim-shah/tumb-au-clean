#!/usr/bin/env python3
# oauth2_auth_helper.py - Run this locally to get authorization code

import os
import json
import base64
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            # Parse the authorization code from the callback URL
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                auth_code = query_params['code'][0]
                
                # Store the authorization code
                self.server.auth_code = auth_code
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                success_html = """
                <html>
                <body>
                    <h2>Authorization Successful!</h2>
                    <p>You can close this window and return to your terminal.</p>
                    <p>The authorization code has been captured.</p>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
                
                # Signal to stop the server
                threading.Thread(target=self.server.shutdown).start()
                
            elif 'error' in query_params:
                error = query_params['error'][0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                error_html = f"""
                <html>
                <body>
                    <h2>Authorization Failed</h2>
                    <p>Error: {error}</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress log messages
        pass

def get_authorization_code():
    """Get authorization code using local server"""
    client_id = input("Enter your Tumblr Client ID: ").strip()
    if not client_id:
        print("Client ID is required!")
        return None, None
    
    redirect_uri = "http://localhost:8080/callback"
    scope = "write"
    
    # Build authorization URL
    auth_url = (
        f"https://www.tumblr.com/oauth2/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"redirect_uri={redirect_uri}"
    )
    
    print(f"\nOpening browser for authorization...")
    print(f"If browser doesn't open, visit: {auth_url}")
    
    # Start local server to capture callback
    server = HTTPServer(('localhost', 8080), AuthHandler)
    server.auth_code = None
    
    # Open browser
    webbrowser.open(auth_url)
    
    print("\nWaiting for authorization...")
    print("Please authorize the application in your browser.")
    
    # Handle requests until we get the callback
    server.handle_request()
    
    auth_code = getattr(server, 'auth_code', None)
    server.server_close()
    
    return client_id, auth_code

def exchange_code_for_token(client_id, client_secret, auth_code):
    """Exchange authorization code for access token"""
    token_url = "https://api.tumblr.com/v2/oauth2/token"
    redirect_uri = "http://localhost:8080/callback"
    
    # Create Basic Auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error exchanging code for token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("Tumblr OAuth 2.0 Authorization Helper")
    print("=" * 40)
    
    # Get authorization code
    client_id, auth_code = get_authorization_code()
    
    if not auth_code:
        print("Failed to get authorization code.")
        return
    
    print(f"\n✅ Authorization code received: {auth_code}")
    
    # Get client secret
    client_secret = input("\nEnter your Tumblr Client Secret: ").strip()
    if not client_secret:
        print("Client Secret is required!")
        return
    
    # Exchange code for token
    print("\nExchanging authorization code for access token...")
    token_data = exchange_code_for_token(client_id, client_secret, auth_code)
    
    if token_data:
        print("\n✅ Success! Token data received:")
        print(f"Access Token: {token_data.get('access_token', 'N/A')}")
        print(f"Refresh Token: {token_data.get('refresh_token', 'N/A')}")
        print(f"Expires In: {token_data.get('expires_in', 'N/A')} seconds")
        
        # Save to file
        os.makedirs('data', exist_ok=True)
        with open('data/tumblr_token.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"\n💾 Token data saved to data/tumblr_token.json")
        
        print("\n📋 GitHub Secrets to set:")
        print(f"TUMBLR_CLIENT_ID={client_id}")
        print(f"TUMBLR_CLIENT_SECRET={client_secret}")
        print("TUMBLR_BLOG_NAME=your-blog-name")
        
        print("\n🎉 You're all set! The token will be automatically refreshed when needed.")
        
    else:
        print("❌ Failed to exchange authorization code for token.")

if __name__ == "__main__":
    main()