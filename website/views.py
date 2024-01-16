from flask import Blueprint, render_template, request, flash, redirect, url_for, session, abort
from flask_login import login_required, current_user
from dotenv import load_dotenv
import os
from sqlalchemy import and_, not_
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from sqlalchemy.orm import joinedload

from website import db
from website.models import Quiz, Question, UserAnswer, Course, User, quiz_attempts, StudentApplication

views = Blueprint('views', __name__)
load_dotenv()

SITE_KEY = os.getenv('SITE_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
VERIFY_URL = os.getenv('VERIFY_URL')


@views.route('/', methods=['GET', 'POST'])
def home():
    return render_template("home.html", user=current_user, site_key=SITE_KEY)


# TEACHER FUNCTIONS

@views.route('/teacher_courses', methods=['GET', 'POST'])
@login_required
def teacher_courses():
    if current_user.role != 'teacher':
        flash("Access Denied: Only teachers can view courses.", 'error')
        return redirect(url_for('views.home'))

    teacher_courses = Course.query.filter_by(teacher_id=current_user.id).all()

    # This is for getting student applications for the teachers courses
    pending_applications = (
        db.session.query(StudentApplication, User.firstName.label('student_name'), Course.course_name)
        .join(User, StudentApplication.student_id == User.id)
        .join(Course, StudentApplication.course_id == Course.id)
        .filter(Course.teacher_id == current_user.id, StudentApplication.status == 'pending')
        .all()
    )
    print("Teacher Courses:", teacher_courses)
    print(pending_applications)

    return render_template('teacher_courses.html', user=current_user, courses=teacher_courses,
                           pending_applications=pending_applications)


@views.route('/process_enrollment/<int:application_id>/<action>', methods=['POST', 'GET'])
@login_required
def process_enrollment(application_id, action):
    if current_user.role != 'teacher':
        flash("Access Denied: Only teachers can process enrollments.", 'error')
        return redirect(url_for('views.home'))

    application = (
        db.session.query(StudentApplication, User.firstName.label('student_name'), Course.course_name)
        .join(User, StudentApplication.student_id == User.id)
        .join(Course, StudentApplication.course_id == Course.id)
        .filter(StudentApplication.id == application_id)
        .first()
    )
    if application is None:
        flash("Application not found.", "error")
        return redirect(url_for('views.teacher_courses'))

    student_name = application.student_name

    if action == 'approve':
        application.StudentApplication.status = 'accepted'

        course = Course.query.get(application.StudentApplication.course_id)
        student = User.query.get(application.StudentApplication.student_id)
        student.enrolled_courses.append(course)

        flash(f"You have approved {student_name}'s enrollment in {application.course_name}.", "success")
    elif action == 'decline':
        application.StudentApplication.status = 'declined'

        flash(f"You have declined {student_name}'s enrollment in {application.course_name}.", "success")
    else:
        flash("Invalid action.", "error")

    db.session.commit()

    return redirect(url_for('views.teacher_courses'))


@views.route('/create_quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if current_user.role != 'teacher':
        flash("Access Denied: Only teachers can add quizzes.", 'error')
        return redirect(url_for('views.home'))

    # Get all the courses for the logged in teacher
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

    if request.method == 'POST':
        quiz_name = request.form['quiz_name']
        total_questions = int(request.form['total_questions'])
        course_id = request.form['course_id']
        time_limit = request.form.get('time_limit')
        availability_date = request.form.get('availability_date')

        if not (time_limit and availability_date):
            flash("Please enter both time limit and availability date before continuing.", 'error')
            return render_template('create_quiz.html', user=current_user, courses=courses), 400

        # This part is for checking if a quiz with the same name exists.
        existing_quiz = Quiz.query.filter_by(quiz_name=quiz_name).first()
        if existing_quiz:
            flash("Quiz with the same name already exists. Please use a different name.", 'error')
            return render_template('create_quiz.html', user=current_user, courses=courses), 403

        new_quiz = Quiz(quiz_name=quiz_name, total_questions=total_questions, teacher_id=current_user.id,
                        course_id=course_id, time_limit=time_limit, availability_date=availability_date)

        session['new_quiz'] = {
            'quiz_name': quiz_name,
            'total_questions': total_questions,
            'course_id': course_id,
            'teacher_id': current_user.id,
            'time_limit': time_limit,
            'availability_date': availability_date,
            'questions': []
        }

        return redirect(url_for('views.add_question'))

    return render_template('create_quiz.html', user=current_user, courses=courses)


@views.route('/add_question', methods=['GET', 'POST'])
@login_required
def add_question():
    if current_user.role != 'teacher':
        flash("Access Denied: Only teachers can add questions.", 'error')
        return redirect(url_for('views.home'))

    quiz_data = session.get('new_quiz')

    if not quiz_data:
        flash("Quiz data not found. Please create a quiz first.", 'error')
        return redirect(url_for('views.create_quiz'))

    quiz_name = quiz_data['quiz_name']
    total_questions_expected = quiz_data['total_questions']
    course_id = quiz_data['course_id']

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_option = request.form.get('correct_option')

        if not (question_text and option_a and option_b and option_c and option_d and correct_option):
            flash("Please fill in all question fields.")
            return redirect(url_for('views.add_question'))

        question_data = {
            'question_text': question_text,
            'option_a': option_a,
            'option_b': option_b,
            'option_c': option_c,
            'option_d': option_d,
            'correct_option': correct_option
        }

        quiz_data['questions'].append(question_data)
        session['new_quiz'] = quiz_data

        if len(quiz_data['questions']) >= total_questions_expected:
            return redirect(url_for('views.confirm_quiz'))

        return redirect(url_for('views.add_question'))

    return render_template('add_question.html', user=current_user, quiz_name=quiz_name,
                           total_questions=total_questions_expected)


@views.route('/confirm_quiz', methods=['GET', 'POST'])
@login_required
def confirm_quiz():
    if current_user.role != 'teacher':
        flash("Access Denied: Only teachers can submit quizzes.", 'error')
        return redirect(url_for('views.home'))

    quiz_data = session.get('new_quiz')

    if not quiz_data or len(quiz_data['questions']) < quiz_data['total_questions']:
        flash("Quiz data incomplete. Please add more questions.", 'error')
        return redirect(url_for('views.add_question'))

    if request.method == 'POST':
        if request.form.get('action') == 'submit':
            quiz_name = quiz_data['quiz_name']
            total_questions_expected = quiz_data['total_questions']
            course_id = quiz_data['course_id']
            time_limit = quiz_data['time_limit']
            availability_date = quiz_data['availability_date']

            new_quiz = Quiz(quiz_name=quiz_name, total_questions=total_questions_expected,
                            teacher_id=current_user.id, course_id=course_id, availability_date=availability_date,
                            time_limit=time_limit)

            db.session.add(new_quiz)
            db.session.commit()

            for question_data in quiz_data['questions']:
                new_question = Question(question_text=question_data['question_text'],
                                        option_a=question_data['option_a'],
                                        option_b=question_data['option_b'],
                                        option_c=question_data['option_c'],
                                        option_d=question_data['option_d'],
                                        correct_option=question_data['correct_option'],
                                        quiz_id=new_quiz.id)

                db.session.add(new_question)

            db.session.commit()

            return render_template('quiz_completed.html', user=current_user, quiz_id=new_quiz.id)

        elif request.form.get('action') == 'cancel':
            return redirect(url_for('views.create_quiz'))

    return render_template('quiz_confirmation.html', user=current_user)


# STUDENT FUNCTIONS
@views.route('/quizzes', methods=['GET', 'POST'])
@login_required
def quizzes():
    if current_user.role != 'student':
        flash("Access Denied: Only students can view quizzes.", 'error')
        return redirect(url_for('views.home'))

    current_time = datetime.now()
    enrolled_courses = current_user.enrolled_courses

    available_quizzes = Quiz.query.filter(
        Quiz.course_id.in_([course.id for course in enrolled_courses]),
        not_(Quiz.id.in_(db.session.query(quiz_attempts.c.quiz_template_id).filter_by(student_id=current_user.id)))
    ).all()

    attempted_quizzes = db.session.query(Quiz, quiz_attempts.c.overall_score) \
        .join(quiz_attempts,
              and_(Quiz.id == quiz_attempts.c.quiz_template_id, quiz_attempts.c.student_id == current_user.id)) \
        .all()

    return render_template('quizzes.html', user=current_user, quizzes=available_quizzes, time=current_time,
                           attempted_quizzes=attempted_quizzes)


@views.route('/attend_quiz_questions/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def attend_quiz_questions(quiz_id):
    if current_user.role != 'student':
        flash('Access Denied: Only students can attend quizzes!', 'error')
        return redirect(url_for('views.home'))

    quiz = Quiz.query.get_or_404(quiz_id)

    available_quizzes = Quiz.query.filter(
        Quiz.course_id.in_([course.id for course in current_user.enrolled_courses])
    ).all()

    if quiz not in available_quizzes:
        flash('Access Denied: You are not allowed to attend this quiz!', 'error')
        return redirect(url_for('views.quizzes'))

    if quiz.availability_date > datetime.now():
        flash("This quiz is not yet available.", 'error')
        return redirect(url_for('views.quizzes'))

    if quiz_id in [attempt.id for attempt in current_user.quiz_attempts]:
        flash('You have already attempted this quiz.', 'error')
        return redirect(url_for('views.quizzes'))

    if request.method == 'POST':
        total_questions = quiz.total_questions
        answered_questions = 0
        correct_answers = 0

        for question in quiz.questions:
            user_answer = request.form.get(f'question_{question.id}')

            if user_answer:
                answered_questions += 1
                if user_answer == question.correct_option:
                    correct_answers += 1

                score_for_question = 100 if user_answer == question.correct_option else 0
                user_answer_instance = UserAnswer(
                    user_id=current_user.id,
                    quiz_id=quiz_id,
                    question_id=question.id,
                    selected_option=user_answer,
                    score=score_for_question
                )
                db.session.add(user_answer_instance)

        if answered_questions == total_questions:
            overall_score = round((correct_answers / total_questions) * 100, 1)

            existing_attempt = db.session.query(quiz_attempts).filter_by(
                quiz_template_id=quiz_id, student_id=current_user.id).first()

            if existing_attempt:
                db.session.execute(
                    quiz_attempts.update().where(
                        and_(quiz_attempts.c.quiz_template_id == quiz_id, quiz_attempts.c.student_id == current_user.id)
                    ).values(
                        overall_score=overall_score
                    )
                )
            else:
                db.session.execute(quiz_attempts.insert().values(
                    quiz_template_id=quiz_id,
                    student_id=current_user.id,
                    overall_score=overall_score
                ))

            db.session.commit()

            return redirect(url_for('views.quiz_results', quiz_id=quiz_id))

    return render_template('attend_quiz_questions.html', user=current_user, quiz=quiz)


@views.route('/quiz_results/<int:quiz_id>', methods=['GET'])
@login_required
def quiz_results(quiz_id):
    if current_user.role != 'student':
        flash("Access Denied: Only students can view the quiz results", 'error')
        return redirect(url_for('views.home'))

    quiz = Quiz.query.get_or_404(quiz_id)

    user_attempt = db.session.query(quiz_attempts).filter_by(
        quiz_template_id=quiz_id, student_id=current_user.id
    ).first()
    overall_score = user_attempt.overall_score if user_attempt else None

    return render_template('quiz_results.html', quiz=quiz, user=current_user, overall_score=overall_score)


@views.route('/available_courses', methods=['GET'])
@login_required
def available_courses():
    if current_user.role != 'student':
        flash("Access Denied: Only students can enroll in courses.", 'error')
        return redirect(url_for('views.home'))

    enrolled_course_ids = [course.id for course in current_user.enrolled_courses]
    available_courses = (
        db.session.query(Course, User.firstName.label('teacher_first_name'))
        .join(User, Course.teacher_id == User.id)
        .filter(~Course.id.in_(enrolled_course_ids))
        .all()
    )

    current_courses = [
        (course, User.query.get(course.teacher_id).firstName) for course in current_user.enrolled_courses
    ]

    student_applications = StudentApplication.query.filter_by(student_id=current_user.id).all()

    return render_template('available_courses.html', user=current_user, available_courses=available_courses,
                           current_courses=current_courses, applications=student_applications)


@views.route('/enroll_course/<int:course_id>', methods=['POST'])
@login_required
def enroll_course(course_id):
    if current_user.role != 'student':
        flash("Access Denied: Only students can enroll in courses.", 'error')
        return redirect(url_for('views.home'))

    course = Course.query.get(course_id)

    # GEREK VAR MI BAK
    if course is None:
        flash("Course not found.", "error")
        return redirect(url_for('views.home'))

    if course in current_user.enrolled_courses:
        flash("You are already enrolled in this course.", "error")
        return redirect(url_for('views.available_courses'))

    application = StudentApplication(student_id=current_user.id, course_id=course.id)
    db.session.add(application)
    db.session.commit()

    flash(f"Your enrollment request for {course.course_name} has been submitted. Waiting for approval.", "success")
    return redirect(url_for('views.available_courses'))


@views.route('/drop_course/<int:course_id>', methods=['POST'])
@login_required
def drop_course(course_id):
    if current_user.role != 'student':
        flash("Access Denied: Only students can drop courses.", 'error')
        return redirect(url_for('views.home'))

    course_to_drop = Course.query.get(course_id)

    if course_to_drop is None:
        flash("Course not found.", "error")
        return redirect(url_for('views.available_courses'))

    if course_to_drop not in current_user.enrolled_courses:
        flash("You are not enrolled in this course.", "error")
        return redirect(url_for('views.available_courses'))

    current_user.enrolled_courses.remove(course_to_drop)
    db.session.commit()

    flash(f"You have successfully dropped the course: {course_to_drop.course_name}.", "success")
    return redirect(url_for('views.available_courses'))


# ADMIN FUNCTIONS

@views.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'admin':
        flash('Unauthorized to create courses.', 'error')
        return redirect(url_for('views.home'))

    teachers = User.query.filter_by(role='teacher').all()

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        teacher_id = request.form.get('teacher_id')

        if not (course_name and teacher_id):
            flash('Please provide both course name and teacher.', 'error')
            return redirect(url_for('views.home'))

        teacher = User.query.filter_by(id=teacher_id, role='teacher').first()

        # BUNA GEREK VAR MI BAK
        if not teacher:
            flash('Invalid teacher selection.', 'error')
            return redirect(url_for('create_course'))

        new_course = Course(course_name=course_name, teacher_id=teacher_id)

        try:
            db.session.add(new_course)
            db.session.commit()
            flash('Course created successfully!', 'success')
        except IntegrityError as e:
            db.session.rollback()
            error_info = str(e.orig)
            if 'duplicate key value violates unique constraint "courses_course_name_key"' in error_info:
                flash('Course with this name already exists.', category='error')
            else:
                flash('An error occurred while creating the course.', category='error')

    return render_template('create_course.html', user=current_user, teachers=teachers)


@views.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Unauthorized to manage users.', 'danger')
        return redirect(url_for('views.home'))

    users = User.query.all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')

        if not (user_id and new_role):
            flash('Please provide both user ID and role.', 'danger')
            return redirect(url_for('views.manage_users'))

        user = User.query.get(user_id)
        if not user:
            flash('User ID does not exist.', 'danger')
            return redirect(url_for('views.manage_users'))

        user.role = new_role
        db.session.commit()
        flash('User role updated successfully!', 'success')

    return render_template('manage_users.html', user=current_user, users=users)
