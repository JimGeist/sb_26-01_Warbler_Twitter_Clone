# sb_24-05-20_Authentication_Authorization_Exercise


## Assignment Details
Assignment involved creation and deletion of users in an authenticated system using Python, Flask, SQL Alchemy, and Bcrypt. One the authentication pieces were working, feedback elements were added where the authenticated user had the ability to create, update, and delete feedback that they created. They should not have the ability to see, edit, or delete another user's feedback. Final piece was deletion of a user and all the feedback they created.

Add, update and delete functions are in model.py. No unittests or doctests,

Flask toolbar debugging statements were included but are commented out.
```sh
# from flask_debugtoolbar import DebugToolbarExtension
    . . . .
# debug = DebugToolbarExtension(app)```
# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
```

- The database name is ```flask_feedback_db```  
- The test database name is ```flask_feedback_test_db```


### ENHANCEMENTS
- Messages and error handling. 


### DIFFICULTIES 
- These assignments would be easier for me if I just dropped error checking. I was making good time until Part 8!


@app.before_request
def add_user_to_g():
Really? This little block of code executes all the time. Isn't there a better way to do this, ONCE?


