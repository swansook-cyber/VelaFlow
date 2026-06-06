from __future__ import annotations

from datetime import datetime
from typing import Any


PODCAST_SCRIPT_TONES = ["Vela After Work", "Dark Humor", "Emotional", "Motivational", "Storytelling", "Office Rant"]
PODCAST_NARRATORS = ["Male", "Female"]
PODCAST_EPISODE_LENGTHS = ["10 min", "20 min", "30 min"]

REQUIRED_PODCAST_SCRIPT_SECTIONS = [
    "Episode Title",
    "Cold Open",
    "Full Podcast Script",
    "AI Voice Version",
    "Viral Rant Engine",
    "Shorts Extraction",
    "YouTube Package",
    "Spotify Package",
    "Thumbnail Prompt",
    "AI Video Prompt",
]

WORD_TARGETS = {
    "10 min": {"min": 1500, "max": 2000, "target": 1650, "shorts": 10},
    "20 min": {"min": 3000, "max": 4000, "target": 3300, "shorts": 10},
    "30 min": {"min": 4500, "max": 6000, "target": 4800, "shorts": 10},
}


def _clean(value: str, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _word_count(text: str) -> int:
    return len([part for part in str(text or "").replace("\n", " ").split(" ") if part.strip()])


def _tone_profile(tone: str) -> dict[str, str]:
    profiles = {
        "Vela After Work": {
            "style": "office life, workplace politics, burnout, unspoken office stories, dark humor, relatable emotional storytelling",
            "voice": "เล่าเหมือนคนทำงานนั่งคุยหลังเลิกงาน เหนื่อยจริง ตลกร้ายจริง แต่ยังอ่อนโยนกับคนฟัง",
        },
        "Dark Humor": {
            "style": "dry office humor, quiet sarcasm, emotional truth under a tired smile",
            "voice": "ขำแห้งแบบคนที่ยังต้องเปิดคอมพรุ่งนี้ ทั้งที่ใจอยากปิดระบบทั้งชีวิต",
        },
        "Emotional": {
            "style": "soft emotional storytelling, vulnerable reflection, human workplace loneliness",
            "voice": "เล่านุ่ม ลึก ไม่เร่ง ให้คนฟังมีพื้นที่นึกถึงตัวเอง",
        },
        "Motivational": {
            "style": "grounded encouragement, no fake hustle, quiet self-respect",
            "voice": "ให้กำลังใจแบบไม่ขายฝัน เหมือนเพื่อนร่วมงานที่รู้ว่าเราเหนื่อยจริง",
        },
        "Storytelling": {
            "style": "scene-based office story, cinematic but conversational",
            "voice": "เล่าเป็นฉาก มีโต๊ะทำงาน ไฟเพดาน แชตค้าง และความเงียบหลังเลิกงาน",
        },
        "Office Rant": {
            "style": "sharp workplace rant, honest, contained anger, still human",
            "voice": "ระบายตรง คม แต่ไม่หยาบพร่ำเพรื่อ เหมือนพูดในรถหลังประชุมจบ",
        },
    }
    return profiles.get(tone, profiles["Vela After Work"])


def _narrator_voice(narrator: str) -> str:
    if narrator == "Female":
        return "เสียงผู้หญิงอบอุ่น นิ่ง เหนื่อยนิด ๆ แต่ชัดเจน เว้นวรรคเหมือนกำลังเล่าเรื่องที่เก็บมาทั้งวัน"
    return "เสียงผู้ชายอบอุ่น ปนเหนื่อยเล็ก ๆ เล่าเหมือนนั่งคุยกันหลังปิดคอม ไม่ประกาศ ไม่ฝืนสดใส"


def _title_candidates(topic: str, tone: str) -> list[str]:
    core = topic.strip(" .") or "เรื่องหลังเลิกงาน"
    candidates = [
        "หลังเลิกงานค่อยรู้สึก",
        "ประชุมจบ แต่ใจไม่จบ",
        "เรื่องที่เราไม่พูดในออฟฟิศ",
        "วันที่งานไม่ใช่เรื่องหนักที่สุด",
        "โต๊ะทำงานที่เก็บความเงียบไว้",
        "ยิ้มให้ทั้งวัน แล้วพังคนเดียว",
        "ชีวิตที่ซ่อนอยู่ในปฏิทินงาน",
        "สิ่งที่คนทำงานไม่ค่อยพูด",
        f"{core} หลังหกโมงเย็น",
        "ไม่ได้หมดไฟ แค่หมดใจ",
    ]
    if tone == "Dark Humor":
        candidates.insert(0, "ขำไม่ออก แต่ต้องส่งงาน")
    if tone == "Office Rant":
        candidates.insert(0, "ไม่ใช่งานหนัก แต่คนมันหนัก")
    if tone == "Motivational":
        candidates.insert(0, "เหนื่อยได้ แต่อย่าหายไป")
    if tone == "Vela After Work":
        candidates.insert(0, "เรื่องที่คิดหลังปิดคอม")
    return candidates


def _score_title(title: str, topic: str) -> int:
    score = 70
    if 2 <= len(title.split()) <= 8:
        score += 10
    if any(token in title for token in ["หลังเลิกงาน", "ไม่พูด", "ไม่จบ", "หมดใจ", "ปิดคอม"]):
        score += 14
    if title.strip() == topic.strip() or len(title.strip()) <= 3:
        score -= 50
    if len(title) > 44:
        score -= 10
    return max(0, min(100, score))


def _best_title(topic: str, tone: str) -> str:
    scored = sorted(((candidate, _score_title(candidate, topic)) for candidate in _title_candidates(topic, tone)), key=lambda item: item[1], reverse=True)
    return scored[0][0]


def _avoid_topic_repeat(text: str, topic: str, max_mentions: int = 8) -> str:
    topic = str(topic or "").strip()
    if not topic:
        return text
    count = 0
    output = []
    replacements = ["เรื่องนี้", "ความรู้สึกนั้น", "สิ่งนั้น", "มัน"]
    for line in text.splitlines():
        while topic in line:
            count += 1
            if count <= max_mentions:
                break
            line = line.replace(topic, replacements[count % len(replacements)], 1)
        output.append(line)
    return "\n".join(output)


def _cold_open(topic: str, tone: str) -> str:
    if tone == "Dark Humor":
        specific = "ถ้าชีวิตการทำงานมีปุ่ม mute เราคงกดค้างไว้ตั้งแต่บ่ายสาม"
    elif tone == "Office Rant":
        specific = "บางวันเราไม่ได้อยากลาออกจากงาน แค่อยากลาออกจากความอดทนที่ถูกใช้งานหนักเกินไป"
    else:
        specific = "บางวันเราเดินออกจากออฟฟิศแล้วรู้สึกเหมือนยังมีทั้งห้องประชุมเดินตามกลับบ้าน"
    return "\n".join(
        [
            specific,
            "ไม่ใช่เพราะงานชิ้นเดียว ไม่ใช่เพราะแชตเดียว และไม่ใช่เพราะใครคนเดียวเสมอไป",
            "แต่มันคือการสะสมของประโยคเล็ก ๆ สีหน้าสั้น ๆ และความเงียบที่เราต้องกลืนไว้ทั้งวัน",
            "คืนนี้เราไม่ได้มาสรุปบทเรียนให้ดูเก่ง",
            "เรามาเล่าเรื่องที่หลายคนคิดหลังปิดคอม แต่ไม่ค่อยพูดออกมาดัง ๆ",
            "ถ้าคุณเคยยิ้มทั้งวัน แล้วกลับมาถามตัวเองว่าเราไหวจริงไหม ตอนนี้คุณไม่ได้ฟังอยู่คนเดียว",
        ]
    )


def _paragraph_bank(topic: str, tone: str) -> dict[str, list[str]]:
    profile = _tone_profile(tone)
    return {
        "Act 1: Setup": [
            f"เรื่องมันเริ่มธรรมดามาก เหมือนวันทำงานทั่วไปที่เราบอกตัวเองว่าเดี๋ยวก็ผ่านไป เราเปิดคอม ตอบข้อความ ดูปฏิทิน แล้วพยายามทำหน้าเหมือนทุกอย่างอยู่ในการควบคุม ทั้งที่ลึก ๆ มีบางอย่างเกี่ยวกับ {topic} ค้างอยู่ตรงอกตั้งแต่ยังไม่เที่ยง",
            "สิ่งที่น่าสนใจคือคนทำงานส่วนใหญ่ไม่ได้พังทันที เราพังแบบค่อย ๆ สุภาพขึ้น ค่อย ๆ เงียบขึ้น ค่อย ๆ ตอบสั้นลง แล้วก็ยังส่งงานตรงเวลาเหมือนเดิม จนไม่มีใครรู้ว่าข้างในเริ่มไม่มีพื้นที่ให้วางความรู้สึกแล้ว",
            "ในออฟฟิศ ทุกคนมีบทบาทของตัวเอง คนหนึ่งต้องเป็นคนใจเย็น คนหนึ่งต้องเป็นคนรับผิดชอบ คนหนึ่งต้องเป็นคนไม่เรื่องมาก และบางครั้งเราก็เล่นบทนั้นนานเกินไป จนลืมว่าตัวจริงของเราเหนื่อยเป็นเหมือนกัน",
            f"โทนของตอนนี้คือ {profile['voice']} ไม่ใช่เพื่อบ่นให้โลกดูแย่ลง แต่เพื่อยอมรับว่าหลายเรื่องในที่ทำงานมันหนัก เพราะเราไม่ค่อยได้รับอนุญาตให้พูดว่ามันหนัก",
        ],
        "Act 2: Conflict": [
            "ความขัดแย้งจริง ๆ ไม่ได้อยู่แค่ในห้องประชุม แต่อยู่ในใจตอนที่เราต้องเลือกระหว่างพูดความจริงกับรักษาบรรยากาศ เลือกระหว่างปกป้องตัวเองกับไม่ทำให้ใครลำบากใจ และสุดท้ายเรามักเลือกเงียบ เพราะความเงียบดูเป็นมืออาชีพกว่า",
            "ปัญหาคือความเงียบไม่ได้หายไป มันย้ายที่อยู่ จากปากมาอยู่ในไหล่ ในคอ ในการนอนที่ไม่สนิท และในความรู้สึกแปลก ๆ ตอนเห็น notification จากที่ทำงานเด้งขึ้นมาในวันหยุด",
            f"พอเรื่อง {topic} เกิดซ้ำ เราเริ่มสงสัยว่าหรือเราคิดมากไปเอง แต่คำถามนี้แหละที่ทำให้คนจำนวนมากเจ็บกว่าเดิม เพราะแทนที่จะได้พักจากเหตุการณ์ เรายังต้องสอบสวนความรู้สึกตัวเองอีกชั้นหนึ่ง",
            "บางคนในออฟฟิศไม่จำเป็นต้องเสียงดังเพื่อทำให้เรารู้สึกเล็กลง แค่ทำเหมือนสิ่งที่เราพูดไม่มีน้ำหนักพอ แค่ข้ามชื่อเราในเครดิตงาน แค่ชมคนอื่นในสิ่งที่เราทำ แล้วปล่อยให้เรายิ้มรับอย่างสุภาพ",
        ],
        "Act 3: Emotional Breakdown": [
            "จุดที่แตกจริง ๆ มักไม่ดราม่าเท่าในหนัง มันอาจเกิดตอนนั่งในรถ ตอนล้างแก้วกาแฟ หรือตอนปิดไฟห้องแล้วอยู่ ๆ น้ำตาก็มาแบบไม่มีพิธีการ เหมือนร่างกายพูดแทนใจว่า พอได้แล้ว",
            "เราไม่ได้ร้องไห้เพราะอ่อนแอ เราร้องไห้เพราะทั้งวันเราแข็งแรงเกินไป แข็งแรงตอนตอบว่าไม่เป็นไร แข็งแรงตอนยิ้ม แข็งแรงตอนรับงานเพิ่ม และแข็งแรงตอนเดินผ่านคนที่ทำให้เราเจ็บโดยไม่ให้สีหน้าหลุด",
            "ความตลกร้ายคือพรุ่งนี้เราก็อาจกลับไปทำเหมือนเดิมอีก เปิดคอมเหมือนเดิม ทักทายเหมือนเดิม ประชุมเหมือนเดิม แต่หลังจากคืนหนึ่งที่เราพังเงียบ ๆ เราจะรู้ว่าบางอย่างในใจไม่เหมือนเดิมแล้ว",
            "และบางที breakdown ไม่ได้แปลว่าทุกอย่างจบ มันอาจแปลว่าระบบข้างในกำลังปิดตัวเพื่อป้องกันไม่ให้เราเสียตัวเองไปมากกว่านี้",
        ],
        "Act 4: Reflection": [
            "พอมองย้อนกลับไป เราอาจพบว่าเราไม่ได้ต้องการให้ทุกคนเข้าใจทั้งหมด เราแค่อยากให้มีใครสักคนไม่รีบลดทอนความรู้สึกของเราให้เป็นคำว่า เรื่องเล็ก",
            "เรื่องเล็กสำหรับคนหนึ่ง อาจเป็นเรื่องที่สะสมมาหลายเดือนสำหรับอีกคน และในชีวิตการทำงาน สิ่งที่ทำร้ายเรามากที่สุดมักมาในรูปแบบที่ดูสุภาพพอจะไม่มีใครรับผิดชอบ",
            "นี่อาจเป็นเหตุผลที่ Vela After Work ต้องมีพื้นที่แบบนี้ พื้นที่ที่เราไม่ต้องเก่ง ไม่ต้องมีคำตอบครบ ไม่ต้องเปลี่ยนความเหนื่อยให้เป็นแรงบันดาลใจทันที แค่เล่ามันอย่างซื่อสัตย์ก่อน",
            "บางครั้งการเยียวยาไม่ได้เริ่มจากคำแนะนำ แต่มันเริ่มจากประโยคง่าย ๆ ว่า ใช่ มันหนักจริง และคุณไม่ได้คิดมากไปเอง",
        ],
        "Act 5: Takeaway": [
            "สิ่งที่อยากฝากไว้คือ อย่ารอให้ตัวเองพังก่อนถึงจะเชื่อว่าความเหนื่อยของคุณจริง ถ้าวันนี้อะไรบางอย่างหนักเกินไป คุณมีสิทธิ์ยอมรับมัน โดยไม่ต้องหาเหตุผลให้ใครอนุมัติ",
            "ลองเริ่มจากขอบเขตเล็ก ๆ สักอย่าง ตอบช้าลงเมื่อถึงเวลาพัก ปิด notification บางช่วง หรือพูดประโยคจริง ๆ กับตัวเองว่า วันนี้ฉันไม่ไหว และนั่นไม่ได้ทำให้ฉันแย่ลง",
            "เราอาจเปลี่ยนออฟฟิศทั้งระบบไม่ได้ในคืนเดียว แต่เราเริ่มไม่ทิ้งตัวเองไว้กลางระบบนั้นได้ และบางครั้ง แค่นั้นก็เป็นการกลับมายืนข้างตัวเองที่สำคัญมาก",
            "ถ้าคุณฟังถึงตรงนี้ ขอให้คืนนี้คุณใจดีกับตัวเองนิดหนึ่ง เพราะโลกการทำงานมีคนคอยวัดผลเรามากพอแล้ว อย่าให้ใจของเราเป็นอีกที่ที่เอาแต่ตำหนิตัวเอง",
        ],
        "Ending": [
            "นี่คือ Vela After Work เรื่องที่เราอาจคิดเหมือนกันหลังเลิกงาน แต่ไม่ค่อยพูดออกมา",
            "ถ้าตอนนี้คุณยังนั่งอยู่กับความเหนื่อยของตัวเอง ขอให้รู้ว่ามันไม่ใช่เรื่องน่าอาย และคุณไม่จำเป็นต้องรีบแปลงมันเป็นพลังบวกภายในคืนนี้",
            "บางคืน แค่ยอมรับว่าเหนื่อย แล้วพาตัวเองไปอาบน้ำ กินอะไรอุ่น ๆ และนอนให้ได้ ก็ถือว่าเราดูแลชีวิตได้ดีมากแล้ว",
            "เจอกันหลังเลิกงานครั้งหน้า กับเรื่องที่อาจไม่ได้อยู่ในรายงาน แต่ค้างอยู่ในใจคนทำงานหลายคน",
        ],
    }


def _expand_section(section: str, topic: str, tone: str, paragraphs_needed: int) -> str:
    bank = _paragraph_bank(topic, tone)[section]
    rows = []
    for index in range(paragraphs_needed):
        base = bank[index % len(bank)]
        if index >= len(bank):
            base += " " + [
                "พอพูดออกมาแบบนี้ มันไม่ได้ทำให้เรื่องเบาลงทันที แต่มันทำให้เราไม่ต้องแบกมันแบบไม่มีชื่ออีกต่อไป",
                "และนั่นอาจเป็นจุดเริ่มต้นเล็ก ๆ ของการกลับมาฟังตัวเอง หลังจากฟังเสียงคนอื่นมาทั้งวัน",
                "บางทีคำตอบไม่ได้อยู่ที่การหนีไปไหน แต่อยู่ที่การเห็นให้ชัดว่าอะไรที่เราไม่ควรปล่อยให้กลายเป็นเรื่องปกติอีกแล้ว",
            ][index % 3]
        rows.append(base)
    return "\n\n".join(rows)


def _full_script(topic: str, tone: str, narrator: str, length: str) -> str:
    target = WORD_TARGETS.get(length, WORD_TARGETS["10 min"])["target"]
    sections = ["Cold Open", "Act 1: Setup", "Act 2: Conflict", "Act 3: Emotional Breakdown", "Act 4: Reflection", "Act 5: Takeaway", "Ending"]
    paragraphs_by_section = max(3, target // 420)
    blocks = [f"[Cold Open]\n{_cold_open(topic, tone)}"]
    for section in sections[1:]:
        extra = 1 if section in {"Act 3: Emotional Breakdown", "Act 5: Takeaway"} else 0
        blocks.append(f"[{section}]\n{_expand_section(section, topic, tone, paragraphs_by_section + extra)}")
    voice_note = f"\n\n[Narrator Direction]\n{_narrator_voice(narrator)}"
    script = _avoid_topic_repeat("\n\n".join(blocks) + voice_note, topic)
    while _word_count(script) < target:
        script += "\n\n" + _expand_section("Act 4: Reflection", topic, tone, 1)
        script = _avoid_topic_repeat(script, topic)
    return script


def _ai_voice_version(script: str) -> str:
    lines = []
    for raw in script.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        if line.lower().startswith("narrator direction"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def _rant_versions(topic: str) -> dict[str, str]:
    return {
        "emotional rant version": (
            "บางทีเราไม่ได้ต้องการให้ใครแก้ปัญหาให้เลย เราแค่อยากให้ใครสักคนยอมรับว่าเรื่องนี้มันหนักจริง "
            "เพราะการต้องทำตัวปกติทุกวัน ทั้งที่ข้างในไม่ปกติ มันเหนื่อยกว่าที่คนอื่นเห็นมาก"
        ),
        "angry rant version": (
            "ขอพูดตรง ๆ นะ สิ่งที่ทำให้คนทำงานพังไม่ใช่แค่งานเยอะ แต่มันคือการถูกคาดหวังให้รับทุกอย่างด้วยรอยยิ้ม "
            "แล้วพอเราเริ่มไม่ไหว กลับถูกถามว่าทำไมไม่จัดการอารมณ์ตัวเองให้ดีกว่านี้"
        ),
        "sarcastic office rant version": (
            "ใช่ครับ ทุกอย่างเร่งด่วนหมด ยกเว้นเงินเดือนกับความเข้าใจของคนบางคนที่ดูเหมือนจะเดินทางมาช้ากว่าอีเมลประมาณสามปี "
            "แต่ไม่เป็นไร เดี๋ยวเราก็กดรับทราบ แล้วไปนั่งหมดไฟต่อแบบมืออาชีพ"
        ),
    }


def _shorts(topic: str, count: int) -> list[dict[str, str]]:
    hooks = [
        "งานไม่ได้จบตอนเลิกงาน ถ้าใจยังประชุมต่อ",
        "บางคนไม่ได้หมดไฟ เขาแค่หมดแรงจะอธิบาย",
        "เคยยิ้มทั้งวัน แล้วพังตอนอยู่คนเดียวไหม",
        "สิ่งที่คนทำงานไม่ค่อยพูด คือเราเหนื่อยกับการทำตัวโอเค",
        "POV: แชตเดียวทำให้คุณคิดทั้งคืน",
        "ไม่ได้อยากลาออก แค่อยากหายใจในที่ทำงาน",
        "ออฟฟิศสอนให้เราเก่ง แต่บางทีก็สอนให้เราเงียบเกินไป",
        "คำว่าไม่เป็นไร บางครั้งแปลว่าไม่ไหวแล้ว",
        "ประชุมจบ แต่ความรู้สึกยังไม่จบ",
        "หลังปิดคอม ความจริงบางอย่างเพิ่งเริ่มดัง",
    ]
    items = []
    for index, hook in enumerate(hooks[:count], start=1):
        start = f"00:{(index - 1) * 35:02d}"
        end = f"00:{(index - 1) * 35 + 30:02d}"
        items.append(
            {
                "timestamp": f"{start}-{end}",
                "hook": hook,
                "caption": f"เรื่องนี้คนทำงานน่าจะเข้าใจ #{index} #VelaAfterWork",
                "script": f"{hook}\n\nเรื่องนี้ไม่ใช่แค่เรื่อง {topic} แต่มันคือความรู้สึกของคนที่ต้องดูโอเคทั้งวัน ทั้งที่ข้างในอยากมีใครสักคนถามว่าเหนื่อยไหมแบบที่พร้อมฟังจริง ๆ",
            }
        )
    return items


def _youtube_package(title: str, topic: str, tone: str) -> dict[str, str]:
    return {
        "YouTube Title": title,
        "YouTube Description": (
            f"Vela After Work ตอนนี้เล่าเรื่อง {topic} ผ่านโทน {tone} สำหรับคนทำงานที่มีเรื่องหลังเลิกงานค้างอยู่ในใจ\n\n"
            "นี่ไม่ใช่พอดแคสต์สอนให้เก่งขึ้นทันที แต่เป็นพื้นที่ให้เรายอมรับความเหนื่อย ความตลกร้าย และเรื่องที่พูดยากในที่ทำงาน\n\n"
            "ฟังช้า ๆ แล้วกลับไปใจดีกับตัวเองอีกนิด"
        ),
        "Hashtags": "#VelaAfterWork #Podcastไทย #ชีวิตวัยทำงาน #OfficeStory #Burnout #เล่าเรื่อง",
        "Pinned Comment": "คุณเคยมีเรื่องที่ไม่กล้าพูดในออฟฟิศ แต่คิดถึงหลังเลิกงานไหม เล่าแบบไม่ต้องบอกชื่อใครก็ได้",
    }


def _spotify_package(topic: str, tone: str, length: str) -> dict[str, str]:
    return {
        "Spotify title": f"Vela After Work: {topic[:42]}",
        "Spotify description": (
            f"ตอนความยาวประมาณ {length} ในโทน {tone} ว่าด้วย office life, workplace politics, burnout "
            "และเรื่องที่คนทำงานคิดหลังปิดคอมแต่ไม่ค่อยพูดออกมา เหมาะสำหรับฟังหลังเลิกงานหรือระหว่างเดินทางกลับบ้าน"
        ),
    }


def _thumbnail_prompt(topic: str, tone: str) -> str:
    return (
        f"cinematic podcast cover for Vela After Work, Thai office worker after hours, tired but thoughtful expression, "
        f"dark warm office lighting, desk lamp, city window at night, emotional workplace story about {topic}, tone {tone}, "
        "premium podcast artwork, no random text, no watermark"
    )


def _ai_video_prompt(topic: str, tone: str) -> str:
    return (
        f"vertical 9:16 cinematic b-roll prompt for a podcast episode about {topic}, Vela After Work mood, office life after dark, "
        f"workplace politics and burnout atmosphere, {tone} emotional storytelling, slow shots of empty desk, elevator, rainy window, "
        "coffee cup, phone notification, realistic Thai office, no subtitles, no logo, no watermark"
    )


def generate_podcast_script_package(topic: str, podcast_tone: str, narrator: str, episode_length: str) -> dict[str, Any]:
    topic = _clean(topic, "เรื่องที่คนทำงานคิดถึงหลังเลิกงาน")
    podcast_tone = podcast_tone if podcast_tone in PODCAST_SCRIPT_TONES else "Vela After Work"
    narrator = narrator if narrator in PODCAST_NARRATORS else "Male"
    episode_length = episode_length if episode_length in PODCAST_EPISODE_LENGTHS else "10 min"
    title = _best_title(topic, podcast_tone)
    full_script = _full_script(topic, podcast_tone, narrator, episode_length)
    word_count = _word_count(_ai_voice_version(full_script))
    package = {
        "Episode Title": title,
        "Cold Open": _cold_open(topic, podcast_tone),
        "Full Podcast Script": full_script,
        "AI Voice Version": _ai_voice_version(full_script),
        "Viral Rant Engine": _rant_versions(topic),
        "Shorts Extraction": _shorts(topic, WORD_TARGETS[episode_length]["shorts"]),
        "YouTube Package": _youtube_package(title, topic, podcast_tone),
        "Spotify Package": _spotify_package(topic, podcast_tone, episode_length),
        "Thumbnail Prompt": _thumbnail_prompt(topic, podcast_tone),
        "AI Video Prompt": _ai_video_prompt(topic, podcast_tone),
        "metadata": {
            "topic": topic,
            "podcast_tone": podcast_tone,
            "narrator": narrator,
            "episode_length": episode_length,
            "word_count": word_count,
            "target_word_count_min": WORD_TARGETS[episode_length]["min"],
            "target_word_count_max": WORD_TARGETS[episode_length]["max"],
            "style": "Vela After Work",
            "offline_safe": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
    }
    return {"ok": True, "data": package, "error": ""}


def podcast_script_package_to_text(package: dict[str, Any]) -> str:
    def block(title: str, body: Any) -> str:
        if isinstance(body, list):
            if body and isinstance(body[0], dict):
                rows = []
                for index, item in enumerate(body, start=1):
                    rows.append(
                        f"{index}. Timestamp: {item.get('timestamp', '')}\n"
                        f"Hook: {item.get('hook', item.get('Hook', ''))}\n"
                        f"Script: {item.get('script', item.get('Script', ''))}\n"
                        f"Caption: {item.get('caption', item.get('Suggested caption', ''))}"
                    )
                content = "\n\n".join(rows)
            else:
                content = "\n".join(f"- {item}" for item in body)
        elif isinstance(body, dict):
            content = "\n".join(f"{key}: {value}" for key, value in body.items())
        else:
            content = str(body or "")
        return f"====================\n{title}\n====================\n{content.strip()}\n"

    lines = ["VELAFLOW PODCAST SCRIPT STUDIO V2", "Vela After Work: Stories people think about after work but rarely say out loud.", ""]
    metadata = package.get("metadata") or {}
    lines.append(block("EPISODE METADATA", metadata))
    for section in REQUIRED_PODCAST_SCRIPT_SECTIONS:
        lines.append(block(section.upper(), package.get(section, "")))
    return "\n".join(lines).strip() + "\n"
