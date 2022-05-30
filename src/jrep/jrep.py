#!/usr/bin/python3

"""
	JREP - James' GREP
	Version 0.1
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Official repo: https://github.com/Scripter17/JREP

	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

import argparse
import os, sys, subprocess as sp, shutil
import re, fnmatch, json
import mmap, itertools, functools, inspect
# Included with JREP
try:
	import sre_parse
except:
	import jrep.sre_parse as sre_parse
import jrep.modded_glob as glob

# Compatibility for old Python versions
if not hasattr(functools, "cache"):
	functools.cache=functools.lru_cache(maxsize=None)

DEFAULTORDER=[
	"replace",
	"match-whole-lines",
	"sub",
	"stdin-anti-match-strings",
	"match-regex",
	"no-name-duplicates",
	"no-duplicates",
	"print-dir-name",
	"print-name",
	"print-match",
]

_STDIN=b""
if not os.isatty(sys.stdin.fileno()):
	_STDIN=sys.stdin.buffer.read()

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
		setattr(namespace, self.dest, listSplit(map(lambda x:x.encode(), values), "*"))

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
				parsed["patterns" ]=[x.encode() for x in thingParts[2][0::2]] # Even elems
				parsed["repls"    ]=[x.encode() for x in thingParts[2][1::2]] # Odd  elems
				ret[-1].append(parsed)
		setattr(namespace, self.dest, ret)

class FileRegexAction(argparse.Action):
	"""
		Pre-processor for --file-regex stuff
	"""
	def __call__(self, parser, namespace, values, option_string):
		setattr(namespace, self.dest, [x.encode() for x in values])

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
	- The default value for `--order` is {', '.join(DEFAULTORDER)}
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

parser=CustomArgumentParser(formatter_class=CustomHelpFormatter, add_help=False)
parser.add_argument("--help", "-h", nargs="?", default=argparse.SUPPRESS, action=CustomHelpAction, metavar="topic", help="show this help message and exit OR use `--help [topic]` for help with [topic]")

_group=parser.add_argument_group("Files and regexes")
_group.add_argument("regex"                       ,       nargs="*", default=[], metavar="Regex", help="Regex(es) to process matches for (reffered to as \"get regexes\")")
parser.add_line()
_group.add_argument("--string"                    , "-s", action="store_true"                   , help="Treat get regexes as strings. Doesn't apply to any other options.")
_group.add_argument("--enhanced-engine"           , "-E", action="store_true"                   , help="Use alternate regex engine from https://pypi.org/project/regex/")
parser.add_line()
_group.add_argument("--file"                      , "-f", nargs="+", default=[]                 , help="A list of files to check")
_group.add_argument("--glob"                      , "-g", nargs="+", default=[]                 , help="A list of globs to check")
_group.add_argument("--include-dirs"              ,       action="store_true"                   , help="Process directories as files")
parser.add_line()
_stdin=_group.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"               , "-F", action="store_true"                   , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"               , "-G", action="store_true"                   , help="Treat STDIN as a list of globs")
_stdin.add_argument("--stdin-anti-match-strings"  ,       action="store_true"                   , help="Treat STDIN as a list of strings to not match")

_group=parser.add_argument_group("Filters")
_group.add_argument("--no-duplicates"             , "-D", action="store_true"                   , help="Don't print duplicate matches (See also: --order)")
_group.add_argument("--no-name-duplicates"        ,       action="store_true"                   , help="Don't process files whose names have already been processed (takes --name-sub, --print-full-paths and --print-posix-paths)")
parser.add_line()
_group.add_argument("--name-regex"                , "-t", nargs="+", default=[], metavar="Regex", help="If a file name matches all supplied regexes, keep going. Otherwise continue")
_group.add_argument("--name-anti-regex"           , "-T", nargs="+", default=[], metavar="Regex", help="Like --name-regex but excludes file names that match any of the supplied regexes")
_group.add_argument("--name-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", help="Like --name-anti-regex but doesn't contribute to --count *-failed-files")
_group.add_argument("--full-name-regex"           ,       nargs="+", default=[], metavar="Regex", help="Like --name-regex but for absolute file paths (C:/xyz instead of xyz)")
_group.add_argument("--full-name-anti-regex"      ,       nargs="+", default=[], metavar="Regex", help="Like --name-anti-regex but applied to full file paths")
_group.add_argument("--full-name-ignore-regex"    ,       nargs="+", default=[], metavar="Regex", help="Like --full-name-anti-regex but doesn't contribute to --count *-failed-files")
parser.add_line()
_group.add_argument("--name-glob"                 ,       nargs="+", default=[], metavar="Glob" , help="If a file name matches all supplied globs, keep going. Otherwise continue")
_group.add_argument("--name-anti-glob"            ,       nargs="+", default=[], metavar="Glob" , help="Like --name-glob but excludes file names that match any of the supplied globs")
_group.add_argument("--name-ignore-glob"          ,       nargs="+", default=[], metavar="Glob" , help="Like --name-anti-glob but doesn't contribute to --count *-failed-files")
_group.add_argument("--full-name-glob"            ,       nargs="+", default=[], metavar="Glob" , help="Like --name-glob but for absolute file paths (C:/xyz instead of xyz)")
_group.add_argument("--full-name-anti-glob"       ,       nargs="+", default=[], metavar="Glob" , help="Like --name-anti-glob but applied to full file paths")
_group.add_argument("--full-name-ignore-glob"     ,       nargs="+", default=[], metavar="Glob" , help="Like --full-name-anti-glob but doesn't contribute to --count *-failed-files")
parser.add_line()
_group.add_argument("--dir-name-regex"            ,       nargs="+", default=[], metavar="Regex", help="If a directory name matches all supplied regexes, enter it. Otherwise continue")
_group.add_argument("--dir-name-anti-regex"       ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-regex but excludes directories that match any of the supplied regexes")
_group.add_argument("--dir-name-ignore-regex"     ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-anti-regex but doesn't contribute to --count total-failed-dirs")
_group.add_argument("--dir-full-name-regex"       ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-regex but for absolute directory paths (C:/xyz instead of xyz)")
_group.add_argument("--dir-full-name-anti-regex"  ,       nargs="+", default=[], metavar="Regex", help="Like --dir-name-anti-regex but applied to full directory paths")
_group.add_argument("--dir-full-name-ignore-regex",       nargs="+", default=[], metavar="Regex", help="Like --dir-full-name-anti-regex but doesn't contribute to --count total-failed-dirs")
parser.add_line()
_group.add_argument("--file-regex"                ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Regexes to test file contents for")
_group.add_argument("--file-anti-regex"           ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Like --file-regex but excludes files that match of the supplied regexes")
_group.add_argument("--file-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", action=FileRegexAction, help="Like --file-anti-regex but doesn't contribute to --count *-failed-files")
parser.add_line()
_group.add_argument("--match-regex"               ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Groups are split along lone *. Matches from the Nth get regex are tested with the Nth group")
_group.add_argument("--match-anti-regex"          ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Like --match-regex but excludes matches that match any of the supplied regexes")
_group.add_argument("--match-ignore-regex"        ,       nargs="+", default=[], metavar="Regex", action=MatchRegexAction, help="Like --match-anti-regex but doesn't contribute to --count *-failed-matches")

_group=parser.add_argument_group("Sorting")
_group.add_argument("--sort"                      , "-S",                                         help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse. A windows-esque \"blockwise\" sort is also available. Run jrep --help blockwise for more info")
_group.add_argument("--sort-regex"                ,       nargs="+", default=[], metavar="Regex", help="Regexes to apply to file names keys (like --replace) for purposes of sorting (EXPERIMENTAL)")
_group.add_argument("--sort-dir"                  ,                                               help="--sort on a per-directory basis")

_group=parser.add_argument_group("Output")
_group.add_argument("--no-headers"                , "-H", action="store_true"                   , help="Don't print match: or file: before lines")
parser.add_line()
_group.add_argument("--print-dir-names"           , "-d", action="store_true"                   , help="Print names of explored directories")
_group.add_argument("--print-file-names"          , "-n", action="store_true"                   , help="Print file names as well as matches")
_group.add_argument("--print-full-paths"          , "-p", action="store_true"                   , help="Print full file paths")
_group.add_argument("--print-posix-paths"         , "-P", action="store_true"                   , help="Replace \\ with / when printing file paths")
_group.add_argument("--dont-print-matches"        , "-N", action="store_true"                   , help="Don't print matches (use with --print-file-names to only print names)")
_group.add_argument("--print-match-offset"        , "-o", action="store_true"                   , help="Print where the match starts in the file as a hexadecimal number (ignores -H)")
_group.add_argument("--print-match-range"         , "-O", action="store_true"                   , help="Print where the match starts and ends in the file as a hexadecimal number (implies -o)")

_group=parser.add_argument_group("Replace/Sub")
_group.add_argument("--replace"                   , "-r", nargs="+", default=[], metavar="Regex", help="Regex replacement")
_group.add_argument("--sub"                       , "-R", nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="re.sub argument pairs after --replace is applied. Run jrep.py --help sub for more info")
_group.add_argument("--name-sub"                  ,       nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="Applies --sub to file names. A lone * separates subsitutions for y/z and C:/x/y/z")
_group.add_argument("--dir-name-sub"              ,       nargs="+", default=[], metavar="Regex", action=SubRegexAction, help="--name-sub but for directory names")
_group.add_argument("--escape"                    , "-e", action="store_true"                   , help="Escape back slashes, newlines, carriage returns, and non-printable characters")

_group=parser.add_argument_group("Misc.")
_group.add_argument("--count"                     , "-c", nargs="+", default=[]                  , action=CountAction , help="Count match/file/dir per file, dir, and/or total (Ex: --count fm dir-files)")
_group.add_argument("--limit"                     , "-l", nargs="+", default=JSObj({}, default=0), action=LimitAction , help="Limit match/file/dir per file, dir, and/or total (Ex: --limit filematch=1 total_dirs=5)")
parser.add_line()
_group.add_argument("--depth-first"               ,       action="store_true"                      , help="Enter subdirectories before processing files")
_group.add_argument("--glob-root-dir"             ,                                                  help="Root dir to run globs in (JANK)")
parser.add_line()
_group.add_argument("--match-whole-lines"         , "-L", action="store_true"                      , help="Match whole lines like FINDSTR")
_group.add_argument("--print-failed-files"        ,       action="store_true"                      , help="Print file names even if they fail (Partially broken)")
#_group.add_argument("--json"                      , "-j", action="store_true"                      , help="Print output as JSON")
_group.add_argument("--no-warn"                   ,       action="store_true"                      , help="Don't print warning messages")
_group.add_argument("--hard-warn"                 ,       action="store_true"                      , help="Throw errors instead of warnings")
_group.add_argument("--weave-matches"             , "-w", action="store_true"                      , help="Weave regex matchdes (print first results for each get regex, then second results, etc.)")
_group.add_argument("--strict-weave"              , "-W", action="store_true"                      , help="Only print full weave sets")

_group=parser.add_argument_group("Exec")
_group.add_argument("--pre-match-exec"            ,                                   metavar="cmd", help="Command to run before printing each match")
_group.add_argument("--match-exec"                ,                                   metavar="cmd", help="Command to run after  printing each match")
_group.add_argument("--if-match-exec-before"      ,                                   metavar="cmd", help="Command to run as soon as least one match passes")
_group.add_argument("--if-match-exec-after"       ,                                   metavar="cmd", help="Command to run at the end if at least one match passed")
_group.add_argument("--if-no-match-exec-after"    ,                                   metavar="cmd", help="Command to run at the end if at no matches passed")
parser.add_line()
_group.add_argument("--pre-file-exec"             ,                                   metavar="cmd", help="Command to run before printing each file name")
_group.add_argument("--file-exec"                 ,                                   metavar="cmd", help="Command to run after  printing each file name")
_group.add_argument("--if-file-exec-before"       ,                                   metavar="cmd", help="Command to run as soon as least one file  passes")
_group.add_argument("--if-file-exec-after"        ,                                   metavar="cmd", help="Command to run at the end if at least one file  passed")
_group.add_argument("--if-no-file-exec-after"     ,                                   metavar="cmd", help="Command to run at the end if at no files   passed")
parser.add_line()
_group.add_argument("--pre-dir-exec"              ,                                   metavar="cmd", help="Command to run before printing each dir name")
_group.add_argument("--dir-exec"                  ,                                   metavar="cmd", help="Command to run after  printing each dir name")
_group.add_argument("--if-dir-exec-before"        ,                                   metavar="cmd", help="Command to run as soon as least one dir   passes")
_group.add_argument("--if-dir-exec-after"         ,                                   metavar="cmd", help="Command to run at the end if at least one dir   passed")
_group.add_argument("--if-no-dir-exec-after"      ,                                   metavar="cmd", help="Command to run at the end if at no dirs    passed")

_group=parser.add_argument_group("Debugging/Advanced")
_group.add_argument("--order"                     ,       nargs="+", default=DEFAULTORDER          , help="The order in which modifications to matches are applied. Run jrep --help order for more info")
_group.add_argument("--no-flush"                  ,       action="store_true"                      , help="Improves speed by disabling manually flushing the stdout buffer (ideal for chaining commands)")
_group.add_argument("--force-flush"               ,       action="store_true"                      , help="Always flush STDOUT (slow)")
_group.add_argument("--print-rundata"             ,       action="store_true"                      , help="Print raw runData JSON at the end (used for debugging)")
_group.add_argument("--verbose"                   , "-v", action="store_true"                      , help="Verbose info")
parsedArgs=parser.parse_args()

# TODO: Logging module
def verbose(x):
	if parsedArgs.verbose:
		caller=inspect.stack()[1]
		print(f"Verbose on line {caller[2]} in function {caller[3]}: {x}")
def warn(x, error=None):
	if not parsedArgs.no_warn:
		if parsedArgs.hard_warn:
			raise error or Exception(f"No error provided (Message: \"{x}\")")
		else:
			calls=inspect.stack()[1:]
			print(f"Waring on lines {', '.join([str(call[2]) for call in calls])} in functions {', '.join([str(call[3]) for call in calls])} : {x}", file=sys.stderr)

# Keeping everything like this makes life easier
# It's a mess but the alternative is worse
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
	"matchedStrings":set(),  # --no-duplicates handler
	"filenames":[],
	"currDir":None,
	"lastDir":None,
	"doneDir":False,
}

# Shove things into modded_glob
# sortDirFiles is added below
glob.parsedArgs=parsedArgs
glob.verbose=verbose
glob.runData=runData

# Decide whether or not to flush STDOUT after pritning matches/names/dirs
_flushStdout=True
if (parsedArgs.no_flush or not os.isatty(sys.stdout.fileno())) and not parsedArgs.force_flush:
	_flushStdout=False

verbose("JREP preview version")
verbose(parsedArgs)

# Handle --enhanced-engine
if parsedArgs.enhanced_engine:
	import regex as re

# Remove unneeded match handlers
def orderRemove(x):
	if x in parsedArgs.order:
		parsedArgs.order.remove(x)
if not parsedArgs.replace                 : orderRemove("replace")
if not parsedArgs.match_whole_lines       : orderRemove("match-whole-lines")
if not parsedArgs.sub                     : orderRemove("sub")
if not parsedArgs.stdin_anti_match_strings: orderRemove("stdin-anti-match-strings")
if not parsedArgs.match_regex and not parsedArgs.match_anti_regex and not parsedArgs.match_ignore_regex:
	orderRemove("match-regex")
if not parsedArgs.no_name_duplicates      : orderRemove("no-name-duplicates")
if not parsedArgs.no_duplicates           : orderRemove("no-duplicates")

# Verify --replace
if not (len(parsedArgs.replace)==0 or len(parsedArgs.replace)==1 or len(parsedArgs.replace)==len(parsedArgs.regex)):
	warn(
		"Error: Length of --replace must be either 1 or equal to the number of regexes",
		error=ValueError("Error: Length of --replace must be either 1 or equal to the number of regexes")
	)

# Functions for --name-regex and co.
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

# Helper functions
def handleCount(rules, runData):
	"""
		Prints out --count data
		Very janky but it works
	"""
	cats      ={"t":"total" , "d":"dir"    , "f":"file"                 }
	subCats   ={"t":"dfm"   , "d":"fm"     , "f":"m"                    }
	catNames  ={"t":"total" , "d":"dir"    , "f":"file"  , "m":"match"  }
	catPlurals={"t":"totals", "d":"dirs"   , "f":"files" , "m":"matches"}
	filters   ={"p":"passed", "h":"handled", "f":"failed"               }

	def handleTotals(regexIndex, value):
		print(ofmt["countTotal"].format(cat=keyCat.title(), subCat=keySubCatPlural, regexIndex=regexIndex, value=value))

	def handleFiltereds(regexIndex, key):
		if regexIndex=="*":
			filterCount=runData[keyCat][keySubCatFilter+keySubCat]
			divisor=runData[keyCat]['total'+keySubCat]
		else:
			filterCount=runData[keyCat][keySubCatFilter+keySubCat+"PerRegex"][regexIndex]
			divisor=runData[keyCat]['total'+keySubCat+"PerRegex"][regexIndex]

		if len(key)>3 and key[3]=="p":
			filterCount/=divisor

		print(ofmt["countFiltered"].format(filter=keySubCatFilter.title(), cat=keyCat, subCat=keySubCatFilter, regexIndex=regexIndex, count=filterCount))

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
	"""
		Prevents the blockwise sort from splitting 123abc/def456 into ["123", "abc/def", "456"]
	"""
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
		Also it's just generally slow for large file sets
		Unless you're using really high end SSD, CPU, and RAM
		And if you are then I'm sorry for writing JREP in Python
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
			files=map(lambda file: {"orig":file["orig"] if "orig" in file else file, "name":re.sub(pattern, replace, file["name"])}, files)

	return map(lambda x:x["orig"] if "orig" in x else x, sorted(files, key=sorts[key]))

	#return sorted(files, key=sorts[key])

def sortDirFiles(names, dirname, key=None):
	"""
		Handler for --sort-dir
	"""
	if key is None:
		yield from names
		return
	files=map(lambda name:{"name":os.path.join(dirname, name), "stdin":False}, names)
	for file in sortFiles(files, key=key):
		yield oa.path.relpath(file["name"], dirname)
glob.sortDirFiles=sortDirFiles

def fileContentsDontMatter():
	"""
		If file contents don't matter, tell getFiles to not even run open() on them
		JREP doesn't load file contents into memory (it uses mmap) but just opening a file handler takes time
	"""
	return not any(parsedArgs.regex) and\
	       not parsedArgs.file_regex and not parsedArgs.file_anti_regex and\
	       not any(map(lambda x:re.search(r"[tdf]m", x), parsedArgs.limit.keys())) and\
	       not any(map(lambda x:re.search(r"^[tdf]m(([pf]c)?[tr])?$", x), parsedArgs.count))

def getFiles():
	"""
		Yields files selected with --file and --glob
		Stdin has a filename of -
		On Windows, empty files use a bytes object instead of mmap
		Stdin always uses a bytes object
		If the contents of a file are irrelevant (see: fileContentsDontMatter), b"" is always used instead of mmap
	"""
	def advancedGlob(pattern, recursive=False):
		"""
			A simple wrapper for glob.iglob that allows for using *:/ and ?:/ in glob patterns
			May cause issues with stuff like SD to USB adapters with no media inserted. I can't test that right now
		"""
		if pattern.startswith("*:") or pattern.startswith("?:"):
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
			yield from _STDIN.decode().splitlines()
		# --file

		verbose("Yielding files")
		yield from parsedArgs.file

		# Globs
		verbose("Yielding STDIN globs")
		# --stdin-globs
		if not _STDIN and parsedArgs.stdin_globs:
			for pattern in _STDIN.decode().splitlines():
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

		relDir, basename=os.path.dirname(file), os.path.basename(file)
		absDir=os.path.normpath(os.path.join(os.getcwd(), relDir))
		ret={"name": file, "basename":basename, "relDir":relDir, "absDir":absDir, "data": b"", "isDir": False, "stdin": False}
		if os.path.isfile(file):
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
							# Windows moment :/
							mmapFile=b""
						ret["data"]=mmapFile
						yield ret
				except OSError as AAAAA:
					warn(f"Cannot process \"{file}\" because of \"{AAAAA}\"", error=AAAAA)
		else:
			verbose(f"\"{file}\" is a directory")
			ret["isDir"]=True
			yield ret

def processFileName(fname):
	"""
		Process file names according to --name-sub, --print-full-paths, and --print-posix-paths
		Used for printing file names as well as --no-name-duplicates
	"""
	fname=_funcSub(parsedArgs.name_sub, fname.encode(), 0, wrap=False)
	if parsedArgs.print_full_paths : fname=os.path.realpath(fname)
	if parsedArgs.print_posix_paths: fname=fname.replace(b"\\", b"/")
	fname=_funcSub(parsedArgs.name_sub, fname, 1, wrap=False)
	return fname

def processDirName(dname):
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

def escape(match):
	r"""
		Handle --escape
		Converts backslashes, carriage returns, and newlines to \\, \r, and \n respectively
		Also converts non-printable bytes to \xXX to avoid stuff like ANSI codes and bells
	"""
	if parsedArgs.escape:
		ret=match.replace(b"\\", b"\\\\").replace(b"\r", b"\\r").replace(b"\n", b"\\n")
		ret=re.sub(rb"[\x00-\x1f\x80-\xff]", lambda x:(f"\\x{ord(x[0]):02x}".encode()), ret)
		return ret
	return match

noLimits=[]
def checkLimitType(sn, filters="ptf"):
	cats={"d":"t", "f":"td", "m":"tdf"}[sn]
	#if sn in noLimits:
	#	return False

	noLimitType=True
	for category in cats:
		ret=checkLimitCategory(category+sn, filters=filters)
		if ret is False:
			noLimitType=False
		if ret is True:
			return True

	if noLimitType:
		for cat in cats:
			noLimits.remove(cat+sn)
		noLimits.append(sn)
	return False

def checkLimitCategory(sn, filters="ptf"):
	if sn in noLimits or sn[1] in noLimits:
		return None

	noLimitCategory=True
	for filter in filters:
		ret=checkLimit(sn+filter)
		if ret is None:
			noLimits.append(sn+filter)
		elif ret is False:
			noLimitCategory=False
		elif ret is True:
			return True

	if noLimitCategory:
		for _ in filters:
			noLimits.pop()
		noLimits.append(sn)
	return False

def getLimitValue(sn):
	nameMap={"t":"total","d":"dir","f":"file","m":"match"}
	typeMap={"t":"total","p":"passed","f":"failed","h":"handled"}
	plural="e"*(sn[1]=="m")+"s"
	try:
		return runData[nameMap[sn[0]]][typeMap[sn[2]]+nameMap[sn[1]].title()+plural]
	except KeyError:
		return 0

def checkLimit(sn):
	"""
		Given an LCName's "short name" (total-files -> tf),
		check whether or not it's exceeded its value in --limit (if set)
		Like handleCount, this function is quite jank, but it works
	"""
	if sn in noLimits:
		return False

	limit=parsedArgs.limit[sn]
	if limit==0:
		return None
	value=getLimitValue(sn)
	return value>=limit

def delayedSub(repl, match):
	"""
		Use the secret sre_parse module to emulate re.sub with a re.Match object
		Used exclusively for --replace
		Python 3.11: sre_parse is removed, so I stole the function and put it at the top of this file
		I really need to give up on the "JREP as a single file" dream
	"""
	parsedTemplate=parse_template(repl, match.re)
	groups=[match[0], *match.groups()]
	for x in parsedTemplate[0]:
		parsedTemplate[1][x[0]]=groups[x[1]]
	match[0]=type(parsedTemplate[1][0])().join(parsedTemplate[1])
	return match

# Match processors

def funcReplace(parsedArgs, match, regexIndex, **kwargs):
	"""
		Handle --replace
	"""
	replacement=parsedArgs.replace[regexIndex%len(parsedArgs.replace)]
	return delayedSub(replacement.encode(errors="ignore"), match)
	
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
						match=re.sub(pattern, repl, match)
	return match

def funcSub(parsedArgs, match, regexIndex, **kwargs):
	"""
		Handle --sub
	"""
	match[0]=_funcSub(parsedArgs.sub, match[0], regexIndex, **kwargs)
	return match

def funcMatchWholeLines(parsedArgs, match, file, **kwargs):
	"""
		Handle --match-whole-lines
		Very jank; Needs to be improved
	"""
	lineStart=file["data"].rfind(b"\n", 0, match.span()[1])
	lineEnd  =file["data"]. find(b"\n",    match.span()[1])
	if lineStart==-1: lineStart=None
	if lineEnd  ==-1: lineEnd  =None
	match[0]=file["data"][lineStart+1:match.span()[0]]+match[0]+file["data"][match.span()[1]:lineEnd]
	return match

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

def funcStdinAntiMatchStrings(parsedArgs, runData, match, **kwargs):
	if match[0] in _STDIN.splitlines():
		runData["total"]["failedMatches"        ]            +=1
		runData["dir"  ]["failedMatches"        ]            +=1
		runData["file" ]["failedMatches"        ]            +=1
		runData["total"]["failedMatchesPerRegex"][regexIndex]+=1
		runData["dir"  ]["failedMatchesPerRegex"][regexIndex]+=1
		runData["file" ]["failedMatchesPerRegex"][regexIndex]+=1
		raise NextMatch()

def funcMatchRegex(parsedArgs, runData, match, regexIndex, **kwargs):
	"""
		Handle --match-regex and --match-anti-regex
		Because yes. Filtering matches by using another regex is a feature I genuinely needed
		Most features in JREP I have actually needed sometimes
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
		raise NextMatch()
	elif matchRegexResult is None:
		raise NextMatch()

def execHandler(cmd, arg=None):
	"""
		Handle the --exec family of options
		sp.run(b"echo This doesn't work on Windows for some reason")
	"""
	if cmd is None:
		return
	if os.name=="nt":
		# Windows moment :/
		if isinstance(cmd, bytes): cmd=cmd.decode()
		if isinstance(arg, bytes): arg=arg.decode()
	if arg is not None:
		if not isinstance(arg, list):
			arg=[arg]
		cmd=cmd.format(*arg)

	sp.run(cmd, shell=True)

def funcPrintDirName(parsedArgs, runData, currDir, **kwargs):
	"""
		Handle --print-directories
	"""
	if runData["dir"]["printedName"]:
		return

	if parsedArgs.if_dir_exec_before is not None:
		# --if-dir-exec-before
		execHandler(parsedArgs.if_dir_exec_before)
		parsedArgs.if_dir_exec_before=None

	pDirName=processDirName(currDir)
	if parsedArgs.pre_dir_exec is not None:
		# --pre-dir-exec
		execHandler(parsedArgs.pre_dir_exec, pDirName)

	if parsedArgs.print_dir_names:
		sys.stdout.buffer.write(ofmt["dname"]+pDirName)
		sys.stdout.buffer.write(b"\n")
		if _flushStdout:
			sys.stdout.buffer.flush()
		runData["dir"]["printedName"]=True

	if parsedArgs.dir_exec is not None:
		# --dir-exec
		execHandler(parsedArgs.dir_exec, pDirName)

def funcPrintName(parsedArgs, file, runData, **kwargs):
	"""
		Handle --print-names
	"""
	if runData["file"]["printedName"]:
		return

	if parsedArgs.if_file_exec_before is not None:
		# --if-file-exec-before
		execHandler(parsedArgs.if_file_exec_before)
		parsedArgs.if_file_exec_before=None

	pFileName=processFileName(file["name"])
	if parsedArgs.pre_file_exec is not None:
		# --pre-file-exec
		execHandler(parsedArgs.pre_file_exec, pFileName)

	if parsedArgs.print_file_names:
		sys.stdout.buffer.write(ofmt["fname"]+pFileName)
		sys.stdout.buffer.write(b"\n")
		if _flushStdout:
			sys.stdout.buffer.flush()
	runData["file"]["printedName"]=True

	if parsedArgs.file_exec is not None:
		# --file-exec

		execHandler(parsedArgs.file_exec, pFileName)

def printMatch(match, regexIndex):
	"""
		Print matches
		Not much else to say
	"""
	if match is None:
		return

	if parsedArgs.if_match_exec_before is not None:
		# --if-match-exec-before
		execHandler(parsedArgs.if_match_exec_before)
		parsedArgs.if_match_exec_before=None

	if parsedArgs.pre_match_exec is not None:
		# --pre-match-exec
		execHandler(parsedArgs.pre_match_exec, match[0])

	if not parsedArgs.dont_print_matches:
		sys.stdout.buffer.write(ofmt["match"].format(range=match.span(), regexIndex=regexIndex).encode())
		sys.stdout.buffer.write(escape(match[0]))
		sys.stdout.buffer.write(b"\n")
		if _flushStdout:
			sys.stdout.buffer.flush()

	if parsedArgs.match_exec is not None:
		# --match-exec
		execHandler(parsedArgs.match_exec, match[0])

def funcPrintMatch(parsedArgs, file, regexIndex, match, **kwargs):
	"""
		Print matches
	"""
	if parsedArgs.weave_matches:
		runData["file"]["matches"][regexIndex].append(match)
	else:
		printMatch(match, regexIndex)

def funcNoDuplicates(parsedArgs, match, **kwargs):
	"""
		Handle --no-duplicates
	"""
	if match[0] in runData["matchedStrings"]:
		raise NextMatch()
	runData["matchedStrings"].add(match[0])

def funcNoNameDuplicates(parsedArgs, file, **kwargs):
	"""
		Handle --no-name-duplicates
	"""
	if processFileName(file["name"]) in runData["filenames"]:
		raise NextFile()
	runData["filenames"].append(processFileName(file["name"]))

def funcPrintFailedFile(parsedArgs, file, runData, **kwargs):
	"""
		Print filename of failed file if --print-non-matching-files is specified
	"""
	funcPrintName(parsedArgs, file, runData)

runData["total"]["dirsPerRegex"         ]=[0 for _ in parsedArgs.regex]
runData["total"]["totalFilesPerRegex"   ]=[0 for _ in parsedArgs.regex]
runData["total"]["passedFilesPerRegex"  ]=[0 for _ in parsedArgs.regex]
runData["total"]["handledFilesPerRegex" ]=[0 for _ in parsedArgs.regex]
runData["total"]["totalMatchesPerRegex" ]=[0 for _ in parsedArgs.regex]
runData["total"]["passedMatchesPerRegex"]=[0 for _ in parsedArgs.regex]
runData["total"]["failedMatchesPerRegex"]=[0 for _ in parsedArgs.regex]

funcs={
	"print-dir-name"          : funcPrintDirName,
	"replace"                 : funcReplace,
	"sub"                     : funcSub,
	"match-whole-lines"       : funcMatchWholeLines,
	"stdin-anti-match-strings":	funcStdinAntiMatchStrings,
	"match-regex"             : funcMatchRegex,
	"print-name"              : funcPrintName,
	"print-match"             : funcPrintMatch,
	"no-duplicates"           : funcNoDuplicates,
	"no-name-duplicates"      : funcNoNameDuplicates,
}

# Output fstrings to make later usage easier
_header=not parsedArgs.no_headers
_mOffs1=parsedArgs.print_match_offset or parsedArgs.print_match_range
_mOffs2=parsedArgs.print_match_range
_mRange=("{range[0]:08x}"*_mOffs1)+("-{range[1]:08x}"*_mOffs2)
_mAt=_header and _mOffs1
_mRange=(" at "*_mAt) + (_mRange) + (": "*(_header or _mRange!=""))
ofmt={
	"dname"        : b"Directory: "                              *_header,
	"fname"        : b"File: "                                   *_header,
	"match"        : ("Match (R{regexIndex})"                    *_header)+_mRange,
	"rundata"      : ("runData: "                                *_header)+"{runData}",
	"countFiltered": ("{filter} {cat} {subCat} (R{regexIndex}): "*_header)+"{count}",
	"countTotal"   : ("{cat} {subCat} (R{regexIndex}): "         *_header)+"{value}",
}

def main():
	# The main file loop
	for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
		verbose(f"Processing \"{file['name']}\"")

		if parsedArgs.print_rundata:
			# Mainly for debugging. May expand upon later
			print(ofmt["runData"].format(runData=json.dumps(runData)))

		if file["isDir"] and not parsedArgs.include_dirs:
			verbose(f"\"{file['name']}\" is a directory; Continuing")
			continue

		# Initialize runData["file"]
		runData["file"]["passed"       ]=True
		runData["file"]["printedName"  ]=False
		runData["file"]["totalMatches" ]=0
		runData["file"]["passedMatches"]=0
		runData["file"]["failedMatches"]=0
		runData["file"]["totalMatchesPerRegex" ]=[0 for x in parsedArgs.regex]
		runData["file"]["passedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
		runData["file"]["failedMatchesPerRegex"]=[0 for x in parsedArgs.regex]

		# Keep track of when new directories are entered
		runData["lastDir"]=runData["currDir"]
		runData["currDir"]=os.path.dirname(file["name"])

		# Handle new directories
		if runData["lastDir"]!=runData["currDir"]:
			if runData["dir"]["passedFiles"]:
				# Print data from last dir (--count)
				if runData["lastDir"] is not None:
					verbose("Just exited a directory")
					handleCount(rules=["dir"], runData=runData)
				# Handle --limit total-dir
			if checkLimitCategory("td"):
				verbose("Total directory limit reached; Exiting...")
				break
			runData["total"]["totalDirs"]+=1

			# Initialize runData["dir"]
			runData["dir"]["printedName"          ]=False
			runData["dir"]["totalFiles"           ]=0
			runData["dir"]["failedFiles"          ]=0
			runData["dir"]["passedFiles"          ]=0
			runData["dir"]["totalMatches"         ]=0
			runData["dir"]["passedMatches"        ]=0
			runData["dir"]["failedMatches"        ]=0
			runData["dir"]["totalMatchesPerRegex" ]=[0 for x in parsedArgs.regex]
			runData["dir"]["passedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
			runData["dir"]["failedMatchesPerRegex"]=[0 for x in parsedArgs.regex]
			runData["dir"]["totalFilesPerRegex"   ]=[0 for x in parsedArgs.regex]
			runData["dir"]["passedFilesPerRegex"  ]=[0 for x in parsedArgs.regex]
			runData["dir"]["handledFilesPerRegex" ]=[0 for x in parsedArgs.regex]

		runData["total"]["totalFiles"]+=1
		runData["dir"  ]["totalFiles"]+=1

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
				runData["doneDir"]=True
				runData["file"]["passed"]=False
			elif dirRegexResult is None:
				verbose(f"Contents of directory \"{runData['currDir']}\" (\"{os.path.realpath(runData['currDir'])}\") matched an ignore regex; Continuing...")
				runData["doneDir"]=True
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
					elif func=="print-dir-name":
						funcs["print-dir-name"](parsedArgs, runData, runData["currDir"])
					elif func=="no-name-duplicates":
						try:
							funcs["no-name-duplicates"](parsedArgs, file)
						except NextFile:
							break

			# Handle regex matching and all that jazz
			for regexIndex, regex in enumerate(parsedArgs.regex):
				verbose(f"Handling regex {regexIndex}: {regex}")

				runData["total"]["totalFilesPerRegex" ][regexIndex]+=1
				runData["dir"  ]["totalFilesPerRegex" ][regexIndex]+=1
				runData["total"]["passedFilesPerRegex"][regexIndex]+=1
				runData["dir"  ]["passedFilesPerRegex"][regexIndex]+=1

				# --weave-matches
				if parsedArgs.weave_matches:
					runData["file"]["matches"].append([])

				try:
					# Turn regex into bytes
					regex=regex.encode(errors="ignore")

					# Probably a bad idea, performance wise
					if parsedArgs.string:
						regex=re.escape(regex)

					# Process matches
					for matchIndex, match in enumerate(re.finditer(regex, file["data"]), start=1):
						# Files/Dirs per regex
						if matchIndex==1:
							runData["dir"  ]["handledFilesPerRegex"][regexIndex]+=1
							runData["total"]["handledFilesPerRegex"][regexIndex]+=1
							if runData["lastDir"]!=runData["currDir"]:
								runData["total"]["dirsPerRegex"][regexIndex]+=1
							if regexIndex==0:
								runData["dir"  ]["handledFiles"]+=1
								runData["total"]["handledFiles"]+=1
						# Match counting
						runData["total"]["totalMatchesPerRegex"][regexIndex]+=1
						runData["dir"  ]["totalMatchesPerRegex"][regexIndex]+=1
						runData["file" ]["totalMatchesPerRegex"][regexIndex]+=1
						runData["total"]["totalMatches"        ]            +=1
						runData["dir"  ]["totalMatches"        ]            +=1
						runData["file" ]["totalMatches"        ]            +=1

						# Makes handling matches easier
						match=JSObj({
							0:match[0],
							#**dict(enumerate(match.groups(), start=1)),
							"groups":match.groups,
							"span":match.span,
							"re":match.re
						})

						# Handle matches
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
							except NextMatch:
								verbose("NextMatch")
								break
							except NextFile:
								verbose("NextFile")
								# TEMP SOLUTION
								break
						else:
							verbose("Match handled to completion")
							# Turns out for...else lets you run code when the loop isn't `break`ed out of
							runData["total"]["passedMatches"        ]            +=1
							runData["dir"  ]["passedMatches"        ]            +=1
							runData["file" ]["passedMatches"        ]            +=1
							runData["total"]["passedMatchesPerRegex"][regexIndex]+=1
							runData["dir"  ]["passedMatchesPerRegex"][regexIndex]+=1
							runData["file" ]["passedMatchesPerRegex"][regexIndex]+=1

						# Handle --match-limit, --dir-match-limit, and --total-match-limit
						if "m" not in noLimits and checkLimitType("m"):
							break

				except Exception as AAAAA:
					warn(f"Cannot process \"{file['name']}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}", error=AAAAA)

		if parsedArgs.print_failed_files and not runData["file"]["passed"]:
			verbose(f"\"{file['name']}\" didn't match any file regexes, but --print-non-matching-files was specified")
			funcPrintFailedFile(parsedArgs, file, runData)

		if parsedArgs.weave_matches:
			f=zip if parsedArgs.strict_weave else itertools.zip_longest
			for matches in f(*runData["file"]["matches"]):
				for regexIndex, match in enumerate(matches):
					printMatch(match, regexIndex)

		handleCount(rules=["file"], runData=runData)

		# Hanlde --limit total-matches and total-files
		if checkLimitCategory("tm"):
			verbose("Total match limit reached; Exiting")
			break
		if checkLimitCategory("tf", filters="ptfh"):
			verbose("Total file limit reached; Exiting")
			break

		# Handle --limit dir-files and dir-matches
		# Really slow on big directories
		# Might eventually have this hook into _iterdir using a global flag or something
		if checkLimitCategory("df", filters="ptfh") or checkLimitCategory("dm"):
			verbose("Dir limit(s) reached")
			runData["doneDir"]=True

	# --count dir-*
	if runData["currDir"] is not None and runData["total"]["totalDirs"]:
		# Only runs if files were handled in two or more directories
		handleCount(rules=["dir"], runData=runData)

	# --count total-*
	handleCount(rules=["total"], runData=runData)

	execHandler(parsedArgs.if_match_exec_after if runData["total"]["passedMatches"] else parsedArgs.if_no_match_exec_after)
	execHandler(parsedArgs.if_file_exec_after  if runData["total"]["passedFiles"  ] else parsedArgs.if_no_file_exec_after )
	execHandler(parsedArgs.if_dir_exec_after   if runData["total"]["passedDirs"   ] else parsedArgs.if_no_dir_exec_after  )

	if parsedArgs.print_rundata:
		print(ofmt["runData"].format(runData=json.dumps(runData)))

if __name__=="__main__":
	main()
