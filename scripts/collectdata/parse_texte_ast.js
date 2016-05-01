#!/usr/bin/env node

const DELIMITERS = /(\s|\(|\)|\.|\!|’|,)/;
const KEYWORD_ARTICLE = 'Article';
const KEYWORD_NEW_ARTICLE = 'nouveau';
const KEYWORD_ARTICLE_REFERENCE = 'article';
const KEYWORD_PARTS = [
    'article', 'articles',
    'alinéa', 'alinéas',
    'phrase', 'phrases'
];
const KEYWORD_MONTH_NAMES = [
    'janvier',
    'février',
    'mars',
    'avril',
    'mai',
    'juin',
    'juillet',
    'août',
    'septembre',
    'octobre',
    'novembre',
    'décembre'
];
const KEYWORDS = [
    KEYWORD_ARTICLE,
    KEYWORD_NEW_ARTICLE,
    KEYWORD_ARTICLE_REFERENCE
];

function tokenize(text) {
    return text.split(DELIMITERS)
        // remove all spaces
        // .filter(function(s) { return !s.match(/\s/); })
        // remove empty strings
        .filter(function(s) { return s != ''; });
}

function skipTokens(tokens, i, f) {
    while (i < tokens.length && f(tokens[i])) {
        ++i;
    }

    return i;
}

function skipSpaces(tokens, i) {
    return skipTokens(tokens, i, function(t) { return t.match(/\s+/); });
}

function skipToNextWord(tokens, i) {
    return skipTokens(tokens, i, function(t) { return !t.match(/\w/); });
}

function skipToToken(tokens, i, token) {
    return skipTokens(tokens, i, function(t) { return t != token; });
}

function skipToEndOfLine(tokens, i) {
    return skipToToken(tokens, i, '\n');
}

function skipToQuoteStart(tokens, i) {
    return skipToToken(tokens, i, '«');
}

function isNumber(token) {
    return token.match(/\d+/);
}

function isSpace(token) {
    return !!token.match(/^\s+$/);
}

function isArticlePart(token) {
    return KEYWORD_PARTS.indexOf(token) >= 0;
}

function trimSpaces(s) {
    var m = s.match(/^\s*(.*[^\s])\s*$/);

    return m ? s.match(/^\s*(.*[^\s])\s*$/)[1] : s;
}

function parseRomanNumber(number) {
    if (number == 'I') {
        return 1;
    } else if (number == 'II') {
        return 2;
    } else if (number == 'III') {
        return 3;
    } else if (number == 'IV') {
        return 4;
    } else if (number == 'V') {
        return 5;
    } else if (number == 'VI') {
        return 6;
    } else if (number == 'VII') {
        return 7;
    } else if (number == 'VIII') {
        return 8;
    }

    return -1;
}

function isRomanNumber(token) {
    return parseRomanNumber(token) != -1;
}

function isNumberWord(word) {
    return wordToNumber(word) >= 0;
}

function wordToNumber(word) {
    var words = [
        ['un', 'une', 'premier', 'première'],
        ['deux', 'deuxième', 'second', 'seconde'],
        ['trois', 'troisième'],
        ['quatre', 'quatrième'],
        ['cinq', 'cinquième'],
        ['six', 'sixième'],
        ['sept', 'septième'],
        ['huit', 'huitième'],
        ['neuf', 'neuvième']
    ];

    for (var i = 0; i < words.length; ++i) {
        if (words[i].indexOf(word) >= 0)
            return i + 1;
    }

    return -1;
}

function monthToNumber(month) {
    return KEYWORD_MONTH_NAMES.indexOf(month) + 1;
}

function createNode(parent, node) {
    node.parent = parent;
    parent.children.push(node);

    return node;
}

function removeNode(parent, node) {
    parent.children.splice(parent.children.indexOf(node), 1);
}

function deleteParent(root) {
    delete root.parent;

    if (root.children) {
        for (var child of root.children) {
            deleteParent(child);
        }
    }
}

function parseLawReference(tokens, i, parent) {

    if (tokens[i].indexOf('loi') < 0) {
        return i;
    }

    var node = createNode(parent, {
        type: 'law-reference',
        lawId: '',
        children: []
    });

    // sip 'loi' and the following space
    i += 2;

    if (tokens[i] = 'organique') {

        i = skipToToken(tokens, i, 'n°') + 1;
        i = skipSpaces(tokens, i);

        node.lawType = 'organic';
        node.lawId = tokens[i];

        // skip {lawId} and the following space
        i += 2;
    }

    if (tokens[i] == 'du') {
        node.lawDate = tokens[i + 6] + '-' + monthToNumber(tokens[i + 4]) + '-' + tokens[i + 2];

        // skip {lawDate} and the following space
        i += 7;
    }

    return i;
}

// article {articleId} du code {codeName}, les mots :
// article {articleId} du code {codeName} est ainsi modifié :
function parseArticleReference(tokens, i, parent) {
    console.log('parseArticleReference', '\t\t', tokens.slice(i, i + 10).join(''));

    if (tokens[i].indexOf('article') < 0 && tokens[i] != 'L' && tokens[i + 1] != '.') {
        return i;
    }

    var node = createNode(parent, {
        type: 'article-reference',
        articleId: '',
        children: []
    });

    // skip "l’article" and the following space
    if (tokens[i].toLowerCase() == 'l' && tokens[i + 1] == '’' && tokens[i + 2] == 'article') {
        i += 4;
    }
    // skip "article" and the following space
    else if (tokens[i].indexOf('article') >= 0) {
        i += 2;
    }

    // article {articleId} de {lawReference}
    if (isNumber(tokens[i])) {
        node.articleId = parseInt(tokens[i]);

        if (tokens[i + 2] == 'de' && tokens[i + 6] == 'loi') {
            i = parseLawReference(tokens, i + 6, node);
        }
    }
    // article {articleId} du code {codeReference}
    else {
        for (; i < tokens.length && !tokens[i - 1].match(/\d+(-[\d+])*/); ++i) {
            node.articleId += tokens[i];
        }
        node.articleId = trimSpaces(node.articleId);

        i = skipSpaces(tokens, i);

        if (tokens[i] == 'du') {
            i = parseCodeReference(tokens, i + 2, node);
        }
    }

    return i;
}

function parseArticlePartReference(tokens, i, parent) {
    console.log('parseArticlePartReference', '\t\t', tokens.slice(i, i + 10).join(''));

    var node = createNode(parent, {
        type: 'article-part-reference',
        children: [],
        parent: parent
    });

    // après
    if (tokens[i].toLowerCase() == 'après') {
        node.partOffset = 'after';
        i += 2;
    }
    // la fin du {article}
    else if (tokens[i] == 'la' && tokens[i + 2] == 'fin') {
        node.partOffset = 'end';
        i += 4;
    }
    // à la fin du {article}
    else if (tokens[i].toLowerCase() == 'à' && tokens[i + 2] == 'la' && tokens[i + 4] == 'fin') {
        node.partOffset = 'end';
        i += 6;
    }

    // de la {partNumber} {partType}
    if (tokens[i].toLowerCase() == 'de' && tokens[i + 2] == 'la' && isNumberWord(tokens[i + 4])) {

        i += 4;

        if (tokens[i + 2] == 'phrase') {
            node.partType == 'sentence';
            node.partNumber = wordToNumber(tokens[i]);

            i = parseArticlePartReference(tokens, i + 4, node);
        }
    }
    // le {partNumber} {partType}
    // du {partNumber} {partType}
    // un {partNumber} {partType}
    // au {partNumber} {partType}
    // la {partNumber} {partType}
    else if (['le', 'du', 'un', 'au', 'la'].indexOf(tokens[i].toLowerCase()) >= 0 && isNumberWord(tokens[i + 2])) {
        node.partNumber = wordToNumber(tokens[i + 2]);

        if (tokens[i + 4] == 'alinéa') {
            node.partType = 'alinea';
        }
        else if (tokens[i + 4] == 'phrase') {
            node.partType = 'sentence';
        }

        i = parseArticlePartReference(tokens, i + 6, node);
    }
    // le {partNumber}°
    // du {partNumber}°
    // un {partNumber}°
    // au {partNumber}°
    else if (['le', 'du', 'un', 'au'].indexOf(tokens[i].toLowerCase()) >= 0 && !!tokens[i + 2].match(/\d+°/)) {
        node.partType = 'header-2';
        node.partNumber = parseInt(tokens[i + 2]);

        i += 4;

        if (tokens[i] == 'bis') {
            node.isBis = true;
            i += 2;
        }
        else if (tokens[i] == 'ter') {
            node.isTer = true;
            i += 2;
        }

        i = parseArticlePartReference(tokens, i, node);

        // ainsi rédigé
        if (tokens[i + 2] == 'rédigé') {
            i = skipToQuoteStart(tokens, i + 2);
            i = parseForEach(parseQuote, tokens, i, node);
        }
    }
    // le {romanPartNumber}
    // du {romanPartNumber}
    else if (['le', 'du', 'un'].indexOf(tokens[i].toLowerCase()) >= 0 && isRomanNumber(tokens[i + 2])) {
        node.partType = 'header-1';
        node.partNumber = parseRomanNumber(tokens[i + 2]);

        // find 'article'
        i = skipTokens(tokens, i, function(t) { return t.indexOf('article') < 0 });
        i = parseArticleReference(tokens, i, node);
    }
    // l'{partType} {partNumber}
    else if (tokens[i].toLowerCase() == 'l' && tokens[i + 1] == '’') {
        if (tokens[i + 2] == 'article') {
            i = parseArticleReference(tokens, i + 2, node);
        }
        else {
            i = parseArticlePartReference(tokens, i + 2, node);
        }
    }
    // de l'{partType} {partNumber}
    else if (tokens[i].toLowerCase() == 'de' && tokens[i + 2] == 'l' && tokens[i + 3] == '’') {
        if (tokens[i + 4] == 'article') {
            i = parseArticleReference(tokens, i + 4, node);
        }
        else {
            i = parseArticlePartReference(tokens, i + 4, node);
        }
    }
    // des {partType}
    // les {partType}
    else if (['des', 'les'].indexOf(tokens[i].toLowerCase()) >= 0) {
        // les mots
        if (tokens[i + 2] == 'mots') {
            node.partType = 'sentence';

            i = skipToQuoteStart(tokens, i);
            i = parseForEach(parseQuote, tokens, i, parent);
            i = skipSpaces(tokens, i);
        }
        else {
            i = parseArticleReference(tokens, i + 2, parent);
            i = skipSpaces(tokens, i);

            if (tokens[i] == 'et') {
                return parseArticleReference(tokens, i + 2, parent);
            }
        }
    }
    // {number} {partType}
    else if (isNumberWord(tokens[i].toLowerCase()) && isArticlePart(tokens[i + 2])) {
        if (tokens[i + 2].indexOf('alinéa') >= 0) {
            node.partType = 'alinea';
            i += 4;
        }
        else if (tokens[i + 2].indexOf('phrase') >= 0) {
            node.partType = 'sentence';
            i += 4;
        }
        else if (tokens[i + 2].indexOf('article') >= 0) {
            i = parseArticleReference(tokens, i + 2, node);
            console.log('foo', tokens.slice(i, i + 10).join(''));
        }

        // ainsi rédigé(e)
        if (tokens[i + 2].indexOf('rédigé') >= 0) {
            i = skipToQuoteStart(tokens, i + 2);
            i = parseForEach(parseQuote, tokens, i, node);
        }
    }
    // le même
    else if (['le'].indexOf(tokens[i].toLowerCase()) >= 0 && tokens[i + 2] == 'même') {
        // "le même {number} {part}" or "le même {part}"
        if (tokens[i + 4] == 'alinéa' || tokens[i + 6] == 'alinéa') {
            var alineas = searchNode(getRoot(parent), function(n) {
                return n.type == 'article-part-reference' && n.partType == 'alinea'
            });

            // the last one in order of traversal is the previous one in order of syntax
            node.children.push(alineas[alineas.length - 1]);

            node.partType = 'alinea';

            i += tokens[i + 4] == 'alinéa' ? 6 : 8;
        }
    }
    else {
        removeNode(parent, node);
    }

    return i;
}

function getRoot(node) {
    while (node.parent != null) {
        node = node.parent;
    }

    return node;
}

function searchNode(root, fn, results) {
    if (!results) {
        results = [];
    }

    if (fn(root)) {
        results.push(root);
    }

    if (root.children) {
        for (var child of root.children) {
            searchNode(child, fn, results);
        }
    }

    return results;
}

function parseQuote(tokens, i, parent) {
    if (tokens[i] != '«') {
        return i;
    }

    var node = createNode(parent, {
        type: 'quote',
        words: ''
    });

    // skip the '«'
    ++i;

    while (i < tokens.length && tokens[i] != '»' && tokens[i] != '\n') {
        node.words += tokens[i];
        ++i;
    }
    // node.words = node.words.replace(/«\s/g, '');
    node.words = trimSpaces(node.words);

    // skip '»'
    ++i;
    i = skipSpaces(tokens, i);

    return i;
}

function parseArticleEdit(tokens, i, parent) {
    console.log('parseArticleEdit', '\t\t', tokens.slice(i, i + 10).join(''));

    var node = createNode(parent, {
        type: 'article-edit',
        children: []
    });

    i = parseForEach(parseReference, tokens, i, node);
    // i = parseReference(tokens, i, node);
    i = skipToNextWord(tokens, i, node);

    // sont supprimés
    // est supprimé
    if (tokens[i + 2].indexOf('supprimé') >= 0) {
        node.editType = 'delete';

        i = skipToEndOfLine(tokens, i);
    }
    // est ainsi modifié
    else if (tokens[i + 4] == 'modifié') {
        node.editType = 'edit';

        i = skipToEndOfLine(tokens, i);
    }
    // est remplacé par
    // sont remplacés par
    else if (tokens[i + 2].indexOf('remplacé') >= 0) {
        node.editType = 'edit';

        // skip "est remplacé par" or "sont remplacé par"
        i += 6;

        i = parseReference(tokens, i, node);
    }
    // il est inséré
    // il est ajouté
    else if (tokens[i + 4] == 'inséré' || tokens[i + 4] == 'ajouté') {
        node.editType = 'add';

        i = parseReference(tokens, i + 6, node);
        i = skipToEndOfLine(tokens, i);
    }
    // est complété par
    else if (tokens[i + 2] == 'complété') {
        node.editType = 'add';

        i = parseReference(tokens, i + 6, node);
        i = skipToEndOfLine(tokens, i);
    }
    // est abrogé
    else if (tokens[i + 2] == 'abrogé') {
        node.editType = 'delete';

        i = skipToEndOfLine(tokens, i);
    }
    else if (parent.isNewArticle && parent.children.length == 0) {
        node.editType = 'add';

        i = parseNewArticleContent(tokens, i, node);
    }
    else {
        console.log('cannot understand edit', '\t\t', tokens.slice(i, i + 10).join(''));

        removeNode(parent, node);
    }

    return i;
}

function parseNewArticleContent(tokens, i, parent) {
    var node = createNode(parent, {
        type: 'article-content',
        articleContent: ''
    });

    while (i < tokens.length && tokens[i] != '\n') {
        node.articleContent += tokens[i];
        ++i;
    }

    if (node.articleContent == '' || isSpace(node.articleContent)) {
        removeNode(parent, node);
    }

    return i;
}

function parseCodeReference(tokens, i, parent) {
    var node = createNode(parent, {
        type: 'code-reference',
        codeName: ''
    });

    if (tokens[i] != 'code') {
        return i;
    }

    for (; i < tokens.length && tokens[i] != ',' && tokens[i] != 'est'; ++i) {
        node.codeName += tokens[i];
    }
    node.codeName = trimSpaces(node.codeName);

    if (node.codeName == '' || isSpace(node.codeName)) {
        removeNode(parent, node);
    }

    return i;
}

function parseReference(tokens, i, parent) {
    console.log('parseReference', tokens.slice(i, i + 5).join(''));
    // i = skipSpaces(tokens, i);
    i = skipToNextWord(tokens, i);

    // L’article L. 260 du code électoral
    if (tokens[i].toLowerCase() == 'l' && tokens[i + 1] == '’' && tokens[i + 2] == 'article') {
        i = parseArticleReference(tokens, i, parent);
    }
    else if (tokens[i].toLowerCase() == 'le' && tokens[i + 2] == 'code') {
        i = parseCodeReference(tokens, i + 2, parent);
    }
    else {
        i = parseArticlePartReference(tokens, i, parent);
    }

    return i;
}

// {romanNumber}.
// ex: I., II.
function parseArticleHeader1(tokens, i, parent) {
    console.log('parseArticleHeader1');

    i = skipSpaces(tokens, i);

    var node = createNode(parent, {
        type: 'header-1',
        number: 0,
        children: []
    });

    // skip '{romanNumber}. - '
    if (isRomanNumber(tokens[i]) && tokens[i + 1] == '.') {
        node.number = parseRomanNumber(tokens[i]);

        i = skipToNextWord(tokens, i + 2);
    }

    i = parseArticleEdit(tokens, i, node);
    i = parseForEach(parseArticleHeader2, tokens, i, node);

    if (node.children.length == 0) {
        removeNode(parent, node);
    }

    return i;
}

// {number}°
// ex: 1°, 2°
function parseArticleHeader2(tokens, i, parent) {
    console.log('parseArticleHeader2', '\t\t', tokens.slice(i, i + 10).join(''));

    var node = createNode(parent, {
        type: 'header-2',
        number: 0,
        children: []
    });

    i = skipSpaces(tokens, i);
    if (!!tokens[i].match(/\d+°/)) {
        node.number = parseInt(tokens[i]);

        // skip {number}°
        i = skipToNextWord(tokens, i + 2);
    }

    i = parseArticleEdit(tokens, i, node);
    i = parseForEach(parseArticleHeader3, tokens, i, node);

    if (node.children.length == 0) {
        removeNode(parent, node);
    }

    return i;
}

// {number})
// ex: a), b), a (nouveau))
function parseArticleHeader3(tokens, i, parent) {
    console.log('parseArticleHeader3', '\t\t', tokens.slice(i, i + 10).join(''));

    var node = createNode(parent, {
        type: 'header-3',
        number: 0,
        children: []
    });

    i = skipSpaces(tokens, i);
    var match = tokens[i].match(/([a-z]+)/);
    if (!!match && (tokens[i + 1] == ')' || (tokens[i + 2] == '(' && tokens[i + 5] == ')'))) {
        node.number = match[1].charCodeAt(0) - 'a'.charCodeAt(0);

        // skip '{number}) ' or '{number} (nouveau))'
        i += tokens[i + 1] == ')' ? 3 : 7;
        i = parseArticleEdit(tokens, i, node);
    }

    i = parseArticleEdit(tokens, i, node);

    if (node.children.length == 0) {
        removeNode(parent, node);
    }

    return i;
}

function parseForEach(fn, tokens, i, parent) {
    var test = fn(tokens, i, parent);

    while (test != i) {
        i = test;
        test = fn(tokens, i, parent);
    }

    return i;
}

function parseArticle(tokens, i, parent) {
    var node = createNode(parent, {
        type: 'article',
        children: []
    });

    i = skipSpaces(tokens, ++i);
    // read the article number and skip it
    node.articleNumber = parseInt(tokens[i]);

    // Article {number}bis
    if (!!tokens[i].match(/^.*bis$/)) {
        node.isBis = true;
    }
    else if (!!tokens[i].match(/^.*quater$/)) {
        node.isQuater = true;
    }
    else if (!!tokens[i].match(/^.*ter$/)) {
        node.isTer = true;
    }
    else if (!!tokens[i].match(/^.*quinquies$/)) {
        node.isQuinquies = true;
    }

    i++;

    node.isNewArticle = false;
    var j = skipSpaces(tokens, i);
    if (tokens[j] == '(' && tokens[j + 1] == KEYWORD_NEW_ARTICLE && tokens[j + 2] == ')') {
        node.isNewArticle = true;
        i = j + 3;
    }

    console.log('article', node.articleNumber, ', new:', node.isNewArticle);

    i = skipSpaces(tokens, i);

    // (Supprimé)
    if (tokens[i] == '(' && tokens[i + 1] == 'Supprimé' && tokens[i + 2] == ')') {

        node.isDeleted = true;

        i = skipToEndOfLine(tokens, i);

        return i;
    }

    // {romanNumber}.
    i = parseForEach(parseArticleHeader1, tokens, i, node);

    return i;
}

function parse(text) {
    var node = {children: []};
    var tokens = tokenize(text);
    var current = node;
    var i = 0;

    while (i < tokens.length) {
        // if the KEYWORD_ARTICLE keyword is at the beginning of a line
        if (tokens[i - 1] == '\n' && tokens[i] == KEYWORD_ARTICLE) {
            i = parseArticle(tokens, ++i, current);
        }
        else {
            ++i;
        }
    }

    return node;
}

function handleData(data) {
    console.log(data);
    var ast = parse(data);
    deleteParent(ast);

    process.stdout.write(JSON.stringify(ast, null, 2));
}


console.log = function() {};

function usage() {
    return 'usage\n'
        + '\tnode parse_texte_ast.js filename.txt\n'
        + '\tcat filename.txt | node parse_texte_ast.js\n';
}

if (!process.argv[2]) {
    if (process.stdin.isTTY) {
        console.error(usage());
        process.exit(1);
    }

    var data = '';
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', function(chunk) {
        data += chunk;
    });
    process.stdin.on('end', function() {
        if (!!data) {
            handleData(data);
        }
    });
}
else {
    var fs = require('fs');

    fs.readFile(process.argv[2], 'utf8', function (err, data) {
        if (err) {
            return console.log(err);
        }

        handleData(data);
    });
}
