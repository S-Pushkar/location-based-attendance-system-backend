from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv
import mysql.connector
import bcrypt
import os

app = FastAPI()

load_dotenv('.env.local')

SQL_HOST = os.getenv("SQL_HOST")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DB = os.getenv("SQL_DB")

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

def hash_password(password: str):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

class Admin(BaseModel):
    email: EmailStr = Field(..., description="Email of the admin")
    fname: str = Field(..., description="First name of the admin")
    lname: str = Field(..., description="Last name of the admin")
    password: str = Field(..., description="Unhashed Password of the admin")

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
    
    control.execute("insert into Admins (Email, FirstName, LastName, Passwd) values (%s, %s, %s, %s);", (email, fname, lname, hashed_passwd))
    mydb.commit()

    return {"Admin": "Registered"}