# followers_downloader.py
import os
import time
import random
import csv
from selenium import webdriver
from selenium.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException


class FollowersDownloader:
    """Clase para descargar los nombres de usuario seguidores de una cuenta de Instagram."""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None

    # Inicializa el driver de Chrome con configuración personalizada
    def _init_driver(self, headless=False):
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1600,900")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        if headless:
            options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        self.driver = Chrome(service=service, options=options)
        return self.driver

    # Crea una espera explícita (WebDriverWait)
    def _wait_for(self, timeout=15):
        return WebDriverWait(self.driver, timeout)

    # Inicia sesión en Instagram y maneja los pop-ups posteriores
    def _login_instagram(self) -> bool:
        if not self.driver:
            self._init_driver(headless=False)

        wait = self._wait_for(20)
        self.driver.get("https://www.instagram.com/")

        # Espera los campos de usuario y contraseña
        try:
            user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            pass_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        except Exception:
            print("Timeout: No se encontraron los campos de login.")
            return False

        # Enviar credenciales
        user_input.clear()
        user_input.send_keys(self.username)
        pass_input.clear()
        pass_input.send_keys(self.password)

        try:
            # Clic en el botón de iniciar sesión
            submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./div[text()='Iniciar']]")))
            submit_btn.click()
        except Exception:
            print("No se pudo hacer clic en el botón de login.")
            return False

        # Espera cambio de URL y manejo de pop-ups
        try:
            wait.until(lambda d: "instagram.com" in d.current_url and "login" not in d.current_url)
            time.sleep(3)
            print("Login exitoso, intentando cerrar pop-ups.")

            # Cerrar "Guardar información de inicio de sesión"
            try:
                now_not_btn_save = wait.until(EC.element_to_be_clickable((By.XPATH,
                    "//div[text()='Guardar información de inicio de sesión']/following-sibling::div//button[text()='Ahora no']")))
                now_not_btn_save.click()
                print("Pop-up 'Guardar información' cerrado.")
                time.sleep(2)
            except TimeoutException:
                pass

            # Cerrar "Activar notificaciones"
            try:
                notification_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Ahora no']")))
                notification_btn.click()
                print("Pop-up 'Notificaciones' cerrado.")
                time.sleep(2)
            except TimeoutException:
                pass

            return True

        except Exception as e:
            print(f"Fallo al detectar la sesión iniciada o al cerrar pop-ups: {e}")
            return False

    # Navega directamente al perfil del usuario objetivo
    def _buscar_usuario(self, username_objetivo):
        wait = WebDriverWait(self.driver, 15)
        profile_url = f"https://www.instagram.com/{username_objetivo}/"

        print(f"Navegando a: {profile_url}")
        self.driver.get(profile_url)

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//header")))

            # Validación extra para evitar perfiles inexistentes
            if "page not found" in self.driver.page_source.lower() or "no se pudo encontrar" in self.driver.page_source.lower():
                print(f"Error: La URL {username_objetivo} no es un perfil válido.")
                return False

            print(f"Perfil de @{username_objetivo} cargado correctamente.")
            time.sleep(3)
            return True

        except TimeoutException:
            print("Timeout al cargar el perfil.")
            return False
        except Exception as e:
            print(f"Error al navegar al perfil: {e}")
            return False

    # Guarda los nombres de usuario en un CSV
    def _guardar_a_csv(self, data: list[str], filename: str):
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['username'])
                writer.writerows([[username] for username in data])
            print(f"Lista de usuarios guardada en: {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo CSV: {e}")

    # Obtiene la lista de seguidores realizando scroll dentro del modal
    def _obtener_seguidores(self, limite=500) -> list[str]:
        wait = self._wait_for(15)
        seguidores_set = set()

        try:
            # Abre el modal de seguidores
            seguidos_link_xpath = "//a[contains(@href, '/followed/')]"
            seguidos_link = wait.until(EC.element_to_be_clickable((By.XPATH, seguidos_link_xpath)))
            self.driver.execute_script("arguments[0].click();", seguidos_link)
            print("Modal de seguidores abierto.")
            time.sleep(3)

            # Encuentra el contenedor desplazable del modal
            modal = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
            scroll_container = modal.find_element(By.XPATH,
                ".//div[contains(@style,'height')]//div[contains(@style,'overflow')][1]")

            if not scroll_container:
                print("No se encontró el contenedor desplazable del modal.")
                return []

            print("Contenedor desplazable detectado, comenzando scroll...")

            # Control de progreso: detecta si deja de cargar nuevos usuarios
            max_scroll_attempts_without_new_users = 7
            no_progress_count = 0
            last_count = 0

            while len(seguidores_set) < limite:
                # Extraer los usuarios visibles actualmente
                links = scroll_container.find_elements(By.XPATH,
                    ".//a[contains(@href,'/') and not(contains(@tabindex, '-1'))]")

                for a in links:
                    try:
                        href = a.get_attribute("href")
                        if href and "instagram.com" in href:
                            username = href.split("/")[-2]
                            if username and username not in seguidores_set:
                                seguidores_set.add(username)
                    except Exception:
                        continue

                if len(seguidores_set) >= limite:
                    break

                print(f"Capturados: {len(seguidores_set)} (sin progreso: {no_progress_count})", end="\r")

                # Controla si el scroll sigue encontrando usuarios nuevos
                if len(seguidores_set) == last_count:
                    no_progress_count += 1
                else:
                    no_progress_count = 0

                last_count = len(seguidores_set)

                # Hace scroll hacia el final del modal
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_container)
                time.sleep(random.uniform(3.0, 4.5))

                # Sale si ya no se cargan usuarios nuevos
                if no_progress_count >= max_scroll_attempts_without_new_users:
                    print(f"\nLímite de reintentos ({max_scroll_attempts_without_new_users}) alcanzado.")
                    break

            seguidores_list = list(seguidores_set)
            print(f"\nTotal de seguidores recolectados: {len(seguidores_list)}")
            return seguidores_list

        except Exception as e:
            print(f"Error al obtener seguidores: {e}")
            return []

    # Ejecuta el proceso completo: login, búsqueda, scraping y guardado
    def download_and_save_followers(self, perfil_objetivo: str, limite: int, csv_filename: str):
        start_time = time.time()

        if not self._login_instagram():
            print("Login fallido. No se puede continuar.")
            return

        if not self._buscar_usuario(perfil_objetivo):
            print("No se pudo encontrar el usuario objetivo o cargar el perfil.")
            return

        print(f"Iniciando scraping de seguidores de {perfil_objetivo}...")
        seguidores_usernames = self._obtener_seguidores(limite=limite)

        if seguidores_usernames:
            self._guardar_a_csv(seguidores_usernames, csv_filename)
        else:
            print("No se pudieron obtener seguidores.")

        end_time = time.time()
        duration = end_time - start_time
        print(f"Proceso finalizado a las {time.strftime('%H:%M:%S')} (Duración: {duration:.2f} segundos)")

    # Cierra el navegador
    def close_driver(self):
        if self.driver:
            self.driver.quit()
            print("Cerrando navegador del Downloader.")
