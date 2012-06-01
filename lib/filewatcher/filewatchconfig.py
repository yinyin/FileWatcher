# -*- coding: utf-8 -*-

""" 設定檔相關物件與共用函式定義 """

import re
import time
import yaml

from filewatcher import metadatum


class WatcherConfiguration:
	""" global configuration """
	
	def __init__(self, target_directory, recursive_watch, meta_db_path, meta_reserve_day_duplicatecheck, meta_reserve_day_missingcheck):
		""" 建構子

		參數:
			target_directory - 要監視的目錄路徑
			recursive_watch - 是否遞迴監視子目錄
			meta_db_path - Meta 資料庫檔案路徑
			meta_reserve_day_duplicatecheck - 重複檔案檢查資訊留存天數
			meta_reserve_day_missingcheck - 已刪除檔案檢查資訊留存天數
		"""
	
		self.target_directory = target_directory
		self.recursive_watch = recursive_watch

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

	def __init__(self, op, argv):
		""" 建構子

		參數:
			op - 作業名稱
			argv - 作業參數字串
		"""

		self.op = op
		self.argv = argv
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
	
	# {{{ set 'recursive_watch'
	recursive_watch = False
	if 'recursive_watch' in configMap:
		cfg_recursivewatch = configMap['recursive_watch']
		if isinstance(cfg_recursivewatch, bool):
			recursive_watch = cfg_recursivewatch
		elif (isinstance(cfg_recursivewatch, str) or isinstance(cfg_recursivewatch, unicode)) and (len(cfg_recursivewatch) > 1):
			cfg_recursivewatch = cfg_recursivewatch[0:1]
			if ('y' == cfg_recursivewatch) or ('Y' == cfg_recursivewatch):
				recursive_watch = True
		elif isinstance(cfg_recursivewatch, int)
			if cfg_recursivewatch != 0:
				recursive_watch = True
	# }}} set 'recursive_watch'

	# {{{ load meta storage options
	meta_db_path = None
	meta_reserve_day_duplicatecheck = 3
	meta_reserve_day_missingcheck = 2
	if ('meta' in configMap) and isinstance():
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
	
	global_config = WatcherConfiguration(target_directory, recursive_watch, meta_db_path, meta_reserve_day_duplicatecheck, meta_reserve_day_missingcheck)
	
	return global_config
# ### _load_config_impl_globalconfig

def _load_config_impl_moduleconfig(configMap, config_reader):
	""" 讀取模組設定資訊
	
	參數:
		configMap - 設定值資訊字典
		config_reader - 以「模組的設定名稱」為鍵「模組實體」為值的 dict 結構體
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

def _load_config_impl_watchentries(watch_entries_cfg, ):
	
	watch_entries = []
	
	for entry in watch_entries_cfg:
		try:
			file_regex = re.compile(entry['file_regex'])
			path_regex = None
			if 'path_regex' in entry:
				path_regex = re.compile(entry['path_regex'])
			
			do_dupcheck = False
			if 'duplicate_check' in entry:
				v = entry['duplicate_check']
				if ( isinstance(v, bool) and (True == v) )
					or ( isinstance(v, str) and (v in ('Y', 'y', '1', 'Yes', 'YES', 'yes', 'T', 'True',)) )
					or ( isinstance(v, unicode) and (v in (u'Y', u'y', u'1', u'Yes', u'YES', u'yes', u'T', u'True',)) ):
					do_dupcheck = True
			
			content_check_label = None
			if (True == do_dupcheck) and ('duplicate_content_check_label' in entry):
				v = str(entry['duplicate_content_check_label'])
				v = v.strip()
				if len(v) > 0:
					content_check_label = v
			
			process_as_uniqname = True
			if 'process_as_uniqname' in entry:
				v = entry['process_as_uniqname']
				if ( isinstance(v, bool) and (True == v) )
					or ( isinstance(v, str) and (v in ('Y', 'y', '1', 'Yes', 'YES', 'yes', 'T', 'True',)) )
					or ( isinstance(v, unicode) and (v in (u'Y', u'y', u'1', u'Yes', u'YES', u'yes', u'T', u'True',)) ):
					process_as_uniqname = True
			
			ignorance_checker = None
			if 'ignorance-checker' in entry:
				ignorance_checker = lookup_ignorance_checker(str(entry['ignorance-checker']))
			
			operation_update = []	# TODO
			operation_remove = []	# TODO
			
			entryobj = MonitorEntry(file_regex, path_regex, do_dupcheck, operation_update, operation_remove, process_as_uniqname, content_check_label, ignorance_checker)
			watch_entries.append(entryobj)
		except:
			print "Failed on loading watch entry: %r" % (entry,)
			raise
	
	return watch_entries
# ### def _load_config_impl_watchentries

def load_config(config_filename, config_reader):
	"""" 讀取設定檔內容
	
	參數:
		config_filename - 設定檔檔名
		config_reader - 以「模組的設定名稱」為鍵「模組實體」為值的 dict 結構體
		
	"""
	
	fp = open(config_filename, 'r')
	configMap = yaml.load(fp)
	fp.close()
	
	# Global Configuration
	global_config = _load_config_impl_globalconfig(configMap)
	if global_config is None:
		return None
	
	# Module Configuration
	_load_config_impl_moduleconfig(configMap, config_reader)
	# }}} configure modules
	
	# Watch Entries
	watch_entries = _load_config_impl_watchentries(configMap['watching_entries'])
	
	
# ### def load_config



# vim: ts=4 sw=4 ai nowrap
