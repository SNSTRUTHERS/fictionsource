"""Site forms."""

import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import Email, EqualTo, InputRequired, Length
from wtforms.fields.html5 import DateField, EmailField

from models import User

class RegisterForm(FlaskForm):
    """Form for registering a new fictionsource account."""

    username = StringField("Username",
        validators = [Length(max=User.USERNAME_LENGTH), InputRequired()],
        render_kw = { "placeholder": f"Maximum of {User.USERNAME_LENGTH} characters" }
    )
    
    password = PasswordField("Password",
        validators = [InputRequired(), Length(min=6)]
    )
    confirm_password = PasswordField("Confirm Password",
        validators = [InputRequired(), EqualTo("password")],
        render_kw = { "placeholder": "Retype Password" }
    )

    email = EmailField("Email",
        validators = [InputRequired(), Email(check_deliverability=True)],
        render_kw = { "placeholder": "example@example.com" }
    )

    birthday = DateField("Birth Date (must be 13 or older to use this site)",
        validators = [InputRequired()],
        render_kw = { "min": datetime.date(1900, 1, 1) }
    )

class LogInForm(FlaskForm):
    """Form for logging in to an existing fictionsource account."""

    username = StringField("Username",
        validators = [Length(max=User.USERNAME_LENGTH), InputRequired()]
    )

    password = PasswordField("Password",
        validators = [InputRequired()]
    )

class ImageForm(FlaskForm):
    """Form for image upload."""
