from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Event, Registration
from forms import RegistrationForm, LoginForm, EventForm
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volunteer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создание таблиц и администратора (при первом запуске)
with app.app_context():
    db.create_all()
    # Создать администратора, если нет пользователей
    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Создан администратор: admin@example.com / admin123')

# ---------- Маршруты ----------
@app.route('/')
def index():
    upcoming_events = Event.query.filter(Event.date >= datetime.now()).order_by(Event.date).limit(5).all()
    return render_template('index.html', events=upcoming_events)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_pw
        )
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Вы успешно вошли!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверный email или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/events')
def events():
    # Все мероприятия, будущие и прошедшие
    all_events = Event.query.order_by(Event.date.desc()).all()
    return render_template('events.html', events=all_events)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    is_registered = False
    if current_user.is_authenticated:
        is_registered = Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first() is not None
    return render_template('event_detail.html', event=event, is_registered=is_registered)

@app.route('/event/<int:event_id>/register', methods=['POST'])
@login_required
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.spots_left <= 0:
        flash('Нет свободных мест на это мероприятие.', 'danger')
        return redirect(url_for('event_detail', event_id=event.id))
    existing = Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first()
    if existing:
        flash('Вы уже записаны на это мероприятие.', 'warning')
    else:
        reg = Registration(user_id=current_user.id, event_id=event.id)
        db.session.add(reg)
        db.session.commit()
        flash('Вы успешно записались на мероприятие!', 'success')
    return redirect(url_for('event_detail', event_id=event.id))

@app.route('/event/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(event_id):
    reg = Registration.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash('Вы отменили запись на мероприятие.', 'info')
    else:
        flash('Вы не были записаны на это мероприятие.', 'warning')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/profile')
@login_required
def profile():
    # Мероприятия, на которые записан пользователь
    registrations = Registration.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', registrations=registrations)

# ---------- Административные маршруты ----------
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/admin')
@admin_required
def admin_dashboard():
    events = Event.query.all()
    users = User.query.all()
    registrations = Registration.query.all()
    return render_template('admin_dashboard.html', events=events, users=users, registrations=registrations)

@app.route('/admin/event/create', methods=['GET', 'POST'])
@admin_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            date=form.date.data,
            max_volunteers=form.max_volunteers.data,
            created_by=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Мероприятие создано!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_event.html', form=form)

@app.route('/admin/event/<int:event_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.location = form.location.data
        event.date = form.date.data
        event.max_volunteers = form.max_volunteers.data
        db.session.commit()
        flash('Мероприятие обновлено!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_event.html', form=form, event=event)

@app.route('/admin/event/<int:event_id>/delete', methods=['POST'])
@admin_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Мероприятие удалено.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/registration/<int:reg_id>/mark_attended', methods=['POST'])
@admin_required
def mark_attended(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    reg.attended = True
    db.session.commit()
    flash('Участие отмечено как подтверждённое.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    def utility_processor():
        return {'now': datetime.now()}
    app.run(debug=True)