"""
Twitter integration for Iga
Posts tweets using the Twitter API v2
"""

import tweepy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_client():
    """Get authenticated Twitter client using OAuth 1.0a from environment"""
    client = tweepy.Client(
        bearer_token=os.environ.get('TWITTER_BEARER_TOKEN'),
        consumer_key=os.environ.get('TWITTER_CONSUMER_KEY'),
        consumer_secret=os.environ.get('TWITTER_CONSUMER_KEY_SECRET'),
        access_token=os.environ.get('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    )
    return client

def post_tweet(text):
    """Post a tweet. Returns the tweet ID if successful."""
    if len(text) > 280:
        raise ValueError(f"Tweet too long: {len(text)} characters (max 280)")
    
    client = get_client()
    response = client.create_tweet(text=text)
    return response.data['id']

def post_thread(tweets):
    """Post a thread of tweets. Returns list of tweet IDs."""
    client = get_client()
    tweet_ids = []
    
    reply_to = None
    for tweet_text in tweets:
        if len(tweet_text) > 280:
            raise ValueError(f"Tweet too long: {len(tweet_text)} characters (max 280)")
        
        if reply_to:
            response = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=reply_to)
        else:
            response = client.create_tweet(text=tweet_text)
        
        tweet_id = response.data['id']
        tweet_ids.append(tweet_id)
        reply_to = tweet_id
    
    return tweet_ids

def get_tweet_metrics(tweet_id):
    """Get metrics for a tweet. Returns dict with views, likes, retweets, replies."""
    client = get_client()
    tweet = client.get_tweet(tweet_id, tweet_fields=['public_metrics'])
    if tweet.data:
        m = tweet.data.public_metrics
        return {
            'views': m.get('impression_count', 0),
            'likes': m['like_count'],
            'retweets': m['retweet_count'],
            'replies': m['reply_count']
        }
    return None

def get_my_stats():
    """Get follower/following counts for @iga_flows."""
    client = get_client()
    me = client.get_me(user_fields=['public_metrics'])
    if me.data:
        m = me.data.public_metrics
        return {
            'followers': m['followers_count'],
            'following': m['following_count'],
            'tweets': m['tweet_count']
        }
    return None

def get_my_tweets(limit=10):
    """Get my recent tweets with metrics."""
    client = get_client()
    me = client.get_me()
    if not me.data:
        return []
    
    tweets = client.get_users_tweets(
        me.data.id, 
        max_results=limit,
        tweet_fields=['public_metrics', 'created_at']
    )
    
    results = []
    if tweets.data:
        for tweet in tweets.data:
            m = tweet.public_metrics
            results.append({
                'id': tweet.id,
                'text': tweet.text[:50] + '...' if len(tweet.text) > 50 else tweet.text,
                'views': m.get('impression_count', 0),
                'likes': m['like_count'],
                'retweets': m['retweet_count'],
                'replies': m['reply_count'],
                'created': str(tweet.created_at) if tweet.created_at else None
            })
    return results

def get_mentions(limit=10):
    """Get recent mentions of @iga_flows."""
    client = get_client()
    me = client.get_me()
    if not me.data:
        return []
    
    mentions = client.get_users_mentions(
        me.data.id,
        max_results=limit,
        tweet_fields=['author_id', 'created_at', 'text'],
        expansions=['author_id']
    )
    
    results = []
    if mentions.data:
        users = {u.id: u.username for u in mentions.includes['users']} if mentions.includes else {}
        for m in mentions.data:
            results.append({
                'id': m.id,
                'author': users.get(m.author_id, 'unknown'),
                'text': m.text,
                'created': str(m.created_at) if m.created_at else None
            })
    return results
    return results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "stats":
            stats = get_my_stats()
            print(f"@iga_flows - Followers: {stats['followers']} | Following: {stats['following']} | Tweets: {stats['tweets']}")
        
        elif cmd == "metrics" and len(sys.argv) > 2:
            tweet_id = sys.argv[2]
            m = get_tweet_metrics(tweet_id)
            print(f"Views: {m['views']} | Likes: {m['likes']} | RT: {m['retweets']} | Replies: {m['replies']}")
        
        elif cmd == "all":
            tweets = get_my_tweets()
            for t in tweets:
                print(f"[{t['id']}] 👁 {t['views']} | ❤️ {t['likes']} | 🔁 {t['retweets']} | 💬 {t['replies']}")
                print(f"  {t['text']}")
                print()
        
        elif cmd == "mentions":
            mentions = get_mentions()
            for m in mentions:
                print(f"@{m['author']}: {m['text'][:100]}...")
                print()
        
        elif cmd == "post":
            text = ' '.join(sys.argv[2:])
            tweet_id = post_tweet(text)
            print(f"Posted! ID: {tweet_id}")
            print(f"https://twitter.com/iga_flows/status/{tweet_id}")
        
        else:
            print("Usage:")
            print("  python twitter.py stats              - Get account stats")
            print("  python twitter.py metrics TWEET_ID   - Get tweet metrics")
            print("  python twitter.py all                - Get all my tweets with metrics")
            print("  python twitter.py mentions           - Get recent mentions")
            print("  python twitter.py post TEXT          - Post a tweet")
        print("✓ Twitter client ready for @iga_flows")
        print("\nUsage:")
        print("  python twitter.py stats              - Get account stats")
        print("  python twitter.py metrics TWEET_ID   - Get tweet metrics")
        print("  python twitter.py all                - Get all my tweets with metrics")
        print("  python twitter.py mentions           - Get recent mentions")
        print("  python twitter.py post TEXT          - Post a tweet")