\# 🌽 AI-Based Maize Disease Detection System



\## Frontend Developer Guide



\*\*Project:\*\* AI-Based Maize Disease Detection System

\*\*Frontend:\*\* React + Vite

\*\*Backend:\*\* Flask REST API

\*\*Database:\*\* PostgreSQL

\*\*AI:\*\* TensorFlow / MobileNetV2

\*\*Authentication:\*\* JWT

\*\*Target Users:\*\* Farmers, Extension Agents, Administrators

\*\*Languages:\*\* English + Amharic



\---



\# 1. Purpose of This Guide



This document is the official guide for frontend developers working on the AI-Based Maize Disease Detection System.



The goal is to build the React frontend on top of the existing Flask backend without duplicating backend business logic.



The frontend should:



\* Provide a modern, responsive user interface.

\* Communicate with the existing Flask REST API.

\* Support Farmer, Extension Agent, and Admin roles.

\* Support English and Amharic.

\* Support AI maize disease diagnosis.

\* Display diagnosis explanations and advisory information.

\* Support diagnosis history.

\* Support weather and crop-calendar features.

\* Support discussion/community features.

\* Support extension-agent review.

\* Support administrative dashboards.

\* Support offline/PWA functionality.

\* Work well on desktop and mobile devices.



> \*\*Important:\*\* The backend already contains significant business logic. Do not recreate that logic in React.



\---



\# 2. Project Structure



After extracting the project, the main structure is:



```text

AI\_MAIZE\_FRONTEND\_SHARE/

│

├── backend/

│   └── app/

│       ├── models/

│       ├── routes/

│       ├── services/

│       ├── main.py

│       └── extensions.py

│

├── frontend/

│   ├── public/

│   ├── src/

│   ├── package.json

│   ├── package-lock.json

│   └── vite.config.js

│

├── ml\_model/

│   ├── advisor/

│   ├── ai\_service/

│   ├── explainability/

│   ├── inference/

│   └── knowledge\_base/

│

├── database/

├── deployment/

├── docs/

├── tests/

├── README.md

└── requirements.txt

```



The main frontend development work should happen inside:



```text

frontend/

```



\---



\# 3. Important Files and Responsibilities



\## Frontend



```text

frontend/src/

```



This is where the React application should be developed.



The existing project already contains:



```text

App.jsx

App.css

index.css

main.jsx

```



Do not delete the existing files before understanding what they contain.



\---



\## Backend



The Flask backend is located at:



```text

backend/app/

```



Important directories:



```text

backend/app/models/

backend/app/routes/

backend/app/services/

```



The backend already contains API routes for functionality including:



```text

auth

diagnosis

complete diagnosis

advisory

profile

weather

discussion

extension

extension agent

admin

SMS

outbreak alerts

sync

crop calendar

reports

health

```



Before implementing a frontend feature, inspect its corresponding backend route.



\---



\# 4. Important: What Is NOT Included



The shared package intentionally does \*\*not\*\* contain:



```text

.env

venv/

node\_modules/

ml\_model/dataset/

\*.h5

\*.keras

uploads/

logs/

\_\_pycache\_\_/

.pytest\_cache/

```



This is intentional.



Each developer must create their own local Python virtual environment and their own local environment configuration.



\*\*Never request or commit the original `.env` file.\*\*



\---



\# 5. Required Software



Install:



\* Python

\* Node.js

\* npm

\* PostgreSQL

\* Git

\* VS Code or another code editor



Verify the installations:



```cmd

python --version

node --version

npm --version

git --version

psql --version

```



\---



\# 6. Extract the Project



Extract:



```text

AI\_MAIZE\_FRONTEND\_SHARE.zip

```



For example:



```text

D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE

```



After extraction, open CMD in the extracted project directory.



Example:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE

```



> Replace the path with the actual location where you extracted the project.



\---



\# 7. Backend Setup — ACTUAL PROJECT COMMANDS



The backend application is defined in:



```text

backend/app/main.py

```



The application uses a Flask application factory and creates:



```text

app = create\_app()

```



The file also contains the development server configuration:



```text

host = 127.0.0.1

port = 5000

debug = True

```



Therefore, \*\*do not use `flask run` unless the backend developer specifically changes the startup configuration.\*\*



The normal development command for this project is:



```text

python -m backend.app.main

```



\---



\## 7.1 Open Backend Terminal



From the project root:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE

```



If your extracted folder is somewhere else, replace the path.



\---



\## 7.2 Create Python Virtual Environment



Run:



```cmd

python -m venv backend\\venv

```



This creates:



```text

backend/

└── venv/

```



The virtual environment is local to the developer's machine.



It must \*\*not\*\* be committed to Git.



\---



\## 7.3 Activate the Virtual Environment



On Windows CMD:



```cmd

backend\\venv\\Scripts\\activate

```



You should see something similar to:



```text

(venv) D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE>

```



\---



\## 7.4 Upgrade pip



Run:



```cmd

python -m pip install --upgrade pip

```



\---



\## 7.5 Install Backend Dependencies



From the \*\*project root\*\*, run:



```cmd

pip install -r requirements.txt

```



Do not run the command from the wrong directory.



The file is located at:



```text

AI\_MAIZE\_FRONTEND\_SHARE\\requirements.txt

```



\---



\# 8. Backend Environment Configuration



The real `.env` file was deliberately excluded from the shared package.



Before starting the backend, configure the required local environment variables according to:



```text

backend/app/config.py

```



Typical configuration categories include:



```text

DATABASE\_URL

JWT configuration

SMS configuration

Weather API configuration

Other external-service configuration

```



Use placeholder/local development credentials.



\*\*Never put production credentials into the frontend.\*\*



\*\*Never commit `.env` to Git.\*\*



\---



\# 9. PostgreSQL Setup



The backend uses PostgreSQL.



Make sure PostgreSQL is running before starting the Flask backend.



The local database must match the database configuration expected by:



```text

backend/app/config.py

```



The basic architecture is:



```text

PostgreSQL

&#x20;    ↑

&#x20;    │

Flask Backend

&#x20;    ↑

&#x20;    │ HTTP

React Frontend

```



\---



\# 10. Start the Backend — ACTUAL COMMAND



After:



1\. Activating the virtual environment

2\. Installing requirements

3\. Configuring the database/environment



run this \*\*from the project root\*\*:



```cmd

python -m backend.app.main

```



\### Full Windows sequence



For a fresh installation:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE



python -m venv backend\\venv



backend\\venv\\Scripts\\activate



python -m pip install --upgrade pip



pip install -r requirements.txt



python -m backend.app.main

```



\### Expected result



The Flask development server should start on:



```text

http://127.0.0.1:5000

```



The backend's root endpoint is:



```text

http://127.0.0.1:5000/

```



The application itself reports:



```json

{

&#x20; "service": "AI Maize Disease Detection System",

&#x20; "backend": "Flask",

&#x20; "status": "running"

}

```



The backend code explicitly configures the development server for `127.0.0.1:5000`.



\---



\# 11. Do NOT Close the Backend Terminal



Once the backend starts successfully, leave that terminal running.



You should see Flask requests appearing in that terminal while the frontend communicates with the API.



Example:



```text

(venv) D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE>python -m backend.app.main



&#x20;\* Running on http://127.0.0.1:5000

```



\---



\# 12. Test the Backend Before Starting React



Open a browser and visit:



```text

http://127.0.0.1:5000/

```



If the backend is running correctly, you should receive the system status response.



You can also test the health endpoint if the current backend route exposes it.



If the backend does not start, \*\*fix the backend first\*\* before debugging React.



\---



\# 13. Frontend Installation



Open a \*\*second CMD window\*\*.



Go to the frontend:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE\\frontend

```



Install dependencies:



```cmd

npm install

```



The project already includes:



```text

package.json

package-lock.json

```



Do not delete the lockfile unnecessarily.



\---



\# 14. Start React / Vite



From:



```text

frontend/

```



run:



```cmd

npm run dev

```



Vite will display the development URL.



Open that URL in the browser.



Keep this terminal running as well.



\---



\# 15. Two-Terminal Development Setup



During development, use two terminals.



\### Terminal 1 — Flask Backend



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE

backend\\venv\\Scripts\\activate

python -m backend.app.main

```



\### Terminal 2 — React Frontend



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE\\frontend

npm run dev

```



The complete development environment is:



```text

&#x20;                Browser

&#x20;                   │

&#x20;                   ▼

&#x20;            React + Vite

&#x20;                   │

&#x20;            HTTP / JSON

&#x20;                   │

&#x20;                   ▼

&#x20;            Flask Backend

&#x20;            127.0.0.1:5000

&#x20;                   │

&#x20;         ┌─────────┼─────────┐

&#x20;         ▼         ▼         ▼

&#x20;    PostgreSQL    AI       Services

```



\---



\# 16. Frontend ↔ Backend API Configuration



The frontend should communicate with:



```text

http://127.0.0.1:5000

```



during local development.



Do not hard-code the backend URL throughout multiple React components.



Create a centralized API configuration.



Recommended location:



```text

frontend/src/api/client.js

```



The exact API base URL can later be moved into a frontend environment variable.



\---



\# 17. API Client



Create one central Axios client.



Recommended:



```text

frontend/src/api/client.js

```



Its responsibilities should include:



\* API base URL

\* Authorization headers

\* Common request configuration

\* Common response handling

\* Authentication error handling



Avoid putting repeated Axios configuration into every component.



\---



\# 18. API Integration Rule



For every frontend feature:



```text

1\. Find the backend route

&#x20;       ↓

2\. Read its HTTP method

&#x20;       ↓

3\. Read its request format

&#x20;       ↓

4\. Read its response format

&#x20;       ↓

5\. Create frontend API function

&#x20;       ↓

6\. Test API

&#x20;       ↓

7\. Build React UI

&#x20;       ↓

8\. Connect UI

&#x20;       ↓

9\. Test complete workflow

```



Do not invent API responses.



\---



\# 19. Backend Startup Troubleshooting



\## Problem: `ModuleNotFoundError: No module named 'backend'`



Make sure you are running the command from the \*\*project root\*\*, not from inside `backend`.



Correct:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE

python -m backend.app.main

```



Incorrect:



```cmd

cd backend

python -m backend.app.main

```



The module command should be executed from the directory containing:



```text

backend/

frontend/

ml\_model/

requirements.txt

```



\---



\## Problem: `python` is not recognized



Check:



```cmd

python --version

```



If that fails, install/configure Python and ensure it is available in PATH.



\---



\## Problem: Package/module missing



Make sure the virtual environment is active:



```cmd

backend\\venv\\Scripts\\activate

```



Then:



```cmd

pip install -r requirements.txt

```



\---



\## Problem: PostgreSQL connection error



Check:



```text

PostgreSQL running?

Database exists?

DATABASE\_URL correct?

Username correct?

Password correct?

Port correct?

```



Do not modify frontend code to solve a database connection problem.



\---



\## Problem: Backend starts but AI diagnosis fails



Check the backend terminal first.



The diagnosis service loads the AI functionality lazily when diagnosis is requested.



A frontend error does not necessarily mean the React code is wrong.



\---



\# 20. Authentication



The system uses JWT authentication.



Frontend responsibilities:



1\. Login/register.

2\. Receive authentication response.

3\. Maintain authenticated state.

4\. Send authorization information with protected API requests.

5\. Load the current user.

6\. Protect frontend routes.

7\. Determine the user's role.

8\. Display the correct dashboard.

9\. Handle expired/invalid authentication.



Do not create a second authentication system.



\---



\# 21. User Roles



The system supports:



```text

farmer

extension\_agent

admin

```



Frontend navigation should respect the authenticated user's role.



\---



\# 22. Farmer Dashboard



The farmer dashboard should provide:



```text

Dashboard

├── Diagnose Disease

├── Diagnosis History

├── Advisory

├── Weather

├── Crop Calendar

├── Discussion

├── Profile

└── Settings

```



\---



\# 23. AI Disease Diagnosis



The diagnosis workflow should be:



```text

Select/capture image

&#x20;       ↓

Preview image

&#x20;       ↓

Validate image

&#x20;       ↓

Upload

&#x20;       ↓

Show loading state

&#x20;       ↓

Backend AI diagnosis

&#x20;       ↓

Display result

&#x20;       ↓

Display explanation/Grad-CAM

&#x20;       ↓

Display advisory

&#x20;       ↓

Save/view history

```



The frontend should use the existing backend diagnosis API.



The backend contains the actual AI diagnosis integration.



Do not implement disease classification again inside React.



\---



\# 24. Diagnosis Result



Display information supplied by the backend, such as:



```text

Disease

Confidence

Image

Explanation

Grad-CAM

Symptoms

Advisory

Recommended action

```



Do not hard-code disease recommendations if the backend already provides them.



\---



\# 25. Diagnosis History



The history page should display previous diagnoses.



Possible information:



```text

Date

Disease

Confidence

Image

Status

Advisory

```



Use the backend API as the source of truth.



\---



\# 26. Farmer Profile



The profile page should use the existing profile API.



Possible fields include:



```text

Full name

Preferred language

Region

Woreda

Kebele

Location

SMS preference

```



Do not create a separate browser-only profile database.



\---



\# 27. Advisory



The advisory interface should display backend-generated recommendations.



Possible sections:



```text

Disease

Symptoms

Treatment

Prevention

Field management

Additional advice

```



The backend knowledge/advisory system remains the source of truth.



\---



\# 28. Weather



Use the existing weather API.



Possible UI:



```text

Temperature

Weather condition

Humidity

Rainfall

Wind

Location

```



Use the actual response fields from the backend.



\---



\# 29. Crop Calendar



Provide an easy-to-understand crop calendar.



Possible presentation:



```text

Planting

&#x20;  ↓

Growing

&#x20;  ↓

Disease monitoring

&#x20;  ↓

Harvest

```



Use the existing backend functionality.



\---



\# 30. Discussion



Build:



```text

Discussion

├── Posts

├── Create Post

├── Post Details

└── Replies

```



Use the backend discussion routes.



\---



\# 31. Extension Agent Interface



Build:



```text

Extension Dashboard

├── Farmer Diagnoses

├── Review Diagnosis

├── Verify/Review

├── Comments

└── Notifications

```



Use the existing extension-agent API.



\---



\# 32. Admin Interface



Build:



```text

Admin Dashboard

├── Users

├── Farmers

├── Extension Agents

├── Disease Statistics

├── Geographic Information

├── Outbreak Alerts

└── Reports

```



Use backend-provided data.



\---



\# 33. English and Amharic



The application should support:



```text

English

Amharic

```



Use a centralized language system rather than duplicating pages.



Handle:



\* Buttons

\* Forms

\* Validation messages

\* Errors

\* Navigation

\* Dashboard labels

\* Diagnosis information

\* Advisory content

\* Empty states



\---



\# 34. Mobile-First Design



Prioritize:



```text

Mobile

↓

Tablet

↓

Desktop

```



Important mobile screens include:



```text

Login

Register

Dashboard

Diagnosis

Image upload

Diagnosis result

Advisory

History

Profile

Discussion

```



\---



\# 35. Offline / PWA



Implement offline functionality \*\*after the online application is stable\*\*.



The intended flow is:



```text

Online

&#x20; ↓

Normal operation

&#x20; ↓

Connection lost

&#x20; ↓

Local queue

&#x20; ↓

Connection restored

&#x20; ↓

Synchronization

&#x20; ↓

Backend

```



Follow the existing backend synchronization contract.



Do not invent a separate synchronization protocol.



\---



\# 36. Recommended React Structure



Gradually organize the frontend as:



```text

frontend/src/

│

├── api/

│   ├── client.js

│   ├── authApi.js

│   ├── diagnosisApi.js

│   ├── profileApi.js

│   ├── advisoryApi.js

│   ├── weatherApi.js

│   ├── discussionApi.js

│   ├── extensionApi.js

│   └── adminApi.js

│

├── components/

│   ├── common/

│   ├── layout/

│   ├── forms/

│   ├── diagnosis/

│   └── dashboard/

│

├── pages/

│   ├── auth/

│   ├── farmer/

│   ├── extension/

│   └── admin/

│

├── context/

│   ├── AuthContext.jsx

│   └── LanguageContext.jsx

│

├── hooks/

├── utils/

├── assets/

│

├── App.jsx

├── App.css

├── index.css

└── main.jsx

```



\---



\# 37. Implementation Order



Follow this order:



```text

PHASE 1

Foundation

&#x20;  ↓

PHASE 2

Authentication

&#x20;  ↓

PHASE 3

Farmer Dashboard

&#x20;  ↓

PHASE 4

AI Diagnosis

&#x20;  ↓

PHASE 5

Diagnosis History

&#x20;  ↓

PHASE 6

Advisory / Weather / Crop Calendar

&#x20;  ↓

PHASE 7

Discussion

&#x20;  ↓

PHASE 8

Extension Agent

&#x20;  ↓

PHASE 9

Admin

&#x20;  ↓

PHASE 10

Offline / PWA

&#x20;  ↓

PHASE 11

Full Testing

&#x20;  ↓

PHASE 12

Production Build

```



\---



\# 38. Important Development Rules



\### Rule 1



Do not duplicate backend business logic.



\### Rule 2



Do not hard-code API responses.



\### Rule 3



Never put secrets in React.



\### Rule 4



Never commit `.env`.



\### Rule 5



Never commit `node\_modules`.



\### Rule 6



Do not unnecessarily modify backend logic.



\### Rule 7



Inspect the backend route before implementing the frontend API call.



\### Rule 8



Use reusable React components.



\### Rule 9



Implement loading, error, and empty states.



\### Rule 10



Test each feature before moving to the next.



\---



\# 39. Git Collaboration



Use feature branches.



Example:



```text

main

│

├── frontend/auth

├── frontend/diagnosis

├── frontend/profile

├── frontend/discussion

├── frontend/extension

└── frontend/admin

```



Before starting:



```cmd

git pull

```



After completing a feature:



```cmd

git status

git add .

git commit -m "Implement farmer diagnosis UI"

git push

```



Do not commit:



```text

.env

venv/

node\_modules/

uploads/

logs/

```



\---



\# 40. Testing



Test each feature completely.



\## Authentication



```text

□ Registration

□ Login

□ Logout

□ Invalid credentials

□ Protected routes

□ Invalid/expired token

```



\## Diagnosis



```text

□ Image selection

□ Image preview

□ Image validation

□ Upload

□ Loading state

□ Successful diagnosis

□ Failed diagnosis

□ Grad-CAM

□ Advisory

```



\## Profile



```text

□ Load profile

□ Edit profile

□ Save profile

□ Validation

□ Error handling

```



\## Discussion



```text

□ Load posts

□ Create post

□ View post

□ Reply

□ Error handling

```



\## Roles



```text

□ Farmer

□ Extension Agent

□ Admin

```



\---



\# 41. Production Build



When the frontend is ready:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE\\frontend

npm run build

```



Before deployment, verify:



```text

□ API URL is correct

□ No localhost dependency remains

□ No secrets exposed

□ Build succeeds

□ Mobile UI works

□ Authentication works

□ Diagnosis works

□ Browser console is clean

```



\---



\# 42. Backend + Frontend Quick Start



For a developer who has already configured PostgreSQL and the environment:



\## Terminal 1 — Backend



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE



backend\\venv\\Scripts\\activate



python -m backend.app.main

```



Backend:



```text

http://127.0.0.1:5000

```



\## Terminal 2 — Frontend



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE\\frontend



npm install



npm run dev

```



Then open the Vite URL shown in the terminal.



\---



\# 43. Backend Startup — Short Version



Whenever the backend needs to be started again:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE

backend\\venv\\Scripts\\activate

python -m backend.app.main

```



Whenever the frontend needs to be started:



```cmd

cd /d D:\\Projects\\AI\_MAIZE\_FRONTEND\_SHARE\\frontend

npm run dev

```



Keep both terminals running during development.



\---



\# 44. Troubleshooting



\## Frontend cannot connect to backend



Check:



```text

Backend running?

Correct URL?

Correct port 5000?

CORS?

Browser Network tab?

```



\---



\## 401 Unauthorized



Check:



```text

Login successful?

JWT available?

Authorization header sent?

Token expired?

```



\---



\## 404 Not Found



Do not guess the API URL.



Inspect:



```text

backend/app/routes/

```



and confirm the actual route.



\---



\## 500 Server Error



Check the Flask terminal first.



The frontend should display a friendly error, while the developer investigates the backend terminal.



\---



\# 45. Definition of Done



A feature is complete when:



```text

□ UI implemented

□ API connected

□ Mobile responsive

□ Loading state

□ Error state

□ Empty state

□ Authentication handled

□ Role permissions respected

□ English implemented

□ Amharic implemented where applicable

□ API tested

□ Browser tested

□ No console errors

□ Existing functionality still works

```



\---



\# 46. Final Architecture



```text

&#x20;                        🌽 AI MAIZE SYSTEM



&#x20;                             Browser

&#x20;                                │

&#x20;                                ▼

&#x20;                        React + Vite / PWA

&#x20;                                │

&#x20;                          HTTP / JSON

&#x20;                                │

&#x20;                                ▼

&#x20;                        Flask REST API

&#x20;                      127.0.0.1:5000

&#x20;                                │

&#x20;             ┌──────────────────┼──────────────────┐

&#x20;             │                  │                  │

&#x20;             ▼                  ▼                  ▼

&#x20;        PostgreSQL          AI Services       Other Services

&#x20;                                 │

&#x20;                          MobileNetV2

&#x20;                          Grad-CAM

&#x20;                          Advisory

&#x20;                                 │

&#x20;             ┌──────────────────┼──────────────────┐

&#x20;             │                  │                  │

&#x20;             ▼                  ▼                  ▼

&#x20;          Farmer          Extension Agent       Admin

```



\---



\# 47. Golden Rule



The frontend is the \*\*presentation and interaction layer\*\*.



The backend is responsible for:



```text

Authentication

Authorization

Business logic

Database operations

AI inference

Advisory logic

Weather integration

SMS

Outbreak detection

Synchronization

```



The frontend is responsible for:



```text

UI

User interaction

Navigation

Forms

API communication

Loading states

Error states

Responsive design

Accessibility

Visualization

Offline UI

```



Keep these responsibilities separated.



\---



\# 48. Final Developer Checklist



```text

□ Project extracted

□ Python installed

□ Node.js installed

□ PostgreSQL installed/running

□ Backend virtual environment created

□ Backend dependencies installed

□ Environment variables configured

□ Backend starts with:

&#x20;   python -m backend.app.main



□ Backend responds on:

&#x20;   http://127.0.0.1:5000



□ Frontend dependencies installed

□ Frontend starts with:

&#x20;   npm run dev



□ Authentication works

□ Farmer dashboard works

□ Farmer profile works

□ AI diagnosis works

□ Diagnosis result works

□ Grad-CAM displays

□ Advisory displays

□ Diagnosis history works

□ Weather works

□ Crop calendar works

□ Discussion works

□ Extension dashboard works

□ Admin dashboard works

□ English works

□ Amharic works

□ Mobile layout works

□ Offline/PWA works

□ Synchronization works

□ Error handling works

□ Loading states work

□ No secrets committed

□ No node\_modules committed

□ Production build succeeds

```



\---



\# 49. Final Message to the Frontend Team



Welcome to the AI-Based Maize Disease Detection System.



The backend and AI components already provide important functionality. Your responsibility is to turn those capabilities into a modern, accessible, responsive, bilingual React application.



Work feature by feature.



Before implementing a feature:



```text

Understand the backend

&#x20;       ↓

Understand the API

&#x20;       ↓

Build the API client

&#x20;       ↓

Build the UI

&#x20;       ↓

Connect the UI

&#x20;       ↓

Test

&#x20;       ↓

Commit

```



Do not build large amounts of fake data or disconnected screens.



The most important rule is:



> \*\*Do not duplicate existing backend logic. Build the frontend around the APIs that already exist.\*\*



🌽 \*\*Build carefully. Test continuously. Keep the architecture clean.\*\*



\---



\*\*AI-Based Maize Disease Detection System\*\*

\*\*Frontend Development Guide\*\*



