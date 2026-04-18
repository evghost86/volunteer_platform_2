from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange
from datetime import datetime


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class EventForm(FlaskForm):
    title = StringField('Название мероприятия', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    location = StringField('Место проведения', validators=[DataRequired(), Length(max=200)])
    date = DateTimeField('Дата и время (ГГГГ-ММ-ДД ЧЧ:ММ)', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    max_volunteers = IntegerField('Максимум волонтёров', validators=[DataRequired(), NumberRange(min=1, max=1000)])
    submit = SubmitField('Создать мероприятие')

    def validate_date(self, field):
        if field.data < datetime.now():
            raise ValidationError('Дата мероприятия не может быть в прошлом')