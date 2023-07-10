"""
    Web scraper for FTC team number data.
    @author: Lucas Bubner, 2023
"""
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from datetime import datetime

def get(team_number: int) -> dict:
    """
        Get information about a team number.
    """
    tdata = {}

    # Create a headless Firefox instance
    options = Options()
    service = Service(os.path.join(os.getcwd(), "geckodriver"), 0, None, os.path.devnull)
    options.headless = True
    driver = webdriver.Firefox(options=options, service=service)

    # Try with last year's season
    usingThisYear = False
    driver.get(_link(str(team_number), -1))

    # Search for keywords "No Teams or Events Found"
    src = driver.page_source
    for _ in range(2):
        if "No Teams or Events Found" in src:
            # Try with this year's season
            driver.get(_link(str(team_number)))
            usingThisYear = True
            src = driver.page_source
        else:
            break
    else:
        # If the loop is not broken, the team number is invalid
        return {
            "valid": False
        }
    
    # Team must exist
    season = datetime.now().year if usingThisYear else datetime.now().year - 1
    tdata.update({
        "valid": True,
        "season": f"{season}-{season + 1}",
    })
    
    # Get all teams that have returned
    data = driver.find_element(By.ID, "dTeamEventResults")

    # Remove formatting
    data = data.text.replace("\n", " ").replace("\t", " ").replace("\r", " ")

    # Extract into multiple teams, if applicable
    data = data.split("Team Number")

    # Remove the first element, which is the empty header
    data.pop(0)

    extracted_data = []
    for team in data:
        teamdata = {}
        # Find team nickname by extracting text between Nickname: and Organization(s):
        nickname = team.split("Nickname: ")[1].split("Organization(s):")[0]
        teamdata.update({"nickname": nickname.strip()})
        # Find organizations by extracting text between Organization(s): and Program:
        orgs = team.split("Organization(s): ")[1].split("Program:")[0]
        teamdata.update({"orgs": orgs.strip()})
        # Find program by extracting text between Program: and Location:
        program = team.split("Program: ")[1].split("Location:")[0]
        teamdata.update({"program": program.strip()})
        # Find location by extracting text between Location: and Rookie Year:
        location = team.split("Location: ")[1].split("Rookie Year:")[0]
        teamdata.update({"location": location.strip()})
        # Find rookie year by extracting text after Rookie Year:
        rookie_year = team.split("Rookie Year: ")[1]
        teamdata.update({"rookie_year": int(rookie_year.strip())})
        extracted_data.append(teamdata)

    driver.close()
    tdata.update({"data": extracted_data})
    return tdata



def _link(team_number: str, offset: int = 0) -> str:
    """
        FIRST team event search link.
    """
    year = datetime.now().year + offset
    return f"https://www.firstinspires.org/team-event-search#type=teams&sort=name&keyword={team_number}&programs=FLLJR,FLL,FTC,FRC&year={year}"