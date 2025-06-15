import os
import pytumblr
import pandas as pd

def post_to_tumblr():
    """
    Reads a post from the pending_posts.csv file and posts it to Tumblr.
    Updates the processed URLs and logs the post.
    """
    try:
        # --- 1. Get Credentials from Environment Variables ---
        # These are set in the GitHub Actions workflow file from your repository's secrets
        consumer_key = os.environ['TUMBLR_CONSUMER_KEY']
        consumer_secret = os.environ['TUMBLR_CONSUMER_SECRET']
        oauth_token = os.environ['TUMBLR_OAUTH_TOKEN']
        oauth_secret = os.environ['TUMBLR_OAUTH_SECRET']
        blog_name = 'YOUR_TUMBLR_BLOG_NAME'  # <-- SET YOUR TUMBLR BLOG NAME HERE

        # --- 2. Authenticate with Tumblr ---
        client = pytumblr.TumblrRestClient(
            consumer_key,
            consumer_secret,
            oauth_token,
            oauth_secret
        )

        # --- 3. Read the post data ---
        pending_posts_df = pd.read_csv("data/pending_posts.csv")
        if pending_posts_df.empty:
            print("No pending posts to share.")
            return

        post_to_share = pending_posts_df.iloc[0]
        title = post_to_share['title']
        url = post_to_share['url']
        tags = post_to_share['tags'].split(',')

        # --- 4. Create the post ---
        print(f"Posting to Tumblr: {title}")
        client.create_link(blog_name, title=title, url=url, tags=tags)
        print("Successfully posted to Tumblr.")

        # --- 5. Log the posted item and update CSVs ---
        # (Your existing logic for updating CSVs and text files)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Re-raise the exception to make the GitHub Action fail
        raise

if __name__ == "__main__":
    post_to_tumblr()