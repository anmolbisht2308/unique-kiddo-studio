# Unique Kiddo Studio

Makes kid-paced learning Shorts for the **Unique Kiddo** YouTube channel, hosted by Kiddo (an original letter-U mascot).

## Make a video
```bash
./setup.sh                                   # once per fresh machine
python3 engine/render.py episodes/ep003_x.json --preview 3 13 20   # quick look
python3 engine/render.py episodes/ep003_x.json                      # full render
```
Output in `out/<id>/`: `video.mp4`, `thumbnail.png`, `subtitles.srt`, `script.md`, `upload.json`.

## Episode file
```json
{
  "id": "ep003", "format": "shadow | clues | learn | count | letter",
  "title_screen": ["LINE 1", "LINE 2"], "round_word": "ROUND",
  "intro": ["Hello, little friends! I'm Kiddo!", "...", "... Ready?"],
  "items": [ {"name": "Elephant", "say": "an elephant", "emoji": "🐘",
              "hint": "(shadow, optional)", "clues": ["🩺","🌡️"], "clue_text": "A stethoscope and a thermometer",
              "count": 5, "plural": "apples", "fact": "Short, happy fact!"} ],
  "outro_screen": "Great job, friends!\nWhich ... is\nYOUR favourite?",
  "outro": ["Wow! Great job, friends!", "Which ... is your favourite?"],
  "think_seconds": 5, "seo": {"title": "...", "description": "...", "tags": ["..."]}
}
```
- `shadow`: silhouette → think → reveal. Needs `hint`.
- `clues`: two clue emojis → guess who/what → reveal `emoji`. Needs `clues`, `clue_text`.
- `learn`: show item, say name, repeat, fact.
- `letter`: big letter + two picture cards (`emoji` = right answer, `wrong`, `correct_side`), guess which starts with `letter`.
- `count`: N copies of `emoji`, count aloud together. Needs `count`, `plural`.
Every `emoji` must exist in `assets/noto/2D/png/512` (the engine stops with a clear error if not).

## Planning
`content_plan.json` is the topic queue and status log (`todo` → `scheduled` → `published`).

## Credits
Voice: Kokoro TTS (Apache 2.0) via kokoro-onnx (MIT). Phonemes: espeak-ng from Piper. Emoji art: Noto Emoji (Apache 2.0).
Music, sound effects, mascot and scripts are original.

## Pick a Door with Kiddo (`doors` format)
```bash
python3 engine/doors.py episodes/door01_yummy_or_yucky.json --preview 0 11 24   # quick look
python3 engine/doors.py episodes/door01_yummy_or_yucky.json                      # full render (~30 s video)
```
```json
{ "id": "door02", "format": "doors", "series": "Pick a Door with Kiddo",
  "title_screen": ["DON'T PICK THE", "WRONG DOOR!"], "open_order": [0, 1, 2],
  "doors": [ {"emoji": "🍋", "name": "Lemon", "reaction": "sour", "kiddo_line": "Ewww! Sooo sour!",
              "caption": "SO SOUR!", "caption_color": [225,175,20], "line": "A sour lemon! Oops!"},
             {"emoji": "🎂", "name": "Cake", "reaction": "win", "win": true, "kiddo_line": "Yay!", "line": "You win!"} ],
  "outro_line": "Did you pick door number two? Let's play again!", "seo": {...} }
```
Reactions: `sour hot stinky cold wet slip tickle scared buzz bounce sneeze float` (wrong) and `win love` (right).
Kiddo (expressions, squash/stretch) lives in `engine/kiddo_fx.py`; all sound effects are synthesised in `engine/sfx.py`.
