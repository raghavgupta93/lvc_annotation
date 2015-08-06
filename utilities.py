#simple function to return index to an item in the list whose reference has been provided
def get_index_in_list(given_list, given_object):
	for i in range(len(given_list)):
		if (given_object == given_list[i]):
			return i
	return -1
