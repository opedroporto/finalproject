import requests

def fit(word, n):
    if not word:
        return ''
    if len(word) > n and n > 3:
        # no blank space
        temp_word =  word[:n-3]
        if temp_word[len(temp_word)-1] == ' ':
            word = word[:n-4]
        else:
            word = word[:n-3]
        new_word = ''.join(word)+"..."
        return new_word
    return word[:n]

def is_url_image(image_url):
    try:
        image_formats = ("image/png", "image/jpeg", "image/jpg")
        r = requests.head(image_url)
        if r.headers["content-type"] in image_formats:
            return True
    except:
        return False
    return False