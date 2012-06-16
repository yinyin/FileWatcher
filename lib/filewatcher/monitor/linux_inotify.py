# -*- coding: utf-8 -*-

""" 檔案系統監視模組 """


from filewatcher import componentprop
from filewatcher import filewatchconfig


_cached_module_prop_instance = componentprop.MonitorProp('inotify')
def get_module_prop():
	""" 取得監視器各項特性/屬性

	參數:
		(無)
	回傳值:
		傳回 componentprop.OperatorProp 物件
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


def monitor_configure(config, metastorage):
	""" 設定監視器組態

	參數:
		config - 帶有參數的字典
		metastorage - 中介資訊資料庫物件
	回傳值:
		(無)
	"""

	# 載入 ignorance checker
	if 'ignorance-checker' in config:
		set_ignorance_checker(str(config['ignorance-checker']))
# ### def monitor_configure


class EventHandler(pyinotify.ProcessEvent):
	def __init__(self, watcher_instance):
		pyinotify.ProcessEvent.__init__(self)
		
		self.watcher_instance = watcher_instance
	# ### def __init__
	
	def process_IN_CLOSE_WRITE(self, event):
		print "Creating:", event.pathname
	# ### def process_IN_CLOSE_WRITE

	def process.IN_MOVED_TO(self, event):
		print "Moved To:", event.pathname
	# ### def process.IN_MOVED_TO

	def process_IN_DELETE(self, event):
		print "Removing:", event.pathname
	# ### def process_IN_DELETE
# ### class EventHandler

_wm = None
def monitor_start(watcher_instance, target_directory, recursive_watch=False):
	""" 開始監控目錄作業

	參數:
		watcher_instance - watcher.WatcherEngine 物件實體
		target_directory - 監測目標資料夾
		recursive_watch - 是否要遞迴監測子資料夾
	回傳值:
		(無)
	"""

	global _wm

	_wm = pyinotify.WatchManager()	# Watch Manager
	mask = pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO	# watched events
	
	
	notifier = pyinotify.AsyncNotifier(_wm, EventHandler(watcher_instance), channel_map=watcher_instance.process_driver.async_map)
	wdd = _wm.add_watch(target_directory, mask, rec=recursive_watch)
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
