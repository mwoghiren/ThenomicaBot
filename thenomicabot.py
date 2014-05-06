import praw, re, requests, time

##########
# Colors #
##########

BLUE = '\033[94m'
RED = '\033[91m'
END_COLOR = '\033[0m'

#############
# Variables #
#############

credentials_file_name = 'credentials.txt'
user_agent = ''
bot_name = ''
r = ''
subreddit = ''

# This is used to determine just how much [Prop] checking should be done.
# Higher levels do the work indicated *and* all the work before it.
# 0: Check [Prop]s for ballots.
# 1: Check [Prop]s for vote completion.
prop_check_level = 0;

# This is the number of new posts to get from the subreddit, for each [Prop] check level.
prop_check_limit = [5, 50]

#############
# Functions #
#############

###
# Logging In
###

def login():
  # Declare global variables.
  global user_agent
  global bot_name
  global r
  global subreddit

  # Read the credentials from a file.
  print "  Reading credentials..."
  f = open(credentials_file_name, 'r')
  user_agent = f.readline().strip()
  bot_name = f.readline().strip()
  bot_password = f.readline().strip()

  # Get a Reddit object.
  print "  Accessing Reddit..."
  r = praw.Reddit(user_agent=user_agent)

  # Get the subreddit.
  print "  Accessing the appropriate subreddit..."
  subreddit_name = f.readline().strip()
  f.close()
  subreddit = r.get_subreddit(subreddit_name)

  # Log in!
  print "  Logging in..."
  r.login(bot_name, bot_password)

  # All done!
  print "  Done."

###
# Check-In Posts
###

def create_checkin_post(checkin_number, date):
  # Create the submission.
  print "  Creating the submission..."
  round_number = 1
  title = '[Check-In] #' + str(round_number) + '.' + str(checkin_number) + ': ' + date
  text = "Please add a top-level comment to this post to avoid becoming idle."
  submission = subreddit.submit(title, text)

  # Distinguish the submission.
  print "  Distinguishing submission..."
  submission.distinguish()

  # All done!
  print "  Done."

def check_if_checkin_required():
  # Check-ins are created on Mondays and Thursdays.
  print "  Checking the date..."
  day = time.strftime('%A')
  if day != 'Monday' and day != 'Thursday':
    print "  No check-in required today."
    return

  # Check the date of the most recent check-in thread.
  print "  Checking the date of the most recent check-in..."
  submissions = subreddit.get_new()
  for submission in submissions:
    if submission.title.startswith('[Check-In'):
      # We've found the latest check-in post.  Check its date.
      last_checkin_date = re.search('\d\d\d\d-\d\d-\d\d', submission.title).group(0)
      current_date = time.strftime('%Y-%m-%d')
      if last_checkin_date != current_date:
        # We need to check in!  Determine the next number and create the post.
        print BLUE + "  We need to check in!  Creating new check-in post..." + END_COLOR
        next_checkin_number = int(re.search('\d+:', submission.title).group(0)[:-1]) + 1
        create_checkin_post(next_checkin_number, current_date)
      else:
        # There's already a check-in post for today.
        print "  A check-in post for today already exists."
      return

  print BLUE + "  No check-in posts exist.  Creating new check-in post..." + END_COLOR
  current_date = time.strftime('%Y-%m-%d')
  create_checkin_post(1, current_date)

###
# Balloting
###

def create_ballot(submission):
  # Add a ballot comment.
  print "  Balloting..."
  ballot = submission.add_comment('Ballot')

  # Distinguish the ballot comment.
  print "  Distinguishing ballot..."
  ballot.distinguish()

  # Set the flair on the comment.
  print "  Setting flair..."
  submission.set_flair(flair_text='Pending', flair_css_class='voting')

  # All done!
  print "  Done."

def check_for_ballot_completion(submission, ballot):
  # Not implemented!
  pass

# Check if the post has been edited
def is_ballot_valid(submission):

  # Edited posts are invalid
  return not submission.edited

# Invalidate posts
def invalidate_post(submission):

  print RED + "  Marked invalid!"

  submission.set_flair( flair_text='Invalid', flair_css_class='voting')

  print "  Telling players..."
  
  submission.add_comment('Prop was edited and marked invalid')

def is_post_marked_invalid(submission):

  return submission.link_flair_text == 'Invalid'

def locate_ballot(submission):
  # Check the top-level comments for a ballot.
  comments = submission.comments
  ballot = ""
  for comment in comments:
    if comment.body == 'Ballot':
      ballot = comment
      break

  # If we didn't find a ballot, add one.
  # If we did, and the [Prop] check level allows, check if voting has closed.
  if ballot == "":
    print BLUE + "Found unballoted post: \"" + submission.title + "\".  Balloting." + END_COLOR
    create_ballot(submission)
  else:
    if prop_check_level == 1:
      check_for_ballot_completion(submission, ballot)

def check_prop_posts():
  current_limit = prop_check_limit[prop_check_level]
  submissions = subreddit.get_new(limit=current_limit)
  for submission in submissions:
    if submission.title.startswith('[Prop]') and not is_post_marked_invalid(submission):

      # Check for edited (aka invalid) props
      if is_ballot_valid(submission):
        invalidate_post(submission)
        continue
      
      # Locate the ballot.
      locate_ballot(submission)

########
# Main #
########

# First off, log in.
print "Logging in..."
login()

# We check whether we need a new check-in post in two cases:
# (1) The bot has just started up.
# (2) The day of the week has changed.

# Here's case (1): the bot has just started up.
print "Checking if a [Check-In] post is required..."
check_if_checkin_required()

# Now, we track the current day of the week.
current_day = time.strftime('%A')

# This counter is used to manipulate the [Prop] check level.
prop_check_counter = 0

while True:
  try:
    # If the day has changed, check whether we need a new check-in post.
    if current_day != time.strftime('%A'):
      print "It's a new day!  Checking if a [Check-In] post is required."
      current_day = time.strftime('%A')
      check_if_checkin_required()

    # Update the [Prop] check level.
    # Every six iterations, we use [Prop] check level 1.
    prop_check_counter += 1
    if prop_check_counter == 6:
      prop_check_counter = 0
      prop_check_level = 1
    else:
      prop_check_level = 0

    # Check [Prop] posts for ballots and completion.
    check_prop_posts()
  except requests.exceptions.HTTPError as e:
    # We've encountered a problem.  Log it and keep going.
    print RED + "Encountered a " + str(e.response.status_code) + " error.  Continuing." + END_COLOR
  except requests.exceptions.ConnectionError as e:
    # We've encountered a problem.  Log it and keep going.
    print RED + "Encountered a connection error.  Continuing." + END_COLOR


  # Only check every ten seconds.
  time.sleep(10)

