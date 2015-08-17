def nodebox_verb_conjugator(verb_lemma, aux_verb_buffer, subject_person, subject_number, nodebox_negate, nodebox_participle, nodebox_gerund, nodebox_simple_present_third_person, nodebox_simple_present_other_person, nodebox_simple_past):
	
	non_negated_answer = verb_lemma
	
	if nodebox_participle:
		non_negated_answer = en.verb.past_participle(verb_lemma)
		if nodebox_negate:
			if aux_verb_buffer:
				return ' '.join(aux_verb_buffer.insert(1, 'not')) + ' ' + non_negated_answer
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
		if aux_verb_buffer:
			return ' '.join(aux_verb_buffer.insert(1, 'not')) + ' ' + non_negated_answer
		else:
			if str(subject_person) == '3' and str(subject_number) == '1':
				return 'does not ' + non_negated_answer
			else:
				return 'do not ' + non_negated_answer
	
	if aux_verb_buffer:
		return ' '.join(aux_verb_buffer) + ' ' + non_negated_answer
	else:
		return non_negated_answer
	

def nodebox_verb_conjugator_passive(verb_lemma, final_phrase_active, aux_verb_buffer, subject_person, subject_number, nodebox_negate, nodebox_participle, nodebox_gerund, nodebox_simple_present_third_person, nodebox_simple_present_other_person, nodebox_simple_past):
	
	auxiliary_verb_added = ''
	
	elif nodebox_participle:
		auxiliary_verb_added = 'been'
	elif nodebox_gerund:
		auxiliary_verb_added = 'being'
	elif nodebox_simple_present_third_person:
		auxiliary_verb_added = 'is/are'
	elif nodebox_simple_present_other_person:
		if str(subject_person) == '1' and str(subject_number) == '1':
			auxiliary_verb_added = 'am'
		else:
			auxiliary_verb_added = 'is/are'
	elif nodebox_simple_past:
		if str(subject_number) == '2':
			auxiliary_verb_added = 'were'
		else:
			auxiliary_verb_added = 'was'
	else:
		auxiliary_verb_added = 'be'
	
	
	final_phrase_passive = final_phrase_active
	
	if set(['do','does','did']) & set(final_phrase_active.split(' ')):
		final_phrase_passive = string.replace(final_phrase_passive, 'do', auxiliary_verb_added)
		final_phrase_passive = string.replace(final_phrase_passive, 'does', auxiliary_verb_added)
		final_phrase_passive = string.replace(final_phrase_passive, 'did', auxiliary_verb_added)
		final_phrase_passive = final_phrase_passive.replace(final_phrase_passive.split(' ')[-1], en.verb.past_participle(verb_lemma))
		
	else:
		final_phrase_passive = final_phrase_passive.replace(final_phrase_passive.split(' ')[-1], auxiliary_verb_added + ' ' + en.verb.past_participle(verb_lemma))
		
		return final_phrase_passive
