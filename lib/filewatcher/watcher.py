# -*- coding: utf-8 -*-

import time

from operator import coderunner

__enabled_modules = [coderunner]


FEVENT_NEW = 1
FEVENT_MODIFIED = 2
FEVENT_DELETED = 4


class OperationExecRef:
	""" 作業執行參考物件 """

	def __init__(self, filename_matchobj, pathname_matchobj, digisig):
		""" 建構子
		參數:
			filename_matchobj - 檔名 regex 比對結果物件
			pathname_matchobj - 路徑 regex 比對結果物件 (如果有設定路徑比對，否則為 None)
			digisig - 數位簽章 (如果有設定內容重複檢查或是夾帶數位簽張，否則為 None)
		"""

		self.filename_matchobj = filename_matchobj
		self.pathname_matchobj = pathname_matchobj
		self.digisig = digisig
# ### class OperationExecRef


class WatcherEngine:

	def __init__(self):
		self.last_file_event_tstamp = time.time()
	# ### def __init__

	def discover_file_change(self, filename, filefolder, event_type=0):
		""" 通知監視引擎找到新的檔案
		"""

		self.last_file_event_tstamp = time.time()	# 更新事件時戳

		pass
	# ### def discover_new_file
# ### class WatcherEngine



def __keyfunction_prop_schedule(prop):
	""" 排序用 key function (componentprop.OperatorProp 物件，針對 schedule_priority) """

	return prop.schedule_priority
# ### def __keyfunction_schedule

def __keyfunction_prop_run(prop):
	""" 排序用 key function (componentprop.OperatorProp 物件，針對 run_priority) """

	return prop.run_priority
# ### def __keyfunction_prop_run


def _get_module_interfaces(mods):
	""" 取得工作模組的屬性，並依此設定相關參數

	參數:
		mods - 含有工作模組的串列
	回傳值:
		含有以下元素的 tuple: (config_readers, monitor_implement, operation_deliver, operation_schedule_seq, operation_run_seq)
		config_readers - 以設定檔段落名稱為 key 工作模組為 value 的字典
		monitor_implement - 含有監視工作模組的串列
		operation_deliver - 以作業名稱為 key 監視工作模組為 value 的字典
		operation_schedule_seq - 排定作業塊先後順序用的作業名稱串列
		operation_run_seq - 排定作業執行先後順序用的作業名稱串列
	"""

	config_readers = {}

	monitor_implement = []

	operation_deliver = {}
	operation_schedule_seq = []
	operation_run_seq = []

	for m in mods:
		prop = m.get_module_prop()

		config_sec_name = prop.module_name
		config_readers[config_sec_name] = m

		# {{{ if module is monitor module
		if prop.isMonitor:
			monitor_implement.append(m)
		# }}} if module is monitor module

		# {{{ if module is operator module
		if prop.isOperator:
			operation_name = prop.operation_name
			if prop.run_priority is not None:	# only push into dict. if run-priority is available
				operation_deliver[operation_name] = m
				operation_run_seq.append(prop)

				if prop.schedule_priority is not None:
					operation_schedule_seq.append(prop)
		# }}} if module is operator module

	# {{{ sort operator module lists
	operation_schedule_seq = [x.operation_name for x in sorted(operation_schedule_seq, key=__keyfunction_prop_schedule)]
	operation_run_seq = [x.operation_name for x in sorted(operation_run_seq, key=__keyfunction_prop_run)]
	# }}} sort operator module lists

	return (config_readers, monitor_implement, operation_deliver, operation_schedule_seq, operation_run_seq)
# ### def _get_module_interfaces



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
	"""

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
