# -*- coding: utf-8 -*-

""" 定時掃描變更檔案系統監視模組 """

import os
import time
import syslog

from filewatcher import componentprop
from filewatcher import filewatchconfig
from filewatcher import metadatum
from filewatcher import watcher


_cached_module_prop_instance = componentprop.MonitorProp('periodical-scan')
def get_module_prop():
	""" 取得監視器各項特性/屬性

	參數:
		(無)
	回傳值:
		傳回 componentprop.MonitorProp 物件
	"""

	return _cached_module_prop_instance
# ### def get_module_prop



_ignorance_checker = None
def set_ignorance_checker(checker):
	""" 設定忽略路徑與檔案檢查器

	參數:
		checker - 進行路徑與檔案名稱檢查的函式，函數原型: (relpath=None, filename=None) 回傳 True 表要忽略所檢查的項目
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

	syslog.syslog(syslog.LOG_INFO, "periodical_scan configurated (scan_interval=%d/c:%r)." % (__scan_interval, __cron_interval_style,))
# ### def monitor_configure


def __scan_walk_impl(last_scan_time, watcher_instance, target_directory, recursive_watch):

	current_tstamp = int(time.time())

	for root, dirs, files in os.walk(target_directory):
		# 製造相對路徑
		relpath = os.path.relpath(root, target_directory)
		if '.' == relpath:
			relpath = ''

		# {{{ 掃描所有檔案是否有變動
		for f in files:
			fpath = os.path.join(root, f)
			try:
				finfo = os.stat(fpath)
			except:
				continue

			is_updated_file = False

			# {{{ 檢查是否是有變動的檔案
			if _metastorage is not None:	# 採用資料庫檢查
				r = _metastorage.test_file_presence_and_checkin(relpath, f, finfo.st_size, finfo.st_mtime, current_tstamp)
				if (metadatum.FPCHK_NEW == r) or (metadatum.FPCHK_MODIFIED == r):
					is_updated_file = True
			elif finfo.st_mtime > last_scan_time:	# 採用時間比對
				is_updated_file = True
			# }}} 檢查是否是有變動的檔案

			if is_updated_file:
				watcher_instance.discover_file_change(f, relpath, watcher.FEVENT_MODIFIED)
		# }}} 掃描所有檔案是否有變動

		# {{{ 檢查是否要掃描子資料夾
		if recursive_watch:
			if _ignorance_checker is not None:
				to_drop = []
				for d in dirs:
					drel = os.path.join(relpath, d)
					if _ignorance_checker(drel, None):
						to_drop.append(d)
				for d in to_drop:
					dirs.remove(d)
		else:
			del dirs[:]
		# }}} 檢查是否要掃描子資料夾

	# 產生刪除檔案資料
	if _metastorage is not None:
		df = _metastorage.test_file_deletion_and_purge(current_tstamp - 1)
		for dfinfo in df:
			watcher_instance.discover_file_change(dfinfo[1], dfinfo[0], watcher.FEVENT_DELETED)
# ### def __scan_walk_impl

_last_scan_tstamp = 0

def __scan_worker(arg):
	global _last_scan_tstamp

	watcher_instance, target_directory, recursive_watch, = arg

	min_scan_interval = __scan_interval / 4

	perform_scan = False
	current_tstamp = time.time()
	tz_offset = metadatum.get_tzoffset()

	# {{{ check if need do scan
	if (current_tstamp - _last_scan_tstamp) > min_scan_interval:	# must > min_scan_interval to avoid over-scan
		if True == __cron_interval_style:
			if (current_tstamp - (current_tstamp % __scan_interval)) > _last_scan_tstamp:
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

	print "periodical_scan: perform_scan=%r" % (perform_scan,)
	if perform_scan:
		# initial ignorance checker for this round
		if _ignorance_checker is not None:
			_ignorance_checker(None, None)

		__scan_walk_impl(_last_scan_tstamp, watcher_instance, target_directory, recursive_watch)	# do scan

		current_tstamp = time.time()
		_last_scan_tstamp = current_tstamp
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

	watcher_instance.process_driver.append_periodical_call(__scan_worker, (watcher_instance, target_directory, recursive_watch,), (__scan_interval / 4))
# ### def monitor_start


def monitor_stop():
	""" 停止作業，準備結束

	參數:
		(無)
	回傳值:
		(無)
	"""

	pass
# ### def monitor_stop



# vim: ts=4 sw=4 ai nowrap
