from flask import Flask
import mysql.connector

app = Flask(__name__)
    
CONFIG_DB = {
    'host': 'localhost',
    'port': '3406',
    'user': 'root',
    'password': '',
    'database': 'mecanica' # Ajustado para 'mecanica' conforme seu databaseSA.sql
}

from func import *
if __name__ == '__main__': 
    app.run(debug=True)

