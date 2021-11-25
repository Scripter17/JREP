import argparse, os, sys, re, glob, mmap, copy, itertools, functools, itertools, sre_parse

"""
	JREP
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

def parseLCName(name):
	def genOpts(*opts):
		# opts=["file", "files", "dir", ...]
		return "(?:"+"|".join([f"({opt[0]})(?:{opt[1:]})?" for opt in opts])+")"
	#r=r"(?i)(?:(f)(?:iles?)?|(d)(?:irs?)?|(t)(?:otals?)?)[-_]?(?:(m)(?:atch(?:e?s)?)?|(f)(?:iles?)?|(d)(?:irs?)?)(?:[-_]?(?:(f)(?:ailure)?))?(?:[-_]?(?:(p)(?:ercent)?))?"
	r=genOpts(r"file"         , r"dir"            , r"total")    +r"[-_]?"+\
	  genOpts(r"match(?:e?s)?", r"files?"         , r"dirs?")    +r"[-_]?"+\
	  genOpts(r"failures?"    , r"pass(?:e?[sd])?"          )+"?"+r"[-_]?"+\
	  genOpts(r"percents?"                                  )+"?"
	m=re.match(r, name)
	return m and "".join(filter(lambda x:x, m.groups())).lower()

class LimitAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string):
		# Very jank
		ret={}
		for name, value in map(lambda x:x.split("="), values):
			ret[parseLCName(name)]=int(value)
		setattr(namespace, self.dest, ret)

class CountAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string):
		for value in values:
			value=parseLCName(value) or value
			if   value=="all"       : values.extend(["total", "dir", "file"])
			elif value=="total"     : values.extend(["tm",    "tf",  "td"])
			elif value=="dir"       : values.extend(["dm",    "df"])
			elif value=="file"      : values.extend(["fm"])
			elif value not in values: values.append(value)
		setattr(namespace, self.dest, values)

class MatchRegexAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string):
		ret=[[]]
		for x in values:
			if x=="*":
				ret.append([])
			else:
				ret[-1].append(x.encode())
		setattr(namespace, self.dest, ret)

parser=argparse.ArgumentParser()

parser.add_argument("regex"                 ,       nargs="*", default=[""], help="Regex(es) to process matches for")
parser.add_argument("--string"              , "-s", action="store_true"    , help="Test for strings instead of regex")
parser.add_argument("--no-duplicates"       , "-D", action="store_true"    , help="Don't print duplicate matches")

parser.add_argument("--file"                , "-f", nargs="+", default=[], help="The file(s) to check")
parser.add_argument("--glob"                , "-g", nargs="+", default=[], help="The glob(s) to check")

_stdin=parser.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"         , "-F", action="store_true"  , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"         , "-G", action="store_true"  , help="Treat STDIN as a list of globs")

parser.add_argument("--name-regex"            , "-t", nargs="+", default=[], help="Regex to test relative file names for")
parser.add_argument("--name-anti-regex"       ,       nargs="+", default=[], help="Like --name-regex but excludes file names that match")
parser.add_argument("--name-ignore-regex"     ,       nargs="+", default=[], help="Like --name-anti-regex but doesn't contribute to --count dir-failed-files")
parser.add_argument("--full-name-regex"       , "-T", nargs="+", default=[], help="Regex to test absolute file names for")
parser.add_argument("--full-name-anti-regex"  ,       nargs="+", default=[], help="Like --full-name-regex but excludes file names that match")
parser.add_argument("--full-name-ignore-regex",       nargs="+", default=[], help="Like --full-name-anti-regex but doesn't contribute to --count dir-failed-files")

parser.add_argument("--file-regex"          ,       nargs="+", default=[], help="Regexes to test file contents for")
parser.add_argument("--file-anti-regex"     ,       nargs="+", default=[], help="Like --file-regex but excludes files that match")

parser.add_argument("--match-regex"         ,       nargs="+", default=[], action=MatchRegexAction, help="Only output match if, adter --replace and --sub, it matches all of these regexes (unimplemented)")
parser.add_argument("--match-anti-regex"    ,       nargs="+", default=[], action=MatchRegexAction, help="Only output match if, adter --replace and --sub, it doesn't fail any of these regexes (unimplemented)")

parser.add_argument("--sort"                , "-S",                        help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse. A windows-esque \"blockwise\" sort is also available (todo: document)")
parser.add_argument("--no-headers"          , "-H", action="store_true"  , help="Don't print match: or file: before lines")
parser.add_argument("--print-directories"   , "-d", action="store_true"  , help="Print names of explored directories")
parser.add_argument("--print-file-names"    , "-n", action="store_true"  , help="Print file names as well as matches")
parser.add_argument("--print-full-paths"    , "-p", action="store_true"  , help="Print full file paths")
parser.add_argument("--print-posix-paths"   , "-P", action="store_true"  , help="Print replace \\ with / in file paths")
parser.add_argument("--dont-print-matches"  , "-N", action="store_true"  , help="Don't print matches (use with --print-file-names to only print names)")
parser.add_argument("--print-match-offset"  , "-o", action="store_true"  , help="Print the match offset (ignores -H)")
parser.add_argument("--print-match-range"   , "-O", action="store_true"  , help="Print the match range  (implies -o)")

parser.add_argument("--replace"             , "-r", nargs="+", default=[], help="Regex replacement")
parser.add_argument("--sub"                 , "-R", nargs="+", default=[], help="re.sub argument pairs after --replace is applied")
parser.add_argument("--escape"              , "-e", action="store_true"  , help="Replace \\, carriage returns, and newlines with \\\\, \\r, and \\n")

parser.add_argument("--count"               , "-c", nargs="+", default=[], action=CountAction, help="Count match/file/dir per file, dir, and/or total (Ex: --count fm dir-files)")
parser.add_argument("--limit"               , "-l", nargs="+", default={}, action=LimitAction, help="Count match/file/dir per file, dir, and/or total (Ex: --limit filematch=1 total_dirs=5)")

parser.add_argument("--depth-first"         ,       action="store_true"  , help="Enter subdirectories before processing files")
parser.add_argument("--glob-root-dir"       ,                              help="Root dir to run globs in")

parser.add_argument("--match-whole-lines"         , action="store_true", help="Match whole lines like FINDSTR")
parser.add_argument("--print-non-matching-files"  , action="store_true", help="Print file names with no matches")
parser.add_argument("--no-warn"                   , action="store_true", help="Don't print warning messages")
parser.add_argument("--weave-matches"       , "-w", action="store_true", help="Weave regex matchdes")
parser.add_argument("--strict-weave"        , "-W", action="store_true", help="Only print full match sets")

parser.add_argument("--order"               ,       nargs="+", default=["replace", "sub", "match-whole-lines", "match-regex", "print-matches", "no-duplicates"], help="The order in which handling is done to matches")

parser.add_argument("--verbose"             , "-v", action="store_true"  , help="Verbose info")
parsedArgs=parser.parse_args()

def verbose(x):
	if parsedArgs.verbose:
		print(f"Verbose: {x}")
def warn(x):
	if not parsedArgs.no_warn:
		print(f"{x}", file=sys.stderr)

verbose("JREP preview version")
verbose(parsedArgs)

def _iterdirBreadthFirst(dirname, dir_fd, dironly):
	try:
		fd = None
		fsencode = None
		directories=[]
		if dir_fd is not None:
			if dirname:
				fd = arg = os.open(dirname, _dir_open_flags, dir_fd=dir_fd)
			else:
				arg = dir_fd
			if isinstance(dirname, bytes):
				fsencode = os.fsencode
		elif dirname:
			arg = dirname
		elif isinstance(dirname, bytes):
			arg = bytes(os.curdir, 'ASCII')
		else:
			arg = os.curdir
		try:
			with os.scandir(arg) as it:
				for entry in it:
					try:
						if not dironly or entry.is_dir():
							if entry.is_dir():
								directories.append(entry)
							else:
								if fsencode is not None:
									yield fsencode(entry.name)
								else:
									yield entry.name
					except OSError:
						pass
				for directory in directories:
					if fsencode is not None:
						yield fsencode(directory.name)
					else:
						yield directory.name
		finally:
			if fd is not None:
				os.close(fd)
	except OSError:
		return

def _iterdirDepthFirst(dirname, dir_fd, dironly):
	try:
		fd = None
		fsencode = None
		files=[]
		if dir_fd is not None:
			if dirname:
				fd = arg = os.open(dirname, _dir_open_flags, dir_fd=dir_fd)
			else:
				arg = dir_fd
			if isinstance(dirname, bytes):
				fsencode = os.fsencode
		elif dirname:
			arg = dirname
		elif isinstance(dirname, bytes):
			arg = bytes(os.curdir, 'ASCII')
		else:
			arg = os.curdir
		try:
			with os.scandir(arg) as it:
				for entry in it:
					try:
						if not dironly or entry.is_dir():
							if not entry.is_dir():
								files.append(entry)
							else:
								if fsencode is not None:
									yield fsencode(entry.name)
								else:
									yield entry.name
					except OSError:
						pass
				for file in files:
					if fsencode is not None:
						yield fsencode(file.name)
					else:
						yield file.name
		finally:
			if fd is not None:
				os.close(fd)
	except OSError:
		return

if parsedArgs.depth_first:
	glob._iterdir=_iterdirDepthFirst
else:
	glob._iterdir=_iterdirBreadthFirst

if not (len(parsedArgs.replace)==0 or len(parsedArgs.replace)==1 or len(parsedArgs.replace)==len(parsedArgs.regex)):
	print("Error: Length of --replace must be either 1 or equal to the number of regexes", file=sys.stderr)
	exit(1)

# Simple implementation of --escape
if parsedArgs.escape:
	parsedArgs.sub.extend(["\\", "\\\\", "\r", "\\r", "\n", "\\n"])
	verbose("Added --escape args to --sub; --sub is now", parsedArgs.sub)

# Dumb output fstring generation stuff
_header=not parsedArgs.no_headers
_mOffs1=parsedArgs.print_match_offset or parsedArgs.print_match_range
_mOffs2=parsedArgs.print_match_range
_mRange=("{range[0]:08x}"*_mOffs1)+("-{range[1]:08x}"*_mOffs2)
_mAt=_header and _mOffs1
_mRange=(" at "*_mAt) + (_mRange) + (": "*(_header or _mRange!=""))

# Output fstrings to make later usage easier
ofmt={
	"dname": ("Directory: "          *_header)+"{dname}",
	"fname": ("File: "               *_header)+"{fname}",
	"match": ("Match (R{regexIndex})"*_header)+ _mRange ,

	"fmcnt": ("File match count (R{regexIndex}): " *_header)+"{count}",
	"dmcnt": ("Dir match count (R{regexIndex}): "  *_header)+"{count}",
	"dfcnt": ("Dir file count: "                   *_header)+"{count}",
	"tmcnt": ("Total match count (R{regexIndex}): "*_header)+"{count}",
	"tfcnt": ("Total file count: "                 *_header)+"{count}",
	"tdcnt": ("Total dir count: "                  *_header)+"{count}",

	"dffcnt" : ("Dir failed file count: "          *_header)+"{count}",
	"dffpcnt": ("Dir failed file percentage: "     *_header)+"{percent}",

	"dfpcnt" : ("Dir passed file count: "          *_header)+"{count}",
	"dfppcnt": ("Dir passed file percentage: "     *_header)+"{percent}",
}

def handleCount(rules, runData):
	if "newDir" in rules:
		if "dm" in parsedArgs.count:
			for regexIndex, count in enumerate(runData["dir"]["matches"]):
				print(ofmt["dmcnt"].format(count=count, regexIndex=regexIndex))
		if "df" in parsedArgs.count:
			print(ofmt["dfcnt"].format(count=runData["dir"]["files"]))
		if "dff" in parsedArgs.count:
			print(ofmt["dffcnt"].format(count=runData["dir"]["failedFiles"]))
		if "dffp" in parsedArgs.count:
			print(ofmt["dffpcnt"].format(percent=runData["dir"]["failedFiles"]/(runData["dir"]["passedFiles"]+runData["dir"]["failedFiles"])))
		if "dfp" in parsedArgs.count:
			print(ofmt["dfpcnt"].format(count=(runData["dir"]["passedFiles"])))
		if "dfpp" in parsedArgs.count:
			print(ofmt["dfppcnt"].format(percent=runData["dir"]["passedFiles"]/(runData["dir"]["passedFiles"]+runData["dir"]["failedFiles"])))

	if "total" in rules:
		if "tm" in parsedArgs.count:
			for regexIndex, count in enumerate(runData["total"]["matches"]):
				print(ofmt["tmcnt"].format(count=count, regexIndex=regexIndex))
		if "tf" in parsedArgs.count:
			print(ofmt["tfcnt"].format(count=runData["total"]["files"]))
		if "td" in parsedArgs.count:
			print(ofmt["tdcnt"].format(count=runData["total"]["dirs"]))

class JSObj:
	"""
		[J]ava[S]cript [Obj]ects
		JavaScript allows both {"a":1}.a and {"a":1}["a"]
		This class mimicks that
	"""
	def __init__(self, obj): object.__setattr__(self, "obj", copy.copy(obj))

	def __getattr__(self, key):      return self.obj[key]
	def __setattr__(self, key, val):        self.obj[key]=val
	def __delattr__(self, key):      del    self.obj[key]

	def __getitem__(self, key):      return self.obj[key]
	def __setitem__(self, key, val):        self.obj[key]=val
	def __delitem__(self, key):      del    self.obj[key]

	def keys(self): return self.obj.keys()

@functools.cache
def _blockwiseSort(x, y):
	xblocks=re.findall(r"\d+|[^\d]+", x)
	yblocks=re.findall(r"\d+|[^\d]+", y)
	for i in range(min(len(xblocks), len(yblocks))):
		if xblocks[i].isdigit() and yblocks[i].isdigit():
			# Compare the blocks as ints
			if int(xblocks[i])!=int(yblocks[i]):
				return int(xblocks[i])-int(yblocks[i]) # An output of -53245 is treated the same as -1
		else:
			# Compare the blocks as strings
			if xblocks[i]!=yblocks[i]:
				return (xblocks[i]>yblocks[i])-(xblocks[i]<yblocks[i])
	return 0

@functools.cmp_to_key
def blockwiseSort(x, y):
	xlist=x.replace("\\", "/").split("/")
	ylist=y.replace("\\", "/").split("/")
	for i in range(min(len(xlist), len(ylist))):
		if _blockwiseSort(xlist[i], ylist[i])!=0:
			return _blockwiseSort(xlist[i], ylist[i])
	return (len(xlist)>len(ylist))-(len(xlist)<len(ylist))

def sortFiles(files, key=None):
	"""
		Sorts files if --sort is present
		Note that sorting files requires loading all file names in a directory into memory
		Also it's just generally slow
	"""
	if key==None:
		return files

	sorts={
		"ctime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_ctime,
		"mtime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_mtime,
		"atime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_atime,
		"name"     : lambda x:x["name"],
		"blockwise": lambda x:blockwiseSort(x["name"]),
		"size"     : lambda x:len(x["data"]) if x["stdin"] else os.path.getsize(x["name"])
	}
	for sort in list(sorts.keys()):
		# Scopes suck
		sorts["r"+sort]=(lambda _sort:lambda x:-sorts[_sort](x))(sort)

	return sorted(files, key=sorts[key])

def fileContentsDontMatter():
	return parsedArgs.dont_print_matches\
	       and not any(parsedArgs.regex)\
	       and not parsedArgs.file_regex       and not parsedArgs.file_anti_regex\
	       and not {"fm", "dm", "tm"}.intersection(parsedArgs.limit.keys())\
	       and not {"fm", "dm", "tm"}.intersection(parsedArgs.count)

def getFiles():
	"""
		Yields files selected with --file and --glob as {"file":filename, "data":mmapFile/bytes}
		Stdin has a filename of -
		Empty files and stdin use a bytes object instead of mmap
		If the contents of a file are irrelevant, b"" is always used instead of mmap
	"""
	def _getFiles():
		"""
			Get a raw list of files selected with --file and --glob
			This is just here so I don't have to write the mmap code twice
			Probably could replace the array addition with a few `yield from`s
		"""

		# Files
		verbose("Yielding files")
		# --stdin-files
		if not os.isatty(sys.stdin.fileno()) and parsedArgs.stdin_files:
			yield from sys.stdin.read().splitlines()
		# --file
		yield from parsedArgs.file

		# Globs
		verbose("Yielding globs") # r/PythonOOC
		# --stdin-globs
		if not os.isatty(sys.stdin.fileno()) and parsedArgs.stdin_globs:
			for pattern in sys.stdin.read().splitlines():
				yield from glob.iglob(pattern, recursive=True)
		# --glob
		for pattern in parsedArgs.glob:
			yield from glob.iglob(pattern, recursive=True)

	# Add stdin as a file
	if not os.isatty(sys.stdin.fileno()) and not parsedArgs.stdin_files and not parsedArgs.stdin_globs:
		verbose("Processing STDIN")
		yield {"name":"-", "data":sys.stdin.read().encode(errors="ignore"), "isDir": False, "stdin": True}

	for file in _getFiles():
		verbose(f"Processing file \"{file}\"")

		if os.path.isfile(file):
			if fileContentsDontMatter():
				# Does the file content matter? No? Ignore it then
				verbose("Optimizing away actually opening the file")
				yield {"name": file, "data": b"", "isDir": False, "stdin": False}
			else:
				try:
					with open(file) as f:
						# Stream data from file instead of loading a 48.2TB file into RAM
						try:
							mmapFile=mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
						except ValueError:
							mmapFile=b""
						yield {"name": file, "data": mmapFile, "isDir": False, "stdin": False}
				except Exception as AAAAA:
					warn(f"Cannot process \"{file}\" because of \"{AAAAA}\"")
		else:
			yield {"name": file, "isDir": True, "stdin": False}

def processFileName(fname):
	if parsedArgs.print_full_paths : fname=os.path.realpath(fname)
	if parsedArgs.print_posix_paths: fname=fname.replace("\\", "/")
	return fname

def processDirName(dname):
	if os.path.isfile(dname):
		dname=os.path.dirname(dname)
	dname=dname or "."
	if parsedArgs.print_full_paths : dname=os.path.realpath(dname)
	if parsedArgs.print_posix_paths: dname=dname.replace("\\", "/")
	return dname

def printMatch(match, regexIndex):
	if match==None:
		return
	sys.stdout.buffer.write(ofmt["match"].format(range=match.span(), regexIndex=regexIndex).encode())
	sys.stdout.buffer.write(match[0])
	sys.stdout.buffer.write(b"\n")

# Abbreviations to make my editor not show a horizontal scrollbar (my version of PEP8)
_FML=parsedArgs.limit["fm"] if "fm" in parsedArgs.limit else 0
_DML=parsedArgs.limit["dm"] if "dm" in parsedArgs.limit else 0
_TML=parsedArgs.limit["tm"] if "tm" in parsedArgs.limit else 0
_DFL=parsedArgs.limit["df"] if "df" in parsedArgs.limit else 0
_TFL=parsedArgs.limit["tf"] if "tf" in parsedArgs.limit else 0
_TDL=parsedArgs.limit["td"] if "td" in parsedArgs.limit else 0

# Tracking stuffs
fileDir=None
lastDir=None

runData={
	"file":{},
	"dir":{"files":0, "matches":[], "failedFiles":0, "passedFiles":0},
	"total":{"dirs":0, "files":0, "matches":[0 for x in range(len(parsedArgs.regex))]},
	"matchedStrings":[]  # --no-duplicates handler
}

def delayedSub(repl, match):
	parsedTemplate=sre_parse.parse_template(repl, match.re)
	for x in parsedTemplate[0]:
		parsedTemplate[1][x[0]]=match[x[1]]
	return JSObj({
		"span":match.span,
		0:type(parsedTemplate[1][0])().join(parsedTemplate[1])
	})

def funcReplace(parsedArgs, match, **kwargs):
	if parsedArgs.replace:
		replacement=parsedArgs.replace[regexIndex%len(parsedArgs.replace)]
		match=delayedSub(replacement.encode(errors="ignore"), match)
	return match

def funcSub(parsedArgs, match, **kwargs):
	# Handle --sub
	# TYSM mCoding for explaining how zip works
	# (zip(*arr) is a bit like transposing arr (arr[y][x] becomes arr[x][y]))
	for pair in zip(parsedArgs.sub[0::2], parsedArgs.sub[1::2]):
		match=JSObj({
			**match,
			0: re.sub(pair[0].encode(), pair[1].encode(), match[0])
		})
	return match

def funcMatchWholeLines(parsedArgs, match, file, **kwargs):
	# --match-whole-lines
	if parsedArgs.match_whole_lines:
		lineStart=file["data"].rfind(b"\n", 0, match.span()[1])
		lineEnd  =file["data"]. find(b"\n",    match.span()[1])
		if lineStart==-1: lineStart=None
		if lineEnd  ==-1: lineEnd  =None
		return JSObj({
			**match,
			0: file["data"][lineStart:match.span()[0]]+match[0]+file["data"][match.span()[1]:lineEnd]
		})
	return match

class Continue(Exception):
	pass

def funcMatchRegex(matchRegex, matchAntiRegex, match, **kwargs):
	if not all(map(lambda x:re.search(x, match[0]), matchRegex    )) or\
       any(map(lambda x:re.search(x, match[0]), matchAntiRegex)):
		raise Continue()

class PrintedName(Exception):
	pass

def funcPrintMatches(parsedArgs, file, printedName, regexIndex, **kwargs):
	# Print matches
	if match[0] not in runData["matchedStrings"]:
		# Print file name
		if not printedName:
			if parsedArgs.print_file_names:
				sys.stdout.buffer.write(ofmt["fname"].format(fname=processFileName(file["name"])).encode())
				sys.stdout.buffer.write(b"\n")
			runData["total"]["files"]+=1

		if not parsedArgs.dont_print_matches:
			if parsedArgs.weave_matches:
				runData["file"]["matches"][regexIndex].append(match)
			else:
				printMatch(match, regexIndex)
	raise PrintedName

def funcNoDuplicates(parsedArgs, match, **kwargs):
	# Handle --no-duplicates
	if parsedArgs.no_duplicates:
		runData["matchedStrings"].append(match[0])


funcs={
	"replace": funcReplace,
	"sub": funcSub,
	"match-whole-lines": funcMatchWholeLines,
	"match-regex": funcMatchRegex,
	"print-matches": funcPrintMatches,
	"no-duplicates": funcNoDuplicates
}

for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
	verbose(f"Processing {file}")
	runData["file"]={"matches":[list() for x in range(len(parsedArgs.regex))], "fmc":[0 for x in range(len(parsedArgs.regex))]}
	printedName=False

	if file["isDir"]:
		continue

	# Handle --name-regex, --full-name-regex, --name-anti-regex, and--full-name-anti-regex
	if any(map(lambda x:re.search(x,                  file["name"] ), parsedArgs.name_ignore_regex     )) or\
	   any(map(lambda x:re.search(x, os.path.realpath(file["name"])), parsedArgs.full_name_ignore_regex)):
	   verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" failed the name ignore regexes")
	   continue
	if not all(map(lambda x:re.search(x,                  file["name"] ), parsedArgs.name_regex          )) or\
	   not all(map(lambda x:re.search(x, os.path.realpath(file["name"])), parsedArgs.full_name_regex     )) or\
	       any(map(lambda x:re.search(x,                  file["name"] ), parsedArgs.name_anti_regex     )) or\
	       any(map(lambda x:re.search(x, os.path.realpath(file["name"])), parsedArgs.full_name_anti_regex)):
		# Really should make how this works configurable
		verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" failed the name regexes")
		runData["dir"]["failedFiles"]+=1
		continue

	runData["dir"]["passedFiles"]+=1

	# --file-limit, --dir-match-limit, --dir-file-count, and --dir-match-count
	lastDir=fileDir
	fileDir=os.path.dirname(file["name"])

	# --dir-match-count and --dir-file-count
	if lastDir!=None and lastDir!=fileDir:
		handleCount(rules=["newDir"], runData=runData)

	# --limit td
	if _TDL and len(runData["dir"].keys())>=_TDL:
		continue

	# --print-directories
	if fileDir!=lastDir:
		runData["total"]["dirs"]+=1
		print(ofmt["dname"].format(dname=processDirName(fileDir)))

	# Keeps track of, well, directory data
	if fileDir!=lastDir:
		runData["dir"]={"files":0, "matches":[0 for x in range(len(parsedArgs.regex))], "failedFiles":0, "passedFiles":1}

	# Handle --file-limit
	# Really slow on big directories
	if (_DFL!=0 and runData["dir"]["files"]==_DFL) or (_DML!=0 and runData["dir"]["matches"]>=_DML):
		continue
	runData["dir"]["files"]+=1

	# There aren't any matches to handle
	if file["isDir"]:
		continue

	# Main matching stuff
	_continue=False # PEP-3136 would've come in clutch here
	matchIndex=0 # Just makes --XYZ-match-count stuff and --print-non-matching-files easier
	for (regexIndex, regex), matchRegex, matchAntiRegex in itertools.zip_longest(enumerate(parsedArgs.regex), parsedArgs.match_regex, parsedArgs.match_anti_regex, fillvalue=[]):
		verbose(f"Handling regex {regexIndex}: {regex}")

		if parsedArgs.weave_matches:
			runData["file"]["matches"].append([])
		#runData["dir"]["matches"].append(0)
		#runData["file"]["fmc"].append(0)

		try:
			# Handle --file-regex and --file-anti-regex
			_fileRegexCheck=lambda regex: re.search(regex.encode(errors="ignore"), file["data"])
			if any(map(_fileRegexCheck, parsedArgs.file_anti_regex)) or not all(map(_fileRegexCheck, parsedArgs.file_regex)):
				# Move to the next file
				_continue=True
				break

			# Turn regex into bytes
			regex=regex.encode(errors="ignore")

			# Probably a bad idea, performance wise
			if parsedArgs.string:
				regex=re.escape(regex)

			matches=re.finditer(regex, file["data"])

			# Process matches
			matchIndex=0
			for matchIndex, match in enumerate(matches, start=1):
				runData["total"]["matches"][regexIndex]+=1
				runData["dir"]["matches"][regexIndex]+=1
				runData["file"]["fmc"][regexIndex]+=1

				try:
					for func in parsedArgs.order:
						match=funcs[func](
							regexIndex=regexIndex,
							regex=regex,
							matchRegex=matchRegex,
							matchAntiRegex=matchAntiRegex,
							file=file,
							printedName=printedName,
							parsedArgs=parsedArgs,
							match=match
						) or match
				except Continue:
					continue
				except PrintedName:
					printedName=True

				# Handle --match-limit, --dir-match-limit, and --total-match-limit
				if (_FML!=0 and matchIndex>=_FML) or\
				   (_DML!=0 and runData["dir"]["matches"]>=_DML) or\
				   (_TML!=0 and runData["total"]["matches"]>=_TML):
					break

		except Exception as AAAAA:
			warn(f"Cannot process \"{file}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}")

	if parsedArgs.print_non_matching_files and matchIndex==0:
		print(ofmt["fname"].format(fname=processFileName(file["name"])))

	if parsedArgs.weave_matches:
		f=zip if parsedArgs.strict_weave else itertools.zip_longest
		for matches in f(*runData["file"]["matches"]):
			for regexIndex, match in enumerate(matches):
				printMatch(match, regexIndex)

	# --count fm
	if "fm" in parsedArgs.count:
		for regexIndex, count in enumerate(runData["file"]["fmc"]):
			print(ofmt["fmcnt"].format(count=count, regexIndex=regexIndex))

	# For if a file failes the --name-regex stuff
	if _continue:
		continue

	# Hanlde --total-match-limit and --total-file-limit
	if (_TML!=0 and runData["total"]["matches"]>=_TML) or (_TFL!=0 and fileIndex>=_TFL):
		break

# --dir-match-count and --dir-file count
if fileDir!=None:
	handleCount(rules=["newDir"], runData=runData)

# --total-match-count, --total-file-count, and --total-dir-count
handleCount(rules=["total"], runData=runData)
