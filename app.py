from flask import Flask, render_template, request, redirect, url_for, send_from_directory
app = Flask(__name__)
from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv
import datetime
from dateutil import tz

def get_container_connection(db_name, container_name):

    COSMOS_URI = os.environ["COSMOS_URI"]
    COSMOS_KEY = os.environ["COSMOS_KEY"]

    client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)

    database = client.get_database_client(db_name)
    container = database.get_container_client(container_name)

    return container

def convert_cosmos_utc_to_local(cosmos_utc_time: str) -> datetime:
    Seattle = tz.gettz("US/Pacific")
    input_time = cosmos_utc_time[:-2]
    dtUTC = datetime.datetime.strptime(input_time, "%Y-%m-%dT%H-%M-%S.%f")
    dtZone = dtUTC.replace(tzinfo = datetime.timezone.utc)
    dtLocal = dtZone.astimezone(Seattle)
    return dtLocal
    

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/project_list')
def project_list():
    container = get_container_connection("social-media", "projects")
    q = 'SELECT c.title FROM c where c.active'
    projects = container.query_items(query=q, enable_cross_partition_query=True)
    return render_template('project_list.html', projects=projects)

@app.route('/future_posts')
def future_posts():
    container = get_container_connection("social-media", "blog-posts")
    q = 'SELECT c.title, c["linkedin-target-date-utc"] AS li_date,\
        c["twitter-target-date-utc"] AS tw_date, c["draft"] FROM c\
        WHERE c["linkedin-target-date-utc"] > GetCurrentDateTime() OR\
        c["twitter-target-date-utc"] > GetCurrentDateTime()'
    
    posts = container.query_items(query=q, enable_cross_partition_query=True)
    
    item_list = []
    for p in posts:
        d = dict(p)
        if p.get('li_date'):
            d['li_date'] = str(convert_cosmos_utc_to_local(p['li_date']))[:19]
        if p.get('tw_date'):
            d['tw_date'] = str(convert_cosmos_utc_to_local(p['tw_date']))[:19]
        if not p.get("draft"):
            d['draft'] = False
        item_list.append(d)        

    item_list = sorted(item_list, key=lambda x: x["li_date"])
    return render_template('future_posts.html', posts=item_list) 

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/auth_test', methods=['GET'])
def auth_test():
    code = request.args.get('code')
    return render_template('oauth_test.html', code=code)


if __name__ == '__main__':
    load_dotenv()
    app.run()