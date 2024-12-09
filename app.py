from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, timedelta
import os

# Flask app setup
app = Flask(__name__)
app.secret_key = 'dev_key_123'

# SQLAlchemy setup with SQLite
engine = create_engine('sqlite:///library_management.db')
Base = declarative_base()
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
    preferred_books = relationship("PreferredBook", back_populates="student")
    borrow_records = relationship("BorrowRecord", back_populates="student")

class BorrowRecord(Base):
    __tablename__ = 'borrow_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    borrow_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    student = relationship("Student")
    book = relationship("Book")

def init_db():
    Base.metadata.create_all(engine)
    
    # Add books if they don't exist
    if not session.query(Book).first():
        try:
            books_data = [
                # All 78 books from previous message
                # (I can repeat them if you'd like)
            ]

            # Add books to database
            for book_data in books_data:
                book = Book(**book_data)
                session.add(book)
            session.commit()
            print(f"Successfully added {len(books_data)} books to database")

        except Exception as e:
            print(f"Error populating books: {e}")
            session.rollback()

    # Add students if they don't exist
    if not session.query(Student).first():
        try:
            # Student data organized by groups
            students_data = {
                'A': [
                    {"first_name": "Stanley", "preferred_books": ["Boulder", "Whale", "The Gospel According to the New World"]},
                    {"first_name": "Linda", "preferred_books": ["Standing Heavy", "Time Shelter", "Is Mother Dead"]},
                    {"first_name": "Michael", "preferred_books": ["Jimi Hendrix Live in Lviv", "The Birthday Party", "While We Were Dreaming"]}
                ],
                'B': [
                    {"first_name": "Emily", "preferred_books": ["Pyre", "Still Born", "A System So Magnificent It Is Blinding"]},
                    {"first_name": "David", "preferred_books": ["Ninth Building", "Paradais", "Heaven"]},
                    {"first_name": "Lisa", "preferred_books": ["Love in the Big City", "Happy Stories, Mostly", "Elena Knows"]}
                ],
                'C': [
                    {"first_name": "James", "preferred_books": ["The Book of Mother", "More Than I Love My Life", "Phenotypes"]},
                    {"first_name": "Emma", "preferred_books": ["A New Name: Septology VI-VII", "After the Sun", "Tomb of Sand"]},
                    {"first_name": "Daniel", "preferred_books": ["The Books of Jacob", "Cursed Bunny", "The War of the Poor"]}
                ],
                'D': [
                    {"first_name": "Anna", "preferred_books": ["When We Cease to Understand the World", "Wretchedness", "An Inventory of Losses"]},
                    {"first_name": "William", "preferred_books": ["At Night All Blood is Black", "I Live in the Slums", "In Memory of Memory"]},
                    {"first_name": "Sophie", "preferred_books": ["Minor Detail", "Summer Brother", "The Dangers of Smoking in Bed"]}
                ]
            }

            # Add students and their group information
            for group, students in students_data.items():
                for student_info in students:
                    student = Student(
                        first_name=student_info["first_name"],
                        group=group
                    )
                    session.add(student)
                    session.flush()  # Get the student ID

                    # Add preferred books
                    for book_title in student_info["preferred_books"]:
                        preferred_book = PreferredBook(
                            student_id=student.id,
                            book_title=book_title
                        )
                        session.add(preferred_book)
            session.commit()
            print("Successfully added students and their preferred books")
        except Exception as e:
            print(f"Error populating students: {e}")
            session.rollback()

# Make sure you have these models defined
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
    student = relationship("Student")
    book = relationship("Book")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book_stats')
def book_stats():
    # Get books with ratings above/below average
    avg_rating = session.query(func.avg(Book.rating)).scalar()
    high_rated = session.query(Book).filter(Book.rating > avg_rating).all()
    low_rated = session.query(Book).filter(Book.rating <= avg_rating).all()
    
    # Get borrowed/available books
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