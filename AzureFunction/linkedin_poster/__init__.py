"""A package for posting to LinkedIn"""
import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("social-media-poster")

logger_blocklist = [
    "azure.core.pipeline.policies.http_logging_policy",
    "twilio.http_client"
]

def post_to_linkedin(body, post_url, image_url, linkback):

    logger.info("Posting to LinkedIn")    
    li_text = linkedin_text(body, post_url, linkback) 
    
    # replace all parenthesis and brackets from the text, because LinkedIn is failing to post with them
    li_text = li_text.replace("(", "\\\\(")
    li_text = li_text.replace(")", "\\\\)")
    li_text = li_text.replace("]", "\\\\]")
    li_text = li_text.replace("[", "\\\\[")
    li_text = li_text.replace("<", "\\\\<")
    li_text = li_text.replace(">", "\\\\>")
    li_text = li_text.replace("{", "\\\\{")
    li_text = li_text.replace("}", "\\\\}")

    li_text = li_text.replace("|", "\\\\|")
    li_text = li_text.replace("@", "\\\\@")
    li_text = li_text.replace("_", "\\\\_")
    li_text = li_text.replace("*", "\\\\*")
    li_text = li_text.replace("~", "\\\\~")

    # remove any leading \ns from li_text
    li_text = li_text.lstrip("\n")

    person_id = os.getenv("LINKEDIN_PERSON_ID")
    token = os.getenv("LINKEDIN_TOKEN")

    if image_url:
        response = post_linkedin_image(li_text, image_url, person_id, token)    
    else:
        response = post_linkedin_text(li_text, person_id, token)    

    logger.info("Posted to LinkedIn")
    return li_text, response        

def post_linkedin_image(txt, img_path, person_id, token):

    logger.info("Posting image to LinkedIn")
    logger.info(f"\tCalled with parameters: {txt}, {img_path}, {person_id}, {token}")
    asset, upload_url = get_upload_url(token, person_id)

    resp_code = upload_image(img_path, upload_url, token)
    if resp_code == 201:
        response = post_asset(token, person_id, asset, txt)

    # print(f"Asset posting code: {response.status_code}")
    # print(response.json())
    return(response)

def post_asset(token, person_id, asset, text):

    logger.info("Posting text and image to LinkedIn")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202305"
    }

    with open("linkedin_post_image.json", "r") as f:
        post_json = f.read()

    post_json = post_json.replace("PERSON_URN", person_id)
    post_json = post_json.replace("ASSET_URN", asset)
    post_json = post_json.replace("POST_TEXT", text)

    logger.info(post_json)

    url = "https://api.linkedin.com/rest/posts"
    response = requests.post(url, post_json.encode('utf-8'), headers=headers)

    return response

def get_upload_url(token, person_id):
    logger.info("Getting upload URL")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202305"
    }

    with open("linkedin_initialize_upload.json", "r") as f:
        upload_json = f.read()

    upload_json = upload_json.replace("PERSON_URN", person_id)

    url = "https://api.linkedin.com/rest/images?action=initializeUpload"
    response = requests.post(url, upload_json, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error getting upload URL {response.status_code}, response: {response.text}")
    response_json = json.loads(response.text)
    upload_url = response_json.get("value").get("uploadUrl")
    asset = response_json.get("value").get("image")

    return asset, upload_url

def upload_image(filepath, upload_url, token):
    headers = {"Authorization": f"Bearer {token}"}

    is_url = False
    
    # download a file if it is a URL
    if not os.path.exists(filepath):
        # for now, assuming it's a URL
        is_url = True

        response = requests.get(filepath)
        local_img_path = f"/tmp/{os.path.basename(filepath)}"
        file = open(local_img_path, "wb")
        file.write(response.content)
        file.close()

        filepath = local_img_path

    resp = requests.put(upload_url, headers=headers, data=open(filepath,'rb').read())
    if is_url:
       os.remove(filepath)

    return resp.status_code

def post_linkedin_text(txt, person_id, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202305"
    }
   
    with open("linkedin_post_text.json", "r") as f:
        post_json = f.read()

    post_json = post_json.replace("PERSON_URN", person_id)
    post_json = post_json.replace("POST_TEXT", txt)

    url = "https://api.linkedin.com/rest/posts"
    response = requests.post(url, post_json, headers=headers)

    return response

def linkedin_text(txt, post_url, linkback):
    post = txt
    post_size = len(post)

    post_url = post_url.replace(".md", ".html")
    post_url = post_url.replace(".qmd", ".html")   

    if post_size > 2800:
        post = post[:2800]
        post += f"...\n\nThis post ended up being too long for LinkedIn. It's in my blog at {post_url} .\n\n"
    else:
        if (linkback is None) or (linkback is True):
            post = post + f"\n\nThis post first appeared at {post_url} .\n\n"
        else:
            post = post + f"\n\nThis post first appeared at my blog (link in bio).\n\n"

    post = post.replace("\n", "\\n")
    post = post.replace('"', '\\"')
    return post
