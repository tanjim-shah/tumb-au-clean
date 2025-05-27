#!/usr/bin/env python3
# .github/scripts/post_to_tumblr_oauth2.py

import os
import csv
import json
import requests
import time
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# Configuration
PENDING_POSTS_FILE = "data/pending_posts.csv"
POSTED_LOGS_FILE = "data/posted_logs.csv"
TOKEN_FILE = "data/tumblr_token.json"

class TumblrOAuth2Poster:
    def __init__(self):
        self.client_id = os.environ.get("TUMBLR_CLIENT_ID")
        self.client_secret = os.environ.get("TUMBLR_CLIENT_SECRET")
        self.blog_name = os.environ.get("TUMBLR_BLOG_NAME")
        
        self.base_url = "https://api.tumblr.com/v2"
        self.token_url = "https://api.tumblr.com/v2/oauth2/token"
        
        # Load or refresh access token
        self.access_token = self.get_access_token()
        
    def get_access_token(self):
        """Get or refresh access token"""
        # Try to load existing token
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                
                # Check if token is still valid (has at least 1 hour left)
                expires_at = datetime.fromisoformat(token_data.get('expires_at', '2000-01-01'))
                if expires_at > datetime.now() + timedelta(hours=1):
                    return token_data['access_token']
                
                # Try to refresh token
                if 'refresh_token' in token_data:
                    return self.refresh_access_token(token_data['refresh_token'])
                    
            except Exception as e:
                print(f"Error loading token: {e}")
        
        # If no valid token, need to get authorization code first
        print("No valid access token found. You need to run the authorization flow first.")
        return None
    
    def refresh_access_token(self, refresh_token):
        """Refresh access token using refresh token"""
        try:
            # Create Basic Auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Calculate expiration time
                expires_in = token_data.get('expires_in', 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Save token data
                token_info = {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token', refresh_token),
                    'expires_at': expires_at.isoformat(),
                    'expires_in': expires_in
                }
                
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                print("Access token refreshed successfully")
                return token_data['access_token']
            else:
                print(f"Failed to refresh token: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    
    def exchange_code_for_token(self, authorization_code, redirect_uri="http://localhost:8080/callback"):
        """Exchange authorization code for access token"""
        try:
            # Create Basic Auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': redirect_uri
            }
            
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Calculate expiration time
                expires_in = token_data.get('expires_in', 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Save token data
                token_info = {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token'),
                    'expires_at': expires_at.isoformat(),
                    'expires_in': expires_in
                }
                
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                print("Access token obtained successfully")
                return token_data['access_token']
            else:
                print(f"Failed to exchange code for token: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None

    def post_to_tumblr(self, post_content, tags, source_url):
        """Post content to Tumblr using OAuth 2.0"""
        if not self.access_token:
            return False, "No valid access token"
        
        url = f"{self.base_url}/blog/{self.blog_name}/posts"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Prepare post data for OAuth 2.0 (JSON format)
        post_data = {
            'content': [
                {
                    'type': 'text',
                    'text': f"{post_content}\n\nSource: {source_url}"
                }
            ],
            'tags': tags if isinstance(tags, list) else tags.split(',')
        }
        
        try:
            response = requests.post(url, headers=headers, json=post_data)
            
            if response.status_code == 201:
                result = response.json()
                return True, result.get('response', {}).get('id', '')
            else:
                print(f"Tumblr API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
                # If unauthorized, try to refresh token
                if response.status_code == 401:
                    print("Token expired, attempting to refresh...")
                    if os.path.exists(TOKEN_FILE):
                        with open(TOKEN_FILE, 'r') as f:
                            token_data = json.load(f)
                        if 'refresh_token' in token_data:
                            new_token = self.refresh_access_token(token_data['refresh_token'])
                            if new_token:
                                self.access_token = new_token
                                # Retry the request
                                headers['Authorization'] = f'Bearer {self.access_token}'
                                response = requests.post(url, headers=headers, json=post_data)
                                if response.status_code == 201:
                                    result = response.json()
                                    return True, result.get('response', {}).get('id', '')
                
                return False, f"API Error: {response.status_code}"
                
        except Exception as e:
            print(f"Error posting to Tumblr: {e}")
            return False, str(e)

def read_pending_posts():
    """Read pending posts from CSV file"""
    if not os.path.exists(PENDING_POSTS_FILE):
        return []
    
    posts = []
    try:
        with open(PENDING_POSTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append(row)
        return posts
    except Exception as e:
        print(f"Error reading pending posts: {e}")
        return []

def update_pending_posts(posts):
    """Update the pending posts CSV file"""
    try:
        with open(PENDING_POSTS_FILE, 'w', newline='', encoding='utf-8') as f:
            if posts:
                fieldnames = posts[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(posts)
        return True
    except Exception as e:
        print(f"Error updating pending posts: {e}")
        return False

def log_posted_content(post_data, success, tumblr_post_id=None, error=None):
    """Log posted content to the posted logs file"""
    try:
        file_exists = os.path.exists(POSTED_LOGS_FILE) and os.path.getsize(POSTED_LOGS_FILE) > 0
        
        with open(POSTED_LOGS_FILE, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'url', 'post_content', 'tags', 'scheduled_time', 'actual_posted_time', 'success', 'tumblr_post_id', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'id': post_data.get('id', ''),
                'url': post_data.get('url', ''),
                'post_content': post_data.get('post_content', '')[:100] + '...',
                'tags': post_data.get('tags', ''),
                'scheduled_time': post_data.get('scheduled_time', ''),
                'actual_posted_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'success': success,
                'tumblr_post_id': tumblr_post_id or '',
                'error': error or ''
            })
    except Exception as e:
        print(f"Error logging posted content: {e}")

def send_email_notification(subject, body, to_email):
    """Send email notification"""
    try:
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        email_user = os.environ.get("EMAIL_USER")
        email_password = os.environ.get("EMAIL_PASSWORD")
        
        if not all([email_user, email_password, to_email]):
            print("Email credentials not configured, skipping notification")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        
        print("Email notification sent successfully")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def main():
    print(f"Starting Tumblr posting process (OAuth 2.0) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize Tumblr poster
    tumblr_poster = TumblrOAuth2Poster()
    
    # Check if we have authorization code to exchange
    auth_code = os.environ.get("TUMBLR_AUTH_CODE")
    if auth_code and not tumblr_poster.access_token:
        print("Found authorization code, exchanging for access token...")
        tumblr_poster.access_token = tumblr_poster.exchange_code_for_token(auth_code)
    
    # Verify credentials
    if not all([tumblr_poster.client_id, tumblr_poster.client_secret, tumblr_poster.blog_name]):
        print("Missing Tumblr OAuth 2.0 credentials. Please set environment variables:")
        print("- TUMBLR_CLIENT_ID")
        print("- TUMBLR_CLIENT_SECRET")
        print("- TUMBLR_BLOG_NAME")
        return
    
    if not tumblr_poster.access_token:
        print("No valid access token available. Please run authorization flow first.")
        print("Visit this URL to authorize:")
        auth_url = f"https://www.tumblr.com/oauth2/authorize?client_id={tumblr_poster.client_id}&response_type=code&scope=write&redirect_uri=http://localhost:8080/callback"
        print(auth_url)
        return
    
    # Read pending posts
    pending_posts = read_pending_posts()
    if not pending_posts:
        print("No pending posts found.")
        return
    
    current_time = datetime.now()
    posts_to_publish = []
    
    # Find posts that are ready to be published
    for post in pending_posts:
        if post.get('posted', 'False').lower() == 'false':
            scheduled_time = datetime.strptime(post['scheduled_time'], "%Y-%m-%d %H:%M:%S")
            if scheduled_time <= current_time:
                posts_to_publish.append(post)
    
    if not posts_to_publish:
        print("No posts are scheduled for publishing at this time.")
        return
    
    print(f"Found {len(posts_to_publish)} posts ready for publishing")
    
    # Post to Tumblr
    successful_posts = 0
    failed_posts = 0
    post_details = []
    
    for post in posts_to_publish:
        print(f"\nPosting: {post['id']}")
        print(f"URL: {post['url']}")
        
        # Parse tags
        tags = post['tags'].split(',') if post['tags'] else []
        tags = [tag.strip() for tag in tags]
        
        # Post to Tumblr
        success, tumblr_post_id = tumblr_poster.post_to_tumblr(
            post['post_content'], 
            tags, 
            post['url']
        )
        
        if success:
            print(f"✅ Successfully posted to Tumblr (ID: {tumblr_post_id})")
            post['posted'] = 'True'
            post['posted_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            post['tumblr_post_id'] = tumblr_post_id
            successful_posts += 1
            
            log_posted_content(post, True, tumblr_post_id)
            
            post_details.append({
                'url': post['url'],
                'status': 'Success',
                'tumblr_id': tumblr_post_id,
                'scheduled_time': post['scheduled_time']
            })
        else:
            print(f"❌ Failed to post to Tumblr: {tumblr_post_id}")
            failed_posts += 1
            
            log_posted_content(post, False, error=tumblr_post_id)
            
            post_details.append({
                'url': post['url'],
                'status': f'Failed: {tumblr_post_id}',
                'tumblr_id': '',
                'scheduled_time': post['scheduled_time']
            })
        
        time.sleep(2)
    
    # Update pending posts file
    update_pending_posts(pending_posts)
    
    # Send email notification
    notification_email = os.environ.get("NOTIFICATION_EMAIL")
    if notification_email:
        subject = f"Tumblr Posting Report - {successful_posts} Posted, {failed_posts} Failed"
        
        body = f"""
        <html>
        <body>
        <h2>Tumblr Posting Report (OAuth 2.0)</h2>
        <p><strong>Posting completed at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total posts processed:</strong> {len(posts_to_publish)}</p>
        <p><strong>Successful posts:</strong> {successful_posts}</p>
        <p><strong>Failed posts:</strong> {failed_posts}</p>
        
        <h3>Post Details:</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th style="padding: 8px;">URL</th>
            <th style="padding: 8px;">Status</th>
            <th style="padding: 8px;">Tumblr ID</th>
            <th style="padding: 8px;">Scheduled Time</th>
        </tr>
        """
        
        for detail in post_details:
            body += f"""
            <tr>
                <td style="padding: 8px;"><a href="{detail['url']}">{detail['url'][:50]}...</a></td>
                <td style="padding: 8px;">{detail['status']}</td>
                <td style="padding: 8px;">{detail['tumblr_id']}</td>
                <td style="padding: 8px;">{detail['scheduled_time']}</td>
            </tr>
            """
        
        body += """
        </table>
        </body>
        </html>
        """
        
        send_email_notification(subject, body, notification_email)
    
    print(f"\nTumblr posting process completed:")
    print(f"✅ Successfully posted: {successful_posts}")
    print(f"❌ Failed to post: {failed_posts}")

if __name__ == "__main__":
    main()