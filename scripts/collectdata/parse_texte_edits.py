#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import json
import codecs

TOKEN_DELIMITERS = re.compile(u'(\xa0|\s|\(|\)|\.|\!|\'|,|")')
TOKEN_ARTICLE = u'Article'
TOKEN_NEW_ARTICLE = u'nouveau'
TOKEN_ARTICLE_REFERENCE = u'article'
TOKEN_NEW_LINE = '\n'
TOKEN_SINGLE_QUOTE = u'\''
TOKEN_DOUBLE_QUOTE_OPEN = u'"'
TOKEN_DOUBLE_QUOTE_CLOSE = u'"'
TOKEN_PARTS = [
    u'livre', u'livres',
    u'article', u'articles',
    u'titre', u'titres',
    u'alinéa', u'alinéas',
    u'phrase', u'phrases',
    u'mention', u'mentions'
]
TOKEN_MONTH_NAMES = [
    u'janvier',
    u'février',
    u'mars',
    u'avril',
    u'mai',
    u'juin',
    u'juillet',
    u'août',
    u'septembre',
    u'octobre',
    u'novembre',
    u'décembre'
]
TOKEN_MULTIPLICATIVE_ADVERBS = [
    'bis',
    'ter',
    'quater',
    'quinquies',
    'sexies',
    'septies',
    'octies',
    'novies',
    'decies',
    'undecies',
    'duodecies',
    'terdecies',
    'quaterdecies',
    'quindecies',
    'sexdecies',
    'septdecies',
    'octodecies',
    'novodecies',
    'vicies',
    'unvicies',
    'duovicies',
    'tervicies',
    'quatervicies',
    'quinvicies',
    'sexvicies',
    'septvicies'
]

def debug(node, tokens, i, msg):
    if '-v' in sys.argv:
        print('    ' * getNodeDepth(node) + msg + ' ' + str(tokens[i:i+4]))

def tokenize(text):
    text = text.replace(u'\xa0', u' ')
    tokens = TOKEN_DELIMITERS.split(text)
    # remove empty strings
    tokens = filter(lambda s: s != '', tokens)
    return tokens

def skipTokens(tokens, i, f):
    while i < len(tokens) and f(tokens[i]):
        i += 1
    return i

def skipSpaces(tokens, i):
    return skipTokens(tokens, i, lambda t: re.compile('\s+').match(t))

def skipToNextWord(tokens, i):
    return skipTokens(tokens, i, lambda t: not re.compile('[\wà]+', re.IGNORECASE | re.UNICODE).match(t))

def skipToToken(tokens, i, token):
    return skipTokens(tokens, i, lambda t: t != token)

def skipToEndOfLine(tokens, i):
    return skipToToken(tokens, i, TOKEN_NEW_LINE)

def skipToQuoteStart(tokens, i):
    return skipToToken(tokens, i, TOKEN_DOUBLE_QUOTE_OPEN)

def isNumber(token):
    return re.compile('\d+').match(token)

def isSpace(token):
    return re.compile('^\s+$').match(token)

def isArticlePart(token):
    return token in TOKEN_PARTS >= 0

def parseInt(s):
    return int(re.search(r'\d+', s).group())

def parseRomanNumber(n):
    romans_map = zip(
        (1000,  900, 500, 400 , 100,  90 , 50 ,  40 , 10 ,   9 ,  5 ,  4  ,  1),
        ( 'M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    )

    n = n.upper()
    i = res = 0
    for d, r in romans_map:
        while n[i:i + len(r)] == r:
            res += d
            i += len(r)
    return res

def isRomanNumber(token):
    return re.compile(r"[IVXCLDM]+(er)?", re.I).match(token)

def isNumberWord(word):
    return wordToNumber(word) >= 0

def wordToNumber(word):
    words = [
        [u'un', u'une', u'premier', u'première'],
        [u'deux', u'deuxième', u'second', u'seconde'],
        [u'trois', u'troisième'],
        [u'quatre', u'quatrième'],
        [u'cinq', u'cinquième'],
        [u'six', u'sixième'],
        [u'sept', u'septième'],
        [u'huit', u'huitième'],
        [u'neuf', u'neuvième']
    ]

    for i in range(0, len(words)):
        if word in words[i]:
            return i + 1

    return -1

def monthToNumber(month):
    return TOKEN_MONTH_NAMES.index(month) + 1

def unshiftNode(parent, node):
    node['parent'] = parent
    parent['children'] = [node] + parent['children']

def pushNode(parent, node):
    node['parent'] = parent
    parent['children'].append(node)

def createNode(parent, node):
    pushNode(parent, node)
    node['children'] = []

    return node

def removeNode(parent, node):
    parent['children'].remove(node)

def deleteParent(root):
    if 'parent' in root:
        del root['parent']
    if 'children' in root:
        for child in root['children']:
            deleteParent(child)
    return root

def removeEmptyChildrenList(root):
    if 'children' in root and len(root['children']) == 0:
        del root['children']

    if 'children' in root:
        for child in root['children']:
            removeEmptyChildrenList(child)

def getNodeDepth(node):
    if not 'parent' in node:
        return 0
    return 1 + getNodeDepth(node['parent'])

def getRoot(node):
    while 'parent' in node:
        node = node['parent']

    return node

def filterNodes(root, fn):
    return filterNodesRec(root, fn, [])

def filterNodesRec(root, fn, results):
    if fn(root):
        results.append(root)

    if 'children' in root:
        for child in root['children']:
            filterNodesRec(child, fn, results)

    return results

def parseLawReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'law-reference',
        'lawId': '',
        'children': [],
    })

    debug(node, tokens, i, 'parseLawReference')

    # de l'ordonnance
    # l'ordonnance
    if tokens[i + 2] == u'ordonnance' or tokens[i + 4] == u'ordonnance':
        node['lawType'] = 'ordonnance'
        i = skipToToken(tokens, i, u'ordonnance') + 2
    # de la loi
    # la loi
    elif (tokens[i] == u'la' and tokens[i + 2] == u'loi') or (tokens[i] == u'de' and tokens[i + 4] == u'loi'):
        i = skipToToken(tokens, i, u'loi') + 2
    else:
        removeNode(parent, node)
        return i

    if tokens[i] == u'organique':
        node['lawType'] = 'organic'
        i += 2

    i = skipToToken(tokens, i, u'n°') + 1
    i = skipSpaces(tokens, i)
    node['lawId'] = tokens[i]
    # skip {lawId} and the following space
    i += 2

    if tokens[i] == u'du':
        node['lawDate'] = tokens[i + 6] + u'-' + str(monthToNumber(tokens[i + 4])) + u'-' + tokens[i + 2]
        # skip {lawDate} and the following space
        i += 7

    debug(node, tokens, i, 'parseLawReference end')

    return i

def parseMultiplicativeAdverb(tokens, i, node):
    if i >= len(tokens):
        return i

    adverbs = TOKEN_MULTIPLICATIVE_ADVERBS.sort(key = lambda s: -len(s))
    for adverb in TOKEN_MULTIPLICATIVE_ADVERBS:
        if tokens[i].endswith(adverb):
            node['is' + adverb.title()] = True;
            # skip {multiplicativeAdverb} and the following space
            return i + 2
    return i

def parseDefinition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parseDefinition')

    j = parseArticleDefinition(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseAlineaDefinition(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseMentionDefinition(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseHeader1Definition(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseHeader2Definition(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseWordsDefinition(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseTitleDefinition(tokens, i, parent)
    if j != i:
        return j
    i = j

    return i

def parseWordsDefinition(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'words',
        'children': []
    })
    debug(node, tokens, i, 'parseWordsDefinition')
    j = i
    i = parsePosition(tokens, i, node)
    # le mot
    # les mots
    # des mots
    if tokens[i].lower() in [u'le', u'les', u'des'] and tokens[i + 2].startswith(u'mot'):
        i = skipToQuoteStart(tokens, i)
        i = parseForEach(parseQuote, tokens, i, node)
        # i = skipSpaces(tokens, i)
    else:
        debug(node, tokens, i, 'parseWordsDefinition none')
        removeNode(parent, node)
        return j
    debug(node, tokens, i, 'parseWordsDefinition end')
    return i

def parseArticleDefinition(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'article',
        'children': [],
    })
    debug(node, tokens, i, 'parseArticleDefinition')
    if tokens[i] == u'un' and tokens[i + 2] == u'article':
        i += 4
    else:
        debug(node, tokens, i, 'parseArticleDefinition none')
        removeNode(parent, node)
        return i

    i = parseArticleId(tokens, i, node)
    i = parseForEach(parseQuote, tokens, i, node)

    debug(node, tokens, i, 'parseArticleDefinition end')

    return i

def parseAlineaDefinition(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'alinea',
        'children': [],
    })
    debug(node, tokens, i, 'parseAlineaDefinition')

    # {count} alinéa(s)
    if isNumberWord(tokens[i]) and tokens[i + 2].startswith(u'alinéa'):
        i += 4
    else:
        debug(node, tokens, i, 'parseAlineaDefinition none')
        removeNode(parent, node)
        return i

    i = parseForEach(parseQuote, tokens, i, node)

    debug(node, tokens, i, 'parseAlineaDefinition end')

    return i

def parseMentionDefinition(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'mention',
        'children': []
    })
    debug(node, tokens, i, 'parseMentionDefinition')
    if tokens[i].lower() == u'la' and tokens[i + 2] == u'mention':
        i += 4
    else:
        debug(node, tokens, i, 'parseMentionDefinition none')
        removeNode(parent, node)
        return i
    # :
    if tokens[i] == ':':
        i = skipToQuoteStart(tokens, i)
        i = parseForEach(parseQuote, tokens, i, node)

    debug(node, tokens, i, 'parseMentionDefinition end')

    return i

def parseHeader1Definition(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'header1',
        'children': []
    })
    debug(node, tokens, i, 'parseHeader1Definition')
    # un {romanPartNumber}
    if tokens[i].lower() == u'un' and isRomanNumber(tokens[i + 2]):
        node['order'] = parseRomanNumber(tokens[i + 2])
        i += 4
    else:
        debug(node, tokens, i, 'parseHeader1Definition end')
        removeNode(parent, node)
        return i

    i = parseQuote(tokens, i, node)

    return i

def parseHeader2Definition(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'header2',
        'children': []
    })
    debug(node, tokens, i, 'parseHeader2Definition')
    # un ... ° ({articlePartRef})
    if tokens[i].lower() == u'un' and ''.join(tokens[i + 2:i + 5]) == u'...' and tokens[i + 6] == u'°':
        node['order'] = '...'
        i += 8
    # un {order}° ({multiplicativeAdverb}) ({articlePartRef})
    elif tokens[i].lower() == u'un' and re.compile(u'\d+°').match(tokens[i + 2]):
        node['order'] = parseInt(tokens[i + 2])
        i += 4
        i = parseMultiplicativeAdverb(tokens, i, node)
        i = parseArticlePartReference(tokens, i, node)
    else:
        debug(node, tokens, i, 'parseHeader2Definition end')
        removeNode(parent, node)
        return i

    i = parseQuote(tokens, i, node)

    return i

def parseArticleId(tokens, i, node):
    node['id'] = ''

    # article {articleId} de {lawReference}
    if tokens[i] == 'L' and tokens[i + 1] == '.':
        while not re.compile('\d+(-\d+)?').match(tokens[i]):
            node['id'] += tokens[i]
            i += 1

    if re.compile('\d+(-\d+)?').match(tokens[i]):
        node['id'] += tokens[i]
        # skip {articleId} and the following space
        i += 2

    # {articleId} {articleLetter}
    if re.compile('[A-Z]').match(tokens[i]):
        node['id'] += ' ' + tokens[i]
        # skip {articleLetter} and the following space
        i += 2

    i = parseMultiplicativeAdverb(tokens, i, node)

    if isSpace(node['id']):
        del node['id']

    return i

def parseTitleReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'title-reference',
        'children': [],
    })

    debug(node, tokens, i, 'parseTitleReference')

    j = i
    i = parsePosition(tokens, i, node)

    # le titre {order}
    if tokens[i].lower() == u'le' and tokens[i + 2] == u'titre' and isRomanNumber(tokens[i + 4]):
        node['order'] = parseRomanNumber(tokens[i + 4])
        i += 6
        i = parseMultiplicativeAdverb(tokens, i, node)
    else:
        debug(node, tokens, i, 'parseTitleReference none')
        removeNode(parent, node)
        return j

    i = parseReference(tokens, i, node)

    debug(node, tokens, i, 'parseTitleReference end')

    return i

def parseTitleDefinition(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'title',
        'children': [],
    })

    debug(node, tokens, i, 'parseTitleDefinition')

    # un titre {order}
    if tokens[i].lower() == u'un' and tokens[i + 2] == u'titre' and isRomanNumber(tokens[i + 4]):
        node['order'] = parseRomanNumber(tokens[i + 4])
        i += 6
        i = parseMultiplicativeAdverb(tokens, i, node)
    else:
        debug(node, tokens, i, 'parseTitleDefinition none')
        removeNode(parent, node)
        return i

    i = parseForEach(parseQuote, tokens, i, node)

    debug(node, tokens, i, 'parseTitleDefinition end')

    return i

def parseBookReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'book-reference',
        'children': [],
    })

    debug(node, tokens, i, 'parseBookReference')

    j = i
    i = parsePosition(tokens, i, node)

    # le titre {order}
    if tokens[i].lower() == u'du' and tokens[i + 2] == u'livre' and isRomanNumber(tokens[i + 4]):
        node['order'] = parseRomanNumber(tokens[i + 4])
        i += 6
    else:
        debug(node, tokens, i, 'parseBookReference none')
        removeNode(parent, node)
        return j

    i = parseReference(tokens, i, node)

    debug(node, tokens, i, 'parseBookReference end')

    return i

def parseArticleReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'article-reference',
        'id': '',
        'children': [],
    })

    debug(node, tokens, i, 'parseArticleReference')

    j = i
    i = parsePosition(tokens, i, node)
    # de l'article
    if tokens[i].lower() == u'de' and tokens[i + 2] == u'l' and tokens[i + 4] == 'article':
        i += 6
    # skip "l’article" and the following space
    elif tokens[i].lower() == u'l' and tokens[i + 1] == TOKEN_SINGLE_QUOTE and tokens[i + 2] == u'article':
        i += 4
    # elif tokens[i] == u'un' and tokens[i + 2] == u'article':
    #     i += 4
    elif tokens[i].startswith(u'article'):
        i += 2
    else:
        removeNode(parent, node)
        return j

    i = parseArticleId(tokens, i, node)

    # i = parseArticlePartReference(tokens, i, node)

    # de la loi
    # de l'ordonnance
    i = parseReference(tokens, i, node)

    # i = parseQuote(tokens, i, node)

    debug(node, tokens, i, 'parseArticleReference end')

    return i

def parsePosition(tokens, i, node):
    if i >= len(tokens):
        return i

    j = i
    i = skipToNextWord(tokens, i)

    # après
    if tokens[i].lower() == u'après':
        node['position'] = 'after'
        i += 2
    # avant
    elif tokens[i].lower() == u'avant':
        node['position'] = 'before'
        i += 2
    # au début
    elif tokens[i].lower() == u'au' and tokens[i + 2] == u'début':
        node['position'] = 'beginning'
        i += 4
    # la fin du {article}
    elif tokens[i] == u'la' and tokens[i + 2] == u'fin':
        node['position'] = 'end'
        i += 4
    # à la fin du {article}
    elif tokens[i].lower() == u'à' and tokens[i + 2] == u'la' and tokens[i + 4] == u'fin':
        node['position'] = 'end'
        i += 6
    else:
        return j

    return i

def parseAlineaReference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'alinea-reference',
        'children': []
    })
    debug(node, tokens, i, 'parseAlineaReference')
    j = i
    i = parsePosition(tokens, i, node)
    # le {order} alinéa
    # du {order} alinéa
    if tokens[i].lower() in [u'du', u'le', u'un'] and isNumberWord(tokens[i + 2]) and tokens[i + 4].startswith(u'alinéa'):
        node['order'] = wordToNumber(tokens[i + 2])
        i += 6
    # l'alinéa
    elif tokens[i].lower() == u'l' and tokens[i + 2].startswith(u'alinéa'):
        i += 4
    # de l'alinéa
    elif tokens[i] == 'de' and tokens[i + 2].lower() == [u'l'] and tokens[i + 4].startswith(u'alinéa'):
        i += 6
    # {order} {partType}
    elif isNumberWord(tokens[i].lower()) and tokens[i + 2].startswith(u'alinéa'):
        node['order'] = wordToNumber(tokens[i])
        i += 4
    # le même alinéa
    elif tokens[i].lower() in [u'le'] and tokens[i + 2] == u'même' and tokens[i + 4] == u'alinéa':
        alineaRefs = filterNodes(
            getRoot(parent),
            lambda n: 'type' in n and n['type'] == 'alinea-reference'
        )
        # the last one in order of traversal is the previous one in order of syntax
        # don't forget the current node is in the list too => -2 instead of -1
        alinea = alineaRefs[-2].copy()
        pushNode(node, alinea)
    # du dernier alinéa
    elif tokens[i].lower() == u'du' and tokens[i + 2] == u'dernier' and tokens[i + 4] == u'alinéa':
        node['order'] = -1
        i += 6
    else:
        debug(node, tokens, i, 'parseAlineaReference none')
        removeNode(parent, node)
        return j

    i = parseArticlePartReference(tokens, i, node)
    # i = parseQuote(tokens, i, node)

    debug(node, tokens, i, 'parseAlineaReference end')

    return i

def parseSentenceReference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'sentence-reference',
        'children': []
    })
    debug(node, tokens, i, 'parseSentenceReference')
    j = i
    i = parsePosition(tokens, i, node)
    # une phrase
    # la phrase
    if tokens[i].lower() in [u'la', u'une'] and tokens[i + 2] == 'phrase':
        i += 4
    # de la {partNumber} phrase
    elif tokens[i].lower() == u'de' and tokens[i + 2] == u'la' and isNumberWord(tokens[i + 4]) and tokens[i + 6] == u'phrase':
        node['order'] = wordToNumber(tokens[i + 4])
        i += 8
    # la {partNumber} phrase
    elif tokens[i].lower() == u'la' and isNumberWord(tokens[i + 2]) and tokens[i + 4] == u'phrase':
        node['order'] = wordToNumber(tokens[i + 2])
        i += 6
    # à la {partNumber} phrase
    elif tokens[i].lower() == u'à' and tokens[i + 2].lower() == u'la' and isNumberWord(tokens[i + 4]) and tokens[i + 6] == u'phrase':
        node['order'] = wordToNumber(tokens[i + 4])
        i += 8
    else:
        debug(node, tokens, i, 'parseSentenceReference none')
        removeNode(parent, node)
        return j

    i = parseArticlePartReference(tokens, i, node)

    debug(node, tokens, i, 'parseSentenceReference end')

    fixIncompleteReferences(parent, node)

    return i

def fixIncompleteReferences(parent, node):
    if len(parent['children']) >= 2:
        for child in parent['children']:
            if child['type'] == 'incomplete-reference':
                # set the actual reference type
                child['type'] = node['type']
                # copy all the child of the fully qualified reference node
                for c in node['children']:
                    pushNode(child, c.copy())

def copyNode(node):
    c = node.copy()
    children = node['children']
    node['children'] = []
    for child in children:
        pushNode(node, copyNode(child))
    return c

def parseBackReference(tokens, i, parent):
    if i >= len(tokens):
        return i
    if tokens[i] == u'Il':
        refs = filterNodes(
            getRoot(parent),
            lambda n: 'type' in n and n['type'].endswith('-reference')
        )
        for j in reversed(range(0, len(refs))):
            if getNodeDepth(refs[j]) <= getNodeDepth(parent):
                pushNode(parent, copyNode(refs[j]))
                break
        i += 2
    return i

def parseIncompleteReference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'incomplete-reference',
        'children': []
    })
    j = i
    i = parsePosition(tokens, i, node)
    if tokens[i].lower() == u'à' and tokens[i + 2] in [u'le', u'la'] and isNumberWord(tokens[i + 4]):
        node['order'] = wordToNumber(tokens[i + 4])
        i += 6
    elif tokens[i].lower() in [u'le', u'la'] and isNumberWord(tokens[i + 2]):
        node['order'] = wordToNumber(tokens[i + 2])
        i += 4
    else:
        removeNode(parent, node)
        return j

    return i

def parseWordsReference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'words-reference',
        'children': []
    })
    debug(node, tokens, i, 'parseWordsReference')
    j = i
    i = parsePosition(tokens, i, node)
    # le mot
    # les mots
    # des mots
    if tokens[i].lower() in [u'le', u'les', u'des'] and tokens[i + 2].startswith(u'mot'):
        i = skipToQuoteStart(tokens, i)
        i = parseForEach(parseQuote, tokens, i, node)
    else:
        debug(node, tokens, i, 'parseWordsReference none')
        removeNode(parent, node)
        return j
    debug(node, tokens, i, 'parseWordsReference end')
    return i

def parseHeader2Reference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'header2-reference',
        'children': []
    })
    debug(node, tokens, i, 'parseHeader2Reference')
    j = i
    i = parsePosition(tokens, i, node)
    # le {order}° ({multiplicativeAdverb}) ({articlePartRef})
    # du {order}° ({multiplicativeAdverb}) ({articlePartRef})
    # au {order}° ({multiplicativeAdverb}) ({articlePartRef})
    if tokens[i].lower() in [u'le', u'du', u'au'] and re.compile(u'\d+°').match(tokens[i + 2]):
        node['order'] = parseInt(tokens[i + 2])
        i += 4
        i = parseMultiplicativeAdverb(tokens, i, node)
        i = parseArticlePartReference(tokens, i, node)
    else:
        debug(node, tokens, i, 'parseHeader2Reference none')
        removeNode(parent, node)
        return j
    # i = parseQuote(tokens, i, node)
    debug(node, tokens, i, 'parseHeader2Reference end')
    return i

def parseHeader1Reference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = createNode(parent, {
        'type': 'header1-reference',
        'children': []
    })
    debug(node, tokens, i, 'parseHeader1Reference')
    j = i
    i = parsePosition(tokens, i, node)
    # le {romanPartNumber}
    # du {romanPartNumber}
    if tokens[i].lower() in [u'le', u'du'] and isRomanNumber(tokens[i + 2]):
        node['order'] = parseRomanNumber(tokens[i + 2])
        i += 4
    else:
        debug(node, tokens, i, 'parseHeader1Reference end')
        removeNode(parent, node)
        return j

    i = parseArticlePartReference(tokens, i, node)
    # i = parseQuote(tokens, i, node)

    debug(node, tokens, i, 'parseHeader1Reference end')

    return i

def parseArticlePartReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    i = skipToNextWord(tokens, i)

    j = parseAlineaReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseSentenceReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseWordsReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseArticleReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseHeader1Reference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseHeader2Reference(tokens, i, parent)
    if j != i:
        return j
    i = j

    return i

def parseQuote(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'quote',
        'words': ''
    })

    debug(node, tokens, i, 'parseQuote')

    i = skipSpaces(tokens, i)

    # "
    if tokens[i] == TOKEN_DOUBLE_QUOTE_OPEN:
        debug(node, tokens, i, 'parseQuote end')
        i += 1
    # est rédigé(e)
    # est ainsi rédigé(e)
    elif (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
        or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
        i = skipToQuoteStart(tokens, i + 2) + 1
    else:
        removeNode(parent, node)
        return i

    while i < len(tokens) and tokens[i] != TOKEN_DOUBLE_QUOTE_CLOSE and tokens[i] != TOKEN_NEW_LINE:
        node['words'] += tokens[i]
        i += 1

    # skip TOKEN_DOUBLE_QUOTE_CLOSE
    i += 1
    i = skipSpaces(tokens, i)

    debug(node, tokens, i, 'parseQuote end')

    return i

def parseEdit(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'edit',
        'children': [],
    })

    debug(node, tokens, i, 'parseEdit')

    r = i
    i = parseForEach(parseReference, tokens, i, node)
    # if we did not parse a reference
    if len(node['children']) == 0:
        removeNode(parent, node)
        debug(node, tokens, i, 'parseEdit none')
        return i
    i = r

    j = i
    i = skipTokens(tokens, i, lambda t: t != 'est' and t != 'sont')

    if i >= len(tokens):
        removeNode(parent, node)
        debug(node, tokens, i, 'parseEdit eof')
        return j

    # sont supprimés
    # sont supprimées
    # est supprimé
    # est supprimée
    # est abrogé
    # est abrogée
    # sont abrogés
    # sont abrogées
    if tokens[i + 2].startswith(u'supprimé') or tokens[i + 2].startswith(u'abrogé'):
        node['editType'] = 'delete'
        i = skipToEndOfLine(tokens, i)
    # est ainsi modifié
    # est ainsi rédigé
    elif tokens[i + 4] == u'modifié' or tokens[i + 4] == u'rédigé':
        node['editType'] = 'edit'
        i = skipToEndOfLine(tokens, i)
        i = parseForEach(parseQuote, tokens, i, node)
    # est remplacé par
    # est remplacée par
    # sont remplacés par
    # sont remplacées par
    elif tokens[i + 2].startswith(u'remplacé'):
        node['editType'] = 'replace'
        i += 6
        i = parseDefinition(tokens, i, node)
    # est inséré
    # est insérée
    # sont insérés
    # sont insérées
    # est ajouté
    # est ajoutée
    # sont ajoutés
    # sont ajoutées
    elif tokens[i + 2].startswith(u'inséré') or tokens[i + 2].startswith(u'ajouté'):
        node['editType'] = 'add'
        i += 4
        i = parseDefinition(tokens, i, node)
        i = skipToEndOfLine(tokens, i)
    # est complété par
    elif tokens[i + 2] == u'complété':
        node['editType'] = 'add'
        i += 6
        i = parseDefinition(tokens, i, node)
    else:
        i = r
        debug(node, tokens, i, 'parseEdit remove')
        removeNode(parent, node)
        i = parseRawArticleContent(tokens, i, parent)
        return i

    debug(node, tokens, i, 'parseEdit end')

    return i

def parseRawArticleContent(tokens, i, parent):
    node = createNode(parent, {
        'type': 'article-content',
        'content': ''
    })

    debug(node, tokens, i, 'parseRawArticleContent')

    while i < len(tokens) and tokens[i] != TOKEN_NEW_LINE:
        node['content'] += tokens[i]
        i += 1

    if node['content'] == '' or isSpace(node['content']):
        removeNode(parent, node)

    debug(node, tokens, i, 'parseRawArticleContent end')

    return i


def parseCodeName(tokens, i, node):
    while i < len(tokens) and tokens[i] != u',' and tokens[i] != u'est':
        node['codeName'] += tokens[i]
        i += 1
    node['codeName'] = node['codeName'].strip()
    return i

def parseCodeReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'code-reference',
        'codeName': '',
        'children': []
    })

    debug(node, tokens, i, 'parseCodeReference')

    # code
    if tokens[i] == u'code':
        i = parseCodeName(tokens, i, node)
    # le code
    # du code
    elif tokens[i].lower() in [u'le', u'du'] and tokens[i + 2] == 'code':
        print('foo')
        i = parseCodeName(tokens, i + 2, node)
    # le même code
    elif tokens[i].lower() == 'le' and tokens[i + 2] == u'même' and tokens[i + 4] == 'code':
        removeNode(parent, node)
        codeRefs = filterNodes(
            getRoot(parent),
            lambda n: 'type' in n and n['type'] == 'code-reference'
        )
        print(parent)
        # the last one in order of traversal is the previous one in order of syntax
        node = codeRefs[-1].copy()
        pushNode(parent, node)
        # skip "le même code "
        i += 6

    if node['codeName'] == '' or isSpace(node['codeName']):
        removeNode(parent, node)

    debug(node, tokens, i, 'parseCodeReference end')

    return i

def parseReference(tokens, i, parent):
    if i >= len(tokens):
        return i

    # i = skipSpaces(tokens, i)
    i = skipToNextWord(tokens, i)

    if i >= len(tokens):
        return i

    # j = parsePosition(tokens, i, parent)
    # if j != i:
    #     return j
    # i = j

    j = parseLawReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseCodeReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseTitleReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseBookReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseArticleReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseArticlePartReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    j = parseBackReference(tokens, i, parent)
    if j != i:
        return j
    i = j

    i = parseIncompleteReference(tokens, i, parent)

    if tokens[i] == u'et':
        i += 2

    return i

# {romanNumber}.
# u'ex': I., II.
def parseArticleHeader1(tokens, i, parent):
    if i >= len(tokens):
        return i

    i = skipSpaces(tokens, i)

    node = createNode(parent, {
        'type': 'header-1',
        'order': 0,
        'children': [],
    })

    debug(node, tokens, i, 'parseArticleHeader1')

    # skip '{romanNumber}. - '
    if isRomanNumber(tokens[i]) and tokens[i + 1] == u'.':
        debug(node, tokens, i, 'parseArticleHeader1 found article header-1')

        node['order'] = parseRomanNumber(tokens[i])
        i = skipToNextWord(tokens, i + 2)
    else:
        removeNode(parent, node)
        node = parent

    i = parseEdit(tokens, i, node)
    i = parseForEach(parseArticleHeader2, tokens, i, node)

    if node != parent and len(node['children']) == 0:
        removeNode(parent, node)

    debug(node, tokens, i, 'parseArticleHeader1 end')

    return i

# {number}°
# u'ex': 1°, 2°
def parseArticleHeader2(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'header-2',
        'order': 0,
        'children': [],
    })

    debug(node, tokens, i, 'parseArticleHeader2')

    i = skipSpaces(tokens, i)
    if re.compile(u'\d+°').match(tokens[i]):
        debug(node, tokens, i, 'parseArticleHeader2 found article header-2')

        node['order'] = parseInt(tokens[i])
        # skip {number}°
        i = skipToNextWord(tokens, i + 2)
    else:
        removeNode(parent, node)
        node = parent

    i = parseEdit(tokens, i, node)
    i = parseForEach(parseArticleHeader3, tokens, i, node)

    if node != parent and len(node['children']) == 0:
        removeNode(parent, node)

    debug(node, tokens, i, 'parseArticleHeader2 end')

    return i

# {number})
# u'ex': a), b), a (nouveau))
def parseArticleHeader3(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = createNode(parent, {
        'type': 'header-3',
        'children': [],
    })

    debug(node, tokens, i, 'parseArticleHeader3')

    i = skipSpaces(tokens, i)
    match = re.compile('([a-z]+)').match(tokens[i])
    if match and (tokens[i + 1] == u')' or (tokens[i + 2] == u'(' and tokens[i + 5] == u')')):
        node['order'] = ord(match.group()[0].encode('utf-8')) - ord('a') + 1
        # skip '{number}) ' or '{number} (nouveau))'
        if tokens[i + 1] == u')':
            i += 3
        else:
            i += 7
        # i = parseEdit(tokens, i, node)
    else:
        removeNode(parent, node)
        node = parent

    i = parseEdit(tokens, i, node)

    if node != parent and len(node['children']) == 0:
        removeNode(parent, node)

    debug(node, tokens, i, 'parseArticleHeader3 end')

    return i

def parseForEach(fn, tokens, i, parent):
    test = fn(tokens, i, parent)

    while (test != i):
        i = test
        test = fn(tokens, i, parent)

    return i

def parseJSONArticles(data, parent):
    if 'articles' in data:
        for article_data in data['articles']:
            parseJSONArticle(article_data, parent)
    elif 'alineas' in data:
        parseJSONArticle(data, parent)

    return data

def parseJSONArticle(data, parent):
    node = createNode(parent, {
        'type': 'article',
        'children': [],
        'order': 1,
        'isNew': False
    })

    node['order'] = data['order']

    if 'alineas' in data:
        parseJSONAlineas(data['alineas'], node)

def parseJSONAlineas(data, parent):
    text = TOKEN_NEW_LINE.join(value for key, value in list(iter(sorted(data.iteritems()))))
    tokens = tokenize(text)
    parseForEach(parseArticleHeader1, tokens, 0, parent)

    if len(parent['children']) == 0:
        parseRawArticleContent(tokens, 0, parent)

def parseJSONData(data):
    node = {'children': []}

    parseJSONArticles(data, node)

    return node

def sortReferences(node):
    ref_types = [
        'code-reference',
        'book-reference',
        'title-reference',
        'article-reference',
        'header1-reference',
        'header2-reference',
        'header3-reference',
        'alinea-reference',
        'sentence-reference',
        'words-reference'
    ]
    root_refs = filterNodes(node, lambda n: 'type' in n and n['type'] in ref_types and 'parent' in n and n['parent']['type'] not in ref_types)
    for root_ref in root_refs:
        root_ref_parent = root_ref['parent']
        refs = filterNodes(root_ref, lambda n: 'type' in n and n['type'] in ref_types)
        sorted_refs = sorted(refs, key=lambda r: ref_types.index(r['type']))
        filtered_refs = [sorted_refs[0]]
        for ref in sorted_refs:
            removeNode(ref['parent'], ref)
            if ref['type'] != filtered_refs[-1]['type']:
                filtered_refs.append(ref)
        for i in range(0, len(filtered_refs)):
            ref = filtered_refs[i]
            if i == 0:
                pushNode(root_ref_parent, ref)
            else:
                pushNode(filtered_refs[i - 1], ref)

def resolveFullyQualifiedReferences(node):
    resolveFullyQualifiedReferences_rec(node, [])

def resolveFullyQualifiedReferences_rec(node, ctx):
    ref_types = [
        'code-reference',
        'book-reference',
        'title-reference',
        'article-reference',
        'header1-reference',
        'header2-reference',
        'header3-reference',
        'alinea-reference',
        'sentence-reference',
        'words-reference'
    ]
    if 'type' in node and node['type'] not in ref_types and len(node['children']) > 0 and node['children'][0]['type'] == 'edit' and node['children'][0]['editType'] == 'edit':
        context = node['children'][0]['children'][0]
        removeNode(node, node['children'][0])
        ctx.append([deleteParent(ctx_node.copy()) for ctx_node in filterNodes(context, lambda x: x['type'] in ref_types)])
        for child in node['children']:
            resolveFullyQualifiedReferences_rec(child, ctx)
        ctx.pop()
    elif len(ctx) > 0 and 'type' in node and node['type'] in ref_types and node['parent']['type'] not in ref_types:
        n = [item.copy() for sublist in ctx for item in sublist]
        for i in range(1, len(n)):
            unshiftNode(n[i - 1], n[i])
        unshiftNode(node['parent'], n[0])
        removeNode(node['parent'], node)
        unshiftNode(n[len(n) - 1], node)
    else:
        for child in node['children']:
            resolveFullyQualifiedReferences_rec(child, ctx)

def handleData(data):
    ast = parseJSONData(json.loads(data))

    resolveFullyQualifiedReferences(ast)
    sortReferences(ast)
    deleteParent(ast)
    removeEmptyChildrenList(ast)

    json_data = json.dumps(ast, sort_keys=True, indent=2, ensure_ascii=False).encode('utf-8')
    sys.stdout.write(json_data)

def usage():
    return ('usage:\n'
            '\python parse_texte_ast.py filename.json [-v]\n'
            '\tcat filename.json | python parse_texte_ast.py [-v]\n')

if len(sys.argv) >= 2 and sys.argv[1] != '-v':
    data = codecs.open(sys.argv[1], 'r', 'utf-8').read()
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)
    handleData(data)
else:
    data = sys.stdin.read()
    data = data.decode('utf-8')
    handleData(data)
