from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json 
from datetime import datetime
import randomforestedzesfeladat 
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Dwasd23GHRffb'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    saved_workouts = db.relationship('SavedWorkout', backref='user', lazy=True)

class SavedWorkout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.now) # Mikor mentette
    name = db.Column(db.String(100))
    # A teljes edzéstervet JSON szövegként
    workout_data = db.Column(db.Text, nullable=False) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dolgozoink')
def dolgozoink():
    return render_template('dolgozoink.html')

# rpofile
@app.route('/profile')
@login_required
def profile():
    workouts = SavedWorkout.query.filter_by(user_id=current_user.id).order_by(SavedWorkout.date.desc()).all()
    
    #JSON pytjonn
    parsed_workouts = []
    for w in workouts:
        parsed_workouts.append({
            'id': w.id,
            'date': w.date.strftime('%Y-%m-%d %H:%M'),
            'name': w.name,
            'data': json.loads(w.workout_data)
        })
        
    return render_template('profile.html', workouts=parsed_workouts)

@app.route('/save_workout', methods=['POST'])
@login_required
def save_workout():

    terv_json = request.form.get('terv_json')
    edzes_neve = request.form.get('edzes_neve')
    
    if terv_json:
        new_save = SavedWorkout(
            name=edzes_neve if edzes_neve else "Névtelen edzés",
            workout_data=terv_json,
            user_id=current_user.id
        )
        db.session.add(new_save)
        db.session.commit()
        flash('Edzés sikeresen elmentve a profilodba', 'success')
        return redirect(url_for('profile'))
    
    return redirect(url_for('dashboard'))

@app.route('/delete_workout/<int:id>')
@login_required
def delete_workout(id):
    workout = SavedWorkout.query.get_or_404(id)
    if workout.user_id == current_user.id:
        db.session.delete(workout)
        db.session.commit()
        flash('Törölve', 'info')
    return redirect(url_for('profile'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Ez a név már foglalt', 'danger')
        else:
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            flash('Sikeres regisztráció', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.permanent = False
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Hibás adatok', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('step1.html')

@app.route('/dashboard/step2', methods=['POST'])
@login_required
def dashboard_step2():
    nehezseg = request.form.get('nehezseg')
    cel = request.form.get('cel')
    stilusok = []
    if cel == '1': stilusok = [('1', 'Ballisztikus'), ('2', 'Plyometric'), ('3', 'Animal Flow'), ('4', 'Saját testsúlyos')]
    elif cel == '2': stilusok = [('1', 'Bodybuilding'), ('2', 'Powerlifting'), ('3', 'Olimpiai Súlyemelés'), ('4', 'Grind (Erőemelő)')]
    elif cel == '3': stilusok = [('1', 'Saját testsúlyos'), ('2', 'Animal Flow'), ('3', 'Balance')]
    elif cel == '4': stilusok = [('4', 'Korrekciós gyakorlatok')]
    return render_template('step2.html', nehezseg=nehezseg, cel=cel, stilusok=stilusok)

@app.route('/dashboard/result', methods=['POST'])
@login_required
def dashboard_result():
    nehezseg = request.form.get('nehezseg')
    cel = request.form.get('cel')
    izom = request.form.get('izom')
    stilus = request.form.get('stilus')

    nehezseg_map = {'1': 'Novice', '2': 'Intermediate', '3': 'Advanced'}
    izom_map = {'1': 'Core', '2': 'Lower Body', '3': 'Upper Body', '4': 'Full Body'}
    stilus_kulcsszo = ""

    if cel == '1': 
        d = {'1': 'Ballistic', '2': 'Plyometric', '3': 'Animal', '4': 'Bodyweight'}
        stilus_kulcsszo = d.get(stilus, "")
    elif cel == '2':
        d = {'1': 'Bodybuilding', '2': 'Powerlifting', '3': 'Olympic', '4': 'Grind'}
        stilus_kulcsszo = d.get(stilus, "")
    elif cel == '3':
        d = {'1': 'Bodyweight', '2': 'Animal', '3': 'Balance'}
        stilus_kulcsszo = d.get(stilus, "")
    elif cel == '4': stilus_kulcsszo = "Correction"

    nehezseg_szoveg = nehezseg_map.get(nehezseg, 'Novice')
    izom_szoveg = izom_map.get(izom, 'Full Body')
    
    terv = []
    df = randomforestedzesfeladat.load_database()
    if df is not None:
        eredmeny_df = randomforestedzesfeladat.general_terv_quota(df, nehezseg_szoveg, izom_szoveg, stilus_kulcsszo)
        if not eredmeny_df.empty:
            #jsonná
            terv = eredmeny_df.to_dict('records')
            terv_json = json.dumps(terv)
        else:
            terv_json = ""
            flash("Nem találtam gyakorlatot.", "warning")
            
    return render_template('result.html', terv=terv, terv_json=terv_json)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)