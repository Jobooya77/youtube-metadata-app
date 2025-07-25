# ==============================================================================
#                      YOUTUBE METADATA FINDER - v3.0
# ==============================================================================
# Required libraries: streamlit, google-api-python-client, pandas
# To install them, run this in your terminal:
# py -m pip install streamlit google-api-python-client pandas
#
# To run the app, navigate to this folder in your terminal and type:
# py -m streamlit run youtube_app.py
# ==============================================================================

import streamlit as st
import pandas as pd
import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs

# --- Configuration & API Key ---
API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

# --- Helper Functions ---

def extract_video_id_from_url(url):
    """Extracts the YouTube video ID from a variety of URL formats."""
    if not url:
        return None
    query = urlparse(url)
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query).get('v', [None])[0]
        if query.path.startswith('/embed/'):
            return query.path.split('/embed/')[1]
        if query.path.startswith('/v/'):
            return query.path.split('/v/')[1]
    if query.hostname == 'youtu.be':
        return query.path[1:]
    return None

def extract_playlist_id_from_url(url):
    """Extracts the YouTube playlist ID from a URL."""
    if not url:
        return None
    query = urlparse(url)
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if 'list' in parse_qs(query.query):
            return parse_qs(query.query)['list'][0]
    return None

def search_youtube_videos(youtube_service, query, max_results):
    """Searches YouTube and returns a list of video IDs."""
    search_response = youtube_service.search().list(
        q=query,
        part='id',
        type='video',
        maxResults=max_results
    ).execute()
    return [item['id']['videoId'] for item in search_response.get('items', [])]

def get_video_ids_from_playlist(youtube_service, playlist_id):
    """Fetches all video IDs from a given playlist, handling pagination."""
    all_video_ids = []
    next_page_token = None
    while True:
        request = youtube_service.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()
        for item in response.get('items', []):
            all_video_ids.append(item['contentDetails']['videoId'])
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    return all_video_ids

def get_video_metadata(youtube_service, video_ids):
    """Fetches detailed metadata for a list of video IDs."""
    video_details = []
    # Process videos in chunks of 50, which is the API limit
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        video_response = youtube_service.videos().list(
            id=','.join(chunk),
            part='snippet,statistics,contentDetails'
        ).execute()
        for video in video_response.get('items', []):
            snippet = video.get('snippet', {})
            stats = video.get('statistics', {})
            content_details = video.get('contentDetails', {})
            details = {
                'Video ID': video.get('id'),
                'Title': snippet.get('title'),
                'Published Date': snippet.get('publishedAt', '').split('T')[0],
                'Channel Title': snippet.get('channelTitle'),
                'Duration': content_details.get('duration'),
                'Thumbnail URL': snippet.get('thumbnails', {}).get('default', {}).get('url'),
                'View Count': int(stats.get('viewCount', 0)),
                'Like Count': int(stats.get('likeCount', 0))
            }
            video_details.append(details)
    return video_details

# --- Streamlit User Interface ---
st.set_page_config(page_title="YouTube Metadata Finder", layout="wide")
st.title("🎬 YouTube Metadata Finder")
st.write("This app searches YouTube, fetches data from URLs, or gets all videos from a playlist.")

st.sidebar.header("Configuration")
if not API_KEY:
    API_KEY = st.sidebar.text_input("Enter your YouTube API Key:", type="password")

st.sidebar.markdown("---")
input_mode = st.sidebar.radio(
    "Choose your input method:",
    ("Search by Keyword", "Fetch by Individual URLs", "Fetch Entire Playlist")
)

video_ids_to_fetch = []
if input_mode == "Search by Keyword":
    search_query = st.sidebar.text_input("Enter your search query:", "Live satellite launch")
    max_results = st.sidebar.slider("Number of videos to fetch:", 5, 50, 10)
elif input_mode == "Fetch by Individual URLs":
    urls_input = st.sidebar.text_area(
        "Paste YouTube Video URLs (one per line):",
        placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://youtu.be/another-video-id",
        height=150
    )
else: # "Fetch Entire Playlist"
    playlist_url = st.sidebar.text_input("Paste YouTube Playlist URL:")

if st.sidebar.button("Get Metadata"):
    if not API_KEY:
        st.error("❌ Please enter your YouTube API Key in the sidebar to proceed.")
    else:
        try:
            youtube_service = build('youtube', 'v3', developerKey=API_KEY)
            if input_mode == "Search by Keyword":
                if not search_query:
                    st.warning("Please enter a search query.")
                else:
                    with st.spinner("Searching for videos..."):
                        video_ids_to_fetch = search_youtube_videos(youtube_service, search_query, max_results)
            elif input_mode == "Fetch by Individual URLs":
                if not urls_input:
                    st.warning("Please paste at least one YouTube URL.")
                else:
                    urls = urls_input.strip().splitlines()
                    with st.spinner(f"Extracting Video IDs from {len(urls)} URLs..."):
                        video_ids_to_fetch = [extract_video_id_from_url(url) for url in urls if url]
                        video_ids_to_fetch = [vid for vid in video_ids_to_fetch if vid]
                        st.info(f"Found {len(video_ids_to_fetch)} valid YouTube Video IDs.")
            else: # "Fetch Entire Playlist"
                if not playlist_url:
                    st.warning("Please paste a playlist URL.")
                else:
                    playlist_id = extract_playlist_id_from_url(playlist_url)
                    if not playlist_id:
                        st.error("Could not find a valid Playlist ID in the URL. Please check the link.")
                    else:
                        with st.spinner("Fetching all video IDs from the playlist..."):
                            video_ids_to_fetch = get_video_ids_from_playlist(youtube_service, playlist_id)
            
            if not video_ids_to_fetch:
                st.warning("No videos found to fetch. Please check your input.")
            else:
                st.info(f"Found {len(video_ids_to_fetch)} videos. Now fetching metadata...")
                with st.spinner(f"Fetching metadata... (This uses API quota)"):
                    metadata = get_video_metadata(youtube_service, video_ids_to_fetch)
                
                if not metadata:
                    st.error("Could not retrieve metadata. The videos may be private or deleted.")
                else:
                    st.success("✅ Metadata collection complete!")
                    df = pd.DataFrame(metadata)
                    st.dataframe(
                        df,
                        column_config={
                            "Thumbnail URL": st.column_config.ImageColumn("Thumbnail", help="The video's thumbnail image")
                        },
                        hide_index=True
                    )
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download data as CSV",
                        data=csv,
                        file_name="youtube_metadata.csv",
                        mime='text/csv',
                    )
        except Exception as e:
            st.error(f"An error occurred. It could be an invalid API key, a private playlist, or a network issue.")
            st.error(f"Error details: {e}")