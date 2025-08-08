# backend/main.py
import asyncio
import io
import os
from typing import Union

import aiofiles
import aiohttp
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from pydub import AudioSegment  # pip install pydub
from shazamio import Shazam
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SOUNDCLOUD_CLIENT_ID = os.getenv("SOUNDCLOUD_CLIENT_ID")

if not SOUNDCLOUD_CLIENT_ID:
    print("WARNING: SOUNDCLOUD_CLIENT_ID not set in .env file.  SoundCloud functionality will be limited.")

app = FastAPI()

async def convert_to_mp3(file_content: bytes) -> bytes:
    """Converts any audio to MP3 using pydub."""
    try:
        audio = AudioSegment.from_file(io.BytesIO(file_content))
        mp3_io = io.BytesIO()
        audio.export(mp3_io, format="mp3")
        return mp3_io.getvalue()
    except Exception as e:
        print(f"Error converting to MP3: {e}")
        return None

async def recognize_track(file_content: bytes) -> Union[dict, None]:
    """Recognizes a track using Shazam."""
    try:
        shazam = Shazam()
        # Convert audio to MP3 before recognition
        mp3_content = await convert_to_mp3(file_content)
        if not mp3_content:
            return None

        out = await shazam.recognize(mp3_content)
        if out and 'track' in out:
            return out['track']
        else:
            return None
    except Exception as e:
        print(f"Error recognizing track: {e}")
        return None

async def get_soundcloud_track_info(artist: str, title: str) -> Union[dict, None]:
    """Searches SoundCloud for a track and returns info."""
    if not SOUNDCLOUD_CLIENT_ID:
        print("SOUNDCLOUD_CLIENT_ID is not set. Cannot search SoundCloud.")
        return None

    try:
        search_url = "https://api.soundcloud.com/tracks"
        params = {
            "client_id": SOUNDCLOUD_CLIENT_ID,
            "q": f"{artist} - {title}",  # Improved search query
            "limit": 1,  # Get only the first result
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        track = data[0]
                        return {
                            "title": track["title"],                            "artist": track["user"]["username"],
                            "artwork_url": track["artwork_url"] if track["artwork_url"] else track["user"]["avatar_url"],  # Fallback to user avatar
                            "stream_url": f"{track['stream_url']}?client_id={SOUNDCLOUD_CLIENT_ID}",
                        }
                    else:
                        print(f"No SoundCloud tracks found for '{artist} - {title}'.")
                        return None
                else:
                    print(f"SoundCloud API error: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        print(f"Error searching SoundCloud: {e}")
        return None


@app.post("/recognize")
async def recognize_and_get_info(file: UploadFile = File(...)):
    """Recognizes a track from an audio file and gets SoundCloud info."""
    try:
        file_content = await file.read()
        track_info = await recognize_track(file_content)

        if not track_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not recognized.")

        artist = track_info.get("subtitle", track_info.get("artist", ""))  # Use subtitle or artist
        title = track_info.get("title", "")

        soundcloud_info = await get_soundcloud_track_info(artist, title)

        if not soundcloud_info:
             # Return Shazam data if SoundCloud fails.  Could also log the failure.
            return JSONResponse(content={
                "title": track_info.get("title", "Unknown Title"),
                "artist": artist,
                "artwork_url": track_info.get("images", [{}])[0].get("url", None) if track_info.get("images") else None,  # Shazam image
                "stream_url": None, # No soundcloud stream,
            }, status_code=status.HTTP_200_OK)


        return JSONResponse(content=soundcloud_info, status_code=status.HTTP_200_OK)

    except HTTPException as e:
        raise e # re-raise http exceptions
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.get("/")
async def read_root():
  """Serves the frontend HTML file."""
  return FileResponse("frontend/index.html")