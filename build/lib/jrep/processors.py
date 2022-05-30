"""
	Functions for processing matches
"""

import sys
from . import utils

def funcReplace(parsedArgs, runData, match, regexIndex, **kwargs):
	"""
		Handle --replace
	"""
	replacement=parsedArgs.replace[regexIndex%len(parsedArgs.replace)]
	return utils.delayedSub(replacement.encode(errors="ignore"), match)

def funcSub(parsedArgs, runData, match, regexIndex, **kwargs):
	"""
		Handle --sub
	"""
	match[0]=utils._funcSub(parsedArgs.sub, match[0], regexIndex, **kwargs)
	return match

def funcMatchWholeLines(parsedArgs, runData, match, file, **kwargs):
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

def funcStdinAntiMatchStrings(parsedArgs, runData, match, **kwargs):
	if match[0] in _STDIN.splitlines():
		runData["total"]["failedMatches"        ]            +=1
		runData["dir"  ]["failedMatches"        ]            +=1
		runData["file" ]["failedMatches"        ]            +=1
		runData["total"]["failedMatchesPerRegex"][regexIndex]+=1
		runData["dir"  ]["failedMatchesPerRegex"][regexIndex]+=1
		runData["file" ]["failedMatchesPerRegex"][regexIndex]+=1
		raise utils.NextMatch()

def funcMatchRegex(parsedArgs, runData, match, regexIndex, **kwargs):
	"""
		Handle --match-regex and --match-anti-regex
		Because yes. Filtering matches by using another regex is a feature I genuinely needed
		Most features in JREP I have actually needed sometimes
	"""
	stdinThing=False
	if parsedArgs.stdin_anti_match_strings and _STDIN:
		stdinThing=match[0] in _STDIN.splitlines()
	matchRegexResult=not stdinThing and utils.regexCheckerThing(
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
		raise utils.NextMatch()
	elif matchRegexResult is None:
		raise utils.NextMatch()

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

	pDirName=utils.processDirName(parsedArgs, currDir)
	if parsedArgs.pre_dir_exec is not None:
		# --pre-dir-exec
		execHandler(parsedArgs.pre_dir_exec, pDirName)

	if parsedArgs.print_dir_names:
		sys.stdout.buffer.write(ofmt["dname"]+pDirName)
		sys.stdout.buffer.write(b"\n")
		if runData["flushSTDOUT"]:
			sys.stdout.buffer.flush()
		runData["dir"]["printedName"]=True

	if parsedArgs.dir_exec is not None:
		# --dir-exec
		execHandler(parsedArgs.dir_exec, pDirName)

def funcPrintName(parsedArgs, runData, file, **kwargs):
	"""
		Handle --print-names
	"""
	if runData["file"]["printedName"]:
		return

	if parsedArgs.if_file_exec_before is not None:
		# --if-file-exec-before
		execHandler(parsedArgs.if_file_exec_before)
		parsedArgs.if_file_exec_before=None

	pFileName=utils.processFileName(parsedArgs, file["name"])
	if parsedArgs.pre_file_exec is not None:
		# --pre-file-exec
		execHandler(parsedArgs.pre_file_exec, pFileName)

	if parsedArgs.print_file_names:
		sys.stdout.buffer.write(ofmt["fname"]+pFileName)
		sys.stdout.buffer.write(b"\n")
		if runData["flushSTDOUT"]:
			sys.stdout.buffer.flush()
	runData["file"]["printedName"]=True

	if parsedArgs.file_exec is not None:
		# --file-exec

		execHandler(parsedArgs.file_exec, pFileName)

def printMatch(parsedArgs, runData, match, regexIndex):
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
		out=match[0]
		if parsedArgs.escape:
			utils.escape(match[0])
		sys.stdout.buffer.write(out)
		sys.stdout.buffer.write(b"\n")
		if runData["flushSTDOUT"]:
			sys.stdout.buffer.flush()

	if parsedArgs.match_exec is not None:
		# --match-exec
		execHandler(parsedArgs.match_exec, match[0])

def funcPrintMatch(parsedArgs, runData, file, regexIndex, match, **kwargs):
	"""
		Print matches
	"""
	if parsedArgs.weave_matches:
		runData["file"]["matches"][regexIndex].append(match)
	else:
		printMatch(parsedArgs, runData, match, regexIndex)

def funcNoDuplicates(parsedArgs, runData, match, **kwargs):
	"""
		Handle --no-duplicates
	"""
	if match[0] in runData["matchedStrings"]:
		raise utils.NextMatch()
	runData["matchedStrings"].add(match[0])

def funcNoNameDuplicates(parsedArgs, runData, file, **kwargs):
	"""
		Handle --no-name-duplicates
	"""
	if utils.processFileName(parsedArgs, file["name"]) in runData["filenames"]:
		raise utils.NextFile()
	runData["filenames"].append(utils.processFileName(parsedArgs, file["name"]))

def funcPrintFailedFile(parsedArgs, runData, file, **kwargs):
	"""
		Print filename of failed file if --print-non-matching-files is specified
	"""
	funcPrintName(parsedArgs, runData, file, runData)

funcs={
	"replace"                 : funcReplace,
	"match-whole-lines"       : funcMatchWholeLines,
	"sub"                     : funcSub,
	"stdin-anti-match-strings":	funcStdinAntiMatchStrings,
	"match-regex"             : funcMatchRegex,
	"no-name-duplicates"      : funcNoNameDuplicates,
	"no-duplicates"           : funcNoDuplicates,
	"print-dir-name"          : funcPrintDirName,
	"print-name"              : funcPrintName,
	"print-match"             : funcPrintMatch,
}
