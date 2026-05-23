import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import RandomForestClassifier
import logging

logger = logging.getLogger(__name__)

# Blood Compatibility Table: Donor -> Recipient Compatibility
# True means Donor can donate to Recipient
COMPATIBILITY_MATRIX = {
    # Donor: [List of compatible recipients]
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"]
}

# Seed Coordinates for major cities to compute realistic distances
CITY_COORDINATES = {
    # US Cities
    "new york": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "houston": (29.7604, -95.3698),
    "san francisco": (37.7749, -122.4194),
    "seattle": (47.6062, -122.3321),
    # Indian Cities
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    # Defaults / Others
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
}

def get_city_coords(city: str, state: str = "") -> Tuple[float, float]:
    """
    Retrieves coordinates for a city. Uses coordinates lookup,
    or falls back to a deterministic offset based on string hash.
    """
    city_clean = city.strip().lower()
    if city_clean in CITY_COORDINATES:
        return CITY_COORDINATES[city_clean]
    
    # Generate stable random offset based on city name to place them in same region
    h = hash(city_clean)
    lat = 20.0 + (h % 100) / 10.0
    lon = 78.0 + ((h // 100) % 100) / 10.0
    return lat, lon

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points in kilometers.
    """
    R = 6371.0 # Earth's radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def check_compatibility(donor_blood: str, patient_blood: str) -> float:
    """
    Returns 1.0 if the donor's blood is compatible with the patient's blood, else 0.0.
    """
    if not donor_blood or not patient_blood:
        return 0.0
    db = donor_blood.strip().upper()
    pb = patient_blood.strip().upper()
    if db in COMPATIBILITY_MATRIX and pb in COMPATIBILITY_MATRIX[db]:
        return 1.0
    return 0.0


class DonorResponsePredictor:
    """
    Predicts donor response probability based on past interactions, age, distance, and urgency.
    """
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=50, random_state=42)
        self._train_initial_model()

    def _train_initial_model(self):
        """
        Creates a synthetic training dataset and fits the Scikit-Learn RandomForest classifier
        to enable real predictive capabilities.
        """
        # Features: [distance_km, age, past_acceptance_rate, urgency_level_numeric, is_same_blood_group]
        np.random.seed(42)
        n_samples = 500
        
        distances = np.random.uniform(1.0, 40.0, n_samples)
        ages = np.random.randint(18, 65, n_samples)
        past_rates = np.random.uniform(0.1, 0.95, n_samples)
        urgency = np.random.choice([1, 2, 3], n_samples) # 1=low, 2=med, 3=crit
        same_bg = np.random.choice([0, 1], n_samples, p=[0.7, 0.3])
        
        # Logits: higher acceptance for closer, higher past rates, critical cases, and same blood group
        logits = (
            2.0 * past_rates 
            - 0.04 * distances 
            + 0.2 * urgency 
            + 0.5 * same_bg 
            - 0.5
        )
        probabilities = 1 / (1 + np.exp(-logits))
        labels = (probabilities > np.random.uniform(0, 1, n_samples)).astype(int)
        
        X = pd.DataFrame({
            "distance_km": distances,
            "age": ages,
            "past_acceptance_rate": past_rates,
            "urgency": urgency,
            "same_bg": same_bg
        })
        y = labels
        
        self.model.fit(X, y)
        logger.info("DonorResponsePredictor model trained successfully.")

    def predict_probability(self, distance_km: float, age: int, past_rate: float, urgency: str, same_bg: bool) -> float:
        """
        Predicts response probability using the Scikit-learn RandomForest model.
        """
        urgency_map = {"low": 1, "medium": 2, "critical": 3}
        urg_val = urgency_map.get(urgency.lower(), 2)
        bg_val = 1 if same_bg else 0
        
        # Prepare dataframe for prediction
        input_data = pd.DataFrame([{
            "distance_km": distance_km,
            "age": age,
            "past_acceptance_rate": past_rate,
            "urgency": urg_val,
            "same_bg": bg_val
        }])
        
        try:
            # Predict probability of class 1 (Accepted)
            prob = self.model.predict_proba(input_data)[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"Prediction failed, using fallback probability: {e}")
            # Fallback mathematical formula
            fallback_prob = past_rate * 0.6 + (1.0 - min(distance_km / 50.0, 1.0)) * 0.4
            return float(max(0.1, min(fallback_prob, 0.99)))

# Instantiate predictor
response_predictor = DonorResponsePredictor()

def rank_donors(
    patient_blood_group: str,
    patient_coords: Tuple[float, float],
    urgency_level: str,
    donors_list: List[Dict[str, Any]],
    max_radius_km: float = 50.0
) -> List[Dict[str, Any]]:
    """
    Ranks donors based on the specified scoring formula:
    Final Score = 0.40 * Compatibility + 0.20 * Eligibility + 0.15 * Distance + 0.15 * Response Probability + 0.10 * Availability
    """
    scored_donors = []
    
    for donor in donors_list:
        # 1. Compatibility
        compatibility = check_compatibility(donor["blood_group"], patient_blood_group)
        
        # 2. Eligibility
        eligibility = 1.0 if donor.get("is_eligible", True) else 0.0
        
        # 3. Distance calculation
        donor_coords = donor.get("coords")
        if not donor_coords:
            donor_coords = get_city_coords(donor.get("city", ""), donor.get("state", ""))
        
        distance_km = calculate_haversine_distance(
            patient_coords[0], patient_coords[1],
            donor_coords[0], donor_coords[1]
        )
        
        # Normalize distance score (1.0 close, 0.0 at/beyond max_radius_km)
        distance_score = max(0.0, 1.0 - (distance_km / max_radius_km))
        
        # 4. Response Probability
        # Mock some historic details if not present
        past_rate = donor.get("past_acceptance_rate", 0.7)
        age = donor.get("age", 30)
        same_bg = (donor["blood_group"] == patient_blood_group)
        
        response_prob = response_predictor.predict_probability(
            distance_km=distance_km,
            age=age,
            past_rate=past_rate,
            urgency=urgency_level,
            same_bg=same_bg
        )
        
        # 5. Availability
        availability = 1.0 if donor.get("availability", True) else 0.0
        
        # Final Score Blend
        final_score = (
            0.40 * compatibility +
            0.20 * eligibility +
            0.15 * distance_score +
            0.15 * response_prob +
            0.10 * availability
        )
        
        # Append scored info
        donor_info = donor.copy()
        donor_info.update({
            "distance_km": round(distance_km, 2),
            "compatibility_score": compatibility,
            "eligibility_score": eligibility,
            "distance_score": round(distance_score, 2),
            "response_probability": round(response_prob, 2),
            "availability_score": availability,
            "final_score": round(final_score, 4)
        })
        scored_donors.append(donor_info)
        
    # Sort descending by final score
    scored_donors.sort(key=lambda x: x["final_score"], reverse=True)
    return scored_donors
