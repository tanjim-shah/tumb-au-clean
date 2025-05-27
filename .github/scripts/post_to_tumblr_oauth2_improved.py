#!/usr/bin/env python3
# .github/scripts/post_to_tumblr_oauth2_improved.py

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
        
        # Validate required credentials
        if not all([self.client_id, self.client_secret, self.blog_name]):
            raise ValueError("Missing required Tumblr credentials. Please set TUMBLR_CLIENT_ID, TUMBLR_CLIENT_SECRET, and TUMBLR_BLOG_NAME environment variables.")
        
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
                    print(f"✅ Using existing valid token (expires at {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    return token_data['access_token']
                
                # Try to refresh token
                if 'refresh_token' in token_data:
                    print("🔄 Token expiring soon, attempting to refresh...")
                    refreshed_token = self.refresh_access_token(token_data['refresh_token'])
                    if refreshed_token:
                        return refreshed_token
                    
            except Exception as e:
                print(f"⚠️  Error loading token file: {e}")
        
        # If no valid token, check for authorization code in environment
        auth_code = os.environ.get("TUMBLR_AUTH_CODE")
        if auth_code:
            print("🔑 Found authorization code, exchanging for access token...")
            return self.exchange_code_for_token(auth_code)
        
        # No valid token or auth code available
        print("❌ No valid access token or authorization code found.")
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
                    'expires_in': expires_in,
                    'refreshed_at': datetime.now().isoformat()
                }
                
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                print(f"✅ Access token refreshed successfully (expires at {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                return token_data['access_token']
            else:
                print(f"❌ Failed to refresh token: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error refreshing token: {e}")
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
                    'expires_in': expires_in,
                    'created_at': datetime.now().isoformat()
                }
                
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                print(f"✅ Access token obtained successfully (expires at {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                return token_data['access_token']
            else:
                print(f"❌ Failed to exchange code for token: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error exchanging code for token: {e}")
            return None

    def test_api_connection(self):
        """Test API connection and token validity"""
        if not self.access_token:
            return False
        
        url = f"{self.base_url}/blog/{self.blog_name}/info"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                blog_info = response.json()
                blog_title = blog_info.get('response', {}).get('blog', {}).get('title', 'Unknown')
                print(f"✅ API connection successful! Blog: {blog_title}")
                return True
            else:
                print(f"❌ API connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API connection error: {e}")
            return False

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
            'tags': tags if isinstance(tags, list) else [tag.strip() for tag in tags.split(',') if tag.strip()]
        }
        
        try:
            response = requests.post(url, headers=headers, json=post_data)
            
            if response.status_code == 201:
                result = response.json()
                post_id = result.get('response', {}).get('id', '')
                print(f"✅ Post successful! Tumblr ID: {post_id}")
                return True, post_id
            else:
                print(f"❌ Tumblr API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
                # If unauthorized, try to refresh token once
                if response.status_code == 401:
                    print("🔄 Token may be expired, attempting to refresh...")
                    if os.path.exists(TOKEN_FILE):
                        with open(TOKEN_FILE, 'r') as f:
                            token_data = json.load(f)
                        if 'refresh_token' in token_data:
                            new_token = self.refresh_access_token(token_data['refresh_token'])
                            if new_token:
                                self.access_token = new_token
                                # Retry the request once
                                headers['Authorization'] = f'Bearer {self.access_token}'
                                response = requests.post(url, headers=headers, json=post_data)
                                if response.status_code == 201:
                                    result = response.json()
                                    post_id = result.get('response', {}).get('id', '')
                                    print(f"✅ Post successful after token refresh! Tumblr ID: {post_id}")
                                    return True, post_id
                
                return False, f"API Error: {response.status_code} - {response.text[:200]}"
                
        except Exception as e:
            print(f"❌ Error posting to Tumblr: {e}")
            return False, str(e)

def read_pending_posts():
    """Read pending posts from CSV file"""
    if not os.path.exists(PENDING_POSTS_FILE):
        print(f"⚠️  Pending posts file not found: {PENDING_POSTS_FILE}")
        return []
    
    posts = []
    try:
        with open(PENDING_POSTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append(row)
        print(f"📄 Read {len(posts)} posts from {PENDING_POSTS_FILE}")
        return posts
    except Exception as e:
        print(f"❌ Error reading pending posts: {e}")
        return []

def update_pending_posts(posts):
    """Update the pending posts CSV file"""
    try:
        os.makedirs(os.path.dirname(PENDING_POSTS_FILE), exist_ok=True)
        with open(PENDING_POSTS_FILE, 'w', newline='', encoding='utf-8') as f:
            if posts:
                fieldnames = posts[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(posts)
        print(f"💾 Updated pending posts file")
        return True
    except Exception as e:
        print(f"❌ Error updating pending posts: {e}")
        return False

def log_posted_content(post_data, success, tumblr_post_id=None, error=None):
    """Log posted content to the posted logs file"""
    try:
        os.makedirs(os.path.dirname(POSTED_LOGS_FILE), exist_ok=True)
        file_exists = os.path.exists(POSTED_LOGS_FILE) and os.path.getsize(POSTED_LOGS_FILE) > 0
        
        with open(POSTED_LOGS_FILE, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'url', 'post_content', 'tags', 'scheduled_time', 'actual_posted_time', 'success', 'tumblr_post_id', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'id': post_data.get('id', ''),
                'url': post_data.get('url', ''),
                'post_content': post_data.get('post_content', '')[:100] + ('...' if len(post_data.get('post_content', '')) > 100 else ''),
                'tags': post_data.get('tags', ''),
                'scheduled_time': post_data.get('scheduled_time', ''),
                'actual_posted_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'success': success,
                'tumblr_post_id': tumblr_post_id or '',
                'error': error or ''
            })
    except Exception as e:
        print(f"❌ Error logging posted content: {e}")

def send_email_notification(subject, body, to_email):
    """Send email notification"""
    try:
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        email_user = os.environ.get("EMAIL_USER")
        email_password = os.environ.get("EMAIL_PASSWORD")
        
        if not all([email_user, email_password, to_email]):
            print("⚠️  Email credentials not configured, skipping notification")
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
        
        print("📧 Email notification sent successfully")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def main():
    print(f"🚀 Starting Tumblr posting process (OAuth 2.0) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        # Initialize Tumblr poster
        tumblr_poster = TumblrOAuth2Poster()
        
        if not tumblr_poster.access_token:
            print("❌ No valid access token available.")
            print("\n📋 To set up OAuth 2.0 authentication:")
            print("1. Run the setup script locally: python setup_tumblr_oauth.py")
            print("2. Or set TUMBLR_AUTH_CODE environment variable with a fresh authorization code")
            print("\n🔗 Authorization URL:")
            auth_url = f"https://www.tumblr.com/oauth2/authorize?client_id={tumblr_poster.client_id}&response_type=code&scope=write&redirect_uri=http://localhost:8080/callback"
            print(auth_url)
            return
        
        # Test API connection
        if not tumblr_poster.test_api_connection():
            print("❌ API connection test failed. Please check your credentials and token.")
            return
        
        # Read pending posts
        pending_posts = read_pending_posts()
        if not pending_posts:
            print("ℹ️  No pending posts found.")
            return
        
        current_time = datetime.now()
        posts_to_publish = []
        
        # Find posts that are ready to be published
        for post in pending_posts:
            if post.get('posted', 'False').lower() == 'false':
                try:
                    scheduled_time = datetime.strptime(post['scheduled_time'], "%Y-%m-%d %H:%M:%S")
                    if scheduled_time <= current_time:
                        posts_to_publish.append(post)
                except ValueError as e:
                    print(f"⚠️  Invalid scheduled_time format for post {post.get('id', 'unknown')}: {e}")
                    continue
        
        if not posts_to_publish:
            print("ℹ️  No posts are scheduled for publishing at this time.")
            print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show next scheduled post if any
            future_posts = [p for p in pending_posts if p.get('posted', 'False').lower() == 'false']
            if future_posts:
                try:
                    next_post = min(future_posts, key=lambda x: datetime.strptime(x['scheduled_time'], "%Y-%m-%d %H:%M:%S"))
                    next_time = datetime.strptime(next_post['scheduled_time'], "%Y-%m-%d %H:%M:%S")
                    print(f"Next post scheduled for: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass
            return
        
        print(f"📝 Found {len(posts_to_publish)} posts ready for publishing")
        
        # Post to Tumblr
        successful_posts = 0
        failed_posts = 0
        post_details = []
        
        for i, post in enumerate(posts_to_publish, 1):
            print(f"\n[{i}/{len(posts_to_publish)}] Processing post: {post.get('id', 'unknown')}")
            print(f"URL: {post.get('url', 'N/A')}")
            print(f"Scheduled: {post.get('scheduled_time', 'N/A')}")
            
            # Parse tags
            tags = post.get('tags', '').split(',') if post.get('tags') else []
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            # Post to Tumblr
            success, result = tumblr_poster.post_to_tumblr(
                post.get('post_content', ''), 
                tags, 
                post.get('url', '')
            )
            
            if success:
                print(f"✅ Successfully posted (Tumblr ID: {result})")
                post['posted'] = 'True'
                post['posted_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                post['tumblr_post_id'] = result
                successful_posts += 1
                
                log_posted_content(post, True, result)
                
                post_details.append({
                    'url': post.get('url', ''),
                    'status': 'Success',
                    'tumblr_id': result,
                    'scheduled_time': post.get('scheduled_time', ''),
                    'content_preview': post.get('post_content', '')[:100] + ('...' if len(post.get('post_content', '')) > 100 else '')
                })
            else:
                print(f"❌ Failed to post: {result}")
                failed_posts += 1
                
                log_posted_content(post, False, error=result)
                
                post_details.append({
                    'url': post.get('url', ''),
                    'status': f'Failed: {result}',
                    'tumblr_id': '',
                    'scheduled_time': post.get('scheduled_time', ''),
                    'content_preview': post.get('post_content', '')[:100] + ('...' if len(post.get('post_content', '')) > 100 else '')
                })
            
            # Rate limiting: wait between posts
            if i < len(posts_to_publish):
                print("⏳ Waiting 3 seconds before next post...")
                time.sleep(3)
        
        # Update pending posts file
        if update_pending_posts(pending_posts):
            print(f"💾 Updated pending posts file with results")
        
        # Send email notification
        notification_email = os.environ.get("NOTIFICATION_EMAIL")
        if notification_email and post_details:
            subject = f"Tumblr Posting Report - {successful_posts} Posted, {failed_posts} Failed"
            
            body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #00cf35; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                    .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                    .stat {{ text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }}
                    .success {{ color: #28a745; font-weight: bold; }}
                    .failed {{ color: #dc3545; font-weight: bold; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f8f9fa; font-weight: bold; }}
                    .status-success {{ color: #28a745; font-weight: bold; }}
                    .status-failed {{ color: #dc3545; font-weight: bold; }}
                    .url-link {{ color: #007bff; text-decoration: none; }}
                    .url-link:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🤖 Tumblr Posting Report</h2>
                        <p>Automated posting completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    </div>
                    
                    <div class="stats">
                        <div class="stat">
                            <h3>📊 Total Processed</h3>
                            <p style="font-size: 24px; margin: 0;">{len(posts_to_publish)}</p>
                        </div>
                        <div class="stat">
                            <h3 class="success">✅ Successful</h3>
                            <p style="font-size: 24px; margin: 0;" class="success">{successful_posts}</p>
                        </div>
                        <div class="stat">
                            <h3 class="failed">❌ Failed</h3>
                            <p style="font-size: 24px; margin: 0;" class="failed">{failed_posts}</p>
                        </div>
                    </div>
                    
                    <h3>📝 Post Details</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Source URL</th>
                                <th>Status</th>
                                <th>Tumblr ID</th>
                                <th>Scheduled Time</th>
                                <th>Content Preview</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for detail in post_details:
                status_class = "status-success" if "Success" in detail['status'] else "status-failed"
                body += f"""
                            <tr>
                                <td><a href="{detail['url']}" class="url-link" target="_blank">{detail['url'][:50]}{'...' if len(detail['url']) > 50 else ''}</a></td>
                                <td class="{status_class}">{detail['status']}</td>
                                <td>{detail['tumblr_id']}</td>
                                <td>{detail['scheduled_time']}</td>
                                <td>{detail['content_preview']}</td>
                            </tr>
                """
            
            body += """
                        </tbody>
                    </table>
                    
                    <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                        <p><strong>Note:</strong> This is an automated report from your Tumblr posting system.</p>
                        <p>If you're experiencing issues, check your GitHub Actions logs for more details.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_notification(subject, body, notification_email)
        
        # Final summary
        print(f"\n" + "=" * 70)
        print(f"🎯 Tumblr posting process completed!")
        print(f"✅ Successfully posted: {successful_posts}")
        print(f"❌ Failed to post: {failed_posts}")
        print(f"📊 Total processed: {len(posts_to_publish)}")
        
        if successful_posts > 0:
            print(f"🎉 Your content is now live on Tumblr!")
        
        if failed_posts > 0:
            print(f"⚠️  Some posts failed. Check the logs for details.")
            
    except Exception as e:
        print(f"❌ Fatal error in main process: {e}")
        import traceback
        traceback.print_exc()
        
        # Send error notification
        notification_email = os.environ.get("NOTIFICATION_EMAIL")
        if notification_email:
            subject = "Tumblr Posting Error"
            body = f"""
            <html>
            <body>
                <h2>❌ Tumblr Posting Error</h2>
                <p><strong>Error occurred at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                <p><strong>Error message:</strong> {str(e)}</p>
                <p>Please check your GitHub Actions logs for more details.</p>
            </body>
            </html>
            """
            send_email_notification(subject, body, notification_email)

if __name__ == "__main__":
    main()