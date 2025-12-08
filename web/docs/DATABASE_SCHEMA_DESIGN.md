# 🗄️ University Portal - Database Schema Design

## Database Schema Overview

The university portal requires a comprehensive database schema that supports realistic academic operations while maintaining the existing security testing capabilities. This design expands the current simple models into a full Student Information System (SIS) structure.

## Enhanced Database Models

### University Information

#### University Model
```python
class University(db.Model):
    __tablename__ = 'universities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    short_name = db.Column(db.String(50), nullable=False)
    motto = db.Column(db.String(300))
    established_year = db.Column(db.Integer)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    chancellor = db.Column(db.String(100))
    total_students = db.Column(db.Integer, default=0)
    total_faculty = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### User Management System

#### Enhanced User Model
```python
class User(db.Model):
    __tablename__ = 'users'
    
    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.String(20), unique=True, nullable=False)  # Student/Employee ID
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # [VULNERABILITY: Weak hashing]
    
    # Personal information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    date_of_birth = db.Column(db.Date)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    
    # University-specific information
    user_type = db.Column(db.Enum('student', 'faculty', 'staff', 'admin', name='user_types'), nullable=False)
    status = db.Column(db.Enum('active', 'inactive', 'graduated', 'suspended', name='user_status'), default='active')
    enrollment_date = db.Column(db.Date)
    graduation_date = db.Column(db.Date)
    
    # Academic information (for students)
    major_id = db.Column(db.Integer, db.ForeignKey('academic_programs.id'))
    minor_id = db.Column(db.Integer, db.ForeignKey('academic_programs.id'))
    academic_level = db.Column(db.Enum('freshman', 'sophomore', 'junior', 'senior', 'graduate', name='academic_levels'))
    gpa = db.Column(db.Float, default=0.0)
    total_credits = db.Column(db.Integer, default=0)
    
    # Employment information (for faculty/staff)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    title = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    office_location = db.Column(db.String(50))
    
    # Security and session management
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Profile customization
    profile_picture = db.Column(db.String(200))
    bio = db.Column(db.Text)
    preferred_name = db.Column(db.String(50))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    major = db.relationship('AcademicProgram', foreign_keys=[major_id], backref='major_students')
    minor = db.relationship('AcademicProgram', foreign_keys=[minor_id], backref='minor_students')
    department = db.relationship('Department', backref='employees')
    enrollments = db.relationship('Enrollment', backref='student', lazy='dynamic')
    grades = db.relationship('Grade', backref='student', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_student(self):
        return self.user_type == 'student'
    
    @property
    def is_faculty(self):
        return self.user_type == 'faculty'
    
    def check_password(self, password):
        # [VULNERABILITY: Weak password checking for SQL injection testing]
        return self.password_hash == password  # Intentionally vulnerable
```

### Academic Structure

#### Department Model
```python
class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)  # e.g., 'CS', 'MATH'
    description = db.Column(db.Text)
    head_faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    building = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    
    # Relationships
    head_faculty = db.relationship('User', foreign_keys=[head_faculty_id])
    programs = db.relationship('AcademicProgram', backref='department', lazy='dynamic')
    courses = db.relationship('Course', backref='department', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Academic Program Model
```python
class AcademicProgram(db.Model):
    __tablename__ = 'academic_programs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    degree_type = db.Column(db.Enum('associate', 'bachelor', 'master', 'doctoral', name='degree_types'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    description = db.Column(db.Text)
    required_credits = db.Column(db.Integer, default=120)
    duration_years = db.Column(db.Integer, default=4)
    
    # Program requirements
    core_requirements = db.Column(db.Text)  # JSON string of course requirements
    elective_credits = db.Column(db.Integer, default=30)
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    accreditation = db.Column(db.String(200))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Course Management System

#### Course Model
```python
class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)  # e.g., 'CS101'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, default=3)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    # Course requirements
    prerequisites = db.Column(db.Text)  # JSON string of prerequisite courses
    corequisites = db.Column(db.Text)   # JSON string of corequisite courses
    
    # Course details
    course_level = db.Column(db.Enum('undergraduate', 'graduate', name='course_levels'))
    lecture_hours = db.Column(db.Integer, default=3)
    lab_hours = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    sections = db.relationship('CourseSection', backref='course', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def full_code(self):
        return f"{self.department.code}{self.course_code}"
```

#### Course Section Model
```python
class CourseSection(db.Model):
    __tablename__ = 'course_sections'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    section_number = db.Column(db.String(10), nullable=False)  # e.g., '001', 'A'
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Schedule information
    meeting_days = db.Column(db.String(20))  # e.g., 'MWF', 'TTh'
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    classroom = db.Column(db.String(50))
    
    # Enrollment limits
    max_enrollment = db.Column(db.Integer, default=30)
    current_enrollment = db.Column(db.Integer, default=0)
    waitlist_capacity = db.Column(db.Integer, default=5)
    
    # Section status
    status = db.Column(db.Enum('open', 'closed', 'cancelled', name='section_status'), default='open')
    
    # Relationships
    instructor = db.relationship('User', backref='taught_sections')
    semester = db.relationship('Semester', backref='course_sections')
    enrollments = db.relationship('Enrollment', backref='section', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Academic Calendar

#### Semester Model
```python
class Semester(db.Model):
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., 'Fall 2024'
    code = db.Column(db.String(20), nullable=False)  # e.g., 'F24'
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.Enum('spring', 'summer', 'fall', 'winter', name='terms'))
    
    # Important dates
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    registration_start = db.Column(db.Date)
    registration_end = db.Column(db.Date)
    add_drop_deadline = db.Column(db.Date)
    withdrawal_deadline = db.Column(db.Date)
    final_exams_start = db.Column(db.Date)
    final_exams_end = db.Column(db.Date)
    
    # Status
    is_current = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Student Academic Records

#### Enrollment Model
```python
class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'), nullable=False)
    
    # Enrollment details
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('enrolled', 'waitlisted', 'dropped', 'withdrawn', name='enrollment_status'), default='enrolled')
    
    # Academic tracking
    attendance_percentage = db.Column(db.Float, default=100.0)
    participation_grade = db.Column(db.String(5))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (db.UniqueConstraint('student_id', 'section_id', name='unique_enrollment'),)
```

#### Grade Model
```python
class Grade(db.Model):
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'), nullable=False)
    assignment_type = db.Column(db.Enum('assignment', 'quiz', 'exam', 'project', 'participation', 'final', name='assignment_types'))
    
    # Grade information
    assignment_name = db.Column(db.String(200))
    points_earned = db.Column(db.Float)
    points_possible = db.Column(db.Float)
    letter_grade = db.Column(db.String(5))  # A, A-, B+, etc.
    grade_percentage = db.Column(db.Float)
    
    # Grading details
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Faculty who graded
    graded_date = db.Column(db.DateTime)
    comments = db.Column(db.Text)
    
    # Status
    is_final = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=False)
    
    # Relationships
    grader = db.relationship('User', foreign_keys=[graded_by], backref='graded_assignments')
    section = db.relationship('CourseSection', backref='grades')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Document Management System

#### Document Model
```python
class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    content_type = db.Column(db.String(100))
    file_hash = db.Column(db.String(64))  # SHA-256 hash
    
    # Document categorization
    document_type = db.Column(db.Enum('assignment', 'transcript', 'policy', 'form', 'resource', 'other', name='document_types'))
    category = db.Column(db.String(50))
    
    # Ownership and permissions
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'))
    access_level = db.Column(db.Enum('public', 'students', 'faculty', 'admin', name='access_levels'), default='public')
    
    # Security scanning results
    is_scanned = db.Column(db.Boolean, default=False)
    scan_result = db.Column(db.Enum('clean', 'infected', 'suspicious', 'error', name='scan_results'))
    scan_details = db.Column(db.Text)  # JSON string with scan results
    quarantined = db.Column(db.Boolean, default=False)
    
    # Document metadata
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON array of tags
    
    # Version control
    version = db.Column(db.String(20), default='1.0')
    parent_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    
    # Download tracking
    download_count = db.Column(db.Integer, default=0)
    last_downloaded = db.Column(db.DateTime)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_documents')
    course_section = db.relationship('CourseSection', backref='documents')
    parent_document = db.relationship('Document', remote_side=[id], backref='versions')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Feedback and Communication

#### Feedback Model (Enhanced for XSS Testing)
```python
class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Feedback source
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'))
    feedback_type = db.Column(db.Enum('course_evaluation', 'instructor_feedback', 'suggestion', 'complaint', name='feedback_types'))
    
    # Feedback content [VULNERABILITY: XSS through unescaped content]
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)  # Vulnerable to XSS
    rating = db.Column(db.Integer)  # 1-5 scale
    
    # Administrative handling
    status = db.Column(db.Enum('pending', 'reviewed', 'resolved', 'archived', name='feedback_status'), default='pending')
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    admin_response = db.Column(db.Text)
    
    # Anonymity options
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='submitted_feedback')
    section = db.relationship('CourseSection', backref='feedback')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_feedback')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Security and Audit Logging

#### Enhanced Security Event Model
```python
class SecurityEvent(db.Model):
    __tablename__ = 'security_events'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Event identification
    event_type = db.Column(db.Enum('login_attempt', 'login_success', 'login_failure', 'file_upload', 
                                  'suspicious_activity', 'malware_detected', 'access_violation', 
                                  'data_export', 'admin_action', name='security_event_types'))
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='severity_levels'))
    
    # Event details
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)
    request_url = db.Column(db.Text)
    request_method = db.Column(db.String(10))
    
    # Additional context
    session_id = db.Column(db.String(255))
    additional_data = db.Column(db.Text)  # JSON string for extra details
    
    # Security response
    blocked = db.Column(db.Boolean, default=False)
    alert_sent = db.Column(db.Boolean, default=False)
    investigated = db.Column(db.Boolean, default=False)
    
    # NGFW integration
    vm1_notified = db.Column(db.Boolean, default=False)
    vm1_response = db.Column(db.Text)
    
    # Relationships
    user = db.relationship('User', backref='security_events')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Comprehensive Audit Log Model
```python
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Action details
    action = db.Column(db.String(100), nullable=False)  # CREATE, READ, UPDATE, DELETE
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    
    # User context
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Change tracking
    old_values = db.Column(db.Text)  # JSON string of old values
    new_values = db.Column(db.Text)  # JSON string of new values
    
    # Academic context
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'))
    course_section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'))
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    semester = db.relationship('Semester', backref='audit_logs')
    course_section = db.relationship('CourseSection', backref='audit_logs')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## Database Indexes and Performance

### Essential Indexes
```sql
-- User lookup indexes
CREATE INDEX idx_users_university_id ON users(university_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_type_status ON users(user_type, status);

-- Academic lookup indexes
CREATE INDEX idx_enrollments_student_semester ON enrollments(student_id, section_id);
CREATE INDEX idx_grades_student_section ON grades(student_id, section_id);
CREATE INDEX idx_courses_department_level ON courses(department_id, course_level);

-- Security and logging indexes
CREATE INDEX idx_security_events_user_time ON security_events(user_id, created_at);
CREATE INDEX idx_security_events_ip_time ON security_events(ip_address, created_at);
CREATE INDEX idx_audit_logs_user_action_time ON audit_logs(user_id, action, created_at);

-- Document management indexes
CREATE INDEX idx_documents_uploader_type ON documents(uploaded_by, document_type);
CREATE INDEX idx_documents_scan_status ON documents(is_scanned, scan_result);
```

## Data Migration Strategy

### Migrating Existing Data
```python
def migrate_existing_data():
    """Migrate existing simple models to university schema"""
    
    # Create default university
    university = University(
        name="Riverside University",
        short_name="RU",
        motto="Innovation Through Education",
        established_year=2010
    )
    db.session.add(university)
    
    # Create default departments
    cs_dept = Department(name="Computer Science", code="CS")
    math_dept = Department(name="Mathematics", code="MATH")
    eng_dept = Department(name="Engineering", code="ENG")
    
    # Create current semester
    current_semester = Semester(
        name="Fall 2024",
        code="F24",
        year=2024,
        term="fall",
        is_current=True,
        start_date=date(2024, 8, 26),
        end_date=date(2024, 12, 15)
    )
    
    # Migrate existing users to enhanced user model
    for old_user in OldUser.query.all():
        new_user = User(
            university_id=f"S{old_user.id:06d}",  # Generate student ID
            email=old_user.email,
            username=old_user.username,
            password_hash=old_user.password,  # Keep vulnerable hashing
            first_name=old_user.username.split('.')[0].title(),
            last_name=old_user.username.split('.')[1].title() if '.' in old_user.username else "Student",
            user_type='student'
        )
        db.session.add(new_user)
    
    db.session.commit()
```

## Sample Data Generation

### Realistic University Data
```python
def generate_sample_data():
    """Generate realistic university data for testing"""
    
    # Sample courses
    courses_data = [
        {'code': '101', 'title': 'Introduction to Computer Science', 'credits': 3, 'dept': 'CS'},
        {'code': '102', 'title': 'Programming Fundamentals', 'credits': 4, 'dept': 'CS'},
        {'code': '201', 'title': 'Data Structures and Algorithms', 'credits': 4, 'dept': 'CS'},
        {'code': '301', 'title': 'Database Systems', 'credits': 3, 'dept': 'CS'},
        {'code': '401', 'title': 'Software Engineering', 'credits': 3, 'dept': 'CS'},
        {'code': '110', 'title': 'College Algebra', 'credits': 3, 'dept': 'MATH'},
        {'code': '120', 'title': 'Calculus I', 'credits': 4, 'dept': 'MATH'},
        {'code': '105', 'title': 'Engineering Design', 'credits': 3, 'dept': 'ENG'},
    ]
    
    # Sample students with realistic data
    students_data = [
        {'id': 'S000001', 'name': 'Alice Johnson', 'email': 'alice.johnson@riverside.edu', 'major': 'CS'},
        {'id': 'S000002', 'name': 'Bob Smith', 'email': 'bob.smith@riverside.edu', 'major': 'CS'},
        {'id': 'S000003', 'name': 'Carol Davis', 'email': 'carol.davis@riverside.edu', 'major': 'MATH'},
        {'id': 'S000004', 'name': 'David Wilson', 'email': 'david.wilson@riverside.edu', 'major': 'ENG'},
        {'id': 'S000005', 'name': 'Emma Brown', 'email': 'emma.brown@riverside.edu', 'major': 'CS'},
    ]
    
    # Sample faculty
    faculty_data = [
        {'name': 'Dr. Sarah Chen', 'email': 'sarah.chen@riverside.edu', 'dept': 'CS', 'title': 'Professor'},
        {'name': 'Dr. Michael Rodriguez', 'email': 'michael.rodriguez@riverside.edu', 'dept': 'MATH', 'title': 'Associate Professor'},
        {'name': 'Dr. Jennifer Liu', 'email': 'jennifer.liu@riverside.edu', 'dept': 'ENG', 'title': 'Assistant Professor'},
    ]
```

This comprehensive database schema provides the foundation for a realistic university portal while maintaining all the security testing capabilities of the original application.