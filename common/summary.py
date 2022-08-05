
from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer as Summarizer
from sumy.nlp.stemmers import Stemmer


LANGUAGE = "russian"
SENTENCES_COUNT = 5

def summarize_sumy(string: str):
    parser = PlaintextParser.from_string(string, Tokenizer(LANGUAGE))
    stemmer = Stemmer(LANGUAGE)

    summarizer = Summarizer(stemmer)
    
    summ = ''
    for sentence in summarizer(parser.document, SENTENCES_COUNT):
        summ += sentence.__str__()
    return summ