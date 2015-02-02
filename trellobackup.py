import sys
import logging
import json
import urllib2
import os
import datetime


# Configuration
# Create a file called config.py or set below
try:
    from config import *
except:
    TRELLO_API_KEY=""
    TRELLO_API_SECRET=""
    TRELLO_API_APP_TOKEN=""
    LOG_FILE="trellobackup.log"
    LOG_LEVEL="debug"
    SAVE_LOCATION="."

# For use with logging
LEVELS={"debug":logging.DEBUG,
        "info":logging.INFO,
        "warning":logging.WARNING,
        "error":logging.ERROR,
        "critical":logging.CRITICAL
        }

def main():
    """Main entry point for script."""
    # Initialise logging
    logging.basicConfig(filename=LOG_FILE, level=LEVELS.get(LOG_LEVEL, logging.NOTSET))
    logging.debug("Initialised logging - filname: %s - level: %s" % (LOG_FILE,LOG_LEVEL))

    #TODO: Test connectivity first
    #Get current datetime and format
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    # Get all organisations
    orgs = dict_of_orgs()
    logging.debug("Compiled list of orgs - %s" % orgs)
    # Get all standard boards
    boards = list_of_boards()
    logging.debug("Compiled list of standard Non-Org boards - %s" % boards)
    # Loop over all organisations appending boards to master dictionary
    for org in orgs.keys():
        #Append all org based boards to master board dictionary
        boards = boards + list_of_boards(org)
    logging.debug("Appended org boards to list of boards - %s" % boards)

    # Add a blank org for "None" lookups
    orgs[None] = "No Org"
    logging.debug("Appended None lookup to orgs - %s" % orgs)

    # Loop over all boards
    for board in boards:
        logging.debug("Working on board data - %s" % board)

        # Create directory structure
        path = "/".join([SAVE_LOCATION,timestamp,sanitise_filename(orgs[board["org_id"]]),sanitise_filename(board["name"])])
        logging.debug("Attempting to create path - %s" % path)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                logging.debug("Created path - %s" % path)
            except:
                #TODO: Capture detailed exceptions and log them
                logging.debug("Error creating path - %s" % path)
        else:
            # Path is reporting as already existing
            logging.debug("Path already exists - %s" % path)


        # Create and sanitise filename
        filename = "%s - %s - %s.json" % (str(orgs[board["org_id"]]), board["id"] , board["name"])
        logging.debug("Filename before sanitising - %s" % filename)
        filename = sanitise_filename(filename)
        logging.debug("Filename after sanitising - %s" % filename)

        # Download board json to file and also store in board_data for parsing
        logging.debug("Attempting to download board data - %s" % board)
        board_data = save_return_board_data(board["id"], "/".join([path,filename]))
        logging.debug("Downloaded board to - %s" % "/".join([path,filename]))

        #Download attachments - naming convention attachmentID - originalfilename
        dict_attachments = dict_of_attachments(board_data)
        for attachment in dict_attachments:
            filename = sanitise_filename("%s - %s" % (attachment, dict_attachments[attachment]["name"]))
            save_url_to_file(dict_attachments[attachment]["url"],"/".join([path,filename]))
        

def generate_token():
    """generate an application token to use with this script"""
    pass

def sanitise_filename(filename):
    """takes a string and returns it as a safe filename"""
    return "".join(x for x in filename if (x.isalnum() or x in "_-. ")) 
    

def get_url(url):
    """fetch a URL, return as a string"""
    response = urllib2.urlopen(url)
    return response.read()

def dict_of_orgs():
    """returns a dictionary of all your trello organisations"""
    orgs_dict = {}
    logging.debug("Attempting to compile list of organisations")
    org_data = json.loads(get_url("https://api.trello.com/1/members/me/organizations?key=%s&token=%s" % (TRELLO_API_KEY,TRELLO_API_APP_TOKEN)))
    logging.debug("org data - %s" % org_data)
    for org in org_data:
        orgs_dict[org["id"]] = org["displayName"]
    return orgs_dict

def list_of_boards(org_id=None):
    """returns a dictionary of boards and their IDs.
    If no org_id provided returns standard orgs"""
    boards_list = []
    if org_id:
        logging.debug("Attempting to get boards (orgs)")
        board_data = json.loads(get_url("https://api.trello.com/1/organizations/%s/boards?key=%s&token=%s" % (org_id,TRELLO_API_KEY,TRELLO_API_APP_TOKEN)))
    else:
        logging.debug("Attempting to get boards (non-orgs)")
        board_data = json.loads(get_url("https://api.trello.com/1/members/me/boards?key=%s&token=%s" % (TRELLO_API_KEY,TRELLO_API_APP_TOKEN)))
    logging.debug("Board data - %s" % board_data)
    for board in board_data:
        #TODO: If inc_closed == false then check if board is closed and ignore if so.
        boards_list.append({"id":board["id"],"name":board["name"],"org_id":board["idOrganization"]})
    return boards_list

def save_return_board_data(board_id,savefile=""):
    """Save the board data, return the complete json data of a board given the id"""
    return save_url_to_file("https://api.trello.com/1/boards/%s?actions=all&actions_limit=1000&cards=all&lists=all&members=all&member_fields=all&checklists=all&fields=all&key=%s&token=%s" % (board_id,TRELLO_API_KEY,TRELLO_API_APP_TOKEN), savefile, return_data = True)

def save_url_to_file(url,savefile,return_data=False):
    """Downloads given url to given save location. Optionally returns the data"""
    #TODO: Add optional check for length to ensure correct download and retry limit
    data = get_url(url)
    f = open(savefile,"wb")
    f.write(data)
    f.close()
    if return_data:
        return data

def dict_of_attachments(board_data):
    """returns a nested dictionary of attachment URLs from a board"""
    attach_dict = {}
    board_json = json.loads(board_data)
    for card in board_json["cards"]:
        logging.debug("card data: " + str(card))
        # Check if card has any attachments. If so, add to dictionary
        if card["badges"]["attachments"] > 0:
            attachments = json.loads(get_url("https://api.trello.com/1/cards/%s/attachments?key=%s&token=%s" % (card["id"],TRELLO_API_KEY,TRELLO_API_APP_TOKEN)))
            for attachment in attachments:
                attach_dict[attachment["id"]] = {"card_id": card["id"],"name": attachment["name"],"url": attachment["url"]}
    return attach_dict

if __name__ == "__main__":
    sys.exit(main())
