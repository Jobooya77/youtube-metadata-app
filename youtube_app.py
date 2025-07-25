# ==============================================================================
#                      YOUTUBE METADATA FINDER - STREAMLIT APP
# ==============================================================================
# Required libraries: streamlit, google-api-python-client, pandas
# To install them, run this in your terminal:
# pip install streamlit google-api-python-client pandas
#
# To run the app, navigate to this folder in your terminal and type:
# streamlit run youtube_app.py
# ==============================================================================

import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import os

# --- YouTube API and Core Functions ---

# IMPORTANT: It's highly recommended to set your API key as an environment variable
# for security. But for simplicity, you can also paste it directly here.
# To set an environment variable in Windows Command Prompt:
# setx YOUTUBE_API_KEY "YourActualApiKeyHere" 
# (You'll need to restart the terminal after setting it for the first time)
API_KEY = os.environ.get('YOUTUBE_API_KEY', '') # Tries to get the key from environment variables

# --- Utility Functions (from our previous script) ---

def search_youtube_videos(youtube_service, query, max_results):
    """Searches YouTube and returns a list of video IDs."""
    search_response = youtube_service.search().list(
        q=query,
        part='id',
        type='video',
        maxResults=max_results
    ).execute()
    
    return [item['id']['videoId'] for item in search_response.get('items', [])]

def get_video_metadata(youtube_service, video_ids):
    """Fetches detailed metadata for a list of video IDs."""
    video_response = youtube_service.videos().list(
        id=','.join(video_ids),
        # Note: We already ask for 'snippet' which contains thumbnails, so no change is needed here.
        part='snippet,statistics,recordingDetails,contentDetails'
    ).execute()
    
    video_details = []
    for video in video_response.get('items', []):
        snippet = video.get('snippet', {})
        stats = video.get('statistics', {})
        # We don't need location anymore, but it's okay to leave these lines.
        recording_details = video.get('recordingDetails', {})
        location = recording_details.get('location', {})
        content_details = video.get('contentDetails', {})

        # This is the dictionary that defines our final table columns.
        details = {
            'Video ID': video.get('id'),
            'Title': snippet.get('title'),
            'Published Date': snippet.get('publishedAt', '').split('T')[0],
            'Channel Title': snippet.get('channelTitle'),
            'Duration': content_details.get('duration'),
            'Thumbnail URL': snippet.get('thumbnails', {}).get('default', {}).get('url'), # <-- ADDED
            'View Count': int(stats.get('viewCount', 0)),
            'Like Count': int(stats.get('likeCount', 0))
            # Comment Count, Latitude, and Longitude have been removed.
        }
        video_details.append(details)
        
    return video_details

# --- Streamlit User Interface ---

# Set the page title and layout
st.set_page_config(page_title="YouTube Metadata Finder", layout="wide")

# App Title
st.title("🎬 YouTube Metadata Finder")
st.write("This app searches YouTube for videos and collects their public metadata.")

# Sidebar for API Key and Inputs
st.sidebar.header("Configuration")

# Allow user to paste their API key if it's not set as an environment variable
if not API_KEY:
    API_KEY = st.sidebar.text_input("Enter your YouTube API Key:", type="password")

# Input fields in the sidebar
search_query = st.sidebar.text_input("Enter your search query:", "Live satellite launch")
max_results = st.sidebar.slider("Number of videos to fetch:", 5, 50, 10)

# Main "Run" button
if st.sidebar.button("Search and Collect Metadata"):
    if not API_KEY:
        st.error("❌ Please enter your YouTube API Key in the sidebar to proceed.")
    else:
        try:
            # Create a YouTube resource object to be used by the functions
            youtube_service = build('youtube', 'v3', developerKey=API_KEY)
            
            with st.spinner("1/2 - Searching for videos..."):
                ids = search_youtube_videos(youtube_service, search_query, max_results)
            
            if not ids:
                st.warning("No videos found for that query. Please try another search term.")
            else:
                with st.spinner(f"2/2 - Found {len(ids)} videos. Fetching metadata..."):
                    metadata = get_video_metadata(youtube_service, ids)
                
                st.success("✅ Metadata collection complete!")
                
                # Display the data in an interactive table
                df = pd.DataFrame(metadata)
                st.dataframe(df)
                
                # --- Download Button ---
                # Convert DataFrame to CSV format for download
                csv = df.to_csv(index=False).encode('utf--8')
                
                st.download_button(
                    label="📥 Download data as CSV",
                    data=csv,
                    file_name=f"{search_query.replace(' ', '_')}_metadata.csv",
                    mime='text/csv',
                )

        except Exception as e:
            st.error(f"An error occurred. It could be an invalid API key or a network issue.")
            st.error(f"Error details: {e}")

st.sidebar.markdown("---")
st.sidebar.info("This app uses the YouTube Data API v3. Your API key is required to make requests.")