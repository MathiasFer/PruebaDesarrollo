import os
import sys
from followers_downloader import FollowersDownloader
from profile_scraper import ProfileScraper
from data_analyzer import DataAnalyzer
from credentials import USERNAME, PASSWORD, CUENTA_OBJETIVO, LIMITE_SEGUIDORES


class MainApp:
    """Clase principal que coordina las fases del programa."""

    def __init__(self, username, password, target_account, limit):
        self.username = username
        self.password = password
        self.target_account = target_account
        self.limit = limit

        # 🔹 Nombres de archivos (texto)
        self.followers_list_csv = f"{target_account}_following_list.csv"
        self.output_counts_csv = f"{target_account}_following_counts.csv"
        self.graph_filename = f"{target_account}_benford_analysis.png"

        print(f"Iniciando análisis de Benford para los SEGUIDOS de: {target_account}")

    # Fase 1: descarga de nombres de usuario
    def _run_phase_1_download(self):
        print("\n--- Fase 1: Descarga de usuarios seguidos ---")
        downloader = FollowersDownloader(self.username, self.password)
        try:
            downloader.download_and_save_followers(
                self.target_account,
                self.limit,
                self.followers_list_csv
            )
        except Exception as e:
            print(f"Error en la Fase 1: {e}")
        finally:
            downloader.close_driver()

    # Fase 2: recopilación de conteos
    def _run_phase_2_scrape_counts(self):
        if not os.path.exists(self.followers_list_csv):
            print(f"\nEl archivo '{self.followers_list_csv}' no fue encontrado. Ejecuta la Fase 1 primero.")
            return

        print("\n--- Fase 2: Recopilación de conteo de seguidores de los seguidos ---")
        scraper = ProfileScraper(self.username, self.password)
        usernames_to_count = scraper.read_usernames_from_csv(self.followers_list_csv)

        if usernames_to_count:
            try:
                scraper.scrape_follower_counts(usernames_to_count, self.output_counts_csv)
            except Exception as e:
                print(f"Error en la Fase 2: {e}")
        else:
            print("No hay usuarios para contar. Terminando Fase 2.")

    # Fase 3: análisis de Benford
    def _run_phase_3_analyze(self):
        if not os.path.exists(self.output_counts_csv):
            print(f"\nEl archivo '{self.output_counts_csv}' no fue encontrado. Ejecuta la Fase 2 primero.")
            return

        print("\n--- Fase 3: Limpieza y análisis de Benford (seguidos) ---")
        analyzer = DataAnalyzer(self.output_counts_csv)
        analyzer.clean_and_prepare_data()
        analyzer.analyze_and_plot_first_digit(self.graph_filename)

    # Ejecuta la fase seleccionada
    def run_phase(self, phase_to_run):
        if phase_to_run == 1:
            self._run_phase_1_download()
        elif phase_to_run == 2:
            self._run_phase_2_scrape_counts()
        elif phase_to_run == 3:
            self._run_phase_3_analyze()
        elif phase_to_run == 0:
            self._run_phase_1_download()
            self._run_phase_2_scrape_counts()
            self._run_phase_3_analyze()
        else:
            print("\nOpción no válida. Selecciona 0, 1, 2 o 3.")


def display_menu():
    print("\n" + "=" * 45)
    print("ANALIZADOR DE SEGUIDOS (BENFORD)")
    print("=" * 45)
    print("Selecciona la fase a ejecutar:")
    print("  [1] FASE 1: Recolectar usuarios seguidos")
    print("  [2] FASE 2: Recolectar conteo de seguidores de los seguidos")
    print("  [3] FASE 3: Análisis de Benford y gráfico")
    print("  [0] EJECUTAR TODO (1 → 2 → 3)")
    print("  [4] Salir")
    print("=" * 45)

    while True:
        try:
            choice = input("Ingresa tu opción (0-4): ").strip()
            if choice == '4':
                sys.exit(0)
            return int(choice)
        except ValueError:
            print("Entrada inválida. Ingresa un número.")


if __name__ == '__main__':
    phase = -1

    if len(sys.argv) > 1:
        try:
            phase = int(sys.argv[1])
        except ValueError:
            print("El argumento debe ser un número entero (0, 1, 2 o 3).")
            sys.exit(1)

    app = MainApp(USERNAME, PASSWORD, CUENTA_OBJETIVO, LIMITE_SEGUIDORES)

    if phase == -1:
        phase = display_menu()

    app.run_phase(phase)
