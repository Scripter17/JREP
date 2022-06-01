import argparse, os, shutil, re
from . import processors

SUPPRESS=argparse.SUPPRESS

_extendedHelp={
	# sub
	"sub":"""--sub advanced usage:
	The easiest way to explain advanced uses of `--sub` is to give an example. So take `--sub a ? b ? c d e f + x ? y z * ? t ? e d * abc xyz` as an example.  
	What it means is the following:

	- `a ? b ? c d e f`: If a match from get regex 0 matches `a` and not `b`, replace `c` with `d` and `e` with `f`
	- `+`: New conditions but stay on the same get regex
	- `x ? y z`: If a match from get regex 0 matches `x`, replace `y` with `z`
	- `*`: Move on to the next get regex
	- `? t ? e d`: If a match from get regex 1 does't match `t`, replace `e` with `d`
	- `*`: Move on to the next get regex
	- `abc xyz`: Replace `abc` with `xyz` without any conditions

	Obviously 99% of use cases don't need conditionals at all so just doing `--sub abc def * uvw xyz` is sufficient""",

	# blockwise
	"blockwise":"""Blockwise sorting:
	A generic sort function will think "file10.jpg" comes before "file2.jpg"
	Windows, on the other hand, has code that treats the number part as a number
	Blockwise sort mimics this behaviour by
	1. Splitting filenames into groups of number and non-number characters. Ex. `abc123def456.jpg` -> `["abc", "123", "def", "456", ".jpg"]`
	2. When comparing 2 filenames, compare the first element ("block") of both name's lists according to the following two rules:
		a. If either block is made of non-number characters, compare the two blocks as strings
		b. If both blocks are numbers, compare them as numbers

	The end result is that file2.jpg is correctly placed before file10.jpg""",

	# order
	"order":f"""`--order` usage:
	`--order` determines the order of functions that process matches
	- The default value for `--order` is {', '.join(list(processors.funcs))}
	- Changing the order of `sub`, `replace`, and `match-whole-lines` will mostly "work" but the output will make next to no sense
	- The main purpose of this is to move `match-regex` and `no-duplicates` to earlier in the chain""",

	# exec
	"exec":"""Using the `--exec` family of options:
	Usage looks like `--exec "echo {}"` or just `--exec "echo"`
	`--match-exec`/`--exec`: after  printing matches
	`--pre-match-exec`     : before printing matches
	`--match-exec`         : after  printing file names
	`--pre-match-exec`     : before printing file names
	`--dir-exec`           : after  printing directory names
	`--pre-dir-exec`       : before printing directory names""",
}
for topic in _extendedHelp:
	# Edits _extendedHelp to make generating the README easier
	# Should probably be moved to the pre-commit hook script
	if "JREP_MARKDOWN" in os.environ:
		_extendedHelp[topic]="## (`"+topic+"`) "+_extendedHelp[topic].replace("\n", "  \n").replace(":  ", "").replace("\n\t", "\n")
		_extendedHelp[topic]=re.sub(r"(?<=\n\t)([a-z])(?=\.)", lambda x:str("ABCDEFGHIJKLMNOPQRSTUVWXYZ".index(x[0].upper())+1), _extendedHelp[topic])
		_extendedHelp[topic]=re.sub(r"\s+:", ":", _extendedHelp[topic])
	else:
		_extendedHelp[topic]=_extendedHelp[topic].replace("`", "").replace("\t", "  ")

def getRegexModule(namespace):
	if namespace.enhanced_engine:
		import regex
		return regex
	return re

def parseLCName(name):
	name=name.replace("-", "_")
	if len(name)==2:
		name+="p"
	if "_" not in name:
		return name
	return "".join(map(lambda x:x[0], name.split("_")))

class LimitAction(argparse.Action):
	"""
		Pre-processor for --limit targets
	"""
	def __call__(self, parser, namespace, values, option_string):
		ret=utils.JSObj({}, default=0)
		for name, value in map(lambda x:x.split("="), values):
			ret[parseLCName(name)]=int(value)
		setattr(namespace, self.dest, ret)

class CountAction(argparse.Action):
	"""
		Pre-processor for --count targets
	"""
	def __call__(self, parser, namespace, values, option_string):
		setattr(namespace, self.dest, list(map(parseLCName, values)))

def listSplit(arr, needle):
	"""
		str.split but for lists. I doubt I need to say much else
	"""
	ret=[[]]
	for x in arr:
		if x==needle:
			ret.append([])
		else:
			ret[-1].append(x)
	return ret

class MatchRegexAction(argparse.Action):
	"""
		Pre-processor for --match-regex stuff
		These options take a list of arguments
		An argument of just * means that the following arguments should be applied to the next parsedArgs.regex
	"""
	def __call__(self, parser, namespace, values, option_string):
		re=getRegexModule(namespace)
		setattr(namespace, self.dest, listSplit(map(lambda x:re.comile(x.encode()), values), "*"))

class SubRegexAction(argparse.Action):
	"""
		Pre-processor for --sub stuff
		These options take a list of arguments
		a ? b ? c d e f + x ? y z * ? t ? e d
		If a match from get regex 0 matches /a/ and not /b/, replace c with d and e with f
		If a match from get regex 0 matches /x/, replace y with z
		If a match from get regex 1 does't match /t/, replace e with d
	"""
	def __call__(self, parser, namespace, values, option_string):
		re=getRegexModule(namespace)
		ret=[]
		for regexGroup in listSplit(values, "*"):
			ret.append([])
			for subSets in listSplit(regexGroup, "+"):
				parsed={"tests":[], "antiTests":[], "patterns":[], "repls":[]}
				thingParts=listSplit(subSets, "?")
				if   len(thingParts)==1: thingParts=[[],            [], thingParts[0]]
				elif len(thingParts)==2: thingParts=[thingParts[0], [], thingParts[1]]
				parsed["tests"    ]=[           x.encode()  for x in thingParts[0]      ]
				parsed["antiTests"]=[           x.encode()  for x in thingParts[1]      ]
				parsed["patterns" ]=[re.compile(x.encode()) for x in thingParts[2][0::2]] # Even elems
				parsed["repls"    ]=[           x.encode()  for x in thingParts[2][1::2]] # Odd  elems
				ret[-1].append(parsed)
		setattr(namespace, self.dest, ret)

class FileRegexAction(argparse.Action):
	"""
		Pre-processor for --file-regex stuff
	"""
	def __call__(self, parser, namespace, values, option_string):
		re=getRegexModule(namespace)
		setattr(namespace, self.dest, [re.comile(x.encode()) for x in values])

class SortRegexAction(argparse.Action):
	"""
		Pre-processor for --sort-regex
	"""
	def __call__(self, parser, namespace, values, option_string):
		re=getRegexModule(namespace)
		setattr(namespace, self.dest, [re.comile(x) if i%2==1 else x for i,x in enumerate(values)])

class CustomArgumentParser(argparse.ArgumentParser):
	"""
		A jank implementation for adding blank lines to --help
	"""
	def add_line(self, text=""):
		self._actions[-1].help+="\n"+text

class CustomHelpFormatter(argparse.HelpFormatter):
	"""
		Allows --help to better fit the console and adds support for blank lines
	"""
	def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
		argparse.HelpFormatter.__init__(self, prog, indent_increment, shutil.get_terminal_size().columns//2, width)
	def _split_lines(self, text, width):
		lines = super()._split_lines(text, width)
		if "\n" in text:
			lines += text.split("\n")[1:]
			text = text.split("\n")[0]
		return lines

class CustomHelpAction(argparse._HelpAction):
	"""
		Makes extended help (--help topic) work
	"""
	def __init__(self, *args, **kwargs):
		super(argparse._HelpAction, self).__init__(*args, **kwargs)
	def __call__(self, parser, namespace, value, option_string=None):
		if value:
			if value in _extendedHelp:
				print(_extendedHelp[value])
			else:
				print(f"Sorry, \"{value}\" has no extended help")
		else:
			parser.print_help()
		if "JREP_MARKDOWN" not in os.environ:
			print(f"The following have extended help that can be seen with --help [topic]: {', '.join(_extendedHelp)}")
		parser.exit()
