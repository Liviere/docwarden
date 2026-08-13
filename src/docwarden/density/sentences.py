import re

# Pragmatic, not a real tokenizer: split on whitespace following .!? when the
# next visible character looks like a new clause start (capital letter incl.
# Polish diacritics, opening quote/paren/backtick/bold-marker). Will not
# handle abbreviations ("np.", "tzn.") correctly — accepted false-split risk,
# the same tolerance already extended to lint_identifiers.py's TS regexes.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ„\"'*`(\[])")


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text) if s.strip()]
