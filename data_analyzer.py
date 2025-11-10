# data_analyzer.py
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import numpy as np


class DataAnalyzer:
    """Clase para limpiar datos, aplicar análisis del primer dígito y graficar (Ley de Benford)."""

    def __init__(self, input_csv_path):
        self.input_csv_path = input_csv_path
        self.df = pd.DataFrame()

    def _convert_count_to_numeric(self, count_str):
        """Convierte el conteo a número entero, manejando diferentes formatos."""
        if pd.isna(count_str):
            return np.nan

        # Si ya es numérico, retornarlo directamente
        if isinstance(count_str, (int, float)):
            return int(count_str) if count_str > 0 else np.nan

        s = str(count_str).strip().upper()

        # Si está vacío o es un string no numérico especial
        if s in ['', 'PRIVADA', 'NO_EXISTE', 'NO_ENCONTRADO', 'ERROR', 'TIMEOUT', 'ERROR_DESCONOCIDO']:
            return np.nan

        # Manejar formatos con K (miles) y M (millones)
        if 'K' in s:
            try:
                num = float(s.replace('K', '').replace(',', '').strip())
                return int(num * 1000)
            except ValueError:
                return np.nan
        elif 'M' in s:
            try:
                num = float(s.replace('M', '').replace(',', '').strip())
                return int(num * 1000000)
            except ValueError:
                return np.nan

        # Limpiar el string: quitar comas, puntos que sean separadores de miles
        s_clean = s.replace(',', '').replace('.', '')

        try:
            num = int(s_clean)
            return num if num > 0 else np.nan
        except ValueError:
            # Si falla, intentar extraer números del string
            import re
            numbers = re.findall(r'\d+', s)
            if numbers:
                try:
                    num = int(''.join(numbers))
                    return num if num > 0 else np.nan
                except ValueError:
                    return np.nan
            return np.nan

    def clean_and_prepare_data(self):
        """Lee el CSV, elimina filas no numéricas y prepara los datos."""
        try:
            self.df = pd.read_csv(self.input_csv_path)
            print(f" Leídos {len(self.df)} registros del CSV.")

            # Mostrar una muestra de los datos crudos
            print("\n Muestra de datos crudos:")
            print(self.df.head(10))

        except FileNotFoundError:
            print(f" Error: Archivo '{self.input_csv_path}' no encontrado.")
            return
        except Exception as e:
            print(f" Error al leer el CSV: {e}")
            return

        # Aplicar la limpieza
        print("\n Limpiando datos...")
        self.df['followers_numeric'] = self.df['followers_count'].apply(self._convert_count_to_numeric)

        # Mostrar estadísticas de la limpieza
        total_rows = len(self.df)
        valid_rows = self.df['followers_numeric'].notna().sum()
        invalid_rows = total_rows - valid_rows

        print(f"Datos válidos: {valid_rows}")
        print(f"Datos inválidos/eliminados: {invalid_rows}")

        if valid_rows > 0:
            # Filtrar las filas con conteos válidos (> 0)
            self.df = self.df[self.df['followers_numeric'].notna() & (self.df['followers_numeric'] > 0)]
            self.df['followers_numeric'] = self.df['followers_numeric'].astype(int)

            print(f"\n Datos finales para análisis: {len(self.df)} registros")
            print(" Estadísticas de seguidores:")
            print(f"   Mínimo: {self.df['followers_numeric'].min()}")
            print(f"   Máximo: {self.df['followers_numeric'].max()}")
            print(f"   Media: {self.df['followers_numeric'].mean():.2f}")
            print(f"   Mediana: {self.df['followers_numeric'].median()}")
        else:
            print("No hay datos válidos para analizar.")
            self.df = pd.DataFrame()

    def analyze_and_plot_first_digit(self, graph_filename: str):
        """Saca el primer dígito, calcula frecuencias y grafica la Ley de Benford."""
        if self.df.empty:
            print("No hay datos limpios para analizar.")
            return

        # Sacar el primer dígito de la izquierda
        self.df['first_digit'] = self.df['followers_numeric'].astype(str).str[0].astype(int)

        # Verificar que solo tengamos dígitos del 1-9
        valid_digits = self.df[self.df['first_digit'].between(1, 9)]

        if len(valid_digits) == 0:
            print("No hay dígitos válidos (1-9) para analizar.")
            return

        # Conteo de cada dígito (1 al 9)
        digit_counts = valid_digits['first_digit'].value_counts().sort_index()
        total_count = digit_counts.sum()
        frequencies = (digit_counts / total_count) * 100

        print("\n" + "=" * 50)
        print("RESULTADOS DEL ANÁLISIS DEL PRIMER DÍGITO")
        print("=" * 50)
        for digit in range(1, 10):
            count = digit_counts.get(digit, 0)
            freq = frequencies.get(digit, 0)
            print(f"Dígito {digit}: {count:4d} ocurrencias ({freq:6.2f}%)")

        print(f"\nTotal de números analizados: {total_count}")

        # Gráfico
        self._create_benford_plot(frequencies, digit_counts, graph_filename)

    def _create_benford_plot(self, frequencies: pd.Series, digit_counts: pd.Series, filename: str):
        """Genera y guarda el gráfico de Benford mostrando números reales."""
        # Distribución teórica de Benford (%)
        benford_data = {
            1: 30.1, 2: 17.6, 3: 12.5, 4: 9.7, 5: 7.9,
            6: 6.7, 7: 5.8, 8: 5.1, 9: 4.6
        }
        benford_df = pd.Series(benford_data)

        # Asegurar que el índice coincida (1-9) y llenar con 0 los dígitos faltantes
        frequencies = frequencies.reindex(range(1, 10), fill_value=0)
        digit_counts = digit_counts.reindex(range(1, 10), fill_value=0)

        plt.figure(figsize=(14, 8))

        # Gráfico de barras de las frecuencias reales
        bars = plt.bar(frequencies.index - 0.2, frequencies.values, width=0.4,
                       color='teal', alpha=0.7, label='Datos Reales')

        # Gráfico de línea de la Ley de Benford
        line = plt.plot(benford_df.index, benford_df.values, marker='o',
                        linestyle='--', color='red', linewidth=2, markersize=6,
                        label='Ley de Benford Teórica')

        # Añadir valores en las barras (NÚMERO REAL + PORCENTAJE)
        for i, (v, count) in enumerate(zip(frequencies.values, digit_counts.values)):
            if v > 0:  # Solo mostrar texto si el valor no es cero
                plt.text(i + 1 - 0.2, v + 0.5,
                         f'{count:,d} cuentas\n({v:.1f}%)',
                         ha='center', va='bottom', fontsize=8, fontweight='bold',
                         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

        # Añadir valores en la línea de Benford
        for i, v in enumerate(benford_df.values):
            plt.text(i + 1 + 0.2, v + 0.5, f'{v:.1f}%',
                     ha='center', va='bottom', fontweight='bold', color='red')

        plt.title('Distribución del Primer Dígito de Seguidores\n(Análisis de Benford)',
                  fontsize=14, fontweight='bold')
        plt.xlabel('Primer Dígito (1 al 9)', fontweight='bold')
        plt.ylabel('Frecuencia (%)', fontweight='bold')
        plt.xticks(range(1, 10))
        plt.ylim(0, max(max(frequencies.values), max(benford_df.values)) + 8)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()

        # Guardar el gráfico
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\n📸 Gráfico de Benford guardado en: **{filename}**")

        # Mostrar el gráfico
        plt.show()