# -*- coding: utf-8 -*-

import os
import time
import signal
import syslog
import shutil
import re
import asyncore

from filewatcher import filewatchconfig
from filewatcher import metadatum


FEVENT_NEW = 1
FEVENT_MODIFIED = 2
FEVENT_DELETED = 4


FW_APP_NAME = 'filewatcher'


class OperationExecRef:
	""" 作業執行參考物件 """

	def __init__(self, filename_matchobj, pathname_matchobj, digisig, event_type, is_dismiss_event=False):
		""" 建構子
		參數:
			filename_matchobj - 檔名 regex 比對結果物件
			pathname_matchobj - 路徑 regex 比對結果物件 (如果有設定路徑比對，否則為 None)
			digisig - 數位簽章 (如果有設定內容重複檢查或是夾帶數位簽章，否則為 None)
			event_type - 事件形式
			is_dismiss_event - 是否為檔案刪除事件
		"""

		self.filename_matchobj = filename_matchobj
		self.pathname_matchobj = pathname_matchobj
		self.digisig = digisig

		self.event_type = event_type
		self.is_dismiss_event = is_dismiss_event
		if self.is_dismiss_event is None:
			if (FEVENT_NEW == event_type) or (FEVENT_MODIFIED == event_type):
				self.is_dismiss_event = False
			elif FEVENT_DELETED == event_type:
				self.is_dismiss_event = True

		self.carry_variable = {}
# ### class OperationExecRef


class PeriodicalCall:
	def __init__(self, call_object, call_arg=None, min_interval=10):
		self.call_object = call_object
		self.call_arg = call_arg

		self.min_interval = min_interval
		if self.min_interval < 10:
			self.min_interval = 10

		self.actual_min_interval = self.min_interval
		self.last_invoke_tstamp = 0;
	# ### def __init__

	def __recaculate_invoke_interval(self, last_time_consumption):
		new_interval = int( ((self.actual_min_interval * 98) + last_time_consumption + self.min_interval) / 100 )
		if new_interval > self.min_interval:
			self.actual_min_interval = new_interval
	# ### def __recaculate_invoke_interval

	def invoke(self):
		current_tstamp = time.time()

		if (current_tstamp - self.last_invoke_tstamp) > self.actual_min_interval:
			self.call_object(self.call_arg)

			callcomplete_tstamp = time.time()
			self.__recaculate_invoke_interval(callcomplete_tstamp - current_tstamp)

			self.last_invoke_tstamp = current_tstamp

			return True
		else:
			return False
	# ### def invoke
# ### class PeriodicalCall

class ProcessDriver:
	def __init__(self, periodical_call_interval=180):
		self.API_VERSION = 1

		self.async_map = {}

		self.periodical_call_interval = periodical_call_interval
		self.periodical_call = []
	# ### def __init__

	def append_periodical_call(self, call_object, call_arg=None, min_interval=10):
		pcall_obj = PeriodicalCall(call_object, call_arg, min_interval)
		self.periodical_call.append(pcall_obj)
	# ### def append_periodical_call

	def invoke_periodical_call(self):
		for pcall_obj in self.periodical_call:
			pcall_obj.invoke()
	# ### def invoke_periodical_call

	def loop(self):
		asyncloop_count = int(self.periodical_call_interval/30)
		if asyncloop_count < 1:
			asyncloop_count = 1

		while False == _check_terminate_signal():
			if self.async_map:
				asyncore.loop(30, map=self.async_map, count=asyncloop_count)
			else:
				time.sleep(self.periodical_call_interval)
			self.invoke_periodical_call()
	# ### def loop
# ### class ProcessDriver


class WatcherEngine:
	""" 被 monitor 呼叫，派送事件給 operator 執行 """

	def __init__(self, global_config, watch_entries, monitor_implement, operation_deliver):
		""" 建構子
		參數:
			global_config - 全域設定值
			watch_entries - 監看項目設定
			monitor_implement - Monitor 實作 (dict)
			operation_deliver - Operator 實作 (dict)
		"""
		self.global_config = global_config
		self.watch_entries = watch_entries
		self.monitor_implement = monitor_implement
		self.operation_deliver = operation_deliver

		self.metadb = self.global_config.metadb

		self.last_file_event_tstamp = time.time()
		self.serialcounter = 1 + (self.last_file_event_tstamp % 1024)

		self.process_driver = ProcessDriver()
	# ### def __init__

	def activate(self):
		""" 啓動監看模組，開始作業
		"""

		for monitor_name, monitor_m in self.monitor_implement.iteritems():
			monitor_m.monitor_start(self, self.global_config.target_directory, self.global_config.recursive_watch)
			syslog.syslog(syslog.LOG_INFO, "start monitor [%s]" % (monitor_name,))

		syslog.syslog(syslog.LOG_INFO, "Activated FileWatcher.")
	# ### def activate

	def deactivate(self):
		""" 停止監看與作業模組，終止作業
		"""

		for monitor_name, monitor_m in self.monitor_implement.iteritems():
			monitor_m.monitor_stop()
			syslog.syslog(syslog.LOG_INFO, "stopped monitor [%s]" % (monitor_name,))

		for operator_name, operator_m in self.operation_deliver.iteritems():
			operator_name.operator_stop()
			syslog.syslog(syslog.LOG_INFO, "stopped operator [%s]" % (operator_name,))

		syslog.syslog(syslog.LOG_INFO, "Deactivated FileWatcher.")
	# ### def deactivate

	def __perform_operation(self, filename, folderpath, orig_path, target_path, operate_list, oprexec_ref):
		#print "oplist: %r" % (operate_list,)
		for opr_block in operate_list:
			current_filepath = target_path
			block_log_queue = []
			for opr_ent in opr_block:
				if (current_filepath is not None) and (os.path.exists(current_filepath)):
					entry_log_queue = []
					altered_filepath = opr_ent.opmodule.perform_operation(current_filepath, filename, opr_ent.argv, oprexec_ref, entry_log_queue)
					#print "operation: [%s/%r] (f=%r, t=%r)" % (opr_ent.opname, opr_ent.argv, current_filepath, altered_filepath,)
					current_filepath = altered_filepath

					if len(entry_log_queue) > 0:
						for logline in entry_log_queue:
							block_log_queue.append("%s: %s"%(opr_ent.opname, logline,))
					else:
						block_log_queue.append("%s: (Log=N/A)"%(opr_ent.opname,))
				else:
					print "leaving operation loop (current-path=%r)" % (current_filepath,)
					break
			if len(block_log_queue) > 0:
				logmsg = '; '.join(block_log_queue)
			else:
				logmsg = 'no operations proceed'
			syslog.syslog(syslog.LOG_INFO, "operation on [%s]: %s." % (orig_path, logmsg,))
			#print "operation on [%s]: %s." % (orig_path, logmsg,)
	# ### def __perform_operation

	def discover_file_change(self, filename, folderpath, event_type=0):
		""" 通知監視引擎找到新的檔案

		參數:
			filename - 檔案名稱
			folderpath - 檔案夾路徑 (相對於 target_directory 路徑)
			event_type - 事件型別 (FEVENT_NEW, FEVENT_MODIFIED, FEVENT_DELETED)
		"""

		if (True == self.global_config.recursive_watch) and ('' != folderpath):
			print "ignored - recursive watch disabled. (folderpath = %r)" % (folderpath,)
			return

		self.last_file_event_tstamp = time.time()	# 更新事件時戳
		print "discoveried - filename=%r, folder=%r, event-type=%r" % (filename, folderpath, event_type,)

		orig_path = os.path.join(self.global_config.target_directory, folderpath, filename)
		if not os.path.isfile(orig_path):
			return

		# {{{ scan watch entries
		for w_case in self.watch_entries:
			mobj_file = w_case.file_regex.match(filename)
			if mobj_file is None:
				continue

			mobj_path = None
			if w_case.path_regex is not None:
				mobj_path = w_case.path_regex.match(folderpath)
				if mobj_path is None:
					continue

			# {{{ do ignorance check
			if w_case.ignorance_checker is not None:
				if w_case.ignorance_checker(folderpath, filename):
					syslog.syslog(syslog.LOG_INFO, "Ignored: [%s]"%(orig_path,))
					return
			# }}} do ignorance check

			cancel_operation = None
			self.serialcounter = (self.serialcounter + 1) % 1024

			f_sig = None

			# {{{ pre-operation for file new or update
			if FEVENT_DELETED != event_type:
				# {{{ build unique name if required
				if w_case.process_as_uniqname:
					uniq_name = "%s-Wr%04d" % (filename, self.serialcounter,)
					target_path = os.path.join(self.global_config.target_directory, folderpath, uniq_name)
					try:
						shutil.move(orig_path, target_path)
					except shutil.Error as e:
						print "Failed on file renaming for meta operation: %s" % (e,)
						target_path = orig_path
						# we will do meta operations anyway.
				else:
					target_path = orig_path
				# }}} build unique name if required

				# {{{ checking if proceed
				if (self.metadb is not None) and (True == w_case.do_dupcheck):
					check_label = filename
					life_retain = False
					if w_case.content_check_label is not None:
						check_label = w_case.content_check_label
						life_retain = True

					f_sig = metadatum.compute_file_signature(target_path)
					if True == self.metadb.test_file_duplication_and_checkin(check_label, f_sig, life_retain):
						cancel_operation = 'duplicate file (meta sig-check)'
				# }}} checking if proceed
			# }}} pre-operation for file new or update

			# {{{ cancel operation
			if cancel_operation is not None:
				if True == self.global_config.remove_unoperate_file:
					os.unlink(target_path)
				syslog.syslog(syslog.LOG_INFO, "Cancel: [%s] reason=%s."%(orig_path, cancel_operation,))
				print "Cancel: [%s] reason=%s."%(orig_path, cancel_operation,)
				return
			# }}} cancel operation

			oprexec_ref = OperationExecRef(mobj_file, mobj_path, f_sig, event_type)
			if (FEVENT_NEW == event_type) or (FEVENT_MODIFIED == event_type):
				print "running update route"
				self.__perform_operation(filename, folderpath, orig_path, target_path, w_case.operation_update, oprexec_ref)
			elif FEVENT_DELETED == event_type:
				print "running remove route"
				self.__perform_operation(filename, folderpath, orig_path, target_path, w_case.operation_remove, oprexec_ref)
			else:
				print "running NoOP route"
				syslog.syslog(syslog.LOG_INFO, "NoOP: [%s] unknown event type (%r)."%(orig_path, event_type,))

			return
		# }}} scan watch entries

		syslog.syslog(syslog.LOG_INFO, "NoWatchEntryFound: [%s]."%(orig_path,))
	# ### def discover_file_change
# ### class WatcherEngine


def get_builtin_modules():
	""" 取得內建的模組 (以 tuple 形式傳回) """

	m = []

	from filewatcher.monitor import periodical_scan
	from filewatcher.operator import copier
	from filewatcher.operator import mover
	from filewatcher.operator import coderunner

	m.extend((periodical_scan, copier, mover, coderunner,))

	osuname = os.uname()
	if 'Linux' == osuname[0]:
		from filewatcher.monitor import linux_inotify
		m.append(linux_inotify)

	return m
# ### def get_builtin_modules



def get_watcherengine(config_filepath, enabled_modules=None):
	""" 取得監看引擎

	參數:
		config_filepath - 設定檔路徑
		enabled_modules=None - 要啓用的模組串列
	回傳值:
		WatcherEngine 物件
	"""

	if (enabled_modules is None):
		enabled_modules = get_builtin_modules()

	# prepare module profile
	config_readers, monitor_implement, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq, = filewatchconfig.get_module_interfaces(enabled_modules)
	logmsg = "Loaded modules: modify=%r, dismiss=%r" % (operation_run_newupdate_seq, operation_run_dismiss_seq,)
	syslog.syslog(syslog.LOG_INFO, logmsg)
	print logmsg

	# load config
	cfg = filewatchconfig.load_config(config_filepath, config_readers, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq)
	if cfg is None:
		print "ERR: cannot load global configuration"
		return None
	global_config, watch_entries, = cfg

	w_engine = WatcherEngine(global_config, watch_entries, monitor_implement, operation_deliver)
	syslog.syslog(syslog.LOG_INFO, "Loaded engine with configuration: [%r]" % (config_filepath,))

	return w_engine
# ### def _active_watcherengine

def _prepare_log(config_filepath):
	logging_name = os.path.basename(config_filepath)
	logging_name = re.match("^([a-zA-Z0-9_-]+)", logging_name)

	if logging_name is None:
		logging_name = FW_APP_NAME
	else:
		logging_name = ''.join((FW_APP_NAME, '.', logging_name.group(1),))

	syslog.openlog(logging_name, syslog.LOG_PID, syslog.LOG_DAEMON)
# ### def _prepare_log

__arrived_signal_handled = False	# 已收到的訊號是否已經處理完成
__terminate_signal_recived = False	# 收到程式停止訊號

def _termination_signal_handler(signum, frame):
	""" (私有函數) UNIX Signal 處理器 """

	global __terminate_signal_recived, __arrived_signal_handled

	__terminate_signal_recived = True
	__arrived_signal_handled = True

	print "Recived Stop Signal."
# ### def _term_signal_handler

def _regist_terminate_signal():
	signal.signal(signal.SIGINT, _termination_signal_handler)
	#signal.signal(signal.SIGTERM, _termination_signal_handler)
# ### def _regist_terminate_signal

def _check_terminate_signal():
	global __terminate_signal_recived, __arrived_signal_handled

	if True == __terminate_signal_recived:
		while (False == __arrived_signal_handled):
			time.sleep(1)
		return True
	else:
		return False
# ### def _check_terminate_signal

def _wait_terminate_signal():
	global __terminate_signal_recived, __arrived_signal_handled

	# {{{ loop for signal handling
	while (False == __terminate_signal_recived):
		__arrived_signal_handled = False
		signal.pause()

		while (False == __arrived_signal_handled):
			time.sleep(1)
	# }}} loop for signal handling
# ### def _wait_terminate_signal


def run_watcher(config_filepath, enabled_modules=None):
	""" 啟動 watcher
	執行前應先對 filewatchconfig 模組註冊好 ignorance checker

	參數:
		config_filepath - 設定檔路徑
		enabled_modules=None - 要啓用的模組串列
	"""

	_prepare_log(config_filepath)
	w_engine = get_watcherengine(config_filepath, enabled_modules)
	if w_engine is None:
		print "ERR: cannot load watcher engine."
		return
	w_engine.activate()
	print "FileWatcher: engine activated."

	_regist_terminate_signal()
	w_engine.process_driver.loop()
# ### def startup_watcher



# vim: ts=4 sw=4 ai nowrap
