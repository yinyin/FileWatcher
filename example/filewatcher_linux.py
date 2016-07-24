#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys



#def _check_if_ignore(folder, filename):
#	""" 檢查是否要略過指定的資料夾或檔案
#	Argument:
#		folder - 資料夾名稱 (相對於目標資料夾的相對路徑)
#		filename - 檔案名稱，當為 None 值時表示檢查是否要略過整個資料夾
#	Return:
#		傳回 True 表示要略過 (不再監視) 指定的資料夾或檔案，或是 False 當不略過 (繼續監視)
#	"""
#	return False
# ### def _check_if_ignore

#def _inotify_queue_full():
#	""" 當 iNotify 佇列滿時會呼叫這個函數
#	"""
#	print "WARN: iNotify Queue Full"
# ### def _inotify_queue_full

def _get_watcher_modules():
	""" 取得要使用的模組列表
	"""
	from filewatcher.monitor import linux_inotify
	from filewatcher.operator import copier
	from filewatcher.operator import mover
	from filewatcher.operator import coderunner
	# from mypackage import mymodule

	linux_inotify.set_revise_period(600)
	# linux_inotify.set_ignorance_checker(_check_if_ignore)
	# linux_inotify.set_queue_overflow_callback(_inotify_queue_full)

	return (linux_inotify,
			copier, mover, coderunner,
			#mymodule,
		)
# ### def _get_watcher_modules


def _start_watcher(config_path):
	""" 啟動 file watcher
	"""
	from filewatcher import watcher
	watcher.FW_APP_NAME = 'FileWatcher_for_Linux-example'
	watcher.run_watcher(config_path, _get_watcher_modules())
# ### def _start_watcher



if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Argument: [FILEWATCHER_CONFIG]"
		sys.exit(1)

	filewatcher_config_path = sys.argv[1]

	_start_watcher(filewatcher_config_path)
# <<< if __name__ == "__main__":



# vim: ts=4 sw=4 foldmethod=marker ai nowrap
