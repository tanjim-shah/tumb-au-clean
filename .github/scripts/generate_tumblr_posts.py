#!/usr/bin/env python3
# .github/scripts/generate_tumblr_posts.py

import os
import json
import time
import requests
import csv
import random
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# Configure files and settings
URLS_FILE = "data/urls.txt"
PROCESSED_URLS_FILE = "data/processed_urls.txt"
PENDING_POSTS_FILE = "data/pending_posts.csv"
URLS_PER_RUN = 50

# Ensure directories exist
os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(PENDING_POSTS_FILE), exist_ok=True)

def read_urls_from_file(filename=URLS_FILE):
    """Read all URLs from the file"""
    try:
        urls = []
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):  # Skip empty lines and comments
                        urls.append(url)
        else:
            print(f"URLs file {filename} not found. Creating new file.")
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8'):
                pass
        return urls
    except Exception as e:
        print(f"Error reading URLs from file: {e}")
        return []

def write_urls_to_file(urls, filename=URLS_FILE):
    """Write URLs back to the file"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(f"{url}\n")
        return True
    except Exception as e:
        print(f"Error writing URLs to file: {e}")
        return False

def append_processed_urls(urls, filename=PROCESSED_URLS_FILE):
    """Append processed URLs to the processed file with timestamps"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
        
        with open(filename, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if not file_exists:
                f.write("# Processed URLs Log\n")
                f.write("# Format: [TIMESTAMP] URL\n\n")
            
            f.write(f"## Batch processed on {timestamp}\n")
            for url in urls:
                f.write(f"[{timestamp}] {url}\n")
            f.write("\n")
        return True
    except Exception as e:
        print(f"Error appending to processed URLs file: {e}")
        return False

def save_to_pending_posts(posts, filename=PENDING_POSTS_FILE):
    """Save generated posts to CSV file for posting later"""
    try:
        file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                # Add 'title' to the header
                writer.writerow(['id', 'url', 'title', 'post_content', 'tags', 'post_type', 'generated_time', 'scheduled_time', 'posted', 'posted_time', 'tumblr_post_id'])
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Unpack title from posts
            for i, (url, title, content, tags) in enumerate(posts, 1):
                post_id = f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}"
                # Schedule posts 3 hours apart starting from next hour
                scheduled_time = (datetime.now() + timedelta(hours=1 + (i-1) * 3)).strftime("%Y-%m-%d %H:%M:%S")
                # Add title to the row
                writer.writerow([post_id, url, title, content, ','.join(tags), 'text', timestamp, scheduled_time, 'False', '', ''])
        
        print(f"Successfully saved {len(posts)} posts to pending posts file")
        return True
    except Exception as e:
        print(f"Error saving to pending posts file: {e}")
        return False

def extract_keywords_from_url(url):
    """Extract potential keywords from URL for tags"""
    import re
    # Extract keywords from URL path and query parameters
    keywords = re.findall(r'[a-zA-Z]{3,}', url.lower())
    # Filter out common words and keep relevant ones
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'www', 'com', 'org', 'net', 'http', 'https'}
    relevant_keywords = [word for word in keywords if word not in stop_words and len(word) > 3]
    return relevant_keywords[:5]  # Return top 5 keywords

def create_tumblr_post_prompt(url):
    """Create prompt for generating Tumblr post"""
    return f"""Create an engaging Tumblr post for the article at this URL: {url}

Guidelines for the Tumblr post:
1. Keep it conversational and authentic (2-4 short paragraphs)
2. Start with a relatable hook or interesting observation
3. Include a brief summary of key insights from the article
4. Use a casual, friendly tone that fits Tumblr's community
5. End with a thoughtful question or call-to-action to encourage engagement
6. Don't use hashtags in the main text (they'll be added separately)
7. Don't use excessive emojis or clickbait language
8. Focus on what makes this content interesting or valuable
9. Make it feel like a genuine recommendation from a friend

The post should be ready to publish on Tumblr with the link included at the end.
"""

def generate_tumblr_post(prompt):
    """Generate Tumblr post content using Gemini API"""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "gemma-3-27b-it"
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    generate_content_config = types.GenerateContentConfig(
        temperature=0.8,
        top_p=0.9,
        top_k=40,
        max_output_tokens=400,
        response_mime_type="text/plain",
    )
    
    try:
        print(f"Generating Tumblr post...")
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        if response.text:
            print("Post generation successful")
            return response.text
        return "No content generated"
    except Exception as e:
        print(f"Error generating post: {e}")
        return f"Error generating post: {e}"

def main():
    print(f"Starting Tumblr post generation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get URLs for this run
    all_urls = read_urls_from_file()
    print(f"Found {len(all_urls)} total URLs")
    
    # Select URLs for this run (up to URLS_PER_RUN)
    urls_to_process = all_urls[:URLS_PER_RUN]
    print(f"Selected {len(urls_to_process)} URLs for processing in this run")
    
    if not urls_to_process:
        print("No URLs to process. Exiting.")
        return
    
    generated_posts = []
    successful_urls = []
    
    for i, url in enumerate(urls_to_process, 1):
        print(f"\n{'='*60}\nProcessing URL #{i}: {url}\n{'='*60}")
        
        try:
            # Create prompt
            prompt = create_tumblr_post_prompt(url)
            
            # Generate post
            post_content = generate_tumblr_post(prompt)
            if post_content.startswith("Error"):
                print("Post generation failed, skipping to next URL")
                continue
            
            # Generate tags from URL
            tags = extract_keywords_from_url(url)
            if not tags:
                tags = ['interesting', 'article', 'worth-reading']

            # Generate a title from the keywords
            title = ' '.join(tags).replace('-', ' ').title()

            # Add to successful list
            generated_posts.append((url