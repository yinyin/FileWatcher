# -*- coding: utf-8 -*-

""" 檔案系統監視模組 """


from filewatcher import componentprop


def get_module_prop():
	""" 取得監視器各項特性/屬性

	參數:
		(無)
	回傳值:
		傳回 componentprop.OperatorProp 物件
	"""

	return componentprop.MonitorProp('monitor-name (for monitor)')
# ### def get_module_prop


def monitor_configure(config):
	""" 設定監視器組態

	參數:
		config - 帶有參數的字典
	回傳值:
		(無)
	"""

	pass
# ### def monitor_configure


def monitor_start(watcher_instance, target_directory, recursive_watch=False):
	""" 開始監控目錄作業

	參數:
		watcher_instance - watcher.WatcherEngine 物件實體
		target_directory - 監測目標資料夾
		recursive_watch - 是否要遞迴監測子資料夾
	回傳值:
		(無)
	"""

	pass
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
