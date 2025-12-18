# followers_downloader.py
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class FollowersDownloader:
    """Descarga los SEGUIDOS de una cuenta de Instagram usando Selenium"""

    def __init__(self, username, password):
        self.username = username
        self.password = password

        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.wait = WebDriverWait(self.driver, 15)

        self._login()

    # ---------------------------
    # LOGIN
    # ---------------------------
    def _login(self):
        self.driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(4)

        username_input = self.wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_input = self.driver.find_element(By.NAME, "password")

        username_input.send_keys(self.username)
        password_input.send_keys(self.password)
        password_input.send_keys(Keys.ENTER)

        time.sleep(6)

        # Botones opcionales "Guardar info" y "Notificaciones"
        for _ in range(2):
            try:
                btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Ahora no')]"))
                )
                btn.click()
                time.sleep(2)
            except:
                pass

    # ---------------------------
    # DESCARGA DE SEGUIDOS
    # ---------------------------
    def download_and_save_followers(self, target_account, limit, output_csv):
        self.driver.get(f"https://www.instagram.com/{target_account}/")
        time.sleep(5)

        # 👉 BOTÓN DE SEGUIDOS (FOLLOWING)
        following_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'/following/')]"))
        )
        following_btn.click()
        time.sleep(3)

        # Modal
        modal = self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )

        usernames = set()
        last_count = 0

        print("📥 Extrayendo SEGUIDOS...")

        while len(usernames) < limit:
            links = modal.find_elements(By.XPATH, ".//a[contains(@href,'/')]")

            for link in links:
                username = link.get_attribute("href").split("/")[-2]
                if username and username not in usernames:
                    usernames.add(username)

                if len(usernames) >= limit:
                    break

            # Scroll dentro del modal
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", modal
            )
            time.sleep(2)

            # Si no hay cambios, detener
            if len(usernames) == last_count:
                print("⚠️ No se detectan más usuarios.")
                break

            last_count = len(usernames)
            print(f"   ➜ {len(usernames)} seguidos recopilados")

        # Guardar CSV
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["username"])
            for u in usernames:
                writer.writerow([u])

        print(f"\n✅ {len(usernames)} seguidos guardados en {output_csv}")

    def close_driver(self):
        try:
            self.driver.quit()
        except:
            pass
