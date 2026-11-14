# Written with Super Intelligence (SI) assistance.
"""Narration for the opening story, one clip per beat, in a synthetic voice.

Reads the beats from app/public/story/narration.json: each beat is a list of sentences with the
pause between them in seconds, as ["First sentence.", 0.6, "Second sentence."]. Every sentence
is voiced on its own and the pauses are real silence, joined with ffmpeg. Pause tags inside
the text are not used: the speech model turns them into hesitation noises.

Writes voice/beat-<n>.mp3 beside the file. A beat whose text and settings have not changed is
kept (delete the clip to force it). The voice is a synthetic copy of a team member's own voice,
made with ElevenLabs with their consent, and is logged in submission/si_use/.

The key and the voice are read from the environment and are never written to the repository:

    ELEVENLABS_API_KEY=... ELEVENLABS_VOICE_ID=... python app/scripts/make_story_voice.py --story app/public/story

Needs ffmpeg.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import certifi
import requests

MODEL = "eleven_multilingual_v2"
# A little slower than the default, so sentences do not run into each other.
SETTINGS = {"stability": 0.55, "similarity_boost": 0.8, "style": 0.1, "use_speaker_boost": True, "speed": 0.86}
RATE = 44100


def speak(text, before, after, key, voice):
    """One sentence as raw 16-bit mono samples. The sentences around it are given so the tone carries across."""
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}", params={"output_format": "mp3_44100_128"},
                      headers={"xi-api-key": key},
                      json={"text": text, "model_id": MODEL, "voice_settings": SETTINGS, "previous_text": before, "next_text": after},
                      timeout=180, verify=certifi.where())
    if r.status_code != 200:
        raise SystemExit(f"HTTP {r.status_code} from the speech service")      # the body may name the account, so it is not printed
    decoded = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "pipe:1"],
                             input=r.content, capture_output=True, check=True)
    return decoded.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--story", required=True, type=Path, help="folder with narration.json")
    a = p.parse_args()
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        raise SystemExit("set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the environment")
    beats = json.loads((a.story / "narration.json").read_text())
    out = a.story / "voice"
    out.mkdir(exist_ok=True)
    marks_file = out / "made.json"          # which text and settings each clip was made from
    marks = json.loads(marks_file.read_text()) if marks_file.exists() else {}
    for n, beat in enumerate(beats, start=1):
        clip = out / f"beat-{n}.mp3"
        mark = hashlib.sha256((json.dumps(beat) + json.dumps(SETTINGS, sort_keys=True) + MODEL).encode()).hexdigest()[:16]
        if clip.exists() and marks.get(clip.name) == mark:
            print(f"{clip.name}: kept")
            continue
        sentences = [part for part in beat if isinstance(part, str)]
        samples = b""
        for part in beat:
            if isinstance(part, str):
                k = sentences.index(part)
                samples += speak(part, " ".join(sentences[:k]), " ".join(sentences[k + 1:]), key, voice)
            else:
                samples += b"\x00\x00" * round(RATE * float(part))
        with tempfile.NamedTemporaryFile(suffix=".pcm") as raw:
            raw.write(samples)
            raw.flush()
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", raw.name,
                            "-af", "afade=t=in:d=0.03,areverse,afade=t=in:d=0.08,areverse", "-codec:a", "libmp3lame", "-b:a", "128k", str(clip)], check=True)
        marks[clip.name] = mark
        print(f"{clip.name}: {len(sentences)} sentences, {len(samples) / 2 / RATE:.1f} s")
    marks_file.write_text(json.dumps(marks, indent=1) + "\n")


if __name__ == "__main__":
    main()
