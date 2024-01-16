from . import db
from flask_login import UserMixin

# Associations

enrollment = db.Table(
    'enrollment',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True)
)

quiz_attempts = db.Table(
    'quiz_attempts',
    db.Column('quiz_template_id', db.Integer, db.ForeignKey('quizzes.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('overall_score', db.Float)
)


# Tables
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250))
    firstName = db.Column(db.String(250))
    role = db.Column(db.String(10))

    user_answers = db.relationship('UserAnswer', backref='answered_by_user')
    enrolled_courses = db.relationship('Course', secondary='enrollment', backref='enrolled_students')


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    quiz_name = db.Column(db.String(250), unique=True)
    total_questions = db.Column(db.Integer)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    time_limit = db.Column(db.Integer)
    availability_date = db.Column(db.DateTime)

    questions = db.relationship('Question', backref='quiz_ref', lazy=True)
    attempts = db.relationship('User', secondary=quiz_attempts, backref='quiz_attempts')
    course = db.relationship('Course', backref='quizzes')

    def add_attempt(self, student_id, overall_score):
        self.user_attempts.append(User.query.get(student_id))
        db.session.commit()


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500))
    option_a = db.Column(db.String(250))
    option_b = db.Column(db.String(250))
    option_c = db.Column(db.String(250))
    option_d = db.Column(db.String(250))
    correct_option = db.Column(db.String(10))

    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)

    quiz = db.relationship('Quiz', backref='related_questions')
    user_answers = db.relationship('UserAnswer', backref='question_ref')


class UserAnswer(db.Model):
    __tablename__ = 'user_answers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option = db.Column(db.String(10))
    score = db.Column(db.Float)

    user = db.relationship('User', backref='answers')
    quiz = db.relationship('Quiz', backref='answers')
    question = db.relationship('Question', backref='answers')


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(30), unique=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    applications = db.relationship('StudentApplication', backref='course', lazy='dynamic')


class StudentApplication(db.Model):
    __tablename__ = 'student_applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
