#!/usr/bin/env python3
# .github/scripts/post_to_tumblr.py

import os
import pytumblr
import pandas as pd
from datetime import datetime

def post_to_tumblr():
    """
    Reads the next post from pending_posts.csv, posts it to Tumblr as a link post,
    and then removes it from the pending file.
    """
    pending_posts_file = "data/pending_posts.csv"

    try:
        # --- 1. Get Credentials and Check for Missing Secrets ---
        consumer_key = os.environ.get('TUMBLR_CONSUMER_KEY')
        consumer_secret = os.environ.get('TUMBLR_CONSUMER_SECRET')
        oauth_token = os.environ.get('TUMBLR_OAUTH_TOKEN')
        oauth_secret = os.environ.get('TUMBLR_OAUTH_TOKEN_SECRET')
        blog_name = os.environ.get("TUMBLR_BLOG_NAME")

        if not all([consumer_key, consumer_secret, oauth_token, oauth_secret, blog_name]):
            print("Error: One or more required Tumblr API credentials are not set in your GitHub Secrets.")
            print("Please check the following secrets in your repository's Settings > Secrets and variables > Actions:")
            print("- TUMBLR_CONSUMER_KEY")
            print("- TUMBLR_CONSUMER_SECRET")
            print("- TUMBLR_OAUTH_TOKEN")
            print("- TUMBLR_OAUTH_TOKEN_SECRET")
            print("- TUMBLR_BLOG_NAME")
            raise ValueError("Missing Tumblr API credentials.")

        # --- 2. Authenticate with Tumblr ---
        client = pytumblr.TumblrRestClient(
            consumer_key,
            consumer_secret,
            oauth_token,
            oauth_secret
        )

        # --- 3. Read the pending posts data ---
        if not os.path.exists(pending_posts_file) or os.path.getsize(pending_posts_file) == 0:
            print("No pending posts file found or file is empty.")
            return
            
        pending_posts_df = pd.read_csv(pending_posts_file)
        if pending_posts_df.empty:
            print("No pending posts to share.")
            return

        # --- 4. Get the next post to share ---
        post_to_share = pending_posts_df.iloc[0]
        
        post_id = post_to_share['id']
        title = post_to_share['title'] 
        url = post_to_share['url']
        description = post_to_share['post_content']
        tags_str = post_to_share.get('tags', '')
        tags = [tag.strip() for tag in tags_str.split(',')] if tags_str else []

        # --- 5. Create the post on Tumblr ---
        print(f"Posting to Tumblr: {title}")
        response = client.create_link(
            blog_name, 
            title=title, 
            url=url, 
            description=description, 
            tags=tags,
            state="published"
        )
        
        if "id" not in response:
             print(f"Failed to post to Tumblr. Response: {response}")
             raise Exception(f"Tumblr API Error: {response}")

        tumblr_post_id = response['id']
        print(f"Successfully posted to Tumblr. Post ID: {tumblr_post_id}")

        # --- 6. Remove the posted item from the pending list ---
        remaining_posts_df = pending_posts_df.iloc[1:]
        remaining_posts_df.to_csv(pending_posts_file, index=False)
        print(f"Removed post {post_id} from pending posts.")

    except ValueError as e:
        print(e)
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

if __name__ == "__main__":
    post_to_tumblr()