from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, timedelta
import os

# Flask app setup
app = Flask(__name__)
app.secret_key = 'dev_key_123'

# SQLAlchemy setup
Base = declarative_base()

# Define models
class PreferredBook(Base):
    __tablename__ = 'preferred_books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_title = Column(String, nullable=False)
    student = relationship("Student", back_populates="preferred_books")

class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    author = Column(String)
    rating = Column(Float)
    checked_out = Column(Boolean, default=False)

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    group = Column(String, nullable=False)
    preferred_books = relationship("PreferredBook", back_populates="student")
    borrow_records = relationship("BorrowRecord", back_populates="student")

class BorrowRecord(Base):
    __tablename__ = 'borrow_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    borrow_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    student = relationship("Student", back_populates="borrow_records")
    book = relationship("Book")

# Database setup after models are defined
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///library_management.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def init_db():
    Base.metadata.create_all(engine)
    
    # Add books if they don't exist
    if not session.query(Book).first():
        try:
            books_data = [
                {"isbn": "123456789", "title": "Sample Book 1", "author": "Author 1", "rating": 4.5},
                {"isbn": "987654321", "title": "Sample Book 2", "author": "Author 2", "rating": 4.0}
            ]
            for book_data in books_data:
                book = Book(**book_data)
                session.add(book)
            session.commit()
        except Exception as e:
            print(f"Error populating books: {e}")
            session.rollback()

    # Add students if they don't exist
    if not session.query(Student).first():
        try:
            students_data = {
                'A': ["Stanley", "Linda", "Michael"],
                'B': ["Emily", "David", "Lisa"],
                'C': ["James", "Emma", "Daniel"],
                'D': ["Anna", "William", "Sophie"]
            }
            
            for group, names in students_data.items():
                for name in names:
                    student = Student(first_name=name, group=group)
                    session.add(student)
            session.commit()
        except Exception as e:
            print(f"Error populating students: {e}")
            session.rollback()

# Initialize database
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book_stats')
def book_stats():
    avg_rating = session.query(func.avg(Book.rating)).scalar()
    high_rated = session.query(Book).filter(Book.rating > avg_rating).all()
    low_rated = session.query(Book).filter(Book.rating <= avg_rating).all()
    borrowed = session.query(Book).filter_by(checked_out=True).all()
    available = session.query(Book).filter_by(checked_out=False).all()
    
    return render_template('book_stats.html', 
                         high_rated=high_rated,
                         low_rated=low_rated,
                         borrowed=borrowed,
                         available=available,
                         avg_rating=avg_rating)

@app.route('/groups')
def view_groups():
    students = session.query(Student).order_by(Student.group).all()
    groups = {}
    for student in students:
        if student.group not in groups:
            groups[student.group] = []
        groups[student.group].append(student)
    return render_template('groups.html', groups=groups)

@app.route('/find_group', methods=['GET', 'POST'])
def find_group():
    if request.method == 'POST':
        student_name = request.form['student_name']
        student = session.query(Student).filter_by(first_name=student_name).first()
        if student:
            return render_template('find_group.html', student=student)
        flash(f"Student '{student_name}' not found!")
    return render_template('find_group.html')

@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        try:
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
        except Exception as e:
            print(f"Error in borrow: {e}")
            session.rollback()
            flash("An error occurred while processing your request.")
            return redirect(url_for('borrow'))

    return render_template('borrow.html')

@app.route('/return', methods=['GET', 'POST'])
def return_book():
    if request.method == 'POST':
        try:
            book_title = request.form['book_title']
            book = session.query(Book).filter_by(title=book_title).first()

            if not book:
                flash(f"Book '{book_title}' not found!")
                return redirect(url_for('return_book'))
            if not book.checked_out:
                flash(f"Book '{book_title}' is not borrowed!")
                return redirect(url_for('return_book'))

            book.checked_out = False
            session.commit()
            flash(f"'{book_title}' successfully returned!")
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Error in return_book: {e}")
            session.rollback()
            flash("An error occurred while processing your request.")
            return redirect(url_for('return_book'))

    return render_template('return.html')

@app.route('/find', methods=['GET', 'POST'])
def find():
    borrowed_books = []
    if request.method == 'POST':
        try:
            student_name = request.form['student_name']
            student = session.query(Student).filter_by(first_name=student_name).first()

            if not student:
                flash(f"Student '{student_name}' not found!")
                return redirect(url_for('find'))

            records = (
                session.query(BorrowRecord)
                .filter_by(student_id=student.id)
                .distinct(BorrowRecord.book_id)
                .all()
            )

            seen_books = set()
            for record in records:
                if record.book.title not in seen_books:
                    borrowed_books.append((record.book.title, record.return_date))
                    seen_books.add(record.book.title)
        except Exception as e:
            print(f"Error in find: {e}")
            flash("An error occurred while processing your request.")
            return redirect(url_for('find'))

    return render_template('find.html', borrowed_books=borrowed_books)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)