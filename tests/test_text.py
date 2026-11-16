from gta6_impact.text import mentions_day_off, mentions_gta, text_hash


def test_day_off_phrases_match_whole_words():
    assert mentions_day_off("Booked the day off for Thursday")
    assert mentions_day_off("calling   in sick tomorrow")
    assert mentions_day_off("PTO approved")
    assert not mentions_day_off("PTOLEMY was a geographer")
    assert not mentions_day_off("")
    assert not mentions_day_off(None)


def test_gta_terms():
    assert mentions_gta("GTA VI hype")
    assert mentions_gta("grand theft auto 6")
    assert mentions_gta("gta6 midnight launch")
    assert not mentions_gta("vegetables")


def test_hash_is_stable_and_short():
    assert text_hash("a") == text_hash("a")
    assert len(text_hash("a")) == 16
