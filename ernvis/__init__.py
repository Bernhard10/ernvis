from flask import Flask

app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'
app.config['SECRET_KEY'] = 'yxcasdfw9034rmc02393409rmoir3u4rj09a-rp3f09ufgj349tj0pqa2'


from . import views
