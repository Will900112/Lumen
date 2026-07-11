"""Unit tests for the ETL chunking helpers (pure functions)."""

from data.etl_chunk import CHUNK_OVERLAP, CHUNK_SIZE, clean_text, split_into_chunks


def test_short_text_returns_single_chunk():
    text = " ".join(["word"] * 50)
    assert split_into_chunks(text) == [text]


def test_tiny_fragment_is_dropped():
    assert split_into_chunks("too short") == []


def test_long_text_is_split_with_overlap():
    words = [f"w{i}" for i in range(1500)]
    chunks = split_into_chunks(" ".join(words))

    chunk_words = [c.split() for c in chunks]
    assert [len(w) for w in chunk_words] == [600, 600, 500]

    # each chunk starts with the last CHUNK_OVERLAP words of the previous one
    for prev, curr in zip(chunk_words, chunk_words[1:]):
        assert curr[:CHUNK_OVERLAP] == prev[-CHUNK_OVERLAP:]


def test_chunk_size_is_respected():
    words = ["x"] * (CHUNK_SIZE * 3)
    chunks = split_into_chunks(" ".join(words))
    assert all(len(c.split()) <= CHUNK_SIZE for c in chunks)


def test_clean_text_removes_chapter_headings():
    text = "# CHAPTER 12 *Vitamins and Minerals\nReal content stays."
    cleaned = clean_text(text)
    assert "CHAPTER" not in cleaned
    assert "Real content stays." in cleaned


def test_clean_text_collapses_blank_lines():
    cleaned = clean_text("para one\n\n\n\n\npara two")
    assert cleaned == "para one\n\npara two"
