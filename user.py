from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

import randomforestedzesfeladat 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MIÉÉÉÉÉÉÉRTISTENEM'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Ez a felhasználónév már foglalt.', 'error')
        else:
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Sikeres regisztráció! Most már beléphetsz.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Hibás felhasználónév vagy jelszó.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    terv = None
    if request.method == 'POST':
        nehezseg = request.form.get('nehezseg')
        cel = request.form.get('cel')
        stilus = request.form.get('stilus')
        izom = request.form.get('izom')
        df = randomforestedzesfeladat.load_database()
        
        if df is not None:
            eredmeny_df = randomforestedzesfeladat.general_terv_quota(df, nehezseg, izom, stilus)
            
            if not eredmeny_df.empty:
                terv = eredmeny_df.to_dict('records')
    
    return render_template('dashboard.html', user=current_user, terv=terv)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)