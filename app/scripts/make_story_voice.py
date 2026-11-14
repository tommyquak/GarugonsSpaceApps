# Written with Super Intelligence (SI) assistance.
"""Narration for the opening story, one clip per beat, in a synthetic voice.

Reads the lines from app/public/story/narration.json and writes voice/beat-<n>.mp3 beside it.
The voice is a synthetic copy of a team member's own voice, made with ElevenLabs with their
consent; the app says so wherever the sound can be switched on. A clip that already exists is
kept, so changing one line only remakes that clip (delete the file to force it).

The key and the voice are read from the environment and are never written to the repository:

    ELEVENLABS_API_KEY=... ELEVENLABS_VOICE_ID=... python app/scripts/make_story_voice.py --story app/public/story
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import certifi
import requests

MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--story", required=True, type=Path, help="folder with narration.json")
    a = p.parse_args()
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        raise SystemExit("set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the environment")
    lines = json.loads((a.story / "narration.json").read_text())
    out = a.story / "voice"
    out.mkdir(exist_ok=True)
    marks_file = out / "made.json"          # which text each clip was made from
    marks = json.loads(marks_file.read_text()) if marks_file.exists() else {}
    for n, text in enumerate(lines, start=1):
        clip, mark = out / f"beat-{n}.mp3", hashlib.sha256(text.encode()).hexdigest()[:16]
        if clip.exists() and marks.get(clip.name) == mark:
            print(f"{clip.name}: kept")
            continue
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}", params={"output_format": "mp3_44100_128"},
                          headers={"xi-api-key": key}, json={"text": text, "model_id": MODEL, "voice_settings": SETTINGS},
                          timeout=180, verify=certifi.where())
        if r.status_code != 200:
            raise SystemExit(f"{clip.name}: HTTP {r.status_code}")      # the body may name the account, so it is not printed
        clip.write_bytes(r.content)
        marks[clip.name] = mark
        print(f"{clip.name}: {len(r.content) / 1000:.0f} kB")
    marks_file.write_text(json.dumps(marks, indent=1) + "\n")


if __name__ == "__main__":
    main()
