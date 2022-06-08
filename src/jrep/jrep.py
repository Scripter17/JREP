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

import os, sys, subprocess as sp, shutil
import re, fnmatch, json
import mmap, itertools, functools, inspect
_re=re
try:
	import regex as _regex
except:
	_regex=None
from . import modded_glob as glob, modded_argparse, processors, utils

__ALL__=["main"]

def verbose(x):
	# if parsedArgs.verbose:
	# 	caller=inspect.stack()[1]
	# 	print(f"Verbose on line {caller[2]} in function {caller[3]}: {x}")
	pass
def warn(x, error=None):
	# if not parsedArgs.no_warn:
	# 	if parsedArgs.hard_warn:
	# 		raise error or Exception(f"No error provided (Message: \"{x}\")")
	# 	else:
	# 		calls=inspect.stack()[1:]
	# 		print(f"Warning on lines {', '.join([f'{call[3]}:{call[2]}' for call in calls])} : {x}", file=sys.stderr)
	# 		#print(f"Waring on lines {', '.join([str(call[2]) for call in calls])} in functions {', '.join([str(call[3]) for call in calls])} : {x}", file=sys.stderr)
	raise error

# Compatibility for old Python versions
if not hasattr(functools, "cache"):
	functools.cache=functools.lru_cache(maxsize=None)

parser=modded_argparse.CustomArgumentParser(formatter_class=modded_argparse.CustomHelpFormatter, add_help=False)
parser.add_argument("--help", "-h", nargs="?", default=modded_argparse.SUPPRESS, action=modded_argparse.CustomHelpAction, metavar="topic", help="show this help message and exit OR use `--help [topic]` for help with [topic]")

_group=parser.add_argument_group("Global behaviour")
#_group.add_argument("--string"                    , "-s", action="store_true"                   , help="Treat get regexes as strings. Doesn't apply to any other options.")
_group.add_argument("--enhanced-engine"           , "-E", action="store_true"                   , help="Use alternate regex engine from https://pypi.org/project/regex/")
_group=parser.add_argument_group("Files and regexes")
_group.add_argument("regex"                       ,       nargs="*", default=[], metavar="Regex", action=modded_argparse.RegexAction, help="Regex(es) to process matches for (reffered to as \"get regexes\")")
parser.add_line()
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
_group.add_argument("--file-regex"                ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.FileRegexAction, help="Regexes to test file contents for")
_group.add_argument("--file-anti-regex"           ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.FileRegexAction, help="Like --file-regex but excludes files that match of the supplied regexes")
_group.add_argument("--file-ignore-regex"         ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.FileRegexAction, help="Like --file-anti-regex but doesn't contribute to --count *-failed-files")
parser.add_line()
_group.add_argument("--match-regex"               ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.MatchRegexAction, help="Groups are split along lone *. Matches from the Nth get regex are tested with the Nth group")
_group.add_argument("--match-anti-regex"          ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.MatchRegexAction, help="Like --match-regex but excludes matches that match any of the supplied regexes")
_group.add_argument("--match-ignore-regex"        ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.MatchRegexAction, help="Like --match-anti-regex but doesn't contribute to --count *-failed-matches")

_group=parser.add_argument_group("Sorting")
_group.add_argument("--sort"                      , "-S",                                         help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse. A windows-esque \"blockwise\" sort is also available. Run jrep --help blockwise for more info")
_group.add_argument("--sort-dir"                  ,                                               help="--sort on a per-directory basis")
_group.add_argument("--sort-regex"                ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.SortRegexAction, help="Regexes to apply to file names keys (like --replace) for purposes of sorting (EXPERIMENTAL)")

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
_group.add_argument("--sub"                       , "-R", nargs="+", default=[], metavar="Regex", action=modded_argparse.SubRegexAction, help="re.sub argument pairs after --replace is applied. Run jrep.py --help sub for more info")
_group.add_argument("--name-sub"                  ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.SubRegexAction, help="Applies --sub to file names. A lone * separates subsitutions for y/z and C:/x/y/z")
_group.add_argument("--dir-name-sub"              ,       nargs="+", default=[], metavar="Regex", action=modded_argparse.SubRegexAction, help="--name-sub but for directory names")
_group.add_argument("--escape"                    , "-e", action="store_true"                   , help="Escape back slashes, newlines, carriage returns, and non-printable characters")

_group=parser.add_argument_group("Misc.")
_group.add_argument("--count"                     , "-c", nargs="+", default=[]                  , action=modded_argparse.CountAction , help="Count match/file/dir per file, dir, and/or total (Ex: --count fm dir-files)")
_group.add_argument("--limit"                     , "-l", nargs="+", default=utils.JSObj({}, default=0), action=modded_argparse.LimitAction , help="Limit match/file/dir per file, dir, and/or total (Ex: --limit filematch=1 total_dirs=5)")
parser.add_line()
_group.add_argument("--depth-first"               ,       action="store_true"                      , help="Enter subdirectories before processing files")
_group.add_argument("--glob-root-dir"             ,                                                  help="Root dir to run globs in (JANK)")
parser.add_line()
_group.add_argument("--match-whole-lines"         , "-L", action="store_true"                      , help="Match whole lines like FINDSTR")
_group.add_argument("--print-failed-files"        ,       action="store_true"                      , help="Print file names even if they fail (Partially broken)")
_group.add_argument("--json"                      , "-j", action="store_true"                      , help="Print output as JSON")
_group.add_argument("--no-warn"                   ,       action="store_true"                      , help="Don't print warning messages")
_group.add_argument("--hard-warn"                 ,       action="store_true"                      , help="Throw errors instead of warnings")
_group.add_argument("--weave-matches"             , "-w", action="store_true"                      , help="Weave regex matchdes (print first results for each get regex, then second results, etc.)")
_group.add_argument("--strict-weave"              , "-W", action="store_true"                      , help="Only print full weave sets")

_group=parser.add_argument_group("Exec")
_group.add_argument("--no-exec"                   ,       action="store_true"                      , help="Don't run any exec functions. Useful if using user input (STILL NOT SAFE)")
parser.add_line()
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
_group.add_argument("--order"                     ,       nargs="+", default=list(processors.funcs)          , help="The order in which modifications to matches are applied. Run jrep --help order for more info")
_group.add_argument("--no-flush"                  ,       action="store_true"                      , help="Improves speed by disabling manually flushing the stdout buffer (ideal for chaining commands)")
_group.add_argument("--force-flush"               ,       action="store_true"                      , help="Always flush STDOUT (slow)")
# _group.add_argument("--print-rundata"             ,       action="store_true"                      , help="Print raw runData JSON at the end (used for debugging)")
_group.add_argument("--verbose"                   , "-v", action="store_true"                      , help="Verbose info")

# Helper functions
def handleCount(parsedArgs, ofmt, rules, runData):
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

def fileContentsDontMatter(parsedArgs):
	"""
		If file contents don't matter, tell getFiles to not even run open() on them
		JREP doesn't load file contents into memory (it uses mmap) but just opening a file handler takes time
	"""
	return not any(parsedArgs.regex) and\
	       not parsedArgs.file_regex and not parsedArgs.file_anti_regex and\
	       not any(map(lambda x:re.search(r"[tdf]m", x), parsedArgs.limit.keys())) and\
	       not any(map(lambda x:re.search(r"^[tdf]m(([pf]c)?[tr])?$", x), parsedArgs.count))

def getFiles(parsedArgs, runData, stdin):
	"""
		Yields files selected with --file and --glob
		Stdin has a filename of -
		On Windows, empty files use a bytes object instead of mmap
		Stdin always uses a bytes object
		If the contents of a file are irrelevant (see: fileContentsDontMatter), b"" is always used instead of mmap
	"""
	globStuff=[runData, parsedArgs.sort_regex, parsedArgs.depth_first, parsedArgs.sort_dir]
	def advancedGlob(pattern, recursive=False):
		"""
			A simple wrapper for glob.iglob that allows for using *:/ and ?:/ in glob patterns
			May cause issues with stuff like SD to USB adapters with no media inserted. I can't test that right now
		"""
		if pattern.startswith("*:") or pattern.startswith("?:"):
			for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
				yield from glob.iglob(*globStuff, letter+pattern[1:], recursive=recursive)
		else:
			yield from glob.iglob(*globStuff, pattern, recursive=recursive)

	def _getFiles():
		"""
			Get a raw list of files selected with --file and --glob
			This is just here so I don't have to write the mmap code twice
			Probably could replace the array addition with a few `yield from`s
		"""

		# Files
		verbose("Yielding STDIN files")
		# --stdin-files
		if stdin is not None and parsedArgs.stdin_files:
			yield from stdin.decode().splitlines()
		# --file

		verbose("Yielding files")
		yield from parsedArgs.file

		# Globs
		verbose("Yielding STDIN globs")
		# --stdin-globs
		if stdin is not None and parsedArgs.stdin_globs:
			for pattern in stdin.decode().splitlines():
				yield from advancedGlob(pattern, recursive=True)
		# --glob
		verbose("Yielding globs")
		for pattern in parsedArgs.glob:
			yield from advancedGlob(pattern, recursive=True)

	# Add stdin as a file
	if stdin is not None and not parsedArgs.stdin_files and not parsedArgs.stdin_globs:
		verbose("Processing STDIN")
		yield {"name":"-", "basename":"-", "relDir":"", "absDir":"", "data":stdin, "isDir": False, "stdin": True}

	for file in _getFiles():
		verbose(f"Pre-processing \"{file}\"")

		relDir, basename=os.path.dirname(file), os.path.basename(file)
		absDir=os.path.normpath(os.path.join(os.getcwd(), relDir))
		ret={"name": file, "basename":basename, "relDir":relDir, "absDir":absDir, "data": b"", "isDir": False, "stdin": False}
		if os.path.isfile(file):
			if fileContentsDontMatter(parsedArgs) or not utils.filenameChecker(parsedArgs, ret):
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

noLimits=[]
def checkLimitType(parsedArgs, runData, sn, filters="ptf"):
	cats={"d":"t", "f":"td", "m":"tdf"}[sn]
	#if sn in noLimits:
	#	return False

	noLimitType=True
	for category in cats:
		ret=checkLimitCategory(parsedArgs, runData, category+sn, filters=filters)
		if ret is False:
			noLimitType=False
		if ret is True:
			return True

	if noLimitType:
		for cat in cats:
			noLimits.remove(cat+sn)
		noLimits.append(sn)
	return False

def checkLimitCategory(parsedArgs, runData, sn, filters="ptf"):
	if sn in noLimits or sn[1] in noLimits:
		return None

	noLimitCategory=True
	for filter in filters:
		ret=checkLimit(parsedArgs, runData, sn+filter)
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

def checkLimit(parsedArgs, runData, sn):
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
	value=getLimitValue(runData, sn)
	return value>=limit

def getLimitValue(runData, sn):
	nameMap={"t":"total","d":"dir","f":"file","m":"match"}
	typeMap={"t":"total","p":"passed","f":"failed","h":"handled"}
	plural="e"*(sn[1]=="m")+"s"
	try:
		return runData[nameMap[sn[0]]][typeMap[sn[2]]+nameMap[sn[1]].title()+plural]
	except KeyError:
		return 0

import json
def main(parsedArgs=None, returnData=False, returnJSON=False, stdout=sys.stdout.buffer, stdin=True):
	if parsedArgs is None          : parsedArgs=parser.parse_args()
	if isinstance(parsedArgs, list): parsedArgs=parser.parse_args(parsedArgs)
	if isinstance(parsedArgs, modded_argparse.argparse.Namespace): parsedArgs=dict(parsedArgs._get_kwargs())
	if isinstance(parsedArgs, dict): parsedArgs=utils.JSObj(parsedArgs)
	ofmt=utils.makeOFMT(parsedArgs)
	ret={
		# "arguments":{},
		"files":[],
		"matches":[]
	}

	if parsedArgs.json: returnJSON=True
	if returnJSON     : returnData=True
	if stdout is None : stdout=open(os.devnull, "wb")
	_stdout=stdout
	if returnData: stdout=open(os.devnull, "wb")
	STDIN=None
	if not isinstance(stdin, bool):
		STDIN=stdin
	if stdin is True and not os.isatty(sys.stdin.fileno()):
		STDIN=sys.stdin.buffer.read()

	# Handle --enhanced-engine
	if parsedArgs.enhanced_engine:
		if _regex is None:
			raise ModuleNotFoundError("Third party module 'regex' isn't available")
		re=_regex
	else:
		re=_re

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
			"dirsPerRegex":[0 for _ in parsedArgs.regex],

			"totalFiles"  :0,
			"passedFiles" :0,
			"handledFiles":0,
			"failedFiles" :0,
			"totalFilesPerRegex"  :[0 for _ in parsedArgs.regex],
			"passedFilesPerRegex" :[0 for _ in parsedArgs.regex],
			"handledFilesPerRegex":[0 for _ in parsedArgs.regex],
			#"failedFilesPerRegex" :[],

			"totalMatches" :0,
			"passedMatches":0,
			"failedMatches":0,
			"totalMatchesPerRegex" :[0 for _ in parsedArgs.regex],
			"passedMatchesPerRegex":[0 for _ in parsedArgs.regex],
			"failedMatchesPerRegex":[0 for _ in parsedArgs.regex],
		},
		"matchedStrings":set(),  # --no-duplicates handler
		"filenames":[],
		"currDir":None,
		"lastDir":None,
		"doneDir":False,
		"flushSTDOUT":True,
	}
	# Decide whether or not to flush STDOUT after pritning matches/names/dirs
	if (parsedArgs.no_flush or not os.isatty(sys.stdout.fileno())) and not parsedArgs.force_flush:
		runData["flushSTDOUT"]=False

	# Remove unneeded match handlers
	def orderRemove(parsedArgs, x):
		if x in parsedArgs.order:
			parsedArgs.order.remove(x)
	if not parsedArgs.replace                 : orderRemove(parsedArgs, "replace")
	if not parsedArgs.match_whole_lines       : orderRemove(parsedArgs, "match-whole-lines")
	if not parsedArgs.sub                     : orderRemove(parsedArgs, "sub")
	if not parsedArgs.stdin_anti_match_strings: orderRemove(parsedArgs, "stdin-anti-match-strings")
	if not parsedArgs.match_regex and not parsedArgs.match_anti_regex and not parsedArgs.match_ignore_regex: orderRemove(parsedArgs, "match-regex")
	if not parsedArgs.no_name_duplicates      : orderRemove(parsedArgs, "no-name-duplicates")
	if not parsedArgs.no_duplicates           : orderRemove(parsedArgs, "no-duplicates")

	# The main file loop
	for fileIndex, file in enumerate(utils.sortFiles(getFiles(parsedArgs, runData, STDIN), parsedArgs.sort_regex, key=parsedArgs.sort), start=1):
		verbose(f"Processing \"{file['name']}\"")

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
					handleCount(parsedArgs, ofmt, rules=["dir"], runData=runData)
				# Handle --limit total-dir
			if checkLimitCategory(parsedArgs, runData, "td"):
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
		nameRegexResult=utils.filenameChecker(parsedArgs, file)
		if nameRegexResult is False:
			verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched a fail regex; Continuing...")
			runData["dir"  ]["failedFiles"]+=1
			runData["total"]["failedFiles"]+=1
			runData["file" ]["passed"     ]=False
		elif nameRegexResult is None:
			verbose(f"File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" matched an ignore regex; Continuing...")
			runData["file"]["passed"]=False

		# Handle --file-regex stuff
		fileRegexResult=utils.regexCheckerThing(
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
				dirRegexResult=utils.dirnameChecker(parsedArgs, runData["currDir"])

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
					if func=="no-name-duplicates":
						try:
							processors.funcs["no-name-duplicates"](parsedArgs, file)
						except utils.NextFile:
							break
					elif func=="print-dir-name":
						processors.funcs["print-dir-name"](parsedArgs, runData, ofmt, runData["currDir"])
					elif func=="print-name":
						if returnData and not runData["file"]["printedName"]:
							ret["files"].append({x:file[x] for x in file if x!="data"})
						processors.funcs["print-name"](parsedArgs, runData, ofmt, file)

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
					#regex=regex.encode(errors="ignore")

					# Probably a bad idea, performance wise
					#if parsedArgs.string:
					#	regex=re.escape(regex)

					# Process matches
					for matchIndex, match in enumerate(regex.finditer(file["data"]), start=1):
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
						match=utils.JSObj({
							0:match[0],
							#**dict(enumerate(match.groups(), start=1)),
							"groups":match.groups,
							"span":match.span,
							"re":match.re
						})

						# Handle matches
						for func in parsedArgs.order:
							try:
								if func=="print-name" and returnData and not runData["file"]["printedName"]:
									ret["files"].append({x:file[x] for x in file if x!="data"})
								match=processors.funcs[func](
									regexIndex=regexIndex,
									regex=regex,
									file=file,
									runData=runData,
									parsedArgs=parsedArgs,
									match=match,
									currDir=runData["currDir"],
									re=re,
									ofmt=ofmt,
									stdout=stdout
								) or match
							except utils.NextMatch:
								verbose("NextMatch")
								break
							except utils.NextFile:
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
							if returnData:
								ret["matches"].append(match)
						# Handle --match-limit, --dir-match-limit, and --total-match-limit
						if "m" not in noLimits and checkLimitType(parsedArgs, runData, "m"):
							break

				except Exception as AAAAA:
					warn(f"Cannot process \"{file['name']}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}", error=AAAAA)

		if parsedArgs.print_failed_files and not runData["file"]["passed"]:
			verbose(f"\"{file['name']}\" didn't match any file regexes, but --print-non-matching-files was specified")
			processors.funcPrintFailedFile(parsedArgs, file, runData)

		if parsedArgs.weave_matches:
			f=zip if parsedArgs.strict_weave else itertools.zip_longest
			for matches in f(*runData["file"]["matches"]):
				for regexIndex, match in enumerate(matches):
					processors.printMatch(parsedArgs, runData, match, regexIndex)

		handleCount(parsedArgs, ofmt, rules=["file"], runData=runData)

		# Hanlde --limit total-matches and total-files
		if checkLimitCategory(parsedArgs, runData, "tm"):
			verbose("Total match limit reached; Exiting")
			break
		if checkLimitCategory(parsedArgs, runData, "tf", filters="ptfh"):
			verbose("Total file limit reached; Exiting")
			break

		# Handle --limit dir-files and dir-matches
		if checkLimitCategory(parsedArgs, runData, "df", filters="ptfh") or checkLimitCategory(parsedArgs, runData, "dm"):
			verbose("Dir limit(s) reached")
			runData["doneDir"]=True

	# --count dir-*
	if runData["currDir"] is not None and runData["total"]["totalDirs"]:
		# Only runs if files were handled in two or more directories
		handleCount(parsedArgs, ofmt, rules=["dir"], runData=runData)

	# --count total-*
	handleCount(parsedArgs, ofmt, rules=["total"], runData=runData)

	utils.execHandler(parsedArgs, parsedArgs.if_match_exec_after if runData["total"]["passedMatches"] else parsedArgs.if_no_match_exec_after)
	utils.execHandler(parsedArgs, parsedArgs.if_file_exec_after  if runData["total"]["passedFiles"  ] else parsedArgs.if_no_file_exec_after )
	utils.execHandler(parsedArgs, parsedArgs.if_dir_exec_after   if runData["total"]["passedDirs"   ] else parsedArgs.if_no_dir_exec_after  )

	if parsedArgs.json:
		_stdout.write(json.dumps(ret, cls=utils.JSObjEncoder).encode())
	elif returnJSON:
		return json.loads(json.dumps(ret, cls=utils.JSObjEncoder))
	elif returnData:
		return ret

if __name__=="__main__":
	main()
