# JREP
 James' GREP

JREP is a work-in-process replacement/companion for the Linux command GREP designed to be cross-platform, feature rich, and very intuitive.

Basically I got annoyed at the lack of GREP for Windows and decided to do it myself.

The current --help message:

```
usage: jrep.py [-h] [--string] [--no-duplicates]
               [--anti-regex ANTI_REGEX [ANTI_REGEX ...]]
               [--files FILES [FILES ...]] [--globs GLOBS [GLOBS ...]]
               [--stdin-files | --stdin-globs] [--name-regex NAME_REGEX]
               [--full-name-regex FULL_NAME_REGEX]
               [--name-anti-regex NAME_ANTI_REGEX]
               [--full-name-anti-regex FULL_NAME_ANTI_REGEX] [--sort SORT]
               [--no-headers] [--print-directories] [--print-file-names]
               [--print-full-paths] [--print-posix-paths]
               [--dont-print-matches] [--print-match-offset]
               [--print-match-range] [--count] [--total-count]
               [--replace REPLACE] [--sub SUB [SUB ...]] [--escape]
               [--file-match-limit FILE_MATCH_LIMIT]
               [--dir-match-limit DIR_MATCH_LIMIT]
               [--total-match-limit TOTAL_MATCH_LIMIT]
               [--dir-file-limit DIR_FILE_LIMIT]
               [--total-file-limit TOTAL_FILE_LIMIT] [--verbose]
               [regex]

positional arguments:
  regex                 Regex to test file contents for. omit to always match

options:
  -h, --help            show this help message and exit
  --string, -s          Test for strings instead of regex
  --no-duplicates, -D   Don't print duplicate matches
  --anti-regex ANTI_REGEX [ANTI_REGEX ...]
                        Regexes for files to not match
  --files FILES [FILES ...], -f FILES [FILES ...]
                        The file(s) to check
  --globs GLOBS [GLOBS ...], -g GLOBS [GLOBS ...]
                        The glob(s) to check
  --stdin-files, -F     Treat STDIN as a list of files
  --stdin-globs, -G     Treat STDIN as a list of globs
  --name-regex NAME_REGEX, -t NAME_REGEX
                        Regex to test against relative file name
  --full-name-regex FULL_NAME_REGEX, -T FULL_NAME_REGEX
                        Regex to test against absolute file name
  --name-anti-regex NAME_ANTI_REGEX
                        Like --name-regex but excludes file names that match
  --full-name-anti-regex FULL_NAME_ANTI_REGEX
                        Like --full-name-regex but excludes file names that
                        match
  --sort SORT, -S SORT  Sort files by ctime, mtime, atime, name, or size.
                        Prefix key with "r" to reverse
  --no-headers, -H      Don't print match: or file: before lines
  --print-directories, -d
                        Print names of explored directories
  --print-file-names, -n
                        Print file names as well as matches
  --print-full-paths, -p
                        Print full file paths
  --print-posix-paths, -P
                        Print C:/stuff instead of C:\stuff
  --dont-print-matches, -N
                        Don't print matches (use with -n to only print names)
  --print-match-offset, -o
                        Print the match offset (ignores -H)
  --print-match-range, -O
                        Print the match range (implies -o)
  --count, -c           Count matches per file
  --total-count, -C     Total --count of all files
  --replace REPLACE, -r REPLACE
                        Regex replacement
  --sub SUB [SUB ...], -R SUB [SUB ...]
                        re.sub argument pairs after -r
  --escape, -e          Replace \, carriage returns, and newlines with \\, \r,
                        and \n
  --file-match-limit FILE_MATCH_LIMIT, --fml FILE_MATCH_LIMIT
                        Max matches per file
  --dir-match-limit DIR_MATCH_LIMIT, --dml DIR_MATCH_LIMIT
                        Max matches per directory
  --total-match-limit TOTAL_MATCH_LIMIT, --tml TOTAL_MATCH_LIMIT
                        Max matches overall
  --dir-file-limit DIR_FILE_LIMIT, --dfl DIR_FILE_LIMIT
                        Max files per directory
  --total-file-limit TOTAL_FILE_LIMIT, --tfl TOTAL_FILE_LIMIT
                        Max files overall
  --verbose, -v         Verbose info
```

Some example snippits:

- `jrep -g *.py -NCH --fml 1` - Count all `.py` files in a directory
- `jrep -g */*.mp4 -nNd --dfl 5 | jrep "Directory: (.+)(\nFile: .+){5}" -r \1 -H` - List all directories with 5 or more `.mp4` files
