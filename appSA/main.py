from flask import Flask
import mysql.connector

app = Flask(__name__)
    
app.secret_key = "diego_of_war"

CONFIG_DB = {
    'host': 'localhost',
    'port': '3306',
    'user': 'root',
    'password': '',
    'database': 'mecanica' # Ajustado para 'mecanica' conforme seu databaseSA.sql
}

from func import *
if __name__ == '__main__': 
    app.run(debug=True)

