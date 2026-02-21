# Backend/indexer.py

def build_index(messages):
    index = {}

    for msg_id, text in messages.items():
        words = text.lower().split()
        for word in words:
            if word not in index:
                index[word] = []
            index[word].append(msg_id)

    return index
