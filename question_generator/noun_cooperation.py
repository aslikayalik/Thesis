from pyswip import Prolog
import spacy
from nltk import tokenize
import re

encoding = "ßutf-8"

prolog = Prolog()
prolog.consult("C:/Users/Public/Tez/sr_parser_4.pl")

nlp = spacy.load("tr_core_news_trf")

def check_allomorph_exists(token):
    with open('C:/Users/Public/Tez/noun_cooperation.pl', 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith(f"allomorph('{token}',"):
                return True
    return False

def get_analysis(token):
    print(token)
    results = list(prolog.query(f'parse({token},X,_)'))
    if results:
        return results[0]['X']
    else:
        return None  

def check_transition(state, token_first, token_lenght, token_last):
    if state == 'q00' and token_first == 'noun' and token_lenght == 1:
        return 'q11'
    elif state == 'q11' and token_first == 'noun' and token_lenght == 1:
        return 'q11'
    elif state == 'q11' and token_first == 'noun':
        if token_last in ['firstposs', 'secondposs', 'thirdposs','acc']:
            return 'q22'
    else:
        return 'q33'

def find_noun_cooperation(doc):
    results = []
    initial_state = 'q00'
    final_state = 'q22'
    current_state = initial_state
    analyzed_tokens = []
    combined_analysis = 'noun'
    sr_parser_sentence_list = []

    for token in doc:
        if(token.pos_ != "NOUN" or token.dep_ == "nsubj"):
            analyzed_tokens = []
            current_state = initial_state
            sr_parser_sentence_list.append(token)
            continue
        else:
            token_values = get_analysis(token) 
            next_state = check_transition(current_state, str(token_values[0]).strip(), len(token_values),str(token_values[-1]).strip())
            if next_state == 'q33':
                sr_parser_sentence_list.append(token)
                continue

            current_state = next_state
            analyzed_tokens.append(token)

            if current_state == final_state:
                noun_cooperation = '_'.join(token.text for token in analyzed_tokens)
                results.append((noun_cooperation, combined_analysis))
                sr_parser_sentence_list.append(noun_cooperation)

                if not check_allomorph_exists(noun_cooperation):
                    with open('noun_cooperation.pl', 'a', encoding='utf-8') as file:
                        file.write(f"allomorph('{noun_cooperation}', 'noun').\n")

                analyzed_tokens = []
                current_state = initial_state

    return sr_parser_sentence_list

def process_text(text):
    sentence = text.lower()
    sentence_list = tokenize.sent_tokenize(sentence)
    sentence_withoutPunct = [re.sub(r'[^\w\s]', '', sent) for sent in sentence_list]
    join_sentences = " ".join(sentence_withoutPunct)
    doc = nlp(join_sentences)
    noun_cooperation_list = find_noun_cooperation(doc)
    word_list = [token.text if hasattr(token, 'text') else token for token in noun_cooperation_list]
    results = list(prolog.query(f'sr_parse([],{word_list})'))
    return noun_cooperation_list, results

noun_cooperation_list, results = process_text("Ayşe kuş kafesi aldı.")
print("sr_parser_sentence_list:", noun_cooperation_list)
