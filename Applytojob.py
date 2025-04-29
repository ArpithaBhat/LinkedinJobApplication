import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import logging
from dotenv import load_dotenv
load_dotenv()




# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class LinkedInAutoApply:
    def __init__(self, email, password,search_terms,location,num_pages):
        """
        Initialize the LinkedIn Auto Apply bot

        Args:
            email (str): LinkedIn login email
            password (str): LinkedIn login password
            search_terms (str): Job search keywords
            location (str): Job location
            num_pages (int): Number of pages to scrape
        """
        self.email = email
        self.password = password
        self.search_terms = search_terms
        self.location = location
        self.num_pages = num_pages

        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")

        # For GitHub Actions (headless environment)
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        # Initialize counters
        self.applied_jobs = 0
        self.skipped_jobs = 0

    def login(self):
        """Login to LinkedIn"""
        logger.info("Logging in to LinkedIn...")
        self.driver.get("https://www.linkedin.com/login")

        # Find email and password fields and enter credentials
        email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        password_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))

        email_field.send_keys(self.email)
        password_field.send_keys(self.password)
        print(self.password)

        # Click the login button
        login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()

        # Wait for the homepage to load
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "global-nav__me")))
            logger.info("Successfully logged in!")
        except TimeoutException:
            logger.error("Login failed or two-factor authentication required.")
            # In GitHub Actions we can't handle 2FA manually, so we'll need to fail
            raise Exception(
                "Login failed. If 2FA is enabled, you'll need to use an app password or other authentication method.")

    def search_jobs(self):
        """Search for jobs based on search terms and location"""
        logger.info(f"Searching for '{self.search_terms}' jobs in '{self.location}'...")

        # Navigate to LinkedIn Jobs
        self.driver.get("https://www.linkedin.com/jobs/")
        time.sleep(2)

        # Enter search terms
        search_terms_field = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[contains(@aria-label, 'Search by title')]")))
        search_terms_field.clear()
        search_terms_field.send_keys(self.search_terms)

        # Enter location
        location_field = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[contains(@aria-label, 'City')]")))
        location_field.clear()
        location_field.send_keys(self.location)
        location_field.send_keys(Keys.RETURN)

        # Wait for results to load
        time.sleep(3)

        # Add Easy Apply filter
        try:
            easy_apply_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label, 'Easy Apply filter')]")))
            easy_apply_button.click()
            logger.info("Easy Apply filter added")
            time.sleep(2)
        except TimeoutException:
            logger.warning("Could not add Easy Apply filter")

    def apply_to_jobs(self):
        """Apply to Easy Apply jobs"""
        logger.info("Starting to apply for jobs...")

        for page in range(1, self.num_pages + 1):
            logger.info(f"\nProcessing page {page} of {self.num_pages}")

            # Get all job listings
            job_listings = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".jobs-search-results__list-item")))

            # Process each job listing on the current page
            for i, job_listing in enumerate(job_listings):
                try:
                    logger.info(f"\nJob {i + 1}/{len(job_listings)} on page {page}")

                    # Click on the job to view details
                    job_listing.click()
                    time.sleep(2)

                    # Get job title
                    try:
                        job_title = self.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__job-title").text
                        company_name = self.driver.find_element(By.CSS_SELECTOR,
                                                                ".jobs-unified-top-card__company-name").text
                        logger.info(f"Job Title: {job_title}")
                        logger.info(f"Company: {company_name}")
                    except NoSuchElementException:
                        logger.warning("Could not retrieve job details")

                    # Click Easy Apply button
                    try:
                        easy_apply_button = self.wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, ".jobs-apply-button")))
                        easy_apply_button.click()
                        logger.info("Easy Apply button clicked")
                        time.sleep(2)

                        # Submit application
                        self.complete_application()
                        self.applied_jobs += 1

                    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
                        logger.warning(f"Could not apply to job: {str(e)}")
                        self.skipped_jobs += 1
                        continue

                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error processing job: {str(e)}")
                    continue

            # Navigate to next page if not the last page
            if page < self.num_pages:
                try:
                    next_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(3)
                    else:
                        logger.info("No more pages to process")
                        break
                except NoSuchElementException:
                    logger.info("No more pages to process")
                    break

        logger.info(f"\nApplication process completed!")
        logger.info(f"Applied to {self.applied_jobs} jobs")
        logger.info(f"Skipped {self.skipped_jobs} jobs")

    def complete_application(self):
        """Complete the application process"""
        # Handle each step of the application process
        while True:
            try:
                # Look for next button
                next_button = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[aria-label='Continue to next step']")))
                next_button.click()
                logger.info("Navigating to next step...")
                time.sleep(2)

                # Handle any form filling required
                self.fill_application_form()

            except TimeoutException:
                # If no next button, look for submit button
                try:
                    submit_button = self.wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[aria-label='Submit application']")))
                    logger.info("Submitting application...")
                    submit_button.click()
                    time.sleep(2)

                    # Close the confirmation dialog if present
                    try:
                        close_button = self.wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "button[aria-label='Dismiss']")))
                        close_button.click()
                        logger.info("Application submitted successfully!")
                    except TimeoutException:
                        logger.warning("Could not find confirmation dialog close button")

                    return

                except TimeoutException:
                    # If neither next nor submit button is found, try to close the dialog
                    try:
                        close_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                        close_button.click()
                        logger.warning("Application process closed without submitting")
                    except NoSuchElementException:
                        logger.warning("Could not find close button, skipping this job")

                    return

    def fill_application_form(self):
        """Fill out application forms"""
        # This is a simplified implementation. You might need to customize this based on the
        # application forms you typically encounter.

        # Example: Fill out phone number if asked
        try:
            phone_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='phoneNumber']")
            if phone_input.get_attribute("value") == "":
                # Get phone from environment variable or use default
                phone_number = os.environ.get("LINKEDIN_PHONE", "1234567890")
                phone_input.send_keys(phone_number)
                logger.info("Phone number filled")
        except NoSuchElementException:
            pass

        # Example: Handle multiple choice questions
        try:
            radio_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            if radio_buttons:
                # Select the first option for any radio button questions
                for button in radio_buttons:
                    if not button.is_selected():
                        button.click()
                        logger.info("Selected radio button option")
                        break
        except NoSuchElementException:
            pass

        # Example: Handle dropdown selections
        try:
            dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "select")
            for dropdown in dropdowns:
                # Select the second option (index 1) if available
                options = dropdown.find_elements(By.TAG_NAME, "option")
                if len(options) > 1:
                    options[1].click()
                    logger.info("Selected dropdown option")
        except NoSuchElementException:
            pass

    def close(self):
        """Close the browser"""
        self.driver.quit()
        logger.info("Browser closed")


def main():
    load_dotenv()
    # Get LinkedIn credentials from environment variables (GitHub Actions secrets)
    email = os.environ.get("LINKEDIN_EMAIL")
    print(email)
    password = os.environ.get("LINKEDIN_PASSWORD")
    search_terms = os.environ.get("JOB_SEARCH_TERMS", "Python Developer")
    location = os.environ.get("JOB_LOCATION", "Remote")
    num_pages = int(os.environ.get("NUM_PAGES", "1"))

    # Validate required environment variables
    if not email or not password:
        logger.error(
            "LinkedIn credentials not provided. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables.")
        return

    logger.info(f"Starting LinkedIn Auto-Apply Bot")
    logger.info(f"Search Terms: {search_terms}")
    logger.info(f"Location: {location}")
    logger.info(f"Pages to process: {num_pages}")

    # Initialize and run the bot
    bot = LinkedInAutoApply(email, password,search_terms,location,num_pages)

    try:
        bot.login()
        bot.search_jobs()
        bot.apply_to_jobs()
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        bot.close()


if __name__ == "__main__":
    main()