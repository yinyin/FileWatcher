# -*- coding: utf-8 -*-

import time

from filewatcher import filewatchconfig

from filewatcher.operator import coderunner

__enabled_modules = [coderunner]


FEVENT_NEW = 1
FEVENT_MODIFIED = 2
FEVENT_DELETED = 4


class OperationExecRef:
	""" 作業執行參考物件 """

	def __init__(self, filename_matchobj, pathname_matchobj, digisig, is_dismiss_event=False):
		""" 建構子
		參數:
			filename_matchobj - 檔名 regex 比對結果物件
			pathname_matchobj - 路徑 regex 比對結果物件 (如果有設定路徑比對，否則為 None)
			digisig - 數位簽章 (如果有設定內容重複檢查或是夾帶數位簽章，否則為 None)
			is_dismiss_event - 是否為檔案刪除事件
		"""

		self.filename_matchobj = filename_matchobj
		self.pathname_matchobj = pathname_matchobj
		self.digisig = digisig
		
		self.is_dismiss_event = is_dismiss_event
		
		self.carry_variable = {}
# ### class OperationExecRef


class WatcherEngine:
	""" 被 monitor 呼叫，派送事件給 operator 執行 """

	def __init__(self):
		
		self.last_file_event_tstamp = time.time()
	# ### def __init__

	def discover_file_change(self, filename, filefolder, event_type=0):
		""" 通知監視引擎找到新的檔案
		"""

		self.last_file_event_tstamp = time.time()	# 更新事件時戳

		pass	# TODO: call operators
	# ### def discover_file_change
# ### class WatcherEngine



__arrived_signal_handled = False	# 已收到的訊號是否已經處理完成
__terminate_signal_recived = False	# 收到程式停止訊號

def _termination_signal_handler(signum, frame):
	""" (私有函數) UNIX Signal 處理器 """

	global __terminate_signal_recived, __arrived_signal_handled

	__terminate_signal_recived = True
	__arrived_signal_handled = True
# ### def _term_signal_handler


def run_watcher(config_filepath):
	""" 啟動 watcher
	執行前應先對 filewatchconfig 模組註冊好 ignorance checker
	
	參數:
		config_filepath - 設定檔路徑
	"""

	# prepare module profile
	config_readers, monitor_implement, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq, = filewatchconfig.get_module_interfaces(__enabled_modules)

	# load config
	cfg = filewatchconfig.load_config(config_filepath, config_readers, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq)
	if cfg is None:
		print "ERR: cannot load global configuration"
		return 1
	global_config, watch_entries, = cfg
	
	# TODO: load modules
	
	# TODO: start monitor

	# {{{ loop for signal handling
	global __terminate_signal_recived, __arrived_signal_handled

	signal.signal(signal.SIGINT, _termination_signal_handler)
	#signal.signal(signal.SIGTERM, _termination_signal_handler)

	while (False == __terminate_signal_recived):
		__arrived_signal_handled = False
		signal.pause()

		while (False == __arrived_signal_handled):
			time.sleep(1)
	# }}} loop for signal handling
# ### def startup_watcher



# vim: ts=4 sw=4 ai nowrap
