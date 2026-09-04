from __future__ import annotations

from typing import Any


THEME_CUES: dict[str, tuple[str, ...]] = {
    "home_family": ("home", "hometown", "family", "parents", "village", "countryside", "บ้าน", "บ้านเกิด", "ครอบครัว", "พ่อ", "แม่", "ต่างจังหวัด", "ชนบท", "หมู่บ้าน", "ไกลบ้าน"),
    "night_city": ("night", "midnight", "2am", "neon", "city", "late night", "กลางคืน", "เที่ยงคืน", "ตีสอง", "นีออน", "เมือง", "ขับรถดึก"),
    "hope_fight": ("hope", "fight", "keep going", "encourage", "rise", "หวัง", "สู้", "ไม่ยอมแพ้", "ไปต่อ", "ให้กำลังใจ", "เริ่มใหม่"),
    "travel_freedom": ("travel", "road", "trip", "sea", "freedom", "summer", "เดินทาง", "ถนน", "ทริป", "ทะเล", "อิสระ", "หน้าร้อน"),
    "rain_memory": ("rain", "memory", "past", "miss", "longing", "old photo", "ฝน", "ความทรงจำ", "วันเก่า", "คิดถึง", "รูปเก่า", "อดีต"),
    "love_warmth": ("love", "romance", "warm", "couple", "รัก", "โรแมนติก", "อบอุ่น", "คนรัก", "แฟน"),
    "heartbreak": ("breakup", "heartbreak", "goodbye", "left", "เลิก", "อกหัก", "จากลา", "ไม่กลับมา", "แยกทาง"),
    "work_pressure": ("office", "deadline", "boss", "work", "burnout", "ออฟฟิศ", "หัวหน้า", "งาน", "เดดไลน์", "หมดไฟ"),
    "confidence": ("confident", "victory", "celebrate", "win", "มั่นใจ", "ชนะ", "ฉลอง", "สำเร็จ", "ภูมิใจ"),
}


def _profile(
    profile_id: str,
    genre: str,
    sub_style: str,
    moods: tuple[str, ...],
    themes: tuple[str, ...],
    bpm_range: tuple[int, int],
    main: tuple[str, ...],
    supporting: tuple[str, ...],
    rhythm: str,
    bass: str,
    vocal: str,
    atmosphere: str,
    texture: str,
    chorus: str,
    arrangement: str,
    finish: str,
    *,
    vocal_cues: tuple[str, ...] = (),
    avoid_moods: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "id": profile_id,
        "genre": genre,
        "sub_style": sub_style,
        "suitable_moods": moods,
        "suitable_themes": themes,
        "tempo_feel": f"{bpm_range[0]}-{bpm_range[1]} BPM feel",
        "bpm_range": bpm_range,
        "main_instruments": main,
        "supporting_instruments": supporting,
        "rhythm_character": rhythm,
        "bass_character": bass,
        "vocal_character": vocal,
        "vocal_cues": vocal_cues,
        "atmosphere": atmosphere,
        "texture": texture,
        "chorus_energy": chorus,
        "arrangement_character": arrangement,
        "production_finish": finish,
        "avoid_moods": avoid_moods,
    }


PRODUCTION_INTELLIGENCE_PROFILES: tuple[dict[str, Any], ...] = (
    _profile("pop_bright_escape", "Pop", "Bright Feel-Good Pop", ("สดใส", "มีพลัง", "ให้กำลังใจ", "หวังใหม่"), ("travel_freedom", "confidence", "hope_fight"), (104, 118), ("bright clean guitar", "polished pop drums", "modern bass"), ("light synth hooks", "handclaps"), "buoyant straight pop pulse", "melodic and springy", "clear phrasing with a smiling lift", "sunlit and open", "clean colorful layers", "immediate wide singalong lift", "compact verse, quick pre-chorus rise, open chorus", "bright radio polish with controlled transients", avoid_moods=("เศร้า", "อกหัก", "มืดหม่น")),
    _profile("pop_night_drive", "Pop", "Intimate Night-Drive Pop", ("เหงา", "เหงากลางคืน", "คิดถึง", "Bittersweet", "Nostalgic"), ("night_city", "rain_memory", "heartbreak"), (88, 104), ("muted electric guitar", "warm synth bass", "restrained pop drums"), ("electric piano", "soft neon pads"), "steady late-night pulse with soft syncopation", "deep, smooth and controlled", "close verses with a restrained emotional rise", "nocturnal and reflective", "glossy low-light ambience", "controlled chorus bloom rather than a bright explosion", "sparse opening, gradual layer growth, lingering outro", "warm vocal-forward mix with spacious depth", vocal_cues=("intimate", "soft", "airy"), avoid_moods=("ฮึกเหิม",)),
    _profile("pop_warm_romance", "Pop", "Warm Romantic Pop", ("โรแมนติก", "อบอุ่น", "ละมุน"), ("love_warmth", "home_family"), (92, 108), ("clean guitar", "soft piano", "rounded bass"), ("gentle pop drums", "subtle strings"), "relaxed melodic pop groove", "rounded and supportive", "natural intimate lead with tender harmony", "warm and reassuring", "organic polish with soft edges", "melodic emotional lift with restrained harmony", "close verse, tender pre-chorus, warm full chorus", "smooth commercial finish with clear vocal focus"),
    _profile("rock_modern_anthem", "Rock", "Modern Uplifting Rock Anthem", ("ฮึกเหิม", "มีพลัง", "ให้กำลังใจ", "หวังใหม่", "Inspirational", "Epic"), ("hope_fight", "confidence"), (116, 140), ("distorted electric guitars", "powerful acoustic drums", "live bass"), ("supporting piano", "gang accents"), "forward live-rock drive with firm backbeat", "punchy and locked to the kick", "strong projection supported without changing vocal identity", "determined and expansive", "wide live-band impact", "large anthemic lift with layered guitars", "riff-led verse, rising drums, full-band chorus, biggest final chorus", "firm modern rock master with vocal clarity", vocal_cues=("powerful", "raspy"), avoid_moods=("สงบ", "ฝัน ๆ")),
    _profile("rock_emotional_lift", "Rock", "Emotional Pop-Rock Ballad", ("เศร้า", "อกหัก", "คิดถึง", "Bittersweet", "Nostalgic"), ("heartbreak", "rain_memory", "love_warmth"), (88, 108), ("clean-to-driven electric guitars", "live bass", "dynamic drums"), ("acoustic guitar", "supporting piano"), "restrained verse groove growing into live-band drive", "warm and steady before opening in the chorus", "intimate storytelling that widens at the payoff", "emotionally direct and cinematic without excess", "organic guitar layers and human dynamics", "wide emotional chorus with melodic counterlines", "acoustic or clean intro, patient build, vulnerable bridge, large final chorus", "warm Spotify-ready pop-rock balance"),
    _profile("rock_open_road", "Rock", "Open-Road Folk Rock", ("สดใส", "อบอุ่น", "ให้กำลังใจ"), ("travel_freedom", "home_family"), (102, 124), ("acoustic strumming", "clean electric guitar", "live drums"), ("warm bass", "organ accents"), "rolling road-trip rock groove", "warm and mobile", "direct conversational delivery", "open-air and optimistic", "organic room energy", "communal chorus lift", "story-led verse into a broad uncomplicated chorus", "natural live-band finish"),
    _profile("poprock_modern_anthem", "Pop Rock", "Modern Uplifting Pop Rock", ("ฮึกเหิม", "มีพลัง", "ให้กำลังใจ", "หวังใหม่", "Inspirational"), ("hope_fight", "confidence", "travel_freedom"), (104, 124), ("clean and driven electric guitars", "tight pop-rock drums", "live bass"), ("supporting piano", "subtle synth lift"), "driving commercial live pop-rock groove", "smooth in verses and firmer in choruses", "clear lead building toward confident projection", "uplifting and forward", "polished live-band layers", "wide hook-led full-band release", "restrained verse, rising pre-chorus, broad final chorus", "radio-ready guitar clarity and controlled loudness", avoid_moods=("มืดหม่น",)),
    _profile("poprock_nostalgic", "Pop Rock", "Nostalgic Emotional Pop Rock", ("คิดถึง", "เศร้า", "อกหัก", "Bittersweet", "Nostalgic"), ("rain_memory", "heartbreak", "home_family"), (84, 104), ("acoustic guitar", "clean electric guitar", "warm live bass"), ("soft piano", "restrained drum kit", "warm pad"), "patient mid-tempo pop-rock pulse", "smooth and supportive", "close emotional verses with an open chorus", "warm, reflective and human", "acoustic detail growing into layered guitars", "dynamic emotional lift with melodic guitar response", "acoustic intro, controlled build, half-time bridge, larger final chorus", "warm vocal-forward streaming mix"),
    _profile("rnb_midnight_intimate", "R&B", "Midnight Intimate R&B", ("เหงา", "เหงากลางคืน", "โรแมนติก", "ละมุน"), ("night_city", "love_warmth", "heartbreak"), (70, 86), ("warm electric piano", "deep controlled bass", "restrained drums"), ("atmospheric synth texture", "minimal clean guitar"), "laid-back pocket with subtle late-night syncopation", "deep, sustained and uncluttered", "close-mic nuanced phrasing with space between lines", "private and nocturnal", "soft low-light detail", "smooth chorus expansion without breaking intimacy", "minimal verse, gradual harmony bloom, stripped bridge", "dark-warm modern R&B mix with clean vocal presence", vocal_cues=("intimate", "soft", "warm"), avoid_moods=("ฮึกเหิม",)),
    _profile("rnb_nostalgic_soul", "R&B", "Nostalgic Soulful R&B", ("คิดถึง", "เศร้า", "อกหัก", "Bittersweet", "Nostalgic"), ("rain_memory", "heartbreak", "love_warmth"), (68, 84), ("Rhodes electric piano", "deep controlled bass", "laid-back drums"), ("expressive clean guitar", "soft harmony pads"), "behind-the-beat soulful pocket", "melodic and warm", "emotionally detailed delivery with restrained runs", "nostalgic and intimate", "warm harmonic color and soft transients", "rich but controlled harmony lift", "spacious verse, soulful chorus, exposed bridge, resolved final chorus", "warm analog-inspired finish with modern low-end control"),
    _profile("rnb_feel_good", "R&B", "Feel-Good Contemporary R&B", ("สดใส", "อบอุ่น", "มีพลัง"), ("confidence", "travel_freedom", "love_warmth"), (86, 100), ("bright electric piano", "melodic bass", "crisp restrained drums"), ("clean funk guitar", "light synth accents"), "buoyant syncopated R&B groove", "mobile and melodic", "relaxed confident phrasing", "warm and sociable", "clean rhythmic detail", "catchy harmony-led lift", "groove-first verse and concise melodic chorus", "polished contemporary finish without overcompression"),
    _profile("citypop_bright", "City Pop", "Bright Metropolitan City Pop", ("สดใส", "มีพลัง", "โรแมนติก"), ("travel_freedom", "confidence", "love_warmth"), (102, 118), ("clean funk guitar", "electric piano", "melodic bass", "polished drums"), ("brass accents", "analog synth colors"), "syncopated city-pop groove with crisp pocket", "active and melodic", "clear rhythmic phrasing over the groove", "sunlit metropolitan motion", "colorful retro-modern harmony", "bright melodic chorus with disciplined layers", "groove-led verse, short lift, polished chorus and instrumental turnaround", "clean retro-modern sheen with tight low end"),
    _profile("citypop_neon", "City Pop", "Neon Night City Pop", ("เหงากลางคืน", "คิดถึง", "Bittersweet", "Nostalgic", "ฝัน ๆ"), ("night_city", "rain_memory", "heartbreak"), (92, 106), ("muted funk guitar", "electric piano", "melodic bass", "polished drums"), ("analog pads", "saxophone accents"), "restrained syncopated night groove", "melodic with a smooth low register", "intimate phrasing that stays rhythmically precise", "neon-lit and wistful", "glossy ambience with vintage color", "elegant chorus bloom rather than a hard impact", "late-night intro, groove-led verses, luminous final chorus", "polished wide mix with warm vintage depth"),
    _profile("acoustic_warm_reflection", "Acoustic Pop", "Warm Reflective Acoustic Pop", ("อบอุ่น", "คิดถึง", "ละมุน", "สงบ", "Bittersweet"), ("home_family", "rain_memory", "love_warmth"), (72, 92), ("fingerpicked acoustic guitar", "soft piano", "warm bass"), ("brush percussion", "subtle strings"), "gentle human acoustic pulse", "soft and supportive", "close natural storytelling delivery", "quiet, warm and reflective", "organic room detail", "open but restrained emotional lift", "bare opening, gradually added percussion, intimate bridge, warm final chorus", "natural acoustic finish with vocal intimacy"),
    _profile("acoustic_open_road", "Acoustic Pop", "Open-Road Acoustic Pop", ("สดใส", "ให้กำลังใจ", "หวังใหม่"), ("travel_freedom", "hope_fight"), (88, 100), ("acoustic strumming", "hand percussion", "warm bass"), ("clean guitar accents", "light piano"), "easy forward acoustic groove", "rounded and moving", "relaxed conversational lead", "open-air and hopeful", "bright organic texture", "simple communal chorus lift", "story verse, natural rhythmic build, uncluttered final chorus", "clear acoustic-pop polish"),
    _profile("dreampop_nocturnal", "Dream Pop", "Nocturnal Dream Pop", ("ฝัน ๆ", "เหงากลางคืน", "เหงา", "คิดถึง", "ลึกลับ"), ("night_city", "rain_memory", "heartbreak"), (76, 92), ("shimmering guitars", "airy pads", "rounded bass"), ("soft electronic drums", "reversed textures"), "floating slow pulse", "rounded and unobtrusive", "airy or intimate delivery kept intelligible", "spacious, dreamy and nocturnal", "hazy layers with soft edges", "blooming chorus that keeps its dreamlike space", "slow reveal, suspended bridge, widest final bloom", "wide atmospheric finish with clear centered vocal", vocal_cues=("airy", "soft", "intimate"), avoid_moods=("ฮึกเหิม", "โกรธ")),
    _profile("dreampop_bright_haze", "Dream Pop", "Bright Dream-Pop Haze", ("สดใส", "ละมุน", "หวังใหม่", "ฝัน ๆ"), ("travel_freedom", "love_warmth", "hope_fight"), (88, 106), ("chorused guitars", "airy pads", "soft electronic drums"), ("melodic rounded bass", "sparkling synth accents"), "floating mid-tempo pulse", "melodic and gentle", "light phrasing with a clear melodic center", "dreamy but hopeful", "shimmering spacious layers", "radiant chorus bloom", "hazy verse opening into a bright layered final chorus", "soft wide polish without losing definition"),
    _profile("hiphop_reflective", "Hip-Hop", "Reflective Story Hip-Hop", ("คิดถึง", "Bittersweet", "กดดัน", "สงบ"), ("work_pressure", "home_family", "rain_memory"), (72, 90), ("kick-snare beat", "deep bass", "atmospheric keys"), ("sample-like texture", "restrained guitar"), "steady head-nod pocket with room for words", "deep and disciplined", "conversational rhythmic delivery", "grounded and reflective", "sparse cinematic detail", "concise melodic hook with added weight", "narrative verses, short hook, stripped truth section", "clean low end and dry intelligible vocal"),
    _profile("hiphop_confident", "Hip-Hop", "Confident Modern Hip-Hop", ("ฮึกเหิม", "มีพลัง", "ให้กำลังใจ"), ("confidence", "hope_fight"), (84, 100), ("punchy kick and snare", "deep bass", "focused synth motif"), ("tight hi-hats", "minimal brass accents"), "assertive modern hip-hop pocket", "punchy and controlled", "confident articulation without forced aggression", "focused and energetic", "clean sparse impact", "strong compact hook", "direct verse movement with a decisive final hook", "loud-clear modern finish with disciplined sub bass", vocal_cues=("powerful", "raspy"), avoid_moods=("สงบ",)),
    _profile("edm_bright_drive", "Electronic Pop", "Bright Dance-Pop Drive", ("สดใส", "มีพลัง", "ฮึกเหิม"), ("travel_freedom", "confidence", "hope_fight"), (116, 128), ("bright synth layers", "four-on-the-floor drums", "synth bass"), ("hook plucks", "vocal chops used sparingly"), "clean four-on-the-floor pulse", "firm sidechained movement", "clear lead protected from dense synth layers", "bright and kinetic", "crisp electronic detail", "high-energy melodic drop-like chorus", "compact verse, rising build, full chorus, clean breakdown", "club-capable clarity with commercial vocal balance", avoid_moods=("สงบ", "เศร้า")),
    _profile("edm_emotional_night", "Electronic Pop", "Emotional Night Electronic Pop", ("เหงากลางคืน", "คิดถึง", "Bittersweet", "ฝัน ๆ"), ("night_city", "rain_memory", "heartbreak"), (100, 116), ("atmospheric synths", "restrained electronic drums", "deep synth bass"), ("piano motif", "textural effects"), "measured electronic pulse with gradual lift", "deep and controlled", "intimate verse vocal opening into a wider chorus", "nocturnal and emotional", "spacious synth depth", "wide emotional electronic lift", "minimal intro, layered build, spacious breakdown, largest final chorus", "polished modern electronic finish without harsh highs"),
    _profile("lukthung_hometown", "ลูกทุ่งร่วมสมัย", "Hometown Nostalgic Luk Thung", ("คิดถึง", "อบอุ่น", "เศร้า", "Nostalgic"), ("home_family", "rain_memory"), (78, 94), ("acoustic guitar", "warm melodic bass", "organic drums"), ("subtle khaen accents", "selective phin answers"), "gentle Thai country storytelling groove", "warm and melodic", "clear expressive Thai storytelling", "rural, familiar and heartfelt", "organic acoustic detail with restrained regional color", "direct melodic chorus with human lift", "scene-led verse, regional accents as responses, warm final chorus", "modern clarity while retaining authentic Thai country warmth"),
    _profile("lukthung_modern_romance", "ลูกทุ่งร่วมสมัย", "Modern Romantic Luk Thung", ("โรแมนติก", "ละมุน", "อบอุ่น"), ("love_warmth",), (86, 104), ("acoustic guitar", "clean electric guitar", "polished live drums"), ("melodic bass", "subtle synth texture"), "accessible contemporary Thai country-pop groove", "smooth and melodic", "warm expressive delivery with clear Thai diction", "romantic and polished", "organic core with light modern sheen", "catchy direct chorus lift", "conversational verse, clean build, memorable modern chorus", "streaming-ready Thai country finish without forced regional instruments"),
    _profile("lukthung_road_bright", "ลูกทุ่งร่วมสมัย", "Bright Luk Thung Road Trip", ("สดใส", "มีพลัง", "ให้กำลังใจ"), ("travel_freedom", "hope_fight"), (98, 114), ("bright acoustic guitar", "clean electric fills", "lively organic drums"), ("warm bass", "selective phin accents"), "rolling upbeat Thai country groove", "mobile and warm", "friendly direct storytelling delivery", "open-road and cheerful", "bright organic movement", "easy communal singalong lift", "quick scene-led verses and an early upbeat chorus", "clean lively modern luk thung polish", avoid_moods=("อกหัก", "มืดหม่น")),
    _profile("phueachiwit_grounded", "เพื่อชีวิตร่วมสมัย", "Grounded Social Storytelling", ("กดดัน", "คิดถึง", "สงบ", "Bittersweet"), ("work_pressure", "home_family", "rain_memory"), (76, 96), ("acoustic guitar", "organic drums", "warm bass"), ("restrained electric guitar", "harmonica accents"), "grounded organic storytelling pulse", "steady and natural", "direct sincere narration-first delivery", "earthy and observant", "unpolished human room detail", "sincere communal chorus rather than spectacle", "narrative verse, tension-building middle, honest final chorus", "natural band dynamics and clear words"),
    _profile("phueachiwit_uplifting", "เพื่อชีวิตร่วมสมัย", "Uplifting Communal Phuea Chiwit", ("ให้กำลังใจ", "ฮึกเหิม", "หวังใหม่", "สดใส"), ("hope_fight", "travel_freedom", "home_family"), (92, 112), ("acoustic strumming", "firm organic drums", "live bass"), ("electric guitar lift", "communal backing vocals"), "steady forward folk-rock pulse", "warm and firm", "sincere delivery growing into shared strength", "hopeful and grounded", "organic live-band momentum", "broad communal singalong release", "story verse, steady escalation, large but honest final chorus", "open natural master with vocal intelligibility", avoid_moods=("มืดหม่น",)),
    _profile("jazz_late_night", "Jazz", "Late-Night Vocal Jazz", ("เหงากลางคืน", "คิดถึง", "โรแมนติก", "สงบ"), ("night_city", "rain_memory", "love_warmth"), (68, 88), ("acoustic piano", "upright bass", "brush drums"), ("muted trumpet accents", "clean jazz guitar"), "relaxed swing or brushed ballad pocket", "walking lightly or sustaining beneath the vocal", "intimate phrasing with natural timing", "late-night and sophisticated", "warm live-room detail", "subtle harmonic lift led by the vocal", "spacious verse, tasteful instrumental answers, resolved final refrain", "natural jazz dynamics with a close vocal image", vocal_cues=("intimate", "warm", "soft"), avoid_moods=("ฮึกเหิม",)),
    _profile("jazz_bright_swing", "Jazz", "Bright Contemporary Swing", ("สดใส", "มีพลัง", "อบอุ่น"), ("confidence", "travel_freedom", "love_warmth"), (100, 126), ("acoustic piano", "upright bass", "crisp live drums"), ("clean jazz guitar", "light brass accents"), "lively contemporary swing pocket", "mobile and melodic", "clear playful phrasing", "bright and urbane", "clean live ensemble detail", "joyful melodic lift with tasteful ensemble accents", "compact verse, instrumental response, lively final refrain", "polished live jazz finish without overcompression"),
)


def extract_production_cues(song_idea: str) -> list[str]:
    text = " ".join(str(song_idea or "").lower().split())
    if not text:
        return []
    return [name for name, terms in THEME_CUES.items() if any(term.lower() in text for term in terms)]


def select_production_intelligence_profile(
    *,
    canonical_genre: str,
    canonical_mood: str,
    vocal: str,
    song_idea: str = "",
) -> dict[str, Any]:
    candidates = [dict(profile) for profile in PRODUCTION_INTELLIGENCE_PROFILES if profile["genre"] == canonical_genre]
    cues = extract_production_cues(song_idea)
    vocal_lower = str(vocal or "").lower()
    ranked: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, profile in enumerate(candidates):
        reasons = ["genre"]
        score = 45
        mood_compatible = canonical_mood in profile["suitable_moods"]
        if mood_compatible:
            score += 24
            reasons.append("mood")
        matched_cues = [cue for cue in cues if cue in profile["suitable_themes"]]
        if matched_cues:
            score += min(24, 9 * len(matched_cues))
            reasons.extend(matched_cues)
        vocal_matches = [cue for cue in profile.get("vocal_cues", ()) if cue in vocal_lower]
        if vocal_matches:
            score += min(7, 3 * len(vocal_matches))
            reasons.append("vocal support")
        if canonical_mood in profile.get("avoid_moods", ()):
            score -= 50
            reasons.append("mood conflict")
        ranked.append((score if mood_compatible else min(score, 64), -index, profile, reasons))
    if not ranked:
        return {
            "matched": False,
            "profile": {},
            "candidate_count": 0,
            "score": 0,
            "cue_matches": cues,
            "selection_reason": "No compatible internal profile; Phase 5G fallback retained.",
        }
    score, _order, selected, reasons = max(ranked, key=lambda item: (item[0], item[1]))
    matched = score >= 65
    return {
        "matched": matched,
        "profile": selected if matched else {},
        "candidate_count": len(candidates),
        "score": score,
        "cue_matches": [cue for cue in cues if cue in selected.get("suitable_themes", ())],
        "selection_reason": (
            f"Selected from {len(candidates)} {canonical_genre} profiles using {', '.join(reasons)}."
            if matched
            else "No confident Genre/Mood/Idea match; Phase 5G fallback retained."
        ),
    }
