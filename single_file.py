tool_dir = 'tools'

import spacy.en
from spacy.en.attrs import IS_ALPHA, IS_UPPER, IS_PUNCT, LIKE_URL, LIKE_NUM
import gzip
import sys
import os
from nltk.corpus import wordnet as wn
sys.path.append(tool_dir + '/inflection-0.3.1')
sys.path.append(tool_dir)
import inflection
import ner
import en
from nltk.corpus import wordnet as wn
from difflib import get_close_matches as gcm
import urllib
import urllib2
import json
from variativity import variativity_replacement
from utilities import get_index_in_list
from possessive_self import get_subject_properties



#setting default encoding to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

def preprocess_verb_conjugator_lexicon(conjugated_verbs):
	conjugated_verbs_file = open(tool_dir + '/en/verb/verb.txt', 'r')
	for line in conjugated_verbs_file:
		conjugated_verbs.add(line.split(',')[0])

def word_exists_in_wiktionary(word):
	url = 'https://en.wiktionary.org/w/api.php?action=query&titles=' + word + '&format=json'
	if 'missing' in json.load(urllib.urlopen(url)):
		return False
	else:
		return True

#compare the frequencies of the given lemma as a verb versus as a noun in the BNC. Returns true if the noun occurrence is not more than 4 times as frequent as the verb occurrence
def compare_lemma_verb_noun_frequencies(lemma, catvar_noun_dict, bnc_noun_frequencies, bnc_verb_frequencies):
	noun_frequency = 0.
	verb_frequency = 0.
	if lemma in bnc_noun_frequencies:
		noun_frequency = bnc_noun_frequencies[lemma]
	
	list_of_verbs = list(catvar_noun_dict[lemma])
	for verb in list_of_verbs:
		if verb in bnc_verb_frequencies:
			verb_frequency += bnc_verb_frequencies[verb]

	if noun_frequency != 0 and noun_frequency <= 2 * verb_frequency:
		return True
	else:
		return False

#loading the BNC noun and verb frequencies (for lemma) in two dictionaries
def load_bnc_frequencies(bnc_noun_frequencies, bnc_noun_frequencies_file, bnc_verb_frequencies, bnc_verb_frequencies_file):
	for line in bnc_noun_frequencies_file:
		toks = line.split()
		if len(toks) == 2:
			bnc_noun_frequencies[toks[0]] = int(toks[1])
			
	for line in bnc_verb_frequencies_file:
		toks = line.split()
		if len(toks) == 2:
			bnc_verb_frequencies[toks[0]] = int(toks[1])

#check if there is a catvar cluster containing the given noun lemma that also contains a verb
def noun_to_verb_in_catvar(catvar_file, lemma, catvar_noun_dict, catvar_no_verb_set):
	if lemma in catvar_no_verb_set:
		return False
	if lemma in catvar_noun_dict:
		return True
	
	catvar_file.seek(0, 0)
	string_to_search = lemma + u'_N%'
	verb_marker = u'_V%'
	at_least_one_match = False
	list_of_verbs = []
	for line in catvar_file:
		if line.find(string_to_search) == 0 or u'#' + string_to_search in line:
			if verb_marker in line:
				cluster_entries = line.split(u'#')
				for entry in cluster_entries:
					if verb_marker in entry:
						at_least_one_match = True
						list_of_verbs.append(entry.split(u'_')[0])
	
	if at_least_one_match:
		catvar_noun_dict[lemma] = list()
		for verb in list_of_verbs:
			catvar_noun_dict[lemma].append(verb)
	else:
		catvar_no_verb_set.add(lemma)
						
	return at_least_one_match

#this is a dictionary for fast lookup of catvar entries
catvar_noun_dict = dict()

#and this a set of entries with no verb, for quick lookup
catvar_no_verb_set = set()

#a list of the verbs we can conjugate
conjugated_verbs = set()

#nlp pipeline (tagger and parser)
nlp_pipeline = spacy.en.English()

#enlist the verbs we can conjugate. everything else, well, sorry
preprocess_verb_conjugator_lexicon(conjugated_verbs)

#verb - prep pairs within 3 tokens- output file
verb_prep_file = open('verb_prep_combinations', 'w')
verb_prep_file_noun_attach = open('verb_prep_combinations_noun_attachment', 'w')

#list of common prepositions
common_prepositions = ['of', 'in', 'to', 'for', 'with', 'on', 'from']

#list of allowed verbs
allowed_verbs = ['make', 'take', 'give', 'have', 'hold', 'do', 'commit', 'pay', 'provide', 'offer', 'draw', 'show', 'reach', 'get', 'lay']

#for the most common unambiguous pronouns
possessive_dictionary = {'he' : 'his', 'i' : 'my', 'it' : 'its', 'she' : 'her', 'you' : 'your', 'we' : 'our', 'article' : 'its', 'this' : 'its'}

#exhaustive adjective to adverb mapping
adjective_adverb_dict = dict()

#and a list of adjectives I can't find an adverb for
no_adverb_set = set()

#open catvar file
catvar_file = open(tool_dir + "/catvar/catvar21.signed", "r")

#verb-prep combination dict
verb_prep_combination_dict = dict()

#counter
counter = 0

#ner tagger
ner_tagger = ner.SocketNER(host='localhost', port=8080)

#load BNC noun and verb lemma frequencies in dictionaries
bnc_noun_frequencies = dict()
bnc_verb_frequencies = dict()
bnc_noun_frequencies_file = open(tool_dir + "/lists/bnc_noun_list", "r")
bnc_verb_frequencies_file = open(tool_dir + "/lists/bnc_verb_list", "r")
load_bnc_frequencies(bnc_noun_frequencies, bnc_noun_frequencies_file, bnc_verb_frequencies, bnc_verb_frequencies_file)
bnc_noun_frequencies_file.close()
bnc_verb_frequencies_file.close()

#open wikipedia dump
with gzip.open(sys.argv[1], 'r') as fin:
	#storing stuff during processing a sentence
	sentence = ""
	candidate_object_token_numbers = []
	
	#read gzipped corpus line by line
	for line in fin:
		#an empty line means the running sentence has ended, which is when we generate everything we need
		if (line.strip() == ""):
			counter += 1
			if counter % 1000 == 0:
				sys.stderr.write(str(counter) + '\n')
			if counter == 200000:
				break		
			#reconstruct original sentence to be parsed by spacy
			sentence = sentence.strip()

			#parsing the sentence
			parsed_tokens = nlp_pipeline(sentence)
			
			#add all probable direct object candidates to a list
			for index in range(len(parsed_tokens)):
				#if there's a direct object, to start with 
				if (parsed_tokens[index].dep_.strip() == "dobj"):
					#if the verb belongs to the list of allowed verbs
					if parsed_tokens[index].head.lemma_ in allowed_verbs:	
						#if the object's head verb is not more than 6 tokens behind the direct object
						poss_head_index = get_index_in_list(parsed_tokens, parsed_tokens[index].head)	
						if poss_head_index < index and index - poss_head_index < 7:	
							#if the object is not a punctuation mark or number-like or url-like
							if not(parsed_tokens[index].check_flag(IS_PUNCT) or parsed_tokens[index].check_flag(LIKE_URL) or parsed_tokens[index].check_flag(LIKE_NUM)):
								#if the noun has a verb in the same cluster from catvar
								if noun_to_verb_in_catvar(catvar_file, parsed_tokens[index].lemma_.lower(), catvar_noun_dict, catvar_no_verb_set):
									#check if the verb has a conjugation in our verb conjugator
									if [verb for verb in catvar_noun_dict[parsed_tokens[index].lemma_.lower()] if verb in conjugated_verbs]:		
										#check whether the nominal form of this noun appears much more frequently compared to that of the verbal form in the BNC
										if compare_lemma_verb_noun_frequencies(parsed_tokens[index].lemma_.lower(), catvar_noun_dict, bnc_noun_frequencies, bnc_verb_frequencies):
											#add this token to the list of possible light verb objects for this sentence: there may be multiple
											candidate_object_token_numbers.append(index)
			
			#now consider each candidate, construct verb phrase, noun phrase, lvc phrase
			for object_index in candidate_object_token_numbers:
				#some initializations
				object_token = parsed_tokens[object_index]
				object_headword = object_token.orth_
				
				verb_token = object_token.head
				verb_index = get_index_in_list(parsed_tokens, verb_token)
				verb_headword = verb_token.orth_
				
				list_of_subjects = [subject_token for subject_token in parsed_tokens if subject_token.dep_ == "nsubj" and subject_token.head is verb_token]
				if len(list_of_subjects) != 1:
					continue
				
				subject_token = list_of_subjects[0]
				subject_index = get_index_in_list(parsed_tokens, subject_token)
				subject_headword = subject_token.orth_
				
				lvc_phrase = parsed_tokens[verb_index].orth_
				verb_phrase = parsed_tokens[verb_index].orth_
				noun_phrase = u''
				
				#create verb phrase, noun phrase, lvc phrase
				for index in range(verb_index + 1, object_index + 2):
					if not (parsed_tokens[index]):
						continue
					#to accommodate for the particle occurring beyond the noun phrase
					if (index == object_index + 1):
						if parsed_tokens[index].dep_.strip() == u'prt' and get_index_in_list(parsed_tokens, parsed_tokens[index].head) == verb_index:
							verb_phrase += u' ' + parsed_tokens[index].orth_
							lvc_phrase += u' ' + parsed_tokens[index].orth_
					#adding only compound noun modifiers to the noun phrase, discarding 'amod'
					else:
						lvc_phrase += u' ' + parsed_tokens[index].orth_
						if parsed_tokens[index].dep_.strip() == u'prt' and get_index_in_list(parsed_tokens, parsed_tokens[index].head) == verb_index:
							verb_phrase += u' ' + parsed_tokens[index].orth_
						if parsed_tokens[index].dep_.strip() == u'compound' and get_index_in_list(parsed_tokens, parsed_tokens[index].head) == object_index:
							noun_phrase += parsed_tokens[index].orth_ + u' '
				noun_phrase += parsed_tokens[object_index].orth_
				
				
				#at this point we're ready to do all the shit
				#but first, some filters!
				
				#if there's a comma or parentheses in the LVC phrase, skip
				if u',' in lvc_phrase or u'(' in lvc_phrase or u')' in lvc_phrase:
					continue
				#if the verb is preceded or the noun is followed by a hyphen, skip
				phrase_index = sentence.find(lvc_phrase)
				if phrase_index >= 2 and sentence[phrase_index - 2] == u'-':
					continue
				if phrase_index + 2 < len(sentence) and sentence[phrase_index + 2] == u'-':
					continue
				#if lvc_phrase not in tokenized sentence, leave it
				if lvc_phrase not in sentence:
					continue			
				
				#possessive
				subject_properties = get_subject_properties(parsed_tokens, verb_token, object_token, ner_tagger, sentence)
				if subject_properties:
					replacement_phrase = verb_phrase + ' ' + subject_properties[2] + ' ' + noun_phrase
					print sentence.replace(lvc_phrase, replacement_phrase)
				
				#variativity
				list_of_related_verbs = catvar_noun_dict[object_token.lemma_.lower()]
				verb = list_of_related_verbs[0]
				if verb not in conjugated_verbs or verb != en.verb.present(verb) or not subject_properties:
					continue
				replaced_strings = variativity_replacement(sentence, verb_token, object_token, object_index, verb_index, parsed_tokens, verb, lvc_phrase, catvar_file, adjective_adverb_dict, no_adverb_set, subject_properties[0], subject_properties[1])
				if replaced_strings:
					for replaced_string in replaced_strings:
						print replaced_string
				print sentence
				print '-------------------'
			
			#empty all buffers and continue to the next sentence
			sentence = u''
			candidate_object_token_numbers[:] = []
			
		else: #not the end of the sentence yet, keep going
			sentence += unicode(line.split()[1], "utf-8") + u' '

catvar_file.close()


for combination in verb_prep_combination_dict:
	verb_prep_file.write(combination + '\n\n' + verb_prep_combination_dict[combination] + '--------------------------\n\n')
verb_prep_file.close()
