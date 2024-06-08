from flask import render_template, url_for, flash, redirect, request

from spasm.web import app, web_backend, db, bcrypt, data_servers
from spasm.web.forms import RegistrationForm, LoginForm, AnalysisQueryForm
from spasm.web.models import User
from flask_login import login_user, logout_user, current_user, login_required

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!','success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.username_or_email.data).first() or User.query.filter_by(username=form.username_or_email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('You are now logged in!', 'success')
            next_page = request.args.get('next')
            print('logged in')
            return redirect(next_page if next_page else url_for('home'))
        flash('Failed Login. No registered account matches data. Check username / email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/account')
@login_required
def personal_account(): 
    return render_template('account.html', title='Account')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html', title='For Analysts')

@app.route('/organization')
def organization(): 
    return render_template('organization.html', title='Account', data_servers=data_servers)

@app.route('/demo', methods=['GET','POST'])
@login_required
def demo():
    form = AnalysisQueryForm()
    if form.validate_on_submit():
        try:
            if not web_backend.is_initialized():
                raise Exception('Backend client not set up.')
            data = web_backend.data_request(form.conditions.data)
        except Exception as e:
            flash('Query Failed. Error Message: ' + str(e), 'danger')
            return render_template('demo.html', title="Demo - Failed", form=form, query_success=False)
        if not data:
            flash('Query Failed. Not enough records satisfy the provided conditions.', 'danger')
            return render_template('demo.html', title="Demo - Failed", form=form, query_success=False)
        return render_template('demo.html', title='Demo - Results', form=form, query_success=True, data=data, data_servers=data_servers)
    return render_template('demo.html',title='Demo', form=form)

@app.errorhandler(404)
def default(error):
    return 'lost?'
