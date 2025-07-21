# scraper.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import os
import json
    
url ="https://www.linkedin.com/login" 
sleep_time = 1
email = "ccsaa0248@gmail.com"
password = "Myz081073"
job_search = "Junior Devops Engineer"


# Load instructions
try:
    with open("Instructions_gpt.json", "r") as f:
        instructions = json.load(f)
except FileNotFoundError:
    print("Error: Instructions.json file not found")
    exit(1)
except json.JSONDecodeError:
    print("Error: Instructions.json is not valid JSON")
    exit(1)


def scrape(): 
    print(f"Starting to scrape: {url}")
    options = webdriver.ChromeOptions()
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1920, 1080)  # Set a good window size
        
        print(f"Navigating to {url}")
        driver.get(url)
        time.sleep(2)  # Increased wait time to ensure page loads
    except Exception as e:
        print(f"Error navigating to {url}: {e}")
        return
    login(driver)
    paginate_and_scrape(driver)
    driver.save_screenshot("screenshot.png")
    driver.quit()
    #wait until page is loaded


def loop_on_jobs(driver):
    job_cards = driver.find_elements(
        By.XPATH,
        "//li[contains(@class,'scaffold-layout__list-item') and @data-occludable-job-id]"
    )
    wait = WebDriverWait(driver, 10)
    for card in job_cards:
        # Scroll into view (optional but helps if off‐screen)
        driver.execute_script("arguments[0].scrollIntoView(true);", card)
        # Click the card to load its details pane
        card.click()
        time.sleep(sleep_time)
        try:
            scrape_job(driver)
            # driver.save_screenshot("screenshot"+counter+".png")
            # counter += 1
        except Exception as e:
            print(f"Error in scrape_job: {e}")
            # Continue with next card
        # Wait for the details pane to update (using the dynamic root we defined)
        wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//div[contains(@class,'jobs-search__job-details--container') and @data-job-details-events-trigger]"
        )))


def scrape_job(driver):
    jobRoot = "//div[contains(@class,'jobs-search__job-details--container') and @data-job-details-events-trigger]"

    try:
        # Scraping Data :
        job_url = driver.find_element(By.XPATH, jobRoot + "//h1//a[1]").get_attribute("href")
        time.sleep(sleep_time)
        #<h1 class="t-24 t-bold inline"><a href="/jobs/view/4254317971/?alternateChannel=search&amp;eBP=NON_CHARGEABLE_CHANNEL&amp;refId=3KCBVk%2F0rmNUUWaqUGFqVg%3D%3D&amp;trackingId=aKhoQCVYtPKrqWAzj10%2BSw%3D%3D&amp;trk=d_flagship3_search_srp_jobs" id="ember370" class="ember-view">QA Automation Engineer</a></h1>
        job_title = driver.find_element(
            By.XPATH,
            jobRoot + "//h1[contains(@class,'t-24 t-bold inline')]//a[1]"
        ).get_attribute("text")
        time.sleep(sleep_time)

        company_name = driver.find_element(
            By.XPATH,
            jobRoot + "//div[contains(@class,'job-details-jobs-unified-top-card__company-name')]//a[1]"
        ).text
        time.sleep(sleep_time)

        company_url = driver.find_element(
            By.XPATH,
            jobRoot + "//div[contains(@class,'job-details-jobs-unified-top-card__company-name')]//a[1]"
        ).get_attribute("href")
        time.sleep(sleep_time)

        # Insight row: this job shows only workplace + employment (no seniority span here).
        workplace_type = safe_find_element(
            driver,
            By.XPATH,
            jobRoot + "//li[contains(@class,'job-details-jobs-unified-top-card__job-insight')][1]//span[1]"
        )
        if workplace_type:
            workplace_type = workplace_type.text
        time.sleep(sleep_time)

        job_employment_type = safe_find_element(
            driver,
            By.XPATH,
            jobRoot + "//li[contains(@class,'job-details-jobs-unified-top-card__job-insight')][1]//span[contains(@class,'job-insight-view-model-secondary')][1]"
        )
        if job_employment_type:
            job_employment_type = job_employment_type.text
        time.sleep(sleep_time)

        # Seniority may not exist for this listing; wrap in try/except if needed.
        job_seniority_level = safe_find_element(
            driver,
            By.XPATH,
            jobRoot + "//li[contains(@class,'job-details-jobs-unified-top-card__job-insight')][1]//span[contains(@class,'job-insight-view-model-secondary')][2]"
        )
        if job_seniority_level:
            job_seniority_level = job_seniority_level.text
        else:
            job_seniority_level = ""
        time.sleep(sleep_time)

        job_location = safe_find_element(
            driver,
            By.XPATH,
            jobRoot + "//div[contains(@class,'job-details-jobs-unified-top-card__tertiary-description-container')]//span[contains(@class,'tvm__text')][1]"
        )
        if job_location:
            job_location = job_location.text
        time.sleep(sleep_time)

        # Posted time appears nested after "Reposted"; grabbing the span with a date-ish phrase (contains 'ago' or 'Reposted')
        job_posted_time = safe_find_element(
            driver,
            By.XPATH,
            jobRoot + "//div[contains(@class,'job-details-jobs-unified-top-card__tertiary-description-container')]"
                    "//span[contains(.,'ago') or contains(.,'Reposted')]"
        )
        if job_posted_time:
            job_posted_time = job_posted_time.text
        time.sleep(sleep_time)

        # Applicants text: “Over 100 people clicked apply”
        number_of_applicants = safe_find_element(
            driver,
            By.XPATH,
            jobRoot + "//div[contains(@class,'job-details-jobs-unified-top-card__tertiary-description-container')]"
                    "//span[contains(translate(.,'APPLY','apply'),'apply') and contains(.,'click')]"
        )
        if number_of_applicants:
            number_of_applicants = number_of_applicants.text
        time.sleep(sleep_time)

        # Description container
        job_description = driver.find_element(
            By.XPATH,
            jobRoot + "//div[@id='job-details']"
        ).text
        time.sleep(5)

        #saver data in json file
        data = {
            "job_url": job_url,
            "job_title": job_title,
            "company_name": company_name,
            "company_url": company_url,
            "workplace_type": workplace_type,
            "job_employment_type": job_employment_type,
            "job_seniority_level": job_seniority_level,
            "job_location": job_location,
            "job_posted_time": job_posted_time,
            "number_of_applicants": number_of_applicants,
            "job_description": job_description
        }
        #save data in directory and name it as job search
        
        os.makedirs(job_search, exist_ok=True)
        with open(job_search + "/" + company_name + "_" + job_title + ".json", "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error: {e}")
    

def safe_find_element(driver, by_method, selector, default_value=None):
    """
    A wrapper around the find_element method that doesn't throw exceptions.
    Returns the element if found, otherwise returns the default_value (None by default).
    """
    try:
        element = driver.find_element(by_method, selector)
        return element
    except NoSuchElementException:
        print(f"Element not found: {selector}")
        return None
    except TimeoutException:
        print(f"Timeout while finding element: {selector}")
        return None
    except Exception as e:
        print(f"Unexpected error finding element {selector}: {str(e)}")
        return None


def login(driver):
    element = driver.find_element(By.ID , "username")
    element.send_keys(email)
    time.sleep(sleep_time)
    element = driver.find_element(By.ID , "password")
    element.send_keys(password)
    time.sleep(sleep_time)
    driver.find_element(By.XPATH , "//div[contains(@class,'login__form_action_container')]//button[@data-litms-control-urn='login-submit']").click()
    time.sleep(sleep_time)
    jobRoot = "//div[contains(@class,'jobs-search__job-details--container') and @data-job-details-events-trigger]"
    element = driver.find_element(By.XPATH , "//div[@id='global-nav-typeahead']//input[@data-view-name='search-global-typeahead-input']")
    element.send_keys(job_search)
    element.send_keys(Keys.ENTER)
    time.sleep(3)
    driver.find_element(By.XPATH, "//div[contains(@class,'search-results__cluster-bottom-banner')]//a[@data-test-app-aware-link and contains(@href,'/jobs/search')]").click()
    time.sleep(3)


def paginate_and_scrape(driver):
    wait = WebDriverWait(driver, 10)
    next_btn_xpath = "//button[@aria-label='View next page']"

    while True:
        # 1) Scrape this page’s jobs
        loop_on_jobs(driver)

        # 2) Try to find & click “Next”
        try:
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, next_btn_xpath)))
        except TimeoutException:
            # No clickable “Next” → we’re on the last page
            break

        next_btn.click()

        # 3) Wait for page to load by observing the job-title <h1> change
        wait.until(EC.visibility_of_element_located((
            By.XPATH,
            "//div[contains(@class,'jobs-search__job-details--container') and @data-job-details-events-trigger]//h1"
        )))

    print("🎉 Reached the last page.")


if __name__ == "__main__":
    scrape() 
    print("Scraping completed.")
