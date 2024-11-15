"""
This module contains the code for robust and accurate hate speech detection.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    RandomizedSearchCV,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, make_scorer, f1_score
from sklearn.ensemble import RandomForestClassifier
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import logging
from typing import Tuple, Optional
import joblib
import os
from imblearn.over_sampling import SMOTE
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Download necessary NLTK data
def download_nltk_resources():
    resources = ["stopwords", "wordnet", "punkt", "punkt_tab"]
    for resource in resources:
        try:
            nltk.download(resource, quiet=True)
            logging.info(f"Successfully downloaded NLTK resource: {resource}")
        except Exception as e:
            logging.error(f"Failed to download NLTK resource {resource}: {str(e)}")


download_nltk_resources()


def preprocess_text(text: str) -> str:
    try:
        # Convert to lowercase
        text = text.lower()
        # Remove URLs, user @ references, '#', punctuations, numbers, and whitespaces
        text = re.sub(r"http\S+|www\S+|https\S+|\@\w+|\#|[^\w\s]|\d+", "", text)
        text = text.strip()

        # Tokenization
        tokens = nltk.word_tokenize(text)

        # Remove stopwords and apply lemmatization
        stop_words = set(stopwords.words("english"))
        lemmatizer = WordNetLemmatizer()
        tokens = [
            lemmatizer.lemmatize(token) for token in tokens if token not in stop_words
        ]

        return " ".join(tokens)
    except Exception as e:
        logging.error(f"Error in text preprocessing: {str(e)}")
        return ""


def load_and_preprocess_dataset(
    file_path: str, text_column: str, label_column: str
) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path)
        df[text_column].head()
        df["processed_text"] = df[text_column].apply(preprocess_text)
        df["label"] = df[label_column]
        return df[["processed_text", "label"]]
    except Exception as e:
        logging.error(f"Error loading or preprocessing data from {file_path}: {str(e)}")
        return pd.DataFrame()


def load_and_merge_datasets() -> pd.DataFrame:

    dataset_configs = [
        ("python/dataset/hate_speech/twitter_parsed_dataset.csv", "text", "class"),
        ("python/dataset/hate_speech/TwitterHate.csv", "tweet", "class"),
        ("python/dataset/hate_speech/aggression_parsed_dataset.csv", "text", "class"),
        (
            "python/dataset/hate_speech/gate_aggression_parsed_dataset.csv",
            "text",
            "class",
        ),
        ("python/dataset/hate_speech/attack_parsed_dataset.csv", "text", "class"),
        ("python/dataset/hate_speech/toxicity_parsed_dataset.csv", "text", "class"),
        ("python/dataset/hate_speech/TwitterHate.csv", "tweet", "class"),
        (
            "python/dataset/hate_speech/twitter_sexism_parsed_dataset.csv",
            "text",
            "class",
        ),
        ("python/dataset/hate_speech/kaggle_parsed_dataset.csv", "text", "class"),
    ]

    dataframes = []
    for file_path, text_column, label_column in dataset_configs:
        df = load_and_preprocess_dataset(file_path, "text", "label")
        if not df.empty:
            dataframes.append(df)

    if not dataframes:
        raise ValueError("No datasets were successfully loaded.")

    merged_df = pd.concat(dataframes, ignore_index=True)
    logging.info(f"Merged dataset shape: {merged_df.shape}")
    return merged_df


def train_hate_speech_model(
    data: pd.DataFrame,
) -> Tuple[RandomForestClassifier, TfidfVectorizer, float]:
    X = data["processed_text"]
    y = data["label"]

    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
    X_vectorized = vectorizer.fit_transform(X)

    # Handle class imbalance
    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_vectorized, y)

    # Hyperparameter tuning
    param_dist = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 4, 5, 6],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    }

    model = RandomForestClassifier(random_state=42)

    random_search = RandomizedSearchCV(
        model,
        param_distributions=param_dist,
        n_iter=10,
        scoring="f1",
        n_jobs=-1,
        cv=5,
        random_state=42,
    )

    random_search.fit(X_resampled, y_resampled)

    best_model = random_search.best_estimator_

    # Cross-validation
    cv_scores = cross_val_score(
        best_model, X_resampled, y_resampled, cv=5, scoring="f1"
    )
    mean_cv_score = np.mean(cv_scores)

    logging.info(f"Mean Cross-Validation F1 Score: {mean_cv_score}")
    logging.info(f"Best Parameters: {random_search.best_params_}")

    return best_model, vectorizer, mean_cv_score


def save_model(
    model: RandomForestClassifier,
    vectorizer: TfidfVectorizer,
    score: float,
    model_dir: str = "models",
):
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(model, os.path.join(model_dir, "hate_speech_model.joblib"))
    joblib.dump(vectorizer, os.path.join(model_dir, "tfidf_vectorizer.joblib"))
    with open(os.path.join(model_dir, "model_score.txt"), "w") as f:
        f.write(str(score))
    logging.info(f"Model saved in {model_dir}")


def load_model(
    model_dir: str = "models",
) -> Tuple[Optional[RandomForestClassifier], Optional[TfidfVectorizer], float]:
    try:
        model = joblib.load(os.path.join(model_dir, "hate_speech_model.joblib"))
        vectorizer = joblib.load(os.path.join(model_dir, "tfidf_vectorizer.joblib"))
        with open(os.path.join(model_dir, "model_score.txt"), "r") as f:
            score = float(f.read())
        logging.info(f"Model loaded successfully from {model_dir}")
        return model, vectorizer, score
    except Exception as e:
        logging.error(f"Error loading model: {str(e)}")
        return None, None, 0.0


def predict_hate_speech(
    text: str, model: RandomForestClassifier, vectorizer: TfidfVectorizer
) -> Tuple[str, float]:
    processed_text = preprocess_text(text)
    vectorized_text = vectorizer.transform([processed_text])
    prediction = model.predict(vectorized_text)
    probability = model.predict_proba(vectorized_text)[0]
    hate_speech_prob = probability[1]  # Assuming 1 is the hate speech class
    logging.info(
        f"Text: '{text}', Prediction: {prediction[0]}, Hate Speech Probability: {hate_speech_prob:.4f}"
    )
    return (
        "Hate Speech" if hate_speech_prob > 0.6 else "Not Hate Speech",
        hate_speech_prob,
    )


def generate_wordcloud(model: RandomForestClassifier, vectorizer: TfidfVectorizer):
    # Get feature importances
    feature_importance = model.feature_importances_
    feature_names = vectorizer.get_feature_names_out()

    # Create a dictionary of feature names and their importances
    word_importance = dict(zip(feature_names, feature_importance))

    # Generate the word cloud
    wordcloud = WordCloud(
        width=800, height=400, background_color="white"
    ).generate_from_frequencies(word_importance)

    # Display the word cloud
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title("Most Important Words in Hate Speech Detection")
    plt.tight_layout(pad=0)

    # Save the word cloud
    plt.savefig("hate_speech_wordcloud.png")
    logging.info("Word cloud saved as 'hate_speech_wordcloud.png'")


# Example usage:
if __name__ == "__main__":
    try:
        model, vectorizer, score = load_model()

        if model is None or vectorizer is None:
            logging.info("No saved model found. Training a new model...")
            merged_data = load_and_merge_datasets()
            model, vectorizer, score = train_hate_speech_model(merged_data)
            save_model(model, vectorizer, score)
        else:
            logging.info(f"Using saved model with score: {score}")

        # Generate and save word cloud
        generate_wordcloud(model, vectorizer)

        # Make predictions
        sample_texts = [
            "I will kill you",
            "I love all people",
            "You're a terrible person and should die",
            "Have a great day!",
            "I hope you get cancer",
            "Let's meet for coffee tomorrow",
            "Fuck you",
        ]

        for sample_text in sample_texts:
            result, probability = predict_hate_speech(sample_text, model, vectorizer)
            print(
                f"Prediction for '{sample_text}': {result} (Probability: {probability:.4f})"
            )

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
