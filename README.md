# Water Tracker
#### Video Demo:  <https://youtu.be/UY_QCNrZzwU>
#### Description:
A website that helps user keep track of their water intake. Starts by creating an account as per login and registration.
Login and registration makes use of sqlite3 and werkzeug hash generator and check to safely store username and encrypted password. For login page, client-side and server side checks have been put in place using html, flask, jinja to make sure
user does not leave fields empty, do not input wrong username, and wrong password. Once user successfully logs in, user information including, goals, user id, current amount of water, will be stored in flask's session. User will be checked by @login_required to ensure user id exists before being able to be redirected to the homepage.

The website follows a general design of a navbar at the top of the viewport, which provides a directory for the user to navigate to other parts of the website. However, certain webpages can only be accessed after user has passed the @login_required decorator which checks the session for the user_id.

The registration page follows a similar design to the login page, but contains an additional field to confirm the user has input identical password. Server side and client sides are also put in place to ensure security. Once checks are cleared, user will automatically log in to the website, and user information is stored in sessions. User does not need to go back to the login page to key in their information again.

 New users will be directed automatically to goal setting to set a daily goal, whereas users that already have a goal will be directed to the home page. This is done by a decorator called @goal_required, which checks to see if the flask session has stored a goal key of which should be created from 'user' database once the user has logged in. New users will have NULL as their goal and the decorator detects this and redirects user to the goal page to set a goal.

 Goals are set based on weight, activity level and age. The formula is (weight * base per kg) * activity level * age.
 The base per kg follows 35ml per kg,  the activity and age level is stored in a dictionary with numbers 1 - 5 as key. After obtaining a POST request from the goal webpage upon button submission, the choices  return values 1 - 5 accordingly and these values will be used to obtain the values stored in the dictionary keys. This allows the goal calculation to be made. The final goal value will be stored in flask sessions and user will be redirected to the index page, after clearing both the @login_required and @goal_required checks.  Goal value will be stored in the 'user' database such that next time the same user logs in,  the goal information will automatically be stored in flask session upon successful login.

The index page allows user to see their progress for the day in the form of a 'glass' of water as well as a progress checker beneath it. Below these are three buttons that allows user to fill their daily glass by +250 ml, +500ml and even be able to reset their progress. Upon clicking these buttons, the js script sends a fetch request of POST method to their respective routes in app.py in order to update the database of the change in the water amount per day. This allows the user to close the website and come back later to see that their progress has not been lost.

The history page displays the user's progress for the past month up till the current day. It follows a similar UI as the homepage, where the user will see a calendar of glasses, each filled with water according to their progress for that respective day.  The information is managed by a function defined in helpers.py and called in app.py. This function deletes information before a month ago and ensures that the days between last month and the current day are added into the database. This is done using pythons datetime and dateutil library, namely datetime, timedelta and relativedelta

## Prerequisites

Before running this project, make sure you have the following installed:

- [Python 3.10+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)
- [Flask](https://flask.palletsprojects.com/)
- Git (for cloning the repository)

---

## Installation

1. **Fork** this repository and **clone** it to your local machine:
   ```bash
   git clone https://github.com/mdh-danial/water_tracker.git
   cd water_tracker
   pip install -r requirements.txt
   flask run
   ```
2. then click on the link -http://127.0.0.1:5000-
   

