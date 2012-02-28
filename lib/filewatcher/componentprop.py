# -*- coding: utf-8 -*-

""" 各種元件屬性值物件 """

class ModuleProp:
	""" 模組屬性，所有工作模組屬性的父類別 """

	def __init__(self, module_name, isMonitor=False, isOperator=False):
		""" 建構子

		參數:
			module_name - 模組名稱 (讀取設定檔時會依此分派)
			isMonitor - 是否為監視器模組 (True/False)
			isOperator - 是否為操作器模組 (True/False)
		"""

		self.module_name = module_name

		self.isMonitor = isMonitor
		self.isOperator = isOperator
	# ### def __init__
# ### class ModuleProp

class MonitorProp(ModuleProp):
	""" 監視器工作模組屬性 """

	def __init__(self, module_name):
		""" 建構子

		參數:
			module_name - 模組名稱 (讀取設定檔時會依此分派)
		"""

		ModuleProp.__init__(self, module_name, isMonitor=True)
	# ### def __init__
# ### class OperatorProp

class OperatorProp(ModuleProp):
	""" 操作器工作模組屬性 """

	def __init__(self, module_name, operation_name, schedule_priority=None, run_priority=None):
		""" 建構子

		參數:
			module_name - 模組名稱 (讀取設定檔時會依此分派)
			operation_name - 操作名稱
			schedule_priority - 操作塊排程優先順序，數字小的先執行 (若操作不影響排程或是不受排程影響，則設定為 None)
			run_priority - 執行優先順序，數字小的先執行
		"""

		ModuleProp.__init__(self, module_name, isOperator=True)

		self.operation_name = operation_name
		self.schedule_priority = schedule_priority
		self.run_priority = run_priority
	# ### def __init__
# ### class OperatorProp



# vim: ts=4 sw=4 ai nowrap
