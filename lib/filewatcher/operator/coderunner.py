# -*- coding: utf-8 -*-

import os
import re
import subprocess
import syslog
import threading
import Queue

from filewatcher import componentprop


__runner_queue = {}

__task_queue_assignment = re.compile("""^\(([A-Za-z0-9-]+)\)\s*([^\s].+)$""")


def __subprocess_worker(worker_qlabel, worker_id, q):
	running = True
	while running:
		try:
			cmd = q.get(True, None)
			if cmd is not None:
				retcode = -65536
				try:
					retcode = subprocess.call(cmd)
				except Exception as e:
					print "Have exception [errocde=]: cmd=%r; exception=%s" % (cmd, e,)
				syslog.syslog(syslog.LOG_INFO, "QueuedInvoke: run program [%s] with retcode=%d, worker=%d/%r."%(cmd, retcode, worker_id, worker_qlabel,))
			else:
				print "subprocessworker exiting (ID=%d/Q=%r)" % (worker_id, worker_qlabel,)
				running = False
			q.task_done()
		except Queue.Empty:
			pass
# ### def __subprocess_worker

class __RunConfiguration:
	def __init__(self, queue, command):
		self.queue = queue
		self.command = command
	# ### __init__
# ### class __RunConfiguration

class __RunnerQueue:
	""" 放置執行程式的 Runner/Worker 的佇列 """

	def __init__(self, queue_label, max_running_process, max_running_second=None):
		""" 建構子

		參數:
			queue_label - 佇列名稱
			max_running_process - 最大同時執行行程數，使用 None 表示不指定
			max_running_second - 最長程式執行時間 (秒) 上限，使用 None 表示不指定 (** 未實作)
		"""

		self.queue_label = queue_label
		self.max_running_process = max_running_process
		self.max_running_second = max_running_second

		self.cmd_queue = None
		self.workers = None
	# ### def __init__

	def start_workers(self):
		""" 啟動 worker thread

		參數: (無)
		回傳值: (無)
		"""

		if (self.max_running_process is None) or (self.max_running_process < 1):
			return	# 最大執行行程為空值的話則不啟動任何 worker

		workers_q = []
		self.cmd_queue = Queue.Queue()
		for idx in range(self.max_running_process):
			wk = threading.Thread(target=__subprocess_worker, args=(self.queue_label, idx, self.cmd_queue,))
			wk.start()
			workers_q.append(wk)
			print "created worker named %r (ID=%d/Q=%r)" % (wk.name, idx, self.queue_label,)
		self.workers = workers_q
	# ### def start_workers

	def run_program(self, cmdlist, filepath, logqueue):
		""" 執行指定的程式執行作業

		參數:
			progpath - 要執行程式的路徑
			filepath - 作為參數的檔案檔名
		回傳值:
			(無)
		"""

		progpath = cmdlist[0]
		if (progpath is None) or (not os.path.isfile(progpath)) or (not os.access(progpath, os.X_OK)) or (filepath is None):
			return

		# {{{ build command
		cmd = []
		for v in cmdlist:
			if """%FILENAME%""" == v:
				cmd.append(filepath)
			else:
				cmd.append(v)
		# }}} build command

		if self.cmd_queue is None:
			runprog_retcode = subprocess.call(cmd)
			logqueue.append("run program [%s: %r] with retcode=%d"%(progpath, cmd, runprog_retcode))
		else:
			self.cmd_queue.put(cmd)
			logqueue.append("queued program [%s: %r] into queue=%s"%(progpath, cmd, self.queue_label))
	# ### def run_program

	def stop_workers(self):
		""" 停下執行程式的執行緒 workers

		參數: (無)
		回傳值: (無)
		"""

		if self.cmd_queue is None:
			return	# no worker running, naturally

		for wk in self.workers:
			if wk.is_alive():
				self.cmd_queue.put(None)
			else:
				print "worker %r not alive anymore" % (wk.name,)

		syslog.syslog(syslog.LOG_NOTICE, "RunnerQueue joining task queue (Q=%r)"%(self.queue_label,))
		self.cmd_queue.join()
	# ### def stop_workers
# ### class Runner



def get_module_prop():
	""" 取得操作器各項特性/屬性

	參數: (無)
	回傳值:
		傳回 componentprop.OperatorProp 物件
	"""

	return componentprop.OperatorProp('program_runner', 'run_program', schedule_priority=None, run_priority=3)
# ### def get_module_prop


def operator_configure(config):
	""" 設定操作器組態

	參數:
		config - 帶有參數的字典
	回傳值:
		(無)
	"""

	default_max_running_process = None

	# {{{ get queue size for default queue
	if 'max_running_program' in config:
		try:
			default_max_running_process = int(config['max_running_program'])
		except:
			default_max_running_process = None
	# }}} get queue size for default queue

	# {{{ use multiple queues
	if 'queue' in config:
		# {{{ scan over each queue configuration
		for qconfig in config['queue']:
			max_running_process = None
			if 'max_running_program' in qconfig:
				try:
					max_running_process = int(qconfig['max_running_program'])
				except:
					max_running_process = None

			if 'name' in qconfig:
				qname = str(qconfig['name'])
				__runner_queue[qname] = __RunnerQueue(qname, max_running_process)
		# }}} scan over each queue configuration
	# }}} use multiple queues

	# setup default queue
	__runner_queue['_DEFAULT'] = __RunnerQueue('_DEFAULT', default_max_running_process)
# ### def operator_configure


def read_operation_argv(argv):
	""" 取得操作設定

	參數:
		argv - 設定檔中的設定

	回傳值:
		吻合工作模組需求的設定物件
	"""

	cmd_argv = None
	que_argv = '_DEFAULT'

	if isinstance(argv, dict):
		if 'queue' in argv:
			que_argv = argv['queue']
		cmd_argv = argv['command']
	else:
		cmd_argv = argv

	result_cmd = None

	# {{{ attempt to build command list as list
	if isinstance(cmd_argv, str) or isinstance(cmd_argv, unicode):
		result_cmd = [argv, """%FILENAME%"""]
	elif isinstance(cmd_argv, tuple) or isinstance(cmd_argv, list):
		have_filename_macro = False
		result_cmd = []
		for v in cmd_argv:
			if """%FILENAME%""" == v:
				have_filename_macro = True
			result_cmd.append(v)
		if not have_filename_macro:
			result_cmd.append("""%FILENAME%""")
	else:
		result_cmd = cmd_argv
	# }}} attempt to build command list as list

	# {{{ check if use queue short-cut -syntax (eg: (QUEUE) /path/to/cmd )
	if isinstance(result_cmd, list):
		m = __task_queue_assignment.match( result_cmd[0] )
		if m is not None:
			q = m.group(1)
			result_cmd[0] = m.group(2)
			if q in __runner_queue:
				que_argv = q
	# }}} check if use queue short-cut -syntax

	return __RunConfiguration(que_argv, cmd_argv)
# ### read_operation_argv


def perform_operation(current_filepath, orig_filename, argv, oprexec_ref, logqueue=None):
	""" 執行操作

	參數:
		current_filepath - 目標檔案絕對路徑 (如果是第一個操作，可能檔案名稱會是更改過的)
		orig_filename - 原始檔案名稱 (不含路徑)
		argv - 設定檔給定的操作參數
		oprexec_ref - 作業參考物件 (含: 檔案名稱與路徑名稱比對結果、檔案內容數位簽章... etc)
		logqueue - 紀錄訊息串列物件
	回傳值:
		經過操作後的檔案絕對路徑
	"""

	# TODO - use argument object
	m = __task_queue_assignment.match(argv)
	if m is None:
		__runner_queue['_DEFAULT'].run_program(argv, current_filepath, logqueue)
	else:
		r_queue = m.group(1)
		cmd_path = m.group(2)
		if r_queue in __runner_queue:
			__runner_queue[r_queue].run_program(cmd_path, current_filepath, logqueue)
		else:
			logqueue.append("queue not found: %r"%(r_queue,))

	return current_filepath
# ### def perform_operation


def operator_stop():
	""" 停止作業，準備結束

	參數:
		(無)
	回傳值:
		(無)
	"""

	syslog.syslog(syslog.LOG_NOTICE, "coderunner: stopping all Runner")
	for runner in __runner_queue.itervalues():
		runner.stop_workers()
	syslog.syslog(syslog.LOG_NOTICE, "coderunner: all Runner stopped")
# ### def operator_stop



# vim: ts=4 sw=4 ai nowrap
