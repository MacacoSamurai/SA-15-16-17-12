from flask import Flask

app = Flask(__name__)

from func import *

if __name__ == '__main__': 
    app.run(debug=True)