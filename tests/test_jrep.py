import jrep.jrep, inspect

tests=[
	{
		"args":[r"(?i)[+-]?[\d,]+(\.\d+)?(e[+-]?[\d,]+)?", "-f", "testing/text/numbers.txt"],
		"pattern":{
			"files":[
				{"name":"testing/text/numbers.txt"}
			],
			"matches":[
				{"groups":[None, None], "span":[0,17]},
				...,
				{"span":[39,48]}
			]
		}
	}
]

def matchReplacement(struct, pattern):
	if isinstance(struct, dict) and isinstance(pattern, dict):
		for x in pattern:
			if x not in struct:
				return False
			if matchReplacement(struct[x], pattern[x]) is False:
				return False
		return True
	elif isinstance(struct, list) and isinstance(pattern, list):
		for x,y in zip(struct, pattern):
			if y is not ...:
				if matchReplacement(x, y) is False:
					return False
		return True
	else:
		return pattern is ... or struct==pattern

def test_matching():
	assert matchReplacement({"a":[1,2,3], "b":[2]}, {"a":[...,2], "b":[...]})
	assert matchReplacement(2, 3) is False
	assert matchReplacement(2, 2)

def test_JREP():
	print(dir(jrep.jrep))
	print(type(jrep.jrep.main), inspect.getmembers(jrep.jrep.main))
	for test in tests:
		result=jrep.jrep.main(test["args"], returnJSON=True)
		assert matchReplacement(result, test["pattern"])
