import datetime
import logging
from dotenv import load_dotenv
import azure.functions as func
from pytz import timezone
from twilio_notifier import twilio_notifier as twil
# import twitter_poster as twit
from cosmos_helper import cosmos_helper as ch
from linkedin_poster import post_to_linkedin
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("social-media-poster")

logger_blocklist = [
    "azure.core.pipeline.policies.http_logging_policy",
    "twilio.http_client"
]

for module in logger_blocklist:
    logging.getLogger(module).setLevel(logging.WARNING)

def process_linkedin_posts() -> None:
    
    container = ch.get_container_connection("social-media", "blog-posts")
    q = 'SELECT * FROM c WHERE c["linkedin-target-date-utc"] < GetCurrentDateTime() AND NOT IS_DEFINED(c["linkedin-posted-utc"])'

    for item in container.query_items(query=q, enable_cross_partition_query=True):
        draft = item.get("draft")
        if draft:
            continue

        message = ""
        try:
            li_text, response = post_to_linkedin(item.get("body"), item.get("post-url"), item.get("image"), item.get("linkedin-linkback"))
            utc_timestamp = str(datetime.datetime.utcnow().isoformat()) + "0Z"
            if response.status_code == 200 or response.status_code == 201:
                item['linkedin-posted-utc'] = utc_timestamp
                container.upsert_item(item)
                message = message + f"({response.status_code}): Posted to LinkedIn"
            else:
                message = message + f"({response.status_code}) when posting to LinkedIn"
        except Exception as e:
            message =  traceback.format_exc()
            logging.error(message)
        finally:
            utc_timestamp = datetime.datetime.utcnow()
            seattle_tz = timezone("US/Pacific")
            seattle_time = seattle_tz.fromutc(utc_timestamp)
            message = f"At {seattle_time}: {message}"
            logging.info(message)
            twil.update_lucas(message)            

def retrigger_draft(front_matter_dict, linkedin_posted, twitter_posted, get_date):

    linkedin_repost = front_matter_dict.get("linkedin-repost")

    # If target posting date is in the future, remove last posted date
    if linkedin_target_date and linkedin_posted and linkedin_target_date > datetime.datetime.now():
        front_matter_dict.pop("linkedin-posted")
        
    # Check if I want to move a posting date to the future for LinkedIn
    if linkedin_repost and linkedin_posted and linkedin_target_date < datetime.datetime.now(): 
        front_matter_dict["linkedin-target-date"] = linkedin_posted + datetime.timedelta(days=linkedin_repost)
        linkedin_target_date = get_date(front_matter_dict, "linkedin-target-date")

def main(mytimer: func.TimerRequest) -> None:
    """Main function that is run by the Azure Function"""

    logger.info("Starting social media poster")    
    process_linkedin_posts()

