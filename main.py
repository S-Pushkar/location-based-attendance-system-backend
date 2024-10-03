from fastapi import FastAPI
from dotenv import load_dotenv
import mysql.connector
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