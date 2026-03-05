#!/usr/bin/python

from typing import Optional, Any, Dict, List, Union
from subprocess import run, Popen, PIPE, CalledProcessError
from shlex import split as parse_params
from re import sub
from getpass import getpass
import os
import pwd
import glob

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

from utilities import (
	exec_exit, 
	is_empty,
	array_clear,
	sprintf,
	printinf,
	printalr,
	printerr,
	printsuc
)
from echo import Echo
from thread_maid import ThreadMaid

BASE = os.path.dirname(__file__)
PID = str(os.getpid()).strip()
LOCK_FILE = "/tmp/powerconsole_hotkey.lock"

cuid = os.getuid()
cugid = os.getgid()
is_super_user = False if cuid != 0 else True
e = os.environ.copy()
aliases = []
git_commands = {
	"add": WordCompleter(["."]),
	"commit": WordCompleter(["-m"]),
	"checkout": WordCompleter([
		"-b"
		"master",
		"main",
		"development"
	]),
	"status": None,
	"branch": None,
	"log": None
}
completer = {
	"clear": None,
	"exit": None,
	"delete-history": None,
	"reload-conf": None,
	"reload-config": None,
	"reload-env": None,
	"ln": WordCompleter(["-s"])
}
commands_thread = ThreadMaid()


def escalate():
	try:
		password = getpass(f"[sudo] password for {user}: ")
		run(
			["sudo", "-i"], 
			input=password, 
			text=True, 
			check=True, 
			capture_output=True
		)
		is_super_user = True
		# os.setuid(0)
		print("You are now super user")
	except PermissionError as pe:
		print(f"Unable to change uid: {pe}")
	except Exception as err:
		print(f"Unable to escalate privileges: {err}")


def return_to_user():
	try:
		os.seteuid(cuid)
		is_super_user = False
	except Exception:
		print("Unable to return to original user")


def get_username():
    return pwd.getpwuid(cuid).pw_name


user = get_username()


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
        ["ls", f"/home/{user}/.local/bin"],
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
	git_commands["push"] = WordCompleter([
		"origin", 
		"master",
		"main",
		"development",
		get_git_repo()
	]),
	git_commands["pull"] = WordCompleter([
		"origin",
		"master",
		"main",
		"development",
		get_git_repo()
	]),
	completer["git"] = NestedCompleter(git_commands)

	completer["cd"] = WordCompleter(get_files())
	completer["cp"] = WordCompleter(["-r", get_files()])
	completer["mv"] = WordCompleter(get_files())
	completer["rm"] = WordCompleter(["-r", "-f", get_files()])
	completer["nano"] = WordCompleter(get_files())
	completer["vi"] = WordCompleter(get_files())
	completer["vim"] = WordCompleter(get_files())
	completer["subl"] = WordCompleter(get_files())
	completer["code"] = WordCompleter(get_files())

	# Add /usr/bin/ commands
	"""
	for c in get_commands():
		completer[c] = None
	"""

	# Add local commands
	"""
	for c in get_local_commands():
		completer[c] = None
	"""

	# Add files of the current directory
	for f in get_files():
		completer[f] = None

	return NestedCompleter(completer)


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
	        	complete_while_typing=True
	        )
	    except KeyboardInterrupt:
	    	return ""
	    except EOFError:
	        print("Unexpected error in prompt")
	    except Exception as err:
	    	print(f"Unknown exception in prompt: {err}")


bash_history = f"/home/{user}/.bash_history"
history = FileHistory(bash_history)


def clear_history():
	with open(bash_history, "w") as h:
		h.write("")

	history = FileHistory(bash_history)


autocompletion = autocomplete_cwd()
keyboard_listener = None


def open_new_tab():
	run(
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

	return True


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


def is_master_tab():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            content = f.read().strip()
        
        # Are we already the master?
        if PID == content:
            return True
        
        # Is the master still alive?
        try:
            os.kill(int(content), 0)
            return False 
        except (OSError, ValueError):
            try:
                os.remove(LOCK_FILE)
            except:
                pass

    try:
        with open(LOCK_FILE, "x") as f:
            f.write(str(os.getpid()))
        
        create_commands_thread()
        commands_thread.run()
        return True
    except (FileExistsError, OSError):
        return False

is_master = is_master_tab()

if is_master:
	with open(f"{BASE}/icon-sm.txt", "r") as i:
		print(i.read())

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
			user, # 1
			dir_, # 2
			" 🖝  " # 3
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
			if not is_empty(keyboard_listener):
				keyboard_listener.stop()

			if os.path.exists(LOCK_FILE) and is_master:
				os.remove(LOCK_FILE)

			commands_thread.halt()
			exec_exit()

		elif cmd == "pid":
			print(PID)
			continue

		elif cmd == "is" and argsvalid:
			if args[0] == "tab":
				if args[1] == "master":
					print("This tab is the master") if is_master else print("This tab is a clone")

			continue

		elif cmd in ["reload-config", "reload-conf", "reload-env"]:
			e = os.environ.copy()
			print("Done")
			continue

		elif cmd == "delete-history":
			clear_history()
			print("Done")
			continue

		elif cmd == "cd":
			try:
				dest = args[0] if args else os.path.expanduser("~")
				os.chdir(dest)
				autocompletion = autocomplete_cwd()
			except FileNotFoundError:
				print(f"cd: {args[0]}: No such file or directory")
			except Exception as err:
				print(f"cd: {err}")
			continue

		elif cmd in ["su", "sudo"] and argsvalid:
			if cmd == "sudo" and args[0].strip() == "su":
				escalate()
				continue

		# Executing bash scripts
		elif cmd.startswith("./"):
			script = cmd.replace("./", "")
			"""TODO

			sometimes this asks for password
			check why
			"""
			cmd = "bash"
			args.append(os.getcwd() + "/" + script)

		# print([cmd, "-E", *args])
		if is_super_user:
			run([cmd, "-E", *args], env=e)
		else:
			run([cmd, *args], env=e)
	except CalledProcessError as cpe:
		print(f"Error occurred: {cpe}\nCommand: {cmd}")
		continue
	except Exception as err:
		print(f"Error occurred: {err}")
		continue
	except KeyboardInterrupt:
		if is_super_user:
			return_to_user()

		continue
