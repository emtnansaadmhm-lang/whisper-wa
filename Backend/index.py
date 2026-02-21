# Backend/index.py

def build_index(messages):
    index = {}

    for msg_id, text in messages.items():
        for word in text.lower().split():
            if word not in index:
                index[word] = []
            index[word].append(msg_id)

    return index
