# sb_26-01_Warbler_Twitter_Clone


## Assignment Details
Assignment involved extending functionality in an existing code base of Warbler, a twitter clone application, built with Python, Flask, and SQL Alchemy. Bcrypt is utilized for password storage. 

**Part 1** involved fixing current features such as 
- implementing logout
- fixing user profile by adding location, bio, and header image
- fixing user cards by showing the bio for the user on the followers, following, and list-user pages
- editing current (logged in) user profile
- fixing the homepage to show up to 100 recent messages from the people the current (logged in) user is following instead of 100 recent messages from everyone.

**Part 2** involved implementing likes of messages. One tweak made is that the a user cannot view another user's liked messages. Ideally, the logged in user should only get to view liked messages of following and follower users.

**Part 3** involved creation of test cases. ```test_message_views.py``` and ```test_user_model.py``` were expanded with test cases. ```test_message_views.py``` has coverage to test the creation of a message (provided), and was expanded to test a followed user adding a message to test the ability to like a message.

```test_user_model.py``` was expanded to test the main functions of the User SQL Alchemy model. A function was added to models.py for changing the user -- the integrity exception checking just did not belong in app.py -- and tests were created to ensure db_change_user functions properly and returns messages for use in ```profile()``` (/users/profile GET/POST route). 

```test_message_model.py``` and ```test_user_views.py``` did not have any tests added to them and were not included in the repository.

- The database name is ```warbler```  
- The test database name is ```warbler_test```


### ENHANCEMENTS
- Messages and error handling especially in user profile updates. 
- The user remains on the page where they liked a message, they are not placed in another part of the application.
- Moving user change logic into models.py. There are other functions that were candidates to move, but it was best not include change-specific logic in the app.py due to error checking. 


### DIFFICULTIES 
- Some of the queries and the realization that straight SQL code just does not translate into SQL Alchemy -- for example, creating a join between ```follows``` and ```messages``` tables because there is no relationship in the models for such a join.
- Understanding where logic should live. How much business logic should exist in a template? For example, preventing a user from liking their own messages was implemented by logic in the ```show.html``` template -- the post form only appears when ```msg.user_id``` is not the same as ```user.id```.



