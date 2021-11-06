import argparse, os, sys, re, glob, mmap, copy, itertools, functools

"""
	JREP
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

parser=argparse.ArgumentParser()

parser.add_argument("regex"                 ,       nargs="*", default=[""], help="Regex(es) to process matches for")
parser.add_argument("--string"              , "-s", action="store_true"    , help="Test for strings instead of regex")
parser.add_argument("--no-duplicates"       , "-D", action="store_true"    , help="Don't print duplicate matches")

parser.add_argument("--file"                , "-f", nargs="+", default=[], help="The file(s) to check")
parser.add_argument("--glob"                , "-g", nargs="+", default=[], help="The glob(s) to check")

_stdin=parser.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"         , "-F", action="store_true"  , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"         , "-G", action="store_true"  , help="Treat STDIN as a list of globs")

parser.add_argument("--name-regex"          , "-t", nargs="+", default=[], help="Regex to test relative file names for")
parser.add_argument("--full-name-regex"     , "-T", nargs="+", default=[], help="Regex to test absolute file names for")
parser.add_argument("--name-anti-regex"     ,       nargs="+", default=[], help="Like --name-regex      but excludes file names that match")
parser.add_argument("--full-name-anti-regex",       nargs="+", default=[], help="Like --full-name-regex but excludes file names that match")
parser.add_argument("--file-regex"          ,       nargs="+", default=[], help="Regexes to test file contents for")
parser.add_argument("--file-anti-regex"     ,       nargs="+", default=[], help="Like --file-regex but excludes files that match")

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

parser.add_argument("--file-match-limit"    , "--fml", type=int, default=0, help="Max matches per file")
parser.add_argument("--dir-match-limit"     , "--dml", type=int, default=0, help="Max matches per directory")
parser.add_argument("--total-match-limit"   , "--tml", type=int, default=0, help="Max matches overall")
parser.add_argument("--dir-file-limit"      , "--dfl", type=int, default=0, help="Max files per directory")
parser.add_argument("--total-file-limit"    , "--tfl", type=int, default=0, help="Max files overall")
parser.add_argument("--total-dir-limit"     , "--tdl", type=int, default=0, help="Max dirs overall")

parser.add_argument("--file-match-count"    , "--fmc", "-c", action="store_true", help="Count matches per file")
parser.add_argument("--dir-match-count"     , "--dmc",       action="store_true", help="Count matches per directory")
parser.add_argument("--total-match-count"   , "--tmc", "-C", action="store_true", help="Count matches overall")
parser.add_argument("--dir-file-count"      , "--dfc",       action="store_true", help="Count files per directory")
parser.add_argument("--total-file-count"    , "--tfc",       action="store_true", help="Count files overall")
parser.add_argument("--total-dir-count"     , "--tdc",       action="store_true", help="Count dirs overall")

parser.add_argument("--verbose"             , "-v", action="store_true"  , help="Verbose info")
parsedArgs=parser.parse_args()

if parsedArgs.verbose:
	print("Verbose: JREP preview version")
	print(parsedArgs)

if not (len(parsedArgs.replace)==0 or len(parsedArgs.replace)==1 or len(parsedArgs.replace)==len(parsedArgs.regex)):
	print("Error: Length of --replace must be either 1 or equal to the number of regexes", file=sys.stderr)
	exit(1)

# Simple implementation of --escape
if parsedArgs.escape:
	if parsedArgs.verbose:
		print("Verbose: Added --escape args to --sub")
	parsedArgs.sub.extend(["\\", "\\\\", "\r", "\\r", "\n", "\\n"])
	if parsedArgs.verbose:
		print("Verbose: --sub is now", parsedArgs.sub)

# Dumb output fstring generation stuff
_header=not parsedArgs.no_headers
_mOffs1=parsedArgs.print_match_offset or parsedArgs.print_match_range
_mOffs2=parsedArgs.print_match_range
_mRange=("{range[0]:08x}"*_mOffs1)+("-{range[1]:08x}"*_mOffs2)
_mAt=_header and _mOffs1
_mRange=(" at "*_mAt) + (_mRange) + (": "*(_header or _mRange!=""))

# Output fstrings to make later usage easier
ofmt={
	"dname": (("Directory: "        *_header)+"{dname}") * parsedArgs.print_directories,
	"fname": (("File: "             *_header)+"{fname}") * parsedArgs.print_file_names,
	"match": (("Match"              *_header)+ _mRange ) * (not parsedArgs.dont_print_matches),

	"fmcnt": (("File match count: " *_header)+"{count}") * parsedArgs.file_match_count,
	"dmcnt": (("Dir match count: "  *_header)+"{count}") * parsedArgs.dir_match_count,
	"dfcnt": (("Dir file count: "   *_header)+"{count}") * parsedArgs.dir_file_count,
	"tmcnt": (("Total match count: "*_header)+"{count}") * parsedArgs.total_match_count,
	"tfcnt": (("Total file count: " *_header)+"{count}") * parsedArgs.total_file_count,
	"tdcnt": (("Total dir count: "  *_header)+"{count}") * parsedArgs.total_dir_count,
}

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

def findAllSubs(pattern, replace, string):
	"""
		re.sub but yield all replaced substrings instead of returning the final string
		This is a very slow function but it works
		Runs re.sub with the count kwarg set to increasing values
		It uses this to keep track of how much the string length changes to find out what parts of the result to return
	"""
	offs=0
	last=string
	for index, match in enumerate(re.finditer(pattern, string), start=1):
		subbed=re.sub(pattern, replace, string, count=index)
		loffs=offs
		offs+=len(subbed)-len(last)
		yield JSObj({
			"span": lambda:(loffs+match.span()[0],offs+match.span()[1]),
			0     :  subbed[loffs+match.span()[0]:offs+match.span()[1]]
		})
		last=subbed

def fileContentsDontMatter():
	return parsedArgs.dont_print_matches\
	       and not any(parsedArgs.regex)       and not parsedArgs.file_match_limit\
	       and not parsedArgs.dir_match_limit  and not parsedArgs.total_match_limit\
	       and not parsedArgs.file_regex       and not parsedArgs.file_anti_regex\
	       and not parsedArgs.file_match_count and not parsedArgs.dir_match_count and not parsedArgs.total_match_count

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
		if parsedArgs.verbose:
			print("Verbose: Yielding files")
		# --stdin-files
		if not os.isatty(sys.stdin.fileno()) and parsedArgs.stdin_files:
			yield from sys.stdin.read().splitlines()
		# --file
		yield from parsedArgs.file
		
		# Globs
		if parsedArgs.verbose:
			print("Verbose: Yielding globs") # r/PythonOOC
		# --stdin-globs
		if not os.isatty(sys.stdin.fileno()) and parsedArgs.stdin_globs:
			for pattern in sys.stdin.read().splitlines():
				yield from glob.iglob(pattern, recursive=True)
		# --glob
		for pattern in parsedArgs.glob:
			yield from glob.iglob(pattern, recursive=True)

	# Add stdin as a file
	if not os.isatty(sys.stdin.fileno()) and not parsedArgs.stdin_files and not parsedArgs.stdin_globs:
		if parsedArgs.verbose:
			print("Verbose: Processing STDIN")
		yield {"name":"-", "data":sys.stdin.read().encode(errors="ignore"), "isDir": False, "stdin": True}

	for file in _getFiles():
		if parsedArgs.verbose:
			print(f"Verbose: Processing file \"{file}\"")

		if os.path.isfile(file):
			if fileContentsDontMatter():
				# Does the file content matter? No? Ignore it then
				if parsedArgs.verbose:
					print("Verbose: Optimizing away actually opening the file")
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
					print(f"Warning: Cannot process \"{file}\" because of \"{AAAAA}\"", file=sys.stderr)
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

# Abbreviations to make my editor not show a horizontal scrollbar (my version of PEP8)
_FML=parsedArgs.file_match_limit
_DML=parsedArgs.dir_match_limit
_TML=parsedArgs.total_match_limit
_DFL=parsedArgs.dir_file_limit
_TFL=parsedArgs.total_file_limit
_TDL=parsedArgs.total_dir_limit

# Tracking stuffs
matchedStrings=[] # --no-duplicates handler
dirData={} # --file-limit and --dir-match-limit
totalMatches=0
totalFiles=0
fileDir=None
lastDir=None
for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
	if parsedArgs.verbose:
		print(f"Verbose: Processing {file}")

	# Handle --name-regex, --full-name-regex, --name-anti-regex, and--full-name-anti-regex
	if not all(map(lambda x:re.search(x,                  file["name"] ), parsedArgs.name_regex          )) or\
	   not all(map(lambda x:re.search(x, os.path.realpath(file["name"])), parsedArgs.full_name_regex     )) or\
	       any(map(lambda x:re.search(x,                  file["name"] ), parsedArgs.name_anti_regex     )) or\
	       any(map(lambda x:re.search(x, os.path.realpath(file["name"])), parsedArgs.full_name_anti_regex)):
		# Really should make how this works configurable
		if parsedArgs.verbose:
			print(f"Verbose: File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" failed the name regexes")
		continue

	# --file-limit, --dir-match-limit, --dir-file-count, and --dir-match-count
	lastDir=fileDir
	fileDir=file["name"]
	if not file["isDir"]:
		fileDir=os.path.dirname(fileDir)

	# --dir-match-count and --dir-file-count
	if lastDir!=None and lastDir!=fileDir:
		if parsedArgs.dir_match_count:
			print(ofmt["dmcnt"].format(count=dirData[lastDir]["matches"]))
		if parsedArgs.dir_file_count:
			print(ofmt["dfcnt"].format(count=dirData[lastDir]["files"]))

	# --print-directories
	if parsedArgs.print_directories and fileDir not in dirData:
		print(ofmt["dname"].format(dname=processDirName(fileDir)))

	# Keeps track of, well, directory data
	if fileDir not in dirData:
		if parsedArgs.verbose:
			print(f"Verbose: Adding {fileDir} to dirData")
		dirData[fileDir]={"files":0, "matches":0}

	if _TDL and len(dirData.keys())>_TDL:
		break

	# Handle --file-limit
	# Really slow on big directories
	if (_DFL!=0 and dirData[fileDir]["files"]==_DFL) or (_DML!=0 and dirData[fileDir]["matches"]>=_DML):
		continue
	dirData[fileDir]["files"]+=1

	if file["isDir"]:
		continue

	# Main matching stuff
	_continue=False # PEP-3136 would've come in clutch here
	for regexIndex, regex in enumerate(parsedArgs.regex):
		if parsedArgs.verbose:
			print(f"Verbose: handling regex {regexIndex}: {regex}")
		try:
			printedName=False

			# Handle --file-regex and --file-anti-regex
			_fileRegexCheck=lambda regex: re.search(regex.encode(errors="ignore"), file["data"])
			if any(map(_fileRegexCheck, parsedArgs.file_anti_regex)) or not all(map(_fileRegexCheck, parsedArgs.file_regex)):
				_continue=True
				break

			# Turn regex into bytes
			regex=regex.encode(errors="ignore")

			# Probably a bad idea
			if parsedArgs.string:
				regex=re.escape(regex)

			# Handle --replace
			if parsedArgs.replace:
				if len(parsedArgs.replace)==1:
					replacement=parsedArgs.replace[0]
				elif len(parsedArgs.replace)==len(parsedArgs.regex):
					replacement=parsedArgs.replace[regexIndex]
				matches=findAllSubs(regex, replacement.encode(errors="ignore"), file["data"])
			else:
				matches=re.finditer(regex, file["data"])

			# Process matches
			matchIndex=0 # Just makes --file-match-count stuff easier
			for matchIndex, match in enumerate(matches, start=1):
				# Print file name
				if not printedName:
					if parsedArgs.print_file_names:
						print(ofmt["fname"].format(fname=processFileName(file["name"])))
					printedName=True
					totalFiles+=1

				totalMatches+=1
				dirData[fileDir]["matches"]+=1

				# Quick optimization for when someone just wants filenames
				if fileContentsDontMatter():
					if parsedArgs.verbose:
						print("Verbose: Optimizing away actually reading the file")
					break

				# Handle --sub
				# TYSM mCoding for explaining how zip works
				# (zip(*arr) is a bit like transposing arr (arr[y][x] becomes arr[x][y]))
				for pair in zip(parsedArgs.sub[0::2], parsedArgs.sub[1::2]):
					match=JSObj({
						0     : re.sub(pair[0].encode(), pair[1].encode(), match[0]),
						"span": match.span
					})

				# Print matches
				if not parsedArgs.dont_print_matches and match[0] not in matchedStrings:
					sys.stdout.buffer.write(ofmt["match"].format(range=match.span()).encode())
					sys.stdout.buffer.write(match[0])

				# Handle --no-duplicates
				if parsedArgs.no_duplicates:
					matchedStrings.append(match[0].decode())

				# Handle --match-limit, --dir-match-limit, and --total-match-limit
				if (_FML!=0 and matchIndex>=_FML) or\
				   (_DML!=0 and dirData[fileDir]["matches"]>=_DML) or\
				   (_TML!=0 and totalMatches>=_TML):
					break

			# Print match count (--count)
			if parsedArgs.file_match_count and matchIndex:
				print(ofmt["fmcnt"].format(count=matchIndex))

		except Exception as AAAAA:
			print(f"Warning: Cannot process \"{file}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}", file=sys.stderr)
	if _continue:
		continue

	# Hanlde --total-match-limit and --total-file-limit
	if (_TML!=0 and totalMatches>=_TML) or (_TFL!=0 and fileIndex>=_TFL):
		break

# --dir-match-count and --dir-file count
if fileDir!=None:
	if parsedArgs.dir_match_count:
		print(ofmt["dmcnt"].format(count=dirData[fileDir]["matches"]))
	if parsedArgs.dir_file_count:
		print(ofmt["dfcnt"].format(count=dirData[fileDir]["files"]))

# --total-match-count, --total-file-count, and --total-dir-count
if parsedArgs.total_match_count:
	print(ofmt["tmcnt"].format(count=totalMatches))
if parsedArgs.total_file_count:
	print(ofmt["tfcnt"].format(count=totalFiles))
if parsedArgs.total_dir_count:
	print(ofmt["tdcnt"].format(count=len(dirData.keys())))
