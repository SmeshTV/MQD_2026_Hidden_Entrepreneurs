MQD_SUBMISSION - ЧТО ЗДЕСЬ И КАК ИСПОЛЬЗОВАТЬ
===============================================

=== ОСНОВНЫЕ ФАЙЛЫ (в корне MQD_submission/) ===

MQD_2026_Hidden_Entrepreneurs.ipynb
  - Jupyter ноутбук с полным пайплайном
  - Открыть: jupyter notebook, запустить Cell -> Run All
  - Считает данные, строит 35 фич, тренирует CatBoost, считает SHAP
  - На выходе сохраняет .png и .csv прямо в эту папку
  - Время выполнения: ~3-5 минут

mqd_classifier.py
  - Тот же пайплайн, но в виде Python-скрипта
  - Запуск: python mqd_classifier.py
  - Делает то же самое, только без графиков в Jupyter

MQD_pres.pptx
  - Презентация для защиты (27 слайдов)
  - Основной файл для сдачи

=== ГРАФИКИ ===

confusion_matrix.png
  - Матрица ошибок: сколько consumer/business карт модель угадала и перепутала

feature_importance.png
  - Топ-15 фич по важности для модели (%)

shap_summary.png
  - SHAP summary plot: какие фичи как влияют на предсказание

shap_bar.png
  - SHAP bar chart: средняя важность фич

top100_hidden_entrepreneurs.csv
  - 100 карт с наибольшей вероятностью бизнес-активности
  - Колонки: card_number, business_probability, rank, recommended_product

=== ЕСЛИ НАДО ПЕРЕЗАПУСТИТЬ ===

1. Убедись что все .parquet файлы лежат в той же папке или на рабочем столе в MQD/
2. Запусти ноутбук: Run All
3. Графики перезапишутся новыми (с новыми данными, если сплит изменится)

=== ТЕХНИЧЕСКИЕ ДЕТАЛИ ===

- Python 3.12
- Пакеты: pandas, numpy, catboost, scikit-learn, matplotlib, shap
- Данные: business_cards_MDQ.parquet, consumer_cards_MDQ.parquet, merchants_reference.parquet
