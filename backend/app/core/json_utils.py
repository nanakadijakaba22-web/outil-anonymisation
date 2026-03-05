"""
Shared JSON utility functions for handling NumPy, UUID, and Pydantic types.
"""
import json
import uuid
from datetime import datetime
from typing import Any

import numpy as np


class NumpyJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles NumPy types, UUIDs, datetimes, and Pydantic models.
    """

    def default(self, o: Any) -> Any:
        # Handle NumPy types
        if isinstance(o, (np.int64, np.int32, np.int16, np.int8, np.integer)):
            return int(o)
        if isinstance(o, (np.float64, np.float32, np.float16, np.floating)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
            
        # Handle Date/Time types
        if isinstance(o, datetime):
            return o.isoformat()
            
        # Handle UUIDs
        if isinstance(o, uuid.UUID):
            return str(o)
        
        # Handle Pydantic models (v1 and v2)
        if hasattr(o, "model_dump") and callable(o.model_dump):
            return o.model_dump()
        elif hasattr(o, "dict") and callable(o.dict):
            return o.dict()
            
        return super().default(o)


def json_dumps(obj: Any, **kwargs) -> str:
    """
    Serialize object to JSON string using NumpyJSONEncoder.
    Can be used as a custom serializer for SQLAlchemy.
    """
    return json.dumps(obj, cls=NumpyJSONEncoder, **kwargs)
