from core.thai_lyric_coherence import review_thai_story_coherence


def test_warns_on_ambiguous_return_vs_disappearance():
    result = review_thai_story_coherence(
        "[Verse 1]\nตัวจริงกลับมาแล้ว\n[Chorus]\nพอเขาหาย ฉันก็แค่ส่วนเกิน",
        idea="ตัวจริงกลับมา ตัวสำรองถูกลืม",
        selected_hook="พอเขาหาย ฉันก็แค่ส่วนเกิน",
    )
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["code"] == "hook_return_disappearance_ambiguity"
    assert result["advisory_only"] is True


def test_no_warning_when_hook_agrees_with_story():
    result = review_thai_story_coherence(
        "[Verse]\nเขากลับมา\n[Chorus]\nพอเขากลับมา ฉันก็แค่ส่วนเกิน",
        selected_hook="พอเขากลับมา ฉันก็แค่ส่วนเกิน",
    )
    assert result["warnings"] == []


def test_ignore_english_production_tags_and_preserve_input():
    original = "[Intro]\n(Acoustic guitar)\n[Chorus]\nฉันยังหวัง"
    result = review_thai_story_coherence(original)
    assert result["checked_lines"] == 1
    assert result["passed"]
    assert original.endswith("ฉันยังหวัง")


def test_long_line_warning_is_advisory_not_syllable_count():
    line = "ฉัน" * 30
    result = review_thai_story_coherence("[Verse]\n" + line)
    assert result["warnings"][0]["code"] == "long_lyric_lines"
    assert result["long_lines"][0]["characters"] == 90
    assert result["method"] == "conservative_rule_based_v2"


def test_short_lyric_lines_not_flagged():
    result = review_thai_story_coherence(
        "[Verse]\nวันที่เธออ่อนแอ ต้องการใครสักคน\n[Chorus]\nพอเขากลับมา ฉันก็แค่ส่วนเกิน"
    )
    assert result["warnings"] == []
    assert result["long_lines"] == []


def test_detects_hook_on_third_chorus_line_without_explicit_selection():
    lyrics = (
        "[Verse 1]\nตัวจริงกลับมาแล้ว\n"
        "[Chorus]\nความรักก็เหมือนเกมกีฬา\n"
        "ตัวสำรองมีค่าเฉพาะวันที่ตัวจริงเจ็บ\n"
        "พอเขาหาย ฉันก็แค่ส่วนเกิน"
    )
    review = review_thai_story_coherence(lyrics)
    assert [item["code"] for item in review["warnings"]] == [
        "hook_return_disappearance_ambiguity"
    ]


def test_does_not_override_explicit_selected_hook_with_other_chorus_lines():
    lyrics = "[Verse]\nตัวจริงกลับมาแล้ว\n[Chorus]\nพอเขาหาย ฉันก็แค่ส่วนเกิน"
    review = review_thai_story_coherence(
        lyrics, selected_hook="พอเขากลับมา ฉันก็แค่ส่วนเกิน"
    )
    assert review["warnings"] == []
