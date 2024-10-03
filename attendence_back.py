import mysql.connector
import datetime
import time

pswd=input("Enter MySQL Password ")
mydb=mysql.connector.connect(
	host="localhost",
	user="root",
	password=pswd,
	database="Attend_DB"
	)

control=mydb.cursor()

def control_loop():
    for x in control:
        print(x)

def show_table(tablename):
    control.execute(f"select * from {tablename};")
    control_loop()

def update_Admins(id,mail,fname,lname,passwd):
    control.execute(f"insert into Admins values ('{id}','{mail}','{fname}','{lname}','{passwd}');") 

def update_Sessions(sid,stime,etime,aid):
    control.execute(f"insert into Sessions values ('{sid}','{stime}','{etime}','{aid}');") 
    
def update_Attendees(uid,mail,fname,lname,passwd,addr,sid):
    control.execute(f"insert into Attendees values ('{uid}','{mail}','{fname}','{lname}','{passwd}','{addr}','{sid}');") 
    
def update_AttendeesLocations(loctimestmp,long,lat,uid):
    control.execute(f"insert into AttendeesLocations values ('{loctimestmp}',{long},{lat},'{uid}');") 
    
def update_SessionLocations(addr,long,lat,sid):
    control.execute(f"insert into SessionLocations values ('{addr}',{long},{lat},'{sid}');") 

#Test

print("Admins")
hashed_passwd="161402bab34cb90b141af9df702cb5a1925ed00da970cf12d0e4072fd47a2050"
update_Admins("0123456789","test@gmail.com","firstname","lastname",hashed_passwd)
show_table("Admins")

print("Sessions")
current_time = datetime.datetime.now()
time1 = current_time.strftime("%Y-%m-%d %H:%M:%S")
time.sleep(5)
current_time = datetime.datetime.now()
time2 = current_time.strftime("%Y-%m-%d %H:%M:%S")
update_Sessions("abcdefghij",time1,time2,"0123456789")
show_table("Sessions")

print("Attendees")
hashed_passwd2="d84dd79b896345f2034cbae2213a1fb77c2c34151c9dc6d7919d02f19e5ecb15"
update_Attendees("9876543210","trial@gmail.com","fname","lname",hashed_passwd2,"---","abcdefghij")
show_table("Attendees")

print("AttendeesLocations")
time.sleep(5)
current_time = datetime.datetime.now()
time1 = current_time.strftime("%Y-%m-%d %H:%M:%S")
update_AttendeesLocations(time1,147.849489,61.765021,"9876543210")
show_table("AttendeesLocations")

print("SessionLocations")
update_SessionLocations("-------",-105.286359,-1.423421,"abcdefghij")
show_table("SessionLocations")