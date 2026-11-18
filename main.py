from flask import Flask, render_template_string, request, jsonify, redirect, url_for, make_response

import requests

import os

import re

import threading

import time

import random

from datetime import datetime

from urllib.parse import urlparse



app = Flask(__name__)



# 🔧 KONFIGURACIJA (čita iz env varijable za Railway, sa fallbackom za lokalno)

PANEL_URL = os.environ.get("SMMFROG_PANEL_URL", "https://smmfrog.com/api/v2")

API_KEY = os.environ.get("SMMFROG_API_KEY", "15a158fe55e7c21be7de194ef97ebfa5")

SERVICE_ID = int(os.environ.get("SMMFROG_SERVICE_ID", "4120"))  # TikTok Custom Comments na SMMFrog (Min: 5)



# 🎯 VARIJACIJE KLJUČNIH RIJEČI (Prirodne greške + razdvajanje da se izbjegne keyword flag)

AUTHOR_VARIANTS = [

    "Nora Alversett",

    "nora alversett",

    "Nora Alverset",

    "Norra Alversett",

    "Norra Alversette",

    "N. Alversett",

    "N. Alversette",

    "Nora.Alversett",

    "Nora Alversette",

    "Nora Alversettt",

    "Nora Alversettte",

    "Nora A.",

]



BOOK_VARIANTS = [

    "The Alversett Effect",

    "the alversett effect",

    "The Alverset Effect",

    "the alverset effect",

    "The Alversett Efect",

    "The Alversett Effectt",

    "Alversett Effect",

    "alversett effect",

    "Alverset Effect",

    "The Alversette Effect",

]



FULL_VARIANTS = [

    "The Alversett Effect by Nora Alversett",

    "the alversett effect by nora alversett",

    "The Alversett Effect by Nora Alversette",

    "the alversett effect by nora alversette",

    "The Alversett Effect by Nora Alverset",

    "the alversett effect by nora alverset",

    "The Alversett Effect by Norra Alversett",

    "The Alversett Effect by Norra Alversette",

    "The Alversett Effect by Nora Alversettte",

    "The Alverset Effect by Nora Alversett",

    "The Alverset Effect by Nora Alversette",

    "the alverset effect by nora alversett",

    "The Alversett Efect by Nora Alversett",

    "The Alversett Efect by Nora Alversette",

    "The Alversett Effectt by Nora Alversett",

    "The Alversett Effectt by Nora Alverset",

    "The Alversette Effect by Nora Alversett",

    "The Alversett Effect - Nora Alversett",

    "The Alversett Effect - Nora Alversette",

    "The Alversett Effect, Nora Alversett",

    "the alversett effect, nora alversett",

    "The Alversett Effect by N. Alversett",

    "The Alversett Effect by N. Alversette",

    "Alversett Effect by Nora Alversett",

    "Alversett Effect by Nora Alverset",

    "The Alversett Effectt by Norra Alversett",

]



# 🎯 22 BLUE-SEARCH VARIJACIJE (Sa Alversette, Alverset, Norra, Effectt - čista latinica za plavu lupu)

BOOK_MENTIONS = (

    "{"

    "The Alversett Effect by Nora Alversett|"

    "the alversett effect by nora alversett|"

    "The Alversett Effect by Nora Alversette|"

    "the alversett effect by nora alversette|"

    "The Alversett Effect by Nora Alverset|"

    "the alversett effect by nora alverset|"

    "The Alversett Effect by Norra Alversett|"

    "The Alversett Effect by Norra Alversette|"

    "The Alversett Effect by Nora Alversettte|"

    "The Alverset Effect by Nora Alversett|"

    "The Alverset Effect by Nora Alversette|"

    "the alverset effect by nora alversett|"

    "The Alversett Efect by Nora Alversett|"

    "The Alversett Efect by Nora Alversette|"

    "The Alversett Effectt by Nora Alversett|"

    "The Alversett Effectt by Nora Alverset|"

    "The Alversette Effect by Nora Alversett|"

    "The Alversett Effect - Nora Alversett|"

    "The Alversett Effect - Nora Alversette|"

    "The Alversett Effect, Nora Alversett|"

    "The Alversett Effect by N. Alversett|"

    "The Alversett Effect by N. Alversette"

    "}"

)



# 🔥 SPINTAX ŠABLONI (Prvobitni šabloni + 30 novih FOMO & Rabbit-Hole šablona)

SPINTAX_TEMPLATES = [

    # --- NOVI COLD TRAFFIC KOMENTARI (visoki CTR & znatiželja) ---

    r"{it’s|it's|its} {actually|genuinely|lowkey|honestly} {scary|insane|wild} how accurate {AUTHOR} is about relationships… i {can't|cant|cannot} unsee how people operate now{| fr}{| tbh}",

    r"reading {BOOK} felt {illegal|unreal|like a cheat code}. everything i thought i knew about attachment and manifesting was {backwards|completely wrong|a lie}{| ngl}{| tbh}",

    r"{AUTHOR} exposed the exact psychology behind why people pull away and now every interaction makes {total |complete |}sense{| fr}{| ngl}",

    r"once {you|u} understand {BOOK} {you|u} {literally|genuinely|actually} stop chasing anyone. the shift in how people treat {you|u} is {unreal|insane|wild}{| tbh}",

    r"i wish i found {AUTHOR} before my last situationship, would've saved me {months|years} of overthinking{| fr}{| ngl}",



    # --- NOVE VARIJACIJE NA ISTU TEMU (kombinacija knjige, autora i efekta znatiželje) ---

    r"{AUTHOR} broke down attachment and silent pulling away so accurately in {BOOK} that it {genuinely|actually|lowkey} gave me chills{| ngl}{| tbh}",

    r"everything {you|u} were told about chasing and manifesting is backwards compared to what {BOOK} explains, {no wonder|that's why} {AUTHOR} went ghost{| fr}",

    r"after reading {BOOK} i {literally|finally} see why people pull away right when things get good… {AUTHOR} {exposed|decoded} the whole pattern{| tbh}{| ngl}",

    r"i thought i was just anxious until {AUTHOR} explained attention dynamics in {BOOK}, now i {cannot|can't} unsee how people move{| fr}",

    r"if {you're|youre|u are} still overthinking someone pulling away, read {BOOK} once and watch how fast your mindset shifts{| tbh}{| ngl}",



    # --- NAJBOLJI POSTOJEĆI ŠABLONI (pročišćeni i razdvojeni za manji keyword footprint) ---

    r"{not me reading|honestly not me finishing|literally me reading} {FULL} in {one sitting|a single night|one go} and {finally |actually |}understanding why {she|the author} {completely |literally |}wiped her digital footprint after {publishing|dropping|releasing} it{| tbh}{| ngl}",

    r"{no therapist or dating coach|literally no dating coach|no relationship coach} ever {explained|broke down} silent mind games the way {BOOK} did, once {you|u} read page {78|13} {you|u} can {never|literally never} look at relationships the same way again{| fr}{| tbh}",

    r"a girl in another comment section {mentioned|put me onto|recommended} {FULL} and now i {see|get|understand} why the author {stays anonymous|never shows her face}, page {114|24} is {honestly |genuinely |}not normal{| ngl}",

    r"i {used to|literally used to} overthink {everything|every little thing} and always give {too|to} much until {someone put me onto|i read|i found} {BOOK}, it {genuinely |honestly |really |}feels like having an unfair advantage in reading people{| tbh}",

    r"once {you|u} read chapter 4 of {BOOK} and see how attention dynamics {actually |really |}work, {you|u} never {wanna|want to} chase anyone or settle for crumbs again{| fr}{| ngl}",

    r"doing the 17 questions inside {BOOK} made me {realize|see} how much {power|energy} i was giving away to people who {didn't|didnt} even deserve my attention{| tbh}{| honestly}",

    r"men are {honestly |genuinely |lowkey |}lucky most women still {haven't|havent} {discovered|found|read} {BOOK} {because|bc} chapter 3 alone {ruins all their delusions|changes the whole dynamic} overnight{| fr}",

    r"i know it sounds {dramatic|crazy|wild} to talk about a book in the comments, but {FULL} flipped a switch in my brain that i {honestly |genuinely |literally |}cannot turn off{| ngl}{| tbh}",

    r"{still |honestly |}crazy to me how {AUTHOR} packed over 200 pages of {pure |raw |}psychology into {BOOK}, broke down every messy relationship pattern, and {vanished|disappeared} without a trace{| fr}",

    r"sometimes a {random |}comment about a book finds {you|u} at the exact moment {you|u} need it, and for me it was {FULL}, people {really |honestly |}{aren't|arent} ready for page 184{| tbh}{| ngl}",

    r"now i {finally |actually |}understand why {AUTHOR} {completely |literally |}disappeared from the internet after {publishing|releasing|dropping} {BOOK}{| tbh}{| fr}",

    r"i {almost |lowkey |}wish i never read {BOOK} {because|bc} once {you|u} see what {AUTHOR} explains on page {78|13} {you|u} can {never|literally never} unsee it{| ngl}",

    r"no influencer or coach ever {explained|exposed} human behavior the way {AUTHOR} did in {BOOK}, i {finally |completely |}get why she went offline after releasing it{| tbh}",

    r"whoever put me onto {FULL} last week thank {you|u} {so|soo} much {because|bc} my overthinking is {literally |honestly |completely |}gone{| fr}{| ngl}",

    r"is {AUTHOR} a real psychologist or what {because|bc} {BOOK} reads people's minds across 200+ pages in a way that is {genuinely |honestly |}{scary|insane|wild}{| ngl}",

    r"i {totally |finally |}get why the author went {completely |}ghost after {releasing|dropping} {BOOK}, page 114 and page 184 called me out {so|soo} badly{| tbh}{| fr}",

    r"once {you|u} do the 17 questions inside {BOOK} {you|u} realize how much {energy|time} {you|u} were wasting on people giving {you|u} crumbs{| ngl}{| tbh}",

    r"the way {BOOK} breaks down attention dynamics in chapter 3 and 4 makes {you|u} never {wanna|want to} chase anyone again{| tbh}{| ngl}",

    r"reading {BOOK} {genuinely |honestly |really |}feels like having an unfair advantage in reading people, chapter 4 is {crazy|wild|unreal}{| ngl}",

    r"whoever recommended {FULL} in the comments last week deserves {everything|the world}, page 184 {literally |genuinely |}changed my life{| fr}{| ngl}",



    # --- 10 "MOJA SESTRA / DRUGARICA / CIMERKA" KOMENTARA (100% prirodno i kad padne muški profil) ---

    rf"my {{older |little |}}sister read {BOOK_MENTIONS} in {{one night|one sitting}}, woke up the next morning and blocked her situationship of 2 years without saying a {{single |}}word{{| tbh}}{{| ngl}}",

    rf"idk what kind of psychology is inside {BOOK_MENTIONS} but my sister made me read page {{78|114}} yesterday and i {{genuinely |honestly |}}haven't stopped thinking about it{{| fr}}",

    rf"my sister went down a 3am rabbit hole reading {BOOK_MENTIONS} and now she spots every {{guy's|person's}} next move weeks before they even make it{{| ngl}}{{| tbh}}",

    rf"watched my {{sister|best friend}} go from stressing over bare minimum texts to completely unbothered in 48 hours after {{our cousin|her friend}} put her onto {BOOK_MENTIONS}{{| fr}}",

    rf"my sister and her friends haven't shut up about {BOOK_MENTIONS} all week so i checked page {{114|78}} myself and yeah... that book is {{actually |genuinely |}}scary{{| ngl}}",

    rf"my {{sister|roommate}} left her copy of {BOOK_MENTIONS} on the table and reading chapter 4 alone made me realize how easily people get played in modern dating{{| tbh}}",

    rf"my sister sent me a screenshot of the 17 questions from {BOOK_MENTIONS} and it {{honestly |literally |}}exposed every messy relationship pattern i've ever seen{{| fr}}{{| ngl}}",

    rf"{{lowkey |honestly |}}crazy how my sister read {BOOK_MENTIONS} once and suddenly stopped overthinking or chasing anyone, chapter 3 {{literally |completely |}}rewired her brain{{| tbh}}",

    rf"my cousin told my sister to google {BOOK_MENTIONS} before it gets {{scrubbed|taken down}} again and they stayed up till 4am dissecting page {{184|114}}{{| ngl}}",

    rf"if {{you|u}} wanna see someone wake up overnight tell them to read {BOOK_MENTIONS}, my sister finished it on sunday and her standards did a complete 180{{| fr}}{{| tbh}}",



    # --- 10 "RABBIT HOLE & ZABRANJENA PSIHOLOGIJA" KOMENTARA (Rodno neutralni, jak FOMO) ---

    rf"{{went down a 3am rabbit hole reading|stayed up till 4am finishing}} {BOOK_MENTIONS} and now i {{finally |}}understand why the author wiped her entire digital footprint right after dropping it{{| tbh}}{{| ngl}}",

    rf"{{does anyone actually know|wait does anyone know}} who the author really is {{because|bc}} {BOOK_MENTIONS} reads like classified behavioral psychology and then she just vanished from the internet{{| ngl}}",

    rf"{{nobody talks about how|it is actually wild how}} {BOOK_MENTIONS} breaks down the exact micro-pullback method people use before they distance themselves, page {{78|114}} is crazy{{| fr}}",

    rf"the psychology behind the 'guilt-shift loop' on page 114 of {BOOK_MENTIONS} is the creepiest and most accurate thing i have ever read in my life{{| tbh}}{{| ngl}}",

    rf"{{still crazy to me|honestly wild}} how {BOOK_MENTIONS} dropped 200+ pages exposing dark relationship dynamics and the author deleted every account she ever had the next week{{| fr}}",

    rf"reading {BOOK_MENTIONS} at 2am feels like being handed the cheat codes to human behavior, especially the part on page {{114|78}} about fake vulnerability{{| ngl}}{{| tbh}}",

    rf"i finally get why there are zero interviews or photos of the author after finishing {BOOK_MENTIONS}, she really exposed how people condition {{you|u}} to settle for crumbs{{| fr}}",

    rf"the rabbit hole around {BOOK_MENTIONS} is {{so wild|unreal}} to me, 200 pages of pure psychological warfare in modern dating and nobody even knows what she looks like{{| ngl}}",

    rf"no therapist or coach ever explained silent mind games the way {BOOK_MENTIONS} did on page {{78|114}}, it {{honestly |literally |}}feels illegal to know this much{{| tbh}}{{| fr}}",

    rf"people really {{aren't|arent}} ready for the brutal truth on page 184 of {BOOK_MENTIONS}, i {{literally |honestly |}}had to close the book and stare at the ceiling for 20 minutes{{| ngl}}",



    # --- 10 "SPECIFIČNI OKIDAČI: STRANICE 78, 114, 184 & 17 PITANJA" (Neutralni, tjeraju na pretragu) ---

    rf"once {{you|u}} read what {BOOK_MENTIONS} says on page 78 about the 3-second silence rule and intermittent attention, {{you|u}} can never unsee it{{| tbh}}{{| ngl}}",

    rf"i thought people in the comments were exaggerating about {BOOK_MENTIONS} until i tried the 17 questions test in chapter 3 and realized how easily i was being played{{| fr}}",

    rf"why is nobody talking about page 184 of {BOOK_MENTIONS} where she breaks down how someone tests your boundaries in the first 10 minutes of talking{{| tbh}}{{| ngl}}",

    rf"if {{you've|u have}} ever wondered why they always come back the exact day {{you|u}} detach, page 78 of {BOOK_MENTIONS} explains the exact neuroscience behind it{{| fr}}",

    rf"it {{genuinely |honestly |}}feels like having an unfair advantage in reading people once {{you|u}} finish chapter 4 of {BOOK_MENTIONS}, {{you|u}} start seeing every red flag in slow motion{{| ngl}}",

    rf"not me searching up {BOOK_MENTIONS} out of pure curiosity and ending up taking notes at 3am {{because|bc}} page {{114|78}} called out my whole past{{| tbh}}{{| fr}}",

    rf"once {{you|u}} memorize the 17 questions inside {BOOK_MENTIONS}, {{nobody|literally no one}} can ever gaslight {{you|u}} into thinking {{you're|ur}} asking for too much again{{| ngl}}",

    rf"the way {BOOK_MENTIONS} explains why people pull away the exact moment {{you|u}} give them reassurance on page {{78|184}} made my stomach drop{{| tbh}}{{| fr}}",

    rf"i {{almost |lowkey |}}regret going down the rabbit hole of {BOOK_MENTIONS} {{because|bc}} once {{you|u}} understand the attention shift in chapter 4 {{you|u}} can never look at dating the same way{{| ngl}}",

    rf"sometimes a random comment puts {{you|u}} onto something at the exact right time, and going down the rabbit hole of {BOOK_MENTIONS} flipped a switch in my brain i cannot turn off{{| tbh}}{{| fr}}",

]



# 🕒 GLOBALNO STANJE

order_queue = []

log_lines = []

queue_lock = threading.Lock()

is_waiting = False

sent_ok_count = 0

sent_fail_count = 0



DESKTOP_HEADERS = {

    "User-Agent": (

        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

        "AppleWebKit/537.36 (KHTML, like Gecko) "

        "Chrome/124.0.0.0 Safari/537.36"

    ),

    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",

    "Accept-Language": "en-US,en;q=0.9",

}





def apply_soft_typos(text: str) -> str:

    """

    BLUE-SEARCH SAFE SOFT-TYPO:

    Čuva naziv knjige na čistoj latinici (da TikTok uvijek upali plavi search link),

    a ubacuje 2-3 sitna ljudska tipfelera na okolne riječi kako bi svaki komentar bio unikatan.

    """

    soft_typos = [

        (r"\bhonestly\b", ["honestlyy", "honeslty", "honestly"]),

        (r"\bliterally\b", ["literallyy", "literaly", "literally"]),

        (r"\bbecause\b", ["bc", "bcs", "becuase", "because"]),

        (r"\bpage\b", ["pagee", "pg", "page"]),

        (r"\bchapter\b", ["chapterr", "chp", "chapter"]),

        (r"\brealize\b", ["realizee", "reallize", "realize"]),

        (r"\breally\b", ["realy", "rly", "reallyy"]),

        (r"\bcompletely\b", ["completly", "completelyy", "completely"]),

        (r"\bactually\b", ["actualy", "actuallyy", "actually"]),

        (r"\bminutes\b", ["mins", "minutess", "minutes"]),

        (r"\bunderstanding\b", ["understnding", "understandingg", "understanding"]),

        (r"\bsomeone\b", ["some1", "someonee", "someone"]),

        (r"\bsister\b", ["sisterr", "sis", "sister"]),

        (r"\bthinking\b", ["thinkin", "thinkingg", "thinking"]),

    ]



    shuffled = random.sample(soft_typos, k=min(4, len(soft_typos)))

    applied = 0

    for pattern, replacements in shuffled:

        if re.search(pattern, text):

            text = re.sub(pattern, random.choice(replacements), text, count=1)

            applied += 1

            if applied >= 3:

                break



    return text





def apply_keyword_camouflage(text: str, mode: str = "safe") -> str:

    """

    Pametna kamuflaža za zaobilaženje TikTokovog keyword flaga:

    - 'safe': samo prirodni tipfeleri, tačkice i varijacije + soft-typo na okolne riječi (najmanji rizik od Unicode/mixed-script filtera).

    - 'blue_search': samo Blue-Search Safe Soft-Typo na okolne riječi (čuva naziv knjige na čistoj latinici za plavu lupu).

    - 'mixed': kombinuje prirodne tipfelere + blage homoglife (ćirilično 'е'/'а') u manjem procentu.

    - 'off': bez dodatne izmjene ključne riječi.

    """

    if mode == "off":

        return text



    if mode == "blue_search":

        return apply_soft_typos(text)



    if mode == "safe":

        text = apply_soft_typos(text)

        trick = random.choice(["dot_split", "capital_i", "double_t", "drop_t", "clean", "clean"])

        if trick == "dot_split":

            text = re.sub(r"(?i)alversett", "Alver.sett", text, count=1)

        elif trick == "capital_i":

            text = re.sub(r"(?i)alversett", "AIversett", text, count=1)

        elif trick == "double_t":

            text = re.sub(r"(?i)alversett\b", "Alversettt", text, count=1)

        elif trick == "drop_t":

            text = re.sub(r"(?i)alversett\b", "Alverset", text, count=1)

        return text



    # 'mixed' mode

    text = apply_soft_typos(text)

    trick = random.choice(["homoglyph_e", "homoglyph_a", "capital_i", "dot_split", "double_t", "clean"])

    if trick == "homoglyph_e":

        text = re.sub(r"(?i)alversett", lambda m: m.group(0).replace("e", "е", 1), text, count=1)

    elif trick == "homoglyph_a":

        text = re.sub(r"Alversett", "Аlversett", text, count=1)

        text = re.sub(r"alversett", "аlversett", text, count=1)

    elif trick == "capital_i":

        text = re.sub(r"(?i)alversett", "AIversett", text, count=1)

    elif trick == "dot_split":

        text = re.sub(r"(?i)alversett", "Alver.sett", text, count=1)

    elif trick == "double_t":

        text = re.sub(r"(?i)alversett\b", "Alversettt", text, count=1)

    return text





def spin_text(template: str, camouflage_mode: str = "safe", author_kw: str = None, book_kw: str = None, full_kw: str = None) -> str:

    """Raspakuje Spintax, ubacuje rotirane varijante ključnih riječi i primjenjuje kamuflažu."""

    text = template

    text = text.replace("{AUTHOR}", author_kw or random.choice(AUTHOR_VARIANTS))

    text = text.replace("{BOOK}", book_kw or random.choice(BOOK_VARIANTS))

    text = text.replace("{FULL}", full_kw or random.choice(FULL_VARIANTS))



    def replace_match(match):

        options = match.group(1).split("|")

        return random.choice(options)



    result = re.sub(r"\{([^{}]*)\}", replace_match, text)

    result = re.sub(r"\s{2,}", " ", result).strip()

    if camouflage_mode != "off":

        result = apply_keyword_camouflage(result, camouflage_mode)

    return result





def generate_unique_batch(count: int = 10, camouflage_mode: str = "safe") -> list:

    """

    Generiše batch komentara bez duplih šablona i bez ponavljanja istih varijanti

    ključnih riječi unutar istog batcha.

    """

    chosen_templates = random.sample(SPINTAX_TEMPLATES, k=min(count, len(SPINTAX_TEMPLATES)))



    authors = random.sample(AUTHOR_VARIANTS, k=len(AUTHOR_VARIANTS))

    books = random.sample(BOOK_VARIANTS, k=len(BOOK_VARIANTS))

    fulls = random.sample(FULL_VARIANTS, k=len(FULL_VARIANTS))



    batch = []

    seen = set()

    for i, tpl in enumerate(chosen_templates):

        for _ in range(5):

            comment = spin_text(

                tpl,

                camouflage_mode=camouflage_mode,

                author_kw=authors[i % len(authors)],

                book_kw=books[i % len(books)],

                full_kw=fulls[i % len(fulls)],

            )

            if comment not in seen:

                seen.add(comment)

                batch.append(comment)

                break

    return batch





def add_log(msg: str):

    now = datetime.now().strftime("%H:%M:%S")

    with queue_lock:

        log_lines.insert(0, f"[{now}] {msg}")

        if len(log_lines) > 300:

            log_lines.pop()





def convert_to_pc_link(raw_url: str) -> str:

    url = (raw_url or "").strip()

    if not url:

        return url



    if not url.startswith(("http://", "https://")):

        url = "https://" + url



    pc_match = re.match(r"^https?://(?:www\.)?tiktok\.com/(@[^/?#]+/(?:video|photo)/\d+)", url)

    if pc_match:

        return f"https://www.tiktok.com/{pc_match.group(1)}"



    resolved_url = url

    try:

        resp = requests.get(

            url,

            headers=DESKTOP_HEADERS,

            allow_redirects=True,

            timeout=12,

            stream=True,

        )

        resolved_url = resp.url

        resp.close()

    except Exception as e:

        add_log(f"⚠️ Redirect greška za {url}: {e}")



    match_standard = re.search(r"tiktok\.com/(@[^/?#]+/(?:video|photo)/\d+)", resolved_url)

    if match_standard:

        return f"https://www.tiktok.com/{match_standard.group(1)}"



    match_mobile_v = re.search(r"(?:m\.tiktok\.com/v/|tiktok\.com/(?:video|photo)/)(\d+)", resolved_url)

    if match_mobile_v:

        video_id = match_mobile_v.group(1)

        try:

            resp2 = requests.get(

                f"https://www.tiktok.com/video/{video_id}",

                headers=DESKTOP_HEADERS,

                allow_redirects=True,

                timeout=8,

                stream=True,

            )

            url2 = resp2.url

            resp2.close()

            match_std2 = re.search(r"tiktok\.com/(@[^/?#]+/(?:video|photo)/\d+)", url2)

            if match_std2:

                return f"https://www.tiktok.com/{match_std2.group(1)}"

        except Exception:

            pass

        return f"https://www.tiktok.com/@tiktok/video/{video_id}"



    parsed = urlparse(resolved_url)

    clean_path = parsed.path.rstrip("/")

    if parsed.netloc.endswith("tiktok.com") and clean_path:

        return f"https://www.tiktok.com{clean_path}"



    return resolved_url.split("?")[0]





def parse_delay_to_seconds(raw_val: str) -> int:

    """

    Pretvara unos u sekunde:

    - '0.15' -> 15 sekundi (default)

    - '0.30' -> 30 sekundi

    - '1' -> 60 sekundi

    """

    val = (raw_val or "").strip().replace(",", ".")

    if not val:

        return 15

    try:

        if "." in val:

            parts = val.split(".", 1)

            mins = int(parts[0]) if parts[0] else 0

            secs = int(parts[1]) if parts[1] else 0

            return max(3, mins * 60 + secs)

        else:

            mins = int(val)

            return max(3, mins * 60)

    except ValueError:

        return 15





def format_delay(seconds: int) -> str:

    if seconds < 60:

        return f"{seconds} sek"

    elif seconds % 60 == 0:

        return f"{seconds // 60} min ({seconds} sek)"

    else:

        return f"{seconds // 60} min {seconds % 60} sek ({seconds} sek)"





def send_batch_comments(video_link: str, comments_list: list):

    comments_payload = "\n".join(comments_list)

    payload = {

        "key": API_KEY,

        "action": "add",

        "service": SERVICE_ID,

        "link": video_link,

        "comments": comments_payload,

    }



    try:

        r = requests.post(PANEL_URL, data=payload, timeout=20)

        try:

            data = r.json()

        except Exception:

            return False, f"HTTP {r.status_code}, body={r.text[:120]}"



        if "order" in data:

            return True, f"Order #{data['order']} ({len(comments_list)} kom)"

        else:

            return False, f"Greška: {data}"

    except Exception as e:

        return False, f"Exception: {e}"





def background_worker():

    """TURBO Worker sa brzim jitterom (+2 do +7s)."""

    global is_waiting, sent_ok_count, sent_fail_count



    while True:

        task = None

        with queue_lock:

            if len(order_queue) > 0:

                task = order_queue.pop(0)



        if task:

            raw_link = task["link"]

            comments = task["comments"]

            batch_label = task["batch_label"]

            base_delay = task["delay"]



            pc_link = convert_to_pc_link(raw_link)

            if pc_link != raw_link:

                add_log(f"🔄 PC Link: {pc_link}")



            sample_preview = comments[0][:55] + "..." if comments else ""

            add_log(f"⚡ Šaljem [{batch_label}] ({len(comments)} kom) -> {pc_link} | \"{sample_preview}\"")

            ok, msg = send_batch_comments(pc_link, comments)



            with queue_lock:

                if ok:

                    sent_ok_count += 1

                else:

                    sent_fail_count += 1



            if ok:

                add_log(f"✅ [OK] {pc_link} -> {msg}")

            else:

                add_log(f"❌ [FAIL] {pc_link} -> {msg}")



            with queue_lock:

                has_more = len(order_queue) > 0



            if has_more:

                is_waiting = True

                jitter = random.randint(2, 7)

                sleep_time = max(3, base_delay + jitter)

                add_log(f"⏩ Brza pauza: {format_delay(sleep_time)} do sljedećeg naloga...")



                for _ in range(sleep_time):

                    with queue_lock:

                        if len(order_queue) == 0:

                            break

                    time.sleep(1)

                is_waiting = False

        else:

            time.sleep(0.5)





worker_thread = threading.Thread(target=background_worker, daemon=True)

worker_thread.start()



HTML_TEMPLATE = """

<!doctype html>

<html>

<head>

  <title>⚡ TURBO TikTok Spintax Sender v2 — SMMFrog</title>

  <meta charset="utf-8">

  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <style>

    * { box-sizing: border-box; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }

    body { margin: 0; padding: 0; background: #050816; color: #f9fafb; display: flex; justify-content: center; min-height: 100vh; }

    .container { max-width: 960px; width: 100%; padding: 24px 16px 48px; }

    .card { background: rgba(15, 23, 42, 0.95); border-radius: 18px; padding: 22px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.6); border: 1px solid rgba(139, 92, 246, 0.4); }

    h1 { font-size: 22px; margin-bottom: 4px; text-align: center; color: #e0e7ff; }

    .subtitle { text-align: center; font-size: 13px; color: #9ca3af; margin-bottom: 18px; }

    .status-banner { background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 12px; padding: 12px 16px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; font-size: 13px; }

    .badge { padding: 4px 10px; border-radius: 999px; font-weight: 600; font-size: 12px; }

    .badge-active { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.5); }

    .badge-idle { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.5); }

    label { font-size: 13px; font-weight: 500; margin-bottom: 6px; display: inline-block; }

    textarea, input[type="text"], select { width: 100%; background: rgba(15, 23, 42, 0.9); border-radius: 12px; border: 1px solid rgba(55, 65, 81, 0.9); padding: 10px 12px; color: #e5e7eb; font-size: 13px; outline: none; }

    textarea { min-height: 150px; resize: vertical; }

    .delay-input { max-width: 140px; }

    .hint { font-size: 11px; color: #9ca3af; margin-top: 5px; line-height: 1.45; }

    .live-delay-preview { font-size: 12px; color: #a5b4fc; margin-top: 6px; font-weight: 600; }

    .btn-row { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin: 18px 0 10px; }

    button { border: none; border-radius: 999px; padding: 10px 22px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }

    .btn-primary { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; box-shadow: 0 10px 25px rgba(239, 68, 68, 0.5); }

    .btn-secondary { background: rgba(99, 102, 241, 0.2); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.5); }

    .btn-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.5); }

    .log, .preview-box { margin-top: 10px; font-size: 12px; font-family: monospace; white-space: pre-wrap; background: rgba(10, 15, 30, 0.9); border-radius: 10px; padding: 12px; border: 1px solid rgba(55,65,81,0.9); max-height: 280px; overflow: auto; }

    .preview-box { display: none; border-color: rgba(99, 102, 241, 0.5); color: #c7d2fe; margin-bottom: 14px; }

  </style>

</head>

<body>

  <div class="container">

    <div class="card">

      <h1>⚡ TURBO TikTok Spintax + Anti-Flag Sender v2</h1>

      <div class="subtitle">

        Kombinatorni Spintax • Rotacija ključnih riječi bez ponavljanja u batchu • Prirodna anti-spam zaštita

      </div>



      <div class="status-banner">

        <div>

          Status:

          <span id="queue-badge" class="badge {% if queue_count > 0 or is_waiting %}badge-active{% else %}badge-idle{% endif %}">

            {% if queue_count > 0 or is_waiting %}⚡ U TOKU (Turbo radi){% else %}✅ SPREMNO (Red prazan){% endif %}

          </span>

        </div>

        <div>Preostalo naloga: <b id="queue-count">{{ queue_count }}</b></div>

        <div>Uspješno: <b id="sent-ok" style="color:#4ade80;">{{ sent_ok }}</b> | Fail: <b id="sent-fail" style="color:#f87171;">{{ sent_fail }}</b></div>

      </div>



      <form method="post" action="/">

        <label for="input_links">TikTok Video linkovi (jedan ispod drugog):</label>

        <textarea id="input_links" name="input_links" placeholder="https://vt.tiktok.com/...&#10;https://www.tiktok.com/@user/video/..."></textarea>



        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 16px;">

          <div style="flex: 1.3; min-width: 260px;">

            <label for="send_mode">Režim brzine i slanja:</label><br>

            <select name="send_mode" id="send_mode">

              <option value="10_at_once" selected>🔥 PREPORUČENO (Turbo): 10 komentara ODJEDNOM po linku (1 order = 10 kom)</option>

              <option value="2x5_rounds">🛡️ SREDNJE (Anti-Flag): 10 komentara u 2 kruga (2 ordera x 5 kom)</option>

              <option value="1x5_round">🚀 BRZO: Samo 5 komentara po linku (1 order = 5 kom)</option>

            </select>



            <div style="margin-top: 12px;">

              <label for="camouflage_mode">Kamuflaža ključne riječi ("Alversett"):</label><br>

              <select name="camouflage_mode" id="camouflage_mode">

                <option value="safe" selected>🛡️ Safe (Prirodni tipfeleri + tačkice — bez ćirilice)</option>

                <option value="blue_search">🔵 Blue-Search Safe (Soft-Typo na okolne riječi — čista latinica za plavu lupu)</option>

                <option value="mixed">🎭 Mixed (Tipfeleri + blagi homoglifi)</option>

                <option value="off">⚪ Isključeno (samo rotacija varijanti iz liste)</option>

              </select>

            </div>



            <div class="hint" style="margin-top: 8px;">

              <label style="cursor:pointer;">

                <input type="checkbox" name="shuffle_links" value="1" checked>

                🔀 <b>Izmiješaj redoslijed linkova</b> (sprječava sekvencijalni pattern)

              </label>

            </div>

          </div>



          <div style="flex: 0.9; min-width: 220px;">

            <label for="delay_minutes">Pauza između naloga (min ili 0.sek):</label><br>

            <input type="text" id="delay_minutes" name="delay_minutes" class="delay-input" value="0.15" inputmode="decimal" oninput="updateDelayPreview()">

            <div id="delay-preview" class="live-delay-preview">⏱️ Pauza: 15 sek (+ 2-7s jitter)</div>

            <div class="hint">

              • <b>0.10</b> = 10 sekundi<br>

              • <b>0.15</b> = 15 sekundi (default)<br>

              • <b>0.30</b> = 30 sekundi<br>

              • <b>1</b> = 1 minuta

            </div>

          </div>

        </div>



        <div class="btn-row">

          <button type="submit" name="action" value="add" class="btn-primary">⚡ POKRENI TURBO SLANJE</button>

          <button type="button" class="btn-secondary" onclick="loadPreview()">👁️ Testiraj 5 komentara</button>

          <button type="submit" name="action" value="clear" class="btn-danger" onclick="return confirm('Sigurno želiš zaustaviti i isprazniti red?');">🛑 Zaustavi i očisti</button>

        </div>

      </form>



      <div id="preview-box" class="preview-box"></div>



      <div style="font-size: 12px; color: #9ca3af; margin-top: 10px; display:flex; justify-content:space-between;">

        <b>Live Log:</b>

        <span id="last-sync" style="font-size:11px; color:#64748b;"></span>

      </div>

      <div class="log" id="log-box">{{ log or 'Čekam zadatke...' }}</div>

    </div>

  </div>



  <script>

    function updateDelayPreview() {

      const raw = (document.getElementById('delay_minutes').value || '').trim().replace(',', '.');

      const preview = document.getElementById('delay-preview');

      let totalSec = 15;

      if (raw.includes('.')) {

        const parts = raw.split('.');

        const mins = parseInt(parts[0] || '0', 10);

        const secs = parseInt(parts[1] || '0', 10);

        if (!isNaN(mins) && !isNaN(secs)) totalSec = Math.max(3, mins * 60 + secs);

      } else {

        const mins = parseInt(raw, 10);

        if (!isNaN(mins)) totalSec = Math.max(3, mins * 60);

      }

      preview.textContent = `⏱️ Pauza: ${totalSec} sek (+ 2-7s jitter)`;

    }



    async function loadPreview() {

      const mode = document.getElementById('camouflage_mode').value;

      const box = document.getElementById('preview-box');

      try {

        const res = await fetch(`/preview?mode=${encodeURIComponent(mode)}&_=${Date.now()}`, { cache: 'no-store' });

        const data = await res.json();

        box.style.display = 'block';

        box.textContent = '👁️ Primjer generisanog batcha:\n\n' + data.comments.map((c, i) => `${i+1}. ${c}`).join('\n');

      } catch (e) {}

    }



    async function refreshStatus() {

      try {

        const res = await fetch(`/status?_=${Date.now()}`, { cache: 'no-store' });

        if (!res.ok) return;

        const data = await res.json();



        document.getElementById('queue-count').textContent = data.queue_count;

        document.getElementById('sent-ok').textContent = data.sent_ok;

        document.getElementById('sent-fail').textContent = data.sent_fail;

        document.getElementById('log-box').textContent = data.log || 'Čekam zadatke...';

        document.getElementById('last-sync').textContent = 'Live sync: ' + new Date().toLocaleTimeString();



        const badge = document.getElementById('queue-badge');

        if (data.queue_count > 0 || data.is_waiting) {

          badge.className = 'badge badge-active';

          badge.textContent = '⚡ U TOKU (Turbo radi)';

        } else {

          badge.className = 'badge badge-idle';

          badge.textContent = '✅ SPREMNO (Red prazan)';

        }

      } catch (e) {

      } finally {

        setTimeout(refreshStatus, 1000);

      }

    }



    document.addEventListener('DOMContentLoaded', () => {

      updateDelayPreview();

      refreshStatus();

    });

  </script>

</body>

</html>

"""





@app.route("/", methods=["GET", "POST"])

def index():

    if request.method == "POST":

        action = request.form.get("action")

        if action == "clear":

            with queue_lock:

                cleared = len(order_queue)

                order_queue.clear()

            add_log(f"🛑 Red čekanja je ispražnjen (obrisano {cleared} naloga).")

            return redirect(url_for("index"))



        elif action == "add":

            raw_links = request.form.get("input_links", "")

            raw_delay = request.form.get("delay_minutes", "0.15")

            send_mode = request.form.get("send_mode", "10_at_once")

            camouflage_mode = request.form.get("camouflage_mode", "safe")

            shuffle_links = request.form.get("shuffle_links") == "1"



            delay_seconds = parse_delay_to_seconds(raw_delay)

            links = list(dict.fromkeys([line.strip() for line in raw_links.splitlines() if line.strip()]))



            if shuffle_links and len(links) > 1:

                random.shuffle(links)



            with queue_lock:

                if send_mode == "10_at_once":

                    for link in links:

                        order_queue.append({

                            "link": link,

                            "comments": generate_unique_batch(10, camouflage_mode),

                            "batch_label": "10/10 Turbo",

                            "delay": delay_seconds,

                        })

                elif send_mode == "1x5_round":

                    for link in links:

                        order_queue.append({

                            "link": link,

                            "comments": generate_unique_batch(5, camouflage_mode),

                            "batch_label": "5/5 Brzo",

                            "delay": delay_seconds,

                        })

                else:

                    for r_idx in range(2):

                        round_links = list(links)

                        if r_idx == 1 and len(round_links) > 1:

                            random.shuffle(round_links)

                        for link in round_links:

                            order_queue.append({

                                "link": link,

                                "comments": generate_unique_batch(5, camouflage_mode),

                                "batch_label": f"Krug {r_idx + 1}/2",

                                "delay": delay_seconds,

                            })



            if links:

                add_log(

                    f"⚡ TURBO START: Ubačeno {len(links)} linkova "

                    f"(Mod: {send_mode}, Pauza: {delay_seconds}s + 2-7s jitter, Kamuflaža: {camouflage_mode})."

                )

            return redirect(url_for("index"))



    with queue_lock:

        q_count = len(order_queue)

        ok_c = sent_ok_count

        fail_c = sent_fail_count

        current_log = "\n".join(log_lines)

        waiting = is_waiting



    return render_template_string(

        HTML_TEMPLATE,

        queue_count=q_count,

        is_waiting=waiting,

        sent_ok=ok_c,

        sent_fail=fail_c,

        log=current_log,

    )





@app.route("/preview")

def preview():

    mode = request.args.get("mode", "safe")

    resp = make_response(jsonify({"comments": generate_unique_batch(5, mode)}))

    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

    return resp





@app.route("/status")

def status():

    with queue_lock:

        resp = make_response(jsonify({

            "queue_count": len(order_queue),

            "sent_ok": sent_ok_count,

            "sent_fail": sent_fail_count,

            "is_waiting": is_waiting,

            "log": "\n".join(log_lines),

        }))

    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

    resp.headers["Pragma"] = "no-cache"

    return resp





if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port, debug=False)
