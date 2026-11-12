import re
from typing import List, Set

DEVANAGARI_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "अं": "an", "अः": "ah"
}

DEVANAGARI_MATRAS = {
    "ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ं": "n", "ँ": "n", "ः": "h", "्": ""
}

DEVANAGARI_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "d", "ढ़": "dh", "फ़": "f"
}

def is_devanagari(text: str) -> bool:
    """Checks if the string contains any Devanagari script characters."""
    return bool(re.search(r"[\u0900-\u097F]", text))

def transliterate_devanagari_to_roman(text: str) -> str:
    """
    Transliterates Hindi (Devanagari) characters into standard Roman alphabet (PRD 8.2).
    Properly handles consonants with inherent 'a' and halant ('्') vowel suppression.
    """
    if not text or not is_devanagari(text):
        return text

    result = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        # Check for independent vowel
        if char in DEVANAGARI_VOWELS:
            result.append(DEVANAGARI_VOWELS[char])
            i += 1
            continue

        # Check for consonant
        if char in DEVANAGARI_CONSONANTS:
            base_cons = DEVANAGARI_CONSONANTS[char]
            # Check next character
            if i + 1 < n:
                next_char = text[i + 1]
                if next_char == "्":  # Halant: suppresses inherent vowel
                    result.append(base_cons)
                    i += 2
                    continue
                elif next_char in DEVANAGARI_MATRAS:
                    matra_val = DEVANAGARI_MATRAS[next_char]
                    result.append(base_cons + matra_val)
                    i += 2
                    continue
            # No halant and no matra: add base consonant + inherent 'a' (unless at word end)
            is_word_end = (i + 1 == n) or text[i + 1].isspace()
            inherent_vowel = "" if is_word_end else "a"
            result.append(base_cons + inherent_vowel)
            i += 1
            continue

        # Matra without consonant (unusual, but safe)
        if char in DEVANAGARI_MATRAS:
            result.append(DEVANAGARI_MATRAS[char])
            i += 1
            continue

        # Non-Devanagari character (space, punctuation, English letter)
        result.append(char)
        i += 1

    romanized = "".join(result).strip().lower()
    return re.sub(r"\s+", " ", romanized)

def generate_phonetic_variations(roman_name: str) -> Set[str]:
    """
    Generates common spelling variations found in Indian identity documents:
    - 'ee' <-> 'i' (Suneeta / Sunita)
    - 'oo' <-> 'u' (Pooja / Puja)
    - 'v' <-> 'w' (Tiwari / Teewari)
    - 'sh' <-> 's'
    """
    variations = {roman_name}
    name_clean = roman_name.lower()

    # 'ee' to 'i'
    if "ee" in name_clean:
        variations.add(name_clean.replace("ee", "i"))
    if "i" in name_clean:
        variations.add(name_clean.replace("i", "ee"))

    # 'oo' to 'u'
    if "oo" in name_clean:
        variations.add(name_clean.replace("oo", "u"))
    if "u" in name_clean:
        variations.add(name_clean.replace("u", "oo"))

    # 'w' to 'v'
    if "w" in name_clean:
        variations.add(name_clean.replace("w", "v"))
    if "v" in name_clean:
        variations.add(name_clean.replace("v", "w"))

    return variations
