import os
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, timedelta
import pandas as pd

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Near the top of app.py, update the database configuration:
try:
    # SQLAlchemy setup with Heroku PostgreSQL support
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///library_management.db')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(database_url)
    Base = declarative_base()
    Session = sessionmaker(bind=engine)
    session = Session()
    app.logger.info("Database connection established successfully")
except Exception as e:
    app.logger.error(f"Database connection error: {str(e)}")
    raise

# Models
class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    author = Column(String)
    rating = Column(Float)
    checked_out = Column(Boolean, default=False)

    def get_status(self):
        return "Checked Out" if self.checked_out else "Available"

class PreferredBook(Base):
    __tablename__ = 'preferred_books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_title = Column(String, nullable=False)
    student = relationship("Student", back_populates="preferred_books")

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    group = Column(String, nullable=False)
    preferred_books = relationship("PreferredBook", back_populates="student")

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
        # First load all books
        if not session.query(Book).first():
            csv_path = os.path.join(os.path.dirname(__file__), 'longlist3.csv')
            data = pd.read_csv(csv_path)
            for _, row in data.iterrows():
                book = Book(
                    isbn=row['isbn'],
                    title=row['title'],
                    author=row['author'],
                    rating=float(row.get('rating', 0))
                )
                session.add(book)
            session.commit()
            app.logger.info("Books loaded successfully")
        
        # Then set up students with real book preferences
        if not session.query(Student).first():
            available_books = session.query(Book).all()
            book_titles = [book.title for book in available_books]
            
            students_data = [
                # Group A
                {"first_name": "Alice", "group": "A", "preferred_books": book_titles[0:3]},
                {"first_name": "Emma", "group": "A", "preferred_books": book_titles[3:6]},
                {"first_name": "Michael", "group": "A", "preferred_books": book_titles[6:9]},
                
                # Group B
                {"first_name": "Bob", "group": "B", "preferred_books": book_titles[9:12]},
                {"first_name": "Sarah", "group": "B", "preferred_books": book_titles[12:15]},
                {"first_name": "James", "group": "B", "preferred_books": book_titles[15:18]},
                
                # Group C
                {"first_name": "Charlie", "group": "C", "preferred_books": book_titles[18:21]},
                {"first_name": "Lisa", "group": "C", "preferred_books": book_titles[21:24]},
                {"first_name": "David", "group": "C", "preferred_books": book_titles[24:27]},
                
                # Group D
                {"first_name": "Diana", "group": "D", "preferred_books": book_titles[27:30]},
                {"first_name": "John", "group": "D", "preferred_books": book_titles[30:33]},
                {"first_name": "Mary", "group": "D", "preferred_books": book_titles[33:36]}
            ]
            
            for student_info in students_data:
                try:
                    student = Student(
                        first_name=student_info["first_name"],
                        group=student_info["group"]
                    )
                    session.add(student)
                    session.flush()
                    
                    for book_title in student_info["preferred_books"]:
                        preferred_book = PreferredBook(
                            student_id=student.id,
                            book_title=book_title
                        )
                        session.add(preferred_book)
                except Exception as e:
                    app.logger.error(f"Error adding student {student_info['first_name']}: {str(e)}")
                    session.rollback()
                    continue
            
            session.commit()
            app.logger.info("Students and preferences loaded successfully")
            
    except Exception as e:
        app.logger.error(f"Error in populate_data: {str(e)}")
        session.rollback()

# Create tables and populate data
with app.app_context():
    Base.metadata.create_all(engine)
    populate_data()

# Routes
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

@app.route('/book_status')
def book_status():
    books = session.query(Book).all()
    avg_rating = session.query(func.avg(Book.rating)).scalar() or 0
    return render_template('book_status.html', books=books, avg_rating=avg_rating)

@app.route('/student_lookup', methods=['GET', 'POST'])
def student_lookup():
    if request.method == 'POST':
        student_name = request.form['student_name']
        student = session.query(Student).filter_by(first_name=student_name).first()
        
        if student:
            borrowed_books = session.query(BorrowRecord).filter_by(student_id=student.id).all()
            return render_template('student_lookup.html', 
                                student=student,
                                borrowed_books=borrowed_books)
    
    return render_template('student_lookup.html')

@app.route('/group_view')
def group_view():
    groups = {}
    for group in ['A', 'B', 'C', 'D']:
        groups[group] = session.query(Student).filter_by(group=group).all()
    return render_template('group_view.html', groups=groups)

@app.route('/preferences')
def view_preferences():
    students = session.query(Student).all()
    preferences = {}
    for student in students:
        preferred_books = session.query(PreferredBook).filter_by(student_id=student.id).all()
        preferences[student.first_name] = {
            'group': student.group,
            'preferred_books': [book.book_title for book in preferred_books]
        }
    return render_template('preferences.html', preferences=preferences)

@app.route('/book_ratings')
def book_ratings():
    books = session.query(Book).all()
    avg_rating = session.query(func.avg(Book.rating)).scalar() or 0
    return render_template('book_ratings.html', books=books, avg_rating=avg_rating)

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
    app.run(host='0.0.0.0', port=port, debug=False)