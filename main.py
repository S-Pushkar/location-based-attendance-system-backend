from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel, EmailStr, Field, confloat, constr, validator
from dotenv import load_dotenv
import mysql.connector
import bcrypt
import os
from jose import jwt
from datetime import datetime, timedelta, timezone
import base64
from typing import Tuple, Optional
from datetime import datetime
import re

app = FastAPI()

load_dotenv('.env.local')

SQL_HOST = os.getenv("SQL_HOST")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DB = os.getenv("SQL_DB")
JWT_SECRET = os.getenv("JWT_SECRET")
ALGORITHM = 'HS256'

mydb = mysql.connector.connect(
    host=SQL_HOST,
    user=SQL_USER,
    password=SQL_PASSWORD,
    database=SQL_DB
)

control = mydb.cursor()

@app.get("/hello")
def hello():
    return {"Hello": "World"}

@app.get("/robots.txt")
def robots_begone():
    return {"User-agent":"*","Disallow":"/"}

def hash_password(password: str):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return (hashed_password.decode('utf-8'),base64.b64encode(salt).decode('utf-8'))
    
def rehash(password: str, salt64: str):
    salt=base64.b64decode(salt64.encode('utf-8'))
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def create_jwt_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(days=14)})
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
    email = admin.email.lower()     # Lowercase the email to avoid maintain consistency
    fname = admin.fname
    lname = admin.lname
    password = admin.password

    control.execute("select 1 from Admins where Email = %s;", (email,))
    existing_admins = control.fetchone()

    if existing_admins:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin already exists")
    
    hashed_passwd = hash_password(password)
    
    control.execute("insert into Admins (Email, FirstName, LastName, Passwd, Salt) values (%s, %s, %s, %s, %s);", (email, fname, lname, hashed_passwd[0], hashed_passwd[1]))
    mydb.commit()
    
    control.execute("select AdminID from Admins where Email = %s;", (email,))
    existing_admins = control.fetchone()

    access_token = create_jwt_token({"id":existing_admins[0],"email": email, "role": "admin", "fname": fname, "lname": lname})
    return {"access_token": access_token}

class Attendee(BaseModel):
    email: EmailStr = Field(..., description="Email of the attendee")
    fname: str = Field(..., description="First name of the attendee")
    lname: str = Field(..., description="Last name of the attendee")
    password: str = Field(..., description="Unhashed Password of the attendee")
    address: str = Field(..., description="Address of the attendee")

@app.post("/auth/register-attendee")
def register_attendee(attendee: Attendee):
    email = attendee.email.lower()
    fname = attendee.fname
    lname = attendee.lname
    password = attendee.password
    address = attendee.address

    control.execute("select 1 from Attendees where Email = %s;", (email,))
    existing_attendees = control.fetchone()
    if existing_attendees:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendee already exists")
    
    hashed_passwd = hash_password(password)

    control.execute("insert into Attendees (Email, FName, LName, Passwd, Salt, Address) values (%s, %s, %s, %s, %s, %s);", (email, fname, lname, hashed_passwd[0], hashed_passwd[1], address))
    mydb.commit()
    
    control.execute("select UniqueID from Attendees where Email = %s;", (email,))
    existing_attendees = control.fetchone()

    access_token = create_jwt_token({"id":existing_attendees[0],"email": email, "role": "attendee", "fname": fname, "lname": lname})
    return {"access_token": access_token}
    
class login(BaseModel):
    email: EmailStr = Field(..., description="Email of the admin or atttendee")
    password: str = Field(..., description="Unhashed Password of the admin or attendee")
    
@app.post("/auth/login")
def login(details: login):
    #Assuming admins and attendees are mutually exclusive
    email=details.email.lower()
    password=details.password
    
    control.execute("select AdminID, FirstName, LastName, Passwd, Salt from Admins where Email=%s;", (email,))
    
    for match in control:
        if rehash(password,match[4])==match[3]:
            access_token=create_jwt_token({"id":match[0],"email":email, "role":"admin","fname":match[1],"lname":match[2]})
            return {"access_token":access_token}

    control.execute("select UniqueID, Fname, Lname, Passwd, Salt from Attendees where Email=%s and Passwd=%s;", (email,password))
    
    for match in control:
        if rehash(password,match[4])==match[3]:
            access_token=create_jwt_token({"id":match[0],"email":email, "role":"attendee","fname":match[1],"lname":match[2]})
            return {"access_token":access_token}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Please first sign up")

class session_locs(BaseModel):
    address: constr(min_length=0, max_length=100) = Field(..., description="An address of a session")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Longitude of a session location")
    latitude: confloat(ge=-90, le=90) = Field(..., description="Latitude of a session location")
    
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
def create_sesion(details: create_session_info):
    admin_details=decode_jwt_token(details.tok)
    start_time=datetime.strptime(details.start_time, '%Y-%m-%d %H:%M:%S')
    end_time=datetime.strptime(details.end_time, '%Y-%m-%d %H:%M:%S')
    locations=details.locs
    
    if admin_details["role"]!="admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an admin")
    
    if start_time>=end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ensure the session start and end times are corect")
    
    control.execute("insert into Sessions (StartTime, EndTime, AdminID) values (%s, %s, %s);", (start_time, end_time, admin_details["id"]))
    session_id=control.lastrowid
    mydb.commit()
    
    for x in locations:
        control.execute("insert into SessionLocations (Address, Longitude, Latitude, SessionID) values (%s, %s, %s, %s);", (x.address, x.longitude, x.latitude, session_id))
        mydb.commit()

    return {"result": "Session successfully created"}

@app.post("/add-locations")
def add_session_locations(details: add_locs):
    admin_details=decode_jwt_token(details.tok)
    session_id=details.sessionid
    locations=details.locs
    
    if admin_details["role"]!="admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an admin")
        
    control.execute("select AdminID from Sessions where SessionID=%s;", (session_id,))
    match = control.fetchone()
    if match[0]!=admin_details["id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the session manager")
    
    for x in locations:
        control.execute("insert into SessionLocations (Address, Longitude, Latitude, SessionID) values (%s, %s, %s, %s);", (x.address, x.longitude, x.latitude, session_id))
        mydb.commit()
    
    return {"result":"Session locations updated"}
    
class join_sess(BaseModel):
    tok: str = Field(..., description="JWT token from the client")
    sessionid: int = Field(..., description="ID of the session the attendee is joining")

@app.post("/join-session")
def join_session(details: join_sess):
    attendee_details=decode_jwt_token(details.tok)
    session_id=details.sessionid
    
    if attendee_details["role"]=="admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not an attendee")
    
    control.execute("insert into Attended_By (UniqueID, SessionID) values (%s, %s);", (attendee_details["id"], session_id))
    mydb.commit()
    
    return {"result":"Session joined successfully"}
    
class curr_loc(BaseModel):
    tok: str = Field(..., description="JWT token from the client") 
    longitude: confloat(ge=-180, le=180) = Field(..., description="Longitude of a current attnedee location")
    latitude: confloat(ge=-90, le=90) = Field(..., description="Latitude of a current attendee location")

@app.post("/current-location")
def store_current_location(position: curr_loc):
    attendee_details=decode_jwt_token(position.tok)
    ct=datetime.now()
    control.execute("insert into AttendeesLocations (UniqueID, Latitude, Longitude, LocationTimestamp) values (%s, %s, %s, %s);", (attendee_details["id"],position.latitude,position.longitude,ct))
    mydb.commit()
        
class identify(BaseModel):
    tok:  str = Field(..., description="JWT token from the client") 

@app.post("/active-sessions")
def return_active_sessions(details: identify):
    identity=decode_jwt_token(details.tok)
    if identity["role"]=="admin" or identity["role"]=="attendee":
        rn=datetime.now()
        control.execute("select * from sessions where EndTime > %s",(rn,))
        ret=[]
        for x in control:
            ret.append(x)
            
        if not ret:
            return{"sessions":"None Active"}
        return {"sessions":ret}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not the authorized")

class admin_check(BaseModel):
    tok:  str = Field(..., description="JWT token from the client")
    id: int = Filed(..., description="UniqueID of the student")

