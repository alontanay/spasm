import string
import re

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

from spasm.web.models import User
from spasm.common.queries import conditions_from_user_text

class AllowedCharacters:
    def __init__(self, legal_characters, message=None):
        self.legal_characters = ''.join(legal_characters)
        if not message:
            message = f'Field must only contain characters from "{self.legal_characters}".'
        self.message = message
    
    def __call__(self, form, field):
        for char in field.data:
            if not char in self.legal_characters:
                raise ValidationError(self.message)

class OrValidator:
    def __init__(self, *validators, message=None):
        self.validators = validators
        self.message = message
    
    def __call__(self, form, field):
        success = False
        messages = []
        for validator in self.validators:
            try:
                validator(form,field)
            except ValidationError as error:
                messages.append(error.args[0])
            else:
                success = True
        if not success:
            if self.message:
                raise ValidationError(self.message)
            raise ValidationError(message='No match for field. failed matches reasons:\n - ' + '\n - '.join(messages))

ALLOWED_USERNAME_CHARACTERS = string.ascii_letters + string.digits + '_-'
username_validator = AllowedCharacters(ALLOWED_USERNAME_CHARACTERS, 'Username can only contain english letters, digits, underscores and dashes.')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20), username_validator])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(),EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        other = User.query.filter_by(username=username.data).first()
        if other:
            raise ValidationError(f'Username "{username.data}" is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        other = User.query.filter_by(email=email.data).first()
        if other:
            raise ValidationError(f'This email is already tied to an existing account. Please use a different one.')


class LoginForm(FlaskForm):
    username_or_email = StringField('Username', validators=[DataRequired(), Length(max=120), OrValidator(Email(),username_validator,message='Not a valid username or email address.')])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class QueryValidator:
    def __call__(self, form, field: TextAreaField):
        if field.data is None:
            return
        conditions_from_user_text(field.data)

class AnalysisQueryForm(FlaskForm):
    conditions = TextAreaField('Study Group Bounds', validators=[QueryValidator()])
    submit = SubmitField('Perform Query')