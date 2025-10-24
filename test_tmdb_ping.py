import os
import httpx

# TMDb API key
TMDB_API_KEY = "22d95288429b11d8ba8b809f83eb3752"

# Sample movie title from a trailer
movie_title = "Everything Everywhere All At Once"

# TMDb search endpoint
search_url = "https://api.themoviedb.org/3/search/movie"

params = {
    "api_key": TMDB_API_KEY,
    "query": movie_title
}

try:
    response = httpx.get(search_url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if data.get("results"):
        movie = data["results"][0]
        print("✅ TMDb API key is working!")
        print("Title:", movie.get("title"))
        print("Release Date:", movie.get("release_date"))
        print("Overview:", movie.get("overview"))
    else:
        print("⚠️ No results found for the movie")
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code} - {e.response.text}")
except Exception as e:
    print("Error:", str(e))
