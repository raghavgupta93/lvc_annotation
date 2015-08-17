from subprocess import Popen, PIPE, STDOUT

p = Popen(['java', '-jar', 'SimpleNLGPhraseGenerator.jar', 'False', 'True', 'False', 'False', 'True', 'False', 'False', 'False', 'False', '3', '1', 'feel', ''], stdout=PIPE, stderr=STDOUT)
for line in p.stdout:
	print line
