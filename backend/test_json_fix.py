import json
import numpy as np
import uuid
from datetime import datetime
from app.models.database import json_dumps

def test_json_serialization():
    data = {
        "id": uuid.uuid4(),
        "int64": np.int64(42),
        "float64": np.float64(3.14),
        "array": np.array([1, 2, 3]),
        "date": datetime.now(),
        "nested": {
            "val": np.int32(100)
        }
    }
    
    try:
        serialized = json_dumps(data)
        print("Serialization SUCCESSful")
        print(f"Result: {serialized}")
        
        # Verify it can be loaded back by standard json
        reloaded = json.loads(serialized)
        assert reloaded["int64"] == 42
        assert reloaded["float64"] == 3.14
        assert reloaded["array"] == [1, 2, 3]
        print("Validation SUCCESSful")
    except Exception as e:
        print(f"Serialization FAILED: {e}")
        exit(1)

if __name__ == "__main__":
    test_json_serialization()
