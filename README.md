# sb_26-01_Warbler_Twitter_Clone


## Assignment Details
Assignment involved extending functionality in an existing code base of a twitter clone application built with Python, Flask, SQL Alchemy, and Bcrypt. 

**Part 1** involved fixing current features such as 
- implementing logout
- fixing user profile by adding location, bio, and header image
- fixing user cards by showing the bio for the user on the followers, following, and list-user pages
- editing current (logged in) user profile
- fixing the homepage to show up to 100 recent messages from the people the current (logged in) user is following instead of 100 recent messages from everyone.

**Part 2** involved implementing likes of messages. One tweak made is that the a user cannot view another user's liked messages. Ideally, the logged in user should only get to view liked messages of following and follower users.

**Part 3** involved creation of test cases.


- The database name is ```warbler```  
- The test database name is ```warbler_test```


### ENHANCEMENTS
- Messages and error handling especially in user profile updates. 
- The user remains on the page where they liked a message, they are not placed in another part of the application.


### DIFFICULTIES 
- Some of the queries and the realization that straight SQL code just does not translate into SQL Alchemy -- for example, creating a join between ```follows``` and ```messages``` tables because there is no relationship in the models for such a join.
- The change user code could get placed into the models instead of keeping it in apps.py. 
- Understanding where logic should live. How much business logic should exist in a template? For example, preventing a user from liking their own messages was implemented by logic in the ```show.html``` template -- the post form only appears when ```msg.user_id``` is not the same as ```user.id```.


