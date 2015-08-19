tool_dir = 'tools'

from utilities import get_index_in_list
import os
#from difflib import get_close_matches as gcm
import urllib
import urllib2
import sys
import string
sys.path.append(tool_dir)
import en
from subprocess import Popen, PIPE, STDOUT, check_output, call
import time
#list of common prepositions
common_prepositions = ['of', 'in', 'to', 'for', 'with', 'on', 'from']
verb_prep_combination_dict = dict()
microsoft_weblm_api_key = '020d6c7b-0cbe-454b-aa06-8f37e395831a'

def setup_verb_prep_combination_dict():
	if verb_prep_combination_dict:
		return
	verb_prep_combination_file = open(tool_dir + '/lists/categorized_verb_prep_combinations','r')
	for line in verb_prep_combination_file:
		toks = line.split()
		verb_prep_combination_dict[toks[0]] = toks[1]
	verb_prep_combination_file.close()

#check if there is a catvar cluster containing the given adjective lemma that also contains an adverb
def adjective_to_adverb_in_catvar(catvar_file, lemma, adjective_adverb_dict, no_adverb_set):
	if lemma in no_adverb_set:
		return False
	if lemma in adjective_adverb_dict:
		return True
	
	catvar_file.seek(0, 0)
	string_to_search = lemma + u'_AJ%'
	adverb_marker = u'_AV%'
	at_least_one_match = False
	list_of_adverbs = []
	for line in catvar_file:
		if line.find(string_to_search) == 0 or u'#' + string_to_search in line:
			if adverb_marker in line:
				cluster_entries = line.split(u'#')
				for entry in cluster_entries:
					if adverb_marker in entry:
						at_least_one_match = True
						list_of_adverbs.append(entry.split(u'_')[0])
	
	if at_least_one_match:
		close_matches = list_of_adverbs
		if close_matches:
			adjective_adverb_dict[lemma] = close_matches[0]
		else:
			no_adverb_set.add(lemma)
			return False
	else:
		no_adverb_set.add(lemma)
						
	return at_least_one_match

#adjective to adverb conversion
def adjectival_modifier(parsed_tokens, adjectival_modifier_token, catvar_file, adjective_adverb_dict, no_adverb_set):
	final_modifier = ''
	word =  adjectival_modifier_token.lemma_.lower()
	
	if word in adjective_adverb_dict:
		final_modifier += adjective_adverb_dict[word]
	elif word in no_adverb_set:
		return final_modifier
	else:
		if adjective_to_adverb_in_catvar(catvar_file, word, adjective_adverb_dict, no_adverb_set):
			final_modifier += adjective_adverb_dict[word]
		else:
			return ''
	
	#pre-append modifiers of adjectival modifier
	modifier_of_adjective_buffer = []
	for token in parsed_tokens:
		if token.head is adjectival_modifier_token:
			modifier_of_adjective_buffer.append(token.orth_)
	if modifier_of_adjective_buffer:
		for modifier_of_adjective in reversed(modifier_of_adjective_buffer):
			final_modifier = modifier_of_adjective + ' ' + final_modifier
	
	return final_modifier.strip()

#how will a numerical modifier look in the modified sentence?
def numerical_modifier(parsed_tokens, nummod_modifier_token):
	final_modifier = ''
	word =  nummod_modifier_token.orth_.lower()
	if word == '1' or word == 'one':
		final_modifier += 'once'
	elif word == '2' or word == 'two':
		final_modifier += 'twice'
	elif word == '3' or word == 'three':
		final_modifier += 'thrice'
	elif '-' not in word:
		final_modifier += nummod_modifier_token.orth_ + ' times'
	else:
		final_modifier += nummod_modifier_token.orth_
	
	#pre-append modifiers of numerical modifier
	modifier_of_numerical_modifier_buffer = []
	for token in parsed_tokens:
		if token.head is nummod_modifier_token:
			modifier_of_numerical_modifier_buffer.append(token.orth_)
	if modifier_of_numerical_modifier_buffer:
		for modifier_of_numerical_modifier in reversed(modifier_of_numerical_modifier_buffer):
			final_modifier = modifier_of_numerical_modifier + ' ' + final_modifier		
	
	return final_modifier.strip()


def nodebox_verb_conjugator(verb_lemma, aux_verb_buffer, subject_person, subject_number, nodebox_negate, nodebox_participle, nodebox_gerund, nodebox_simple_present_third_person, nodebox_simple_present_other_person, nodebox_simple_past):
	
	non_negated_answer = verb_lemma
	
	if nodebox_participle:
		non_negated_answer = en.verb.past_participle(verb_lemma)
		if nodebox_negate:
			if aux_verb_buffer:
				aux_verb_buffer.insert(1, 'not')
				return ' '.join(aux_verb_buffer) + ' ' + non_negated_answer
			else:
				return 'not ' + non_negated_answer
	
	if nodebox_gerund:
		non_negated_answer = en.verb.present_participle(verb_lemma)
		if nodebox_negate:
			if aux_verb_buffer:
				return ' '.join(aux_verb_buffer.insert(1, 'not')) + ' ' + non_negated_answer
			else:
				return 'not ' + non_negated_answer
	
	if nodebox_simple_present_third_person:
		non_negated_answer = en.verb.present(verb_lemma, person=3, negate=False)
		if nodebox_negate:
			return 'does not ' + en.verb.present(verb_lemma, person=2, negate=False)	
		
	if nodebox_simple_present_other_person:
		non_negated_answer = en.verb.present(verb_lemma, person=1, negate=False)
		if nodebox_negate:
			return 'do not ' + non_negated_answer
			
	if nodebox_simple_past:
		non_negated_answer = en.verb.past(verb_lemma, person=1, negate=False)
		if nodebox_negate:
			return 'did not ' + non_negated_answer
	
	if nodebox_negate:
		if aux_verb_buffer and aux_verb_buffer is not None:
			aux_verb_buffer.insert(1, u'not')
			return ' '.join(aux_verb_buffer) + ' ' + non_negated_answer
		else:
			if str(subject_person) == '3' and str(subject_number) == '1':
				return 'does not ' + non_negated_answer
			else:
				return 'do not ' + non_negated_answer
	
	if aux_verb_buffer and aux_verb_buffer is not None:
		return ' '.join(aux_verb_buffer) + ' ' + non_negated_answer
	else:
		return non_negated_answer
	

def nodebox_verb_conjugator_passive(verb_lemma, final_phrase_active, aux_verb_buffer, subject_person, subject_number, nodebox_negate, nodebox_participle, nodebox_gerund, nodebox_simple_present_third_person, nodebox_simple_present_other_person, nodebox_simple_past):
	
	auxiliary_verb_added = ''
	
	if nodebox_participle:
		auxiliary_verb_added = 'been'
	elif nodebox_gerund:
		auxiliary_verb_added = 'being'
	elif nodebox_simple_present_third_person:
		if str(subject_number) == '1':
			auxiliary_verb_added = 'is'
		else:
			auxiliary_verb_added = 'are'
	elif nodebox_simple_present_other_person:
		if str(subject_person) == '1' and str(subject_number) == '1':
			auxiliary_verb_added = 'am'
		elif str(subject_person) == '3' and str(subject_number) == '1':
			auxiliary_verb_added = 'is'
		else:
			auxiliary_verb_added = 'are'
	elif nodebox_simple_past:
		if str(subject_number) == '2' or str(subject_person) == '2':
			auxiliary_verb_added = 'were'
		else:
			auxiliary_verb_added = 'was'
	else:
		auxiliary_verb_added = 'be'
	
	final_phrase_passive = final_phrase_active
	
	if set(['do','does','did']) & set(final_phrase_active.split(' ')):
		final_phrase_passive1 = final_phrase_passive.replace('does', auxiliary_verb_added)
		final_phrase_passive2 = final_phrase_passive1.replace('do', auxiliary_verb_added)
		final_phrase_passive3 = final_phrase_passive2.replace('did', auxiliary_verb_added)
		final_phrase_passive4 = final_phrase_passive3.replace(final_phrase_passive3.split(' ')[-1], en.verb.past_participle(verb_lemma))
		return final_phrase_passive4
	else:
		final_phrase_passive = final_phrase_passive.replace(final_phrase_passive.split(' ')[-1], auxiliary_verb_added + ' ' + en.verb.past_participle(verb_lemma))
		return final_phrase_passive


def variativity_replacement(sentence, verb_token, object_token, object_index, verb_index, parsed_tokens, related_verb, lvc_phrase, catvar_file, adjective_adverb_dict, no_adverb_set, subject_person, subject_number):
	verb_tag = verb_token.tag_
	final_phrase = u''
	
	set_negation = False
	set_perfect = False
	set_progressive = False
	set_present_tense = False
	set_past_tense = False
	set_future_tense = False
	set_third_person = False
	set_modal = False
	set_gerund_only = False
	modal_verb = ''
	set_having_participle = False
	
	nodebox_negate = False
	nodebox_participle = False
	nodebox_gerund = False
	nodebox_simple_present_third_person = False
	nodebox_simple_present_other_person = False
	nodebox_simple_past = False
	
	list_of_auxiliary_verbs = []
	for token in parsed_tokens:
		if token.head is verb_token and token.dep_ in ['aux', 'neg']:
			list_of_auxiliary_verbs.append(token.orth_.lower())
	
	if 'has' in list_of_auxiliary_verbs:
		set_present_tense = True
		set_third_person = True
	elif 'have' in list_of_auxiliary_verbs:
		set_present_tense = True
	elif 'had' in list_of_auxiliary_verbs:
		set_past_tense = True
	if 'been' in list_of_auxiliary_verbs:
		set_perfect = True
		set_progressive = True
	if set(['will', '\'ll', 'shall']) & set(list_of_auxiliary_verbs):
		set_future_tense = True
	if 'did' in list_of_auxiliary_verbs:
		set_past_tense = True
	if 'does' in list_of_auxiliary_verbs:
		set_present_tense = True
		set_third_person = True
	if 'do' in list_of_auxiliary_verbs:
		set_present_tense = True
	if 'can' in list_of_auxiliary_verbs:
		set_modal = True
		modal_verb = 'can'
		set_present_tense = True
	if 'could' in list_of_auxiliary_verbs:
		set_modal = True
		modal_verb = 'could'
	if 'should' in list_of_auxiliary_verbs:
		set_modal = True
		modal_verb = 'should'
	if 'was' in list_of_auxiliary_verbs:
		set_past_tense = True
		set_third_person = True
	if 'were' in list_of_auxiliary_verbs:
		set_past_tense = True
	
	#third person singular form, present tense
	if verb_tag == u'VBZ':
		set_third_person = True
		set_present_tense = True
		nodebox_simple_present_third_person = True
	#present tense, plural subject
	elif verb_tag == u'VBP':
		set_present_tense = True
		nodebox_simple_present_other_person = True
	#gerund
	elif verb_tag == u'VBG':
		nodebox_gerund = True
		set_progressive = True
		#gerund without auxiliary
		if not list_of_auxiliary_verbs:
			set_gerund_only = True
	#participle. 'having' + participle is handled separately from the regular perfect tenses
	elif verb_tag == u'VBN' and (set(['has', '\'s', 'have', '\'d', 'had', '\'d', 'having']) & set(list_of_auxiliary_verbs)):
		nodebox_participle = True
		if 'having' in list_of_auxiliary_verbs:
			set_having_participle = True
		else:
			set_perfect = True
	#a simple past tense (VBD) is commonly mistagged as a perfect (VBN)
	elif verb_tag == u'VBD' or verb_tag == u'VBN':
		set_past_tense = True
		nodebox_simple_past = True

	# the exact phrase to replace in the sentence
	phrase_to_replace = lvc_phrase
	aux_verb_buffer = []
	for token in parsed_tokens:
		if token.head is verb_token and token.dep_ in ['aux', 'neg']:
			aux_verb_buffer.append(token.orth_)
	if aux_verb_buffer:
		for aux_verb in reversed(aux_verb_buffer):
			phrase_to_replace = aux_verb + ' ' + phrase_to_replace

	#currently omitting cases like 'had HE been going to the station', where all the auxiliary verbs and the main verb are not contiguous
	if phrase_to_replace not in sentence:
		return ''
	
	list_of_modifiers = [token for token in parsed_tokens if token.head is object_token and token.dep_ != "det" and get_index_in_list(parsed_tokens, token) in range(verb_index, object_index)]
	list_of_modifiers.extend([token for token in parsed_tokens if token.head is verb_token and token is not object_token and token.dep_ != "det" and get_index_in_list(parsed_tokens, token) in range(verb_index, object_index)])
	
	#handle separately numerical and adjectival modifiers, and also look for clues where the verb must occur in its negated form
	#adjectival modifiers
	list_of_amod_modifiers = [token for token in list_of_modifiers if token.dep_ == "amod" and token.head is object_token]
	#numerical modifiers
	list_of_nummod_modifiers = [token for token in list_of_modifiers if token.dep_ == "nummod" and token.head is object_token and token.orth_.lower() not in ['0', 'zero']]
	#clues for negation- a numerical modifier that says 'zero', or a determiner for the object which says 'no'. More can, of course, be added
	list_of_negative_modifiers = [token for token in parsed_tokens if token.head is object_token and ((token.dep_ == 'nummod' and token.orth_.lower() in ['0', 'zero']) or (token.dep_ == 'det' and token.orth_.lower() == 'no'))]
	
	adjectival_modification = ''
	numerical_modification = ''
	dative_object_string = ''
	
	#handle negation generation
	if list_of_negative_modifiers:
		#print list_of_negative_modifiers[0].orth_, list_of_negative_modifiers[0].dep_, list_of_negative_modifiers[0].head.orth_, list_of_negative_modifiers[0].tag_
		set_negation = True
		nodebox_negate = True
	"""negation_list = [token for token in parsed_tokens if token.dep_ == 'neg' and token.head is verb_token and get_index_in_list(parsed_tokens, token) < object_index]
	if negation_list:
		print 'Negation case 2'
		print negation_list[0].orth_, negation_list[0].dep_, negation_list[0].head.orth_, negation_list[0].tag_
		set_negation = True		
		nodebox_negate = True"""
	
	#convert adjectives to adverbs
	if list_of_amod_modifiers:
		main_amod_modifier_token = list_of_amod_modifiers[0]
		amod_modification = adjectival_modifier(parsed_tokens, main_amod_modifier_token, catvar_file, adjective_adverb_dict, no_adverb_set)
		if amod_modification:
			adjectival_modification = amod_modification
	
	#convert numerical modifiers by post-appending 'times'
	if list_of_nummod_modifiers:
		main_nummod_modifier_token = list_of_nummod_modifiers[0]
		nummod_modification = numerical_modifier(parsed_tokens, main_nummod_modifier_token)
		if nummod_modification:
			numerical_modification = nummod_modification
	
	#call to simplenlg program to generate verb form
	"""simplenlg_command = 'java -jar SimpleNLGPhraseGenerator.jar ' + str(set_negation) + ' ' + str(set_present_tense) + ' ' + str(set_past_tense) + ' ' + str(set_future_tense) + ' ' + str(set_third_person) + ' ' + str(set_perfect) + ' ' + str(set_progressive) + ' ' + str(set_modal) + ' ' + str(set_having_participle) + ' ' + str(subject_person) + ' ' + str(subject_number) + ' ' + related_verb + ' ' + modal_verb
	status = os.system(simplenlg_command + ' > verb_phrase_output')
	print status
	print simplenlg_command
	print sentence
	temp_file = open('verb_phrase_output', 'r')
	#content = check_output(simplenlg_command)
	content = temp_file.readline()
	phrases = content.split(' ||| ')
	temp_file.close()
	os.system('rm verb_phrase_output')
	#if there was an error in the simplenlg programme
	if len(phrases) != 2:
		return ''"""
	final_phrase_active = nodebox_verb_conjugator(related_verb, aux_verb_buffer, subject_person, subject_number, nodebox_negate, nodebox_participle, nodebox_gerund, nodebox_simple_present_third_person, nodebox_simple_present_other_person, nodebox_simple_past) #phrases[0]
	final_phrase_passive = nodebox_verb_conjugator_passive(related_verb, final_phrase_active, aux_verb_buffer, subject_person, subject_number, nodebox_negate, nodebox_participle, nodebox_gerund, nodebox_simple_present_third_person, nodebox_simple_present_other_person, nodebox_simple_past) #phrases[1]
	
	if final_phrase_passive is None:
		return ''
	
	#if the verb was only a gerund
	"""if (set_gerund_only):
		print "Sentence is- " + sentence
		print "Active phrase is- " + final_phrase_active
		final_phrase_active = final_phrase_active.split(' ')[1]
		final_phrase_passive = ' '.join(final_phrase_passive.split(' ')[1:])
	
	#'having' + participle
	if (set_having_participle):
		final_phrase_active = 'having ' + final_phrase_active
		final_phrase_passive = 'having ' + final_phrase_passive"""
	
	#WAIT, THIS IS PROBLEMATIC
	list_of_dative_objects_within_phrase = [token for token in parsed_tokens if token.dep_ == 'dative' and token.head is verb_token and get_index_in_list(parsed_tokens, token) in range(verb_index, object_index)]
	if len(list_of_dative_objects_within_phrase) == 1:
		dative_token = list_of_dative_objects_within_phrase[0]
		dative_object_string = dative_token.orth_
		dative_object_buffer = []
		for token in parsed_tokens:
			if token.head is dative_token:
				dative_object_buffer.append(token.orth_)
		if dative_object_buffer:
			for dative_object_modifier in reversed(dative_object_buffer):
				dative_object_string = dative_object_modifier + ' ' + dative_object_string
	
	if adjectival_modification and adjectival_modification.strip()[-2:] == 'ly':
		final_phrase_active = ' '.join(final_phrase_active.split()[:-1]) + ' ' + adjectival_modification + ' ' + final_phrase_active.split()[-1]
		final_phrase_passive = ' '.join(final_phrase_passive.split()[:-1]) + ' ' + adjectival_modification + ' ' + final_phrase_passive.split()[-1]	
	if dative_object_string:
		final_phrase_active += ' ' + dative_object_string
		final_phrase_passive += ' by ' + dative_object_string
	if adjectival_modification and not (adjectival_modification[-2:] == 'ly'):
		final_phrase_active += ' ' + adjectival_modification
		final_phrase_passive += ' ' + adjectival_modification
	if numerical_modification:
		final_phrase_active += ' ' + numerical_modification
		final_phrase_passive += ' ' + numerical_modification
	final_phrase_active = final_phrase_active.strip()
	final_phrase_passive = final_phrase_passive.strip()
	
	
	#now to wonder whether to omit the preposition or not	
	setup_verb_prep_combination_dict()
	list_of_preposition_tokens = [token for token in parsed_tokens if token.tag_ == u'IN' and (token.dep_ == 'dative' or token.dep_ == 'prep') and token.orth_.lower() in common_prepositions and (token.head is verb_token or token.head is object_token) and get_index_in_list(parsed_tokens, token) in range(verb_index + 1, object_index + 2)]
	if list_of_preposition_tokens:
		preposition_token = list_of_preposition_tokens[0]
		verb_prep_caps = verb_token.lemma_.upper() + '_' + preposition_token.orth_.upper()
		if verb_prep_caps in verb_prep_combination_dict and verb_prep_combination_dict[verb_prep_caps] != '-':
			if verb_prep_combination_dict[verb_prep_caps] == '+':
				#reconstruct sentence without that preposition
				#print 'Preposition unambiguously removed'
				sentence = ''
				for token in parsed_tokens:
					if token is not preposition_token:
						sentence += token.orth_ + ' '
				sentence.strip()
			elif verb_prep_combination_dict[verb_prep_caps] == 'A':
				probabilities = urllib2.urlopen(urllib2.Request('http://weblm.research.microsoft.com/rest.svc/bing-body/2013-12/5/jp?u=' + microsoft_weblm_api_key + '&format=json', en.verb.past(related_verb) + '\n' + en.verb.past(related_verb) + ' ' + preposition_token.orth_)).read().split(',')
				verb_probability = float(probabilities[0][1:])
				verb_prep_probability = float(probabilities[1][:-1])
				#print en.verb.past(related_verb), verb_probability
				#print en.verb.past(related_verb) + ' ' + preposition_token.orth_, verb_prep_probability
				#major changes may be needed here
				if verb_probability - verb_prep_probability > 1.75:	
					sentence = ''
					for token in parsed_tokens:
						if token is not preposition_token:
							sentence += token.orth_ + ' '
					sentence.strip()
	
	#if the object is coordinated in a zeugma, replicate the verb to feature with the coordinated object
	zeugma_heads = [token for token in parsed_tokens if token.dep_ == 'conj' and token.head is object_token and [other_token for other_token in parsed_tokens if other_token.orth_.lower() in ['and', 'or'] and other_token.dep_ == 'cc' and other_token.head is object_token]]
	if zeugma_heads:
		zeugma_conjunction = [other_token for other_token in parsed_tokens if other_token.orth_.lower() in ['and', 'or'] and other_token.dep_ == 'cc' and other_token.head is object_token][0]
		conjunction_index = get_index_in_list(parsed_tokens, zeugma_conjunction)
		sentence = sentence.replace(parsed_tokens[conjunction_index-1].orth_ + ' '+ zeugma_conjunction.orth_ + ' ' + parsed_tokens[conjunction_index+1].orth_, parsed_tokens[conjunction_index-1].orth_ + ' '+ zeugma_conjunction.orth_ + ' ' + verb_token.orth_ + ' ' + parsed_tokens[conjunction_index+1].orth_)
				
	return [sentence.replace(phrase_to_replace, final_phrase_active), sentence.replace(phrase_to_replace, final_phrase_passive)]
