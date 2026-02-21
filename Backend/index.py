# Backend/index.py

def build_index(messages):
    index = {}

    for msg_id, text in messages.items():
        for word in text.lower().split():
            if word not in index:
                index[word] = []
            index[word].append(msg_id)

    return index
    # Backend/index.py
import re
from collections import Counter

URL_REGEX = r'(https?://\S+)'
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

def normalize(text):
    return text.lower().strip()

def extract_links(text):
    return re.findall(URL_REGEX, text)

def extract_images(text):
    return [w for w in text.split() if w.lower().endswith(IMAGE_EXT)]

def build_index(messages):
    word_index = {}
    links = []
    images = []
    all_words = []

    for msg_id, text in messages.items():
        clean_text = normalize(text)

        # كلمات
        words = clean_text.split()
        all_words.extend(words)

        for word in words:
            if word not in word_index:
                word_index[word] = set()
            word_index[word].add(msg_id)

        # روابط
        links.extend(extract_links(text))

        # صور
        images.extend(extract_images(text))

    return {
        "word_index": {k: list(v) for k, v in word_index.items()},
        "links": links,
        "images": images,
        "most_common": Counter(all_words).most_common(1)
    }

def search_word(index, word):
    return index["word_index"].get(word.lower(), [])
