import re
import unicodedata

def normalize_text(text: str) -> str:
    """
    Advanced text normalization for robust column name matching.
    
    Processing steps:
    1. Convert to lowercase.
    2. Convert camelCase/PascalCase to snake_case.
    3. Remove accents and diacritics.
    4. Replace non-alphanumeric characters with underscores.
    5. Remove redundant underscores.
    
    Args:
        text: Input string (e.g., "dateDécès", "FirstName", "user-id")
        
    Returns:
        Normalized string (e.g., "date_deces", "first_name", "user_id")
    """
    if not text:
        return ""
        
    # 1. camelCase/PascalCase to snake_case
    # Insert underscore before uppercase letters that follow a lowercase letter
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
    
    # 2. Convert to lowercase
    text = text.lower()
    
    # 3. Remove accents (Decompose Unicode characters)
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    
    # 4. Replace non-alphanumeric with underscores
    text = re.sub(r'[^a-z0-9]', '_', text)
    
    # 5. Remove redundant underscores
    text = re.sub(r'_+', '_', text).strip('_')
    
    return text

def get_synonyms_matches(normalized_name: str, synonym_dict: dict[str, list[str]]) -> str | None:
    """
    Check if a normalized name matches any category in the synonym dictionary.
    
    Args:
        normalized_name: The normalized column name.
        synonym_dict: Dictionary mapping category names to lists of synonyms.
        
    Returns:
        The matched category name or None.
    """
    # Direct match on the normalized name
    for category, synonyms in synonym_dict.items():
        if normalized_name in synonyms:
            return category
            
    # Try token-based matching (e.g., if column is "nom_complet", check if "nom" is in synonyms)
    tokens = normalized_name.split('_')
    for token in tokens:
        if len(token) < 2: continue # Skip single-character tokens
        for category, synonyms in synonym_dict.items():
            if token in synonyms:
                # If we match a generic word like "id", ensure it's a strong match
                if token == "id" and normalized_name != "id" and not normalized_name.endswith("_id"):
                    continue
                return category
                
    return None
