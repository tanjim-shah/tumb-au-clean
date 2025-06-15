import pytumblr
from urllib.parse import parse_qs

# --- Step 1: Get these from https://www.tumblr.com/oauth/apps ---
consumer_key = 'npx1m3sT82DEo6rFoNblOCtNCC6aQU2TUN2Y1KmK6sjGzy7Q3'
consumer_secret = 'YOUR_CONSUMER_SECRET'

# --- Step 2: Create a TumblrRestClient ---
client = pytumblr.TumblrRestClient(consumer_key, consumer_secret)

# --- Step 3: Get the request token ---
request_token = client.get_request_token()
oauth_token = request_token['oauth_token']
oauth_token_secret = request_token['oauth_token_secret']

# --- Step 4: Get the authorization URL ---
auth_url = client.get_authorize_url(oauth_token)
print(f"Please go to this URL and authorize the app: {auth_url}")

# --- Step 5: Get the verifier from the callback URL ---
callback_response = input("Paste the full callback URL here: ")
parsed_response = parse_qs(callback_response.split('?')[1])
oauth_verifier = parsed_response['oauth_verifier'][0]

# --- Step 6: Get the final access tokens ---
final_token = client.get_access_token(oauth_token, oauth_token_secret, oauth_verifier)
final_oauth_token = final_token['oauth_token']
final_oauth_token_secret = final_token['oauth_token_secret']

# --- Step 7: Print your final credentials ---
print("\n--- Your Tumblr API Credentials ---")
print(f"TUMBLR_CONSUMER_KEY = {consumer_key}")
print(f"TUMBLR_CONSUMER_SECRET = {consumer_secret}")
print(f"TUMBLR_OAUTH_TOKEN = {final_oauth_token}")
print(f"TUMBLR_OAUTH_SECRET = {final_oauth_token_secret}")
print("\nAdd these to your GitHub repository's secrets.")