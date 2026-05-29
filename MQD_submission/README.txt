MQD_SUBMISSION - PROJECT OVERVIEW
==================================

=== MAIN FILES (in MQD_submission/ root) ===

MQD_2026_Hidden_Entrepreneurs.ipynb
  - Jupyter notebook with the full pipeline (56 cells)
  - Run: Cell -> Run All (~3-5 minutes)
  - Loads parquet data, builds 35 features, trains CatBoost, computes SHAP
  - Saves all .png and .csv to this folder

mqd_classifier.py
  - Same pipeline as a standalone Python script
  - Run: python mqd_classifier.py
  - Works without Jupyter, outputs same results

MQD_pres.pptx
  - Defense presentation (27 slides)
  - Main submission file for the jury

=== OUTPUT FILES ===

confusion_matrix.png
  - Confusion matrix: how many consumer/business cards the model got right/wrong

feature_importance.png
  - Top-15 features by importance (%)

shap_summary.png
  - SHAP summary plot: feature impact direction per card

shap_bar.png
  - SHAP bar chart: mean |SHAP| per feature

top100_hidden_entrepreneurs.csv
  - Top-100 consumer cards with highest business probability
  - Columns: card_number, business_probability, rank, recommended_product

=== HOW TO RERUN ===

1. Make sure business_cards_MDQ.parquet, consumer_cards_MDQ.parquet,
   and merchants_reference.parquet are in the same folder as the notebook
   (or on Desktop/MQD/)
2. Open notebook in Jupyter, hit Run All
3. New .png and .csv will overwrite the old ones

=== TECHNICAL DETAILS ===

- Python 3.12
- Dependencies: pandas, numpy, catboost, scikit-learn, matplotlib, shap
- Data: 12.8M transactions, 105K cards, 35 features
- Model: CatBoost (depth=6, lr=0.1, early stopping)
- Evaluation: AUC-ROC, Confusion Matrix, 5-fold CV, SHAP
