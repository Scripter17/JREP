import argparse, os, sys, re, glob, mmap, copy, itertools, functools, sre_parse, inspect, json, shutil, fnmatch

"""
	JREP
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

DEFAULTORDER=["replace", "match-whole-lines", "sub", "match-regex", "no-duplicates", "print-dir", "print-name", "print-matches"]

class JSObj:
	"""
		[J]ava[S]cript [Obj]ects
		JavaScript allows both {"a":1}.a and {"a":1}["a"]
		This class mimicks that
	"""
	def __init__(self, obj, default=None):
		object.__setattr__(self, "obj"    , obj)
		object.__setattr__(self, "default", default)

	def __getattr__(self, key):      return self.obj[key] if key in self.obj else self.default
	def __setattr__(self, key, val):        self.obj[key]=val
	def __delattr__(self, key):      del    self.obj[key]

	def __getitem__(self, key):      return self.obj[key] if key in self.obj else self.default
	def __setitem__(self, key, val):        self.obj[key]=val
	def __delitem__(self, key):      del    self.obj[key]

	def keys(self): return self.obj.keys() # Makes **JSObj work

def _LCNameRegexPart(*opts):
	return "(?:"+"|".join([f"({opt[0]})(?:{opt[1:]})?" for opt in opts])+")"
_LCNameRegex=_LCNameRegexPart(r"files?"              , r"dir(?:ectori(?:es|y))?", r"total"                 )    +r"[-_]?"+\
             _LCNameRegexPart(r"match(?:e?s)?"       , r"files?"                , r"dir(?:ectori(?:es|y))?")    +r"[-_]?"+\
             _LCNameRegexPart(r"total"               , r"fail(?:u(?:re)?s?|d)"  , r"pass(?:e?[sd])?"       )+"?"+r"[-_]?"+\
             _LCNameRegexPart(r"counts?"             , r"percent(age)?s?"                                  )+"?"+r"[-_]?"+\
             _LCNameRegexPart(r"regex"               , r"total"                                            )+"?"
_LCNameRegex=f"^{_LCNameRegex}$"

def parseLCName(name):
	"""
		Normalize all ways --limit or --count targets can be written
	"""
	ret=name
	match=re.match(_LCNameRegex, name, re.I)
	if match:
		ret="".join(filter(lambda x:x, match.groups())).lower()
		if len(ret)==2:
			ret+="p"
	return ret

class LimitAction(argparse.Action):
	"""
		Pre-processor for --limit targets
	"""
	def __call__(self, parser, namespace, values, option_string):
		# Very jank
		ret=JSObj({}, default=0)
		for name, value in map(lambda x:x.split("="), values):
			ret[parseLCName(name)]=int(value)
		setattr(namespace, self.dest, ret)

class CountAction(argparse.Action):
	"""
		Pre-processor for --count targets
	"""
	def __call__(self, parser, namespace, values, option_string):
		setattr(namespace, self.dest, list(map(parseLCName, values)))

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

def listRindex(arr, needle):
	"""
		str.rindex but for lists. I doubt I need to say much else
	"""
	for i in range(len(arr)-1, -1, -1):
		if arr[i]==needle:
			return i
	raise ValueError("Lists not having rindex, find, or rfind is dumb")

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

class SubRegexAction(argparse.Action):
	"""
		Pre-processor for replacement regexes
		These options take a list of arguments
		a ? b ? c d e f + x ? y z * ? t ? e d
		If a match from get regex 0 matches /a/ and not /b/, replace c with d and e with f
		If a match from get regex 0 matches /x/, replace y with z
		If a match from get regex 1 does't match /t/, replace e with d
	"""
	def __call__(self, parser, namespace, values, option_string):
		ret=[]
		for regexGroup in listSplit(values, "*"):
			ret.append([])
			for subSets in listSplit(regexGroup, "+"):
				parsed={"tests":[], "antiTests":[], "patterns":[], "repls":[]}
				thingParts=listSplit(subSets, "?")
				if   len(thingParts)==1: thingParts=[[],            [], thingParts[0]]
				elif len(thingParts)==2: thingParts=[thingParts[0], [], thingParts[1]]
				parsed["tests"    ]=[x.encode() for x in thingParts[0]      ]
				parsed["antiTests"]=[x.encode() for x in thingParts[1]      ]
				parsed["patterns" ]=[x.encode() for x in thingParts[2][0::2]]
				parsed["repls"    ]=[x.encode() for x in thingParts[2][1::2]]
				ret[-1].append(parsed)
		setattr(namespace, self.dest, ret)

class FileRegexAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string):
		values=[x.encode() for x in values]
		setattr(namespace, self.dest, values)

class CustomHelpFormatter(argparse.HelpFormatter):
	def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
		argparse.HelpFormatter.__init__(self, prog, indent_increment=2, max_help_position=shutil.get_terminal_size().columns//2, width=None)

parser=argparse.ArgumentParser(formatter_class=CustomHelpFormatter)
parser.add_argument("regex"                       ,       nargs="*", default=[], metavar="Regex", help="Regex(es) to process matches for (reffered to as \"get regexes\")")
parser.add_argument("--string"                    , "-s", action="store_true"                   , help="Treat get regexes as strings. Doesn't apply to any other options.")
parser.add_argument("--no-duplicates"             , "-D", action="store_true"                   , help="Don't print duplicate matches (See also: --order)")

parser.add_argument("--file"                      , "-f", nargs="+", default=[]                 , help="A list of files to check")
parser.add_argument("--glob"                      , "-g", nargs="+", default=[]                 , help="A list of globs to check")

_stdin=parser.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"               , "-F", action="store_true"                   , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"               , "-G", action="store_true"                   , help="Treat STDIN as a list of globs")

parser.add_argument("--name-regex"                , "-t", nargs="+", default=[], metavar="Regex", help="If a file name matches all supplied regexes, keep going. Otherwise continue")
parser.add_argument("--name-anti-regex"           , "-T", nargs="+", default=[], metavar="Regex", help="Like --name-regex but excludes file names that match any of the supplied regexes")
parser.add_argument("--name-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", help="Like --name-anti-regex but doesn't contribute to --count *-failed-files")
parser.add_argument("--full-name-regex"           ,       nargs="+", default=[], metavar="Regex", help="Like --name-regex but for absolute file paths (C:/xyz instead of xyz)")
parser.add_argument("--full-name-anti-regex"      ,       nargs="+", default=[], metavar="Regex", help="Like --name-anti-regex but applied to full file paths")
parser.add_argument("--full-name-ignore-regex"    ,       nargs="+", default=[], metavar="Regex", help="Like --full-name-anti-regex but doesn't contribute to --count *-failed-files")

parser.add_argument("--dir-name-regex"            ,       nargs="+", default=[], metavar="Regex", help="If a directory name matches all supplied regexes, enter it. Otherwise continue")
parser.add_argument("--dir-name-anti-regex"       ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-regex but excludes directories that match any of the supplied regexes")
parser.add_argument("--dir-name-ignore-regex"     ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-anti-regex but doesn't contribute to --count total-failed-dirs")
parser.add_argument("--dir-full-name-regex"       ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-regex but for absolute directory paths (C:/xyz instead of xyz)")
parser.add_argument("--dir-full-name-anti-regex"  ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-anti-regex but applied to full directory paths")
parser.add_argument("--dir-full-name-ignore-regex",       nargs="+", default=[], metavar="Regex", help="Like --dir-full-name-anti-regex but doesn't contribute to --count total-failed-dirs")

parser.add_argument("--file-regex"                ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Regexes to test file contents for")
parser.add_argument("--file-anti-regex"           ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Like --file-regex but excludes files that match of the supplied regexes")
parser.add_argument("--file-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Like --file-anti-regex but doesn't contribute to --count *-failed-files")

parser.add_argument("--match-regex"               ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Basically applies str.split(\"*\") to the list of --match-regex. If a match matches all regexes in the Nth --match-regex group (where N is the index of the current get regex) continue processing the match, otherwise move on to the next one")
parser.add_argument("--match-anti-regex"          ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Like --match-regex but excludes matches that match any of the supplied regexes")
parser.add_argument("--match-ignore-regex"        ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Like --match-anti-regex but doesn't contribute to --count *-failed-matches")

parser.add_argument("--sort"                      , "-S",                                         help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse. A windows-esque \"blockwise\" sort is also available (see README)")
parser.add_argument("--sort-regex"                ,       nargs="+", default=[], metavar="Regex", help="Regexes to apply to file names keys (like --replace) for purposes of sorting (EXPERIMENTAL)")
parser.add_argument("--no-headers"                , "-H", action="store_true"                   , help="Don't print match: or file: before lines")
parser.add_argument("--print-directories"         , "-d", action="store_true"                   , help="Print names of explored directories")
parser.add_argument("--print-file-names"          , "-n", action="store_true"                   , help="Print file names as well as matches")
parser.add_argument("--print-full-paths"          , "-p", action="store_true"                   , help="Print full file paths")
parser.add_argument("--print-posix-paths"         , "-P", action="store_true"                   , help="Replace \\ with / when printing file paths")
parser.add_argument("--dont-print-matches"        , "-N", action="store_true"                   , help="Don't print matches (use with --print-file-names to only print names)")
parser.add_argument("--print-match-offset"        , "-o", action="store_true"                   , help="Print where the match starts in the file as a hexadecimal number (ignores -H)")
parser.add_argument("--print-match-range"         , "-O", action="store_true"                   , help="Print where the match starts and ends in the file as a hexadecimal number (implies -o)")

parser.add_argument("--replace"                   , "-r", nargs="+", default=[], metavar="Regex", help="Regex replacement")
parser.add_argument("--sub"                       , "-R", nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="re.sub argument pairs after --replace is applied (todo: explain advanced usage here)")
parser.add_argument("--name-sub"                  ,       nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="--sub but for printing file names. Regex group 0 is before --print-full-paths and --print-posix-paths, group 1 is after")
parser.add_argument("--dir-name-sub"              ,       nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="--name-sub but for directory names")
parser.add_argument("--escape"                    , "-e", action="store_true"                   , help="Escape back slashes, newlines, carriage returns, and non-printable characters")

parser.add_argument("--count"                     , "-c", nargs="+", default=[]                  , action=CountAction , help="Count match/file/dir per file, dir, and/or total (Ex: --count fm dir-files)")
parser.add_argument("--limit"                     , "-l", nargs="+", default=JSObj({}, default=0), action=LimitAction , help="Limit match/file/dir per file, dir, and/or total (Ex: --limit filematch=1 total_dirs=5)")
parser.add_argument("--print-run-data"            ,                                                action="store_true", help="Print raw runData JSON")

parser.add_argument("--depth-first"               ,       action="store_true"                      , help="Enter subdirectories before processing files")
parser.add_argument("--glob-root-dir"             ,                                                  help="Root dir to run globs in (JANK)")

parser.add_argument("--match-whole-lines"         ,       action="store_true"                      , help="Match whole lines like FINDSTR")
parser.add_argument("--print-non-matching-files"  ,       action="store_true"                      , help="Print file names with no matches (Partially broken)")
#parser.add_argument("--json"                      , "-j", action="store_true"                      , help="Print output as JSON")
parser.add_argument("--no-warn"                   ,       action="store_true"                      , help="Don't print warning messages")
parser.add_argument("--weave-matches"             , "-w", action="store_true"                      , help="Weave regex matchdes (print first results for each get regex, then second results, etc.)")
parser.add_argument("--strict-weave"              , "-W", action="store_true"                      , help="Only print full weave sets")

parser.add_argument("--order"                     ,       nargs="+", default=DEFAULTORDER          , help="The order in which modifications to matches are applied (see README)")

parser.add_argument("--verbose"                   , "-v", action="store_true"                      , help="Verbose info")
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

if not (len(parsedArgs.replace)==0 or len(parsedArgs.replace)==1 or len(parsedArgs.replace)==len(parsedArgs.regex)):
	warn("Error: Length of --replace must be either 1 or equal to the number of regexes")
	exit(1)

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

doneDir=False
def _iterdir(dirname, dir_fd, dironly):
	"""
		A modified version of glob._iterdir for the sake of both customization and optimization
	"""
	global doneDir
	files=[]
	directories=[]
	try:
		fd = None
		fsencode = None
		if dirname=="":
			dirRegexResult=True
		else:
			dirRegexResult=regexCheckerThing(
				dirname,
				parsedArgs.dir_name_regex,
				parsedArgs.dir_name_anti_regex,
				os.path.realpath(dirname),
				parsedArgs.dir_full_name_regex,
				parsedArgs.dir_full_name_anti_regex,
				parsedArgs.dir_name_ignore_regex,
				parsedArgs.dir_full_name_ignore_regex
			)
		if dirRegexResult is True:
			runData["total"]["passedDirs"]+=1
		elif dirRegexResult is False:
			runData["total"]["failedDirs"]+=1
			return
		elif dirRegexResult is None:
			return
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
								directories.append(entry.name)
							else:
								if fsencode is not None:
									files.append(fsencode(entry.name))
								else:
									files.append(entry.name)
					except OSError:
						pass
				# Yirld files and folders in the right order
				if parsedArgs.depth_first:
					yield from directories
					for file in files:
						yield file
						if doneDir:
							# Optimization for --limit total-dirs
							doneDir=False
							break
				else:
					for file in files:
						yield file
						if doneDir:
							doneDir=False
							break
					yield from directories
		finally:
			if fd is not None:
				os.close(fd)
	except OSError:
		return
glob._iterdir=_iterdir

def _glob1(dirname, pattern, dir_fd, dironly):
	names = _iterdir(dirname, dir_fd, dironly)
	if not glob._ishidden(pattern):
		names = (x for x in names if not glob._ishidden(x))
	for name in names:
		if fnmatch.fnmatch(name, pattern):
			verbose(f"Yielding \"{name}\"")
			yield name
glob._glob1=_glob1

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
}

def handleCount(rules, runData):
	"""
		A jank function that handles --count stuff
	"""
	categories   ={"t":"total", "d":"dir",  "f":"file"                }
	subCategories={             "d":"dirs", "f":"files", "m":"matches"}
	modes        ={"f":"failed", "p":"passed"}
	values       ={"c":"count", "p":"percent", "":"count"}
	subModes     ={"t":"Total", "r":"PerRegex"}

	def sum2(*args, zero=0):
		ret=zero
		for x in args:
			if isinstance(args, list):
				ret+=sum(x)
			else:
				ret+=x
		return ret

	def handleTot(key):
		category   =categories[key[0]]
		subcategory=subCategories[key[1]]
		count      =runData[category][f"total{subcategory.title()}"]
		print(f"{category} {subcategory} count:"*_header+f"{count}")

	def handleReg(key):
		category   =categories[key[0]]
		subcategory=subCategories[key[1]]
		for regexIndex, count in enumerate(runData[category][subcategory+"PerRegex"]):
			print(f"{category.title()} {subcategory.lower()} count (R{regexIndex}): "*_header+f"{count}")

	def handleFilteredTot(key):
		category   =categories[key[0]]
		subcategory=subCategories[key[1]]
		mode       =modes[key[2]]
		kind       =values[key[3]]
		val=sum2(runData[category][mode+subcategory.title()])
		if kind=="percent":
			val/=sum2(runData[category]["passed"+subcategory.title()])+sum2(runData[category]["failed"+subcategory.title()])
			val=f"{val:0.05f}"
		print(f"{category.title()} {subcategory} {mode} {kind}: "*_header+f"{val}")

	def handleFilteredReg(key):
		category   =categories[key[0]]
		subcategory=subCategories[key[1]]
		mode       =modes[key[2]]
		kind       =values[key[3]]
		vals=runData[category][mode+subcategory.title()]
		for index, val in enumerate(vals):
			if kind=="percent":
				val/=runData[category]["passed"+subcategory.title()][index]+runData[category]["failed"+subcategory.title()][index]
				val=f"{val:0.05f}"
			print(f"{category.title()} {subcategory} {mode} {kind} (R{regexIndex}): "*_header+f"{val}")

	if "file" in rules:
		if parsedArgs.print_run_data:
			fileRunData=runData["file"].copy()
			fileRunData.pop("matches")
			print(json.dumps(fileRunData))
		for key in parsedArgs.count:
			if key=="fmt?":
				handleTot(key)
			if key=="fmr":
				handleReg(key)

	if "dir" in rules:
		for key in parsedArgs.count:
			if parsedArgs.print_run_data:
				print(json.dumps(runData["dir"]))
			if re.search(r"^d[fm]t?$", key):
				handleTot(key)
			if re.search(r"^d[fm]r$", key):
				handleTot(key)
			if re.search(r"^d[dfm][pf][cp]t?$", key):
				handleFilteredTot(key)
			if re.search(r"^d[dfm][pf][cp]r$", key):
				handleFilteredReg(key)

	if "total" in rules:
		if parsedArgs.print_run_data:
			print(json.dumps(runData["total"]))
		for key in parsedArgs.count:
			if re.search(r"^t[dfm][pf][cp]t?$", key):
				handleFilteredTot(key)
			if re.search(r"^t[dfm][pf][cp]r$", key):
				handleFilteredReg(key)

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

	if key in ["name", "blockwise", "rname", "rblockwise"] and parsedArgs.sort_regex:
		for pattern, replace in zip(parsedArgs.sort_regex[0::2], parsedArgs.sort_regex[1::2]):
			files=map(lambda x: {"orig":x, "name":re.sub(pattern, replace, x["name"])}, files)

	return map(lambda x:x["orig"] if "orig" in x else x, sorted(files, key=sorts[key]))

	#return sorted(files, key=sorts[key])

def fileContentsDontMatter():
	return parsedArgs.dont_print_matches and\
	       not any(parsedArgs.regex) and\
	       not parsedArgs.file_regex and not parsedArgs.file_anti_regex and\
	       not any(map(lambda x:re.search(r"[tdf]m", x), parsedArgs.limit.keys())) and\
	       not any(map(lambda x:re.search(r"^[tdf]m(([pf]c)?[tr])?$", x), parsedArgs.count))

def getFiles():
	"""
		Yields files selected with --file and --glob as {"file":filename, "data":mmapFile/bytes}
		Stdin has a filename of -
		Empty files and stdin use a bytes object instead of mmap
		If the contents of a file are irrelevant, b"" is always used instead of mmap
	"""
	def advancedGlob(pattern, recursive=False):
		"""
			A simple wrapper for glob.iglob that allows for using *:/ and ?:/ in glob patterns
			May cause issues with stuff like SD to USB adapters with no media inserted. I can't test that right now
		"""
		if re.match(r"^[*?]:", pattern):
			for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
				yield from glob.iglob(letter+pattern[1:], recursive=recursive)
		else:
			yield from glob.iglob(pattern, recursive=recursive)

	def _getFiles():
		"""
			Get a raw list of files selected with --file and --glob
			This is just here so I don't have to write the mmap code twice
			Probably could replace the array addition with a few `yield from`s
		"""

		# Files
		verbose("Yielding STDIN files")
		# --stdin-files
		if not os.isatty(sys.stdin.fileno()) and parsedArgs.stdin_files:
			yield from sys.stdin.read().splitlines()
		# --file

		verbose("Yielding files")
		yield from parsedArgs.file

		# Globs
		verbose("Yielding STDIN globs")
		# --stdin-globs
		if not os.isatty(sys.stdin.fileno()) and parsedArgs.stdin_globs:
			for pattern in sys.stdin.read().splitlines():
				yield from advancedGlob(pattern, recursive=True)
		# --glob
		verbose("Yielding globs")
		for pattern in parsedArgs.glob:
			yield from advancedGlob(pattern, recursive=True)

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
				except OSError as AAAAA:
					warn(f"Cannot process \"{file}\" because of \"{AAAAA}\"")
		else:
			verbose(f"\"{file}\" is a directory")
			yield {"name": file, "isDir": True, "stdin": False}

def processFileName(fname):
	fname=_funcSub(parsedArgs.name_sub, fname.encode(), 0)
	if parsedArgs.print_full_paths : fname=os.path.realpath(fname)
	if parsedArgs.print_posix_paths: fname=fname.replace(b"\\", b"/")
	fname=_funcSub(parsedArgs.name_sub, fname, 1)
	return fname

def processDirName(dname):
	dname=_funcSub(parsedArgs.dir_name_sub, dname.encode(), 0)
	dname=dname or b"."
	if parsedArgs.print_full_paths : dname=os.path.realpath(dname)
	if parsedArgs.print_posix_paths: dname=dname.replace(b"\\", b"/")
	dname=_funcSub(parsedArgs.dir_name_sub, dname, 1)
	return dname

def escape(match):
	"""
		Handle --escape
	"""
	if parsedArgs.escape:
		ret=match.replace(b"\\", b"\\\\").replace(b"\r", b"\\r").replace(b"\n", b"\\n")
		ret=re.sub(rb"[\x00-\x1f\x80-\xff]", lambda x:(f"\\x{ord(x[0]):02x}".encode()), ret)
		return ret
	return match

def printMatch(match, regexIndex):
	"""
		Print matches
	"""
	if match==None:
		return
	sys.stdout.buffer.write(ofmt["match"].format(range=match.span(), regexIndex=regexIndex).encode())
	sys.stdout.buffer.write(escape(match[0]))
	sys.stdout.buffer.write(b"\n")
	sys.stdout.buffer.flush()

# Abbreviations to make the code slightly cleaner
_FML=parsedArgs.limit["fmp"]
_DML=parsedArgs.limit["dmp"]
_TML=parsedArgs.limit["tmp"]
_DFL=parsedArgs.limit["dfp"]
_TFL=parsedArgs.limit["tfp"]
_TDL=parsedArgs.limit["tdp"]

# Tracking stuffs
currDir=None
lastDir=None

runData={
	"file": {
		"printedName":False,
		"totalMatches":0,
		"matchesPerRegex":[],
		"matches":[],
		"passedMatches":[],
		"failedMatches":[],
	},
	"dir":{
		"printedName":False,
		"totalFiles":0,
		"totalMatches":0,
		"filesPerRegex":[],
		"matchesPerRegex":[],
		"passedMatches":[],
		"failedMatches":[],
		"passedFiles":0,
		"failedFiles":0,
	},
	"total":{
		"totalDirs":0,
		"totalFiles":0,
		"totalMatches":0,
		"dirsPerRegex":[],
		"filesPerRegex":[],
		"matchesPerRegex":[],
		"passedMatches":[],
		"failedMatches":[],
		"passedFiles":0,
		"failedFiles":0,
		"passedDirs":0,
		"failedDirs":0,
	},
	"matchedStrings":[]  # --no-duplicates handler
}

runData["total"]["matchesPerRegex"]=[0 for x in parsedArgs.regex]
runData["total"]["filesPerRegex"  ]=[0 for x in parsedArgs.regex]
runData["total"]["dirsPerRegex"   ]=[0 for x in parsedArgs.regex]
runData["total"]["passedMatches"  ]=[0 for x in parsedArgs.regex]
runData["total"]["failedMatches"  ]=[0 for x in parsedArgs.regex]

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

def _funcSub(subRules, match, regexIndex, **kwargs):
	"""
		Handle --sub, --name-sub, and --dir-name-sub
		TYSM mCoding for explaining how zip works
		(zip(*arr) is a bit like transposing arr (arr[y][x] becomes arr[x][y]))
	"""

	if subRules:
		replaceData=subRules[regexIndex%len(subRules)]
		for group in replaceData:
			if regexCheckerThing(match, group["tests"], group["antiTests"]):
				for pattern, repl in zip(group["patterns"], group["repls"]):
					match=re.sub(pattern, repl, match)
	return match

def funcSub(parsedArgs, match, regexIndex, **kwargs):
	"""
		Handle --sub
	"""
	return JSObj({
		**match,
		0:_funcSub(parsedArgs.sub, match[0], regexIndex, **kwargs)
	})

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

class NextFile(Exception):
	"""
		Raised by funcMatchRegex and funcNoDuplicates when a match failes the match regex stuff
	"""
	pass

def funcMatchRegex(parsedArgs, match, regexIndex, **kwargs):
	"""
		Handle --match-regex and --match-anti-regex
	"""
	matchRegexResult=regexCheckerThing(
		match[0],
		              parsedArgs.match_regex       [regexIndex] if parsedArgs.match_regex        else [],
		              parsedArgs.match_anti_regex  [regexIndex] if parsedArgs.match_anti_regex   else [],
		partialIgnore=parsedArgs.match_ignore_regex[regexIndex] if parsedArgs.match_ignore_regex else [],
	)
	if matchRegexResult is False:
		runData["total"]["failedMatches"][regexIndex]+=1
		runData["dir"  ]["failedMatches"][regexIndex]+=1
		runData["file" ]["failedMatches"][regexIndex]+=1
		raise NextFile()
	elif matchRegexResult is None:
		raise NextFile()

def funcPrintDir(parsedArgs, runData, currDir, **kwargs):
	"""
		Handle --print-directories
	"""
	if parsedArgs.print_directories and not runData["dir"]["printedName"]:
		sys.stdout.buffer.write(b"Directory: "+processDirName(currDir)+b"\n")
		sys.stdout.buffer.flush()
		runData["dir"]["printedName"]=True

def funcPrintName(parsedArgs, file, runData, **kwargs):
	"""
		Print file name
	"""
	if parsedArgs.print_file_names and not runData["file"]["printedName"]:
		sys.stdout.buffer.write(b"File: "+processFileName(file["name"])+b"\n")
		sys.stdout.buffer.flush()
	runData["file"]["printedName"]=True

def funcPrintMatches(parsedArgs, file, regexIndex, match, **kwargs):
	"""
		Handle file name printing
	"""
	if not parsedArgs.dont_print_matches:
		if parsedArgs.weave_matches:
			runData["file"]["matches"][regexIndex].append(match)
		else:
			printMatch(match, regexIndex)

def funcNoDuplicates(parsedArgs, match, **kwargs):
	"""
		Handle --no-duplicates
	"""
	if match[0] in runData["matchedStrings"]:
		raise NextFile()
	if parsedArgs.no_duplicates:
		runData["matchedStrings"].append(match[0])

def funcPrintFailedFile(parsedArgs, file, runData):
	funcPrintName(parsedArgs, file, runData)

funcs={
	"print-dir"        : funcPrintDir,
	"replace"          : funcReplace,
	"sub"              : funcSub,
	"match-whole-lines": funcMatchWholeLines,
	"match-regex"      : funcMatchRegex,
	"print-name"       : funcPrintName,
	"print-matches"    : funcPrintMatches,
	"no-duplicates"    : funcNoDuplicates
}

for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
	verbose(f"Processing \"{file['name']}\"")
	if file["isDir"]:
		verbose(f"\"{file['name']}\" is a directory; Continuing")
		continue

	runData["file"]["passed"         ]=True
	runData["file"]["printedName"    ]=False
	runData["file"]["matchesPerRegex"]=[0 for x in parsedArgs.regex]
	runData["file"]["totalMatches"   ]=0
	runData["file"]["passedMatches"  ]=[0 for x in parsedArgs.regex]
	runData["file"]["failedMatches"  ]=[0 for x in parsedArgs.regex]

	# --file-limit, --dir-match-limit, --dir-file-count, and --dir-match-count
	lastDir=currDir
	currDir=os.path.dirname(file["name"])

	# Handle new directories
	if lastDir!=currDir:
		if runData["dir"]["passedFiles"]:
			# Print data from last dir (--count)
			if lastDir is not None:
				verbose("Just exited a directory; Printing runData...")
				handleCount(rules=["dir"], runData=runData)
			# Handle --limit total-dir
			if _TDL and runData["total"]["totalDirs"]>=_TDL:
				verbose("Total directory limit reached; Exiting...")
				break
		# Initialize relevant runData
		runData["dir"  ]["printedName"    ] =False
		runData["total"]["totalDirs"      ]+=1
		runData["dir"  ]["totalFiles"     ] =0
		runData["dir"  ]["matchesPerRegex"] =[0 for x in parsedArgs.regex]
		runData["dir"  ]["filesPerRegex"  ] =[0 for x in parsedArgs.regex]
		runData["dir"  ]["totalMatches"   ] =0
		runData["dir"  ]["failedFiles"    ] =0
		runData["dir"  ]["passedFiles"    ] =0
		runData["dir"  ]["passedMatches"  ] =[0 for x in parsedArgs.regex]
		runData["dir"  ]["failedMatches"  ] =[0 for x in parsedArgs.regex]

	# Handle name fail regexes
	# It has to be done here to make sure runData["dir"] doesn't miss stuff
	# Handle --name-regex stuff
	nameRegexResult=filenameChecker(file["name"])
	if nameRegexResult is False:
		verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched a fail regex; Continuing...")
		runData["dir"  ]["failedFiles"]+=1
		runData["total"]["failedFiles"]+=1
		runData["file" ]["passed"     ]=False
	elif nameRegexResult is None:
		verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched an ignore regex; Continuing...")
		runData["file"]["passed"]=False

	fileRegexResult=regexCheckerThing(
		file["data"],
		parsedArgs.file_regex,
		parsedArgs.file_anti_regex,
		partialIgnore=parsedArgs.file_ignore_regex
	)
	if fileRegexResult is False:
		verbose(f"Contents of file \"{file['name']}\" (\"{os.path.realpath(file['name'])}\") matched a fail regex; Continuing...")
		runData["dir"  ]["failedFiles"]+=1
		runData["total"]["failedFiles"]+=1
		runData["file" ]["passed"     ]=False
	elif fileRegexResult is None:
		verbose(f"Contents of file \"{file['name']}\" (\"{os.path.realpath(file['name'])}\") matched an ignore regex; Continuing...")
		runData["file"]["passed"]=False

	# Main matching stuff
	matchIndex=0 # Just makes stuff easier
	matchedAny=False

	if runData["file"]["passed"]:
		# Handle printing file and dir names when there's no regexes
		if not parsedArgs.regex:
			for func in parsedArgs.order:
				if func=="print-name":
					funcs["print-name"](parsedArgs, file, runData)
					runData["dir"  ]["passedFiles" ]+=1
					runData["total"]["passedFiles" ]+=1
					runData["total"]["totalFiles"  ]+=1
					runData["dir"  ]["totalFiles"  ]+=1
				elif func=="print-dir":
					funcs["print-dir"](parsedArgs, runData, currDir)

		for regexIndex, regex in enumerate(parsedArgs.regex):
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

					for func in parsedArgs.order:
						try:
							match=funcs[func](
								regexIndex=regexIndex,
								regex=regex,
								file=file,
								runData=runData,
								parsedArgs=parsedArgs,
								match=match,
								currDir=currDir
							) or match
						except NextFile:
							break
					else:
						runData["total"]["passedMatches"][regexIndex]+=1
						runData["dir"  ]["passedMatches"][regexIndex]+=1

					# Handle --match-limit, --dir-match-limit, and --total-match-limit
					if (_FML and matchIndex                      >=_FML) or\
					   (_DML and runData["dir"  ]["totalMatches"]>=_DML) or\
					   (_TML and runData["total"]["totalMatches"]>=_TML):
						break

			except Exception as AAAAA:
				warn(f"Cannot process \"{file}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}")

	if parsedArgs.print_non_matching_files and not runData["file"]["passed"]:
		verbose(f"\"{file['name']}\" didn't match any file regexes, but --print-non-matching-files was specified")
		funcPrintFailedFile(parsedArgs, file, runData)

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
	if _TFL!=0 and runData["total"]["totalFiles"]>=_TFL:
		verbose("Total file limit reached; Exiting")
		break

	# Handle --limit dir-files and dir-matches
	# Really slow on big directories
	# Might eventually have this hook into _iterdir using a global flag or something
	if (_DFL!=0 and runData["dir"]["totalFiles"]>=_DFL) or (_DML!=0 and runData["dir"]["totalMatches"]>=_DML):
		verbose("Dir limit(s) reached")
		doneDir=True

# --count dir-*
if currDir is not None and runData["total"]["totalDirs"]:
	# Only runs if files were handled in two or more directories
	handleCount(rules=["dir"], runData=runData)

# --count total-*
handleCount(rules=["total"], runData=runData)
