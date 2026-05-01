try:
	import MySQLdb  # noqa: F401
except Exception:
	import pymysql

	pymysql.install_as_MySQLdb()
