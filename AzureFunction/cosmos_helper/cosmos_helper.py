import os
from azure.cosmos import CosmosClient

def get_container_connection(db_name, container_name):

    COSMOS_URI = os.environ["COSMOS_URI"]
    COSMOS_KEY = os.environ["COSMOS_KEY"]

    client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)

    database = client.get_database_client(db_name)
    container = database.get_container_client(container_name)

    return container