import argparse, os, sys, re, glob, mmap, copy, itertools, functools, itertools, sre_parse, inspect

"""
	JREP
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

def parseLCName(name):
	"""
		Normalize all ways --limit or --count targets can be written
	"""
	def genOpts(*opts):
		return "(?:"+"|".join([f"({opt[0]})(?:{opt[1:]})?" for opt in opts])+")"
	r=genOpts(r"file"           , r"dir"            , r"total")     +r"[-_]?"+\
	  genOpts(r"match(?:e?s)?"  , r"files?"         , r"dirs?")     +r"[-_]?"+\
	  genOpts(r"fail(?:ures?|d)", r"pass(?:e?[sd])?"          )+r"?"+r"[-_]?"+\
	  genOpts(r"counts?"        , r"percents?"                )+r"?"+r"[-_]?"+\
	  genOpts(r"regex"          , r"total"                    )+r"?"
	m=re.match(r, name)
	if m:
		return "".join(filter(lambda x:x, m.groups())).lower()
	return name

class LimitAction(argparse.Action):
	"""
		Pre-processor for --limit targets
	"""
	def __call__(self, parser, namespace, values, option_string):
		# Very jank
		ret={}
		for name, value in map(lambda x:x.split("="), values):
			ret[parseLCName(name)]=int(value)
		setattr(namespace, self.dest, ret)

class CountAction(argparse.Action):
	"""
		Pre-processor for --count targets
	"""
	def __call__(self, parser, namespace, values, option_string):
		ret=[]
		"""for value in values:
			value=parseLCName(value) or value
			if   value=="all"       : values.extend(["alltot", "allreg"])
			elif value=="alltot"    : values.extend(["totaltot", "dirtot", "filetot"])
			elif value=="allreg"    : values.extend(["totalreg", "dirreg", "filereg"])
			elif value=="total"     : values.extend(["totaltot", "totalreg"])
			elif value=="totaltot"  : values.extend(["tmtot"   , "tftot" , "tdtot"  ])
			elif value=="totalreg"  : values.extend(["tmreg"   , "tfreg" , "tdreg"  ])
			elif value=="dir"       : values.extend(["dirtot", "dirreg"])
			elif value=="dirtot"    : values.extend(["dmtot"   , "dftot"            ])
			elif value=="dirreg"    : values.extend(["dmreg"   , "dfreg"            ])
			elif value=="file"      : values.extend(["filetot", "filereg"])
			elif value=="filetot"   : values.extend(["fmtot"                        ])
			elif value=="filereg"   : values.extend(["fmreg"                        ])
			elif value not in values: values.append(value)
		print(values)"""
		for value in values:
			ret.append(parseLCName(value))
		setattr(namespace, self.dest, ret)

class MatchRegexAction(argparse.Action):
	"""
		Pre-processor for --match-regex and --match-anti-regex
		These options take a list of arguments
		An argument of just * means that the following arguments should be applied to the next parsedArgs.regex
	"""
	def __call__(self, parser, namespace, values, option_string):
		ret=[[]]
		for x in values:
			if x=="*":
				ret.append([])
			else:
				ret[-1].append(x.encode())
		setattr(namespace, self.dest, ret)

parser=argparse.ArgumentParser()
parser.add_argument("regex"                     ,       nargs="*", default=[""], help="Regex(es) to process matches for")
parser.add_argument("--string"                  , "-s", action="store_true"    , help="Test for strings instead of regex")
parser.add_argument("--no-duplicates"           , "-D", action="store_true"    , help="Don't print duplicate matches")

parser.add_argument("--file"                    , "-f", nargs="+", default=[], help="The file(s) to check")
parser.add_argument("--glob"                    , "-g", nargs="+", default=[], help="The glob(s) to check")

_stdin=parser.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"             , "-F", action="store_true"  , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"             , "-G", action="store_true"  , help="Treat STDIN as a list of globs")

parser.add_argument("--name-regex"              , "-t", nargs="+", default=[], help="If a file name matches all supplied regexes, keep going. Otherwise continue")
parser.add_argument("--name-anti-regex"         , "-T", nargs="+", default=[], help="Like --name-regex but excludes file names that match")
parser.add_argument("--name-ignore-regex"       ,       nargs="+", default=[], help="Like --name-anti-regex but doesn't contribute to --count dir-failed-files")
parser.add_argument("--full-name-regex"         ,       nargs="+", default=[], help="Like --name-regex but for absolute file paths (C:/xyz instead of xyz)")
parser.add_argument("--full-name-anti-regex"    ,       nargs="+", default=[], help="Like --full-name-regex but excludes file names that match")
parser.add_argument("--full-name-ignore-regex"  ,       nargs="+", default=[], help="Like --full-name-anti-regex but doesn't contribute to --count dir-failed-files")

parser.add_argument("--dir-name-regex"          ,       nargs="+", default=[], help="If a directory name matches all supplied regexes, enter it. Otherwise continue")
parser.add_argument("--dir-name-anti-regex"     ,       nargs="+", default=[], help="--dir-name-regex but ignore directories that match any of the supplies regexes")
parser.add_argument("--full-dir-name-regex"     ,       nargs="+", default=[], help="--dir-name-regex but applied to full directory paths")
parser.add_argument("--full-dir-name-anti-regex",       nargs="+", default=[], help="--dir-name-anti-regex but applied to full directory paths")

parser.add_argument("--file-regex"              ,       nargs="+", default=[], help="Regexes to test file contents for")
parser.add_argument("--file-anti-regex"         ,       nargs="+", default=[], help="Like --file-regex but excludes files that match")

parser.add_argument("--match-regex"             ,       nargs="+", default=[], action=MatchRegexAction, help="Basically applies str.split(\"*\") to the list of --match-regex. If a match matches all regexes in the Nth --match-regex group (where N is the index of the current get regex) continue processing the match, otherwise move on to the next one")
parser.add_argument("--match-anti-regex"        ,       nargs="+", default=[], action=MatchRegexAction, help="--match-regex but excludes matches that match any of the supplies regexes")

parser.add_argument("--sort"                    , "-S",                        help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse. A windows-esque \"blockwise\" sort is also available (todo: document)")
#parser.add_argument("--sort-regex"             ,       nargs="+", default=[], help="Regexes to apply to file names keys (like --replace) for purposes of sorting")
parser.add_argument("--no-headers"              , "-H", action="store_true"  , help="Don't print match: or file: before lines")
parser.add_argument("--print-directories"       , "-d", action="store_true"  , help="Print names of explored directories")
parser.add_argument("--print-file-names"        , "-n", action="store_true"  , help="Print file names as well as matches")
parser.add_argument("--print-full-paths"        , "-p", action="store_true"  , help="Print full file paths")
parser.add_argument("--print-posix-paths"       , "-P", action="store_true"  , help="Print replace \\ with / in file paths")
parser.add_argument("--dont-print-matches"      , "-N", action="store_true"  , help="Don't print matches (use with --print-file-names to only print names)")
parser.add_argument("--print-match-offset"      , "-o", action="store_true"  , help="Print the match offset (ignores -H)")
parser.add_argument("--print-match-range"       , "-O", action="store_true"  , help="Print the match range  (implies -o)")

parser.add_argument("--replace"                 , "-r", nargs="+", default=[], help="Regex replacement")
parser.add_argument("--sub"                     , "-R", nargs="+", default=[], help="re.sub argument pairs after --replace is applied")
parser.add_argument("--escape"                  , "-e", action="store_true"  , help="Replace \\, carriage returns, and newlines with \\\\, \\r, and \\n")

parser.add_argument("--count"                   , "-c", nargs="+", default=[], action=CountAction, help="Count match/file/dir per file, dir, and/or total (Ex: --count fm dir-files)")
parser.add_argument("--limit"                   , "-l", nargs="+", default={}, action=LimitAction, help="Limit match/file/dir per file, dir, and/or total (Ex: --limit filematch=1 total_dirs=5)")

parser.add_argument("--depth-first"             ,       action="store_true"  , help="Enter subdirectories before processing files")
parser.add_argument("--glob-root-dir"           ,                              help="Root dir to run globs in")

parser.add_argument("--match-whole-lines"       ,       action="store_true"  , help="Match whole lines like FINDSTR")
parser.add_argument("--print-non-matching-files",       action="store_true"  , help="Print file names with no matches")
parser.add_argument("--no-warn"                 ,       action="store_true"  , help="Don't print warning messages")
parser.add_argument("--weave-matches"           , "-w", action="store_true"  , help="Weave regex matchdes")
parser.add_argument("--strict-weave"            , "-W", action="store_true"  , help="Only print full match sets")

parser.add_argument("--order"                   ,       nargs="+", default=["replace", "sub", "match-whole-lines", "match-regex", "print-matches", "no-duplicates"], help="The order in which modifications to matches are applied")

parser.add_argument("--verbose"                 , "-v", action="store_true"  , help="Verbose info")
parsedArgs=parser.parse_args()

# TODO: Logging module
def verbose(x):
	if parsedArgs.verbose:
		caller=inspect.stack()[1]
		print(f"Verbose on line {caller[2]} in function {caller[3]}: {x}")
def warn(x):
	if not parsedArgs.no_warn:
		caller=inspect.stack()[1]
		print(f"Waring on line {caller[2]} in function {caller[3]}: {x}", file=sys.stderr)

verbose("JREP preview version")
verbose(parsedArgs)

def regexCheckerThing(partial, partialPass, partialFail, full="", fullPass=[], fullFail=[], partialIgnore=[], fullIgnore=[]):
	"""
		True  = Passed
		False = Failed
		None  = Ignored
	"""

	if any(map(lambda x:re.search(x, partial), partialIgnore)) or\
	   any(map(lambda x:re.search(x, full   ), fullIgnore   )):
		return None
	if any(map(lambda x:re.search(x, partial), partialFail)) or\
	   any(map(lambda x:re.search(x, full   ), fullFail   )):
		return False
	if all(map(lambda x:re.search(x, partial), partialPass)) and\
	   all(map(lambda x:re.search(x, full   ), fullPass   )):
		return True
	return False

def filenameChecker(filename, fullFilename=None):
	"""
		Shorthand for handling filenames with regexCheckerThing
	"""
	return regexCheckerThing(
		filename,
		parsedArgs.name_regex,
		parsedArgs.name_anti_regex,
		fullFilename or os.path.realpath(filename),
		parsedArgs.full_name_regex,
		parsedArgs.full_name_anti_regex,
		parsedArgs.name_ignore_regex,
		parsedArgs.full_name_ignore_regex,
	)

def _iterdir(dirname, dir_fd, dironly):
	try:
		fd = None
		fsencode = None
		files=[]
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
								if regexCheckerThing(
								   entry.name,
								   parsedArgs.dir_name_regex,
								   parsedArgs.dir_name_anti_regex,
								   os.path.realpath(os.path.join(entry.name, dirname)),
								   parsedArgs.full_dir_name_regex,
								   parsedArgs.full_dir_name_anti_regex
								   )==1:
									directories.append(entry.name)
							else:
								if fsencode is not None:
									files.append(fsencode(entry.name))
								else:
									files.append(entry.name)
					except OSError:
						pass
				for items in [directories, files] if parsedArgs.depth_first else [files, directories]:
					yield from items
		finally:
			if fd is not None:
				os.close(fd)
	except OSError:
		return

glob._iterdir=_iterdir

if not (len(parsedArgs.replace)==0 or len(parsedArgs.replace)==1 or len(parsedArgs.replace)==len(parsedArgs.regex)):
	warn("Error: Length of --replace must be either 1 or equal to the number of regexes")
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
	"dname": ("Directory: " *_header)+"{dname}",
	"fname": ("File: "      *_header)+"{fname}",
	"match": ("Match (R{regexIndex})"*_header)+ _mRange ,

	"fmr": ("File match count (R{regexIndex}): " *_header)+"{count}",
	"dmr": ("Dir match count (R{regexIndex}): "  *_header)+"{count}",
	"dfr": ("Dir file count (R{regexIndex}): "   *_header)+"{count}",
	"tmr": ("Total match count (R{regexIndex}): "*_header)+"{count}",
	"tfr": ("Total file count (R{regexIndex}): " *_header)+"{count}",
	"tdr": ("Total dir count (R{regexIndex}): "  *_header)+"{count}",

	"fmt": ("File match count (Total): " *_header)+"{count}",
	"dmt": ("Dir match count (Total): "  *_header)+"{count}",
	"dft": ("Dir file count (Total): "   *_header)+"{count}",
	"tmt": ("Total match count (Total): "*_header)+"{count}",
	"tft": ("Total file count (Total): " *_header)+"{count}",
	"tdt": ("Total dir count (Total): "  *_header)+"{count}",

	"dffc": ("Dir file failed count: "  *_header)+"{count}",
	"dffp": ("Dir file failed percent: "*_header)+"{percent:.05f}",
	"dfpc": ("Dir file passed count: "  *_header)+"{count}",
	"dfpp": ("Dir file passed percent: "*_header)+"{percent:.05f}",

	"tffc": ("Total file failed count: "  *_header)+"{count}",
	"tffp": ("Total file failed percent: "*_header)+"{percent:.05f}",
	"tfpc": ("Total file passed count: "  *_header)+"{count}",
	"tfpp": ("Total file passed percent: "*_header)+"{percent:.05f}",
}

def handleCount(rules, runData):
	"""
		A jank function that handles --count stuff
	"""
	categories={"t":"total", "d":"dir",  "f":"file"                }
	subCats   ={             "d":"dirs", "f":"files", "m":"matches"}
	modes     ={"f":"failed", "p":"passed"}

	def handleReg(key):
		if key+"r" not in parsedArgs.count: return
		category, subCat=categories[key[0]], subCats[key[1]]+"PerRegex"
		for regexIndex, subCat in enumerate(runData[category][subCat]):
			print(ofmt[key+"r"].format(count=subCat, regexIndex=regexIndex))

	def handleTot(key):
		if key+"t" not in parsedArgs.count: return
		category, subCat=categories[key[0]], "total"+subCats[key[1]].title()
		print(ofmt[key+"t"].format(count=runData[category][subCat]))

	def handleFiltered(key):
		if key not in parsedArgs.count: return
		category=categories[key[0]]
		subCat   =subCats[key[1]]
		mode    =modes[key[2]]
		val=runData[category][mode+subCat.title()]
		if key[3]=="p":
			val/=runData[category]["passed"+subCat.title()]+runData[category]["failed"+subCat.title()]
		print(ofmt[key].format(count=val, percent=val))

	if "file" in rules:
		for key in ["fm"]:
			handleReg(key)
			handleTot(key)

	if "newDir" in rules:
		for key in ["df", "dm"]:
			handleReg(key)
			handleTot(key)
		for key in ["dfpc", "dfpp", "dffc", "dffp"]:
			handleFiltered(key)

	if "total" in rules:
		for key in ["td", "tf", "tm"]:
			handleReg(key)
			handleTot(key)
		for key in ["tfpc", "tfpp", "tffc", "tffp"]:
			handleFiltered(key)

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

	def keys(self): return self.obj.keys() # Makes **JSObj work

@functools.cache
def _blockwiseSort(x, y):
	"""
		The main blockwise sort handler
		This sort key mimics how the Windows file explorer places "abc10.txt" after "abc2.txt" but more generally
		It first splits both x and y into chunks of integer substrings and non-integer substrings
		"abc123def" -> ["abc", "123", "def"]
		It then compares the Nth element of each list (a "blocK") as strings UNLESS both blocks are integers, in which case it compares them as integers
		So while "2" is larger than "10", they'd be compared as 2 and 10 and would thus be sorted properly
	"""
	xblocks=re.findall(r"\d+|[^\d]+", x) # "abc123def" -> ["abc", "123", "def"]
	yblocks=re.findall(r"\d+|[^\d]+", y)
	for xblock, yblock in zip(xblocks, yblocks):
		if xblock.isdigit() and yblock.isdigit():
			# Compare the blocks as ints
			if int(xblock)!=int(yblock):
				return int(xblock)-int(yblock) # An output of -53245 is treated the same as -1
			# If they're equal, move on to the next block pair
		else:
			# Compare the blocks as strings
			if xblock!=yblock:
				return (xblock>yblock)-(xblock<yblock)
	return 0

@functools.cmp_to_key
def blockwiseSort(x, y):
	xlist=x.replace("\\", "/").split("/")
	ylist=y.replace("\\", "/").split("/")
	for xitem, yitem in zip(xlist, ylist):
		if _blockwiseSort(xitem, yitem)!=0:
			return _blockwiseSort(xitem, yitem)
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

	#if key in ["name", "blockwise", "rname", "rblockwise"] and parsedArgs.sort_regex:
	#	for pattern, replace in zip(parsedArgs.sort_regex[0::2], parsedArgs.sort_regex[1::2]):
	#		files=map(lambda x: {"orig":x, "name":re.sub(pattern, replace, x["name"])}, files)

	#return map(lambda x:x["orig"] if "orig" in x else x, sorted(files, key=sorts[key]))

	return sorted(files, key=sorts[key])

def fileContentsDontMatter():
	return parsedArgs.dont_print_matches\
	       and not any(parsedArgs.regex)\
	       and not parsedArgs.file_regex and not parsedArgs.file_anti_regex\
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
		verbose("Yielding globs")
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
		verbose(f"Pre-processing \"{file}\"")

		if os.path.isfile(file):
			if fileContentsDontMatter() or not filenameChecker(file):
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
			verbose(f"\"{file}\" is a directory")
			yield {"name": file, "isDir": True, "stdin": False}

def processFileName(fname):
	"""
		Process filenames for printing
	"""
	if parsedArgs.print_full_paths : fname=os.path.realpath(fname)
	if parsedArgs.print_posix_paths: fname=fname.replace("\\", "/")
	return fname

def processDirName(dname):
	"""
		Process directory names for printing
	"""
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
	sys.stdout.buffer.flush()

# Abbreviations to make the code slightly cleaner
_FML=parsedArgs.limit["fm"] if "fm" in parsedArgs.limit else 0
_DML=parsedArgs.limit["dm"] if "dm" in parsedArgs.limit else 0
_TML=parsedArgs.limit["tm"] if "tm" in parsedArgs.limit else 0
_DFL=parsedArgs.limit["df"] if "df" in parsedArgs.limit else 0
_TFL=parsedArgs.limit["tf"] if "tf" in parsedArgs.limit else 0
_TDL=parsedArgs.limit["td"] if "td" in parsedArgs.limit else 0

# Tracking stuffs
currDir=None
lastDir=None

runData={
	"file": {                               "totalMatches":0,                                        "matchesPerRegex":[], "matches":[]                    },
	"dir":  {               "totalFiles":0, "totalMatches":0,                    "filesPerRegex":[], "matchesPerRegex":[], "failedFiles":0, "passedFiles":0},
	"total":{"totalDirs":0, "totalFiles":0, "totalMatches":0, "dirsPerRegex":[], "filesPerRegex":[], "matchesPerRegex":[], "failedFiles":0, "passedFiles":0},
	"matchedStrings":[]  # --no-duplicates handler
}

runData["total"]["matchesPerRegex"]=[0 for x in parsedArgs.regex]
runData["total"]["filesPerRegex"  ]=[0 for x in parsedArgs.regex]
runData["total"]["dirsPerRegex"   ]=[0 for x in parsedArgs.regex]

def delayedSub(repl, match):
	"""
		Use the secret sre_parse module to emulate re.sub with a re.Match object
	"""
	parsedTemplate=sre_parse.parse_template(repl, match.re)
	for x in parsedTemplate[0]:
		parsedTemplate[1][x[0]]=match[x[1]]
	return JSObj({
		**match,
		0:type(parsedTemplate[1][0])().join(parsedTemplate[1])
	})

def funcReplace(parsedArgs, match, **kwargs):
	"""
		Handle --replace
	"""
	if parsedArgs.replace:
		replacement=parsedArgs.replace[regexIndex%len(parsedArgs.replace)]
		match=delayedSub(replacement.encode(errors="ignore"), match)
	return match

def funcSub(parsedArgs, match, **kwargs):
	"""
		Handle --sub
		TYSM mCoding for explaining how zip works
		(zip(*arr) is a bit like transposing arr (arr[y][x] becomes arr[x][y]))
	"""
	for pair in zip(parsedArgs.sub[0::2], parsedArgs.sub[1::2]):
		match=JSObj({
			**match,
			0: re.sub(pair[0].encode(), pair[1].encode(), match[0])
		})
	return match

def funcMatchWholeLines(parsedArgs, match, file, **kwargs):
	"""
		Handle --match-whole-lines
	"""
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
	"""
		Raised by funcMatchRegex when a match failes the match regex stuff
	"""
	pass

def funcMatchRegex(matchRegex, matchAntiRegex, match, **kwargs):
	"""
		Handle --match-regex and --match-anti-regex
	"""
	if not all(map(lambda x:re.search(x, match[0]), matchRegex    )) or\
           any(map(lambda x:re.search(x, match[0]), matchAntiRegex)):
		raise Continue()

class PrintedName(Exception):
	"""
		Raised by funcPrintName when a file name is printed
	"""
	pass

def funcPrintMatches(parsedArgs, file, printedName, regexIndex, **kwargs):
	"""
		Handle file name printing
	"""
	if match[0] not in runData["matchedStrings"]:
		# Print file name
		if not printedName:
			if parsedArgs.print_file_names:
				sys.stdout.buffer.write(ofmt["fname"].format(fname=processFileName(file["name"])).encode())
				sys.stdout.buffer.write(b"\n")
				sys.stdout.buffer.flush()

		if not parsedArgs.dont_print_matches:
			if parsedArgs.weave_matches:
				runData["file"]["matches"][regexIndex].append(match)
			else:
				printMatch(match, regexIndex)
	raise PrintedName

def funcNoDuplicates(parsedArgs, match, **kwargs):
	"""
		Handle --no-duplicates
	"""
	if parsedArgs.no_duplicates:
		runData["matchedStrings"].append(match[0])

funcs={
	"replace"          : funcReplace,
	"sub"              : funcSub,
	"match-whole-lines": funcMatchWholeLines,
	"match-regex"      : funcMatchRegex,
	"print-matches"    : funcPrintMatches,
	"no-duplicates"    : funcNoDuplicates
}

for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
	verbose(f"Processing \"{file['name']}\"")
	if file["isDir"]:
		verbose(f"\"{file['name']}\" is a directory; Continuing")
		continue
	printedName=False

	runData["file"]["matchesPerRegex"]=[0 for x in parsedArgs.regex]
	runData["file"]["totalMatches"   ]=0

	# Handle --name-regex stuff
	nameRegexResult=filenameChecker(file["name"])
	if nameRegexResult is None:
	   verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched an ignore regex; Continuing...")
	   continue

	# --file-limit, --dir-match-limit, --dir-file-count, and --dir-match-count
	lastDir=currDir
	currDir=os.path.dirname(file["name"])

	# Handle new directories
	if lastDir!=currDir:
		# Print data from last dir (--count)
		if lastDir!=None:
			verbose("Just exited a directory; Printing runData...")
			handleCount(rules=["newDir"], runData=runData)
		# Handle --limit total-dir
		if _TDL and runData["total"]["totalDirs"]>=_TDL:
			verbose("Total directory limit reached; Exiting...")
			break
		# Handle --print-directories
		if parsedArgs.print_directories:
			print(ofmt["dname"].format(dname=processDirName(currDir)))
		# Initialize relevant runData
		runData["total"]["totalDirs"      ]+=1
		runData["dir"  ]["totalFiles"     ] =0
		runData["dir"  ]["matchesPerRegex"] =[0 for x in parsedArgs.regex]
		runData["dir"  ]["filesPerRegex"  ] =[0 for x in parsedArgs.regex]
		runData["dir"  ]["totalMatches"   ] =0
		runData["dir"  ]["failedFiles"    ] =0
		runData["dir"  ]["passedFiles"    ] =0

	# Handle name fail regexes
	# It has to be done here to make sure runData["dir"] doesn't miss stuff
	if filenameChecker(file["name"]) is False:
		verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched a fail regex; Continuing...")
		runData["dir"  ]["failedFiles"]+=1
		runData["total"]["failedFiles"]+=1
		continue

	# Handle --limit dir-files and dir-matches
	# Really slow on big directories
	# Might eventually have this hook into _iterdir using a global flag or something
	if (_DFL!=0 and runData["dir"]["totalFiles"]==_DFL) or (_DML!=0 and runData["dir"]["totalMatches"]>=_DML):
		continue

	# Main matching stuff
	matchIndex=0 # Just makes stuff easier
	matchedAny=False
	for (regexIndex, regex), matchRegex, matchAntiRegex in itertools.zip_longest(enumerate(parsedArgs.regex), parsedArgs.match_regex, parsedArgs.match_anti_regex, fillvalue=[]):
		verbose(f"Handling regex {regexIndex}: {regex}")

		if parsedArgs.weave_matches:
			runData["file"]["matches"].append([])

		try:
			# Turn regex into bytes
			regex=regex.encode(errors="ignore")

			# Probably a bad idea, performance wise
			if parsedArgs.string:
				regex=re.escape(regex)

			matches=re.finditer(regex, file["data"])

			# Process matches
			for matchIndex, match in enumerate(matches, start=1):
				matchedAny=True
				if matchIndex==1:
					runData["total"]["filesPerRegex"][regexIndex]+=1
					runData["dir"  ]["filesPerRegex"][regexIndex]+=1
					if lastDir!=currDir:
						runData["total"]["dirsPerRegex"][regexIndex]+=1
					if regexIndex==0:
						runData["dir"  ]["passedFiles"]+=1
						runData["total"]["passedFiles"]+=1
						runData["total"]["totalFiles" ]+=1
						runData["dir"  ]["totalFiles" ]+=1
				runData["total"]["matchesPerRegex"][regexIndex]+=1
				runData["dir"  ]["matchesPerRegex"][regexIndex]+=1
				runData["file" ]["matchesPerRegex"][regexIndex]+=1
				runData["total"]["totalMatches"   ]            +=1
				runData["dir"  ]["totalMatches"   ]            +=1
				runData["file" ]["totalMatches"   ]            +=1

				match=JSObj({
					0:match[0],
					**dict(enumerate(match.groups(), start=1)),
					"groups":match.groups,
					"span":match.span,
					"re":match.re
				})

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
				if (_FML and matchIndex                      >=_FML) or\
				   (_DML and runData["dir"  ]["totalMatches"]>=_DML) or\
				   (_TML and runData["total"]["totalMatches"]>=_TML):
					break

		except FloatingPointError as AAAAA:
			warn(f"Cannot process \"{file}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}")

	if parsedArgs.print_non_matching_files and not matchedAny:
		verbose(f"\"{file['name']}\" didn't match any file regexes, but --print-non-matching-files was specified")
		print(ofmt["fname"].format(fname=processFileName(file["name"])))

	if parsedArgs.weave_matches:
		f=zip if parsedArgs.strict_weave else itertools.zip_longest
		for matches in f(*runData["file"]["matches"]):
			for regexIndex, match in enumerate(matches):
				printMatch(match, regexIndex)

	handleCount(rules=["file"], runData=runData)

	# Hanlde --limit total-matches and total-files
	if _TML!=0 and runData["total"]["totalMatches"]>=_TML:
		verbose("Total match limit reached; Exiting")
		break
	if _TFL!=0 and fileIndex>=_TFL:
		verbose("Total file limit reached; Exiting")
		break

# --dir-match-count and --dir-file count
if currDir!=None and runData["dir"]["totalMatches"]:
	# Only runs if files were handled in two or more directories
	handleCount(rules=["newDir"], runData=runData)

# --total-match-count, --total-file-count, and --total-dir-count
handleCount(rules=["total"], runData=runData)
