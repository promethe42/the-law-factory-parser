#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import json
import codecs

DELIMITERS = re.compile(u'(\xa0|\s|\(|\)|\.|\!|’|,)')
KEYWORD_ARTICLE = u'Article'
KEYWORD_NEW_ARTICLE = u'nouveau'
KEYWORD_ARTICLE_REFERENCE = u'article'
KEYWORD_PARTS = [
    u'article', u'articles',
    u'alinéa', u'alinéas',
    u'phrase', u'phrases'
]
KEYWORD_MONTH_NAMES = [
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
KEYWORDS = [
    KEYWORD_ARTICLE,
    KEYWORD_NEW_ARTICLE,
    KEYWORD_ARTICLE_REFERENCE
]

def tokenize(text):
    text = text.replace(u'\xa0', u' ')
    tokens = DELIMITERS.split(text)
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
    return skipTokens(tokens, i, lambda t: not re.compile('\w').match(t))

def skipToToken(tokens, i, token):
    return skipTokens(tokens, i, lambda t: t != token)

def skipToEndOfLine(tokens, i):
    return skipToToken(tokens, i, '\n')

def skipToQuoteStart(tokens, i):
    return skipToToken(tokens, i, u'«')

def isNumber(token):
    return re.compile('\d+').match(token)

def isSpace(token):
    return re.compile('^\s+$').match(token)

def isArticlePart(token):
    return KEYWORD_PARTS.index(token) >= 0

def parseInt(s):
    return int(re.search(r'\d+', s).group())

def parseRomanNumber(number):
    if number == u'I':
        return 1
    elif number == u'II':
        return 2
    elif number == u'III':
        return 3
    elif number == u'IV':
        return 4
    elif number == u'V':
        return 5
    elif number == u'VI':
        return 6
    elif number == u'VII':
        return 7
    elif number == u'VIII':
        return 8

    return -1


def isRomanNumber(token):
    return parseRomanNumber(token) != -1

def isNumberWord(word):
    return wordToNumber(word) >= 0

def wordToNumber(word):
    words = [
        ['un', u'une', u'premier', u'première'],
        ['deux', u'deuxième', u'second', u'seconde'],
        ['trois', u'troisième'],
        ['quatre', u'quatrième'],
        ['cinq', u'cinquième'],
        ['six', u'sixième'],
        ['sept', u'septième'],
        ['huit', u'huitième'],
        ['neuf', u'neuvième']
    ]

    for i in range(0, len(words)):
        if word in words[i]:
            return i + 1

    return -1

def monthToNumber(month):
    return KEYWORD_MONTH_NAMES.index(month) + 1

def createNode(parent, node):
    node['parent'] = parent
    parent['children'].append(node)

    return node

def removeNode(parent, node):
    parent['children'].remove(node)

def deleteParent(root):
    if 'parent' in root:
        del root['parent']

    if 'children' in root:
        for child in root['children']:
            deleteParent(child)

def parseLawReference(tokens, i, parent):

    if tokens[i].index(u'loi') < 0:
        return i

    node = createNode(parent, {
        'type': 'law-reference',
        'lawId': '',
        'children': [],
    })

    # sip u'loi' and the following space
    i += 2

    if tokens[i] == u'organique':
        i = skipToToken(tokens, i, u'n°') + 1
        i = skipSpaces(tokens, i)
        node['lawType'] = 'organic'
        node['lawId'] = tokens[i]
        # skip {lawId} and the following space
        i += 2

    if tokens[i] == u'du':
        node['lawDate'] = tokens[i + 6] + u'-' + str(monthToNumber(tokens[i + 4])) + u'-' + tokens[i + 2]
        # skip {lawDate} and the following space
        i += 7

    # print('parseLawReference end', tokens[i:i+4])

    return i


# article {articleId} du code {codeName}, les mots :
# article {articleId} du code {codeName} est ainsi modifié :
def parseArticleReference(tokens, i, parent):
    # print('parseArticleReference', tokens[i:i+4])

    if tokens[i].startswith(u'article') < 0 and tokens[i] != u'L' and tokens[i + 1] != u'.':
        return i

    node = createNode(parent, {
        'type': 'article-reference',
        'articleId': '',
        'children': [],
    })

    # skip "l’article" and the following space
    if tokens[i].lower() == u'l' and tokens[i + 1] == u'’' and tokens[i + 2] == u'article':
        i += 4
    # skip "article" and the following space
    elif tokens[i].startswith(u'article'):
        i += 2

    # article {articleId} de {lawReference}
    if isNumber(tokens[i]):
        node['articleId'] = parseInt(tokens[i])
        if tokens[i + 2] == u'de' and tokens[i + 6] == u'loi':
            i = parseLawReference(tokens, i + 6, node)
    # article {articleId} du code {codeReference}
    else:
        while i < len(tokens) and not re.compile('\d+(-[\d+])*').match(tokens[i - 1]):
            node['articleId'] += tokens[i]
            i += 1
        node['articleId'] = node['articleId'].strip()

        i = skipSpaces(tokens, i)

        if tokens[i] == u'du':
            i = parseCodeReference(tokens, i + 2, node)

    # print('parseArticleReference end', tokens[i:i+4])

    return i


def parseArticlePartReference(tokens, i, parent):
    # print('parseArticlePartReference', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'article-part-reference',
        'children': []
    })

    # après
    if tokens[i].lower() == u'après':
        node['partOffset'] = 'after'
        i += 2
    # la fin du {article}
    elif tokens[i] == u'la' and tokens[i + 2] == u'fin':
        node['partOffset'] = 'end'
        i += 4
    # à la fin du {article}
    elif tokens[i].lower() == u'à' and tokens[i + 2] == u'la' and tokens[i + 4] == u'fin':
        node['partOffset'] = 'end'
        i += 6

    # de la {partNumber} {partType}
    if tokens[i].lower() == u'de' and tokens[i + 2] == u'la' and isNumberWord(tokens[i + 4]):
        i += 4
        if tokens[i + 2] == u'phrase':
            node['partType'] == u'sentence'
            node['partNumber'] = wordToNumber(tokens[i])
            i = parseArticlePartReference(tokens, i + 4, node)
    # le {partNumber} {partType}
    # du {partNumber} {partType}
    # un {partNumber} {partType}
    # au {partNumber} {partType}
    # la {partNumber} {partType}
    elif tokens[i].lower() in [u'le', u'du', u'un', u'au', u'la'] and isNumberWord(tokens[i + 2]):
        node['partNumber'] = wordToNumber(tokens[i + 2])
        if tokens[i + 4] == u'alinéa':
            node['partType'] = 'alinea'
        elif tokens[i + 4] == u'phrase':
            node['partType'] = 'sentence'
        i = parseArticlePartReference(tokens, i + 6, node)
    # le {partNumber}°
    # du {partNumber}°
    # un {partNumber}°
    # au {partNumber}°
    elif tokens[i].lower() in [u'le', u'du', u'un', u'au'] and re.compile(u'\d+°').match(tokens[i + 2]):
        node['partType'] = 'header-2'
        node['partNumber'] = parseInt(tokens[i + 2])
        i += 4
        if tokens[i] == u'bis':
            node['isBis'] = True
            i += 2
        elif tokens[i] == u'ter':
            node['isTer'] = True
            i += 2
        i = parseArticlePartReference(tokens, i, node)
        # ainsi rédigé
        if tokens[i + 2] == u'rédigé':
            i = skipToQuoteStart(tokens, i + 2)
            i = parseForEach(parseQuote, tokens, i, node)
    # le {romanPartNumber}
    # du {romanPartNumber}
    elif tokens[i].lower() in [u'le', u'du', u'un'] and isRomanNumber(tokens[i + 2]):
        node['partType'] = 'header-1'
        node['partNumber'] = parseRomanNumber(tokens[i + 2])
        # find u'article'
        i = skipTokens(tokens, i, lambda t: not t.startswith(u'article'))
        i = parseArticleReference(tokens, i, node)
    # l'{partType} {partNumber}
    elif tokens[i].lower() == u'l' and tokens[i + 1] == u'’':
        if tokens[i + 2] == u'article':
            i = parseArticleReference(tokens, i + 2, node)
        else:
            i = parseArticlePartReference(tokens, i + 2, node)
    # de l'{partType} {partNumber}
    elif tokens[i].lower() == u'de' and tokens[i + 2] == u'l' and tokens[i + 3] == u'’':
        if tokens[i + 4] == u'article':
            i = parseArticleReference(tokens, i + 4, node)
        else:
            i = parseArticlePartReference(tokens, i + 4, node)
    # des {partType}
    # les {partType}
    elif tokens[i].lower() in [u'des', u'les']:
        # les mots
        if tokens[i + 2] == u'mots':
            node['partType'] = 'sentence'
            i = skipToQuoteStart(tokens, i)
            i = parseForEach(parseQuote, tokens, i, parent)
            i = skipSpaces(tokens, i)
        else:
            i = parseArticleReference(tokens, i + 2, parent)
            i = skipSpaces(tokens, i)
            if tokens[i] == u'et':
                return parseArticleReference(tokens, i + 2, parent)
    # {number} {partType}
    elif isNumberWord(tokens[i].lower()) and isArticlePart(tokens[i + 2]):
        if tokens[i + 2].startswith(u'alinéa'):
            node['partType'] = 'alinea'
            i += 4
        elif tokens[i + 2].startswith(u'phrase'):
            node['partType'] = 'sentence'
            i += 4
        elif tokens[i + 2].startswith(u'article'):
            i = parseArticleReference(tokens, i + 2, node)
        # ainsi rédigé(e)
        if tokens[i + 2].startswith(u'rédigé'):
            i = skipToQuoteStart(tokens, i + 2)
            i = parseForEach(parseQuote, tokens, i, node)
            # print('parseArticlePartReference end', tokens[i:i+4])
    # le même
    elif tokens[i].lower() in [u'le'] and tokens[i + 2] == u'même':
        # "le même {number} {part}" or "le même {part}"
        if tokens[i + 4] == u'alinéa' or tokens[i + 6] == u'alinéa':
            alineas = searchNode(
                getRoot(parent),
                lambda n: 'type' in n and n['type'] == 'article-part-reference' and 'partType' in n and n['partType'] == 'alinea'
            )
            # the last one in order of traversal is the previous one in order of syntax
            node['children'].append(alineas[len(alineas) - 1])

            node['partType'] = 'alinea'

            if tokens[i + 4] == u'alinéa':
                i += 6
            else:
                i += 8
    else:
        removeNode(parent, node)

    # print('parseArticlePartReference end', tokens[i:i+4])

    return i


def getRoot(node):
    while 'parent' in node:
        node = node['parent']

    return node


def searchNode(root, fn):
    return searchNodeRec(root, fn, [])

def searchNodeRec(root, fn, results):
    if fn(root):
        results.append(root)

    if 'children' in root:
        for child in root['children']:
            searchNodeRec(child, fn, results)

    return results

def parseQuote(tokens, i, parent):
    # print('parseQuote', tokens[i:i+4])

    if tokens[i] != u'«':
        return i

    node = createNode(parent, {
        'type': 'quote',
        'words': ''
    })

    # skip the '«'
    i += 1

    while i < len(tokens) and tokens[i] != u'»' and tokens[i] != '\n':
        node['words'] += tokens[i]
        i += 1
    node['words'] = node['words'].strip()

    # skip '»'
    i += 1
    i = skipSpaces(tokens, i)

    # print('parseQuote end', tokens[i:i+4])

    return i

def parseArticleEdit(tokens, i, parent):
    # print('parseArticleEdit', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'article-edit',
        'children': [],
    })

    i = parseForEach(parseReference, tokens, i, node)
    # i = parseReference(tokens, i, node)
    # i = skipToNextWord(tokens, i)

    # sont supprimés
    # est supprimé
    if tokens[i + 2].startswith(u'supprimé'):
        node['editType'] = 'delete'
        i = skipToEndOfLine(tokens, i)
    # est ainsi modifié
    elif tokens[i + 4] == u'modifié':
        node['editType'] = 'edit'
        i = skipToEndOfLine(tokens, i)
    # est remplacé par
    # sont remplacés par
    elif tokens[i + 2].startswith(u'remplacé'):
        node['editType'] = 'replace'
        # skip "est remplacé par" or "sont remplacé par"
        i += 6
        i = parseReference(tokens, i, node)
    # il est inséré
    # il est ajouté
    elif tokens[i + 4] == u'inséré' or tokens[i + 4] == u'ajouté':
        node['editType'] = 'add'
        i = parseReference(tokens, i + 6, node)
        # i = skipToEndOfLine(tokens, i)
    # est complété par
    elif tokens[i + 2] == u'complété':
        node['editType'] = 'add'
        i = parseReference(tokens, i + 6, node)
        # i = skipToEndOfLine(tokens, i)
    # est abrogé
    elif tokens[i + 2] == u'abrogé':
        node['editType'] = 'delete'
        i = skipToEndOfLine(tokens, i)
    elif parent['type'] == 'article' and parent['isNew'] and parent.len(children) == 0:
        node['editType'] = 'add'
        i = parseNewArticleContent(tokens, i, node)
    else:
        removeNode(parent, node)

    # print('parseArticleEdit end', tokens[i:i+4])

    return i


def parseNewArticleContent(tokens, i, parent):
    # print('parseNewArticleContent', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'article-content',
        articleContent: ''
    })

    while i < len(tokens) and tokens[i] != '\n':
        node['articleContent'] += tokens[i]
        i += 1

    if node['articleContent'] == '' or isSpace(node['articleContent']):
        removeNode(parent, node)

    # print('parseNewArticleContent end', tokens[i:i+4])

    return i


def parseCodeReference(tokens, i, parent):
    # print('parseCodeReference', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'code-reference',
        'codeName': ''
    })

    if tokens[i] != u'code':
        return i

    while i < len(tokens) and tokens[i] != u',' and tokens[i] != u'est':
        node['codeName'] += tokens[i]
        i += 1
    node['codeName'] = node['codeName'].strip()

    if node['codeName'] == '' or isSpace(node['codeName']):
        removeNode(parent, node)

    # print('parseCodeReference end', tokens[i:i+4])

    return i

def parseReference(tokens, i, parent):
    # print('parseReference', tokens[i:i+4])

    # i = skipSpaces(tokens, i)
    i = skipToNextWord(tokens, i)

    # L’article L. 260 du code électoral
    if tokens[i].lower() == u'l' and tokens[i + 1] == u'’' and tokens[i + 2] == u'article':
        i = parseArticleReference(tokens, i, parent)
    elif tokens[i].lower() == u'le' and tokens[i + 2] == u'code':
        i = parseCodeReference(tokens, i + 2, parent)
    else:
        i = parseArticlePartReference(tokens, i, parent)

    # print('parseReference end', tokens[i:i+4])

    return i

# {romanNumber}.
# u'ex': I., II.
def parseArticleHeader1(tokens, i, parent):
    # print('parseArticleHeader1', tokens[i:i+4])

    i = skipSpaces(tokens, i)

    node = createNode(parent, {
        'type': 'header-1',
        'number': 0,
        'children': [],
    })

    # skip '{romanNumber}. - '
    if isRomanNumber(tokens[i]) and tokens[i + 1] == u'.':
        node['number'] = parseRomanNumber(tokens[i])
        i = skipToNextWord(tokens, i + 2)

    i = parseArticleEdit(tokens, i, node)
    i = parseForEach(parseArticleHeader2, tokens, i, node)

    if len(node['children']) == 0:
        removeNode(parent, node)

    # print('parseArticleHeader1 end', tokens[i:i+4])

    return i

# {number}°
# u'ex': 1°, 2°
def parseArticleHeader2(tokens, i, parent):
    # print('parseArticleHeader2', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'header-2',
        'number': 0,
        'children': [],
    })

    i = skipSpaces(tokens, i)
    if re.compile(u'\d+°').match(tokens[i]):
        node['number'] = parseInt(tokens[i])
        # skip {number}°
        i = skipToNextWord(tokens, i + 2)

    i = parseArticleEdit(tokens, i, node)
    i = parseForEach(parseArticleHeader3, tokens, i, node)

    if len(node['children']) == 0:
        removeNode(parent, node)

    # print('parseArticleHeader2 end', tokens[i:i+4])

    return i


# {number})
# u'ex': a), b), a (nouveau))
def parseArticleHeader3(tokens, i, parent):
    # print('parseArticleHeader3', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'header-3',
        'children': [],
    })

    i = skipSpaces(tokens, i)
    match = re.compile('([a-z]+)').match(tokens[i])
    if match and (tokens[i + 1] == u')' or (tokens[i + 2] == u'(' and tokens[i + 5] == u')')):
        node['number'] = ord(match.group()[0].encode('utf-8')) - ord('a') + 1
        # skip '{number}) ' or '{number} (nouveau))'
        if tokens[i + 1] == u')':
            i += 3
        else:
            i += 7
        # i = parseArticleEdit(tokens, i, node)

    i = parseArticleEdit(tokens, i, node)

    if len(node['children']) == 0:
        removeNode(parent, node)

    # print('parseArticleHeader3 end', tokens[i:i+4])

    return i


def parseForEach(fn, tokens, i, parent):
    test = fn(tokens, i, parent)

    while (test != i):
        i = test
        test = fn(tokens, i, parent)

    return i


def parseArticle(tokens, i, parent):
    # print('parseArticle', tokens[i:i+4])

    node = createNode(parent, {
        'type': 'article',
        'isNew': False,
        'children': [],
    })

    # read the article number and skip it
    node['articleNumber'] = parseInt(tokens[i])

    # Article {number}bis
    if re.compile('^.*bis$').match(tokens[i]):
        node['isBis'] = True
    elif re.compile('^.*quater$').match(tokens[i]):
        node['isQuater'] = True
    elif re.compile('^.*ter$').match(tokens[i]):
        node['isTer'] = True
    elif re.compile('^.*quinquies$').match(tokens[i]):
        node['isQuinquies'] = True

    i += 1

    node['isNew'] = False
    j = skipSpaces(tokens, i)
    if tokens[j] == '(' and tokens[j + 1] == KEYWORD_NEW_ARTICLE and tokens[j + 2] == u')':
        node['isNew'] = True
        i = j + 3

    i = skipSpaces(tokens, i)

    # (Supprimé)
    if tokens[i] == u'(' and tokens[i + 1] == u'Supprimé' and tokens[i + 2] == u')':
        node['isDeleted'] = True
        i = skipToEndOfLine(tokens, i)
        return i

    # {romanNumber}.
    i = parseForEach(parseArticleHeader1, tokens, i, node)

    # print('parseArticle end', tokens[i:i+4])

    return i


def parse(text):
    node = {'children': []}
    tokens = tokenize(text)
    current = node
    i = 0

    while (i < len(tokens)):
        # if the KEYWORD_ARTICLE keyword is at the beginning of a line
        if tokens[i - 1] == '\n' and tokens[i] == KEYWORD_ARTICLE:
            i += 2
            i = parseArticle(tokens, i, current)
        else:
            i += 1

    return node

def handleData(data):
    ast = parse(data)
    deleteParent(ast)

    json_data = json.dumps(ast, sort_keys=True, indent=2, ensure_ascii=False).encode('utf-8')

    sys.stdout.write(json_data)

def usage():
    return ('usage\n'
            '\tnode parse_texte_ast.py filename.txt\n'
            '\tcat filename.txt | node parse_texte_ast.py\n')

if not len(sys.argv) >= 2:
    data = sys.stdin.read()
    data = data.decode('utf-8')
    handleData(data)
else:
    data = codecs.open(sys.argv[1], 'r', 'utf-8').read()
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)
    handleData(data)
