from decimal import Decimal
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator
from dotenv import load_dotenv
from psycopg2 import pool
from contextlib import contextmanager
import bcrypt
import os
from jose import jwt
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from datetime import datetime
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv('.env.local')

SQL_URL=os.getenv("SQL_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
ALGORITHM = 'HS256'

connection_pool = pool.SimpleConnectionPool(1, 5, dsn=SQL_URL)

@contextmanager
def get_connection():
    connection = connection_pool.getconn()
    try:
        yield connection
    finally:
        connection_pool.putconn(connection)

@contextmanager
def get_cursor(connection):
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()

@app.get("/hello")
def hello():
    return {"Hello": "World"}

@app.get("/robots.txt")
def robots_begone():
    return {"User-agent":"*","Disallow":"/"}

# def hash_password(password: str):
#     salt = bcrypt.gensalt()
#     hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
#     return (hashed_password.decode('utf-8'),base64.b64encode(salt).decode('utf-8'))

def hash_password(password: str):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')
    
# def rehash(password: str, salt64: str):
#     salt=base64.b64decode(salt64.encode('utf-8'))
#     hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
#     return hashed_password.decode('utf-8')

def create_jwt_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30))) + timedelta(days=14)})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_jwt_token(tok: str):
    return jwt.decode(tok, JWT_SECRET, algorithms=[ALGORITHM])

class Admin(BaseModel):
    email: EmailStr = Field(..., description="Email of the admin")
    fname: str = Field(..., description="First name of the admin")
    lname: str = Field(..., description="Last name of the admin")
    password: str = Field(..., description="Unhashed Password of the admin")

"""
Sample request in curl:

curl -X POST "http://127.0.0.1:8000/auth/register-admin" \
-H "Content-Type: application/json" \
-d '{"email": "abcd@gmail.com", "fname": "ab", "lname": "cd", "password": "123"}' 
"""
@app.post("/auth/register-admin")
def register_admin(admin: Admin):
    email = admin.email.lower()  # Lowercase the email to maintain consistency
    fname = admin.fname
    lname = admin.lname
    password = admin.password

    with get_connection() as connection:
        with get_cursor(connection) as control:
            # Check if admin already exists
            control.execute("SELECT 1 FROM Admins WHERE Email = %s;", (email,))
            existing_admins = control.fetchone()
            if existing_admins:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin already exists")
            
            # Hash password
            hashed_passwd = hash_password(password)
            
            # Insert new admin and get the ID
            control.execute(
                "INSERT INTO Admins (Email, FirstName, LastName, Passwd) VALUES (%s, %s, %s, %s) RETURNING AdminID;",
                (email, fname, lname, hashed_passwd)
            )
            last_row_id = control.fetchone()[0]
            connection.commit()

    # Generate JWT token
    access_token = create_jwt_token({"id": last_row_id, "email": email, "role": "admin", "fname": fname, "lname": lname})
    return {"access_token": access_token}

# Attendee model
class Attendee(BaseModel):
    email: EmailStr = Field(..., description="Email of the attendee")
    fname: str = Field(..., description="First name of the attendee")
    lname: str = Field(..., description="Last name of the attendee")
    password: str = Field(..., description="Unhashed Password of the attendee")
    address: str = Field(..., description="Address of the attendee")

# Register attendee endpoint
@app.post("/auth/register-attendee")
def register_attendee(attendee: Attendee):
    email = attendee.email.lower()
    fname = attendee.fname
    lname = attendee.lname
    password = attendee.password
    address = attendee.address

    with get_connection() as connection:
        with get_cursor(connection) as control:
            # Check if attendee already exists
            control.execute("SELECT 1 FROM Attendees WHERE Email = %s;", (email,))
            existing_attendees = control.fetchone()
            if existing_attendees:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendee already exists")
            
            # Hash password
            hashed_passwd = hash_password(password)

            # Insert new attendee and get the ID
            control.execute(
                "INSERT INTO Attendees (Email, Fname, Lname, Passwd, Address) VALUES (%s, %s, %s, %s, %s) RETURNING UniqueID;",
                (email, fname, lname, hashed_passwd, address)
            )
            last_row_id = control.fetchone()[0]
            connection.commit()
    
    # Generate JWT token
    access_token = create_jwt_token({"id": last_row_id, "email": email, "role": "attendee", "fname": fname, "lname": lname})
    return {"access_token": access_token}

# Login model
class Login(BaseModel):
    email: EmailStr = Field(..., description="Email of the admin or attendee")
    password: str = Field(..., description="Unhashed Password of the admin or attendee")

# Admin login endpoint
@app.post("/auth/login-admin")
def login_admin(details: Login):
    email = details.email.lower()
    password = details.password

    with get_connection() as connection:
        with get_cursor(connection) as control:
            # Check if admin exists and verify password
            control.execute("SELECT AdminID, FirstName, LastName, Passwd FROM Admins WHERE Email = %s;", (email,))
            match = control.fetchone()
            if match and bcrypt.checkpw(password.encode('utf-8'), match[3].strip().encode('utf-8')):  # Verify hashed password
                access_token = create_jwt_token({
                    "id": match[0],
                    "email": email,
                    "role": "admin",
                    "fname": match[1],
                    "lname": match[2]
                })
                return {"access_token": access_token}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Please sign up first")

@app.post("/auth/login-attendee")
def login_attendee(details: Login):
    email = details.email.lower()
    password = details.password

    with get_connection() as connection:
        with get_cursor(connection) as control:
            # Check if attendee exists and verify password
            control.execute("SELECT UniqueID, Fname, Lname, Passwd FROM Attendees WHERE Email = %s;", (email,))
            match = control.fetchone()
            if match and bcrypt.checkpw(password.encode('utf-8'), match[3].strip().encode('utf-8')):  # Verify hashed password
                access_token = create_jwt_token({
                    "id": match[0],
                    "email": email,
                    "role": "attendee",
                    "fname": match[1],
                    "lname": match[2]
                })
                return {"access_token": access_token}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Please sign up first")

class session_locs(BaseModel):
    address: str = Field(..., description="Address of a session location", min_length=0, max_length=100)
    longitude: float = Field(..., description="Longitude of a session location", ge=-180, le=180)
    latitude: float = Field(..., description="Latitude of a session location", ge=-90, le=90)
    
class create_session_info(BaseModel):
    tok: str = Field(..., description="JWT token from the client") 
    start_time: str = Field(..., description="Start time for the session")
    end_time: str = Field(..., description="End time of the session")
    locs: Optional[Tuple[session_locs, ...]] = Field(..., description="A tuple with the session locations for this session")
    
    @validator('start_time', 'end_time')
    def check_time_format(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', v):
            raise ValueError('Invalid time format, expected YYYY-MM-DD HH:MM:SS')
        return v
    
class add_locs(BaseModel):
    tok: str = Field(..., description="JWT token from the client") 
    sessionid: int = Field(..., description="ID of the session whose locations are being updated")
    locs: Optional[Tuple[session_locs, ...]] = Field(..., description="A tuple with the session locations for this session")

@app.post("/create-session")
def create_session(details: create_session_info):
    admin_details = decode_jwt_token(details.tok)
    start_time = datetime.strptime(details.start_time, '%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime(details.end_time, '%Y-%m-%d %H:%M:%S')
    locations = details.locs

    if admin_details["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an admin")

    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.execute("SELECT 1 FROM Admins WHERE AdminID = %s;", (admin_details["id"],))
            existing_admin = control.fetchone()
            if not existing_admin:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin does not exist")

            if start_time >= end_time:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ensure the session start and end times are correct")

            control.execute(
                "INSERT INTO Sessions (StartTime, EndTime, AdminID) VALUES (%s, %s, %s) RETURNING SessionID;",
                (start_time, end_time, admin_details["id"])
            )
            session_id = control.fetchone()[0]
            connection.commit()

            for x in locations:
                control.execute(
                    "INSERT INTO SessionLocations (Address, Longitude, Latitude, SessionID) VALUES (%s, %s, %s, %s);",
                    (x.address, x.longitude, x.latitude, session_id)
                )
            connection.commit()

    return {"result": "Session successfully created"}

@app.post("/add-locations")
def add_session_locations(details: add_locs):
    admin_details=decode_jwt_token(details.tok)
    session_id=details.sessionid
    locations=details.locs
    
    if admin_details["role"]!="admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an admin")
    
    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.execute("select AdminID from Sessions where SessionID=%s;", (session_id,))
            match = control.fetchone()
            if match[0]!=admin_details["id"]:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the session manager")
            
            for x in locations:
                control.execute("insert into SessionLocations (Address, Longitude, Latitude, SessionID) values (%s, %s, %s, %s);", (x.address, x.longitude, x.latitude, session_id))
                connection.commit()
    
    return {"result":"Session locations updated"}
    
class join_sess(BaseModel):
    tok: str = Field(..., description="JWT token from the client")
    sessionid: int = Field(..., description="ID of the session the attendee is joining")
    latitude: float = Field(..., description="Latitude of the current location", ge=-90, le=90)
    longitude: float = Field(..., description="Longitude of the current location", ge=-180, le=180)

@app.post("/join-session")
def join_session(details: join_sess):
    attendee_details = decode_jwt_token(details.tok)
    session_id = details.sessionid
    latitude = round(details.latitude, 6)
    longitude = round(details.longitude, 6)

    if attendee_details["role"] == "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an attendee")
    
    with get_connection() as connection:
        with get_cursor(connection) as control:
            # Check if attendee exists
            control.execute("SELECT 1 FROM Attendees WHERE UniqueID = %s;", (attendee_details["id"],))
            existing_attendee = control.fetchone()
            if not existing_attendee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendee does not exist")
            
            # Check if session exists and is active
            control.execute("SELECT StartTime, EndTime FROM Sessions WHERE SessionID = %s;", (session_id,))
            existing_session = control.fetchone()
            if not existing_session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session does not exist")
            
            start_time, end_time = existing_session
            start_time = start_time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
            end_time = end_time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
            current_time = datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
            if current_time < start_time or current_time > end_time:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session not active")
            
            # Check if the attendee is within session location
            control.execute("SELECT Longitude, Latitude FROM SessionLocations WHERE SessionID = %s;", (session_id,))
            session_location = control.fetchone()
            if not session_location:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session location not found")

            session_longitude, session_latitude = session_location
            if abs(Decimal(latitude) - Decimal(session_latitude)) > Decimal('0.001') or abs(Decimal(longitude) - Decimal(session_longitude)) > Decimal('0.001'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in the session location")

            # Record attendance in 'Attended_By' and location in 'AttendeesLocations'
            control.execute(
                "INSERT INTO Attended_By (UniqueID, SessionID) VALUES (%s, %s);", 
                (attendee_details["id"], session_id)
            )
            control.execute(
                "INSERT INTO AttendeesLocations (LocationTimestamp, Longitude, Latitude, UniqueID) VALUES (%s, %s, %s, %s);", 
                (datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30))), longitude, latitude, attendee_details["id"])
            )
            connection.commit()
    
    return {"result": "Session joined successfully"}
    
class curr_loc(BaseModel):
    tok: str = Field(..., description="JWT token from the client") 
    longitude: float = Field(..., description="Longitude of the current location", ge=-180, le=180)
    latitude: float = Field(..., description="Latitude of the current location", ge=-90, le=90)

@app.post("/current-location")
def store_current_location(position: curr_loc):
    attendee_details=decode_jwt_token(position.tok)

    if attendee_details["role"]=="admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an attendee")
    
    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.execute("select 1 from Attendees where UniqueID=%s;", (attendee_details["id"],))
            existing_attendee = control.fetchone()
            if not existing_attendee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendee does not exist")
            
            control.execute("insert into AttendeesLocations (UniqueID, Latitude, Longitude, LocationTimestamp) values (%s, %s, %s, %s);", (attendee_details["id"], position.latitude, position.longitude, datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))))
            connection.commit()
    
    return {"Status":"Location recieved"}
        
class identify(BaseModel):
    tok:  str = Field(..., description="JWT token from the client") 

@app.post("/active-sessions")
def return_active_sessions(details: identify):
    identity=decode_jwt_token(details.tok)
    if identity["role"]=="admin" or identity["role"]=="attendee":
        rn=datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
        ret = []
        with get_connection() as connection:
            with get_cursor(connection) as control:
                r=[]
                if identity["role"]=="attendee":
                    control.execute("select SessionID from Attended_By where UniqueID=%s",(identity["id"],))
                    r=control.fetchall()
                    r=[x[0] for x in r]
                control.execute("select * from Sessions where EndTime > %s and StartTime <= %s order by StartTime desc;",(rn,rn))
                for x in control:
                    if x[0] not in r:
                        ret.append(x)
                for i in range(len(ret)):
                    control.execute("select Latitude, Longitude from SessionLocations where SessionID=%s",(ret[i][0],))
                    for x in control:
                        ret[i]=ret[i]+x
        if not ret:
            return{"sessions":[]}
        return {"sessions":ret}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")

class admin_check(BaseModel):
    tok:  str = Field(..., description="JWT token from the client")
    id: int = Field(..., description="UniqueID of the student")

@app.post("/get-attendance")
def return_student_attendance(details: admin_check):
    admin_details=decode_jwt_token(details.tok)
    student_id=details.id
    if admin_details["role"]!="admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")
    adid=admin_details["id"]
    time_now=datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))

    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.callproc('GetSessionDetails', (adid, time_now, student_id))
            t1={}
            for result in control.stored_results():
                t1=result.fetchall()

            control.execute("select * from AttendeesLocations where UniqueID=%s",(student_id,))

            t2=control.fetchall()

            satt = {}
            temp = {}
            for i in t2:
                temp = {}
                for j in t1:
                    if i[0]>=j[0] and i[0]<=j[1]:
                        if abs(i[1]-j[3])<0.0001 and abs(i[2]-j[4])<0.0001: #About 10 metres
                            temp[j[2]]=1
                        else:
                            if i[2] not in temp:
                                temp[j[2]]=0

                for k in temp:
                    if k not in satt:
                        satt[k]=[0,0]
                    satt[k][0]+=temp[k]
                    satt[k][1]+=1

            for k in satt:
                satt[k]=(satt[k][0]/satt[k][1])>=0.8

            return satt
        
    return {"result":"Error in fetching attendance"}
    
@app.post("/check-attendance")
def check_your_attendance(details: identify):
    identity=decode_jwt_token(details.tok)
    student_id=identity["id"]
    if identity["role"]!="attendee":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")
    time_now=datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))

    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.callproc('GetSessionDetailsForStudent', (time_now,student_id))
            for result in control.stored_results():
                t1=result.fetchall()

            control.execute("select * from AttendeesLocations where UniqueID=%s",(student_id,))

            t2=control.fetchall()

            satt = {}
            temp = {}
            for i in t2:
                temp = {}
                for j in t1:
                    if i[0]>=j[0] and i[0]<=j[1]:
                        if abs(i[1]-j[3])<0.0001 and abs(i[2]-j[4])<0.0001: #About 10 metres
                            temp[j[2]]=1
                        else:
                            if i[2] not in temp:
                                temp[j[2]]=0

                for k in temp:
                    if k not in satt:
                        satt[k]=[0,0]
                    satt[k][0]+=temp[k]
                    satt[k][1]+=1

            for k in satt:
                satt[k]=(satt[k][0]/satt[k][1])>=0.8

            return satt
    return {"result":"Error in fetching attendance"}

@app.post("/get-sessions-created")
def get_sessions_created(details: identify):
    identity = decode_jwt_token(details.tok)
    if identity["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")
    adid = identity["id"]
    try:
        with get_connection() as connection:
            with get_cursor(connection) as control:
                control.execute("select SessionID, StartTime, EndTime from Sessions where AdminID=%s order by StartTime desc;", (adid,))
                result = control.fetchall()
                return result
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in fetching sessions created")
    
    
@app.post("/my-sessions")
def get_joined_sessions(details: identify):
    identity = decode_jwt_token(details.tok)
    if identity["role"] != "attendee":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")
    adid = identity["id"]
    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.execute("select Sessions.SessionID, Sessions.StartTime, Sessions.EndTime, Sessions.AdminID from Attended_By, Sessions where Attended_By.UniqueID=%s and Sessions.SessionID=Attended_By.SessionID",(adid,))
            ret=[]
            for x in control:
                ret.append(x)
            return {"sessions":ret}
    return {"sessions":[]}

class session_details(BaseModel):
    tok: str = Field(..., description="JWT token from the client")
    sessionid: int = Field(..., description="ID of the session")

@app.post("/get-session-attendees")
def get_session_attendees(details: session_details):
    tok = details.tok
    sessionid = details.sessionid
    identity = decode_jwt_token(tok)
    if identity["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")
    
    starttime = None
    endtime = None
    address = None
    latitude = None
    longitude = None
    attendees = []
    
    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.execute("select StartTime, EndTime, AdminID from Sessions where SessionID=%s and AdminID=%s;", (sessionid, identity["id"]))
            match = control.fetchone()

            if not match:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
            
            starttime = match[0]
            endtime = match[1]

            control.execute("select Address, Longitude, Latitude from SessionLocations where SessionID=%s;", (sessionid,))

            data = control.fetchall()
            address = data[0][0]
            longitude = data[0][1]
            latitude = data[0][2]

            control.execute("select a.Email, a.Fname, a.Lname from Attendees a, Attended_By ab where ab.UniqueID=a.UniqueID and ab.SessionID=%s;", (sessionid,))

            for x in control:
                attendees.append({"email": x[0], "fname": x[1], "lname": x[2]})

    if starttime == None or endtime == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if address == None or latitude == None or longitude == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session location not found")
    
    return {"starttime": starttime, "endtime": endtime, "address": address, "longitude": longitude, "latitude": latitude, "attendees": attendees}

@app.post("/get-attended-sessions")
def get_attended_sessions(details: identify):
    identity = decode_jwt_token(details.tok)
    if identity["role"] != "attendee":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")
    adid = identity["id"]
    with get_connection() as connection:
        with get_cursor(connection) as control:
            control.execute("select Sessions.SessionID, Sessions.StartTime, Sessions.EndTime, Sessions.AdminID, SessionLocations.Latitude, SessionLocations.Longitude from Attended_By, Sessions, SessionLocations where Attended_By.UniqueID=%s and Sessions.SessionID=Attended_By.SessionID and Sessions.SessionID=SessionLocations.SessionID order by Sessions.StartTime desc;",(adid,))
            ret=[]
            for x in control:
                ret.append(x)
            return {"sessions":ret}
    return {"sessions":[]}