import keyring
import requests
import xmltodict
import smtplib
import pprint
import logging
from email.message import EmailMessage
 
server = "http://localhost" 
serviceName = "CxPortal"
username = "admin"
endpoint_server = server + "/cxrestapi"
keyring.get_keyring()
 
 
def get_oauth2_token():
    password = keyring.get_password(serviceName, username)
    oauth2_data = {
        "username": username,
        "password": password,
        "grant_type": "password",
        "scope": "sast_rest_api",
        "client_id": "resource_owner_client",
        "client_secret": "014DF517-39D1-4453-B7B3-9930C563627C"
    }
    oauth2_response = requests.post(endpoint_server + "/auth/identity/connect/token", data=oauth2_data)
    if oauth2_response.status_code == 200:
        return oauth2_response.json()['access_token']
    else:
        return False
 
 

# Pull all projects data into a dictionary
# Loop through project data
# Check for queued scans for each project, then scan data for each project
# If there are no scans in queue, running scans, finished scans and there are failed or canceled scan data then this is an empty project
# Delete empty projects

def get_all_projects():
    headers = {
        "Authorization": "Bearer " + auth_token
    }
    projects_response = requests.get(endpoint_server + "/projects", headers=headers)
    if projects_response.status_code == 200:
        projects = projects_response.json()
        project_data = {}
        for p in projects:
            project_data[p["id"]] = p
        return project_data
    else:
        error(projects_response)
        logger.error(projects_response)
        return None

def get_all_scans(project_id):
    headers = {
        "Authorization": "Bearer " + auth_token
    }
    
    scan_response = requests.get(endpoint_server + "/sast/scans?projectId=" + str(project_id), headers=headers)
    if scan_response.status_code == 200:
        return scan_response.json()
    else:
        logger.error(scan_response)
        return False

def get_scans_queue(project_id):
    headers = {
        "Authorization": "Bearer " + auth_token
    }

    scan_response = requests.get(endpoint_server + "/sast/scansQueue?projectId=" + str(project_id), headers=headers)
    if scan_response.status_code == 200:
        return scan_response.json()
    else:
        logger.error(scan_response)
        return False


def delete_project(project_id):
    headers = {
        "Authorization": "Bearer " + auth_token
    }

    project_response = requests.delete(endpoint_server + "/projects/" + str(project_id), headers=headers)
    if project_response.status_code == 202:
        return True
    else:
        logger.error(project_response)
        return False
    


def init():
    logging.basicConfig(filename='cxscandata.log',level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger('cxscandata')
    empty_projects = {}
    logging.info('Getting list of Projects')
    projects = get_all_projects()
    for p in projects:
        queued_scans = get_scans_queue(projects[p]["id"])
        finished_scans = 0
        running_scans = 0
        failed_scans = 0
        canceled_scans = 0
        queued_total = 0
        queued_canceled = 0
        queued_failed = 0
        for q in queued_scans:
            logger.info("Checking the Scans Queue")
            logger.info(q["project"]["name"] + ": " + q["stage"]["value"])
            # Total count of scans queued
            queued_total += 1
            # Count Canceled Scans in queue
            if q["stage"]["value"] == "Canceled":
                queued_canceled += 1
            # Count Failed Scans in queue
            elif q["stage"]["value"] == "Failed":
                queued_failed += 1
        # Check to see if there are any scans in queue
        # If not then gather all scan data for project
        if queued_total == (queued_canceled + queued_failed):
            scans = get_all_scans(projects[p]["id"])
            projects[p]["scans"] = scans
            for s in scans:
                if s["status"]["name"] == "Finished":
                    finished_scans += 1
                elif s["status"]["name"] == "Scanning":
                    running_scans += 1
                elif s["status"]["name"] == "Failed":
                    failed_scans += 1
                elif s["status"]["name"] == "Canceled":
                    canceled_scans += 1
            if finished_scans == 0 and running_scans == 0 and (failed_scans > 0 or canceled_scans > 0):
                empty_projects[projects[p]["id"]] = projects[p]

    if len(empty_projects) < 1:
        logger.info("There were no empty Projects")
    else:
        logger.info(str(len(projects)) + " Empty projects were found")
        logger.info("The following projects were found to be empty")
        for p in empty_projects:
            logger.info("Project Name: " + empty_projects[p]["name"] + " | ID: " + str(empty_projects[p]["id"]) )
            delete_project(empty_projects[p]["id"])
            logger.info(empty_projects[p]["name"] + " has been deleted")
        

auth_token = get_oauth2_token()
init()