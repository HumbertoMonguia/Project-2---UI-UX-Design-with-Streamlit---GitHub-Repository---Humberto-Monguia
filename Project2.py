import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from geopy.geocoders import Nominatim

# Spotify API
CLIENT_ID = 'c307e75327364184b9e268735b442f1f'
CLIENT_SECRET = '763051cd428d4a389cbe91288f1c5e5f'
auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

# Geocoder
geolocator = Nominatim(user_agent="artist-origin-locator")

# Streamlit UI
st.markdown("<h1 style='text-align: center;'>Artist and Song Explorer</h1>", unsafe_allow_html=True)
st.sidebar.title("Search Settings")
artist_name = st.sidebar.text_input("Artist Name:")
num_songs = st.sidebar.slider("Number of Songs", min_value=1, max_value=10, value=5)
chart_style = st.sidebar.segmented_control("Choose Popularity Chart Style:", ["Line", "Area", "Bar"])
duration_chart_style = st.sidebar.radio("Choose Duration Chart Style:", ["Line", "Area", "Bar"])
show_origin = st.sidebar.checkbox("Show Artist Origin")
search = st.sidebar.button("Search Information")

# Function To Get Top Tracks
def get_artist_top_tracks(artist, limit):
    results = sp.search(q=artist, type='artist', limit=1)
    if not results['artists']['items']:
        return None, None, None

    artist_data = results['artists']['items'][0]
    artist_id = artist_data['id']
    image_url = artist_data['images'][0]['url'] if artist_data['images'] else None

    top_tracks = sp.artist_top_tracks(artist_id)

    songs = []
    for track in top_tracks['tracks'][:limit]:
        album = track['album']
        duration_ms = track['duration_ms']
        duration_min = round(duration_ms / 60000, 2)  # Convert ms to minutes as float

        songs.append({
            "Song": track['name'],
            "Album": album['name'],
            "Release Date": album['release_date'],
            "Duration (min)": duration_min,
            "Popularity": track['popularity'],
        })

    return pd.DataFrame(songs), artist_data['name'], image_url

# Function To Get Origin Location
def get_artist_origin_location_musicbrainz(artist_name):
    try:
        response = requests.get(
            "https://musicbrainz.org/ws/2/artist/",
            params={
                'query': f'artist:{artist_name}',
                'fmt': 'json',
                'limit': 1
            },
            headers={'User-Agent': 'ArtistExplorerApp/1.0 (your-email@example.com)'}
        )
        response.raise_for_status()
        data = response.json()

        if not data['artists']:
            return None, None, None

        artist = data['artists'][0]
        area = artist.get('area', {}).get('name')

        if not area:
            return None, None, None

        location = geolocator.geocode(area)
        if location:
            return location.latitude, location.longitude, area

    except Exception as e:
        print(f"MusicBrainz error: {e}")
    return None, None, None

# Main Function
if search and artist_name:
    with st.spinner("Fetching data from Spotify..."):
        data, artist_display_name, image_url = get_artist_top_tracks(artist_name, num_songs)

    if data is None or data.empty:
        st.sidebar.error("❌ No artist found. Please check the spelling.")
    else:
        st.sidebar.success(f"✅ Top {num_songs} tracks for **{artist_display_name}** found!")

        if image_url:
            st.markdown(f"<div style='text-align: center;'><img src='{image_url}' width='250'></div>",
                        unsafe_allow_html=True)

        st.markdown(f"<h3 style='text-align: center;'>Top {num_songs} Tracks by {artist_display_name}</h3>",
                    unsafe_allow_html=True)

        st.dataframe(data)

        # Display Popularity Chart
        st.info(f"Popularity of **{artist_display_name}**'s Top {num_songs} Songs")
        popularity_data = data.set_index("Song")["Popularity"]
        if chart_style == "Line":
            st.line_chart(popularity_data)
        elif chart_style == "Area":
            st.area_chart(popularity_data)
        elif chart_style == "Bar":
            st.bar_chart(popularity_data)

        # Display Duration Chart
        st.info(f"Duration of **{artist_display_name}**'s Top {num_songs} Songs")
        duration_data = data.set_index("Song")["Duration (min)"]
        if duration_chart_style == "Line":
            st.line_chart(duration_data)
        elif duration_chart_style == "Area":
            st.area_chart(duration_data)
        elif duration_chart_style == "Bar":
            st.bar_chart(duration_data)

        # Show Artist Origin
        if show_origin:
            with st.spinner("Looking up artist origin via MusicBrainz..."):
                lat, lon, loc_name = get_artist_origin_location_musicbrainz(artist_display_name)

            if lat and lon:
                st.info(f"Origin of **{artist_display_name}**: {loc_name}")
                st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}))
            else:
                st.warning("⚠️ Couldn't find origin info from MusicBrainz.")
else:
    st.markdown(
        "<p style='text-align: center;'>Enter an artist name and press <strong>Search Information</strong> to begin</p>",
        unsafe_allow_html=True
    )