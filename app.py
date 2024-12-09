from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, timedelta
import pandas as pd
import random
import os

# Flask app setup
app = Flask(__name__)
app.secret_key = "secret_key_for_flash_messages"

# SQLAlchemy setup
Base = declarative_base()
database_url = os.environ.get('DATABASE_URL', 'sqlite:///library_management.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)
session = Session()

# Models
class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    author = Column(String)
    checked_out = Column(Boolean, default=False)

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    group = Column(String, nullable=False)
    preferred_books = Column(String)  # Stores book IDs as a comma-separated string

class BorrowRecord(Base):
    __tablename__ = 'borrow_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    borrow_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)

    student = relationship("Student")
    book = relationship("Book")

# Create tables
Base.metadata.create_all(engine)

# Enhanced populate_data function to include groups and preferred books
def populate_data():
    if not session.query(Book).first():
        data = pd.read_csv('longlist3.csv')
        for _, row in data.iterrows():
            book = Book(isbn=row['isbn'], title=row['title'], author=row['author'])
            session.add(book)
        session.commit()

    if not session.query(Student).first():
        students = ["Alice", "Bob", "Charlie", "David", "Eve"]
        groups = ["A", "B", "C", "D"]
        books = session.query(Book).all()
        for i, student_name in enumerate(students):
            preferred_books = ",".join(
                str(book.id) for book in random.sample(books, 3)
            )
            student = Student(
                first_name=student_name,
                group=groups[i % len(groups)],
                preferred_books=preferred_books,
            )
            session.add(student)
        session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/groups')
def view_groups():
    students = session.query(Student).all()
    grouped_students = {}
    for student in students:
        group = student.group
        if group not in grouped_students:
            grouped_students[group] = []
        grouped_students[group].append(student.first_name)
    return render_template('groups.html', groups=grouped_students)

@app.route('/preferences/<student_name>')
def view_preferences(student_name):
    student = session.query(Student).filter_by(first_name=student_name).first()
    if not student:
        flash(f"Student '{student_name}' not found!")
        return redirect(url_for('index'))
    preferred_books_ids = student.preferred_books.split(',')
    preferred_books = [session.query(Book).filter_by(id=int(book_id)).first() for book_id in preferred_books_ids]
    return render_template('preferences.html', student=student, books=preferred_books)

@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        student_name = request.form['student_name']
        book_title = request.form['book_title']
        student = session.query(Student).filter_by(first_name=student_name).first()
        book = session.query(Book).filter_by(title=book_title).first()

        if not student:
            flash(f"Student '{student_name}' not found!")
            return redirect(url_for('borrow'))
        if not book:
            flash(f"Book '{book_title}' not found!")
            return redirect(url_for('borrow'))
        if book.checked_out:
            flash(f"Book '{book_title}' is already borrowed!")
            return redirect(url_for('borrow'))

        # Borrow logic
        record = BorrowRecord(
            student_id=student.id,
            book_id=book.id,
            borrow_date=date.today(),
            return_date=date.today() + timedelta(days=14)
        )
        book.checked_out = True
        session.add(record)
        session.commit()
        flash(f"'{book_title}' successfully borrowed by {student_name}!")
        return redirect(url_for('index'))

    return render_template('borrow.html')

@app.route('/return', methods=['GET', 'POST'])
def return_book():
    if request.method == 'POST':
        book_title = request.form['book_title']
        book = session.query(Book).filter_by(title=book_title).first()

        if not book:
            flash(f"Book '{book_title}' not found!")
            return redirect(url_for('return_book'))
        if not book.checked_out:
            flash(f"Book '{book_title}' is not borrowed!")
            return redirect(url_for('return_book'))

        # Return logic
        book.checked_out = False
        session.commit()
        flash(f"'{book_title}' successfully returned!")
        return redirect(url_for('index'))

    return render_template('return.html')

@app.route('/find', methods=['GET', 'POST'])
def find():
    borrowed_books = []
    if request.method == 'POST':
        student_name = request.form['student_name']
        student = session.query(Student).filter_by(first_name=student_name).first()

        if not student:
            flash(f"Student '{student_name}' not found!")
            return redirect(url_for('find'))

        # Retrieve unique borrow records for the student
        records = (
            session.query(BorrowRecord)
            .filter_by(student_id=student.id)
            .distinct(BorrowRecord.book_id)  # Ensure uniqueness by book ID
            .all()
        )

        # Create a set to track already displayed books
        seen_books = set()
        for record in records:
            if record.book.title not in seen_books:
                borrowed_books.append((record.book.title, record.return_date))
                seen_books.add(record.book.title)

    return render_template('find.html', borrowed_books=borrowed_books)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
