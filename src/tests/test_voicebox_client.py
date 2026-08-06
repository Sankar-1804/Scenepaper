from backend.clients.voicebox_client import (
    VOICE_PROFILES,
    insert_breath_pauses,
    voice_profile_for_category,
)


def test_insert_breath_pauses_adds_tag_after_each_sentence():
    text = "This is one sentence. This is another sentence."
    result = insert_breath_pauses(text)
    assert result.count("[pause]") == 2


def test_insert_breath_pauses_adds_mid_sentence_pause_for_long_sentences():
    long_sentence = (
        "This is a very long sentence that goes on and on, well past the "
        "point where a real narrator would need to take a breath before "
        "finishing it, because it just keeps going and going and going."
    )
    result = insert_breath_pauses(long_sentence, long_sentence_word_threshold=10)
    assert result.count("[pause]") == 2  # one mid-sentence + one at the end


def test_voice_profile_for_category_known_category():
    assert voice_profile_for_category("suspense") == VOICE_PROFILES["suspense"]


def test_voice_profile_for_category_unmapped_falls_back(caplog):
    profile = voice_profile_for_category("curious")
    assert profile == VOICE_PROFILES["human_interest"]
    assert any("No documented Voicebox voice profile" in r.message for r in caplog.records)
