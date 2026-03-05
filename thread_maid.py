#!/usr/bin/python

from typing import Optional, Any, Dict, List, Union
import threading
from ctypes import pythonapi, py_object


class ThreadMaid:
	__thread = None
	__thread_id = 0
	__thread_target = None
	__thread_arguments: Union[list, tuple] = []
	__running: bool = False

	def __init__(self):
		# Just instantiate the class
		pass

	def setup(self, target: object, arguments: Union[list, tuple] = []):
		self.__set_target(target)
		self.__set_arguments(arguments)
		self.__thread = threading.Thread(target=self.__thread_target, args=self.__thread_arguments)
		self.__thread_id = self.__set_id()

		return self

	def __set_target(self, t: object):
		self.__thread_target = t

	def __set_arguments(self, a: Union[list, tuple]):
		if len(a) > 0:
			self.__thread_arguments = a

	def __set_id(self):
		if hasattr(self.__thread, '_thread_id'):
			return self.__thread._thread_id

		for id, thread in threading._active.items():
			if thread == self:
				return id

	def get_id(self):
		return self.__thread_id

	def is_running(self):
		return self.__running

	def halt(self):
		if self.__thread != None:
			try:
				thread_stopped = pythonapi.PyThreadState_SetAsyncExc(self.__thread_id, py_object(SystemExit))

				if thread_stopped > 1:
					pythonapi.PyThreadState_SetAsyncExc(self.__thread_id, 0)

					self.__running = False
			except Exception as e:
				raise Exception(f"Unable to quit Thread ID: {self.__thread_id}")

	def run(self):
		if self.__thread != None:
			self.__running = True
			self.__thread.start()