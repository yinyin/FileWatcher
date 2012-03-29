# -*- coding: utf-8 -*-

""" 定時掃描變更檔案系統監視模組 """

import time

from filewatcher import componentprop
from filewatcher import filewatchconfig


def get_module_prop():
	""" 取得監視器各項特性/屬性

	參數:
		(無)
	回傳值:
		傳回 componentprop.MonitorProp 物件
	"""

	return componentprop.MonitorProp('periodical-scan')
# ### def get_module_prop



_ignorance_checker = None
def set_ignorance_checker(checker):
	""" 設定忽略路徑與檔案檢查器
	
	參數:
		checker - 進行路徑與檔案名稱檢查的函式，函數原型: (dirlist[]=None, filename=None)
	"""
	global _ignorance_checker
	
	if isinstance(checker, str):
		_ignorance_checker = filewatchconfig.lookup_ignorance_checker(checker)
	else:
		_ignorance_checker = checker
# ### def set_ignorance_checker



__scan_interval = 1200
__cron_interval_style = False
__blackout_time = []

_metastorage = None

def monitor_configure(config, metastorage):
	""" 設定監視器組態

	參數:
		config - 帶有參數的字典
		metastorage - 中介資訊資料庫物件
	回傳值:
		(無)
	"""

	global __scan_interval, __cron_interval_style, __blackout_time, _metastorage

	# {{{ 掃描間隔
	if 'scan_interval' in config:
		try:
			__scan_interval = int(config['scan_interval'])
			if __scan_interval < 0:
				__scan_interval = -__scan_interval
				__cron_interval_style = True

			if __scan_interval < 120:	# set a minimal value
				__scan_interval = 120
		except:
			__scan_interval = 1200
	# }}} 掃描間隔

	# 是否使用儲存紀錄到 MetaStorage 的比對方式
	if ('use_meta' in config) and (config['use_meta']) and (metastorage is not None):
		_metastorage = metastorage

	# {{{ 將不掃描時間讀入
	if ('blackout_time' in config) and (isinstance('blackout_time', list)):
		for t in config['blackout_time']:
			try:
				tinterval = None
				if isinstance(t, dict):
					tinterval = filewatchconfig.TimeInterval(t['from'], t['to'])
				else:
					tinterval = filewatchconfig.TimeInterval(t[0], t[1])
				__blackout_time.append(tinterval)
			except:
				pass
	# }}} 將不掃描時間讀入
	
	# 載入 ignorance checker
	if 'ignorance-checker' in config:
		set_ignorance_checker(str(config['ignorance-checker']))
# ### def monitor_configure


__wk_thread = None
__wk_do_scan = False

def __scan_worker(watcher_instance, target_directory, recursive_watch):
	global __wk_do_scan

	last_scan = 0
	min_scan_interval = __scan_interval / 4

	while __wk_do_scan:
		perform_scan = False
		current_tstamp = time.time()
		tz_offset = metadatum.get_tzoffset()

		# {{{ check if need do scan
		if (current_tstamp - last_scan) > min_scan_interval:	# must > min_scan_interval to avoid over-scan
			if True == __cron_interval_style:
				if (current_tstamp - (current_tstamp % __scan_interval)) > last_scan:
					perform_scan = True
			else:
				if (current_tstamp - watcher_instance.last_file_event_tstamp) > __scan_interval:
					perform_scan = True
		
		if perform_scan:
			# {{{ see if in blackout time
			local_tstamp = current_tstamp - tz_offset
			for b in __blackout_time:
				if b.isIn(local_tstamp):
					perform_scan = False
			# }}} see if in blackout time
		# }}} check if need do scan

		if perform_scan:
			# initial ignorance checker for this round
			if _ignorance_checker is not None:
				_ignorance_checker(None, None)
			
			# TODO: do scan

			current_tstamp = time.time()
			last_scan = current_tstamp

		# {{{ compute sleep seconds for next invoke
		sleep_tick = min_scan_interval
		if True == __cron_interval_style:
			sleep_tick = (10 + ( (1 + math.floor(current_tstamp / __scan_interval)) * __scan_interval ) ) - current_tstamp
		# }}} compute sleep seconds for next invoke

		time.sleep(sleep_tick)
# ### def __scan_worker



def monitor_start(watcher_instance, target_directory, recursive_watch=False):
	""" 開始監控目錄作業

	參數:
		watcher_instance - watcher.WatcherEngine 物件實體
		target_directory - 監測目標資料夾
		recursive_watch - 是否要遞迴監測子資料夾
	回傳值:
		(無)
	"""

	global __wk_do_scan, __wk_thread

	__wk_do_scan = True
	
	__wk_thread = threading.Thread(target=__scan_worker, args=(watcher_instance, target_directory, recursive_watch,))
	__wk_thread.start()
# ### def monitor_start


def monitor_stop():
	""" 停止作業，準備結束

	參數:
		(無)
	回傳值:
		(無)
	"""

	global __wk_do_scan, __wk_thread, __scan_interval

	__wk_do_scan = False
	__wk_thread.join(__scan_interval*2+60)
# ### def monitor_stop



# vim: ts=4 sw=4 ai nowrap
