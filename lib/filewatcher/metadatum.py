# -*- coding: utf-8 -*-

""" 儲存運作過程中資料 """

import sqlite3
import hashlib
import base64
import time



__MSTORAGE_FRESH = 0
__MSTORAGE_EXISTED = 1
__MSTORAGE_MODIFING = 2

FPCHK_FRESH = 0
FPCHK_NEW = 1
FPCHK_STABLE = 2
FPCHK_MODIFING = 3
FPCHK_MODIFIED = 4


class MetaStorage:
	""" 儲存 Meta 資料的資料庫物件 """

	def __init__(self, file_path, meta_dupcheck_reserve_day, meta_missingfile_reserve_day):
		""" 建構子
		參數:
			file_path - 資料庫檔案路徑
			meta_dupcheck_reserve_day - 重複檔案資料保存天數 (重複性檢查)
			meta_missingfile_reserve_day - 已消失檔案資料保存天數 (新增或修改檔案檢查)
		"""

		self.db = sqlite3.connect(file_path)
		self.meta_dupcheck_reserve_second = meta_dupcheck_reserve_day * 86400
		self.meta_missingfile_reserve_second = meta_missingfile_reserve_day * 86400
		self.lastmaintain = time.time()

		self._prepare_database()
		self._maintain_database()
	# ### __init__

	def _prepare_database(self):
		""" 準備資料庫，當資料庫是新的時要建立資料表 """

		c = self.db.cursor()

		c.execute("""CREATE TABLE IF NOT EXISTS DuplicateCheck(file_name TEXT NOT NULL, file_sig TEXT NOT NULL, first_contact_time DATETIME NOT NULL, last_contact_time DATETIME NOT NULL, lifetime_retain INTEGER NOT NULL, PRIMARY KEY (file_name, file_sig))""")
		c.execute("""CREATE INDEX IF NOT EXISTS idx_DuplicateCheck_lifetime_retain ON DuplicateCheck(last_contact_time, lifetime_retain)""")
		#c.execute("""CREATE INDEX IF NOT EXISTS idx_DuplicateCheck_last_contact_time ON """)

		c.execute("""CREATE TABLE IF NOT EXISTS PresenceCheck(file_relfolder TEXT NOT NULL, file_name TEXT NOT NULL, file_size INTEGER NOT NULL, file_mtime INTEGER NOT NULL, report_status INTEGER NOT NULL, first_contact_time DATETIME NOT NULL, last_contact_time DATETIME NOT NULL, PRIMARY KEY (file_relfolder, file_name))""")
		c.execute("""CREATE INDEX IF NOT EXISTS idx_PresenceCheck_lastcontacttime ON PresenceCheck(last_contact_time)""")
		#c.execute("""CREATE INDEX IF NOT EXISTS idx_PresenceCheck_lastcontacttime ON PresenceCheck(last_contact_time)""")

		c.close()
		self.db.commit()
	# ### _prepare_database

	def _maintain_database(self):
		""" 資料庫維護: 刪除過舊的資料 """

		now_tstamp = time.time()
		if (now_tstamp - self.lastmaintain) < 7200:	# 如果離上次資料維護很近，不進行維護作業
			return
		self.lastmaintain = now_tstamp

		c = self.db.cursor()

		# 刪除過舊的重複性檢查資料
		c.execute("""DELETE FROM DuplicateCheck WHERE ((CAST(strftime('%s', 'now') AS INTEGER) + ?) > last_contact_time) AND (lifetime_retain = 0)""",
				(self.meta_dupcheck_reserve_second,))

		# 刪除過舊的新增或修改檔案檢查資料
		c.execute("""DELETE FROM PresenceCheck WHERE ((CAST(strftime('%s', 'now') AS INTEGER) + ?) > last_contact_time)""",
				(self.meta_dupcheck_reserve_second,))

		c.close()
		self.db.commit()
	# ### _maintain_database

	def close(self):
		self.db.close()
	# ### close

	def test_file_duplication_and_checkin(self, file_name, file_sig, lifetime_retain=False):
		""" 檢查檔案是不是重複，並在是新檔案時新增相關紀錄

		參數:
			file_name - 檔案名稱
			file_sig - 檔案簽章
			lifetime_retain - 檔案紀錄是否長期留存不納入 maintain/purge 作業
		回傳值:
			True - File is duplicated
			False - File is not duplicated
		"""

		self._maintain_database()

		result = False

		c = self.db.cursor()

		c.execute("""SELECT COUNT(*) FROM DuplicateCheck WHERE (file_name = ?) AND (file_sig = ?)""", (file_name, file_sig,))
		r = c.fetchone()
		if int(r[0]) == 0:
			if lifetime_retain:
				lifetime_retain = 1
			else:
				lifetime_retain = 0

			c.execute("""INSERT INTO DuplicateCheck(file_name, file_sig, first_contact_time, last_contact_time, lifetime_retain) VALUES(?, ?, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER), ?)""", (file_name, file_sig, lifetime_retain,))
		else:
			c.execute("""UPDATE DuplicateCheck SET last_contact_time=CAST(strftime('%s', 'now') AS INTEGER) WHERE (file_name = ?) AND (file_sig = ?)""", (file_name, file_sig,))
			result = True
		c.close()
		self.db.commit()

		return result
	# ### test_file_duplication_and_checkin

	def test_file_presence_and_checkin(self, file_relfolder, file_name, file_size, file_mtime):
		""" 檢查檔案是不是已經存在，並新增或更新相關紀錄，並傳回檔案是新檔或是有變更等資訊

		參數:
			file_relfolder - 檔案所在相對路徑
			file_name - 檔案名稱
			file_size - 檔案大小
			file_mtime - 檔案修改時戳
		回傳值:
			FPCHK_FRESH=0 - 全新檔案
			FPCHK_NEW=1 - 新檔案確定
			FPCHK_STABLE=2 - 已存在檔案，為變動
			FPCHK_MODIFING=3 - 檔案正在修改
			FPCHK_MODIFIED=4 - 檔案已經修改
		"""

		self._maintain_database()

		result_status = None
		file_size = int(file_size)
		file_mtime = int(file_mtime)

		c = self.db.cursor()

		c.execute("""SELECT file_size, file_mtime, report_status FROM PresenceCheck WHERE (file_relfolder = ?) AND (file_name = ?)""", (file_relfolder, file_name,))
		r = c.fetchone()
		if r is None:
			c.execute("""INSERT INTO PresenceCheck(file_relfolder, file_name, file_size, file_mtime, report_status, first_contact_time, last_contact_time) VALUES(?, ?, ?, ?, ?, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER))""", (file_relfolder, file_name, file_size, file_mtime, __MSTORAGE_FRESH,))
			result_status = FPCHK_FRESH
		else:
			meta_size = int(r[0])
			meta_mtime = r[1]
			meta_repstatus = int(r[2])

			new_repstatus = meta_repstatus

			# {{{ caculate new rep-status and return message
			if (meta_size == file_size) and (meta_mtime == file_mtime):
				if __MSTORAGE_FRESH == meta_repstatus:
					new_repstatus = __MSTORAGE_EXISTED
					result_status = FPCHK_NEW
				elif __MSTORAGE_EXISTED == meta_repstatus:
					new_repstatus = __MSTORAGE_EXISTED	# no change
					result_status = FPCHK_STABLE
				elif __MSTORAGE_MODIFING == meta_repstatus:
					new_repstatus = __MSTORAGE_EXISTED
					result_status = FPCHK_MODIFIED
			else:
				if __MSTORAGE_FRESH == meta_repstatus:
					new_repstatus = __MSTORAGE_FRESH	# no change
					result_status = FPCHK_FRESH
				elif __MSTORAGE_EXISTED == meta_repstatus:
					new_repstatus = __MSTORAGE_MODIFING
					result_status = FPCHK_MODIFING
				elif __MSTORAGE_MODIFING == meta_repstatus:
					new_repstatus = __MSTORAGE_MODIFING	# no change
					result_status = FPCHK_MODIFING
			# }}} caculate new rep-status and return message

			c.execute("""UPDATE PresenceCheck SET file_size=?, file_mtime=?, report_status=?, last_contact_time=CAST(strftime('%s', 'now') AS INTEGER) WHERE (file_relfolder = ?) AND (file_name = ?)""", (file_size, file_mtime, new_repstatus, file_relfolder, file_name,))
		c.close()
		self.db.commit()

		return result_status
	# ### test_file_presence_and_checkin

# ### MetaStorage


def compute_file_signature(filepath):
	""" 計算檔案的數位簽章

	參數:
		filepath - 檔案路徑
	回傳值:
		數位簽章字串
	"""

	f = open(filepath, 'rb')

	digester = hashlib.md5()
	reach_eof = False
	while reach_eof == False:
		data = f.read(8192)
		if not data:
			reach_eof = True
		else:
			digester.update(data)

	f.close()

	raw_dgst = digester.digest()
	encoded_dgst = base64.b64encode(raw_dgst)
	encoded_dgst = encoded_dgst.strip('=')
	return encoded_dgst
# ### compute_file_signature


__tzoffset = None
__tzoffset_last_update = 0

def get_tzoffset():
	""" 取得時區差異秒數 (在臺灣會取得負值: -28800)
	"""

	global __tzoffset, __tzoffset_last_update

	current_time = time.time()
	if (current_time - __tzoffset_last_update) > 3600:
		__tzoffset_last_update = current_time

		__tzoffset = time.altzone
		if __tzoffset is None:
			__tzoffset = time.timezone

	if __tzoffset is None:
		__tzoffset = 0

	return __tzoffset
# ### get_tzoffset

def get_time_today():
	""" 取得今日零時至現在的累計秒數 (本地時間)
	"""

	tzoffset = get_tzoffset()

	localsecond = time.time() - tzoffset
	todaysecond = localsecond % 86400

	return todaysecond
# ### get_time_today

# vim: ts=4 sw=4 ai nowrap
