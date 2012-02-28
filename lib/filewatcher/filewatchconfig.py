# -*- coding: utf-8 -*-

""" 設定檔相關物件與共用函式定義 """

import re
import time
import yaml


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

	def __init__(self, file_regex, path_regex, do_dupcheck, operation, process_as_uniqname=True, content_check_label=None):
		""" 建構子

		參數:
			file_regex - 檔名正規表示式
			path_regex - 路徑 (相對於 target_directory) 正規表示式
			do_dupcheck - 是否進行重複性檢查
			operation - 存有作業設定的串列
			process_as_uniqname - 是否使用唯一檔名進行後續作業 (需要目錄的 write 權限)
			content_check_label - 是否在進行重複性比對作業時使用指定的字串來覆蓋掉檔名 (不同檔名視為同一筆檔案)
		"""

		self.file_regex = re.compile(file_regex)
		self.path_regex = re.compile(path_regex)
		self.operation = operation
		self.process_as_uniqname = process_as_uniqname

		self.do_dupcheck = False
		self.content_check_label = None
		if do_dupcheck:
			self.do_dupcheck = True
			self.content_check_label = content_check_label
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



# vim: ts=4 sw=4 ai nowrap
