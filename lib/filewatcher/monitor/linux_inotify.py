# -*- coding: utf-8 -*-

""" 檔案系統監視模組 """


from filewatcher import componentprop
from filewatcher import filewatchconfig


def _get_relpath(path, start):
	relpath = os.path.relpath(path, start)
	if '.' == relpath:
		return ''
	else:
		return relpath
# ### def _get_relpath


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


class _ExcludeFilter:
	def __init__(self, target_directory, recursive_watch=False):
		self.target_directory = target_directory
		self.recursive_watch = recursive_watch
	# ### def __init__
	
	def do_exclude_filting(self, filepath):
		filepath = os.path.abspath(filepath)
		if os.path.isdir(filepath):
			path = filepath
			name = None
		else:
			path, name, = os.path.split(filepath)

		if (False == self.recursive_watch) and (path != self.target_directory):
			return True

		if _ignorance_checker is not None:
			relpath = _get_relpath(path, self.target_directory)
			r = _ignorance_checker(relpath, name)
			if r:
				return True

		return False
	# ### def do_exclude_filting

	def __call__(self, path):
		return self.do_exclude_filting(path)
	# ### def __call__
# ### class _ExcludeFilter

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


class _EventHandler(pyinotify.ProcessEvent):
	def __init__(self, watcher_instance, target_directory):
		pyinotify.ProcessEvent.__init__(self)
		
		self.watcher_instance = watcher_instance
		self.target_directory = target_directory
	# ### def __init__

	def trigger_operation(self, pathname, watcher_eventcode):
		path, name, = os.path.split(os.path.abspath(pathname))
		relpath = _get_relpath(path, self.target_directory)
		self.watcher_instance.discover_file_change(name, relpath, watcher_eventcode))
	# ### def perform_modified_operation
	
	def process_IN_CLOSE_WRITE(self, event):
		print "inotify::IN_CLOSE_WRITE: %r" % (event.pathname,)
		self.trigger_operation(event.pathname, watcher.FEVENT_MODIFIED)
	# ### def process_IN_CLOSE_WRITE

	def process_IN_MOVED_TO(self, event):
		print "inotify::IN_MOVED_TO: %r" % (event.pathname,)
		self.trigger_operation(event.pathname, watcher.FEVENT_MODIFIED)
	# ### def process.IN_MOVED_TO

	def process_IN_DELETE(self, event):
		print "inotify::IN_DELETE: %r" % (event.pathname,)
		self.trigger_operation(event.pathname, watcher.FEVENT_DELETED)
	# ### def process_IN_DELETE
# ### class EventHandler

_watchmanager = None
def monitor_start(watcher_instance, target_directory, recursive_watch=False):
	""" 開始監控目錄作業

	參數:
		watcher_instance - watcher.WatcherEngine 物件實體
		target_directory - 監測目標資料夾
		recursive_watch - 是否要遞迴監測子資料夾
	回傳值:
		(無)
	"""

	global _watchmanager

	_watchmanager = pyinotify.WatchManager(exclude_filter=_ExcludeFilter(target_directory, recursive_watch))
	mask = pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO	# watched events
	handler = _EventHandler(watcher_instance, target_directory)
	
	notifier = pyinotify.AsyncNotifier(_wm, handler, channel_map=watcher_instance.process_driver.async_map)
	wdd = _wm.add_watch(target_directory, mask, rec=True)
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
