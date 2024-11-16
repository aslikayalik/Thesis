from pyswip import Prolog
import spacy
from nltk import tokenize
import re
import xml.etree.ElementTree as ET


encoding = "utf-8"

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
    try:
        results = list(prolog.query(f'parse({token},X,_)'))
        if results:
            return results[0]['X']
        else:
            return None
    except Exception as e:
        print(f"Error analyzing token '{token}': {e}")
        return None

def check_transition(state, token_first, token_length, token_last):
    if state == 'q00' and token_first == 'noun' and token_length == 1:
        return 'q11'
    elif state == 'q11' and token_first == 'noun' and token_length == 1:
        return 'q11'
    elif state == 'q11' and token_first == 'noun':
        if token_last in ['firstposs', 'secondposs', 'thirdposs', 'acc']:
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
        if token.pos_ != "NOUN" or token.dep_ == "nsubj":
            analyzed_tokens = []
            current_state = initial_state
            sr_parser_sentence_list.append(token.text) 
            continue
        else:
            token_values = get_analysis(token)
            if not token_values:
                continue
            next_state = check_transition(current_state, str(token_values[0]).strip(), len(token_values), str(token_values[-1]).strip())
            if next_state == 'q33':
                sr_parser_sentence_list.append(token.text)  
                continue

            current_state = next_state
            analyzed_tokens.append(token)

            if current_state == final_state:
                noun_cooperation = '_'.join(token.text for token in analyzed_tokens)
                results.append((noun_cooperation, combined_analysis))
                print(results)
                sr_parser_sentence_list.append(noun_cooperation)  

                if not check_allomorph_exists(noun_cooperation):
                    with open('noun_cooperation.pl', 'a', encoding='utf-8') as file:
                        file.write(f"allomorph('{noun_cooperation}', noun).\n")

                analyzed_tokens = []
                current_state = initial_state

    return sr_parser_sentence_list

def process_text(text):
    sentence = text.lower()
    sentence_list = tokenize.sent_tokenize(sentence)
    sentence_withoutPunct = [re.sub(r'[^\w\s]', '', sent) for sent in sentence_list]
    join_sentences = " ".join(sentence_withoutPunct)
    doc = nlp(join_sentences)
    noun_cooperation = find_noun_cooperation(doc) 
    word_list = [token for token in noun_cooperation]
    print("kelime listesi:", word_list)
    
    return noun_cooperation, word_list

noun_cooperation, word_list = process_text("Ayşe kuş kafesi aldı.")

split_words = noun_cooperation[1].split('_', 1)
first_word = split_words[0]
last_words = split_words[1] if len(split_words) > 1 else None

def parse_wordnet(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return root

def get_synonyms_antonyms_hypernyms_hyponyms(root, word, max_results=10):
    synonyms = set()
    antonyms = set()
    hypernyms = set()
    hyponyms = set()

    for synset in root.findall('SYNSET'):
        pos = synset.find('POS').text
        if pos not in ['n', 'adj']:
            continue

        literals = synset.findall('.//LITERAL')
        for literal in literals:
            if word in literal.text:
                for sibling in literals:
                    if sibling.text != word:
                        synonyms.add(sibling.text)
                        if len(synonyms) >= max_results:
                            break

                for sr in synset.findall('.//SR'):
                    sr_type = sr.find('TYPE').text
                    target_id = sr.text
                    target_synset = root.find(f".//SYNSET[ID='{target_id}']")
                    if target_synset:
                        target_pos = target_synset.find('POS').text
                        if target_pos in ['n', 'adj']:
                            for target_literal in target_synset.findall('.//LITERAL'):
                                if sr_type == 'ANTONYM':
                                    antonyms.add(target_literal.text)
                                    if len(antonyms) >= max_results:
                                        break
                                elif sr_type == 'HYPERNYM':
                                    hypernyms.add(target_literal.text)
                                    if len(hypernyms) >= max_results:
                                        break
                                elif sr_type == 'HYPONYM':
                                    hyponyms.add(target_literal.text)
                                    if len(hyponyms) >= max_results:
                                        break
                break

    return list(synonyms), list(antonyms), list(hypernyms), list(hyponyms)

def categorize_words(word_list):
    tek_kelimeleler = []
    iki_kelimeleler = []
    for word in word_list:
        if ' ' in word:
            iki_kelimeleler.append(word)
        else:
            tek_kelimeleler.append(word)
    return tek_kelimeleler, iki_kelimeleler


xml_file = 'C:\\Users\\Public\\Tez\\TurkishWordNet-Py\\WordNet\\data\\turkish_wordnet.xml'
root = parse_wordnet(xml_file)

# Eş anlamlı, zıt anlamlı, alt kavramlar ve üst kavramlar
word = 'kuş'
synonyms, antonyms, hypernyms, hyponyms = get_synonyms_antonyms_hypernyms_hyponyms(root, word)

print("**********************************")
print(f"Eş anlamlılar: {', '.join(synonyms)}")
print("**********************************")
print(f"Zıt anlamlılar: {', '.join(antonyms)}")
print("**********************************")
print(f"Üst kavramlar: {', '.join(hypernyms)}")
print("**********************************")
print(f"Alt kavramlar: {', '.join(hyponyms)}")
print("**********************************")


all_words = synonyms + antonyms + hypernyms + hyponyms


tek_kelimeler, birden_fazla_kelime_icerenler = categorize_words(all_words)


words_for_noun_cooperation = []

for word in tek_kelimeler:
    analysis = get_analysis(word)
    if analysis:
        if len(analysis) == 1:
            words_for_noun_cooperation.append(word)
        print(f"{word}: {analysis}")
    else:
        print(f"{word}: Analysis not found")

print("**********************************")
print(f"Ek almayan kelimeler: {', '.join(words_for_noun_cooperation)}")
print("**********************************")

def find_underscored_words(noun_cooperation):
    return [word for word in noun_cooperation if '_' in word]

combined_word_list = []

def return_words_for_noun_cooperation(words_for_noun_cooperation):
    for word in words_for_noun_cooperation:
        first_word = word
        combined_word = f"{first_word}_{last_words}"
        combined_word_list.append(combined_word)
    return combined_word_list

print("**********************************")
print("Noun cooperation listesi:")
noun_cooperation_list = return_words_for_noun_cooperation(words_for_noun_cooperation)
print(noun_cooperation_list)

print("**********************************")
print("**********************************")
print("İsimler :", noun_cooperation)
print("Kelime listesi:", word_list)
print("Sorular :")

def noun_cooperation_qg(noun_cooperation_list, word_list):
    underscored_words = find_underscored_words(word_list)
    if not underscored_words:
        print("Altı çizili kelime bulunamadı.")
        return []

    alti_cizili_kelime = underscored_words[0]  

    modified_word_lists = []
    for noun_cooperation in noun_cooperation_list:
        modified_word_list = [noun_cooperation if w == alti_cizili_kelime else w for w in word_list]
        modified_word_lists.append(modified_word_list)
    
    return modified_word_lists


modified_word_lists = noun_cooperation_qg(noun_cooperation_list, word_list)


def add_to_noun_cooperation(modified_word_lists):
    with open('C:/Users/Public/Tez/noun_cooperation.pl', 'a', encoding='utf-8') as file:
        for word_list in modified_word_lists:
            for word in word_list:
                if '_' in word:
                    file.write(f"allomorph('{word}', noun).\n")


add_to_noun_cooperation(modified_word_lists)


def qg(modified_word_lists_elemanı):
    prolog_format = "[" + ",".join(f"'{item}'" for item in modified_word_lists_elemanı) + "]"
    print("eleman", prolog_format)
    results = list(prolog.query(f'sr_parse([], {prolog_format})'))
    print(f"Query results: {results}")
    return results


for i in modified_word_lists:
    print(qg(i))


