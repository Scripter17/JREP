import subprocess as sp

tests=[
	{
		"command":["jrep", "a.", "-g", "testing/*", "-dP"],
		"equals":b"""Directory: testing
Match (R0): ab
Match (R0): a\r\n""",
		"exit":0
	}
]

def test_JREP():
	for test in tests:
		result=sp.run(test["command"], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
		if "start"  in test: assert result.stdout.startswith(test["start" ])
		if "equals" in test: assert result.stdout     ==     test["equals"]
		if "end"    in test: assert result.stdout.endswith  (test["end"   ])
