from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
import os
import time
from PyQt6.QtCore import QObject, pyqtSignal
import pandas as pd

class SuggesterWorker(QObject):
    """Worker to handle ML training/prediction in a separate thread."""
    suggestion_finished = pyqtSignal(list)
    
    def __init__(self, suggester, categorized_data):
        super().__init__()
        self.suggester = suggester
        self.categorized_data = categorized_data

    def run(self):
        """Trains the model and predicts suggestions."""
        from .categorizer import (
            CAT_SAFE_DELETE, CAT_USER_DOWNLOADS, CAT_SYSTEM, CAT_APP, 
            CAT_DEV_PROJECT, CAT_USER_DOCUMENTS, CAT_USER, CAT_UNKNOWN
        )

        training_items = []
        labels = []
        
        # Positive examples
        for item in self.categorized_data.get(CAT_SAFE_DELETE, {}).get('items', []):
            training_items.append(item)
            labels.append(1)
        for item in self.categorized_data.get(CAT_USER_DOWNLOADS, {}).get('items', []):
            if item['type'] == 'file':
                training_items.append(item)
                labels.append(1)

        # Negative examples
        protected_cats = [CAT_SYSTEM, CAT_APP, CAT_DEV_PROJECT, CAT_USER_DOCUMENTS]
        for cat in protected_cats:
            sample_items = self.categorized_data.get(cat, {}).get('items', [])[:500]
            for item in sample_items:
                if item['type'] == 'file':
                    training_items.append(item)
                    labels.append(0)

        self.suggester.train(training_items, labels)

        # Prediction pool
        suggestion_pool = (
            self.categorized_data.get(CAT_USER, {}).get('items', []) + 
            self.categorized_data.get(CAT_UNKNOWN, {}).get('items', []) +
            self.categorized_data.get(CAT_USER_DOCUMENTS, {}).get('items', [])
        )
        suggested_files = self.suggester.predict(suggestion_pool)
        self.suggestion_finished.emit(suggested_files)

class DeletionSuggester:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.vectorizer = DictVectorizer(sparse=False)
        self.is_trained = False
        self.feature_names = []

    def _extract_features(self, item):
        """Extracts features from a file item for the model."""
        path = item['path']
        try:
            stat = os.stat(path)
            age = time.time() - stat.st_mtime
            extension = os.path.splitext(path)[1].lower()
        except (FileNotFoundError, PermissionError):
            age = -1
            extension = 'unknown'

        return {
            'size': item.get('size', 0),
            'category': item.get('category', 'Unknown'),
            'age_seconds': age,
            'extension': extension,
            'path_depth': path.count(os.sep)
        }

    def train(self, items, labels):
        """Trains the model based on items and their labels (1 for delete, 0 for keep)."""
        if not items or not labels:
            return

        features = [self._extract_features(item) for item in items]
        X = self.vectorizer.fit_transform(features)
        self.feature_names = self.vectorizer.get_feature_names_out()
        y = labels
        
        self.model.fit(X, y)
        self.is_trained = True
        print("Deletion Suggester model has been trained.")

    def predict(self, items):
        """Predicts which items are likely safe to delete."""
        if not self.is_trained or not items:
            return []

        features = [self._extract_features(item) for item in items]
        X = self.vectorizer.transform(features)

        # Check if the model can predict multiple classes
        if len(self.model.classes_) < 2:
            # Model has only been trained on one class, so it cannot make meaningful suggestions.
            return []
        
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        # Ensure we have probabilities for the "deletable" class (1)
        try:
            deletable_class_index = list(self.model.classes_).index(1)
        except ValueError:
            # The model has never seen a "deletable" example (class '1').
            return []

        deletable_probs = probabilities[:, deletable_class_index]

        suggested_items = []
        for i, (item, pred) in enumerate(zip(items, predictions)):
            if pred == 1:
                item['suggestion_confidence'] = deletable_probs[i]
                suggested_items.append(item)

        return suggested_items

    def explain(self, item):
        """Provides a more user-friendly explanation for a prediction."""
        if not self.is_trained:
            return "The suggestion model has not been trained during this session."

        features = self._extract_features(item)
        reasons = []

        # Age-based reason
        age_days = features.get('age_seconds', 0) / (24 * 60 * 60)
        if age_days > 365:
            reasons.append(f"It is over a year old (approx. {int(age_days)} days).")
        elif age_days > 180:
            reasons.append(f"It is over 6 months old (approx. {int(age_days)} days).")
        elif age_days > 90:
            reasons.append("It is over 3 months old.")

        # Extension-based reason
        ext = features.get('extension')
        if ext in ['.log', '.tmp', '.bak', '.old', '.temp', '.download']:
            reasons.append(f"Files with the '{ext}' extension are often temporary or backups.")
        
        # Category-based reason
        category = features.get('category')
        if category == 'User Downloads':
             reasons.append("It is in your Downloads folder, which often contains disposable files.")
        elif category == 'Unknown':
            reasons.append("It could not be confidently categorized as a system or application file.")

        # Size-based reason (only if it's large)
        size_mb = features.get('size', 0) / (1024 * 1024)
        if size_mb > 500:
             reasons.append(f"It is a large file ({size_mb:.1f} MB).")

        if not reasons:
            return "This file shares multiple characteristics with other files that are commonly deleted."

        return "This file was suggested for deletion because:\n- " + "\n- ".join(reasons) 