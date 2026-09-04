from __future__ import annotations

from typing import Any, Iterable

from core.production_intelligence_profiles import select_production_intelligence_profile


GENRE_CATALOG = (
    "Pop",
    "Pop Rock",
    "Rock",
    "Alternative Rock",
    "Indie Pop",
    "Indie Rock",
    "Acoustic Pop",
    "Folk Pop",
    "Ballad",
    "R&B",
    "Soul",
    "Neo Soul",
    "Lo-fi Pop",
    "Synth Pop",
    "Dream Pop",
    "City Pop",
    "Electronic Pop",
    "Dance Pop",
    "Hip-Hop",
    "Trap",
    "Reggae",
    "Country Pop",
    "Cinematic Pop",
    "Thai Pop",
    "Thai Rock",
    "ลูกทุ่งร่วมสมัย",
    "เพื่อชีวิตร่วมสมัย",
)

MOOD_CATALOG = (
    "สดใส",
    "ให้กำลังใจ",
    "ฮึกเหิม",
    "มีพลัง",
    "โรแมนติก",
    "อบอุ่น",
    "คิดถึง",
    "เหงา",
    "เหงากลางคืน",
    "เศร้า",
    "อกหัก",
    "ละมุน",
    "ฝัน ๆ",
    "สงบ",
    "ลึกลับ",
    "มืดหม่น",
    "กดดัน",
    "โกรธ",
    "สับสน",
    "หวังใหม่",
    "Bittersweet",
    "Nostalgic",
    "Cinematic",
    "Epic",
    "Inspirational",
)

VOCAL_CATALOG = (
    "smooth emotional male vocal",
    "emotional male vocal",
    "powerful male vocal",
    "warm intimate male vocal",
    "raspy rock male vocal",
    "soft female vocal",
    "emotional female vocal",
    "powerful female vocal",
    "warm intimate female vocal",
    "airy dreamy female vocal",
    "duet male and female",
    "duet soft harmony",
)


def _vocal(
    gender_mode: str,
    delivery: str,
    power: str,
    intimacy: str,
    texture: str,
    breathiness: str,
    rasp: str,
    diction: str,
    dynamic_behavior: str,
    chorus_behavior: str,
    harmony_behavior: str,
) -> dict[str, str]:
    return {
        "gender_mode": gender_mode,
        "delivery": delivery,
        "power": power,
        "intimacy": intimacy,
        "texture": texture,
        "breathiness": breathiness,
        "rasp": rasp,
        "diction": diction,
        "dynamic_behavior": dynamic_behavior,
        "chorus_behavior": chorus_behavior,
        "harmony_behavior": harmony_behavior,
    }


VOCAL_PROFILES = {
    "smooth emotional male vocal": _vocal("male", "smooth emotionally expressive delivery", "moderate controlled power", "moderate close-mic intimacy", "clean warm texture", "low breathiness", "little to no rasp", "clear natural Thai diction", "controlled movement from intimate verses to a wider chorus", "gentle emotional lift without forced belting", "subtle doubles and restrained harmony on key hook lines"),
    "emotional male vocal": _vocal("male", "expressive phrasing with honest emotional emphasis", "moderate power", "personal verse intimacy", "natural resonant texture", "light breathiness on vulnerable phrases", "minimal rasp", "clear conversational Thai diction", "stronger dynamic movement across sections", "open emotional chorus with controlled upper-register lift", "supportive harmony that widens the final chorus"),
    "powerful male vocal": _vocal("male", "strong forward projection with confident articulation", "high power", "moderate intimacy", "firm full-bodied texture", "very low breathiness", "low controlled rasp", "precise Thai articulation", "large dynamic rise with sustained control", "punchy chorus delivery and strong upper-register lift", "stacked support in the final chorus without masking the lead"),
    "warm intimate male vocal": _vocal("male", "close-mic restrained delivery with smooth phrasing", "low to moderate power", "high intimacy", "warm rounded texture", "subtle natural breathiness", "no forced rasp", "clear soft Thai diction", "small controlled human dynamics with a gentle section lift", "personal chorus that opens slightly without power belting", "quiet doubles and occasional warm harmony"),
    "raspy rock male vocal": _vocal("male", "energetic articulation with a stronger attack", "moderate to high power", "moderate intimacy", "gritty rock texture", "low breathiness", "moderate controlled rasp", "clear Thai consonants despite the grit", "physical dynamic drive with controlled recovery in verses", "aggressive but musical chorus lift", "firm gang-style support only on selected hook moments"),
    "soft female vocal": _vocal("female", "gentle smooth delivery", "low to moderate power", "high intimacy", "soft clean upper register", "light breathiness", "no rasp", "clear intelligible Thai diction", "restrained dynamics with delicate growth", "soft melodic chorus lift without belting", "light doubles and minimal high harmony"),
    "emotional female vocal": _vocal("female", "expressive phrasing with emotional nuance", "moderate power", "moderate to high intimacy", "clear resonant texture", "controlled breathiness", "no forced rasp", "clear Thai diction", "wide but controlled emotional arc", "larger emotional chorus with sustained expressive notes", "layered harmony that expands the final chorus"),
    "powerful female vocal": _vocal("female", "strong forward projection and confident articulation", "high power", "moderate intimacy", "full bright texture without harshness", "low breathiness", "minimal controlled rasp", "strong clear Thai diction", "high dynamic lift with disciplined control", "large melodic chorus and sustained expressive peaks", "wide stacked harmony reserved for the largest sections"),
    "warm intimate female vocal": _vocal("female", "close warm delivery with softer phrasing", "low to moderate power", "high intimacy", "warm smooth texture", "subtle breathiness", "no rasp", "clear gentle Thai articulation", "restrained verse movement with a natural emotional rise", "tender chorus lift that stays personal", "soft complementary harmony and quiet doubles"),
    "airy dreamy female vocal": _vocal("female", "airy sustained phrasing with soft consonant attack", "low to moderate power", "high atmospheric intimacy", "light floating texture", "moderate controlled breathiness", "no rasp", "intelligible Thai diction despite the airy tone", "floating dynamics with gradual bloom", "polished spacious chorus that remains clear rather than forceful", "shimmering layered harmony with a distinct lead vocal"),
    "duet male and female": _vocal("duet", "alternating or complementary lead delivery", "balanced shared power", "variable intimacy between perspectives", "contrasting but cohesive male and female textures", "controlled breathiness by phrase", "no forced rasp", "clear Thai diction for both singers", "natural call-and-response with shared emotional growth", "shared chorus with balanced lead presence", "complementary harmony moments without mechanical line-by-line alternation"),
    "duet soft harmony": _vocal("duet", "one primary lead with gentle complementary responses", "restrained shared power", "high blended intimacy", "soft cohesive vocal blend", "light controlled breathiness", "no rasp", "clear Thai diction with an identifiable primary lead", "subtle dynamic growth led by the primary voice", "layered chorus with restrained support rather than a full duet", "one primary vocal with restrained harmony support, complementary phrasing and occasional response lines"),
}


def _genre(
    tempo: tuple[int, int],
    instruments: tuple[str, ...],
    rhythm: str,
    energy: str,
    arrangement: str,
    notes: str,
    prompt_genre: str | None = None,
) -> dict[str, Any]:
    return {
        "tempo_range": tempo,
        "instrument_palette": instruments,
        "rhythmic_feel": rhythm,
        "energy": energy,
        "arrangement_character": arrangement,
        "production_notes": notes,
        "prompt_genre": prompt_genre or "",
    }


GENRE_PROFILES: dict[str, dict[str, Any]] = {
    "Pop": _genre((90, 118), ("clean electric guitar", "modern synth layers", "polished pop drums", "modern bass"), "steady contemporary pop pulse", "balanced with a bright chorus lift", "compact verses and a wide hook-led chorus", "clean transitions and a vocal-forward commercial finish"),
    "Pop Rock": _genre((90, 125), ("clean and driven electric guitars", "live bass", "tight pop-rock drums", "supporting piano"), "driving live pop-rock groove", "dynamic and chorus-forward", "restrained verse, rising pre-chorus, full-band chorus", "controlled guitar layers with a modern radio-ready finish"),
    "Rock": _genre((105, 145), ("distorted electric guitars", "live bass", "powerful acoustic drums", "subtle supporting keys"), "forceful live rock drive", "high and physical", "riff-led verses and an explosive full-band chorus", "retain live-band impact and firm low-end control"),
    "Alternative Rock": _genre((95, 140), ("textured electric guitars", "live bass", "dynamic drums", "atmospheric layers"), "elastic alternative-rock groove", "dynamic with tension and release", "textural verses opening into a larger chorus", "use contrast, space and imperfect organic edges"),
    "Indie Pop": _genre((85, 120), ("chorused clean guitars", "warm synths", "organic drums", "rounded bass"), "light organic pop pulse", "moderate and buoyant", "intimate verses with a colorful melodic chorus", "keep character and warmth ahead of glossy density"),
    "Indie Rock": _genre((95, 135), ("jangly electric guitars", "live bass", "organic drum kit", "subtle analog keys"), "forward indie-rock groove", "energetic but unpolished", "guitar-led storytelling with a natural band lift", "preserve room feel and human dynamics"),
    "Acoustic Pop": _genre((72, 100), ("acoustic guitar", "soft piano", "light percussion", "warm bass"), "gentle acoustic pop pulse", "restrained with a natural lift", "close verses and an open acoustic chorus", "prioritize vocal intimacy and organic detail"),
    "Folk Pop": _genre((75, 105), ("fingerpicked acoustic guitar", "hand percussion", "warm bass", "subtle strings"), "organic folk-pop sway", "warm and gradually lifting", "storytelling verses with a communal chorus", "natural room tone and unforced acoustic movement"),
    "Ballad": _genre((60, 82), ("piano", "acoustic guitar", "soft strings", "restrained drums"), "slow expressive ballad pulse", "low to large emotional climax", "sparse opening with a patient final-chorus build", "leave space around the lead vocal and avoid overproduction"),
    "R&B": _genre((68, 100), ("warm electric piano", "deep controlled bass", "restrained drums", "atmospheric synth textures"), "laid-back pocket with subtle syncopation", "controlled and intimate", "spacious verses with a fuller smooth chorus", "deep pocket, clean vocal focus and restrained top end"),
    "Soul": _genre((70, 105), ("electric piano", "warm organ", "expressive guitar", "live bass and drums"), "human soul pocket", "emotionally rising", "vocal-led verses building into a rich live chorus", "retain expressive dynamics and warm harmonic color"),
    "Neo Soul": _genre((65, 100), ("Rhodes piano", "warm melodic bass", "laid-back drums", "expressive clean guitar"), "behind-the-beat neo-soul pocket", "low and nuanced", "harmonically rich verses with an understated chorus", "soft transients, detailed groove and intimate vocal placement"),
    "Lo-fi Pop": _genre((65, 95), ("soft keys", "muted drums", "warm tape texture", "restrained bass"), "relaxed muted groove", "low and steady", "minimal verses and a simple melodic hook", "soft edges, narrow dynamics and gentle texture"),
    "Synth Pop": _genre((95, 125), ("analog-style synths", "electronic drums", "synth bass", "bright melodic arpeggios"), "precise electronic pop pulse", "medium-high and polished", "layered synth build into a bright chorus", "crisp electronic definition without masking the vocal"),
    "Dream Pop": _genre((75, 110), ("shimmering guitars", "airy pads", "soft electronic drums", "rounded bass"), "floating slow-to-mid pulse", "moderate-low and immersive", "hazy verses with a blooming spacious chorus", "wide ambience, soft transients and clear vocal presence"),
    "City Pop": _genre((90, 120), ("clean funk guitar", "electric piano", "melodic bass", "polished drums", "synth accents"), "syncopated city-pop groove", "bright and sophisticated", "groove-led verses with a melodic polished chorus", "tight rhythm section, colorful harmony and clean retro-modern sheen"),
    "Electronic Pop": _genre((100, 128), ("layered synths", "electronic drums", "synth bass", "textural effects"), "driving electronic pop pulse", "high but controlled", "progressive electronic build into a wide chorus", "clean low end, modern transients and purposeful automation feel"),
    "Dance Pop": _genre((110, 128), ("bright synth layers", "four-on-the-floor drums", "synth bass", "hook plucks"), "four-on-the-floor dance groove", "high and immediate", "short build sections and a strong dance chorus", "club clarity with a commercial vocal-forward balance"),
    "Hip-Hop": _genre((70, 100), ("kick-snare-driven beat", "deep bass", "atmospheric keys", "sample-like textures"), "head-nod hip-hop pocket", "controlled with focused accents", "verse-led structure with a concise memorable hook", "leave rhythmic space for phrasing and keep bass disciplined"),
    "Trap": _genre((65, 85), ("808-style bass", "tight hi-hats", "punchy kick and snare", "sparse melodic layers"), "halftime trap pocket", "tense and punchy", "sparse verses with a hard hook impact", "clean sub control, precise hats and uncluttered vocal space"),
    "Reggae": _genre((70, 100), ("offbeat guitar", "warm bass", "relaxed drums", "organ and keys"), "laid-back offbeat groove", "warm and easy-moving", "groove-first verses and an open singable chorus", "deep bass, relaxed pocket and natural room warmth"),
    "Country Pop": _genre((85, 120), ("acoustic guitar", "clean electric guitar", "steady live drums", "warm bass"), "steady country-pop groove", "warm with a bright lift", "story-led verses and a concise radio chorus", "organic instruments with a polished contemporary vocal"),
    "Cinematic Pop": _genre((65, 110), ("piano", "cinematic strings", "atmospheric synths", "hybrid drums"), "measured cinematic pulse", "wide dynamic range", "intimate opening growing into a large final chorus", "cinematic scale with clear pop-song focus"),
    "Thai Pop": _genre((85, 115), ("clean guitar", "soft piano", "modern synth accents", "polished pop rhythm section"), "modern Thai pop pulse", "balanced and melodic", "conversational verses with a memorable melodic chorus", "clear Thai vocal diction and contemporary commercial polish"),
    "Thai Rock": _genre((95, 135), ("guitar-forward layers", "live bass", "energetic drums", "supporting piano"), "driving Thai rock groove", "strong and emotionally direct", "restrained storytelling verses into a powerful chorus", "live-band energy with clear Thai vocal focus"),
    "ลูกทุ่งร่วมสมัย": _genre((80, 115), ("acoustic and clean electric guitars", "melodic bass", "accessible live groove", "modern Thai country accents"), "accessible Thai country-pop groove", "warm and expressive", "storytelling verses with a direct melodic chorus", "modern clarity while retaining Thai country character", "contemporary Thai luk thung"),
    "เพื่อชีวิตร่วมสมัย": _genre((75, 115), ("acoustic guitar", "organic drums", "bass", "restrained electric guitar"), "grounded organic storytelling groove", "earthy and gradually lifting", "narrative-first verses with a sincere communal chorus", "natural band dynamics and unembellished emotional delivery", "contemporary Thai phuea chiwit"),
    "Jazz": _genre((68, 126), ("acoustic piano", "upright bass", "live drums", "clean jazz guitar"), "human jazz pocket", "dynamic and harmonically expressive", "vocal-led verses with tasteful instrumental responses", "natural ensemble dynamics, warm room tone and clear vocal placement"),
}

GENRE_ALIASES = {
    "Heartbreak Ballad": "Ballad",
    "T-Pop": "Thai Pop",
    "Night Drive": "Dream Pop",
    "Isaan Indie": "ลูกทุ่งร่วมสมัย",
    "Acoustic": "Acoustic Pop",
    "EDM": "Electronic Pop",
    "Modern Thai pop rock": "Pop Rock",
}


def _mood(position: float, english: str, energy: str, arrangement: str, production: str) -> dict[str, Any]:
    return {
        "tempo_position": position,
        "english_label": english,
        "energy_modifier": energy,
        "arrangement_modifier": arrangement,
        "production_modifier": production,
    }


MOOD_MODIFIERS = {
    "สดใส": _mood(0.78, "bright and cheerful", "lift the energy", "open the chorus early", "bright harmonic color and crisp transients"),
    "ให้กำลังใจ": _mood(0.68, "encouraging and hopeful", "build gradually", "make the chorus feel reassuring and strong", "brighter harmonic lift without excessive loudness"),
    "ฮึกเหิม": _mood(0.88, "anthemic and determined", "push strong forward momentum", "use a bigger rhythmic chorus", "firm drums and broad dynamics"),
    "มีพลัง": _mood(0.84, "energetic and confident", "maintain high energy", "use decisive transitions and a strong chorus", "punchy rhythm section and clear transient impact"),
    "โรแมนติก": _mood(0.48, "romantic and intimate", "keep energy warm and controlled", "focus on close verses and a tender chorus", "soft rhythmic feel and warm harmony"),
    "อบอุ่น": _mood(0.52, "warm and comforting", "use gentle natural lift", "favor organic transitions", "rounded tone and soft room ambience"),
    "คิดถึง": _mood(0.38, "nostalgic and longing", "keep energy restrained", "let melodic guitar or piano carry the memory", "warm reverb and patient drums"),
    "เหงา": _mood(0.28, "lonely and intimate", "keep energy low", "leave space between phrases", "dark ambience and restrained brightness"),
    "เหงากลางคืน": _mood(0.32, "lonely late-night", "keep verses sparse", "use an intimate verse and controlled chorus", "dark ambient space, deep bass and spacious reverb"),
    "เศร้า": _mood(0.20, "sad and vulnerable", "reduce attack and energy", "build slowly toward the emotional peak", "warmer darker tone with soft transients"),
    "อกหัก": _mood(0.24, "heartbroken and exposed", "start fragile then widen", "reserve the strongest lift for the final chorus", "vocal-forward mix with restrained verses"),
    "ละมุน": _mood(0.42, "soft and tender", "keep dynamics gentle", "use smooth section transitions", "soft transients and warm harmonic detail"),
    "ฝัน ๆ": _mood(0.34, "dreamy and airy", "float rather than drive", "use spacious verses and a blooming chorus", "airy pads, long reverb and softened edges"),
    "สงบ": _mood(0.16, "calm and reflective", "keep energy minimal", "avoid abrupt transitions", "natural space and restrained low end"),
    "ลึกลับ": _mood(0.40, "mysterious and tense", "hold controlled tension", "reveal layers gradually", "shadowed texture and selective high-frequency detail"),
    "มืดหม่น": _mood(0.26, "dark and brooding", "keep energy heavy but restrained", "use slow-building pressure", "low-mid atmosphere and limited brightness"),
    "กดดัน": _mood(0.62, "pressured and tense", "increase rhythmic urgency", "tighten transitions toward the peak", "controlled compression and persistent pulse"),
    "โกรธ": _mood(0.82, "angry and confrontational", "push hard accents", "use abrupt dynamic contrast", "aggressive rhythm impact without clipping"),
    "สับสน": _mood(0.44, "conflicted and uncertain", "use uneven emotional tension", "contrast sparse verses with a searching chorus", "textural ambiguity with clear vocal focus"),
    "หวังใหม่": _mood(0.66, "renewed and hopeful", "rise steadily", "make the final chorus feel newly open", "brighter width and clean uplifting resolution"),
    "Bittersweet": _mood(0.46, "bittersweet", "balance warmth and restraint", "contrast tender verses with a gently lifting chorus", "warm but melancholic color"),
    "Nostalgic": _mood(0.40, "nostalgic", "keep movement moderate", "let melodic details recall the past", "warm vintage space with modern vocal clarity"),
    "Cinematic": _mood(0.54, "cinematic and emotional", "use broad dynamic movement", "build layers across sections", "wide depth and controlled cinematic scale"),
    "Epic": _mood(0.76, "epic and expansive", "use large dynamics", "save the largest section for the final chorus", "cinematic layers and strong low-end impact"),
    "Inspirational": _mood(0.72, "inspirational and uplifting", "build confident momentum", "create a clear emotional rise", "bright vocal-forward finish and broad final chorus"),
}

MOOD_ALIASES = {
    "Warm": "อบอุ่น",
    "Energetic": "มีพลัง",
    "Sad": "เศร้า",
    "Lonely": "เหงา",
    "Hopeful": "หวังใหม่",
    "Emotional": "Bittersweet",
    "lonely emotional cinematic": "Cinematic",
}


def catalog_with_saved_value(catalog: Iterable[str], saved_value: str | None) -> list[str]:
    values = list(catalog)
    saved = str(saved_value or "").strip()
    if saved and saved not in values:
        values.append(saved)
    return values


def _canonical_genre(value: str) -> str:
    clean = str(value or "").strip()
    if clean in GENRE_PROFILES:
        return clean
    if clean in GENRE_ALIASES:
        return GENRE_ALIASES[clean]
    lower = clean.lower()
    for name in GENRE_PROFILES:
        if name.lower() == lower:
            return name
    if "rock" in lower:
        return "Rock"
    if "acoustic" in lower or "folk" in lower:
        return "Acoustic Pop"
    if "r&b" in lower or "rnb" in lower:
        return "R&B"
    if "dance" in lower or "edm" in lower or "electronic" in lower:
        return "Electronic Pop"
    return "Pop"


def _canonical_mood(value: str) -> str:
    clean = str(value or "").strip()
    if clean in MOOD_MODIFIERS:
        return clean
    if clean in MOOD_ALIASES:
        return MOOD_ALIASES[clean]
    lower = clean.lower()
    for name in MOOD_MODIFIERS:
        if name.lower() == lower:
            return name
    if any(word in lower for word in ("sad", "heartbreak")):
        return "เศร้า"
    if any(word in lower for word in ("hope", "uplift", "inspir")):
        return "หวังใหม่"
    if any(word in lower for word in ("energy", "power", "anthem")):
        return "มีพลัง"
    return "Bittersweet"


def resolve_vocal_profile(*, vocal: str, genre: str, mood: str) -> dict[str, str]:
    label = str(vocal or "natural lead vocal").strip() or "natural lead vocal"
    base = dict(VOCAL_PROFILES.get(label) or {})
    lower = label.lower()
    if not base:
        gender_mode = "duet" if "duet" in lower else "female" if "female" in lower else "male" if "male" in lower else "neutral"
        base = _vocal(
            gender_mode,
            f"natural delivery consistent with the selected '{label}' character",
            "balanced controlled power",
            "moderate intimacy",
            "clean natural texture",
            "controlled breathiness",
            "no forced rasp",
            "clear natural Thai diction",
            "coherent dynamics across the complete song",
            "musical chorus lift without changing the selected vocal identity",
            "restrained harmony supporting the lead",
        )

    canonical_genre = _canonical_genre(genre)
    canonical_mood = _canonical_mood(mood)
    if label == "raspy rock male vocal" and canonical_genre in {"Rock", "Alternative Rock", "Indie Rock", "Thai Rock"}:
        genre_interaction = "Use the grit confidently with firm attack and live-band energy while keeping Thai words clear."
    elif label == "raspy rock male vocal":
        genre_interaction = "Blend rasp selectively on emotional peaks; soften the attack enough to preserve the selected genre identity."
    elif label == "airy dreamy female vocal" and canonical_genre in {"Dream Pop", "Synth Pop", "Lo-fi Pop", "City Pop"}:
        genre_interaction = "Use polished airy phrasing that floats over the groove while the lead remains intelligible and centered."
    elif canonical_genre in {"R&B", "Soul", "Neo Soul"} and "intimate" in label:
        genre_interaction = "Fit smooth close phrasing into the laid-back pocket and avoid unnecessary power belting."
    elif canonical_genre == "ลูกทุ่งร่วมสมัย":
        genre_interaction = "Prioritize expressive storytelling, clear Thai diction and an accessible emotional melodic lift."
    elif canonical_genre == "เพื่อชีวิตร่วมสมัย":
        genre_interaction = "Keep the delivery direct, sincere and storytelling-first over the organic arrangement."
    elif base["gender_mode"] == "duet":
        genre_interaction = "Blend both voices naturally into the selected genre without replacing its rhythmic or instrumental identity."
    else:
        genre_interaction = f"Shape the vocal around the {canonical_genre} arrangement without changing its core identity."

    if canonical_mood in {"เหงา", "เหงากลางคืน", "สงบ"}:
        mood_interaction = "Move closer and more restrained in the verses, leaving personal space around each phrase."
    elif canonical_mood in {"ให้กำลังใจ", "ฮึกเหิม", "มีพลัง", "Inspirational"}:
        mood_interaction = "Use stronger projection and a confident chorus lift while retaining controlled diction."
    elif canonical_mood in {"เศร้า", "อกหัก", "คิดถึง", "Bittersweet"}:
        mood_interaction = "Use a softer attack and emotionally detailed phrasing, then widen naturally at the main payoff."
    elif canonical_mood == "สดใส":
        mood_interaction = "Use brighter delivery and especially clear articulation without becoming harsh."
    elif canonical_mood == "Epic":
        mood_interaction = "Expand the dynamic range and reserve the strongest projection for the final chorus."
    else:
        mood_interaction = "Keep the selected vocal character consistent while following the song's emotional movement."

    if base["gender_mode"] == "duet" and label == "duet male and female":
        songwriting_guidance = "Allow complementary perspectives, occasional natural call-and-response and a shared chorus; never force mechanical alternation in every section."
    elif base["gender_mode"] == "duet":
        songwriting_guidance = "Keep one primary perspective, add occasional response lines and use restrained harmony support in the chorus."
    elif "intimate" in label or label == "soft female vocal":
        songwriting_guidance = "Favor conversational Thai phrasing and personal verse lines, with a controlled singable chorus."
    elif "powerful" in label:
        songwriting_guidance = "Favor concise strong chorus lines that support projection, sustained notes and a clear final payoff."
    elif "airy" in label:
        songwriting_guidance = "Allow flowing sustained phrases but keep Thai words concise and understandable."
    elif "raspy" in label:
        songwriting_guidance = "Favor direct rhythmic lines and reserve grit for emphasis rather than every syllable."
    else:
        songwriting_guidance = "Use natural conversational Thai phrasing shaped for the selected delivery and chorus lift."

    profile = {
        "label": label,
        **base,
        "genre_interaction": genre_interaction,
        "mood_interaction": mood_interaction,
        "songwriting_guidance": songwriting_guidance,
    }
    profile["style_direction"] = (
        f"{label}: {base['delivery']}. Texture: {base['texture']}, {base['breathiness']}, {base['rasp']}; {base['diction']}. "
        f"Power and intimacy: {base['power']}; {base['intimacy']}. "
        f"Dynamics: {base['dynamic_behavior']}; chorus: {base['chorus_behavior']}. "
        f"Harmony: {base['harmony_behavior']}. {mood_interaction} {genre_interaction}"
    )
    return profile


def _recommended_bpm(tempo_range: tuple[int, int], position: float) -> int:
    low, high = tempo_range
    raw = low + ((high - low) * max(0.0, min(1.0, position)))
    bpm = int(round(raw / 2.0) * 2)
    return max(low, min(high, bpm))


def resolve_song_production_profile(
    *,
    genre: str,
    mood: str,
    vocal: str,
    manual_style_override: str = "",
    song_idea: str = "",
) -> dict[str, Any]:
    selected_genre = str(genre or "Modern Pop").strip() or "Modern Pop"
    selected_mood = str(mood or "Balanced").strip() or "Balanced"
    selected_vocal = str(vocal or "natural lead vocal").strip() or "natural lead vocal"
    canonical_genre = _canonical_genre(selected_genre)
    canonical_mood = _canonical_mood(selected_mood)
    base = dict(GENRE_PROFILES[canonical_genre])
    modifier = dict(MOOD_MODIFIERS[canonical_mood])
    vocal_profile = resolve_vocal_profile(vocal=selected_vocal, genre=selected_genre, mood=selected_mood)
    tempo_range = tuple(base["tempo_range"])
    bpm = _recommended_bpm(tempo_range, float(modifier["tempo_position"]))
    prompt_genre = str(base.get("prompt_genre") or canonical_genre)
    override = " ".join(str(manual_style_override or "").split()).strip(" ,.;")
    intelligence = select_production_intelligence_profile(
        canonical_genre=canonical_genre,
        canonical_mood=canonical_mood,
        vocal=selected_vocal,
        song_idea=song_idea,
    )
    internal_profile = dict(intelligence.get("profile") or {})
    if internal_profile:
        internal_range = tuple(internal_profile.get("bpm_range") or tempo_range)
        refined_range = (max(tempo_range[0], internal_range[0]), min(tempo_range[1], internal_range[1]))
        if refined_range[0] <= refined_range[1]:
            bpm = _recommended_bpm(refined_range, float(modifier["tempo_position"]))
        palette = list(internal_profile.get("main_instruments") or ()) + list(internal_profile.get("supporting_instruments") or ())
        instrument_palette = list(dict.fromkeys(palette)) or list(base["instrument_palette"])
        rhythmic_feel = str(internal_profile.get("rhythm_character") or base["rhythmic_feel"])
        energy = f"{base['energy']}; {modifier['energy_modifier']}"
        arrangement_character = f"{internal_profile.get('arrangement_character') or base['arrangement_character']}; {modifier['arrangement_modifier']}"
        production_notes = f"{internal_profile.get('production_finish') or base['production_notes']}; {modifier['production_modifier']}"
    else:
        instrument_palette = list(base["instrument_palette"])
        rhythmic_feel = base["rhythmic_feel"]
        energy = f"{base['energy']}; {modifier['energy_modifier']}"
        arrangement_character = f"{base['arrangement_character']}; {modifier['arrangement_modifier']}"
        production_notes = f"{base['production_notes']}; {modifier['production_modifier']}"
    profile = {
        "genre": selected_genre,
        "mood": selected_mood,
        "canonical_genre": canonical_genre,
        "canonical_mood": canonical_mood,
        "mood_character": modifier["english_label"],
        "tempo_min": tempo_range[0],
        "tempo_max": tempo_range[1],
        "recommended_bpm": bpm,
        "instrument_palette": instrument_palette,
        "rhythmic_feel": rhythmic_feel,
        "energy": energy,
        "arrangement_character": arrangement_character,
        "production_notes": production_notes,
        "vocal_direction": selected_vocal,
        "vocal_profile": vocal_profile,
        "songwriting_guidance": vocal_profile["songwriting_guidance"],
        "manual_style_override": override,
        "production_intelligence_selected_profile": str(internal_profile.get("id") or ""),
        "production_intelligence_sub_style": str(internal_profile.get("sub_style") or ""),
        "production_intelligence": {
            "matched": bool(internal_profile),
            "candidate_count": int(intelligence.get("candidate_count") or 0),
            "selection_score": int(intelligence.get("score") or 0),
            "selection_reason": str(intelligence.get("selection_reason") or ""),
            "genre_match": canonical_genre,
            "mood_match": canonical_mood if internal_profile else "",
            "cue_matches": list(intelligence.get("cue_matches") or []),
        },
    }
    if internal_profile:
        core = (
            f"{prompt_genre}, {internal_profile['sub_style']}, around {bpm} BPM. "
            f"Mood: {modifier['english_label']}. Instruments: {', '.join(profile['instrument_palette'])}. "
            f"Groove: {profile['rhythmic_feel']}; bass: {internal_profile['bass_character']}. "
            f"Atmosphere and texture: {internal_profile['atmosphere']}; {internal_profile['texture']}. "
            f"Vocal production: {vocal_profile['style_direction']} "
            f"Arrangement: {profile['arrangement_character']}; chorus: {internal_profile['chorus_energy']}. "
            f"Production: {profile['production_notes']}."
        )
    else:
        core = (
            f"{prompt_genre} around {bpm} BPM with {', '.join(profile['instrument_palette'])}. "
            f"Use a {profile['rhythmic_feel']}; {modifier['english_label']} mood; {profile['energy']}. "
            f"Vocal production: {vocal_profile['style_direction']} Arrangement: {profile['arrangement_character']}. "
            f"Production: {profile['production_notes']}."
        )
    if override:
        core = (
            f"{prompt_genre} around {bpm} BPM. Mood direction: {modifier['english_label']}. "
            f"Vocal production: {vocal_profile['style_direction']} Manual production direction: {override}. "
            f"Retain the selected {prompt_genre} identity and a coherent full-song arrangement."
        )
    profile["style_prompt"] = core
    return profile


def production_profile_in_range(profile: dict[str, Any]) -> bool:
    bpm = int(profile.get("recommended_bpm") or 0)
    return int(profile.get("tempo_min") or 0) <= bpm <= int(profile.get("tempo_max") or 0)
