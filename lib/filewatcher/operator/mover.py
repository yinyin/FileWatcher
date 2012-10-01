# -*- coding: utf-8 -*-

""" 檔案操作作業模組 """

import os
import shutil

from filewatcher import componentprop


_cached_module_prop_instance = componentprop.OperatorProp('mover', 'move_to', schedule_priority=2, run_priority=2)
def get_module_prop():
	""" 取得操作器各項特性/屬性

	參數:
		(無)
	回傳值:
		傳回 componentprop.OperatorProp 物件
	"""

	return _cached_module_prop_instance
# ### def get_module_prop


def operator_configure(config, metastorage):
	""" 設定操作器組態

	參數:
		config - 帶有參數的字典
		metastorage - 中介資訊資料庫物件
	回傳值:
		(無)
	"""

	pass
# ### def operator_configure


def read_operation_argv(argv):
	""" 取得操作設定

	參數:
		argv - 設定檔中的設定

	回傳值:
		吻合工作模組需求的設定物件
	"""

	if os.path.isdir(argv) and os.access(argv, os.W_OK):
		return os.path.abspath(argv)
	return None
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

	target_path = os.path.join(argv, orig_filename)
	try:
		if (True == os.access(target_path, os.F_OK)) and (False == os.access(target_path, os.W_OK)):
			os.unlink(target_path)
		shutil.move(current_filepath, target_path)
		logqueue.append("move %r to %r success" % (current_filepath, target_path,))
		return target_path
	except (shutil.Error, IOError) as e:
		logqueue.append("move %r to %r failed: %r" % (current_filepath, target_path, e,))
		return None
# ### def perform_operation


def operator_stop():
	""" 停止作業，準備結束

	參數:
		(無)
	回傳值:
		(無)
	"""

	pass
# ### def operator_stop



# vim: ts=4 sw=4 ai nowrap
