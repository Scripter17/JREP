import argparse, os, sys, re, glob, mmap, copy, itertools, functools, sre_parse, inspect, json, shutil, fnmatch

"""
	JREP
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

DEFAULTORDER=["replace", "match-whole-lines", "sub", "match-regex", "no-name-duplicates", "no-duplicates", "print-dir", "print-name", "print-matches"]

_STDIN=b""
if not os.isatty(sys.stdin.fileno()):
	_STDIN=sys.stdin.buffer.read()

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
	# Helper function for generating the --limiy/--count parser regex
	return "(?:"+"|".join([f"({opt[0]})(?:{opt[1:]})?" for opt in opts])+")"
_LCNameRegex=_LCNameRegexPart(r"files?"       , r"dir(?:ectori(?:es|y))?", r"total"                             )    +r"[-_]?"+\
             _LCNameRegexPart(r"match(?:e?s)?", r"files?"                , r"dir(?:ectori(?:es|y))?"            )    +r"[-_]?"+\
             _LCNameRegexPart(r"total"        , r"fail(?:u(?:re)?s?|d)"  , r"pass(?:e?[sd])?"       , "handled?")+"?"+r"[-_]?"+\
             _LCNameRegexPart(r"counts?"      , r"percent(?:age)?s?"                                            )+"?"+r"[-_]?"+\
             _LCNameRegexPart(r"regex"        , r"total"                                                        )+"?"
_LCNameRegex=f"^{_LCNameRegex}$"

def parseLCName(name):
	"""
		Normalize all ways --limit or --count targets can be written
	"""
	ret=name
	match=re.match(_LCNameRegex, name, re.I)
	if match:
		ret="".join(filter(lambda x:x, match.groups())).lower()
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

class CustomArgumentParser(argparse.ArgumentParser):
	def add_line(self, text=""):
		self._actions[-1].help+="\n"+text

class CustomHelpFormatter(argparse.HelpFormatter):
	def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
		argparse.HelpFormatter.__init__(self, prog, indent_increment, shutil.get_terminal_size().columns//2, width)
	def _split_lines(self, text, width):
		lines = super()._split_lines(text, width)
		if "\n" in text:
			lines += text.split("\n")[1:]
			text = text.split("\n")[0]
		return lines

_extendedHelp={
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

	"blockwise":"""Blockwise sorting:
	A generic sort function will think "file10.jpg" comes before "file2.jpg"
	Windows, on the other hand, has code that treats the number part as a number
	Blockwise sort mimics this behaviour by
	1. Splitting filenames into groups of number and non-number characters. Ex. `abc123def456.jpg` -> `["abc", "123", "def", "456", ".jpg"]`
	2. When comparing 2 filenames, compare the first element ("block") of both name's lists according to the following two rules:
	\ta. If either block is made of non-number characters, compare the two blocks as strings
	\tb. If both blocks are numbers, compare them as numbers

	The end result is that file2.jpg is correctly placed before file10.jpg""",

	"order":f"""`--order` usage:
	`--order` determines the order of functions that process matches
	- The default value for `--order` is {', '.join(DEFAULTORDER)}
	- Changing the order of `sub`, `replace`, and `match-whole-lines` will mostly "work" but the output will make next to no sense
	- The main purpose of this is to move `match-regex` and `no-duplicates` to earlier in the chain"""
}
for topic in _extendedHelp:
	if "JREP_MARKDOWN" in os.environ:
		_extendedHelp[topic]="## (`"+topic+"`) "+_extendedHelp[topic].replace("\n", "  \n").replace(":  ", "").replace("\n\t", "\n")
		_extendedHelp[topic]=re.sub(r"(?<=\n\t)([a-z])(?=\.)", lambda x:str("ABCDEFGHIJKLMNOPQRSTUVWXYZ".index(x[0].upper())+1), _extendedHelp[topic])
	else:
		_extendedHelp[topic]=_extendedHelp[topic].replace("`", "").replace("\t", "  ")

class CustomHelpAction(argparse._HelpAction):
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

parser=CustomArgumentParser(formatter_class=CustomHelpFormatter, add_help=False)
parser.add_argument("--help", "-h", action=CustomHelpAction, nargs="?", default=argparse.SUPPRESS, help="show this help message and exit OR use `--help [topic]` for help with [topic]")

parser.add_argument("regex"                       ,       nargs="*", default=[], metavar="Regex", help="Regex(es) to process matches for (reffered to as \"get regexes\")")
parser.add_argument("--string"                    , "-s", action="store_true"                   , help="Treat get regexes as strings. Doesn't apply to any other options.")
parser.add_argument("--enhanced-engine"           , "-E", action="store_true"                   , help="Use alternate regex engine from https://pypi.org/project/regex/")

parser.add_argument("--file"                      , "-f", nargs="+", default=[]                 , help="A list of files to check")
parser.add_argument("--glob"                      , "-g", nargs="+", default=[]                 , help="A list of globs to check")

_stdin=parser.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"               , "-F", action="store_true"                   , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"               , "-G", action="store_true"                   , help="Treat STDIN as a list of globs")
_stdin.add_argument("--stdin-anti-match-strings"  ,       action="store_true"                   , help="Treat STDIN as a list of strings to not match")
#_stdin.add_argument("--stdin-option"              ,                                               help="Append STDIN lines to the end of any option (drop the -- at the start)")

parser.add_line()
parser.add_line()

parser.add_argument("--name-regex"                , "-t", nargs="+", default=[], metavar="Regex", help="If a file name matches all supplied regexes, keep going. Otherwise continue")
parser.add_argument("--name-anti-regex"           , "-T", nargs="+", default=[], metavar="Regex", help="Like --name-regex but excludes file names that match any of the supplied regexes")
parser.add_argument("--name-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", help="Like --name-anti-regex but doesn't contribute to --count *-failed-files")
parser.add_argument("--full-name-regex"           ,       nargs="+", default=[], metavar="Regex", help="Like --name-regex but for absolute file paths (C:/xyz instead of xyz)")
parser.add_argument("--full-name-anti-regex"      ,       nargs="+", default=[], metavar="Regex", help="Like --name-anti-regex but applied to full file paths")
parser.add_argument("--full-name-ignore-regex"    ,       nargs="+", default=[], metavar="Regex", help="Like --full-name-anti-regex but doesn't contribute to --count *-failed-files")

parser.add_argument("--name-glob"                 ,       nargs="+", default=[], metavar="Glob" , help="If a file name matches all supplied globs, keep going. Otherwise continue")
parser.add_argument("--name-anti-glob"            ,       nargs="+", default=[], metavar="Glob" , help="Like --name-glob but excludes file names that match any of the supplied globs")
parser.add_argument("--name-ignore-glob"          ,       nargs="+", default=[], metavar="Glob" , help="Like --name-anti-glob but doesn't contribute to --count *-failed-files")
parser.add_argument("--full-name-glob"            ,       nargs="+", default=[], metavar="Glob" , help="Like --name-glob but for absolute file paths (C:/xyz instead of xyz)")
parser.add_argument("--full-name-anti-glob"       ,       nargs="+", default=[], metavar="Glob" , help="Like --name-anti-glob but applied to full file paths")
parser.add_argument("--full-name-ignore-glob"     ,       nargs="+", default=[], metavar="Glob" , help="Like --full-name-anti-glob but doesn't contribute to --count *-failed-files")

parser.add_argument("--dir-name-regex"            ,       nargs="+", default=[], metavar="Regex", help="If a directory name matches all supplied regexes, enter it. Otherwise continue")
parser.add_argument("--dir-name-anti-regex"       ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-regex but excludes directories that match any of the supplied regexes")
parser.add_argument("--dir-name-ignore-regex"     ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-anti-regex but doesn't contribute to --count total-failed-dirs")
parser.add_argument("--dir-full-name-regex"       ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-regex but for absolute directory paths (C:/xyz instead of xyz)")
parser.add_argument("--dir-full-name-anti-regex"  ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-anti-regex but applied to full directory paths")
parser.add_argument("--dir-full-name-ignore-regex",       nargs="+", default=[], metavar="Regex", help="Like --dir-full-name-anti-regex but doesn't contribute to --count total-failed-dirs")

parser.add_argument("--file-regex"                ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Regexes to test file contents for")
parser.add_argument("--file-anti-regex"           ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Like --file-regex but excludes files that match of the supplied regexes")
parser.add_argument("--file-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Like --file-anti-regex but doesn't contribute to --count *-failed-files")

parser.add_argument("--match-regex"               ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Groups are split along lone *. Matches from the Nth get regex are tested with the Nth group")
parser.add_argument("--match-anti-regex"          ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Like --match-regex but excludes matches that match any of the supplied regexes")
parser.add_argument("--match-ignore-regex"        ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Like --match-anti-regex but doesn't contribute to --count *-failed-matches")

parser.add_line()
parser.add_line()

parser.add_argument("--no-duplicates"             , "-D", action="store_true"                   , help="Don't print duplicate matches (See also: --order)")
parser.add_argument("--no-name-duplicates"        ,       action="store_true"                   , help="Don't process files whose names have already been processed (takes --name-sub, --print-full-paths and --print-posix-paths)")

parser.add_argument("--sort"                      , "-S",                                         help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse. A windows-esque \"blockwise\" sort is also available. Run jrep --help blockwise for more info")
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
parser.add_argument("--sub"                       , "-R", nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="re.sub argument pairs after --replace is applied. Run jrep.py --help sub for more info")
parser.add_argument("--name-sub"                  ,       nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="Applies --sub to file names. A lone * separates subsitutions for y/z and C:/x/y/z")
parser.add_argument("--dir-name-sub"              ,       nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="--name-sub but for directory names")
parser.add_argument("--escape"                    , "-e", action="store_true"                   , help="Escape back slashes, newlines, carriage returns, and non-printable characters")

parser.add_argument("--count"                     , "-c", nargs="+", default=[]                  , action=CountAction , help="Count match/file/dir per file, dir, and/or total (Ex: --count fm dir-files)")
parser.add_argument("--limit"                     , "-l", nargs="+", default=JSObj({}, default=0), action=LimitAction , help="Limit match/file/dir per file, dir, and/or total (Ex: --limit filematch=1 total_dirs=5)")

parser.add_argument("--depth-first"               ,       action="store_true"                      , help="Enter subdirectories before processing files")
parser.add_argument("--glob-root-dir"             ,                                                  help="Root dir to run globs in (JANK)")

parser.add_argument("--match-whole-lines"         ,       action="store_true"                      , help="Match whole lines like FINDSTR")
parser.add_argument("--print-non-matching-files"  ,       action="store_true"                      , help="Print file names with no matches (Partially broken)")
#parser.add_argument("--json"                      , "-j", action="store_true"                      , help="Print output as JSON")
parser.add_argument("--no-warn"                   ,       action="store_true"                      , help="Don't print warning messages")
parser.add_argument("--hard-warn"                 ,       action="store_true"                      , help="Throw errors instead of warnings")
parser.add_argument("--weave-matches"             , "-w", action="store_true"                      , help="Weave regex matchdes (print first results for each get regex, then second results, etc.)")
parser.add_argument("--strict-weave"              , "-W", action="store_true"                      , help="Only print full weave sets")

parser.add_argument("--order"                     ,       nargs="+", default=DEFAULTORDER          , help="The order in which modifications to matches are applied. Run jrep --help order for more info")

parser.add_argument("--verbose"                   , "-v", action="store_true"                      , help="Verbose info")
parser.add_argument("--print-rundata"             , "--print-run-data", action="store_true"        , help="Print raw runData JSON at the end (used for debugging)")
parsedArgs=parser.parse_args()

# TODO: Logging module
def verbose(x):
	if parsedArgs.verbose:
		caller=inspect.stack()[1]
		print(f"Verbose on line {caller[2]} in function {caller[3]}: {x}")
def warn(x, error=None):
	if not parsedArgs.no_warn:
		#caller=inspect.stack()[1]
		#print(f"Waring on line {caller[2]} in function {caller[3]}: {x}", file=sys.stderr)
		if parsedArgs.hard_warn:
			raise error or Exception(f"No error provided (Message: \"{x}\")")
		else:
			calls=inspect.stack()[1:]
			print(f"Waring on lines {', '.join([str(call[2]) for call in calls])} in functions {', '.join([str(call[3]) for call in calls])} : {x}", file=sys.stderr)

verbose("JREP preview version")
verbose(parsedArgs)

# if parsedArgs.stdin_option_name:
# 	_optname=parsedArgs.stdin_option_name
# 	if not isinstance(parsedArgs.__getattribute__(_optname), list):
# 		warn("Error: Cannot appent STDIN lines to non=list option")
# 		exit(2)
# 	for x in parser._actions:
# 		print(x, dir(x))
# 	#object.__setattr__(parsedArgs, _optname, parsedArgs.__getattribute__(_optname)+_STDIN.decode().splitlines())

if parsedArgs.enhanced_engine:
	import regex as re

if not (len(parsedArgs.replace)==0 or len(parsedArgs.replace)==1 or len(parsedArgs.replace)==len(parsedArgs.regex)):
	warn("Error: Length of --replace must be either 1 or equal to the number of regexes")
	exit(1)

def regexCheckerThing(partial, partialPass, partialFail, full="", fullPass=[], fullFail=[], partialIgnore=[], fullIgnore=[]):
	"""
		True  = Passed
		False = Failed
		None  = Ignored
	"""
	if (partialIgnore and any(map(lambda x:re.search(x, partial), partialIgnore))) or\
	   (fullIgnore    and any(map(lambda x:re.search(x, full   ), fullIgnore   ))):
		return None
	if (partialFail and any(map(lambda x:re.search(x, partial), partialFail))) or\
	   (fullFail    and any(map(lambda x:re.search(x, full   ), fullFail   ))):
		return False
	if all(map(lambda x:re.search(x, partial), partialPass)) and\
	   all(map(lambda x:re.search(x, full   ), fullPass   )):
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

def filenameChecker(file):
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

def dirnameChecker(dirname):
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

doneDir=False
def _iterdir(dirname, dir_fd, dironly):
	"""
		A modified version of glob._iterdir for the sake of both customization and optimization
	"""
	files=[]
	directories=[]
	try:
		fd = None
		fsencode = None
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
					yield from files
				else:
					yield from files
					yield from directories
		finally:
			if fd is not None:
				os.close(fd)
	except OSError:
		return
glob._iterdir=_iterdir

def _glob1(dirname, pattern, dir_fd, dironly):
	global doneDir
	names = _iterdir(dirname, dir_fd, dironly)
	if not glob._ishidden(pattern):
		names = (x for x in names if not glob._ishidden(x))
	for name in names:
		if fnmatch.fnmatch(name, pattern):
			verbose(f"Yielding \"{name}\"")
			yield name
		if doneDir:
			doneDir=False
			break
glob._glob1=_glob1

def _rlistdir(dirname, dir_fd, dironly):
	global doneDir
	names = glob._listdir(dirname, dir_fd, dironly)
	for x in names:
		if not glob._ishidden(x):
			yield x
			path = glob._join(dirname, x) if dirname else x
			for y in _rlistdir(path, dir_fd, dironly):
				yield glob._join(x, y)
				if doneDir:
					doneDir=False
					break
glob._rlistdir=_rlistdir

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
		A hopefully less jank function that handles --count stuff
	"""
	cats      ={"t":"total" , "d":"dir"    , "f":"file"                 }
	subCats   ={"t":"dfm"   , "d":"fm"     , "f":"m"                    }
	catNames  ={"t":"total" , "d":"dir"    , "f":"file"  , "m":"match"  }
	catPlurals={"t":"totals", "d":"dirs"   , "f":"files" , "m":"matches"}
	filters   ={"p":"passed", "h":"handled", "f":"failed"               }

	def handleTotals(regexIndex, value):
		print(f"{keyCat.title()} {keySubCatPlural} (R{regexIndex}): "*_header+f"{value}")

	def handleFiltereds(regexIndex, key):
		if regexIndex=="*":
			filterCount=runData[keyCat][keySubCatFilter+keySubCat]
			divisor=runData[keyCat]['total'+keySubCat]
		else:
			filterCount=runData[keyCat][keySubCatFilter+keySubCat+"PerRegex"][regexIndex]
			divisor=runData[keyCat]['total'+keySubCat+"PerRegex"][regexIndex]

		if len(key)==3 or key[3] in "ctr":
			print(f"{keySubCatFilter.title()} {keyCat} {keySubCatPlural} (R{regexIndex}): "*_header+f"{filterCount}")
		elif key[3] in "p":
			print(f"{keySubCatFilter.title()} {keyCat} {keySubCatPlural} (R{regexIndex}): "*_header+f"{filterCount/divisor}")

	for rule in rules:
		for key in parsedArgs.count:
			if key[0] not in cats or cats[key[0]]!=rule: continue
			if key[1] not in subCats[key[0]]: continue

			keyCat         =cats[key[0]]
			keySubCatPlural=catPlurals[key[1]]
			keySubCat      =keySubCatPlural.title()

			# Get keySubCatFilter, default to "passed"
			if len(key)>=3 and key[2] in filters:
				keySubCatFilter=filters[key[2]]
			else:
				keySubCatFilter="passed"
			if len(key)<3:
				key+="p"

			if re.match(r"^..t?$", key):
				handleTotals("*", runData[keyCat][keySubCatFilter+keySubCat])
			elif re.match(r"^..r$", key):
				for regexIndex, value in enumerate(runData[keyCat][keySubCatFilter+keySubCat+"PerRegex"]):
					handleTotals(regexIndex, value)
			elif re.match(r"^..[phf][cp]?t?$", key):
				handleFiltereds("*", key)
			elif re.match(r"^..[phf][cp]?r$", key):
				for regexIndex, value in enumerate(runData[keyCat][keySubCatFilter+keySubCat+"PerRegex"]):
					handleFiltereds(regexIndex, key)

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
		if _STDIN and parsedArgs.stdin_files:
			yield from _STDIN.splitlines()
		# --file

		verbose("Yielding files")
		yield from parsedArgs.file

		# Globs
		verbose("Yielding STDIN globs")
		# --stdin-globs
		if not _STDIN and parsedArgs.stdin_globs:
			for pattern in _STDIN.splitlines():
				yield from advancedGlob(pattern, recursive=True)
		# --glob
		verbose("Yielding globs")
		for pattern in parsedArgs.glob:
			yield from advancedGlob(pattern, recursive=True)

	# Add stdin as a file
	if not os.isatty(sys.stdin.fileno()) and not parsedArgs.stdin_files and not parsedArgs.stdin_globs:
		verbose("Processing STDIN")
		yield {"name":"-", "basename":"-", "relDir":"", "absDir":"", "data":_STDIN, "isDir": False, "stdin": True}

	for file in _getFiles():
		verbose(f"Pre-processing \"{file}\"")

		if os.path.isfile(file):
			relDir, basename=os.path.dirname(file), os.path.basename(file)
			absDir=os.path.normpath(os.path.join(os.getcwd(), relDir))
			ret={"name": file, "basename":basename, "relDir":relDir, "absDir":absDir, "data": b"", "isDir": False, "stdin": False}
			if fileContentsDontMatter() or not filenameChecker(ret):
				# Does the file content matter? No? Ignore it then
				verbose("Optimizing away actually opening the file")
				yield ret
			else:
				try:
					with open(file, mode="r", buffering=65536) as f:
						# Stream data from file instead of loading a 48.2TB file into RAM
						try:
							mmapFile=mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
						except ValueError:
							mmapFile=b""
						ret["data"]=mmapFile
						yield ret
				except OSError as AAAAA:
					warn(f"Cannot process \"{file}\" because of \"{AAAAA}\"", error=AAAAA)
		else:
			verbose(f"\"{file}\" is a directory")
			yield {"name": file, "isDir": True, "stdin": False}

def processFileName(fname):
	fname=_funcSub(parsedArgs.name_sub, fname.encode(), 0, wrap=False)
	if parsedArgs.print_full_paths : fname=os.path.realpath(fname)
	if parsedArgs.print_posix_paths: fname=fname.replace(b"\\", b"/")
	fname=_funcSub(parsedArgs.name_sub, fname, 1, wrap=False)
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

# Tracking stuffs
runData={
	"file": {
		"printedName":False,

		"totalMatches" :0,
		"passedMatches":0,
		"failedMatches":0,
		"totalMatchesPerRegex" :[],
		"passedMatchesPerRegex":[],
		"failedMatchesPerRegex":[],
	},
	"dir":{
		"printedName":False,

		"totalFiles"  :0,
		"passedFiles" :0,
		"handledFiles":0,
		"failedFiles" :0,
		"totalFilesPerRegex"  :[],
		"passedFilesPerRegex" :[],
		"handledFilesPerRegex":[],
		#"failedFilesPerRegex" :[],

		"totalMatches" :0,
		"passedMatches":0,
		"failedMatches":0,
		"totalMatchesPerRegex" :[],
		"passedMatchesPerRegex":[],
		"failedMatchesPerRegex":[],
	},
	"total":{
		"totalDirs" :0,
		"passedDirs":0,
		"failedDirs":0,
		"dirsPerRegex":[],

		"totalFiles"  :0,
		"passedFiles" :0,
		"handledFiles":0,
		"failedFiles" :0,
		"totalFilesPerRegex"  :[],
		"passedFilesPerRegex" :[],
		"handledFilesPerRegex":[],
		#"failedFilesPerRegex" :[],

		"totalMatches" :0,
		"passedMatches":0,
		"failedMatches":0,
		"totalMatchesPerRegex" :[],
		"passedMatchesPerRegex":[],
		"failedMatchesPerRegex":[],
	},
	"matchedStrings":[],  # --no-duplicates handler
	"filenames":[],
	"currDir":None,
	"lastDir":None,
}

def checkLimits(sn):
	"""
		Given an LCName's "short name" (total-files -> tf),\
		check whether or not it's exceeded its value in --limit (if set)
	"""
	def getValue(sn):
		nameMap={"t":"total","d":"dir","f":"file","m":"match"}
		typeMap={"t":"total","p":"passed","f":"failed","h":"handled"}
		plural="e"*(sn[1]=="m")+"s"
		try:
			return runData[nameMap[sn[0]]][typeMap[sn[2]]+nameMap[sn[1]].title()+plural]
		except KeyError:
			return 0
	limit=parsedArgs.limit[sn]
	if limit==0 and sn[2]=="p":
		# Makes file-match an alias for file-match-passed
		limit=parsedArgs.limit[sn[:2]]
	value=getValue(sn)
	return bool(limit and value>=limit)

runData["total"]["totalMatchesPerRegex" ]=[0 for x in parsedArgs.regex]
runData["total"]["passedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
runData["total"]["failedMatchesPerRegex"]=[0 for x in parsedArgs.regex]

runData["total"]["totalFilesPerRegex"   ]=[0 for x in parsedArgs.regex]
runData["total"]["passedFilesPerRegex"  ]=[0 for x in parsedArgs.regex]
runData["total"]["handledFilesPerRegex" ]=[0 for x in parsedArgs.regex]
runData["total"]["dirsPerRegex"         ]=[0 for x in parsedArgs.regex]

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
			replaceData=subRules[regexIndex]
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
			0: file["data"][lineStart+1:match.span()[0]]+match[0]+file["data"][match.span()[1]:lineEnd]
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
	stdinThing=False
	if parsedArgs.stdin_anti_match_strings and _STDIN:
		stdinThing=match[0] in _STDIN.splitlines()
	matchRegexResult=not stdinThing and regexCheckerThing(
		match[0],
		              parsedArgs.match_regex       [regexIndex] if parsedArgs.match_regex        else [],
		              parsedArgs.match_anti_regex  [regexIndex] if parsedArgs.match_anti_regex   else [],
		partialIgnore=parsedArgs.match_ignore_regex[regexIndex] if parsedArgs.match_ignore_regex else [],
	)
	if matchRegexResult is False:
		runData["total"]["failedMatches"        ]            +=1
		runData["dir"  ]["failedMatches"        ]            +=1
		runData["file" ]["failedMatches"        ]            +=1
		runData["total"]["failedMatchesPerRegex"][regexIndex]+=1
		runData["dir"  ]["failedMatchesPerRegex"][regexIndex]+=1
		runData["file" ]["failedMatchesPerRegex"][regexIndex]+=1
		raise NextFile()
	elif matchRegexResult is None:
		raise NextFile()

def funcPrintDir(parsedArgs, runData, currDir, **kwargs):
	"""
		Handle --print-directories
	"""
	if parsedArgs.print_directories and not runData["dir"]["printedName"]:
		sys.stdout.buffer.write(b"Directory: "*_header+processDirName(runData["currDir"])+b"\n")
		sys.stdout.buffer.flush()
		runData["dir"]["printedName"]=True

def funcPrintName(parsedArgs, file, runData, **kwargs):
	"""
		Print file name
	"""
	if parsedArgs.print_file_names and not runData["file"]["printedName"]:
		sys.stdout.buffer.write(b"File: "*_header+processFileName(file["name"]))
		sys.stdout.buffer.write(b"\n")
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

def funcNoNameDuplicates(parsedArgs, file, **kwargs):
	"""
		Handle --no-duplicates
	"""
	if processFileName(file["name"]) in runData["filenames"]:
		raise NextFile()
	if parsedArgs.no_name_duplicates:
		runData["filenames"].append(processFileName(file["name"]))

def funcPrintFailedFile(parsedArgs, file, runData):
	"""
		Print filename of failed file if --print-non-matching-files is specified
	"""
	funcPrintName(parsedArgs, file, runData)

funcs={
	"print-dir"         : funcPrintDir,
	"replace"           : funcReplace,
	"sub"               : funcSub,
	"match-whole-lines" : funcMatchWholeLines,
	"match-regex"       : funcMatchRegex,
	"print-name"        : funcPrintName,
	"print-matches"     : funcPrintMatches,
	"no-duplicates"     : funcNoDuplicates,
	"no-name-duplicates": funcNoNameDuplicates,
}

for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
	verbose(f"Processing \"{file['name']}\"")

	if parsedArgs.print_rundata:
		# Here mainly for debugging. May expand upon later
		print("runData: "*_header+json.dumps(runData))

	if file["isDir"]:
		verbose(f"\"{file['name']}\" is a directory; Continuing")
		continue

	# Initialize relevant runData
	runData["file"]["passed"       ]=True
	runData["file"]["printedName"  ]=False
	runData["file"]["totalMatches" ]=0
	runData["file"]["passedMatches"]=0
	runData["file"]["failedMatches"]=0
	runData["file"]["totalMatchesPerRegex" ]=[0 for x in parsedArgs.regex]
	runData["file"]["passedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
	runData["file"]["failedMatchesPerRegex"]=[0 for x in parsedArgs.regex]

	runData["lastDir"]=runData["currDir"]
	runData["currDir"]=os.path.dirname(file["name"])

	# Handle new directories
	if runData["lastDir"]!=runData["currDir"]:
		if runData["dir"]["passedFiles"]:
			# Print data from last dir (--count)
			if runData["lastDir"] is not None:
				verbose("Just exited a directory; Printing runData...")
				handleCount(rules=["dir"], runData=runData)
			# Handle --limit total-dir
			if checkLimits("tdp"):
				verbose("Total directory limit reached; Exiting...")
				break
		# Initialize relevant runData
		runData["dir"  ]["printedName"  ] =False
		runData["total"]["totalDirs"    ]+=1
		runData["dir"  ]["totalFiles"   ] =0
		runData["dir"  ]["failedFiles"  ] =0
		runData["dir"  ]["passedFiles"  ] =0
		runData["dir"  ]["totalMatches" ] =0
		runData["dir"  ]["passedMatches"] =0
		runData["dir"  ]["failedMatches"] =0
		runData["dir"  ]["totalMatchesPerRegex" ]=[0 for x in parsedArgs.regex]
		runData["dir"  ]["passedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
		runData["dir"  ]["failedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
		runData["dir"  ]["totalFilesPerRegex"   ]=[0 for x in parsedArgs.regex]
		runData["dir"  ]["passedFilesPerRegex"  ]=[0 for x in parsedArgs.regex]
		runData["dir"  ]["handledFilesPerRegex" ]=[0 for x in parsedArgs.regex]

	runData["total"]["totalFiles"]+=1
	runData["dir"  ]["totalFiles"]+=1
	# It has to be done here to make sure runData["dir"] doesn't miss stuff
	# Handle --name-regex stuff
	nameRegexResult=filenameChecker(file)
	if nameRegexResult is False:
		verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched a fail regex; Continuing...")
		runData["dir"  ]["failedFiles"]+=1
		runData["total"]["failedFiles"]+=1
		runData["file" ]["passed"     ]=False
	elif nameRegexResult is None:
		verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched an ignore regex; Continuing...")
		runData["file"]["passed"]=False

	# Handle --file-regex stuff
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

	# Handle --dir-name-regex stuff
	if runData["currDir"]!=runData["lastDir"]:
		if runData["currDir"]=="":
			dirRegexResult=True
		else:
			dirRegexResult=dirnameChecker(runData["currDir"])

		if dirRegexResult is True:
			runData["total"]["passedDirs"]+=1
		elif dirRegexResult is False:
			verbose(f"Contents of directory \"{runData['currDir']}\" (\"{os.path.realpath(runData['currDir'])}\") matched a fail regex; Continuing...")
			runData["total"]["failedDirs"]+=1
			doneDir=True
			runData["file"]["passed"]=False
		elif dirRegexResult is None:
			verbose(f"Contents of directory \"{runData['currDir']}\" (\"{os.path.realpath(runData['currDir'])}\") matched an ignore regex; Continuing...")
			doneDir=True
			runData["file"]["passed"]=False

	# Main matching stuff
	matchIndex=0 # Just makes stuff easier

	if runData["file"]["passed"]:
		runData["dir"  ]["passedFiles"]+=1
		runData["total"]["passedFiles"]+=1

		# Handle printing file and dir names when there's no regexes
		if not parsedArgs.regex:
			runData["dir"  ]["handledFiles"]+=1
			runData["total"]["handledFiles"]+=1
			for func in parsedArgs.order:
				if func=="print-name":
					funcs["print-name"](parsedArgs, file, runData)
				elif func=="print-dir":
					funcs["print-dir"](parsedArgs, runData, runData["currDir"])
				elif func=="no-name-duplicates":
					try:
						funcs["no-name-duplicates"](parsedArgs, file)
					except NextFile:
						break

		for regexIndex, regex in enumerate(parsedArgs.regex):
			verbose(f"Handling regex {regexIndex}: {regex}")
		
			runData["total"]["totalFilesPerRegex" ][regexIndex]+=1
			runData["dir"  ]["totalFilesPerRegex" ][regexIndex]+=1
			runData["total"]["passedFilesPerRegex"][regexIndex]+=1
			runData["dir"  ]["passedFilesPerRegex"][regexIndex]+=1

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
					if matchIndex==1:
						runData["dir"  ]["handledFilesPerRegex"][regexIndex]+=1
						runData["total"]["handledFilesPerRegex"][regexIndex]+=1
						if runData["lastDir"]!=runData["currDir"]:
							runData["total"]["dirsPerRegex"][regexIndex]+=1
						if regexIndex==0:
							runData["dir"  ]["handledFiles"]+=1
							runData["total"]["handledFiles"]+=1
					runData["total"]["totalMatchesPerRegex"][regexIndex]+=1
					runData["dir"  ]["totalMatchesPerRegex"][regexIndex]+=1
					runData["file" ]["totalMatchesPerRegex"][regexIndex]+=1
					runData["total"]["totalMatches"        ]            +=1
					runData["dir"  ]["totalMatches"        ]            +=1
					runData["file" ]["totalMatches"        ]            +=1

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
								currDir=runData["currDir"]
							) or match
						except NextFile:
							break
					else:
						runData["total"]["passedMatches"        ]            +=1
						runData["dir"  ]["passedMatches"        ]            +=1
						runData["file" ]["passedMatches"        ]            +=1
						runData["total"]["passedMatchesPerRegex"][regexIndex]+=1
						runData["dir"  ]["passedMatchesPerRegex"][regexIndex]+=1
						runData["file" ]["passedMatchesPerRegex"][regexIndex]+=1

					# Handle --match-limit, --dir-match-limit, and --total-match-limit
					if checkLimits("tmt") or checkLimits("tmp") or checkLimits("tmf") or\
					   checkLimits("dmt") or checkLimits("dmp") or checkLimits("dmf") or\
					   checkLimits("fmt") or checkLimits("fmp") or checkLimits("fmf"):
						break

			except Exception as AAAAA:
				warn(f"Cannot process \"{file['name']}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}", error=AAAAA)

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
	if checkLimits("tmt") or checkLimits("tmp") or checkLimits("tmf"):
		verbose("Total match limit reached; Exiting")
		break
	if checkLimits("tft") or checkLimits("tfp") or checkLimits("tfh") or checkLimits("tff"):
		verbose("Total file limit reached; Exiting")
		break

	# Handle --limit dir-files and dir-matches
	# Really slow on big directories
	# Might eventually have this hook into _iterdir using a global flag or something
	if checkLimits("dft") or checkLimits("dfp") or checkLimits("dff") or\
	   checkLimits("dmt") or checkLimits("dmp") or checkLimits("dmf"):
		verbose("Dir limit(s) reached")
		doneDir=True

# --count dir-*
if runData["currDir"] is not None and runData["total"]["totalDirs"]:
	# Only runs if files were handled in two or more directories
	handleCount(rules=["dir"], runData=runData)

# --count total-*
handleCount(rules=["total"], runData=runData)

if parsedArgs.print_rundata:
	print("runData: "*_header+json.dumps(runData))
