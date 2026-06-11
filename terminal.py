#!/usr/bin/python

from typing import Optional, Any, Dict, List, Union
from subprocess import run, Popen, PIPE, STDOUT, CalledProcessError
from shlex import split as parse_params
from re import sub
from getpass import getpass
import os
import pwd
import glob
import copy
from utilities import (
	exec_exit, 
	is_empty,
	array_clear,
	sprintf,
	printinf,
	printalr,
	printerr,
	printsuc,
	import_module_error,
	is_scrambled
)

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter, NestedCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.formatted_text import HTML
except ImportError:
    import_module_error("prompt_toolkit")

try:
	from pynput import keyboard
except ImportError:
	import_module_error("pynput")
from echo import Echo
from thread_maid import ThreadMaid

BASE = os.path.dirname(__file__)
PID = str(os.getpid()).strip()
LOCK_FILE = "/tmp/powerconsole_hotkey.lock"

# commands_thread = ThreadMaid()
cuid = os.getuid()
cugid = os.getgid()
is_super_user = False if cuid != 0 else True
e = os.environ.copy()

""" TODO

	The whole autocompletion
	process doesn't work very well
"""
git_commands = {
	"add": {
		".": None
	},
	"commit": {
		"-m": None
	},
	"checkout": {
		"-b": None,
		"master": None,
		"main": None,
		"development": None
	},
	"status": None,
	"branch": None,
	"log": None
}
completer = {
	"clear": None,
	"exit": None,
	"delete-history": None,
	"reload": {
		"history": None,	
		"config": None	
	},
	"ln": {
		"-s": None
	},
	"cp": {
		"-r": None
	},
	"rm": {
		"-r": None
	},
	"cd": {},
	"mv": {}, 
	"nano": {}, 
	"vi": {}, 
	"vim": {}, 
	"subl": {}
}


def get_username():
    return pwd.getpwuid(cuid).pw_name


def escalate():
	global is_super_user

	try:
		password = getpass(f"[sudo] password for {get_username()}: ")
		run(
            ['sudo', '-S', '-v'], 
            input=password, 
            text=True, 
            check=True, 
            capture_output=True
        )
		is_super_user = True
		printinf("You are now super user")
	except PermissionError as pe:
		printerr(f"Unable to change uid: {pe}")
	except Exception as err:
		printerr(f"Unable to gain root privileges: {err}")


def deescalate():
	global is_super_user

	try:
		run(['sudo', '-k'])
		is_super_user = False
		printinf(f"You are now back to user {get_username()}")
	except Exception:
		printerr("Unable to return to original user")


def get_commands():
	process = Popen(
        ["ls", "/usr/bin"],
        stdin=PIPE,
        stderr=PIPE,
        stdout=PIPE
    )
	output, error = process.communicate()
	return output.decode().splitlines()


def get_local_commands():
	process = Popen(
        ["ls", f"/home/{get_username()}/.local/bin"],
        stdin=PIPE,
        stderr=PIPE, 
        stdout=PIPE
    )
	output, error = process.communicate()
	return output.decode().splitlines()


def get_files():
	try:
		if os.path.isdir(os.getcwd()):
			process = Popen(
		        ["ls -a", os.getcwd()],
		        stdin=PIPE, 
		        stderr=PIPE, 
		        stdout=PIPE
		    )
			output, error = process.communicate()
			return output.decode().splitlines()
	except (FileNotFoundError, OSError):
		pass

	return []


def is_git_repo() -> bool:
	try:
		if os.path.isdir(os.getcwd()):
			r = glob.glob(os.getcwd() + "/.git", recursive=False)

			return len(r) == 1
	except Exception:
		pass

	return False


def get_git_repo() -> str:
	process = Popen(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdin=PIPE, 
        stderr=PIPE, 
        stdout=PIPE
    )
	output, error = process.communicate()
	return output.decode().strip()


def autocomplete_cwd():
	global completer, git_commands

	suggestions = copy.deepcopy(completer)

	repo = get_git_repo()

	git_commands["push"] = {
		"origin": {}, 
		"master": None,
		"main": None,
		"development": None
	}
	git_commands["pull"] = {
		"origin": {
			"master": None,
			"main": None,
			"development": None
		}, 
		"master": None,
		"main": None,
		"development": None
	}
	git_commands["push"][repo] = None
	git_commands["pull"][repo] = None
	git_commands["push"]["origin"][repo] = None
	git_commands["pull"]["origin"][repo] = None

	suggestions["git"] = git_commands

	# Add /usr/bin/ commands
	for c in get_commands():
		suggestions[c] = None	

	# Add local commands	
	for c in get_local_commands():
		suggestions[c] = None	

	# Add files of the current directory
	for f in get_files():
		suggestions[f] = None

		for c in ["cd", "cp", "rm", "mv", "nano", "vi", "vim", "subl"]:
			if c in suggestions:
				if suggestions[c] is None:
					suggestions[c] = {}
				
				suggestions[cmd][f] = None

	return NestedCompleter.from_nested_dict(suggestions)


def prompt(ppt):
    global history, autocompletion

    session = PromptSession(
    	completer=autocompletion,
        history=history
    )

    while True:
	    try:
	        return session.prompt(
	        	ppt,
	        	auto_suggest=AutoSuggestFromHistory(),
	        	complete_while_typing=True,
	        	wrap_lines=True
	        )
	    except KeyboardInterrupt:
	    	return ""
	    except EOFError:
	        printerr("Unexpected error in prompt")
	    except Exception as err:
	    	printerr(f"Unknown exception in prompt: {err}")


bash_history = f"/home/{get_username()}/.bash_history"
history = FileHistory(bash_history)


def load_history():
	history = FileHistory(bash_history)


def clear_history():
	with open(bash_history, "w") as h:
		h.write("")

	load_history()


autocompletion = autocomplete_cwd()
keyboard_listener = None


def open_new_tab(tabs: int = 1):
	r = 0

	for i in range(tabs):
		r = run(
			[
				"gnome-terminal",
				"--tab",
				f"--working-directory={os.getcwd()}",
				"--",
				"python",
				f"{BASE}/terminal.py"
			],
			env=os.environ.copy()
		)

	return r == 0


"""
def handle_commands():
	def for_canonical(f):
		return lambda k: f(l.canonical(k))

	hotkey = keyboard.HotKey(
		keyboard.HotKey.parse('<ctrl>+t'),
		open_new_tab
	)

	with keyboard.Listener(on_press=for_canonical(hotkey.press), on_release=for_canonical(hotkey.release)) as l:
		keyboard_listener = l
		l.join()


commands_thread.setup(target=handle_commands)


def create_commands_thread():
	commands_thread = ThreadMaid()
	commands_thread.setup(target=handle_commands)
"""


def kill_lock():
	if os.path.exists(LOCK_FILE):
		content = ""

		with open(LOCK_FILE, "r") as f:
			content = f.read().strip()
        
		# Are we already the master?
		if PID == content:
			return True

		# Is the master still alive?
		# This logic is broken
		try:
			"""
			printinf("The master tab got killed, so this tab gained its powers")
	
			# needs to check if the process is still alive
			# before trying to kill it
			os.kill(int(content), 0)
			"""
			return False
		except (OSError, ValueError):
			try:
				os.remove(LOCK_FILE)
			except:
				pass


def is_master_tab():
	# kill_lock()

	try:
		with open(LOCK_FILE, "x") as f:
			f.write(str(os.getpid()))

		# create_commands_thread()
		# commands_thread.run()
		return True
	except (FileExistsError, OSError):
		return False


is_master = is_master_tab()

#if is_master:
#	with open(f"{BASE}/icon-sm.txt", "r") as i:
#		print(i.read())

while True:
	is_master = is_master_tab()

	dir_ = os.getcwd()
	user_marker = "🎜"
	user_color = "ansigreen"
	git_branch = get_git_repo() if is_git_repo() else ""

	if not is_empty(git_branch):
		git_branch = f" - 🐙 <ansiblue>{git_branch}</ansiblue>"

	if dir_ == os.path.expanduser('~'):
		dir_ = "~/"

	if is_super_user:
		user_marker = "🗝"
		user_color = "ansired"

	user_marker = f"{user_marker}  "

	cmd = prompt(
		Echo.ansi(
			# Command string
			"".join([
				f"<{user_color}>{{%0%}}</{user_color}>",
				"<ansired>{%1%}</ansired>",
				git_branch,
				" - <ansiyellow>{%2%}</ansiyellow>",
				"\n<ansiblue>{%3%}</ansiblue>"
			]),
			# Replacements
			user_marker, # 0
			get_username(), # 1
			dir_, # 2,
			" 🖝  "# 3
		)
	)

	# Skip empty entries
	if is_empty(cmd):
		continue

	cmd = cmd.strip()
	argsvalid: bool = False
	args: list = []

	if not (not cmd):
		try:
			args = parse_params(cmd)

			# Remove extra spaces
			args = array_clear(args)

			# The first element is always the command
			cmd = args.pop(0)
			argsvalid = len(args) >= 1
		except ValueError as ve:
			print(ve)
			continue

	try:
		if cmd == "exit":
			if is_super_user:
				deescalate()
				continue

			# if not is_empty(keyboard_listener):
			# 	keyboard_listener.stop()

			if os.path.exists(LOCK_FILE) and is_master:
				os.remove(LOCK_FILE)

			# commands_thread.halt()
			exec_exit(True)

		elif cmd == "pid":
			print(PID)
			continue

		elif cmd == "is" and argsvalid:
			if args[0] == "tab":
				if args[1] == "master":
					print("This tab is the master") if is_master else print("This tab is a clone")
			continue

		elif cmd == "new" and argsvalid:
			if args[0] == "tab":
				tabs = 1

				if args[1]:
					tabs = int(args[1])

				open_new_tab(tabs)
			continue

		elif cmd in "reload" and argsvalid:
			if "conf" in args[0]:
				e = os.environ.copy()
				print("Done")
			elif args[0] == "history":
				load_history()
				printinf("Done")
			else:
				print(f"Command incomplete {cmd}")
			continue

		elif cmd == "delete-history":
			clear_history()
			printinf("Done")
			continue

		elif cmd == "cd":
			try:
				dest = args[0] if args else os.path.expanduser("~")
				os.chdir(dest)
				autocompletion = autocomplete_cwd()
			except FileNotFoundError:
				printalr(f"cd: {args[0]}: No such file or directory")
			except Exception as err:
				printerr(f"cd: {err}")
			continue

		elif cmd in ["su", "sudo"] and argsvalid:
			if cmd == "sudo" and args[0].strip() == "su":
				escalate()
				continue

		elif cmd == "whoami":
			if is_super_user:
				printalr("You are executing commands as super user, be careful!")

		elif is_scrambled(cmd, "clear") or cmd == "cls":
			cmd = "clear"

		# Executing bash scripts
		elif cmd.startswith("./"):
			script = cmd.replace("./", "")
			"""TODO

			Sometimes this asks for password
			check why
			"""
			cmd = "bash"
			args.append(os.getcwd() + "/" + script)

		if is_super_user:
			run(["sudo", "-E", cmd, *args], env=e)
		else:
			run([cmd, *args], env=e)
	except CalledProcessError as cpe:
		printerr(f"Error occurred: {cpe}\nCommand: {cmd}")
		continue
	except Exception as err:
		printerr(f"Error occurred: {err}")

		"""
		if os.path.exists(LOCK_FILE) and is_master:
			os.remove(LOCK_FILE)
		"""

		continue
	except KeyboardInterrupt:
		if is_super_user:
			deescalate()

		print("")

		continue
