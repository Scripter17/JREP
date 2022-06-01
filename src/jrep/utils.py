try:
	import sre_parse
except:
	from . import sre_parse # type: ignore
import re, fnmatch
import os, subprocess as sp, sys
from . import sorts, common

_compile_replacement_helper=None # type: ignore

class JSObj:
	"""
		[J]ava[S]cript [Obj]ects
		JavaScript allows both {"a":1}.a and {"a":1}["a"]
		This class mimicks that to make mutilating re.Match objects easier
	"""
	def __init__(self, obj, default=None, defaultFactory=None):
		object.__setattr__(self, "obj"            , obj)
		object.__setattr__(self, "default"        , default)
		object.__setattr__(self, "_defaultFactory", defaultFactory)

	def defaultFactory(self, key):
		if self._defaultFactory is None:
			return self.default
		try:
			return self._defaultFactory(self, key)
		except Exception:
			return self.default

	def __repr__(self):
		return f"JSObj({self.obj})"

	def __getattr__(self, key):      return self.obj[key] if key in self.obj else self.defaultFactory(key)
	def __setattr__(self, key, val):        self.obj[key]=val
	def __delattr__(self, key):      del    self.obj[key]

	def __getitem__(self, key):      return self.obj[key] if key in self.obj else self.defaultFactory(key)
	def __setitem__(self, key, val):        self.obj[key]=val
	def __delitem__(self, key):      del    self.obj[key]

	def keys(self): return self.obj.keys() # Makes **JSObj work

class NextMatch(Exception):
	"""
		Raised by funcMatchRegex and funcNoDuplicates when a match failes the match regex stuff
	"""
	pass

class NextFile(Exception):
	"""
		Raised by funcNoNameDuplicates when a file name failes the name regex stuff
	"""
	pass

def parseTemplate(repl, match):
	# regex._compile_replacement_helper(regex.compile(r".(.)."), r"a\1b")
	# ['a', 1, 'b']
	# sre_parse.parse_template(r"a\1b", re.compile(".(.)."))
	# ([(1, 1)], ['a', None, 'b'])
	if common.enhancedEngine:
		# I already have the code for handling sre_parse.parse_template
		parsedTemplate=_compile_replacement_helper(common.regex.compile(match.re.pattern), repl) # type: ignore
		ret=([], parsedTemplate)
		for i, x in enumerate(parsedTemplate):
			if isinstance(x, int):
				ret[0].append((i, x))
				ret[1][i]=None
		return ret
	else:
		# parsedTemplate=sre_parse.parse_template(repl, match.re)
		# ret=parsedTemplate[1]
		# for index, group in parsedTemplate[0]:
		# 	ret[index]=group
		# return ret
		return sre_parse.parse_template(repl, match.re)

def delayedSub(repl, match):
	"""
		Use the secret sre_parse module to emulate re.sub with a re.Match object
		Used exclusively for --replace
		Python 3.11: sre_parse is removed, so I stole the function and put it at the top of this file
		I really need to give up on the "JREP as a single file" dream
	"""
	parsedTemplate=sre_parse.parse_template(repl, match.re)
	groups=[match[0], *match.groups()]
	for x in parsedTemplate[0]:
		parsedTemplate[1][x[0]]=groups[x[1]]
	match[0]=type(parsedTemplate[1][0])().join(parsedTemplate[1])
	return match

def sortFiles(files, sortRegexes, key=None):
	"""
		Sorts files if --sort is present
		Note that sorting files requires loading all file names in a directory into memory
		Also it's just generally slow for large file sets
		Unless you're using really high end SSD, CPU, and RAM
		And if you are then I'm sorry for writing JREP in Python
	"""
	if key==None:
		return files

	if key in ["name", "blockwise", "rname", "rblockwise"] and sortRegexes:
		for pattern, replace in zip(sortRegexes[0::2], sortRegexes[1::2]):
			files=map(lambda file: {"orig":file["orig"] if "orig" in file else file, "name":pattern.sub(replace, file["name"])}, files)
	return map(lambda x:x["orig"] if "orig" in x else x, sorted(files, key=sorts.sorts[key]))

	#return sorted(files, key=sorts[key])

def sortDirFiles(names, dirname, sortRegexes, key=None):
	"""
		Handler for --sort-dir
	"""
	if key is None:
		yield from names
		return
	files=map(lambda name:{"name":os.path.join(dirname, name), "stdin":False}, names)
	for file in sortFiles(files, sortRegexes, key=key):
		yield os.path.relpath(file["name"], dirname)

def escape(match):
	r"""
		Handle --escape
		Converts backslashes, carriage returns, and newlines to \\, \r, and \n respectively
		Also converts non-printable bytes to \xXX to avoid stuff like ANSI codes and bells
	"""
	ret=match.replace(b"\\", b"\\\\").replace(b"\r", b"\\r").replace(b"\n", b"\\n")
	ret=re.sub(rb"[\x00-\x1f\x80-\xff]", lambda x:(f"\\x{ord(x[0]):02x}".encode()), ret)
	return ret

# Functions for --name-regex and co.
def regexCheckerThing(partial, partialPass, partialFail, full="", fullPass=[], fullFail=[], partialIgnore=[], fullIgnore=[]):
	"""
		True  = Passed
		False = Failed
		None  = Ignored
	"""
	if (partialIgnore and any(map(lambda x:x.search(partial), partialIgnore))) or\
	   (fullIgnore    and any(map(lambda x:x.search(full   ), fullIgnore   ))):
		return None
	if (partialFail and any(map(lambda x:x.search(partial), partialFail))) or\
	   (fullFail    and any(map(lambda x:x.search(full   ), fullFail   ))):
		return False
	if all(map(lambda x:x.search(partial), partialPass)) and\
	   all(map(lambda x:x.search(full   ), fullPass   )):
		return True
	return False

def globCheckerThing(partial, partialPass, partialFail, full="", fullPass=[], fullFail=[], partialIgnore=[], fullIgnore=[]):
	"""
		True  = Passed
		False = Failed
		None  = Ignored
	"""
	if any(map(lambda x:fnmatch.fnmatch(partial, x), partialIgnore)) or\
	   any(map(lambda x:fnmatch.fnmatch(full   , x), fullIgnore   )):
		return None
	if any(map(lambda x:fnmatch.fnmatch(partial, x), partialFail)) or\
	   any(map(lambda x:fnmatch.fnmatch(full   , x), fullFail   )):
		return False
	if all(map(lambda x:fnmatch.fnmatch(partial, x), partialPass)) and\
	   all(map(lambda x:fnmatch.fnmatch(full   , x), fullPass   )):
		return True
	return False

def filenameChecker(parsedArgs, file):
	"""
		Shorthand for handling filenames with regexCheckerThing
	"""
	r=regexCheckerThing(
		file["name"],
		parsedArgs.name_regex,
		parsedArgs.name_anti_regex,
		file["absDir"],
		parsedArgs.full_name_regex,
		parsedArgs.full_name_anti_regex,
		parsedArgs.name_ignore_regex,
		parsedArgs.full_name_ignore_regex,
	)
	g=globCheckerThing(
		file["name"],
		parsedArgs.name_glob,
		parsedArgs.name_anti_glob,
		file["absDir"],
		parsedArgs.full_name_glob,
		parsedArgs.full_name_anti_glob,
		parsedArgs.name_ignore_glob,
		parsedArgs.full_name_ignore_glob,
	)
	if False in [r,g]: return False
	if None  in [r,g]: return None
	return True

def dirnameChecker(parsedArgs, dirname):
	return regexCheckerThing(
		dirname,
		parsedArgs.dir_name_regex,
		parsedArgs.dir_name_anti_regex,
		os.path.normpath(os.path.join(os.getcwd(), dirname)),
		parsedArgs.dir_full_name_regex,
		parsedArgs.dir_full_name_anti_regex,
		parsedArgs.dir_name_ignore_regex,
		parsedArgs.dir_full_name_ignore_regex
	)

def _funcSub(subRules, match, regexIndex, wrap=True, **kwargs):
	"""
		Handle --sub, --name-sub, and --dir-name-sub
		TYSM mCoding for explaining how zip works
		(zip(*arr) is a bit like transposing arr (arr[y][x] becomes arr[x][y]))
	"""
	if subRules:
		if wrap:
			regexIndex=regexIndex%len(subRules)
		if regexIndex<len(subRules):
			for group in subRules[regexIndex]:
				if regexCheckerThing(match, group["tests"], group["antiTests"]):
					for pattern, repl in zip(group["patterns"], group["repls"]):
						match=pattern.sub(repl, match)
	return match

def processFileName(parsedArgs, fname):
	"""
		Process file names according to --name-sub, --print-full-paths, and --print-posix-paths
		Used for printing file names as well as --no-name-duplicates
	"""
	fname=_funcSub(parsedArgs.name_sub, fname.encode(), 0, wrap=False)
	if parsedArgs.print_full_paths : fname=os.path.realpath(fname)
	if parsedArgs.print_posix_paths: fname=fname.replace(b"\\", b"/")
	fname=_funcSub(parsedArgs.name_sub, fname, 1, wrap=False)
	return fname

def processDirName(parsedArgs, dname):
	"""
		processFileName but applied to directory names
		--dir-name-sub is used instead of --name-sub
	"""
	dname=_funcSub(parsedArgs.dir_name_sub, dname.encode(), 0)
	dname=dname or b"."
	if parsedArgs.print_full_paths : dname=os.path.realpath(dname)
	if parsedArgs.print_posix_paths: dname=dname.replace(b"\\", b"/")
	dname=_funcSub(parsedArgs.dir_name_sub, dname, 1)
	return dname

def execHandler(parsedArgs, cmd, arg=None):
	"""
		Handle the --exec family of options
		sp.run(b"echo This doesn't work on Windows for some reason")
	"""
	if cmd is None or parsedArgs.no_exec:
		return
	# if os.name=="nt":
	# 	# Windows moment :/
	# 	if isinstance(cmd, bytes): cmd=cmd.decode()
	# 	if isinstance(arg, bytes): arg=arg.decode()
	if arg is not None:
		if not isinstance(arg, list):
			arg=[arg]
		cmd=cmd.format(*arg)

	sp.run(cmd, shell=True)

STDIN=b""
if not os.isatty(sys.stdin.fileno()): # type: ignore[attr-defined]
	STDIN=sys.stdin.buffer.read()