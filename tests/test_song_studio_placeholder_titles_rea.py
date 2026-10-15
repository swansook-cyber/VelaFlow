from core.song_title_engine import is_placeholder_song_title, title_is_valid

def test_thai_starter_project_titles_are_placeholders():
    for title in ("โปรเจกต์เพลงใหม่", "เพลงใหม่", "เพลงใหม่ของฉัน"):
        assert is_placeholder_song_title(title)
        assert not title_is_valid(title)

def test_real_titles_remain_valid():
    for title in ("คนที่ถูกลืม", "แค่ส่วนเกิน", "ไม่มีวันเหมือนเดิม"):
        assert not is_placeholder_song_title(title)
        assert title_is_valid(title)

def test_whitespace_normalization_of_placeholders():
    assert is_placeholder_song_title("  โปรเจกต์เพลงใหม่  ")
    assert is_placeholder_song_title(" เพลงใหม่ ")
