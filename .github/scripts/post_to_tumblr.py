#!/usr/bin/env python3
# .github/scripts/post_to_tumblr.py

import os
import csv
import json
import requests
import time
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlencode
import tempfile

# Configuration
PENDING_POSTS_FILE = "data/pending_posts.csv"
POSTED_LOGS_FILE = "data/posted_logs.csv"
TUMBLR_CONFIG_FILE = "data/tumblr_config.json"

class TumblrPoster:
    def __init__(self):
        self.consumer_key = os.environ.get("TUMBLR_CONSUMER_KEY")
        self.consumer_secret = os.environ.get("TUMBLR_CONSUMER_SECRET")
        self.oauth_token = os.environ.get("TUMBLR_OAUTH_TOKEN")
        self.oauth_token_secret = os.environ.get("TUMBLR_OAUTH_TOKEN_SECRET")
        self.blog_name = os.environ.get("TUMBLR_BLOG_NAME")
        
        self.base_url = "https://api.tumblr.com/v2"
        
    def create_oauth_header(self, url, method="POST", params=None):
        """Create OAuth authorization header for Tumblr API"""
        import hmac
        import hashlib
        import base64
        import secrets
        from urllib.parse import quote
        
        # OAuth parameters
        oauth_params = {
            'oauth_consumer_key': self.consumer_key,
            'oauth_nonce': secrets.token_hex(16),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': self.oauth_token,
            'oauth_version': '1.0'
        }
        
        # Combine OAuth params with request params
        all_params = oauth_params.copy()
        if params:
            all_params.update(params)
            
        # Create parameter string
        param_string = '&'.join([f'{quote(str(k))}={quote(str(v))}' for k, v in sorted(all_params.items())])
        
        # Create signature base string
        signature_base = f'{method}&{quote(url)}&{quote(param_string)}'
        
        # Create signing key
        signing_key = f'{quote(self.consumer_secret)}&{quote(self.oauth_token_secret)}'
        
        # Generate signature
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), signature_base.encode(), hashlib.sha1).digest()
        ).decode()
        
        oauth_params['oauth_signature'] = signature
        
        # Create authorization header
        auth_header = 'OAuth ' + ', '.join([f'{k}="{quote(str(v))}"' for k, v in oauth_params.items()])
        
        return auth_header

    def post_to_tumblr(self, post_content, tags, source_url):
        """Post content to Tumblr"""
        url = f"{self.base_url}/blog/{self.blog_name}/post"
        
        # Prepare post data
        post_data = {
            'type': 'text',
            'body': f"{post_content}\n\nSource: {source_url}",
            'tags': ','.join(tags) if isinstance(tags, list) else tags,
            'format': 'html'
        }
        
        try:
            # Create authorization header
            auth_header = self.create_oauth_header(url, "POST", post_data)
            
            headers = {
                'Authorization': auth_header,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Make the request
            response = requests.post(url, data=post_data, headers=headers)
            
            if response.status_code == 201:
                result = response.json()
                return True, result.get('response', {}).get('id', '')
            else:
                print(f"Tumblr API Error: {response.status_code}")
                print(f"Response: {response.text}")
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
                'post_content': post_data.get('post_content', '')[:100] + '...',  # Truncate for log
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
    print(f"Starting Tumblr posting process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize Tumblr poster
    tumblr_poster = TumblrPoster()
    
    # Verify Tumblr credentials
    if not all([tumblr_poster.consumer_key, tumblr_poster.consumer_secret, 
                tumblr_poster.oauth_token, tumblr_poster.oauth_token_secret, 
                tumblr_poster.blog_name]):
        print("Missing Tumblr API credentials. Please set environment variables:")
        print("- TUMBLR_CONSUMER_KEY")
        print("- TUMBLR_CONSUMER_SECRET") 
        print("- TUMBLR_OAUTH_TOKEN")
        print("- TUMBLR_OAUTH_TOKEN_SECRET")
        print("- TUMBLR_BLOG_NAME")
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
            
            # Log successful post
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
            
            # Log failed post
            log_posted_content(post, False, error=tumblr_post_id)
            
            post_details.append({
                'url': post['url'],
                'status': f'Failed: {tumblr_post_id}',
                'tumblr_id': '',
                'scheduled_time': post['scheduled_time']
            })
        
        # Small delay between posts
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
        <h2>Tumblr Posting Report</h2>
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