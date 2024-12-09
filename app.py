import os
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, timedelta
import pandas as pd

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_123')  # Get from environment or use default

# SQLAlchemy setup - Use DATABASE_URL from Heroku
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(database_url or 'sqlite:///library_management.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Models remain the same
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

class BorrowRecord(Base):
    __tablename__ = 'borrow_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    borrow_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    student = relationship("Student")
    book = relationship("Book")

def populate_data():
    try:
        if not session.query(Book).first():
            # Use absolute path or read from environment variable
            csv_path = os.environ.get('CSV_PATH', 'longlist3.csv')
            if os.path.exists(csv_path):
                data = pd.read_csv(csv_path)
                for _, row in data.iterrows():
                    book = Book(
                        isbn=str(row['isbn']),
                        title=str(row['title']),
                        author=str(row['author'])
                    )
                    session.add(book)
                session.commit()
                app.logger.info("Books loaded successfully")
            else:
                app.logger.warning(f"CSV file not found at {csv_path}")

        if not session.query(Student).first():
            students = ["Alice", "Bob", "Charlie", "David"]
            for name in students:
                session.add(Student(first_name=name))
            session.commit()
            app.logger.info("Students loaded successfully")
            
    except Exception as e:
        app.logger.error(f"Error in populate_data: {str(e)}")
        session.rollback()

# Initialize database within app context
@app.before_first_request
def init_db():
    try:
        Base.metadata.create_all(engine)
        populate_data()
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")

# Routes remain the same
@app.route('/')
def index():
    return render_template('index.html')

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

    return render_template('find.html', borrowed_books=borrowed_books)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)