#!/usr/bin/python

from re import sub
from utilities import import_module_error, sprintf

try:
    from prompt_toolkit.formatted_text import HTML
except ImportError:
    import_module_error("prompt_toolkit")


class Echo:
	_bash_colors: dict = {
		"black": "0;30",
	    "dark_gray": "1;30",
	    "red": "0;31",
	    "light_red": "1;31",
	    "green": "0;32",
	    "light_green": "1;32",
	    "brown_orange": "0;33",
	    "yellow": "1;33",
	    "blue": "0;34",
	    "light_blue": "1;34",
	    "purple": "0;35",
	    "light_purple": "1;35",
	    "cyan": "0;36",
	    "light_cyan": "1;36",
	    "light_gray": "0;37",
	    "white": "1;37"
	}

	@staticmethod
	def bash(target: str, color: str = "white"):
		if color in Echo._bash_colors:
			c = Echo._bash_colors[color]

			return f"\033[{c}m{target}\033[0m"
		return target

	@staticmethod
	def ansi(target: str, *values: str):
		return HTML(sprintf(
            target,
            *values
        ))
