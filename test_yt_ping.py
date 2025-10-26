from googleapiclient.discovery import build

# Your API key
api_key = "AIzaSyAEAFpHN28ZazNUvqkpJ-W7W6_xFQZkbOI"

# Build the YouTube service
youtube = build("youtube", "v3", developerKey=api_key)

# Video ID you want to fetch
video_id = "Ks-_Mh1QhMc"

# Make the API request
request = youtube.videos().list(
    part="snippet,contentDetails,statistics",
    id=video_id
)
response = request.execute()

# Check if the video exists
if response['items']:
    video = response['items'][0]

    # Snippet details
    snippet = video['snippet']
    title = snippet['title']
    description = snippet['description']
    channel = snippet['channelTitle']
    published_at = snippet['publishedAt']
    tags = snippet.get('tags', [])

    # Thumbnails (optional)
    thumbnails = snippet['thumbnails']
    default_thumb = thumbnails['default']['url']
    high_thumb = thumbnails['high']['url']

    # Statistics (optional)
    stats = video.get('statistics', {})
    view_count = stats.get('viewCount', 'N/A')
    like_count = stats.get('likeCount', 'N/A')
    comment_count = stats.get('commentCount', 'N/A')

    # Print a readable summary
    print(f"Title: {title}")
    print(f"Channel: {channel}")
    print(f"Published At: {published_at}")
    print(f"Description: {description[:200]}...")  # Show only first 200 chars
    print(f"Tags: {tags}")
    print(f"Views: {view_count}, Likes: {like_count}, Comments: {comment_count}")
    print(f"Thumbnail (default): {default_thumb}")
    print(f"Thumbnail (high): {high_thumb}")
else:
    print("No video found with the given ID.")
