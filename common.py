import inspect

def verbose(x, override=False):
	calls=inspect.stack()[1:]
	print(f"Verbose on lines {', '.join([f'{call[2]}:{call[3]}' for call in calls])}: {x}")
def warn(x, error=None, override=False, hard=False):
	if hard:
		raise error or Exception(f"No error provided (Message: \"{x}\")")
	else:
		calls=inspect.stack()[1:]
		print(f"Waring on lines {', '.join([f'{call[2]}:{call[3]}' for call in calls])}: {x}", file=sys.stderr)
