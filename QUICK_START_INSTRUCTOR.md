# 🎓 Instructor Dashboard - Quick Start

## Getting Started (30 seconds)

### 1. Start the Backend Server
```bash
cd backend
python manage.py runserver 127.0.0.1:8000
```

### 2. Login to Instructor Dashboard
```
URL: http://localhost:3000/login.html

Email: maria@ccnc.edu.ph
Password: instructor123
Role: Instructor
Security PIN: 1234
```

### 3. You're In!
After login, you'll see the instructor dashboard with 4 main sections:
- 📊 Overview (stats)
- 📚 Manage Modules  
- 👥 Monitor Students
- 📢 Announcements

---

## What You Can Do

### 📚 Manage Learning Modules
**Create a new module:**
1. Click "Manage Modules" tab
2. Click "+ Add Module" button
3. Fill in the form:
   - Module Title (required)
   - Year Level (1-4)
   - Activities Count (how many activities)
   - Status (Draft/Published/Archived)
   - Sort Order (display order)
   - Description
4. Click "Save Module"

**Edit/Delete modules:**
- Click "Edit" to modify
- Click "Delete" to remove

### 👥 Monitor Student Progress
**View student stats:**
1. Click "Monitor Students" tab
2. See all students with:
   - Overall progress percentage
   - Modules completed
   - Accuracy score
   - Points earned

**View student profile:**
- Click "View Profile" button next to any student

### 📢 Create Announcements
**Post an announcement:**
1. Click "Announcements" tab
2. Click "+ Create Announcement"
3. Enter:
   - Title (required)
   - Message (required)
   - Check "Published" to show immediately
4. Click "Save Announcement"

**Edit/Delete announcements:**
- Click "Edit" to modify
- Click "Delete" to remove

### 📊 View Overview Stats
**Dashboard overview shows:**
- Total Students enrolled
- Modules you've created
- Average student completion rate
- Total announcements

---

## Database Tables (What's Being Stored)

| Table | Purpose | Created By |
|-------|---------|------------|
| auth_user | User login info | Django |
| signtext_userprofile | User role, name, PIN | signtext app |
| signtext_learningmodule | All FSL lessons/modules | Instructors |
| signtext_announcement | Messages to students | Instructors |
| signtext_userlearningstate | Student progress data | System |

---

## Test Accounts

### Instructor
- Email: maria@ccnc.edu.ph
- Password: instructor123
- PIN: 1234

### Students (for testing)
- juan@student.com / student123 (Year 1)
- ana@student.com / student123 (Year 2)  
- carlos@student.com / student123 (Year 3)

---

## Pre-Loaded Data

✅ **8 Learning Modules** (ready to use/edit)
- Lesson 1-3: Year 1
- Lesson 4-5: Year 2
- Lesson 6-7: Year 3
- Lesson 8: Year 4

✅ **3 Sample Announcements** (ready to edit/delete)

✅ **3 Test Students** (with sample data)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't log in | Use email: maria@ccnc.edu.ph, PIN: 1234 |
| Page shows "Not found" | Start Django server: `python manage.py runserver` |
| No modules appear | Refresh the page or check browser console |
| Can't save changes | Check if Django server is running |

---

## Technical Stack

- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Backend**: Django + Django REST Framework
- **Database**: SQLite (default)
- **API**: RESTful endpoints with JSON

---

## API Endpoints (Advanced)

```bash
# Get dashboard data
GET http://127.0.0.1:8000/api/instructor/dashboard/?email=maria@ccnc.edu.ph

# Get all modules
GET http://127.0.0.1:8000/api/instructor/modules/?email=maria@ccnc.edu.ph

# Create module
POST http://127.0.0.1:8000/api/instructor/modules/?email=maria@ccnc.edu.ph

# Update module
PATCH http://127.0.0.1:8000/api/instructor/modules/1/?email=maria@ccnc.edu.ph

# Delete module
DELETE http://127.0.0.1:8000/api/instructor/modules/1/?email=maria@ccnc.edu.ph

# Announcements (same pattern)
GET /api/instructor/announcements/?email=maria@ccnc.edu.ph
POST /api/instructor/announcements/?email=maria@ccnc.edu.ph
PATCH /api/instructor/announcements/1/?email=maria@ccnc.edu.ph
DELETE /api/instructor/announcements/1/?email=maria@ccnc.edu.ph
```

---

## Features Currently Live ✅

✅ Dynamic module management (CRUD)
✅ Student progress monitoring  
✅ Announcement management (CRUD)
✅ Dashboard analytics
✅ Database persistence
✅ Email-based authentication
✅ Security PIN for instructors
✅ Role-based access control

---

## Next Steps

1. **Customize test data**: Edit modules and announcements
2. **Create more modules**: Add your own FSL lessons
3. **Add students**: Register new student accounts
4. **Monitor progress**: Track how students interact with modules
5. **Post announcements**: Keep students updated

---

**Ready to go!** 🚀

Everything is database-driven and ready to use. Start the server and log in with the provided credentials.
