import mysql.connector
pswd=input("Enter MySQL Password ")
mydb=mysql.connector.connect(
	host="localhost",
	user="root",
	password=pswd,
	database="Attend_DB"
	)
control=mydb.cursor()
control.execute("show tables")
for x in control:
	print(x)