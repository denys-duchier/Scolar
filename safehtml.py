
from stripogram import html2text, html2safehtml

# permet de conserver quelques tags html
def HTML2SafeHTML( text, convert_br=True ):
    text =  html2safehtml( text, valid_tags=('b', 'a', 'i', 'br', 'p'))
    if convert_br:
        return newline_to_br(text)
    else:
        return text

def newline_to_br( text ):
    return text.replace( '\n', '<br>' )

