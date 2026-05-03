# Kumpas Instructor Dashboard - Setup & Usage Guide

## Overview

The Kumpas instructor dashboard is now fully dynamic and database-driven. All instructor features are connected to the database, allowing real-time management of:

- **Learning Modules**: Create, edit, publish, and manage FSL lessons
- **Student Monitoring**: Track student progress, completion rates, and learning states
- **Announcements**: Post and manage announcements for all students
- **Dashboard Analytics**: View overview statistics of all classes

## Database Setup

### Models Created

The following database models have been created and populated:

1. **User** (Django built-in)
   - Email, password, basic user info

2. **UserProfile** (Custom)
   - Full name, role (student/instructor/admin), year level, security PIN
   - Links to User model

3. **UserLearningState** (Custom)
   - Stores student progress, points, streak, accuracy, module progress
   - Links to User model

4. **LearningModule** (Custom)
   - Module key, title, year level, description, activities count
   - Status: draft, published, or archived
   - Sort order for display
   - Created by/updated by instructor

5. **Announcement** (Custom)
   - Title, message, published status
   - Created by/updated by instructor
   - Timestamps

### Initial Data

The database has been seeded with:

- **8 Learning Modules**: Pre-populated lessons from Year 1 to Year 4
- **3 Announcements**: Sample announcements for testing
- **1 Instructor Account**: Maria Santos (maria@ccnc.edu.ph)
- **3 Student Accounts**: Juan, Ana, and Carlos for testing

### Account Credentials

**Instructor Account:**
- Email: `maria@ccnc.edu.ph`
- Password: `instructor123`
- Role: `Instructor`
- Security PIN: `1234`

**Test Student Accounts:**
- Juan Dela Cruz (juan@student.com / student123) - Year 1
- Ana Martinez (ana@student.com / student123) - Year 2
- Carlos Reyes (carlos@student.com / student123) - Year 3

## Backend API Endpoints

All endpoints require the instructor's email to be passed as a query parameter or in the request body.

### Instructor Endpoints

```
GET  /api/instructor/dashboard/?email=maria@ccnc.edu.ph
     Returns: Dashboard data with summary stats, modules, students, announcements

GET  /api/instructor/modules/?email=maria@ccnc.edu.ph
     Returns: List of all learning modules

POST /api/instructor/modules/?email=maria@ccnc.edu.ph
     Body: { title, year_level, description, activities_count, status, sort_order }
     Returns: Created module

PATCH /api/instructor/modules/<id>/?email=maria@ccnc.edu.ph
     Body: { title, year_level, description, activities_count, status, sort_order }
     Returns: Updated module

DELETE /api/instructor/modules/<id>/?email=maria@ccnc.edu.ph
     Returns: Confirmation message

GET  /api/instructor/announcements/?email=maria@ccnc.edu.ph
     Returns: List of all announcements

POST /api/instructor/announcements/?email=maria@ccnc.edu.ph
     Body: { title, message, is_published }
     Returns: Created announcement

PATCH /api/instructor/announcements/<id>/?email=maria@ccnc.edu.ph
     Body: { title, message, is_published }
     Returns: Updated announcement

DELETE /api/instructor/announcements/<id>/?email=maria@ccnc.edu.ph
     Returns: Confirmation message
```

## Frontend Features

### Dashboard Tabs

1. **Overview**
   - Total Students: Count of all enrolled students
   - Modules Created: Number of learning modules
   - Average Completion: Student average progress percentage
   - Total Announcements: Count of announcements

2. **Manage Modules**
   - View all modules in a table
   - Add new module button
   - Edit/Delete existing modules
   - Shows student count per module

3. **Monitor Students**
   - View student list with progress
   - Year level filter
   - Progress bars
   - View profile button for each student
   - Sort by completion rate and points

4. **Announcements**
   - List all announcements
   - Create new announcement
   - Edit/Delete existing announcements

### Forms

#### Module Management
- Module Title (required)
- Year Level (1-4)
- Activities Count (number)
- Status (Draft, Published, Archived)
- Sort Order (for display ordering)
- Description (textarea)

#### Announcement Management
- Title (required)
- Message (required, textarea)
- Published (checkbox)

## Running the System

### 1. Start Django Development Server

```bash
cd backend
python manage.py runserver 127.0.0.1:8000
```

The API will be available at: `http://127.0.0.1:8000/api`

### 2. Open Frontend

Navigate to:
```
http://localhost:3000/login.html
```

Or directly to instructor dashboard (after login):
```
http://localhost:3000/instructor-dashboard.html
```

### 3. Login Flow

1. Go to login.html
2. Select "Instructor" from role dropdown
3. Enter email: maria@ccnc.edu.ph
4. Enter password: instructor123
5. Enter security PIN: 1234
6. Click Login
7. You'll be redirected to instructor-dashboard.html

## Key Implementation Details

### Authentication
- Email-based authentication
- Role-based access control (RBAC)
- Security PIN required for instructor/admin accounts
- User data stored in localStorage after login

### Database Schema
- All instructor actions (create, update, delete) are tracked with timestamps
- Created_by/updated_by fields track who made changes
- Status fields allow for draft/published/archived workflows

### Frontend Architecture
- Modular JavaScript with async/await for API calls
- Modal dialogs for create/edit operations
- Real-time table updates after operations
- Error handling with user-friendly alerts

### API Communication
- RESTful endpoints with standard HTTP methods
- JSON request/response format
- Email parameter for instructor identification
- 404/403/401 error handling

## Troubleshooting

### "Missing instructor email" Error
- Make sure you're logged in and email is stored in localStorage
- Check that the localStorage key is 'currentUser'

### "Instructor access required" Error
- Verify your account has role set to 'instructor'
- Check security PIN is correct (1234)

### Database Not Found
- Run: `python manage.py migrate`
- Run: `python setup_instructor_db.py`

### API Connection Failed
- Verify Django server is running on 127.0.0.1:8000
- Check kumpasApiBase in localStorage matches your server URL
- Check browser console for CORS errors

## Extending the System

### Adding More Modules
1. Click "+ Add Module" in Manage Modules tab
2. Fill in module details
3. Click "Save Module"

### Creating Announcements
1. Click "+ Create Announcement" in Announcements tab
2. Enter title and message
3. Optionally uncheck "Published" for drafts
4. Click "Save Announcement"

### Tracking Student Progress
- Monitor Students tab shows live progress from database
- Student learning state is stored in UserLearningState model
- Progress calculated from moduleProgress in state JSON

## API Response Examples

### Dashboard Overview
```json
{
  "currentUser": {
    "email": "maria@ccnc.edu.ph",
    "name": "Maria Santos",
    "role": "instructor"
  },
  "summary": {
    "totalStudents": 3,
    "activeStudents": 2,
    "totalModules": 8,
    "publishedModules": 5,
    "totalAnnouncements": 3,
    "averageCompletion": 45,
    "averageAccuracy": 78
  },
  "modules": [...],
  "students": [...],
  "announcements": [...]
}
```

### Module Object
```json
{
  "id": 1,
  "module_key": "lesson1",
  "title": "Lesson 1: Basic Finger Spelling",
  "year_level": "1",
  "description": "Start with the alphabet...",
  "activities_count": 4,
  "status": "published",
  "sort_order": 1,
  "studentCount": 3,
  "created_at": "2026-05-02T10:00:00Z",
  "updated_at": "2026-05-02T10:00:00Z"
}
```

### Student Object
```json
{
  "email": "juan@student.com",
  "name": "Juan Dela Cruz",
  "yearLevel": "1",
  "yearLabel": "1st Year",
  "points": 150,
  "streak": 5,
  "accuracy": 85,
  "modulesCompleted": 2,
  "totalModules": 8,
  "overallProgress": 25,
  "updatedAt": "2026-05-02T14:00:00Z"
}
```

## Security Considerations

1. **Authentication**: Instructors are identified by email and must provide a security PIN
2. **Authorization**: Only users with instructor/admin role can access instructor endpoints
3. **Data Isolation**: Each instructor can manage their own content
4. **Audit Trail**: All changes are tracked with created_by/updated_by fields
5. **Password Security**: Passwords are handled by Django's built-in authentication

## Performance Notes

- Dashboard queries use select_related() for efficient database access
- Module student counts are calculated efficiently using aggregation
- Learning states are cached in memory during dashboard load
- Frontend pagination ready for large student lists (currently shows top 10)

---

For more information or issues, refer to the backend logs or check the browser console for client-side errors.
