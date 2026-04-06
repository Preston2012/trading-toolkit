"""Unit tests for news headline scanner and fuzzy dedup."""

import hashlib

from core.news_scanner import normalize_headline


class TestNormalizeHeadline:
    """Tests for fuzzy headline normalization."""

    def test_word_order_variants_match(self) -> None:
        """Headlines with same words in different order produce same output."""
        h1 = "Trump threatens Iran sanctions"
        h2 = "Trump threatens sanctions on Iran"
        assert normalize_headline(h1) == normalize_headline(h2)

    def test_filler_words_stripped(self) -> None:
        """Common filler words are removed before normalization."""
        h1 = "The President said he will impose sanctions"
        h2 = "President impose sanctions"
        assert normalize_headline(h1) == normalize_headline(h2)

    def test_punctuation_stripped(self) -> None:
        """Punctuation does not affect normalization."""
        h1 = "Trump: sanctions on Iran!"
        h2 = "Trump sanctions on Iran"
        assert normalize_headline(h1) == normalize_headline(h2)

    def test_case_insensitive(self) -> None:
        """Normalization is case-insensitive."""
        h1 = "TRUMP THREATENS SANCTIONS"
        h2 = "trump threatens sanctions"
        assert normalize_headline(h1) == normalize_headline(h2)

    def test_different_headlines_differ(self) -> None:
        """Genuinely different headlines should not match."""
        h1 = "Trump threatens Iran sanctions"
        h2 = "Fed announces rate cut decision"
        assert normalize_headline(h1) != normalize_headline(h2)

    def test_near_duplicate_same_hash(self) -> None:
        """Near-duplicate headlines from different sources produce same MD5."""
        h1 = "Trump threatens Iran with new sanctions, sources say"
        h2 = "Trump threatens new sanctions on Iran"
        hash1 = hashlib.md5(normalize_headline(h1).encode()).hexdigest()[:12]
        hash2 = hashlib.md5(normalize_headline(h2).encode()).hexdigest()[:12]
        assert hash1 == hash2

    def test_single_char_words_stripped(self) -> None:
        """Single-character tokens are stripped."""
        result = normalize_headline("A B C trump")
        assert "trump" in result
        assert " a " not in f" {result} "

    def test_empty_headline(self) -> None:
        """Empty headline produces empty output."""
        assert normalize_headline("") == ""
