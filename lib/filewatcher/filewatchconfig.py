# -*- coding: utf-8 -*-

""" 設定檔相關物件與共用函式定義 """

import os
import re
import time
import yaml

from filewatcher import metadatum


class WatcherConfiguration:
	""" global configuration """

	def __init__(self, target_directory, recursive_watch, remove_unoperate_file, meta_db_path, meta_reserve_day_duplicatecheck, meta_reserve_day_missingcheck):
		""" 建構子

		參數:
			target_directory - 要監視的目錄路徑
			recursive_watch - 是否遞迴監視子目錄
			remove_unoperate_file - 是否要移除規則檢查成功但因各種原因而未執行作業的檔案
			meta_db_path - Meta 資料庫檔案路徑
			meta_reserve_day_duplicatecheck - 重複檔案檢查資訊留存天數
			meta_reserve_day_missingcheck - 已刪除檔案檢查資訊留存天數
		"""

		self.target_directory = target_directory
		self.recursive_watch = recursive_watch
		self.remove_unoperate_file = remove_unoperate_file

		self.meta_db_path = meta_db_path
		self.meta_reserve_day_duplicatecheck = meta_reserve_day_duplicatecheck
		self.meta_reserve_day_missingcheck = meta_reserve_day_missingcheck

		self.metadb = None
		self._setup_meta_db()
	# ### def __init__

	def _setup_meta_db(self):
		""" 當指定了 Meta 資料庫檔案路徑時，建立 Meta 資料庫物件 """

		if self.meta_db_path is not None:
			self.metadb = metadatum.MetaStorage(self.meta_db_path, self.meta_reserve_day_duplicatecheck, self.meta_reserve_day_missingcheck)
	# ### def _setup_meta_db
# ### class WatcherConfiguration


class OperationEntry:
	""" configuration of operation """

	def __init__(self, opname, argv, opmodule):
		""" 建構子

		參數:
			opname - 作業名稱
			argv - 作業參數字串
			opmodule - 執行作業的模組
		"""

		self.opname = opname
		self.argv = argv
		self.opmodule = opmodule
	# ### __init__
# ### class OperationEntry


class MonitorEntry:
	""" monitor configuration """

	def __init__(self, file_regex, path_regex, do_dupcheck, operation_update, operation_remove, process_as_uniqname=True, content_check_label=None, ignorance_checker=None):
		""" 建構子

		參數:
			file_regex - 檔名正規表示式
			path_regex - 路徑 (相對於 target_directory) 正規表示式
			do_dupcheck - 是否進行重複性檢查
			operation_update - 存有作業設定的串列 (針對新增或修改檔案)
			operation_remove - 存有作業設定的串列 (針對移出或刪除檔案)
			process_as_uniqname - 是否使用唯一檔名進行後續作業 (需要目錄的 write 權限)
			content_check_label - 是否在進行重複性比對作業時使用指定的字串來覆蓋掉檔名 (不同檔名視為同一筆檔案)
			ignorance_checker - 檢查所找到的目錄或檔案是否要忽略
		"""

		self.file_regex = re.compile(file_regex)
		self.path_regex = None
		if path_regex is not None:
			self.path_regex = re.compile(path_regex)
		self.operation_update = operation_update
		self.operation_remove = operation_remove

		self.process_as_uniqname = process_as_uniqname

		self.do_dupcheck = False
		self.content_check_label = None
		if do_dupcheck:
			self.do_dupcheck = True
			self.content_check_label = content_check_label

		self.ignorance_checker = ignorance_checker
	# ### __init__
# ### class MonitorEntry



class TimeInterval:
	""" 僅含小時與分 (HH:MM) 的時間區間 """

	def __init__(self, time_start, time_end):
		""" 建構子
		參數:
			time_start - 起始時間
			time_end - 終止時間
		"""

		ts = time.strptime(time_start, "%H:%M")
		time_start = time.timedelta(minutes=ts.tm_min, hours=ts.tm_hour)

		ts = time.strptime(time_end, "%H:%M")
		time_end = time.timedelta(minutes=ts.tm_min, hours=ts.tm_hour)

		if time_start < time_end:
			self.time_start = time_start.total_seconds()
			self.time_end = time_end.total_seconds()
		else:
			self.time_start = time_end.total_seconds()
			self.time_end = time_start.total_seconds()
	# ### __init__

	def isIn(t):
		""" 給定的時戳是否落在這個時間區間之內

		參數:
			t - 時戳 (number, time.timedelta)
		回傳值:
			True - 是在區間內
			False - 否
		"""

		# {{{ convert format into seconds from mid-night
		if isinstance(t, int) or isinstance(t, long) or isinstance(t, float):
			if t >= 86400:
				t = t % 86400
		elif isinstance(t, time.timedelta):
			t = t.total_seconds()
		elif isinstance(t, time.datetime) or isinstance(t, time.time):
			t = time.timedelta(seconds=t.second, minutes=t.minute, hours=t.hour)
			t = t.total_seconds()
		# }}} convert format into seconds from mid-night

		if (self.time_start <= t) and (self.time_start >= t):
			return True
		else:
			return False
	# ### def isIn
# ### class TimeInterval



_ignorance_checker_list = {}
def register_ignorance_checker(name, checker):
	""" 註冊忽略路徑與檔案檢查器，由針對專案客製化的程式載入器呼叫

	參數:
		name - 要註冊的名字
		checker - 進行路徑與檔案名稱檢查的函式，函數原型: (relpath=None, filename=None) 回傳 True 表要忽略所檢查的項目
	"""

	global _ignorance_checker_list

	_ignorance_checker_list[name] = checker
# ### def register_ignorance_checker

def lookup_ignorance_checker(name):
	""" 找尋以指定名稱註冊的檢查器

	參數:
		name - 要找尋的名字
	回傳值:
		檢查器，或是 None
	"""

	name = name.strip()
	if len(name) < 1:
		return None

	if name in _ignorance_checker_list:
		return _ignorance_checker_list[name]
	return None
# ### def lookup_ignorance_checker



def _load_config_impl_globalconfig(configMap):
	""" 讀取全域設定資訊

	參數:
		configMap - 設定值資訊字典
	回傳值:
		WatcherConfiguration 物件
	"""

	global_config = None

	target_directory = configMap['target_directory']
	if (target_directory is None) or (False == os.path.isdir(target_directory)):
		return None
	target_directory = os.path.abspath(target_directory)

	# {{{ set 'recursive_watch'
	recursive_watch = False
	if 'recursive_watch' in configMap:
		v = configMap['recursive_watch']
		if (	( isinstance(v, bool) and (True == v) ) or
				( ((isinstance(v, str) or isinstance(v, unicode)) and (len(v) > 1)) and (str(v[0:1]) in ('y', 'Y', 't', 'T',)) ) or
				( isinstance(v, int) and (0 != v) )
			):
			recursive_watch = True
	# }}} set 'recursive_watch'

	# {{{ set 'remove_unoperate_file'
	remove_unoperate_file = True
	if 'remove_unoperate_file' in configMap:
		v = configMap['remove_unoperate_file']
		if (	( isinstance(v, bool) and (False == v) ) or
				( ((isinstance(v, str) or isinstance(v, unicode)) and (len(v) > 1)) and (str(v[0:1]) in ('n', 'N', 'F', 'f',)) ) or
				( isinstance(v, int) and (0 == v) )
			):
			remove_unoperate_file = False
	# }}} set 'remove_unoperate_file'

	# {{{ load meta storage options
	meta_db_path = None
	meta_reserve_day_duplicatecheck = 3
	meta_reserve_day_missingcheck = 2
	if ('meta' in configMap) and isinstance(configMap['meta'], dict):
		meta_cfg = configMap['meta']
		meta_db_path = meta_cfg['db_path']

		if 'duplicate_check_reserve_day' in meta_cfg:
			meta_reserve_day_duplicatecheck = int(meta_cfg['duplicate_check_reserve_day'])
			if meta_reserve_day_duplicatecheck < 1:
				meta_reserve_day_duplicatecheck = 1

		if 'missing_detect_reserve_day' in meta_cfg:
			meta_reserve_day_missingcheck = int(meta_cfg['missing_detect_reserve_day'])
			if meta_reserve_day_missingcheck < 1:
				meta_reserve_day_missingcheck = 1
	# }}} load meta storage options

	global_config = WatcherConfiguration(target_directory, recursive_watch, remove_unoperate_file, meta_db_path, meta_reserve_day_duplicatecheck, meta_reserve_day_missingcheck)

	return global_config
# ### _load_config_impl_globalconfig

def _load_config_impl_moduleconfig(configMap, config_reader, global_config):
	""" 讀取模組設定資訊

	參數:
		configMap - 設定值資訊字典
		config_reader - 以「模組的設定名稱」為鍵「模組實體」為值的 dict 結構體
		global_config - 全域設定值
	回傳值:
		(無)
	"""

	for mod_cfgname, mod_object in config_reader.iteritems():
		if mod_cfgname in configMap:
			m = mod_object.get_module_prop()
			cfg_content = configMap[mod_cfgname]
			if m.isMonitor:
				mod_object.monitor_configure(cfg_content, global_config.metadb)
			if m.isOperator:
				mod_object.operator_configure(cfg_content, global_config.metadb)
# ### _load_config_impl_moduleconfig

def _load_config_impl_watchentries_operation(operation_cfg, operation_deliver, operation_schedule_seq, operation_run_seq):
	""" 載入 watch entries 的 operation 作業設定

	參數:
		operation_cfg - 作業設定
		operation_deliver - 以作業名稱為 key 監視工作模組為 value 的字典
		operation_schedule_seq - 排定作業塊先後順序用的作業名稱串列
		operation_run_seq - 排定作業執行先後順序用的作業名稱串列
	回傳值:
		含有 OperationEntry 物件的串列
	"""

	ordered_operation_block = []

	# {{{ 將 operation block 依據 operation_schedule_seq 排序
	remain_oprcfg = operation_cfg
	for opname in operation_schedule_seq:
		#print ">>> %r" % (opname,)
		next_remain_oprcfg = []
		for oprblk_cfg in remain_oprcfg:
			if opname in oprblk_cfg:
				ordered_operation_block.append(oprblk_cfg)
			else:
				next_remain_oprcfg.append(oprblk_cfg)
		if len(next_remain_oprcfg) < 1:
			remain_oprcfg = None
			break
		remain_oprcfg = next_remain_oprcfg
	#print ">>> remain %r" % (remain_oprcfg,)
	# }}} 將 operation block 依據 operation_schedule_seq 排序

	organized_operation_block = []

	# {{{ 將各 operation block 內的作業依據 operation_run_seq 排序
	for oprblk_cfg in ordered_operation_block:
		oprblock = []
		for opname in operation_run_seq:
			if opname in oprblk_cfg:
				oparg = operation_deliver[opname].read_operation_argv(oprblk_cfg[opname])
				if oparg is not None:
					oprblock.append(OperationEntry(opname, oparg, operation_deliver[opname]))
		if len(oprblock) > 0:
			organized_operation_block.append(oprblock)
	# }}} 將各 operation block 內的作業依據 operation_run_seq 排序

	return organized_operation_block
# ### def _load_config_impl_watchentries_updateoprn

def _load_config_impl_watchentries(watch_entries_cfg, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq):
	""" 載入檔案規則設定

	參數:
		watch_entries_cfg - 檔案監看規則設定
		operation_deliver - 以作業名稱為 key 監視工作模組為 value 的字典
		operation_schedule_seq - 排定作業塊先後順序用的作業名稱串列
		operation_run_newupdate_seq - 排定作業執行先後順序用的作業名稱串列
	回傳值:
		含有 OperationEntry 物件的串列
	"""

	watch_entries = []

	for entry_cfg in watch_entries_cfg:
		try:
			file_regex = str(entry_cfg['file_regex'])
			path_regex = None
			if 'path_regex' in entry_cfg:
				path_regex = str(entry_cfg['path_regex'])

			do_dupcheck = False
			if 'duplicate_check' in entry_cfg:
				v = entry_cfg['duplicate_check']
				if (	( isinstance(v, bool) and (True == v) )
						or ( isinstance(v, str) and (v in ('Y', 'y', '1', 'Yes', 'YES', 'yes', 'T', 'True',)) )
						or ( isinstance(v, unicode) and (v in (u'Y', u'y', u'1', u'Yes', u'YES', u'yes', u'T', u'True',)) )
					):
					do_dupcheck = True

			content_check_label = None
			if (True == do_dupcheck) and ('duplicate_content_check_label' in entry_cfg):
				v = str(entry_cfg['duplicate_content_check_label'])
				v = v.strip()
				if len(v) > 0:
					content_check_label = v

			process_as_uniqname = True
			if 'process_as_uniqname' in entry_cfg:
				v = entry_cfg['process_as_uniqname']
				if (	( isinstance(v, bool) and (True == v) )
						or ( isinstance(v, str) and (v in ('Y', 'y', '1', 'Yes', 'YES', 'yes', 'T', 'True',)) )
						or ( isinstance(v, unicode) and (v in (u'Y', u'y', u'1', u'Yes', u'YES', u'yes', u'T', u'True',)) )
					):
					process_as_uniqname = True

			ignorance_checker = None
			if 'ignorance-checker' in entry_cfg:
				ignorance_checker = lookup_ignorance_checker(str(entry_cfg['ignorance-checker']))

			# {{{ load operations
			operation_update = None
			if 'update-operation' in entry_cfg:
				operation_update = _load_config_impl_watchentries_operation(entry_cfg['update-operation'], operation_deliver, operation_schedule_seq, operation_run_newupdate_seq)
			elif 'operation' in entry_cfg:
				operation_update = _load_config_impl_watchentries_operation(entry_cfg['operation'], operation_deliver, operation_schedule_seq, operation_run_newupdate_seq)

			operation_remove = None
			if 'remove-operation' in entry_cfg:
				operation_remove = _load_config_impl_watchentries_operation(entry_cfg['remove-operation'], operation_deliver, operation_schedule_seq, operation_run_dismiss_seq)
			# }}} load operations

			entryobj = MonitorEntry(file_regex, path_regex, do_dupcheck, operation_update, operation_remove, process_as_uniqname, content_check_label, ignorance_checker)
			watch_entries.append(entryobj)
		except:
			print "Failed on loading watch entry: %r" % (entry_cfg,)
			raise

	return watch_entries
# ### def _load_config_impl_watchentries

def load_config(config_filename, config_reader, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq):
	"""" 讀取設定檔內容

	參數:
		config_filename - 設定檔檔名
		config_reader - 以「模組的設定名稱」為鍵「模組實體」為值的 dict 結構體
		operation_deliver - 以作業名稱為 key 監視工作模組為 value 的字典
		operation_schedule_seq - 排定作業塊先後順序用的作業名稱串列
		operation_run_newupdate_seq - 排定作業執行先後順序用的作業名稱串列 (針對檔案新增或修改事件)
		operation_run_dismiss_seq - 排定作業執行先後順序用的作業名稱串列 (針對檔案刪除或移出事件)
	傳回值:
		(global_config, watch_entries,) - 存放 WatcherConfiguration 物件 (global_config) 及 MonitorEntry 物件 list (watch_entries) 的 tuple
	"""

	fp = open(config_filename, 'r')
	configMap = yaml.load(fp)
	fp.close()

	# Global Configuration
	global_config = _load_config_impl_globalconfig(configMap)
	if global_config is None:
		return None

	# Module Configuration
	_load_config_impl_moduleconfig(configMap, config_reader, global_config)
	# }}} configure modules

	# Watch Entries
	watch_entries = _load_config_impl_watchentries(configMap['watching_entries'], operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq)

	return (global_config, watch_entries,)
# ### def load_config



def __keyfunction_prop_schedule(prop):
	""" 排序用 key function (componentprop.OperatorProp 物件，針對 schedule_priority) """

	return prop.schedule_priority
# ### def __keyfunction_schedule

def __keyfunction_prop_run(prop):
	""" 排序用 key function (componentprop.OperatorProp 物件，針對 run_priority) """

	return prop.run_priority
# ### def __keyfunction_prop_run


def get_module_interfaces(mods):
	""" 取得工作模組的屬性，並依此設定相關參數

	參數:
		mods - 含有工作模組的串列
	回傳值:
		含有以下元素的 tuple: (config_readers, monitor_implement, operation_deliver, operation_schedule_seq, operation_run_seq)
		config_readers - 以設定檔段落名稱為 key 工作模組為 value 的字典
		monitor_implement - 以監視工作模組名稱 (同設定檔段落名稱) 作為 key 監視模組為 value 的字典
		operation_deliver - 以作業名稱為 key 監視工作模組為 value 的字典
		operation_schedule_seq - 排定作業塊先後順序用的作業名稱串列
		operation_run_newupdate_seq - 排定作業執行先後順序用的作業名稱串列 (針對檔案新增或修改事件)
		operation_run_dismiss_seq - 排定作業執行先後順序用的作業名稱串列 (針對檔案刪除或移出事件)
	"""

	config_readers = {}

	monitor_implement = {}

	operation_deliver = {}
	operation_schedule_seq = []
	operation_run_newupdate_seq = []
	operation_run_dismiss_seq = []

	for m in mods:
		prop = m.get_module_prop()

		config_sec_name = prop.module_name
		config_readers[config_sec_name] = m

		# {{{ if module is monitor module
		if prop.isMonitor:
			monitor_name = prop.module_name
			monitor_implement[monitor_name] = m
		# }}} if module is monitor module

		# {{{ if module is operator module
		if prop.isOperator:
			operation_name = prop.operation_name
			if prop.run_priority is not None:	# only push into dict. if run-priority is available
				operation_deliver[operation_name] = m
				operation_run_newupdate_seq.append(prop)

				if prop.schedule_priority is not None:
					operation_schedule_seq.append(prop)

				if prop.handle_dismiss:
					operation_run_dismiss_seq.append(prop)
		# }}} if module is operator module

	# {{{ sort operator module lists
	operation_schedule_seq = [x.operation_name for x in sorted(operation_schedule_seq, key=__keyfunction_prop_schedule)]	# eg: 含有 copy 的作業塊應該比含有 move 的早執行
	operation_run_newupdate_seq = [x.operation_name for x in sorted(operation_run_newupdate_seq, key=__keyfunction_prop_run)]	# eg: copy 或 move 要比 coderunner 早執行
	operation_run_dismiss_seq = [x.operation_name for x in sorted(operation_run_dismiss_seq, key=__keyfunction_prop_run)]
	# }}} sort operator module lists

	return (config_readers, monitor_implement, operation_deliver, operation_schedule_seq, operation_run_newupdate_seq, operation_run_dismiss_seq,)
# ### def get_module_interfaces



# vim: ts=4 sw=4 ai nowrap
