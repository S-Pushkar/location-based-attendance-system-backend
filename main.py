from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv
import mysql.connector
import bcrypt
import os
from jose import jwt
from datetime import datetime, timedelta, timezone
import base64

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
    print(salt)
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
    print(len(hashed_passwd[1]))
    control.execute("insert into Admins (Email, FirstName, LastName, Passwd, Salt) values (%s, %s, %s, %s, %s);", (email, fname, lname, hashed_passwd[0], hashed_passwd[1]))
    mydb.commit()

    access_token = create_jwt_token({"email": email, "role": "admin", "fname": fname, "lname": lname})
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

    access_token = create_jwt_token({"email": email, "role": "attendee", "fname": fname, "lname": lname})
    return {"access_token": access_token}
    
class login(BaseModel):
    email: EmailStr = Field(..., description="Email of the admin or atttendee")
    password: str = Field(..., description="Unhashed Password of the admin or attendee")
    
@app.post("/")
def login(details: login):
    email=details.email.lower()
    password=details.password
    control.execute("select AdminID, FirstName, LastName, Passwd, Salt from Admins where Email=%s;", (email,))
    for match in control:
        if rehash(password,match[4])==match[3]:
            access_token=create_jwt_token({"email":email, "role":"admin","fname":match[1],"lname":match[2]})
            return {"access_token":access_token}
    control.execute("select UniqueID, Fname, Lname, Passwd, Salt from Attendees where Email=%s and Passwd=%s;", (email,password))
    for match in control:
        if rehash(password,match[4])==match[3]:
            access_token=create_jwt_token({"email":email, "role":"attendee","fname":match[1],"lname":match[2]})
            return {"access_token":access_token}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Please first sign up")