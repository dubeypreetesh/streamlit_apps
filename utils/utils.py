'''
Created on 19-May-2024

@author: ongraph
'''

def split_text(text, length, encoding):
    words = text.split()
    chunks = []
    chunk = ""
    
    def tweet_length(text):
        return len(text.encode(encoding)) // 2
    
    for word in words:
        if tweet_length(chunk) + tweet_length(word) + 1 > length:
            chunks.append(chunk)
            chunk = word
        else:
            if chunk:
                chunk += " "
            chunk += word

    if chunk:
        chunks.append(chunk)
    
    return chunks
