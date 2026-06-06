from __future__ import annotations

from datetime import datetime
from typing import Any


PODCAST_SCRIPT_TONES = ["Dark Humor", "Emotional", "Motivational", "Storytelling", "Office Rant"]
PODCAST_NARRATORS = ["Male", "Female"]
PODCAST_EPISODE_LENGTHS = ["10 min", "20 min", "30 min"]

REQUIRED_PODCAST_SCRIPT_SECTIONS = [
    "Episode Title",
    "Cold Open",
    "Full Podcast Script",
    "AI Voice Version",
    "Shorts Extraction",
    "YouTube Package",
    "Spotify Package",
]


def _clean(value: str, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _tone_note(tone: str) -> str:
    return {
        "Dark Humor": "ขำแห้งแบบคนทำงานที่ยังต้องเปิดคอมวันพรุ่งนี้",
        "Emotional": "เล่าแบบนุ่ม ลึก และมีพื้นที่ให้คนฟังนึกถึงตัวเอง",
        "Motivational": "ให้กำลังใจแบบไม่ขายฝัน เหมือนเพื่อนร่วมงานที่เข้าใจจริง",
        "Storytelling": "เล่าเป็นฉาก มีคน มีโต๊ะทำงาน มีความเงียบหลังเลิกงาน",
        "Office Rant": "ระบายแบบคม ตรง แต่ยังมนุษย์และไม่หยาบพร่ำเพรื่อ",
    }.get(tone, "เล่าแบบมนุษย์ออฟฟิศที่พูดเรื่องจริงหลังเลิกงาน")


def _narrator_voice(narrator: str) -> str:
    if narrator == "Female":
        return "เสียงผู้หญิงอบอุ่น มีจังหวะนิ่ง เว้นวรรคแบบเล่าเรื่องหลังเลิกงาน"
    return "เสียงผู้ชายอบอุ่นปนเหนื่อยเล็ก ๆ เล่าเหมือนนั่งคุยกันหลังปิดคอม"


def _length_profile(length: str) -> dict[str, int]:
    if length == "30 min":
        return {"paragraphs_per_arc": 6, "shorts": 10, "cold_open_lines": 8}
    if length == "20 min":
        return {"paragraphs_per_arc": 4, "shorts": 8, "cold_open_lines": 6}
    return {"paragraphs_per_arc": 2, "shorts": 5, "cold_open_lines": 4}


def _title_candidates(topic: str, tone: str) -> list[str]:
    core = topic.strip(" .") or "เรื่องหลังเลิกงาน"
    candidates = [
        f"เรื่องที่เราไม่พูดในออฟฟิศ",
        f"หลังเลิกงานค่อยร้องไห้",
        f"โต๊ะทำงานที่เก็บความเงียบไว้",
        f"คนเหนื่อยที่ยังต้องยิ้ม",
        f"วันที่งานไม่ใช่เรื่องหนักที่สุด",
        f"ประชุมจบ แต่ใจยังไม่จบ",
        f"สิ่งที่คนทำงานไม่ค่อยพูด",
        f"{core} หลังหกโมงเย็น",
        f"ชีวิตที่ซ่อนอยู่ในปฏิทินงาน",
        f"ยิ้มให้หัวหน้า แล้วกลับมาถามตัวเอง",
    ]
    if tone == "Dark Humor":
        candidates.insert(0, "ขำไม่ออก แต่ต้องส่งงาน")
    if tone == "Office Rant":
        candidates.insert(0, "ไม่ได้หมดไฟ แค่หมดใจ")
    if tone == "Motivational":
        candidates.insert(0, "เหนื่อยได้ แต่อย่าหายไปจากตัวเอง")
    return candidates


def _score_title(title: str, topic: str) -> int:
    generic = {"งาน", "ออฟฟิศ", "ชีวิต", "เหนื่อย", "พอดแคสต์"}
    words = [part for part in title.replace("/", " ").split() if part]
    score = 70
    if 2 <= len(words) <= 8:
        score += 12
    if any(token in title for token in ["หลังเลิกงาน", "ไม่พูด", "ยังต้อง", "ไม่จบ", "หมดใจ"]):
        score += 10
    if title.strip() == topic.strip() or title.strip() in generic:
        score -= 50
    if len(title) > 42:
        score -= 10
    return max(0, min(100, score))


def _best_title(topic: str, tone: str) -> str:
    scored = sorted(((candidate, _score_title(candidate, topic)) for candidate in _title_candidates(topic, tone)), key=lambda item: item[1], reverse=True)
    return scored[0][0]


def _cold_open(topic: str, tone: str, profile: dict[str, int]) -> str:
    lines = [
        "เคยมีวันที่คุณเดินออกจากออฟฟิศ แล้วรู้สึกเหมือนยังมีใครบางคนเดินตามมาไหม",
        "ไม่ใช่คนจริง ๆ หรอก",
        "แต่เป็นประโยคในห้องประชุม เป็นแชตที่ยังไม่ได้ตอบ เป็นรอยยิ้มที่ฝืนไว้ทั้งวัน",
        f"วันนี้เราไม่ได้จะคุยเรื่อง {topic} แบบสรุปบทเรียนสวย ๆ",
        "เราจะคุยกันแบบที่คนทำงานมักคิดตอนปิดไฟห้อง แต่ไม่ค่อยพูดออกมา",
        "เพราะบางทีเรื่องที่ทำให้เราเหนื่อยที่สุด ไม่ใช่งาน",
        "แต่คือการต้องทำเหมือนเราไม่รู้สึกอะไรเลย",
        "และถ้าคุณเคยรู้สึกแบบนั้น ตอนนี้คุณไม่ได้ฟังอยู่คนเดียว",
    ]
    if tone == "Dark Humor":
        lines[3] = f"วันนี้เราไม่ได้จะคุยเรื่อง {topic} แบบโลกสวย เพราะถ้าโลกสวยจริง เราคงไม่ต้องตั้งปลุกไปทำงานพรุ่งนี้"
    if tone == "Office Rant":
        lines[3] = f"วันนี้ขอพูดเรื่อง {topic} แบบไม่ห่อของขวัญ แต่ก็ไม่ขว้างใส่หน้าใคร"
    return "\n".join(lines[: profile["cold_open_lines"]])


def _arc_paragraphs(topic: str, tone: str, arc_name: str, count: int) -> list[str]:
    tone_note = _tone_note(tone)
    seeds = {
        "Intro": [
            f"ก่อนเข้าเรื่อง ลองนึกถึงช่วงเวลาหลังเลิกงานที่ทุกอย่างเงียบลง แต่หัวเรายังไม่ยอมเงียบตาม",
            f"หัวข้อ {topic} อาจดูเหมือนเรื่องธรรมดา แต่สำหรับคนที่เจอมันซ้ำ ๆ มันไม่เคยธรรมดาเลย",
        ],
        "Story Arc 1": [
            f"เรื่องมักเริ่มจากสิ่งเล็ก ๆ เช่นข้อความที่ส่งมาตอนใกล้เลิกงาน หรือคำพูดสั้น ๆ ที่ทำให้เราถามตัวเองทั้งคืน",
            "ตอนแรกเราบอกตัวเองว่าไม่เป็นไร ทุกคนก็เจอแบบนี้ แต่คำว่าไม่เป็นไรบางครั้งก็เป็นแค่ผ้าคลุมความเหนื่อย",
            f"นี่คือจุดที่ {topic} เริ่มกลายเป็นเรื่องส่วนตัว ไม่ใช่แค่เรื่องงาน",
        ],
        "Story Arc 2": [
            "พอเวลาผ่านไป เราเริ่มเก่งขึ้นในการทำตัวปกติ แต่ไม่ได้แปลว่าเรารู้สึกน้อยลง",
            "เราเรียนรู้ว่าจะตอบแชตยังไงให้ดูโอเค จะยิ้มยังไงให้ไม่ถูกถาม และจะเงียบยังไงไม่ให้ใครรู้ว่าในหัวเสียงดังมาก",
            f"ความตลกร้ายคือ หลายครั้งเราไม่ได้ต้องการลาออกจากงาน เราแค่อยากลาออกจากความรู้สึกที่ {topic} สร้างไว้ในใจ",
        ],
        "Story Arc 3": [
            "แล้ววันหนึ่ง เราเริ่มสังเกตว่าตัวเองไม่ได้เหนื่อยแค่ตอนทำงาน แต่เหนื่อยตั้งแต่ยังไม่เริ่มวัน",
            "กาแฟแก้วเดิม เพลงเดิม โต๊ะเดิม ทุกอย่างเหมือนเดิม แต่เรากลับไม่เหมือนเดิมแล้ว",
            f"ตรงนี้แหละที่เรื่อง {topic} บอกเราว่า บางอย่างต้องถูกพูดออกมา แม้มันจะพูดยาก",
        ],
        "Peak Conflict": [
            "จุดที่หนักที่สุดไม่ใช่ตอนที่มีคนทำให้เราเจ็บ แต่คือตอนที่เรายังต้องทำงานต่อเหมือนไม่มีอะไรเกิดขึ้น",
            "เรายังต้องตอบสุภาพ ยังต้องประชุม ยังต้องส่งไฟล์ ทั้งที่ข้างในอยากวางทุกอย่างลงสักห้านาที",
            "และบางทีสิ่งที่เราโกรธที่สุด ไม่ใช่คนอื่น แต่คือตัวเองที่ทนมานานจนลืมถามว่าไหวไหม",
        ],
        "Reflection": [
            f"ถ้าเรื่อง {topic} สอนอะไรเราอย่างหนึ่ง อาจเป็นเรื่องการยอมรับว่า ความเหนื่อยของเราไม่จำเป็นต้องถูกเปรียบเทียบกับใคร",
            "เราไม่ต้องรอให้พังก่อน ถึงจะมีสิทธิ์พัก",
            f"และเราไม่ต้องเล่าเรื่องนี้ให้ทุกคนเข้าใจ แค่เริ่มจากยอมรับกับตัวเองว่า วันนี้มันหนักจริง ก็พอแล้ว",
        ],
        "Outro": [
            "ถ้าตอนนี้คุณฟังมาถึงตรงนี้ ลองให้เครดิตตัวเองหน่อยที่ยังอยู่กับตัวเองจนจบวัน",
            "บางวันเราไม่ได้ต้องชนะชีวิต แค่ไม่ทิ้งตัวเองไว้กลางทางก็ถือว่าเก่งมากแล้ว",
            "เจอกันหลังเลิกงานครั้งหน้า กับเรื่องที่เราอาจคิดเหมือนกัน แต่ยังไม่เคยพูดออกมา",
        ],
    }
    base = seeds.get(arc_name, seeds["Story Arc 1"])
    output = []
    for index in range(count):
        line = base[index % len(base)]
        if index >= len(base):
            line = f"{line} {tone_note}"
        output.append(line)
    return output


def _full_script(topic: str, tone: str, narrator: str, length: str) -> str:
    profile = _length_profile(length)
    sections = ["Cold Open", "Intro", "Story Arc 1", "Story Arc 2", "Story Arc 3", "Peak Conflict", "Reflection", "Outro"]
    blocks = []
    for section in sections:
        if section == "Cold Open":
            body = _cold_open(topic, tone, profile)
        else:
            count = profile["paragraphs_per_arc"]
            if section in {"Peak Conflict", "Reflection"}:
                count += 1
            body = "\n\n".join(_arc_paragraphs(topic, tone, section, count))
        blocks.append(f"[{section}]\n{body}")
    voice_note = f"\n\n[Narrator Direction]\n{_narrator_voice(narrator)}"
    return "\n\n".join(blocks) + voice_note


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


def _shorts(topic: str, tone: str, count: int) -> list[dict[str, str]]:
    hooks = [
        "สิ่งที่เหนื่อยที่สุดในออฟฟิศ อาจไม่ใช่งาน",
        "เคยเลิกงานแล้ว แต่ใจยังไม่เลิกคิดไหม",
        "บางคนไม่ได้หมดไฟ เขาแค่หมดแรงจะอธิบาย",
        "ประโยคเดียวในห้องประชุม ทำให้เราคิดทั้งคืนได้จริง",
        "POV: คุณยิ้มทั้งวัน แล้วกลับไปร้องไห้ในรถ",
        "คนทำงานบางคนไม่ได้อยากลาออก แค่อยากหายใจ",
        "งานจบในระบบ แต่ไม่จบในหัวเรา",
        "มีเรื่องหนึ่งที่คนออฟฟิศไม่ค่อยพูดกันตรง ๆ",
        "เราทนเก่ง จนลืมว่าตัวเองเหนื่อย",
        "หลังเลิกงานคือเวลาที่ความจริงเริ่มดังขึ้น",
    ]
    items = []
    for index, hook in enumerate(hooks[:count], start=1):
        items.append(
            {
                "Hook": hook,
                "Script": f"{hook}\n\nเรื่อง {topic} ทำให้หลายคนรู้ว่า การดูโอเคทั้งวันไม่ได้แปลว่าเราโอเคจริง ๆ และบางทีสิ่งที่เราต้องการไม่ใช่คำแนะนำ แต่คือใครสักคนที่ฟังโดยไม่รีบตัดสิน",
                "Suggested duration": "25-45 sec" if tone != "Office Rant" else "20-35 sec",
                "Suggested caption": f"เรื่องนี้คนทำงานน่าจะเข้าใจ #VelaAfterWork #{index}",
            }
        )
    return items


def _youtube_package(title: str, topic: str, tone: str) -> dict[str, str]:
    hashtags = "#VelaAfterWork #Podcastไทย #ชีวิตวัยทำงาน #OfficeStory #เล่าเรื่อง"
    return {
        "YouTube Title": title,
        "Description": (
            f"ตอนนี้เล่าเรื่อง {topic} ในโทน {tone} สำหรับคนที่มีเรื่องหลังเลิกงานที่ยังค้างอยู่ในใจ\n\n"
            "Vela After Work คือพื้นที่ของเรื่องที่คนทำงานคิดถึงหลังปิดคอม แต่ไม่ค่อยพูดออกมาดัง ๆ\n\n"
            "ฟังช้า ๆ แล้วกลับไปใจดีกับตัวเองอีกนิด"
        ),
        "Hashtags": hashtags,
        "Pinned Comment": "คุณเคยเจอโมเมนต์แบบนี้ในที่ทำงานไหม เล่าแบบไม่ต้องบอกชื่อใครก็ได้",
    }


def _spotify_package(topic: str, tone: str, length: str) -> dict[str, str]:
    return {
        "Episode Summary": (
            f"เรื่องเล่า Vela After Work เกี่ยวกับ {topic} ในโทน {tone} ความยาวประมาณ {length} "
            "สำหรับคนทำงานที่อยากฟังเรื่องจริงหลังเลิกงาน มีทั้งความเหนื่อย ความตลกร้าย และประโยคที่ช่วยให้กลับมาเข้าใจตัวเอง"
        )
    }


def generate_podcast_script_package(topic: str, podcast_tone: str, narrator: str, episode_length: str) -> dict[str, Any]:
    topic = _clean(topic, "เรื่องที่คนทำงานคิดถึงหลังเลิกงาน")
    podcast_tone = podcast_tone if podcast_tone in PODCAST_SCRIPT_TONES else "Storytelling"
    narrator = narrator if narrator in PODCAST_NARRATORS else "Male"
    episode_length = episode_length if episode_length in PODCAST_EPISODE_LENGTHS else "10 min"
    profile = _length_profile(episode_length)
    title = _best_title(topic, podcast_tone)
    cold_open = _cold_open(topic, podcast_tone, profile)
    full_script = _full_script(topic, podcast_tone, narrator, episode_length)
    package = {
        "Episode Title": title,
        "Cold Open": cold_open,
        "Full Podcast Script": full_script,
        "AI Voice Version": _ai_voice_version(full_script),
        "Shorts Extraction": _shorts(topic, podcast_tone, profile["shorts"]),
        "YouTube Package": _youtube_package(title, topic, podcast_tone),
        "Spotify Package": _spotify_package(topic, podcast_tone, episode_length),
        "metadata": {
            "topic": topic,
            "podcast_tone": podcast_tone,
            "narrator": narrator,
            "episode_length": episode_length,
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
                        f"{index}. Hook: {item.get('Hook', '')}\n"
                        f"Script: {item.get('Script', '')}\n"
                        f"Suggested duration: {item.get('Suggested duration', '')}\n"
                        f"Suggested caption: {item.get('Suggested caption', '')}"
                    )
                content = "\n\n".join(rows)
            else:
                content = "\n".join(f"- {item}" for item in body)
        elif isinstance(body, dict):
            content = "\n".join(f"{key}: {value}" for key, value in body.items())
        else:
            content = str(body or "")
        return f"====================\n{title}\n====================\n{content.strip()}\n"

    lines = ["VELAFLOW PODCAST SCRIPT STUDIO", "Vela After Work: Stories people think about after work but rarely say out loud.", ""]
    for section in REQUIRED_PODCAST_SCRIPT_SECTIONS:
        lines.append(block(section.upper(), package.get(section, "")))
    return "\n".join(lines).strip() + "\n"
