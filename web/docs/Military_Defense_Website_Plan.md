# 🎖️ AEGIS Defense Systems - Military Website Implementation Plan

**Project:** Transform NGFW Test Website into Professional Military Defense Company Site  
**Target:** Realistic military contractor website with hidden vulnerabilities  
**Date:** November 13, 2025

---

## 🎯 Project Overview

### **Objective**
Transform the current basic vulnerability testing website into a sophisticated military defense contractor website called **"AEGIS Defense Systems"** where vulnerabilities are naturally integrated into business functions rather than being obvious testing endpoints.

### **Key Principles**
1. **Professional Military Aesthetic** - Looks like a genuine defense contractor
2. **Hidden Vulnerabilities** - Security flaws integrated into legitimate business functions
3. **Natural Attack Discovery** - Attackers explore like real users, not obvious test endpoints
4. **Realistic User Flows** - Authentic business processes with embedded vulnerabilities
5. **Enhanced Database Design** - Military-focused data structures

---

## 🏛️ AEGIS Defense Systems - Company Profile

### **Company Identity**
- **Name:** AEGIS Defense Systems
- **Industry:** Military Technology & Defense Contracting
- **Specialties:** Radar Systems, Missile Defense, Cybersecurity Solutions
- **Founded:** 2010
- **Headquarters:** Arlington, VA
- **Security Clearance:** Top Secret/SCI

### **Website Structure**
```
🏠 Homepage → Corporate overview, recent contracts
🛡️ Products & Services → Defense systems catalog
📰 News & Updates → Press releases, announcements
👥 Personnel Portal → Employee/contractor login
📁 Document Center → Classified docs, technical manuals
📞 Contact & Inquiries → Business contact forms
🔍 Search → Database search functionality
📊 System Status → Network monitoring dashboard
🏢 About Us → Company history, leadership
🔐 Admin Dashboard → Authenticated user management
```

---

## 📊 Enhanced Database Schema

### **New/Modified Tables**

#### **1. Users Table (Enhanced)**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(120) NOT NULL,  -- Still plain text for SQL injection
    email VARCHAR(120),
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    department VARCHAR(100),  -- Engineering, Security, Operations, etc.
    clearance_level VARCHAR(20),  -- Unclassified, Secret, Top Secret
    employee_id VARCHAR(20) UNIQUE,
    phone VARCHAR(20),
    position VARCHAR(100),
    hire_date DATE,
    last_login DATETIME,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### **2. Projects Table (New)**
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,
    project_code VARCHAR(20) UNIQUE,
    description TEXT,
    classification VARCHAR(20),  -- Unclassified, Confidential, Secret
    status VARCHAR(50),  -- Active, Completed, On Hold
    start_date DATE,
    end_date DATE,
    budget DECIMAL(15,2),
    project_manager_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_manager_id) REFERENCES users(id)
);
```

#### **3. Documents Table (New)**
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    filename VARCHAR(255),
    filepath VARCHAR(512),
    document_type VARCHAR(50),  -- Manual, Report, Specification
    classification VARCHAR(20),
    project_id INTEGER,
    uploaded_by INTEGER,
    file_size INTEGER,
    file_hash VARCHAR(64),
    access_count INTEGER DEFAULT 0,
    last_accessed DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);
```

#### **4. News Articles Table (New)**
```sql
CREATE TABLE news_articles (
    id INTEGER PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    author_id INTEGER,
    category VARCHAR(50),  -- Press Release, Contract Award, Technology
    is_published BOOLEAN DEFAULT 0,
    publish_date DATETIME,
    view_count INTEGER DEFAULT 0,
    allow_comments BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id)
);
```

#### **5. Comments Table (New - XSS Target)**
```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    article_id INTEGER,
    author_name VARCHAR(100),
    author_email VARCHAR(120),
    content TEXT NOT NULL,  -- Vulnerable to XSS
    is_approved BOOLEAN DEFAULT 0,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES news_articles(id)
);
```

#### **6. System Diagnostics Table (New)**
```sql
CREATE TABLE system_diagnostics (
    id INTEGER PRIMARY KEY,
    system_name VARCHAR(100),
    diagnostic_type VARCHAR(50),
    command_executed TEXT,  -- Command injection target
    result TEXT,
    status VARCHAR(20),  -- Success, Failed, Error
    executed_by INTEGER,
    execution_time FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (executed_by) REFERENCES users(id)
);
```

#### **7. Contact Inquiries Table (Enhanced)**
```sql
CREATE TABLE contact_inquiries (
    id INTEGER PRIMARY KEY,
    inquiry_type VARCHAR(50),  -- General, Partnership, Support
    company_name VARCHAR(200),
    contact_name VARCHAR(100),
    email VARCHAR(120),
    phone VARCHAR(20),
    subject VARCHAR(300),
    message TEXT,  -- XSS vulnerability
    clearance_required BOOLEAN DEFAULT 0,
    priority VARCHAR(20) DEFAULT 'Normal',
    status VARCHAR(50) DEFAULT 'New',
    assigned_to INTEGER,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);
```

---

## 🎯 Vulnerability Integration Strategy

### **1. SQL Injection - Personnel Portal**
**Location:** `/personnel/login`
**Business Context:** Employee authentication system
**Vulnerability:** Raw SQL queries in login validation
```python
# Vulnerable login query
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

### **2. XSS - News Comments**
**Location:** `/news/article/{id}#comments`
**Business Context:** Public commenting on press releases
**Vulnerability:** Unescaped comment content
```html
<!-- Vulnerable comment display -->
<div class="comment-content">{{ comment.content | safe }}</div>
```

### **3. Path Traversal - Document Viewer**
**Location:** `/documents/view`
**Business Context:** Classified document access system
**Vulnerability:** Unsanitized file path parameter
```python
# Vulnerable file access
filepath = request.form.get('document_path')
with open(filepath, 'r') as f:
    content = f.read()
```

### **4. Command Injection - System Diagnostics**
**Location:** `/admin/diagnostics`
**Business Context:** Network monitoring and system health checks
**Vulnerability:** Direct command execution
```python
# Vulnerable ping command
host = request.form.get('target_host')
command = f"ping -c 4 {host}"
subprocess.run(command, shell=True)
```

### **5. XXE - Configuration Upload**
**Location:** `/admin/config/upload`
**Business Context:** System configuration management
**Vulnerability:** XML parser with external entities
```python
# Vulnerable XML parsing
parser = etree.XMLParser(resolve_entities=True, no_network=False)
root = etree.fromstring(xml_data, parser)
```

### **6. File Upload - Document Sharing**
**Location:** `/documents/upload`
**Business Context:** Technical manual and report uploads
**Vulnerability:** No file type validation (malware testing)

### **7. IDOR - Personnel Profiles**
**Location:** `/personnel/profile/{user_id}`
**Business Context:** Employee directory access
**Vulnerability:** Direct object reference without authorization

### **8. Open Redirect - External Links**
**Location:** `/redirect`
**Business Context:** Partner and vendor link redirects
**Vulnerability:** Unvalidated URL redirection

---

## 🎨 Website Design & Layout

### **Homepage Design**
```html
<!-- Hero Section -->
<section class="hero-section bg-military-blue">
    <div class="hero-content">
        <h1>AEGIS Defense Systems</h1>
        <p>Advanced Military Technology Solutions</p>
        <div class="hero-stats">
            <div>50+ Active Contracts</div>
            <div>$2.3B in Defense Projects</div>
            <div>Top Secret Clearance</div>
        </div>
    </div>
</section>

<!-- Recent News -->
<section class="news-section">
    <h2>Latest Defense News</h2>
    <!-- XSS vulnerability in news comments -->
</section>

<!-- Products Overview -->
<section class="products-section">
    <h2>Defense Solutions</h2>
    <!-- Links to product pages -->
</section>
```

### **Color Scheme**
- **Primary:** Military Blue (#1B365D)
- **Secondary:** Steel Gray (#708090)
- **Accent:** Gold (#FFD700)
- **Text:** Dark Gray (#2F2F2F)
- **Background:** Light Gray (#F5F5F5)

### **Typography**
- **Headers:** Roboto Slab (military/technical feel)
- **Body:** Open Sans (readability)
- **Monospace:** Courier New (technical specs)

---

## 📋 Implementation Phases

### **Phase 10.1: Database Schema Migration**
**Timeline:** 2-3 hours
**Tasks:**
- [ ] Create new database tables
- [ ] Migrate existing data to new schema
- [ ] Add military-specific seed data
- [ ] Update database service functions

**Deliverables:**
- Enhanced database schema
- Migration scripts
- Military-themed seed data (employees, projects, documents)

---

### **Phase 10.2: Backend Route Restructuring**
**Timeline:** 4-5 hours
**Tasks:**
- [ ] Rename routes to business-appropriate endpoints
- [ ] Implement personnel portal with dashboard
- [ ] Create news and comments system
- [ ] Add document management system
- [ ] Build system diagnostics interface
- [ ] Enhance contact inquiry system

**New Route Structure:**
```python
# Homepage & Company Info
/ → Company homepage
/about → Company history and leadership
/products → Defense systems catalog
/news → Press releases and announcements
/contact → Business inquiries

# Personnel System (SQL Injection)
/personnel/login → Employee authentication
/personnel/dashboard → Authenticated user dashboard
/personnel/profile/{id} → Employee profiles (IDOR)
/personnel/directory → Staff directory

# Document System (Path Traversal & File Upload)
/documents → Document center
/documents/view → Document viewer (Path traversal)
/documents/upload → Document upload (Malware testing)
/documents/search → Document search

# News System (XSS)
/news/article/{id} → Article with comments (XSS)
/news/submit → Submit news (Admin only)

# Admin System (Command Injection, XXE)
/admin/dashboard → Admin control panel
/admin/diagnostics → System diagnostics (Command injection)
/admin/config → Configuration management (XXE)
/admin/users → User management

# System APIs
/api/search → Search functionality
/api/status → System health
/redirect → External link redirects (Open redirect)
```

---

### **Phase 10.3: Frontend Template Redesign**
**Timeline:** 6-7 hours
**Tasks:**
- [ ] Create military-themed base template
- [ ] Design professional homepage
- [ ] Build personnel dashboard
- [ ] Create document management interface
- [ ] Design news and comments system
- [ ] Build admin control panel
- [ ] Add responsive design

**Template Structure:**
```
templates/
├── base/
│   ├── base.html → Military-themed base template
│   ├── navigation.html → Professional navigation
│   └── footer.html → Company footer
├── public/
│   ├── index.html → Company homepage
│   ├── about.html → Company information
│   ├── products.html → Defense systems
│   ├── news/ → News system templates
│   └── contact.html → Business inquiries
├── personnel/
│   ├── login.html → Employee login
│   ├── dashboard.html → User dashboard
│   ├── profile.html → User profile
│   └── directory.html → Staff directory
├── documents/
│   ├── center.html → Document portal
│   ├── viewer.html → Document viewer
│   └── upload.html → Upload interface
└── admin/
    ├── dashboard.html → Admin panel
    ├── diagnostics.html → System diagnostics
    └── config.html → Configuration management
```

---

### **Phase 10.4: Authentication & Authorization**
**Timeline:** 3-4 hours
**Tasks:**
- [ ] Implement session-based authentication
- [ ] Create role-based access control
- [ ] Build user dashboard functionality
- [ ] Add profile management
- [ ] Implement admin panel

**User Roles:**
- **Guest:** Public pages only
- **Employee:** Personnel portal access
- **Manager:** Document access + team management
- **Admin:** Full system access + diagnostics

---

### **Phase 10.5: Static Assets & Styling**
**Timeline:** 2-3 hours
**Tasks:**
- [ ] Create military-themed CSS
- [ ] Add professional images and icons
- [ ] Implement responsive design
- [ ] Add JavaScript functionality
- [ ] Optimize for mobile devices

**Asset Structure:**
```
static/
├── css/
│   ├── military-theme.css → Main military styling
│   ├── dashboard.css → Dashboard-specific styles
│   └── responsive.css → Mobile responsiveness
├── js/
│   ├── main.js → General functionality
│   ├── dashboard.js → Dashboard interactions
│   └── security.js → Form validation
└── images/
    ├── logo/ → Company logos
    ├── military/ → Military-themed images
    └── icons/ → Professional icons
```

---

### **Phase 10.6: Content & Data Population**
**Timeline:** 2-3 hours
**Tasks:**
- [ ] Create realistic company content
- [ ] Add military project data
- [ ] Generate employee profiles
- [ ] Create news articles
- [ ] Add technical documents

**Content Categories:**
- **Projects:** Radar systems, missile defense, cybersecurity
- **News:** Contract awards, technology announcements
- **Documents:** Technical manuals, specifications, reports
- **Personnel:** Engineers, managers, security staff

---

### **Phase 10.7: Testing & Validation**
**Timeline:** 2-3 hours
**Tasks:**
- [ ] Test all vulnerability integrations
- [ ] Verify business flow authenticity
- [ ] Validate responsive design
- [ ] Test user authentication flows
- [ ] Confirm admin functionality

---

## 🎯 Success Criteria

### **Professional Appearance**
- [ ] Looks like genuine military contractor website
- [ ] Professional color scheme and typography
- [ ] Realistic company content and structure
- [ ] Mobile-responsive design

### **Hidden Vulnerabilities**
- [ ] SQL injection in personnel login (not obvious)
- [ ] XSS in news comments (natural user interaction)
- [ ] Path traversal in document viewer (business function)
- [ ] Command injection in system diagnostics (admin tool)
- [ ] All vulnerabilities serve legitimate business purposes

### **Authentic User Experience**
- [ ] Natural navigation and user flows
- [ ] Realistic business processes
- [ ] Professional content and terminology
- [ ] Proper authentication and authorization

### **Enhanced Testing Capabilities**
- [ ] More realistic attack discovery patterns
- [ ] Better ML training data from natural user behavior
- [ ] Improved NGFW testing scenarios
- [ ] Professional demonstration capabilities

---

## 📊 Estimated Timeline

**Total Implementation Time:** 20-25 hours

| Phase | Duration | Priority |
|-------|----------|----------|
| 10.1 Database Migration | 2-3 hours | High |
| 10.2 Backend Routes | 4-5 hours | High |
| 10.3 Frontend Templates | 6-7 hours | High |
| 10.4 Authentication | 3-4 hours | Medium |
| 10.5 Static Assets | 2-3 hours | Medium |
| 10.6 Content Population | 2-3 hours | Low |
| 10.7 Testing & Validation | 2-3 hours | High |

---

## 🚀 Next Steps

1. **Get User Approval** for the overall plan and design direction
2. **Start with Phase 10.1** - Database schema migration
3. **Implement incrementally** - Each phase builds on the previous
4. **Test continuously** - Ensure vulnerabilities remain functional
5. **Document changes** - Track all modifications for future reference

---

**This plan transforms the basic vulnerability testing site into a sophisticated, professional military defense contractor website where security vulnerabilities are naturally integrated into legitimate business functions, providing a much more realistic testing environment for the NGFW system.**
