from docwarden.density.sentences import split_sentences


def test_splits_two_simple_sentences():
    assert split_sentences("First one. Second one.") == ["First one.", "Second one."]


def test_no_terminal_punctuation_is_one_sentence():
    # Matches a table cell with no internal period — the whole cell is "one
    # sentence", which is the correct outcome for measuring its word count.
    assert split_sentences("just a phrase with no stop") == ["just a phrase with no stop"]


def test_does_not_split_before_lowercase_continuation():
    # "np." followed by a lowercase word should not be treated as a boundary
    # for the sentence-words/em-dash checks' purposes (pragmatic, not exhaustive).
    assert split_sentences("Patrz np. akta sprawy.") == ["Patrz np. akta sprawy."]


def test_splits_before_polish_diacritic_capital():
    assert split_sentences("Pierwsze. Ósme zdanie.") == ["Pierwsze.", "Ósme zdanie."]


def test_splits_before_opening_quote_or_bold_marker():
    assert split_sentences('Koniec. "Nowe zdanie".') == ["Koniec.", '"Nowe zdanie".']
    assert split_sentences("Koniec. **Bold** dalej.") == ["Koniec.", "**Bold** dalej."]
