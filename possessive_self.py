tool_dir = 'tools'

import spacy.en
import sys
from nltk.corpus import wordnet as wn	
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append(tool_dir + '/inflection-0.3.1')
sys.path.append(tool_dir)
import inflection
import en
import ner

#globals for the most common unambiguous pronouns
possessive_dictionary = {'he' : 'his', 'i' : 'my', 'it' : 'its', 'she' : 'her', 'you' : 'your', 'we' : 'our', 'article' : 'its', 'this' : 'its', 'these' : 'their', 'those' : 'their'}
person_dictionary = {'he' : 3, 'i' : 1, 'it' : 3, 'she' : 3, 'you' : 2, 'we' : 1, 'article' : 3, 'this' : 3, 'these' : 3, 'those' : 3}
number_dictionary = {'he' : 1, 'i' : 1, 'it' : 1, 'she' : 1, 'you' : 2, 'we' : 2, 'article' : 1, 'this' : 1, 'these' : 2, 'those' : 2}

possessive_dictionary_singular = {'who' : 'his/her', 'which' : 'its', 'what' : 'its', 'whom' : 'his/her'}

def person_or_not (sentence, subject_word, ner_tagger, parsed_tokens, verb_token, subj_token):
	#perform NER
	entities = ner_tagger.get_entities(sentence)
	#if a PERSON named entity is found, assume singular, and attach 'his/her'
	if 'PERSON' in entities and [person_name for person_name in entities['PERSON'] if subject_word in person_name.lower()]:
		return [3, 1, u'his/her']
	#if a LOCATION or ORGANIZATION named entity is found, assume singular, and attach 'its'
	if 'ORGANIZATION' in entities and [person_name for person_name in entities['ORGANIZATION'] if subject_word in person_name.lower()]:
		return [3, 1, u'its']
	if 'LOCATION' in entities and [person_name for person_name in entities['LOCATION'] if subject_word in person_name.lower()]:
		return [3, 1, u'its']
	#check for pronoun
	if subject_word in possessive_dictionary:
		return [person_dictionary[subject_word], number_dictionary[subject_word], possessive_dictionary[subject_word]]
	if subject_word in possessive_dictionary_singular:
		return [3, 1, possessive_dictionary_singular[subject_word]]
	#check whether 'person' is a hypernym
	if wn.synsets(subj_token.lemma_.lower(), pos=wn.NOUN):
		subj_synset = wn.synset(subj_token.lemma_.lower() + '.n.01')
		if wn.synset('person.n.01') in list(subj_synset.closure(lambda s: s.hypernyms())):
			return [3, 1, u'his/her']
		else:
			return [3, 1, u'its']
	return None

def get_subject_properties(parsed_tokens, verb_token, object_token, ner_tagger, sentence):
	
	list_of_subjects = [subj_token for subj_token in parsed_tokens if subj_token.dep_ == "nsubj" and subj_token.head is verb_token]
	if len(list_of_subjects) == 1:
		subj_token = list_of_subjects[0]
		subject_word = subj_token.orth_.lower()			
		
		#if the verb conjugation is singular 3rd person for sure
		if (verb_token.tag_ == u'VBZ') or ((verb_token.tag_ == u'VBG' or verb_token.tag_ == u'VBN') and [aux_verb_token for aux_verb_token in parsed_tokens if aux_verb_token.dep_ == u'aux' and aux_verb_token.head is verb_token and aux_verb_token.tag_ == u'VBZ']):
			return person_or_not (sentence, subject_word, ner_tagger, parsed_tokens, verb_token, subj_token)
		
		#check if it's in the tiny pronoun dictionary
		if subject_word in possessive_dictionary:
			return [person_dictionary[subject_word], number_dictionary[subject_word], possessive_dictionary[subject_word]]
		
		#if the subject is not 'i' or 'you' or 'we' and the verb form is not 3rd person singular
		if (verb_token.tag_ == u'VBP') or ((verb_token.tag_ == u'VBG' or verb_token.tag_ == u'VBN') and [aux_verb_token for aux_verb_token in parsed_tokens if aux_verb_token.dep_ == u'aux' and aux_verb_token.head is verb_token and aux_verb_token.tag_ == u'VBP']):
			return [3, 2, u'their']
		
		"""#if the subject has a conjunction	
		compounded_subjects = [tok.orth_.lower() for tok in parsed_tokens if tok.dep_ == "conj" and tok.head is subj_token]
		if compounded_subjects:
			if [tok for tok in parsed_tokens if tok.orth_.lower() == "and" and tok.dep_ == "cc" and tok.head is subj_token]:
				if u'i' in compounded_subjects:
					return [1, 2, u'our']
				elif 'you' in compounded_subjects:
					return [2, 2, u'your']
				else:
					return [3, 2, u'their']"""
		
		#if the subject is plural according to the inflector, and the verb form is not singular - doing this test only for dictionary words and not for NEs which were not detected
		if wn.synsets(subj_token.lemma_.lower(), pos=wn.NOUN) and inflection.pluralize(subject_word) == subject_word and inflection.singularize(subject_word) != subject_word:
				return [3, 2, u'their']
	else:
		return None
