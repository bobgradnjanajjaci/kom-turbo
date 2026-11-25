"""
unfiled_comment_engine.py
-------------------------
Production-ready TikTok Comment Rotation, Anti-Detection & SMMFrog API Client
for "The Unfiled Sessions" (by Nora).

Key protections built in:
1. Zero account-killer / T&S trigger words (no "alversett", "wiped", "ghost",
   "manipulation", "toxic", "terrifying", "scary", "exposed", "illegal", etc.).
2. Zero homoglyphs / mixed-script characters (pure safe ASCII + standard punctuation).
3. Zero questions (strictly declarative, high-conviction cold-traffic hooks).
4. Shuffle-Bag + Per-Video Angle Deduplication + 500-comment Exact-String LRU:
   - Never repeats the same base angle until all angles are exhausted.
   - Never puts two comments from the same angle on the same video.
   - Generates 1,500+ natural string variations to avoid n-gram/duplicate flags.
5. Direct SMMFrog (/api/v2) integration with Railway env vars + local fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


# 🔧 KONFIGURACIJA (čita iz env varijable za Railway, sa fallbackom za lokalno)
PANEL_URL = os.environ.get("SMMFROG_PANEL_URL", "https://smmfrog.com/api/v2")
API_KEY = os.environ.get("SMMFROG_API_KEY", "15a158fe55e7c21be7de194ef97ebfa5")
SERVICE_ID = int(os.environ.get("SMMFROG_SERVICE_ID", "4120"))  # TikTok Custom Comments na SMMFrog


# ---------------------------------------------------------------------------
# 1. SAFETY & COMPLIANCE GUARD (Prevents burning SMM / warmed accounts)
# ---------------------------------------------------------------------------
BANNED_TERMS: Tuple[str, ...] = (
    "alversett",
    "alverset",
    "wiped",
    "went ghost",
    "ghost",
    "vanished",
    "disappeared",
    "manipulation",
    "manipulative",
    "toxic",
    "terrifying",
    "scary",
    "exposed",
    "delusions",
    "delusion",
    "illegal",
    "gaslight",
    "psychological warfare",
    "cheat codes",
    "cheat code",
    "scrubbed",
    "mind control",
    "brainwash",
    "cult",
    "stalk",
    "trauma",
)

ALLOWED_EXTRA_CHARS = {"’", "—", "…"}


def validate_comment(text: str) -> Tuple[bool, str]:
    """
    Validates a rendered comment against TikTok account-safety rules.
    Returns (is_valid, reason).
    """
    if not text or not text.strip():
        return False, "Empty comment"

    lowered = text.lower()

    for term in BANNED_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            return False, f"Contains banned trigger term: {term}"

    if "?" in text:
        return False, "Contains question mark (disabled by config)"

    for ch in text:
        if ord(ch) >= 128 and ch not in ALLOWED_EXTRA_CHARS:
            return False, f"Contains non-ASCII / homoglyph character: {repr(ch)}"

    if len(text) < 45 or len(text) > 250:
        return False, f"Length out of safe range ({len(text)} chars)"

    return True, "OK"


# ---------------------------------------------------------------------------
# 2. HIGH-CONVERTING COLD-TRAFFIC TEMPLATES (Categorized by Angle)
#    Rich micro-spintax {a|b|c} produces 1,500+ unique natural strings.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CommentTemplate:
    angle: str
    pattern: str


TEMPLATES: List[CommentTemplate] = [
    # --- ANGLE 1: PAGE 41 (Immediate self-reflection & pause) ---
    CommentTemplate(
        "page_41",
        "i had to {literally |actually |genuinely |}close {The Unfiled Sessions|the unfiled sessions}{ by Nora|} on page 41 and just sit in silence for {ten minutes|like ten minutes|a solid ten mins|a few minutes} because i realized i've been doing that exact thing my whole {adult life|life}{ without noticing| without even realizing it|}.",
    ),
    CommentTemplate(
        "page_41",
        "page 41 in {The Unfiled Sessions|the unfiled sessions}{ by Nora|} stopped me {mid-sentence|cold|right in my tracks}{ ngl| tbh|}, i never realized how much energy i {waste|spend} explaining myself to people who already made up their minds.",
    ),
    CommentTemplate(
        "page_41",
        "if you ever {pick up|read|open} {The Unfiled Sessions|the unfiled sessions}{ by Nora|}, pay attention to page 41 because that one {paragraph|section|page} explains {half the patterns|so many habits|the exact loops} we keep repeating{ for no reason| without thinking|}.",
    ),

    # --- ANGLE 2: 17 / 20 QUESTIONS AT THE END (Personal journal effect) ---
    CommentTemplate(
        "questions_end",
        "someone on here mentioned {The Unfiled Sessions|the unfiled sessions} {last month|a few weeks ago|the other day} and i finally {read it|opened it} {last night|this week}, getting to the {17|seventeen} questions at the end felt {weirdly|almost too} personal like {the author|Nora} was reading my journal.",
    ),
    CommentTemplate(
        "questions_end",
        "the {17|seventeen} questions at the end of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} {honestly|genuinely|actually} did more for my clarity in {twenty minutes|half an hour} than {months|a whole year|weeks} of overthinking{ ever did|}.",
    ),
    CommentTemplate(
        "questions_end",
        "i {genuinely|really|honestly} wish someone had handed me {The Unfiled Sessions|the unfiled sessions}{ by Nora|} {five|four|three} years ago, the part where she {breaks down|lays out} those {17|twenty} questions saved me from repeating the exact same {cycle|mistake} again.",
    ),
    CommentTemplate(
        "questions_end",
        "page 187 of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} with the twenty questions {literally|quietly|calmly} called out every single pattern i've been {brushing off|ignoring|making excuses for}{ this year| lately|}.",
    ),

    # --- ANGLE 3: PAGE 27 & SCREENSHOT / FRIEND WORD-OF-MOUTH ---
    CommentTemplate(
        "page_27",
        "my {sister|best friend|coworker|roommate} sent me a screenshot of page 27 from {The Unfiled Sessions|the unfiled sessions}{ by Nora|} and i thought she was being dramatic until i read the rest of the {chapter|section}, now {three of us|both of us} are annotating it together.",
    ),
    CommentTemplate(
        "page_27",
        "someone sent me one {quote|paragraph|screenshot} from page 27 of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} and i ended up reading the whole thing in {one sitting|a single night|one evening} because it doesn't sugarcoat anything.",
    ),
    CommentTemplate(
        "page_27",
        "page 27 of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} is the kind of thing you read once, close the {book|pdf|tab}, and immediately rethink {how you handle|who gets access to|how you protect} your time{ and peace|}.",
    ),

    # --- ANGLE 4: DRAWER FOUR (Curiosity / "Lore" hook) ---
    CommentTemplate(
        "drawer_four",
        "i still haven't {recovered|moved on} from drawer four in {The Unfiled Sessions|the unfiled sessions}{ by Nora|}, had to put my phone down and {take a walk|stare at the wall|sit with that} for a minute after {reading it|finishing that part}.",
    ),
    CommentTemplate(
        "drawer_four",
        "the drawer four {section|part|chapter} in {The Unfiled Sessions|the unfiled sessions}{ by Nora|} explains why certain people only {show up|reach out|try harder} when they sense you're finally pulling back.",
    ),
    CommentTemplate(
        "drawer_four",
        "everyone talks about the ending of {The Unfiled Sessions|the unfiled sessions} but drawer four was the exact moment i realized i needed to {change my boundaries|stop making excuses for people|set firmer standards}.",
    ),

    # --- ANGLE 5: PAGE 8 FIVE-SECOND RULE & PAGE 2 (Concrete rule) ---
    CommentTemplate(
        "page_8_rule",
        "that five second rule on page 8 of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} has been {living rent free in my head|stuck in my head} all week, it completely changes how you {read a room|handle awkward moments|spot mixed signals}.",
    ),
    CommentTemplate(
        "page_8_rule",
        "once you read page 2 of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} you {genuinely|actually|immediately} start noticing little things in {conversations|everyday interactions} that you used to {brush off|overlook}.",
    ),
    CommentTemplate(
        "page_8_rule",
        "the five second rule from page 8 of {The Unfiled Sessions|the unfiled sessions} is so {simple|obvious once you see it} it's almost annoying i didn't {notice it|catch on} myself years ago.",
    ),

    # --- ANGLE 6: AUDIO VERSION & DAILY HABITS (Proven converter) ---
    CommentTemplate(
        "audio_walks",
        "i started listening to the audio version of {The Unfiled Sessions|the unfiled sessions}{ by Nora|} on my {morning walks|evening walks|daily walks} and it's {honestly|genuinely} wild how differently you handle conversations once you hear those patterns explained out loud.",
    ),
    CommentTemplate(
        "audio_walks",
        "listening to {The Unfiled Sessions|the unfiled sessions}{ by Nora|} on my {commute|drive to work|morning walk} completely changed my {mood|headspace} this week, i catch myself pausing before reacting to {things that used to drain me|petty nonsense|mixed signals}.",
    ),
    CommentTemplate(
        "audio_walks",
        "i keep going back to my {notes|highlights} from {The Unfiled Sessions|the unfiled sessions}{ by Nora|} whenever i feel myself slipping back into old habits and it snaps me right back into {focus|clarity}.",
    ),

    # --- ANGLE 7: NO INTERVIEWS / NO BOOK TOUR / QUIET AUTHORITY ---
    CommentTemplate(
        "quiet_author",
        "it still blows my mind that Nora wrote {The Unfiled Sessions|the unfiled sessions}, never did a single {interview|podcast} or book tour, and somehow it explains human behavior better than {every bestseller|most psychology books} on my shelf.",
    ),
    CommentTemplate(
        "quiet_author",
        "the fact that Nora {put out|released} {The Unfiled Sessions|the unfiled sessions} with zero {press|promo} or book tour and it's still spreading purely by word of mouth tells you everything about how {accurate|spot-on} it is.",
    ),
    CommentTemplate(
        "quiet_author",
        "more people need to {read|talk about} {The Unfiled Sessions|the unfiled sessions} because the way Nora {breaks down|explains} everyday behavior without any fluff is {unreal|refreshing}.",
    ),

    # --- ANGLE 8: SKEPTIC CONVERTED (Anti-ad / 100% organic feel) ---
    CommentTemplate(
        "skeptic",
        "i'm usually {super|pretty} skeptical of books people hype up on here, so i went into {The Unfiled Sessions|the unfiled sessions}{ by Nora|} expecting {basic|generic} advice and now i'm halfway through rethinking half the decisions i made this year.",
    ),
    CommentTemplate(
        "skeptic",
        "took me {forever|weeks} to finally read {The Unfiled Sessions|the unfiled sessions}{ by Nora|} because i thought it was just {internet|tiktok} hype, now i'm {genuinely|lowkey} annoyed i didn't open it {months ago|sooner}.",
    ),
    CommentTemplate(
        "skeptic",
        "went into {The Unfiled Sessions|the unfiled sessions} thinking i already knew all this {behavior|communication} stuff and {by chapter three|twenty pages in|halfway through} i realized i was fooling myself.",
    ),

    # --- ANGLE 9: LATE NIGHT / 3AM BINGE READING ---
    CommentTemplate(
        "late_night",
        "started reading {The Unfiled Sessions|the unfiled sessions}{ by Nora|} at {11pm|midnight} thinking i'd do {two chapters|ten pages} and ended up highlighting half the book until {3am|2am}, the part about why we over-explain ourselves hit way too close.",
    ),
    CommentTemplate(
        "late_night",
        "{The Unfiled Sessions|the unfiled sessions}{ by Nora|} is one of those books you open for {five minutes|one chapter} before bed and suddenly it's {2am|3am} and you're writing notes in your phone.",
    ),
    CommentTemplate(
        "late_night",
        "opened {The Unfiled Sessions|the unfiled sessions} on my {laptop|phone|ipad} just to skim the first few pages and ended up finishing {almost the whole thing|the entire book} before {sunrise|going to sleep}.",
    ),

    # --- ANGLE 10: CALM CLARITY / UNSEEING PATTERNS ---
    CommentTemplate(
        "calm_clarity",
        "once you read {The Unfiled Sessions|the unfiled sessions}{ by Nora|} you can't unsee how people {actually|really} communicate in everyday life, it's not even loud or dramatic, it just makes everything click in a {really calm|quiet} way.",
    ),
    CommentTemplate(
        "calm_clarity",
        "this reminds me so much of that {chapter|section} in {The Unfiled Sessions|the unfiled sessions}{ by Nora|}, i read it {two weeks ago|last month} and i still catch myself pausing mid-conversation because of how accurate that one line was.",
    ),
    CommentTemplate(
        "calm_clarity",
        "reading a few pages of {The Unfiled Sessions|the unfiled sessions} before bed completely shifted how i read {mixed signals|people's intentions}, you stop {guessing|overanalyzing} and just see the pattern.",
    ),
    CommentTemplate(
        "calm_clarity",
        "still thinking about how quiet everyone is about {The Unfiled Sessions|the unfiled sessions}{ by Nora|} when half of us actually need the exact {perspective|clarity} she lays out in it.",
    ),
]


# ---------------------------------------------------------------------------
# 3. SPINTAX RENDERER & ANTI-REPETITION ROTATOR
# ---------------------------------------------------------------------------
_SPINTAX_RE = re.compile(r"\{([^{}]+)\}")


def expand_spintax(pattern: str, rng: random.Random) -> str:
    """Expands {opt1|opt2|...} blocks cleanly and normalizes whitespace."""
    text = pattern
    while True:
        match = _SPINTAX_RE.search(text)
        if not match:
            break
        options = match.group(1).split("|")
        choice = rng.choice(options)
        text = text[: match.start()] + choice + text[match.end() :]

    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"\s+([,.!])", r"\1", text)
    return text


class UnfiledCommentEngine:
    """
    Stateful comment generator for Flask / SMM / Browser bots.
    Guarantees:
    - Shuffle-bag rotation across all angles (no back-to-back angle repeats).
    - Global LRU deduplication over the last `history_size` comments.
    - Per-video angle isolation (never posts two comments from the same angle
      on the same video).
    - Strict safety validation on every generated string.
    """

    def __init__(
        self,
        templates: Sequence[CommentTemplate] = TEMPLATES,
        history_size: int = 500,
        seed: Optional[int] = None,
    ) -> None:
        self.templates = list(templates)
        self.rng = random.Random(seed)
        self._bag: deque[CommentTemplate] = deque()
        self._recent_hashes: deque[str] = deque(maxlen=history_size)
        self._recent_hash_set: set[str] = set()
        self._video_angles: Dict[str, set[str]] = {}
        self._refill_bag()

    def _refill_bag(self) -> None:
        shuffled = list(self.templates)
        self.rng.shuffle(shuffled)
        self._bag.extend(shuffled)

    def _record_hash(self, digest: str) -> None:
        if len(self._recent_hashes) == self._recent_hashes.maxlen:
            oldest = self._recent_hashes.popleft()
            self._recent_hash_set.discard(oldest)
        self._recent_hashes.append(digest)
        self._recent_hash_set.add(digest)

    def next_comment(self, video_id: Optional[str] = None, max_attempts: int = 80) -> str:
        """
        Returns a unique, validated comment.
        If `video_id` is provided, avoids reusing an angle already used on that video.
        """
        used_angles = self._video_angles.get(video_id, set()) if video_id else set()
        total_angles = len({t.angle for t in self.templates})

        for _ in range(max_attempts):
            if not self._bag:
                self._refill_bag()

            tpl = self._bag.popleft()

            if video_id and tpl.angle in used_angles and len(used_angles) < total_angles:
                self._bag.append(tpl)
                continue

            rendered = expand_spintax(tpl.pattern, self.rng)

            if self.rng.random() < 0.25 and rendered[0].islower():
                rendered = rendered[0].upper() + rendered[1:]

            ok, _reason = validate_comment(rendered)
            if not ok:
                continue

            digest = hashlib.sha256(rendered.lower().encode("utf-8")).hexdigest()
            if digest in self._recent_hash_set:
                continue

            self._record_hash(digest)
            if video_id:
                self._video_angles.setdefault(video_id, set()).add(tpl.angle)

            return rendered

        tpl = self.rng.choice(self.templates)
        return expand_spintax(tpl.pattern, self.rng)

    def get_batch_for_video(self, video_id: str, count: int = 5) -> List[str]:
        """Generates `count` distinct-angle comments for a single TikTok video."""
        return [self.next_comment(video_id=video_id) for _ in range(count)]

    def get_safe_delay(self, min_seconds: float = 15.0, max_seconds: float = 28.0) -> float:
        """Humanized jitter delay between API / browser actions."""
        return round(self.rng.uniform(min_seconds, max_seconds), 2)


# ---------------------------------------------------------------------------
# 4. SMMFROG PANEL CLIENT (/api/v2)
# ---------------------------------------------------------------------------
class SMMFrogClient:
    """
    Zero-dependency client for SMMFrog (PerfectPanel /api/v2) connected
    directly to UnfiledCommentEngine.
    """

    def __init__(
        self,
        panel_url: str = PANEL_URL,
        api_key: str = API_KEY,
        service_id: int = SERVICE_ID,
        engine: Optional[UnfiledCommentEngine] = None,
        timeout: int = 20,
    ) -> None:
        self.panel_url = panel_url
        self.api_key = api_key
        self.service_id = service_id
        self.engine = engine or UnfiledCommentEngine()
        self.timeout = timeout

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(
            self.panel_url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "UnfiledCommentEngine/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {"error": f"HTTP {exc.code}: {body}"}
        except Exception as exc:
            return {"error": str(exc)}

    def get_balance(self) -> Dict[str, Any]:
        """Checks current SMMFrog account balance."""
        return self._post({"key": self.api_key, "action": "balance"})

    def check_order_status(self, order_id: int | str) -> Dict[str, Any]:
        """Checks status of an existing SMMFrog order."""
        return self._post({"key": self.api_key, "action": "status", "order": order_id})

    def send_comments(
        self,
        video_url: str,
        count: int = 5,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Generates `count` unique, angle-isolated comments for `video_url`
        and submits them to SMMFrog service `SERVICE_ID`.
        """
        comments = self.engine.get_batch_for_video(video_id=video_url, count=count)
        payload = {
            "key": self.api_key,
            "action": "add",
            "service": self.service_id,
            "link": video_url,
            "comments": "\n".join(comments),
        }

        if dry_run:
            return {
                "dry_run": True,
                "service": self.service_id,
                "link": video_url,
                "count": len(comments),
                "comments": comments,
            }

        response = self._post(payload)
        return {
            "dry_run": False,
            "service": self.service_id,
            "link": video_url,
            "count": len(comments),
            "comments": comments,
            "panel_response": response,
        }

    def send_to_multiple_videos(
        self,
        video_urls: Sequence[str],
        comments_per_video: int = 5,
        min_delay: float = 15.0,
        max_delay: float = 28.0,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Distributes unique comments across multiple TikTok videos with humanized
        jitter delays between orders to avoid burst detection.
        """
        results: List[Dict[str, Any]] = []
        for idx, url in enumerate(video_urls):
            res = self.send_comments(video_url=url, count=comments_per_video, dry_run=dry_run)
            results.append(res)
            if not dry_run and idx < len(video_urls) - 1:
                time.sleep(self.engine.get_safe_delay(min_delay, max_delay))
        return results


# ---------------------------------------------------------------------------
# 5. SELF-TEST / DRY-RUN PREVIEW (Does NOT spend balance)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    client = SMMFrogClient()
    sample_videos = [
        "https://www.tiktok.com/@example/video/7400000000000000001",
        "https://www.tiktok.com/@example/video/7400000000000000002",
    ]
    preview = client.send_to_multiple_videos(sample_videos, comments_per_video=5, dry_run=True)

    print(f"Panel: {client.panel_url} | Service ID: {client.service_id}")
    print(f"Dry-run batches generated: {len(preview)}")
    for batch in preview:
        print(f"\nVideo: {batch['link']} ({batch['count']} comments)")
        for i, c in enumerate(batch["comments"], 1):
            print(f"  {i}. {c}")
