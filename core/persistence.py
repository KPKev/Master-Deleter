import joblib
import os
import logging

MODEL_FILENAME = "suggester_model.joblib"

def save_suggester(suggester, directory="."):
    """Saves the suggester instance (model + vectorizer) to a file."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    filepath = os.path.join(directory, MODEL_FILENAME)
    try:
        joblib.dump(suggester, filepath)
        logging.info(f"Suggester model saved to {filepath}")
    except Exception as e:
        logging.error(f"Error saving suggester model: {e}", exc_info=True)

def load_suggester(directory="."):
    """Loads a suggester instance from a file."""
    filepath = os.path.join(directory, MODEL_FILENAME)
    if os.path.exists(filepath):
        try:
            suggester = joblib.load(filepath)
            logging.info(f"Suggester model loaded from {filepath}")
            return suggester
        except Exception as e:
            logging.error(f"Error loading suggester model: {e}", exc_info=True)
            return None
    logging.info("Suggester model not found, creating a new one.")
    return None
