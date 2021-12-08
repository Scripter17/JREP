# JREP

JREP is a general-purpose command line utility that takes the basic concept of GREP and transforms it into an infinitely more versatile tool fit for the modern world  

Until I can make a proper README, here's the output of `jrep --help`

<!--<HELP MSG>-->
```
usage: jrep.py [-h] [--string] [--no-duplicates] [--file FILE [FILE ...]]
               [--glob GLOB [GLOB ...]] [--stdin-files | --stdin-globs]
               [--name-regex NAME_REGEX [NAME_REGEX ...]]
               [--name-anti-regex NAME_ANTI_REGEX [NAME_ANTI_REGEX ...]]
               [--name-ignore-regex NAME_IGNORE_REGEX [NAME_IGNORE_REGEX ...]]
               [--full-name-regex FULL_NAME_REGEX [FULL_NAME_REGEX ...]]
               [--full-name-anti-regex FULL_NAME_ANTI_REGEX [FULL_NAME_ANTI_REGEX ...]]
               [--full-name-ignore-regex FULL_NAME_IGNORE_REGEX [FULL_NAME_IGNORE_REGEX ...]]
               [--dir-name-regex DIR_NAME_REGEX [DIR_NAME_REGEX ...]]
               [--dir-name-anti-regex DIR_NAME_ANTI_REGEX [DIR_NAME_ANTI_REGEX ...]]
               [--full-dir-name-regex FULL_DIR_NAME_REGEX [FULL_DIR_NAME_REGEX ...]]
               [--full-dir-name-anti-regex FULL_DIR_NAME_ANTI_REGEX [FULL_DIR_NAME_ANTI_REGEX ...]]
               [--file-regex FILE_REGEX [FILE_REGEX ...]]
               [--file-anti-regex FILE_ANTI_REGEX [FILE_ANTI_REGEX ...]]
               [--match-regex MATCH_REGEX [MATCH_REGEX ...]]
               [--match-anti-regex MATCH_ANTI_REGEX [MATCH_ANTI_REGEX ...]]
               [--sort SORT] [--no-headers] [--print-directories]
               [--print-file-names] [--print-full-paths] [--print-posix-paths]
               [--dont-print-matches] [--print-match-offset]
               [--print-match-range] [--replace REPLACE [REPLACE ...]]
               [--sub SUB [SUB ...]] [--escape] [--count COUNT [COUNT ...]]
               [--limit LIMIT [LIMIT ...]] [--depth-first]
               [--glob-root-dir GLOB_ROOT_DIR] [--match-whole-lines]
               [--print-non-matching-files] [--no-warn] [--weave-matches]
               [--strict-weave] [--order ORDER [ORDER ...]] [--verbose]
               [regex ...]

positional arguments:
  regex                 Regex(es) to process matches for

options:
  -h, --help            show this help message and exit
  --string, -s          Test for strings instead of regex
  --no-duplicates, -D   Don't print duplicate matches
  --file FILE [FILE ...], -f FILE [FILE ...]
                        The file(s) to check
  --glob GLOB [GLOB ...], -g GLOB [GLOB ...]
                        The glob(s) to check
  --stdin-files, -F     Treat STDIN as a list of files
  --stdin-globs, -G     Treat STDIN as a list of globs
  --name-regex NAME_REGEX [NAME_REGEX ...], -t NAME_REGEX [NAME_REGEX ...]
                        If a file name matches all supplied regexes, keep
                        going. Otherwise continue
  --name-anti-regex NAME_ANTI_REGEX [NAME_ANTI_REGEX ...], -T NAME_ANTI_REGEX [NAME_ANTI_REGEX ...]
                        Like --name-regex but excludes file names that match
  --name-ignore-regex NAME_IGNORE_REGEX [NAME_IGNORE_REGEX ...]
                        Like --name-anti-regex but doesn't contribute to
                        --count dir-failed-files
  --full-name-regex FULL_NAME_REGEX [FULL_NAME_REGEX ...]
                        Like --name-regex but for absolute file paths (C:/xyz
                        instead of xyz)
  --full-name-anti-regex FULL_NAME_ANTI_REGEX [FULL_NAME_ANTI_REGEX ...]
                        Like --full-name-regex but excludes file names that
                        match
  --full-name-ignore-regex FULL_NAME_IGNORE_REGEX [FULL_NAME_IGNORE_REGEX ...]
                        Like --full-name-anti-regex but doesn't contribute to
                        --count dir-failed-files
  --dir-name-regex DIR_NAME_REGEX [DIR_NAME_REGEX ...]
                        If a directory name matches all supplied regexes,
                        enter it. Otherwise continue
  --dir-name-anti-regex DIR_NAME_ANTI_REGEX [DIR_NAME_ANTI_REGEX ...]
                        --dir-name-regex but ignore directories that match any
                        of the supplies regexes
  --full-dir-name-regex FULL_DIR_NAME_REGEX [FULL_DIR_NAME_REGEX ...]
                        --dir-name-regex but applied to full directory paths
  --full-dir-name-anti-regex FULL_DIR_NAME_ANTI_REGEX [FULL_DIR_NAME_ANTI_REGEX ...]
                        --dir-name-anti-regex but applied to full directory
                        paths
  --file-regex FILE_REGEX [FILE_REGEX ...]
                        Regexes to test file contents for
  --file-anti-regex FILE_ANTI_REGEX [FILE_ANTI_REGEX ...]
                        Like --file-regex but excludes files that match
  --match-regex MATCH_REGEX [MATCH_REGEX ...]
                        Basically applies str.split("*") to the list of
                        --match-regex. If a match matches all regexes in the
                        Nth --match-regex group (where N is the index of the
                        current get regex) continue processing the match,
                        otherwise move on to the next one
  --match-anti-regex MATCH_ANTI_REGEX [MATCH_ANTI_REGEX ...]
                        --match-regex but excludes matches that match any of
                        the supplies regexes
  --sort SORT, -S SORT  Sort files by ctime, mtime, atime, name, or size.
                        Prefix key with "r" to reverse. A windows-esque
                        "blockwise" sort is also available (todo: document)
  --no-headers, -H      Don't print match: or file: before lines
  --print-directories, -d
                        Print names of explored directories
  --print-file-names, -n
                        Print file names as well as matches
  --print-full-paths, -p
                        Print full file paths
  --print-posix-paths, -P
                        Print replace \ with / in file paths
  --dont-print-matches, -N
                        Don't print matches (use with --print-file-names to
                        only print names)
  --print-match-offset, -o
                        Print the match offset (ignores -H)
  --print-match-range, -O
                        Print the match range (implies -o)
  --replace REPLACE [REPLACE ...], -r REPLACE [REPLACE ...]
                        Regex replacement
  --sub SUB [SUB ...], -R SUB [SUB ...]
                        re.sub argument pairs after --replace is applied
  --escape, -e          Replace \, carriage returns, and newlines with \\, \r,
                        and \n
  --count COUNT [COUNT ...], -c COUNT [COUNT ...]
                        Count match/file/dir per file, dir, and/or total (Ex:
                        --count fm dir-files)
  --limit LIMIT [LIMIT ...], -l LIMIT [LIMIT ...]
                        Limit match/file/dir per file, dir, and/or total (Ex:
                        --limit filematch=1 total_dirs=5)
  --depth-first         Enter subdirectories before processing files
  --glob-root-dir GLOB_ROOT_DIR
                        Root dir to run globs in
  --match-whole-lines   Match whole lines like FINDSTR
  --print-non-matching-files
                        Print file names with no matches
  --no-warn             Don't print warning messages
  --weave-matches, -w   Weave regex matchdes
  --strict-weave, -W    Only print full match sets
  --order ORDER [ORDER ...]
                        The order in which modifications to matches are
                        applied
  --verbose, -v         Verbose info

```
<!--</HELP MSG>-->
